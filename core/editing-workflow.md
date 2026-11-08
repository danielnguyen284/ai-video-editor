# Flow mặc định khi nhận yêu cầu edit video

Áp dụng cho các yêu cầu như “edit giúp tôi một video”, dựng raw, tạo bản thử hoặc sửa revision trong dự án này. Đây là chỉ dẫn thường trực đã được người dùng chọn: **agent tự đánh giá nguồn, đề xuất một phương án cụ thể, người dùng duyệt rồi mới dựng**. Agent không hỏi lại các lựa chọn kỹ thuật đã cố định. Đọc file này trước các hướng dẫn riêng của nhóm skill.

Nguồn cấu hình thực thi: [preferences/workflow.json](../preferences/workflow.json). Lựa chọn mới trong prompt hoặc lựa chọn đã ghi của job được ưu tiên hơn mặc định. Mặc định bổ sung phần chưa chốt; không viết lại quyết định, snapshot hay vùng đã duyệt của job cũ.

## Những phần đã chốt, không hỏi lại

| Phần | Cách xử lý |
|---|---|
| Môi trường | Dùng Python `.venv` của repo, FFmpeg/ffprobe local, Remotion khi cần motion và AI Editor Studio để chỉnh trực quan. Không tự đổi sang app/engine khác. |
| Phiên âm lời nói | **faster-whisper large-v3 local**, ưu tiên chất lượng. Dùng thư mục `.tools/models/faster-whisper-large-v3`; thiết lập hiện tại CPU/int8, word timestamps. Không đưa lại menu large-v3/small cho từng video. |
| Model thiếu hoặc lỗi | Kiểm tra thư mục và file. Báo lỗi cụ thể, phục hồi/cung cấp đúng model đã chọn; nếu cần tải lại thì hỏi về việc tải đúng large-v3, không hỏi lại chọn loại model. Không tự chuyển model/nhà cung cấp. Setup STT chỉ cài package, ZIP không chứa weights. |
| Transcript đã có | Đọc và dùng lại transcript đúng nguồn/timebase; không phiên âm lại chỉ vì đổi style hoặc revision. Giữ `raw.json`, sửa có dấu vết trong `cleaned.json`. Transcript do user cung cấp được ưu tiên; không chạy STT cho video không có lời nói hoặc khi user yêu cầu bỏ STT. |
| Quy trình sáng tạo | Tự đánh giá rồi đưa **một phương án đề xuất**. Đưa lựa chọn khác chỉ khi có đánh đổi quan trọng. Chờ user duyệt trước khi áp dụng cut/visual/audio hoặc xuất video. |
| Nền tảng | TikTok là nền tảng gợi ý chính theo preference đã ghi. Đưa tỷ lệ, kích thước, thời lượng và cách crop/pad cụ thể vào phương án; không áp dụng chúng như một lựa chọn output đã duyệt nếu brief chưa rõ. |
| Bố cục video người nói (TikTok) | Mặc định đã xác nhận ở `preferences/default.json` (`tiktok_layout`, `visual_density`): title 2 dòng cố định trên cùng, motion (ảnh, thẻ Points) tràn chiều rộng và đặc, che title khi hiện; thông tin dài (từ 3 ý trở lên hoặc cần đọc khoảng 8 giây) dùng thẻ Points phủ toàn màn hình; caption lời nói ở dưới, ngay trên vùng chữ của TikTok; không đặt hiệu ứng âm thanh lúc minh họa hoặc thẻ xuất hiện, tiếng "vút" chỉ ở chuyển cảnh giữa clip; app được nhắc tới thì hiện icon chính thức. Phương án luôn có sẵn kế hoạch minh họa và 3 lựa chọn câu title; chỉ chỉnh số đo theo vị trí mặt thật, không hỏi lại bố cục. |
| Chữ tiếng Việt | Dùng font Be Vietnam Pro đi kèm khi không có font thương hiệu được chọn. Với keyword phủ footage, ưu tiên chữ thuần trong suốt và canh theo mốc từ; không tự thêm hộp nền che người nói. Đây không phải lệnh bỏ mọi nền scene của tất cả style. |
| Dữ liệu và bản xuất | Copy raw, giữ nguồn; giữ job, snapshot, raw transcript, revision đã xuất và các vùng khóa. Preview không encode MP4. Export tạo revision mới và vẫn encode toàn timeline, có cache motion. |
| Kiểm tra | Agent tự kiểm tra khả năng chạy, file/timebase/timing/font/asset và lỗi thực thi. Người dùng xem bản dựng và đánh giá thẩm mỹ; không có role critic độc lập hoặc vòng tự sửa/render lặp. |

## 1. Xác định đúng đầu vào và trạng thái

- Đọc brief, đường dẫn/selection và project đang làm. Nếu có đúng một video được chỉ định, dùng video đó. Khi có nhiều video chưa rõ cái nào, chỉ hỏi phần định danh cần thiết; không hỏi lại model hay bộ công cụ.
- Với job đang làm, đọc draft/revision và lựa chọn đã ghi, đối chiếu output user đã xem và locks. Yêu cầu sửa bản đã xuất đi qua `revision --from-revision ... --feedback ...`. Chỉ unlock khi user nói rõ.
- Với raw mới, probe duration, fps, kích thước, rotation, audio và kiểm tra nguồn đọc được. Xác định điều gì có thể suy ra từ dữ liệu và điều gì cần người dùng quyết định.
- Nếu user nêu skill, dùng skill đó. Nếu chưa nêu, chọn **một nhóm ứng viên để phân tích/đề xuất** dựa trên brief và công cụ thực có, đọc entrypoint liên quan. Profile ứng viên của job ban đầu không phải xác nhận một style; mọi quyết định dựng vẫn pending. Không có một house style tự áp cho mọi video. Báo rõ giới hạn native engine/Windows ngay trong phương án nếu có.

