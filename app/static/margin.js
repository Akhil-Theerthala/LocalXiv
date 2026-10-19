// Highlights and Question cards in the Paper view: the marks on the words, the card at a mark, the layout of the
// reading column and the margin, the shell of each card, the line from a card to its words, and Ask About the Paper.
// chat.js has the body of a Question card and its stream, and notes.js has All Notes.
// reader.js, app.js, chat.js, and notes.js import this module, and this module imports reader.js, app.js, and chat.js.
// Its top level only defines functions and adds listeners, so no module reads another's bindings before all have run.
import {node} from './render.js';
import {native, chrome, register} from './shell.js';
import {wideMeasure} from './appearance.js';
import {selectionToolbar, buttonBar, fillBar, placeBar} from './selection.js';
import {textMap, findWords} from './onetext.js';
import {api, paperAPI, notice, prefs} from './app.js';
import {goPassage, selected, detail} from './reader.js';
import {drawTurns, drawActions, drawCompose, send} from './chat.js';

const $ = id => document.getElementById(id);
const frame = () => $('paper-frame');
// The margin takes up to 300 px. With less than 210 px for the margin, cards fold to markers in the page's right padding.
const GAP = 24, MAX_CARD = 300, MIN_CARD = 210, MARKER = 20;
// The text of the Paper keeps at least this many em of the reading size, so that each full line has at least 45
// characters at every reading size (the serif is wider for each em at the small sizes).
const MIN_TEXT = 26.75;
const EXPLAIN = 'Explain this passage.';
// The top of the view that the toolbar leaves free.
const viewTop = () => native ? 12 : 64;

// The four colours of a Highlight, in order, with their names.
export const COLOURS = {key: 'Key point', question: 'Question', use: 'Use in my work', disagree: 'Disagree'};

// The marks: every record of the Paper, as {id, record, draft, pending, controller, element, words}. A mark with
// words is painted and hit-tested. A draft has no question yet, so the server does not have it; its first question
// stores it.
export const marks = new Map();
// The marks with a margin card: a Question card, or the active mark. A Highlight with no Note is a mark only.
export const hasCard = mark => mark.id === active || !mark.record.kept || mark.record.turns.length > 0 || Boolean(mark.pending);
// What Discard and Delete removed in this session, for ⌘Z, each with its Paper: {paper, records, question} as the
// server had them, with the question of a follow-up that was discarded during its answer, or {paper, where, question}
// for a new card that was discarded during its first answer. ⌘Z restores the last entry of the selected Paper. The
// Native shell's Edit › Undo sends 'undo' while canUndo is true, which is only in the Paper view.
const undo = [];
const undoable = () => selected === paperId && undo.some(entry => entry.paper === paperId);
const syncUndo = () => chrome.update({canUndo: mounted && undoable()});
export let paperId = null;
// The colour of the last Highlight that the reader made or changed.
export let lastColour = 'key';
// `down` is where the pointer last went down in the Paper.
let mounted = false, margin = null, toolbar = null, observer = null, doc = null, chapter = '', docPaper = null, pop = null, down = null;
let folded = false, width = MAX_CARD, active = '', wanted = '', drafts = 0, scheduled = 0;
// The one text of each element of the loaded chapter. A chapter load clears it.
let texts = new WeakMap();
const oneText = element => texts.get(element) || texts.set(element, textMap(element)).get(element);

