# Learn style rules from edit requests

The user has authorized the Editor to maintain style skills and related documentation as part of every edit request and revision task. Read the actual prompt/feedback and extract relevant reusable guidance, implement it where appropriate, and explain the result briefly. Do not stop solely to request approval for routine skill/documentation maintenance. Existing creative-choice checkpoints still apply.

This is an IDE-agent responsibility. The CLI executes explicit plans; it does not interpret feedback, rewrite skills or run a background learning process.

## Extract and scope

Consider each new edit request, answer that changes the edit treatment, and revision feedback. Read the selected style and its relevant references. Use what the user actually said or selected; silence, an unselected suggestion and the agent's own preference are not evidence.

Read the current installed package under `skills/` before changing it, and the job's locked snapshot when interpreting an old revision. Merge the lesson into the current package; do not replace it with the older job copy or calculate a new library version from that older snapshot.

| Information in the request | Where it belongs |
|---|---|
| A reusable rule about titles, keywords/captions, pacing, framing, illustration layout or sound treatment for the selected style | The relevant style paragraph or a focused reference, with conditions where needed |
| A user, project or brand preference that should not redefine the style for everyone | Scoped editorial preferences/notes, with the source and intended scope; not a global style default |
| Source-specific facts, actual title wording, ticker corrections, an exact image or song, a timestamp cut or a one-video placement | The job's plan, transcript, assets or feedback; retain reusable principles only if the request supports them |
| A rendering limitation or setup problem | Technical implementation/setup documentation; change code and tests only when implementation is part of the task |

For a local style correction, extract a conditional rule when it is supported by the feedback, rather than copying literal coordinates or content. For example, “this keyword covers the speaker's face” can reinforce selecting clear space around the subject; it does not establish one fixed `y` position for all videos. If the skill already says that, record that it is covered and avoid a duplicate rule.

Clear style-wide instructions can be implemented directly. When intended scope is unclear, keep the candidate in the current job's notes and follow the user's local request; do not silently replace the shared style's identity. Ask only when resolving the ambiguity is needed for an actual creative decision. Preserve separate styles: a request for a different editing language can justify a new style/profile rather than overwriting an unrelated one.

## Update useful rules

1. Apply the user's selected edit/revision within its scope. Extract learning during the same task, before the final handoff; do not delay the work merely to build a learning catalog.
2. Compare the candidate with existing instructions. Merge or refine a relevant paragraph instead of appending another near-duplicate. State the condition, intended outcome and executable treatment. If there is no new supported rule, leave the shared skill unchanged.
3. Update the appropriate `SKILL.md` and any affected reference or defaults. Keep substantial treatment-specific instructions in references. Do not put transcript text, personal details or job-specific media into shared skill files.
4. Bump `skill.json.version` when the package changes. Update every current profile selecting that style to the exact installed version and bump the affected profile versions. The current resolver has one installed package version per style ID; leaving a profile pinned to another version causes a mismatch.
5. Update related documentation in the same task: a changed workflow/capability belongs in README or core guidance, and a changed recipient instruction belongs in `HUONG-DAN.html`. Avoid copying the full rule into every document; link to its maintained location. Refresh any affected examples and correct conflicting old text.
6. Validate frontmatter, reference links, JSON and profile resolution. Use the skill validator when available. If the change affects rendering code/defaults, run the relevant existing media tests; do not download models just to check documentation.

Updating prose does not implement a new renderer capability. Describe unsupported effects accurately and use only fields in the current schemas.

## Preserve job decisions and evidence

Skill updates guide future jobs. Keep existing job/revision snapshots and exported videos intact. Apply a user's current revision feedback using its recorded config and a new revision when required. A library skill update does not silently migrate that config or approve new visual/audio choices. If the user also requests a skill/profile upgrade for the current job, resolve it into the new revision and record matching choices after applying it.

When a job exists, append a concise event to `jobs/<job>/feedback/style-learning.json`, using an `events` array. Include the actual user quote or an existing feedback reference, revision, style ID/version, scope, extracted rule or reason for no change, updated relative file paths and version changes. Record candidates as candidates; do not invent an approval. This is an agent-maintained feedback note, not an edit-plan field or a new CLI command.

When the task is only tool/style maintenance and has no job, update the relevant files and report the changes without creating a dummy media job. In all cases, the handoff briefly states the reusable rule updated and its scope, or that the request was job-specific/already covered when relevant. Do not add an AI video-review role or an automatic repair loop.

When packaging a release, rebuild the ZIP so it includes the updated skills and documents. Raw learning events remain private job data and are excluded by the existing source-only packaging process.
