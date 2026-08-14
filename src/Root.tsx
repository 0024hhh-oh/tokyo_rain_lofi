import {Composition} from 'remotion';
import {NightLightingLoop} from './NightLightingLoop';
import {NightVideoLightingLoop} from './NightVideoLightingLoop';

export const Root: React.FC = () => {
  return (
    <>
      <Composition
        id="NightLightingLoop"
        component={NightLightingLoop}
        durationInFrames={900}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="NightVideoLightingLoop"
        component={NightVideoLightingLoop}
        durationInFrames={900}
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
