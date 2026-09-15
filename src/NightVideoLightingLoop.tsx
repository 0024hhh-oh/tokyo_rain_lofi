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
  zoneIndexes: number[];
};

const SOURCE_PLAYBACK_RATE = 0.5;
const SOURCE_DURATION_IN_FRAMES = videoMetadata.sourceDurationInFrames;
const LOOP_DURATION_IN_FRAMES = SOURCE_DURATION_IN_FRAMES / SOURCE_PLAYBACK_RATE;
const MAX_GLOW_OPACITY = 1;
const MASK_WIDTH = 160;
const MASK_HEIGHT = 90;
const selection = selectVideoLightZones(
  lighting.zones as VideoLightZone[],
);
const selectedLightZones = selection.zones;

const seededOrder = (length: number, seed: number) =>
  Array.from({length}, (_, index) => index)
    .sort((a, b) => {
      const scoreA = Math.sin((a + 1) * 91.7 + seed * 17.3);
      const scoreB = Math.sin((b + 1) * 91.7 + seed * 17.3);
      return scoreA - scoreB || a - b;
    });

const eventSpecs = [
  {start: 1.2, end: 3.8, level: 2.14, count: 3},
  {start: 4.0, end: 6.8, level: 2.22, count: 1},
  {start: 8.4, end: 11.0, level: 2.16, count: 3},
  {start: 12.0, end: 14.6, level: 2.20, count: 2},
  {start: 15.6, end: 18.2, level: 2.18, count: 3},
  {start: 19.2, end: 21.8, level: 2.24, count: 2},
  {start: 22.8, end: 25.4, level: 2.16, count: 3},
  {start: 26.4, end: 29.2, level: 2.22, count: 2},
] as const;

const makeEvents = (): Flicker[] => {
  const order = seededOrder(selectedLightZones.length, 137);
  const maxCount = Math.max(1, selectedLightZones.length - 1);
  let cursor = 0;
  return eventSpecs.map(({start, end, level, count: requestedCount}) => {
    const count = Math.min(requestedCount, 3, maxCount);
    const zoneIndexes = Array.from(
      {length: Math.min(count, order.length)},
      (_, offset) => order[(cursor + offset) % order.length],
    );
    cursor += zoneIndexes.length;
    return {start, end, level, zoneIndexes};
  });
};

// A seeded shuffled cycle looks random but guarantees that every selected
// source is used before the cycle repeats. Every event still lights only 1-3.
const flickerEvents = makeEvents();

const getBrightness = (frame: number, fps: number, zoneIndex: number) => {
  const seconds = frame / fps;
  let brightness = 1;
  for (const flicker of flickerEvents) {
    if (!flicker.zoneIndexes.includes(zoneIndex)) continue;
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
  Math.min(MAX_GLOW_OPACITY, Math.max(0, brightness - 1) * 1.2);

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
        const brightness = getBrightness(frame, fps, index);
        if (brightness <= 1) return null;
        const opacity = getOverlayOpacity(brightness);
        // Never promote a separately detected road reflection to a light event.
        // For low emitters, retain only their source-facing upper mask cells;
        // any future reflection overlay must be driven by this same event.
        const reflectionCutoff = (zone.y + zone.height * 0.02) * MASK_HEIGHT;
        const maskCells = (zone.maskCells ?? []).filter(([, y]) =>
          zone.y < 0.62 || y <= reflectionCutoff,
        );
        if (maskCells.length === 0) return null;
        // Distant lights occupy only a few 12px mask cells at 1080p. A single
        // tight overlay is technically brighter but still invisible on a
        // phone. Use three source-shaped bands so the increase reads clearly
        // without turning it into a circular or full-surface glow.
        const isSmallSource = maskCells.length <= 6;
        const outerPadding = isSmallSource ? 1.25 : 0.42;
        const middlePadding = isSmallSource ? 0.62 : 0.28;
        const corePadding = isSmallSource ? 0.12 : 0;
        const [red, green, blue] = zone.color;
        const coreRed = Math.min(255, Math.round(red * 0.25 + 255 * 0.75));
        const coreGreen = Math.min(255, Math.round(green * 0.25 + 250 * 0.75));
        const coreBlue = Math.min(255, Math.round(blue * 0.25 + 226 * 0.75));

        const outerFilterId = `source-outer-${zone.id}`;
        const middleFilterId = `source-middle-${zone.id}`;
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
              <filter id={outerFilterId} x="-80%" y="-80%" width="260%" height="260%">
                <feGaussianBlur stdDeviation="1.05" />
              </filter>
              <filter id={middleFilterId} x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="0.38" />
              </filter>
            </defs>
            <g
              filter={`url(#${outerFilterId})`}
              opacity={Math.min(0.78, opacity * 0.78)}
            >
              {maskCells.map(([x, y], cellIndex) => (
                <rect
                  key={`outer-${cellIndex}`}
                  x={x - outerPadding}
                  y={y - outerPadding}
                  width={1 + outerPadding * 2}
                  height={1 + outerPadding * 2}
                  rx="0.22"
                  fill={`rgb(${red}, ${green}, ${blue})`}
                />
              ))}
            </g>
            <g
              filter={`url(#${middleFilterId})`}
              opacity={Math.min(0.96, opacity * 1.05)}
            >
              {maskCells.map(([x, y], cellIndex) => (
                <rect
                  key={`middle-${cellIndex}`}
                  x={x - middlePadding}
                  y={y - middlePadding}
                  width={1 + middlePadding * 2}
                  height={1 + middlePadding * 2}
                  rx="0.16"
                  fill={`rgb(${red}, ${green}, ${blue})`}
                />
              ))}
            </g>
            <g opacity={Math.min(1, opacity * 1.4)}>
              {maskCells.map(([x, y], cellIndex) => (
                <rect
                  key={`core-${cellIndex}`}
                  x={x - corePadding}
                  y={y - corePadding}
                  width={1 + corePadding * 2}
                  height={1 + corePadding * 2}
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
