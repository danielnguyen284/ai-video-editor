---
name: video-agentic-apply-notes
description: "Áp dụng feedback video theo timestamp để tạo revision mới."
---

# video-agentic-apply-notes

Đây là entrypoint để Claude Code nhận diện qua menu skill. Khi được chọn, dùng skill `agentic/apply-notes` cho đúng phạm vi yêu cầu.

Đọc [hướng dẫn tích hợp dự án](../../../core/skill-library.md), rồi đọc [SKILL.md gốc](../../../.tools/skill-library/agentic/apply-notes/SKILL.md) trước khi thực hiện. Chỉ tải references/helper cần cho tác vụ.

Thư mục upstream thực tế nằm trong `.tools/skill-library/`; ánh xạ đường dẫn ví dụ của upstream tới đó. Nếu source chưa có, chạy `scripts/install_skill_library.py` tại repo để khôi phục đúng bản đã pin. Việc gọi entrypoint không tự setup engine, chọn thêm style hoặc thay workflow khóa/duyệt của project.
