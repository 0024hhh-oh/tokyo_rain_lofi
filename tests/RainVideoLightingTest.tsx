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
const MAX_DIM_OPACITY = 0.72;
const MAX_GLOW_OPACITY = 0.92;

const safeLightZones = (lighting.zones as LightZone[])
  .filter((zone) => zone.warmth >= SAFE_MIN_WARMTH && zone.y < SAFE_MAX_Y)
  .slice(0, MAX_LIGHTS);
const hasThreeSafeLights = safeLightZones.length === MAX_LIGHTS;

const flickerSchedules: Flicker[][] = [
  [
    {start: 0.85, end: 0.97, level: 0.25},
    {start: 5.95, end: 6.13, level: 0.32},
    {start: 18.40, end: 18.55, level: 0.22},
  ],
  [
    {start: 3.45, end: 3.67, level: 0.30},
    {start: 23.10, end: 23.27, level: 0.35},
  ],
  [
    {start: 2.90, end: 3.18, level: 2.30},
    {start: 7.15, end: 7.47, level: 2.10},
    {start: 13.60, end: 13.84, level: 2.20},
    {start: 27.35, end: 27.69, level: 2.00},
  ],
];

const getBrightness = (seconds: number, flickers: Flicker[]) => {
  let brightness = 1;
  for (const flicker of flickers) {
    const fade = Math.min(0.18, (flicker.end - flicker.start) / 3);
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
    return Math.min(MAX_DIM_OPACITY, (1 - brightness) * 1.1);
  }
  return Math.min(MAX_GLOW_OPACITY, (brightness - 1) * 1.35);
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
  const seconds = frame / fps;

  return (
    <AbsoluteFill style={{backgroundColor: '#050608'}}>
      <MutedRainVideo />

      {lighting.animate && hasThreeSafeLights && safeLightZones.map((zone, index) => {
        const brightness = getBrightness(seconds, flickerSchedules[index]);
        const brightening = Math.max(0, brightness - 1);
        const opacity = getOverlayOpacity(brightness);
        const isBrightening = brightening > 0;
        const width = zone.width * 0.8;
        const height = zone.height * 0.8;

        return (
          <div
            key={zone.id}
            style={{
              backgroundColor: isBrightening
                ? `rgba(255, 188, 105, ${opacity})`
                : `rgba(0, 0, 0, ${opacity})`,
              borderRadius: '26%',
              boxShadow: isBrightening
                ? `0 0 34px 20px rgba(255, 155, 70, ${opacity * 0.72})`
                : 'none',
              filter: 'blur(6px)',
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
