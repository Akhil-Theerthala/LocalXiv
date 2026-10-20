import {AbsoluteFill, Easing, interpolate, useCurrentFrame} from 'remotion';
import {ACCENT, EASE_IN, EASE_IN_OUT, EASE_OUT, INK, LINE, MUTED, PAPER, SANS, arc, beats, clamp} from '../brand.jsx';
import {Camera, Crop, Shot} from '../stage.jsx';
import {CUES} from '../timeline.mjs';
import rects from '../../public/rects.json';

const LINK = 'https://arxiv.org/abs/1706.03762';
const LIBRARY_BUTTON = [1281, 33];
const {homeUrl: input, homeAdd: button} = rects;
const INPUT_CENTER = [input.x + input.width / 2, input.y + input.height / 2];
const BUTTON_CENTER = [button.x + button.width / 2, button.y + button.height / 2];

// The link types itself on thirty-second notes, the cursor presses Add paper on the downbeat,
// and the paper flies on an arc into the Library button.
export const Add = () => {
  const frame = useCurrentFrame();
  const {typeStart, typeEnd, click} = CUES.Add;
  const typed = Math.floor(interpolate(frame, [beats(typeStart), beats(typeEnd)], [0, LINK.length], clamp));
  const caretX = input.x + input.padding + (typed ? input.prefixes[typed - 1] : 0);
  const pressed = frame >= beats(typeStart);
  const flight = interpolate(frame, [beats(click + 1), beats(click + 2.5)], [0, 1], {...clamp, easing: EASE_IN_OUT});
  const [cardX, cardY] = arc(flight, INPUT_CENTER, LIBRARY_BUTTON, 140);
  const cursor = interpolate(frame, [beats(5.5), beats(7.6)], [0, 1], {...clamp, easing: EASE_IN_OUT});
  const [cursorX, cursorY] = arc(cursor, [1250, 760], [BUTTON_CENTER[0] + 20, BUTTON_CENTER[1] + 10], 40);
  const landed = beats(click + 2.5);
  return (
    <AbsoluteFill style={{background: PAPER}}>
      <Camera easing={EASE_IN_OUT} move={36} keys={[[0, 720, 450, 1], [beats(1.5), 720, 430, 1.4], [beats(click + 0.25), 720, 450, 1]]}>
        <Shot src={pressed ? 'home-filled.png' : 'home.png'} />
        {pressed && <div style={{position: 'absolute', left: caretX, top: input.y + 5, width: input.x + input.width - caretX - 4, height: input.height - 10, background: PAPER}} />}
        {frame < beats(click) && (frame < beats(typeStart) || frame > beats(typeEnd) ? Math.floor(frame / 16) % 2 === 0 : true) &&
          <div style={{position: 'absolute', left: caretX + 1, top: input.y + 13, width: 1.6, height: input.height - 26, background: INK}} />}
        <div style={{position: 'absolute', left: button.x - 3, top: button.y + 1, width: button.width + 6, height: button.height - 2, background: PAPER}} />
        <Crop src="home-filled.png" rect={button} style={{borderRadius: 10,
          scale: interpolate(frame, [beats(click) - 6, beats(click), beats(click) + 12], [1, 0.95, 1], {...clamp, easing: [EASE_IN, Easing.spring({damping: 9})]})}} />
        <div style={{position: 'absolute', left: BUTTON_CENTER[0] - 60, top: BUTTON_CENTER[1] - 60, width: 120, height: 120, borderRadius: '50%',
          border: `3px solid ${ACCENT}`, opacity: interpolate(frame, [beats(click), beats(click) + 36], [0.9, 0], clamp),
          scale: interpolate(frame, [beats(click), beats(click) + 36], [0.3, 1.6], {...clamp, easing: EASE_OUT}), visibility: frame >= beats(click) ? 'visible' : 'hidden'}} />
        <div style={{position: 'absolute', left: LIBRARY_BUTTON[0] - 44, top: LIBRARY_BUTTON[1] - 26, width: 88, height: 52, borderRadius: 14,
          border: `3px solid ${ACCENT}`, opacity: interpolate(frame, [landed, landed + 30], [1, 0], clamp), visibility: frame >= landed ? 'visible' : 'hidden',
          scale: interpolate(frame, [landed, landed + 30], [1, 1.5], {...clamp, easing: EASE_OUT})}} />
        {frame >= beats(click + 0.25) && frame < landed && <PaperCard frame={frame} x={cardX} y={cardY} flight={flight} start={beats(click + 0.25)} />}
        {frame >= beats(5.5) && frame < beats(click + 1) && (
          <svg width="34" height="44" viewBox="0 0 17 22" style={{position: 'absolute', left: cursorX, top: cursorY,
            opacity: interpolate(frame, [beats(5.5), beats(5.5) + 10, beats(click + 0.5), beats(click + 1)], [0, 1, 1, 0], clamp),
            scale: interpolate(frame, [beats(click) - 6, beats(click), beats(click) + 12], [1, 0.94, 1], {...clamp, easing: [EASE_IN, EASE_OUT]})}}>
            <path d="M1 1 L1 17 L5 13 L8 20 L11 19 L8 12 L14 12 Z" fill={INK} stroke={PAPER} strokeWidth="1.4" strokeLinejoin="round" />
          </svg>
        )}
      </Camera>
    </AbsoluteFill>
  );
};

const PaperCard = ({frame, x, y, flight, start}) => (
  <div style={{position: 'absolute', left: x - 130, top: y - 58, width: 260, height: 116, padding: '16px 18px', boxSizing: 'border-box',
    background: PAPER, border: `1.5px solid ${LINE}`, borderRadius: 16, fontFamily: SANS, textAlign: 'left',
    boxShadow: `0 ${20 - 12 * flight}px 40px #1f281733`, display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
    opacity: interpolate(flight, [0.85, 1], [1, 0], clamp),
    rotate: `${interpolate(flight, [0, 0.5, 1], [0, -7, 0], clamp)}deg`,
    scale: String(interpolate(frame, [start, start + 26], [0.6, 1], {...clamp, easing: Easing.spring({damping: 11})}) * interpolate(flight, [0, 1], [1, 0.2], clamp))}}>
    <div style={{fontSize: 17, fontWeight: 650, color: INK}}>Attention Is All You Need</div>
    <div style={{fontSize: 14, color: MUTED}}>1706.03762v7</div>
  </div>
);
