// The Chrome state, its two renderers (the Native shell, or the web sidebar and toolbar in a browser),
// the one command dispatcher, the key map, the history, and the bridge to Swift.
import {node, icon} from './render.js';
import {THEMES, FONTS, WIDTHS, SPACINGS, SIZES, DEFAULTS} from './appearance.js';

const bridge = window.webkit?.messageHandlers?.shell;
export const native = Boolean(bridge);
const $ = id => document.getElementById(id);

// ---- Chrome state ----
const state = {
  mode: 'home', title: 'Home', subtitle: '', canBack: false, canForward: false,
  sidebar: {selected: 'home', counts: {all: 0, new: 0, reading: 0, read: 0}, recent: [], reader: null},
  views: null, actions: {share: [], more: []}, prefs: {...DEFAULTS}, activity: null, search: {query: ''},
};
const plain = value => value !== null && typeof value === 'object' && !Array.isArray(value);
function merge(target, patch) {
  for (const [key, value] of Object.entries(patch)) target[key] = plain(value) && plain(target[key]) ? merge({...target[key]}, value) : value;
  return target;
}
let frame = 0, timer = 0, ready = false, posted = '';
// A hidden or occluded web view runs no animation frames, so a timer delivers the state there.
function schedule() {
  if (frame || !ready) return;
  frame = requestAnimationFrame(flush); timer = setTimeout(flush, 100);
}
function flush() {
  cancelAnimationFrame(frame); clearTimeout(timer); frame = 0;
  const json = JSON.stringify(state);
  if (json === posted) return;
  posted = json;
  if (native) bridge.postMessage({type: 'state', state: JSON.parse(json)});
  else draw();
}
export const chrome = {
  state,
  update(patch) { merge(state, patch); schedule(); },
  // Swift queues its commands until this message, so it goes out once every handler is registered.
  ready() {
    if (ready) return;
    ready = true;
    if (native) bridge.postMessage({type: 'ready'});
    schedule();
  },
};

// ---- Commands ----
const handlers = new Map();
export function register(name, handler) { handlers.set(name, handler); }
// A modal dialog holds the page, so a key or a native menu must not change the page behind it.
const PAGE_COMMANDS = new Set(['go', 'open', 'view', 'outline', 'back', 'forward', 'search', 'add']);
export const commands = {run: command => {
  if (PAGE_COMMANDS.has(command?.name) && document.querySelector('dialog[open]')) return;
  return handlers.get(command?.name)?.(command);
}};
window.localxiv = {command: command => commands.run(command)};

// ---- History: page changes only; the web app owns it, so Back works the same from Swift and from keys ----
const entries = [];
let at = -1, showEntry = () => {};
function syncHistory() { chrome.update({canBack: at > 0, canForward: at < entries.length - 1}); }
export const nav = {
  get current() { return entries[at] || null; },
  get previous() { return entries[at - 1] || null; },
  onShow(handler) { showEntry = handler; },
  push(entry) {
    if (entries[at]) entries[at].scroll = window.scrollY;
    entries.splice(at + 1, Infinity, entry); at = entries.length - 1; syncHistory();
  },
  replace(entry) { if (at < 0) return nav.push(entry); entries[at] = entry; syncHistory(); },
  step(delta) {
    if (!entries[at + delta]) return;
    entries[at].scroll = window.scrollY; at += delta; syncHistory();
    showEntry(entries[at]);
  },
};
register('back', () => nav.step(-1));
register('forward', () => nav.step(1));

// ---- Keys: in the Native shell the menus own these, so the map is off there ----
const KEYS = {
  'meta+1': {name: 'view', view: 'overview'}, 'meta+2': {name: 'view', view: 'blog'}, 'meta+3': {name: 'view', view: 'paper'},
  'meta+[': {name: 'back'}, 'meta+]': {name: 'forward'}, 'ctrl+meta+s': {name: 'sidebar'},
  'meta+=': {name: 'text-size', step: 1}, 'shift+meta++': {name: 'text-size', step: 1}, 'shift+meta+=': {name: 'text-size', step: 1},
  'meta+-': {name: 'text-size', step: -1}, 'meta+0': {name: 'text-size', step: 0},
  'meta+n': {name: 'add'}, 'meta+,': {name: 'settings'}, 'shift+meta+h': {name: 'go', to: 'home'}, 'shift+meta+l': {name: 'go', to: 'all'},
};
export function keydown(event) {
  if (native || event.defaultPrevented) return;
  const key = `${event.ctrlKey ? 'ctrl+' : ''}${event.altKey ? 'alt+' : ''}${event.shiftKey ? 'shift+' : ''}${event.metaKey ? 'meta+' : ''}${event.key.toLowerCase()}`;
  // Inside the reader ⌘F stays the browser's find in the open view.
  if (key === 'meta+f' && state.mode !== 'reader') { event.preventDefault(); $('tb-search-input').focus(); return; }
  if (!KEYS[key]) return;
  event.preventDefault(); commands.run(KEYS[key]);
}
document.addEventListener('keydown', keydown);

