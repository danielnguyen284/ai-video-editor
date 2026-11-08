import { readFileSync } from "node:fs";
import assert from "node:assert/strict";
import { test } from "node:test";
import { stripTypeScriptTypes } from "node:module";
const source = readFileSync(
  new URL("../src/model.ts", import.meta.url),
  "utf8",
);
const js = stripTypeScriptTypes(source);
const {
  cutSource,
  cuesForWords,
  outputFrame,
  pauseRanges,
  refreshCues,
  restoreSource,
  unlockedRanges,
  wordRanges,
} = await import(
  "data:text/javascript;base64," + Buffer.from(js).toString("base64")
);
const ids = () => {
  let n = 0;
  return (prefix) => `${prefix}-t${++n}`;
};
const words = [
  { start: 0.5, end: 0.8, text: "xin", segment: 0 },
  { start: 0.8, end: 1.2, text: "chào", segment: 0 },
  { start: 2.0, end: 2.3, text: "ờ", segment: 0 },
  { start: 3.5, end: 3.8, text: "mọi", segment: 1 },
  { start: 3.8, end: 4.2, text: "người", segment: 1 },
];
const fixture = () => ({
  plan: {
    fps: 30,
    duration_frames: 180,
    clips: [
      {
        clip_id: "clip-a",
        asset_id: "raw-001",
        source_in_seconds: 0,
        source_out_seconds: 6,
        timeline_in_frame: 0,
        timeline_out_frame: 180,
        playback_rate: 1,
      },
    ],
    overlays: [],
    captions: { enabled: true, max_chars: 20, max_lines: 2 },
    audio: { voice_gain: 1, music: null },
  },
  cues: [
    { id: "cue-a", timeline_in_frame: 15, timeline_out_frame: 36, text: "xin chào" },
    { id: "cue-b", timeline_in_frame: 60, timeline_out_frame: 126, text: "ờ mọi người" },
  ],
  motions: {},
  locks: [],
});

test("cutting a word removes it from the video and its caption", () => {
  const state = fixture();
  const range = wordRanges(words, [2]);
  assert.deepEqual(range, [[1.6, 2.9]]);
  const next = cutSource(state, range, ids());
  assert.deepEqual(
    next.plan.clips.map((c) => [c.source_in_seconds, c.source_out_seconds]),
    [
      [0, 1.6],
      [2.9, 6],
    ],
  );
  assert.equal(next.plan.duration_frames, 141);
  assert.equal(refreshCues(state, next, words), 0);
  const cue = next.cues.find((c) => c.id === "cue-b");
  assert.deepEqual(
    [cue.timeline_in_frame, cue.timeline_out_frame, cue.text],
    [48, 87, "mọi người"],
  );
  assert.equal(outputFrame(next.plan, 2.1), null);
  assert.equal(state.plan.clips.length, 1, "input stays unchanged");
});

test("hand-edited captions are kept and reported instead of rewritten", () => {
  const state = fixture();
  state.cues[1].text = "Ờ, mọi người!";
  const next = cutSource(state, wordRanges(words, [2]), ids());
  assert.equal(refreshCues(state, next, words), 1);
  assert.equal(next.cues.find((c) => c.id === "cue-b").text, "Ờ, mọi người!");
});

test("long pauses shrink to the kept silence; head/tail lose the whole gap", () => {
  const ranges = pauseRanges(fixture().plan, words, 0.5, 0.2);
  assert.deepEqual(
    ranges.map(([a, b]) => [+a.toFixed(3), +b.toFixed(3)]),
    [
      [1.3, 1.9],
      [2.4, 3.4],
      [4.3, 6],
    ],
  );
  const next = cutSource(fixture(), ranges, ids());
  assert.equal(next.plan.duration_frames, 180 - 18 - 30 - 51);
});

test("cuts before or inside an approved region are skipped", () => {
  const state = fixture();
  state.locks = [{ id: "l", start: 0, end: 45, label: "ok", signature: "x" }];
  const { allowed, skipped } = unlockedRanges(
    state,
    pauseRanges(state.plan, words, 0.5, 0.2),
  );
  assert.equal(skipped, 1);
  assert.equal(allowed.length, 2);
});

test("a cut word can be restored with its caption, but not before a lock", () => {
  const make = ids();
  const cut = cutSource(fixture(), wordRanges(words, [2]), make);
  const back = restoreSource(cut, [1.6, 2.9], make);
  assert.equal(back.plan.duration_frames, 180);
  assert.deepEqual(
    back.plan.clips.map((c) => [c.source_in_seconds, c.source_out_seconds]),
    [
      [0, 1.6],
      [1.6, 2.9],
      [2.9, 6],
    ],
  );
  const [cue] = cuesForWords(back, [words[2]], make);
  assert.deepEqual([cue.timeline_in_frame, cue.text], [60, "ờ"]);
  assert.equal(restoreSource(cut, [1.6, 2.9], make, 100), null);
});

test("word times map through clip speed and cutting everything fails", () => {
  const state = fixture();
  state.plan.clips[0].playback_rate = 2;
  state.plan.clips[0].timeline_out_frame = 90;
  state.plan.duration_frames = 90;
  assert.equal(outputFrame(state.plan, 2), 30);
  assert.throws(() => cutSource(state, [[0, 6]], ids()), /toàn bộ/);
});