// ---- Mount ----
export function mountMargin() {
  if (selected !== paperId) reset();
  if (!mounted) {
    mounted = true;
    if (!margin) {
      margin = node('div', undefined, 'lx-margin');
      margin.setAttribute('role', 'complementary'); margin.setAttribute('aria-label', 'Question cards');
      // A card that moves to its place moves the end of the line.
      margin.addEventListener('transitionend', () => line?.draw());
    }
    document.body.append(margin);
    toolbar ||= selectionToolbar([
      ...Object.entries(COLOURS).map(([colour, name]) => ({ariaLabel: name, colour, action: range => highlight(range, colour)})),
      {label: 'Ask', ariaLabel: 'Ask about the selected text', action: range => openCard(askAbout(range))},
      {label: 'Explain', ariaLabel: 'Explain the selected text', action: range => openCard(askAbout(range), EXPLAIN)}]);
    observer ||= new ResizeObserver(schedule);
    // The frame resizes with Reading preferences and chapters, and main with the web sidebar.
    observer.observe(frame()); observer.observe($('main'));
    for (const card of marks.values()) if (card.element) observer.observe(card.element);
  }
  paint(); layout(); syncUndo();
}
export function unmountMargin() {
  if (!mounted) return;
  mounted = false;
  observer.disconnect(); margin.remove(); toolbar.hide(); closePop(); clearLine(); syncUndo();
  active = ''; dropDraft();
  const page = $('reader-page');
  page.style.maxWidth = page.style.marginLeft = page.style.marginRight = '';
}
// The Chat settings can change in Settings or in the Settings window, so each Chrome state sync redraws the question
// fields. A field redraws only when what it shows changes.
export function syncCards() {
  if (mounted) for (const card of marks.values()) drawCompose(card);
}
export function reset() {
  for (const card of marks.values()) card.controller?.abort();
  marks.clear(); margin?.replaceChildren(); clearLine(); closePop();
  paperId = selected; active = wanted = '';
  // The frame keeps a chapter of this Paper that loaded before the Paper view showed, and no load event follows.
  if (docPaper !== selected) { doc = null; chapter = ''; }
  for (const record of detail?.highlights || []) marks.set(record.id, {id: record.id, record});
  syncUndo();
}
export function schedule() {
  if (!scheduled) scheduled = requestAnimationFrame(() => { scheduled = 0; layout(); });
}
addEventListener('lx-chapter', event => {
  ({doc, path: chapter, paper: docPaper} = event.detail);
  texts = new WeakMap();
  doc.addEventListener('keydown', keys);
  // This runs before the click, which can open the card at a mark.
  doc.addEventListener('pointerdown', event => { down = [event.clientX, event.clientY]; closePop(); deselect(); });
  doc.addEventListener('click', clicked);
  doc.defaultView.addEventListener('scroll', scrolled, {passive: true});
  if (!mounted) return;
  paint(); layout();
  const card = marks.get(wanted);
  wanted = '';
  if (card) select(card);
});
addEventListener('resize', () => { if (mounted) layout(); });
// A scroll of the page or the frame moves the line, and an active card that follows the view. When the card starts or
// stops following, the layout places the cards again.
function scrolled() {
  if (!mounted) return;
  const card = marks.get(active);
  if (card?.element) {
    const follow = following(card);
    if (follow !== card.element.classList.contains('is-following')) return layout();
    if (follow) card.element.style.top = viewTop() - margin.getBoundingClientRect().top + 'px';
  }
  line?.draw();
}
addEventListener('scroll', scrolled, {passive: true});
// The selection toolbar and the card at a mark are .selbar.
document.addEventListener('pointerdown', event => {
  if (!pop?.contains(event.target)) closePop();
  if (!event.target.closest?.('.lx-card, .selbar, .menu, dialog, .pop')) deselect();
});
document.addEventListener('keydown', keys);
function keys(event) {
  const editing = event.target.closest?.('input, textarea, select, [contenteditable]');
  if (event.key === 'Escape' && pop && !pop.hidden) { event.preventDefault(); closePop(); }
  else if (event.key === 'Escape' && active && !document.querySelector('dialog[open]')) { event.preventDefault(); deselect(); }
  else if ((event.metaKey || event.ctrlKey) && !event.shiftKey && event.key.toLowerCase() === 'z' && !editing && undoable()) {
    event.preventDefault(); restore();
  }
}
register('undo', () => { if (undoable()) restore(); });

