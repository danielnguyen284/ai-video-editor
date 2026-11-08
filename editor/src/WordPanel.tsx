import React, { useMemo, useState } from "react";
import {
  ArrowCounterClockwise,
  MagnifyingGlass,
  Scissors,
  Timer,
} from "@phosphor-icons/react";
import {
  cuesForWords,
  cutSource,
  outputFrame,
  pauseRanges,
  refreshCues,
  restoreSource,
  unlockedRanges,
  wordRanges,
  type Project,
  type Word,
} from "./model";

/** Edit the cut by its words: removing text removes that source time. */
export function WordPanel({
  project,
  words,
  frame,
  change,
  seek,
  notify,
}: {
  project: Project;
  words: Word[];
  frame: number;
  change: (mutate: (state: Project) => void | Project) => void;
  seek: (frame: number) => void;
  notify: (message: string) => void;
}) {
  const [selection, setSelection] = useState<number[]>([]);
  const [anchor, setAnchor] = useState<number | null>(null);
  const [query, setQuery] = useState("");
  const [minGap, setMinGap] = useState(0.5);
  const [keep, setKeep] = useState(0.2);
  const plan = project.plan;
  const at = useMemo(
    () =>
      words.map((w) => ({
        mid: outputFrame(plan, (w.start + w.end) / 2),
        start: outputFrame(plan, w.start),
        end: outputFrame(plan, w.end - 1e-3),
      })),
    [plan, words],
  );
  const guard = Math.max(0, ...project.locks.map((l) => l.end));
  // Whole words first, so "ờ" does not also pick "ngờ"; partial text otherwise.
  const matches = useMemo(() => {
    const plain = (s: string) =>
      s.toLocaleLowerCase("vi").replace(/[^\p{L}\p{N}\s]+/gu, "").trim();
    const q = plain(query);
    if (!q) return [];
    const exact = words.flatMap((w, i) => (plain(w.text) === q ? [i] : []));
    return exact.length
      ? exact
      : words.flatMap((w, i) => (plain(w.text).includes(q) ? [i] : []));
  }, [query, words]);
  const paragraphs = useMemo(() => {
    const groups: number[][] = [];
    words.forEach((w, i) => {
      if (!groups.length || words[i - 1].segment !== w.segment) groups.push([]);
      groups.at(-1)!.push(i);
    });
    return groups;
  }, [words]);
  const kept = selection.filter((i) => at[i].mid !== null),
    removed = selection.filter((i) => at[i].mid === null);
  const click = (i: number, e: React.MouseEvent) => {
    if (e.shiftKey && anchor !== null) {
      const [a, b] = [Math.min(anchor, i), Math.max(anchor, i)];
      setSelection(Array.from({ length: b - a + 1 }, (_, k) => a + k));
      return;
    }
    if (e.ctrlKey || e.metaKey)
      setSelection((s) => (s.includes(i) ? s.filter((x) => x !== i) : [...s, i]));
    else setSelection([i]);
    setAnchor(i);
    const target = at[i].start ?? at[i].mid;
    if (target !== null) seek(target);
  };
  const cut = (ranges: [number, number][], label: string) => {
    const { allowed, skipped } = unlockedRanges(project, ranges);
    const locked = skipped
      ? ` Bỏ qua ${skipped} đoạn nằm trước hoặc trong vùng đã khóa (cắt sẽ làm dịch vùng đó).`
      : "";
    if (!allowed.length) {
      notify(`${label}: không có đoạn nào để cắt.${locked}`);
      return;
    }
    let saved = 0,
      review = 0;
    change((s) => {
      const next = cutSource(s, allowed);
      review = refreshCues(s, next, words);
      saved = s.plan.duration_frames - next.plan.duration_frames;
      return next;
    });
    notify(
      `${label}: cắt ${allowed.length} đoạn, video ngắn đi ${(saved / plan.fps).toFixed(1)} giây.${locked}${review ? ` ${review} caption đã sửa tay cần kiểm tra lại chữ.` : ""} Ctrl+Z để hoàn tác.`,
    );
    setSelection([]);
  };
  const restore = () => {
    const runs: number[][] = [];
    [...removed]
      .sort((a, b) => a - b)
      .forEach((i) =>
        runs.at(-1)?.at(-1) === i - 1 ? runs.at(-1)!.push(i) : runs.push([i]),
      );
    let restored = 0,
      skipped = 0;
    change((s) => {
      let next = s;
      for (const run of runs) {
        const result = restoreSource(next, wordRanges(words, run)[0], undefined, guard);
        if (!result) {
          skipped++;
          continue;
        }
        if (next.cues.length || next.plan.captions.enabled)
          result.cues.push(...cuesForWords(result, run.map((i) => words[i])));
        next = result;
        restored++;
      }
      return next;
    });
    notify(
      `Đã khôi phục ${restored} đoạn.${skipped ? ` Bỏ qua ${skipped} đoạn (trước vùng khóa hoặc quá ngắn).` : ""} Ctrl+Z để hoàn tác.`,
    );
    setSelection([]);
  };
  const current = at.findIndex(
    (f) => f.start !== null && f.end !== null && f.start <= frame && frame <= f.end,
  );
  return (
    <section className="word-panel" aria-label="Sửa video bằng transcript">
      <div className="caption-search">
        <label>
          <MagnifyingGlass size={15} />
          <input
            aria-label="Tìm từ trong transcript"
            placeholder="Tìm từ, ví dụ: ờ, à, kiểu như…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
        <small role="status">
          {query
            ? `${matches.length} kết quả · ${matches.filter((i) => at[i].mid !== null).length} còn trong video`
            : "Bấm chữ để xem · Shift chọn khoảng · Ctrl chọn rời"}
        </small>
        <div className="word-actions">
          <button
            disabled={!matches.some((i) => at[i].mid !== null)}
            onClick={() => setSelection(matches.filter((i) => at[i].mid !== null))}
          >
            Chọn kết quả
          </button>
          <button
            disabled={!kept.length}
            onClick={() => cut(wordRanges(words, kept), "Cắt chữ")}
          >
            <Scissors size={14} />
            Cắt {kept.length ? `(${kept.length})` : ""}
          </button>
          <button disabled={!removed.length} onClick={restore}>
            <ArrowCounterClockwise size={14} />
            Khôi phục
          </button>
        </div>
        <details className="word-pauses">
          <summary>
            <Timer size={14} />
            Rút khoảng lặng
          </summary>
          <div>
            <label>
              Lặng dài hơn (giây)
              <input
                type="number"
                min="0.2"
                max="5"
                step="0.1"
                value={minGap}
                onChange={(e) =>
                  setMinGap(Math.max(0.2, Number(e.target.value)))
                }
              />
            </label>
            <label>
              Giữ lại (giây)
              <input
                type="number"
                min="0"
                max="1"
                step="0.05"
                value={keep}
                onChange={(e) =>
                  setKeep(Math.min(minGap, Math.max(0, Number(e.target.value))))
                }
              />
            </label>
            <button
              onClick={() =>
                cut(pauseRanges(plan, words, minGap, keep), "Rút khoảng lặng")
              }
            >
              Rút
            </button>
          </div>
        </details>
      </div>
      <div className="word-text">
        {paragraphs.map((ids, p) => (
          <p key={p}>
            {ids.map((i) => {
              const f = at[i].mid;
              const classes = [
                f === null ? "word-cut" : "",
                f !== null && f < guard ? "word-locked" : "",
                selection.includes(i) ? "word-selected" : "",
                i === current ? "word-now" : "",
                query && matches.includes(i) ? "word-match" : "",
              ];
              return (
                <span
                  key={i}
                  role="button"
                  tabIndex={-1}
                  className={classes.filter(Boolean).join(" ")}
                  onClick={(e) => click(i, e)}
                >
                  {words[i].text}{" "}
                </span>
              );
            })}
          </p>
        ))}
      </div>
    </section>
  );
}
