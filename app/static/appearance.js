// Reading preferences to values. No DOM: the page root and the reader iframe apply what this returns,
// and app.css :root is the one place a colour is written.
export const DEFAULTS = Object.freeze({theme: 'system', font: 'new-york', size: 18, width: 'medium', spacing: 'normal'});
export const THEMES = {light: 'Light', sepia: 'Sepia', dark: 'Dark', system: 'Match System'};
// "New York" is reached only through ui-serif; the family name never appears in a stack.
export const FONTS = {
  'new-york': {name: 'New York', stack: 'ui-serif, Georgia, serif'},
  charter: {name: 'Charter', stack: 'Charter, "Bitstream Charter", ui-serif, serif'},
  iowan: {name: 'Iowan Old Style', stack: '"Iowan Old Style", ui-serif, serif'},
  palatino: {name: 'Palatino', stack: 'Palatino, "Palatino Linotype", ui-serif, serif'},
  'sf-pro': {name: 'SF Pro', stack: '-apple-system, system-ui, sans-serif'},
};
export const WIDTHS = {short: ['Short', '28em'], medium: ['Medium', '34em'], long: ['Long', '40em']};
export const SPACINGS = {compact: ['Compact', 1.4], normal: ['Normal', 1.55], relaxed: ['Relaxed', 1.7]};
export const SIZES = [15, 26];
export const STORAGE_KEY = 'localxiv-reading';

export function normalize(prefs) {
  const size = Math.round(Number(prefs?.size));
  return {
    theme: prefs?.theme in THEMES ? prefs.theme : DEFAULTS.theme,
    font: prefs?.font in FONTS ? prefs.font : DEFAULTS.font,
    size: size >= SIZES[0] && size <= SIZES[1] ? size : DEFAULTS.size,
    width: prefs?.width in WIDTHS ? prefs.width : DEFAULTS.width,
    spacing: prefs?.spacing in SPACINGS ? prefs.spacing : DEFAULTS.spacing,
  };
}

const FIELDS = ['theme', 'font', 'size', 'width', 'spacing'];
export const fromSettings = settings => normalize(Object.fromEntries(FIELDS.map(field => [field, settings?.['reading_' + field]])));
export const toSettings = patch => Object.fromEntries(Object.entries(patch).filter(([field]) => FIELDS.includes(field)).map(([field, value]) => ['reading_' + field, value]));

// The copy only gives the first paint the right theme; the server settings stay the source.
export function readCopy(storage) {
  try { return normalize(JSON.parse(storage.getItem(STORAGE_KEY))); } catch { return {...DEFAULTS}; }
}
export function writeCopy(storage, prefs) {
  try { storage.setItem(STORAGE_KEY, JSON.stringify(prefs)); } catch {}
}

export const resolveTheme = (theme, systemDark) => theme === 'system' ? (systemDark ? 'dark' : 'light') : theme;

// The measure is set in em of the reading size, so a size change keeps the line length.
export const measure = ({size, width}) => parseFloat(WIDTHS[width][1]) * size;

export function rootProperties({font, size, width, spacing}) {
  return {'--reading-font': FONTS[font].stack, '--reading-size': size + 'px', '--measure': measure({size, width}) + 'px', '--reading-leading': String(SPACINGS[spacing][1])};
}

// The paper iframe has no access to the page's stylesheet, so it gets the resolved values. Text keeps
// the measure; figures, tables, and display equations may run to 1.5 times it.
export function readerStylesheet({theme, prefs, tokens}) {
  const {stack} = FONTS[prefs.font], leading = SPACINGS[prefs.spacing][1], text = measure(prefs);
  const wide = 'figure,table,pre,.display-math,math[display=block]';
  return `html{color-scheme:${theme === 'dark' ? 'dark' : 'light'};height:auto!important;background:${tokens.paper}!important;color:${tokens.ink}!important}`
    + `body{font-family:${stack}!important;font-size:${prefs.size}px!important;line-height:${leading}!important;max-width:${text * 1.5}px!important;margin:0 auto!important;padding:8px 0 24px!important;height:auto!important;min-height:0!important;background:inherit!important;color:inherit!important;hyphens:auto;-webkit-hyphens:auto}`
    + `:is(body,section,aside,div:not(.minipage))>:not(section,div,${wide}){max-width:${text}px!important;margin-left:auto!important;margin-right:auto!important}`
    + `p{text-wrap:pretty;margin-top:0!important;margin-bottom:.85em!important}h1,h2,h3,h4{font-family:-apple-system,system-ui,sans-serif!important;line-height:1.25!important;font-weight:600!important;text-wrap:balance;hyphens:manual;color:${tokens.label}!important}h1{font-size:1.25em!important}h2{font-size:1.17em!important}h3{font-size:1.05em!important}h4{font-size:1em!important}`
    + `.header-section-number{color:${tokens.label2};font-weight:500;margin-right:.4em;font-variant-numeric:tabular-nums}`
    + `a{color:${tokens.accent}!important;text-decoration:none!important}img,svg{max-width:100%;height:auto;object-fit:contain}`
    + `figure{margin:1.6em auto!important;text-align:center}`
    + `figure img{max-height:${tokens.figureMaxHeight}px!important;width:auto!important;cursor:zoom-in;box-sizing:border-box;background:#fff;border-radius:10px;padding:${theme === 'light' ? 0 : 12}px}`
    + `figcaption{font:13px/1.45 -apple-system,system-ui,sans-serif!important;color:${tokens.label2}!important;margin:10px auto 0!important;max-width:${text}px;text-wrap:balance}`
    // `block math` keeps MathML layout, which centres a display equation; a wide one scrolls in its own box.
    // The paragraph around an equation keeps the measure, so the equation's own margins widen it, never past the frame.
    + `math[display=block]{display:block;display:block math;overflow-x:auto;overflow-y:hidden;margin-inline:calc((100% - min(${text * 1.5}px, 100vw - 40px)) / 2);padding:6px 0}.display-math{overflow-x:auto}`
    + `table{display:block;overflow:auto;width:fit-content;max-width:100%;margin-left:auto;margin-right:auto;font-size:.85em;font-variant-numeric:tabular-nums}pre{overflow:auto;white-space:pre-wrap}`
    + `.lx-flash{background:${tokens.accentTint};border-radius:4px;box-shadow:0 0 0 4px ${tokens.accentTint};transition:background-color 1.4s ease,box-shadow 1.4s ease}`
    + `body>:first-child,body>section:first-child>:first-child{margin-top:0!important}`
    // A frame narrower than the measure, as in the Split view pane, keeps a margin.
    + `@media (max-width:${text + 40}px){body{padding-left:20px!important;padding-right:20px!important}}`;
}