// ---- Where a mark's words are ----
const hrefOf = record => record.href || detail?.paper?.passages?.find(item => item.id === record.passage)?.href || '';
// The passages of the loaded chapter, with their elements, in reading order.
function chapterPassages() {
  if (!doc) return [];
  return (detail?.paper?.passages || []).flatMap(item => {
    const [path, id] = item.href.split('#'), element = path === chapter && id && doc.getElementById(id);
    return element ? [{...item, element}] : [];
  });
}
const inRange = (range, source) => Array.isArray(source)
  ? range.comparePoint(source[0], source[1]) === 0 && range.comparePoint(source[0], source[1] + 1) === 0
  : range.intersectsNode(source);
// The selected characters of the one text of `root`: {text, start, stop}, with no space at either end, or null. The
// browser's Selection.toString() writes a formula as styled letters (𝑑 for d), which no stored text has.
function span(root, range) {
  const {text, map} = oneText(root);
  let start = -1, stop = -1;
  map.forEach((source, index) => { if (inRange(range, source)) { if (start < 0) start = index; stop = index + 1; } });
  while (start < stop && text[start] === ' ') start++;
  while (stop > start && text[stop - 1] === ' ') stop--;
  return start < stop ? {text, start, stop} : null;
}
const words = ({text, start, stop}) => text.slice(start, stop);
const before = ({text, start}) => text.slice(Math.max(0, start - 32), start), after = ({text, stop}) => text.slice(stop, stop + 32);
// The anchor of a selection in the one text that findOffset searches: its passage, its words, and up to 32 characters
// before and after them. A selection across passages keeps its words in the first passage as `head`, and those in the
// last passage as `end`. Text outside a passage takes the nearest element with an ID. Null when it has no words.
export function anchor(range) {
  const parts = chapterPassages().filter(item => range.intersectsNode(item.element))
    .flatMap(item => { const part = span(item.element, range); return part ? [{...part, item}] : []; });
  if (!parts.length) {
    const box = range.commonAncestorContainer, element = (box.nodeType === 1 ? box : box.parentElement).closest('[id]') || doc.body;
    const part = span(element, range);
    return part && {passage: null, href: element.id ? `${chapter}#${element.id}` : chapter, quote: words(part), head: null,
      prefix: before(part), suffix: after(part), section: null, end: null};
  }
  const first = parts[0], last = parts.at(-1), across = parts.length > 1;
  return {passage: first.item.id, href: first.item.href, quote: parts.map(words).join(' '), head: across ? words(first) : null,
    prefix: before(first), suffix: across ? '' : after(first), section: first.item.section ?? null,
    end: across ? {passage: last.item.id, href: last.item.href, quote: words(last), suffix: after(last)} : null};
}
// The anchor fields of a record, as anchor() makes them.
export const anchorOf = ({passage, href, quote, head, prefix, suffix, section, end}) => ({passage, href, quote, head, prefix, suffix, section, end});
// The anchor of a selection for Ask: words in a passage, at most 2,000 characters.
function askAbout(range) {
  const where = anchor(range);
  if (!where?.passage) notice('Select text in a paragraph of the Paper, then ask.', true);
  else if (where.quote.length > 2000) notice('Select at most 2,000 characters, then ask again.', true);
  else return {...where, whole: false};
  return null;
}
const firstSentence = element => {
  const text = oneText(element).text;
  return (text.match(/^.{20,200}?[.!?](?=\s|$)/s)?.[0] || text.slice(0, 120)).trim();
};
// A mark's words in the loaded chapter: its passage first, then the whole chapter. A record that the server found
// again with changed words has them in `match`. A question about the whole Paper marks the first sentence of its
// passage. A card whose words are gone shows at its passage.
function locate(mark) {
  const record = mark.record, [path, id] = hrefOf(record).split('#');
  if (!doc?.body || path !== chapter) return null;
  const passage = id ? doc.getElementById(id) : null;
  const quote = record.whole ? passage && firstSentence(passage) : record.match || record.quote;
  const find = root => root && findWords(root, quote, record.prefix, record.suffix, oneText(root));
  const found = record.end && !record.match ? across(record, passage) : quote ? find(passage) || find(doc.body) : null;
  return {found: Boolean(found), range: found?.range, formulas: found?.formulas || [], anchor: passage || doc.body};
}
// The words of a selection across passages: from its words at the end of the first passage to its words at the start
// of the last one.
function across(record, first) {
  const id = record.end.href?.split('#')[1], last = id && doc.getElementById(id);
  const head = first && findWords(first, record.head, record.prefix, '', oneText(first));
  const tail = last && findWords(last, record.end.quote, '', record.end.suffix, oneText(last));
  if (!head || !tail) return null;
  const range = doc.createRange();
  range.setStart(head.range.startContainer, head.range.startOffset); range.setEnd(tail.range.endContainer, tail.range.endOffset);
  return {range, formulas: [...range.commonAncestorContainer.querySelectorAll?.('math') || []].filter(math => range.intersectsNode(math))};
}
// The top and bottom of a card's words in the window, or of its passage when the words are gone.
function wordsBox(card) {
  const rects = card.words?.range ? [...card.words.range.getClientRects()] : [];
  const first = rects[0] || card.words?.anchor.getBoundingClientRect(), last = rects.at(-1) || first;
  if (!first) return null;
  const outer = frame().getBoundingClientRect().top;
  return {top: outer + first.top, bottom: outer + last.bottom};
}
// The active card stays at the top of the view while its words are not in the view: in another chapter, or out of the
// window after a citation or a scroll. When its words come back into the view, the card goes back to them.
function following(card) {
  if (card.id !== active) return false;
  const box = wordsBox(card);
  return !box || box.bottom <= viewTop() || box.top >= innerHeight;
}
// The words of each mark get a tint of its colour, and those of an open question also a dashed line. The CSS Custom
// Highlight API changes no DOM; WebKit paints no highlight inside MathML, so a formula gets a class from the reader
// stylesheet instead. It runs only when the marks change.
const PAINTS = [...Object.keys(COLOURS), 'open'], CLASSES = PAINTS.map(name => `lx-h-${name}`);
function paint() {
  if (!doc?.body) return;
  for (const math of doc.querySelectorAll(CLASSES.map(name => '.' + name).join())) math.classList.remove(...CLASSES);
  const ranges = Object.fromEntries(PAINTS.map(name => [name, []]));
  for (const mark of marks.values()) {
    mark.words = locate(mark);
    if (!mark.words?.range) continue;
    for (const name of mark.record.kept ? [mark.record.colour] : [mark.record.colour, 'open']) {
      ranges[name].push(mark.words.range);
      for (const math of mark.words.formulas) math.classList.add(`lx-h-${name}`);
    }
  }
  const win = doc.defaultView;
  if (!win.CSS?.highlights || !win.Highlight) return;
  for (const [name, list] of Object.entries(ranges)) win.CSS.highlights.set(`lx-${name}`, new win.Highlight(...list));
}

