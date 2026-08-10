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

const getLightLevel = (
  zone: LightZone,
  frame: number,
  fps: number,
) => {
  const seconds = frame / fps;
  const cycleSeconds = 5.2 + random(`${zone.id}-cycle`) * 2.4;
  const phase = random(`${zone.id}-phase`) * Math.PI * 2;
  const wave = Math.sin((seconds / cycleSeconds) * Math.PI * 2 + phase);

  // Cross the on/off boundary quickly enough to read as a light switching,
  // while retaining a short eased transition instead of a harsh strobe.
  const transition = clamp((wave + 0.16) / 0.32, 0, 1);
  const switched = transition * transition * (3 - 2 * transition);
  const slowDrift = Math.sin(
    (seconds / (cycleSeconds * 2.7)) * Math.PI * 2 + phase * 0.41,
  );

  return clamp(0.04 + switched * 0.92 + slowDrift * 0.025, 0.02, 1);
};

export const NightLightingLoop: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const zones = lighting.zones as LightZone[];

  return (
    <AbsoluteFill style={{backgroundColor: '#050608'}}>
      <Img
        src={staticFile('background.png')}
        style={{height: '100%', objectFit: 'cover', width: '100%'}}
      />

      {lighting.animate && zones.map((zone) => {
        const level = getLightLevel(zone, frame, fps);
        const left = (zone.x - zone.width / 2) * 100;
        const top = (zone.y - zone.height / 2) * 100;
        const right = 100 - (zone.x + zone.width / 2) * 100;
        const bottom = 100 - (zone.y + zone.height / 2) * 100;
        const brightness = 0.36 + level * zone.strength * 1.5;
        const glowOpacity = level * zone.strength * (0.24 + zone.warmth * 0.18);

        return (
          <div key={zone.id}>
            <AbsoluteFill
              style={{
                clipPath: `inset(${top}% ${right}% ${bottom}% ${left}% round 14%)`,
                filter: `brightness(${brightness}) saturate(${0.72 + level * zone.warmth * 0.48})`,
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
