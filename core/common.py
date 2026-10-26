from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]


class EditorError(Exception):
    """Actionable local workflow error, not a video quality judgment."""


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, data, *, replace=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w" if replace else "x", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def merge(base, extra):
    result = deepcopy(base)
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def identifier(value):
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value):
        raise EditorError("Use a lowercase ID containing letters, numbers and hyphens.")
    return value


def within(base, relative):
    base = Path(base).resolve()
    path = (base / relative).resolve()
    if not path.is_relative_to(base):
        raise EditorError(f"Path must stay inside {base}: {relative}")
    return path


def executable(name):
    configured = os.environ.get("AI_EDITOR_" + name.upper())
    if configured:
        if not Path(configured).is_file():
            raise EditorError(f"Configured {name} does not exist: {configured}")
        return configured
    local = ROOT / ".tools" / "ffmpeg" / "bin" / (name + (".exe" if os.name == "nt" else ""))
    found = str(local) if local.is_file() else shutil.which(name)
    if not found:
        raise EditorError(f"Missing {name}. Run: python scripts/setup_tools.py")
    return found


def resolve_profile(profile_id):
    profile = read_json(ROOT / "profiles" / (identifier(profile_id) + ".json"))
    snapshots = []
    settings = {}
    for kind in ("style", "domain"):
        selected = profile["skills"][kind]
        prefix, name = selected["id"].split("/", 1)
        if prefix != kind:
            raise EditorError(f"Expected a {kind} skill: {selected['id']}")
        folder = ROOT / "skills" / ("styles" if kind == "style" else "domains") / identifier(name)
        metadata = read_json(folder / "skill.json")
        if metadata["id"] != selected["id"] or metadata["version"] != selected["version"]:
            raise EditorError(f"Skill ID/version mismatch: {folder}")
        if not (folder / "SKILL.md").is_file():
            raise EditorError(f"Missing skill entrypoint: {folder}")
        files = {
            str(path.relative_to(folder)).replace("\\", "/"): path.read_text(encoding="utf-8-sig")
            for path in sorted(folder.rglob("*"))
            if path.is_file() and path.suffix in (".md", ".txt", ".json")
        }
        snapshots.append({"id": metadata["id"], "version": metadata["version"], "files": files})
        settings = merge(settings, metadata.get("defaults", {}))
    preference = read_json(within(ROOT, profile["preferences_ref"]))
    settings = merge(settings, preference.get("overrides", {}))
    settings = merge(settings, profile.get("overrides", {}))
    return {
        "schema_version": "1.0", "profile": profile, "skills": snapshots,
        "settings": settings, "resolved_at": timestamp(),
        "precedence": ["skill defaults", "user preferences", "profile overrides", "edit plan"],
    }
