export type Clip = {
  clip_id: string;
  asset_id: string;
  source_in_seconds: number;
  source_out_seconds: number;
  timeline_in_frame: number;
  timeline_out_frame: number;
  playback_rate: number;
  crop?: { x: number; y: number; width: number; height: number };
  zoom?: ZoomKey[];
  transition?: Transition;
};
// Picture transition into a clip, centred on its cut; the voice still cuts hard.
// Same names as TRANSITIONS in core/adapters/ffmpeg.py.
export type TransitionType =
  | "fade"
  | "flash"
  | "slide-left"
  | "slide-right"
  | "slide-up"
  | "wipe-left"
  | "whip";
export type Transition = { type: TransitionType; frames: number };
export const TRANSITIONS: Record<TransitionType, string> = {
  fade: "Mờ chồng",
  flash: "Chớp trắng",
  "slide-left": "Trượt sang trái",
  "slide-right": "Trượt sang phải",
  "slide-up": "Trượt lên",
  "wipe-left": "Quét ngang",
  whip: "Lia nhanh",
};
export const MIN_TRANSITION_FRAMES = 2,
  MAX_TRANSITION_FRAMES = 30;
// Illustration template entry/exit and on-screen motion; mirrors core/adapters/motion.py.
export const ILLUSTRATION_MOVES = {
  "slide-left": "Trượt từ phải sang",
  "slide-right": "Trượt từ trái sang",
  "slide-up": "Trượt lên",
  zoom: "Phóng",
  wipe: "Quét",
  fade: "Mờ dần",
} as const;
export const ILLUSTRATION_MOTIONS = {
  "zoom-in": "Zoom vào chậm",
  "zoom-out": "Zoom ra chậm",
  "pan-left": "Lia sang trái",
  "pan-right": "Lia sang phải",
  none: "Đứng yên",
} as const;
// Same contract as core/adapters/camera.py: keyframes sit on source seconds,
// x/y is the focal point (0-1) inside the cropped source picture.
export type ZoomEase = "linear" | "in" | "out" | "in-out" | "hold";
export type ZoomKey = {
  source_seconds: number;
  scale: number;
  x: number;
  y: number;
  ease?: ZoomEase;
};
export type Sfx = {
  id: string;
  path: string;
  timeline_in_frame: number;
  timeline_out_frame: number;
  gain: number;
};
export type Layer = {
  id: string;
  type: "image" | "video";
  path: string;
  timeline_in_frame: number;
  timeline_out_frame: number;
  x: number;
  y: number;
  width: number;
  height: number;
  fit: "contain" | "cover" | "stretch";
  opacity?: number;
  source_in_seconds?: number;
  loop?: boolean;
};
export type Cue = {
  id: string;
  timeline_in_frame: number;
  timeline_out_frame: number;
  text: string;
};
export type Motion = {
  template:
    | "KineticScene"
    | "MetricCard"
    | "BarChart"
    | "LowerThird"
    | "Keyword"
    | "Illustration"
    | "Points";
  width: number;
  height: number;
  fps: number;
  duration_frames: number;
  props: Record<string, any>;
};
export type Plan = {
  schema_version: string;
  job_id: string;
  revision: number;
  config_ref: string;
  fps: number;
  duration_frames: number;
  export: {
    preset: string;
    width: number;
    height: number;
    fps: number;
    fit: "pad" | "crop" | "blur";
  };
  clips: Clip[];
  overlays: Layer[];
  captions: {
    enabled: boolean;
    font_name: string;
    font_size: number;
    margin_v: number;
    max_chars: number;
    max_lines: number;
    outline_width?: number;
    transcript_ref: string;
    items?: any[];
  };
  audio: {
    voice_gain: number;
    music: null | { path: string; gain: number; ducking: boolean };
    sfx?: Sfx[];
    // Export-only cleanup; absent means off so old locks stay valid.
    denoise?: "light" | "strong";
    loudness_lufs?: number;
  };
  notes: string[];
};
export type Lock = {
  id: string;
  start: number;
  end: number;
  label: string;
  signature: string;
};
export type Project = {
  schema_version: string;
  version: number;
  job_id: string;
  base_revision: string;
  base_plan_sha256: string;
  plan: Plan;
  cues: Cue[];
  motions: Record<string, Motion>;
  locks: Lock[];
  updated_at: string;
};
export type View = {
  profile: { id: string; skills: { style: { id: string }; domain: { id: string } } };
  media: {
    width: number;
    height: number;
    duration_seconds: number;
    has_audio: boolean;
  };
  source: string;
  library: {
    path: string;
    name: string;
    type: string;
    duration_seconds?: number;
  }[];
  setup: any;
  durations?: Record<string, number>;
  transcript?: { ref: string; words: Word[] } | null;
};
/** A source-time word from the job transcript (read-only). */
export type Word = { start: number; end: number; text: string; segment: number };
export const mediaUrl = (job: string, path: string, proxy = false) =>
  `/media?job=${encodeURIComponent(job)}&path=${encodeURIComponent(path)}${proxy ? "&proxy=1" : ""}`;
