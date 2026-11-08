# Executable edit plan — starter v1

The CLI supports a **single source video**, cut/reorder/repeat, a constant speed per clip (0.5-2x, pitch kept), per-clip fixed source crop, keyframed source zoom/punch-in, picture transitions between clips, output crop/pad/blurred backdrop, image/logo/B-roll layers, Remotion alpha-video assets, ASS captions, voice gain, optional looped/ducked background music and timed SFX. Speed ramps within a clip, continuous face following and split-screen/PIP layouts are not implemented; unsupported fields fail explicitly. KineticScene animates text/cards/progress inside a pre-rendered overlay asset; see the visual schema, not new main-timeline effect fields.

All source paths are relative to the job root and must stay inside it. The renderer invokes FFmpeg with an argument list, without a shell. The original imported video stays untouched.

The visual editor stores working plans, cue IDs, editable motion requests, history and approval locks outside this schema, under `jobs/JOB/editor/`. It compiles selected cues into supported `captions.items` and renders changed motion specs into video assets before exporting. No editor-only fields belong in the executable plan. CLI export and dry-run also enforce approved visual ranges; see [the editor contract](../visual-editor.md).

## Timeline

- `schema_version`: `1.0`; `job_id`: current job; `revision`: integer matching the `rNNN` directory.
- `config_ref`: `resolved-config.json` in that revision. Its settings and skill files are snapshots taken when the job/revision was created.
- `fps`: positive integer; `duration_frames`: total output frames.
- `export`: `{preset, width, height, fps, fit}`. Width/height must be even; `fit` is `pad` (keep all image on black), `crop` (center crop to fill) or `blur` (keep all image over a blurred, slightly darkened cover copy of the same picture, e.g. a landscape take in a 9:16 frame). No automatic moving crop is applied.
- `clips`: ordered objects with unique `clip_id`, `asset_id`, `source_in_seconds`, `source_out_seconds`, `timeline_in_frame`, `timeline_out_frame`, `playback_rate`, optional `crop`, `zoom` and `transition`.
- Intervals are start-inclusive/end-exclusive. Output timeline starts at 0, has no gaps/overlaps, and the last clip ends at `duration_frames`.
- `playback_rate` is a constant speed from 0.5 to 2.0 (`1.0` is unchanged). `(source_out_seconds − source_in_seconds) × fps / playback_rate` must match the output frame duration within half a frame. The voice keeps its pitch (FFmpeg `atempo`). Captions and lock fingerprints map source time through the rate. A speed is a creative choice like any other; a style group's habit (e.g. 1.15x) is not selected until the user chooses it.
- `overlays`: ordered image/video layers. See `core/schemas/visuals-and-footage.md` for exact fields, timing and transparency behavior.
- A clip after the first may contain `transition: {type, frames}`, the picture transition **into** it from the previous clip. `type` is `fade`, `flash` (through white), `slide-left`, `slide-right`, `slide-up`, `wipe-left` or `whip` (fast horizontal blur); `frames` is 2-30. It is centred on the cut: `floor(frames/2)` frames before it, the rest after. The output length and every timeline frame stay the same, and the voice still cuts hard (no overlapping speech). The picture needs source "handles": the previous clip continues past its `source_out_seconds` and this clip starts before its `source_in_seconds` by those frames (times `playback_rate`), so they must exist in the input; the handle frames may show material that was cut away. Two transitions around one clip must not overlap. Zoom keyframes stay on source seconds, so handles zoom correctly. FFmpeg `xfade` renders it; a plan without transitions keeps its previous filtergraph. Use transitions where the story changes or into/out of an illustration, not on every jump cut.
- A clip may contain `crop: {x, y, width, height}` in source pixels. This fixed rectangle is applied before output sizing; it must stay inside the displayed source dimensions. The analyzer can propose a rectangle, but the user selects whether to apply it. Source rotation metadata is reflected in the dimensions reported by `probe`.

Example: keep source 8–10s, then 2–3s at 30fps:

```json
[
  {"clip_id":"clip-001","asset_id":"raw-001","source_in_seconds":8,"source_out_seconds":10,"timeline_in_frame":0,"timeline_out_frame":60,"playback_rate":1.0},
  {"clip_id":"clip-002","asset_id":"raw-001","source_in_seconds":2,"source_out_seconds":3,"timeline_in_frame":60,"timeline_out_frame":90,"playback_rate":1.0}
]
```

Set `duration_frames` to 90. A reference to output second 2.5 now points to source second 2.5 in the second clip, not source second 10.5.

At `playback_rate: 2.0`, the first clip above (source 8-10 s) would last 30 output frames.

### Zoom and punch-in

`zoom` is a list of 1-32 keyframes with strictly increasing `source_seconds`:

```json
"zoom": [
  {"source_seconds": 12.0, "scale": 1.0, "x": 0.5, "y": 0.4},
  {"source_seconds": 15.5, "scale": 1.12, "x": 0.5, "y": 0.4, "ease": "in-out"},
  {"source_seconds": 16.2, "scale": 1.3, "x": 0.5, "y": 0.35, "ease": "hold"}
]
```

- `source_seconds` anchors the keyframe to the source, so trimming, splitting, reordering or changing speed keeps a punch-in on the same word. Use the transcript's word `start` directly. Keyframes outside the clip only shape the curve; before the first and after the last keyframe the value holds.
- `scale` is 1-4 relative to the clip's picture after its fixed `crop` and before output framing. `x`/`y` (0-1) is the focal point inside that picture; it stays in place while the picture scales, like CSS `transform-origin`. Faces usually sit near `y` 0.3-0.45; Footage Analyst face boxes can supply the point.
- `ease` describes the move **into** that keyframe: `in-out` (default), `in`, `out`, `linear`, or `hold` (stay at the previous value, then jump at this keyframe: a punch-in). It is ignored on the first keyframe.
- Export uses FFmpeg `perspective` with subpixel sampling: no zoompan jitter, and scale 1 is an exact identity. Studio previews the same formula with a CSS transform. Zooming beyond the source resolution softens the picture; keep punch-ins modest on 1080p sources.
- A clip that never scales above 1 adds no filter. Zoom affects only the main video, not overlays or captions.

## Captions

The initial plan includes style defaults but `enabled: false`. After transcription, the Editor can set it to true with `transcript_ref: "transcript/cleaned.json"`. The render adapter maps source word timestamps through each clip into output time. Word text is used when available, so glossary corrections must also update the word array.

Transcript shape:

```json
{
  "schema_version":"1.0","job_id":"demo","revision":0,"asset_id":"raw-001",
  "segments":[{"segment_id":"segment-0001","start":0.5,"end":1.2,"text":"Xin chào","words":[{"start":0.5,"end":0.8,"text":"Xin"},{"start":0.8,"end":1.2,"text":"chào"}]}]
}
```

For manually placed output captions, add `captions.items` instead of reading the source transcript:

```json
[{"timeline_in_frame":0,"timeline_out_frame":45,"text":"Ví dụ caption"}]
```

Style fields: `font_name`, `font_size`, `margin_v`, `max_chars`, `max_lines`, optional `outline_width` (finite 0–6 px, export default 3). Values are in output pixels/characters, not percentages; adjust for a different resolution. `Be Vietnam Pro` uses the project's bundled Regular/Bold TTF files for ASS via revision-local `fontsdir` and the same files in Studio. No OS font installation or external font request is needed. Legacy plans using Arial/other installed fonts retain that choice. Browser wrapping/rasterization can still differ slightly from ASS.

ASS `font_size` is the line height (ascent plus descent), not the em size. Be Vietnam Pro reserves tall space for Vietnamese marks (1 em ≈ 0.79 × `font_size`), so 58 at 1080×1920 reads like a ~40 px caption; about 80 gives a phone-readable full-speech caption, and a 26-character line is then about 860 px wide. Check a short test render before choosing a size; Studio's CSS preview does not show this difference.

