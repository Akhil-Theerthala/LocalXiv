import {AbsoluteFill, Easing, interpolate, useCurrentFrame} from 'remotion';
import {ACCENT, EASE_IN, EASE_OUT, INK, Icon, SANS, SERIF, beats, clamp} from '../brand.jsx';
import {CUES} from '../timeline.mjs';

const LINES = [
  [['Read', SANS], ['arXiv', SANS], ['papers', SANS], ['comfortably.', SERIF]],
  [['On', SANS], ['your', SANS], ['Mac', SANS], ['or', SANS], ['Kindle.', SERIF]],
];

// Words land on eighth notes, then give way to the icon and wordmark, which push toward the camera into the app.
export const Title = () => {
  const frame = useCurrentFrame();
  const logo = beats(CUES.Title.logo);
  let word = 0;
  return (
    <AbsoluteFill style={{fontFamily: SANS, color: INK}}>
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', gap: 6,
        opacity: interpolate(frame, [logo - 14, logo + 4], [1, 0], {...clamp, easing: EASE_IN}),
        scale: interpolate(frame, [logo - 14, logo + 4], [1, 0.94], {...clamp, easing: EASE_IN}),
        filter: `blur(${interpolate(frame, [logo - 14, logo + 4], [0, 10], clamp)}px)`}}>
        {LINES.map((line, row) => (
          <div key={row} style={{display: 'flex', gap: 26, alignItems: 'baseline'}}>
            {line.map(([text, font]) => {
              const start = beats(CUES.Title.words[word++]);
              return (
                <span key={text} style={{fontFamily: font, fontSize: 112, fontWeight: font === SANS ? 650 : 400,
                  fontStyle: font === SERIF ? 'italic' : 'normal', letterSpacing: font === SANS ? -3.5 : -2,
                  color: font === SERIF ? ACCENT : INK, display: 'inline-block',
                  opacity: interpolate(frame, [start, start + 8], [0, 1], clamp),
                  translate: interpolate(frame, [start, start + 22], ['0px 70px', '0px 0px'], {...clamp, easing: Easing.spring({damping: 13})}),
                  rotate: interpolate(frame, [start, start + 22], ['5deg', '0deg'], {...clamp, easing: Easing.spring({damping: 13})})}}>
                  {text}
                </span>
              );
            })}
          </div>
        ))}
      </AbsoluteFill>
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center',
        opacity: interpolate(frame, [beats(7.5), beats(8)], [1, 0], {...clamp, easing: EASE_IN}),
        scale: interpolate(frame, [beats(7.5), beats(8)], [1, 1.5], {...clamp, easing: EASE_IN, output: 'perceptual-scale'})}}>
        <div style={{opacity: interpolate(frame, [logo, logo + 6], [0, 1], clamp),
          scale: interpolate(frame, [logo, logo + 40], [0.5, 1], {...clamp, easing: Easing.spring({damping: 12}), output: 'perceptual-scale'})}}>
          <Icon size={220} progress={interpolate(frame, [logo, logo + 60], [0, 1], clamp)} />
        </div>
        <div style={{display: 'flex', fontSize: 120, fontWeight: 650, letterSpacing: -4, marginTop: 18}}>
          {'LocalXiv'.split('').map((letter, i) => (
            <span key={i} style={{display: 'inline-block',
              opacity: interpolate(frame, [logo + 16 + i * 2, logo + 28 + i * 2], [0, 1], clamp),
              translate: interpolate(frame, [logo + 16 + i * 2, logo + 40 + i * 2], ['0px 50px', '0px 0px'], {...clamp, easing: EASE_OUT})}}>{letter}</span>
          ))}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
