// No autoload, require, or HTML packages: overview TeX cannot fetch code or add links.
window.MathJax = {
  startup: {typeset: false},
  options: {enableMenu: false},
  tex: {packages: ['base', 'ams', 'newcommand', 'noundefined'], maxBuffer: 20000, maxMacros: 1000},
  svg: {fontCache: 'local'}
};
