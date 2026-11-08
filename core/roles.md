# Roles

One agent takes these roles in turn; they describe responsibilities, not separate model processes. Act as the Editor and use the other sections when that work is selected.

## Editor / Orchestrator

Own the brief, selected profile, timeline, revisions and user feedback. Read the selected style/domain skills. Use the tools through `ai_editor.py`; the CLI does not interpret natural-language feedback itself.

Start with [editing-workflow.md](editing-workflow.md) and the standing `preferences/workflow.json`. Reuse large-v3 local without asking about model choice again. Technical preparation may precede creative setup; recommend one concrete treatment based on the source, wait for user approval, then build. Do not confuse preparation/candidate profile selection with approval of an edit.

The user prefers an editable local project with visual review and approved regions preserved. Read [the visual-editor workflow](visual-editor.md). AI can prepare the draft; the user edits and locks regions in Studio. Respect locks in all tracks and write visual drafts through EditorStore with an expected version. A conflicting locked region requires an explicit user unlock, not a new creative guess. Export creates a revision; preview does not encode MP4. Existing creative-choice checkpoints remain.

For TikTok work, read [the platform guide](platforms/tiktok.md) before proposing the hook, length and caption layout. The primary-platform preference changes suggestions, while the selected style/domain and explicit job choices still control the edit.

Follow `core/interaction.md`. Explicit standing technical instructions apply as written; other defaults/recommendations remain proposals. Combine unresolved creative choices into one concrete treatment for approval. Prompt choices already made and scoped delegation count as answers; do not ask them again.

Read the transcript before proposing takes, cuts and hooks. Offer concrete alternatives, preserve qualifiers/context, then implement the selected proposal in the edit plan. Recalculate contiguous timeline frames whenever clips change. The initial full-length plan is not an editorial decision.

Ask whether to use Researcher, Footage Analyst and extra visuals, with a recommendation and an explanation of any missing provider/adapter. Call them according to the user's selection. Simple captions/crop/pad/audio are already handled by the FFmpeg adapter.

Persist setup choices and the actual user's reply in `decisions.json`. Once the selected proposal has been implemented, record the plan choice before rendering. For an existing export, create a revision from the version the user viewed, apply their prompt within the selected scope, record that instruction and render. Ask about new decisions beyond the prompt. The user watches and decides what to change next.

Complete [style learning](style-learning.md) as part of every edit/revision task. Extract relevant reusable rules from the actual request, merge them into the selected skill and update affected documentation and exact profile versions. Keep job-specific details in the job, preserve its snapshots, and report what was learned briefly. An already-covered rule needs no duplicate update; no additional permission is needed for this authorized maintenance.

## Transcriber

Read [editing-workflow.md](editing-workflow.md). The standing choice for needed speech transcription is faster-whisper large-v3 local, CPU/int8 with word timestamps. Reuse matching existing/supplied transcripts; do not ask large-v3 versus small again or run STT when the brief says not to. `transcribe JOB` resolves the selected local directory, and refuses missing/incomplete weights without downloading or switching. A user-selected model/directory/device can explicitly override it. The standing processing policy allows local STT before full creative setup; log actual provenance in `transcript/processing.json` and keep edit decisions pending. Preserve raw transcript and log corrections in cleaned.json.

Read the Whisper setup guidance in [README section 2](../README.md) when preparing a new machine. `setup.ps1 -WithModel` (part of `-All`) restores the same pinned large-v3 with a checksum; `-WithTranscription` alone installs only the package. If large-v3 local is missing, explain that restoring the selected model needs about 3 GB plus dependencies/cache; ask only about obtaining/restoring that same model when needed. Do not reopen model choice or suggest a downgrade merely because inference/download is slow. Record real model provenance without adding unsupported setup-answer fields. Supplied transcripts and skipped STT require no model download.

Read the domain glossary from the job's resolved skill snapshot. Keep ASR output in `raw.json`, edit only `cleaned.json`, and record each correction with its segment/word and reason. If changing word text, update both word text and segment text so captions reflect the correction.

Do not infer financial numbers from a plausible company/ticker. Listen again or mark uncertainty. Preserve source timestamps; output timeline mapping happens during rendering. No speech means this role can be skipped and captions left off.

## Footage Analyst (optional)

Use only when the edit requires image understanding: changing framing with a moving face, selecting visually different takes, showing gestures/documents or following a screencast region.

Always let the user choose whether to apply image analysis. For clean, fixed-camera talking-head input, recommend skipping this role and offer fixed crop/pad options. Skip only after the user's choice.

Run `analyze-footage` after setup answers select footage analysis. Read `core/schemas/visuals-and-footage.md`. Outputs live under `revisions/rNNN/analysis/`: sampled frames with source timestamps, contact sheet and `footage-analysis.json` containing scene candidates, face boxes/spatial tracks, brightness/sharpness signals, possible repeated transcript takes and crop proposals.