// ---- Highlights, and the card at a mark ----
// One click makes a Highlight with no Note, so it has no card and nothing else on screen moves. The client makes the
// ID, so the words paint before the server answers.
async function highlight(range, colour) {
  lastColour = colour;
  const record = {id: crypto.randomUUID().replaceAll('-', ''), colour, kept: true, whole: false, ...anchor(range)};
  if (!record.quote) return notice('Select words in the Paper first.', true);
  // The server takes a quote of at most 20,000 characters, in a request of at most 64 KiB.
  if (record.quote.length > 20000 || new Blob([JSON.stringify({highlight: record})]).size > 65536) return notice('Select less text to make a Highlight.', true);
  const mark = {id: record.id, record}, selection = range.startContainer.ownerDocument.getSelection();
  marks.set(mark.id, mark); paint();
  // The selection would cover the new colour.
  if (selection?.rangeCount) selection.collapseToEnd();
  try { ({highlight: mark.record} = await api(`${paperAPI(paperId)}/highlights/add`, {highlight: record})); }
  catch (error) { marks.delete(mark.id); paint(); notice(error.message); }
}
async function recolour(mark, colour) {
  lastColour = colour; closePop();
  if (mark.record.colour === colour) return;
  try { const {highlights: [record]} = await api(`${paperAPI(paperId)}/highlights/update`, {updates: [{id: mark.id, colour}]}); mark.record = {...mark.record, colour: record.colour}; }
  catch (error) { return notice(error.message); }
  paint(); layout();
}
// A click on painted words that leaves no selection opens a small card at the mark: the four colours and Delete. The
// browser removes a selection at such a click only after the click event, so the click itself tells: it does not move
// from where the pointer went down, it is not a double click, and Shift does not extend the selection with it. The
// mark is the one under the caret, or the one around a clicked formula, which has no caret position.
function clicked(event) {
  if (!mounted || !down || event.defaultPrevented || event.detail > 1 || event.shiftKey || event.target.closest?.('a, img')
    || Math.hypot(event.clientX - down[0], event.clientY - down[1]) > 3) return;
  const caret = doc.caretRangeFromPoint?.(event.clientX, event.clientY), math = event.target.closest?.('math');
  const mark = [...marks.values()].findLast(item => !item.draft && item.words?.range
    && (math ? item.words.formulas.includes(math) : caret && item.words.range.isPointInRange(caret.startContainer, caret.startOffset)));
  if (!mark) return;
  const line = [...mark.words.range.getClientRects()].find(rect => rect.top <= event.clientY && event.clientY <= rect.bottom);
  openPop(mark, {left: event.clientX, width: 0, top: line?.top ?? event.clientY, bottom: line?.bottom ?? event.clientY});
}
function openPop(mark, box) {
  if (!pop) pop = buttonBar('Highlight');
  fillBar(pop, [...Object.entries(COLOURS).map(([colour, name]) => ({ariaLabel: name, colour, action: () => recolour(mark, colour)})),
    {label: 'Delete', ariaLabel: 'Delete', action: () => { closePop(); remove(mark); }}]);
  for (const button of pop.querySelectorAll('.swatch')) button.setAttribute('aria-pressed', String(button.dataset.colour === mark.record.colour));
  // Focus stays in the Paper: Tab moves it to the card, as to the selection toolbar.
  placeBar(pop, box);
}
// Focus in the card goes back to the Paper.
function closePop() {
  if (!pop || pop.hidden) return;
  if (pop.contains(document.activeElement)) frame().contentWindow?.focus();
  pop.hidden = true;
}

