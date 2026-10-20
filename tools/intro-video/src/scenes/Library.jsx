import {AbsoluteFill, Easing, interpolate, useCurrentFrame} from 'remotion';
import {ACCENT, EASE_OUT, PAPER, beats, clamp} from '../brand.jsx';
import {Camera, Shot} from '../stage.jsx';
import rects from '../../public/rects.json';

// The saved paper drops into its row, squashes a little on landing, and the highlight fades.
export const Library = () => {
  const frame = useCurrentFrame();
  const {x, y, width, height} = rects.libraryRow;
  const drop = beats(0.5);
  return (
    <AbsoluteFill style={{background: PAPER}}>
      <Camera keys={[[0, 720, 450, 1], [beats(0.5), 720, 420, 1.08]]} move={beats(3)}>
        <Shot src="library.png" />
        <div style={{position: 'absolute', left: x - 8, top: y + 4, width: width + 16, height: height - 8, borderRadius: 16,
          border: `2.5px solid ${ACCENT}`, background: '#e9eddf66', transformOrigin: '50% 100%',
          opacity: interpolate(frame, [drop, drop + 8, beats(3), beats(3.8)], [0, 1, 1, 0], clamp),
          translate: interpolate(frame, [drop, drop + 18], ['0px -90px', '0px 0px'], {...clamp, easing: Easing.in(Easing.quad)}),
          scale: interpolate(frame, [drop + 18, drop + 24, drop + 40], [1, 0.96, 1], {...clamp, easing: [EASE_OUT, Easing.spring({damping: 10})]})}} />
      </Camera>
    </AbsoluteFill>
  );
};
