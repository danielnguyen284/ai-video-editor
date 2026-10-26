import React, { useCallback, useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { type PlayerRef } from "@remotion/player";
import {
  ArrowCounterClockwise,
  ArrowClockwise,
  FloppyDisk,
  Export,
  Play,
  Pause,
  Scissors,
  LockKey,
  LockKeyOpen,
  Plus,
  Trash,
  FilmStrip,
  TextT,
  ImageSquare,
  Waveform,
  Stack,
  FolderOpen,
  ArrowUp,
  ArrowDown,
  SlidersHorizontal,
  Check,
  Warning,
  MagicWand,
  CornersOut,
} from "@phosphor-icons/react";
import { StudioPlayer } from "./StudioPlayer";
import {
  clone,
  mediaUrl,
  reflow,
  uid,
  type Project,
  type View,
  type Clip,
  type Layer,
  type Cue,
} from "./model";
import "./style.css";

async function api(path: string, body?: unknown) {
  const response = await fetch(
    "/api/" + path,
    body
      ? {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-AI-Editor": "studio",
          },
          body: JSON.stringify(body),
        }
      : {},
  );
  const data = await response.json();
  if (!response.ok) throw new Error(data.error ?? "Không thể kết nối editor.");
  return data;
}
type Selection = { kind: "clip" | "layer" | "cue"; id: string } | null;
const tc = (frame: number, fps: number) =>
  `${Math.floor(frame / fps / 60)
    .toString()
    .padStart(2, "0")}:${Math.floor((frame / fps) % 60)
    .toString()
    .padStart(2, "0")}:${Math.round(frame % fps)
    .toString()
    .padStart(2, "0")}`;
const number = (e: React.ChangeEvent<HTMLInputElement>) =>
  Number(e.target.value);