// ---- Layout ----
// Sizes the reading column and the margin as one centred unit. Folded, the page keeps its own size.
function measure() {
  const main = $('main'), style = getComputedStyle(main), page = $('reader-page');
  const content = main.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
  // The page adds its padding (64 px, app.css) and the Paper frame's body padding (40 px, appearance.js) to the text.
  const room = content - MIN_TEXT * prefs.size - 64 - 40 - GAP * 3;
  folded = room < MIN_CARD;
  width = Math.min(MAX_CARD, room);
  if (folded) { page.style.maxWidth = page.style.marginLeft = page.style.marginRight = ''; return; }
  // The page's own maximum: the wide measure and its padding, as app.css sets it.
  const text = Math.min(wideMeasure(prefs) + 64, content - width - GAP * 3);
  page.style.maxWidth = text + 'px'; page.style.marginRight = '0';
  page.style.marginLeft = Math.max(GAP, (content - text - width - GAP) / 2) + 'px';
}
// Places each card at the height of its words, then pushes cards apart so that none overlap. The active card keeps its
// place at its words, and the cards above it move up. Folded, each card is a marker, and the active one opens beside
// its marker, under its words.
function layout() {
  if (!mounted) return;
  measure();
  const page = $('reader-page').getBoundingClientRect();
  margin.style.left = (folded ? page.right - 30 : page.right + GAP) + scrollX + 'px';
  margin.style.width = (folded ? MARKER : width) + 'px';
  const items = [...marks.values()].filter(card => hasCard(card) && (card.words || card.id === active)).map(card => {
    const box = wordsBox(card);
    return {card, y: box ? box.top + scrollY : null, bottom: box ? box.bottom + scrollY : null};
  }).sort((a, b) => (a.y ?? -1) - (b.y ?? -1));
  // The DOM order is the reading order, so Tab follows it. A card moves only when it is out of order.
  const elements = items.map(({card}) => card.element ||= build(card));
  for (const element of [...margin.children]) if (!elements.includes(element)) { element.remove(); observer.unobserve(element); }
  let at = margin.firstElementChild;
  for (const element of elements) {
    if (element === at) at = at.nextElementSibling; else margin.insertBefore(element, at);
    observer.observe(element);
  }
  for (const {card} of items) shape(card);
  const top = scrollY + margin.getBoundingClientRect().top, inset = viewTop();
  const heights = items.map(({card}) => folded && card.id !== active ? MARKER : card.element.offsetHeight);
  const tops = items.map(({y}) => (y ?? scrollY + inset) - top);
  const index = items.findIndex(({card}) => card.id === active);
  // An active card that follows the view (shape() sets the class) is at the top of the view, and it takes no place
  // among the others.
  const follow = index >= 0 && items[index].card.element.classList.contains('is-following');
  if (follow) tops[index] = scrollY + inset - top;
  else if (index >= 0 && folded) tops[index] = items[index].bottom - top + 8;
  if (index >= 0 && !folded && !follow) {
    for (let i = index + 1; i < items.length; i++) tops[i] = Math.max(tops[i], tops[i - 1] + heights[i - 1] + 8);
    for (let i = index - 1; i >= 0; i--) tops[i] = Math.min(tops[i], tops[i + 1] - heights[i] - 8);
  } else {
    let floor = -Infinity;
    items.forEach((item, i) => {
      if (i === index) return;
      tops[i] = Math.max(tops[i], floor); floor = tops[i] + heights[i] + (folded ? 6 : 8);
    });
  }
  items.forEach(({card}, i) => { card.element.style.top = tops[i] + 'px'; });
  line?.draw();
}
function shape(card) {
  const element = card.element, floating = folded && card.id === active;
  element.classList.toggle('is-marker', folded && !floating);
  element.classList.toggle('is-floating', floating);
  element.classList.toggle('is-active', card.id === active);
  // It follows the view as the reader scrolls, so it does not slide to each new place.
  element.classList.toggle('is-following', following(card));
  element.style.setProperty('--c', `var(--${card.record.colour})`);
  element.style.width = folded ? '' : width + 'px';
  element.title = folded && !floating ? 'Show the question' : '';
  drawCompose(card);
}

