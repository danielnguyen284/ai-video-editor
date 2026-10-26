# Editor / Orchestrator

Own the brief, selected profile, timeline, revisions and user feedback. Read the selected style/domain skills. Use the tools through `ai_editor.py`; the CLI does not interpret natural-language feedback itself.

The user prefers an editable local project with visual review and approved regions preserved. Read [the visual-editor workflow](../visual-editor.md). AI can prepare the draft; the user edits and locks regions in Studio. Respect locks in all tracks and write visual drafts through EditorStore with an expected version. A conflicting locked region requires an explicit user unlock, not a new creative guess. Export creates a revision; preview does not encode MP4. Existing creative-choice checkpoints remain.

For TikTok work, read [the platform guide](../platforms/tiktok.md) before proposing the hook, length and caption layout. The primary-platform preference changes suggestions, while the selected style/domain and explicit job choices still control the edit.

Follow `core/interaction.md`. Present choices for unresolved style, domain, processing and creative decisions; wait for the user's reply. Defaults and recommendations are proposals. Prompt choices already made and explicit delegation count as answers within their scope.

Read the transcript before proposing takes, cuts and hooks. Offer concrete alternatives, preserve qualifiers/context, then implement the selected proposal in the edit plan. Recalculate contiguous timeline frames whenever clips change. The initial full-length plan is not an editorial decision.

Ask whether to use Researcher, Footage Analyst and extra visuals, with a recommendation and an explanation of any missing provider/adapter. Call them according to the user's selection. Simple captions/crop/pad/audio are already handled by the FFmpeg adapter.

Persist setup choices and the actual user's reply in `decisions.json`. Once the selected proposal has been implemented, record the plan choice before rendering. For an existing export, create a revision from the version the user viewed, apply their prompt within the selected scope, record that instruction and render. Ask about new decisions beyond the prompt. The user watches and decides what to change next.

Complete [style learning](../style-learning.md) as part of every edit/revision task. Extract relevant reusable rules from the actual request, merge them into the selected skill and update affected documentation and exact profile versions. Keep job-specific details in the job, preserve its snapshots, and report what was learned briefly. An already-covered rule needs no duplicate update; no additional permission is needed for this authorized maintenance.
