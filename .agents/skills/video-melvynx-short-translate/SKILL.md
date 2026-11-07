---
name: video-melvynx-short-translate
description: "Dịch và lồng tiếng video qua ElevenLabs khi đã chọn dịch vụ."
---

# video-melvynx-short-translate

Đây là entrypoint để Codex nhận diện qua menu skill. Khi được chọn, dùng skill `melvynx/short-translate` cho đúng phạm vi yêu cầu.

Đọc [hướng dẫn tích hợp dự án](../../../core/skill-library.md), rồi đọc [SKILL.md gốc](../../../.tools/skill-library/melvynx/short-translate/SKILL.md) trước khi thực hiện. Chỉ tải references/helper cần cho tác vụ.

Thư mục upstream thực tế nằm trong `.tools/skill-library/`; ánh xạ đường dẫn ví dụ của upstream tới đó. Nếu source chưa có, chạy `scripts/install_skill_library.py` tại repo để khôi phục đúng bản đã pin. Việc gọi entrypoint không tự setup engine, chọn thêm style hoặc thay workflow khóa/duyệt của project.
