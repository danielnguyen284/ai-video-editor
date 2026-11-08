# User-choice workflow

The selected flow is: the agent analyzes the source and proposes one concrete treatment; the user approves or adjusts it before the agent builds. Read [editing-workflow.md](editing-workflow.md) and `preferences/workflow.json` first. Apply standing large-v3 local/tooling choices without re-asking. Keep creative choices distinct from technical preparation.

TikTok is the user's primary platform for suggestions. For these briefs, read [the TikTok guide](platforms/tiktok.md), then tailor questions to the opening, useful duration, 9:16 framing and captions clear of existing text and platform controls. A stored platform preference is not a selected output setting. Preserve explicit choices from the current job and avoid imposing a fixed short duration or a faster style.

## How to ask

- Present one recommended treatment derived from the actual source/transcript, including its practical effect. Add an alternative only for a material tradeoff. Allow a custom adjustment; do not repeat choices already made in the prompt or standing instructions.
- Ask brief intake questions only for genuinely missing information; batch remaining creative choices into the treatment proposal rather than an upfront ten-question checklist. Use the runtime's question UI when useful.
- Never interpret silence, elapsed time, a recommended option or a profile default as an answer. While waiting, only prepare work independent of that choice, such as reading media metadata.
- General preferences and prior examples inform suggestions; they are not automatically selected creative choices. Explicit standing instructions in `preferences/workflow.json` do authorize their stated technical scope. Current prompt and existing job decisions override them. An explicit answer within the job carries over until changed.
- The user may explicitly delegate a decision, e.g. “choose cuts within this style for me.” Record that scope. Ask again for changes outside it.
- Verify installed files and runtime capability separately before offering a group as ready. Read `core/skill-library.md` for the six upstream groups, profiles and Windows limitations; `ai_editor.py skills --full` checks pinned packages. A group selects an editorial vocabulary, not every upstream layout, language, CTA, speed or cloud provider. For comparisons, clarify what varies and what stays shared, then create independent drafts/outputs without mixing every group's defaults. Visual options in the existing renderer are image/logo/B-roll layers, static text PNGs via `scripts/render_text.py`, Remotion MetricCard/BarChart/LowerThird/Keyword/KineticScene/Illustration/Points, picture transitions between clips, keyframed zoom/punch-in, constant per-clip speed (0.5-2x), a blurred-backdrop framing and timed SFX from supplied or licensed files (see `core/schemas/edit-plan.md`). Footage options remain local signals, IDE image inspection or a selected installed Ollama model. Speed ramps, face-following crops, split-screen/PIP, external engines and services need explicit implementation/setup before being represented as working.

## Decision groups

1. **Prepare:** identify the source/job, probe its metadata and check existing decisions/transcripts/locks. A candidate group/profile can scaffold a pending analysis job; do not treat it as a selected style.
2. **Processing:** use the standing local large-v3 choice for needed speech transcription without a model questionnaire. Reuse supplied/matching transcript; honor no-STT work. A missing local model requires restoring that same selection, not a new model recommendation.
   If footage analysis is selected, ask local signals only, AI in the IDE inspecting sampled frames, or a selected Ollama vision model. Do not start model downloads or send frames to a remote endpoint based on a local-only choice.
3. **Propose:** after reading the transcript, recommend one group, output/framing, hook/structure, actual keep/cut ranges, caption/keyword, visuals/audio and expected length. Include optional footage/research modes and any missing assets/engine limitations in the same reviewable treatment.
4. **Approve then build:** wait for approval or adjustments unless already selected/delegated within scope. Record the real reply plus the relevant standing-default references. Never record the agent's proposal as a user reply.

Technical details can be derived from selected choices: frame arithmetic, codec flags, temporary filenames and executing FFmpeg do not each need another question. A change in the story, selected take, framing, added claim, style or audio treatment outside the chosen scope does.

The user selected [local visual editing](visual-editor.md): AI prepares an editable draft, the user can adjust individual layers and protect approved output ranges. Treat direct UI edits, explicit unlocking, revision adoption and export confirmation as scoped user actions; record their UI origin instead of inventing a chat message. Do not change locked regions or silently adopt another revision. This workflow selection does not preselect style/output/music or other unanswered job decisions.

## Persist and execute

Each revision has `decisions.json` with setup answers, the concrete selected proposal, the user's actual reply and a history. Setup answers are collected in a JSON object with these fields:

```json
{
  "style": "style/melvynx-raw",
  "domain": "domain/source-context",
  "output": {"width":1080,"height":1920,"fps":30,"fit":"pad"},
  "footage_analysis": false,
  "transcription": true,
  "editing": "Keep original order, remove only stumbles and repeated takes",
  "captions": true,
  "research": "Use supplied materials only",
  "visuals": "Framing and captions only",
  "audio": "Voice only"
}
```

This is a shape example, **not a preselected answer**. After the treatment is approved, the agent writes the actual chosen answers to `revisions/rNNN/setup-answers.json` and runs:

```text
ai_editor.py decide JOB --revision r001 --stage setup --answers PATH --user-message "actual user reply/answers"
```

If choices arrive across several messages, preserve their text in `user-message` or the selection summary. Apply style/domain changes to the selected profile/config; the CLI does not silently implement different skills. Read only the selected packages.

After implementing the concrete edit proposal selected by the user:

```text
ai_editor.py decide JOB --revision r001 --stage edit-plan --summary "selected proposal and scope" --user-message "actual user reply"
ai_editor.py render JOB --revision r001
```

The CLI records the exact plan/config hashes and refuses a different plan. It does not verify that the quoted user message is authentic or semantically interpret the prose choices: following the dialogue and applying all selected decisions is the agent's responsibility. Never use the command to fabricate an answer or bypass pending questions.

`choices JOB` displays the standing workflow separately from pending creative decisions and suggestions. `transcribe JOB` can run before full setup under the standing local-processing policy, logging actual model provenance without approving any edit. `render --dry-run` prepares commands while a decision is pending. Existing jobs without decisions still need a real treatment approval before exporting.

## After export

The user watches the video and prompts again. A revision inherits previously selected setup choices and starts with a pending edit proposal. The user's feedback can itself select a concrete change; record it after applying those changes. Ask before introducing new changes beyond that prompt. This is a dialogue with the user, not an AI review step.

For every edit request, changed edit-treatment answer and revision feedback, the Editor also follows [style-learning.md](style-learning.md). Extract and maintain reusable style guidance and related documentation during the same task; this maintenance does not need another permission question. Preserve the distinction between a style rule and a one-video instruction. Learned guidance informs future suggestions and does not replace the user's choices for the current revision.
