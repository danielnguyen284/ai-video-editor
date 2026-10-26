# AI Video Editor — Bộ khung role và skill

## 1. Mục tiêu dự án

Xây dựng bộ khung AI editor có thể tái sử dụng cho nhiều style dựng và nhiều lĩnh vực nội dung.

Người dùng đưa video raw, mô tả kết quả mong muốn và feedback bằng ngôn ngữ tự nhiên. Hệ thống phân tích footage, nghiên cứu, lập kế hoạch dựng, tạo visual khi cần, xử lý âm thanh và dùng FFmpeg để cắt ghép, xuất video. AI Editor Studio cho phép user sửa trực quan timeline/caption/layer/motion, xem preview và khóa các vùng đã ưng. Có thể prompt AI sửa tiếp rồi mở revision mới vào editor sau khi kiểm tra khóa.

**AI luôn đưa lựa chọn cho các quyết định chưa chốt; người dùng chọn rồi AI mới thực hiện.** Bao gồm style, lĩnh vực, định dạng, dùng/bỏ phân tích footage, phiên âm, cách cắt/hook, caption, research, visual và âm thanh. AI đưa khuyến nghị, không tự coi khuyến nghị hoặc giá trị mặc định là câu trả lời. Lựa chọn đã nêu rõ trong prompt được tính là đã trả lời; chỉ hỏi tiếp phần chưa rõ hoặc phát sinh mới.

Ví dụ:

> “Dựng video này kiểu premium, chủ đề chứng khoán, xuất TikTok tiếng Việt.”

> “Cùng footage này, làm thêm bản tutorial chậm hơn để giải thích cho người mới.”

**TikTok là nền tảng dựng chủ yếu; tài chính tiếng Việt là profile triển khai đầu tiên.** Hướng dẫn nền tảng nằm ở `core/platforms/tiktok.md`: mở ý sớm, cắt theo nội dung, caption tránh giao diện và chữ sẵn, đưa phương án cụ thể để người dùng chọn. Bộ khung lõi phải dùng lại được khi chuyển sang công nghệ, giáo dục, kinh doanh hoặc style khác.

Tài liệu này mô tả kiến trúc và lộ trình. Bộ khung Python, role, CLI FFmpeg, layer ảnh/video, phân tích footage và editor local React + Remotion Player đã có code. Thư viện hiện có bốn style (premium-explainer, visual-keyword, talking-head-pro, kinetic-motion), hai domain (finance, general) và bốn template Remotion (MetricCard, BarChart, LowerThird, KineticScene). Xem `README.md`, `core/visual-editor.md`, `core/schemas/edit-plan.md` và `core/schemas/visuals-and-footage.md` để biết cách dùng/giới hạn. Xuất MP4 cuối vẫn encode timeline; chỉ motion asset được cache, chưa có smart-render từng đoạn.

---

## 2. Mô hình cốt lõi: Role + Skill + Tool + Profile

| Thành phần | Trả lời câu hỏi | Ví dụ |
|---|---|---|
| Role | Ai chịu trách nhiệm việc gì? | Researcher tìm nguồn và dữ liệu; Editor đề xuất phương án và thực hiện lựa chọn của người dùng |
| Skill | Thực hiện công việc theo phương pháp và tiêu chuẩn nào? | Research tài chính; dựng premium explainer |
| Tool | Dùng công cụ nào để thực thi? | Browser/search, faster-whisper, Remotion, FFmpeg |
| Profile | Dự án này chọn tổ hợp nào? | Finance + premium explainer + tiếng Việt + video dọc |

Nguyên tắc:

- Bộ role ổn định, dùng chung giữa các dự án.
- Skill được nạp theo style dựng và lĩnh vực; có thể thêm skill mà không đổi toàn bộ pipeline.
- Một skill có thể có hướng dẫn riêng cho nhiều role.
- Một role có thể dùng nhiều skill phù hợp với nhiệm vụ hiện tại.
- Tool có thể thay thế qua adapter, không làm thay đổi trách nhiệm của role.
- Profile ghép skill với thiết lập dự án và preference của người dùng.
- Role là ranh giới trách nhiệm; không bắt buộc mỗi role là một model hay một tiến trình riêng. V1 có thể chạy tuần tự bằng cùng một agent.

Ví dụ cùng role Researcher:

```text
Researcher + domain/finance
→ tìm BCTC, kiểm tra ticker, đơn vị và kỳ báo cáo

Researcher + domain/technology
→ tìm tài liệu sản phẩm, phiên bản và nguồn xác nhận tính năng
```

Ví dụ cùng một lĩnh vực:

```text
Finance + style/premium-explainer
→ giải thích bằng chart sạch, nhịp vừa, motion tiết chế

Finance + style/shortform-dynamic
→ mở đầu nhanh, caption nổi bật, thông tin chia thành các beat ngắn
```

