import React from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  Loop,
  Sequence,
  Video,
  useCurrentFrame,
} from "remotion";
import { MotionAsset, type MotionRequest } from "../../motion/src/MotionAsset";
import { mediaUrl, type Project, type View } from "./model";

function MotionView({
  request,
  offset,
  fps,
}: {
  request: Motion;
  offset: number;
  fps: number;
}) {
  const scaleFps = fps / request.fps;
  const duration = Math.round(request.duration_frames * scaleFps);
  return (
    <Sequence
      from={-Math.round(offset * fps)}
      durationInFrames={duration}
      width={request.width}
      height={request.height}
    >
      <MotionAsset {...(request as MotionRequest)} />
    </Sequence>
  );
}
type Motion = Project["motions"][string];
function wrap(text: string, width: number) {
  const lines: string[] = [];
  let line = "";
  for (const word of text
    .replace(/\\/g, " ")
    .replace(/{/g, "(")
    .replace(/}/g, ")")
    .trim()
    .split(/\s+/)) {
    if (line && line.length + 1 + word.length > width) {
      lines.push(line);
      line = word;
    } else line += (line ? " " : "") + word;
  }
  if (line) lines.push(line);
  return lines.join("\n");
}
export const Preview: React.FC<{ project: Project; view: View }> = ({
  project: s,
  view,
}) => {
  const p = s.plan,
    frame = useCurrentFrame(),
    { width: w, height: h } = p.export;
  return (
    <AbsoluteFill style={{ backgroundColor: "#000", overflow: "hidden" }}>
      {p.clips.map((c) => {
        const crop = c.crop ?? {
          x: 0,
          y: 0,
          width: view.media.width,
          height: view.media.height,
        };
        const fit =
          p.export.fit === "pad"
            ? Math.min(w / crop.width, h / crop.height)
            : Math.max(w / crop.width, h / crop.height);
        return (
          <Sequence
            key={c.clip_id}
            from={c.timeline_in_frame}
            durationInFrames={c.timeline_out_frame - c.timeline_in_frame}
          >
            <div
              style={{
                position: "absolute",
                left: (w - crop.width * fit) / 2,
                top: (h - crop.height * fit) / 2,
                width: crop.width * fit,
                height: crop.height * fit,
                overflow: "hidden",
              }}
            >
              <Video
                src={mediaUrl(s.job_id, view.source, true)}
                startFrom={Math.round(c.source_in_seconds * p.fps)}
                volume={Math.min(1, p.audio.voice_gain)}
                style={{
                  position: "absolute",
                  maxWidth: "none",
                  width: view.media.width * fit,
                  height: view.media.height * fit,
                  left: -crop.x * fit,
                  top: -crop.y * fit,
                }}
              />
            </div>
          </Sequence>
        );
      })}
      {p.overlays.map((l) => {
        const spec = s.motions[l.id];
        const scale = spec
          ? l.fit === "stretch"
            ? null
            : l.fit === "contain"
              ? Math.min(l.width / spec.width, l.height / spec.height)
              : Math.max(l.width / spec.width, l.height / spec.height)
          : 1;
        const inner = spec ? (
          <div
            style={{
              position: "absolute",
              width: spec.width,
              height: spec.height,
              left:
                (l.width - spec.width * (scale ?? l.width / spec.width)) / 2,
              top:
                (l.height - spec.height * (scale ?? l.height / spec.height)) /
                2,
              transform: `scale(${scale ?? l.width / spec.width},${scale ?? l.height / spec.height})`,
              transformOrigin: "top left",
            }}
          >
            <MotionView
              request={spec}
              offset={l.source_in_seconds ?? 0}
              fps={p.fps}
            />
          </div>
        ) : l.type === "image" ? (
          <Img
            src={mediaUrl(s.job_id, l.path)}
            style={{
              width: "100%",
              height: "100%",
              objectFit: l.fit === "stretch" ? "fill" : l.fit,
            }}
          />
        ) : (
          <Video
            src={mediaUrl(s.job_id, l.path, true)}
            startFrom={Math.round((l.source_in_seconds ?? 0) * p.fps)}
            muted
            style={{
              width: "100%",
              height: "100%",
              objectFit: l.fit === "stretch" ? "fill" : l.fit,
            }}
          />
        );
        return (
          <Sequence
            key={l.id}
            from={l.timeline_in_frame}
            durationInFrames={l.timeline_out_frame - l.timeline_in_frame}
          >
            <div
              style={{
                position: "absolute",
                left: l.x,
                top: l.y,
                width: l.width,
                height: l.height,
                opacity: l.opacity ?? 1,
                overflow: "hidden",
              }}
            >
              {l.loop && !spec ? (
                <Loop
                  durationInFrames={Math.max(
                    1,
                    Math.round(
                      ((view.durations?.[l.path] ??
                        (l.timeline_out_frame - l.timeline_in_frame) / p.fps) -
                        (l.source_in_seconds ?? 0)) *
                        p.fps,
                    ),
                  )}
                >
                  {inner}
                </Loop>
              ) : (
                inner
              )}
            </div>
          </Sequence>
        );
      })}
      {p.captions.enabled &&
        s.cues
          .filter(
            (c) => c.timeline_in_frame <= frame && frame < c.timeline_out_frame,
          )
          .map((c) => (
            <div
              key={c.id}
              style={{
                position: "absolute",
                left: 70,
                right: 70,
                bottom: p.captions.margin_v,
                textAlign: "center",
                fontFamily: p.captions.font_name,
                fontSize: p.captions.font_size,
                fontWeight: 700,
                lineHeight: 1.16,
                color: "#fff",
                whiteSpace: "pre-wrap",
                WebkitTextStroke: "1.5px #101010",
                paintOrder: "stroke fill",
                textShadow: "1px 1px 1px #000",
              }}
            >
              {wrap(c.text, p.captions.max_chars)}
            </div>
          ))}
      {p.audio.music && (
        <Audio
          src={mediaUrl(s.job_id, p.audio.music.path)}
          volume={Math.min(1, p.audio.music.gain)}
          loop
        />
      )}
    </AbsoluteFill>
  );
};
