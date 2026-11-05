export function keywordEnvelope(
  frame: number,
  duration: number,
  enter: number,
  exit: number,
  start = 0,
) {
  const p = Math.max(0, Math.min(1, (frame - start) / enter));
  const eased = 1 - (1 - p) ** 3;
  const leaving = Math.max(0, Math.min(1, (duration - 1 - frame) / exit));
  const fade = leaving * leaving * (3 - 2 * leaving);
  return {
    opacity: frame < start ? 0 : eased * fade,
    y: (1 - eased) * 5 - (1 - fade) * 2,
  };
}
