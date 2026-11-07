"""Pinned upstream skills, loaded per group; installation does not run their engines."""
from __future__ import annotations

import hashlib
from pathlib import Path

from core.common import EditorError, ROOT, read_json, within

RUNTIME_PARTS = {"node_modules", "__pycache__", ".cache", ".git"}


def content_digest(folder):
    """Hash source paths and bytes independently of the installation directory."""
    folder = Path(folder).resolve()
    result = hashlib.sha256()
    for path in sorted(folder.rglob("*")):
        relative = path.relative_to(folder)
        if set(relative.parts) & RUNTIME_PARTS or not path.is_file():
            continue
        if path.is_symlink() or not path.resolve().is_relative_to(folder):
            raise EditorError(f"Skill contains an unsafe path: {relative}")
        result.update(relative.as_posix().encode("utf-8") + b"\0")
        result.update(hashlib.sha256(path.read_bytes()).digest())
    return result.hexdigest()


def catalog(root=ROOT):
    return read_json(Path(root) / "skills/library.json")


def package_info(package_id, root=ROOT):
    data = catalog(root)
    for source in data["sources"]:
        for package in source["packages"]:
            if package["id"] == package_id:
                folder = within(root, data["install_root"] + "/" + source["key"] + "/" + package["name"])
                return source, package, folder
    raise EditorError(f"Unknown upstream skill: {package_id}")


def package_status(source, package, folder, *, full=False):
    entry = folder / "SKILL.md"
    if not entry.is_file():
        return "missing"
    actual = hashlib.sha256(entry.read_bytes()).hexdigest()
    if actual != package["entrypoint_sha256"]:
        return "modified"
    if full and content_digest(folder) != package["content_sha256"]:
        return "modified"
    return "installed"


def inventory(root=ROOT, *, full=False):
    data = catalog(root)
    rows = []
    for source in data["sources"]:
        for package in source["packages"]:
            _, _, folder = package_info(package["id"], root)
            rows.append({"id": package["id"], "repo": source["repo"], "commit": source["commit"],
                         "status": package_status(source, package, folder, full=full),
                         "license": source["license"], "path": folder.relative_to(root).as_posix()})
    return {"groups": data["groups"], "packages": rows,
            "note": "Installed means skill files are present; upstream engines/services require separate setup."}


def snapshot(package_id, root=ROOT):
    source, package, folder = package_info(package_id, root)
    status = package_status(source, package, folder, full=True)
    if status != "installed":
        raise EditorError(f"Upstream skill {package_id} is {status}. Run scripts/install_skill_library.py; changed files are never overwritten automatically.")
    # Instructions are frozen in the job. Executable/assets stay pinned by the content hash.
    files = {path.relative_to(folder).as_posix(): path.read_text(encoding="utf-8-sig")
             for path in sorted(folder.rglob("*.md"))
             if path.is_file() and not (set(path.relative_to(folder).parts) & RUNTIME_PARTS)}
    return {"id": "upstream/" + package_id, "version": source["commit"], "files": files,
            "source": {"repo": source["repo"], "path": package["source_path"],
                       "content_sha256": package["content_sha256"], "license": source["license"]}}
