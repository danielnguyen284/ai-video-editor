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
import { VietnameseFont } from "../../motion/src/VietnameseFont";
import {
  captionLines,
  clipHandles,
  mediaUrl,
  rateOf,
  transitionSplit,
  transitionStyle,
  sourceAt,
  zoomAt,
  type Project,
  type View,
} from "./model";

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
  const safe = text.replace(/\\/g, " ").replace(/{/g, "(").replace(/}/g, ")");
  return captionLines(safe, width).join("\n");
}
export const Preview: React.FC<{ project: Project; view: View }> = ({
  project: s,
  view,
}) => {
  const p = s.plan,
    frame = useCurrentFrame(),
    { width: w, height: h } = p.export,
    handles = clipHandles(p.clips);
  return (
    <AbsoluteFill style={{ backgroundColor: "#000", overflow: "hidden" }}>
      {p.clips.map((c, i) => {
        const crop = c.crop ?? {
          x: 0,
          y: 0,
          width: view.media.width,
          height: view.media.height,
        };
        const contain = Math.min(w / crop.width, h / crop.height),
          cover = Math.max(w / crop.width, h / crop.height);
        // Transitions show picture just beyond the cuts (handles), voice muted there.
        const [lead, tail] = handles[i],
          frames = c.timeline_out_frame - c.timeline_in_frame,
          into = c.transition,
          out = p.clips[i + 1]?.transition;
        const active =
          c.timeline_in_frame - lead <= frame &&
          frame < c.timeline_out_frame + tail;
        let effect = {};
        if (into && frame < c.timeline_in_frame + transitionSplit(into.frames)[1])
          effect = transitionStyle(
            into.type,
            (frame - (c.timeline_in_frame - lead)) / into.frames,
            true,
          );
        else if (out && frame >= c.timeline_out_frame - transitionSplit(out.frames)[0])
          effect = transitionStyle(
            out.type,
            (frame - (c.timeline_out_frame - transitionSplit(out.frames)[0])) /
              out.frames,
            false,
          );
        // Same zoom as the export: the focal point stays put inside the cropped picture.
        const [scale, fx, fy] = active
          ? zoomAt(c.zoom, sourceAt(c, frame, p.fps))
          : [1, 0.5, 0.5];
        const picture = (fit: number, backdrop = false) => (
          <div
            style={{
              position: "absolute",
              left: (w - crop.width * fit) / 2,
              top: (h - crop.height * fit) / 2,
              width: crop.width * fit,
              height: crop.height * fit,
              overflow: "hidden",
              // Export blurs a cover copy; CSS blur fades at its own edges, so
              // the backdrop is oversized and the canvas clips it.
              filter: backdrop ? "blur(32px) brightness(0.88)" : undefined,
            }}
          >
            <div
              style={{
                position: "absolute",
                inset: 0,
                transform: scale === 1 ? undefined : `scale(${scale})`,
                transformOrigin: `${fx * 100}% ${fy * 100}%`,
              }}
            >
              <Video
                src={mediaUrl(s.job_id, view.source, true)}
                startFrom={Math.round(c.source_in_seconds * p.fps - lead * rateOf(c))}
                playbackRate={rateOf(c)}
                muted={backdrop}
                volume={(f) =>
                  backdrop || f < lead || f >= lead + frames
                    ? 0
                    : Math.min(1, p.audio.voice_gain)
                }
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
          </div>
        );
        // Each clip mounts its own <Video>; premounting loads and seeks it a second
        // early (hidden), otherwise the frame is black while the browser seeks at the cut.
        return (
          <Sequence
            key={c.clip_id}
            from={c.timeline_in_frame - lead}
            durationInFrames={frames + lead + tail}
            premountFor={p.fps}
          >
            <AbsoluteFill style={effect}>
              {p.export.fit === "blur" && picture(cover * 1.12, true)}
              {picture(p.export.fit === "crop" ? cover : contain)}
            </AbsoluteFill>
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
              request={
                spec.template === "Illustration"
                  ? { ...spec, props: { ...spec.props, image: mediaUrl(s.job_id, spec.props.image) } }
                  : spec.template === "Points" && spec.props.icon
                    ? { ...spec, props: { ...spec.props, icon: mediaUrl(s.job_id, spec.props.icon) } }
                    : spec
              }
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
            premountFor={p.fps}
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
          .map((c) => {
            const caption = (
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
                  WebkitTextStroke: `${p.captions.outline_width ?? 1.5}px #101010`,
                  paintOrder: "stroke fill",
                  textShadow: "1px 1px 1px #000",
                }}
              >
                {wrap(c.text, p.captions.max_chars)}
              </div>
            );
            return p.captions.font_name === "Be Vietnam Pro" ? (
              <VietnameseFont key={c.id}>{caption}</VietnameseFont>
            ) : (
              caption
            );
          })}
      {p.audio.music && (
        <Audio
          src={mediaUrl(s.job_id, p.audio.music.path)}
          volume={Math.min(1, p.audio.music.gain)}
          loop
        />
      )}
      {(p.audio.sfx ?? []).map((x) => (
        <Sequence
          key={x.id}
          from={x.timeline_in_frame}
          durationInFrames={x.timeline_out_frame - x.timeline_in_frame}
        >
          <Audio src={mediaUrl(s.job_id, x.path)} volume={Math.min(1, x.gain)} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
