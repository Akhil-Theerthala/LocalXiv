// Bars of buttons over the Paper: the selection toolbar, and the card at a mark (margin.js).
import {node} from './render.js';
import {native, chrome, commands, openMenu, closeMenu} from './shell.js';
import {copy} from './app.js';

const frame = () => document.getElementById('paper-frame');

// ---- Bars ----
// While a bar shows, as after a keyboard selection, Tab in the Paper moves focus to it: to its pressed button, or else
// to its first one. The arrow keys move between its buttons, and Escape closes the bar and returns focus to the Paper.
// A scroll closes each bar.
const bars = [];
addEventListener('scroll', () => { for (const bar of bars) bar.hidden = true; }, {passive: true});
export function buttonBar(name) {
  const bar = node('div', undefined, 'selbar');
  bar.setAttribute('role', 'toolbar'); bar.setAttribute('aria-label', name); bar.hidden = true;
  bar.onkeydown = event => {
    const buttons = [...bar.children], at = buttons.indexOf(document.activeElement);
    if (event.key === 'Escape') { bar.hidden = true; frame().contentWindow?.focus(); }
    else if (['ArrowLeft', 'ArrowRight'].includes(event.key)) buttons[(at + (event.key === 'ArrowRight' ? 1 : buttons.length - 1)) % buttons.length].focus();
    else return;
    event.preventDefault(); event.stopPropagation();
  };
  document.body.append(bar);
  bars.push(bar);
  return bar;
}
// The buttons of a bar. Each item is {label, ariaLabel, action}; a colour swatch has no label and gives its `colour`.
export function fillBar(bar, items) {
  bar.replaceChildren(...items.map(({label, ariaLabel, action, colour}) => {
    const button = node('button', label, colour ? 'swatch' : undefined);
    button.type = 'button'; button.title = ariaLabel; button.setAttribute('aria-label', ariaLabel);
    if (colour) { button.dataset.colour = colour; button.style.setProperty('--c', `var(--${colour})`); }
    // The Paper keeps its selection while the pointer presses a button.
    button.onpointerdown = event => event.preventDefault();
    button.onclick = action;
    return button;
  }));
}
// Shows `bar` over `box`, a rectangle in the Paper frame, or under it when the top of the window has no room.
export function placeBar(bar, box) {
  bar.hidden = false;
  const outer = frame().getBoundingClientRect(), own = bar.getBoundingClientRect(), ceiling = native ? 8 : 60, above = outer.top + box.top - own.height - 8;
  bar.style.left = Math.max(8, Math.min(innerWidth - own.width - 8, outer.left + box.left + box.width / 2 - own.width / 2)) + 'px';
  bar.style.top = (above >= ceiling ? above : outer.top + box.bottom + 8) + 'px';
}

// ---- The selection toolbar ----
// It shows over a selection in the Paper view. There is one toolbar: a later call changes only its buttons.
let toolbar = null, chosen = null;
const wired = new WeakSet();
export function selectionToolbar(items) {
  if (!toolbar) {
    toolbar = buttonBar('Selection');
    addEventListener('lx-chapter', event => wire(event.detail.doc));
    if (frame().contentDocument?.body) wire(frame().contentDocument);
  }
  fillBar(toolbar, items.map(item => ({...item, action: () => act(item.action, chosen)})));
  return {hide, act};
}
// Runs `action` on `range`. Focus leaves the hidden toolbar for the Paper; an action can move it again.
function act(action, range) {
  if (toolbar.contains(document.activeElement)) frame().contentWindow?.focus();
  hide();
  if (range) action(range);
}
// The selection in the Paper view, or null when it has no words.
export function liveRange(doc = frame().contentDocument) {
  const selection = doc?.getSelection();
  if (document.getElementById('reader-page').dataset.view !== 'paper' || !selection?.rangeCount || selection.isCollapsed
    || !selection.toString().trim()) return null;
  return selection.getRangeAt(0).cloneRange();
}
// The selection commands of the Paper menu (app.js readerActions), which the context menu also holds.
const COMMANDS = ['highlight', 'add-note', 'ask', 'explain'];
function wire(doc) {
  if (wired.has(doc)) return;
  wired.add(doc);
  // A right-click opens the context menu, which has the same commands.
  doc.addEventListener('mouseup', event => { if (event.button === 0) setTimeout(() => show(doc)); });
  doc.addEventListener('keyup', event => { if (event.shiftKey || event.key === 'Shift') show(doc); });
  doc.addEventListener('keydown', event => {
    const bar = bars.find(item => !item.hidden);
    if (event.key !== 'Tab' || event.shiftKey || !bar) return;
    event.preventDefault(); (bar.querySelector('[aria-pressed=true]') || bar.firstChild).focus();
  });
  doc.addEventListener('selectionchange', () => { if (doc.getSelection()?.isCollapsed) hide(); });
  // In a browser, the context menu on a selection holds the selection commands and Copy. The Native shell adds the
  // commands to WebKit's own menu. A press in the Paper closes the menu, as a press in the page does.
  doc.addEventListener('contextmenu', event => {
    const range = liveRange(doc);
    if (native || !range) return;
    event.preventDefault(); hide();
    const outer = frame().getBoundingClientRect(), items = chrome.state.actions.more.filter(item => COMMANDS.includes(item.id));
    openMenu({clientX: outer.left + event.clientX, clientY: outer.top + event.clientY},
      [...items, {id: 'copy', label: 'Copy', enabled: true, separatorBefore: true}],
      id => id === 'copy' ? copy(range.toString(), 'Text') : commands.run({name: 'action', id}));
  });
  doc.addEventListener('pointerdown', () => closeMenu());
}
function show(doc) {
  chosen = liveRange(doc);
  if (!chosen) return hide();
  placeBar(toolbar, chosen.getClientRects()[0] || chosen.getBoundingClientRect());
}
function hide() { if (toolbar) toolbar.hidden = true; }
