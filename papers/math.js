/* Render retained MathML locally; glyph paths are embedded in each SVG. */
const fs = require('node:fs');
const {mathjax} = require('mathjax-full/js/mathjax.js');
const {MathML} = require('mathjax-full/js/input/mathml.js');
const {SVG} = require('mathjax-full/js/output/svg.js');
const {liteAdaptor} = require('mathjax-full/js/adaptors/liteAdaptor.js');
const {RegisterHTMLHandler} = require('mathjax-full/js/handlers/html.js');
const adaptor = liteAdaptor();
RegisterHTMLHandler(adaptor);
const document = mathjax.document('', {InputJax: new MathML(), OutputJax: new SVG({fontCache: 'none'})});
const formulas = JSON.parse(fs.readFileSync(0, 'utf8'));
const result = formulas.map(({math, display}) => {
  const node = document.convert(math, {display, em: 16, ex: 8, containerWidth: 560});
  const svg = adaptor.firstChild(node);
  const width = parseFloat(adaptor.getAttribute(svg, 'width')) / 2;
  const height = parseFloat(adaptor.getAttribute(svg, 'height')) / 2;
  const style = adaptor.getAttribute(svg, 'style') || '';
  const baseline = parseFloat((style.match(/vertical-align:\s*([-\d.]+)ex/) || [0, 0])[1]) / 2;
  if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) {
    throw new Error('MathJax produced an equation without usable dimensions.');
  }
  adaptor.setAttribute(svg, 'width', `${width * 64}px`);
  adaptor.setAttribute(svg, 'height', `${height * 64}px`);
  return {svg: adaptor.outerHTML(svg), width, height, baseline};
});
process.stdout.write(JSON.stringify(result));
