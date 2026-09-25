import {AbsoluteFill, Easing, interpolate, useCurrentFrame} from 'remotion';
import {EASE_IN, EASE_IN_OUT, EASE_OUT, PAPER, beats, clamp} from '../brand.jsx';
import {Camera, Crop, Shot} from '../stage.jsx';
import {CUES} from '../timeline.mjs';
import rects from '../../public/rects.json';

// Preferences pop open, the text grows, and dark mode spreads out from the theme button.
export const Read = () => {
  const frame = useCurrentFrame();
  const {preferences: open, preferencesClose: close, size, dark} = CUES.Read;
  const toggle = [rects.themeToggle.x + rects.themeToggle.width / 2, rects.themeToggle.y + rects.themeToggle.height / 2];
  const dialog = interpolate(frame, [beats(open), beats(open) + 8, beats(close), beats(close) + 10], [0, 1, 1, 0], clamp);
  return (
    <AbsoluteFill style={{background: PAPER}}>
      <Camera easing={EASE_IN_OUT} move={40}
        keys={[[0, 720, 450, 1], [beats(size), 640, 560, 1.16], [beats(dark - 1), 720, 450, 1], [beats(dark + 0.75), 640, 540, 1.1]]}>
        <Shot src="paper.png" />
        <Shot src="paper-large.png" style={{opacity: interpolate(frame, [beats(size), beats(size) + 12], [0, 1], clamp)}} />
        <Shot src="paper-preferences.png" style={{opacity: dialog}} />
        <Crop src="paper-preferences.png" rect={rects.preferences} style={{borderRadius: 20, opacity: dialog,
          scale: interpolate(frame, [beats(open), beats(open) + 30, beats(close), beats(close) + 10], [0.88, 1, 1, 0.96],
            {...clamp, easing: [Easing.spring({damping: 12}), Easing.linear, EASE_IN], output: 'perceptual-scale'})}} />
        <Shot src="paper-large-dark.png" style={{
          clipPath: `circle(${interpolate(frame, [beats(dark), beats(dark) + 28], [0, 1750], {...clamp, easing: EASE_IN_OUT})}px at ${toggle[0]}px ${toggle[1]}px)`}} />
        <div style={{position: 'absolute', left: toggle[0] - 40, top: toggle[1] - 40, width: 80, height: 80, borderRadius: '50%',
          border: '3px solid #d1dea8', visibility: frame >= beats(dark) ? 'visible' : 'hidden',
          opacity: interpolate(frame, [beats(dark), beats(dark) + 30], [1, 0], clamp),
          scale: interpolate(frame, [beats(dark), beats(dark) + 30], [0.4, 1.8], {...clamp, easing: EASE_OUT})}} />
      </Camera>
    </AbsoluteFill>
  );
};
