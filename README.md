# AI Video Editor

Bộ dựng video bằng role + skill và **AI Editor Studio chạy local**. AI chuẩn bị draft; bạn xem trực tiếp, sửa timeline/caption/hình/motion và khóa những phần đã ưng trước khi xuất. Những lựa chọn sáng tạo còn thiếu vẫn được hỏi, không tự áp profile hoặc preference.

**Máy mới (clone hoặc nhận ZIP):** làm theo [mục 2. Cài đặt trên máy mới](#2-cài-đặt-trên-máy-mới), một lệnh `setup.ps1 -All` cài đủ công cụ, model, thư viện skill và Studio. Bản ZIP có thêm [HUONG-DAN.html](HUONG-DAN.html). AI dựng nháp và xử lý prompt qua IDE; giao diện local cho phép bạn tự sửa trực quan.

**Flow đã chốt cho yêu cầu “edit giúp tôi một video”:** agent đọc [flow mặc định](core/editing-workflow.md), dùng lại **large-v3 local** và bộ công cụ đã có, tự phân tích nguồn rồi đề xuất **một phương án để bạn duyệt trước khi dựng**. Không hỏi lại model ở mỗi clip. Các lựa chọn thường trực nằm ở [preferences/workflow.json](preferences/workflow.json); prompt mới và quyết định cũ của job được ưu tiên. Agent được phiên âm chuẩn bị trước creative setup, nhưng việc đó không duyệt cut, chữ, hình hay âm thanh.

## Editor trực quan

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1 -WithEditor -WithSkills
.\.venv\Scripts\python.exe ai_editor.py editor
```

Sau setup `-WithEditor`, nhấp shortcut **AI Editor Studio** trên desktop hoặc file **Open AI Editor.cmd** trong thư mục dự án. Launcher bật server ẩn và mở browser; mở nhiều lần dùng lại cùng server. Studio khôi phục project, tab, độ phóng timeline và vị trí xem gần nhất trong cùng browser. Không tự phát video. Có thể tạo lại shortcut bằng `scripts/create_shortcut.ps1`.

Mở [AI Editor Studio trên máy](http://127.0.0.1:8765). Tạo project bằng **Chọn video từ máy…**, hoặc nhập đường dẫn. Nút **+** ở Tài nguyên mở hộp chọn nhiều video/ảnh/nhạc; thư viện hiện thumbnail (nhạc có waveform), bấm để thêm vào timeline. Tab **Lời thoại** tìm caption, sửa từng câu, thay câu chọn hoặc thay tất cả câu chưa khóa, có phân biệt hoa thường. Sửa chữ/timing từng cue, kéo layer trên preview, kéo/trim trên timeline, chia clip, đổi thứ tự và chỉnh nội dung Kinetic. Có autosave, undo/redo, snapshot và mở revision do AI dựng. Khóa một vùng sẽ bảo vệ mọi lớp tác động tới vùng đó, được kiểm tra cả lúc lưu lẫn khi xuất bằng CLI.

**Sửa và preview không encode MP4.** Chỉ khi bấm Xuất MP4 mới tạo revision và encode video cuối; motion không đổi được tái sử dụng. Chưa có smart-render chỉ encode các đoạn sửa. Preview caption có thể khác ASS đôi chút, ducking chỉ áp khi xuất. [Cách dùng, giới hạn và workflow AI ↔ editor](core/visual-editor.md).

**Chữ bám lời nói:** template `Keyword` là chữ thuần trong suốt, có mốc hiện riêng cho dòng nhấn và fade/slide nhẹ. AI map word timestamps sang timeline trước khi tạo asset; editor không tự đồng bộ lời nói. Font **Be Vietnam Pro** Regular/Bold kèm giấy phép OFL nằm trong project, dùng cùng file cho keyword, caption chọn font này và preview/export; không cần cài font vào Windows. KineticScene vẫn có bố cục thẻ riêng. [Contract chữ và motion](core/schemas/visuals-and-footage.md).

**Ưu tiên TikTok:** agent gợi ý khung dọc 9:16, mở ý sớm, nhịp cắt gọn và caption dễ đọc, tránh chữ sẵn và giao diện TikTok. Thời lượng theo nội dung, không ép mọi video dưới 60 giây. Bạn vẫn chọn hook, độ dài, framing, footage/visual và âm thanh trước khi dựng. Hướng dẫn dùng chung ở [core/platforms/tiktok.md](core/platforms/tiktok.md); preference nền tảng lưu tại `preferences/default.json` và chỉ dùng để gợi ý, không tự chọn thay bạn.

**Hiện có thể chạy:** tạo job, snapshot profile/skill, STT tiếng Việt, cắt/đổi thứ tự clip, chuyển cảnh giữa clip (mờ chồng, chớp trắng, trượt, quét, lia nhanh; tiếng vẫn cắt thẳng), tốc độ cố định theo clip (0.5-2x, giữ cao độ giọng), crop nguồn theo clip, zoom keyframe/punch-in gắn với giây nguồn, pad/crop/nền mờ đầu ra, caption, lớp ảnh/logo/B-roll, voice gain, nhạc nền/ducking, SFX đặt theo timeline, giảm ồn giọng, chuẩn hóa âm lượng (-14 LUFS cho TikTok) và lưu revision. Trong Studio có thể cắt video bằng chữ trên transcript (cắt, khôi phục, tìm từ đệm, rút khoảng lặng) và duyệt hoặc bỏ đề xuất AI gửi vào. Remotion tạo MetricCard, BarChart, LowerThird, Keyword, KineticScene (chữ/thẻ/progress), Illustration (ảnh minh họa trong khung bo góc, trượt/phóng vào ra, zoom chậm) và Points (thẻ chữ lớn, từng ý hiện theo lời nói, số đếm lên) để ghép bằng FFmpeg; KineticScene có nền sáng/tối hoặc trong suốt. Footage analysis tạo ảnh trích, contact sheet, gợi ý cảnh/khuôn mặt/crop và đoạn nói lặp.

**Dùng qua agent:** lựa chọn phương án dựng/research được hỏi trong IDE, CLI thực hiện kế hoạch đã chọn. Hiểu ngữ nghĩa hình ảnh có hai cách: AI trong IDE xem ảnh trích hoặc gọi model vision đã cài qua Ollama. CLI không tự hiểu prompt dựng. Speed ramp trong một clip, crop tự di chuyển theo mặt, chia màn hình/PIP và chuyển cảnh giữa clip chưa được triển khai. Không kèm thư viện SFX; dùng file bạn đưa hoặc nguồn bạn đã chọn license.

## Thư viện skill mới và các phương án so sánh

Bộ style/domain tự viết trước đây đã được gỡ khỏi danh sách dùng cho job mới. **32 skill từ 6 repo đang mở trong Chrome**, cùng skill kết nối OpenChatCut, đã được cài local và ghim commit/checksum. Các nhóm:

| Nhóm | Profile | Mục đích |
|---|---|---|
| A · Melvynx | `melvynx-raw-vi` | Raw/short-form, script, B-roll, học style và repurpose |
| B · Sunithvs | `sunithvs-raw-vi` | Talking-head, kinetic text, Reels/YouTube |
| C · Wallstreet | `wallstreet-finance-vi` | Presenter, bằng chứng, số liệu và explainer tài chính/công nghệ |
| D · Motion Prompt | `motion-catalog-vi` | Chọn motion/chuyển cảnh theo ID và port vào composition |
| E · Agentic | `review-variants-vi` | Biến thể ad/hook, feedback theo timestamp |
| F · Resolve | `resolve-roughcut-vi` | Rough cut, caption và âm thanh trong DaVinci Resolve |

**Đã cài skill không có nghĩa đã cài engine của mọi repo.** Sunithvs/Agentic có phần phụ thuộc macOS; Resolve cần ứng dụng/scripting và nguồn có license phi thương mại. Từng nhóm, giới hạn chạy Windows và cách dùng nằm ở [core/skill-library.md](core/skill-library.md). Chọn một nhóm cho mỗi output; chỉ đọc helper liên quan. Các bản dựng cũ tiếp tục dùng snapshot của chính chúng; font, template và renderer kỹ thuật vẫn được giữ.

Nguồn upstream cài trong `.tools/skill-library/`, không commit media/ví dụ của bên thứ ba. [skills/library.json](skills/library.json) lưu nguồn, phiên bản và checksum. Trên máy mới hoặc sau khi nhận ZIP, `setup.ps1 -WithSkills` (có trong `-All`) tải lại từ GitHub đúng commit đã ghim và đối chiếu checksum, không cần Codex. Có thể chạy riêng:

```powershell
.\.venv\Scripts\python.exe scripts/install_skill_library.py
.\.venv\Scripts\python.exe scripts/install_skill_library.py --check
.\.venv\Scripts\python.exe ai_editor.py skills --full
```

Có thể dùng flag `-WithSkills` trong setup. Các file đã chỉnh khác checksum được giữ nguyên và báo lỗi, không bị ghi đè. **40 entrypoint trong `.agents/skills/` (Codex) và `.claude/skills/` (Claude Code)** giúp cả hai nhận diện 33 skill riêng lẻ, 6 nhóm và `video-edit` (điểm vào quy trình dựng của dự án) trong menu; source upstream vẫn nằm tại `.tools/skill-library/`. Đây là skill phạm vi repo, không thay đổi skill toàn cục.

Trong Codex CLI/IDE, mở đúng workspace `ai-editor`, gõ `$video-` rồi chọn skill. Ví dụ: `$video-melvynx-short-editing` cho một workflow cụ thể, `$video-motion-prompt` để chọn motion, hoặc `$video-group-melvynx-raw` để chọn cả nhóm và định tuyến tới helper phù hợp. Trong Claude Code, dùng cùng tên với dấu `/`, ví dụ `/video-melvynx-short-editing`. Prompt mẫu:

> Dùng $video-melvynx-short-editing dựng `inbox/raw.mp4` thành TikTok tiếng Việt. Đề xuất cách cắt, caption và hình minh họa để tôi chọn.

Hoặc chỉ cần chỉ định video và nói “edit giúp tôi video này”; agent dùng flow trên và tự đề xuất nhóm phù hợp. Không cần lặp model/engine ở mỗi prompt. Nếu chưa rõ video nào hoặc có một quyết định không thể suy ra từ nguồn, agent chỉ hỏi phần còn thiếu đó.

Không cần gõ tên profile JSON vào menu `$`; profile dùng khi tạo job qua CLI/Studio. Trong ChatGPT, dùng menu `@` nếu host hiển thị skill. Nếu danh sách vẫn cũ, khởi động lại Codex hoặc mở phiên Claude Code mới trong đúng repo. [Cách gọi và vị trí nhận diện skill chính thức](https://learn.chatgpt.com/docs/build-skills). Lệnh phục hồi riêng entrypoint: `.venv/Scripts/python.exe scripts/register_skill_shortcuts.py`.

**OpenChatCut là ứng viên thay giao diện.** Skill kết nối đã cài; app và MCP chưa cấu hình. [Đánh giá kỹ thuật và phương án chuyển dữ liệu](core/openchatcut.md) chỉ ra những phần cần map, đặc biệt khóa vùng đã duyệt và custom motion. Studio hiện tại tiếp tục phục vụ job cũ.

## 1. Bắt đầu một video hoặc nhiều bản thử

Đặt video vào `inbox/raw.mp4`, hoặc dùng **Chọn video từ máy…** trong Studio. AI copy nguồn và giữ file gốc. Ví dụ prompt:

> Dựng `inbox/raw.mp4` bằng nhóm `melvynx-raw-vi`. Đọc transcript và đưa phương án cắt, caption, hình minh họa và âm thanh để tôi chọn. Giữ tiếng Việt, nói rõ những hiệu ứng chưa chạy được trên máy này.

Hoặc tạo các draft độc lập từ cùng nguồn để sau này dựng A/B/C:

```powershell
.\.venv\Scripts\python.exe ai_editor.py compare-new thu-01 --video .\inbox\raw.mp4 --profiles melvynx-raw-vi sunithvs-raw-vi wallstreet-finance-vi --format vertical --brief "So sánh ba cách dựng; giữ chung nội dung và âm thanh"
```

Lệnh tạo `jobs/thu-01-a`, `jobs/thu-01-b`, `jobs/thu-01-c` với cùng nguồn và định dạng. Đây là draft đầy đủ footage, caption tắt, chưa tự cắt/STT/render. Người dùng chọn hoặc giao phạm vi quyết định; AI mới dựng từng phương án. [Workflow so sánh và giới hạn](core/skill-library.md#tạo-nhiều-output-để-so-sánh).

Khi đã có các bản xuất, chạy:

```powershell
.\.venv\Scripts\python.exe ai_editor.py compare-view thu-01
```

Mở HTML được trả về để xem cạnh nhau/phát cùng lúc. Trang dùng bản đã xuất mới nhất của từng job; không tự chọn bản thắng. Những bản có cut khác nhau không tự căn theo cùng câu nói.

Video nằm ở `jobs/JOB/revisions/rNNN/renders/video.mp4`. Xem rồi prompt tiếp, ví dụ: “Job `thu-01-a`, bản `r001`: giây 12–15 bỏ ảnh, giữ phần còn lại; tạo revision mới.” Mốc feedback là timeline bản đã xem. Với project có lock, dùng revision/EditorStore và giữ khóa; không nhập lại raw để vượt vùng đã duyệt.

Lựa chọn trong brief đã rõ được giữ lại. Các mục chưa rõ về output, Footage Analyst, STT, research, cắt, chữ/hình và âm thanh vẫn được hỏi theo nhóm nhỏ. Không có role AI chấm video hoặc vòng tự sửa chất lượng; bạn xem output và quyết định sửa tiếp/final.


## 2. Cài đặt trên máy mới

Làm đúng 4 bước dưới đây là chạy được, không cần Codex để cài (Codex hoặc Claude Code chỉ cần khi bắt đầu dựng).

### Cần có trước

| Thành phần | Yêu cầu | Ghi chú |
|---|---|---|
| Hệ điều hành | Windows 10/11 64-bit | Không cần quyền admin |
| Python | 3.11 đến 3.13 từ [python.org](https://www.python.org/downloads/) | Khi cài, tick **Add python.exe to PATH**. Bản "python" của Microsoft Store không dùng được |
| Node.js | 22 LTS từ [nodejs.org](https://nodejs.org/) | Cần cho Studio và Remotion |
| Git | [git-scm.com](https://git-scm.com/) | Chỉ cần khi clone; nhận ZIP thì bỏ qua |
| Trình duyệt | Chrome hoặc Edge | Studio và Remotion dùng trình duyệt có sẵn |
| Agent | Codex hoặc Claude Code, tài khoản riêng | Agent đọc `AGENTS.md` / `CLAUDE.md` trong repo |
| Ổ đĩa, RAM, mạng | Khoảng 8 GB trống; RAM 8 GB, nên 16 GB; tải khoảng 4 GB lần đầu | Phiên âm large-v3 cần khoảng 3 GB RAM trống |

Cài xong Python và Node.js thì **mở cửa sổ PowerShell mới** để PATH có hiệu lực.

### Bước 1. Lấy mã nguồn

```powershell
git clone https://github.com/danielnguyen284/ai-video-editor.git
cd ai-video-editor
```

Repo private thì chủ repo cần mời tài khoản GitHub của bạn trước. Nhận bản ZIP thì giải nén, mở PowerShell trong thư mục `ai-editor`.

### Bước 2. Cài mọi thứ bằng một lệnh

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1 -All
```

Lệnh làm lần lượt, mỗi phần có kiểm tra:

1. Kiểm tra Python, Node.js và dung lượng ổ đĩa; báo rõ thiếu gì.
2. Tạo `.venv/` và tải FFmpeg/ffprobe portable (đối chiếu SHA-256).
3. Tải 33 skill đã ghim từ GitHub (đúng commit, đối chiếu checksum) và đăng ký 40 skill cho Codex và Claude Code.
4. Cài faster-whisper và **tải model large-v3 đúng bản đã ghim** (khoảng 3 GB, đối chiếu mã băm). Mất mạng giữa chừng thì chạy lại đúng lệnh, phần đã tải được giữ và tải tiếp.
5. Cài OpenCV, Remotion, build AI Editor Studio và tạo shortcut **AI Editor Studio** trên desktop.
6. Chạy `doctor` để kiểm tra lần cuối.

Thường mất 20-60 phút, chủ yếu là tải model. Chạy lại bao nhiêu lần cũng an toàn: phần đã xong được kiểm tra rồi bỏ qua.

Muốn cài từng phần thay cho `-All`: `-WithSkills` (thư viện skill, bắt buộc để tạo job), `-WithTranscription` (thư viện phiên âm), `-WithModel` (model large-v3, tự kèm thư viện phiên âm), `-WithMotion` (Remotion), `-WithVision` (phân tích footage), `-WithEditor` (Studio và shortcut).

### Bước 3. Kiểm tra

```powershell
.\.venv\Scripts\python.exe ai_editor.py doctor
```

Cài đủ thì thấy: `OK ffmpeg`, `OK ffprobe`, `Large-v3 model: ready`, `Skill library: 33/33 pinned packages`, `Motion: {...}` và `Visual editor: ready`.

### Bước 4. Dựng video đầu tiên

1. Mở **AI Editor Studio** trên desktop (hoặc `Open AI Editor.cmd`).
2. Mở thư mục dự án trong Codex hoặc Claude Code.
3. Chép video vào `inbox/` rồi nhắn: "Edit cho tôi video inbox/ten-video.mp4". Trong Claude Code có thể gõ `/video-edit`, trong Codex là `$video-edit`.
4. Agent phân tích, gửi **một phương án** và chờ bạn duyệt rồi mới dựng. Bản xuất nằm ở `jobs/<job>/revisions/rNNN/renders/video.mp4`; sửa tiếp trong Studio hoặc nhắn agent.

### Cập nhật bản mới

```powershell
git pull
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1 -All
```

Nếu Studio đang mở, dừng server cũ để nạp code mới rồi mở lại shortcut:

```powershell
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'ai_editor\.py"?\s+editor' } | ForEach-Object { Stop-Process -Id $_.ProcessId }
```

### Chép từ máy đã cài (không có mạng)

Chép `.tools/models/faster-whisper-large-v3` (model) và `.tools/skill-library` (thư viện skill) từ máy đã cài sang đúng đường dẫn đó, rồi chạy setup như bước 2. Setup kiểm tra mã băm và bỏ qua phần đã có. Không chép `.venv/`, `node_modules/` (gắn với đường dẫn máy cũ), `jobs/`, `inbox/` hay `preferences/local-feedback.json` (dữ liệu riêng).

### Lỗi thường gặp

| Thông báo | Cách xử lý |
|---|---|
| `running scripts is disabled on this system` | Chạy đúng lệnh có `powershell -ExecutionPolicy Bypass -File ...` như bước 2 |
| `Python 3.11-3.13 is not installed` | Cài Python từ python.org, tick Add to PATH, mở PowerShell mới |
| `Node.js is not installed` | Cài Node.js 22 LTS, mở PowerShell mới |
| `Model download did not finish` | Kiểm tra mạng rồi chạy lại đúng lệnh setup; tải tiếp từ chỗ dừng |
| `Skill library: x/33` trong doctor | Chạy lại `setup.ps1 -WithSkills` (cần truy cập GitHub) |
| Phiên âm báo thiếu bộ nhớ | Đóng bớt ứng dụng và tab trình duyệt nặng (cần khoảng 3 GB RAM trống) |
| Studio báo `Unsupported ... fields` sau khi cập nhật | Dừng server Studio cũ bằng lệnh ở mục cập nhật rồi mở lại shortcut |
| Studio báo cổng đang được dùng | Đóng ứng dụng khác dùng cổng 8765, hoặc chạy `ai_editor.py editor --port 8766` |

Remotion dùng Chrome/Edge sẵn có, máy không có trình duyệt thì tự tải Chrome Headless Shell ở lần render đầu. Ollama (phân tích ảnh bằng model) không nằm trong setup, chỉ cài khi bạn chọn dùng.

Nguồn công cụ: [FFmpeg downloads](https://ffmpeg.org/download.html), [Windows build từ Gyan](https://www.gyan.dev/ffmpeg/builds/), [faster-whisper](https://github.com/SYSTRAN/faster-whisper). Mặc định dùng model local; override bằng tên model khác có thể tải weights qua Hugging Face. Có thể truyền một thư mục model tương thích đã chuẩn bị bằng `--model`.

### Whisper

**Cài thư viện và tải model là hai bước khác nhau.** Dự án dùng `faster-whisper` để phiên âm local:

1. `setup.ps1 -WithTranscription` chỉ cài thư viện STT và các phụ thuộc. `setup.ps1 -WithModel` (có trong `-All`) tải đúng bản large-v3 đã ghim vào `.tools/models/faster-whisper-large-v3`, đối chiếu mã băm, tải tiếp được khi đứt mạng; có thể chạy riêng `.\.venv\Scripts\python.exe scripts/download_model.py`.
2. Flow hiện tại dùng large-v3 trong thư mục local đã chuẩn bị. Model **không nằm trong ZIP hay Git**, nên mỗi máy mới chạy `-WithModel` hoặc chép thư mục model từ máy đã cài. Chỉ khi user chủ động override sang tên model khác, faster-whisper mới có thể tải weights chưa cache trong lệnh đó.

| Lựa chọn | Điều cần biết |
|---|---|
| `large-v3` | Đã chọn thường trực ở dạng local; file model khoảng **3 GB**, cần thêm dung lượng cho thư viện/cache. Không hỏi lại ở mỗi video. |
| `small` hoặc model khác | Chỉ là override khi user chủ động yêu cầu; không là phương án fallback tự động khi model đã chọn bị thiếu hoặc chạy chậm. |

**Model đã được chọn thường trực là large-v3 local.** Với video lời nói cần phiên âm, dùng lại transcript đúng nguồn nếu có; nếu chưa có, agent chạy lệnh sau, không hỏi chọn model lại:

```powershell
.\.venv\Scripts\python.exe ai_editor.py transcribe video-001
```

CLI ưu tiên thư mục `.tools/models/faster-whisper-large-v3` theo workflow đã chụp của job. Nếu thiếu/incomplete model, lệnh dừng trước khi chạy model và báo file thiếu; không tự tải hoặc đổi sang model khác. Trên máy mới, cài thư viện STT không đồng nghĩa có weights. Việc tải lại đúng model đã chọn cần được xử lý như một bước khôi phục môi trường.

Các lệnh bên dưới là **override rõ ràng**, chỉ dùng khi bạn yêu cầu một model/thư mục khác:

```powershell
# large-v3 cũng resolve về thư mục local đã chọn
.\.venv\Scripts\python.exe ai_editor.py transcribe video-001 --model large-v3

# Hoặc small, nếu người dùng chọn model nhẹ hơn
.\.venv\Scripts\python.exe ai_editor.py transcribe video-001 --model small
```

Thời gian phiên âm phụ thuộc độ dài video, CPU và RAM. Nếu một model khác được yêu cầu rõ bằng tên, faster-whisper có thể tải weights chưa cache; đó là giai đoạn tải, khác với inference. Không âm thầm đổi model hoặc xóa cache, không chạy lại để ghi đè khi `transcript/raw.json` đã có.

Với override theo tên, model được tái sử dụng từ cache khi còn đầy đủ; không phải tải lại toàn bộ cho từng video. Cache Hugging Face mặc định trên Windows là `%USERPROFILE%\.cache\huggingface\hub`, có thể thay đổi bởi cấu hình `HF_HOME`/`HF_HUB_CACHE`. Xóa cache, đổi model hoặc version có thể phát sinh tải thêm cho override đó. Large-v3 local của flow mặc định vẫn dùng thư mục đã chọn. Xem [cách cache hoạt động](https://huggingface.co/docs/huggingface_hub/en/guides/manage-cache).

Nếu đã có **thư mục model đầy đủ ở định dạng faster-whisper/CTranslate2**, truyền đường dẫn thay cho tên model:

```powershell
.\.venv\Scripts\python.exe ai_editor.py transcribe video-001 --model .\.tools\models\faster-whisper-large-v3
```

Thư mục này là mặc định đã chọn của workspace; chỉ `setup.ps1 -WithModel` tải nó (đúng bản đã ghim), lệnh `transcribe` không tự tải. `doctor` kiểm tra thư viện/công cụ; báo STT đã cài không có nghĩa model hợp lệ đã có. Nếu dùng transcript có sẵn hoặc bỏ phiên âm, không cần tải model. Xem [flow và provenance](core/editing-workflow.md) cùng [tài liệu faster-whisper](https://github.com/SYSTRAN/faster-whisper#model-conversion).

## 3. Cấu trúc dự án

```text
AGENTS.md                     Agent đọc hướng dẫn thao tác
ai_editor.py                  CLI Python
core/
  roles.md                    Trách nhiệm từng role
  adapters/                   FFmpeg, STT, visual, Remotion, footage và Ollama
  schemas/edit-plan.md        Cấu trúc plan, khả năng thực tế
skills/
  library.json                Commit, license, checksum và nhóm upstream
  styles/                     Sáu nhóm định tuyến, mỗi output chọn một nhóm
  domains/source-context/     Ngữ cảnh lấy từ brief, không ép domain mặc định
.tools/skill-library/         Source upstream đã cài, không commit
comparisons/                  Manifest và trang so sánh local (runtime)
profiles/                     Ghép skill, ngôn ngữ và cấu hình xuất
motion/                       Project React/TypeScript, template và Node renderer
editor/                       React + Remotion Player, timeline và bảng thuộc tính
preferences/                  Preference và workflow kỹ thuật thường trực
inbox/                        Bạn đặt raw video ở đây
jobs/                         Input, transcript, asset, feedback và từng revision
scripts/                      Thiết lập môi trường
tests/                        Test code/cắt ghép bằng video tổng hợp
```

Các role dùng chung: Editor, Transcriber, Researcher, Animator, Sound Designer, Finisher. AI luôn đưa lựa chọn dùng/bỏ Footage Analyst; video khung cố định được gợi ý bỏ, quyết định thuộc về bạn. Bạn có thể tự sửa qua editor, xem bản xuất rồi prompt tiếp.

Flow cố định ở `core/editing-workflow.md`; cách ghi lựa chọn ở `core/interaction.md`. Agent tự phân tích và đưa một phương án để bạn duyệt, áp dụng các thiết lập kỹ thuật thường trực không hỏi lại. Khi chưa duyệt phương án, chỉ làm phần chuẩn bị độc lập. Nếu bạn giao quyền tự chọn trong một phạm vi cụ thể, agent làm trong phạm vi đó.

Skill nằm trong dự án, được agent đọc qua `AGENTS.md`/profile. Chưa cài chúng thành global skills của IDE. Một agent có thể lần lượt đảm nhận các role; không cần chạy nhiều agent/model cùng lúc.

## 4. Các lệnh có thể chạy

```powershell
# Xem công cụ có sẵn
.\.venv\Scripts\python.exe ai_editor.py doctor

# Tạo job: copy raw, khóa skill/config và tạo plan giữ nguyên toàn bộ video
.\.venv\Scripts\python.exe ai_editor.py new-job hpg-001 --video .\inbox\raw.mp4 --profile melvynx-raw-vi --brief "TikTok tài chính, caption tiếng Việt"

# Hiển thị các quyết định đang chờ và gợi ý lựa chọn
.\.venv\Scripts\python.exe ai_editor.py choices hpg-001

# Agent dùng large-v3 local để phân tích, đề xuất một phương án; sau khi duyệt, ghi setup
# decide --stage setup --answers PATH --user-message "câu trả lời thực tế"

# Phiên âm chuẩn bị bằng large-v3 local, CPU/int8; không ghi đè transcript
.\.venv\Scripts\python.exe ai_editor.py transcribe hpg-001

# Agent đọc transcript, chọn cut, sửa plan r001 và bật captions.enabled
# Chỉ tạo job/transcribe chưa có nghĩa là video đã được biên tập.
# AI đưa phương án dựng cụ thể; sau lựa chọn của người dùng, áp dụng vào plan
# rồi ghi decide --stage edit-plan --summary ... --user-message ...

# Sau khi duyệt: bỏ các đoạn giây gốc đã chốt; điểm cắt tự dời về khe lặng, báo từ bị cắt ngang
.\.venv\Scripts\python.exe ai_editor.py cut hpg-001 --revision r001 --remove 0-0.8 12.75-14.13
# Caption 2 dòng cân đối từ transcript đã sửa, không tách từ ghép
.\.venv\Scripts\python.exe ai_editor.py captions hpg-001 --revision r001
# Dựng thử 25 giây đầu và ảnh ghép vài mốc vào previews/, không tạo revision
.\.venv\Scripts\python.exe ai_editor.py preview hpg-001 --revision r001 --seconds 25 --stills 1 12 24

# Xem lệnh và filtergraph sẽ chạy; chưa xuất video
.\.venv\Scripts\python.exe ai_editor.py render hpg-001 --revision r001 --dry-run

# Xuất video từ plan đã chỉnh
.\.venv\Scripts\python.exe ai_editor.py render hpg-001 --revision r001

# Tạo bản mới từ đúng bản bạn đã xem
.\.venv\Scripts\python.exe ai_editor.py revision hpg-001 --from-revision r001 --feedback "Bỏ 2 giây đầu"

# Agent cần áp dụng feedback vào plan r002 trước khi render
# Feedback cụ thể được tính là lựa chọn; hỏi thêm khi còn quyết định mới/chưa rõ
# và ghi lại lựa chọn edit-plan cho r002
.\.venv\Scripts\python.exe ai_editor.py render hpg-001 --revision r002

# AI gửi bản sửa draft để bạn bấm Duyệt/Bỏ trong Studio; draft chưa đổi cho tới khi duyệt
.\.venv\Scripts\python.exe ai_editor.py propose hpg-001 --state proposal.json --summary "Cắt từ đệm và rút khoảng lặng"
.\.venv\Scripts\python.exe ai_editor.py proposal hpg-001
```

`revision` lưu prompt, copy kế hoạch và giữ các lựa chọn setup đã chốt; phương án sửa của bản mới cần được ghi nhận riêng. `decide` chỉ lưu câu trả lời, agent phải thực sự hỏi và áp dụng câu trả lời đó. `render` chặn khi còn lựa chọn chưa trả lời hoặc plan/config đã đổi sau lựa chọn được lưu; `--dry-run` vẫn chuẩn bị được lệnh trước khi chốt phương án. Đây là lựa chọn của người dùng, không phải review bởi AI.

`render` mặc định dùng revision mới nhất nếu bỏ `--revision`. Bản xuất sẵn không bị ghi đè. Lỗi thực thi nằm trong `ffmpeg.log`; không có bước AI tự chấm điểm hay tự dựng lại sau khi xuất.

Plan nháp dùng `fit: pad` để chuẩn bị dữ liệu; agent phải hỏi bạn giữ toàn bộ hình với padding, crop hay nền mờ (`blur`) trước khi xuất. Giá trị trong plan nháp không được tính là bạn đã chọn. Footage analysis có gợi ý crop cố định từ ảnh mẫu, chưa có crop tự di chuyển theo mặt.

## 5. Thêm style hoặc lĩnh vực

Ví dụ prompt:

> Thêm skill style `shortform-dynamic` dựa trên video tham chiếu này; giữ domain finance và tạo profile mới để dùng riêng.

Agent tạo package có `SKILL.md` (frontmatter `name`, `description`) và `skill.json`, rồi tạo profile tham chiếu đúng ID/version. Dùng skill hiện có làm mẫu. Style chứa hướng dẫn cách dựng và mặc định caption/audio; domain chứa thuật ngữ, nguồn và cách xử lý dữ liệu. Không sao chép ticker vào style hoặc màu sắc vào domain.

Profile chọn skill và định dạng xuất. Preference lưu ở `preferences/default.json`; `editorial_preferences` là hướng dẫn cho agent, còn `overrides` là tham số CLI dùng khi tạo snapshot. Yêu cầu từng job được áp dụng vào plan sau lựa chọn của bạn. Job lưu snapshot file skill/config để những thay đổi sau không âm thầm ảnh hưởng bản cũ.

### Tích lũy style từ mỗi yêu cầu edit và sửa

Trong mỗi phiên edit/sửa, AI agent phải chắt lọc các chỉ dẫn có thể dùng lại về tiêu đề, keyword/caption, nhịp cắt, bố cục, ảnh và âm thanh. Khi có bài học mới phù hợp, agent cập nhật skill, phiên bản profile và tài liệu liên quan ngay trong phiên đó; bạn không cần nhắc lại hoặc cấp phép riêng cho việc bảo trì này. Quy trình chi tiết ở [core/style-learning.md](core/style-learning.md).

Mốc cắt, số liệu, tên mã, nội dung tiêu đề hoặc một ảnh của riêng video được giữ trong job. Quy tắc đã có sẽ được gộp hoặc giữ nguyên, không thêm lặp. Nếu có job, nguồn yêu cầu và kết quả chắt lọc được ghi tại `feedback/style-learning.json`. Các snapshot/quyết định cũ vẫn được giữ; style học được dùng cho các job sau và không thay thế bước bạn chọn phương án dựng. Đây là trách nhiệm của agent trong IDE, không phải chức năng CLI tự đọc feedback rồi sửa skill.

## 6. Kiểm tra code

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Test dùng media tổng hợp để kiểm tra thứ tự cắt ghép, thời lượng, audio/caption, revision và các thao tác chưa hỗ trợ. Đây là kiểm tra code; video của bạn do bạn xem và quyết định.

## 7. Visual, Remotion và footage đã chọn

Hợp đồng JSON, ví dụ layer/spec và giới hạn được ghi tại [visuals-and-footage.md](core/schemas/visuals-and-footage.md). Agent đọc tài liệu đó để dựng theo lựa chọn của bạn; bạn không cần tự viết JSON.

Sau khi đã hỏi và lưu các lựa chọn setup, agent có thể chạy:

```powershell
# Phân tích local: ảnh trích, cảnh, tín hiệu nét/sáng, khuôn mặt và đề xuất crop
.\.venv\Scripts\python.exe ai_editor.py analyze-footage hpg-001 --revision r001 --mode local

# Render request do agent tạo từ visual/data đã được bạn chọn
.\.venv\Scripts\python.exe ai_editor.py render-motion hpg-001 metric-01 --revision r001 --spec assets/metric-request.json
```

Kết quả phân tích nằm tại `jobs/hpg-001/revisions/r001/analysis/`; motion asset ở `jobs/hpg-001/assets/visuals/metric-01/`. Agent thêm ảnh/logo/video/motion asset vào `edit-plan.json`, hỏi về phương án chưa được chọn, ghi nhận lựa chọn rồi xuất bằng FFmpeg.

Nếu muốn AI hiểu nội dung hình ảnh, bạn chọn AI trong IDE xem ảnh trích hoặc Ollama. Với Ollama cần dịch vụ đang chạy và model vision đã cài; `--mode ollama --model TEN_MODEL_DA_CAI` gọi endpoint local mặc định. Không có model vision đi kèm và CLI không tự tải model đó. Ảnh mẫu có thể bỏ sót sự kiện ngắn, kết quả ngữ nghĩa là đề xuất chưa kiểm chứng và không tự sửa video.

Phần triển khai phase 2–3–4 đã có code: ghép visual, các template Remotion và phân tích footage/connector vision. KineticScene bổ sung chữ lớn, reveal thẻ và progress; [contract riêng](core/schemas/visuals-and-footage.md#kineticscene) mô tả props và giới hạn. Test dùng media tổng hợp; kết nối Ollama được kiểm tra qua server giả lập. Dữ liệu video/job thực tế không đi kèm gói chia sẻ.

## 8. Đóng gói để chia sẻ

```powershell
python scripts/package_release.py
```

ZIP và checksum nằm trong `dist/`. Gói có mã nguồn, skill/profile, test, script setup và hướng dẫn HTML; bỏ video, job/export cá nhân, model, `.tools/`, `.venv/`, `node_modules`, cache và lịch sử preference. Bản làm việc không bị xóa. Để tạo gói khác cùng ngày, dùng `--output dist/ten-goi-moi.zip`.
