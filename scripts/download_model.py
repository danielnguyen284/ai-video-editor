"""Restore the standing faster-whisper large-v3 model (pinned revision, verified checksum).

Setup runs this only with -WithModel. It downloads the same model the workflow selects
into .tools/models/faster-whisper-large-v3; it never switches to another model. An
interrupted download resumes from the partial file when the script runs again.
"""
from __future__ import annotations

import argparse
import hashlib
from http.client import HTTPException
import json
from pathlib import Path
import shutil
import sys
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "Systran/faster-whisper-large-v3"
REVISION = "edaa852ec7e145841d8ffdb056a99866b5f0a478"
MODEL_SHA256 = "69f74147e3334731bc3a76048724833325d2ec74642fb52620eda87352e3d4f1"
FILES = ("config.json", "preprocessor_config.json", "tokenizer.json", "vocabulary.json", "model.bin")
NEEDED_BYTES = 3_300_000_000


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 24), b""):
            digest.update(block)
    return digest.hexdigest()


def fetch(url, target, *, quiet=False):
    """Download url to target, resuming from target.part when it exists."""
    partial = target.with_name(target.name + ".part")
    have = partial.stat().st_size if partial.exists() else 0
    request = Request(url, headers={"User-Agent": "AI-Editor-setup", **({"Range": f"bytes={have}-"} if have else {})})
    with urlopen(request, timeout=60) as response:
        if have and response.status != 206:
            have = 0  # The server ignored the range: start again.
        total = have + int(response.headers.get("Content-Length") or 0)
        step, shown = max(total // 20, 1), have
        with partial.open("ab" if have else "wb") as output:
            while True:
                block = response.read(1 << 20)
                if not block:
                    break
                output.write(block)
                have += len(block)
                if not quiet and total > 50_000_000 and have - shown >= step:
                    shown = have
                    print(f"  {target.name}: {have / 1e9:.2f} / {total / 1e9:.2f} GB", flush=True)
    if total > have:
        raise OSError(f"{target.name} stopped at {have} of {total} bytes")
    partial.replace(target)


def restore(target=None, *, base_url=None, files=FILES, model_sha256=MODEL_SHA256, needed=NEEDED_BYTES, quiet=False):
    target = Path(target or ROOT / ".tools/models/faster-whisper-large-v3")
    base_url = base_url or f"https://huggingface.co/{REPOSITORY}/resolve/{REVISION}"
    target.mkdir(parents=True, exist_ok=True)
    model = target / "model.bin"
    complete = all((target / name).is_file() for name in files)
    if complete:
        print("Model files present; verifying model.bin checksum...", flush=True)
        if sha256(model) == model_sha256:
            print(f"Model ready: {target}")
            return target
        raise SystemExit(f"model.bin in {target} does not match the pinned checksum. Move the folder aside, then run setup -WithModel again.")
    if shutil.disk_usage(target).free < needed:
        raise SystemExit(f"Not enough disk space for the model: need about {needed / 1e9:.1f} GB free on this drive.")
    print(f"Downloading {REPOSITORY} at {REVISION[:12]} (about 3 GB). Re-running resumes an interrupted download.", flush=True)
    for name in files:
        if not (target / name).is_file():
            fetch(f"{base_url}/{name}", target / name, quiet=quiet)
    print("Verifying model.bin checksum...", flush=True)
    if sha256(model) != model_sha256:
        model.replace(model.with_name("model.bin.bad"))
        raise SystemExit("Downloaded model.bin does not match the pinned checksum; it was renamed model.bin.bad. Run setup -WithModel again.")
    (target / "source.json").write_text(json.dumps({"repository": REPOSITORY, "revision": REVISION, "model_sha256": model_sha256}, indent=2) + "\n",
                                        encoding="utf-8")
    print(f"Model ready: {target}")
    return target


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, help="Model folder (default: the standing local large-v3 folder)")
    args = parser.parse_args()
    try:
        restore(args.target)
    except (OSError, HTTPException) as error:
        print(f"ERROR: download failed ({error}). Check the connection and run the same command again to resume.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
