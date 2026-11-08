"""Repo-scoped Codex and Claude Code discovery entrypoints for the pinned video library."""
from __future__ import annotations

import json
from pathlib import Path

from core.common import EditorError, ROOT, identifier, within
from core.skill_library import catalog

# Each agent host scans its own folder; both use the same relative depth to the targets.
HOSTS = ({"key": "codex", "folder": ".agents/skills", "label": "Codex", "prefix": "$"},
         {"key": "claude", "folder": ".claude/skills", "label": "Claude Code", "prefix": "/"})


WORKFLOW = {"name": "video-edit", "id": "workflow/edit", "kind": "workflow", "target": "core/agent-playbook.md",
            "description": "Dựng hoặc sửa một video trong repo này theo quy trình chuẩn: phân tích nguồn, đề xuất một phương án, chờ duyệt, dựng, xem thử, xuất và sửa tiếp trong Studio."}


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
    # The project workflow itself, so every host can start an edit the same way.
    if (Path(root) / WORKFLOW["target"]).is_file():
        result.append(dict(WORKFLOW))
    if len({item["name"] for item in result}) != len(result):
        raise EditorError("Native skill names must be unique across sources and groups.")
    return result


def entry_text(item, host=HOSTS[0]):
    if item["kind"] == "workflow":
        return ("---\nname: " + item["name"] + "\ndescription: " + json.dumps(item["description"], ensure_ascii=False) +
                "\n---\n\n# " + item["name"] + "\n\n" +
                "Đây là entrypoint để " + host["label"] + " bắt đầu mọi yêu cầu dựng hoặc sửa video trong repo này.\n\n" +
                "1. Đọc [AGENTS.md](../../../AGENTS.md), [quy trình mặc định](../../../core/editing-workflow.md) và `preferences/workflow.json`, `preferences/default.json`.\n" +
                "2. Làm theo [sổ tay agent](../../../" + item["target"] + "): phân tích, gửi một phương án, chờ duyệt, rồi dùng các lệnh `cut`, `captions`, `preview`, `render`.\n" +
                "3. Chọn một nhóm skill cho output (menu `video-group-...`) và chỉ đọc helper cần dùng.\n\n" +
                "Entry này không tự chọn style, không bỏ qua bước duyệt và không thay khóa vùng của Studio.\n")
    label = "nhóm" if item["kind"] == "group" else "skill"
    return ("---\nname: " + item["name"] + "\ndescription: " + json.dumps(item["description"], ensure_ascii=False) +
            "\n---\n\n# " + item["name"] + "\n\n" +
            "Đây là entrypoint để " + host["label"] + " nhận diện qua menu skill. Khi được chọn, dùng " + label + " `" + item["id"] +
            "` cho đúng phạm vi yêu cầu.\n\n" +
            "Đọc [hướng dẫn tích hợp dự án](../../../core/skill-library.md), rồi đọc [SKILL.md gốc](../../../" + item["target"] +
            ") trước khi thực hiện. Chỉ tải references/helper cần cho tác vụ.\n\n" +
            "Thư mục upstream thực tế nằm trong `.tools/skill-library/`; ánh xạ đường dẫn ví dụ của upstream tới đó. " +
            "Nếu source chưa có, chạy `scripts/install_skill_library.py` tại repo để khôi phục đúng bản đã pin. " +
            "Việc gọi entrypoint không tự setup engine, chọn thêm style hoặc thay workflow khóa/duyệt của project.\n")


def entry_path(item, host, root=ROOT):
    return within(root, host["folder"] + "/" + item["name"] + "/SKILL.md")


def shortcut_status(item, host=HOSTS[0], root=ROOT):
    path = entry_path(item, host, root)
    if not path.is_file():
        return "missing"
    return "registered" if path.read_text(encoding="utf-8-sig") == entry_text(item, host) else "modified"


def check_shortcuts(root=ROOT):
    return [{"name": item["name"], "id": item["id"], "kind": item["kind"], "host": host["key"],
             "invoke": host["prefix"] + item["name"], "status": shortcut_status(item, host, root)}
            for host in HOSTS for item in entries(root)]


def register_shortcuts(root=ROOT):
    planned = entries(root)
    # Check every existing entry before writing, preserving local authoring changes.
    for item in planned:
        for host in HOSTS:
            if shortcut_status(item, host, root) == "modified":
                raise EditorError(f"Preserved modified native skill: {host['folder']}/{item['name']}. Review that file before regenerating.")
        if not within(root, item["target"]).is_file():
            raise EditorError(f"Missing target for {item['name']}: {item['target']}. Restore the library first.")
    created = 0
    for host in HOSTS:
        for item in planned:
            path = entry_path(item, host, root)
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("x", encoding="utf-8", newline="\n") as stream:
                    stream.write(entry_text(item, host))
                created += 1
    return {"registered": len(planned), "created": created, "folders": [host["folder"] for host in HOSTS]}