---

## 3. Bộ role dùng chung

| Role | Trách nhiệm | Đầu vào chính | Đầu ra chính |
|---|---|---|---|
| **Editor / Orchestrator** | Hiểu yêu cầu, đưa lựa chọn về profile/skill và phương án dựng, chờ người dùng chọn, điều phối thực hiện và xử lý feedback | Brief, lựa chọn người dùng, transcript, footage/research khi được chọn | `job.json`, `decisions.json`, `edit-plan.json`, yêu cầu sửa |
| **Transcriber** | Chuyển giọng nói thành văn bản có timestamp, dùng glossary, đánh dấu chỗ chưa chắc | Audio, ngôn ngữ, glossary lĩnh vực | `transcript/raw.json`, `transcript/cleaned.json` |
| **Footage Analyst (tùy chọn)** | Được hỏi dùng/bỏ ở mỗi job; gợi ý bỏ với khung cố định, chỉ chạy khi người dùng chọn và có tool phù hợp | Video raw, transcript, lựa chọn người dùng | `footage-analysis.json` khi được sử dụng |
| **Researcher** | Tìm và đối chiếu dữ liệu, nguồn, logo, ảnh, B-roll; kiểm chứng theo skill lĩnh vực | Research brief từ Editor, claim cần kiểm tra, domain skill | `research.json`, `asset-manifest.json` |
| **Animator / Visual Designer** | Chọn component, tạo chart, card, caption và motion đúng style | Edit plan, dữ liệu đã xác nhận, style skill | Visual specification, component/asset cần dùng |
| **Sound Designer** | Làm sạch voice, chọn BGM/SFX, ducking, phối âm theo style | Audio, edit plan, style skill, tài nguyên âm thanh | `audio-plan.json`, audio đã xử lý |
| **Finisher** | Dùng FFmpeg cắt ghép clip, chèn caption/visual, phối audio, encode và xuất đúng phiên bản | Edit plan, visual, audio, export preset | Video từng revision và `render-manifest.json` |

### Ranh giới trách nhiệm

- Editor đề xuất nội dung và timeline, người dùng chọn phương án, các role thực hiện theo lựa chọn đã chốt.
- Researcher cung cấp bằng chứng và asset, không tự sửa lời nói hoặc tự thay cấu trúc video.
- Kiểm chứng chuyên ngành là nhiệm vụ của Researcher sử dụng domain skill; chưa cần tạo role Finance Verifier riêng.
- Finisher thực thi kế hoạch dựng bằng FFmpeg; thay đổi nội dung phải quay lại Editor.
- Người dùng trực tiếp xem video và quyết định cần sửa gì bằng prompt. Không có bước AI tự xem lại bản dựng, chấm điểm hoặc tự mở vòng sửa sau khi xuất.
- Screen editing như crop màn hình, zoom vùng thao tác, con trỏ và callout được xử lý qua Footage Analyst + Animator với skill tutorial/screencast. Chỉ tách role riêng khi khối lượng công việc yêu cầu.
- Quản lý revision và preference ban đầu thuộc Editor; không cần thêm agent chỉ để lưu trạng thái.

---

## 4. Hai nhóm skill chính

### 4.1. Style skill — cách dựng và trình bày

Một style skill định nghĩa:

- Nhịp dựng, cách chọn hook, xử lý khoảng lặng và câu lặp.
- Bố cục, typography, màu sắc, caption và safe area.
- Quy tắc crop, zoom, B-roll, transition và motion.
- Component/template được phép dùng và cách truyền tham số.
- Cách chọn BGM, cường độ SFX và ưu tiên giọng nói.
- Những lỗi thẩm mỹ cần tránh và tiêu chí hướng dẫn dựng.
- Reference và preset có thể tái sử dụng.

Danh mục dự kiến:

| Skill | Đặc trưng |
|---|---|
| `style/premium-explainer` | Bố cục rõ, chart sạch, motion tiết chế, thông tin phân cấp tốt |
| `style/shortform-dynamic` | Hook sớm, beat ngắn, caption nổi bật, chuyển visual có chủ đích |
| `style/minimal-corporate` | Chuyển động ít, typography nhất quán, ưu tiên sự rõ ràng |
| `style/tutorial-screencast` | Giữ đủ các bước thao tác, zoom vùng quan trọng, callout dễ theo dõi |
| `style/documentary` | Ưu tiên mạch kể chuyện, B-roll hỗ trợ ngữ cảnh, nhịp thay đổi theo nội dung |

Style phải độc lập với lĩnh vực. Không đóng cứng ticker, thuật ngữ tài chính hay nguồn BCTC vào `premium-explainer`.

### 4.2. Domain skill — hiểu và xử lý lĩnh vực

Một domain skill định nghĩa:

- Glossary, tên riêng, entity và cách viết thuật ngữ.
- Nguồn ưu tiên, cách tìm và kiểm chứng thông tin.
- Quy tắc số liệu, đơn vị, mốc thời gian và ngữ cảnh.
- Loại visual phù hợp với nội dung: chart, so sánh, sơ đồ, minh họa thao tác.
- Những thay đổi có thể làm sai ý nghĩa khi cắt dựng.
- Cách trình bày nguồn, xử lý mâu thuẫn và thông tin chưa xác nhận.
- Hướng dẫn chuyên ngành cho Transcriber, Researcher, Editor và Animator.

Danh mục dự kiến:

| Skill | Nội dung chính |
|---|---|
| `domain/finance` | Ticker, BCTC, kỳ báo cáo, chỉ số tài chính, nguồn dữ liệu và đơn vị |
| `domain/technology` | Tên sản phẩm, phiên bản, tài liệu chính thức, bằng chứng về tính năng |
| `domain/education` | Thuật ngữ bài học, thứ tự giải thích, ví dụ, tính đầy đủ của các bước |
| `domain/business` | Chỉ số kinh doanh, case study, so sánh và nguồn cho các claim |

Thêm lĩnh vực mới bằng skill riêng. Các lĩnh vực trong bảng là hướng mở rộng, không phải cam kết triển khai tất cả ở V1.

---

## 5. Cấu trúc một skill

Mỗi skill là một package có phiên bản, hướng dẫn và tài nguyên đi kèm. Cấu trúc dưới đây là quy ước nội bộ dự kiến của framework; adapter sẽ ánh xạ sang cơ chế skill của agent runtime được chọn.

```text
skills/
  styles/
    premium-explainer/
      skill.json
      SKILL.md
      references/
      presets/
      examples/
  domains/
    finance/
      skill.json
      SKILL.md
      glossary.txt
      sources.md
      guidelines/
      examples/
```

Ví dụ metadata của style skill:

```json
{
  "id": "style/premium-explainer",
  "version": "1.2.1",
  "kind": "style",
  "roles": ["editor", "animator", "sound-designer", "finisher"],
  "requires": {
    "components": ["SubtitleBlock", "MetricCard", "SourceCitation"]
  },
  "entrypoint": "SKILL.md"
}
```

`SKILL.md` cần nêu rõ:

1. Khi nào dùng skill và khi nào không phù hợp.
2. Role nào đọc phần hướng dẫn nào.
3. Đầu vào cần có và đầu ra phải tạo.
4. Quy tắc bắt buộc, tham số mặc định và phần cho phép tùy chỉnh.
5. Tài nguyên/component phụ thuộc và cách xử lý khi thiếu.
6. Ví dụ tốt, lỗi thường gặp và tiêu chí hướng dẫn dựng.

Ví dụ nội dung domain skill được phân theo role:

```text
Transcriber: cách viết ticker, thuật ngữ, xử lý từ chưa chắc.
Researcher: nguồn ưu tiên, đối chiếu số liệu, lưu bằng chứng.
Editor: giữ ngữ cảnh, không cắt mất điều kiện của một nhận định.
Animator: nhãn chart, đơn vị, kỳ dữ liệu, source citation.
```

---

## 6. Profile: ghép style với lĩnh vực

Profile chứa lựa chọn cho một nhóm video, không sao chép toàn bộ hướng dẫn của skill.

Ví dụ `profiles/finance-premium-vi.json`:

```json
{
  "id": "finance-premium-vi",
  "version": "1.2.1",
  "language": "vi",
  "skills": {
    "style": {"id": "style/premium-explainer", "version": "1.2.1"},
    "domain": {"id": "domain/finance", "version": "1.0.0"}
  },
  "export": {
    "preset": "vertical-shortform",
    "width": 1080,
    "height": 1920,
    "fps": 30,
    "fit": "pad"
  },
  "overrides": {
    "captions": {"max_lines": 2}
  },
  "preferences_ref": "preferences/default.json"
}
```

Ngôn ngữ, thương hiệu và thông số nền tảng là cấu hình bổ trợ. Không trộn chúng vào domain skill hoặc buộc một style chỉ xuất được một kích thước video.

Hai lựa chọn style hiện có được giữ thành package/profile riêng:

| Style | Profile tài chính | Cách thể hiện |
|---|---|---|
| `premium-explainer` | `finance-premium-vi` | Caption lời nói theo cụm, motion tiết chế |
| `visual-keyword` | `finance-visual-keyword-vi` | Tiêu đề hiện từ đầu, keyword lớn chọn lọc và ảnh minh họa; transcript dùng để chọn ý/canh thời gian, không chuyển hết thành caption |

