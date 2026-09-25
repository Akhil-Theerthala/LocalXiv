import {AbsoluteFill, Easing, Img, interpolate, spring, staticFile, useCurrentFrame} from 'remotion';
import rects from '../public/rects.json';

export const FPS = 30;
export const DURATION = 48;

// Screenshots are 1440x900 CSS pixels at 2x. The window shows them 1400 wide.
const WIDTH = 1400, SCALE = WIDTH / 1440, HEIGHT = 900 * SCALE, BAR = 44, TOP = 200;
const WINDOW_IN = 3.4, WINDOW_OUT = 42.5;
const FADE = 0.35;
const INK = '#272820', MUTED = '#646456', PAPER = '#fffdf7', PAGE = '#f5f1e8', ACCENT = '#3f573d';
const SANS = "'Avenir Next', Avenir, -apple-system, sans-serif", SERIF = 'Georgia, serif', MONO = 'Menlo, monospace';

// start and length are seconds. Camera zooms are [scale, focus x, focus y] in screenshot CSS pixels.
// A tall shot scrolls instead: `tall` is its CSS height at 1440 wide, `fit` narrows it inside the window.
const SHOTS = [
  {src: 'home.png', start: 3.4, length: 4.6, zoom: [[1, 720, 420], [1.3, 720, 420]]},
  {src: 'library.png', start: 8, length: 3.5, zoom: [[1, 720, 0], [1.12, 720, 0]]},
  {src: 'paper.png', start: 11.5, length: 2.5, zoom: [[1, 720, 0], [1.05, 720, 0]]},
  {src: 'paper-preferences.png', start: 14, length: 2, zoom: [[1.08, 720, 450], [1.14, 720, 450]]},
  {src: 'paper-large.png', start: 16, length: 2.5, zoom: [[1.05, 720, 0], [1.08, 720, 0]]},
  {src: 'paper-dark.png', start: 18.5, length: 2.5, zoom: [[1.08, 720, 0], [1, 720, 0]]},
  {src: 'overview.png', start: 21, length: 2.5, zoom: [[1, 720, 0], [1.08, 720, 0]]},
  {src: 'attention_figure.png', start: 23.5, length: 7, tall: 2350, fit: 0.82},
  {src: 'blog-full.png', start: 30.5, length: 7, tall: 3852, scroll: 2300},
  {src: 'share.png', start: 37.5, length: 2, zoom: [[1.1, 720, 450], [1.2, 720, 450]]},
  {src: 'share-kindle.png', start: 39.5, length: 3, zoom: [[1.2, 720, 450], [1.25, 720, 520]]},
];

const CAPTIONS = [
  {start: 3.4, eyebrow: 'Add', title: 'Paste an arXiv or alphaXiv link.'},
  {start: 8, eyebrow: 'Library', title: 'The paper joins your library on your Mac.'},
  {start: 11.5, eyebrow: 'Read', title: 'Choose your font, text size, margins, and theme.'},
  {start: 21, eyebrow: 'Overview', title: 'See the core of the paper in one figure.'},
  {start: 30.5, eyebrow: 'Blog', title: 'Read a longer explanation with source citations.'},
  {start: 37.5, eyebrow: 'Kindle', title: 'Export an EPUB, or send it to your Kindle.'},
  {start: WINDOW_OUT},
];

const TYPE_START = 1.0, TYPE_END = 2.4, CLICK = 3.2;
const LINK = 'https://arxiv.org/abs/1706.03762';

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'};
const ease = Easing.bezier(0.22, 1, 0.36, 1);
const smooth = Easing.inOut(Easing.cubic);
const between = (t, a, b, from, to, easing = ease) => interpolate(t, [a, b], [from, to], {...clamp, easing});

export const Intro = () => {
  const frame = useCurrentFrame(), t = frame / FPS;
  return (
    <AbsoluteFill style={{background: PAGE, fontFamily: SANS, color: INK, overflow: 'hidden'}}>
      <Glow t={t} />
      <Title t={t} />
      <Captions t={t} />
      <Window t={t} frame={frame} />
      <Outro t={t} frame={frame} />
    </AbsoluteFill>
  );
};

// The app's --glow background, drifting slowly.
const Glow = ({t}) => {
  const d = Math.sin(t / 6) * 6;
  return <AbsoluteFill style={{background: `radial-gradient(ellipse at ${d}% ${12 + d}%, #a9be8970, transparent 43%), radial-gradient(ellipse at ${100 - d}% 75%, #d4b07942, transparent 44%), radial-gradient(ellipse at 78% ${d}%, #9cb7bd3d, transparent 35%)`}} />;
};

