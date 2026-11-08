# Sổ tay agent: dựng video người nói cho TikTok từ đầu đến cuối

Dùng cho mọi agent (Codex, Claude Code hay agent khác) khi người dùng nhờ dựng hoặc sửa video trong repo này. Đây là trình tự đã chạy trơn tru với người dùng, cùng các lệnh và bẫy đã gặp. Quy tắc gốc vẫn ở [AGENTS.md](../AGENTS.md), [editing-workflow.md](editing-workflow.md) và [interaction.md](interaction.md); sổ tay này không thay chúng, chỉ cho biết làm thế nào cho nhanh và đúng.

## 0. Đọc trước (mỗi yêu cầu dựng)

1. `preferences/workflow.json` (kỹ thuật cố định: large-v3 local, Studio, không hỏi lại).
2. `preferences/default.json` → `editorial_preferences`: `tiktok_layout` (bố cục đã xác nhận) và `visual_density` (luôn có kế hoạch minh họa). Bố cục này là mặc định, chỉ chỉnh số đo theo mặt người nói thật.
3. [platforms/tiktok.md](platforms/tiktok.md), nhóm skill ứng viên (`skills/styles/<nhóm>/SKILL.md`), và nếu cần thêm lớp hình thì [schemas/visuals-and-footage.md](schemas/visuals-and-footage.md).

## 1. Phân tích nguồn (chưa hỏi gì)

- Probe: `ffprobe` (thời lượng, kích thước, fps, có tiếng). Nguồn 720×1280 vẫn xuất 1080×1920 (chữ nét hơn), nói rõ hình hơi mềm.
- Xem 6 khung hình rải đều (ảnh ghép có lưới 10%) để biết: mặt nằm từ đâu tới đâu, có chữ in sẵn không, vùng trống ở đâu. Vị trí mặt quyết định chỗ đặt caption và chiều cao motion.
- `new-job` với nhóm ứng viên (người nói trước camera: `melvynx-raw-vi`), rồi `transcribe` (cần khoảng 3 GB RAM trống; thiếu thì báo người dùng đóng bớt ứng dụng).
- Đọc transcript theo từ có mốc giây; đo khoảng lặng thật (`silencedetect` hoặc năng lượng âm thanh). Tìm: câu nói lại, chỗ vấp, câu hỏi lặp, từ đệm, ngập ngừng dài. Lặp có chủ ý để nhấn mạnh thì giữ.
- Liệt kê lỗi nhận dạng giọng nói: sửa chắc chắn (chính tả theo ngữ cảnh) và **chỗ cần người dùng xác nhận** (tên riêng, tên kênh, thuật ngữ, từ tiếng Anh). Từ Whisper lặp với độ dài 0 giây và độ tin cậy thấp là lỗi nhận dạng, không phải người nói lặp.

## 2. Gửi một phương án (rồi dừng chờ duyệt)

Ghi phương án chi tiết vào `jobs/JOB/edit-treatment.json`, gửi người dùng bản ngắn gọn gồm:

- Tóm tắt nội dung video; nhóm skill và lý do (nói rõ không dùng engine/tăng tốc/nhạc của upstream nếu không được yêu cầu).
- Khung hình, mở đầu (câu gốc và mốc), bảng cắt (giây gốc → bỏ gì, vì sao), thời lượng dự kiến; một bản ngắn hơn chỉ khi đánh đổi đáng kể.
- Bố cục theo `tiktok_layout`, **3 lựa chọn câu title** lấy từ transcript.
- Bảng minh họa: mốc, lời nói, minh họa (ảnh stock có license, thẻ Points, thẻ số lớn, thẻ kêu gọi), chỗ nào phủ toàn màn hình (thông tin dài từ 3 ý).
- Âm thanh: giọng gốc, -14 LUFS, lọc ồn chỉ khi nền ồn cao; tiếng "vút" chỉ ở chuyển cảnh giữa clip.
- 3 mục bắt buộc: Footage Analyst (khuyên bỏ với camera cố định), research, hình thêm.
- Danh sách sửa lỗi nhận dạng và các chỗ cần xác nhận.
- Ghi sự kiện học style vào `jobs/JOB/feedback/style-learning.json`.

Câu trả lời ngắn như "ok", "2 / giữ / bạn tìm nhé" là duyệt; ghi đúng nguyên văn bằng `decide --stage setup`.

## 3. Dựng sau khi duyệt

