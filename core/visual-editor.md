# AI Editor Studio — sửa trực quan trên máy

Người dùng đã chọn workflow ngày 27/10/2026: “Editor riêng trong dự án: AI dựng nháp, bạn sửa timeline/chữ/hình và khóa phần đã ưng ngay trong giao diện local.” Mục tiêu là giữ project có thể sửa từng lớp, xem ngay và giữ các vùng đã duyệt. Đây là lựa chọn workflow; không tự chọn style, lời mở, cắt, nhạc hoặc phân tích footage cho job mới.

## Mở editor

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1 -WithEditor
.\.venv\Scripts\python.exe ai_editor.py editor
```

Setup cài/build editor và motion, không tải model Whisper. Server chỉ nghe `127.0.0.1:8765`, có thể đổi bằng `--port`; `--no-open` không tự bật browser. Media được đọc từ ổ đĩa và stream nội bộ, không upload lên dịch vụ. Cần giữ process chạy trong khi dùng editor. Nếu nhận ZIP, chạy setup trên máy mới; không có node_modules/build/model trong ZIP.

Chọn job có sẵn hoặc tạo job bằng đường dẫn video trên máy và profile cụ thể. `new-job` vẫn copy video gốc. Bản xuất cũ và plan/config của revision nguồn không bị sửa khi làm việc trên draft.

## Cách dùng

- **Preview:** Space phát/dừng; mũi tên trái/phải đi từng frame; nút toàn màn hình để xem lớn. Playhead trên thước thời gian có thể chọn vị trí. Không encode MP4 khi sửa chữ, di chuyển layer hoặc xem timeline.
- **Timeline:** chọn clip, chia tại playhead; kéo hai mép clip để trim có ripple, hoặc sửa source in/out trong bảng thuộc tính. Dùng Đưa trước/Đưa sau để đổi thứ tự. Caption/visual được map lại theo đoạn nguồn; layer vượt ranh giới có thể được tách. Kiểm tra câu caption ở ranh giới khi cắt ngang một cue đã sửa tay.
- **Caption:** chọn cue để sửa riêng chữ/timing; kéo cue và hai mép trên timeline, thêm/xóa cue; sửa font/cỡ chữ/khoảng cách đáy. Cue có ID ổn định trong draft, không ghi ID vào schema caption của plan. Editor materialize các cue hiện có thành items tính theo output frame khi xuất; raw/cleaned transcript giữ nguyên.
- **Hình:** nhập file qua đường dẫn local, thêm ở playhead; kéo trên preview để di chuyển, kéo góc dưới phải để đổi kích thước, hoặc sửa số và opacity/fit trong bảng thuộc tính. Video layer giữ audio nguồn chính, không phát âm thanh của B-roll.
- **Kinetic:** thêm scene, sửa title/emphasis/subtitle, thẻ, theme, accent, progress và duration. Các template có request/manifest Remotion được đọc lại thành nội dung có thể sửa. Preview dùng chung component React với renderer, không render MOV mỗi lần gõ chữ.
- **Giữ phần đã ưng:** chọn clip/cue/layer rồi bấm Khóa vùng. Khóa bảo vệ tất cả lớp tác động tới interval đó, không chỉ phần đang chọn. Tab Đã khóa liệt kê vùng và cho phép mở khóa rõ ràng. Thay đổi audio/framing/style caption toàn cục hoặc ripple trước vùng khóa có thể bị chặn vì ảnh hưởng vùng đã duyệt.
- **Lưu:** autosave sau khoảng nghỉ ngắn; trạng thái lỗi lưu hiện rõ, draft chưa lưu vẫn ở giao diện để sửa/hoàn tác. Ctrl+Z/Ctrl+Shift+Z cho undo/redo trong phiên; các bản lưu có snapshot trên đĩa. Nếu phiên khác thay đổi draft, phải tải lại thay vì ghi đè.
- **Mở revision do AI dựng:** chọn revision cạnh tên project. Editor lưu checkpoint draft trước khi nhận bản mới và kiểm tra vùng khóa; bản xung đột bị từ chối. Không âm thầm nhập revision mới vào draft đang làm.
- **Xuất:** bấm Xuất MP4 và xác nhận bản đang hiển thị. Nếu job chưa có setup, chọn các mục hiển thị trước xuất. Footage Analyst, STT và research mới vẫn thực hiện qua AI/CLI theo lựa chọn; editor không âm thầm chạy chúng. Bản xuất tạo revision mới và ghi nguồn feedback từ hành động UI, không giả làm tin nhắn chat của người dùng.

## Dữ liệu và khóa

```text
jobs/JOB/editor/project.json       Draft đang làm + version, base revision và checksum nguồn
jobs/JOB/editor/history/           Snapshot mỗi lần lưu
jobs/JOB/editor/checkpoints/       Snapshot trước khi mở revision khác
jobs/JOB/editor/locks.json         Interval đã duyệt + fingerprint nội dung
jobs/JOB/editor/setup.json         Thiết lập đã xác nhận qua nút xuất
jobs/JOB/editor/proxies/           Proxy browser tạo khi cần cho định dạng không phát trực tiếp
```

Khóa nằm ngoài edit-plan để không phát minh trường renderer không hiểu. Server kiểm tra fingerprint nguồn, clip/source-time/crop, các overlay/cue giao nhau, thông số motion, output, caption style và audio. Thay đổi gain nhạc/voice tác động mọi đoạn nên bị chặn khi có vùng khóa liên quan. `render`/`render --dry-run` cũng kiểm tra các khóa này; đổi JSON ngoài UI không tự vượt qua chúng. Chỉ mở khóa khi có hành động hoặc chỉ dẫn rõ của user.

Khóa là bảo vệ nội dung/bố cục/timing đã duyệt, không là cam kết MP4 xuất lại có cùng byte hay cùng lượng tử nén. Motion đang dựng trực tiếp được khóa theo spec và thời điểm phát; khi xuất thành asset mới, cache path có thể đổi mà nội dung đã chọn giữ nguyên.

## AI tiếp tục sửa

Đọc draft hiện tại bằng `EditorStore.load(JOB)` trong `core/editor_service.py`. Chỉ sửa phần được yêu cầu và ghi bằng `EditorStore.save(JOB, candidate, expected_version)`; không sửa trực tiếp `project.json` hay `locks.json`. Trả lỗi xung đột/khóa cho user và giữ phần còn lại. Khi làm qua revision CLI, tiếp tục dùng `revision --from-revision ... --feedback ...`, áp dụng thay đổi thật và để user mở revision đó vào editor. Không sửa hay ghi đè bản đã xuất.

Không chuyển khóa thành quyền bỏ qua các quyết định sáng tạo. Một yêu cầu sửa chữ không tự chọn nhạc, crop, hook hay ảnh mới. Người dùng được xem preview và trực tiếp điều khiển; không thêm role AI review/vòng tự sửa chất lượng.

## Preview, cache và giới hạn

Preview chạy video/ảnh/caption trên browser và component Remotion cho motion. ASS khi xuất có thể khác chút về rasterization/font/wrapping; so lại bản xuất. Voice gain trên 1 và ducking chỉ áp đầy đủ ở FFmpeg; preview phát gain tĩnh. MOV/ProRes ngoài template cần proxy H.264 lần đầu; proxy không giữ alpha. Template có request/manifest dùng React nên không cần proxy MOV. Bộ dựng hiện vẫn một video nguồn chính; B-roll có thể nằm trên các layer.

Xuất MP4 cuối vẫn encode timeline bằng FFmpeg. Motion không đổi dùng lại asset gốc; motion thay đổi render theo hash spec, và lần xuất sau tái sử dụng asset cùng spec/hash hợp lệ. Đây là cache asset, không phải smart-render/stream-copy những đoạn MP4 cũ. Không báo “không render lại video cuối” hoặc “chỉ encode đoạn sửa” khi chưa có engine đó. Keyframe camera, color grading, speed ramp, SFX theo timeline, TTS và phân tích/phiên âm chạy bằng nút trong UI chưa được thêm.

## Nguồn tham khảo và kiểm chứng

Đối chiếu ngày 27/10/2026: [OpenCut](https://github.com/OpenCut-app/OpenCut) và [classic](https://github.com/OpenCut-app/opencut-classic) cho hướng sản phẩm editor local; main đang viết lại, classic ghi đã archive. Không fork source của các repo vào dự án. Chọn tiếp stack Python/FFmpeg và Remotion hiện có để đọc đúng job/plan/asset của dự án.

Các API Player và tương tác canvas theo tài liệu chính thức: [Player](https://www.remotion.dev/docs/player/player), [drag/resize](https://www.remotion.dev/docs/player/drag-and-drop), [best practices](https://www.remotion.dev/docs/player/best-practices). Player được memo hóa riêng với transport/playhead. Editor là code mới của dự án, không phải Remotion Editor Starter trả phí.

Kiểm tra bằng `python -m unittest discover -s tests -v`, `npm --prefix editor test`, `npm --prefix editor run build`, `npm --prefix motion run typecheck`. Media test tổng hợp kiểm tra lưu/khóa/revision/export/cache, và thử UI qua Chrome với project tổng hợp. Đây là kiểm tra phần mềm, không phải bước AI chấm video của user.