function App() {
  const [jobs, setJobs] = useState<any[]>([]),
    [project, setProject] = useState<Project | null>(null),
    [view, setView] = useState<View | null>(null);
  const [selected, setSelected] = useState<Selection>(null),
    [frame, setFrame] = useState(0),
    [playing, setPlaying] = useState(false),
    [zoom, setZoom] = useState(12),
    [tab, setTab] = useState("media");
  const [dirty, setDirty] = useState(false),
    [saving, setSaving] = useState(false),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [task, setTask] = useState<any>(null);
  const [modal, setModal] = useState<"import" | "export" | null>(null),
    [profiles, setProfiles] = useState<any[]>([]),
    [newJob, setNewJob] = useState({
      job: "",
      video: "",
      profile: "",
      brief: "",
    }),
    [setup, setSetup] = useState<Record<string, string>>({});
  const undo = useRef<Project[]>([]),
    redo = useRef<Project[]>([]),
    current = useRef<Project | null>(null),
    generation = useRef(0),
    version = useRef(0),
    pending = useRef<Promise<void> | null>(null),
    player = useRef<PlayerRef>(null),
    canvas = useRef<HTMLDivElement>(null);
  const reloadJobs = () =>
    api("jobs")
      .then(setJobs)
      .catch((e) => setError(e.message));
  useEffect(() => {
    reloadJobs();
    api("profiles").then(setProfiles);
  }, []);
  const open = async (job: string) => {
    try {
      if (
        dirty &&
        !window.confirm("Draft chưa lưu. Bỏ thay đổi chưa lưu để mở job khác?")
      )
        return;
      const data = await api("project?job=" + encodeURIComponent(job));
      const { media, source, library, setup, durations, ...state } = data;
      current.current = state;
      version.current = state.version;
      generation.current++;
      undo.current = [];
      redo.current = [];
      setProject(state);
      setView({ media, source, library, setup, durations });
      setSelected(null);
      setFrame(0);
      setDirty(false);
      setError("");
      setNotice("Đang xem draft • bản nguồn " + state.base_revision);
    } catch (e: any) {
      setError(e.message);
    }
  };
  const change = useCallback(
    (mutate: (s: Project) => void | Project, history = true) => {
      const old = current.current;
      if (!old) return;
      const value = clone(old);
      let result: Project;
      try {
        result = mutate(value) ?? value;
      } catch (e: any) {
        setError(e.message);
        return;
      }
      if (history) {
        undo.current.push(clone(old));
        if (undo.current.length > 100) undo.current.shift();
        redo.current = [];
      }
      current.current = result;
      generation.current++;
      setProject(result);
      setDirty(true);
      setError("");
    },
    [],
  );
  const save = useCallback(async () => {
    if (pending.current) await pending.current;
    if (!current.current) return;
    const run = async () => {
      setSaving(true);
      try {
        const gen = generation.current,
          snapshot = clone(current.current!);
        snapshot.version = version.current;
        const result: Project = await api("project", {
          job: snapshot.job_id,
          state: snapshot,
          expected_version: version.current,
        });
        version.current = result.version;
        const merged = {
          ...current.current!,
          version: result.version,
          updated_at: result.updated_at,
          locks: result.locks,
        };
        current.current = merged;
        setProject(merged);
        if (gen === generation.current) setDirty(false);
        setError("");
      } catch (e: any) {
        setError(e.message);
        throw e;
      } finally {
        setSaving(false);
      }
    };
    const promise = run();
    pending.current = promise;
    try {
      await promise;
    } finally {
      pending.current = null;
    }
  }, []);
  useEffect(() => {
    if (!dirty) return;
    const timer = setTimeout(() => {
      save().catch(() => {});
    }, 1100);
    return () => clearTimeout(timer);
  }, [project, dirty, save]);
  const history = (direction: "undo" | "redo") => {
    const from = direction === "undo" ? undo : redo,
      to = direction === "undo" ? redo : undo;
    const previous = from.current.pop();
    if (previous && current.current) {
      to.current.push(clone(current.current));
      previous.version = version.current;
      previous.locks = current.current.locks;
      current.current = previous;
      generation.current++;
      setProject(previous);
      setDirty(true);
      setError("");
    }
  };
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)) return;
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") {
        e.preventDefault();
        history(e.shiftKey ? "redo" : "undo");
      }
      if (e.code === "Space") {
        e.preventDefault();
        player.current?.toggle();
      }
      if (e.key === "ArrowRight")
        player.current?.seekTo((player.current?.getCurrentFrame() ?? 0) + 1);
      if (e.key === "ArrowLeft")
        player.current?.seekTo(
          Math.max(0, (player.current?.getCurrentFrame() ?? 0) - 1),
        );
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, []);
  useEffect(() => {
    const warn = (e: BeforeUnloadEvent) => {
      if (dirty) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);
  useEffect(() => {
    const p = player.current;
    if (!p) return;
    const tick = (e: any) => setFrame(e.detail.frame);
    const play = () => setPlaying(true),
      pause = () => setPlaying(false);
    p.addEventListener("frameupdate", tick);
    p.addEventListener("play", play);
    p.addEventListener("pause", pause);
    return () => {
      p.removeEventListener("frameupdate", tick);
      p.removeEventListener("play", play);
      p.removeEventListener("pause", pause);
    };
  }, [project?.job_id]);
  useEffect(() => {
    if (!task?.id || task.status !== "running") return;
    const id = setInterval(async () => {
      try {
        const result = await api("task?id=" + task.id);
        setTask({ id: task.id, ...result });
        if (result.status === "complete") {
          reloadJobs();
          setNotice("Đã xuất " + result.revision + " • " + result.path);
        }
        if (result.status === "error") setError(result.message);
      } catch (e: any) {
        setError(e.message);
      }
    }, 1200);
    return () => clearInterval(id);
  }, [task?.id, task?.status]);
  const p = project?.plan,
    fps = p?.fps ?? 30;
  const item =
    project && selected
      ? selected.kind === "clip"
        ? p!.clips.find((c) => c.clip_id === selected.id)
        : selected.kind === "layer"
          ? p!.overlays.find((l) => l.id === selected.id)
          : project.cues.find((c) => c.id === selected.id)
      : null;
  const locked = !!(
    project &&
    item &&
    project.locks.some(
      (l) =>
        l.start < item.timeline_out_frame && item.timeline_in_frame < l.end,
    )
  );
  const seek = (f: number) => {
    const v = Math.max(
      0,
      Math.min((p?.duration_frames ?? 1) - 1, Math.round(f)),
    );
    player.current?.seekTo(v);
    setFrame(v);
  };
  const patchItem = (data: any) =>
    change((s) => {
      if (!selected) return;
      if (selected.kind === "clip") {
        const clips = clone(s.plan.clips),
          c = clips.find((c) => c.clip_id === selected.id)!;
        Object.assign(c, data);
        return reflow(s, clips);
      }
      const array = selected.kind === "layer" ? s.plan.overlays : s.cues;
      Object.assign(array.find((i) => i.id === selected.id)!, data);
    });
  const remove = () => {
    if (!selected) return;
    change((s) => {
      if (selected.kind === "clip") {
        if (s.plan.clips.length === 1)
          throw new Error("Không thể xóa clip cuối.");
        return reflow(
          s,
          clone(s.plan.clips).filter((c) => c.clip_id !== selected.id),
        );
      }
      if (selected.kind === "layer") {
        s.plan.overlays = s.plan.overlays.filter((l) => l.id !== selected.id);
        delete s.motions[selected.id];
      } else s.cues = s.cues.filter((c) => c.id !== selected.id);
    });
    setSelected(null);
  };
  const split = () => {
    if (!project) return;
    const c = p!.clips.find(
      (c) => c.timeline_in_frame < frame && frame < c.timeline_out_frame,
    );
    if (!c) return;
    const second = uid("clip"),
      at = c.source_in_seconds + (frame - c.timeline_in_frame) / fps;
    change((s) => {
      const list = clone(s.plan.clips),
        index = list.findIndex((x) => x.clip_id === c.clip_id);
      list.splice(
        index,
        1,
        { ...c, source_out_seconds: at },
        { ...c, clip_id: second, source_in_seconds: at },
      );
      return reflow(s, list, { [second]: c.clip_id });
    });
    setSelected({ kind: "clip", id: second });
  };
  const moveClip = (delta: number) => {
    if (!selected) return;
    change((s) => {
      const list = clone(s.plan.clips),
        index = list.findIndex((c) => c.clip_id === selected.id);
      if (index + delta < 0 || index + delta >= list.length) return;
      [list[index], list[index + delta]] = [list[index + delta], list[index]];
      return reflow(s, list);
    });
  };
  const toggleLock = async () => {
    if (!project || !item) return;
    try {
      await save();
      const s = current.current!;
      const existing = s.locks.filter(
        (l) =>
          l.start < item.timeline_out_frame && item.timeline_in_frame < l.end,
      );
      let response: Project;
      if (existing.length) {
        response = s;
        for (const lock of existing)
          response = await api("unlock", { job: s.job_id, id: lock.id });
      } else
        response = await api("lock", {
          job: s.job_id,
          start: item.timeline_in_frame,
          end: item.timeline_out_frame,
          label:
            selected?.kind === "cue"
              ? (item as Cue).text
              : "Cảnh " + tc(item.timeline_in_frame, fps),
          expected_version: version.current,
        });
      current.current = { ...s, locks: response.locks };
      setProject(current.current);
      setNotice(
        existing.length
          ? "Đã mở khóa vùng được chọn."
          : "Đã khóa mọi lớp trong vùng được chọn.",
      );
    } catch (e: any) {
      setError(e.message);
    }
  };
  const addLayer = (asset: View["library"][number]) => {
    if (!project) return;
    if (asset.type === "audio") {
      change((s) => {
        s.plan.audio.music = { path: asset.path, gain: 0.08, ducking: true };
      });
      return;
    }
    const id = uid("layer");
    change((s) => {
      s.plan.overlays.push({
        id,
        type: asset.type === "image" ? "image" : "video",
        path: asset.path,
        timeline_in_frame: frame,
        timeline_out_frame: Math.min(s.plan.duration_frames, frame + fps * 3),
        x: Math.round(s.plan.export.width * 0.1),
        y: Math.round(s.plan.export.height * 0.2),
        width: Math.round(s.plan.export.width * 0.8),
        height: Math.round(s.plan.export.height * 0.35),
        fit: "contain",
      });
    });
    setSelected({ kind: "layer", id });
  };
  const addMotion = () => {
    if (!project || !view) return;
    if (p!.duration_frames - frame < 2 * fps) {
      setError(
        "Cần ít nhất 2 giây còn lại để thêm KineticScene. Di chuyển playhead về trước.",
      );
      return;
    }
    const id = uid("motion"),
      frames = Math.min(p!.duration_frames - frame, fps * 4);
    change((s) => {
      s.plan.overlays.push({
        id,
        type: "video",
        path: view.source,
        timeline_in_frame: frame,
        timeline_out_frame: frame + frames,
        x: 0,
        y: 0,
        width: s.plan.export.width,
        height: s.plan.export.height,
        fit: "contain",
      });
      s.motions[id] = {
        template: "KineticScene",
        width: 720,
        height: 1280,
        fps,
        duration_frames: frames,
        props: {
          title: "Một ý quan trọng",
          emphasis: "Bắt đầu từ đây",
          theme: "dark",
          accent: "#A6EDBC",
          layout: "stack",
          cards: [
            {
              label: "Bước đầu tiên",
              detail: "Chỉnh nội dung theo video của bạn",
            },
          ],
        },
      };
    });
    setSelected({ kind: "layer", id });
    seek(frame + Math.min(24, frames - 1));
  };
  const addCue = () => {
    const id = uid("cue");
    change((s) => {
      s.cues.push({
        id,
        timeline_in_frame: frame,
        timeline_out_frame: Math.min(s.plan.duration_frames, frame + fps * 2),
        text: "Nội dung mới",
      });
      s.plan.captions.enabled = true;
    });
    setSelected({ kind: "cue", id });
  };
  const timelineWidth = Math.max(740, ((p?.duration_frames ?? 0) / fps) * zoom);
  const drag = (
    e: React.PointerEvent,
    kind: "layer" | "cue",
    id: string,
    edge: "move" | "start" | "end",
  ) => {
    e.stopPropagation();
    if (e.button !== 0 || !project) return;
    const start = e.clientX,
      original = clone(project),
      list = kind === "layer" ? original.plan.overlays : original.cues,
      entry = list.find((l) => l.id === id)!;
    if (
      original.locks.some(
        (l) =>
          l.start < entry.timeline_out_frame && entry.timeline_in_frame < l.end,
      )
    )
      return;
    setSelected({ kind, id });
    e.currentTarget.setPointerCapture(e.pointerId);
    let moved = false;
    const target = e.currentTarget;
    const move = (event: PointerEvent) => {
      const delta = Math.round(
        ((event.clientX - start) / timelineWidth) *
          original.plan.duration_frames,
      );
      if (!delta && !moved) return;
      if (!moved) {
        undo.current.push(clone(original));
        redo.current = [];
        moved = true;
      }
      change((s) => {
        const value = (kind === "layer" ? s.plan.overlays : s.cues).find(
          (l) => l.id === id,
        )!;
        if (edge === "move") {
          const length = entry.timeline_out_frame - entry.timeline_in_frame;
          value.timeline_in_frame = Math.max(
            0,
            Math.min(
              original.plan.duration_frames - length,
              entry.timeline_in_frame + delta,
            ),
          );
          value.timeline_out_frame = value.timeline_in_frame + length;
        } else if (edge === "start")
          value.timeline_in_frame = Math.max(
            0,
            Math.min(
              entry.timeline_out_frame - 1,
              entry.timeline_in_frame + delta,
            ),
          );
        else
          value.timeline_out_frame = Math.min(
            original.plan.duration_frames,
            Math.max(
              entry.timeline_in_frame + 1,
              entry.timeline_out_frame + delta,
            ),
          );
      }, false);
    };
    const end = () => {
      target.removeEventListener("pointermove", move as any);
      target.removeEventListener("pointerup", end);
      target.removeEventListener("pointercancel", end);
    };
    target.addEventListener("pointermove", move as any);
    target.addEventListener("pointerup", end);
    target.addEventListener("pointercancel", end);
  };
  const dragClip = (
    e: React.PointerEvent,
    id: string,
    edge: "start" | "end",
  ) => {
    e.stopPropagation();
    if (!project || !view) return;
    const original = clone(project),
      entry = original.plan.clips.find((c) => c.clip_id === id)!;
    if (
      original.locks.some(
        (l) =>
          l.start < entry.timeline_out_frame && entry.timeline_in_frame < l.end,
      )
    )
      return;
    const start = e.clientX,
      target = e.currentTarget;
    target.setPointerCapture(e.pointerId);
    setSelected({ kind: "clip", id });
    undo.current.push(original);
    redo.current = [];
    const move = (event: PointerEvent) => {
      const delta =
        Math.round(
          ((event.clientX - start) / timelineWidth) *
            original.plan.duration_frames,
        ) / fps;
      const list = clone(original.plan.clips),
        c = list.find((c) => c.clip_id === id)!;
      if (edge === "start")
        c.source_in_seconds = Math.max(
          0,
          Math.min(
            c.source_out_seconds - 1 / fps,
            entry.source_in_seconds + delta,
          ),
        );
      else
        c.source_out_seconds = Math.min(
          view.media.duration_seconds,
          Math.max(
            c.source_in_seconds + 1 / fps,
            entry.source_out_seconds + delta,
          ),
        );
      change(() => reflow(original, list), false);
    };
    const end = () => {
      target.removeEventListener("pointermove", move as any);
      target.removeEventListener("pointerup", end);
      target.removeEventListener("pointercancel", end);
    };
    target.addEventListener("pointermove", move as any);
    target.addEventListener("pointerup", end);
    target.addEventListener("pointercancel", end);
  };
  const dragCanvas = (e: React.PointerEvent) => {
    if (
      !selected ||
      selected.kind !== "layer" ||
      !project ||
      locked ||
      !canvas.current
    )
      return;
    e.preventDefault();
    const resizing = (e.target as HTMLElement).dataset.resize === "1";
    const layer = clone(item as Layer),
      startX = e.clientX,
      startY = e.clientY,
      rect = canvas.current.getBoundingClientRect(),
      original = clone(project);
    e.currentTarget.setPointerCapture(e.pointerId);
    undo.current.push(original);
    redo.current = [];
    const target = e.currentTarget;
    const move = (event: PointerEvent) =>
      change((s) => {
        const l = s.plan.overlays.find((x) => x.id === layer.id)!;
        if (resizing) {
          l.width = Math.max(
            16,
            Math.min(
              p!.export.width - l.x,
              Math.round(
                layer.width +
                  ((event.clientX - startX) / rect.width) * p!.export.width,
              ),
            ),
          );
          l.height = Math.max(
            16,
            Math.min(
              p!.export.height - l.y,
              Math.round(
                layer.height +
                  ((event.clientY - startY) / rect.height) * p!.export.height,
              ),
            ),
          );
        } else {
          l.x = Math.max(
            0,
            Math.min(
              p!.export.width - l.width,
              Math.round(
                layer.x +
                  ((event.clientX - startX) / rect.width) * p!.export.width,
              ),
            ),
          );
          l.y = Math.max(
            0,
            Math.min(
              p!.export.height - l.height,
              Math.round(
                layer.y +
                  ((event.clientY - startY) / rect.height) * p!.export.height,
              ),
            ),
          );
        }
      }, false);
    const end = () => {
      target.removeEventListener("pointermove", move as any);
      target.removeEventListener("pointerup", end);
    };
    target.addEventListener("pointermove", move as any);
    target.addEventListener("pointerup", end);
  };
  const exportVideo = async () => {
    if (!project || !view) return;
    try {
      await save();
      const s = current.current!;
      let answers: any = null;
      if (view.setup.status !== "selected") {
        if (setup.processing?.startsWith("Dùng Footage"))
          throw new Error(
            "Footage Analyst được chạy qua AI/CLI trước. Chọn chế độ phân tích với AI, rồi mở lại draft có kết quả; editor không tự phân tích hình.",
          );
        if (
          !setup.editing ||
          !setup.research ||
          !setup.visuals ||
          !setup.audio ||
          !setup.processing
        )
          throw new Error("Hãy chọn các mục thiết lập còn trống.");
        const profile = profiles.find(
          (x) => x.id === jobs.find((j) => j.id === s.job_id)?.profile,
        );
        answers = {
          style: profile.skills.style.id,
          domain: profile.skills.domain.id,
          output: s.plan.export,
          footage_analysis: false,
          transcription: false,
          captions: s.plan.captions.enabled,
          editing: setup.editing,
          research: setup.research,
          visuals: setup.visuals,
          audio: setup.audio,
        };
      }
      const result = await api("export", {
        job: s.job_id,
        expected_version: version.current,
        setup: answers,
      });
      setTask({
        id: result.task,
        status: "running",
        message: "Đang chuẩn bị xuất…",
      });
      if (answers)
        setView((v) =>
          v ? { ...v, setup: { status: "selected", answers } } : v,
        );
      setModal(null);
    } catch (e: any) {
      setError(e.message);
    }
  };
  const motion =
    project && selected?.kind === "layer" ? project.motions[selected.id] : null;
  const patchMotion = (props: any) =>
    change((s) => {
      const content = s.motions[selected!.id].props;
      for (const [key, value] of Object.entries(props)) {
        if (
          value === undefined ||
          (value === "" && !["title", "value"].includes(key))
        )
          delete content[key];
        else content[key] = value;
      }
    });
  const selectItem = (
    kind: NonNullable<Selection>["kind"],
    id: string,
    start: number,
  ) => {
    setSelected({ kind, id });
    const layer =
      kind === "layer" ? project?.plan.overlays.find((l) => l.id === id) : null;
    seek(
      layer && project?.motions[id]
        ? Math.min(layer.timeline_out_frame - 1, start + 24)
        : start,
    );
  };
  return (
    <main className="studio">
      <header className="topbar">
        <a className="brand" href="/" aria-label="AI Editor Studio">
          <span className="brand-mark">
            <FilmStrip size={21} weight="duotone" />
          </span>
          <span>
            AI EDITOR <b>STUDIO</b>
          </span>
        </a>
        <div className="project-picker">
          <FolderOpen size={18} />
          <select
            aria-label="Chọn project"
            value={project?.job_id ?? ""}
            onChange={(e) => open(e.target.value)}
          >
            <option value="">Mở project…</option>
            {jobs.map((j) => (
              <option key={j.id} value={j.id}>
                {j.id}
              </option>
            ))}
          </select>
          <button title="Tạo project" onClick={() => setModal("import")}>
            <Plus size={18} />
          </button>
          {project && (
            <select
              className="revision-picker"
              aria-label="Mở revision"
              value={project.base_revision}
              onFocus={() => reloadJobs()}
              onChange={async (e) => {
                const revision = e.target.value;
                try {
                  await save();
                  await api("checkout", {
                    job: project.job_id,
                    revision,
                    expected_version: version.current,
                  });
                  setDirty(false);
                  const data = await api(
                    "project?job=" + encodeURIComponent(project.job_id),
                  );
                  const { media, source, library, setup, durations, ...state } =
                    data;
                  current.current = state;
                  version.current = state.version;
                  undo.current = [];
                  redo.current = [];
                  setProject(state);
                  setView({ media, source, library, setup, durations });
                  setSelected(null);
                  seek(0);
                  setNotice("Đã mở " + revision + "; các vùng khóa được giữ.");
                } catch (e: any) {
                  setError(e.message);
                }
              }}
            >
              {(jobs.find((j) => j.id === project.job_id)?.revisions ?? []).map(
                (r: string) => (
                  <option key={r}>{r}</option>
                ),
              )}
            </select>
          )}
        </div>
        <div className="top-status">
          {project ? (
            <>
              <i className={dirty ? "dirty" : ""} />
              {saving
                ? "Đang lưu…"
                : dirty
                  ? "Có thay đổi chưa lưu"
                  : "Đã lưu trên máy"}
              <span className="divider" />
              {project.base_revision} · draft {project.version}
            </>
          ) : (
            "Local workspace"
          )}
        </div>
        <div className="top-actions">
          <button
            title="Hoàn tác Ctrl+Z"
            disabled={!undo.current.length}
            onClick={() => history("undo")}
          >
            <ArrowCounterClockwise size={18} />
          </button>
          <button
            title="Làm lại Ctrl+Shift+Z"
            disabled={!redo.current.length}
            onClick={() => history("redo")}
          >
            <ArrowClockwise size={18} />
          </button>
          <button
            disabled={!project || saving}
            onClick={() => save().catch(() => {})}
          >
            <FloppyDisk size={17} />
            Lưu
          </button>
          <button
            className="primary"
            disabled={!project || task?.status === "running"}
            onClick={() => setModal("export")}
          >
            <Export size={17} />
            Xuất MP4
          </button>
        </div>
      </header>
      {error && (
        <div role="alert" className="banner error">
          <Warning size={18} />
          <span>{error}</span>
          <button onClick={() => setError("")}>Đóng</button>
        </div>
      )}
      {task?.status === "running" && (
        <div className="banner progress">
          <span className="spinner" />
          {task.message}
        </div>
      )}
      <section className="workspace">
        <aside className="library">
          <div className="panel-head">
            <span>TÀI NGUYÊN</span>
            <button
              title="Nhập tài nguyên từ đường dẫn trên máy"
              disabled={!project}
              onClick={async () => {
                const path = window.prompt(
                  "Đường dẫn đầy đủ đến ảnh, video hoặc nhạc trên máy:",
                );
                if (path)
                  try {
                    const data = await api("asset", {
                      job: project!.job_id,
                      path,
                    });
                    setView((v) => (v ? { ...v, library: data.library } : v));
                  } catch (e: any) {
                    setError(e.message);
                  }
              }}
            >
              <Plus size={17} />
            </button>
          </div>
          <nav className="library-tabs">
            <button
              className={tab === "media" ? "active" : ""}
              onClick={() => setTab("media")}
            >
              <ImageSquare size={17} />
              Media
            </button>
            <button
              className={tab === "text" ? "active" : ""}
              onClick={() => setTab("text")}
            >
              <TextT size={17} />
              Chữ
            </button>
            <button
              className={tab === "locks" ? "active" : ""}
              onClick={() => setTab("locks")}
            >
              <LockKey size={17} />
              Đã khóa
            </button>
          </nav>
          {!project ? (
            <div className="empty-side">
              <FolderOpen size={32} />
              <p>Mở một job đã có hoặc tạo project từ video trên máy.</p>
              <button onClick={() => setModal("import")}>Tạo project</button>
            </div>
          ) : tab === "media" ? (
            <>
              <p className="aside-help">
                Bấm tài nguyên để thêm vào vị trí playhead.
              </p>
              <div className="asset-list">
                {view?.library.map((a) => (
                  <button
                    className="asset"
                    key={a.path}
                    title={a.path}
                    onClick={() => addLayer(a)}
                  >
                    <span className={"asset-icon " + a.type}>
                      {a.type === "image" ? (
                        <ImageSquare size={22} />
                      ) : a.type === "audio" ? (
                        <Waveform size={22} />
                      ) : (
                        <FilmStrip size={22} />
                      )}
                    </span>
                    <span>
                      <strong>
                        {a.path === view.source ? "Video gốc" : a.name}
                      </strong>
                      <small>
                        {a.type === "audio"
                          ? "Nhạc nền"
                          : a.path === view.source
                            ? "Nguồn · giữ nguyên file gốc"
                            : a.type === "image"
                              ? "Ảnh · thêm lớp"
                              : "Video · thêm lớp"}
                      </small>
                    </span>
                    <Plus size={15} />
                  </button>
                ))}
              </div>
              <button className="motion-add" onClick={addMotion}>
                <MagicWand size={22} />
                <span>
                  <strong>Kinetic motion</strong>
                  <small>Chữ lớn · thẻ · progress</small>
                </span>
                <Plus size={16} />
              </button>
            </>
          ) : tab === "text" ? (
            <>
              <button className="wide" onClick={addCue}>
                <Plus size={18} />
                Thêm caption tại playhead
              </button>
              <label className="toggle">
                <input
                  type="checkbox"
                  checked={p!.captions.enabled}
                  onChange={(e) =>
                    change((s) => {
                      s.plan.captions.enabled = e.target.checked;
                    })
                  }
                />
                Hiện caption
              </label>
              <div className="cue-list">
                {project.cues.map((c) => (
                  <button
                    key={c.id}
                    className={selected?.id === c.id ? "active" : ""}
                    onClick={() => selectItem("cue", c.id, c.timeline_in_frame)}
                  >
                    <small>{tc(c.timeline_in_frame, fps)}</small>
                    <span>{c.text}</span>
                  </button>
                ))}
              </div>
            </>
          ) : (
            <>
              <p className="aside-help">
                Vùng đã khóa được bảo vệ ở mọi lớp, kể cả khi sửa bằng AI hoặc
                CLI.
              </p>
              {project.locks.length ? (
                project.locks.map((l) => (
                  <div className="lock-entry" key={l.id}>
                    <LockKey size={18} />
                    <span>
                      <strong>{l.label}</strong>
                      <small>
                        {tc(l.start, fps)} — {tc(l.end, fps)}
                      </small>
                    </span>
                    <button
                      title="Mở khóa"
                      onClick={async () => {
                        try {
                          await save();
                          const data = await api("unlock", {
                            job: project.job_id,
                            id: l.id,
                          });
                          current.current = {
                            ...current.current!,
                            locks: data.locks,
                          };
                          setProject(current.current);
                        } catch (e: any) {
                          setError(e.message);
                        }
                      }}
                    >
                      <LockKeyOpen size={18} />
                    </button>
                  </div>
                ))
              ) : (
                <p className="aside-help">
                  Chọn clip, caption hoặc layer rồi bấm Khóa vùng.
                </p>
              )}
            </>
          )}
          <div className="library-footer">
            <span className="local-dot" />
            Media ở trên máy của bạn
          </div>
        </aside>
        <section className="viewer">
          <div className="viewer-head">
            <span>PREVIEW</span>
            {p && (
              <span>
                {p.export.width} × {p.export.height} <i>·</i> {fps} fps
              </span>
            )}
            <span className="live-label">Xem trực tiếp</span>
            <button
              title="Xem toàn màn hình"
              disabled={!project}
              onClick={() => player.current?.requestFullscreen()}
            >
              <CornersOut size={17} />
            </button>
          </div>
          <div className="stage">
            {project && view ? (
              <div
                className="canvas"
                ref={canvas}
                style={{
                  aspectRatio: `${p!.export.width}/${p!.export.height}`,
                }}
              >
                <StudioPlayer
                  key={project.job_id}
                  playerRef={player}
                  project={project}
                  view={view}
                />
                {selected?.kind === "layer" &&
                  item &&
                  item.timeline_in_frame <= frame &&
                  frame < item.timeline_out_frame && (
                    <div
                      className={"selection-box " + (locked ? "locked" : "")}
                      onPointerDown={dragCanvas}
                      style={{
                        left: `${((item as Layer).x / p!.export.width) * 100}%`,
                        top: `${((item as Layer).y / p!.export.height) * 100}%`,
                        width: `${((item as Layer).width / p!.export.width) * 100}%`,
                        height: `${((item as Layer).height / p!.export.height) * 100}%`,
                      }}
                    >
                      <span>{locked ? "Đã khóa" : "Kéo để di chuyển"}</span>
                      <i />
                      <i />
                      <i />
                      <i data-resize="1" title="Kéo để đổi kích thước" />
                    </div>
                  )}
              </div>
            ) : (
              <div className="welcome">
                <span className="welcome-kicker">KHÔNG GIAN DỰNG CỦA BẠN</span>
                <h1>
                  Dựng nháp bằng AI.
                  <br />
                  Hoàn thiện theo ý bạn.
                </h1>
                <p>
                  Xem trực tiếp, sửa từng lớp và khóa những đoạn đã ưng.
                  <br />
                  Chỉ xuất video khi bạn sẵn sàng.
                </p>
                <button className="primary" onClick={() => setModal("import")}>
                  <Plus size={18} />
                  Bắt đầu từ video
                </button>
                {jobs.length > 0 && (
                  <button className="recent" onClick={() => open(jobs[0].id)}>
                    Mở {jobs[0].id} <span>→</span>
                  </button>
                )}
              </div>
            )}
          </div>
          <div className="transport">
            <span className="timecode">
              {tc(frame, fps)} <i>/ {tc(p?.duration_frames ?? 0, fps)}</i>
            </span>
            <div>
              <button
                title="Lùi một frame"
                disabled={!project}
                onClick={() => seek(frame - 1)}
              >
                −1f
              </button>
              <button
                className="play"
                title="Phát / dừng (Space)"
                disabled={!project}
                onClick={() => player.current?.toggle()}
              >
                {playing ? (
                  <Pause weight="fill" size={19} />
                ) : (
                  <Play weight="fill" size={19} />
                )}
              </button>
              <button
                title="Tiến một frame"
                disabled={!project}
                onClick={() => seek(frame + 1)}
              >
                +1f
              </button>
            </div>
            <span className="preview-note">Preview · chưa encode MP4</span>
          </div>
        </section>
        <aside className="inspector">
          <div className="panel-head">
            <span>THUỘC TÍNH</span>
            <SlidersHorizontal size={17} />
          </div>
          {project && p ? (
            <>
              {item && selected ? (
                <>
                  <div className="selection-title">
                    <span>
                      {selected.kind === "clip"
                        ? "Clip gốc"
                        : selected.kind === "cue"
                          ? "Caption"
                          : (motion?.template ?? "Lớp hình")}
                    </span>
                    <div>
                      <button
                        title="Khóa toàn bộ vùng này"
                        className={locked ? "is-locked" : ""}
                        onClick={toggleLock}
                      >
                        {locked ? (
                          <LockKey weight="fill" size={19} />
                        ) : (
                          <LockKeyOpen size={19} />
                        )}
                      </button>
                      <button
                        title="Xóa phần đã chọn"
                        disabled={
                          locked ||
                          (selected.kind === "clip" && p.clips.length === 1)
                        }
                        onClick={remove}
                      >
                        <Trash size={18} />
                      </button>
                    </div>
                  </div>
                  <button
                    className={"lock-action " + (locked ? "is-locked" : "")}
                    onClick={toggleLock}
                  >
                    {locked ? <LockKey size={16} /> : <LockKeyOpen size={16} />}{" "}
                    {locked ? "Mở khóa vùng" : "Khóa vùng đã ưng"}
                  </button>
                  <fieldset disabled={locked}>
                    <h3>Thời gian</h3>
                    {selected.kind === "clip" ? (
                      <>
                        <div className="field-grid">
                          <Field label="Nguồn vào (giây)">
                            <input
                              type="number"
                              step={1 / fps}
                              min={0}
                              value={(item as Clip).source_in_seconds}
                              onChange={(e) =>
                                patchItem({ source_in_seconds: number(e) })
                              }
                            />
                          </Field>
                          <Field label="Nguồn ra (giây)">
                            <input
                              type="number"
                              step={1 / fps}
                              max={view?.media.duration_seconds}
                              value={(item as Clip).source_out_seconds}
                              onChange={(e) =>
                                patchItem({ source_out_seconds: number(e) })
                              }
                            />
                          </Field>
                        </div>
                        <div className="button-row">
                          <button
                            disabled={p.clips[0].clip_id === selected.id}
                            onClick={() => moveClip(-1)}
                          >
                            <ArrowUp size={15} />
                            Đưa trước
                          </button>
                          <button
                            disabled={p.clips.at(-1)?.clip_id === selected.id}
                            onClick={() => moveClip(1)}
                          >
                            <ArrowDown size={15} />
                            Đưa sau
                          </button>
                        </div>
                        <p className="field-help">
                          Trim có ripple. Layer và caption được map lại theo
                          clip; kiểm tra chữ tại ranh giới cắt. Vùng khóa sẽ
                          chặn thay đổi ảnh hưởng tới nó.
                        </p>
                        {["x", "y", "width", "height"].map((key) => (
                          <Field key={key} label={"Crop nguồn · " + key}>
                            <input
                              type="number"
                              value={
                                (item as Clip).crop?.[key as "x"] ??
                                (key === "width"
                                  ? view!.media.width
                                  : key === "height"
                                    ? view!.media.height
                                    : 0)
                              }
                              onChange={(e) =>
                                patchItem({
                                  crop: {
                                    x: 0,
                                    y: 0,
                                    width: view!.media.width,
                                    height: view!.media.height,
                                    ...(item as Clip).crop,
                                    [key]: number(e),
                                  },
                                })
                              }
                            />
                          </Field>
                        ))}
                      </>
                    ) : (
                      <div className="field-grid">
                        <Field label="Vào (frame)">
                          <input
                            type="number"
                            value={item.timeline_in_frame}
                            onChange={(e) =>
                              patchItem({ timeline_in_frame: number(e) })
                            }
                          />
                        </Field>
                        <Field label="Ra (frame)">
                          <input
                            type="number"
                            value={item.timeline_out_frame}
                            onChange={(e) =>
                              patchItem({ timeline_out_frame: number(e) })
                            }
                          />
                        </Field>
                      </div>
                    )}
                    {selected.kind === "cue" && (
                      <Field label="Nội dung">
                        <textarea
                          aria-label="Nội dung caption"
                          value={(item as Cue).text}
                          onChange={(e) => patchItem({ text: e.target.value })}
                        />
                      </Field>
                    )}
                    {selected.kind === "layer" && (
                      <>
                        <h3>Vị trí & kích thước</h3>
                        <div className="field-grid">
                          {["x", "y", "width", "height"].map((key) => (
                            <Field key={key} label={key}>
                              <input
                                type="number"
                                value={(item as any)[key]}
                                onChange={(e) =>
                                  patchItem({ [key]: number(e) })
                                }
                              />
                            </Field>
                          ))}
                        </div>
                        <Field label="Cách đặt hình">
                          <select
                            value={(item as Layer).fit}
                            onChange={(e) => patchItem({ fit: e.target.value })}
                          >
                            <option value="contain">Giữ đủ hình</option>
                            <option value="cover">Phủ kín, crop</option>
                            <option value="stretch">Kéo giãn</option>
                          </select>
                        </Field>
                        <Field
                          label={
                            "Độ hiện · " +
                            Math.round(((item as Layer).opacity ?? 1) * 100) +
                            "%"
                          }
                        >
                          <input
                            type="range"
                            min="0"
                            max="1"
                            step="0.01"
                            value={(item as Layer).opacity ?? 1}
                            onChange={(e) => patchItem({ opacity: number(e) })}
                          />
                        </Field>
                        {(item as Layer).type === "video" && (
                          <Field label="Bắt đầu asset (giây)">
                            <input
                              type="number"
                              step="0.1"
                              min="0"
                              value={(item as Layer).source_in_seconds ?? 0}
                              onChange={(e) =>
                                patchItem({ source_in_seconds: number(e) })
                              }
                            />
                          </Field>
                        )}
                        {motion && (
                          <>
                            <h3>{motion.template} · sửa trực tiếp</h3>
                            {[
                              "title",
                              ...(motion.template === "KineticScene"
                                ? ["emphasis", "subtitle"]
                                : motion.template === "MetricCard"
                                  ? ["value", "subtitle"]
                                  : ["subtitle"]),
                              "source",
                            ].map((key) => (
                              <Field key={key} label={key}>
                                <input
                                  aria-label={"Motion " + key}
                                  value={motion.props[key] ?? ""}
                                  onChange={(e) =>
                                    patchMotion({ [key]: e.target.value })
                                  }
                                />
                              </Field>
                            ))}
                            <Field label="Màu nhấn">
                              <input
                                type="color"
                                value={motion.props.accent ?? "#A6EDBC"}
                                onChange={(e) =>
                                  patchMotion({ accent: e.target.value })
                                }
                              />
                            </Field>
                            <Field label="Thời lượng asset (frame)">
                              <input
                                type="number"
                                min={24}
                                value={motion.duration_frames}
                                onChange={(e) =>
                                  change((s) => {
                                    s.motions[selected.id].duration_frames =
                                      number(e);
                                  })
                                }
                              />
                            </Field>
                            {motion.template === "KineticScene" && (
                              <>
                                <Field label="Nền">
                                  <select
                                    value={motion.props.theme ?? "light"}
                                    onChange={(e) =>
                                      patchMotion({ theme: e.target.value })
                                    }
                                  >
                                    <option value="light">Sáng</option>
                                    <option value="dark">Tối</option>
                                  </select>
                                </Field>
                                <label className="toggle">
                                  <input
                                    type="checkbox"
                                    checked={motion.props.transparent ?? false}
                                    onChange={(e) =>
                                      patchMotion({
                                        transparent: e.target.checked,
                                      })
                                    }
                                  />
                                  Nền trong suốt
                                </label>
                                <Field label="Bố cục thẻ">
                                  <select
                                    value={motion.props.layout ?? "stack"}
                                    onChange={(e) =>
                                      patchMotion({ layout: e.target.value })
                                    }
                                  >
                                    <option value="stack">Xếp dọc</option>
                                    <option value="grid">Lưới</option>
                                  </select>
                                </Field>
                                {(motion.props.cards ?? []).map(
                                  (card: any, i: number) => (
                                    <div className="card-editor" key={i}>
                                      <input
                                        aria-label={"Thẻ " + (i + 1)}
                                        value={card.label}
                                        onChange={(e) => {
                                          const cards = clone(
                                            motion.props.cards,
                                          );
                                          cards[i].label = e.target.value;
                                          patchMotion({ cards });
                                        }}
                                      />
                                      <input
                                        aria-label={"Mô tả thẻ " + (i + 1)}
                                        value={card.detail ?? ""}
                                        onChange={(e) => {
                                          const cards = clone(
                                            motion.props.cards,
                                          );
                                          if (e.target.value)
                                            cards[i].detail = e.target.value;
                                          else delete cards[i].detail;
                                          patchMotion({ cards });
                                        }}
                                      />
                                      <button
                                        title="Xóa thẻ"
                                        onClick={() =>
                                          patchMotion({
                                            cards:
                                              motion.props.cards.length > 1
                                                ? motion.props.cards.filter(
                                                    (_: any, index: number) =>
                                                      i !== index,
                                                  )
                                                : undefined,
                                          })
                                        }
                                      >
                                        <Trash size={14} />
                                      </button>
                                    </div>
                                  ),
                                )}
                                {(motion.props.cards?.length ?? 0) < 4 && (
                                  <button
                                    className="wide"
                                    onClick={() =>
                                      patchMotion({
                                        cards: [
                                          ...(motion.props.cards ?? []),
                                          { label: "Ý tiếp theo" },
                                        ],
                                      })
                                    }
                                  >
                                    <Plus size={16} />
                                    Thêm thẻ
                                  </button>
                                )}
                                <label className="toggle">
                                  <input
                                    type="checkbox"
                                    checked={
                                      motion.props.progress !== undefined
                                    }
                                    onChange={(e) =>
                                      patchMotion({
                                        progress: e.target.checked
                                          ? 1
                                          : undefined,
                                      })
                                    }
                                  />
                                  Thanh tiến độ
                                </label>
                                {motion.props.progress !== undefined && (
                                  <input
                                    aria-label="Giá trị progress"
                                    type="range"
                                    min="0"
                                    max="1"
                                    step="0.01"
                                    value={motion.props.progress}
                                    onChange={(e) =>
                                      patchMotion({ progress: number(e) })
                                    }
                                  />
                                )}
                              </>
                            )}
                          </>
                        )}
                      </>
                    )}
                  </fieldset>
                </>
              ) : (
                <div className="inspector-empty">
                  <Stack size={27} />
                  <p>Chọn clip hoặc một lớp trên timeline để chỉnh.</p>
                </div>
              )}
              <div className="project-settings">
                <h3>Khung & caption</h3>
                <Field label="Framing">
                  <select
                    value={p.export.fit}
                    onChange={(e) =>
                      change((s) => {
                        s.plan.export.fit = e.target.value as "pad" | "crop";
                      })
                    }
                  >
                    <option value="pad">Giữ đủ hình / padding</option>
                    <option value="crop">Crop để phủ kín</option>
                  </select>
                </Field>
                <label className="toggle">
                  <input
                    type="checkbox"
                    checked={p.captions.enabled}
                    onChange={(e) =>
                      change((s) => {
                        s.plan.captions.enabled = e.target.checked;
                      })
                    }
                  />
                  Hiện caption
                </label>
                <div className="field-grid">
                  <Field label="Cỡ chữ">
                    <input
                      type="number"
                      min="1"
                      value={p.captions.font_size}
                      onChange={(e) =>
                        change((s) => {
                          s.plan.captions.font_size = number(e);
                        })
                      }
                    />
                  </Field>
                  <Field label="Cách đáy (px)">
                    <input
                      type="number"
                      min="0"
                      value={p.captions.margin_v}
                      onChange={(e) =>
                        change((s) => {
                          s.plan.captions.margin_v = number(e);
                        })
                      }
                    />
                  </Field>
                </div>
                <Field label="Font">
                  <input
                    value={p.captions.font_name}
                    onChange={(e) =>
                      change((s) => {
                        s.plan.captions.font_name = e.target.value;
                      })
                    }
                  />
                </Field>
                <h3>Âm thanh</h3>
                <Field label={"Giọng nói · " + p.audio.voice_gain.toFixed(2)}>
                  <input
                    type="range"
                    min="0"
                    max="2"
                    step="0.01"
                    value={p.audio.voice_gain}
                    onChange={(e) =>
                      change((s) => {
                        s.plan.audio.voice_gain = number(e);
                      })
                    }
                  />
                </Field>
                {p.audio.music ? (
                  <>
                    <Field label="Nhạc nền">
                      <small>{p.audio.music.path}</small>
                      <input
                        aria-label="Âm lượng nhạc"
                        type="range"
                        min="0"
                        max="1"
                        step="0.01"
                        value={p.audio.music.gain}
                        onChange={(e) =>
                          change((s) => {
                            s.plan.audio.music!.gain = number(e);
                          })
                        }
                      />
                    </Field>
                    <label className="toggle">
                      <input
                        type="checkbox"
                        checked={p.audio.music.ducking}
                        onChange={(e) =>
                          change((s) => {
                            s.plan.audio.music!.ducking = e.target.checked;
                          })
                        }
                      />
                      Ducking khi xuất
                    </label>
                    <button
                      className="wide"
                      onClick={() =>
                        change((s) => {
                          s.plan.audio.music = null;
                        })
                      }
                    >
                      Bỏ nhạc nền
                    </button>
                    <p className="field-help">
                      Preview nghe gain tĩnh; ducking được áp khi xuất. Gain
                      giọng trên 1 cũng chỉ áp đầy đủ khi xuất.
                    </p>
                  </>
                ) : (
                  <p className="field-help">
                    Voice-only. Nhập file nhạc rồi bấm vào tài nguyên để thêm.
                  </p>
                )}
              </div>
            </>
          ) : (
            <div className="inspector-empty">
              <SlidersHorizontal size={28} />
              <p>Thuộc tính của phần đang chọn sẽ hiện ở đây.</p>
            </div>
          )}
        </aside>
      </section>
      <section className="timeline">
        <div className="timeline-toolbar">
          <div>
            <span className="timeline-title">TIMELINE</span>
            <button
              disabled={!project}
              onClick={split}
              title="Chia clip tại playhead"
            >
              <Scissors size={18} />
              Chia clip
            </button>
            <button disabled={!item} onClick={toggleLock}>
              {locked ? <LockKey size={16} /> : <LockKeyOpen size={16} />}Khóa
              vùng
            </button>
            <button disabled={!project} onClick={addCue}>
              <TextT size={17} />
              Caption
            </button>
          </div>
          <div>
            <span className="timeline-hint">
              Space phát · ← → từng frame · Ctrl Z hoàn tác
            </span>
            <span className="zoom-label">−</span>
            <input
              aria-label="Zoom timeline"
              type="range"
              min="4"
              max="100"
              value={zoom}
              onChange={(e) => setZoom(number(e))}
            />
            <span>+</span>
          </div>
        </div>
        <div className="timeline-body">
          <div className="track-labels">
            <div className="ruler-label">
              {project
                ? `${(p!.duration_frames / fps).toFixed(1)} giây`
                : "Chưa có project"}
            </div>
            <div>
              <FilmStrip size={17} />
              Video
            </div>
            <div>
              <TextT size={17} />
              Caption
            </div>
            {(p?.overlays ?? []).map((l) => (
              <div key={l.id}>
                <ImageSquare size={17} />
                <span>
                  {project?.motions[l.id]?.template ?? l.id.slice(0, 15)}
                </span>
              </div>
            ))}
            <div>
              <Waveform size={17} />
              Âm thanh
            </div>
            <div>
              <LockKey size={17} />
              Vùng đã duyệt
            </div>
          </div>
          <div className="timeline-scroll">
            <div className="timeline-content" style={{ width: timelineWidth }}>
              <div
                className="ruler"
                onPointerDown={(e) => {
                  if (!p) return;
                  const rect = e.currentTarget.getBoundingClientRect();
                  seek(
                    ((e.clientX - rect.left) / rect.width) * p.duration_frames,
                  );
                }}
              >
                {Array.from({ length: 11 }, (_, i) => (
                  <span key={i} style={{ left: `${i * 10}%` }}>
                    {p
                      ? tc(Math.round((p.duration_frames * i) / 10), fps)
                      : "00:00"}
                  </span>
                ))}
              </div>
              <div className="track video-track">
                {p?.clips.map((c, i) => (
                  <button
                    key={c.clip_id}
                    className={
                      "timeline-item video-item " +
                      (selected?.id === c.clip_id ? "selected" : "")
                    }
                    style={{
                      left: `${(c.timeline_in_frame / p.duration_frames) * 100}%`,
                      width: `${((c.timeline_out_frame - c.timeline_in_frame) / p.duration_frames) * 100}%`,
                    }}
                    onClick={() =>
                      selectItem("clip", c.clip_id, c.timeline_in_frame)
                    }
                  >
                    <i onPointerDown={(e) => dragClip(e, c.clip_id, "start")} />
                    <FilmStrip size={16} />
                    <span>
                      {String(i + 1).padStart(2, "0")} ·{" "}
                      {c.source_in_seconds.toFixed(1)}–
                      {c.source_out_seconds.toFixed(1)}s
                    </span>
                    <i onPointerDown={(e) => dragClip(e, c.clip_id, "end")} />
                  </button>
                ))}
              </div>
              <div
                className={
                  "track " + (!p?.captions.enabled ? "track-disabled" : "")
                }
              >
                {project?.cues.map((c) => (
                  <div
                    key={c.id}
                    role="button"
                    tabIndex={0}
                    aria-label={"Caption: " + c.text}
                    className={
                      "timeline-item cue-item " +
                      (selected?.id === c.id ? "selected" : "")
                    }
                    style={{
                      left: `${(c.timeline_in_frame / p!.duration_frames) * 100}%`,
                      width: `${((c.timeline_out_frame - c.timeline_in_frame) / p!.duration_frames) * 100}%`,
                    }}
                    onClick={() => selectItem("cue", c.id, c.timeline_in_frame)}
                    onPointerDown={(e) => drag(e, "cue", c.id, "move")}
                  >
                    <i onPointerDown={(e) => drag(e, "cue", c.id, "start")} />
                    <span>{c.text}</span>
                    <i onPointerDown={(e) => drag(e, "cue", c.id, "end")} />
                  </div>
                ))}
              </div>
              {p?.overlays.map((l) => (
                <div className="track" key={l.id}>
                  <div
                    role="button"
                    tabIndex={0}
                    aria-label={"Layer: " + l.id}
                    className={
                      "timeline-item layer-item " +
                      (selected?.id === l.id ? "selected" : "")
                    }
                    style={{
                      left: `${(l.timeline_in_frame / p.duration_frames) * 100}%`,
                      width: `${((l.timeline_out_frame - l.timeline_in_frame) / p.duration_frames) * 100}%`,
                    }}
                    onClick={() =>
                      selectItem("layer", l.id, l.timeline_in_frame)
                    }
                    onPointerDown={(e) => drag(e, "layer", l.id, "move")}
                  >
                    <i onPointerDown={(e) => drag(e, "layer", l.id, "start")} />
                    <span>
                      {project!.motions[l.id]?.props.title ??
                        l.path.split("/").at(-1)}
                    </span>
                    <i onPointerDown={(e) => drag(e, "layer", l.id, "end")} />
                  </div>
                </div>
              ))}
              <div className="track audio-track">
                {project && (
                  <div className="audio-wave">
                    <Waveform size={18} />
                    <span>
                      {p?.audio.music
                        ? "Giọng nói + nhạc nền"
                        : "Giọng nói gốc"}
                    </span>
                  </div>
                )}
              </div>
              <div className="track locks-track">
                {project?.locks.map((l) => (
                  <div
                    title={l.label}
                    key={l.id}
                    className="lock-region"
                    style={{
                      left: `${(l.start / p!.duration_frames) * 100}%`,
                      width: `${((l.end - l.start) / p!.duration_frames) * 100}%`,
                    }}
                  >
                    <LockKey size={13} />
                    {l.label}
                  </div>
                ))}
              </div>
              {p && (
                <div
                  className="playhead"
                  style={{ left: `${(frame / p.duration_frames) * 100}%` }}
                >
                  <span />
                </div>
              )}
            </div>
          </div>
        </div>
      </section>
      <footer className="statusbar">
        <span>{notice || "Sẵn sàng"}</span>
        <span>Preview tức thì · lưu draft riêng · bản xuất giữ nguyên</span>
      </footer>
      {modal && (
        <div className="modal-backdrop">
          <section
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-label={modal === "import" ? "Tạo project" : "Xuất MP4"}
          >
            <header>
              <h2>
                {modal === "import"
                  ? "Tạo project từ video"
                  : "Xuất bản dựng đang hiển thị"}
              </h2>
              <button onClick={() => setModal(null)}>Đóng</button>
            </header>
            {modal === "import" ? (
              <>
                <p>
                  File được copy vào job. Chọn style để chuẩn bị draft; bạn có
                  thể sửa trực tiếp trước khi xuất.
                </p>
                <Field label="Tên job">
                  <input
                    placeholder="video-002"
                    value={newJob.job}
                    onChange={(e) =>
                      setNewJob({ ...newJob, job: e.target.value })
                    }
                  />
                </Field>
                <Field label="Đường dẫn video trên máy">
                  <input
                    placeholder="C:\Users\admin\Videos\raw.mp4"
                    value={newJob.video}
                    onChange={(e) =>
                      setNewJob({ ...newJob, video: e.target.value })
                    }
                  />
                </Field>
                <Field label="Profile">
                  <select
                    value={newJob.profile}
                    onChange={(e) =>
                      setNewJob({ ...newJob, profile: e.target.value })
                    }
                  >
                    <option value="">Chọn style & lĩnh vực…</option>
                    {profiles.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.id}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="Mô tả mục tiêu">
                  <textarea
                    value={newJob.brief}
                    onChange={(e) =>
                      setNewJob({ ...newJob, brief: e.target.value })
                    }
                  />
                </Field>
                <button
                  className="primary wide"
                  disabled={!newJob.job || !newJob.video || !newJob.profile}
                  onClick={async () => {
                    try {
                      await api("import", newJob);
                      await reloadJobs();
                      setModal(null);
                      await open(newJob.job);
                    } catch (e: any) {
                      setError(e.message);
                    }
                  }}
                >
                  <Plus size={17} />
                  Tạo draft
                </button>
              </>
            ) : (
              project && (
                <>
                  <p>
                    Bản xuất mới dùng đúng timeline đã lưu và giữ các vùng khóa.
                    Bạn vẫn sửa tiếp được trong draft.
                  </p>
                  <dl className="export-summary">
                    <div>
                      <dt>Video</dt>
                      <dd>
                        {p?.export.width} × {p?.export.height} · {fps} fps
                      </dd>
                    </div>
                    <div>
                      <dt>Độ dài</dt>
                      <dd>{tc(p!.duration_frames, fps)}</dd>
                    </div>
                    <div>
                      <dt>Caption</dt>
                      <dd>
                        {p?.captions.enabled
                          ? `${project.cues.length} cue`
                          : "Tắt"}
                      </dd>
                    </div>
                    <div>
                      <dt>Bảo vệ</dt>
                      <dd>{project.locks.length} vùng khóa</dd>
                    </div>
                  </dl>
                  {view?.setup.status !== "selected" && (
                    <>
                      <h3>Chọn thiết lập cho lần xuất đầu</h3>
                      <Field label="Xử lý footage / lời nói">
                        <select
                          value={setup.processing ?? ""}
                          onChange={(e) =>
                            setSetup({ ...setup, processing: e.target.value })
                          }
                        >
                          <option value="">Chọn…</option>
                          <option>
                            Bỏ Footage Analyst, dùng nguồn/transcript hiện có;
                            không phiên âm mới
                          </option>
                          <option>
                            Dùng Footage Analyst trước khi xuất (qua AI/CLI)
                          </option>
                        </select>
                      </Field>
                      {Object.entries({
                        editing: ["Chỉ các cắt/trim tôi đã đặt trên timeline"],
                        research: [
                          "Dùng tài liệu hiện có, không research thêm",
                          "Không thêm research",
                        ],
                        visuals: ["Dùng đúng các layer tôi đang xem"],
                        audio: [
                          "Dùng đúng voice/gain/nhạc/ducking đang hiển thị",
                        ],
                      }).map(([key, options]) => (
                        <Field
                          key={key}
                          label={
                            {
                              editing: "Cách cắt",
                              research: "Nghiên cứu",
                              visuals: "Hình bổ sung",
                              audio: "Âm thanh",
                            }[key] ?? key
                          }
                        >
                          <select
                            value={setup[key] ?? ""}
                            onChange={(e) =>
                              setSetup({ ...setup, [key]: e.target.value })
                            }
                          >
                            <option value="">Chọn…</option>
                            {options.map((text) => (
                              <option key={text}>{text}</option>
                            ))}
                          </select>
                        </Field>
                      ))}
                      <p className="field-help">
                        Muốn phân tích footage, phiên âm mới hoặc research? Nhờ
                        AI chuẩn bị ở job trước khi xuất; editor này không tự
                        chạy các bước đó.
                      </p>
                    </>
                  )}
                  <p className="field-help">
                    FFmpeg encode MP4 khi xuất. Motion giữ nguyên được tái sử
                    dụng; chỉ motion thay đổi cần render asset mới. Chữ trong
                    preview có thể khác ASS đôi chút; ducking áp dụng khi xuất.
                  </p>
                  <button className="primary wide" onClick={exportVideo}>
                    <Export size={17} />
                    Xác nhận bản dựng & xuất MP4
                  </button>
                  {task?.status === "complete" && (
                    <a
                      href={mediaUrl(project.job_id, task.relative)}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Xem {task.revision}
                    </a>
                  )}
                </>
              )
            )}
            {error && <p className="modal-error">{error}</p>}
          </section>
        </div>
      )}
    </main>
  );
}
function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
    </label>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
