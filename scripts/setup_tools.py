"""Install a portable FFmpeg build inside this project on Windows."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"


def main():
    target = ROOT / ".tools" / "ffmpeg"
    binaries = target / "bin"
    if all((binaries / name).is_file() for name in ("ffmpeg.exe", "ffprobe.exe")):
        subprocess.run([str(binaries / "ffmpeg.exe"), "-version"], check=True)
        return
    if os.name != "nt" or platform.machine().lower() not in ("amd64", "x86_64"):
        raise SystemExit("Install FFmpeg and ffprobe for your platform and add them to PATH.")
    target.mkdir(parents=True, exist_ok=True)
    archive = target / "download.zip"
    print("Downloading portable FFmpeg from gyan.dev (about 100 MB)...", flush=True)
    checksum_text = urllib.request.urlopen(URL + ".sha256", timeout=60).read().decode()
    expected = re.search(r"\b[0-9a-fA-F]{64}\b", checksum_text)
    if not expected:
        raise SystemExit("Could not read the publisher's SHA-256 checksum.")
    with urllib.request.urlopen(URL, timeout=60) as response, archive.open("wb") as output:
        shutil.copyfileobj(response, output)
    with archive.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual.lower() != expected.group().lower():
        raise SystemExit("Checksum mismatch. No binaries were installed; run setup again.")
    binaries.mkdir(exist_ok=True)
    # Copy only known files; do not extract arbitrary paths from the archive.
    with zipfile.ZipFile(archive) as bundle:
        for name in ("ffmpeg.exe", "ffprobe.exe"):
            matches = [entry for entry in bundle.namelist() if entry.endswith("/bin/" + name)]
            if len(matches) != 1:
                raise SystemExit(f"Expected one {name} in the archive.")
            with bundle.open(matches[0]) as source, (binaries / name).open("wb") as dest:
                shutil.copyfileobj(source, dest)
        for entry in bundle.namelist():
            if Path(entry).name.upper() in ("LICENSE", "LICENSE.TXT"):
                (target / "LICENSE.txt").write_bytes(bundle.read(entry))
    (target / "source.json").write_text(json.dumps({"url": URL, "sha256": actual}, indent=2))
    archive.unlink()
    print(f"Installed: {binaries}")


if __name__ == "__main__":
    main()
