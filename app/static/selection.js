// The selection toolbar over the Paper, and the one text that a selection maps to: the passage text that
// papers/document.py _text() builds, so a stored quote is found again in the Paper and in the library row.
import {node} from './render.js';
import {native} from './shell.js';

const MATHML = 'http://www.w3.org/1998/Math/MathML';
const frame = () => document.getElementById('paper-frame');

// A formula's TeX, as papers/document.py _tex() reads it.
function tex(math) {
  return math.getAttribute('alttext')
    || [...math.getElementsByTagNameNS(MATHML, 'annotation')].find(note => note.getAttribute('encoding') === 'application/x-tex')?.textContent || '';
}

// The text of `root` as papers/document.py _text() builds it: each formula is " $tex$ ", and whitespace collapses
// to one space with none at the ends. `map[i]` is where character i comes from: [text node, offset], or the
// formula's math element, so that a selection edge inside a formula takes the whole formula.
export function textMap(root) {
  let text = '', space = null;
  const map = [];
  const add = (char, source) => {
    if (/\s/.test(char)) { space ??= source; return; }
    if (space && text) { text += ' '; map.push(space); }
    space = null; text += char; map.push(source);
  };
  const walk = parent => {
    for (const child of parent.childNodes) {
      if (child.nodeType === Node.TEXT_NODE || child.nodeType === Node.CDATA_SECTION_NODE) {
        for (let offset = 0; offset < child.data.length; offset++) add(child.data[offset], [child, offset]);
      } else if (child.nodeType !== Node.ELEMENT_NODE) continue;
      else if (child.namespaceURI === MATHML && child.localName === 'math') {
        const source = tex(child), value = source ? ` $${source}$ ` : ` ${child.textContent} `;
        for (const char of value) add(char, child);
      } else walk(child);
    }
  };
  walk(root);
  return {text, map};
}

const inRange = (range, source) => Array.isArray(source)
  ? range.comparePoint(source[0], source[1]) === 0 && range.comparePoint(source[0], source[1] + 1) === 0
  : range.intersectsNode(source);

// The selected words of `passage` in that one text. The browser's Selection.toString() writes a formula as styled
// letters (𝑑 for d), which no stored text has.
export function rangeText(passage, range) {
  const {text, map} = textMap(passage);
  let first = -1, last = -1;
  map.forEach((source, index) => { if (inRange(range, source)) { if (first < 0) first = index; last = index; } });
  return first < 0 ? '' : text.slice(first, last + 1).trim();
}

// The DOM range of the first place `quote` is in `root`, and the formulas in it, or null.
// shortcut: a short quote that is also earlier in the passage marks those earlier words, until Release 2 anchors store a
// prefix and a suffix with the quote.
export function findWords(root, quote) {
  const {text, map} = textMap(root), start = quote ? text.indexOf(quote) : -1;
  if (start < 0) return null;
  const first = map[start], last = map[start + quote.length - 1], range = root.ownerDocument.createRange();
  if (Array.isArray(first)) range.setStart(...first); else range.setStartBefore(first);
  if (Array.isArray(last)) range.setEnd(last[0], last[1] + 1); else range.setEndAfter(last);
  const formulas = new Set(map.slice(start, start + quote.length).filter(source => !Array.isArray(source)));
  return {range, formulas: [...formulas]};
}

// ---- The toolbar ----
// It shows over a selection in the Paper view. After a keyboard selection, Tab moves focus to it, the arrow keys
// move between its buttons, and Escape returns focus to the Paper.
let bar = null, chosen = null;
const wired = new WeakSet();
export function selectionToolbar({ask, explain}) {
  bar = node('div', undefined, 'selbar');
  bar.setAttribute('role', 'toolbar'); bar.setAttribute('aria-label', 'Selection'); bar.hidden = true;
  for (const [label, action, title] of [['Ask', ask, 'Ask about the selected text'], ['Explain', explain, 'Explain the selected text']]) {
    const button = node('button', label);
    button.type = 'button'; button.title = title;
    // The Paper keeps its selection while the pointer presses a button.
    button.onpointerdown = event => event.preventDefault();
    button.onclick = () => { const range = chosen; hide(); if (range) action(range); };
    bar.append(button);
  }
  bar.onkeydown = event => {
    const buttons = [...bar.children], at = buttons.indexOf(document.activeElement);
    if (event.key === 'Escape') { hide(); frame().contentWindow?.focus(); }
    else if (['ArrowLeft', 'ArrowRight'].includes(event.key)) buttons[(at + (event.key === 'ArrowRight' ? 1 : buttons.length - 1)) % buttons.length].focus();
    else return;
    event.preventDefault(); event.stopPropagation();
  };
  document.body.append(bar);
  addEventListener('lx-chapter', event => wire(event.detail.doc));
  if (frame().contentDocument?.body) wire(frame().contentDocument);
  addEventListener('scroll', hide, {passive: true});
  return {hide};
}
function wire(doc) {
  if (wired.has(doc)) return;
  wired.add(doc);
  doc.addEventListener('mouseup', () => setTimeout(() => show(doc)));
  doc.addEventListener('keyup', event => { if (event.shiftKey || event.key === 'Shift') show(doc); });
  doc.addEventListener('keydown', event => {
    if (event.key !== 'Tab' || event.shiftKey || bar.hidden) return;
    event.preventDefault(); bar.firstChild.focus();
  });
  doc.addEventListener('selectionchange', () => { if (doc.getSelection()?.isCollapsed) hide(); });
}
function show(doc) {
  const selection = doc.getSelection();
  if (document.getElementById('reader-page').dataset.view !== 'paper' || !selection?.rangeCount || selection.isCollapsed
    || !selection.toString().trim()) return hide();
  chosen = selection.getRangeAt(0).cloneRange();
  bar.hidden = false;
  const box = chosen.getClientRects()[0] || chosen.getBoundingClientRect(), outer = frame().getBoundingClientRect();
  const own = bar.getBoundingClientRect(), ceiling = native ? 8 : 60, above = outer.top + box.top - own.height - 8;
  bar.style.left = Math.max(8, Math.min(innerWidth - own.width - 8, outer.left + box.left + box.width / 2 - own.width / 2)) + 'px';
  bar.style.top = (above >= ceiling ? above : outer.top + box.bottom + 8) + 'px';
}
function hide() { if (bar) bar.hidden = true; }
