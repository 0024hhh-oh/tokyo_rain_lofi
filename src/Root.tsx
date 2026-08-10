import {Composition} from 'remotion';
import {NightLightingLoop} from './NightLightingLoop';

export const Root: React.FC = () => {
  return (
    <Composition
      id="NightLightingLoop"
      component={NightLightingLoop}
      durationInFrames={900}
      fps={30}
      width={1920}
      height={1080}
    />
  );
};
