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
const REAR_MAX_Y = 0.55;
const SOURCE_PLAYBACK_RATE = 0.5;
const SOURCE_DURATION_IN_FRAMES = videoMetadata.sourceDurationInFrames;
const LOOP_DURATION_IN_FRAMES = SOURCE_DURATION_IN_FRAMES / SOURCE_PLAYBACK_RATE;
const MAX_GLOW_OPACITY = 0.34;

const safeLightZones = (lighting.zones as unknown as LightZone[])
  .filter((zone) => zone.eligible)
  .filter((zone) => zone.y < REAR_MAX_Y)
  .sort((first, second) => first.y - second.y)
  .slice(0, 1);

const flickerSchedules: Flicker[][] = [
  [
    {start: 0.85, end: 1.55, level: 1.18},
    {start: 5.70, end: 6.38, level: 1.15},
    {start: 18.40, end: 19.12, level: 1.17},
  ],
  [
    {start: 3.45, end: 4.20, level: 1.16},
    {start: 23.10, end: 23.82, level: 1.14},
  ],
  [
    {start: 2.90, end: 3.62, level: 1.38},
    {start: 7.15, end: 7.90, level: 1.34},
    {start: 13.60, end: 14.34, level: 1.36},
    {start: 27.35, end: 28.08, level: 1.34},
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
  return Math.min(MAX_GLOW_OPACITY, (brightness - 1) * 2.0);
};

export const NightVideoLightingLoop: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  return (
    <AbsoluteFill style={{backgroundColor: '#050608'}}>
      <Loop durationInFrames={LOOP_DURATION_IN_FRAMES}>
        <OffthreadVideo
          loop
          muted
          playbackRate={SOURCE_PLAYBACK_RATE}
          src={staticFile('night-source.mp4')}
          style={{height: '100%', objectFit: 'cover', width: '100%'}}
        />
      </Loop>

      {lighting.animate && safeLightZones.map((zone, index) => {
        const brightness = getBrightness(frame, fps, flickerSchedules[index]);
        const isDaylightAccent = zone.selectionMode === 'daylight-accent';
        const opacity = isDaylightAccent
          ? Math.min(0.62, Math.max(0, brightness - 1) * 2.4)
          : getOverlayOpacity(brightness);
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
