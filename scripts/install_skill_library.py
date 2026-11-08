"""Restore the pinned project skill library from GitHub (no Codex or other agent required).

Each source repository is downloaded once as the ZIP of its pinned commit; only the
listed package folders are extracted, and a package is kept only when its content
checksum matches skills/library.json. Changed or partial packages are never overwritten.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path, PurePosixPath
import shutil
import sys
import tempfile
from urllib.request import Request, urlopen
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.common import EditorError, within
from core.skill_library import catalog, content_digest, inventory, package_status
from core.skill_shortcuts import check_shortcuts, register_shortcuts

HEADERS = {"User-Agent": "AI-Editor-skill-library"}


def download(url, target):
    with urlopen(Request(url, headers=HEADERS), timeout=180) as response, target.open("wb") as output:
        shutil.copyfileobj(response, output)
    return target


def extract(bundle, source_path, folder):
    """Copy one folder of a GitHub source ZIP into `folder`, refusing unsafe or linked paths."""
    names = bundle.namelist()
    top = names[0].split("/")[0] + "/"
    prefix = top if source_path in (".", "") else top + source_path.strip("/") + "/"
    members = [name for name in names if name.startswith(prefix) and not name.endswith("/")]
    if not members:
        raise EditorError(f"{source_path} is not in the downloaded source.")
    for name in members:
        relative = PurePosixPath(name[len(prefix):])
        if relative.is_absolute() or ".." in relative.parts:
            raise EditorError(f"Unsafe path in source archive: {name}")
        info = bundle.getinfo(name)
        if (info.external_attr >> 16) & 0o170000 == 0o120000:
            raise EditorError(f"Symbolic link in source archive: {name}")
        destination = folder / Path(*relative.parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with bundle.open(info) as stream, destination.open("xb") as output:
            shutil.copyfileobj(stream, output)


def install(root=ROOT):
    root = Path(root)
    data = catalog(root)
    install_root = within(root, data["install_root"])
    install_root.mkdir(parents=True, exist_ok=True)
    for source in data["sources"]:
        destination = within(root, data["install_root"] + "/" + source["key"])
        missing = []
        for package in source["packages"]:
            folder = destination / package["name"]
            state = package_status(source, package, folder, full=True)
            if state == "modified" or (state == "missing" and folder.exists()):
                raise EditorError(f"Preserved changed/incomplete package: {folder}. Move it aside explicitly before reinstalling.")
            if state == "missing":
                missing.append(package)
        if missing:
            print(f"Downloading {source['repo']} at {source['commit'][:12]} ({len(missing)} package(s))...", flush=True)
            with tempfile.TemporaryDirectory(prefix=".download-", dir=install_root) as temp:
                temp = Path(temp)
                archive = download(f"https://codeload.github.com/{source['repo']}/zip/{source['commit']}", temp / "source.zip")
                with zipfile.ZipFile(archive) as bundle:
                    for package in missing:
                        staged = temp / "staged" / package["name"]
                        extract(bundle, package["source_path"], staged)
                        if content_digest(staged) != package["content_sha256"]:
                            raise EditorError(f"Checksum mismatch for {package['id']}; nothing was installed for it.")
                        destination.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(staged), str(destination / package["name"]))
        license_path = destination / "UPSTREAM-LICENSE"
        if not license_path.is_file():
            payload = urlopen(Request(f"https://raw.githubusercontent.com/{source['repo']}/{source['commit']}/LICENSE", headers=HEADERS),
                              timeout=45).read()
            if hashlib.sha256(payload).hexdigest() != source["license_sha256"]:
                raise EditorError(f"License checksum mismatch: {source['repo']}")
            destination.mkdir(parents=True, exist_ok=True)
            with license_path.open("xb") as stream:
                stream.write(payload)
    rows = inventory(root, full=True)["packages"]
    if any(row["status"] != "installed" for row in rows):
        raise EditorError("Skill verification failed; run --check for details.")
    shortcuts = register_shortcuts(root)
    print(f"Registered {shortcuts['registered']} project skill shortcuts in {' and '.join(shortcuts['folders'])}.")
    print(f"Verified {len(rows)} pinned skills. No upstream setup, model download or external service was started.")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
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
                print(f"{row['status']:10} {row['invoke']}")
            return int(any(row["status"] != "installed" for row in rows) or bool(invalid))
        install()
        return 0
    except (EditorError, OSError, ValueError, zipfile.BadZipFile) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