export const uid = (prefix: string) =>
  `${prefix}-${crypto.randomUUID().slice(0, 8)}`;
export const clone = <T>(value: T): T => structuredClone(value);

export const MIN_RATE = 0.5,
  MAX_RATE = 2;
export const rateOf = (clip: Clip) => clip.playback_rate || 1;
/** Source second shown at an output frame of this clip. */
export const sourceAt = (clip: Clip, frame: number, fps: number) =>
  clip.source_in_seconds +
  ((frame - clip.timeline_in_frame) / fps) * rateOf(clip);

export function eased(u: number, ease: ZoomEase = "in-out") {
  if (ease === "hold") return 0;
  if (ease === "in") return u * u;
  if (ease === "out") return u * (2 - u);
  if (ease === "in-out") return u * u * (3 - 2 * u);
  return u;
}
/** [scale, x, y] at a source second; mirrors zoom_at in core/adapters/camera.py. */
export function zoomAt(zoom: ZoomKey[] | undefined, seconds: number) {
  if (!zoom?.length) return [1, 0.5, 0.5];
  const value = (k: ZoomKey) => [k.scale, k.x, k.y];
  if (seconds < zoom[0].source_seconds) return value(zoom[0]);
  for (let i = 0; i + 1 < zoom.length; i++) {
    const a = zoom[i],
      b = zoom[i + 1];
    if (seconds < b.source_seconds) {
      const k = eased(
        (seconds - a.source_seconds) / (b.source_seconds - a.source_seconds),
        b.ease,
      );
      return value(a).map((v, n) => v + (value(b)[n] - v) * k);
    }
  }
  return value(zoom.at(-1)!);
}

/** Frames before and after the cut; mirrors transition_split in core/adapters/ffmpeg.py. */
export function transitionSplit(frames: number): [number, number] {
  const before = Math.floor(frames / 2);
  return [before, frames - before];
}

/** Extra picture frames [before start, after end] each clip shows for transitions. */
export function clipHandles(clips: Clip[]) {
  const handles = clips.map((): [number, number] => [0, 0]);
  clips.forEach((c, i) => {
    if (!i || !c.transition) return;
    const [before, after] = transitionSplit(c.transition.frames);
    handles[i][0] = before;
    handles[i - 1][1] = after;
  });
  return handles;
}

/**
 * CSS for one side of a transition at progress u (0-1). The preview approximates
 * the FFmpeg xfade look; the incoming clip is drawn above the outgoing one.
 */
export function transitionStyle(
  type: TransitionType,
  u: number,
  incoming: boolean,
): { opacity?: number; transform?: string; clipPath?: string; filter?: string } {
  const peak = 1 - Math.abs(2 * u - 1);
  switch (type) {
    case "fade":
      return incoming ? { opacity: u } : {};
    case "flash":
      return {
        opacity: incoming ? (u >= 0.5 ? 1 : 0) : 1,
        filter: `brightness(${1 + 2.5 * peak})`,
      };
    case "slide-left":
      return { transform: `translateX(${(incoming ? 1 - u : -u) * 100}%)` };
    case "slide-right":
      return { transform: `translateX(${(incoming ? u - 1 : u) * 100}%)` };
    case "slide-up":
      return { transform: `translateY(${(incoming ? 1 - u : -u) * 100}%)` };
    case "wipe-left":
      return incoming ? { clipPath: `inset(0 0 0 ${(1 - u) * 100}%)` } : {};
    case "whip":
      return {
        ...(incoming ? { opacity: u } : {}),
        filter: `blur(${Math.round(18 * peak)}px)`,
      };
  }
}