// ---- Selecting a card, and the line to its words ----
function select(card) {
  active = card.id;
  layout();
  connect(card);
}
function deselect() {
  if (!active) return;
  active = ''; clearLine(); dropDraft(); layout();
}
// A draft with no typed question, and no question that waits for a Chat model, goes away when the reader leaves it.
function dropDraft() {
  let dropped = false;
  for (const card of marks.values()) {
    if (card.draft && !card.pending && !card.waiting && !card.input?.value.trim() && card.id !== active) { marks.delete(card.id); card.element?.remove(); dropped = true; }
  }
  if (dropped) paint();
}
// A dotted line that moves along its length joins the card to its words, and the words pulse once. It is drawn again
// at a scroll, a resize, and a layout, not at each frame. With Reduce Motion the line does not move, and the outline
// stays on the words.
const SVG = 'http://www.w3.org/2000/svg';
let line = null;
function clearLine() {
  if (!line) return;
  line.svg.remove(); line = null;
}
function connect(card) {
  clearLine();
  if (!card.words?.range) return;
  const svg = document.createElementNS(SVG, 'svg'), path = document.createElementNS(SVG, 'path'), dot = document.createElementNS(SVG, 'circle');
  svg.setAttribute('class', 'lx-line'); svg.setAttribute('aria-hidden', 'true'); dot.setAttribute('r', '3.5');
  svg.style.setProperty('--c', `var(--${card.record.colour})`);
  const outlines = [...card.words.range.getClientRects()].map(() => document.createElementNS(SVG, 'rect'));
  svg.append(path, dot, ...outlines);
  document.body.append(svg);
  const draw = () => {
    const rects = card.words?.range ? [...card.words.range.getClientRects()] : [];
    if (!card.element?.isConnected || !rects.length) return clearLine();
    const outer = frame().getBoundingClientRect(), box = card.element.getBoundingClientRect(), first = rects[0], last = rects.at(-1);
    let x2, y2;
    if (card.element.classList.contains('is-floating')) {
      // The open card of a marker is under its words, so the line goes up to the end of their last line.
      x2 = outer.left + last.right; y2 = outer.top + last.bottom;
      const x1 = Math.min(box.right - 16, Math.max(box.left + 16, x2)), y1 = box.top, bend = Math.max(12, (y1 - y2) / 2);
      path.setAttribute('d', `M${x1},${y1} C${x1},${y1 - bend} ${x2},${y2 + bend} ${x2},${y2}`);
    } else {
      // The end of the words nearest the card: the end of their first line when the card is on the right.
      const right = box.left > outer.left + first.right;
      x2 = outer.left + (right ? first.right : first.left); y2 = outer.top + first.top + first.height / 2;
      const x1 = right ? box.left : box.right, y1 = Math.min(box.bottom - 12, Math.max(box.top + 12, y2));
      const bend = Math.max(30, Math.abs(x1 - x2) / 2) * (right ? -1 : 1);
      path.setAttribute('d', `M${x1},${y1} C${x1 + bend},${y1} ${x2 - bend},${y2} ${x2},${y2}`);
    }
    dot.setAttribute('cx', x2); dot.setAttribute('cy', y2);
    outlines.forEach((outline, i) => {
      const rect = rects[i] || rects[0];
      for (const [name, value] of [['x', outer.left + rect.left - 2], ['y', outer.top + rect.top - 1], ['width', rect.width + 4], ['height', rect.height + 2]]) outline.setAttribute(name, value);
    });
  };
  line = {svg, draw};
  draw();
}

