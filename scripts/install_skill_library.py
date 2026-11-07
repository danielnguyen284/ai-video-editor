"""Restore the pinned project skill library through Codex's skill-installer helper."""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import sys
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.common import EditorError, within
from core.skill_library import catalog, inventory, package_status
from core.skill_shortcuts import check_shortcuts, register_shortcuts


def install(installer):
    installer = Path(installer).resolve()
    if not installer.is_file():
        raise EditorError("Codex skill-installer helper not found. Supply --installer PATH to install-skill-from-github.py.")
    data = catalog()
    for source in data["sources"]:
        destination = within(ROOT, data["install_root"] + "/" + source["key"])
        missing = []
        for package in source["packages"]:
            folder = destination / package["name"]
            state = package_status(source, package, folder, full=True)
            if state == "modified" or (state == "missing" and folder.exists()):
                raise EditorError(f"Preserved changed/incomplete package: {folder}. Move it aside explicitly before reinstalling.")
            if state == "missing":
                missing.append(package)
        if missing:
            command = [sys.executable, str(installer), "--repo", source["repo"], "--ref", source["commit"],
                       "--dest", str(destination), "--method", "download", "--path",
                       *(p["source_path"] for p in missing)]
            if any(p["source_path"] == "." for p in missing):
                if len(missing) != 1:
                    raise EditorError("A root skill must be installed separately.")
                command += ["--name", missing[0]["name"]]
            result = subprocess.run(command)
            if result.returncode:
                raise EditorError(f"Skill installation failed for {source['repo']} (exit {result.returncode}). Existing packages were preserved.")
        license_path = destination / "UPSTREAM-LICENSE"
        if not license_path.is_file():
            request = Request(f"https://raw.githubusercontent.com/{source['repo']}/{source['commit']}/LICENSE",
                              headers={"User-Agent": "AI-Editor-skill-library"})
            with urlopen(request, timeout=45) as response:
                payload = response.read()
            if hashlib.sha256(payload).hexdigest() != source["license_sha256"]:
                raise EditorError(f"License checksum mismatch: {source['repo']}")
            destination.mkdir(parents=True, exist_ok=True)
            with license_path.open("xb") as stream:
                stream.write(payload)
    rows = inventory(full=True)["packages"]
    if any(row["status"] != "installed" for row in rows):
        raise EditorError("Skill verification failed; run --check for details.")
    shortcuts = register_shortcuts()
    print(f"Registered {shortcuts['registered']} project skill shortcuts in .agents/skills.")
    print(f"Verified {len(rows)} pinned skills. No upstream setup, model download or external service was started.")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    codex_root = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installer", type=Path, default=codex_root / "skills/.system/skill-installer/scripts/install-skill-from-github.py")
    parser.add_argument("--check", action="store_true", help="Check every installed source file without network or mutation")
    args = parser.parse_args()
    try:
        if args.check:
            rows = inventory(full=True)["packages"]
            for row in rows:
                print(f"{row['status']:10} {row['id']}")
            shortcuts = check_shortcuts()
            invalid = [row for row in shortcuts if row["status"] != "registered"]
            print(f"Native entrypoints: {len(shortcuts) - len(invalid)}/{len(shortcuts)} registered")
            for row in invalid:
                print(f"{row['status']:10} ${row['name']}")
            return int(any(row["status"] != "installed" for row in rows) or bool(invalid))
        install(args.installer)
        return 0
    except (EditorError, OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
