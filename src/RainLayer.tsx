import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';

const DROP_COUNT = 220;
const LOOP_FRAMES = 900;
const DROP_LIFETIMES = [30, 36, 45, 50, 60, 75];

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
      {drops.map((drop, index) => {
        const localFrame = (frame + drop.delay) % drop.lifetime;
        const progress = localFrame / drop.lifetime;
        const length = 26 + drop.depth * 46;
        const opacity = 0.16 + drop.depth * 0.32;
        const width = 0.8 + drop.depth * 1.1;
        const xDrift = interpolate(progress, [0, 1], [-28, 34]);
        const y = interpolate(progress, [0, 1], [-80, 1160]);

        return (
          <div
            key={index}
            style={{
              background:
                'linear-gradient(180deg, rgba(225,235,240,0), rgba(235,242,246,0.96))',
              borderRadius: 999,
              filter: `blur(${0.15 + (1 - drop.depth) * 0.35}px)`,
              height: length,
              left: `${drop.left}%`,
              opacity,
              position: 'absolute',
              top: 0,
              transform: `translate3d(${xDrift}px, ${y}px, 0) rotate(-8deg)`,
              width,
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};