// ---- Cards ----
// Opens a draft card at `where` and focuses its question field; with `question`, asks it at once. A `waiting`
// question goes into the field.
function openCard(where, question = '', waiting = '') {
  if (!where) return;
  const card = {id: `draft-${++drafts}`, draft: true, waiting, record: {id: '', paper: paperId, colour: 'question', kept: false, turns: [], ...where}};
  marks.set(card.id, card);
  active = card.id;
  dropDraft(); paint(); select(card);
  if (question) send(card, question); else card.input?.focus({preventScroll: true});
}
export function askPaper() {
  if (!mounted) return;
  const line = viewTop() - frame().getBoundingClientRect().top;
  const passage = chapterPassages().find(item => item.element.getBoundingClientRect().bottom > line);
  if (!passage) return notice('Open a chapter with text, then ask about the Paper.', true);
  openCard({passage: passage.id, href: passage.href, quote: '', whole: true});
}
function build(card) {
  const element = node('div', undefined, 'lx-card');
  element.tabIndex = 0; element.setAttribute('role', 'group');
  element.setAttribute('aria-label', card.record.whole ? 'Question about the Paper' : `Question about: ${card.record.quote.slice(0, 80)}`);
  const kind = node('p', card.record.whole ? 'Question about the Paper' : 'Question', 'lx-kind');
  card.lost = node('div', undefined, 'lx-lost');
  // The turns are a polite live region. A streaming answer is busy until it ends, so a screen reader reads it once.
  card.turns = node('div', undefined, 'lx-turns'); card.turns.setAttribute('aria-live', 'polite');
  card.compose = node('div'); card.actions = node('div', undefined, 'lx-actions');
  element.append(kind, card.lost, card.turns, card.compose, card.actions);
  element.onclick = event => { if (!event.target.closest('button, input, form, a')) select(card); };
  element.onkeydown = event => { if (event.target === element && ['Enter', ' '].includes(event.key)) { event.preventDefault(); select(card); } };
  card.element = element;
  drawTurns(card); drawActions(card);
  return element;
}
export function drawLost(card) {
  card.lost.replaceChildren();
  if (card.words?.found !== false) return;
  if (card.record.quote) card.lost.append(node('blockquote', card.record.quote, 'lx-quote'));
  card.lost.append(node('p', 'LocalXiv cannot find these words in this version of the Paper.', 'lx-note'));
}