Style `visual-keyword` có phân tích tham chiếu `sample.mp4`, hướng dẫn tạo layer và helper tạo PNG chữ tại `skills/styles/visual-keyword/`. Nó dùng FFmpeg/ASS/lớp PNG hiện có, không cần một engine mới. Tiêu đề, keyword cụ thể và ảnh minh họa được đưa trong phương án dựng để người dùng chọn; nguồn ảnh và âm thanh vẫn cần được chốt theo từng job.

Đổi sang công nghệ: thay domain skill và glossary tương ứng. Đổi cách dựng: thay style skill. Editor cập nhật asset/component phụ thuộc rồi xuất revision mới để người dùng xem và prompt tiếp.

V1 chọn một style chính và một domain chính cho mỗi job. Tổ hợp nhiều style hoặc nhiều domain sẽ được bổ sung khi có cơ chế hợp nhất rõ ràng.

---

## 7. Chọn skill và giải quyết xung đột

Editor thực hiện trước khi phân tích/dựng:

1. Đọc yêu cầu, footage và profile được chọn.
2. Nếu người dùng đã chỉ rõ lựa chọn, ghi nhận. Với phần chưa rõ, đưa 2–3 phương án cùng khuyến nghị và cho phép người dùng tự mô tả lựa chọn khác; không tự dùng profile mặc định.
3. Gom câu hỏi theo nhóm nhỏ: hướng dựng, xử lý đầu vào, cách trình bày; chờ người dùng trả lời từng nhóm. Sau transcript, đưa phương án cắt/hook cụ thể để người dùng chọn. Người dùng có thể giao quyền tự chọn trong một phạm vi được nêu rõ.
4. Kiểm tra skill tồn tại, đúng phiên bản và đủ dependency.
5. Tạo `resolved-config.json`: cấu hình đã hợp nhất, nguồn của từng override và phiên bản skill/tool/component.
6. Mỗi role chỉ nạp hướng dẫn và tài nguyên liên quan đến nhiệm vụ của mình.
7. Lưu lựa chọn và câu trả lời thực tế vào `decisions.json` theo revision. Chỉ render khi phương án đã được chọn và plan/config khớp với lựa chọn được ghi; tham số lệnh và phép tính frame là phần thực thi, không cần hỏi từng thao tác kỹ thuật.

Quy tắc hợp nhất:

- Domain skill quyết định cách xử lý thuật ngữ, bằng chứng và tính đúng đắn chuyên ngành.
- Style skill quyết định cách trình bày, nhịp dựng và chuyển động.
- Với các tham số trình bày được phép tùy chỉnh: yêu cầu cụ thể của job > override dự án > preference đã lưu > mặc định của skill.
- Ràng buộc toàn vẹn nội dung luôn phải được giữ: không bịa số liệu, không gắn nguồn giả, không cắt làm đảo nghĩa, không hiển thị claim chưa xác nhận như sự thật đã kiểm chứng.
- Nếu nhịp nhanh làm mất bước giải thích hoặc ngữ cảnh quan trọng, Editor phải giữ nội dung cần thiết và điều chỉnh nhịp.
- Thiếu skill/dependency phải được báo rõ. Fallback cần được ghi vào job, không im lặng nhận là đã áp dụng đủ skill.

---

## 8. Kiến trúc tổng thể

```text
USER: footage + yêu cầu + feedback
                    ↓
          Editor / Orchestrator
                    ↓
       AI đưa lựa chọn → USER chọn
                    ↓
   Profile + style skill + domain skill đã chọn
                    ↓
            Resolved config
                    ↓
    Transcriber + Footage Analyst khi cần
                    ↓
        Researcher khi cần nguồn/asset
                    ↓
       Editor tạo edit-plan + timeline map
                    ↓
       USER chọn phương án dựng cụ thể
                    ↓
   Animator khi cần + Sound Designer
                    ↓
      Finisher: FFmpeg cắt ghép / xuất video
                    ↓
          USER tự xem bản dựng
           ↙                 ↘
   Prompt chỉnh sửa       Ưng ý → dùng bản xuất
           ↓
   Editor tạo revision mới → FFmpeg xuất lại
```

Đây là luồng trách nhiệm, không bắt buộc tất cả role luôn chạy. AI luôn hỏi dùng/bỏ Footage Analyst, gợi ý bỏ với video khung cố định. Khi dùng, người dùng chọn phân tích local, AI trong IDE xem ảnh trích hoặc Ollama với model vision đã cài. Tương tự, AI hỏi về phiên âm, research và visual, rồi chạy theo lựa chọn của người dùng.

Các nhiệm vụ độc lập có thể chạy song song khi runtime hỗ trợ. Editor vẫn là nơi tổng hợp thay đổi vào kế hoạch dựng.

---

## 9. Hợp đồng dữ liệu giữa các role

Mỗi output phải có `schema_version`, `job_id`, revision và tham chiếu input/config đã sử dụng. ID cần ổn định qua các revision khi đối tượng không đổi.

