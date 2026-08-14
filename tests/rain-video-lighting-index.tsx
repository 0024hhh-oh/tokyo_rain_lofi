import {Composition, registerRoot} from 'remotion';
import {RainVideoLightingTest} from './RainVideoLightingTest';

const TestRoot: React.FC = () => (
  <Composition
    id="RainVideoLightingTest"
    component={RainVideoLightingTest}
    durationInFrames={900}
    fps={30}
    width={1920}
    height={1080}
  />
);

registerRoot(TestRoot);
