import React from 'react';
import {AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';

export type KineticContent = {
  title: string;
  emphasis?: string;
  subtitle?: string;
  source?: string;
  accent?: string;
  theme?: 'light' | 'dark';
  transparent?: boolean;
  layout?: 'stack' | 'grid';
  cards?: {label: string; detail?: string}[];
  progress?: number;
};

// A fixed design canvas keeps Vietnamese type and card spacing predictable.
// All animation is local to this asset's frames, independent of wall-clock time.
export const KineticScene: React.FC<{content: KineticContent}> = ({content}) => {
  const frame = useCurrentFrame();
  const {width, height, fps, durationInFrames} = useVideoConfig();
  const scale = Math.min(width / 720, height / 1280);
  const dark = content.theme === 'dark';
  const ink = dark ? '#F5F4F0' : '#20262D';
  const muted = dark ? '#BAC6D1' : '#5F6973';
  const accent = content.accent ?? '#E5A137';
  const grid = content.layout === 'grid';
  const appear = (start: number, seconds = .28) => interpolate(frame, [start * fps, (start + seconds) * fps], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
  const enter = appear(0);
  const emphasis = appear(.12);
  const exit = interpolate(frame, [durationInFrames - Math.max(2, Math.round(fps * .16)), durationInFrames - 1], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const fill = interpolate(frame, [.6 * fps, Math.max(.8 * fps, durationInFrames - .45 * fps)], [0, content.progress ?? 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.cubic)});
  const wrap: React.CSSProperties = {overflowWrap: 'anywhere', whiteSpace: 'pre-wrap'};
  return <AbsoluteFill style={{background: content.transparent ? 'transparent' : dark ? 'radial-gradient(ellipse at 20% 10%, #183A5D, #0C1727 75%)' : '#FAFAF7', fontFamily: 'Arial, sans-serif', color: ink}}>
    <div style={{position: 'absolute', width: 720, height: 1280, left: (width - 720 * scale) / 2, top: (height - 1280 * scale) / 2, transform: `scale(${scale})`, transformOrigin: 'top left', opacity: exit}}>
      <div style={{position: 'absolute', left: 64, right: 96, top: 120, opacity: enter, transform: `translateY(${(1 - enter) * 18}px)`}}>
        <div style={{...wrap, fontSize: Math.min(38, 1400 / content.title.length), fontWeight: 700, lineHeight: 1.15}}>{content.title}</div>
        {content.emphasis && <div style={{...wrap, color: accent, fontSize: Math.min(62, 1250 / content.emphasis.length), fontWeight: 800, letterSpacing: '-0.035em', lineHeight: 1.05, marginTop: 18, opacity: emphasis, transform: `scale(${.94 + emphasis * .06})`, transformOrigin: 'left center'}}>{content.emphasis}</div>}
        {content.subtitle && <div style={{...wrap, fontSize: Math.min(27, 1600 / content.subtitle.length), color: muted, lineHeight: 1.3, marginTop: 22}}>{content.subtitle}</div>}
      </div>
      <div style={{position: 'absolute', left: 64, right: 96, top: 530, display: 'grid', gridTemplateColumns: grid ? '1fr 1fr' : '1fr', gap: 16}}>
        {(content.cards ?? []).map((card, index) => {
          const reveal = appear(.4 + index * .18);
          return <div key={index} style={{boxSizing: 'border-box', minWidth: 0, height: grid ? 172 : 94, display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: grid ? '18px 20px' : '12px 20px', background: dark ? '#192C41' : '#FFFFFF', border: `1px solid ${dark ? '#3B536A' : '#DDE1E3'}`, borderLeft: `5px solid ${accent}`, borderRadius: 14, boxShadow: dark ? '0 10px 20px #00000028' : '0 10px 20px #18232E0D', opacity: reveal, transform: `translateY(${(1 - reveal) * 24}px)`}}>
            <div style={{...wrap, fontSize: Math.min(grid ? 26 : 27, (grid ? 430 : 800) / card.label.length), fontWeight: 700, lineHeight: 1.15}}>{card.label}</div>
            {card.detail && <div style={{...wrap, fontSize: Math.min(grid ? 20 : 21, (grid ? 520 : 700) / card.detail.length), color: muted, lineHeight: 1.2, marginTop: 6}}>{card.detail}</div>}
          </div>;
        })}
      </div>
      {content.progress !== undefined && <div style={{position: 'absolute', left: 64, right: 96, top: 1000, opacity: appear(.6)}}>
        <div style={{height: 14, borderRadius: 10, overflow: 'hidden', background: dark ? '#29435C' : '#E2E5E7'}}>
          <div style={{width: `${fill * 100}%`, height: '100%', borderRadius: 10, background: accent}}/>
        </div>
      </div>}
      {content.source && <div style={{...wrap, position: 'absolute', left: 64, right: 96, top: 1090, fontSize: 20, lineHeight: 1.3, color: muted, opacity: enter}}>{content.source}</div>}
    </div>
  </AbsoluteFill>;
};
