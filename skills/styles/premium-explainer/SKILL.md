---
name: premium-explainer
description: Apply a clear, restrained explainer edit across subjects, with readable captions, deliberate cuts and voice-first audio. Use when the chosen project style is premium-explainer.
---

# Premium explainer

Read `skill.json` for the parameter defaults used by profiles. The values are starting points; a concrete user request may adjust presentation.

For a TikTok brief, read [the TikTok editing guide](../../../core/platforms/tiktok.md). Apply its opening, pacing and interface-clearance guidance while retaining this style's restrained treatment. The user's primary platform guides suggestions; it does not select cuts, music or extra visuals.

For every edit request or revision feedback, follow [style learning](../../../core/style-learning.md): extract supported reusable treatment rules, merge them here or into a relevant reference, and update related documentation and versioned profiles. Keep one-video instructions in the job and preserve its locked choices. This maintenance is already authorized; no new rule or duplicate text is needed when the skill already covers the request.

## Editor

Build around a complete opening point and understandable progression. Remove false starts, repeated takes and dead air where timestamps support the cut. Preserve negations, caveats and setup needed by later statements. Use the source speaker's actual words for the hook.

Prefer meaningful visual changes over a fixed effects-per-minute quota. For a fixed camera, start with consistent framing; choose crop only if the subject stays visible, otherwise retain the frame with padding. Do not require vision analysis for every video.

## Animator / Finisher

Use high-contrast captions, up to two lines, with sufficient lower margin for a vertical short. Defaults target 1080x1920; adjust font/margins when changing resolution. Group words into short cues rather than filling the screen with paragraphs.

For TikTok, propose a caption position that leaves room for platform controls as well as existing source titles. The numeric defaults are a starting layout, not a guaranteed safe zone. If the source already has captions, offer retaining those or adding new ones in a specific clear area; do not automatically place a second caption band underneath them.

Offer flat charts and simple cards when the brief needs them; the user selects whether to add them. Chart values/units come from the domain skill and research. A source citation belongs with externally sourced data.

Available motion templates are MetricCard, BarChart (1-8 nonnegative values) and LowerThird. Use `render-motion` to produce transparent ProRes assets and place them as timed FFmpeg video layers. Static logos/images and B-roll can be layered directly. Keep captions above visual layers, keep faces legible, and let the user select placement/timing. Read [visual and footage contracts](../../../core/schemas/visuals-and-footage.md) when constructing specs or overlays. Arbitrary animation, animated punch zoom and continuous face following are not implemented.

## Sound Designer

Keep speech in front. Use a low music gain, with ducking when music is included. Silence is acceptable if there is no supplied music. Avoid adding effects just to make the edit seem busier.

Export and let the user judge pacing/design through feedback. This skill does not create a separate review stage.
