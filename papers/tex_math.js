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
};

const results = JSON.parse(fs.readFileSync(0, 'utf8')).map(({tex, display}) => {
  try {
    const input = new TeX({packages, macros, formatError: (_, error) => {throw error;}});
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
