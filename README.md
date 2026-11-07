# AI Video Editor

Bộ dựng video bằng role + skill và **AI Editor Studio chạy local**. AI chuẩn bị draft; bạn xem trực tiếp, sửa timeline/caption/hình/motion và khóa những phần đã ưng trước khi xuất. Những lựa chọn sáng tạo còn thiếu vẫn được hỏi, không tự áp profile hoặc preference.

**Mới nhận bản ZIP:** giải nén rồi mở [HUONG-DAN.html](HUONG-DAN.html). Chạy setup để cài editor/công cụ trên máy mới. AI dựng nháp và xử lý prompt qua IDE; giao diện local cho phép bạn tự sửa trực quan.

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

**Hiện có thể chạy:** tạo job, snapshot profile/skill, STT tiếng Việt, cắt/đổi thứ tự clip, crop nguồn theo clip, pad/crop đầu ra, caption, lớp ảnh/logo/B-roll, voice gain, nhạc nền/ducking và lưu revision. Remotion tạo MetricCard, BarChart, LowerThird, Keyword và KineticScene (chữ/thẻ/progress) để ghép bằng FFmpeg; KineticScene có nền sáng/tối hoặc trong suốt. Footage analysis tạo ảnh trích, contact sheet, gợi ý cảnh/khuôn mặt/crop và đoạn nói lặp.

**Dùng qua agent:** lựa chọn phương án dựng/research được hỏi trong IDE, CLI thực hiện kế hoạch đã chọn. Hiểu ngữ nghĩa hình ảnh có hai cách: AI trong IDE xem ảnh trích hoặc gọi model vision đã cài qua Ollama. CLI không tự hiểu prompt dựng. Animated punch zoom, crop tự di chuyển theo mặt, đổi tốc độ và SFX theo timeline chưa được triển khai.

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

Nguồn upstream cài trong `.tools/skill-library/`, không commit media/ví dụ của bên thứ ba. [skills/library.json](skills/library.json) lưu nguồn, phiên bản và checksum. Trên máy mới hoặc sau khi nhận ZIP, khôi phục qua helper skill-installer của Codex:

```powershell
.\.venv\Scripts\python.exe scripts/install_skill_library.py
.\.venv\Scripts\python.exe scripts/install_skill_library.py --check
.\.venv\Scripts\python.exe ai_editor.py skills --full
```

Có thể dùng flag `-WithSkills` trong setup. Các file đã chỉnh khác checksum được giữ nguyên và báo lỗi, không bị ghi đè. Các skill được định tuyến qua AGENTS/profile trong dự án; skill toàn cục không thay đổi. Chúng có thể được agent đọc ở lượt chat tiếp theo trong workspace này.

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


## 2. Thiết lập môi trường