| Artifact | Nội dung bắt buộc |
|---|---|
| `job.json` | Brief, input media, profile, giả định, mục tiêu, ngân sách/thời gian xử lý |
| `resolved-config.json` | Skill đã chọn và phiên bản, cấu hình hợp nhất, override và dependency |
| `decisions.json` | Lựa chọn setup/phương án dựng, câu trả lời thực tế, trạng thái chờ/đã chọn và hash plan/config tương ứng |
| Transcript | Văn bản gốc/đã làm sạch, source timestamp, word timestamp nếu có, chỗ cần kiểm tra |
| `footage-analysis.json` | Scene/take, source timestamp, lỗi hình ảnh, vùng mặt, đề xuất crop |
| `research.json` | Claim/entity, giá trị, đơn vị, kỳ dữ liệu, nguồn/bằng chứng, ngày truy cập, trạng thái kiểm chứng |
| `asset-manifest.json` | Asset ID, file, nguồn, thông tin quyền sử dụng nếu có, credit và hạn chế sử dụng |
| `edit-plan.json` | Clip giữ lại, thứ tự, mapping thời gian, overlay, caption, motion, audio và source reference |
| `render-manifest.json` | Input/plan/config revision, file xuất, thông số encode và trạng thái thực thi FFmpeg |
| Feedback | Prompt của người dùng, revision đã xem, timestamp/clip liên quan và thay đổi cần thực hiện |

Role gửi đề xuất sửa về Editor; không để nhiều role tự ghi đè cùng một timeline.

---

## 10. Edit plan và ánh xạ thời gian

Phải phân biệt thời gian trong raw với thời gian trong bản dựng. Caption, chart, audio và feedback đều liên kết với cùng bản timeline.

Ví dụ minh họa cấu trúc plan:

```json
{
  "schema_version": "1.0",
  "job_id": "video-001",
  "revision": 1,
  "config_ref": "resolved-config.json",
  "fps": 30,
  "duration_frames": 150,
  "export": {"preset": "vertical-shortform", "width": 1080, "height": 1920, "fps": 30, "fit": "pad"},
  "clips": [
    {
      "clip_id": "clip-001",
      "asset_id": "raw-001",
      "source_in_seconds": 8.0,
      "source_out_seconds": 13.0,
      "timeline_in_frame": 0,
      "timeline_out_frame": 150,
      "playback_rate": 1.0
    }
  ],
  "captions": {
    "enabled": true,
    "font_name": "Arial",
    "font_size": 58,
    "margin_v": 300,
    "max_chars": 28,
    "max_lines": 2,
    "items": [{"timeline_in_frame": 30, "timeline_out_frame": 90, "text": "HPG"}]
  },
  "audio": {"voice_gain": 1.0, "music": null},
  "overlays": []
}
```

Quy ước: khoảng thời gian bắt đầu bao gồm, kết thúc không bao gồm. Frame trên timeline là số nguyên; source timestamp giữ theo media gốc. Khi đổi tốc độ, thứ tự clip hoặc thời lượng, phải tính lại toàn bộ mapping và các phần phụ thuộc.

Trong ví dụ, source giây 8 trở thành frame 0 của bản dựng. Feedback luôn gắn với revision người dùng đã xem để tránh sửa nhầm sau khi timeline thay đổi.

---

## 11. Tool và engine

Bộ khung dùng Python 3.11+ để quản lý job/cấu hình/tool và Node.js với React/TypeScript cho Remotion. Agent trong IDE hỏi lựa chọn và thực hiện quyết định dựng/research; CLI không tự hiểu prompt dựng. OpenCV phân tích local, connector Ollama có thể gọi model vision đã được người dùng chọn/cài; dịch vụ search API riêng chưa được tích hợp.

FFmpeg là công cụ cắt ghép và xuất video chính:

| Nhiệm vụ | Lựa chọn khởi đầu | Vai trò sử dụng |
|---|---|---|
| Điều phối và suy luận | Agent runtime được chọn cho dự án | Editor và các role chuyên môn |
| STT tiếng Việt | faster-whisper + Whisper large-v3; benchmark phương án khác khi cần | Transcriber |
| Tách audio, cắt/ghép clip, crop/scale, chèn caption/visual, phối âm và encode | FFmpeg | Transcriber, Sound Designer, Finisher |
| Tìm nguồn và asset | Browser/search hoặc data API qua adapter | Researcher |
| Tạo motion graphic/chart động khi cần | Remotion, render thành asset để FFmpeg ghép vào video | Animator |
| Phân tích footage đầu vào | OpenCV lấy mẫu/cảnh/mặt/crop; AI trong IDE hoặc Ollama cho ngữ nghĩa khi được chọn | Footage Analyst |

