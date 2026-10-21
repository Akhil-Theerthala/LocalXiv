// Highlights, Note cards, and Question cards in the Paper view: the marks on the words, the card at a mark, Place
// Again, the layout of the reading column and the margin, the shell of each card, the line from a card to its words,
// and Ask About the Paper. chat.js has the questions of a card and their stream, and notes.js has the Note editor and
// All Notes. reader.js, app.js, chat.js, and notes.js import this module, and this module imports reader.js, app.js,
// chat.js, and notes.js. Its top level only defines functions and adds listeners, so no module reads another's
// bindings before all have run.
import {node} from './render.js';
import {native, chrome, register} from './shell.js';
import {wideMeasure} from './appearance.js';
import {selectionToolbar, toolbarShown, liveRange, buttonBar, fillBar, placeBar} from './selection.js';
import {textMap, findWords} from './onetext.js';
import {api, paperAPI, notice, prefs} from './app.js';
import {goPassage, selected, detail, syncReaderChrome, closePreview} from './reader.js';
import {drawTurns, drawActions, drawCompose, send, openAsk} from './chat.js';
import {drawNote, editNote, flushNotes, drawAllNotes} from './notes.js';

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

// The marks: every record of the Paper, as {id, record, draft, pending, controller, element, words, editor}. A mark
// with words is painted and hit-tested. A draft has no question yet, so the server does not have it; its first
// question stores it.
export const marks = new Map();
// The marks with a card: the active mark, a Question card (open, with turns, with an answer that runs or failed, or
// with its question field open), a Note or its open editor, and a Highlight whose words changed. A Highlight with no
// Note is a mark only. A card shows in the margin only when its words are in the loaded chapter (locate).
export const hasCard = mark => mark.id === active || !mark.record.kept || mark.record.turns.length > 0
  || Boolean(mark.pending || mark.error || mark.asking || mark.editor || mark.record.note) || mark.record.found === 'moved';
// A Paper note has no words and no passage. All Notes shows it, and the margin does not.
export const paperNote = record => !record.quote && !record.passage;
// What Discard and Delete removed in this session, for ⌘Z, each with its Paper: {paper, records, question} as the
// server had them, with the question of a follow-up that was discarded during its answer, or {paper, where, question}
// for a new card that was discarded during its first answer. ⌘Z restores the last entry of the selected Paper. The
// Native shell's Edit › Undo sends 'undo' while canUndo is true, which is only in the Paper view. All Notes opens in
// every view, and ⌘Z restores a record that it deleted.
const undo = [];
const undoable = () => (mounted || Boolean(document.querySelector('dialog.all-notes[open]'))) && selected === paperId
  && undo.some(entry => entry.paper === paperId);
export const syncUndo = () => chrome.update({canUndo: undoable()});
export let paperId = null;
// The colour of the last Highlight that the reader made or changed.
export let lastColour = 'key';
// `down` is where the pointer last went down in the Paper. `placing` is the mark that Place Again waits to place, and
// `quoting` the card whose Add Quote waits for a selection.
let mounted = false, margin = null, toolbar = null, observer = null, doc = null, chapter = '', docPaper = null, pop = null, down = null;
let folded = false, width = MAX_CARD, active = '', wanted = '', drafts = 0, scheduled = 0, placing = null, quoting = null;
// The one text of each element of the loaded chapter. A chapter load clears it.
let texts = new WeakMap();
const oneText = element => texts.get(element) || texts.set(element, textMap(element)).get(element);
// The Export EPUB with Notes and Copy Notes actions depend on the records, so the offer and the Chrome state follow
// them.
const syncRecords = () => { drawOffer(); if (mounted) syncReaderChrome(); };

