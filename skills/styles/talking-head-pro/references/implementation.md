# Cách thực thi trong AI Editor

Có thể mở draft trong [AI Editor Studio](../../../../core/visual-editor.md) để user sửa caption, timing, ảnh và motion trực tiếp. Preview không encode MP4; vùng đã duyệt khóa cả các lớp tác động tới nó. Khi AI tiếp tục sửa, đọc draft mới nhất, giữ khóa và dùng `EditorStore.save` hoặc revision mới đúng workflow. Xuất video cuối vẫn encode bằng FFmpeg; không hứa smart-render từng đoạn.

Đọc [edit-plan](../../../../core/schemas/edit-plan.md) và [visual contract](../../../../core/schemas/visuals-and-footage.md). `new-job` chỉ tạo bản nháp giữ toàn bộ footage và tắt caption. Profile chọn style/domain; vẫn phải ghi setup và phương án thật của user trước xuất.

| Treatment | Đường thực thi |
|---|---|
| Caption cụm nghĩa | `captions.enabled: true` + cleaned transcript có word timings; hoặc `captions.items` tính theo output frames |
| Keyword màu/chữ lớn, logo | PNG qua helper `skills/styles/visual-keyword/scripts/render_text.py` nếu package có sẵn; đọc `--help`, dùng file UTF-8 và layer ảnh. Không sửa transcript thành toàn bộ keyword |
| Cảnh infographic các thẻ | `KineticScene` theme dark, accent xanh ngọc, stack/grid; đọc [request và giới hạn](../../../../core/schemas/visuals-and-footage.md#kineticscene) |
| Số liệu, biểu đồ, tên người | `MetricCard`, `BarChart`, `LowerThird` qua `render-motion` |
| Screenshot, B-roll | Image/video layer đúng interval đầu ra; voice nguồn tiếp tục |
| Thay cỡ khuôn hình tại điểm cắt | Fixed crop riêng từng clip nếu user chọn. Đây là jump cut đổi framing, không phải zoom chuyển động |

Khi dùng infographic phủ kín, `overlays` chỉ thay hình, không kéo dài hay đổi thứ tự clip. Dựng đủ duration của asset bằng interval đã chọn; không loop asset để vô tình lặp intro. Caption ASS nằm trên mọi layer: nếu user chọn bỏ caption ở cảnh infographic, tạo explicit items cho các phần còn lại. Không có trường bật/tắt caption theo scene tự động.

KineticScene là template chữ/thẻ/progress mới của dự án. Nó không tái tạo avatar tròn, screenshot trong màn hình thiết bị, vật thể 3D hoặc camera zoom của demo. Có thể ghép ảnh hợp lệ bằng layer tĩnh; chuyển động riêng cho asset đó cần phần triển khai mới, phải báo trước khi hứa.

Prompt dùng:

> Dựng `inbox/raw.mp4` bằng profile `talking-head-pro-vi`. Đề xuất bản caption gọn và bản thêm infographic; đưa source range, lời mở, chữ, hình, nhạc cho tôi chọn trước khi dựng.

> Job `video-001`, bản `r001`, ở giây 18–22: bỏ cảnh infographic, giữ hình người nói và caption. Tạo revision mới, giữ các lựa chọn khác.

Các prompt là ví dụ, không phải actual reply để ghi `decide` cho một job thật.