export const cueLocked = (project: Project, cue: Cue) =>
  project.locks.some(
    (lock) =>
      lock.start < cue.timeline_out_frame && cue.timeline_in_frame < lock.end,
  );

export function captionPattern(query: string, matchCase = false) {
  return query
    ? new RegExp(
        query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"),
        matchCase ? "gu" : "giu",
      )
    : null;
}

export function replaceCaptions(
  project: Project,
  query: string,
  replacement: string,
  matchCase = false,
  cueId?: string,
) {
  const next = clone(project);
  let count = 0,
    lockedCount = 0,
    emptyCount = 0;
  const pattern = captionPattern(query, matchCase);
  if (!pattern) return { project: next, count, lockedCount, emptyCount };
  for (const cue of next.cues) {
    if (cueId && cue.id !== cueId) continue;
    // A callback preserves literal replacement strings such as "$&".
    const changed = cue.text.replace(pattern, () => replacement);
    if (changed === cue.text) continue;
    if (cueLocked(project, cue)) {
      lockedCount++;
      continue;
    }
    if (!changed.trim()) {
      emptyCount++;
      continue;
    }
    cue.text = changed;
    count++;
  }
  return { project: next, count, lockedCount, emptyCount };
}

export function resumeSession(raw: string | null, jobs: { id: string }[]) {
  try {
    const value = JSON.parse(raw ?? "null");
    if (!value || !jobs.some((job) => job.id === value.job)) return null;
    return {
      job: value.job as string,
      frame: Number.isFinite(value.frame)
        ? Math.max(0, Math.round(value.frame))
        : 0,
      tab: ["media", "text", "words", "locks"].includes(value.tab)
        ? (value.tab as string)
        : "media",
      zoom: Number.isFinite(value.zoom)
        ? Math.max(4, Math.min(100, value.zoom))
        : 12,
    };
  } catch {
    return null;
  }
}
export function reflow(
  s: Project,
  clips: Clip[],
  parents: Record<string, string> = {},
) {
  const next = clone(s),
    fps = s.plan.fps;
  let cursor = 0;
  clips.forEach((c) => {
    if (!(rateOf(c) >= MIN_RATE && rateOf(c) <= MAX_RATE))
      throw new Error(`Tốc độ clip phải từ ${MIN_RATE} đến ${MAX_RATE}.`);
    const length = Math.round(
      ((c.source_out_seconds - c.source_in_seconds) * fps) / rateOf(c),
    );
    c.timeline_in_frame = cursor;
    c.timeline_out_frame = cursor + length;
    cursor += length;
  });
  if (!cursor) throw new Error("Timeline cần ít nhất một frame.");
  // A transition belongs to the cut that started its clip: the first clip and
  // new pieces from a split/cut have none, and it must fit both neighbours.
  clips.forEach((c, i) => {
    if (!c.transition) return;
    const parent = parents[c.clip_id];
    if (!i || (parent && parent !== c.clip_id)) {
      delete c.transition;
      return;
    }
    const room = Math.min(
      c.timeline_out_frame - c.timeline_in_frame,
      clips[i - 1].timeline_out_frame - clips[i - 1].timeline_in_frame,
      MAX_TRANSITION_FRAMES,
    );
    if (room < MIN_TRANSITION_FRAMES) delete c.transition;
    else if (c.transition.frames > room) c.transition.frames = room;
  });
  // Anchor every timed visual and cue to its previous source-clip interval.
  // Items spanning a reordered boundary are split, instead of silently covering unrelated footage.
  const retime = <
    T extends {
      id: string;
      timeline_in_frame: number;
      timeline_out_frame: number;
      source_in_seconds?: number;
      type?: string;
    },
  >(
    items: T[],
  ) => {
    const result: T[] = [];
    for (const item of items) {
      const pieces: T[] = [];
      for (const c of clips) {
        const old = s.plan.clips.find(
          (o) => o.clip_id === (parents[c.clip_id] ?? c.clip_id),
        );
        if (!old) continue;
        const a = Math.max(item.timeline_in_frame, old.timeline_in_frame),
          b = Math.min(item.timeline_out_frame, old.timeline_out_frame);
        if (a >= b) continue;
        const sourceA = Math.max(c.source_in_seconds, sourceAt(old, a, fps));
        const sourceB = Math.min(c.source_out_seconds, sourceAt(old, b, fps));
        if (sourceA >= sourceB) continue;
        const part = clone(item);
        part.timeline_in_frame =
          c.timeline_in_frame +
          Math.round(((sourceA - c.source_in_seconds) * fps) / rateOf(c));
        part.timeline_out_frame =
          c.timeline_in_frame +
          Math.round(((sourceB - c.source_in_seconds) * fps) / rateOf(c));
        if (part.type === "video")
          part.source_in_seconds =
            (item.source_in_seconds ?? 0) +
            (old.timeline_in_frame +
              ((sourceA - old.source_in_seconds) * fps) / rateOf(old) -
              item.timeline_in_frame) /
              fps;
        if (part.timeline_out_frame > part.timeline_in_frame) pieces.push(part);
      }
      pieces.sort((a, b) => a.timeline_in_frame - b.timeline_in_frame);
      const merged: T[] = [];
      for (const part of pieces) {
        const last = merged.at(-1);
        const contiguous =
          !last?.type ||
          last.type !== "video" ||
          Math.abs(
            (last.source_in_seconds ?? 0) +
              (last.timeline_out_frame - last.timeline_in_frame) / fps -
              (part.source_in_seconds ?? 0),
          ) < 0.001;
        if (
          last &&
          last.timeline_out_frame === part.timeline_in_frame &&
          contiguous
        )
          last.timeline_out_frame = part.timeline_out_frame;
        else merged.push(part);
      }
      merged.forEach((part, i) => {
        part.id = i === 0 ? item.id : `${item.id}-part-${i}`;
        result.push(part);
        if (i && s.motions[item.id])
          next.motions[part.id] = clone(s.motions[item.id]);
      });
    }
    return result;
  };
  // A one-shot sound keeps its start on the same source moment and is never
  // split; it is dropped when that moment is cut away.
  const anchor = (items: Sfx[]) =>
    items.flatMap((item) => {
      const old = s.plan.clips.find(
        (o) =>
          o.timeline_in_frame <= item.timeline_in_frame &&
          item.timeline_in_frame < o.timeline_out_frame,
      );
      if (!old) return [];
      const source = sourceAt(old, item.timeline_in_frame, fps);
      const c = clips.find(
        (c) =>
          (parents[c.clip_id] ?? c.clip_id) === old.clip_id &&
          c.source_in_seconds - 1e-6 <= source &&
          source < c.source_out_seconds - 1e-6,
      );
      if (!c) return [];
      const start = Math.min(
        c.timeline_out_frame - 1,
        c.timeline_in_frame +
          Math.round(((source - c.source_in_seconds) * fps) / rateOf(c)),
      );
      return [
        {
          ...item,
          timeline_in_frame: start,
          timeline_out_frame: Math.min(
            cursor,
            start + item.timeline_out_frame - item.timeline_in_frame,
          ),
        },
      ];
    });
  next.plan.clips = clips;
  next.plan.duration_frames = cursor;
  next.plan.overlays = retime(s.plan.overlays);
  next.cues = retime(s.cues);
  if (s.plan.audio?.sfx) next.plan.audio.sfx = anchor(s.plan.audio.sfx);
  for (const key of Object.keys(next.motions))
    if (!next.plan.overlays.some((l) => l.id === key)) delete next.motions[key];
  return next;
}