// ---- Web menus: Share, More, and the Library context menu, in both modes ----
const menuElement = node('div', undefined, 'menu');
menuElement.setAttribute('role', 'menu'); menuElement.hidden = true;
let menuReturn = null;
function closeMenu() {
  if (menuElement.hidden) return;
  menuElement.hidden = true;
  menuReturn?.setAttribute?.('aria-expanded', 'false');
  if (menuReturn?.isConnected && menuElement.contains(document.activeElement)) menuReturn.focus();
}
// `at` is the button that opens the menu, or a pointer event for a context menu.
export function openMenu(at, items, onPick) {
  closeMenu(); document.body.append(menuElement);
  menuElement.replaceChildren(...items.flatMap(item => {
    const button = node('button', item.label, item.role === 'destructive' ? 'destructive' : '');
    button.type = 'button'; button.setAttribute('role', 'menuitem'); button.disabled = !item.enabled;
    button.onclick = () => { closeMenu(); onPick(item.id); };
    return item.separatorBefore ? [node('hr'), button] : [button];
  }));
  menuElement.hidden = false;
  const box = menuElement.getBoundingClientRect(), anchor = at instanceof Element ? at.getBoundingClientRect() : null;
  const left = anchor ? anchor.right - box.width : at.clientX, top = anchor ? anchor.bottom + 6 : at.clientY;
  menuElement.style.left = Math.max(8, Math.min(innerWidth - box.width - 8, left)) + 'px';
  menuElement.style.top = Math.max(8, top + box.height > innerHeight - 8 ? (anchor ? anchor.top - box.height - 6 : top - box.height) : top) + 'px';
  menuReturn = at instanceof Element ? at : document.activeElement;
  if (at instanceof Element) at.setAttribute('aria-expanded', 'true');
  menuElement.querySelector('button:not(:disabled)')?.focus();
}
menuElement.onkeydown = event => {
  const buttons = [...menuElement.querySelectorAll('button:not(:disabled)')], index = buttons.indexOf(document.activeElement);
  if (event.key === 'Escape') closeMenu();
  else if (['ArrowDown', 'ArrowUp'].includes(event.key)) buttons[(index + (event.key === 'ArrowDown' ? 1 : buttons.length - 1)) % buttons.length]?.focus();
  else if (event.key === 'Tab') closeMenu();
  else return;
  event.preventDefault(); event.stopPropagation();
};

// ---- Browser mode: the web sidebar and toolbar draw the same Chrome state ----
const narrow = matchMedia('(max-width: 999px)');
register('sidebar', () => {
  if (narrow.matches) document.body.classList.toggle('sidebar-open');
  else document.body.classList.toggle('sidebar-hidden');
});
narrow.addEventListener('change', () => document.body.classList.remove('sidebar-open'));
const LIBRARY = [['all', 'All Papers', 'stack'], ['new', 'New', 'unread'], ['reading', 'Reading', 'progress'], ['read', 'Read', 'check-circle']];

function row(label, glyph, command, {current = false, count, className = 'sb-row'} = {}) {
  const button = node('button', undefined, className);
  button.type = 'button';
  if (glyph) button.append(icon(glyph));
  button.append(node('span', label, 't'));
  if (count !== undefined) button.append(node('span', String(count), 'n'));
  if (current) button.setAttribute('aria-current', 'page');
  button.onclick = () => { document.body.classList.remove('sidebar-open'); commands.run(command); };
  return button;
}
function section(label) { return node('div', label, 'sb-section'); }

