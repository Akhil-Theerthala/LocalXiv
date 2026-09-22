// Reading preferences to values. No DOM: the page root and the reader iframe apply what this returns,
// and app.css :root is the one place a colour is written.
export const READING_SIZES = ['14', '16', '18', '20', '22'];
export const THEMES = ['system', 'light', 'dark'];
export const READING_FONTS = {georgia: 'Georgia,serif', charter: 'Charter,Georgia,serif', palatino: 'Palatino,"Palatino Linotype",serif', system: '-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif'};
export const READING_WIDTHS = {wide: '560px', balanced: '720px', narrow: '880px'};
export const MOBILE_GUTTERS = {wide: '34px', balanced: '24px', narrow: '16px'};

const pick = (value, allowed, fallback) => allowed.includes(value) ? value : fallback;

export function readPreferences(storage) {
  return {
    size: pick(storage.getItem('papers-text-size'), READING_SIZES, '16'),
    theme: pick(storage.getItem('papers-theme'), THEMES, 'system'),
    font: pick(storage.getItem('papers-font'), Object.keys(READING_FONTS), 'palatino'),
    margin: pick(storage.getItem('papers-margin'), Object.keys(READING_WIDTHS), 'narrow'),
  };
}

export function resolveTheme(preference, systemDark) {
  return preference === 'system' ? (systemDark ? 'dark' : 'light') : preference;
}

export function rootProperties({size, font, margin}) {
  return {'--reading-size': size + 'px', '--reading-font': READING_FONTS[font], '--reading-width': READING_WIDTHS[margin], '--mobile-reading-gutter': MOBILE_GUTTERS[margin]};
}

export function readerStylesheet({theme, size, fontStack, canvas, ink, paper, accent, line, figureMaxHeight}) {
  return `html{font-size:${size}px!important;color-scheme:${theme};height:auto!important;background:${canvas}!important;color:${ink}!important}`
    + `body{font:inherit!important;font-family:${fontStack}!important;font-size:${size}px!important;line-height:1.85!important;max-width:none!important;margin:0!important;padding:12px 0 25px!important;height:auto!important;min-height:0!important;background:inherit!important;color:inherit!important}`
    + `h1,h2,h3,h4{font-family:'Avenir Next',sans-serif!important;line-height:1.35!important;font-weight:600!important}h1{font-size:1.5em!important}h2{font-size:1.3em!important}`
    + `a{color:${accent}!important}img,svg{max-width:100%;height:auto;object-fit:contain}`
    + `figure img{max-height:${figureMaxHeight}px!important;width:100%!important;cursor:zoom-in;background:${paper};border-radius:10px}`
    + `figcaption{font:12px/1.65 'Avenir Next',sans-serif!important;margin:12px 0!important}`
    + `math[display=block]{display:block;overflow-x:auto;max-width:100%;padding:10px 0}table{display:block;overflow:auto;max-width:100%;font-size:.85em}pre{overflow:auto;white-space:pre-wrap}`
    + `p{margin:0 0 1.2em!important}body>:first-child{margin-top:0!important}`
    + `*{scrollbar-width:thin;scrollbar-color:${line} transparent}::-webkit-scrollbar{width:5px;height:5px}::-webkit-scrollbar-thumb{background:${line};border-radius:8px}`;
}
