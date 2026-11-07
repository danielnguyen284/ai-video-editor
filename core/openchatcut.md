# Đánh giá OpenChatCut làm giao diện

Đối chiếu source [0xsline/OpenChatCut](https://github.com/0xsline/OpenChatCut/tree/9242a95aea248ff3a8dab495514384e858320d47), commit `9242a95aea248ff3a8dab495514384e858320d47`, package 0.2.17 ngày 07/11/2026. Đây là đánh giá tài liệu/model/session source có chọn lọc, chưa là kết quả chạy thử app hoặc kiểm chứng chất lượng xuất video.

**Đề xuất: chọn OpenChatCut làm ứng viên giao diện tiếp theo và thử bằng project sao chép.** Multi-track timeline, chỉnh clip/caption/effect, undo và giao thức MCP draft phù hợp hướng AI dựng, người dùng chỉnh trực quan. Skill thư viện sáng tạo có thể dùng với nhiều backend; giữ chúng độc lập với một UI cụ thể.

## Phần đã chuẩn bị

- Skill `openchatcut` và references đã cài trong `.tools/skill-library/openchatcut/openchatcut`, đúng commit và checksum trong `skills/library.json`.
- Chưa cài app, chưa ghi cấu hình MCP/Codex, chưa mở rộng quyền đọc thư mục hoặc đụng project đang dùng. Giao diện Studio hiện tại tiếp tục hoạt động.
- Source yêu cầu Node `>=24.22.1 <25`; máy hiện có Node `22.17.0`. Chạy source cần môi trường Node 24 phù hợp riêng. Upstream cũng có Windows desktop installer bản sớm tại [Releases](https://github.com/0xsline/OpenChatCut/releases).

## Khả năng chuyển đổi

| Dữ liệu/tác vụ của AI Editor | OpenChatCut tương ứng | Việc cần làm |
|---|---|---|
| Một nguồn chính, clips source in/out và output frames | ProjectDoc → assets/timelines/tracks/clips | Viết adapter nhập asset, cut và timebase; kiểm tra số frame và audio sync bằng clip tổng hợp |
| Cue caption output frame + font Be Vietnam Pro | Caption track/data | Map timing, text, font/outline/placement và so preview/export tiếng Việt |
| Layer ảnh/B-roll + Keyword/Kinetic source/spec | Media clip hoặc motion graphic/effect | Map transform, alpha, layer order và thời gian; asset video baked chỉ sửa như video, muốn sửa chữ cần port component/spec |
| Voice gain/nhạc/ducking | Audio tracks và routing | Map thông số và kiểm tra nghe/xuất; không giả định gain/ducking giống engine FFmpeg hiện tại |
| Revision và optimistic version | External edit session, baseRevision, draft, manual proposal và atomic undo | Giữ một session; đối chiếu revision; commit đúng bản người dùng duyệt |
| Khóa interval cho mọi lớp bằng fingerprint | TrackFlags có `locked` cho thao tác cấu trúc track | Chưa có bridge tương đương interval fingerprint của dự án. Cần lớp kiểm tra range/nguồn trước apply/export, không coi track lock là đã bảo toàn quy tắc cũ |
| `jobs/JOB/editor/project.json` và locks riêng | ProjectDoc/local store riêng | Không mở trực tiếp JSON của Studio như project OpenChatCut; giữ bản cũ, nhập qua adapter và lập báo cáo phần không map được |

Model [ProjectDoc](https://github.com/0xsline/OpenChatCut/blob/9242a95aea248ff3a8dab495514384e858320d47/src/editor/projectTypes.ts) có assets/timelines/activeTimelineId. [TrackFlags](https://github.com/0xsline/OpenChatCut/blob/9242a95aea248ff3a8dab495514384e858320d47/src/editor/trackTypes.ts) và [edit-session](https://github.com/0xsline/OpenChatCut/blob/9242a95aea248ff3a8dab495514384e858320d47/src/agent/external-edit-session.ts) cho thấy đây là model khác với draft/lock file của dự án. Chưa xác minh chuyển qua FCPXML giữ được đầy đủ custom motion và lock; chỉ dùng như một kênh interchange có giới hạn sau khi thử.

## Phương án thử trước khi chuyển mặc định

1. Dùng bản OSS trong thư mục/app riêng; source dùng Node đúng version hoặc chọn installer Windows từ release chính chủ. Không đổi Node đang phục vụ dự án hiện tại chỉ để chạy thử.
2. Nhập clip tổng hợp 5–10 giây, caption tiếng Việt, alpha text và hai audio layer. Thử trim/split/undo, đổi một keyword, xuất và mở lại project.
3. Kết nối MCP theo Settings → MCP, endpoint thường là `http://localhost:5199/api/external-mcp/mcp`, dùng bearer token của app và `approvalMode: manual`. Không lưu token trong Git hoặc tự chọn quyền đọc toàn ổ đĩa; browser local import cần danh sách thư mục cho phép.
4. Viết/kiểm tra adapter từ bản sao job hiện có, kiểm tra rõ phần bảo vệ range đã duyệt. Sau đó mới chọn thay launcher/UI mặc định. Không chuyển project đang có lock trước khi quy tắc này hoạt động.

Core timeline/manual editor/local store được upstream mô tả là hoạt động không phụ thuộc cloud; các tính năng AI/transcription/media online cần provider tương ứng. Không mặc định model large-v3 đang có sẽ được app dùng trực tiếp. Source dùng AGPL-3.0-or-later; xem [LICENSE](https://github.com/0xsline/OpenChatCut/blob/9242a95aea248ff3a8dab495514384e858320d47/LICENSE) khi quyết định fork/phân phối.

Phần thay UI chưa được triển khai trong lần thay thư viện skill này; chưa có tuyên bố về tốc độ, độ đẹp hoặc khả năng bảo toàn project qua chuyển đổi.
