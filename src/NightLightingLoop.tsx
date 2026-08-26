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
  isCompactEmitter: boolean;
  eligible: boolean;
  selectionMode: 'strict-emitter' | 'daylight-accent' | 'rejected';
  color: [number, number, number];
};

type Flicker = {
  start: number;
  end: number;
  level: number;
};

const MAX_LIGHTS = 3;
const REAR_MAX_Y = 0.40;
const safeLightZones = (lighting.zones as unknown as LightZone[])
  .filter((zone) => zone.eligible)
  .filter((zone) => zone.y < REAR_MAX_Y)
  .sort((first, second) => first.y - second.y)
  .slice(0, 1);

// Positive glow only. The source image is never made darker.
const flickerSchedules: Flicker[][] = [
  [
    {start: 0.85, end: 0.99, level: 1.18},
    {start: 5.95, end: 6.28, level: 1.15},
    {start: 18.40, end: 18.71, level: 1.17},
  ],
  [
    {start: 3.45, end: 4.05, level: 1.16},
    {start: 23.10, end: 23.53, level: 1.14},
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
        const isDaylightAccent = zone.selectionMode === 'daylight-accent';
        const opacity = isDaylightAccent
          ? Math.min(0.62, Math.max(0, brightness - 1) * 2.4)
          : Math.min(0.58, Math.max(0, brightness - 1) * 2.0);
        const sizeScale = isDaylightAccent ? 0.46 : 0.86;
        const width = zone.width * sizeScale;
        const height = zone.height * sizeScale;
        const [red, green, blue] = zone.color;

        return (
          <div
            key={zone.id}
            style={{
              backgroundColor: `rgba(${red}, ${green}, ${blue}, ${opacity})`,
              borderRadius: '50%',
              boxShadow: `0 0 24px 12px rgba(${red}, ${green}, ${blue}, ${opacity * 0.6})`,
              filter: 'blur(1px)',
              height: `${height * 100}%`,
              left: `${(zone.x - width / 2) * 100}%`,
              mixBlendMode: 'screen',
              pointerEvents: 'none',
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
