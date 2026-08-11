import {Composition, registerRoot} from 'remotion';
import {LightingVisualTest} from './LightingVisualTest';

const TestRoot: React.FC = () => (
  <Composition
    id="LightingVisualTest"
    component={LightingVisualTest}
    durationInFrames={240}
    fps={30}
    width={1920}
    height={1080}
  />
);

registerRoot(TestRoot);
