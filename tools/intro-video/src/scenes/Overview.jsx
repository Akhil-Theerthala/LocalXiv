import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {ACCENT, EASE_IN_OUT, EASE_OUT, PAPER, beats, clamp} from '../brand.jsx';
import {CONTENT, Camera, Shot} from '../stage.jsx';

// The figure is 2000 pixels wide; at the window's 1440 it is 2350 tall.
const FIGURE_HEIGHT = 3264 * CONTENT.width / 2000;
const BEST_RESULT = {x: 728, y: 1996, width: 486, height: 36};

// The in-app Overview, then a camera that stops on each panel on a downbeat and ends on the best BLEU score.
export const Overview = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{background: PAPER}}>
      <Camera keys={[[0, 720, 450, 1], [beats(0.5), 720, 520, 1.05]]} move={beats(3.5)}>
        <Shot src="overview.png" />
      </Camera>
      <AbsoluteFill style={{background: PAPER, opacity: interpolate(frame, [beats(4), beats(4) + 14], [0, 1], clamp)}}>
        <Camera easing={EASE_IN_OUT} move={36}
          keys={[[0, 720, 450, 1], [beats(6), 720, 475, 1], [beats(8), 720, 970, 1], [beats(10), 720, 1724, 0.95], [beats(12.5), 971, 1990, 2]]}>
          <Img src={staticFile('attention_figure.png')} style={{position: 'absolute', width: CONTENT.width, height: FIGURE_HEIGHT}} />
          <svg style={{position: 'absolute', left: BEST_RESULT.x, top: BEST_RESULT.y, overflow: 'visible'}} width={BEST_RESULT.width} height={BEST_RESULT.height}>
            <rect x="0" y="0" width={BEST_RESULT.width} height={BEST_RESULT.height} rx="8" fill="none" stroke={ACCENT} strokeWidth="2.5"
              pathLength="1" strokeDasharray="1" strokeDashoffset={interpolate(frame, [beats(13.25), beats(13.25) + 30], [1, 0], {...clamp, easing: EASE_OUT})} />
          </svg>
        </Camera>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
