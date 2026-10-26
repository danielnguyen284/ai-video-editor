import React from 'react';
import {Composition, registerRoot} from 'remotion';
import {MotionAsset, type MotionRequest} from './MotionAsset';
const initial: MotionRequest = {template: 'MetricCard', width: 720, height: 400, fps: 30, duration_frames: 90, props: {title: 'Metric', value: '42', subtitle: 'Demo data'}};
const Root: React.FC = () => <Composition id="MotionAsset" component={MotionAsset} defaultProps={initial} width={720} height={400} fps={30} durationInFrames={90} calculateMetadata={({props}: {props: MotionRequest}) => ({width: props.width, height: props.height, fps: props.fps, durationInFrames: props.duration_frames})}/>;
registerRoot(Root);
