---
name: review-variants
description: "Nhóm skill video Agentic: biến thể quảng cáo và feedback theo mốc; dùng khi chọn nhóm này hoặc tạo một phương án dựng độc lập để so sánh."
---

# Agentic: biến thể quảng cáo và feedback theo mốc

Đây là nhóm định tuyến tới skill upstream đã cài, không phải bản thay tên của skill cũ. Đọc [quy tắc tích hợp](../../../core/skill-library.md) trước khi dùng.

Dùng cho phương án ad/biến thể hook và xử lý feedback có timestamp. Đọc skill dựng hoặc `apply-notes` theo yêu cầu. Upstream dùng Apple Silicon/macOS (mlx-whisper, VideoToolbox, Apple Vision) và một review server riêng tại port 8765; chưa chạy nguyên pipeline trên Windows và không khởi động server đè Studio. `video-qa` đã được cài để tham khảo, không được tự kích hoạt role chấm video hoặc vòng tự sửa vì workflow dự án hiện do người dùng xem và góp ý. Khi so sánh hook, xác định rõ phần thân dùng chung, phần được thay và lời thoại nguồn, rồi tạo output độc lập.

Entrypoint: [ve-video-edit-general](../../../.tools/skill-library/agentic/ve-video-edit-general/SKILL.md). Danh sách package và commit chính xác ở [library.json](../../library.json); chỉ tải hướng dẫn liên quan vào context. Mọi thay đổi draft Studio đi qua EditorStore và giữ locks. Các bản dựng cũ tiếp tục dùng snapshot đã ghi.
