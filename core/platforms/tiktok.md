# TikTok editing guide

Use for TikTok briefs and when preparing suggestions for this user's primary platform. Platform changes presentation; the chosen style still controls the visual language and the domain skill controls terminology and evidence. Follow [interaction.md](../interaction.md) for unresolved decisions.

## Brief and structure

- Start with the audience and the one point this clip should communicate. For an ordinary organic post, suggest an explainer or commentary treatment; do not assume an ad, sales pitch or trend format.
- After reading the transcript, offer the original opening and, when useful, an alternative hook using an actual source sentence with source timestamps. Aim to make the subject clear in roughly the first 1–3 seconds; this is an editorial target, not a platform requirement or a promise of reach.
- Propose a short complete cut and a fuller version when the content supports both, with actual ranges and estimated lengths. Do not force every clip under 60 seconds. A user request to keep most content takes precedence.
- Remove pauses, repetitions and detours only within the selected scope. Retain the explanation needed for the payoff. In finance, keep negations, conditions, dates, units and the basis of comparisons attached to the claim.
- Let a change in point motivate a cut or visual. Premium-explainer remains restrained; TikTok does not automatically mean constant zooms, sound effects or word-by-word captions.
- End on the completed point. Offer a CTA, alternate ending or loop only when useful, and ask before adding it or reordering source material to create it.

## Vertical frame and captions

- Suggest 9:16. Offer 1080×1920 when the source supports it and retaining native resolution when it does not; explain upscaling before offering it. Resolve pad versus crop with the user, including charts and existing titles that a crop could remove.
- Follow the selected text treatment: premium-explainer can use phrase captions; visual-keyword uses an opening title and sparse selected words with gaps, without full speech captions. Suggest readable, high-contrast text with at most two lines. Scale the font and `margin_v` to the chosen output resolution. Keep a ticker, number and unit together where possible; shorten cues rather than shrinking dense text until it becomes hard to read.
- Leave room for the right-side interaction buttons and the lower account, description and sound rows. Keep the essential text, face and chart labels clear. Safe areas vary with the interface and post/ad layout; no fixed pixel rectangle guarantees clearance on every device.
- Before constructing the plan, identify existing burned-in captions, titles and watermarks. If they compete with the new captions, offer concrete placements or keeping only the existing captions. Do not automatically stack new captions at the very bottom or reuse a previous video's coordinates. Tell the user when the selected placement may overlap TikTok UI; retain an explicit choice unless they change it.
- The current ASS renderer supports font, size, vertical margin and phrase wrapping, with fixed horizontal margins. It has no automatic TikTok UI detector, arbitrary caption positioning or animated word highlighting. Offer only placements the renderer can produce; read [edit-plan.md](../schemas/edit-plan.md) for supported fields.

## Visuals and sound

- Offer original footage plus captions as a simple treatment, with images, B-roll or supported Remotion cards as optional alternatives tied to a specific explanation. Do not add footage merely to meet an effects quota.
- Keep voice intelligible. Ask whether to use voice only, supplied music or music proposals. If chosen, use a quiet mix and ducking. Provide required attribution with the export; do not assume any track is usable just because it appears in another TikTok video.
- Editing does not include publishing or choosing a cover, post description or hashtags. Prepare those only when requested; a cover is a separate deliverable, not an unimplemented edit-plan field.

## Concrete proposal and delivery

Include the opening sentence and its source range, kept/removed ranges, expected duration, caption placement, chosen visuals and audio in the proposal. Record the user's selection through the existing decision workflow. Export with FFmpeg and return the revision for the user to watch; no AI review role or automatic re-edit loop is added.

The preference in `preferences/default.json` guides agent suggestions only. The CLI does not read it as an instruction to select TikTok, change a plan or resolve pending choices. Existing jobs retain their snapshots and selected decisions.

## Sources and scope

Consulted 2026-10-18:

- [TikTok creative best practices](https://ads.tiktok.com/resources/help/article/creative-best-practices?lang=en): vertical presentation, an early proposition and captions. This is advertising guidance; use it as context, not as mandatory organic-post rules or a reason to change the selected style.
- [TikTok in-feed ad specifications and safe zones](https://ads.tiktok.com/resources/help/article/tiktok-auction-in-feed-ads?lang=en-GB): safe areas vary with dimensions, caption length and additional formats. For an ad brief, check the current placement template; do not present ad-specific limits as universal organic-upload limits.