Cần Python 3.11 trở lên; phần Remotion cần Node.js/npm và browser Chromium. Workspace đã chạy với Python 3.13, Node.js 22 và Chrome. Từ thư mục dự án trên Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1 -WithTranscription -WithMotion -WithVision -WithSkills
.\.venv\Scripts\python.exe ai_editor.py doctor
```

Script tạo `.venv/`, tải FFmpeg/ffprobe portable vào `.tools/ffmpeg/bin/` và đối chiếu SHA-256. Các flag cài thêm STT, Remotion và OpenCV; có thể bỏ flag cho phần không sử dụng. Remotion dùng Chrome/Edge sẵn có hoặc tải Chrome Headless Shell khi render lần đầu trên máy chưa có browser. Script không sửa PATH hệ thống và không cần quyền admin.

Bản chia sẻ chỉ kèm mã nguồn và hướng dẫn. Mỗi máy cần chạy setup để tạo `.venv/`, tải FFmpeg và cài các phần tùy chọn. Model Whisper tải khi phiên âm lần đầu; large-v3 khoảng 3 GB và CPU có thể chạy chậm. Ollama vision cần cài riêng nếu được chọn. `doctor` không tải model, không chạy review video.

Nguồn công cụ: [FFmpeg downloads](https://ffmpeg.org/download.html), [Windows build từ Gyan](https://www.gyan.dev/ffmpeg/builds/), [faster-whisper](https://github.com/SYSTRAN/faster-whisper). STT tải model qua Hugging Face khi dùng tên model lần đầu. Có thể truyền đường dẫn model đã tải bằng `--model`.

### Whisper

**Cài thư viện và tải model là hai bước khác nhau.** Dự án dùng `faster-whisper` để phiên âm local:

1. `setup.ps1 -WithTranscription` chỉ cài thư viện STT và các phụ thuộc, **chưa tải model Whisper**. Nếu đã có `.venv`, cũng có thể cài bằng `.\.venv\Scripts\python.exe -m pip install -r requirements-stt.txt`.
2. Khi người dùng đã chọn phiên âm và model, lệnh `transcribe` sẽ tải model đó từ Hugging Face nếu chưa có. Model **không nằm trong ZIP**, nên mỗi máy mới cần mạng và dung lượng đĩa cho lần tải đầu.

| Lựa chọn | Điều cần biết |
|---|---|
| `large-v3` | Mặc định của CLI; file model khoảng **3 GB**, cần thêm dung lượng cho thư viện/cache. Ưu tiên chất lượng, có thể phiên âm chậm và tốn RAM trên CPU. |
| `small` | Model nhỏ hơn, phù hợp khi muốn giảm thời gian tải và tài nguyên; chất lượng nhận dạng có thể khác. Chỉ chuyển khi người dùng chọn. |

Agent phải giải thích và hỏi model trước khi tải lần đầu, trừ khi bạn đã chọn rõ. Sau khi có job và đã ghi nhận setup chọn phiên âm, agent chạy **một** phương án:

```powershell
# Chọn large-v3: lần đầu tự tải khoảng 3 GB, rồi mới bắt đầu phiên âm
.\.venv\Scripts\python.exe ai_editor.py transcribe video-001 --model large-v3

# Hoặc small, nếu người dùng chọn model nhẹ hơn
.\.venv\Scripts\python.exe ai_editor.py transcribe video-001 --model small
```

Thời gian tải phụ thuộc mạng; thời gian phiên âm phụ thuộc độ dài video, CPU và RAM. Giai đoạn tải chưa có transcript là bình thường. Nếu xảy ra lỗi tải, agent báo lỗi và thử lại đúng model đã chọn; không âm thầm đổi model hoặc xóa cache. Không chạy lại để ghi đè khi `transcript/raw.json` đã có.

Model được tái sử dụng từ cache khi còn đầy đủ và đúng phiên bản; không phải tải lại toàn bộ cho từng video. Cache Hugging Face mặc định trên Windows là `%USERPROFILE%\.cache\huggingface\hub`, có thể thay đổi bởi cấu hình `HF_HOME`/`HF_HUB_CACHE`. Nếu xóa cache, đổi model hoặc có phiên bản model mới, có thể phát sinh tải thêm. Xem [cách cache hoạt động](https://huggingface.co/docs/huggingface_hub/en/guides/manage-cache).

Nếu đã có **thư mục model đầy đủ ở định dạng faster-whisper/CTranslate2**, truyền đường dẫn thay cho tên model:

```powershell
.\.venv\Scripts\python.exe ai_editor.py transcribe video-001 --model .\.tools\models\faster-whisper-large-v3
```

Đây là đường dẫn ví dụ khi model đã được chuẩn bị riêng, không phải thư mục mà setup tự tạo. `doctor` kiểm tra thư viện/công cụ; báo STT đã cài không có nghĩa là model đã tải xong. Nếu dùng transcript có sẵn hoặc bỏ phiên âm, không cần tải model Whisper. Chi tiết tải theo tên model và dùng thư mục local có trong [tài liệu faster-whisper](https://github.com/SYSTRAN/faster-whisper#model-conversion).

## 3. Cấu trúc dự án

```text
AGENTS.md                     Agent đọc hướng dẫn thao tác
ai_editor.py                  CLI Python
ai-video-editor-project.md    Bản thiết kế gốc (lưu trữ)
core/
  roles/                      Trách nhiệm từng role
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
preferences/                  Preference có phạm vi của người dùng
inbox/                        Bạn đặt raw video ở đây
jobs/                         Input, transcript, asset, feedback và từng revision
scripts/                      Thiết lập môi trường
tests/                        Test code/cắt ghép bằng video tổng hợp
```

Các role dùng chung: Editor, Transcriber, Researcher, Animator, Sound Designer, Finisher. AI luôn đưa lựa chọn dùng/bỏ Footage Analyst; video khung cố định được gợi ý bỏ, quyết định thuộc về bạn. Bạn có thể tự sửa qua editor, xem bản xuất rồi prompt tiếp.

Quy ước hội thoại và lưu lựa chọn nằm trong `core/interaction.md`. AI chờ khi bạn chưa trả lời, chỉ làm phần chuẩn bị độc lập. Bạn cũng có thể chọn “AI tự chọn trong phạm vi này”; AI chỉ tự quyết trong phạm vi bạn đã giao.

Skill nằm trong dự án, được agent đọc qua `AGENTS.md`/profile. Chưa cài chúng thành global skills của IDE. Một agent có thể lần lượt đảm nhận các role; không cần chạy nhiều agent/model cùng lúc.

## 4. Các lệnh có thể chạy

```powershell
# Xem công cụ có sẵn
.\.venv\Scripts\python.exe ai_editor.py doctor

