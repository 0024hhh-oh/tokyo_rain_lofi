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
  hasLightCore: boolean;
  isCompactEmitter: boolean;
  color: [number, number, number];
};

type Flicker = {
  start: number;
  end: number;
  level: number;
};

const MAX_LIGHTS = 3;
const SAFE_MIN_WARMTH = 0.75;
const SAFE_MAX_Y = 0.72;

// Only compact, warm emitters are eligible. Uncertain scenes render unchanged.
const safeLightZones = (lighting.zones as LightZone[])
  .filter((zone) =>
    zone.hasLightCore && zone.isCompactEmitter &&
    zone.warmth >= SAFE_MIN_WARMTH && zone.y < SAFE_MAX_Y)
  .slice(0, MAX_LIGHTS);

// Positive glow only; the source is never darkened.
const flickerSchedules: Flicker[][] = [
  [
    {start: 0.85, end: 0.99, level: 1.18},
    {start: 5.95, end: 6.28, level: 1.15},
  ],
  [
    {start: 3.45, end: 4.05, level: 1.16},
  ],
  [
    {start: 2.90, end: 3.10, level: 1.35},
    {start: 7.15, end: 7.56, level: 1.28},
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
    if (Math.abs(level - 1) > Math.abs(brightness - 1)) {
      brightness = level;
    }
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

      {lighting.animate && safeLightZones.map((zone, index) => {
        const brightness = getBrightness(seconds, flickerSchedules[index]);
        const opacity = Math.min(0.30, Math.max(0, brightness - 1) * 0.9);
        const width = zone.width * 0.58;
        const height = zone.height * 0.58;
        const [red, green, blue] = zone.color;
        return (
          <div
            key={zone.id}
            style={{
              backgroundColor: `rgba(${red}, ${green}, ${blue}, ${opacity})`,
              borderRadius: '50%',
              boxShadow: `0 0 16px 8px rgba(${red}, ${green}, ${blue}, ${opacity * 0.45})`,
              filter: 'blur(2px)',
              height: `${height * 100}%`,
              left: `${(zone.x - width / 2) * 100}%`,
              mixBlendMode: 'screen',
              position: 'absolute',
              top: `${(zone.y - height / 2) * 100}%`,
              width: `${width * 100}%`,
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};
