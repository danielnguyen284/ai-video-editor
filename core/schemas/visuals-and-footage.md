# Visual layers, motion assets and footage analysis

All operations follow `core/interaction.md`. Ask about visual/analysis choices first; `render-motion` and `analyze-footage` require recorded setup answers. The final edit plan is selected after generated assets and chosen crop/layer changes have been applied. The examples below are illustrative, not user answers or verified finance data.

## Image, logo and B-roll layers

Add layers to `edit-plan.json` under `overlays`. Timing is in **output frames**, start inclusive/end exclusive. Paths are relative to the job root and must stay inside it.

```json
[
  {
    "id":"company-logo",
    "type":"image",
    "path":"assets/visuals/logo.png",
    "timeline_in_frame":30,
    "timeline_out_frame":120,
    "x":80,"y":160,"width":200,"height":200,
    "fit":"contain","opacity":1
  },
  {
    "id":"supporting-broll",
    "type":"video",
    "path":"assets/visuals/broll.mp4",
    "timeline_in_frame":120,
    "timeline_out_frame":210,
    "x":0,"y":0,"width":1080,"height":1920,
    "fit":"cover","source_in_seconds":1,"loop":false
  }
]
```

- Required fields: `id`, `type`, `path`, frame range, `x`, `y`, `width`, `height`, `fit`.
- `id` uses lowercase letters/numbers/hyphens and must be unique. The rectangle must stay inside the output image.
- `fit`: `contain` preserves the full asset with transparent padding; `cover` fills and crops the layer; `stretch` uses the exact rectangle without preserving aspect.
- `opacity`: optional linear alpha 0–1, default 1. PNG alpha and alpha-video are retained.
- `type: image`: static PNG, JPEG, WebP, BMP or TIFF. Convert SVG to a raster asset before use. Image layers repeat for their selected duration; they do not accept loop or a nonzero source start.
- `type: video`: optional `source_in_seconds` (default 0) and `loop` (default false). Without looping, the asset must cover the entire selected duration. Short assets fail explicitly instead of silently freezing. Video layer audio is muted; the selected main voice/music continues.
- Later array entries render above earlier entries. ASS captions render above all visual layers. Video layers do not change the source/output time mapping of the main clips.
- B-roll is a video layer; it may cover the frame or appear in a smaller rectangle. This adapter does not search for or download B-roll.
- Existing exports and generated assets are preserved. Final render manifests record hashes of visual files used by the export.

## Remotion assets

The Node project lives in `motion/`; `package-lock.json` locks dependencies. The rendering engine is Remotion/React/TypeScript. It uses an installed Chrome/Edge when detected, or Remotion's Chrome Headless Shell otherwise. Set `AI_EDITOR_BROWSER` to an executable path to choose a browser explicitly; that browser is launched headless for rendering with temporary storage.

Create a request in the job, e.g. `assets/metric-request.json`:

```json
{
  "template":"MetricCard",
  "width":720,"height":400,"fps":30,"duration_frames":90,
  "props":{
    "title":"Sample metric",
    "value":"42",
    "subtitle":"Illustrative data only",
    "source":"Source: example fixture",
    "accent":"#A6EDBC"
  }
}
```

```powershell
.\.venv\Scripts\python.exe ai_editor.py render-motion JOB metric-01 --revision r001 --spec assets/metric-request.json
```

Output: `assets/visuals/metric-01/motion.mov`, its request, render log and manifest. Assets use ProRes 4444 + alpha (`yuva444p10le`) so FFmpeg can composite them without a background rectangle. Width/height must be positive even integers; duration must be at least 24 frames. Use a unique asset name when changing the design/data.

Available templates:

| Template | Props |
|---|---|
| `MetricCard` | Required `title`, text `value`; optional `subtitle`, `source`, `accent` |
| `BarChart` | Required `title`, `data: [{label, value}]` with 1–8 nonnegative finite values; optional `unit`, `source`, `accent` |
| `LowerThird` | Required `title`; optional `subtitle`, `accent` |
| `KineticScene` | Portrait typography/cards/progress; see contract below |

`accent` is a six-digit hex color. These are fixed templates; add a component and validator to support a different chart form or animation. They do not verify business data. The selected domain/research workflow supplies evidence for real claims.

### KineticScene

An original template for kinetic-motion and infographic inserts in talking-head-pro. This animates an overlay asset, not the source crop/camera. No example media is bundled. Use the usual request envelope with `template: "KineticScene"`.

Dimensions must be even, at least 320×480, with width/height between 0.5 and 0.8. Duration must be at least `2 * fps` frames. The 720×1280 internal design canvas scales to fit; its margins are a starting layout, not a guaranteed TikTok safe zone.

