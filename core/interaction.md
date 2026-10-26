# User-choice workflow

The user wants the AI to ask and offer options throughout editing. The Editor recommends, the user chooses, the roles execute those choices. Apply this to editing decisions, not to routine command syntax or error repair needed to execute a selected operation.

TikTok is the user's primary platform for suggestions. For these briefs, read [the TikTok guide](platforms/tiktok.md), then tailor questions to the opening, useful duration, 9:16 framing and captions clear of existing text and platform controls. A stored platform preference is not a selected output setting. Preserve explicit choices from the current job and avoid imposing a fixed short duration or a faster style.

## How to ask

- Present two or three short options per question, with a recommendation and its practical effect. Allow a custom answer. For a decision already clearly selected in the prompt, record that answer instead of repeating the question.
- Batch related questions; do not dump ten questions at once. When available, use the runtime's question UI. Otherwise provide concise numbered choices in chat and wait for the reply.
- Never interpret silence, elapsed time, a recommended option or a profile default as an answer. While waiting, only prepare work independent of that choice, such as reading media metadata.
- Preferences and prior jobs inform suggestions. They do not authorize silent choices for a new job. An explicit answer within the current job carries over until the user changes it.
- The user may explicitly delegate a decision, e.g. “choose cuts within this style for me.” Record that scope. Ask again for changes outside it.
- Verify what is actually installed before offering it as ready. Styles are premium-explainer (restrained phrase captions), visual-keyword (opening title + sparse keywords/images), talking-head-pro (phrase captions + selective infographic inserts) and kinetic-motion (large scene text + staggered cards/progress). The two new styles have general and finance profiles. Selecting visual-keyword or kinetic-motion chooses selective text rather than automatic full-transcript captions; ask about the actual words, timing and sourcing. “Create a new style from my reference” is a supported agent task. Visual options are image/logo/B-roll layers, static text PNGs through the visual-keyword helper and Remotion MetricCard, BarChart, LowerThird or KineticScene. Footage options are local OpenCV signals, IDE inspection of sampled images or Ollama semantics with an installed vision model. KineticScene animates its own text/cards; arbitrary source-camera animation and continuous face following are not bundled. Motion availability still depends on doctor/setup.

## Decision groups

1. **Direction:** style, domain, target format/duration. Show the installed choice and the option to supply a reference/create another skill. Ask how to frame the source: retain the image with padding or center crop where appropriate.
2. **Processing:** image/footage analysis, local transcription or supplied transcript, research or supplied materials only. Explain the first model download if local STT is chosen.
   If footage analysis is selected, ask local signals only, AI in the IDE inspecting sampled frames, or a selected Ollama vision model. Do not start model downloads or send frames to a remote endpoint based on a local-only choice.
3. **Edit treatment:** original order or new hook/structure, degree of cutting, caption style, additional visuals and voice/music treatment. Ask about supplied assets before referring to nonexistent files.
4. **Concrete edit proposal:** after reading the transcript, propose the actual source ranges, hook, overlays/audio and expected length. Offer two or three meaningful alternatives when they exist. If the user already selected detailed cuts or delegated this scope, execute that instruction without a duplicate question.

Technical details can be derived from selected choices: frame arithmetic, codec flags, temporary filenames and executing FFmpeg do not each need another question. A change in the story, selected take, framing, added claim, style or audio treatment outside the chosen scope does.

The user selected [local visual editing](visual-editor.md): AI prepares an editable draft, the user can adjust individual layers and protect approved output ranges. Treat direct UI edits, explicit unlocking, revision adoption and export confirmation as scoped user actions; record their UI origin instead of inventing a chat message. Do not change locked regions or silently adopt another revision. This workflow selection does not preselect style/output/music or other unanswered job decisions.

## Persist and execute

Each revision has `decisions.json` with setup answers, the concrete selected proposal, the user's actual reply and a history. Setup answers are collected in a JSON object with these fields:

```json
{
  "style": "style/premium-explainer",
  "domain": "domain/finance",
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

This is a shape example, **not a preselected answer**. The agent writes the actual answers to `revisions/rNNN/setup-answers.json` after the user's replies and runs:

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

`choices JOB` displays pending decisions and suggestions. `render --dry-run` prepares the commands without exporting video while a decision is pending. Existing jobs without a decision file must collect user choices before exporting; do not invent answers for them.

## After export

The user watches the video and prompts again. A revision inherits previously selected setup choices and starts with a pending edit proposal. The user's feedback can itself select a concrete change; record it after applying those changes. Ask before introducing new changes beyond that prompt. This is a dialogue with the user, not an AI review step.

For every edit request, changed edit-treatment answer and revision feedback, the Editor also follows [style-learning.md](style-learning.md). Extract and maintain reusable style guidance and related documentation during the same task; this maintenance does not need another permission question. Preserve the distinction between a style rule and a one-video instruction. Learned guidance informs future suggestions and does not replace the user's choices for the current revision.
