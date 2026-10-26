"""Build a source-only sharing ZIP, excluding media, dependencies and personal jobs."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = (
    "ai_editor.py", "AGENTS.md", "README.md", "HUONG-DAN.html",
    "ai-video-editor-project.md", "requirements-stt.txt", "requirements-vision.txt", ".gitignore",
)
SOURCE_DIRS = ("core", "skills", "profiles", "scripts", "tests", "editor")
MOTION_FILES = ("package.json", "package-lock.json", "tsconfig.json", "render.mjs")
EXTENSIONS = {".py", ".md", ".txt", ".json", ".ps1", ".tsx", ".ts", ".mjs", ".css", ".html", ".svg"}
EXCLUDED_PARTS = {"__pycache__", "node_modules", ".cache", ".git", ".venv", ".tools", ".test-output", "dist", "build"}
EXCLUDED = ["Source/reference videos and audio", "Personal jobs and exports", "Downloaded tools and model weights", "Virtual environments and node_modules", "Caches, compiled files and test output", "Personal preference feedback history and environment files"]


def selected_files():
    files = [ROOT / name for name in ROOT_FILES]
    for name in SOURCE_DIRS:
        files.extend(path for path in (ROOT/name).rglob("*") if path.is_file() and path.suffix.lower() in EXTENSIONS and not (set(path.relative_to(ROOT).parts) & EXCLUDED_PARTS))
    files.extend(ROOT/"motion"/name for name in MOTION_FILES)
    files.extend(path for path in (ROOT/"motion/src").rglob("*") if path.is_file() and path.suffix.lower() in EXTENSIONS)
    for path in files:
        if not path.is_file() or not path.resolve().is_relative_to(ROOT):
            raise ValueError(f"Missing source file or path outside project: {path.name}")
    return sorted(set(files))


def package(output):
    output = Path(output).resolve()
    dist = (ROOT/"dist").resolve()
    if not output.is_relative_to(dist) or output.suffix.lower() != ".zip":
        raise ValueError("The release ZIP must be inside this project's dist/ directory.")
    if output.exists() or output.with_suffix(".zip.sha256").exists():
        raise FileExistsError("Release already exists. Choose another --output filename.")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".package-", dir=output.parent) as temporary:
        temporary = Path(temporary).resolve()
        # TemporaryDirectory recursively cleans up only this verified workspace path.
        assert temporary.is_relative_to(dist) and temporary != dist
        stage = temporary/"ai-editor"
        stage.mkdir()
        for path in selected_files():
            target = stage/path.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path,target)
        for name in ("inbox", "jobs"):
            (stage/name).mkdir()
            (stage/name/".gitkeep").touch()
        (stage/"preferences").mkdir()
        preference = {"scope":"user", "editorial_preferences":{"primary_platform":"tiktok"}, "overrides":{}, "feedback_sources":[]}
        (stage/"preferences/default.json").write_text(json.dumps(preference,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        entries = {path.relative_to(stage).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(stage.rglob("*")) if path.is_file()}
        manifest = {"name":"AI Editor", "package_kind":"source-only", "created_at":datetime.now(timezone.utc).isoformat(), "entry_guide":"HUONG-DAN.html", "excluded":EXCLUDED, "files_sha256":entries}
        (stage/"MANIFEST.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        archive = temporary/"release.zip"
        with zipfile.ZipFile(archive,"x",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as bundle:
            for path in sorted(stage.rglob("*")):
                if path.is_file():
                    bundle.write(path,"ai-editor/"+path.relative_to(stage).as_posix())
        with zipfile.ZipFile(archive) as bundle:
            if bundle.testzip() is not None:
                raise ValueError("ZIP integrity check failed.")
        checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
        with output.open("xb") as dest, archive.open("rb") as source:
            shutil.copyfileobj(source,dest)
        with output.with_suffix(".zip.sha256").open("x",encoding="utf-8") as f:
            f.write(f"{checksum}  {output.name}\n")
    print(f"ZIP: {output}\nFiles: {len(entries)+1}\nSize: {output.stat().st_size:,} bytes\nSHA-256: {checksum}")
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=ROOT/"dist"/f"ai-editor-tiktok-{datetime.now(timezone.utc):%Y-%m-%d}.zip")
    args = parser.parse_args()
    try:
        package(args.output)
    except (OSError,ValueError,zipfile.BadZipFile) as error:
        parser.exit(1,f"ERROR: {error}\n")


if __name__ == "__main__":
    main()
