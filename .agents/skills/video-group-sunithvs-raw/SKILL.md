---
name: video-group-sunithvs-raw
description: "Chọn nhóm B Sunithvs cho phương án talking-head và kinetic text."
---

# video-group-sunithvs-raw

Đây là entrypoint để Codex nhận diện qua menu skill. Khi được chọn, dùng nhóm `sunithvs-raw` cho đúng phạm vi yêu cầu.

Đọc [hướng dẫn tích hợp dự án](../../../core/skill-library.md), rồi đọc [SKILL.md gốc](../../../skills/styles/sunithvs-raw/SKILL.md) trước khi thực hiện. Chỉ tải references/helper cần cho tác vụ.

Thư mục upstream thực tế nằm trong `.tools/skill-library/`; ánh xạ đường dẫn ví dụ của upstream tới đó. Nếu source chưa có, chạy `scripts/install_skill_library.py` tại repo để khôi phục đúng bản đã pin. Việc gọi entrypoint không tự setup engine, chọn thêm style hoặc thay workflow khóa/duyệt của project.
