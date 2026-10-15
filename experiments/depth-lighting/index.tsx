import React from 'react';
import {Composition, registerRoot} from 'remotion';
import {Scene, Comparison} from './Scene';
import {SceneWithRain} from './RainLayers';
import {FPS, FRAMES} from './timing';
const Root: React.FC = () => <>
  <Composition id="DepthLightingClean" component={Scene} durationInFrames={FRAMES} fps={FPS} width={1920} height={1080}/>
  <Composition id="DepthLightingRain" component={SceneWithRain} durationInFrames={FRAMES} fps={FPS} width={1920} height={1080}/>
  <Composition id="DepthLightingCompare" component={Comparison} durationInFrames={FRAMES} fps={FPS} width={1920} height={1080}/>
</>;
registerRoot(Root);
