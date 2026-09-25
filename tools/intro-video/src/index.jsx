import {Composition, registerRoot} from 'remotion';
import {Intro, FPS, DURATION} from './Intro';

registerRoot(() => (
  <Composition id="Intro" component={Intro} durationInFrames={DURATION * FPS} fps={FPS} width={1920} height={1080} />
));