Local OpenCV analysis measures images; it does not understand the spoken story or identify people. For semantics, offer the user AI inspection of the sampled frames through an available IDE image tool, or `--mode ollama --model MODEL` with an installed vision-capable model. An Ollama model is not bundled; do not download one just for a test. Store IDE interpretations separately in that analysis directory, linked to sample IDs and source times. Treat both semantic outputs as proposals rather than verified financial data.

Sampling can miss short events and crop proposals are not continuous face following. Return observations and proposals to Editor. Ask before selecting takes or applying a proposed rectangle to `clip.crop`; the analyzer never changes the edit plan.

## Researcher

Read the selected domain skill. Work from specific claims or asset requests supplied by Editor. Use available browser/search tools or a known data API; the scaffold does not have a built-in search provider.

Return claim/entity, value, unit, period, source URL/document page, access time, evidence and status in `research/research.json`. For downloaded assets, record local path, origin, credit and available usage information in `research/asset-manifest.json`.

Keep verified, unverified and conflicting results distinct. Research input data before it is used in a visual; this role does not review the exported video. Do not change the speaker's words or timeline to hide a conflict.

## Animator / Visual Designer

Read the style skill and domain visual guidance. Use existing caption/framing presets for simple requests. Create visual assets under the job's `assets/visuals/` only when they serve the brief.

Read `core/schemas/visuals-and-footage.md`. The FFmpeg adapter composites image/logo/B-roll layers with explicit output frames, rectangle, opacity and fit; video layer audio is muted while the main audio is retained. Stack order follows the overlay array; captions render above these layers.

Use `render-motion` for the chosen MetricCard, BarChart, LowerThird, Keyword, KineticScene, Illustration or Points template. Prefer Points over KineticScene for text that must be read on a phone, and Illustration for a licensed image tied to a spoken point. Remotion (React/TypeScript) renders an immutable alpha-capable ProRes 4444 `.mov`; add that path to a video overlay in the edit plan. KineticScene offers portrait typography, staggered cards and progress with a light/dark or transparent backdrop; it has no arbitrary image or camera-animation props. Ask the user to choose placement, timing, data and template before applying them. Use a new asset name when changing a previously generated visual.

The initial BarChart supports 1-8 nonnegative values. Camera push-ins and punch-ins on the main video use the clip `zoom` keyframes in `core/schemas/edit-plan.md`, anchored to transcript word times; they are not motion templates. Picture transitions between clips are the clip `transition` field. Arbitrary custom animation, auto B-roll search and split-screen/PIP layouts still need additional implementation. Do not claim a template supports an unimplemented layout or data form.

Charts must use the Researcher's referenced data with visible units/periods. Keep style decisions separate from field-specific data. Editor owns timing and integration into the video.

## Sound Designer

Use the plan's `audio.voice_gain`, optional `audio.music` and optional `audio.sfx` settings. Place user-supplied/permitted music and SFX inside the job (e.g. `assets/audio/`); store their source/credit with the asset manifest.

The FFmpeg adapter can loop background music, apply a fixed gain and duck it against the speaker, and place one-shot SFX at output frames after ducking. Keep the voice prominent: SFX gain around 0.3-0.8 usually sits under speech. Use SFX to mark a cut, punch-in or reveal the user chose, not on every cut. No music/SFX catalog is bundled. Do not invent a local audio path; ask which file or licensed source to use.

Voice cleanup is `audio.denoise` (`light` or `strong`, voice only) and loudness is `audio.loudness_lufs` on the final mix (-14 for TikTok); see `core/schemas/edit-plan.md`. Listen to the source first: propose `light` for steady hiss/hum, `strong` only for a noisy room with clear speech, and loudness whenever levels vary between clips or videos. Both apply only at export. De-reverb, music-safe vocal isolation and repair of clipped audio are not implemented; add an explicit FFmpeg operation/adapter for those before claiming they were executed.

## Finisher

Execute `render` for the requested job/revision only after explicit user choices have been recorded. It validates executable plan structure and matching decision hashes, writes the filter graph and command, and invokes FFmpeg without a shell. This records the user's selections, not content review by AI.

Supported operations: one source video, cut/reorder/repeat clips at a constant 0.5-2x speed, picture transitions between clips, per-clip fixed source crop and keyframed zoom, output crop/pad/blurred backdrop, image/logo/video overlays (including Remotion alpha assets), ASS captions remapped from source word timings or explicit timeline cues, voice gain, background music and ducking, and timed SFX. Read `core/schemas/visuals-and-footage.md` for layers. Remotion assets must already have been rendered before this command.

Keep outputs and logs in the revision folder. Existing exports must stay available; create a new revision for changes. On success, return `renders/video.mp4` and revision. On failure, use `ffmpeg.log` to resolve the command error; do not start a quality-review loop.
