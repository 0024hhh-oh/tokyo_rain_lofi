import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import lighting from './generated-light-zones.json';

type Flicker = {start: number; end: number; peak: number};
const flickers: Flicker[] = [
  {start: 0.85, end: 1.35, peak: 1},
  {start: 3.40, end: 4.18, peak: 0.82},
  {start: 7.15, end: 7.52, peak: 0.92},
  {start: 13.60, end: 14.26, peak: 0.74},
  {start: 22.80, end: 23.48, peak: 0.88},
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

export const NightLightingLoop: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const opacity = lighting.animate ? getOverlayOpacity(frame / fps) : 0;
  return (
    <AbsoluteFill>
      <Img src={staticFile('background.png')} style={{height: '100%', objectFit: 'cover', width: '100%'}} />
      {lighting.animate && <Img src={staticFile('light_overlay.png')} style={{height: '100%', objectFit: 'cover', opacity, width: '100%'}} />}
    </AbsoluteFill>
  );
};