// ---- Mount ----
export function mountMargin() {
  if (selected !== paperId) reset();
  if (!mounted) {
    mounted = true;
    if (!margin) {
      margin = node('div', undefined, 'lx-margin');
      margin.setAttribute('role', 'complementary'); margin.setAttribute('aria-label', 'Notes');
    }
    document.body.append(margin);
    toolbar ||= selectionToolbar(tools());
    observer ||= new ResizeObserver(schedule);
    // The frame resizes with Reading preferences and chapters, and main with the web sidebar.
    observer.observe(frame()); observer.observe($('main'));
    for (const card of marks.values()) if (card.element) observer.observe(card.element);
  }
  paint(); layout(); drawOffer(); syncUndo();
}
export function unmountMargin() {
  if (!mounted) return;
  mounted = false;
  // A key such as ⌘[ can leave the Paper view with focus in a Note editor, and then no blur saves it.
  flushNotes();
  if (placing) placeAgain(null);
  if (quoting) addQuote(null);
  observer.disconnect(); margin.remove(); toolbar.hide(); closePop(); clearLine(); drawOffer(); syncUndo();
  active = ''; dropDraft();
  const page = $('reader-page');
  page.style.maxWidth = page.style.marginLeft = page.style.marginRight = '';
}
// The Chat settings can change in Settings or in the Settings window, so each Chrome state sync redraws the question
// fields. A field redraws only when what it shows changes.
export function syncCards() {
  if (mounted) for (const card of marks.values()) drawCompose(card);
}
// An answer of the Paper that the reader leaves runs on, because the server saves it only while its stream is open
// (chat.js send).
export function reset() {
  if (placing) placeAgain(null);
  if (quoting) addQuote(null);
  flushNotes();
  marks.clear(); margin?.replaceChildren(); offer = null; clearLine(); closePop();
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
  // While Add Quote waits, the card keeps its place and its draft.
  doc.addEventListener('pointerdown', event => { down = [event.clientX, event.clientY]; closePop(); if (!quoting) deselect(); });
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
    // The cards under the following card move out from under it at the next frame.
    if (follow) { card.element.style.top = viewTop() - margin.getBoundingClientRect().top + 'px'; schedule(); }
  }
  if (offer) offer.style.top = viewTop() - margin.getBoundingClientRect().top + 'px';
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
  if (event.key === 'Escape' && !document.querySelector('dialog[open]') && closePreview()) event.preventDefault();
  else if (event.key === 'Escape' && pop && !pop.hidden) { event.preventDefault(); closePop(); }
  else if (event.key === 'Escape' && placing && !document.querySelector('dialog[open]')) { event.preventDefault(); placeAgain(null); toolbar.hide(); }
  else if (event.key === 'Escape' && quoting && !document.querySelector('dialog[open]')) { event.preventDefault(); addQuote(null); toolbar.hide(); }
  else if (event.key === 'Escape' && active && !document.querySelector('dialog[open]')) { event.preventDefault(); deselect(); }
  else if (event.key === 'Escape' && toolbarShown() && !document.querySelector('dialog[open]')) { event.preventDefault(); toolbar.hide(); }
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
// passage. A card whose words are gone shows at its passage. A Not found record has no words, as a record outside
// a passage has when its words are not at its `href`: it has no paint and no margin card.
function locate(mark) {
  const record = mark.record, [path, id] = hrefOf(record).split('#');
  if (!doc?.body || path !== chapter || record.found === 'not-found') return null;
  const passage = id ? doc.getElementById(id) : null;
  const quote = record.whole ? passage && firstSentence(passage) : record.match || record.quote;
  const find = root => root && findWords(root, quote, record.prefix, record.suffix, oneText(root));
  // The server's `match` of a selection across passages joins words that are not next to each other in the page, so
  // such a record shows at its first passage, with no paint, until the reader places it again.
  const found = record.end ? !record.match && across(record, passage) : quote ? find(passage) || find(doc.body) : null;
  if (!found && !record.passage) return null;
  return {found: Boolean(found), range: found?.range, formulas: found?.formulas || [], anchor: passage || doc.body};
}
// Not found: the server's search did not find the words in this version, or a record outside a passage has no words at
// its `href` in the loaded chapter. All Notes marks it.
// shortcut: a record outside a passage shows as Not found only while its chapter is loaded; the reimport search on the
// server would have to find such records to mark them in every chapter.
export const notFound = mark => mark.record.found === 'not-found' || !mark.record.passage && !paperNote(mark.record)
  && Boolean(doc?.body) && hrefOf(mark.record).split('#')[0] === chapter && !locate(mark);
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