// Editing by transcript. Ranges are [start, end) in source seconds; every
// change goes through reflow so layers, captions, SFX and zoom follow.
type Range = [number, number];
const mid = (w: Word) => (w.start + w.end) / 2;

/** Output frame where a source second plays, or null when it is cut away. */
export function outputFrame(plan: Plan, seconds: number) {
  for (const c of plan.clips)
    if (c.source_in_seconds <= seconds && seconds < c.source_out_seconds)
      return (
        c.timeline_in_frame +
        Math.round(((seconds - c.source_in_seconds) * plan.fps) / rateOf(c))
      );
  return null;
}

/** Cut between word edges at the middle of the surrounding silence. */
export function wordRanges(words: Word[], indices: number[]): Range[] {
  const sorted = [...new Set(indices)].sort((a, b) => a - b),
    ranges: Range[] = [];
  for (let k = 0; k < sorted.length; k++) {
    let j = k;
    while (sorted[j + 1] === sorted[j] + 1) j++;
    const first = words[sorted[k]],
      last = words[sorted[j]];
    const before = words[sorted[k] - 1]?.end ?? first.start - 0.1,
      after = words[sorted[j] + 1]?.start ?? last.end + 0.1;
    ranges.push([
      before <= first.start ? (before + first.start) / 2 : first.start,
      after >= last.end ? (last.end + after) / 2 : last.end,
    ]);
    k = j;
  }
  return ranges;
}