| Prop | Contract |
|---|---|
| `title` | Required nonempty text, up to 60 characters |
| `emphasis` | Optional nonempty text, up to 36 characters, larger/accent color |
| `subtitle` | Optional nonempty text, up to 90 characters |
| `source` | Optional nonempty credit/context text, up to 100 characters |
| `theme` | `light` (default) or `dark` |
| `transparent` | Boolean, default false. True removes the backdrop; text/cards/progress remain |
| `accent` | Optional six-digit hex, default `#E5A137` |
| `layout` | `stack` (default) or `grid` |
| `cards` | Optional 1–4 objects with required `label` and optional `detail`. Stack character limits: 36/48; grid: 24/38. Omit for text-only scenes |
| `progress` | Optional finite number 0–1; animate from zero to this fraction. Omit to hide. A visual indicator, not verified data |

All supplied text must be nonblank on one input line; wrapping is automatic. Long strings reduce type size; prefer concise text rather than using the ceilings as targets. Invalid values and unknown props/card fields are rejected. There are no image, voice, icon, font, arbitrary position or per-card timing props.

Animation uses asset-local frames: heading fade/slide, emphasis scale, card reveals from 0.4s staggered by 0.18s, progress from 0.6s with a final hold, and a short exit fade. The asset must cover the selected overlay duration; do not loop merely to extend it. ProRes 4444 retains alpha; the backdrop is opaque throughout when `transparent: false`, unused pixels stay transparent when true.

Read [the kinetic implementation guide](../../skills/styles/kinetic-motion/references/implementation.md) for request/storyboard and CLI usage. These props belong in the motion request, never the edit-plan overlay. Full-frame scenes can cover a video while its selected narration continues. Audio-only/script-only job creation remains unsupported; `new-job` needs video.

### Placing a rendered asset

Place the rendered asset as a video layer:

```json
{
  "id":"metric-layer","type":"video",
  "path":"assets/visuals/metric-01/motion.mov",
  "timeline_in_frame":60,"timeline_out_frame":150,
  "x":80,"y":500,"width":920,"height":512,
  "fit":"contain","opacity":1,"source_in_seconds":0,"loop":false
}
```

Choose the duration in seconds consistently if the motion asset and main video use different fps. In this example both are 30fps and 90 frames. Default entry/exit animation belongs to the template; looping a card may repeat its entry/exit, so loop only if the user chooses that behavior.

## Footage analysis

After the user selects footage analysis in setup:

```powershell
.\.venv\Scripts\python.exe ai_editor.py analyze-footage JOB --revision r001 --mode local --interval 1 --max-samples 120
```

The report is `revisions/r001/analysis/footage-analysis.json`, with `frames/` and `contact-sheet.jpg` beside it. Everything refers to **source time**, before cuts/reordering.

Local OpenCV analysis returns:

- Sample timestamps and paths; frames are at most 640 pixels wide.
- Approximate scene boundaries from histogram changes.
- Haar face boxes and simple spatial track IDs between sampled frames. These are not identity recognition or continuous face tracking.
- Brightness and Laplacian sharpness measures. A low value may mean a flat/low-texture image, not necessarily bad focus.
- Per-sample/per-scene crop proposals based on the largest detected face, or center framing if no face is detected.
- Repeated transcript candidates by text similarity when a cleaned transcript exists. Similar statements may be intentional; the user chooses takes.

Sampling is capped at 600 frames. If the duration exceeds `interval * max_samples`, the sampler spreads frames over the source with a larger reported interval. Short events can be missed. Analysis never modifies the edit plan and existing reports in a revision are not overwritten.

Offer the user the report's proposed source rectangles. To apply a selected fixed rectangle, place only `x`, `y`, `width`, `height` into the relevant clip's `crop` field and then record the selected edit proposal. Crop reports do not generate an automatic moving zoom.

## Semantic image understanding

Two options are available after the user chooses semantics:

1. The IDE agent opens selected sampled frames/contact sheet using an available image tool, then records observations in `revisions/rNNN/analysis/semantic-notes.json` linked to sample IDs/source times. There is no separate API key requirement for this agent workflow.
2. Use an installed vision-capable Ollama model through the API:

```powershell
.\.venv\Scripts\python.exe ai_editor.py analyze-footage JOB --revision r001 --mode ollama --model YOUR_INSTALLED_VISION_MODEL --semantic-samples 12
```

The default endpoint is `http://127.0.0.1:11434/api/chat`; `--vision-endpoint` selects another Ollama-compatible chat endpoint. Explain where images will be sent before selecting a remote service. Model weights are not bundled or downloaded by this CLI.

Sample descriptions, visible text/actions and editing suggestions are marked `model-proposal-unverified`. They must not become verified finance claims. Semantic calls cover an evenly spaced subset of the local samples, not every source frame. If the service fails, a partial report is retained with the failure and the command returns an error; it does not silently claim semantic analysis succeeded.

Tests use synthetic media and a local fake Ollama server. A real vision model and real user video have not yet been used in validation.

## Technical references

- [FFmpeg overlay filter](https://ffmpeg.org/ffmpeg-filters.html#overlay)
- [Remotion programmatic rendering](https://www.remotion.dev/docs/renderer/render-media)
- [Remotion alpha video settings](https://www.remotion.dev/docs/transparent-videos)
- [Ollama vision API](https://docs.ollama.com/capabilities/vision)