// ---- Highlights, the card at a mark, and Place Again ----
// The selection commands of the Paper menu and the context menu. The toolbar has the last three.
const SELECTION = {
  highlight: range => highlight(range, lastColour),
  'add-note': range => { const mark = highlight(range, lastColour); if (mark) editNote(mark); },
  ask: range => openCard(askAbout(range)),
  explain: range => openCard(askAbout(range), EXPLAIN),
};
// The selection toolbar: the four colours, Note, Ask, and Explain. While Place Again waits, Place Here and Cancel, and
// while Add Quote waits, Add to Question and Cancel.
const tools = () => placing ? [
  {label: 'Place Here', ariaLabel: 'Place the Highlight on the selected text', action: placeHere},
  {label: 'Cancel', ariaLabel: 'Cancel Place Again', action: () => placeAgain(null)}] : quoting ? [
  {label: 'Add to Question', ariaLabel: 'Add the selected text to the question', action: addToQuestion},
  {label: 'Cancel', ariaLabel: 'Cancel Add Quote', action: () => addQuote(null)}] : [
  ...Object.entries(COLOURS).map(([colour, name]) => ({ariaLabel: `Highlight in ${name}`, colour, action: range => highlight(range, colour)})),
  {label: 'Note', ariaLabel: 'Add a Note to the selected text', action: SELECTION['add-note']},
  {label: 'Ask', ariaLabel: 'Ask about the selected text', action: SELECTION.ask},
  {label: 'Explain', ariaLabel: 'Explain the selected text', action: SELECTION.explain}];
