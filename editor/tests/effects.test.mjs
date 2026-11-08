import { readFileSync } from "node:fs";
import assert from "node:assert/strict";
import { test } from "node:test";
import { stripTypeScriptTypes } from "node:module";
const source = readFileSync(
  new URL("../src/model.ts", import.meta.url),
  "utf8",
);
const js = stripTypeScriptTypes(source);
const { reflow, zoomAt, sourceAt } = await import(
  "data:text/javascript;base64," + Buffer.from(js).toString("base64")
);
const clip = (id, start, end, tin, tout, rate = 1) => ({
  clip_id: id,
  source_in_seconds: start,
  source_out_seconds: end,
  timeline_in_frame: tin,
  timeline_out_frame: tout,
  asset_id: "raw-001",
  playback_rate: rate,
});
const fixture = () => ({
  plan: {
    fps: 30,
    duration_frames: 240,
    clips: [clip("clip-a", 0, 4, 0, 120), clip("clip-b", 4, 8, 120, 240)],
    overlays: [],
    audio: {
      voice_gain: 1,
      music: null,
      sfx: [
        {
          id: "pop",
          path: "assets/pop.wav",
          timeline_in_frame: 130,
          timeline_out_frame: 140,
          gain: 1,
        },
      ],
    },
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

test("speed shortens a clip and keeps captions on the same words", () => {
  const state = fixture();
  const clips = structuredClone(state.plan.clips);
  clips[0].playback_rate = 2;
  const result = reflow(state, clips);
  assert.equal(result.plan.clips[0].timeline_out_frame, 60);
  assert.equal(result.plan.duration_frames, 180);
  assert.deepEqual(
    [result.cues[0].timeline_in_frame, result.cues[0].timeline_out_frame],
    [15, 30],
  );
  assert.equal(sourceAt(result.plan.clips[0], 15, 30), 1);
  clips[0].playback_rate = 3;
  assert.throws(() => reflow(state, clips), /Tốc độ/);
});

test("a sound effect follows its source moment and is never split", () => {
  const state = fixture();
  const reversed = reflow(state, structuredClone(state.plan.clips).reverse());
  assert.deepEqual(
    [
      reversed.plan.audio.sfx[0].timeline_in_frame,
      reversed.plan.audio.sfx[0].timeline_out_frame,
    ],
    [10, 20],
  );
  const faster = structuredClone(state.plan.clips);
  faster[1].playback_rate = 2;
  const sped = reflow(state, faster);
  // Source 4.333 s sits 0.333 s into clip-b, now 5 output frames at 2x.
  assert.equal(sped.plan.audio.sfx[0].timeline_in_frame, 125);
  const trimmed = structuredClone(state.plan.clips);
  trimmed[1].source_in_seconds = 5;
  assert.deepEqual(reflow(state, trimmed).plan.audio.sfx, []);
});

test("zoom values match the export evaluator", () => {
  const keys = [
    { source_seconds: 1, scale: 1, x: 0.5, y: 0.5 },
    { source_seconds: 3, scale: 2, x: 0, y: 1, ease: "linear" },
  ];
  assert.deepEqual(zoomAt(keys, 0), [1, 0.5, 0.5]);
  assert.deepEqual(zoomAt(keys, 2), [1.5, 0.25, 0.75]);
  assert.deepEqual(zoomAt(keys, 5), [2, 0, 1]);
  keys[1].ease = "hold";
  assert.equal(zoomAt(keys, 2.999)[0], 1);
  assert.equal(zoomAt(keys, 3)[0], 2);
  delete keys[1].ease;
  assert.equal(zoomAt(keys, 2)[0], 1.5);
  assert.ok(zoomAt(keys, 1.5)[0] < 1.25);
  assert.deepEqual(zoomAt(undefined, 2), [1, 0.5, 0.5]);
});

test("transitions split around the cut, need handles and approximate xfade in CSS", async () => {
  const { transitionSplit, clipHandles, transitionStyle } = await import(
    "data:text/javascript;base64," + Buffer.from(js).toString("base64")
  );
  assert.deepEqual(transitionSplit(10), [5, 5]);
  assert.deepEqual(transitionSplit(7), [3, 4]);
  const clips = [clip("a", 0, 2, 0, 60), clip("b", 3, 5, 60, 120), clip("c", 6, 7, 120, 150)];
  clips[1].transition = { type: "fade", frames: 10 };
  clips[2].transition = { type: "whip", frames: 7 };
  assert.deepEqual(clipHandles(clips), [[0, 5], [5, 4], [3, 0]]);
  assert.deepEqual(transitionStyle("fade", 0.25, true), { opacity: 0.25 });
  assert.deepEqual(transitionStyle("fade", 0.25, false), {});
  assert.equal(transitionStyle("slide-left", 0.5, true).transform, "translateX(50%)");
  assert.equal(transitionStyle("slide-left", 0.5, false).transform, "translateX(-50%)");
  assert.equal(transitionStyle("wipe-left", 1, true).clipPath, "inset(0 0 0 0%)");
  assert.equal(transitionStyle("flash", 0.5, true).filter, "brightness(3.5)");
});

test("reflow drops transitions on the first clip and on new pieces, and fits short neighbours", () => {
  const s = fixture();
  const clips = structuredClone(s.plan.clips);
  clips[0].transition = { type: "fade", frames: 10 };
  clips[1].transition = { type: "slide-left", frames: 10 };
  let next = reflow(s, clips);
  assert.equal(next.plan.clips[0].transition, undefined);
  assert.deepEqual(next.plan.clips[1].transition, { type: "slide-left", frames: 10 });
  // A split's second half is a new piece of the same source clip: no transition at the split.
  const split = structuredClone(next.plan.clips);
  split.splice(1, 1, { ...split[1], source_out_seconds: 6 }, { ...split[1], clip_id: "clip-b2", source_in_seconds: 6 });
  next = reflow(next, split, { "clip-b2": "clip-b" });
  assert.deepEqual(next.plan.clips[1].transition, { type: "slide-left", frames: 10 });
  assert.equal(next.plan.clips[2].transition, undefined);
  // A 4-frame neighbour leaves room for at most a 4-frame transition.
  const short = structuredClone(s.plan.clips);
  short[0].source_out_seconds = 4 / 30;
  short[1].transition = { type: "fade", frames: 10 };
  assert.equal(reflow(s, short).plan.clips[1].transition.frames, 4);
});
