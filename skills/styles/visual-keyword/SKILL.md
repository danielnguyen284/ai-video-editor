---
name: visual-keyword
description: Edit vertical explainers with an immediate opening title, sparse large keywords and supporting images instead of full speech captions. Use when the selected project style is visual-keyword or the user requests this treatment.
---

# Visual keyword

Use this as a separate style from premium-explainer. Read `skill.json` and [the TikTok guide](../../../core/platforms/tiktok.md). For the supplied reference, read [sample-analysis.md](references/sample-analysis.md); for executable layers and text assets, read [implementation.md](references/implementation.md).

For every edit request or revision feedback, follow [style learning](../../../core/style-learning.md). Extract reusable guidance about titles, selective text, illustrations, pacing or sound from the actual request; refine the relevant rule and related documentation with matching package/profile versions. Keep this style separate from full speech-caption treatments, keep local media decisions in the job, and preserve its snapshots. Routine learning updates are already authorized; do not add duplicate rules.

## Editor

- Selecting this style means an opening title, selective large keywords and relevant illustrations. Do not ask again whether the user wants full speech captions unless they request a different treatment. Confirm the actual title, keywords, image choices and timings in the concrete proposal.
- Use the transcript to understand the story, select concepts and map timing. It is working material, not the on-screen text track. Never enable automatic full-transcript captions for this style.
- Put a short title over the opening footage from output frame 0. Suggest one or two lines that communicate the point; choose its wording and duration with the user. Preserve qualifications, especially for financial claims. A title may summarize, but must not exaggerate what the source supports.
- Select a few strong concepts, names or numbers at changes of idea. Prefer 1–4 words per cue; leave stretches of speech without any new text. Do not turn every sentence or every spoken word into a keyword.
- Show a keyword when the speaker introduces that concept. Keep it on screen long enough to read without rushing the narration. There is no fixed quota of effects or illustrations per minute.
- Preserve the selected order and cutting scope. Show the proposal as source ranges plus output title/keyword/image intervals and estimated length; resolve all new creative decisions before export.

## Text and layout

- Suggest bold sans-serif text with strong contrast and a dark outline. Keyword defaults target 1080×1920: Arial Bold through the ASS renderer, size 96, at most two short lines, vertical margin 520. Scale these to output size and the subject's position; they are not universal safe coordinates.
- The reference uses white keywords, occasional yellow emphasis and red/white opening title strips. Treat these as a starting palette to propose, not colors that override a user's brand.
- Separate title, keyword and illustration areas. Avoid covering eyes, a chart's relevant labels or existing source text. Leave space for TikTok controls. If the source already contains full captions/title bands, show the user the available placement/crop choices instead of stacking more text automatically.
- A keyword should stay understandable by itself: keep a number with its unit, and a ticker distinct from a similar ticker. Use the domain skill for wording and uncertainty.

## Illustrations and sound

- Propose actual assets tied to the point: an image of the subject, a relevant scene, an article excerpt or a chart. Use an inset when it supports the presenter; use a full-frame insert when the image needs room to read. Preserve original narration beneath it.
- Resolve asset sourcing: user-supplied images, researched assets, or generated conceptual illustrations. Explain provider availability before offering generation; do not require an API key for the local render. Record source/credit and distinguish a conceptual illustration from evidence. Do not silently copy assets, statistics or branding from the reference.
- Do not add an illustration merely to fill every pause. Leave the speaker visible when their explanation carries the point. The selected domain controls research requirements for claims and numbers.
- Resolve audio separately. Selecting this visual style does not choose music or SFX. If music is selected, keep it behind speech with ducking.

## Execution

Use existing FFmpeg image/video layers and explicit `captions.items` for sparse keyword cues. The package's empty `items` default prevents an accidental fallthrough to the full transcript. The initial job still starts with captions disabled; the editor must implement the selected cues before enabling them.

Use static PNG title layers for visibility at frame 0. The supplied `scripts/render_text.py` creates title strips or transparent keyword PNGs with FFmpeg, without new dependencies. PNG keyword layers can vary color, size and placement per cue; ASS items share one style. No animated typography is required or automatically installed by this package. Read the implementation reference before constructing assets or a plan.

Export the selected plan and return the revision for the user to watch and prompt. Do not introduce an AI review role or re-edit an existing export without a new revision.
