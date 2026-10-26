from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from core.common import ROOT
from scripts import package_release


class PackageTests(unittest.TestCase):
    def setUp(self):
        base = (ROOT/".test-output").resolve()
        base.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="package-test-",dir=base)
        self.root = Path(self.temp.name).resolve()
        assert self.root.is_relative_to(base) and self.root != base
        for name in package_release.ROOT_FILES:
            (self.root/name).write_text("source fixture",encoding="utf-8")
        files = {
            "core/main.py":"print('source')", "skills/style/SKILL.md":"style instructions",
            "profiles/demo.json":"{}", "scripts/setup.ps1":"# setup", "tests/test_demo.py":"# test",
            "motion/src/index.tsx":"// source", "motion/package.json":"{}", "motion/package-lock.json":"{}",
            "motion/tsconfig.json":"{}", "motion/render.mjs":"// renderer",
            "editor/package.json":"{}", "editor/package-lock.json":"{}", "editor/index.html":"<html></html>",
            "editor/src/main.tsx":"// UI source", "editor/src/style.css":"body{}",
            "editor/build/assets/private.js":"PRIVATE BUILD", "editor/node_modules/private.js":"PRIVATE NODE MODULE",
            "preferences/default.json":json.dumps({"feedback_sources":["PRIVATE FEEDBACK"],"overrides":{"private":"secret"}}),
            ".env":"SECRET=value", ".tools/model.bin":"PRIVATE MODEL", ".venv/private.py":"PRIVATE ENV",
            "jobs/private/export.mp4":"PRIVATE VIDEO", "inbox/private.mp4":"PRIVATE INPUT", "sample.mp4":"REFERENCE VIDEO",
            "motion/node_modules/private.js":"PRIVATE DEPENDENCY", "motion/.cache/bundle.js":"PRIVATE CACHE",
            "core/__pycache__/should-not-copy.py":"PRIVATE BYTECODE CACHE",
        }
        for name,content in files.items():
            path = self.root/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(content,encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_release_excludes_private_runtime_and_hashes_all_payload_files(self):
        output = self.root/"dist/share.zip"
        with patch.object(package_release,"ROOT",self.root):
            package_release.package(output)
        with zipfile.ZipFile(output) as bundle:
            names = bundle.namelist()
            self.assertIsNone(bundle.testzip())
            self.assertIn("ai-editor/HUONG-DAN.html",names)
            self.assertIn("ai-editor/motion/package-lock.json",names)
            self.assertIn("ai-editor/skills/style/SKILL.md",names)
            self.assertIn("ai-editor/editor/src/main.tsx",names)
            self.assertIn("ai-editor/editor/package-lock.json",names)
            self.assertFalse(any(name.startswith("ai-editor/editor/build/") for name in names))
            self.assertTrue(all(name.startswith("ai-editor/") and ".." not in Path(name).parts for name in names))
            self.assertEqual([name for name in names if name.startswith("ai-editor/jobs/")],["ai-editor/jobs/.gitkeep"])
            self.assertEqual([name for name in names if name.startswith("ai-editor/inbox/")],["ai-editor/inbox/.gitkeep"])
            self.assertFalse(any(any(part in name for part in (".env",".tools/",".venv/","node_modules/",".cache/","__pycache__/","sample.mp4")) for name in names))
            preference = json.loads(bundle.read("ai-editor/preferences/default.json"))
            self.assertEqual(preference["feedback_sources"],[])
            self.assertEqual(preference["overrides"],{})
            manifest = json.loads(bundle.read("ai-editor/MANIFEST.json"))
            self.assertEqual(len(names),len(manifest["files_sha256"])+1)
            for name,digest in manifest["files_sha256"].items():
                self.assertEqual(hashlib.sha256(bundle.read("ai-editor/"+name)).hexdigest(),digest)
        self.assertEqual(output.with_suffix(".zip.sha256").read_text().split()[0],hashlib.sha256(output.read_bytes()).hexdigest())
        self.assertEqual((self.root/"jobs/private/export.mp4").read_text(),"PRIVATE VIDEO")
        self.assertEqual((self.root/"preferences/default.json").read_text().count("PRIVATE FEEDBACK"),1)
        self.assertFalse(list((self.root/"dist").glob(".package-*")))

    def test_existing_release_and_output_outside_dist_are_preserved(self):
        output = self.root/"dist/share.zip"
        output.parent.mkdir()
        output.write_bytes(b"existing release")
        with patch.object(package_release,"ROOT",self.root):
            with self.assertRaises(FileExistsError):
                package_release.package(output)
            with self.assertRaises(ValueError):
                package_release.package(self.root/"outside.zip")
        self.assertEqual(output.read_bytes(),b"existing release")
        self.assertFalse((self.root/"outside.zip").exists())


if __name__ == "__main__":
    unittest.main()