/** Silences longer than minGap, shortened so `keep` seconds remain. */
export function pauseRanges(
  plan: Plan,
  words: Word[],
  minGap = 0.8,
  keep = 0.3,
): Range[] {
  const ranges: Range[] = [];
  for (const c of plan.clips) {
    const spoken = words.filter(
      (w) => c.source_in_seconds <= mid(w) && mid(w) < c.source_out_seconds,
    );
    if (!spoken.length) continue; // a clip without speech is a chosen visual
    const edges: Range[] = [
      [c.source_in_seconds, spoken[0].start],
      ...spoken.slice(1).map((w, i): Range => [spoken[i].end, w.start]),
      [spoken.at(-1)!.end, c.source_out_seconds],
    ];
    edges.forEach(([a, b], i) => {
      if (b - a <= minGap) return;
      const head = i === 0,
        tail = i === edges.length - 1;
      ranges.push([head ? a : a + keep / 2, tail ? b : b - keep / 2]);
    });
  }
  return ranges;
}

/**
 * Ranges a cut may touch without moving an approved region: a cut ripples
 * everything after it, so it must start after the last locked frame.
 */
export function unlockedRanges(project: Project, ranges: Range[]) {
  const guard = Math.max(0, ...project.locks.map((l) => l.end));
  const allowed: Range[] = [];
  let skipped = 0;
  for (const range of ranges) {
    const starts = project.plan.clips
      .filter(
        (c) =>
          range[0] < c.source_out_seconds && c.source_in_seconds < range[1],
      )
      .map((c) => outputFrame(project.plan, Math.max(range[0], c.source_in_seconds))!);
    if (!starts.length) continue;
    if (Math.min(...starts) < guard) skipped++;
    else allowed.push(range);
  }
  return { allowed, skipped };
}

/** Remove source ranges from every clip that plays them. */
export function cutSource(s: Project, ranges: Range[], makeId = uid) {
  const fps = s.plan.fps,
    clips: Clip[] = [],
    parents: Record<string, string> = {};
  for (const c of s.plan.clips) {
    let pieces: Range[] = [[c.source_in_seconds, c.source_out_seconds]];
    for (const [a, b] of ranges)
      pieces = pieces.flatMap(([x, y]): Range[] =>
        b <= x || a >= y
          ? [[x, y]]
          : ([[x, a], [b, y]] as Range[]).filter(([p, q]) => q - p > 1e-6),
      );
    pieces
      .filter(([x, y]) => Math.round(((y - x) * fps) / rateOf(c)) >= 1)
      .forEach(([x, y], i) => {
        const id = i === 0 ? c.clip_id : makeId("clip");
        parents[id] = c.clip_id;
        clips.push({
          ...clone(c),
          clip_id: id,
          source_in_seconds: x,
          source_out_seconds: y,
        });
      });
  }
  if (!clips.length) throw new Error("Không thể cắt bỏ toàn bộ video.");
  return reflow(s, clips, parents);
}

/**
 * Put a cut-away source range back right after the clip that ends before it.
 * Returns null when nothing fits or the insert would move a region before
 * `guard` (the end of the last lock).
 */
