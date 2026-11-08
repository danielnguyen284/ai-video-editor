import { readFileSync } from "node:fs";
import assert from "node:assert/strict";
import { test } from "node:test";
import { stripTypeScriptTypes } from "node:module";
const js = stripTypeScriptTypes(
  readFileSync(new URL("../src/model.ts", import.meta.url), "utf8"),
);
const { replaceCaptions, captionPattern, resumeSession, captionLines, lineCount } = await import(
  "data:text/javascript;base64," + Buffer.from(js).toString("base64")
);
const cue = (id, start, text) => ({
  id,
  timeline_in_frame: start,
  timeline_out_frame: start + 30,
  text,
});
const fixture = () => ({
  plan: { captions: { enabled: true }, clips: [{ id: "original" }] },
  cues: [
    cue("a", 0, "Công ty hpg, HPG tăng."),
    cue("b", 30, "HPG giữ nguyên"),
    cue("c", 60, "HPG đổi sau vùng khóa"),
  ],
  locks: [{ start: 35, end: 60, label: "Đã ưng" }],
  motions: {},
});

test("bulk replacement skips partially locked cues, respects end-exclusive boundaries, preserves other data and input", () => {
  const state = fixture(),
    before = structuredClone(state);
  const result = replaceCaptions(state, "hpg", "Hòa Phát");
  assert.equal(result.count, 2);
  assert.equal(result.lockedCount, 1);
  assert.equal(result.project.cues[0].text, "Công ty Hòa Phát, Hòa Phát tăng.");
  assert.deepEqual(result.project.cues[1], before.cues[1]);
  assert.equal(result.project.cues[2].text, "Hòa Phát đổi sau vùng khóa");
  assert.deepEqual(result.project.plan, before.plan);
  assert.deepEqual(result.project.locks, before.locks);
  assert.deepEqual(state, before);
});
test("search and replacement treat metacharacters and dollar expressions literally", () => {
  const state = fixture();
  state.cues[0].text = "Giá (a+b)? [x]. (a+b)?";
  const result = replaceCaptions(state, "(a+b)?", "$&");
  assert.equal(result.project.cues[0].text, "Giá $& [x]. $&");
  assert.equal(captionPattern("[x].").test("[x]."), true);
  assert.equal(captionPattern("[x].").test("xxx"), false);
});
test("case selection, Vietnamese, single cue, missing query and no-op replacements", () => {
  const state = fixture();
  state.cues[0].text = "ĐẦU tư đầu tư";
  assert.equal(
    replaceCaptions(state, "đầu", "Vốn").project.cues[0].text,
    "Vốn tư Vốn tư",
  );
  assert.equal(
    replaceCaptions(state, "đầu", "Vốn", true).project.cues[0].text,
    "ĐẦU tư Vốn tư",
  );
  const single = replaceCaptions(state, "HPG", "ABC", true, "c");
  assert.equal(single.count, 1);
  assert.equal(single.lockedCount, 0);
  assert.deepEqual(single.project.cues[0], state.cues[0]);
  assert.equal(replaceCaptions(state, "", "x").count, 0);
  assert.equal(replaceCaptions(state, "HPG", "HPG").count, 0);
});
test("deleting a word works but a wholly empty caption is kept and reported", () => {
  const state = fixture();
  state.cues[0].text = "bỏ giữ";
  state.cues[2].text = "bỏ";
  const result = replaceCaptions(state, "bỏ", "");
  assert.equal(result.count, 1);
  assert.equal(result.emptyCount, 1);
  assert.equal(result.project.cues[0].text, " giữ");
  assert.equal(result.project.cues[2].text, "bỏ");
});
test("session restoration accepts only existing jobs and valid frame/tab/zoom", () => {
  const jobs = [{ id: "demo" }];
  assert.equal(resumeSession("{broken", jobs), null);
  assert.equal(resumeSession(JSON.stringify({ job: "gone" }), jobs), null);
  assert.deepEqual(
    resumeSession(
      JSON.stringify({ job: "demo", frame: -7, tab: "invalid", zoom: 999 }),
      jobs,
    ),
    { job: "demo", frame: 0, tab: "media", zoom: 100 },
  );
  assert.deepEqual(
    resumeSession(
      JSON.stringify({ job: "demo", frame: 123.4, tab: "text", zoom: 20 }),
      jobs,
    ),
    { job: "demo", frame: 123, tab: "text", zoom: 20 },
  );
});

test("a typed caption line break is kept like the export, each line still wraps", () => {
  assert.deepEqual(captionLines("Một loại rủi ro phi hệ thống nằm", 22), [
    "Một loại rủi ro phi hệ",
    "thống nằm",
  ]);
  assert.deepEqual(captionLines("Một loại rủi ro\nphi  hệ thống nằm", 22), [
    "Một loại rủi ro",
    "phi hệ thống nằm",
  ]);
  assert.equal(lineCount("Một\nloại\nrủi ro", 22), 3);
  assert.equal(lineCount("", 22), 0);
});
