import React from 'react';
import {AbsoluteFill, Easing, Img, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';

type Move = 'slide-left' | 'slide-right' | 'slide-up' | 'zoom' | 'wipe' | 'fade';
export type IllustrationContent = {
  // A URL by the time it renders: the CLI passes a data URL, Studio a media URL.
  image: string;
  enter?: Move;
  exit?: Move;
  motion?: 'zoom-in' | 'zoom-out' | 'pan-left' | 'pan-right' | 'none';
  radius?: number;
  fill?: boolean;
  enter_frames?: number;
  exit_frames?: number;
};

// Where the card is at progress p (0 hidden, 1 in place) for one move.
const placement = (move: Move, p: number): React.CSSProperties => {
  const away = 1 - p;
  switch (move) {
    case 'slide-left': return {transform: `translateX(${away * 110}%)`};
    case 'slide-right': return {transform: `translateX(${-away * 110}%)`};
    case 'slide-up': return {transform: `translateY(${away * 110}%)`};
    case 'zoom': return {transform: `scale(${0.55 + 0.45 * p})`, opacity: p};
    case 'wipe': return {clipPath: `inset(0 ${away * 100}% 0 0 round 0)`};
    case 'fade': return {opacity: p};
  }
};

// Rounded image card on a transparent layer: animated entry and exit, slow camera move while shown.
export const Illustration: React.FC<{content: IllustrationContent}> = ({content}) => {
  const frame = useCurrentFrame();
  const {durationInFrames, width} = useVideoConfig();
  const enterFrames = content.enter_frames ?? 10;
  const exitFrames = content.exit_frames ?? 8;
  const shown = interpolate(frame, [0, enterFrames], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
  const gone = interpolate(frame, [durationInFrames - exitFrames, durationInFrames], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.in(Easing.cubic)});
  // Slides leave in their own direction (slide-left exits to the left); other moves reverse.
  const exit = content.exit ?? 'fade';
  const leaving: Record<string, React.CSSProperties> = {
    'slide-left': {transform: `translateX(${-gone * 110}%)`},
    'slide-right': {transform: `translateX(${gone * 110}%)`},
    'slide-up': {transform: `translateY(${-gone * 110}%)`},
  };
  const style = gone > 0 ? leaving[exit] ?? placement(exit, 1 - gone) : placement(content.enter ?? 'slide-left', shown);
  const t = frame / Math.max(1, durationInFrames - 1);
  const camera = {
    'zoom-in': `scale(${1 + 0.1 * t})`,
    'zoom-out': `scale(${1.1 - 0.1 * t})`,
    'pan-left': `scale(1.1) translateX(${4 - 8 * t}%)`,
    'pan-right': `scale(1.1) translateX(${-4 + 8 * t}%)`,
    none: undefined,
  }[content.motion ?? 'zoom-in'];
  // fill: edge to edge and opaque, e.g. a full-width panel that hides a title underneath.
  const radius = content.fill ? 0 : content.radius ?? Math.round(width * 0.04);
  const inset = content.fill ? 0 : Math.round(width * 0.03);
  const frameStyle: React.CSSProperties = content.fill
    ? {backgroundColor: '#0B1420'}
    : {border: '6px solid rgba(255,255,255,.92)', boxShadow: '0 18px 40px rgba(0,0,0,.35)'};
  return <AbsoluteFill style={{backgroundColor: 'transparent'}}>
    <div style={{position: 'absolute', inset, borderRadius: radius, overflow: 'hidden', ...frameStyle, ...style}}>
      <Img src={content.image} style={{width: '100%', height: '100%', objectFit: 'cover', transform: camera, transformOrigin: '50% 50%'}}/>
    </div>
  </AbsoluteFill>;
};
