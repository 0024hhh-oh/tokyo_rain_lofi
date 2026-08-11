import {AbsoluteFill, Img, staticFile} from 'remotion';
import {RainLayer} from './RainLayer';

export const DayRainLoop: React.FC = () => (
  <AbsoluteFill style={{backgroundColor: '#c9ced0'}}>
    <Img
      src={staticFile('background.png')}
      style={{height: '100%', objectFit: 'cover', width: '100%'}}
    />
    <RainLayer />
  </AbsoluteFill>
);