// The stored card replaces the draft, or the card as the server has it now.
export function adopt(card, record) {
  if (card.draft) {
    marks.delete(card.id);
    if (active === card.id) active = record.id;
    card.id = record.id; card.draft = false; marks.set(card.id, card);
  }
  card.record = record;
  drawActions(card);
}
export async function keep(card) {
  try { const {highlights: [record]} = await api(`${paperAPI(paperId)}/highlights/update`, {updates: [{id: card.id, kept: true}]}); card.record = {...card.record, kept: record.kept}; }
  catch (error) { return notice(error.message); }
  drawActions(card); paint();
}
export async function remove(card) {
  // The server stores a question only with its answer. Thus ⌘Z brings a card that is discarded during an answer back
  // with the question in its field: a new card as a draft, and a card with turns as the server had it.
  const {whole, kept, turns} = card.record, question = card.pending?.question || '';
  if (!card.draft) {
    let removed;
    // The delete also stops the answer on the server, and the server does not save it.
    try { ({removed} = await api(`${paperAPI(paperId)}/highlights/delete`, {ids: [card.id]})); }
    catch (error) { return notice(error.message); }
    // The answer can end, and the server can save it, before the delete.
    const saved = removed.some(record => record.turns.length > turns.length);
    if (question && !saved && !turns.length) undo.push({paper: paperId, where: {...anchorOf(card.record), whole}, question});
    else if (removed.length) undo.push({paper: paperId, records: removed, question: saved ? '' : question});
    syncUndo();
    notice(`${kept && !turns.length ? 'Highlight' : 'Question'} removed. Press ⌘Z to undo.`, true);
  }
  card.controller?.abort(); marks.delete(card.id); card.element?.remove();
  if (card.element) observer?.unobserve(card.element);
  if (active === card.id) { active = ''; clearLine(); }
  paint(); layout();
}
async function restore() {
  const [entry] = undo.splice(undo.findLastIndex(item => item.paper === paperId), 1);
  syncUndo();
  if (entry.where) return openCard(entry.where, '', entry.question);
  try {
    const {highlights} = await api(`${paperAPI(paperId)}/highlights/restore`, {highlights: entry.records});
    // The question of an answer that Discard stopped waits for the field of its card.
    for (const record of highlights) if (!marks.has(record.id)) marks.set(record.id, {id: record.id, record, waiting: entry.records.some(item => item.id === record.id) && entry.question || ''});
  } catch (error) { undo.push(entry); syncUndo(); return notice(error.message); }
  paint(); layout();
}

// Goes to a card's words in the Paper view and selects the card there.
export function show(card) {
  const href = hrefOf(card.record);
  // A reimport can drop the chapter, and then no chapter load would select the card.
  if (!detail?.paper?.chapters?.some(item => item.path === href.split('#')[0])) return notice('This version of the Paper does not have the passage of this question.', true);
  wanted = card.id;
  goPassage(href);
  // A chapter that is already in the frame sends no lx-chapter event.
  if (mounted && href.split('#')[0] === chapter && doc === frame().contentDocument) { wanted = ''; select(card); }
}
