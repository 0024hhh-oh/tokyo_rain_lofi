import {
  AbsoluteFill,
  Img,
  random,
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
};

const clamp = (value: number, min: number, max: number) =>
  Math.min(max, Math.max(min, value));

const circularDistance = (a: number, b: number) => {
  const direct = Math.abs(a - b);
  return Math.min(direct, 1 - direct);
};

const getLightLevel = (
  zone: LightZone,
  frame: number,
  durationInFrames: number,
) => {
  const progress = frame / durationInFrames;
  const phase = random(`${zone.id}-phase`) * Math.PI * 2;
  const slowCycles = 1 + Math.floor(random(`${zone.id}-slow`) * 3);
  const mediumCycles = 4 + Math.floor(random(`${zone.id}-medium`) * 4);
  const quickCycles = 9 + Math.floor(random(`${zone.id}-quick`) * 7);

  const drift =
    Math.sin(progress * Math.PI * 2 * slowCycles + phase) * 0.48 +
    Math.sin(progress * Math.PI * 2 * mediumCycles + phase * 0.63) * 0.22 +
    Math.sin(progress * Math.PI * 2 * quickCycles + phase * 1.31) * 0.08;

  const dipCount = 1 + Math.floor(random(`${zone.id}-dip-count`) * 3);
  let softDip = 0;
  for (let index = 0; index < dipCount; index += 1) {
    const center = random(`${zone.id}-dip-${index}`);
    const width = 0.009 + random(`${zone.id}-dip-width-${index}`) * 0.018;
    const distance = circularDistance(progress, center);
    softDip += Math.exp(-0.5 * (distance / width) ** 2) *
      (0.18 + random(`${zone.id}-dip-depth-${index}`) * 0.2);
  }

  return clamp(0.56 + drift - softDip, 0.12, 1);
};

export const NightLightingLoop: React.FC = () => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const zones = lighting.zones as LightZone[];

  return (
    <AbsoluteFill style={{backgroundColor: '#050608'}}>
      <Img
        src={staticFile('background.png')}
        style={{height: '100%', objectFit: 'cover', width: '100%'}}
      />

      {lighting.animate && zones.map((zone) => {
        const level = getLightLevel(zone, frame, durationInFrames);
        const left = (zone.x - zone.width / 2) * 100;
        const top = (zone.y - zone.height / 2) * 100;
        const right = 100 - (zone.x + zone.width / 2) * 100;
        const bottom = 100 - (zone.y + zone.height / 2) * 100;
        const brightness = 1 + level * zone.strength * 0.13;
        const glowOpacity = level * zone.strength * (0.035 + zone.warmth * 0.035);

        return (
          <div key={zone.id}>
            <AbsoluteFill
              style={{
                clipPath: `inset(${top}% ${right}% ${bottom}% ${left}% round 14%)`,
                filter: `brightness(${brightness}) saturate(${1 + zone.warmth * 0.05})`,
                maskImage: `radial-gradient(ellipse at ${zone.x * 100}% ${zone.y * 100}%, black 0%, transparent 74%)`,
                WebkitMaskImage: `radial-gradient(ellipse at ${zone.x * 100}% ${zone.y * 100}%, black 0%, transparent 74%)`,
              }}
            >
              <Img
                src={staticFile('background.png')}
                style={{height: '100%', objectFit: 'cover', width: '100%'}}
              />
            </AbsoluteFill>
            <div
              style={{
                background: `radial-gradient(ellipse, rgba(255, ${Math.round(185 + zone.warmth * 35)}, 128, ${glowOpacity}) 0%, rgba(255, 174, 96, 0) 72%)`,
                height: `${zone.height * 126}%`,
                left: `${zone.x * 100}%`,
                mixBlendMode: 'screen',
                position: 'absolute',
                top: `${zone.y * 100}%`,
                transform: 'translate(-50%, -50%)',
                width: `${zone.width * 126}%`,
              }}
            />
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