Edit plan được chuyển thành các lệnh/filter graph FFmpeg để cắt ghép và xuất video. Caption, overlay và hiệu ứng đơn giản ưu tiên xử lý trực tiếp bằng FFmpeg. Remotion là công cụ tùy chọn để tạo visual hoặc motion phức tạp thành asset; job không cần những visual đó có thể chạy hoàn toàn bằng FFmpeg.

Người dùng xem file video đã xuất bằng trình phát và prompt chỉnh sửa. OpenChatCut, Diffusion Studio hoặc editor GUI là tùy chọn nếu sau này cần chỉnh tay.

Finisher nhận plan từ Editor và thực thi bằng FFmpeg; tránh để từng role tự tạo một cơ chế cắt ghép riêng. Lỗi lệnh, thiếu file hoặc encode thất bại được báo lại như lỗi thực thi, không tạo thành bước review nội dung. Cần tính chi phí tool, asset và dịch vụ theo cách sử dụng thực tế.

---

## 12. Component library và style system

Xây bộ visual template và preset dùng lại được. Preset đơn giản ánh xạ sang FFmpeg filter, subtitle style hoặc asset; component motion phức tạp có thể render bằng Remotion khi cần:

```text
SubtitleBlock    KeywordHighlight    LowerThird
MetricCard       ComparisonChart     TimelineChart
QuoteCard        NewsHeadline        SourceCitation
LogoCard         CalloutBox          PunchZoom
ScreenFocus      CursorHighlight     BRollLayer
```

- Component nhận data và theme token, không chứa sẵn nội dung chuyên ngành trong layout.
- Style skill chọn component, token, animation preset và giới hạn sử dụng.
- Domain skill hướng dẫn chọn dữ liệu, nhãn, đơn vị và loại biểu diễn phù hợp.
- Asset, template và component chuyên ngành có thể đi kèm domain skill nhưng phải đăng ký dependency rõ ràng.
- Không sinh lại toàn bộ thiết kế cho mỗi video. Thêm template/component khi thư viện hiện tại chưa đáp ứng yêu cầu rồi đưa vào bản xuất để người dùng xem.

Ví dụ `MetricCard` dùng được cho doanh thu, số người dùng hoặc kết quả học tập; domain skill quyết định ý nghĩa và cách đọc dữ liệu, style skill quyết định cách thể hiện.

---

## 13. Profile đầu tiên: tài chính tiếng Việt, premium explainer

### Transcription

- Dùng glossary ticker, doanh nghiệp và thuật ngữ như HPG, FPT, VN-Index, P/E, EPS, ROE.
- Giữ transcript gốc và lịch sử chỉnh sửa.
- Không đoán số liệu hoặc sửa con số chỉ dựa trên glossary.
- Khi chưa chắc, đánh dấu vị trí để nghe lại/đối chiếu.

### Research

- Ưu tiên công bố chính thức, BCTC và trang quan hệ nhà đầu tư; nguồn tổng hợp dùng để tìm kiếm/đối chiếu khi phù hợp.
- Mỗi số liệu đưa vào visual cần có giá trị, đơn vị, kỳ dữ liệu, nguồn và trạng thái kiểm chứng.
- Phân biệt doanh thu/lợi nhuận, quý/năm, tỷ đồng/triệu đồng, phần trăm/điểm phần trăm.
- Trạng thái claim: `verified`, `unverified`, `conflicting`.
- Claim chưa xác nhận hoặc có mâu thuẫn không được tự chuyển thành visual khẳng định. Editor cần yêu cầu xác nhận hoặc bỏ phần bổ sung đó, đồng thời ghi rõ vấn đề còn lại trong lời nói gốc.
- ASR nghe sai thì sửa dựa trên audio. Người nói sai so với nguồn thì ghi nhận mâu thuẫn, không âm thầm đổi caption để che khác biệt.

### Dựng và visual

- Video dọc 1080x1920, 30fps theo profile khởi đầu.
- Hook rõ trong phần mở đầu; ưu tiên câu có sẵn trong footage và giữ đúng ngữ cảnh.
- Caption tối đa hai dòng, font hỗ trợ tiếng Việt, tránh mặt và vùng giao diện nền tảng.
- Chart phẳng, nhãn và đơn vị rõ, có source citation khi dùng dữ liệu ngoài.
- Khi bổ sung adapter punch zoom: mặc định đề xuất scale tối đa 1.08, cách nhau ít nhất 8 giây; đây là hướng mở rộng, chưa có trong renderer ban đầu.
- Thay đổi visual theo nội dung; không thêm hiệu ứng chỉ để đạt một tần suất cố định.
- Voice là ưu tiên, BGM ducking, SFX tiết chế.
- Ưu tiên asset người dùng cung cấp, nguồn thật và chart dựng từ dữ liệu đã kiểm chứng. AI-generated visual chỉ dùng khi cần minh họa và không tạo bằng chứng giả.

---

## 14. Feedback, revision và preference

Ví dụ feedback:

> “Đoạn 15–20 giây nhạt quá.”

> “Chart này khó đọc, đổi sang bar chart.”

> “Những video sau ít zoom lại.”

Editor thực hiện:

1. Gắn feedback với revision, timestamp hoặc scene/entity liên quan.
2. Phân biệt yêu cầu cho một đoạn, một video hay preference cho những video sau.
3. Tạo revision mới của plan/config; giữ phần đã duyệt nếu không có phụ thuộc cần thay đổi.
4. Chỉ chạy lại các nhiệm vụ bị ảnh hưởng; dùng FFmpeg xuất revision mới và gửi người dùng xem.
5. Lưu revision trước để so sánh/hoàn tác.
6. Chắt lọc chỉ dẫn liên quan đến style theo `core/style-learning.md`; cập nhật skill và tài liệu khi có bài học dùng lại được, ghi nguồn và kết quả trong feedback của job.

Preference lưu ở phạm vi user, brand hoặc project với nguồn feedback. Một yêu cầu cục bộ không tự biến thành rule toàn cục.

Mỗi yêu cầu edit/chỉnh sửa đều được xem xét để tích lũy style. Người dùng đã cho phép agent tự cập nhật các quy tắc phù hợp vào skill và tài liệu trong cùng phiên, không phải hỏi lại chỉ để bảo trì file. Chỉ đưa phần dùng lại được vào đúng phạm vi; không biến một yêu cầu cục bộ thành luật cho mọi video và không thêm lặp quy tắc đã có. Khi skill thay đổi, tăng phiên bản và cập nhật profile khớp chính xác. Job đang làm tiếp tục dùng snapshot đã khóa cho đến khi có yêu cầu nâng cấp; việc học style không tự chọn thêm thay đổi sáng tạo cho revision đó.

Có thể cache asset, transcript, research và segment render theo dependency. Render từng phần chỉ áp dụng khi các phụ thuộc như transition, audio và timeline cho phép; không mặc định mọi thay đổi đều render riêng được.

---

## 15. Người dùng xem và prompt chỉnh sửa

Sau mỗi lần xuất thành công, hệ thống trả file video cùng revision để người dùng tự xem. Chất lượng dựng, nhịp, caption, visual và âm thanh do người dùng nhận xét trực tiếp qua prompt.

```text
FFmpeg xuất r001 → Người dùng xem
                       ↓
“Giây 15–20 cắt nhanh hơn, nhạc nhỏ lại”
                       ↓
Editor sửa plan/audio → FFmpeg xuất r002 → Người dùng xem tiếp
```

- Không có role review, QA report, chấm điểm hay vòng tự sửa chất lượng sau khi xuất.
- Researcher vẫn đối chiếu nguồn khi tạo dữ liệu/asset; đây là công việc nghiên cứu đầu vào, không phải review bản dựng.
- Editor chỉ thay đổi bản dựng tiếp theo theo prompt của người dùng; lỗi thực thi FFmpeg được xử lý riêng để hoàn thành lần xuất đang được yêu cầu.
- Người dùng có thể tải và sử dụng bất kỳ revision đã xuất thành công nào. Chỉ đánh dấu một revision là final khi người dùng chọn hoặc yêu cầu, không cần một bước duyệt của AI.
- Vòng chỉnh sửa không có giới hạn số lượt cố định; mỗi lượt bắt đầu từ prompt mới của người dùng.

---

## 16. Cấu trúc thư mục đề xuất

```text
ai-editor/
  ai-video-editor-project.md
  core/
    roles/
    orchestration/
    schemas/
    adapters/
  skills/
    styles/
      premium-explainer/
      shortform-dynamic/
    domains/
      finance/
      technology/
  profiles/
    finance-premium-vi.json
  preferences/
    default.json
  components/
    captions/
    charts/
    cards/
    effects/
  jobs/
    video-001/
      job.json
      resolved-config.json
      input/
      transcript/
      analysis/
      research/
      assets/
      revisions/
        r001/
          edit-plan.json
          decisions.json
          audio-plan.json
          render-manifest.json
          renders/
      feedback/
  tests/
    fixtures/
```

Đây là cấu trúc mục tiêu. Khi triển khai chỉ tạo những thư mục và file có chức năng thực tế; không cần tạo sẵn mọi package trong danh mục dự kiến.

---

## 17. Lộ trình triển khai

Đã có role/skill/profile snapshot và CLI tạo job/phiên âm/revision/lựa chọn/render. FFmpeg hỗ trợ cắt nối một source ở tốc độ 1x, crop nguồn cố định theo clip, pad/crop đầu ra, caption, layer ảnh/logo/B-roll, voice gain và nhạc nền/ducking. Remotion render MetricCard, BarChart, LowerThird và KineticScene thành asset alpha; KineticScene có thể giữ nền sáng/tối hoặc trong suốt. OpenCV xuất phân tích footage và có connector Ollama cho ngữ nghĩa. Chọn cut và áp dụng feedback do agent thực hiện theo lựa chọn của người dùng.

