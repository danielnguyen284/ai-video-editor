import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { VietnameseFont, VIETNAMESE_FONT } from "./VietnameseFont";
import { keywordEnvelope } from "./keyword-timing";

export type KeywordContent = {
  title: string;
  emphasis?: string;
  emphasis_frame?: number;
  font_size?: number;
  color?: string;
  accent?: string;
  enter_frames?: number;
  exit_frames?: number;
};

// No backdrop, cards, border or shadow panel. The layer rectangle controls placement.
export const Keyword: React.FC<{ content: KeywordContent }> = ({ content }) => {
  const frame = useCurrentFrame();
  const { height, durationInFrames } = useVideoConfig();
  const enter = content.enter_frames ?? 6;
  const exit = content.exit_frames ?? 5;
  const main = keywordEnvelope(frame, durationInFrames, enter, exit);
  const secondary = keywordEnvelope(
    frame,
    durationInFrames,
    enter,
    exit,
    content.emphasis_frame ?? 0,
  );
  const size = content.font_size ?? Math.min(44, Math.floor(height / 3.5));
  const style: React.CSSProperties = {
    fontFamily: VIETNAMESE_FONT,
    fontWeight: 700,
    fontSize: size,
    lineHeight: 1.38,
    letterSpacing: 0,
    whiteSpace: "pre-wrap",
    overflowWrap: "break-word",
    WebkitTextStroke: ".7px rgba(255,255,255,.72)",
    paintOrder: "stroke fill",
    textShadow: "0 1px 2px rgba(255,255,255,.45)",
  };
  return (
    <VietnameseFont>
      <AbsoluteFill
        style={{
          backgroundColor: "transparent",
          justifyContent: "center",
          alignItems: "center",
          textAlign: "center",
          overflow: "hidden",
          padding: "6px 14px",
        }}
      >
        <div
          style={{
            ...style,
            color: content.color ?? "#193440",
            opacity: main.opacity,
            transform: `translateY(${main.y}px)`,
          }}
        >
          {content.title}
        </div>
        {content.emphasis && (
          <div
            style={{
              ...style,
              color: content.accent ?? "#086559",
              opacity: secondary.opacity,
              transform: `translateY(${secondary.y}px)`,
              marginTop: 2,
            }}
          >
            {content.emphasis}
          </div>
        )}
      </AbsoluteFill>
    </VietnameseFont>
  );
};