const Title = ({t}) => {
  const frame = t * FPS;
  const pop = spring({frame: frame - 8, fps: FPS, config: {damping: 14, mass: 0.8}});
  const out = between(t, 2.9, 3.5, 1, 0, Easing.in(Easing.cubic));
  if (out === 0) return null;
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', opacity: out, transform: `translateY(${(1 - out) * -60}px)`}}>
      <Img src={staticFile('icon.svg')} style={{width: 150, transform: `scale(${0.6 + pop * 0.4}) rotate(${(1 - pop) * -8}deg)`, opacity: pop}} />
      <div style={{fontSize: 96, fontWeight: 650, letterSpacing: -3, marginTop: 28, opacity: between(t, 0.5, 1.1, 0, 1), transform: `translateY(${between(t, 0.5, 1.1, 24, 0)}px)`}}>LocalXiv</div>
      <div style={{fontFamily: SERIF, fontSize: 40, color: MUTED, marginTop: 10, opacity: between(t, 1.1, 1.8, 0, 1), transform: `translateY(${between(t, 1.1, 1.8, 20, 0)}px)`}}>
        Read arXiv papers comfortably. On your Mac or Kindle.
      </div>
    </AbsoluteFill>
  );
};

const Captions = ({t}) => CAPTIONS.slice(0, -1).map((caption, i) => {
  const end = CAPTIONS[i + 1].start;
  if (t < caption.start || t > end) return null;
  const inside = between(t, caption.start, caption.start + 0.6, 0, 1);
  const leave = between(t, end - 0.3, end, 0, 1, Easing.in(Easing.cubic));
  return (
    <div key={caption.start} style={{position: 'absolute', top: 44, width: '100%', textAlign: 'center', opacity: inside * (1 - leave), transform: `translateY(${(1 - inside) * 22 - leave * 16}px)`}}>
      <div style={{fontFamily: MONO, fontSize: 18, color: MUTED, letterSpacing: 1}}>{caption.eyebrow}</div>
      <div style={{fontFamily: SERIF, fontSize: 58, letterSpacing: -1.6, marginTop: 8}}>{caption.title}</div>
    </div>
  );
});

const Window = ({t, frame}) => {
  const rise = spring({frame: frame - WINDOW_IN * FPS, fps: FPS, config: {damping: 20, mass: 1.1}});
  const drop = between(t, WINDOW_OUT, WINDOW_OUT + 0.7, 0, 1, Easing.in(Easing.cubic));
  if (rise <= 0.001 || drop === 1) return null;
  return (
    <div style={{position: 'absolute', left: (1920 - WIDTH) / 2, top: TOP + (1 - rise) * 900 + drop * 140, opacity: 1 - drop,
      width: WIDTH, height: HEIGHT + BAR, borderRadius: 18, overflow: 'hidden', background: PAPER,
      boxShadow: '0 30px 90px #20281738, 0 0 0 1px #dedbcf'}}>
      <div style={{height: BAR, display: 'flex', alignItems: 'center', gap: 9, paddingLeft: 18, background: '#f3efe6', borderBottom: '1px solid #dedbcf'}}>
        {['#ec6a5e', '#f4bf4f', '#61c554'].map(color => <div key={color} style={{width: 13, height: 13, borderRadius: 7, background: color}} />)}
        <div style={{flex: 1, textAlign: 'center', marginRight: 80, fontSize: 15, fontWeight: 600, color: MUTED}}>LocalXiv</div>
      </div>
      <div style={{position: 'relative', height: HEIGHT, overflow: 'hidden'}}>
        {SHOTS.map((shot, i) => <Shot key={shot.src} shot={shot} t={t} first={i === 0} />)}
      </div>
    </div>
  );
};

