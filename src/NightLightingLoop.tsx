import {
  AbsoluteFill,
  Img,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import lighting from './generated-light-zones.json';

type LightZone = {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  warmth: number;
  strength: number;
  hasLightCore: boolean;
};

type Flicker = {
  start: number;
  end: number;
  level: number;
};

const MAX_LIGHTS = 3;
const SAFE_MIN_WARMTH = 0.55;
const SAFE_MAX_Y = 0.72;

const safeLightZones = (lighting.zones as LightZone[])
  .filter((zone) =>
    zone.hasLightCore && zone.warmth >= SAFE_MIN_WARMTH && zone.y < SAFE_MAX_Y)
  .slice(0, MAX_LIGHTS);

// Two locations dim and one brightens. All events are sparse, non-overlapping,
// and use different gaps and durations so the 30-second loop has no steady beat.
const flickerSchedules: Flicker[][] = [
  [
    {start: 0.85, end: 0.99, level: 0.76},
    {start: 5.95, end: 6.28, level: 0.80},
    {start: 18.40, end: 18.71, level: 0.74},
  ],
  [
    {start: 3.45, end: 4.05, level: 0.72},
    {start: 23.10, end: 23.53, level: 0.78},
  ],
  [
    {start: 2.90, end: 3.10, level: 1.35},
    {start: 7.15, end: 7.56, level: 1.28},
    {start: 13.60, end: 13.87, level: 1.32},
    {start: 27.35, end: 27.83, level: 1.30},
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
    if (Math.abs(level - 1) > Math.abs(brightness - 1)) brightness = level;
  }
  return brightness;
};

export const NightLightingLoop: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const seconds = frame / fps;

  return (
    <AbsoluteFill style={{backgroundColor: '#050608'}}>
      <Img
        src={staticFile('background.png')}
        style={{height: '100%', objectFit: 'cover', width: '100%'}}
      />

      {lighting.animate && safeLightZones.map((zone, index) => {
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