Without word timings, a source segment can be mapped only when kept in full. If a cut crosses it, supply word timings or explicit timeline items. Empty enabled captions and overly long manual cues cause actionable execution errors.

Transcript mapping keeps a word when its midpoint falls inside a kept clip. Whisper often stretches a word over the pause after it (or starts the first word early), so cutting that pause can silently drop the word from the captions. After choosing cuts, list the words around each boundary; correct a stretched word's start/end in `cleaned.json` from the audio energy and log it as a timing correction. The automatic grouping (`max_chars` × `max_lines`, at most 2.5 s) can also leave a one-word cue, split a compound word across cues, and its greedy line wrap can split one inside a cue ("phi hệ / thống"). For a finished edit, supply balanced `captions.items` (break at sentence ends and commas, never inside a compound such as "doanh nghiệp", capitalize only a real sentence start or the first word after a cut). Keep `transcript_ref` so Studio's transcript tools still work.

A line break (`\n`) in an item or Studio cue text is kept as an explicit line break; each line still wraps greedily at `max_chars`, and the total must fit `max_lines`. Export, Studio preview and the Studio save check use the same rule (`caption_lines` / `captionLines`). Choose a balanced break with both lines within `max_chars` to control where a two-line caption splits.

## Audio

```json
{
  "voice_gain":1.0,
  "music":{"path":"assets/music/background.mp3","gain":0.08,"ducking":true}
}
```

Set `music: null` to omit music. Gains are linear multipliers. Music loops to the output duration and can duck against voice; sources without audio receive silence. No music or SFX library is bundled.

Optional voice cleanup and loudness, both export-only (Studio preview plays the original sound). Omit a key for off; do not write an "off" value:

- `denoise`: `light` (high-pass plus FFT noise reduction, about 6 dB less steady room noise) or `strong` (adds a gentle gate that lowers the room about 12 dB more between phrases; very quiet speech can be softened too). Applied to the source voice before `voice_gain`, never to music or SFX.
- `loudness_lufs`: integrated loudness target for the final mix, -24 to -9. Use -14 for TikTok/Reels/Shorts. Single-pass `loudnorm` with a -1.5 dBTP ceiling; expect the result within about 1 LU.

Choosing cleanup is an audio treatment decision like music; propose it when the source has hiss, hum or uneven levels.

Optional `sfx` places one-shot sounds on the output timeline:

```json
"sfx": [{"id":"whoosh-01","path":"assets/audio/whoosh.wav","timeline_in_frame":120,"timeline_out_frame":138,"gain":0.6}]
```

Each sound starts from its beginning at `timeline_in_frame` and is cut at `timeline_out_frame`; a range longer than the file ends in silence. `gain` is 0-4. SFX are mixed after music ducking, so they never duck the music, and the voice keeps its level. Use only files the user supplied or chose from a source whose license they accepted; record its credit like other assets. Studio keeps a sound on the same source moment when clips are trimmed, reordered or sped up, and drops it when that moment is cut away. A lock fingerprints only the sounds overlapping its range.

## Revision rules

The `revision` command clones a plan/config and records feedback, **it does not interpret or apply the prompt**. The IDE agent reads the feedback and edits the new plan. Once a video is exported, make a new revision for changes. `render --dry-run` writes an inspectable FFmpeg command/filtergraph and captions, without encoding video. It is not a content review.

## User choices

Read `core/interaction.md`. Every revision has `decisions.json`: setup answers from the user, the chosen concrete edit proposal, actual reply text and history. New jobs start pending; revisions inherit explicit setup answers and start with a pending edit proposal. Profile defaults are preparation values, not user selections.

Local transcription requires selected setup answers with `transcription: true`. Rendering requires selected setup/proposal, matching style/domain, output/caption settings and matching plan/config hashes. Editing the plan/config after recording the proposal requires a new matching selection. `--dry-run` prepares work without exporting while choices are pending. The CLI cannot authenticate a quoted reply or interpret prose answers; the agent must genuinely ask, wait and apply the user's choices.
