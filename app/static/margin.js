// Question cards in the margin of the Paper view: the layout of the reading column and the margin, the cards with
// their streamed answers, the line from a card to its words, All Notes, and Ask About the Paper.
// reader.js and app.js import this module and this module imports them. Its top level only defines functions and
// adds listeners, so no module reads another's bindings before all have run.
import {node, renderProse} from './render.js';
import {native} from './shell.js';
import {wideMeasure} from './appearance.js';
import {selectionToolbar, rangeText, textMap, findWords} from './selection.js';
import {api, paperAPI, fileURL, notice, openSettings, aiReady, state, prefs, token} from './app.js';
import {goPassage, renderMath, selected, detail} from './reader.js';

const $ = id => document.getElementById(id);
const frame = () => $('paper-frame');
// The reading column keeps at least 520 px, and the margin takes up to 300 px. With less than 210 px for the
// margin, cards fold to markers in the page's right padding.
const GAP = 24, MIN_TEXT = 520, MAX_CARD = 300, MIN_CARD = 210, MARKER = 20;
const EXPLAIN = 'Explain this passage.';
const PROVIDERS = {'api.anthropic.com': 'Anthropic', 'api.openai.com': 'OpenAI', 'openrouter.ai': 'OpenRouter',
  'api.deepseek.com': 'DeepSeek', 'generativelanguage.googleapis.com': 'Google'};
const loopback = host => /^(127\.|localhost$|\[?::1\]?$)/.test(host || '');

// Each card: {id, record, draft, pending, controller, element, words}. A draft has no question yet, so the server
// does not have it; its first question stores it.
const cards = new Map();
// What Discard and Delete removed in this session, for ⌘Z.
const undo = [];
let paperId = null, mounted = false, margin = null, toolbar = null, observer = null, doc = null, chapter = '';
let folded = false, width = MAX_CARD, active = '', wanted = '', drafts = 0, scheduled = 0;

// ---- Mount ----
export function mountMargin() {
  if (selected !== paperId) reset();
  if (!mounted) {
    mounted = true;
    if (!margin) {
      margin = node('div', undefined, 'lx-margin');
      margin.setAttribute('role', 'complementary'); margin.setAttribute('aria-label', 'Question cards');
    }
    document.body.append(margin);
    toolbar ||= selectionToolbar({ask: range => openCard(fromRange(range)), explain: range => openCard(fromRange(range), EXPLAIN)});
    observer ||= new ResizeObserver(schedule);
    // The frame resizes with Reading preferences and chapters, and main with the web sidebar.
    observer.observe(frame()); observer.observe($('main'));
    for (const card of cards.values()) if (card.element) observer.observe(card.element);
  }
  paint(); layout();
}
export function unmountMargin() {
  if (!mounted) return;
  mounted = false;
  observer.disconnect(); margin.remove(); toolbar.hide(); clearLine();
  active = ''; dropDraft();
  const page = $('reader-page');
  page.style.maxWidth = page.style.marginLeft = page.style.marginRight = '';
}
// The Chat settings can change in Settings or in the Settings window, so each Chrome state sync redraws the question
// fields. A field redraws only when what it shows changes.
export function syncCards() {
  if (mounted) for (const card of cards.values()) drawCompose(card);
}
function reset() {
  for (const card of cards.values()) card.controller?.abort();
  cards.clear(); undo.length = 0; margin?.replaceChildren(); clearLine();
  paperId = selected; active = wanted = ''; doc = null; chapter = '';
  for (const record of detail?.chat || []) cards.set(record.id, {id: record.id, record});
}
function schedule() {
  if (!scheduled) scheduled = requestAnimationFrame(() => { scheduled = 0; layout(); });
}
addEventListener('lx-chapter', event => {
  ({doc, path: chapter} = event.detail);
  doc.addEventListener('keydown', keys);
  doc.addEventListener('pointerdown', () => deselect());
  if (!mounted) return;
  paint(); layout();
  const card = cards.get(wanted);
  wanted = '';
  if (card) select(card);
});
addEventListener('resize', () => { if (mounted) layout(); });
addEventListener('scroll', () => { if (mounted && active) schedule(); }, {passive: true});
document.addEventListener('pointerdown', event => {
  if (!event.target.closest?.('.lx-card, .selbar, .menu, dialog')) deselect();
});
document.addEventListener('keydown', keys);
function keys(event) {
  const editing = event.target.closest?.('input, textarea, select, [contenteditable]');
  if (event.key === 'Escape' && active && !document.querySelector('dialog[open]')) { event.preventDefault(); deselect(); }
  else if ((event.metaKey || event.ctrlKey) && !event.shiftKey && event.key.toLowerCase() === 'z' && !editing && undo.length && selected === paperId) {
    event.preventDefault(); restore();
  }
}

