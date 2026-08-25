import {AbsoluteFill, Img, Loop, OffthreadVideo, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import lighting from './generated-light-zones.json';
import videoMetadata from './generated-video-metadata.json';

type Flicker = {start: number; end: number; peak: number};
const flickers: Flicker[] = [
  {start: 0.85, end: 1.55, peak: 1},
  {start: 3.45, end: 4.20, peak: 0.82},
  {start: 7.15, end: 7.90, peak: 0.94},
  {start: 13.60, end: 14.34, peak: 0.76},
  {start: 23.10, end: 23.82, peak: 0.90},
];

const getOverlayOpacity = (seconds: number) => {
  let opacity = 0;
  for (const flicker of flickers) {
    const fade = Math.min(0.16, (flicker.end - flicker.start) / 3);
    opacity = Math.max(opacity, interpolate(
      seconds,
      [flicker.start, flicker.start + fade, flicker.end - fade, flicker.end],
      [0, flicker.peak, flicker.peak, 0],
      {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
    ));
  }
  return opacity;
};

export const NightVideoLightingLoop: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const opacity = lighting.animate ? getOverlayOpacity(frame / fps) : 0;
  return (
    <AbsoluteFill>
      <Loop durationInFrames={videoMetadata.sourceDurationInFrames / 0.5}>
        <OffthreadVideo muted playbackRate={0.5} src={staticFile('night-source.mp4')} style={{height: '100%', objectFit: 'cover', width: '100%'}} />
      </Loop>
      {lighting.animate && <Img src={staticFile('light_overlay.png')} style={{height: '100%', objectFit: 'cover', opacity, width: '100%'}} />}
    </AbsoluteFill>
  );
};
