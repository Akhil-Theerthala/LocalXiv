import {Composition, Folder, registerRoot} from 'remotion';
import {Intro} from './Intro.jsx';
import {CONTENT} from './stage.jsx';
import {FPS, BEAT, TOTAL_BEATS} from './timeline.mjs';
import {Add} from './scenes/Add.jsx';
import {Blog} from './scenes/Blog.jsx';
import {Kindle} from './scenes/Kindle.jsx';
import {Library} from './scenes/Library.jsx';
import {Outro} from './scenes/Outro.jsx';
import {Overview} from './scenes/Overview.jsx';
import {Read} from './scenes/Read.jsx';
import {Title} from './scenes/Title.jsx';

const stage = {width: 1920, height: 1080, fps: FPS};
const window = {...CONTENT, fps: FPS};

registerRoot(() => (
  <>
    <Composition id="Intro" component={Intro} durationInFrames={TOTAL_BEATS * BEAT} {...stage} />
    <Folder name="Scenes">
      <Composition id="Title" component={Title} durationInFrames={8 * BEAT} {...stage} />
      <Composition id="Outro" component={Outro} durationInFrames={12 * BEAT} {...stage} />
    </Folder>
    <Folder name="Window-scenes">
      <Composition id="Add" component={Add} durationInFrames={12 * BEAT} {...window} />
      <Composition id="Library" component={Library} durationInFrames={4 * BEAT} {...window} />
      <Composition id="Read" component={Read} durationInFrames={16 * BEAT} {...window} />
      <Composition id="Overview" component={Overview} durationInFrames={16 * BEAT} {...window} />
      <Composition id="Blog" component={Blog} durationInFrames={8 * BEAT} {...window} />
      <Composition id="Kindle" component={Kindle} durationInFrames={12 * BEAT} {...window} />
    </Folder>
  </>
));