Theo yêu cầu triển khai trước khi thử video thật, phase 2 (visual layers), phase 3 (template Remotion) và phase 4 (phân tích footage/connector vision) đã có code. Bổ sung ngày 27/10/2026: hai style mới tự viết từ demo công khai, domain general, profile tương ứng và template KineticScene cho typography/thẻ/progress; nguồn và phạm vi học nằm trong references của từng skill. Test dùng media tổng hợp; API Ollama dùng server giả lập, chưa chạy model vision thật. Video thật, model STT/vision và các tổ hợp nội dung thực tế là bước kiểm chứng tiếp theo. Animated punch zoom, crop liên tục theo mặt, đổi tốc độ, SFX theo timeline và animation tùy ý vẫn chưa được triển khai.

### V1 — khung chạy được với profile đầu tiên

- Đặc tả trách nhiệm role và schema dữ liệu chung.
- Chọn/nạp style skill và domain skill, hợp nhất profile, khóa phiên bản cho job.
- Triển khai `style/premium-explainer` và `domain/finance` ở mức tối thiểu đủ dùng.
- STT tiếng Việt, phân tích footage cơ bản, research theo nhu cầu.
- Edit plan có mapping source/timeline và revision.
- Preset FFmpeg cho caption, overlay, punch zoom; asset metric card và source citation cơ bản.
- Dùng FFmpeg cắt ghép, xử lý audio và xuất video theo revision.
- Người dùng tự xem, prompt chỉnh sửa; Editor tạo revision mới và hỗ trợ hoàn tác.
- AI hỏi và đưa lựa chọn cho từng nhóm quyết định, lưu câu trả lời theo revision; không render khi còn lựa chọn chưa được trả lời.
- Chỉ bổ sung Remotion khi một yêu cầu motion graphic thực tế cần đến.

### V2 — chứng minh khả năng tái sử dụng

- Thêm `style/shortform-dynamic` và `domain/technology`.
- Dùng cùng core roles để dựng: finance + hai style, và hai domain + premium explainer.
- Mở rộng B-roll, screencast, chart, crop theo khuôn mặt và chọn take.
- Thêm brand profile, preference có phạm vi và cache các bước tốn chi phí.
- Hoàn thiện bộ ví dụ/hướng dẫn và kiểm tra tương thích của từng skill.

### V3 — mở rộng sản xuất

- Batch processing và nhiều video trong một project.
- Từ video dài tạo nhiều clip có nội dung độc lập.
- Nhiều tỷ lệ khung hình, tiêu đề, mô tả và thumbnail.
- Kết hợp nhiều domain/style có quy tắc rõ ràng.
- Quản lý phiên bản, nâng cấp và đánh giá chất lượng skill theo các job mẫu.

Không thêm role chỉ vì có thêm style, lĩnh vực hoặc công cụ. Chỉ tách role khi xuất hiện trách nhiệm độc lập cần quản lý riêng.

---

## 18. Definition of Done

### Cho bộ khung

- Role có trách nhiệm, input/output và ranh giới sửa dữ liệu rõ ràng.
- Profile chọn được style/domain skill và ghi lại cấu hình đã resolve.
- Core không chứa ticker, source list hoặc quy tắc thẩm mỹ riêng của profile đầu tiên.
- Thêm skill mới không cần viết lại orchestration; dependency mới được khai báo qua cơ chế chung.
- Có mapping thời gian, revision và khả năng tái tạo bản dựng từ input/config đã lưu.
- V1 chạy được với finance + premium explainer; V2 chứng minh đổi style/domain bằng các tổ hợp ở lộ trình.

### Cho một video

- Đúng brief, profile, định dạng xuất và revision người dùng yêu cầu.
- Caption và cắt dựng giữ đúng lời nói/ngữ cảnh; chỗ chưa chắc được xử lý hoặc báo rõ.
- Dữ liệu bổ sung có bằng chứng theo domain skill, không bịa nguồn hoặc số liệu.
- FFmpeg xuất thành công file video theo plan và thông số của revision.
- Người dùng tự đánh giá visual, âm thanh và chọn bản final theo ý muốn.
- Người dùng có thể feedback bằng lời để sửa tiếp hoặc hoàn tác.

---

## 19. North Star

> Một bộ khung editor có các role chuyên môn dùng chung; thay skill để đổi cách dựng và lĩnh vực, thay profile để phù hợp từng dự án.

Người dùng chỉ cần đưa footage và nói kết quả mong muốn. Hệ thống quản lý toàn bộ công việc phía sau, đồng thời giữ được tính nhất quán, khả năng kiểm tra và khả năng chỉnh sửa qua nhiều phiên bản.