1. **Sửa transcript**: chỉ sửa `transcript/cleaned.json` (giữ `raw.json`), mỗi sửa đổi có log (`corrections`: trước, sau, loại, lý do).
2. **Cắt**: `ai_editor.py cut JOB --revision rNNN --remove 0-0.8 12.75-14.13 ...` (giây gốc cần bỏ). Lệnh dời mỗi điểm cắt về khe lặng gần nhất giữa hai âm tiết, khớp khung hình, viết lại clips và `cut-report.json`. Đọc báo cáo: `check_word_timing` là từ Whisper kéo dài qua khoảng lặng bị cắt; sửa `start`/`end` của từ đó trong `cleaned.json` theo âm thanh (có log) nếu không caption sẽ mất từ.
3. **Zoom/chuyển cảnh**: zoom 108% xen kẽ ở các clip sau chỗ cắt nhỏ để giấu bước nhảy; `transition` chỉ ở chỗ đổi phần (trượt, lia nhanh 10 khung).
4. **Caption**: `ai_editor.py captions JOB --revision rNNN` (cân đối 2 dòng, không tách từ ghép, chỉ viết hoa đầu câu thật hoặc sau chỗ cắt; thêm cụm không được tách bằng `--keep-together "lãi suất"`). Cỡ 80, viền 3; vị trí theo `tiktok_layout` (mép dưới khoảng y 1600, kiểm tra miệng/cằm).
5. **Title**: `scripts/render_text.py --text-file title.txt --output assets/title/title.png --width 1000 --height 210 --font-size 76 --color #14344A --second-color #C02126 --outline-color #FFFFFF --outline-width 5`; lớp ảnh suốt video ở y khoảng 225, đứng **trước** các lớp motion trong danh sách overlay.
6. **Minh họa**: ảnh trong `assets/illustrations/`, request JSON trong `assets/requests/`, `render-motion` (chạy tuần tự, mỗi asset 30-60 giây). Illustration và Points với `fill: true`, 1080×1000 ở y 0; thông tin dài dùng Points 1080×1920. Mốc `at` của từng ý lấy từ thời điểm nói (đổi giây gốc sang khung của asset). Đo bề rộng chữ bằng file font đi kèm trước khi chọn cỡ.
7. **Nguồn**: ảnh Pexels/Unsplash (tránh người nhận diện được trong ngữ cảnh tiêu cực), âm thanh Mixkit Free (kiểm tra license của từng file), app nhắc tới thì dùng icon chính thức từ trang App Store, giữ nguyên. Ghi tất cả vào `jobs/JOB/CREDITS.md`.
8. **Xem thử trước khi xuất**: `ai_editor.py preview JOB --revision rNNN --seconds 25 --stills 1 12 18 24` rồi mở ảnh ghép để kiểm tra chữ, vị trí, che mặt. `--seconds 0` dựng toàn bộ (vẫn ngoài revision). Bản xuất chính thức không được ghi đè nên phải xem thử trước.
9. `decide --stage edit-plan` (tóm tắt + câu duyệt nguyên văn), `render`, rồi kiểm tra: số khung hình, thời lượng, `ebur128` (khoảng -14 LUFS, đỉnh dưới -1 dB), ảnh ghép vài mốc.

## 4. Sửa tiếp và Studio

- Người dùng xem bản xuất rồi nhắn sửa: `revision --from-revision rNNN --feedback "<nguyên văn>"`, áp dụng, xem thử, xuất bản mới.
- Người dùng đang chỉnh trong Studio: `EditorStore.load`, so với lịch sử `editor/history/` để biết họ đã đổi gì, rồi gửi **đề xuất** (`EditorStore.propose`, không `save` đè). Đề xuất mới thay đề xuất cũ; người dùng sửa thêm thì Duyệt bị từ chối, gửi lại trên version mới.
- Sửa code Python của dự án trong lúc Studio đang chạy: dừng tiến trình `ai_editor.py editor`, gọi `core.launcher.launch(open_browser=False)`, bảo người dùng tải lại trang. Thông báo "Unsupported ... props fields" với trường vừa thêm là dấu hiệu server cũ. Sửa `editor/src` thì `npm --prefix editor run build`.
- Người dùng nói "từ giờ", "cho các video sau", "luôn": ghi vào `preferences/default.json` (preference chung) và trỏ từ tài liệu quy trình; nếu chưa rõ phạm vi thì ghi là ứng viên trong job và hỏi một câu.

## 5. Bẫy đã gặp (Windows)

- In tiếng Việt từ Python: đặt `PYTHONIOENCODING=utf-8`; Python hệ thống chạy `-I` bỏ qua biến môi trường, dùng `sys.stdout.reconfigure(encoding="utf-8")`.
- `Path.write_text` trên Windows đổi `\n` thành `\r\n`; danh sách tên đọc bằng shell sẽ dính `\r` (lỗi "Use a lowercase ID"). Dùng `newline="\n"` hoặc `tr -d '\r'`.
- Heredoc và `sed` làm hỏng chuỗi có `\n` hay ` `; sửa file bằng công cụ chỉnh sửa hoặc dùng `chr(10)`.
- Dựng có chuyển cảnh với một đầu đọc file chung từng hết RAM; renderer đã tách đầu đọc tiếng, đừng gộp lại.
- Tua ở đầu ra (`-ss` sau `-i`) với bộ lọc của plan từng cho ảnh trống; dùng lệnh `preview`.
- Không chạy Remotion và build Studio song song khi máy ít RAM; không xóa dữ liệu người dùng khi chưa hỏi.

## 6. Cách trả lời người dùng

Tiếng Việt, ngắn, bảng khi so sánh, không dùng ký tự gạch dưới hay gạch ngang dài trong văn bản gửi người dùng (quy định của tổ chức). Báo đúng kết quả: test nào chạy, lệnh nào lỗi, chỗ nào cần người dùng nghe hoặc xem lại.
