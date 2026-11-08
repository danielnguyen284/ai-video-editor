---
name: video-resolve-edit-video
description: "Điều phối một bản dựng nháp trong DaVinci Resolve."
---

# video-resolve-edit-video

Đây là entrypoint để Claude Code nhận diện qua menu skill. Khi được chọn, dùng skill `resolve/edit-video` cho đúng phạm vi yêu cầu.

Đọc [hướng dẫn tích hợp dự án](../../../core/skill-library.md), rồi đọc [SKILL.md gốc](../../../.tools/skill-library/resolve/edit-video/SKILL.md) trước khi thực hiện. Chỉ tải references/helper cần cho tác vụ.

Thư mục upstream thực tế nằm trong `.tools/skill-library/`; ánh xạ đường dẫn ví dụ của upstream tới đó. Nếu source chưa có, chạy `scripts/install_skill_library.py` tại repo để khôi phục đúng bản đã pin. Việc gọi entrypoint không tự setup engine, chọn thêm style hoặc thay workflow khóa/duyệt của project.
