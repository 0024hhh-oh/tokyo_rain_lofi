import {
  AbsoluteFill,
  Img,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import lighting from '../src/generated-light-zones.json';

type LightZone = {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  warmth: number;
  strength: number;
};

type Flicker = {
  start: number;
  end: number;
  level: number;
};

const MAX_LIGHTS = 3;
const SAFE_MIN_WARMTH = 0.55;
const SAFE_MAX_Y = 0.8;

// The detector may find windows, street lamps, and wet-road reflections.
// Keep only warm, independently bounded lights above the reflection-heavy
// lower fifth of the image, then cap the animation at three locations.
const safeLightZones = (lighting.zones as LightZone[])
  .filter((zone) => zone.warmth >= SAFE_MIN_WARMTH && zone.y < SAFE_MAX_Y)
  .slice(0, MAX_LIGHTS);
const hasThreeSafeLights = safeLightZones.length === MAX_LIGHTS;

// Each light has different start times, durations, and dim levels. The events
// are deliberately non-overlapping so no two locations switch together.
const flickerSchedules: Flicker[][] = [
  [
    {start: 0.72, end: 0.92, level: 0.78},
    {start: 4.96, end: 5.30, level: 0.72},
    {start: 7.32, end: 7.47, level: 0.82},
  ],
  [
    {start: 1.38, end: 1.50, level: 0.74},
    {start: 3.55, end: 3.82, level: 0.80},
    {start: 6.54, end: 6.91, level: 0.70},
  ],
  [
    {start: 2.06, end: 2.36, level: 0.71},
    {start: 4.18, end: 4.35, level: 0.81},
    {start: 5.76, end: 5.99, level: 0.76},
  ],
];

const getBrightness = (seconds: number, flickers: Flicker[]) => {
  let brightness = 1;
  for (const flicker of flickers) {
    const fade = Math.min(0.07, (flicker.end - flicker.start) / 3);
    const level = interpolate(
      seconds,
      [flicker.start, flicker.start + fade, flicker.end - fade, flicker.end],
      [1, flicker.level, flicker.level, 1],
      {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
    );
    brightness = Math.min(brightness, level);
  }
  return brightness;
};

export const LightingVisualTest: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const seconds = frame / fps;

  return (
    <AbsoluteFill style={{backgroundColor: '#050608'}}>
      <Img
        src={staticFile('background.png')}
        style={{height: '100%', objectFit: 'cover', width: '100%'}}
      />

      {lighting.animate && hasThreeSafeLights && safeLightZones.map((zone, index) => {
        const brightness = getBrightness(seconds, flickerSchedules[index]);
        const mask = `radial-gradient(ellipse ${zone.width * 50}% ${zone.height * 50}% at ${zone.x * 100}% ${zone.y * 100}%, rgba(0, 0, 0, 1) 0%, rgba(0, 0, 0, 0.96) 58%, rgba(0, 0, 0, 0.48) 80%, transparent 100%)`;
        return (
          <AbsoluteFill
            key={zone.id}
            style={{
              filter: `brightness(${brightness}) saturate(${0.9 + brightness * 0.1})`,
              maskImage: mask,
              WebkitMaskImage: mask,
            }}
          >
            <Img
              src={staticFile('background.png')}
              style={{height: '100%', objectFit: 'cover', width: '100%'}}
            />
          </AbsoluteFill>
        );
      })}
    </AbsoluteFill>
  );
};
