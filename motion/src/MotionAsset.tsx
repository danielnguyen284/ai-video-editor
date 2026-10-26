import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {KineticScene, type KineticContent} from './KineticScene';

type Bar = {label: string; value: number};
type Content = {title: string; value?: string; subtitle?: string; source?: string; unit?: string; accent?: string; data?: Bar[]} & Partial<KineticContent>;
export type MotionRequest = {template: 'MetricCard' | 'BarChart' | 'LowerThird' | 'KineticScene'; width: number; height: number; fps: number; duration_frames: number; props: Content};
const initial: MotionRequest = {template: 'MetricCard', width: 720, height: 400, fps: 30, duration_frames: 90, props: {title: 'Metric', value: '42', subtitle: 'Demo data'}};

const StandardAsset: React.FC<MotionRequest> = ({template, props: content}) => {
  const frame = useCurrentFrame();
  const {width, height, durationInFrames} = useVideoConfig();
  const enter = interpolate(frame, [0, 12], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const leave = interpolate(frame, [Math.max(12, durationInFrames - 8), durationInFrames], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const accent = content.accent ?? '#A6EDBC';
  const pad = Math.max(12, Math.round(width * 0.05));
  const small = Math.max(12, Math.round(Math.min(width / 28, height / 14)));
  const titleSize = Math.max(16, Math.round(Math.min(width / 16, height / 7)));
  const panel: React.CSSProperties = {position: 'absolute', inset: '4%', background: '#121C26', color: '#F6F4ED', borderRadius: Math.max(8, width / 35), padding: pad, overflow: 'hidden', opacity: enter * leave, transform: `translateY(${(1 - enter) * 18}px)`, border: '1px solid #34424D'};
  return <AbsoluteFill style={{fontFamily: 'Arial, sans-serif', backgroundColor: 'transparent'}}>
    <div style={panel}>
      {template === 'MetricCard' && <>
        <div style={{fontSize: titleSize, color: '#B7C2CC', lineHeight: 1.15}}>{content.title}</div>
        <div style={{fontSize: Math.min(width / 7, height / 3), fontWeight: 700, color: accent, letterSpacing: '-0.04em', marginTop: height * 0.025, lineHeight: 1.08}}>{content.value}</div>
        <div style={{fontSize: small * 1.15, marginTop: height * 0.03, maxWidth: '96%'}}>{content.subtitle}</div>
      </>}
      {template === 'LowerThird' && <div style={{display: 'flex', height: '100%', alignItems: 'center', gap: pad}}>
        <div style={{width: Math.max(4, width / 100), height: '72%', background: accent, flexShrink: 0}}/>
        <div><div style={{fontSize: titleSize * 1.25, fontWeight: 700, lineHeight: 1.15}}>{content.title}</div><div style={{fontSize: small * 1.2, marginTop: 8, color: '#B7C2CC'}}>{content.subtitle}</div></div>
      </div>}
      {template === 'BarChart' && <>
        <div style={{fontSize: titleSize, fontWeight: 700, lineHeight: 1.1}}>{content.title} <span style={{fontSize: small, color: '#B7C2CC'}}>{content.unit}</span></div>
        <div style={{display: 'flex', alignItems: 'flex-end', gap: Math.max(8, width * 0.025), height: '61%', marginTop: height * 0.04, borderBottom: '1px solid #4A5966'}}>
          {(content.data ?? []).map((bar, index, data) => {
            const maximum = Math.max(1, ...data.map((item) => item.value));
            const growth = interpolate(frame, [index * 2, index * 2 + 18], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
            return <div key={index} style={{flex: 1, height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', alignItems: 'center', minWidth: 0}}>
              <div style={{fontSize: small, color: accent, marginBottom: 4}}>{bar.value}</div>
              <div style={{background: accent, width: '68%', height: `${Math.max(0, bar.value / maximum * 72 * growth)}%`, borderRadius: '4px 4px 0 0', flexShrink: 0}}/>
              <div style={{fontSize: small, paddingTop: 5, height: small * 2.4, width: '100%', textAlign: 'center', overflow: 'hidden'}}>{bar.label}</div>
            </div>;
          })}
        </div>
      </>}
      {content.source && template !== 'LowerThird' && <div style={{position: 'absolute', left: pad, right: pad, bottom: Math.max(10, height * 0.035), fontSize: small * 0.8, color: '#9AA8B4'}}>{content.source}</div>}
    </div>
  </AbsoluteFill>;
};

export const MotionAsset: React.FC<MotionRequest> = (request) => request.template === 'KineticScene'
  ? <KineticScene content={request.props}/>
  : <StandardAsset {...request}/>;
