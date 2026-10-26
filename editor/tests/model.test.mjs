import { readFileSync } from "node:fs";
import assert from "node:assert/strict";
import { test } from "node:test";
import { stripTypeScriptTypes } from "node:module";
const source = readFileSync(
  new URL("../src/model.ts", import.meta.url),
  "utf8",
);
const js = stripTypeScriptTypes(source);
const { reflow } = await import(
  "data:text/javascript;base64," + Buffer.from(js).toString("base64")
);
const clip = (id, start, end, tin, tout) => ({
  clip_id: id,
  source_in_seconds: start,
  source_out_seconds: end,
  timeline_in_frame: tin,
  timeline_out_frame: tout,
  asset_id: "raw-001",
  playback_rate: 1,
});
const fixture = () => ({
  plan: {
    fps: 30,
    duration_frames: 240,
    clips: [clip("clip-a", 0, 4, 0, 120), clip("clip-b", 4, 8, 120, 240)],
    overlays: [],
  },
  cues: [
    {
      id: "cue-a",
      timeline_in_frame: 30,
      timeline_out_frame: 60,
      text: "Keep me",
    },
  ],
  motions: {},
});

test("reordering clips carries their captions and leaves input unchanged", () => {
  const state = fixture(),
    before = structuredClone(state);
  const result = reflow(state, structuredClone(state.plan.clips).reverse());
  assert.deepEqual(result.cues[0], {
    ...state.cues[0],
    timeline_in_frame: 150,
    timeline_out_frame: 180,
  });
  assert.deepEqual(state, before);
  assert.equal(result.plan.clips[0].timeline_in_frame, 0);
  assert.equal(result.plan.clips[1].timeline_out_frame, 240);
});
test("split preserves timing and does not duplicate a caption crossing the split", () => {
  const state = fixture();
  state.cues[0].timeline_out_frame = 100;
  const result = reflow(
    state,
    [
      clip("clip-a", 0, 2, 0, 60),
      clip("new", 2, 4, 60, 120),
      state.plan.clips[1],
    ],
    { new: "clip-a" },
  );
  assert.deepEqual(result.cues, state.cues);
});
test("visual across reordered clips splits and retains video source offsets and motion specs", () => {
  const state = fixture();
  state.plan.overlays = [
    {
      id: "visual",
      type: "video",
      source_in_seconds: 0,
      timeline_in_frame: 90,
      timeline_out_frame: 150,
    },
  ];
  state.motions.visual = { template: "KineticScene" };
  const result = reflow(state, structuredClone(state.plan.clips).reverse());
  assert.equal(result.plan.overlays.length, 2);
  assert.deepEqual(
    result.plan.overlays.map((l) => [
      l.timeline_in_frame,
      l.timeline_out_frame,
      l.source_in_seconds,
    ]),
    [
      [0, 30, 1],
      [210, 240, 0],
    ],
  );
  assert.deepEqual(result.motions["visual-part-1"], state.motions.visual);
});
test("trim removes dropped visuals, bounds retained captions, and cleans orphaned motion", () => {
  const state = fixture();
  state.plan.overlays = [
    { id: "gone", type: "video", timeline_in_frame: 0, timeline_out_frame: 20 },
  ];
  state.motions.gone = { template: "KineticScene" };
  const result = reflow(state, [
    clip("clip-a", 1.5, 4, 0, 75),
    state.plan.clips[1],
  ]);
  assert.equal(result.plan.duration_frames, 195);
  assert.deepEqual(
    result.cues.map((c) => [c.timeline_in_frame, c.timeline_out_frame]),
    [[0, 15]],
  );
  assert.equal(result.plan.overlays.length, 0);
  assert.deepEqual(result.motions, {});
});
