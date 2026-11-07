---
name: motion-catalog
description: "Nhóm skill video Motion Prompt: motion và chuyển cảnh có mã số; dùng khi chọn nhóm này hoặc tạo một phương án dựng độc lập để so sánh."
---

# Motion Prompt: motion và chuyển cảnh có mã số

Đây là nhóm định tuyến tới skill upstream đã cài, không phải bản thay tên của skill cũ. Đọc [quy tắc tích hợp](../../../core/skill-library.md) trước khi dùng.

Dùng để chọn và triển khai motion có mã số, hoặc tạo phương án motion để so sánh. Đọc skill gốc; CLI `scripts/motion-prompt.mjs` có thể list/search/get/kit. Lấy spec/code và kit của đúng các ID đã chọn; port chúng sang Remotion/Canvas theo `references/porting.md`. Ghi lại ID, demo URL và thay đổi. Skill này là thư viện motion, không tự quyết định câu chuyện/cắt lời nói; giữ cùng cut/transcript khi so sánh riêng chuyển động. Không thêm trường plan chưa được renderer hỗ trợ.

Entrypoint: [motion-prompt](../../../.tools/skill-library/motion-prompt/motion-prompt/SKILL.md). Danh sách package và commit chính xác ở [library.json](../../library.json); chỉ tải hướng dẫn liên quan vào context. Mọi thay đổi draft Studio đi qua EditorStore và giữ locks. Các bản dựng cũ tiếp tục dùng snapshot đã ghi.
