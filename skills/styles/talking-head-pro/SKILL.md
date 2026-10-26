---
name: talking-head-pro
description: Dựng talking-head dọc với caption theo cụm, nhấn ý chính và infographic xen kẽ. Dùng khi chọn style talking-head-pro hoặc yêu cầu phong cách từ mẫu Edit Video Pro s1 công khai.
---

# Talking-head pro

Đây là style độc lập, viết từ thông tin và demo công khai; không phải package Edit Video Pro của tác giả. Đọc `skill.json` và [phân tích mẫu](references/source-analysis.md) khi cần hiểu thiết kế. Không áp bố cục của bản v2 quảng cáo trên cùng trang vào style s1.

## Hướng dựng

Giữ người nói làm trục chính. Caption ngắn theo lời nói giúp theo dõi; chữ lớn và infographic giải thích một ý khó ở đúng thời điểm. Có khoảng nghỉ thị giác giữa các điểm nhấn. Không biến cả clip thành slide hoặc chèn hiệu ứng theo quota.

- Đề xuất khung 9:16 cho TikTok. Đọc [hướng dẫn TikTok](../../../core/platforms/tiktok.md) để xử lý hook, crop/pad, chữ có sẵn và khoảng trống giao diện; tọa độ mặc định không phải safe zone bảo đảm.
- Dùng lời thật trong transcript cho hook. Chỉ đề xuất cắt vấp/lặp/retake khi nghe và mốc thời gian cho thấy đó là lỗi. Khi chưa đủ bằng chứng, giữ đoạn và đưa lựa chọn; lặp để nhấn mạnh không tự động là lỗi.
- Giữ phủ định, điều kiện, đơn vị, mốc thời gian và phần giải thích dẫn tới kết luận. Không nối hai mệnh đề thành một khẳng định khác nghĩa. Sau cắt/đảo đoạn, tính lại frame và map caption/visual sang timeline đầu ra.
- Đề xuất hai mức khi phù hợp: người nói + caption; hoặc cùng cách cắt đó nhưng thêm một số cảnh infographic/B-roll ở các luận điểm cụ thể. Người dùng chọn mức hoặc giao quyền trong phạm vi rõ ràng.

## Chữ và infographic

Caption là lớp đọc phụ: ưu tiên một hoặc hai dòng ngắn, tách theo cụm nghĩa. Mẫu có chữ trắng nhỏ với một số từ màu xanh ngọc; hãy đề xuất cỡ đọc được trên điện thoại thay vì sao chép nguyên cỡ chữ nhỏ của demo. Bộ ASS hiện tại chỉ có style chung cho cue, chưa có highlight động từng từ. Khi chọn nhấn màu riêng, dùng PNG chữ hoặc KineticScene, không hứa ASS có chức năng đó.

Chữ lớn diễn đạt một ý chính, khác vai trò với caption. Dùng vùng trống trên/giữa hình sau khi kiểm tra gương mặt, tay, chữ cháy sẵn và giao diện TikTok. Đừng phủ mắt hoặc đặt hai bản cùng câu ở hai lớp chữ. Với cảnh đồ họa phủ kín, đề xuất ngắt caption trùng ý bằng `captions.items` theo output frame; không tự đổi lựa chọn caption đã chốt.

Ngôn ngữ infographic gợi ý: nền xanh đen, chữ trắng, accent xanh ngọc, thẻ viền mảnh, thanh tiến độ/sơ đồ tầng và ít icon. Màu là đề xuất từ mẫu, không phải nhận diện thương hiệu bắt buộc. Đổi nền sáng là một lựa chọn cho điểm tổng kết. Không lấy logo, gương mặt, screenshot, dữ liệu hoặc CTA bán hàng trong demo làm asset của job.

Chọn hình theo luận điểm: screenshot cần đọc → insert đủ lớn; mô hình nhiều bước → các thẻ reveal lần lượt; một số liệu → MetricCard/BarChart có đơn vị và nguồn; tên/chức danh → LowerThird. B-roll giữ voice gốc, âm thanh trong layer video bị tắt theo adapter hiện tại.

## Hỏi và thực thi

Theo [interaction.md](../../../core/interaction.md): giữ các lựa chọn đã có, hỏi từng nhóm nhỏ về phạm vi cắt/hook, framing/độ dài, caption, hình, research và audio. Luôn đưa lựa chọn dùng/bỏ Footage Analyst; đề xuất bỏ với máy quay cố định. Giải thích công cụ chưa sẵn trước khi người dùng chọn. Nếu chọn STT lần đầu, làm đúng bước hỏi model trong README; không tải model trong lúc chỉ thiết lập skill.

Sau khi đọc transcript, đưa bảng đề xuất gồm ID cảnh, source range, output range, câu mở, chữ, asset và audio. Khi người dùng chỉ đoạn bằng lời thoại, tìm câu trong transcript, đưa các lần xuất hiện nếu trùng; không đoán timestamp. Chỉ thực hiện đề xuất đã chọn hoặc nằm trong phạm vi được giao. Tạo job/snapshot và ghi setup/actual reply bằng CLI trước xử lý; ghi lựa chọn edit-plan sau khi áp dụng.

Đọc [implementation.md](references/implementation.md) trước tạo layer. FFmpeg dựng timeline cuối; Remotion xuất asset được chọn. Không thay engine toàn dự án theo nội dung quảng cáo. Animated camera zoom, tracking mặt, speed ramp và SFX theo timeline vẫn chưa hỗ trợ. Không thêm trường JSON để giả lập chúng.

Giọng nói luôn rõ; voice-only là lựa chọn hợp lệ. Music/ducking cần người dùng chọn, không đi kèm nhạc từ demo. Xuất revision rồi trả đường dẫn cho người dùng xem. Sửa bản đã xuất bằng revision mới, timestamp theo bản đã xem; không có role AI review hoặc vòng tự sửa chất lượng.

Mỗi edit/feedback phải theo [style-learning.md](../../../core/style-learning.md): gộp quy tắc dùng lại có bằng chứng vào đúng package, cập nhật version/profile/tài liệu; giữ lựa chọn riêng và snapshot trong job. Việc tạo skill này chỉ thêm lựa chọn style, không tự đổi style của job cũ.