const Shot = ({shot, t, first}) => {
  const end = shot.start + shot.length;
  // The last shot stays until the window leaves.
  if (t < shot.start || (t > end + FADE && shot !== SHOTS.at(-1))) return null;
  const opacity = first ? 1 : between(t, shot.start, shot.start + FADE, 0, 1, smooth);
  const progress = between(t, shot.start, end + FADE, 0, 1, smooth);
  if (shot.tall) {
    const width = WIDTH * (shot.fit || 1), height = shot.tall * SCALE * (shot.fit || 1);
    const scroll = Math.min(shot.scroll || Infinity, height - HEIGHT) * between(t, shot.start + 0.8, end, 0, 1, smooth);
    return (
      <AbsoluteFill style={{opacity, background: PAPER}}>
        <Img src={staticFile(shot.src)} style={{position: 'absolute', width, left: (WIDTH - width) / 2, top: -scroll}} />
      </AbsoluteFill>
    );
  }
  const [[s0, x0, y0], [s1, x1, y1]] = shot.zoom;
  const lerp = (a, b) => a + (b - a) * progress;
  return (
    <AbsoluteFill style={{opacity, transformOrigin: `${lerp(x0, x1) * SCALE}px ${lerp(y0, y1) * SCALE}px`, transform: `scale(${lerp(s0, s1)})`}}>
      <Img src={staticFile(t < shot.start + TYPE_START || !first ? shot.src : 'home-filled.png')} style={{width: WIDTH}} />
      {first && <Typing t={t - shot.start} />}
    </AbsoluteFill>
  );
};

// Reveals the link in the real filled input one character at a time, then presses Add paper.
const Typing = ({t}) => {
  const {homeUrl: input, homeAdd: button} = rects;
  const typed = Math.floor(between(t, TYPE_START, TYPE_END, 0, LINK.length, Easing.linear));
  const x = input.x + input.padding + (typed ? input.prefixes[typed - 1] : 0);
  const caretOn = (t >= TYPE_START && t < TYPE_END) || Math.floor(t * 2.5) % 2 === 0;
  const press = between(t, CLICK, CLICK + 0.12, 0, 1) * between(t, CLICK + 0.2, CLICK + 0.5, 1, 0);
  const ripple = between(t, CLICK, CLICK + 0.7, 0, 1);
  const box = (left, top, width, height) => ({position: 'absolute', left: left * SCALE, top: top * SCALE, width: width * SCALE, height: height * SCALE});
  return (
    <>
      {t >= TYPE_START && <div style={{...box(x, input.y + 5, input.x + input.width - x - 4, input.height - 10), background: PAPER}} />}
      {caretOn && t < CLICK && <div style={{...box(x + 1, input.y + 13, 1.6, input.height - 26), background: INK}} />}
      <div style={{...box(button.x, button.y + 4, button.width, button.height - 8), borderRadius: 10, background: `rgba(0,0,0,${press * 0.25})`, transform: `scale(${1 - press * 0.04})`}} />
      {ripple > 0 && ripple < 1 && <div style={{...box(button.x + button.width / 2 - 60, button.y + button.height / 2 - 60, 120, 120), borderRadius: '50%', border: `3px solid ${ACCENT}`, opacity: 1 - ripple, transform: `scale(${0.3 + ripple})`}} />}
    </>
  );
};

const Outro = ({t, frame}) => {
  const start = WINDOW_OUT + 0.5;
  if (t < start) return null;
  const pop = spring({frame: frame - start * FPS, fps: FPS, config: {damping: 14, mass: 0.8}});
  const line = (at, style, text) => (
    <div style={{opacity: between(t, start + at, start + at + 0.6, 0, 1), transform: `translateY(${between(t, start + at, start + at + 0.6, 18, 0)}px)`, ...style}}>{text}</div>
  );
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', textAlign: 'center'}}>
      <Img src={staticFile('icon.svg')} style={{width: 120, opacity: pop, transform: `scale(${0.6 + pop * 0.4})`}} />
      {line(0.3, {fontSize: 80, fontWeight: 650, letterSpacing: -2.5, marginTop: 20}, 'LocalXiv')}
      {line(0.6, {fontFamily: SERIF, fontSize: 38, color: MUTED, marginTop: 6}, 'Free and open source. No AI account needed to read.')}
      {line(1.0, {fontSize: 24, color: MUTED, marginTop: 34}, 'Optional AI features use your own provider and API key.')}
      {line(1.4, {fontFamily: MONO, fontSize: 24, color: ACCENT, marginTop: 34, padding: '12px 22px', border: `1.5px solid ${ACCENT}`, borderRadius: 999}, 'github.com/Akhil-Theerthala/LocalXiv')}
      {line(1.7, {fontSize: 18, color: MUTED, marginTop: 18}, 'Early preview · Apple Silicon · macOS 26 or newer')}
    </AbsoluteFill>
  );
};
