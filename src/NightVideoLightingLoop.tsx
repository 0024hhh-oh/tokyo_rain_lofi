import {
  AbsoluteFill,
  Loop,
  OffthreadVideo,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import lighting from './generated-light-zones.json';
import videoMetadata from './generated-video-metadata.json';

type LightZone = {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  warmth: number;
  strength: number;
  hasLightCore: boolean;
  animationEligible: boolean;
  color: [number, number, number];
};

type Flicker = {
  start: number;
  end: number;
  level: number;
};

const MAX_LIGHTS = 3;
// Video compression and rain mute warm pixels more than the still reference.
// 0.4 keeps the accepted vending/sign/lantern trio without admitting cool lights.
const SAFE_MIN_WARMTH = 0.4;
const SAFE_MAX_Y = 0.72;
const SOURCE_PLAYBACK_RATE = 0.5;
const SOURCE_DURATION_IN_FRAMES = videoMetadata.sourceDurationInFrames;
const LOOP_DURATION_IN_FRAMES = SOURCE_DURATION_IN_FRAMES / SOURCE_PLAYBACK_RATE;
const MAX_DIM_OPACITY = 0.40;
const MAX_GLOW_OPACITY = 0.38;
const DIM_ZONE_SCALES = [1.05, 1.10] as const;

const safeLightZones = (lighting.zones as LightZone[])
  .filter((zone) =>
    zone.animationEligible &&
    zone.hasLightCore &&
    zone.warmth >= SAFE_MIN_WARMTH &&
    zone.y < SAFE_MAX_Y)
  .slice(0, MAX_LIGHTS);

const flickerSchedules: Flicker[][] = [
  [
    {start: 0.85, end: 1.55, level: 0.58},
    {start: 5.70, end: 6.38, level: 0.64},
    {start: 18.40, end: 19.12, level: 0.60},
  ],
  [
    {start: 3.45, end: 4.20, level: 0.60},
    {start: 23.10, end: 23.82, level: 0.65},
  ],
  [
    {start: 2.90, end: 3.62, level: 1.50},
    {start: 7.15, end: 7.90, level: 1.42},
    {start: 13.60, end: 14.34, level: 1.46},
    {start: 27.35, end: 28.08, level: 1.42},
  ],
];

const getBrightness = (frame: number, fps: number, flickers: Flicker[]) => {
  const seconds = frame / fps;
  let brightness = 1;
  for (const flicker of flickers) {
    const fade = Math.min(0.16, (flicker.end - flicker.start) / 3);
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

export const NightVideoLightingLoop: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  return (
    <AbsoluteFill style={{backgroundColor: '#050608'}}>
      <Loop durationInFrames={LOOP_DURATION_IN_FRAMES}>
        <OffthreadVideo
          muted
          playbackRate={SOURCE_PLAYBACK_RATE}
          src={staticFile('night-source.mp4')}
          style={{height: '100%', objectFit: 'cover', width: '100%'}}
        />
      </Loop>

      {lighting.animate && safeLightZones.map((zone, index) => {
        const brightness = getBrightness(frame, fps, flickerSchedules[index]);
        const brightening = Math.max(0, brightness - 1);
        const opacity = getOverlayOpacity(brightness);
        const isBrightening = brightening > 0;
        const sizeScale = isBrightening ? 0.68 : DIM_ZONE_SCALES[index] ?? 1.05;
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
                ? `0 0 18px 9px rgba(${red}, ${green}, ${blue}, ${opacity * 0.5})`
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
