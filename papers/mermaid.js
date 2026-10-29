/* Render one Mermaid source with Pele and report what the Diagram checks need. */
const fs = require('node:fs');
const {mathjax} = require('mathjax-full/js/mathjax.js');
const {TeX} = require('mathjax-full/js/input/tex.js');
const {SVG} = require('mathjax-full/js/output/svg.js');
const {liteAdaptor} = require('mathjax-full/js/adaptors/liteAdaptor.js');
const {RegisterHTMLHandler} = require('mathjax-full/js/handlers/html.js');
// The page's TeX packages (app/static/math-config.js): none of them can add a link, a style, or fetch code.
for (const name of ['base/BaseConfiguration', 'ams/AmsConfiguration', 'newcommand/NewcommandConfiguration',
                    'noundefined/NoUndefinedConfiguration']) require(`mathjax-full/js/input/tex/${name}.js`);

const adaptor = liteAdaptor();
RegisterHTMLHandler(adaptor);
const tex = mathjax.document('', {InputJax: new TeX({packages: ['base', 'ams', 'newcommand', 'noundefined']}),
                                  OutputJax: new SVG({fontCache: 'none'})});

// A label's $$TeX$$ drawn by MathJax. Broken TeX returns nothing, so Pele shows the source instead.
function math(source, size) {
  try {
    const node = adaptor.firstChild(tex.convert(source, {display: false, em: size, ex: size / 2}));
    if (adaptor.kind(node) !== 'svg') return null;
    const width = parseFloat(adaptor.getAttribute(node, 'width')) * size / 2;
    const height = parseFloat(adaptor.getAttribute(node, 'height')) * size / 2;
    if (!(width > 0 && height > 0)) return null;
    adaptor.setAttribute(node, 'width', width + 'px');
    adaptor.setAttribute(node, 'height', height + 'px');
    // The checks read a label's TeX source from this attribute, since the drawing has no text.
    adaptor.setAttribute(node, 'data-tex', source);
    return {svg: adaptor.outerHTML(node), width, height};
  } catch (_) {
    return null;
  }
}

const decode = text => text.replace(/<[^>]+>/g, '').replace(/&lt;/g, '<').replace(/&gt;/g, '>')
  .replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&amp;/g, '&');
const words = markup => decode(markup.replace(/<\/tspan>/g, ' ')).replace(/\s+/g, ' ').trim();
// Text sizes in units: Pele writes its own as plain numbers, and a diagram's styles may use other units.
const UNITS = {px: 1, pt: 4 / 3, em: 16, rem: 16, '%': 0.16};

(async () => {
  const {parse, render} = await import('pele');
  const {source, width, config} = JSON.parse(fs.readFileSync(0, 'utf8'));
  let result;
  try {
    parse(source);
    const drawn = render(source, {math, config, maxWidth: width, autoDirection: false, links: false, images: false});
    // Each label's TeX, in $$, stands in for its drawing, so the checks read the words a reader sees.
    const plain = drawn.svg.replace(/<svg[^>]*\bdata-tex="([^"]*)"[^>]*>[\s\S]*?<\/svg>/g, (_, tex) => `<text>$$${tex}$$</text>`);
    const sizes = [...plain.matchAll(/font-size(?:="|:\s*)([\d.]+)(px|pt|em|rem|%)?/g)]
      .map(match => parseFloat(match[1]) * UNITS[match[2] || 'px']);
    // A sequence diagram draws each participant twice, at the top and the bottom, with one ID.
    const nodes = new Map();
    for (const match of plain.matchAll(/<g class="pele-node[^"]*" data-id="([^"]+)"[^>]*>([\s\S]*?)<\/g>/g)) {
      if (!nodes.has(match[1])) nodes.set(match[1], {id: match[1], text: words(match[2])});
    }
    result = {
      ok: true, type: drawn.type, width: drawn.width, height: drawn.height,
      svg: drawn.svg.replace(/\sdata-tex="[^"]*"/g, ''),
      labels: [...plain.matchAll(/<text\b[^>]*>([\s\S]*?)<\/text>/g)].map(match => words(match[1])),
      nodes: [...nodes.values()],
      // Pele's base text size is 16 units.
      min_font: Math.min(16, ...sizes),
    };
  } catch (error) {
    result = {ok: false, error: String(error.message || error)};
  }
  process.stdout.write(JSON.stringify(result));
})();
