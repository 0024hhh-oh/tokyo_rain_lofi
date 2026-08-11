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
        const radiusX = zone.width * 72;
        const radiusY = zone.height * 72;
        const featheredMask = `radial-gradient(ellipse ${radiusX}% ${radiusY}% at ${zone.x * 100}% ${zone.y * 100}%, black 0%, rgba(0, 0, 0, 0.94) 34%, rgba(0, 0, 0, 0.56) 62%, transparent 100%)`;
        const glowOpacity = lightsOn ? zone.strength * (0.06 + zone.warmth * 0.04) : 0;

        return (
          <div key={zone.id}>
            {!lightsOn && (
              <AbsoluteFill
                style={{
                  filter: `brightness(${0.27 + (1 - zone.strength) * 0.08}) saturate(0.58)`,
                  maskImage: featheredMask,
                  WebkitMaskImage: featheredMask,
                }}
              >
                <Img
                  src={staticFile('background.png')}
                  style={{height: '100%', objectFit: 'cover', width: '100%'}}
                />
              </AbsoluteFill>
            )}
            <div
              style={{
                background: `radial-gradient(ellipse, rgba(255, ${Math.round(185 + zone.warmth * 35)}, 128, ${glowOpacity}) 0%, rgba(255, 174, 96, 0) 72%)`,
                height: `${zone.height * 112}%`,
                left: `${zone.x * 100}%`,
                mixBlendMode: 'screen',
                position: 'absolute',
                top: `${zone.y * 100}%`,
                transform: 'translate(-50%, -50%)',
                width: `${zone.width * 112}%`,
              }}
            />
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
