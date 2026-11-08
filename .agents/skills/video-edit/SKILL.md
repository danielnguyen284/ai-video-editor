---
name: video-edit
description: "Dựng hoặc sửa một video trong repo này theo quy trình chuẩn: phân tích nguồn, đề xuất một phương án, chờ duyệt, dựng, xem thử, xuất và sửa tiếp trong Studio."
---

# video-edit

Đây là entrypoint để Codex bắt đầu mọi yêu cầu dựng hoặc sửa video trong repo này.

1. Đọc [AGENTS.md](../../../AGENTS.md), [quy trình mặc định](../../../core/editing-workflow.md) và `preferences/workflow.json`, `preferences/default.json`.
2. Làm theo [sổ tay agent](../../../core/agent-playbook.md): phân tích, gửi một phương án, chờ duyệt, rồi dùng các lệnh `cut`, `captions`, `preview`, `render`.
3. Chọn một nhóm skill cho output (menu `video-group-...`) và chỉ đọc helper cần dùng.

Entry này không tự chọn style, không bỏ qua bước duyệt và không thay khóa vùng của Studio.