// ---- Where a card's words are ----
const hrefOf = record => record.href || detail?.paper?.passages?.find(item => item.id === record.passage)?.href || '';
// The passages of the loaded chapter, with their elements, in reading order.
function chapterPassages() {
  if (!doc) return [];
  return (detail?.paper?.passages || []).flatMap(item => {
    const [path, id] = item.href.split('#'), element = path === chapter && id && doc.getElementById(id);
    return element ? [{...item, element}] : [];
  });
}
// The Ask target of a selection: its first passage and its words in the one text.
function fromRange(range) {
  const passages = chapterPassages(), start = range.startContainer;
  const passage = passages.find(item => item.element.contains(start)) || passages.find(item => range.intersectsNode(item.element));
  const quote = passage && rangeText(passage.element.contains(range.endContainer) ? passage.element : doc.body, range);
  if (!quote) { notice('Select text in a paragraph of the Paper, then ask.', true); return null; }
  if (quote.length > 2000) { notice('Select at most 2,000 characters, then ask again.', true); return null; }
  return {passage: passage.id, href: passage.href, quote, whole: false};
}
const firstSentence = element => {
  const text = textMap(element).text;
  return (text.match(/^.{20,200}?[.!?](?=\s|$)/s)?.[0] || text.slice(0, 120)).trim();
};
// The card's words in the loaded chapter: its passage first, then the whole chapter. A question about the whole
// Paper marks the first sentence of its passage. A card whose words are gone shows at its passage.
function locate(card) {
  const [path, id] = hrefOf(card.record).split('#');
  if (!doc?.body || path !== chapter) return null;
  const passage = id ? doc.getElementById(id) : null;
  const quote = card.record.whole ? passage && firstSentence(passage) : card.record.quote;
  const found = quote ? passage && findWords(passage, quote) || findWords(doc.body, quote) : null;
  return {found: Boolean(found), range: found?.range, formulas: found?.formulas || [], anchor: passage || doc.body};
}
// The words of open questions get a dashed mark, and kept ones a tint. The CSS Custom Highlight API changes no
// DOM; WebKit paints no highlight inside MathML, so a formula gets a class from the reader stylesheet instead.
function paint() {
  if (!doc?.body) return;
  for (const math of doc.querySelectorAll('.lx-q-open, .lx-q-kept')) math.classList.remove('lx-q-open', 'lx-q-kept');
  const ranges = {open: [], kept: []};
  for (const card of cards.values()) {
    card.words = locate(card);
    if (!card.words?.range) continue;
    const kind = card.record.kept ? 'kept' : 'open';
    ranges[kind].push(card.words.range);
    for (const math of card.words.formulas) math.classList.add(`lx-q-${kind}`);
  }
  const win = doc.defaultView;
  if (!win.CSS?.highlights || !win.Highlight) return;
  for (const [kind, list] of Object.entries(ranges)) win.CSS.highlights.set(`lx-${kind}`, new win.Highlight(...list));
}

