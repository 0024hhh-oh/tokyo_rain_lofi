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
import {
  selectVideoLightZones,
  type VideoLightZone,
} from './video-light-selection';

type Flicker = {
  start: number;
  end: number;
  level: number;
};

const SOURCE_PLAYBACK_RATE = 0.5;
const SOURCE_DURATION_IN_FRAMES = videoMetadata.sourceDurationInFrames;
const LOOP_DURATION_IN_FRAMES = SOURCE_DURATION_IN_FRAMES / SOURCE_PLAYBACK_RATE;
const MAX_GLOW_OPACITY = 0.7;
const MASK_WIDTH = 160;
const MASK_HEIGHT = 90;
const selection = selectVideoLightZones(
  lighting.zones as VideoLightZone[],
);
const selectedLightZones = selection.zones;

const flickerSchedules: Flicker[][] = [
  [
    {start: 3.6, end: 6.4, level: 1.75},
    {start: 15.2, end: 18.1, level: 1.68},
    {start: 25.0, end: 27.8, level: 1.72},
  ],
  [
    {start: 3.45, end: 4.20, level: 1.30},
    {start: 23.10, end: 23.82, level: 1.25},
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
    const fade = Math.min(0.65, (flicker.end - flicker.start) / 3);
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

const getOverlayOpacity = (brightness: number) =>
  Math.min(MAX_GLOW_OPACITY, Math.max(0, brightness - 1) * 0.84);

export const NightVideoLightingLoop: React.FC<{lightingEnabled?: boolean}> = ({
  lightingEnabled = true,
}) => {
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

      {lightingEnabled && lighting.animate && selectedLightZones.map((zone, index) => {
        const brightness = getBrightness(frame, fps, flickerSchedules[index]);
        if (brightness <= 1) return null;
        const opacity = getOverlayOpacity(brightness);
        const reflectionCutoff = (zone.y + zone.height * 0.02) * MASK_HEIGHT;
        const maskCells = (zone.maskCells ?? []).filter(([, y]) =>
          selection.mode === 'fallback' || zone.y < 0.62 || y <= reflectionCutoff,
        );
        if (maskCells.length === 0) return null;
        const [red, green, blue] = zone.color;
        const coreRed = Math.min(255, Math.round(red * 0.45 + 255 * 0.55));
        const coreGreen = Math.min(255, Math.round(green * 0.45 + 248 * 0.55));
        const coreBlue = Math.min(255, Math.round(blue * 0.45 + 224 * 0.55));

        const filterId = `source-feather-${zone.id}`;
        return (
          <svg
            key={zone.id}
            viewBox={`0 0 ${MASK_WIDTH} ${MASK_HEIGHT}`}
            preserveAspectRatio="none"
            style={{
              height: '100%',
              left: 0,
              mixBlendMode: 'screen',
              pointerEvents: 'none',
              position: 'absolute',
              top: 0,
              width: '100%',
            }}
          >
            <defs>
              <filter id={filterId} x="-30%" y="-30%" width="160%" height="160%">
                <feGaussianBlur stdDeviation="0.42" />
              </filter>
            </defs>
            <g filter={`url(#${filterId})`} opacity={opacity * 0.72}>
              {maskCells.map(([x, y], cellIndex) => (
                <rect
                  key={`halo-${cellIndex}`}
                  x={x - 0.18}
                  y={y - 0.18}
                  width="1.36"
                  height="1.36"
                  rx="0.16"
                  fill={`rgb(${red}, ${green}, ${blue})`}
                />
              ))}
            </g>
            <g opacity={Math.min(0.88, opacity * 1.16)}>
              {maskCells.map(([x, y], cellIndex) => (
                <rect
                  key={`core-${cellIndex}`}
                  x={x}
                  y={y}
                  width="1"
                  height="1"
                  rx="0.1"
                  fill={`rgb(${coreRed}, ${coreGreen}, ${coreBlue})`}
                />
              ))}
            </g>
          </svg>
        );
      })}
    </AbsoluteFill>
  );
};
