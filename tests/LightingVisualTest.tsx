import {AbsoluteFill, Img, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
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

export const LightingVisualTest: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const lightsOn = frame >= fps * 4;
  const zones = lighting.zones as LightZone[];

  return (
    <AbsoluteFill style={{backgroundColor: '#050608'}}>
      <Img
        src={staticFile('background.png')}
        style={{height: '100%', objectFit: 'cover', width: '100%'}}
      />

      {lighting.animate && zones.map((zone) => {
        const left = (zone.x - zone.width / 2) * 100;
        const top = (zone.y - zone.height / 2) * 100;
        const right = 100 - (zone.x + zone.width / 2) * 100;
        const bottom = 100 - (zone.y + zone.height / 2) * 100;
        const brightness = lightsOn ? 1 + zone.strength * 0.7 : 0.16;
        const saturation = lightsOn ? 1 + zone.warmth * 0.35 : 0.42;
        const glowOpacity = lightsOn ? zone.strength * (0.28 + zone.warmth * 0.2) : 0;

        return (
          <div key={zone.id}>
            <AbsoluteFill
              style={{
                clipPath: `inset(${top}% ${right}% ${bottom}% ${left}% round 14%)`,
                filter: `brightness(${brightness}) saturate(${saturation})`,
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
