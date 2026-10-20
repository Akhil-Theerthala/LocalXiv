import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {ACCENT, EASE_IN_OUT, EASE_OUT, PAPER, beats, clamp} from '../brand.jsx';
import {Camera, Shot} from '../stage.jsx';
import rects from '../../public/rects.json';

// Scroll to the attention equation, hold on it, then keep reading.
export const Blog = () => {
  const frame = useCurrentFrame();
  const {x, y, width, height} = rects.blogEquation;
  const center = [x + width / 2, y + height / 2];
  return (
    <AbsoluteFill style={{background: PAPER}}>
      <Camera easing={EASE_IN_OUT} move={44}
        keys={[[0, 720, 450, 1], [beats(0.75), 720, center[1] - 60, 1], [beats(2.5), center[0], center[1], 1.5], [beats(5.5), 720, 1500, 1]]}>
        <Shot src="blog-full.png" />
        <div style={{position: 'absolute', left: center[0] - 230, top: y + height + 6, height: 5, borderRadius: 3, background: ACCENT,
          width: interpolate(frame, [beats(3), beats(3) + 24], [0, 460], {...clamp, easing: EASE_OUT}),
          opacity: interpolate(frame, [beats(5), beats(5.5)], [1, 0], clamp)}} />
      </Camera>
    </AbsoluteFill>
  );
};