// The Paper menu, its keys, and the context menu run a selection command on the live selection in the Paper. As in the
// Native shell's menu, the commands are off while a text field has the focus. A modal dialog holds the page.
export function selectionCommand(id) {
  if (chrome.state.editing || document.querySelector('dialog[open]')) return;
  const range = mounted && liveRange();
  if (!range) return notice('Select words in the Paper first.', true);
  toolbar.act(SELECTION[id], range);
}
// The server takes a quote of at most 20,000 characters, in a request of at most 64 KiB.
const tooLarge = (quote, body) => quote.length > 20000 || new Blob([JSON.stringify(body)]).size > 65536;
// One click makes a Highlight with no Note, so it has no card and nothing else on screen moves. The client makes the
// ID, so the words paint before the server answers. Returns the new mark.
function highlight(range, colour) {
  lastColour = colour;
  const record = {id: crypto.randomUUID().replaceAll('-', ''), colour, kept: true, whole: false, turns: [], ...anchor(range)};
  if (!record.quote) return notice('Select words in the Paper first.', true);
  if (tooLarge(record.quote, {highlight: record})) return notice('Select less text to make a Highlight.', true);
  const mark = {id: record.id, record}, selection = range.startContainer.ownerDocument.getSelection();
  marks.set(mark.id, mark); paint(); syncRecords();
  // The selection would cover the new colour.
  if (selection?.rangeCount) selection.collapseToEnd();
  // `adding` stays the request, so that a wait on it fails when the add fails.
  mark.adding = api(`${paperAPI(paperId)}/highlights/add`, {highlight: record});
  mark.adding.then(({highlight: stored}) => { mark.record = stored; }, error => {
    mark.adding = null;
    if (!mark.editor) { drop(mark); return notice(error.message); }
    // A Note that the reader writes keeps its card, and its Save adds the Highlight again (notes.js).
    mark.unsaved = true;
    Object.assign(mark.editor.querySelector('.lx-error'), {textContent: error.message, hidden: false});
  });
  return mark;
}
// Removes a mark that the server does not have.
export function drop(mark) {
  marks.delete(mark.id);
  if (active === mark.id) { active = ''; clearLine(); }
  paint(); schedule(); syncRecords();
}
export async function recolour(mark, colour) {
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
  fillBar(pop, [...Object.entries(COLOURS).map(([colour, name]) => ({ariaLabel: `Highlight in ${name}`, colour, action: () => recolour(mark, colour)})),
    {label: 'Note', ariaLabel: mark.record.note ? 'Edit the Note' : 'Add a Note', action: () => { closePop(); editNote(mark); }},
    {label: 'Ask', ariaLabel: 'Ask about these words', action: () => { closePop(); openAsk(mark); }},
    {label: 'Delete', ariaLabel: 'Delete Highlight', action: () => { closePop(); remove(mark); }}]);
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
// Place Again waits for the next selection, and its toolbar then places the mark on the selected words. Null cancels.
export function placeAgain(mark) {
  placing = mark;
  if (toolbar) selectionToolbar(tools());
  if (mark) notice('Select the words in the Paper, then choose Place Here. Press Escape to cancel.', true);
}
async function placeHere(range) {
  const mark = placing, where = anchor(range), body = {updates: [{id: mark.id, anchor: where}]};
  if (!where?.quote) return notice('Select words in the Paper first.', true);
  if (tooLarge(where.quote, body)) return notice('Select less text to make a Highlight.', true);
  const selection = range.startContainer.ownerDocument.getSelection();
  try { const {highlights: [record]} = await api(`${paperAPI(paperId)}/highlights/update`, body); mark.record = {...mark.record, ...anchorOf(record), found: record.found, match: record.match}; }
  catch (error) { return notice(error.message); }
  if (placing === mark) placeAgain(null);
  if (marks.get(mark.id) !== mark) return;
  if (selection?.rangeCount) selection.collapseToEnd();
  paint(); select(mark);
  if (mark.element) drawActions(mark);
}
// Add Quote waits for the next selection, and its toolbar then adds the selected words to the next question of the
// card. Null cancels.
export function addQuote(card) {
  quoting = card;
  if (toolbar) selectionToolbar(tools());
  if (card) { select(card); notice('Select the words in the Paper, then choose Add to Question. Press Escape to cancel.', true); }
}
function addToQuestion(range) {
  const card = quoting, where = anchor(range);
  if (!where?.quote) return notice('Select words in the Paper first.', true);
  if (where.quote.length > 2000) return notice('Add at most 4 quotes of at most 2,000 characters each.', true);
  addQuote(null);
  if (marks.get(card.id) !== card) return;
  (card.quotes ||= []).push({passage: where.passage || '', href: where.href || '', quote: where.quote});
  const selection = range.startContainer.ownerDocument.getSelection();
  if (selection?.rangeCount) selection.collapseToEnd();
  drawCompose(card); select(card);
  card.input?.focus({preventScroll: true});
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
  for (const element of [...margin.children]) if (!elements.includes(element) && element !== offer) { element.remove(); observer.unobserve(element); }
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
    // A following card is at the top of the view, and the cards there go under it, as any card pushes the next one.
    const band = follow && !folded ? [tops[index], tops[index] + heights[index] + 8] : null;
    let floor = -Infinity;
    items.forEach((item, i) => {
      if (i === index) return;
      let y = Math.max(tops[i], floor);
      if (band && y < band[1] && y + heights[i] + 8 > band[0]) y = band[1];
      tops[i] = y; floor = y + heights[i] + (folded ? 6 : 8);
    });
  }
  items.forEach(({card}, i) => { card.element.style.top = tops[i] + 'px'; });
  if (offer) offer.style.top = scrollY + inset - top + 'px';
  line?.draw();
}
function shape(card) {
  const element = card.element, floating = folded && card.id === active;
  element.classList.toggle('is-marker', folded && !floating);
  element.classList.toggle('is-floating', floating);
  element.classList.toggle('is-active', card.id === active);
  // It follows the view as the reader scrolls.
  element.classList.toggle('is-following', following(card));
  element.style.setProperty('--c', `var(--${card.record.colour})`);
  element.style.width = folded ? '' : width + 'px';
  element.title = folded && !floating ? card.record.kept ? 'Show the Note' : 'Show the question' : '';
  // The kind names the colour, and so does the label: an open question is a Question until the reader keeps it.
  const {whole, kept, colour} = card.record, name = whole ? 'Question about the Paper' : kept ? COLOURS[colour] : 'Question';
  if (card.kind.textContent !== name) card.kind.textContent = name;
  element.setAttribute('aria-label', recordLabel(card.record));
  drawLost(card); drawCompose(card);
}
// The name of a card and of its row in All Notes, with its colour name and its first words.
export const recordLabel = ({whole, kept, colour, quote}) => whole ? 'Question about the Paper'
  : `${kept ? `${COLOURS[colour]} Highlight` : 'Question about'}: ${quote.slice(0, 80)}`;

