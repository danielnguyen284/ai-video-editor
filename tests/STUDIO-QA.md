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

## Transparent speech-keyword follow-up — 2026-11-05

After user feedback, added the pure-alpha Keyword template, independent emphasis frame, shared bundled Be Vietnam Pro fonts and adjustable caption outline. **35 Python tests** and **10 frontend tests** passed, plus motion typecheck, skill validation and production editor build. The new media test decodes actual ProRes alpha before/after the emphasis anchor, checks transparent entry/exit/corners, composites it on source footage, and verifies libass selects the bundled bold font without missing-glyph messages. Old template tests still pass.

The source release includes the Regular/Bold TTF files, OFL license and checksums. HTTP checks confirm Studio serves the exact bundled font bytes. The revised project's caption/motion metadata, version and checkpoint are verified through EditorStore and the project API. Current browser UI inspection was unavailable because local browser control was disabled in Work settings; these checks do not claim a new manual UI pass. Private revision media and feedback remain excluded from Git and the source ZIP.

## Speed, keyframed zoom, blurred framing and SFX - 2026-11-07

Scope: constant per-clip speed (0.5-2x), source-anchored zoom/punch-in keyframes, `fit: blur` and timed SFX in the renderer, lock fingerprints, Studio preview and controls. Software verification only.

- `tests/test_effects.py` (14 tests, real FFmpeg on synthetic media): 2x speed halves duration and the colour change lands at the right second; a 440 Hz tone still counts ~440 rises/s after `atempo` (resampling would give 880). A black/white edge moves exactly as a left-anchored linear zoom predicts at 0, 1 and 2.5 s; a `hold` punch-in on source second 2 lands on output second 1 at 2x. `blur` fills pad bars with the picture's colour while the centre stays sharp. A 1 kHz SFX at frame 30 is audible only in its window with the voice muted; a missing SFX file fails dry-run. A plan without new fields keeps its previous filtergraph. Locks: zoom at 1x and SFX outside the range keep existing signatures; speed, visible zoom and overlapping SFX are blocked; a Studio export with all four effects renders through the setup/decision path.
- `editor/tests/effects.test.mjs` (3 tests): reflow lengths and caption mapping at 2x, SFX anchored to its source moment across reorder/speed and dropped when cut away, zoom values identical to the Python evaluator.
- Prototype check: FFmpeg `perspective` at scale 1 is bit-identical to the input (PSNR inf) and renders 90 frames of 1080×1920 in about 1 s.
- Browser (Chrome, throwaway job from `sample.mp4` in a scratch root, not under `jobs/`): the project opened with blurred framing; the clip inspector showed speed, presets and keyframe rows; changing speed to 1.5x shortened the timeline to 7.1 s, moved the SFX with its clip and autosaved; Punch-in at the playhead autosaved; preview after the punch-in matched the exported frame. The SFX track and inspector (frames, file, volume) rendered.
- Found and fixed during the browser pass: with more tracks than the panel height, the track area scrolled vertically on its own and drifted from the sticky labels. `.timeline-scroll` now aligns to its content so the whole timeline body scrolls together.
- Full Python suite run concurrently with an editor production build failed two Remotion tests with "Chrome ran out of memory or disk space" (disk was 97% full); both passed when rerun alone. Keep heavy builds and Remotion renders sequential on this machine.

Boundaries: preview blur uses CSS and only approximates the FFmpeg backdrop; preview caps SFX/music volume at 1. Speed ramps, face-following crops, split-screen/PIP and clip transitions are not implemented.

## Editing by transcript, voice cleanup/loudness and Studio proposals - 2026-11-07

Ideas taken from the OpenChatCut feature list and written fresh for this project (no OpenChatCut code copied; its source is AGPL).

- `tests/test_editing_tools.py` (9 tests): `denoise: strong` lowers synthetic room noise between phrases by more than 10 dB after AAC export; `loudness_lufs: -14` measures within 1.5 LU of -14 with `ebur128`; invalid values fail. Transcript words come from the plan's transcript, then `cleaned.json`, then `raw.json`, skip another asset's transcript, and keep a sentence without word timings as one token. Proposals leave `project.json` byte-identical until accepted, become exactly one new version, archive as accepted/rejected/superseded without their state, are refused when the draft changed after proposing or when they touch a locked range, and work over the Studio HTTP API (brief polling without state, full state, accept).
- `editor/tests/words.test.mjs` (6 tests): cutting a word cuts at the middle of the surrounding silences and updates its caption; hand-edited captions are kept and counted; pause ranges and their total; cuts before a lock are skipped; restore re-inserts the range with a caption and refuses to move a locked region; word times map through clip speed; cutting everything fails.
- Browser (throwaway job in a scratch root with a synthetic word transcript): the Cắt chữ tab showed kept, cut and searched words; searching "ờ" then Chọn kết quả and Cắt removed two fillers (-1.3 s), split the timeline and autosaved; Khôi phục brought one back; Rút khoảng lặng reported nothing left to cut. A proposal bar showed the summary and changes; Xem trước switched preview and timeline to the proposal read-only; a stale proposal was refused with an explicit message; a fresh one was approved as one version and a single undo returned to the previous draft.
- Fixed during the browser pass: four library tabs did not fit the column (the last one was clipped); the proposal summary reported a clip-count change when only zoom changed; a word search for "ờ" also matched "ngờ" (now whole words first).
- Observed: the browser screenshot tool sometimes timed out for 30 s right after seeking in a project with blurred framing, then recovered; a seek in the same project did not reproduce it. Not proven to be the blur preview; watch for slow seeks.

Boundaries: cleanup and loudness are export-only; cuts and restores use Whisper word times, which can be off by a few hundredths of a second; restoring inserts after the nearest earlier clip in source order.