## 2. Chuẩn bị thông tin để đề xuất

Tạo job từ nguồn với profile ứng viên, giữ plan ban đầu toàn footage/caption tắt. Resolver chụp cấu hình workflow hiện hành vào `resolved-config.json`. Việc tạo job và phiên âm local là chuẩn bị, không phải đã dựng theo style hoặc đã duyệt output.

Với video lời nói cần phiên âm và chưa có transcript:

```powershell
.\.venv\Scripts\python.exe ai_editor.py transcribe JOB
```

Không cần lặp `--model` ở mỗi prompt. CLI tự resolve large-v3 sang thư mục local đã cấu hình; thiếu file thì dừng, không âm thầm tải hay đổi model. CPU/int8 và word timing đi theo thiết lập thường trực. Lựa chọn `--model`/`--device` rõ ràng có thể override; chỉ truyền chúng khi user đã chọn thay đổi hoặc chỉ định một thư mục tương thích. Không ghi đè transcript.

Được chạy phiên âm trước khi đủ toàn bộ creative setup, dựa trên chỉ dẫn thường trực này. Ghi thông số/provenance thật vào `transcript/processing.json`; `decisions.json` vẫn pending. Nếu job đã ghi `transcription: false`, lựa chọn đó thắng và lệnh bị từ chối. Không giả một câu trả lời mới của user để mở gate phiên âm.

Đọc toàn transcript, kiểm tra tên riêng, số, đơn vị, câu nói lặp/vấp và ý cần giữ. Nêu điểm chưa chắc thay vì tự thêm claim. Dùng timestamp nguồn và word timing, tính mapping sang output khi chốt cut.

Footage Analyst, Ollama, research bổ sung, stock/B-roll mới, nhạc và dịch vụ ngoài vẫn tùy phạm vi job. Kế thừa lựa chọn đã có; khi chưa chọn, đưa chế độ đề xuất vào cùng phương án, nêu công cụ thiếu trước khi người dùng duyệt. Không tự gửi media lên dịch vụ ngoài. Phân tích footage nâng cao chỉ chạy khi đã được chọn.

## 3. Đề xuất một phương án cụ thể

Tóm tắt điều agent đọc được từ video, rồi đưa một phương án có thể duyệt, gồm các phần còn chưa chốt:

- Mục tiêu, group/skill đề xuất và output (tỷ lệ, kích thước, fps, crop/pad).
- Hook/ý chính, khoảng nguồn giữ/bỏ, thời lượng dự kiến, phần lời nói phải giữ đúng ngữ nghĩa.
- Caption hay keyword chọn lọc; chữ thật cần hiện, ví dụ/mốc dự kiến và bố cục tránh che người nói.
- Hình/B-roll/motion, nguồn minh họa và cách xử lý audio. Ghi rõ giữ nguyên khi không đề xuất thay đổi.
- Footage/research mới nếu cần, phạm vi công cụ chạy được và phần cần setup/port.

Không hỏi lại engine, model, raw preservation, revision hay lock. Phần đã rõ trong prompt được đưa vào phương án và giữ nguyên; không bắt user trả lời lại cả bảng setup. Chờ một câu duyệt/chỉnh cụ thể. Trong lúc chờ chỉ làm phần chuẩn bị độc lập.

## 4. Sau khi user duyệt

Ghi setup bằng câu trả lời thật và các chỉ dẫn thường trực có liên quan, đối chiếu profile/config. Không biến một profile mặc định hoặc sự im lặng thành sự đồng ý. Dựng đúng phương án đã duyệt; khi có xung đột lock, giữ project và báo đoạn cần user unlock.

Tính lại timeline, caption, visual và duration; viết draft bằng `EditorStore.save` với expected version. Khi user muốn duyệt trực tiếp trong Studio, khi sửa draft user đang chỉnh tay, hoặc khi bản dựng lệch khỏi điều đã duyệt, gửi bằng `propose` thay vì save để user bấm Duyệt/Bỏ (xem [visual-editor.md](visual-editor.md)). Trước export, tự kiểm tra nguồn/asset/font, schema, word timing, transparency và các lựa chọn đã ghi. Dùng dry-run cho kiểm tra lệnh; sửa lỗi kỹ thuật trong phạm vi đã chọn. Đổi câu chuyện, cut, bố cục hoặc âm thanh ngoài phương án cần user chọn lại.

Ghi `decide --stage edit-plan` với summary và câu user duyệt, rồi export revision mới. Không tự ghi final. Trả đường dẫn/revision và giới hạn thực tế để user xem và sửa tiếp trong Studio. Với nhiều output đã chọn, giữ input/brief và các biến dùng chung, lưu mỗi bản riêng rồi dùng `compare-view`.

## 5. Duy trì kiến thức

Theo [style-learning.md](style-learning.md), gộp bài học tái sử dụng vào đúng nhóm hoặc quy tắc chung có điều kiện; việc riêng một video ở lại job. Chỉ dẫn kỹ thuật thường trực nằm ở file này và `preferences/workflow.json`, không sao chép vào 33 package upstream. Khi đổi quy tắc, giữ snapshot của job cũ; chỉ chụp bản mới cho job mới. Xem [interaction.md](interaction.md), [skill-library.md](skill-library.md) và [visual-editor.md](visual-editor.md) khi thực hiện.
