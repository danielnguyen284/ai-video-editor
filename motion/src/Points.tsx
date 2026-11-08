import React from 'react';
import {AbsoluteFill, Easing, Img, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {VietnameseFont, VIETNAMESE_FONT} from './VietnameseFont';

export type PointsContent = {
  title: string;
  // Each item appears on its own frame (relative to the asset), e.g. when it is spoken.
  items?: {text: string; at: number}[];
  // A large figure; digits count up from 0 when it appears.
  big?: string;
  big_at?: number;
  emphasis?: string;
  emphasis_at?: number;
  accent?: string;
  // Edge to edge and opaque: a full-width panel at the top that hides a title underneath.
  fill?: boolean;
  // An app/logo image beside the title, a URL by the time it renders (data URL in the CLI, media URL in Studio).
  icon?: string;
};

const ease = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const, easing: Easing.out(Easing.cubic)};

// A dark card of large spoken points: slides in, reveals each point on its frame, slides out.
export const Points: React.FC<{content: PointsContent}> = ({content}) => {
  const frame = useCurrentFrame();
  const {width, height, durationInFrames} = useVideoConfig();
  const accent = content.accent ?? '#E5484D';
  const shown = interpolate(frame, [0, 10], [0, 1], ease);
  const gone = interpolate(frame, [durationInFrames - 8, durationInFrames], [0, 1], {...ease, easing: Easing.in(Easing.cubic)});
  const unit = width / 1000;
  const reveal = (at = 0) => interpolate(frame, [at, at + 8], [0, 1], ease);
  const bigIn = reveal(content.big_at);
  const digits = content.big?.match(/^(\D*)(\d+)(.*)$/);
  const big = digits && bigIn < 1
    ? digits[1] + Math.round(Number(digits[2]) * interpolate(frame, [content.big_at ?? 0, (content.big_at ?? 0) + 18], [0, 1], ease)) + digits[3]
    : content.big;
  const emphasisIn = reveal(content.emphasis_at);
  // A full-width panel starts at the top of the frame: keep text below the platform header.
  // A full-screen panel (taller than 1500 px) also keeps it above the bottom captions (from about y 1400).
  const bottom = height > 1500 ? height - 1400 : 60 * unit;
  const panel: React.CSSProperties = content.fill
    ? {inset: 0, background: 'linear-gradient(160deg, #0E1B2A, #080F18)', padding: `${230 * unit}px ${70 * unit}px ${bottom}px`}
    : {inset: 30 * unit, borderRadius: 40 * unit, background: 'linear-gradient(160deg, rgba(14,27,42,.95), rgba(8,15,24,.95))',
      border: `${3 * unit}px solid rgba(255,255,255,.18)`, boxShadow: '0 18px 40px rgba(0,0,0,.35)', padding: `${56 * unit}px ${60 * unit}px`};
  const title = <div style={{fontSize: (content.icon ? 64 : 52) * unit, lineHeight: 1.25, color: content.icon ? '#F6F4ED' : '#C9D4DE'}}>{content.title}</div>;
  return <VietnameseFont>
    <AbsoluteFill style={{backgroundColor: 'transparent', fontFamily: VIETNAMESE_FONT, fontWeight: 700}}>
      <div style={{position: 'absolute', overflow: 'hidden', color: '#F6F4ED', display: 'flex', flexDirection: 'column',
        justifyContent: 'center', gap: 30 * unit, transform: `translateX(${(1 - shown) * 110 - gone * 110}%)`, ...panel}}>
        {content.icon
          ? <div style={{display: 'flex', alignItems: 'center', gap: 36 * unit}}>
            <Img src={content.icon} style={{width: 170 * unit, height: 170 * unit, borderRadius: 38 * unit, flexShrink: 0,
              boxShadow: '0 8px 24px rgba(0,0,0,.35)'}}/>
            {title}
          </div>
          : title}
        {content.big && <div style={{fontSize: 210 * unit, lineHeight: 1, color: accent, letterSpacing: '-0.03em',
          opacity: bigIn, transform: `scale(${0.8 + 0.2 * bigIn})`, transformOrigin: 'left center'}}>{big}</div>}
        {(content.items ?? []).map((item, index) => {
          const p = reveal(item.at);
          return <div key={index} style={{display: 'flex', alignItems: 'center', gap: 26 * unit, opacity: p,
            transform: `translateX(${(1 - p) * -40 * unit}px)`}}>
            <div style={{width: 12 * unit, alignSelf: 'stretch', borderRadius: 6 * unit, background: accent, flexShrink: 0}}/>
            <div style={{fontSize: 62 * unit, lineHeight: 1.2}}>{item.text}</div>
          </div>;
        })}
        {content.emphasis && <div style={{fontSize: 74 * unit, lineHeight: 1.15, color: accent, opacity: emphasisIn,
          transform: `scale(${0.85 + 0.15 * emphasisIn})`, transformOrigin: 'left center'}}>{content.emphasis}</div>}
      </div>
    </AbsoluteFill>
  </VietnameseFont>;
};
