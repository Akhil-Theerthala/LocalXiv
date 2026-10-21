// Reading preferences to values. No DOM: the page root and the reader iframe apply what this returns,
// and app.css :root is the one place a colour is written.
export const DEFAULTS = Object.freeze({theme: 'system', font: 'new-york', size: 18, margins: 'normal', spacing: 'normal'});
export const THEMES = {light: 'Light', sepia: 'Sepia', dark: 'Dark', system: 'Match System'};
// "New York" is reached only through ui-serif; the family name never appears in a stack.
export const FONTS = {
  'new-york': {name: 'New York', stack: 'ui-serif, Georgia, serif'},
  charter: {name: 'Charter', stack: 'Charter, "Bitstream Charter", ui-serif, serif'},
  iowan: {name: 'Iowan Old Style', stack: '"Iowan Old Style", ui-serif, serif'},
  palatino: {name: 'Palatino', stack: 'Palatino, "Palatino Linotype", ui-serif, serif'},
  'sf-pro': {name: 'SF Pro', stack: '-apple-system, system-ui, sans-serif'},
};
// Margins name the space beside the text, so Narrow margins give the longest lines.
export const MARGINS = {narrow: ['Narrow', '40em'], normal: ['Normal', '34em'], wide: ['Wide', '28em']};
export const SPACINGS = {compact: ['Compact', 1.4], normal: ['Normal', 1.55], relaxed: ['Relaxed', 1.7]};
export const SIZES = [15, 36];
export const STORAGE_KEY = 'localxiv-reading';

export function normalize(prefs) {
  const size = Math.round(Number(prefs?.size));
  return {
    theme: prefs?.theme in THEMES ? prefs.theme : DEFAULTS.theme,
    font: prefs?.font in FONTS ? prefs.font : DEFAULTS.font,
    size: size >= SIZES[0] && size <= SIZES[1] ? size : DEFAULTS.size,
    margins: prefs?.margins in MARGINS ? prefs.margins : DEFAULTS.margins,
    spacing: prefs?.spacing in SPACINGS ? prefs.spacing : DEFAULTS.spacing,
  };
}

const FIELDS = ['theme', 'font', 'size', 'margins', 'spacing'];
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
export const measure = ({size, margins}) => parseFloat(MARGINS[margins][1]) * size;
// Figures, tables, and display equations may run to 1.5 times the Normal measure. Margins set only the text.
export const wideMeasure = ({size}) => measure({size, margins: 'normal'}) * 1.5;

export function rootProperties(prefs) {
  const {font, size, spacing} = prefs;
  return {'--reading-font': FONTS[font].stack, '--reading-size': size + 'px', '--measure': measure(prefs) + 'px', '--wide': wideMeasure(prefs) + 'px', '--reading-leading': String(SPACINGS[spacing][1])};
}

