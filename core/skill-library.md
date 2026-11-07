# Thư viện skill video và các nhóm so sánh

Bộ skill tự viết trước đây đã được thay ngày 07/11/2026. Có 32 skill thuộc 6 repo đang mở trong Chrome, cùng 1 skill kết nối OpenChatCut. Nguồn, commit, license và checksum được ghim trong [library.json](../skills/library.json). Source upstream cài tại `.tools/skill-library/`, được giữ nguyên và không commit cùng dự án. Profile cũ không còn được dùng để tạo job mới; job/revision cũ giữ config và nội dung skill snapshot đã ghi.

## Chọn một nhóm cho mỗi phương án

| Nhóm | Profile | Nguồn và việc chính | Trạng thái thực tế |
|---|---|---|---|
| A · Melvynx | `melvynx-raw-vi` | [video-agent-skills](https://github.com/Melvynx/video-agent-skills): raw/short-form, script, B-roll, học style, repurpose và các tác vụ phụ | 13 skill đã cài; native engine Node/Chrome/FFmpeg có bước setup riêng |
| B · Sunithvs | `sunithvs-raw-vi` | [video-agent-skill](https://github.com/sunithvs/video-agent-skill): talking-head, kinetic text, Reels và YouTube | 2 skill đã cài; script upstream nhắm macOS/Linux, cần port/kiểm tra trên Windows |
| C · Wallstreet | `wallstreet-finance-vi` | [wallstreet-explainer](https://github.com/HeyChengC/wallstreet-explainer): presenter, bằng chứng, đồ thị và motion tài chính/công nghệ | Skill và kit đã cài; compositor/model riêng chưa setup; ví dụ 16:9 không tự là layout TikTok |
| D · Motion Prompt | `motion-catalog-vi` | [motion-prompt](https://github.com/showheyohtaki/motion-prompt): chọn motion/chuyển cảnh bằng ID, spec và code mẫu | Skill/CLI đã cài; từng move cần port vào composition của job |
| E · Agentic | `review-variants-vi` | [agentic-video-editing](https://github.com/real-simple-labs/agentic-video-editing): ad variants và feedback theo timestamp | 3 skill đã cài; native pipeline dùng Apple Silicon/macOS; AI QA không tự bật |
| F · Resolve | `resolve-roughcut-vi` | [video-editor-skills](https://github.com/appariciojunior/video-editor-skills): rough cut, caption, B-roll, audio và export trong Resolve | 12 skill đã cài; cần Resolve/scripting; nguồn ghi CC BY-NC 4.0, chưa có quyền dùng thương mại |

Đây là các nhóm hướng dẫn và công cụ có nguồn rõ ràng. Việc cài skill không bổ sung tự động keyframe, speed ramp, tách nền hoặc renderer mới vào Studio. Trước một job, đọc entrypoint nhóm và đúng các file upstream liên quan, xác định engine có thể dùng, giải thích phần thiếu trước khi người dùng chọn phương án. Không tải toàn bộ 33 skill vào context hoặc trộn các mặc định thẩm mỹ của mọi nhóm thành một style.

Các template Keyword/KineticScene, font Be Vietnam Pro và helper [render_text.py](../scripts/render_text.py) là công cụ render kỹ thuật dùng chung. Chúng tiếp tục phục vụ các bản đã dựng và asset mới khi được chọn; không đại diện cho các skill cũ đã gỡ.

## Cài lại, kiểm tra và lưu snapshot

Codex nhận diện skill repo từ `.agents/skills/`. Source đặt riêng trong `.tools/skill-library/` không tự hiện trong menu. Dự án đăng ký **39 entrypoint** (33 package + 6 nhóm) với tên riêng, không copy/sửa package upstream. Theo [tài liệu chính thức](https://learn.chatgpt.com/docs/build-skills), Codex CLI/IDE dùng `$` hoặc `/skills`; ChatGPT dùng `@` khi skill có trong selector của host.

| Muốn dùng | Tên trong menu Codex |
|---|---|
| Melvynx dựng short cụ thể | `$video-melvynx-short-editing` |
| Chọn nhóm Melvynx và helper phù hợp | `$video-group-melvynx-raw` |
| Catalog motion theo ID | `$video-motion-prompt` |
| Explainer tài chính/công nghệ | `$video-wallstreet-explainer` |
| Kết nối OpenChatCut | `$video-openchatcut` |
| B-roll Melvynx / Resolve | `$video-melvynx-broll` / `$video-resolve-broll` |

Gõ `$video-` để lọc các mục của repo. Chọn một skill hoặc nhóm làm workflow chính trong prompt; chỉ đọc helper khi cần. Tên profile như `motion-catalog-vi` dùng cho CLI/Studio, không phải tên skill trong menu. Khi menu còn cache, khởi động lại Codex trong đúng workspace. Phạm vi cục bộ không làm skill xuất hiện trong một workspace khác.

```powershell
.\.venv\Scripts\python.exe scripts/install_skill_library.py
.\.venv\Scripts\python.exe scripts/install_skill_library.py --check
.\.venv\Scripts\python.exe ai_editor.py skills --full
.\.venv\Scripts\python.exe scripts/register_skill_shortcuts.py --check
```

Script dùng helper `skill-installer` của Codex và đúng commit trong manifest. Có thể truyền `--installer PATH` nếu helper nằm nơi khác. Nó giữ các package đã đúng checksum, không ghi đè package bị sửa hoặc cài dở, và không chạy setup engine/API/model của upstream. Sau khi kiểm tra source, nó đăng ký entrypoint vào `.agents/skills/`. Có thể chạy `scripts/register_skill_shortcuts.py` riêng để bổ sung các entrypoint còn thiếu; file đã sửa tay được giữ lại và báo lỗi. Setup tổng hợp có flag `-WithSkills`. ZIP nguồn mang manifest, nhóm định tuyến, entrypoint và script phục hồi; source tải về, ví dụ media và engine bên thứ ba không nằm trong ZIP.

Khi làm theo lệnh trong upstream, ánh xạ `<skill-dir>` hoặc đường dẫn ví dụ `~/.claude/skills/...` tới thư mục package thực tế trong `.tools/skill-library/<source>/<package>`. Giữ các package cùng nguồn cạnh nhau để các reference tương đối tìm đúng chỗ. Kiểm tra script/path thực có trên máy trước khi chạy.

Khi tạo job, resolver kiểm tra toàn bộ checksum package của nhóm và lưu Markdown upstream vào `resolved-config.json`, cùng commit/license/hash source. Nhờ vậy sửa thư viện về sau không âm thầm đổi instruction của job cũ. Profile có tên nhóm riêng; trường domain hiện dùng `domain/source-context` làm cầu nối kỹ thuật, còn lĩnh vực/ngôn ngữ lấy từ lựa chọn và brief thực tế.

## Tạo nhiều output để so sánh

Với video mới, chọn các nhóm cần thử, chung nguồn và brief, đồng thời chọn khung so sánh. Ví dụ sau tạo ba **draft ban đầu**, chưa cắt, phiên âm hoặc xuất video:

```powershell
.\.venv\Scripts\python.exe ai_editor.py compare-new thu-01 --video .\inbox\raw.mp4 --profiles melvynx-raw-vi sunithvs-raw-vi wallstreet-finance-vi --format vertical --brief "So sánh ba cách dựng từ cùng nguồn; giữ cùng nội dung và âm thanh"
```

Lệnh tạo `thu-01-a`, `thu-01-b`, `thu-01-c` dưới `jobs/` và manifest tại `comparisons/thu-01/comparison.json`. Video gốc được copy, nguồn được đối chiếu checksum; tất cả dùng chung kích thước/fps. Setup và phương án dựng vẫn pending. Không xem tên profile hoặc ví dụ này là sự đồng ý cho tốc độ 1.15x, nhạc, TTS, API hoặc nền mặc định của upstream.

Agent đọc transcript, làm rõ biến nào cần so sánh (motion/style, hook, cut hoặc bố cục) và biến nào dùng chung. Sau lựa chọn hoặc ủy quyền có phạm vi, dựng từng job thành output độc lập, ghi quyết định thật và xuất revision riêng. Không tự thêm AI chấm điểm hay chọn bản thắng.

Sau khi có các MP4:

```powershell
.\.venv\Scripts\python.exe ai_editor.py compare-view thu-01
```

Mở file HTML được trả về để xem các bản cạnh nhau, phát/dừng cùng lúc. Trang chọn revision đã xuất mới nhất của mỗi job, không tự coi đó là final. Các cut khác nhau không tự căn theo cùng câu nói; cần giữ chung cut nếu mục đích chỉ là so motion. Chạy lại `compare-view` khi xuất revision mới.

Với project hiện hữu có vùng đã duyệt, giữ workflow revision/EditorStore và kiểm tra khóa. Không dùng `compare-new` để nhập lại nguồn rồi coi như được phép vượt khóa của project cũ. Không sửa `locks.json` hoặc `project.json` trực tiếp.

## Quy tắc dùng upstream trong dự án

- Engine mặc định của Studio vẫn thực thi schema hiện có. Asset dựng bằng engine ngoài phải được copy vào job, giữ source/spec/credit và mô tả đúng mức chỉnh sửa được trong UI. Video đã bake không tự trở thành từng layer có thể sửa.
- Giữ STT local/model đã được chọn và transcript nguồn. Đổi sang whisper.cpp, MLX, ElevenLabs, dịch hoặc TTS cần lựa chọn tương ứng của user; cài skill không chọn thay.
- Skill setup không được tự sửa quyền agent, cài extension, đăng nhập tài khoản, nới permission hoặc đăng video. Chỉ thực hiện các tác vụ ngoài này khi người dùng yêu cầu đúng phạm vi đó.
- `video-qa` và review server của upstream được cài nhưng không tự chạy. Workflow hiện tại vẫn là người dùng xem output và góp ý; code tests và kiểm tra file/media kỹ thuật tiếp tục bình thường.
- Với Resolve, giữ giới hạn sử dụng phi thương mại theo license nguồn khi chưa có cấp quyền khác. Với mọi nhóm, media/font/logo ví dụ có quyền riêng, không tự chọn làm asset cho video người dùng.
- Ghi các bài học có phạm vi vào nhóm định tuyến hoặc preference/job. Không sửa trực tiếp upstream đã pin; đổi source cần cập nhật manifest/hash có chủ ý và giữ snapshot cũ. Xem [style-learning.md](style-learning.md).

## Giao diện

Đã cài skill kết nối [OpenChatCut](../.tools/skill-library/openchatcut/openchatcut/SKILL.md). App/MCP chưa được cài, kết nối hoặc thay cho Studio. Đánh giá và phương án chuyển dữ liệu ở [openchatcut.md](openchatcut.md).
