import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {BACK, EASE_IN, EASE_OUT, LINE, MUTED, PAPER, beats, clamp} from './brand.jsx';
import {START} from './timeline.mjs';

// Window content is the screenshots' own 1440x900 CSS pixel space.
export const CONTENT = {width: 1440, height: 900};
export const BAR = 40;

// Where the window sits for each scene: center, scale, and tilt toward the caption.
export const LAYOUTS = {
  Enter: {x: 960, y: 1560, scale: 0.86, tiltX: 34, tiltY: 0},
  Add: {x: 960, y: 632, scale: 0.86, tiltX: 0, tiltY: 0},
  Library: {x: 960, y: 632, scale: 0.86, tiltX: 0, tiltY: 0},
  Read: {x: 1225, y: 560, scale: 0.7, tiltX: 0, tiltY: -12},
  Overview: {x: 960, y: 736, scale: 1.2, tiltX: 0, tiltY: 0},
  Blog: {x: 695, y: 560, scale: 0.7, tiltX: 0, tiltY: 12},
  Kindle: {x: 690, y: 626, scale: 0.66, tiltX: 0, tiltY: 0},
};
const ORDER = ['Add', 'Library', 'Read', 'Overview', 'Blog', 'Kindle'];
const MOVE = 42;
export const EXIT = 36;

// The pose at an absolute frame: fly in, move between layouts on each scene's first beat, fly out.
const pose = frame => {
  const enter = interpolate(frame, [beats(START.Add), beats(START.Add) + 54], [0, 1], {...clamp, easing: EASE_OUT});
  let current = mix(LAYOUTS.Enter, LAYOUTS.Add, enter);
  for (const [i, id] of ORDER.entries()) {
    if (i === 0) continue;
    const p = interpolate(frame, [beats(START[id]), beats(START[id]) + MOVE], [0, 1], {...clamp, easing: BACK});
    if (p > 0) current = mix(LAYOUTS[ORDER[i - 1]], LAYOUTS[id], p);
  }
  const leave = interpolate(frame, [beats(START.Outro), beats(START.Outro) + EXIT], [0, 1], {...clamp, easing: EASE_IN});
  return {...current, scale: current.scale * (1 - 0.35 * leave), y: current.y - 180 * leave, tiltX: current.tiltX - 18 * leave, opacity: 1 - leave};
};
const mix = (a, b, p) => Object.fromEntries(Object.keys(a).map(key => [key, a[key] + (b[key] - a[key]) * p]));

// Maps a point in window content to the 1920x1080 stage for an untilted layout.
export const toStage = (layout, [x, y]) => {
  const {x: cx, y: cy, scale} = LAYOUTS[layout];
  return [cx + (x - CONTENT.width / 2) * scale, cy + (y + BAR - (CONTENT.height + BAR) / 2) * scale];
};

export const Window = ({children}) => {
  const frame = useCurrentFrame();
  const {x, y, scale, tiltX, tiltY, opacity} = pose(frame);
  if (opacity <= 0) return null;
  return (
    <AbsoluteFill style={{perspective: 2400}}>
      <div style={{position: 'absolute', left: x - CONTENT.width / 2, top: y - (CONTENT.height + BAR) / 2,
        width: CONTENT.width, height: CONTENT.height + BAR, borderRadius: 20, overflow: 'hidden', background: PAPER, opacity,
        transform: `scale(${scale}) rotateX(${tiltX}deg) rotateY(${tiltY}deg)`,
        boxShadow: '0 50px 120px #1f28172e, 0 12px 30px #1f281714, 0 0 0 1px #d5d0c2'}}>
        <div style={{height: BAR, display: 'flex', alignItems: 'center', gap: 9, paddingLeft: 18, background: '#f3efe6', borderBottom: `1px solid ${LINE}`}}>
          {['#ec6a5e', '#f4bf4f', '#61c554'].map(color => <div key={color} style={{width: 13, height: 13, borderRadius: 7, background: color}} />)}
          <div style={{flex: 1, textAlign: 'center', marginRight: 80, fontSize: 15, fontWeight: 600, color: MUTED}}>LocalXiv</div>
        </div>
        <div style={{position: 'relative', width: CONTENT.width, height: CONTENT.height, overflow: 'hidden'}}>{children}</div>
      </div>
    </AbsoluteFill>
  );
};

// A camera over window content. Keys are [frame, focus x, focus y, zoom]; each move eases out from its key frame.
export const Camera = ({keys, children, easing = EASE_OUT, move = 30}) => {
  const frame = useCurrentFrame();
  let [, x, y, zoom] = keys[0];
  for (let i = 1; i < keys.length; i++) {
    const [start, nx, ny, nz] = keys[i];
    const p = interpolate(frame, [start, start + move], [0, 1], {...clamp, easing});
    if (p > 0) [x, y, zoom] = [x + (nx - x) * p, y + (ny - y) * p, zoom * (nz / zoom) ** p];
  }
  return (
    <AbsoluteFill style={{transformOrigin: '0 0', translate: `${CONTENT.width / 2 - x * zoom}px ${CONTENT.height / 2 - y * zoom}px`, scale: String(zoom)}}>
      {children}
    </AbsoluteFill>
  );
};

export const Shot = ({src, style}) => <Img src={staticFile(src)} style={{position: 'absolute', left: 0, top: 0, width: CONTENT.width, ...style}} />;

// One region of a screenshot as its own layer, so a button or dialog can move by itself.
export const Crop = ({src, rect: {x, y, width, height}, style}) => (
  <div style={{position: 'absolute', left: x, top: y, width, height, overflow: 'hidden', ...style}}>
    <Img src={staticFile(src)} style={{position: 'absolute', left: -x, top: -y, width: CONTENT.width}} />
  </div>
);