function drawSidebar() {
  const {sidebar, mode} = state, scroll = $('sidebar-scroll');
  const items = [];
  if (sidebar.reader) {
    const reader = sidebar.reader, paper = node('div', undefined, 'sb-paper');
    items.push(row(reader.back, 'chev-l', {name: 'back'}, {className: 'sb-row sb-back'}));
    paper.append(node('div', reader.title, 'pt'), node('div', reader.byline, 'pm'));
    items.push(paper, section('Contents'));
    const outline = node('nav'); outline.setAttribute('aria-label', 'Contents');
    for (const entry of reader.outline) {
      const button = node('button', undefined, `toc-row lvl${entry.level}${entry.current ? ' is-current' : ''}`);
      button.type = 'button';
      button.append(node('span', entry.number, 'num'), node('span', entry.label, 't'));
      if (entry.current) button.setAttribute('aria-current', 'location');
      button.onclick = () => { document.body.classList.remove('sidebar-open'); commands.run({name: 'outline', id: entry.id}); };
      outline.append(button);
    }
    if (!reader.outline.length) outline.append(node('p', 'This view has no sections.', 'sb-note'));
    items.push(outline);
  } else {
    items.push(row('Home', 'house', {name: 'go', to: 'home'}, {current: sidebar.selected === 'home'}), section('Library'));
    for (const [to, label, glyph] of LIBRARY) items.push(row(label, glyph, {name: 'go', to}, {current: sidebar.selected === to, count: sidebar.counts[to]}));
    if (sidebar.recent.length) items.push(section('Recent'));
    for (const paper of sidebar.recent) items.push(row(paper.title, 'doc', {name: 'open', id: paper.id}, {current: paper.current && mode === 'reader'}));
  }
  scroll.replaceChildren(...items);
  scroll.querySelector('.is-current')?.scrollIntoView({block: 'nearest'});
}

function drawActivity() {
  const activity = state.activity, button = $('sb-activity');
  button.hidden = !activity;
  if (!activity) return;
  $('sb-activity-label').textContent = activity.label;
  $('sb-activity-count').textContent = activity.count > 1 ? String(activity.count) : '';
  const bar = $('sb-activity-bar');
  if (activity.progress === null) bar.removeAttribute('value'); else bar.value = activity.progress;
}

let sidebarSignature = '';
function draw() {
  document.body.dataset.mode = state.mode;
  document.title = state.mode === 'home' ? 'LocalXiv' : `${state.title} · LocalXiv`;
  $('tb-title').textContent = state.title;
  $('tb-subtitle').textContent = state.subtitle;
  $('tb-back').disabled = !state.canBack; $('tb-forward').disabled = !state.canForward;
  const reader = Boolean(state.views);
  $('tb-add').hidden = reader; $('tb-views').hidden = !reader; $('tb-reader').hidden = !reader;
  for (const view of ['overview', 'blog', 'paper']) {
    const button = $('tb-view-' + view), viewState = state.views?.[view];
    button.setAttribute('aria-pressed', String(state.views?.current === view));
    button.disabled = viewState === 'off';
    button.title = viewState === 'off' ? 'Connect AI in Settings to make this view' : viewState === 'working' ? 'Being made now' : '';
  }
  $('tb-share').disabled = !state.actions.share.length; $('tb-more').disabled = !state.actions.more.length;
  // Each keystroke sets the query before this runs, so writing it back never drops typed text.
  if ($('tb-search-input').value !== state.search.query) $('tb-search-input').value = state.search.query;
  const signature = JSON.stringify([state.mode, state.sidebar]);
  if (signature !== sidebarSignature) { sidebarSignature = signature; drawSidebar(); }
  drawActivity();
  if (!$('aa-popover').hidden) syncPrefs();
}

