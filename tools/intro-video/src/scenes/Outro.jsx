import {AbsoluteFill, Easing, interpolate, useCurrentFrame} from 'remotion';
import {ACCENT, EASE_IN_OUT, EASE_OUT, INK, Icon, LINE, MONO, MUTED, PAPER, SANS, SERIF, beats, clamp} from '../brand.jsx';

const rise = (frame, start, distance = 30) => ({
  opacity: interpolate(frame, [start, start + 16], [0, 1], clamp),
  translate: interpolate(frame, [start, start + 36], [`0px ${distance}px`, '0px 0px'], {...clamp, easing: EASE_OUT}),
});
const FACTS = ['Free and open source', 'No AI account needed to read', 'Optional AI uses your own key'];

// Once the window has left, the icon fans out, then the name, the promise, the facts, and where to get it.
export const Outro = () => {
  const frame = useCurrentFrame();
  const start = beats(1);
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', fontFamily: SANS, color: INK, textAlign: 'center',
      scale: interpolate(frame, [beats(3), beats(12)], [1, 1.035], {...clamp, easing: EASE_IN_OUT})}}>
      <div style={{opacity: interpolate(frame, [start, start + 6], [0, 1], clamp),
        scale: interpolate(frame, [start, start + 40], [0.4, 1], {...clamp, easing: Easing.spring({damping: 12}), output: 'perceptual-scale'})}}>
        <Icon size={170} progress={interpolate(frame, [start, start + 60], [0, 1], clamp)} />
      </div>
      <div style={{display: 'flex', fontSize: 104, fontWeight: 650, letterSpacing: -3.5, marginTop: 12}}>
        {'LocalXiv'.split('').map((letter, i) => (
          <span key={i} style={{display: 'inline-block', ...rise(frame, beats(1.5) + i * 2, 44)}}>{letter}</span>
        ))}
      </div>
      <div style={{fontFamily: SERIF, fontSize: 44, color: MUTED, marginTop: 4, ...rise(frame, beats(2.5))}}>
        Read arXiv papers comfortably. On your Mac or Kindle.
      </div>
      <div style={{display: 'flex', gap: 14, marginTop: 40}}>
        {FACTS.map((fact, i) => (
          <div key={fact} style={{fontSize: 26, fontWeight: 600, padding: '12px 22px', borderRadius: 999, background: PAPER,
            border: `1.5px solid ${LINE}`, ...rise(frame, beats(3.5) + i * 3, 20),
            scale: interpolate(frame, [beats(3.5) + i * 3, beats(3.5) + i * 3 + 30], [0.9, 1], {...clamp, easing: Easing.spring({damping: 12}), output: 'perceptual-scale'})}}>
            {fact}
          </div>
        ))}
      </div>
      <div style={{fontFamily: MONO, fontSize: 30, color: PAPER, background: ACCENT, padding: '16px 30px', borderRadius: 999, marginTop: 40,
        ...rise(frame, beats(5), 24)}}>
        github.com/Akhil-Theerthala/LocalXiv
      </div>
      <div style={{fontSize: 22, color: MUTED, marginTop: 20, ...rise(frame, beats(5.5), 16)}}>Early preview · Apple Silicon · macOS 26 or newer</div>
    </AbsoluteFill>
  );
};
