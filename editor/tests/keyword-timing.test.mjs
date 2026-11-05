import { readFileSync } from "node:fs";
import assert from "node:assert/strict";
import { test } from "node:test";
import { stripTypeScriptTypes } from "node:module";
const source = readFileSync(
  new URL("../../motion/src/keyword-timing.ts", import.meta.url),
  "utf8",
);
const { keywordEnvelope } = await import(
  "data:text/javascript;base64," +
    Buffer.from(stripTypeScriptTypes(source)).toString("base64")
);
test("keyword emphasis stays hidden until its speech anchor, eases monotonically without overshoot and exits to transparent", () => {
  assert.equal(keywordEnvelope(41, 90, 6, 5, 42).opacity, 0);
  assert.equal(keywordEnvelope(42, 90, 6, 5, 42).opacity, 0);
  const entering = Array.from({ length: 7 }, (_, i) =>
    keywordEnvelope(42 + i, 90, 6, 5, 42),
  );
  entering.forEach((v, i) => {
    assert.ok(v.opacity >= 0 && v.opacity <= 1);
    assert.ok(v.y >= 0 && v.y <= 5);
    if (i) assert.ok(v.opacity >= entering[i - 1].opacity);
  });
  assert.equal(entering.at(-1).opacity, 1);
  const leaving = Array.from({ length: 6 }, (_, i) =>
    keywordEnvelope(84 + i, 90, 6, 5, 42),
  );
  leaving.forEach((v, i) => {
    if (i) assert.ok(v.opacity <= leaving[i - 1].opacity);
  });
  assert.equal(leaving.at(-1).opacity, 0);
  assert.equal(keywordEnvelope(95, 90, 6, 5, 42).opacity, 0);
});