// ---- The Aa popover in browser mode; in the Native shell, AppKit draws it ----
function segmented(field, options) {
  const group = node('div', undefined, 'segs');
  group.setAttribute('role', 'radiogroup');
  for (const [value, label] of options) {
    const button = node('button', label);
    button.type = 'button'; button.setAttribute('role', 'radio'); button.dataset.field = field; button.dataset.value = value;
    button.onclick = () => commands.run({name: 'prefs', patch: {[field]: value}});
    group.append(button);
  }
  return group;
}
function group(label, control, value) {
  const wrapper = node('div', undefined, 'grp'), heading = node('div', label, 'gl');
  if (value) heading.append(value);
  wrapper.append(heading, control);
  return wrapper;
}
function buildPrefs() {
  const popover = $('aa-popover'), swatches = node('div', undefined, 'swatches'), fonts = node('div', undefined, 'fonts');
  swatches.setAttribute('role', 'radiogroup'); fonts.setAttribute('role', 'radiogroup');
  for (const [value, label] of Object.entries(THEMES)) {
    const button = node('button', undefined, 'sw'), chip = node('span', 'Aa', 'chipx');
    button.type = 'button'; button.setAttribute('role', 'radio'); button.dataset.field = 'theme'; button.dataset.value = value; button.dataset.v = value;
    button.append(chip, node('span', label));
    button.onclick = () => commands.run({name: 'prefs', patch: {theme: value}});
    swatches.append(button);
  }
  for (const [value, {name, stack}] of Object.entries(FONTS)) {
    const button = node('button', name);
    button.type = 'button'; button.setAttribute('role', 'radio'); button.dataset.field = 'font'; button.dataset.value = value; button.style.fontFamily = stack;
    button.append(icon('check', 'i ck'));
    button.onclick = () => commands.run({name: 'prefs', patch: {font: value}});
    fonts.append(button);
  }
  const stepper = node('div', undefined, 'stepper'), smaller = node('button', 'A', 'a1'), bigger = node('button', 'A', 'a2'), slider = node('input');
  smaller.type = bigger.type = 'button'; smaller.setAttribute('aria-label', 'Smaller text'); bigger.setAttribute('aria-label', 'Bigger text');
  smaller.onclick = () => commands.run({name: 'text-size', step: -1}); bigger.onclick = () => commands.run({name: 'text-size', step: 1});
  Object.assign(slider, {type: 'range', min: SIZES[0], max: SIZES[1], step: 1, id: 'aa-size'}); slider.setAttribute('aria-label', 'Text size');
  slider.oninput = () => commands.run({name: 'prefs', patch: {size: Number(slider.value)}});
  stepper.append(smaller, slider, bigger);
  const sizeValue = node('span', '', 'v'); sizeValue.id = 'aa-size-value';
  popover.replaceChildren(
    group('Theme', swatches), group('Font', fonts), group('Text size', stepper, sizeValue),
    group('Line length', segmented('width', Object.entries(WIDTHS).map(([value, [label]]) => [value, label]))),
    group('Line spacing', segmented('spacing', Object.entries(SPACINGS).map(([value, [label]]) => [value, label]))));
}
function syncPrefs() {
  for (const button of $('aa-popover').querySelectorAll('[data-field]')) button.setAttribute('aria-checked', String(String(state.prefs[button.dataset.field]) === button.dataset.value));
  const slider = $('aa-size');
  slider.value = state.prefs.size;
  slider.style.setProperty('--fillp', (state.prefs.size - SIZES[0]) / (SIZES[1] - SIZES[0]) * 100 + '%');
  $('aa-size-value').textContent = state.prefs.size + ' px';
}
function togglePrefs(open = $('aa-popover').hidden) {
  const popover = $('aa-popover');
  popover.hidden = !open; $('tb-aa').setAttribute('aria-expanded', String(open));
  if (!open) return;
  if (!popover.firstChild) buildPrefs();
  syncPrefs();
  const anchor = $('tb-aa').getBoundingClientRect();
  popover.style.right = Math.max(8, innerWidth - anchor.right - 120) + 'px';
  popover.querySelector('[aria-checked=true]')?.focus();
}

if (!native) {
  document.body.classList.add('web');
  $('tb-sidebar').onclick = () => commands.run({name: 'sidebar'});
  $('tb-back').onclick = () => commands.run({name: 'back'});
  $('tb-forward').onclick = () => commands.run({name: 'forward'});
  $('tb-add').onclick = () => commands.run({name: 'add'});
  for (const view of ['overview', 'blog', 'paper']) $('tb-view-' + view).onclick = () => commands.run({name: 'view', view});
  $('tb-aa').onclick = () => togglePrefs();
  for (const kind of ['share', 'more']) $('tb-' + kind).onclick = event => openMenu(event.currentTarget, state.actions[kind], id => commands.run({name: 'action', id}));
  $('sb-activity').onclick = () => commands.run({name: 'activity'});
  $('sb-settings').onclick = () => commands.run({name: 'settings'});
  const search = $('tb-search-input');
  search.oninput = () => commands.run({name: 'search', query: search.value});
  search.onkeydown = event => {
    if (event.key === 'Enter') { event.preventDefault(); commands.run({name: 'search', query: search.value, submit: true}); }
    else if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); search.value = ''; commands.run({name: 'search', query: ''}); search.blur(); }
  };
  $('sidebar-scrim').onclick = () => document.body.classList.remove('sidebar-open');
  document.addEventListener('pointerdown', event => {
    if (!menuElement.contains(event.target)) closeMenu();
    if (!$('aa-popover').hidden && !$('aa-popover').contains(event.target) && !$('tb-aa').contains(event.target)) togglePrefs(false);
  });
  document.addEventListener('keydown', event => {
    if (event.key !== 'Escape') return;
    if (!$('aa-popover').hidden) { togglePrefs(false); $('tb-aa').focus(); event.preventDefault(); }
    else if (document.body.classList.contains('sidebar-open')) { document.body.classList.remove('sidebar-open'); event.preventDefault(); }
  });
} else {
  document.body.classList.add('native');
  document.addEventListener('pointerdown', event => { if (!menuElement.contains(event.target)) closeMenu(); });
}
