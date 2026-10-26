# Executable edit plan — starter v1

The CLI supports a **single source video**, cut/reorder/repeat at 1x, per-clip fixed source crop, output crop/pad, image/logo/B-roll layers, Remotion alpha-video assets, ASS captions, voice gain and optional looped/ducked background music. Source-camera zoom animation, SFX scheduling, continuous face following and speed changes are not implemented; unsupported fields fail explicitly. KineticScene animates text/cards/progress inside a pre-rendered overlay asset; see the visual schema, not new main-timeline effect fields.

All source paths are relative to the job root and must stay inside it. The renderer invokes FFmpeg with an argument list, without a shell. The original imported video stays untouched.

The visual editor stores working plans, cue IDs, editable motion requests, history and approval locks outside this schema, under `jobs/JOB/editor/`. It compiles selected cues into supported `captions.items` and renders changed motion specs into video assets before exporting. No editor-only fields belong in the executable plan. CLI export and dry-run also enforce approved visual ranges; see [the editor contract](../visual-editor.md).

## Timeline

- `schema_version`: `1.0`; `job_id`: current job; `revision`: integer matching the `rNNN` directory.
- `config_ref`: `resolved-config.json` in that revision. Its settings and skill files are snapshots taken when the job/revision was created.
- `fps`: positive integer; `duration_frames`: total output frames.
- `export`: `{preset, width, height, fps, fit}`. Width/height must be even; `fit` is `pad` (keep all image) or `crop` (center crop to fill). No automatic moving crop is applied.
- `clips`: ordered objects with unique `clip_id`, `asset_id`, `source_in_seconds`, `source_out_seconds`, `timeline_in_frame`, `timeline_out_frame`, `playback_rate: 1.0`.
- Intervals are start-inclusive/end-exclusive. Output timeline starts at 0, has no gaps/overlaps, and the last clip ends at `duration_frames`.
- At 1x, source seconds times fps must match output frame duration within half a frame. Set source boundaries to frame-aligned positions when possible.
- `overlays`: ordered image/video layers. See `core/schemas/visuals-and-footage.md` for exact fields, timing and transparency behavior.
- A clip may contain `crop: {x, y, width, height}` in source pixels. This fixed rectangle is applied before output sizing; it must stay inside the displayed source dimensions. The analyzer can propose a rectangle, but the user selects whether to apply it. Source rotation metadata is reflected in the dimensions reported by `probe`.

Example: keep source 8–10s, then 2–3s at 30fps:

```json
[
  {"clip_id":"clip-001","asset_id":"raw-001","source_in_seconds":8,"source_out_seconds":10,"timeline_in_frame":0,"timeline_out_frame":60,"playback_rate":1.0},
  {"clip_id":"clip-002","asset_id":"raw-001","source_in_seconds":2,"source_out_seconds":3,"timeline_in_frame":60,"timeline_out_frame":90,"playback_rate":1.0}
]
```

Set `duration_frames` to 90. A reference to output second 2.5 now points to source second 2.5 in the second clip, not source second 10.5.

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

Style fields: `font_name`, `font_size`, `margin_v`, `max_chars`, `max_lines`. Values are in output pixels/characters, not percentages; adjust for a different resolution. Default font Arial is present on this Windows machine; use an installed Vietnamese-capable font.

Without word timings, a source segment can be mapped only when kept in full. If a cut crosses it, supply word timings or explicit timeline items. Empty enabled captions and overly long manual cues cause actionable execution errors.

## Audio

```json
{
  "voice_gain":1.0,
  "music":{"path":"assets/music/background.mp3","gain":0.08,"ducking":true}
}
```

Set `music: null` to omit music. Gains are linear multipliers. Music loops to the output duration and can duck against voice; sources without audio receive silence. No music is bundled. Specialized denoise, normalization and SFX placement are not automated in this starter.

## Revision rules

The `revision` command clones a plan/config and records feedback, **it does not interpret or apply the prompt**. The IDE agent reads the feedback and edits the new plan. Once a video is exported, make a new revision for changes. `render --dry-run` writes an inspectable FFmpeg command/filtergraph and captions, without encoding video. It is not a content review.

## User choices

Read `core/interaction.md`. Every revision has `decisions.json`: setup answers from the user, the chosen concrete edit proposal, actual reply text and history. New jobs start pending; revisions inherit explicit setup answers and start with a pending edit proposal. Profile defaults are preparation values, not user selections.

Local transcription requires selected setup answers with `transcription: true`. Rendering requires selected setup/proposal, matching style/domain, output/caption settings and matching plan/config hashes. Editing the plan/config after recording the proposal requires a new matching selection. `--dry-run` prepares work without exporting while choices are pending. The CLI cannot authenticate a quoted reply or interpret prose answers; the agent must genuinely ask, wait and apply the user's choices.
