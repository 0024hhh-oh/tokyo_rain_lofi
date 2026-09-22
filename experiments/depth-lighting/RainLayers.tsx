import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {Scene, type LightingProfile} from './Scene';

// Both trajectories wrap at the same 30-second boundary. Different travel
// counts give the two planes different speeds without a shared opacity pulse.
const FRAMES = 900;
const WIDTH = 1920;
const HEIGHT = 1080;

type RainPlane = {
  count: number;
  cycles: number;
  margin: number;
  length: number;
  width: number;
  opacity: number;
  blur: number;
  seed: number;
};

const planes: RainPlane[] = [
  {count: 72, cycles: 3, margin: 42, length: 13, width: 0.8, opacity: 0.13, blur: 0.3, seed: 17},
  {count: 32, cycles: 5, margin: 74, length: 28, width: 1.3, opacity: 0.18, blur: 0.5, seed: 83},
];

const hash = (n: number) => {
  const value = Math.sin(n * 127.1 + 19.7) * 43758.5453;
  return value - Math.floor(value);
};

export const RainLayers: React.FC = () => {
  const frame = useCurrentFrame() % FRAMES;
  return (
    <AbsoluteFill style={{pointerEvents: 'none', overflow: 'hidden', mixBlendMode: 'screen'}}>
      {planes.map((plane, layer) =>
        Array.from({length: plane.count}, (_, index) => {
          const key = plane.seed + index * 29;
          const span = HEIGHT + plane.margin * 2;
          const x = 12 + hash(key) * (WIDTH - 24);
          const origin = hash(key + 7) * span;
          const y = (origin + frame * plane.cycles * span / FRAMES) % span - plane.margin;
          const opacity = plane.opacity * (0.65 + hash(key + 13) * 0.35);
          return (
            <div key={layer + '-' + index} style={{
              position: 'absolute',
              left: x,
              top: y,
              width: plane.width,
              height: plane.length,
              borderRadius: '50%',
              background: 'linear-gradient(to bottom, transparent, rgba(207,222,231,0.9) 55%, transparent)',
              opacity,
              filter: 'blur(' + plane.blur + 'px)',
              transform: 'rotate(9deg)',
              transformOrigin: 'top center',
            }} />
          );
        })
      )}
    </AbsoluteFill>
  );
};

export const SceneWithRain: React.FC<{profile?: LightingProfile}> = ({profile}) => (
  <AbsoluteFill>
    <Scene profile={profile} />
    <RainLayers />
  </AbsoluteFill>
);