# Tạo job: copy raw, khóa skill/config và tạo plan giữ nguyên toàn bộ video
.\.venv\Scripts\python.exe ai_editor.py new-job hpg-001 --video .\inbox\raw.mp4 --profile melvynx-raw-vi --brief "TikTok tài chính, caption tiếng Việt"

# Hiển thị các quyết định đang chờ và gợi ý lựa chọn
.\.venv\Scripts\python.exe ai_editor.py choices hpg-001

# Agent hỏi người dùng; sau khi có câu trả lời, ghi setup theo core/interaction.md
# decide --stage setup --answers PATH --user-message "câu trả lời thực tế"

# Phiên âm: lần đầu tải model, mặc định CPU/int8
.\.venv\Scripts\python.exe ai_editor.py transcribe hpg-001

# Agent đọc transcript, chọn cut, sửa plan r001 và bật captions.enabled
# Chỉ tạo job/transcribe chưa có nghĩa là video đã được biên tập.
# AI đưa phương án dựng cụ thể; sau lựa chọn của người dùng, áp dụng vào plan
# rồi ghi decide --stage edit-plan --summary ... --user-message ...

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
```

`revision` lưu prompt, copy kế hoạch và giữ các lựa chọn setup đã chốt; phương án sửa của bản mới cần được ghi nhận riêng. `decide` chỉ lưu câu trả lời, agent phải thực sự hỏi và áp dụng câu trả lời đó. `render` chặn khi còn lựa chọn chưa trả lời hoặc plan/config đã đổi sau lựa chọn được lưu; `--dry-run` vẫn chuẩn bị được lệnh trước khi chốt phương án. Đây là lựa chọn của người dùng, không phải review bởi AI.

`render` mặc định dùng revision mới nhất nếu bỏ `--revision`. Bản xuất sẵn không bị ghi đè. Lỗi thực thi nằm trong `ffmpeg.log`; không có bước AI tự chấm điểm hay tự dựng lại sau khi xuất.

Plan nháp dùng `fit: pad` để chuẩn bị dữ liệu; agent phải hỏi bạn giữ toàn bộ hình với padding hay crop trước khi xuất. Giá trị trong plan nháp không được tính là bạn đã chọn. Footage analysis có gợi ý crop cố định từ ảnh mẫu, chưa có crop tự di chuyển theo mặt.

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
