import {AbsoluteFill, Easing, interpolate, useCurrentFrame} from 'remotion';
import {BEAT, START} from './timeline.mjs';

export const INK = '#272820', MUTED = '#646456', PAPER = '#fffdf7', PAGE = '#f5f1e8', LINE = '#dedbcf', ACCENT = '#3f573d', TINT = '#e9eddf';
export const SANS = "'Avenir Next', Avenir, -apple-system, sans-serif", SERIF = 'Georgia, serif', MONO = 'Menlo, monospace';

// Entrances arrive fast and settle; exits build speed; moves wind up and overshoot a little.
export const EASE_OUT = Easing.bezier(0.16, 1, 0.3, 1);
export const EASE_IN = Easing.bezier(0.7, 0, 0.84, 0);
export const EASE_IN_OUT = Easing.bezier(0.65, 0, 0.35, 1);
export const BACK = Easing.bezier(0.55, -0.25, 0.3, 1.25);
export const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'};
export const beats = n => n * BEAT;

// The app's --glow background. It brightens a little on every kick.
export const Background = () => {
  const frame = useCurrentFrame(), t = frame / 60;
  const drums = frame >= beats(START.Add) && frame < beats(START.Outro + 4);
  const d = Math.sin(t / 5) * 6;
  return (
    <AbsoluteFill style={{background: PAGE}}>
      <AbsoluteFill style={{background: `radial-gradient(ellipse at ${d}% ${12 + d}%, #a9be8970, transparent 43%), radial-gradient(ellipse at ${100 - d}% 75%, #d4b07942, transparent 44%), radial-gradient(ellipse at 78% ${d}%, #9cb7bd3d, transparent 35%)`}} />
      <AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 55%, #ffffff, transparent 60%)',
        opacity: drums ? 0.35 * Math.exp(-(frame % beats(1)) / 8) : 0}} />
    </AbsoluteFill>
  );
};

// The app icon drawn from its SVG parts, so the three sheets can fan out one after another.
export const Icon = ({size, progress}) => {
  const sheet = (delay, angle) => interpolate(progress, [delay, delay + 0.6], [0, angle], {...clamp, easing: Easing.spring({damping: 11})});
  const line = delay => interpolate(progress, [delay, delay + 0.35], [0, 1], {...clamp, easing: EASE_OUT});
  return (
    <svg width={size} height={size} viewBox="0 0 1024 1024" style={{overflow: 'visible'}}>
      <path d="M512 64 C856 64 960 64 960 512 C960 856 960 960 512 960 C168 960 64 960 64 512 C64 168 64 64 512 64Z" fill="#fbf8ef" stroke="#d5cdbf" strokeWidth="5" />
      <g stroke="#9b432b" strokeWidth="24" strokeLinejoin="round">
        <rect x="358" y="204" width="390" height="510" rx="34" fill="#d8b4a2" transform={`translate(${sheet(0.1, -116)} ${sheet(0.1, 60)}) rotate(${sheet(0.1, -12)} 553 459)`} />
        <rect x="358" y="204" width="390" height="510" rx="34" fill="#ecd7c5" transform={`translate(${sheet(0.2, -58)} ${sheet(0.2, 30)}) rotate(${sheet(0.2, -6)} 553 459)`} />
        <rect x="358" y="204" width="390" height="510" rx="34" fill="#fffdf7" />
      </g>
      <g fill="#9b432b">
        {[[290, 208, 32], [382, 270, 20], [438, 270, 20], [494, 196, 20]].map(([y, width, height], i) => (
          <rect key={y} x="418" y={y} width={width * line(0.35 + i * 0.08)} height={height} rx={height / 2} />
        ))}
      </g>
    </svg>
  );
};

// Eyebrow, then the title word by word, 2 frames apart. Layout is 'top', 'left', or 'right'.
export const Caption = ({eyebrow, title, layout, length}) => {
  const frame = useCurrentFrame();
  const leave = interpolate(frame, [length - 14, length], [0, 1], {...clamp, easing: EASE_IN});
  const column = layout !== 'top';
  return (
    <div style={{position: 'absolute', top: column ? 0 : 38, bottom: column ? 0 : undefined, width: column ? 560 : '100%',
      left: layout === 'right' ? undefined : column ? 110 : 0, right: layout === 'right' ? 110 : undefined,
      display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: column ? 'flex-start' : 'center',
      opacity: 1 - leave, translate: `0px ${leave * -24}px`}}>
      <div style={{fontFamily: MONO, fontSize: 24, letterSpacing: 2, color: ACCENT, textTransform: 'uppercase',
        opacity: interpolate(frame, [8, 26], [0, 1], {...clamp, easing: EASE_OUT}),
        translate: interpolate(frame, [8, 26], ['0px 24px', '0px 0px'], {...clamp, easing: EASE_OUT})}}>{eyebrow}</div>
      <div style={{fontFamily: SERIF, fontSize: column ? 72 : 62, lineHeight: 1.12, letterSpacing: -1.8, color: INK, marginTop: 12,
        textAlign: column ? 'left' : 'center', maxWidth: column ? 560 : 1600}}>
        {title.split(' ').map((word, i) => (
          <span key={i} style={{display: 'inline-block', marginRight: '0.26em',
            opacity: interpolate(frame, [16 + i * 2, 36 + i * 2], [0, 1], {...clamp, easing: EASE_OUT}),
            translate: interpolate(frame, [16 + i * 2, 36 + i * 2], ['0px 30px', '0px 0px'], {...clamp, easing: EASE_OUT})}}>{word}</span>
        ))}
      </div>
    </div>
  );
};

// A point along a quadratic arc from a to b that bends up by lift.
export const arc = (p, [ax, ay], [bx, by], lift) => {
  const cx = (ax + bx) / 2, cy = Math.min(ay, by) - lift;
  return [(1 - p) ** 2 * ax + 2 * (1 - p) * p * cx + p ** 2 * bx, (1 - p) ** 2 * ay + 2 * (1 - p) * p * cy + p ** 2 * by];
};
