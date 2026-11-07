---
name: sunithvs-raw
description: Nhóm skill video Sunithvs talking-head và kinetic text; dùng khi chọn nhóm này hoặc tạo một phương án dựng độc lập để so sánh.
---

# Sunithvs talking-head và kinetic text

Đây là nhóm định tuyến tới skill upstream đã cài, không phải bản thay tên của skill cũ. Đọc [quy tắc tích hợp](../../../core/skill-library.md) trước khi dùng.

Dùng cho một phương án talking-head khác: caption/kinetic text bám từ, B-roll, bố cục face/PIP và bản dài YouTube. Chọn `reel-editor` hoặc `youtube-editor` theo output đã chọn. Upstream yêu cầu macOS/Linux và có lệnh shell/uv; trên Windows chỉ phần hướng dẫn và các phần đã port/kiểm tra mới được báo là chạy được. Không dùng avconvert, VideoToolbox hay lệnh Unix như thể có sẵn. Native HTML seek(t) có thể tạo asset riêng sau khi kiểm tra toolchain; nội dung đó chưa trở thành layer có thể sửa nội bộ trong custom Studio.

Entrypoint: [reel-editor](../../../.tools/skill-library/sunithvs/reel-editor/SKILL.md). Danh sách package và commit chính xác ở [library.json](../../library.json); chỉ tải hướng dẫn liên quan vào context. Mọi thay đổi draft Studio đi qua EditorStore và giữ locks. Các bản dựng cũ tiếp tục dùng snapshot đã ghi.
