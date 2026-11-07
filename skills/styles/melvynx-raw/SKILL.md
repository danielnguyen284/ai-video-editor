---
name: melvynx-raw
description: Nhóm skill video Melvynx raw và short-form; dùng khi chọn nhóm này hoặc tạo một phương án dựng độc lập để so sánh.
---

# Melvynx raw và short-form

Đây là nhóm định tuyến tới skill upstream đã cài, không phải bản thay tên của skill cũ. Đọc [quy tắc tích hợp](../../../core/skill-library.md) trước khi dùng.

Dùng cho raw talking-head, cắt theo transcript, B-roll, short-form và học style từ video mẫu. Đọc `editing/SKILL.md`, rồi chỉ đọc các skill nó chọn cho yêu cầu hiện tại. `short-editing` có engine Node/Chrome/FFmpeg riêng; cài thư mục skill chưa chạy setup engine đó. Layout giấy/split-screen, tăng tốc 1.15x, cắt mọi khoảng lặng 0.3 giây và CTA của upstream là những lựa chọn cần được chọn trong brief hoặc phương án so sánh. Giữ tiếng Việt và phiên âm local đã chọn; không tự chạy whisper.cpp để thay transcript đang dùng. Các skill research, dịch, audit tài khoản và publish chỉ dùng khi người dùng yêu cầu đúng tác vụ đó.

Entrypoint: [editing](../../../.tools/skill-library/melvynx/editing/SKILL.md). Danh sách package và commit chính xác ở [library.json](../../library.json); chỉ tải hướng dẫn liên quan vào context. Mọi thay đổi draft Studio đi qua EditorStore và giữ locks. Các bản dựng cũ tiếp tục dùng snapshot đã ghi.
