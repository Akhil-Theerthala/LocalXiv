/* Convert isolated TeX expressions to MathML; unknown commands must fail. */
const fs = require('node:fs');
const {mathjax} = require('mathjax-full/js/mathjax.js');
const {TeX} = require('mathjax-full/js/input/tex.js');
const {SVG} = require('mathjax-full/js/output/svg.js');
const {AllPackages} = require('mathjax-full/js/input/tex/AllPackages.js');
const {liteAdaptor} = require('mathjax-full/js/adaptors/liteAdaptor.js');
const {RegisterHTMLHandler} = require('mathjax-full/js/handlers/html.js');
const {SerializedMmlVisitor} = require('mathjax-full/js/core/MmlTree/SerializedMmlVisitor.js');
RegisterHTMLHandler(liteAdaptor());
require('mathjax-full/js/input/tex/physics/PhysicsConfiguration.js');
const packages = AllPackages.filter(name => !['noerrors', 'noundefined', 'require', 'autoload'].includes(name));
const macros = {
  hfill: '', // Page-width glue has no width in a reflowable isolated equation.
  protect: '', // TeX expansion control has no effect in an isolated expression.
  // MathJax has no small-caps math variant; text preserves source spacing.
  textsc: ['\\text{#1}', 1],
  textsuperscript: ['^{\\text{#1}}', 1],
  textsubscript: ['_{\\text{#1}}', 1],
  Bar: ['\\overline{#1}', 1],
  bm: ['\\boldsymbol{#1}', 1],
  // LaTeX and package commands that MathJax lacks. A paper's own definition replaces any of them.
  ensuremath: ['#1', 1],
  emph: ['\\textit{#1}', 1],
  bold: ['\\mathbf{#1}', 1],
  mathds: ['\\mathbb{#1}', 1],
  mathbbm: ['\\mathbb{#1}', 1],
  mathbbmss: ['\\mathbb{#1}', 1],
  mathbold: ['\\boldsymbol{#1}', 1],
  // amsmath's capital accents, for accents on accented symbols.
  Hat: ['\\hat{#1}', 1],
  Check: ['\\check{#1}', 1],
  Tilde: ['\\tilde{#1}', 1],
  Acute: ['\\acute{#1}', 1],
  Grave: ['\\grave{#1}', 1],
  Dot: ['\\dot{#1}', 1],
  Ddot: ['\\ddot{#1}', 1],
  Breve: ['\\breve{#1}', 1],
  Vec: ['\\vec{#1}', 1],
  joinrel: '',
  unskip: '',
  uline: ['\\underline{#1}', 1],
  uuline: ['\\underline{\\underline{#1}}', 1],
  widebar: ['\\overline{#1}', 1],
  varoint: '\\oint',
  mathlarger: ['#1', 1],
  mathsmaller: ['#1', 1],
  qed: '\\square',
  AA: '\u00c5',
  l: '\u0142',
  '-': '',
  normalcolor: '',
  setlength: ['', 2],
  addtocounter: ['', 2],
};

const request = JSON.parse(fs.readFileSync(0, 'utf8'));
const paperPackages = [...packages, ...request.packages];
const paperMacros = {...macros, ...request.macros};
const results = request.formulas.map(({tex, display}) => {
  try {
    const input = new TeX({packages: paperPackages, macros: paperMacros, formatError: (_, error) => {throw error;}});
    const doc = mathjax.document('', {InputJax: input, OutputJax: new SVG({fontCache: 'none'})});
    const node = doc.convert(tex, {display: Boolean(display), end: 20});
    const mathml = new SerializedMmlVisitor().visitTree(node);
    if (mathml.includes('<merror')) throw new Error('Unresolved math');
    return {tex, mathml};
  } catch (error) {
    return {tex, error: error.message};
  }
});
process.stdout.write(JSON.stringify(results));
