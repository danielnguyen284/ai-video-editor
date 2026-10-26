# Implementing the selected visual-keyword edit

Read [the edit-plan schema](../../../../core/schemas/edit-plan.md) and [visual contracts](../../../../core/schemas/visuals-and-footage.md). Examples below are technical illustrations, not a selected user edit. All frame intervals refer to the output timeline after cuts.

## Opening title and image layers

Create one or two short title lines after the user confirms the wording. The text helper reads a UTF-8 file; intentional newlines give up to two lines. It uses the requested size without automatic wrapping or fitting. Inspect the generated PNG during asset preparation; shorten the text, split a line or adjust the size if it clips. Example from the workspace root:

```powershell
# Write the chosen title into this text file first.
.\.venv\Scripts\python.exe skills/styles/visual-keyword/scripts/render_text.py --text-file jobs/JOB/assets/title.txt --output jobs/JOB/assets/visuals/title.png --width 920 --height 220 --font-size 72 --background '#D91B34' --color '#FFFFFF' --outline-width 0
```

By default the background is transparent, the text white with a dark outline, and the font Windows Arial Bold. Supply `--font-file` on another system. Use separate PNGs for separately colored title lines, or yellow keyword text with `--color '#FFE24A'`. Generated typography is a local code-rendered asset; photos/illustrations are sourced separately.

Place the title image from frame 0 for the selected duration. The PNG is immediately visible; it does not fade in from transparent. Example layers at 1080×1920 and 30 fps:

```json
[
  {"id":"opening-title","type":"image","path":"assets/visuals/title.png","timeline_in_frame":0,"timeline_out_frame":90,"x":60,"y":1000,"width":920,"height":220,"fit":"contain"},
  {"id":"illustration-01","type":"image","path":"assets/visuals/approved-image.jpg","timeline_in_frame":120,"timeline_out_frame":210,"x":60,"y":850,"width":920,"height":560,"fit":"contain"}
]
```

Change these rectangles to the selected layout and output size. They are not guaranteed TikTok safe zones. Use `contain` for an article/chart whose labels must stay visible. A full-frame `image` or `video` layer can cover the presenter while the source audio continues; layer video audio is muted. The renderer does not automatically find, generate or animate pictures.

## Selective keyword cues

For one consistent white/outlined keyword style, enable captions and fill **explicit items**, for example:

```json
{
  "enabled": true,
  "font_name": "Arial",
  "font_size": 96,
  "margin_v": 520,
  "max_chars": 16,
  "max_lines": 2,
  "items": [
    {"timeline_in_frame":120,"timeline_out_frame":180,"text":"TỪ KHÓA"},
    {"timeline_in_frame":300,"timeline_out_frame":360,"text":"Ý CHÍNH"}
  ]
}
```

Remove `transcript_ref` from this concrete plan for clarity. `items` takes precedence over the transcript; keep it explicit, including in revisions. Gaps between cues are intentional. Never fill the array with all transcript words. Recalculate these frame intervals after every cut/reorder; they are not remapped automatically like source word captions.

For a different color, size or position per cue, create transparent keyword PNGs with the same helper and time them as image layers. If all text uses PNGs, set `captions.enabled: false`, record setup `captions: false` (no ASS caption track), and describe the chosen title/keyword layers in `visuals` and the edit-plan summary. If also using selected ASS keyword cues, set captions to true and supply those items. The current renderer requires at least one cue for an enabled ASS track. Do not invent a caption-mode plan field.

## Propose, record and export

The concrete proposal lists title wording/duration, each keyword, the actual illustration assets with source/credit, positions and frame intervals. Resolve sourcing and audio choices separately. Ask about ambiguous terms rather than treating a similarly spelled financial ticker as certain. Record the user's actual choice after implementing it, then render with the normal CLI. This package does not change an existing exported revision.