// ---- Selecting a card, and the line to its words ----
export function select(card) {
  active = card.id;
  layout();
  connect(card);
}
function deselect() {
  if (!active) return;
  // An Ask field with no typed question closes when the reader leaves its card.
  const card = marks.get(active);
  if (card?.asking && !card.input?.value.trim()) { card.asking = false; drawActions(card); }
  active = ''; clearLine(); dropDraft(); layout();
}
// A draft with no typed question, no added quote, and no question that waits for a Chat model, goes away when the
// reader leaves it.
function dropDraft() {
  let dropped = false;
  for (const card of marks.values()) {
    if (card.draft && !card.pending && !card.waiting && !card.input?.value.trim() && !card.quotes?.length && card.id !== active) {
      if (quoting === card) addQuote(null);
      marks.delete(card.id); card.element?.remove(); dropped = true;
    }
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
// A card: the kind, the quote and what changed in its words, the Note, the turns, the question field, and the
// actions. shape() names the kind and the card.
function build(card) {
  const element = node('div', undefined, 'lx-card');
  element.tabIndex = 0; element.setAttribute('role', 'group');
  card.kind = node('p', '', 'lx-kind');
  card.lost = node('div', undefined, 'lx-lost');
  // During an edit in All Notes, the editor is in its row, and the card's box waits as `home` (notes.js).
  const note = node('div');
  if ('home' in card) card.home = note; else card.note = note;
  // The turns are a polite live region. A streaming answer is busy until it ends, so a screen reader reads it once.
  card.turns = node('div', undefined, 'lx-turns'); card.turns.setAttribute('aria-live', 'polite');
  card.compose = node('div'); card.actions = node('div', undefined, 'lx-actions');
  element.append(card.kind, card.lost, note, card.turns, card.compose, card.actions);
  element.onclick = event => { if (!event.target.closest('button, input, textarea, form, a')) select(card); };
  element.onkeydown = event => { if (event.target === element && ['Enter', ' '].includes(event.key)) { event.preventDefault(); select(card); } };
  card.element = element;
  drawNote(card); drawTurns(card); drawActions(card);
  return element;
}
// A kept card shows its quote, as does an open question whose words are gone. A record that the server found again
// with changed words says so, and the reader can place it again.
export function drawLost(card) {
  const {kept, whole, quote, found} = card.record, moved = found === 'moved', gone = !moved && card.words?.found === false;
  const shown = (kept || gone) && !whole && quote, line = moved ? 'The words changed in this version.' : gone ? 'LocalXiv cannot find these words in this version of the Paper.' : '';
  const signature = JSON.stringify([shown, line]);
  if (card.lostDrawn === signature) return;
  card.lostDrawn = signature;
  card.lost.replaceChildren(...shown ? [node('blockquote', shown, 'lx-quote')] : [], ...line ? [node('p', line, 'lx-note')] : []);
}

// The stored card replaces the draft, or the card as the server has it now.
export function adopt(card, record) {
  if (card.draft) {
    marks.delete(card.id);
    if (active === card.id) active = record.id;
    card.id = record.id; card.draft = false; marks.set(card.id, card); syncRecords();
  }
  card.record = record;
  drawActions(card);
}
export async function keep(card) {
  try { const {highlights: [record]} = await api(`${paperAPI(paperId)}/highlights/update`, {updates: [{id: card.id, kept: true}]}); card.record = {...card.record, kept: record.kept}; }
  catch (error) { return notice(error.message); }
  drawActions(card); paint(); schedule();
}
export async function remove(card) {
  const paper = paperId;
  // A new Highlight goes only after the server stores it, or the store would bring it back. A failed store removes it.
  if (card.adding) try { await card.adding; } catch { return; }
  // The server stores a question only with its answer. Thus ⌘Z brings a card that is discarded during an answer back
  // with the question in its field: a new card as a draft, and a card with turns as the server had it.
  const {whole, kept, turns, note} = card.record, question = card.pending?.question || '';
  if (!card.draft && !card.unsaved) {
    let removed;
    // The delete also stops the answer on the server, and the server does not save it.
    try { ({removed} = await api(`${paperAPI(paper)}/highlights/delete`, {ids: [card.id]})); }
    catch (error) { return notice(error.message); }
    // The answer can end, and the server can save it, before the delete.
    const saved = removed.some(record => record.turns.length > turns.length);
    if (question && !saved && !turns.length) undo.push({paper, where: {...anchorOf(card.record), whole}, question});
    else if (removed.length) undo.push({paper, records: removed, question: saved ? '' : question});
    syncUndo();
    notice(`${!kept || turns.length ? 'Question' : note ? 'Note' : 'Highlight'} removed. Press ⌘Z to undo.`, true);
  }
  if (placing === card) placeAgain(null);
  if (quoting === card) addQuote(null);
  card.editor = null; card.controller?.abort(); marks.delete(card.id); card.element?.remove();
  if (card.element) observer?.unobserve(card.element);
  if (active === card.id) { active = ''; clearLine(); }
  paint(); layout(); syncRecords();
}
async function restore() {
  const [entry] = undo.splice(undo.findLastIndex(item => item.paper === paperId), 1);
  syncUndo();
  if (entry.where) return openCard(entry.where, '', entry.question);
  // After Clear Chat, a record that still exists keeps its fields as they are now, and the turns it got since the clear
  // come after the ones it gets back.
  const records = entry.clear ? entry.records.map(record => {
    const current = marks.get(record.id)?.record;
    return current ? {...current, turns: [...record.turns, ...current.turns]} : record;
  }) : entry.records;
  try {
    const {highlights} = await api(`${paperAPI(paperId)}/highlights/restore`, {highlights: records});
    for (const record of highlights) {
      const mark = marks.get(record.id);
      // The question of an answer that Discard or Clear Chat stopped goes back to the field of its card.
      const question = entry.questions?.[record.id] || entry.records.some(item => item.id === record.id) && entry.question || '';
      if (mark) {
        mark.record = record;
        // The turns that come back go before the ones the card has, so the box is drawn again from the start.
        if (mark.element) { mark.turns.replaceChildren(); drawTurns(mark); drawActions(mark); drawCompose(mark); }
        if (question && mark.input && !mark.input.value) mark.input.value = question;
      } else marks.set(record.id, {id: record.id, record, waiting: question});
    }
  } catch (error) { undo.push(entry); syncUndo(); return notice(error.message); }
  paint(); layout(); drawAllNotes(); syncRecords();
}
// Clear Chat removes each open Question card and the turns of each kept record. Every Highlight, Note, and colour
// stays. ⌘Z brings the turns and the removed cards back.
export async function clearChat() {
  const paper = paperId;
  let removed;
  try { ({removed} = await api(`${paperAPI(paper)}/chat/clear`, {})); }
  catch (error) { return notice(error.message); }
  if (!removed.length) return notice('This Paper has no Chat questions.', true);
  const entry = {paper, records: removed, question: '', questions: {}, clear: true};
  undo.push(entry); syncUndo();
  if (paper !== paperId) return;
  // The server stopped the answers that ran and does not save them, so their streams end here with no turn. ⌘Z puts
  // each question back in its field.
  for (const card of marks.values()) {
    if (!card.pending) continue;
    entry.questions[card.id] = card.pending.question; card.pending = null; card.controller?.abort();
    if (card.element) { drawTurns(card); drawCompose(card); }
  }
  for (const record of removed) {
    const card = marks.get(record.id);
    if (!card) continue;
    if (record.kept) { card.record = {...card.record, turns: []}; if (card.element) { drawTurns(card); drawActions(card); drawCompose(card); } }
    else {
      if (quoting === card) addQuote(null);
      card.editor = null; marks.delete(card.id);
      if (active === card.id) { active = ''; clearLine(); }
    }
  }
  paint(); layout(); drawAllNotes(); syncRecords();
  notice('Chat cleared. Press ⌘Z to undo.', true);
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

// ---- The offer to copy the Highlights and Notes of another version of the Paper ----
// The version with the most records, when the Paper has none of its own. Not Now hides the card for this page session;
// the Paper menu's Copy Notes stays.
const dismissed = new Set();
let offer = null;
export const versionOf = id => id.match(/v(\d+)$/)?.[1] || id;
export const offerVersion = () => (detail?.versions || []).filter(version => version.highlights > 0)
  .sort((a, b) => b.highlights - a.highlights)[0] || null;
function drawOffer() {
  const from = offerVersion();
  if (!mounted || !from || dismissed.has(paperId) || [...marks.values()].some(mark => !mark.draft)) { offer?.remove(); offer = null; return; }
  if (offer) return;
  offer = node('div', undefined, 'lx-card lx-offer');
  offer.setAttribute('role', 'group'); offer.setAttribute('aria-label', 'Copy the Highlights and Notes of another version');
  const text = node('p', `LocalXiv has ${from.highlights} Highlights and Notes on version ${versionOf(from.id)} of this Paper. Copy them to this version?`);
  const actions = node('div', undefined, 'lx-actions'), copy = node('button', 'Copy', 'btn-accent'), later = node('button', 'Not Now', 'btn-quiet');
  copy.type = later.type = 'button';
  copy.onclick = () => copyNotes();
  later.onclick = () => { dismissed.add(paperId); syncRecords(); };
  actions.append(copy, later); offer.append(text, actions);
  margin.prepend(offer); layout();
}
// Copies the records, which the server searches in this version, then shows them.
export async function copyNotes() {
  const from = offerVersion(), paper = paperId;
  if (!from || !paper) return;
  try {
    const result = await api(`${paperAPI(paper)}/highlights/copy`, {from: from.id});
    const {highlights} = await api(paperAPI(paper));
    // The reader can open another Paper while the copy runs; its records are not this Paper's.
    if (paperId !== paper || selected !== paper) return;
    detail.highlights.splice(0, detail.highlights.length, ...highlights);
    for (const record of highlights) if (!marks.has(record.id)) marks.set(record.id, {id: record.id, record});
    paint(); layout(); syncRecords();
    notice(`Copied ${result.copied}. ${result.found} found, ${result.moved} moved, ${result.not_found} not found.`, true);
  } catch (error) { notice(error.message); }
}
