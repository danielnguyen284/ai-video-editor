import React, { useMemo, useState } from "react";
import { LockKey, MagnifyingGlass } from "@phosphor-icons/react";
import {
  captionPattern,
  cueLocked,
  replaceCaptions,
  type Project,
} from "./model";

export function CaptionPanel({
  project,
  selectedId,
  frame,
  change,
  select,
  notify,
}: {
  project: Project;
  selectedId?: string;
  frame: number;
  change: (mutate: (state: Project) => void | Project) => void;
  select: (id: string, start: number) => void;
  notify: (message: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [replacement, setReplacement] = useState("");
  const [matchCase, setMatchCase] = useState(false);
  const cues = useMemo(
    () =>
      project.cues
        .filter((cue) => {
          const pattern = captionPattern(query, matchCase);
          return !pattern || pattern.test(cue.text);
        })
        .sort((a, b) => a.timeline_in_frame - b.timeline_in_frame),
    [project.cues, query, matchCase],
  );
  const preview = useMemo(
    () => replaceCaptions(project, query, replacement, matchCase),
    [project, query, replacement, matchCase],
  );
  const replace = (id?: string) => {
    const result = replaceCaptions(project, query, replacement, matchCase, id);
    if (result.count) change(() => result.project);
    notify(
      `Đã thay ${result.count} câu. Bỏ qua ${result.lockedCount} câu đã khóa${result.emptyCount ? ` và ${result.emptyCount} câu sẽ bị trống (dùng Xóa cue nếu muốn bỏ câu)` : ""}. Có thể hoàn tác bằng Ctrl+Z.`,
    );
  };
  const time = (f: number) =>
    `${Math.floor(f / project.plan.fps / 60)
      .toString()
      .padStart(
        2,
        "0",
      )}:${((f / project.plan.fps) % 60).toFixed(2).padStart(5, "0")}`;
  return (
    <section
      className="transcript-panel"
      aria-label="Lời thoại và tìm thay caption"
    >
      <div className="caption-search">
        <label>
          <MagnifyingGlass size={15} />
          <input
            aria-label="Tìm caption"
            placeholder="Tìm trong caption…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
        <details className="caption-replace">
          <summary>Thay từ hàng loạt{matchCase ? " · Aa" : ""}</summary>
          <input
            aria-label="Thay bằng"
            placeholder="Thay bằng…"
            value={replacement}
            onChange={(e) => setReplacement(e.target.value)}
          />
          <label className="toggle">
            <input
              type="checkbox"
              checked={matchCase}
              onChange={(e) => setMatchCase(e.target.checked)}
            />
            Phân biệt hoa thường
          </label>
          <div className="replace-actions">
            <button
              disabled={
                !query ||
                !selectedId ||
                !preview.project.cues.some(
                  (c) =>
                    c.id === selectedId &&
                    c.text !== project.cues.find((o) => o.id === c.id)?.text,
                )
              }
              onClick={() => replace(selectedId)}
            >
              Thay câu chọn
            </button>
            <button disabled={!preview.count} onClick={() => replace()}>
              Thay tất cả ({preview.count})
            </button>
          </div>
        </details>
        <small role="status">
          {cues.length}/{project.cues.length} câu
          {query
            ? ` · ${preview.lockedCount} câu khóa được giữ nguyên`
            : " · bấm thời gian để xem"}
          {preview.emptyCount
            ? ` · ${preview.emptyCount} câu sẽ trống, hãy dùng Xóa cue`
            : ""}
        </small>
      </div>
      {!project.cues.length && (
        <p className="aside-help">
          Chưa có caption. Thêm câu ở playhead hoặc nhờ AI chuẩn bị từ
          transcript.
        </p>
      )}
      {!!project.cues.length && !cues.length && (
        <p className="aside-help">Không tìm thấy câu phù hợp.</p>
      )}
      <div className="transcript-cues">
        {cues.map((cue) => {
          const locked = cueLocked(project, cue);
          const active =
            cue.timeline_in_frame <= frame && frame < cue.timeline_out_frame;
          return (
            <div
              key={cue.id}
              className={`transcript-cue ${selectedId === cue.id ? "selected" : ""} ${active ? "playing-cue" : ""}`}
            >
              <button
                className="cue-time"
                aria-label={`Xem câu ${time(cue.timeline_in_frame)}`}
                onClick={() => select(cue.id, cue.timeline_in_frame)}
              >
                {time(cue.timeline_in_frame)} — {time(cue.timeline_out_frame)}
                {locked && <LockKey size={13} aria-label="Đã khóa" />}
              </button>
              <textarea
                aria-label={`Sửa câu ${time(cue.timeline_in_frame)}`}
                value={cue.text}
                disabled={locked}
                rows={2}
                onFocus={() => select(cue.id, cue.timeline_in_frame)}
                onChange={(e) =>
                  change((s) => {
                    s.cues.find((c) => c.id === cue.id)!.text = e.target.value;
                  })
                }
              />
            </div>
          );
        })}
      </div>
    </section>
  );
}
