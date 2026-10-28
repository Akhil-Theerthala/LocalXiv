/* Render one Mermaid source with Pele and report what the Diagram checks need. */
const fs = require('node:fs');
const {mathjax} = require('mathjax-full/js/mathjax.js');
const {TeX} = require('mathjax-full/js/input/tex.js');
const {SVG} = require('mathjax-full/js/output/svg.js');
const {liteAdaptor} = require('mathjax-full/js/adaptors/liteAdaptor.js');
const {RegisterHTMLHandler} = require('mathjax-full/js/handlers/html.js');
const {AllPackages} = require('mathjax-full/js/input/tex/AllPackages.js');

const adaptor = liteAdaptor();
RegisterHTMLHandler(adaptor);
const tex = mathjax.document('', {InputJax: new TeX({packages: AllPackages}), OutputJax: new SVG({fontCache: 'none'})});

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
    return {svg: adaptor.outerHTML(node), width, height};
  } catch (_) {
    return null;
  }
}

const decode = text => text.replace(/<[^>]+>/g, '').replace(/&lt;/g, '<').replace(/&gt;/g, '>')
  .replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&amp;/g, '&');
const words = markup => decode(markup.replace(/<\/tspan>/g, ' ')).replace(/\s+/g, ' ').trim();

(async () => {
  const {parse, render} = await import('pele');
  const {source, width, config} = JSON.parse(fs.readFileSync(0, 'utf8'));
  let result;
  try {
    parse(source);
    const drawn = render(source, {math, config, maxWidth: width, autoDirection: false, links: false, images: false});
    const sizes = [...drawn.svg.matchAll(/font-size(?::\s*|=")([\d.]+)px/g)].map(match => parseFloat(match[1]));
    result = {
      ok: true, type: drawn.type, width: drawn.width, height: drawn.height, svg: drawn.svg,
      // The words a reader sees, and each node with its Mermaid ID.
      labels: [...drawn.svg.matchAll(/<text\b[^>]*>([\s\S]*?)<\/text>/g)].map(match => words(match[1])),
      nodes: [...drawn.svg.matchAll(/<g class="pele-node[^"]*" data-id="([^"]+)"[^>]*>([\s\S]*?)<\/g>/g)]
        .map(match => ({id: match[1], text: words(match[2])})),
      // Pele's base text size is 16 units; a diagram's own styles can only add sizes.
      min_font: Math.min(16, ...sizes),
    };
  } catch (error) {
    result = {ok: false, error: String(error.message || error)};
  }
  process.stdout.write(JSON.stringify(result));
})();