// The paper iframe has no access to the page's stylesheet, so it gets the resolved values. Text keeps
// the measure; figures, tables, and display equations may run to the wide measure.
export function readerStylesheet({theme, prefs, tokens, split}) {
  const {stack} = FONTS[prefs.font], leading = SPACINGS[prefs.spacing][1], text = measure(prefs), wide = wideMeasure(prefs);
  const blocks = 'figure,table,pre,.display-math,math[display=block]';
  return `html{color-scheme:${theme === 'dark' ? 'dark' : 'light'}!important;height:auto!important;background:${tokens.paper}!important;color:${tokens.ink}!important}`
    // In Split view the frame scrolls by itself, so a scroll past its end does not move the page.
    + (split ? 'html{overscroll-behavior:contain}' : '')
    + `body{font-family:${stack}!important;font-size:${prefs.size}px!important;line-height:${leading}!important;max-width:${wide}px!important;margin:0 auto!important;padding:8px 0 24px!important;height:auto!important;min-height:0!important;background:inherit!important;color:inherit!important;hyphens:auto;-webkit-hyphens:auto}`
    + `:is(body,section,aside,div:not(.minipage))>:not(section,div,${blocks}){max-width:${text}px!important;margin-left:auto!important;margin-right:auto!important}`
    + `p,li,blockquote{text-wrap:pretty}p{margin-top:0!important;margin-bottom:.85em!important}:is(ul,ol){margin-bottom:.85em!important}li>:is(ul,ol){margin-bottom:0!important}h1,h2,h3,h4,h5,h6{font-family:-apple-system,system-ui,sans-serif!important;line-height:1.25!important;font-weight:600!important;margin-bottom:.55em!important;text-wrap:balance;hyphens:manual;color:${tokens.label}!important}h1{font-size:1.25em!important}h2{font-size:1.17em!important}h3{font-size:1.05em!important}h4,h5,h6{font-size:1em!important}`
    + `.header-section-number{color:${tokens.label2};font-weight:500;margin-right:.4em;font-variant-numeric:tabular-nums}`
    // Green alone is under 3:1 against the ink in Dark and Sepia, so a link also has a faint underline.
    + `a{color:${tokens.accent}!important;text-decoration:underline!important;text-decoration-thickness:1px!important;text-decoration-color:color-mix(in srgb,currentColor 35%,transparent)!important;text-underline-offset:.18em}a:is(:hover,.is-open){text-decoration-color:currentColor!important}`
    + `:is(sup,sub,a.footnote-ref){line-height:0}a.footnote-ref{font-size:.75em}img,svg{max-width:100%;height:auto;object-fit:contain}`
    + `figure{margin:1.6em auto!important;text-align:center}`
    + `figure img{max-height:${tokens.figureMaxHeight}px!important;width:auto!important;cursor:zoom-in;box-sizing:border-box;background:${tokens.figureCard};border-radius:10px;padding:${theme === 'light' ? 0 : 12}px${theme === 'dark' ? ';filter:brightness(.88)' : ''}}`
    // A caption grows with the text size, 13 px at 18 px. A one-line caption stays centred under its figure.
    + `figcaption{font:.72em/1.45 -apple-system,system-ui,sans-serif!important;color:${tokens.label2}!important;margin:10px auto 0!important;max-width:${text}px;width:fit-content;text-align:start;text-wrap:pretty}table>caption{font-family:-apple-system,system-ui,sans-serif;color:${tokens.label2};text-align:start}`
    // `block math` keeps MathML layout, which centres a display equation; a wide one scrolls in its own box.
    // The paragraph around an equation keeps the measure, so the equation's own margins widen it, never past the frame.
    + `math[display=block]{display:block;display:block math;overflow-x:auto;overflow-y:hidden;margin-inline:calc((100% - min(${wide}px, 100vw - 40px)) / 2);padding:6px 0}.display-math{overflow-x:auto}`
    + `table{display:block;overflow:auto;width:fit-content;max-width:100%;margin-left:auto;margin-right:auto;font-size:.85em;font-variant-numeric:tabular-nums}pre{overflow:auto;white-space:pre-wrap}:is(code,pre,kbd,samp){font-family:ui-monospace,Menlo,monospace!important}`
    // The measure rule removes a quote's own margin, so its indent is padding inside the measure.
    + `blockquote{box-sizing:border-box;padding-left:1.7em;hanging-punctuation:first last}`
    + `.lx-flash{border-radius:4px;animation:lx-flash 1.6s ease-out forwards}`
    // The words of a Highlight get a tint of its colour, and those of an open question also a dashed line. WebKit paints
    // no highlight inside MathML, so a formula in the words gets a class.
    + Object.entries(tokens.marks).map(([name, {tint}]) => `::highlight(lx-${name}){background-color:${tint}}math.lx-h-${name}{background:${tint}}`).join('')
    + `::highlight(lx-open){text-decoration:underline dashed ${tokens.marks.question.colour}}math.lx-h-open{border-bottom:1.5px dashed ${tokens.marks.question.colour}}`
    + `@keyframes lx-flash{from,25%{background:${tokens.accentTint};box-shadow:0 0 0 4px ${tokens.accentTint}}to{background:transparent;box-shadow:0 0 0 4px transparent}}`
    + `body>:first-child,body>section:first-child>:first-child{margin-top:0!important}`
    // A frame narrower than the measure, as in the Split view pane, keeps a margin.
    + `@media (max-width:${text + 40}px){body{padding-left:20px!important;padding-right:20px!important}}`;
}
