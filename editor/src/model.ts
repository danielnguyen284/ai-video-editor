export type Clip = {
  clip_id: string;
  asset_id: string;
  source_in_seconds: number;
  source_out_seconds: number;
  timeline_in_frame: number;
  timeline_out_frame: number;
  playback_rate: number;
  crop?: { x: number; y: number; width: number; height: number };
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
  template: "KineticScene" | "MetricCard" | "BarChart" | "LowerThird";
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
    fit: "pad" | "crop";
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
    transcript_ref: string;
    items?: any[];
  };
  audio: {
    voice_gain: number;
    music: null | { path: string; gain: number; ducking: boolean };
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
  media: {
    width: number;
    height: number;
    duration_seconds: number;
    has_audio: boolean;
  };
  source: string;
  library: { path: string; name: string; type: string }[];
  setup: any;
  durations?: Record<string, number>;
};
export const mediaUrl = (job: string, path: string, proxy = false) =>
  `/media?job=${encodeURIComponent(job)}&path=${encodeURIComponent(path)}${proxy ? "&proxy=1" : ""}`;
export const uid = (prefix: string) =>
  `${prefix}-${crypto.randomUUID().slice(0, 8)}`;
export const clone = <T>(value: T): T => structuredClone(value);
export function reflow(
  s: Project,
  clips: Clip[],
  parents: Record<string, string> = {},
) {
  const next = clone(s),
    fps = s.plan.fps;
  let cursor = 0;
  clips.forEach((c) => {
    const length = Math.round(
      (c.source_out_seconds - c.source_in_seconds) * fps,
    );
    c.timeline_in_frame = cursor;
    c.timeline_out_frame = cursor + length;
    cursor += length;
  });
  if (!cursor) throw new Error("Timeline cần ít nhất một frame.");
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
        const sourceA = Math.max(
          c.source_in_seconds,
          old.source_in_seconds + (a - old.timeline_in_frame) / fps,
        );
        const sourceB = Math.min(
          c.source_out_seconds,
          old.source_in_seconds + (b - old.timeline_in_frame) / fps,
        );
        if (sourceA >= sourceB) continue;
        const part = clone(item);
        part.timeline_in_frame =
          c.timeline_in_frame +
          Math.round((sourceA - c.source_in_seconds) * fps);
        part.timeline_out_frame =
          c.timeline_in_frame +
          Math.round((sourceB - c.source_in_seconds) * fps);
        if (part.type === "video")
          part.source_in_seconds =
            (item.source_in_seconds ?? 0) +
            (old.timeline_in_frame +
              (sourceA - old.source_in_seconds) * fps -
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
  next.plan.clips = clips;
  next.plan.duration_frames = cursor;
  next.plan.overlays = retime(s.plan.overlays);
  next.cues = retime(s.cues);
  for (const key of Object.keys(next.motions))
    if (!next.plan.overlays.some((l) => l.id === key)) delete next.motions[key];
  return next;
}
