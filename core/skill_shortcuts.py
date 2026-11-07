"""Repo-scoped Codex discovery entrypoints for the pinned video library."""
from __future__ import annotations

import json
from pathlib import Path

from core.common import EditorError, ROOT, identifier, within
from core.skill_library import catalog


def native_name(source_key, package_name):
    suffix = package_name if package_name == source_key or package_name.startswith(source_key + "-") else source_key + "-" + package_name
    name = identifier("video-" + suffix)
    if len(name) > 64:
        raise EditorError(f"Native skill name is too long: {name}")
    return name


def entries(root=ROOT):
    data = catalog(root)
    result = []
    for source in data["sources"]:
        for package in source["packages"]:
            target = within(root, data["install_root"] + "/" + source["key"] + "/" + package["name"] + "/SKILL.md")
            result.append({"name": native_name(source["key"], package["name"]),
                           "description": package["menu_description"], "id": package["id"],
                           "target": target.relative_to(root).as_posix(), "kind": "package"})
    for group in data["groups"]:
        name = identifier("video-group-" + group["id"])
        if len(name) > 64:
            raise EditorError(f"Native group name is too long: {name}")
        result.append({"name": name, "description": group["menu_description"], "id": group["id"],
                       "target": "skills/styles/" + identifier(group["id"]) + "/SKILL.md", "kind": "group"})
    if len({item["name"] for item in result}) != len(result):
        raise EditorError("Native skill names must be unique across sources and groups.")
    return result


def entry_text(item):
    label = "nhóm" if item["kind"] == "group" else "skill"
    return ("---\nname: " + item["name"] + "\ndescription: " + json.dumps(item["description"], ensure_ascii=False) +
            "\n---\n\n# " + item["name"] + "\n\n" +
            "Đây là entrypoint để Codex nhận diện qua menu skill. Khi được chọn, dùng " + label + " `" + item["id"] +
            "` cho đúng phạm vi yêu cầu.\n\n" +
            "Đọc [hướng dẫn tích hợp dự án](../../../core/skill-library.md), rồi đọc [SKILL.md gốc](../../../" + item["target"] +
            ") trước khi thực hiện. Chỉ tải references/helper cần cho tác vụ.\n\n" +
            "Thư mục upstream thực tế nằm trong `.tools/skill-library/`; ánh xạ đường dẫn ví dụ của upstream tới đó. " +
            "Nếu source chưa có, chạy `scripts/install_skill_library.py` tại repo để khôi phục đúng bản đã pin. " +
            "Việc gọi entrypoint không tự setup engine, chọn thêm style hoặc thay workflow khóa/duyệt của project.\n")


def shortcut_status(item, root=ROOT):
    path = within(root, ".agents/skills/" + item["name"] + "/SKILL.md")
    if not path.is_file():
        return "missing"
    return "registered" if path.read_text(encoding="utf-8-sig") == entry_text(item) else "modified"


def check_shortcuts(root=ROOT):
    return [{"name": item["name"], "id": item["id"], "kind": item["kind"],
             "status": shortcut_status(item, root)} for item in entries(root)]


def register_shortcuts(root=ROOT):
    planned = entries(root)
    # Check every existing entry before writing, preserving local authoring changes.
    for item in planned:
        if shortcut_status(item, root) == "modified":
            raise EditorError(f"Preserved modified native skill: {item['name']}. Review that file before regenerating.")
        if not within(root, item["target"]).is_file():
            raise EditorError(f"Missing target for {item['name']}: {item['target']}. Restore the library first.")
    created = 0
    for item in planned:
        path = within(root, ".agents/skills/" + item["name"] + "/SKILL.md")
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(entry_text(item))
            created += 1
    return {"registered": len(planned), "created": created}