export function restoreSource(
  s: Project,
  [a, b]: Range,
  makeId = uid,
  guard = 0,
) {
  const clips = clone(s.plan.clips);
  const before = clips
    .filter((c) => c.source_out_seconds <= a + 1e-6)
    .sort((x, y) => y.source_out_seconds - x.source_out_seconds)[0];
  const anchor =
    before ??
    clips
      .filter((c) => c.source_in_seconds >= b - 1e-6)
      .sort((x, y) => x.source_in_seconds - y.source_in_seconds)[0];
  if (!anchor) return null;
  const index = clips.indexOf(anchor) + (before ? 1 : 0);
  // Never overlap the neighbours in the timeline.
  const start = Math.max(a, before ? before.source_out_seconds : 0),
    next = clips[index],
    end =
      next && next.source_in_seconds >= start
        ? Math.min(b, next.source_in_seconds)
        : b;
  if (Math.round(((end - start) * s.plan.fps) / rateOf(anchor)) < 1)
    return null;
  if ((index ? clips[index - 1].timeline_out_frame : 0) < guard) return null;
  const restored = clone(anchor);
  delete restored.transition;
  clips.splice(index, 0, {
    ...restored,
    clip_id: makeId("clip"),
    source_in_seconds: start,
    source_out_seconds: end,
  });
  return reflow(s, clips);
}

/**
 * After a cut, captions that lost words get the remaining words' text when
 * they still read exactly as the transcript; hand-edited ones are reported.
 */
export function refreshCues(before: Project, after: Project, words: Word[]) {
  const spoken = (project: Project, cue: Cue) =>
    words
      .filter((w) => {
        const f = outputFrame(project.plan, mid(w));
        return f !== null && cue.timeline_in_frame <= f && f < cue.timeline_out_frame;
      })
      .map((w) => w.text);
  const plain = (text: string) => text.split(/\s+/).filter(Boolean).join(" ");
  let review = 0;
  after.cues = after.cues.flatMap((cue) => {
    const old = before.cues.find((c) => c.id === cue.id);
    if (!old) return [cue];
    const was = spoken(before, old),
      now = spoken(after, cue);
    if (was.join(" ") === now.join(" ")) return [cue];
    if (plain(old.text) !== was.join(" ")) {
      review++;
      return [cue];
    }
    return now.length ? [{ ...cue, text: now.join(" ") }] : [];
  });
  return review;
}

/** Caption lines as export and preview draw them: a typed line break is kept, each line wraps greedily. */
export function captionLines(text: string, width: number) {
  const lines: string[] = [];
  for (const part of text.split("\n")) {
    let line = "";
    for (const word of part.split(/\s+/).filter(Boolean)) {
      if (line && line.length + 1 + word.length > width) {
        lines.push(line);
        line = word;
      } else line += (line ? " " : "") + word;
    }
    if (line) lines.push(line);
  }
  return lines;
}

export function lineCount(text: string, width: number) {
  return captionLines(text, width).length;
}

/** Captions for restored words, grouped within the plan's caption limits. */
export function cuesForWords(project: Project, restored: Word[], makeId = uid) {
  const { max_chars, max_lines } = project.plan.captions,
    result: Cue[] = [];
  let group: Word[] = [];
  const flush = () => {
    const first = group[0],
      last = group.at(-1)!;
    const a = outputFrame(project.plan, first.start) ?? outputFrame(project.plan, mid(first)),
      b = outputFrame(project.plan, last.end - 1e-3) ?? outputFrame(project.plan, mid(last));
    if (a !== null && b !== null)
      result.push({
        id: makeId("cue"),
        timeline_in_frame: a,
        timeline_out_frame: Math.max(b, a + 1),
        text: group.map((w) => w.text).join(" "),
      });
    group = [];
  };
  for (const w of restored) {
    const text = [...group, w].map((x) => x.text).join(" ");
    if (
      group.length &&
      (lineCount(text, max_chars) > max_lines || w.end - group[0].start > 2.5)
    )
      flush();
    group.push(w);
  }
  if (group.length) flush();
  return result;
}
