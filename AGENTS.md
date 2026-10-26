# AI Editor project instructions

Read `README.md` for commands and `core/schemas/edit-plan.md` before changing an edit plan.

## Workflow

- Act as the Editor using `core/roles/editor.md`. Other roles describe responsibilities, not required separate model processes.
- The user selected a local visual editor workflow. Read `core/visual-editor.md` when preparing editable drafts, opening revisions in Studio or modifying an active visual project. Respect approved ranges in `jobs/JOB/editor/locks.json`; use `EditorStore.save` with the expected version for draft edits and never strip locks or overwrite the visual project file to bypass them. User must explicitly unlock a conflicting range. Preview changes do not require an MP4 encode; final export still does.
- For every edit request, edit-treatment answer or revision feedback, follow `core/style-learning.md`: extract supported reusable style guidance, update the relevant skill and related documentation in the same task, and briefly report the scope. This maintenance is already authorized; do not ask for separate permission to edit those files. Keep one-video instructions local, merge duplicates, and preserve recorded job snapshots and creative choices.
- The user's primary platform is TikTok. Read `core/platforms/tiktok.md` when preparing TikTok suggestions and `preferences/default.json` for editorial preferences. This guides recommendations; unresolved framing, length, hooks, captions, visuals and audio still require the user's choices.
- Use `.venv/Scripts/python.exe ai_editor.py` on this Windows workspace. `doctor` reports local dependencies.
- Follow `core/interaction.md`: present choices and wait for the user's answers for every unresolved creative/workflow decision. A suggestion or stored preference is not a selected answer. A clear choice already supplied in the prompt counts; do not ask the same question again.
- Ask in small batches about style, domain, output, footage analysis, transcription, cuts, captions, research, visuals and audio. Then present concrete edit proposals derived from the transcript. The user can select an option, describe their own choice or explicitly delegate a defined decision.
- Resolve the chosen profile from `profiles/`. Read its style/domain `SKILL.md` files. `finance-premium-vi` is an available suggestion, not an automatic user selection.
- Create jobs with `new-job`. Copy source media, preserve the original. The initial plan keeps all footage and disables captions; it is a starting point, not a finished edit.
- Record setup answers and the actual user reply with `decide --stage setup` before transcription. Read the transcript, propose cuts/hooks, wait for any missing decisions, then implement the selected proposal. Preserve `transcript/raw.json`; log corrections in `cleaned.json`.
- Before the first local transcription, explain that `setup.ps1 -WithTranscription` installs the faster-whisper package only; model weights are not bundled in the sharing ZIP. Offer the CLI default `large-v3` (about 3 GB, potentially slow and memory-heavy on CPU), a lighter model such as `small`, or an existing compatible local model directory. Wait for a model choice unless already supplied, record it with the actual reply in the job's intake/setup notes, and pass that model explicitly to `transcribe`. Do not silently change the selected model. Explain download versus inference progress and cache reuse; `doctor` does not verify or download weights. See `README.md` under Whisper.
- Always offer the choice of using or skipping Footage Analyst. Recommend skipping it for a fixed-camera talking-head video, but do not silently decide. Ask about research and extra visuals too; describe unavailable tools/adapters before the user chooses them.
- Use FFmpeg for cutting, joining, framing, captions, image/logo/B-roll layers and audio. Remotion source lives under `motion/` for MetricCard, BarChart, LowerThird and KineticScene assets; check `doctor` and install its dependencies through `scripts/setup.ps1 -WithMotion` before offering it as ready on a new machine. Use `render-motion` only when the user chooses a motion visual. Read `core/schemas/visuals-and-footage.md` before adding layers or motion specs.
- If footage analysis is selected, use `analyze-footage` to produce source-time frame samples, local scene/face/quality signals and crop proposals. Offer local-only analysis, AI inspection of the sampled images in the IDE, or Ollama semantics with an explicitly selected installed model. Local heuristics do not understand the narrative and proposals never edit the plan automatically.
- After implementing the user's selected proposal, record it with `decide --stage edit-plan --summary ... --user-message ...`. Render requires resolved choices matching the plan/config. `--dry-run` can prepare concrete commands before that choice. Do not record a reply the user never gave.
- No AI review role or automatic quality-repair loop. Export the selected edit and return its path/revision for the user to watch and prompt again. Report command failures as execution errors.
- Before changing an already exported video, run `revision --feedback ... --from-revision rNNN` for the version the user watched. That command clones a plan and logs feedback; you must apply the actual changes before rendering.
- Timestamp feedback refers to the watched revision's output timeline, not to raw source time. Recalculate clip mappings, caption timings and duration after edits.
- Revisions carry over explicit setup answers; ask about changes and any new decision. The feedback prompt itself can choose the requested revision. Do not reopen unchanged choices or introduce extra changes without asking. A plan/config changed after its recorded choice needs a new matching user selection before rendering.
- Do not overwrite a rendered revision or label a revision final unless the user chooses it. Pending revisions may be edited before their first export.
- Do not add unsupported plan fields and claim they were rendered. The current capabilities and limits are in `core/schemas/edit-plan.md`.

## Skill routing

- `skills/styles/premium-explainer/SKILL.md`: premium explanatory editing, caption/motion/audio choices.
- `skills/styles/visual-keyword/SKILL.md`: separate style with a title from frame 0, sparse large keywords and selected illustrations; profile `finance-visual-keyword-vi`. Use explicit keyword cues or text PNG layers, never automatic full-transcript captions for this style.
- `skills/styles/talking-head-pro/SKILL.md`: phrase captions, selected emphasis and infographic inserts, independently based on the public s1 demo. Profiles `talking-head-pro-vi` (general) and `finance-talking-head-pro-vi`.
- `skills/styles/kinetic-motion/SKILL.md`: large scene typography, staggered UI cards and progress via KineticScene. Profiles `kinetic-motion-vi` (general) and `finance-kinetic-motion-vi`. In the reference-page context, “kinematic” refers to Kinetic Motion, not cinematic footage or physics. Keep automatic full-transcript captions off unless the user selects them.
- `core/platforms/tiktok.md`: shared TikTok guidance for opening, pacing, vertical layout and interface clearance; combine with the selected style/domain rather than replacing them.
- `core/style-learning.md`: required learning from edit/revision requests, with scope, evidence, skill/profile versioning and documentation updates.
- `skills/domains/finance/SKILL.md`: Vietnamese financial terminology, source research and number handling.
- `skills/domains/general/SKILL.md`: non-specialist knowledge/personal-brand content, preserving claims and distinguishing examples from evidence. Do not select finance merely because the project has finance profiles.
- Add new styles/domains under `skills/` with `skill.json`, `SKILL.md` frontmatter and a profile selecting the exact version. Read the selected package when used; do not load every skill.
- These are project-local skills loaded through this file/profile, not globally installed skills.

## Changes to this code

- Keep local rendering usable without LLM API keys. The IDE agent supplies creative decisions and browser research; the CLI executes explicit plans.
- Test meaningful media behavior with `python -m unittest discover -s tests -v`. These are code tests, not an automated video-review stage.
- Runtime job data, video, downloaded tools and virtual environments are ignored by Git. Do not commit them or download model weights just for a scaffold test.
- Keep personal preference feedback in ignored `preferences/local-feedback.json`. `preferences/default.json` contains shareable defaults; do not commit chat history, private job data or local credentials.
