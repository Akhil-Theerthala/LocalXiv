import {Audio} from '@remotion/media';
import {TransitionSeries, springTiming} from '@remotion/transitions';
import {fade} from '@remotion/transitions/fade';
import {slide} from '@remotion/transitions/slide';
import {AbsoluteFill, Sequence, staticFile} from 'remotion';
import {Background, Caption, beats} from './brand.jsx';
import {EXIT, Window} from './stage.jsx';
import {START, TRANSITION} from './timeline.mjs';
import {Add} from './scenes/Add.jsx';
import {Blog} from './scenes/Blog.jsx';
import {Kindle, KindleReader} from './scenes/Kindle.jsx';
import {Library} from './scenes/Library.jsx';
import {Outro} from './scenes/Outro.jsx';
import {Overview} from './scenes/Overview.jsx';
import {Read} from './scenes/Read.jsx';
import {Title} from './scenes/Title.jsx';

// Navigation slides; a change of mode fades. Every change starts on its scene's first beat.
const timing = springTiming({config: {damping: 200}, durationInFrames: TRANSITION});
const CAPTIONS = [
  {id: 'Add', eyebrow: 'Add', title: 'Paste an arXiv or alphaXiv link.', layout: 'top'},
  {id: 'Library', eyebrow: 'Library', title: 'It joins your library on your Mac.', layout: 'top'},
  {id: 'Read', eyebrow: 'Read', title: 'Choose your font, text size, margins, and theme.', layout: 'left'},
  {id: 'Overview', eyebrow: 'Overview', title: 'See the core of the paper in one figure.', layout: 'top'},
  {id: 'Blog', eyebrow: 'Blog', title: 'Read a longer explanation, with source citations.', layout: 'right'},
  {id: 'Kindle', eyebrow: 'Kindle', title: 'Export an EPUB, or send it to your Kindle.', layout: 'top'},
];
const NEXT = {Add: 'Library', Library: 'Read', Read: 'Overview', Overview: 'Blog', Blog: 'Kindle', Kindle: 'Outro'};

export const Intro = () => (
  <AbsoluteFill>
    <Background />
    <Sequence name="Title" durationInFrames={beats(START.Add)}>
      <Title />
    </Sequence>
    {CAPTIONS.map(({id, ...caption}) => {
      const length = beats(START[NEXT[id]] - START[id] - 0.5);
      return (
        <Sequence key={id} name={`${id} caption`} from={beats(START[id] + 0.5)} durationInFrames={length}>
          <Caption {...caption} length={length} />
        </Sequence>
      );
    })}
    <Window>
      <Sequence name="Window" from={beats(START.Add)}>
        <TransitionSeries>
          <TransitionSeries.Sequence name="Add" durationInFrames={beats(12) + TRANSITION}>
            <Add />
          </TransitionSeries.Sequence>
          <TransitionSeries.Transition presentation={slide({direction: 'from-right'})} timing={timing} />
          <TransitionSeries.Sequence name="Library" durationInFrames={beats(4) + TRANSITION}>
            <Library />
          </TransitionSeries.Sequence>
          <TransitionSeries.Transition presentation={slide({direction: 'from-right'})} timing={timing} />
          <TransitionSeries.Sequence name="Read" durationInFrames={beats(16) + TRANSITION}>
            <Read />
          </TransitionSeries.Sequence>
          <TransitionSeries.Transition presentation={fade()} timing={timing} />
          <TransitionSeries.Sequence name="Overview" durationInFrames={beats(16) + TRANSITION}>
            <Overview />
          </TransitionSeries.Sequence>
          <TransitionSeries.Transition presentation={fade()} timing={timing} />
          <TransitionSeries.Sequence name="Blog" durationInFrames={beats(8) + TRANSITION}>
            <Blog />
          </TransitionSeries.Sequence>
          <TransitionSeries.Transition presentation={fade()} timing={timing} />
          <TransitionSeries.Sequence name="Kindle" durationInFrames={beats(12) + EXIT}>
            <Kindle />
          </TransitionSeries.Sequence>
        </TransitionSeries>
      </Sequence>
    </Window>
    <Sequence name="E-reader" from={beats(START.Kindle)} durationInFrames={beats(12) + EXIT}>
      <KindleReader />
    </Sequence>
    <Sequence name="Outro" from={beats(START.Outro)}>
      <Outro />
    </Sequence>
    <Audio src={staticFile('music.wav')} />
  </AbsoluteFill>
);
