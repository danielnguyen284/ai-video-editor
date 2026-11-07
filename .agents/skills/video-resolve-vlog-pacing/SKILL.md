---
name: video-resolve-vlog-pacing
description: "Chỉnh padding, khoảng nghỉ và nhịp cắt vlog trong Resolve."
---

# video-resolve-vlog-pacing

Đây là entrypoint để Codex nhận diện qua menu skill. Khi được chọn, dùng skill `resolve/vlog-pacing` cho đúng phạm vi yêu cầu.

Đọc [hướng dẫn tích hợp dự án](../../../core/skill-library.md), rồi đọc [SKILL.md gốc](../../../.tools/skill-library/resolve/vlog-pacing/SKILL.md) trước khi thực hiện. Chỉ tải references/helper cần cho tác vụ.

Thư mục upstream thực tế nằm trong `.tools/skill-library/`; ánh xạ đường dẫn ví dụ của upstream tới đó. Nếu source chưa có, chạy `scripts/install_skill_library.py` tại repo để khôi phục đúng bản đã pin. Việc gọi entrypoint không tự setup engine, chọn thêm style hoặc thay workflow khóa/duyệt của project.
