---
name: kinetic-motion
description: Thiết kế motion graphic dọc với typography lớn, thẻ reveal theo nhịp và progress; dùng cho yêu cầu Kinetic Motion hoặc kinematic trong ngữ cảnh mẫu video này, độc lập hoặc xen vào talking-head.
---

# Kinetic motion

Style tự viết dựa trên demo Kinetic Motion v1 công khai, không phải file skill của tác giả. Trong dự án này “kinematic” được hiểu là yêu cầu Kinetic Motion trên trang tham chiếu; nếu người dùng nói về cinematic footage/phim hoặc động học vật lý thì cần xác định lại, không tự áp style này.

Đọc `skill.json`; đọc [source-analysis.md](references/source-analysis.md) khi đối chiếu mẫu và [implementation.md](references/implementation.md) trước render. Đây là motion giải thích theo ý, không phải hiệu ứng karaoke toàn transcript.

## Cấu trúc theo ý

Chia nội dung thành beat: vấn đề → điều làm nó phức tạp → hành động rõ ràng → kết quả. Đây là một phương án khi nội dung phù hợp, không ép mọi bài vào bốn cảnh. Mỗi scene có một thông điệp, một cụm chữ nhấn và tối đa bốn thẻ. Chuyển động cho thấy quan hệ: thẻ xuất hiện lần lượt cho các bước, grid cho nhiều yếu tố, progress cho tiến trình đã giải thích. Không dùng tiến độ tăng giả để minh họa một số liệu tài chính thật.

Chọn chữ từ script/transcript đã chốt. Tách title dẫn vào, emphasis nổi bật và subtitle hỗ trợ. Gợi ý emphasis 1–5 từ, title 1–2 dòng; số liệu đi với đơn vị và điều kiện. Không tự biến một ví dụ thành sự thật. Với nội dung cần evidence, dùng domain tương ứng và hỏi phạm vi research.

Chừa thời gian đọc sau reveal; độ dài phụ thuộc câu và số thẻ. Điểm bắt đầu gợi ý là scene 3–6 giây cho một ý ngắn, không phải yêu cầu bắt buộc. Template cần ít nhất 2 giây để còn thời gian giữ chữ. Không dồn title, thẻ, progress và ảnh chuyển động cùng lúc vào một frame.

## Hình thức

Mẫu dùng nền trắng, đen và xanh đậm xen kẽ, chữ đậm màu tối/trắng và accent cam vàng; thẻ gọn kiểu cửa sổ giao diện. Gợi ý một accent cho từ khóa, viền thẻ và progress. Không đổi màu theo từng từ vô cớ. Nền sáng/tối theo beat là lựa chọn thiết kế để user duyệt, không có quota đổi nền.

Chuyển động mới của dự án: fade/slide nhẹ cho heading, scale/slide ngắn cho emphasis, reveal thẻ stagger, progress tăng tới giá trị đã chọn rồi hold; outro fade. Các chuyển động được tính bằng frame, không random, không phụ thuộc thời gian hệ thống. Không hứa đây là easing chính xác của demo. Ảnh não/laptop/điện thoại trong mẫu không đi kèm skill; chọn ảnh có nguồn hoặc tạo minh họa khi user muốn và công cụ sẵn.

Theo [TikTok guide](../../../core/platforms/tiktok.md): đề xuất 9:16 và bố cục dễ đọc trong vùng tránh giao diện; kiểm tra chữ có sẵn/subject với overlay. Preset template 720×1280 là hệ tọa độ thiết kế, không phải safe zone của mọi bài đăng. Với layer có nền trong suốt, chọn theme để chữ/thẻ tương phản footage thật. Không tự bật caption toàn lời nói: `items: []` giữ track trống; text nằm trong cảnh motion. Nếu user muốn caption bổ sung thì hỏi vị trí và tránh lặp lại cùng câu.

## Lựa chọn và bàn giao

Tuân thủ [interaction.md](../../../core/interaction.md). Hỏi mục đích (cảnh xen hay motion toàn màn hình), script/voice, thời lượng/khung, chữ/visual, palette và audio khi chưa được chọn hoặc giao quyền. Luôn đưa dùng/bỏ Footage Analyst; clip chỉ chữ/đồ họa thường phù hợp bỏ. Với STT, hỏi model lần đầu theo README; với research/asset, nói rõ nguồn và công cụ sẵn. Nhạc, SFX và ảnh của demo không tự động được chọn.

Đưa storyboard cụ thể: scene ID, thông điệp, câu voice, output interval, title/emphasis, thẻ, theme, asset và kiểu chuyển động. User chọn hoặc giao quyền trong phạm vi xác định rồi mới tạo motion cho job. Các props trong ví dụ và defaults không phải câu trả lời của user. Final render vẫn cần setup + edit-plan choice khớp hashes.

`KineticScene` render được qua Remotion, FFmpeg ghép asset vào timeline. CLI hiện cần video nguồn để tạo job: motion toàn màn hình có thể phủ lên video voice đã có; audio-only/script-only chưa có luồng job riêng. Nếu chỉ có script, làm storyboard trước và trình bày bước triển khai còn thiếu; không tạo nguồn giả/voice giả rồi coi là yêu cầu đã được chọn. Nếu chỉ yêu cầu skill/storyboard, không tạo job hoặc tải model.

Không chuyển quảng cáo thành quyền dựng lại tự động. Xuất revision cho user xem; sửa theo output timeline của revision được xem và tạo bản mới. Theo [style learning](../../../core/style-learning.md), học quy tắc dùng lại có bằng chứng vào đúng style; không học lời script, số liệu hoặc hình của một clip thành default. Giữ style này riêng với visual-keyword và talking-head-pro; không di chuyển job cũ sang profile mới.
