# Studio usability release verification — 2026-11-05

Scope: desktop launcher and session recovery, browser file selection with media thumbnails, and caption search/replacement while preserving approval locks. This is software verification, not an AI video quality review.

## Automated checks

- `.venv/Scripts/python.exe -m unittest discover -s tests -v`: **33 passed**. Includes real FFmpeg exports, caption corrections beside a locked cue, transcript/source preservation, motion cache reuse, legacy approval locks, optimistic saves, HTTP origin/path/range checks, streamed uploads, interrupted-upload cleanup, and real hidden server startup/reuse.
- `npm --prefix editor test`: **9 passed**. Covers timeline mapping, literal/Vietnamese/case-sensitive caption search, single/bulk replacement, partial lock intersections, empty-result protection, immutable input and invalid/stale browser sessions.
- `npm --prefix editor run build`: TypeScript and production build passed after the final UI changes.
- `npm --prefix motion run typecheck`: passed. Existing client-directive/chunk-size bundler warnings remain; they do not fail the build.
- Source packaging tests verify both launch entry points are included and runtime/private files are excluded.

## Manual Windows + Chrome checks

| Requirement | Observed result |
|---|---|
| Installed desktop shortcut | `AI Editor Studio.lnk` targets the workspace's Python windowless executable, launcher script and working directory. |
| Cold start, then repeated clicks | The actual shortcut starts a stopped server and opens Studio. Two subsequent shortcut launches retain the same listening server PID. Duplicate browser tabs were closed after verification. |
| Close and resume | Closed the saved Studio tab, stopped the server, opened the desktop shortcut. The same project, Lời thoại tab and frame 120 (4 seconds at 30 fps) returned; preview remained paused. |
| Real source selection | Chose a 113.23-second 720 × 1280 MP4 through the browser file chooser. The imported source checksum matched its original. Preview reached readyState 4 and played. |
| Multiple media selection | Selected a Vietnamese-named image, WAV and MP4 in one chooser. All three appeared with successfully loaded image/video/waveform thumbnails. |
| Cancel selection | Dismissed the chooser without selecting files; library and draft were unchanged. |
| Use imported media | Added image and music from their thumbnails, then a short MP4. Saved two overlays and background music. The short video layer ended at its available duration rather than assuming three seconds. |
| Caption bulk edit | A synthetic three-cue draft had its middle cue locked. Replacing HPG changed the other two cues and reported one skipped locked cue. |
| Undo / redo / individual edit | One undo restored both replaced cues; redo reapplied them. Direct cue editing, single-cue replacement, case-sensitive no-results and timestamp seeking worked. |
| Existing lock compatibility | A browser round trip initially exposed the old 1.0/1 fingerprint mismatch. The fix accepts equivalent numeric values, verifies old approvals against matching original snapshots and leaves lock files unchanged. Tests still reject changed locked text and gain. |
| Screen height | Checked the actual desktop browser viewport. Media lists retain scrollable thumbnail space; replacement controls collapse so caption rows remain reachable. |
| Final state | Studio left open on the synthetic sample with the locked cue selected and its text/timing controls disabled. |

Private evidence is kept in ignored `.test-output/ease-ui/` (including the final screenshot), with full Python results in `.test-output/ease-python-tests.log`. The existing jobs' 23 JSON files matched their pre-test hashes. Real media, personal jobs, screenshots, local session data and server logs are not part of the source release or Git commit.

## Boundaries

The three usability additions do not implement STT inside Studio, a chat UI, or smart MP4 rendering. Final export still encodes the timeline. Session location uses browser local storage; saved drafts and locks remain on disk. A browser crash before a new job is created can leave its temporary source in `.studio/imports/`; see `core/visual-editor.md`.
