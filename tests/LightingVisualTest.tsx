import {
  AbsoluteFill,
  Img,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

const flickerSeconds = [
  0,
  1.56, 1.68, 1.78, 1.88, 1.98,
  4.48, 4.58, 4.67, 4.77,
  6.72, 6.82, 6.92, 7.02,
  8,
];

const flickerBrightness = [
  1,
  1, 0.7, 0.94, 0.76, 1,
  1, 0.82, 0.72, 1,
  1, 0.7, 0.92, 1,
  1,
];

// This mask is intentionally tied to the single red lantern in the supplied
// visual-test scene. It must not include the vending machine, windows, street
// lamps, or road reflections.
const lanternMask = 'radial-gradient(ellipse 2.35% 5.4% at 52.6% 48.2%, rgba(0, 0, 0, 1) 0%, rgba(0, 0, 0, 0.96) 58%, rgba(0, 0, 0, 0.48) 80%, transparent 100%)';

export const LightingVisualTest: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const lanternBrightness = interpolate(
    frame,
    flickerSeconds.map((second) => second * fps),
    flickerBrightness,
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  return (
    <AbsoluteFill style={{backgroundColor: '#050608'}}>
      <Img
        src={staticFile('background.png')}
        style={{height: '100%', objectFit: 'cover', width: '100%'}}
      />

      <AbsoluteFill
        style={{
          filter: `brightness(${lanternBrightness}) saturate(${0.9 + lanternBrightness * 0.1})`,
          maskImage: lanternMask,
          WebkitMaskImage: lanternMask,
        }}
      >
        <Img
          src={staticFile('background.png')}
          style={{height: '100%', objectFit: 'cover', width: '100%'}}
        />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
