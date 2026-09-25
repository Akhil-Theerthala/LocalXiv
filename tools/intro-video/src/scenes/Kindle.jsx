import {AbsoluteFill, Easing, Img, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {ACCENT, EASE_IN, EASE_IN_OUT, EASE_OUT, INK, LINE, MONO, PAPER, arc, beats, clamp} from '../brand.jsx';
import {Camera, Crop, EXIT, Shot, toStage} from '../stage.jsx';
import {CUES} from '../timeline.mjs';
import rects from '../../public/rects.json';

const SEND_BUTTON = [603, 666];
const READER = {x: 1560, y: 600, width: 420, height: 580};

// Share opens over the Blog, and the dialog grows as Send to Kindle expands.
export const Kindle = () => {
  const frame = useCurrentFrame();
  const {share, shareKindle} = rects;
  const expand = interpolate(frame, [beats(CUES.Kindle.expand), beats(CUES.Kindle.expand) + 26], [0, 1], {...clamp, easing: EASE_OUT});
  const inset = key => share[key] + (shareKindle[key] - share[key]) * expand;
  const open = beats(0.5);
  return (
    <AbsoluteFill style={{background: PAPER}}>
      <Camera easing={EASE_IN_OUT} move={40} keys={[[0, 720, 450, 1], [beats(1), 720, 460, 1.1], [beats(CUES.Kindle.send - 1.5), 720, 450, 1]]}>
        <Shot src="blog.png" />
        <Shot src="share.png" style={{opacity: interpolate(frame, [open, open + 10], [0, 1], clamp)}} />
        <Shot src="share-kindle.png" style={{opacity: expand}} />
        <Crop src="share.png" rect={share} style={{borderRadius: 22, opacity: interpolate(frame, [open, open + 8], [0, 1], clamp) * (1 - expand),
          scale: interpolate(frame, [open, open + 30], [0.88, 1], {...clamp, easing: Easing.spring({damping: 12}), output: 'perceptual-scale'})}} />
        <Crop src="share-kindle.png" rect={{x: inset('x'), y: inset('y'), width: inset('width'), height: inset('height')}}
          style={{borderRadius: 22, opacity: expand > 0 ? 1 : 0}} />
      </Camera>
    </AbsoluteFill>
  );
};

// Outside the window: an EPUB flies on an arc from Send to Kindle into a generic e-reader, which refreshes like e-ink.
export const KindleReader = () => {
  const frame = useCurrentFrame();
  const {send, arrive} = CUES.Kindle;
  const enter = interpolate(frame, [beats(send - 1), beats(send)], [0, 1], {...clamp, easing: Easing.spring({damping: 14})});
  const leave = interpolate(frame, [beats(12), beats(12) + EXIT], [0, 1], {...clamp, easing: EASE_IN});
  const flight = interpolate(frame, [beats(send), beats(arrive)], [0, 1], {...clamp, easing: EASE_IN_OUT});
  const [chipX, chipY] = arc(flight, toStage('Kindle', SEND_BUTTON), [READER.x, READER.y], 220);
  const refresh = frame - beats(arrive);
  return (
    <AbsoluteFill style={{perspective: 2000}}>
      <div style={{position: 'absolute', left: READER.x - READER.width / 2, top: READER.y - READER.height / 2, width: READER.width, height: READER.height,
        borderRadius: 34, background: '#2b2d2a', boxShadow: '0 40px 90px #1f281740, inset 0 0 0 2px #3c3f3a', padding: '34px 28px 60px', boxSizing: 'border-box',
        opacity: (1 - leave), transform: `translateX(${(1 - enter) * 520 + leave * 300}px) rotateY(${-24 + 14 * enter}deg)`}}>
        <div style={{position: 'relative', width: '100%', height: '100%', background: '#ebe9e2', borderRadius: 6, overflow: 'hidden'}}>
          {refresh >= 4 && (
            <Img src={staticFile('blog-full.png')} style={{position: 'absolute', width: 1440 * 0.4, left: -270 * 0.4 + 4, top: -450 * 0.4 + 12,
              filter: 'grayscale(1) contrast(1.15)', mixBlendMode: 'multiply',
              clipPath: `inset(0 0 ${interpolate(refresh, [4, 22], [100, 0], {...clamp, easing: EASE_OUT})}% 0)`}} />
          )}
          <AbsoluteFill style={{background: INK, opacity: refresh >= 0 && refresh < 4 ? 1 : 0}} />
        </div>
      </div>
      {flight > 0 && flight < 1 && (
        <div style={{position: 'absolute', left: chipX - 70, top: chipY - 44, width: 140, height: 88, borderRadius: 14, background: PAPER,
          border: `2px solid ${LINE}`, boxShadow: '0 18px 40px #1f281733', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
          rotate: `${interpolate(flight, [0, 0.5, 1], [0, 10, 0])}deg`, scale: String(interpolate(flight, [0, 0.15, 1], [0.6, 1, 0.55], clamp))}}>
          <svg width="26" height="32" viewBox="0 0 26 32"><path d="M2 2h15l7 7v21H2z" fill={PAPER} stroke={ACCENT} strokeWidth="2.5" strokeLinejoin="round" /><path d="M17 2v7h7" fill="none" stroke={ACCENT} strokeWidth="2.5" /></svg>
          <span style={{fontFamily: MONO, fontSize: 22, fontWeight: 700, color: ACCENT}}>EPUB</span>
        </div>
      )}
    </AbsoluteFill>
  );
};
