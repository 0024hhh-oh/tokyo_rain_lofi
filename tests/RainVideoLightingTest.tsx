import {
  AbsoluteFill,
  Loop,
  OffthreadVideo,
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
  color: [number, number, number];
};

type Flicker = {
  start: number;
  end: number;
  level: number;
};

const MAX_LIGHTS = 3;
const SAFE_MIN_WARMTH = 0.55;
const SAFE_MAX_Y = 0.72;
const SOURCE_DURATION_IN_FRAMES = 242;
const SOURCE_PLAYBACK_RATE = 0.5;
const LOOP_DURATION_IN_FRAMES = SOURCE_DURATION_IN_FRAMES / SOURCE_PLAYBACK_RATE;
const MAX_DIM_OPACITY = 0.28;
const MAX_GLOW_OPACITY = 0.20;
const DIM_ZONE_SCALES = [1.05, 1.10] as const;

const safeLightZones = (lighting.zones as LightZone[])
  .filter((zone) =>
    zone.hasLightCore && zone.warmth >= SAFE_MIN_WARMTH && zone.y < SAFE_MAX_Y)
  .slice(0, MAX_LIGHTS);
const hasThreeSafeLights = safeLightZones.length === MAX_LIGHTS;

const flickerSchedules: Flicker[][] = [
  [
    {start: 0.85, end: 1.10, level: 0.78},
    {start: 5.95, end: 6.24, level: 0.82},
    {start: 18.40, end: 18.66, level: 0.76},
  ],
  [
    {start: 3.45, end: 3.78, level: 0.76},
    {start: 23.10, end: 23.38, level: 0.80},
  ],
  [
    {start: 2.90, end: 3.22, level: 1.22},
    {start: 7.15, end: 7.50, level: 1.18},
    {start: 13.60, end: 13.92, level: 1.20},
    {start: 27.35, end: 27.70, level: 1.18},
  ],
];

const getBrightness = (frame: number, fps: number, flickers: Flicker[]) => {
  const seconds = frame / fps;
  let brightness = 1;
  for (const flicker of flickers) {
    const fade = Math.min(0.10, (flicker.end - flicker.start) / 3);
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

const getOverlayOpacity = (brightness: number) => {
  if (brightness < 1) {
    return Math.min(MAX_DIM_OPACITY, (1 - brightness) * 0.9);
  }
  return Math.min(MAX_GLOW_OPACITY, (brightness - 1) * 0.9);
};

const MutedRainVideo: React.FC = () => (
  <Loop durationInFrames={LOOP_DURATION_IN_FRAMES}>
    <OffthreadVideo
      muted
      playbackRate={SOURCE_PLAYBACK_RATE}
      src={staticFile('rain-video.mp4')}
      style={{height: '100%', objectFit: 'cover', width: '100%'}}
    />
  </Loop>
);

export const RainVideoLightingTest: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  return (
    <AbsoluteFill style={{backgroundColor: '#050608'}}>
      <MutedRainVideo />

      {lighting.animate && hasThreeSafeLights && safeLightZones.map((zone, index) => {
        const brightness = getBrightness(frame, fps, flickerSchedules[index]);
        const brightening = Math.max(0, brightness - 1);
        const opacity = getOverlayOpacity(brightness);
        const isBrightening = brightening > 0;
        const sizeScale = isBrightening ? 0.45 : DIM_ZONE_SCALES[index] ?? 1.05;
        const width = zone.width * sizeScale;
        const height = zone.height * sizeScale;
        const [red, green, blue] = zone.color;

        return (
          <div
            key={zone.id}
            style={{
              backgroundColor: isBrightening
                ? `rgba(${red}, ${green}, ${blue}, ${opacity})`
                : `rgba(0, 0, 0, ${opacity})`,
              borderRadius: '50%',
              boxShadow: isBrightening
                ? `0 0 16px 8px rgba(${red}, ${green}, ${blue}, ${opacity * 0.45})`
                : 'none',
              filter: isBrightening ? 'blur(2px)' : 'blur(6px)',
              height: `${height * 100}%`,
              left: `${(zone.x - width / 2) * 100}%`,
              mixBlendMode: isBrightening ? 'screen' : 'normal',
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
