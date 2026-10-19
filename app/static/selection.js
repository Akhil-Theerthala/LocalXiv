// The selection toolbar over the Paper, and the selected words in the one text of onetext.js.
import {node} from './render.js';
import {native} from './shell.js';
import {textMap} from './onetext.js';

const frame = () => document.getElementById('paper-frame');

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