// ---- Layout ----
// Sizes the reading column and the margin as one centred unit. Folded, the page keeps its own size.
function measure() {
  const main = $('main'), style = getComputedStyle(main), page = $('reader-page');
  const content = main.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
  const room = content - MIN_TEXT - GAP * 3;
  folded = room < MIN_CARD;
  width = Math.min(MAX_CARD, room);
  if (folded) { page.style.maxWidth = page.style.marginLeft = page.style.marginRight = ''; return; }
  // The page's own maximum: the wide measure and its padding, as app.css sets it.
  const text = Math.min(wideMeasure(prefs) + 64, content - width - GAP * 3);
  page.style.maxWidth = text + 'px'; page.style.marginRight = '0';
  page.style.marginLeft = Math.max(GAP, (content - text - width - GAP) / 2) + 'px';
}
// Places each card at the height of its words, then pushes cards apart so that none overlap. The active card keeps its
// place at its words, and the cards above it move up. When its words are out of view, it shows at the edge of the
// window, so that it stays open. Folded, each card is a marker, and the active one opens beside its marker, under its
// words.
function layout() {
  if (!mounted) return;
  measure();
  const page = $('reader-page').getBoundingClientRect(), outer = frame().getBoundingClientRect();
  margin.style.left = (folded ? page.right - 30 : page.right + GAP) + scrollX + 'px';
  margin.style.width = (folded ? MARKER : width) + 'px';
  const items = [...cards.values()].filter(card => card.words || card.id === active).map(card => {
    const rects = card.words?.range ? [...card.words.range.getClientRects()] : [];
    const first = rects[0] || card.words?.anchor.getBoundingClientRect(), last = rects.at(-1) || first;
    return {card, y: first ? outer.top + scrollY + first.top : null, bottom: last ? outer.top + scrollY + last.bottom : null};
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
  const top = scrollY + margin.getBoundingClientRect().top, inset = native ? 12 : 64;
  const heights = items.map(({card}) => folded && card.id !== active ? MARKER : card.element.offsetHeight);
  const tops = items.map(({y}) => (y ?? scrollY + inset) - top);
  const index = items.findIndex(({card}) => card.id === active);
  if (index >= 0 && folded && items[index].bottom !== null) tops[index] = items[index].bottom - top + 8;
  // An active card with no words in this chapter takes no place among the others.
  if (index >= 0 && !folded && items[index].y !== null) {
    for (let i = index + 1; i < items.length; i++) tops[i] = Math.max(tops[i], tops[i - 1] + heights[i - 1] + 8);
    for (let i = index - 1; i >= 0; i--) tops[i] = Math.min(tops[i], tops[i + 1] - heights[i] - 8);
  } else {
    let floor = -Infinity;
    items.forEach((item, i) => {
      if (i === index) return;
      tops[i] = Math.max(tops[i], floor); floor = tops[i] + heights[i] + (folded ? 6 : 8);
    });
  }
  // The other cards stay at their words, and the active card comes into view over them. A card taller than the
  // window keeps its top in view.
  if (index >= 0) {
    const view = scrollY - top;
    tops[index] = Math.max(view + inset, Math.min(tops[index], view + innerHeight - heights[index] - 12));
  }
  items.forEach(({card}, i) => { card.element.style.top = tops[i] + 'px'; });
}
function shape(card) {
  const element = card.element, floating = folded && card.id === active;
  element.classList.toggle('is-marker', folded && !floating);
  element.classList.toggle('is-floating', floating);
  element.classList.toggle('is-active', card.id === active);
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
// A draft with no typed question goes away when the reader leaves it.
function dropDraft() {
  for (const card of cards.values()) {
    if (card.draft && !card.pending && !card.input?.value.trim() && card.id !== active) { cards.delete(card.id); card.element?.remove(); }
  }
  paint();
}
// A dotted line that moves along its length joins the card to its words, and the words pulse once. It follows
// scrolling and layout. With Reduce Motion the line does not move, and the outline stays on the words.
const SVG = 'http://www.w3.org/2000/svg';
let line = null;
function clearLine() {
  if (!line) return;
  cancelAnimationFrame(line.frame); line.svg.remove(); line = null;
}
function connect(card) {
  clearLine();
  if (!card.words?.range) return;
  const svg = document.createElementNS(SVG, 'svg'), path = document.createElementNS(SVG, 'path'), dot = document.createElementNS(SVG, 'circle');
  svg.setAttribute('class', 'lx-line'); svg.setAttribute('aria-hidden', 'true'); dot.setAttribute('r', '3.5');
  const outlines = [...card.words.range.getClientRects()].map(() => document.createElementNS(SVG, 'rect'));
  svg.append(path, dot, ...outlines);
  document.body.append(svg);
  line = {svg, frame: 0};
  const draw = () => {
    const rects = card.words?.range ? [...card.words.range.getClientRects()] : [];
    if (!line || !card.element?.isConnected || !rects.length) return clearLine();
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
    line.frame = requestAnimationFrame(draw);
  };
  draw();
}

// ---- Cards ----
// Opens a draft card at `where` and focuses its question field; with `question`, asks it at once.
function openCard(where, question = '') {
  if (!where) return;
  const card = {id: `draft-${++drafts}`, draft: true, record: {id: '', paper: paperId, kept: false, turns: [], ...where}};
  cards.set(card.id, card);
  active = card.id;
  dropDraft(); select(card);
  if (question) send(card, question); else card.input?.focus({preventScroll: true});
}
export function askPaper() {
  if (!mounted) return;
  const line = (native ? 12 : 64) - frame().getBoundingClientRect().top;
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
function drawLost(card) {
  card.lost.replaceChildren();
  if (card.words?.found !== false) return;
  if (card.record.quote) card.lost.append(node('blockquote', card.record.quote, 'lx-quote'));
  card.lost.append(node('p', 'LocalXiv cannot find these words in this version of the Paper.', 'lx-note'));
}
// Turns only grow, and the streaming turn becomes the last one, so only new turns are added to the live region.
function drawTurns(card) {
  drawLost(card);
  const box = card.turns, turns = card.record.turns, count = turns.length + (card.pending ? 1 : 0);
  while (box.children.length > count) box.lastElementChild.remove();
  turns.forEach((turn, index) => {
    const element = box.children[index];
    if (!element) box.append(fillTurn(node('div', undefined, 'lx-turn'), turn));
    else if (element.classList.contains('is-pending')) fillTurn(element, turn);
  });
  if (card.pending && box.children.length === turns.length) box.append(pendingTurn(card));
}
function pendingTurn(card) {
  const element = node('div', undefined, 'lx-turn is-pending'), status = node('p', undefined, 'lx-status'), stop = node('button', 'Stop');
  stop.type = 'button'; stop.onclick = () => card.controller?.abort();
  // Chat names what it reads before the first words.
  status.append(node('span', 'Reading the Paper…'), stop);
  const answer = node('div', undefined, 'prose lx-answer');
  answer.setAttribute('aria-busy', 'true');
  element.append(node('p', card.pending.question, 'lx-q'), answer, status);
  card.pending.element = element;
  return element;
}
// While the answer streams, its citations number the Paper's passages; the saved answer has only the checked ones.
function drawPending(card) {
  const pending = card.pending;
  if (!pending?.element || pending.drawn) return;
  pending.drawn = requestAnimationFrame(() => {
    pending.drawn = 0;
    if (card.pending !== pending) return;
    pending.element.querySelector('.lx-status span').textContent = 'Answering…';
    prose(pending.element.querySelector('.lx-answer'), pending.text, detail?.paper?.passages || [], () => {});
  });
}
function fillTurn(element, turn) {
  const answer = turn.answer, text = node('div', undefined, 'prose lx-answer');
  if (element.classList.contains('is-pending') && element.contains(document.activeElement)) element.closest('.lx-card')?.focus({preventScroll: true});
  element.className = 'lx-turn';
  element.replaceChildren(node('p', turn.question, 'lx-q'));
  if (answer.text) { prose(text, answer.text, answer.cites || [], renderMath); element.append(text); }
  if (answer.stopped) element.append(node('p', 'Stopped.', 'lx-meta'));
  if (answer.error) element.append(node('p', answer.error, 'lx-error'));
  if (answer.dropped > 0) element.append(node('p', 'Older questions on this card no longer go to the model.', 'lx-meta'));
  element.append(node('p', provenance(answer), 'lx-meta'));
  return element;
}
const prose = (target, text, references, math, openSource = goPassage) => renderProse(target, text, {node, references, fileURL, renderMath: math, openSource});
const count = value => value >= 100_000 ? `${Math.round(value / 1000)}k` : value >= 1000 ? `${(value / 1000).toFixed(1)}k` : String(value || 0);
// The model, the provider, the date, and the tokens: the reader pays for each token with their own key.
function provenance(answer) {
  const date = new Date(answer.created_at * 1000).toLocaleDateString(undefined, {day: 'numeric', month: 'short', year: 'numeric'});
  const tokens = answer.tokens && `Tokens: ${count(answer.tokens.cached)} cached, ${count(answer.tokens.new)} new, ${count(answer.tokens.output)} output`;
  const provider = PROVIDERS[answer.host] || (loopback(answer.host) ? 'this Mac' : answer.host);
  return [answer.model, provider, date, tokens].filter(Boolean).join(' · ');
}
// The question field names the provider host that gets the Paper. With no Chat model, the card offers the two ways
// to connect one; Chat never takes the Overview connection by itself.
function drawCompose(card) {
  if (!card.compose) return;
  const ready = Boolean(state.settings?.chat_ready), endpoint = state.settings?.chat_endpoint || '';
  const signature = JSON.stringify([ready, endpoint, aiReady(), card.error, card.record.turns.length]);
  if (card.composed === signature) return;
  card.composed = signature;
  if (!card.form) {
    const form = node('form', undefined, 'lx-form'), input = node('input'), ask = node('button', 'Ask', 'btn-quiet');
    input.type = 'text'; input.maxLength = 4000; input.setAttribute('aria-label', 'Question'); ask.type = 'submit';
    form.onsubmit = event => {
      event.preventDefault();
      const question = input.value.trim();
      if (!question || card.pending) return;
      input.value = ''; send(card, question);
    };
    form.append(input, ask);
    card.form = form; card.input = input; card.host = node('p', '', 'lx-host'); card.errorLine = node('p', '', 'lx-error');
  }
  // A question that waited for a Chat model goes into the field once one is connected.
  if (ready && card.waiting) { card.input.value ||= card.waiting; card.waiting = ''; }
  let host = '';
  try { host = new URL(endpoint).hostname; } catch {}
  card.input.placeholder = card.record.turns.length ? 'Ask a follow-up' : card.record.whole ? 'Ask about the Paper' : 'Ask about these words';
  card.host.textContent = !host ? '' : PROVIDERS[host] ? `Asks ${PROVIDERS[host]} (${host})` : loopback(host) ? `Asks a model on this Mac (${host})` : `Asks ${host}`;
  card.errorLine.textContent = card.error || ''; card.errorLine.hidden = !card.error;
  const parts = ready ? [card.form, card.host, card.errorLine] : [blocked(card), card.errorLine];
  // Moving the field would take focus from it, so the parts are replaced only when they change.
  if (parts.some((part, index) => card.compose.children[index] !== part) || card.compose.children.length !== parts.length) card.compose.replaceChildren(...parts);
}
function blocked(card) {
  const box = node('div', undefined, 'lx-blocked'), row = node('div', undefined, 'lx-row');
  box.append(node('p', 'Chat needs its own Chat model. Chat uses your Overview connection only when you select it.'));
  if (aiReady()) {
    const copy = node('button', 'Use my Overview connection', 'btn-quiet');
    copy.type = 'button'; copy.onclick = () => useOverview(card);
    row.append(copy);
  }
  const setup = node('button', 'Set up Chat…', 'btn-quiet');
  setup.type = 'button'; setup.onclick = () => openSettings('chat');
  row.append(setup);
  box.append(row);
  return box;
}
// One explicit copy of the Overview connection to Chat. A question that waited for a Chat model goes then.
async function useOverview(card) {
  try { state.settings = await api('/api/settings', {chat_copy: true}); }
  catch (error) { card.error = error.message; drawCompose(card); return; }
  card.error = '';
  for (const each of cards.values()) drawCompose(each);
  if (card.waiting) { const question = card.waiting; card.waiting = ''; send(card, question); }
  else card.input?.focus();
}
function drawActions(card) {
  const buttons = [];
  const button = (label, title, action) => {
    const element = node('button', label); element.type = 'button'; element.title = title; element.onclick = action;
    buttons.push(element);
  };
  if (!card.draft && !card.record.kept) button('Keep as Note', 'Keep this question and its answers in the Paper.', () => keep(card));
  if (card.record.kept) buttons.push(node('span', 'Kept as a Note', 'lx-meta'));
  button(card.record.kept ? 'Delete' : 'Discard', 'Remove this question. Press ⌘Z to undo.', () => remove(card));
  card.actions.replaceChildren(...buttons);
}

// ---- Asking: the stream client ----
// The route answers 400 before it streams, or NDJSON lines: the card before the question, text deltas, blank
// heartbeats, and last the card with the new turn. Stop closes the response, and the server stops the provider.
async function send(card, question) {
  if (!state.settings?.chat_ready) { card.waiting = question; drawCompose(card); return; }
  const body = card.draft ? {passage: card.record.passage || '', quote: card.record.quote, question} : {thread: card.id, question};
  const controller = card.controller = new AbortController();
  card.pending = {question, text: '', started: false}; card.error = '';
  drawTurns(card); drawCompose(card); schedule();
  let ended = false;
  try {
    const response = await fetch(`${paperAPI(paperId)}/chat`, {method: 'POST', signal: controller.signal, body: JSON.stringify(body),
      headers: {Authorization: `Bearer ${token}`, 'Content-Type': 'application/json'}});
    if (!response.ok) throw new Error((await response.json().catch(() => ({}))).error || `Request failed (${response.status})`);
    const reader = response.body.getReader(), decoder = new TextDecoder();
    let buffer = '';
    while (!ended) {
      const {value, done} = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, {stream: true});
      for (let cut = buffer.indexOf('\n'); cut >= 0; cut = buffer.indexOf('\n')) {
        const text = buffer.slice(0, cut).trim();
        buffer = buffer.slice(cut + 1);
        if (text) ended = receive(card, JSON.parse(text)) || ended;
      }
    }
    if (!ended) throw new Error('The answer stopped before its end. Ask again.');
  } catch (error) {
    // A network failure is a TypeError, with a message that differs between browsers.
    if (card.pending) end(card, controller.signal.aborted ? '' : error instanceof TypeError ? 'LocalXiv cannot reach its library service. Try again in a moment.' : error.message);
  } finally {
    if (card.controller === controller) card.controller = null;
  }
}
// Returns true at the last line.
function receive(card, line) {
  if (line.type === 'thread') {
    adopt(card, line.thread);
    card.pending.started = true;
  } else if (line.type === 'text') {
    card.pending.text += line.text; drawPending(card);
  } else if (line.type === 'done' || line.type === 'error') {
    card.record = line.thread; card.pending = null;
    drawTurns(card); drawActions(card); drawCompose(card); schedule();
    return true;
  }
  return false;
}
// The stored card replaces the draft, or the card as the server has it now.
function adopt(card, record) {
  if (card.draft) {
    cards.delete(card.id);
    if (active === card.id) active = record.id;
    card.id = record.id; card.draft = false; cards.set(card.id, card);
  }
  card.record = record;
  drawActions(card);
}
// Ends a question with no last line. After the card is stored, a Stop keeps the words so far as a stopped turn,
// and a failure keeps the question with the message. Before that, the question goes back to the field.
function end(card, message) {
  const {question, text, started} = card.pending;
  card.pending = null;
  if (started) {
    const host = (() => { try { return new URL(state.settings?.chat_endpoint).hostname; } catch { return ''; } })();
    card.record.turns = [...card.record.turns, {question, answer: {text, cites: [], unknown: [], model: state.settings?.chat_model || '',
      host, created_at: Date.now() / 1000, stopped: !message, error: message || null, dropped: 0}}];
  } else {
    if (card.input && !card.input.value) card.input.value = question;
    card.error = message;
  }
  drawTurns(card); drawCompose(card); schedule();
}
async function keep(card) {
  try { const {thread} = await api(`${paperAPI(paperId)}/chat/update`, {thread: card.id, kept: true}); card.record = {...card.record, kept: thread.kept}; }
  catch (error) { return notice(error.message); }
  drawActions(card); paint();
}
async function remove(card) {
  if (!card.draft) {
    let removed;
    try { ({removed} = await api(`${paperAPI(paperId)}/chat/delete`, {threads: [card.id]})); }
    catch (error) { return notice(error.message); }
    if (removed.length) undo.push(removed);
    notice('Question removed. Press ⌘Z to undo.', true);
  }
  card.controller?.abort(); cards.delete(card.id); card.element?.remove();
  if (card.element) observer?.unobserve(card.element);
  if (active === card.id) { active = ''; clearLine(); }
  paint(); layout();
}
async function restore() {
  const records = undo.pop();
  try {
    const {chat} = await api(`${paperAPI(paperId)}/chat/restore`, {threads: records});
    for (const record of chat) if (!cards.has(record.id)) cards.set(record.id, {id: record.id, record});
  } catch (error) { undo.push(records); return notice(error.message); }
  paint(); layout();
}

// ---- All Notes ----
// Every Question card of the Paper in reading order: the one Chat history of the Paper. A card opens at its words.
const order = card => {
  const index = detail?.paper?.passages?.findIndex(item => item.id === card.record.passage) ?? -1;
  return [index < 0 ? Infinity : index, card.record.created_at || 0];
};
export function showAllNotes() {
  // The cards are another Paper's until the margin mounts for this one, as on a PDF.
  if (selected !== paperId) reset();
  const dialog = node('dialog', undefined, 'all-notes'), head = node('div', undefined, 'dialog-heading'), title = node('h2', 'All Notes');
  const done = node('button', 'Done', 'btn-quiet');
  title.id = 'all-notes-title'; dialog.setAttribute('aria-labelledby', title.id);
  done.type = 'button'; done.onclick = () => dialog.close();
  head.append(title, done);
  dialog.append(head);
  const list = [...cards.values()].filter(card => !card.draft).sort((a, b) => {
    const [x, y] = [order(a), order(b)];
    return x[0] - y[0] || x[1] - y[1];
  });
  dialog.append(node('p', list.length ? 'Every Question card of this Paper, in reading order.' : 'This Paper has no Question cards. Select text in the Paper, then choose Ask.', 'help'));
  for (const card of list) {
    const row = node('section', undefined, 'an-row'), go = node('button', undefined, 'an-go');
    const section = detail?.paper?.passages?.find(item => item.id === card.record.passage)?.section || '';
    go.type = 'button';
    go.append(node('span', [section, card.record.kept ? 'Kept as a Note' : ''].filter(Boolean).join(' · '), 'an-where'),
      node('span', card.record.whole ? 'Question about the Paper' : `“${card.record.quote}”`, 'an-quote'));
    go.onclick = () => { dialog.close(); show(card); };
    row.append(go);
    for (const turn of card.record.turns) {
      row.append(node('p', turn.question, 'lx-q'));
      if (turn.answer.text) {
        const text = node('div', undefined, 'prose lx-answer');
        prose(text, turn.answer.text, turn.answer.cites || [], renderMath, href => { dialog.close(); goPassage(href); });
        row.append(text);
      }
      if (turn.answer.stopped) row.append(node('p', 'Stopped.', 'lx-meta'));
      if (turn.answer.error) row.append(node('p', turn.answer.error, 'lx-error'));
    }
    dialog.append(row);
  }
  dialog.onclose = () => dialog.remove();
  document.body.append(dialog); dialog.showModal();
}
// Goes to a card's words in the Paper view and selects the card there.
function show(card) {
  const href = hrefOf(card.record);
  if (!href) return;
  wanted = card.id;
  goPassage(href);
  // A chapter that is already in the frame sends no lx-chapter event.
  if (mounted && href.split('#')[0] === chapter && doc === frame().contentDocument) { wanted = ''; select(card); }
}
