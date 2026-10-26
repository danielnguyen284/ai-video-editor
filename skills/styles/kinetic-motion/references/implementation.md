# Storyboard → motion asset → video

Với [AI Editor Studio](../../../../core/visual-editor.md), user sửa chữ/thẻ/theme/accent/progress của KineticScene bằng live preview dùng chung component React với renderer. Chỉ khi xuất mới render asset đã thay đổi; asset giữ nguyên hoặc cùng spec/hash được tái sử dụng. Vùng đã khóa phải được bảo vệ trong draft và mọi revision. Không đồng nhất cache motion với khả năng chỉ encode đoạn MP4 vừa sửa.

Đọc [hợp đồng KineticScene](../../../../core/schemas/visuals-and-footage.md#kineticscene) để biết đúng props/giới hạn. Không đưa các props bên dưới vào `edit-plan.json`; chúng là request riêng của `render-motion`.

Ví dụ thiết kế minh họa, chưa được chọn cho job nào:

```json
{
  "template": "KineticScene",
  "width": 720, "height": 1280, "fps": 30, "duration_frames": 150,
  "props": {
    "title": "Giảm những việc phân tán",
    "emphasis": "Chọn một việc",
    "subtitle": "Lần lượt hoàn thành từng bước",
    "theme": "light", "accent": "#E5A137", "layout": "stack",
    "cards": [
      {"label": "Xác định mục tiêu", "detail": "Việc quan trọng nhất hôm nay"},
      {"label": "Tắt thông báo", "detail": "Dành một khoảng tập trung"}
    ],
    "progress": 1
  }
}
```

`progress` ở ví dụ là chỉ báo tiến trình minh họa; không diễn giải thành hiệu suất thật. Có thể bỏ nếu không cần. Không dùng `value`, `data` hay `unit` của template khác cho KineticScene.

1. Chốt storyboard, nguồn/script/voice, output, research/visual và audio theo workflow của dự án. Nếu có video, tạo `new-job` bằng profile đã chọn; `kinetic-motion-vi` dùng domain general, `finance-kinetic-motion-vi` dùng finance. Không tự chọn tài chính từ palette.
2. Ghi setup với actual reply. Kiểm tra `doctor`; nếu motion chưa cài thì cài bằng `scripts/setup.ps1 -WithMotion`. Không gọi render-motion lúc mới chỉ gợi ý motion.
3. Tạo một request trong `jobs/JOB/assets/` cho mỗi scene; duration đúng interval đầu ra. `duration_frames / fps` phải đủ dài so với layer. Chạy `.venv/Scripts/python.exe ai_editor.py render-motion JOB scene-01 --revision r001 --spec assets/scene-01.json`.
4. Thêm asset vào `overlays`, `type: video`, `path: assets/visuals/scene-01/motion.mov`, với output frames, rectangle, `fit`, `source_in_seconds: 0`, `loop: false` theo schema. Scene full-frame có nền opaque che hình nguồn; `transparent: true` chỉ chừa các phần không có chữ/thẻ, dùng khi user chọn overlay.
5. Ảnh hợp lệ có thể ghép bằng layer trên motion; ảnh không tự nhận chuyển động của thẻ. Hai scene nối bằng interval liền nhau; fade bên trong template không phải crossfade camera giữa hai clip. ASS caption nằm trên motion, tránh caption trùng nội dung bằng lựa chọn rõ ràng.
6. Sau áp dụng đủ phương án, ghi `decide --stage edit-plan` đúng câu trả lời thật rồi xuất FFmpeg. Báo lỗi thực thi nếu thất bại; không thay nội dung để chữa lỗi một cách chưa được chọn. Revision tiếp theo dùng feedback theo bản đã xem.

Render có tính quyết định theo frame; scene thay đổi chỉ cần asset mới có tên mới và revision mới nếu đã xuất. Không tuyên bố CLI render lại riêng một đoạn của video cuối: asset có thể render riêng, video cuối vẫn encode từ plan revision.

Prompt dùng:

> Dùng skill kinetic-motion để đề xuất storyboard 20 giây về tập trung làm việc, theo mẫu chữ lớn + thẻ UI. Đưa hai hướng màu và phương án voice/nhạc cho tôi chọn; chưa cần render.

> Dựng video voice `inbox/voice-video.mp4` bằng profile `kinetic-motion-vi`, motion phủ kín khung dọc. Đọc transcript rồi đưa storyboard, chữ và các khoảng thời gian cho tôi chọn.

> Job `video-001`, r002, giây 8–12: đổi emphasis thành câu tôi cung cấp, giữ các phần khác; tạo revision mới.
