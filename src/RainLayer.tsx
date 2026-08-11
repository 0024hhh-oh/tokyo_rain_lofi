import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';

const DROP_COUNT = 720;
const LOOP_FRAMES = 900;
const DROP_LIFETIMES = [16, 18, 21, 24, 28, 32];

type RainDrop = {
  delay: number;
  depth: number;
  left: number;
  lifetime: number;
};

// Fixed arithmetic keeps every render deterministic while avoiding an obvious grid.
const drops: RainDrop[] = Array.from({length: DROP_COUNT}, (_, index) => ({
  delay: (index * 137 + index * index * 17) % LOOP_FRAMES,
  depth: ((index * 29) % 100) / 100,
  left: (index * 61 + index * index * 13) % 104 - 2,
  lifetime: DROP_LIFETIMES[index % DROP_LIFETIMES.length],
}));

export const RainLayer: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill style={{overflow: 'hidden', pointerEvents: 'none'}}>
      <AbsoluteFill
        style={{
          background:
            'linear-gradient(105deg, rgba(190,205,215,0.05), rgba(220,230,236,0.13) 48%, rgba(170,190,202,0.07))',
        }}
      />
      {drops.map((drop, index) => {
        const localFrame = (frame + drop.delay) % drop.lifetime;
        const progress = localFrame / drop.lifetime;
        const length = 50 + drop.depth * 100;
        const opacity = 0.32 + drop.depth * 0.5;
        const width = 0.9 + drop.depth * 2.3;
        const xDrift = interpolate(progress, [0, 1], [-52, 78]);
        const y = interpolate(progress, [0, 1], [-180, 1260]);

        return (
          <div
            key={index}
            style={{
              background:
                'linear-gradient(180deg, rgba(220,232,240,0), rgba(242,247,250,0.98))',
              borderRadius: 999,
              filter: `blur(${0.1 + (1 - drop.depth) * 0.45}px)`,
              height: length,
              left: `${drop.left}%`,
              opacity,
              position: 'absolute',
              top: 0,
              transform: `translate3d(${xDrift}px, ${y}px, 0) rotate(-11deg)`,
              width,
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};
