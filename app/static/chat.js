// The questions of a card and the client of the Chat stream: the turns, the question field, the actions, the
// Markdown copy, and the request that streams an answer. margin.js holds the card shell and imports this module, and
// this module imports margin.js. As in margin.js, the top level only defines functions and adds listeners.
import {node, renderProse, baseID} from './render.js';
import {api, paperAPI, fileURL, openSettings, aiReady, state, token, copy} from './app.js';
import {goPassage, openPreview, renderMath, detail, syncReaderChrome} from './reader.js';
import {marks, paperId, schedule, select, drawLost, adopt, keep, remove, placeAgain, anchorOf, addQuote} from './margin.js';
import {editNote} from './notes.js';

const PROVIDERS = {'api.anthropic.com': 'Anthropic', 'api.openai.com': 'OpenAI', 'openrouter.ai': 'OpenRouter',
  'api.deepseek.com': 'DeepSeek', 'generativelanguage.googleapis.com': 'Google'};
const loopback = host => /^(127\.|localhost$|\[?::1\]?$)/.test(host || '');
// The Papers whose large prompt the reader confirmed in this page session. Follow-ups send the same prefix.
const largeOK = new Set();

// ---- The card body ----
// The added quotes of a question, above it.
const quoteBlocks = quotes => quotes.map(item => node('blockquote', item.quote, 'lx-quote'));
// Turns only grow, and the streaming turn becomes the last one, so only new turns are added to the live region.
export function drawTurns(card) {
  drawLost(card);
  const box = card.turns, turns = card.record.turns, count = turns.length + (card.pending ? 1 : 0);
  while (box.children.length > count) box.lastElementChild.remove();
  turns.forEach((turn, index) => {
    const element = box.children[index];
    if (!element) box.append(fillTurn(node('div', undefined, 'lx-turn'), turn));
    else if (element.classList.contains('is-pending')) fillTurn(element, turn);
  });
  if (card.pending && box.children.length === turns.length) box.append(pendingTurn(card));
  // Retry asks the last question again when its answer stopped or failed, and no answer runs.
  box.querySelector('.lx-retry')?.remove();
  const last = turns.at(-1);
  if (!card.pending && last && (last.answer.stopped || last.answer.error)) {
    const retry = node('button', 'Retry', 'btn-quiet lx-retry');
    retry.type = 'button'; retry.title = 'Ask this question again.';
    retry.onclick = () => send(card, last.question, last.quotes || []);
    box.children[turns.length - 1].append(retry);
  }
}
function pendingTurn(card) {
  const element = node('div', undefined, 'lx-turn is-pending'), status = node('p', undefined, 'lx-status');
  // Chat names what it reads before the first words.
  status.append(node('span', 'Reading the Paper…'));
  const answer = node('div', undefined, 'prose lx-answer');
  answer.setAttribute('aria-busy', 'true');
  element.append(...quoteBlocks(card.pending.quotes), node('p', card.pending.question, 'lx-q'), answer, status);
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
    prose(pending.element.querySelector('.lx-answer'), pending.text, detail?.paper?.passages || [], () => {});
  });
}
function fillTurn(element, turn) {
  const answer = turn.answer, text = node('div', undefined, 'prose lx-answer');
  if (element.classList.contains('is-pending') && element.contains(document.activeElement)) element.closest('.lx-card')?.focus({preventScroll: true});
  element.className = 'lx-turn';
  element.replaceChildren(...quoteBlocks(turn.quotes || []), node('p', turn.question, 'lx-q'));
  if (answer.text) { prose(text, answer.text, answer.cites || [], renderMath); element.append(text); }
  if (answer.stopped) element.append(node('p', 'Stopped.', 'lx-meta'));
  if (answer.error) element.append(node('p', answer.error, 'lx-error'));
  if (answer.dropped > 0) element.append(node('p', 'Older questions on this card no longer go to the model.', 'lx-meta'));
  element.append(node('p', provenance(answer), 'lx-meta'));
  return element;
}
// A cited ID that is not in `references` shows as unverified: in a saved answer these are the turn's `unknown` IDs.
// A Turn keeps the text of each passage it cited. A passage ID is a position, so after a reimport the ID can name
// other text, or nothing: the citation is then from an earlier version of the Paper.
const currentText = () => new Map((detail?.paper?.passages || []).map(item => [item.id, item.text]));
const earlier = (source, texts = currentText()) => texts.get(source.id) !== source.text;
export const prose = (target, text, references, math, openSource = goPassage, onEarlier = openEarlier) => {
  const texts = currentText();
  return renderProse(target, text, {node, references: references.map(source => earlier(source, texts) ? {...source, earlier: true} : source),
    fileURL, renderMath: math, openSource, openEarlier: onEarlier, unverified: true});
};
// Shows the text that the answer cited. Its place in the Paper now has other text, or no longer exists.
export function openEarlier(mark, source) {
  const now = detail?.paper?.passages?.find(item => item.id === source.id);
  openPreview(mark, `${source.section || 'Passage'} · From an earlier version`, node('p', source.text, 'clamp'),
    now ? [['Open in Paper', 'doc', () => goPassage(now.href), true]] : [],
    now ? 'The Paper has other text at this place now.' : 'This version of the Paper does not have this passage.');
}
const count = value => value >= 100_000 ? `${Math.round(value / 1000)}k` : value >= 1000 ? `${(value / 1000).toFixed(1)}k` : String(value || 0);
// The model, the provider, the date, and the tokens: the reader pays for each token with their own key. A stopped
// answer, an error, or a provider that sends no usage stores 0 tokens, which is no count, so the line leaves them out.
function provenance(answer) {
  const date = new Date(answer.created_at * 1000).toLocaleDateString(undefined, {day: 'numeric', month: 'short', year: 'numeric'});
  const tokens = Object.values(answer.tokens || {}).some(Boolean) && `Tokens: ${count(answer.tokens.cached)} cached, ${count(answer.tokens.new)} new, ${count(answer.tokens.output)} output`;
  const provider = PROVIDERS[answer.host] || (loopback(answer.host) ? 'this Mac' : answer.host);
  return [answer.model, provider, date, tokens].filter(Boolean).join(' · ');
}
// A Question card has the question field. A kept card with no turns has it after Ask, so that its answers join it.
const asks = card => Boolean(!card.record.kept || card.record.turns.length || card.pending || card.asking || card.waiting || card.error);
export function openAsk(card) {
  card.asking = true;
  select(card); drawCompose(card); drawActions(card);
  card.input?.focus({preventScroll: true});
}
// The question field names the provider host that gets the Paper. With no Chat model, the card offers the two ways
// to connect one; Chat never takes the Overview connection by itself.
export function drawCompose(card) {
  if (!card.compose) return;
  const ready = Boolean(state.settings?.chat_ready), endpoint = state.settings?.chat_endpoint || '';
  card.quotes ||= [];
  const signature = JSON.stringify([asks(card), ready, endpoint, aiReady(), card.error, card.confirm, card.waiting, card.record.turns.length, card.quotes, Boolean(card.pending)]);
  if (card.composed === signature) return;
  card.composed = signature;
  if (!asks(card)) return card.compose.replaceChildren();
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
    card.form = form; card.input = input; card.ask = ask; card.host = node('p', '', 'lx-host'); card.errorLine = node('p', '', 'lx-error');
    card.quoteBox = node('div', undefined, 'lx-quotes');
  }
  // The added quotes for the next question, each with Remove, and Add Quote, which waits for a selection in the Paper.
  const add = node('button', 'Add Quote', 'btn-quiet');
  add.type = 'button'; add.title = 'Add more words from the Paper to the next question.'; add.onclick = () => addQuote(card);
  add.hidden = card.quotes.length >= 4 || Boolean(card.pending);
  card.quoteBox.replaceChildren(...card.quotes.map((item, index) => {
    const row = node('div', undefined, 'lx-added'), drop = node('button', 'Remove', 'btn-quiet');
    drop.type = 'button'; drop.setAttribute('aria-label', 'Remove this quote');
    drop.onclick = () => { card.quotes.splice(index, 1); drawCompose(card); card.input.focus(); };
    row.append(node('blockquote', item.quote, 'lx-quote'), drop);
    return row;
  }), add);
  // A question that waited for a Chat model goes into the field once one is connected.
  if (ready && card.waiting) { card.input.value ||= card.waiting; card.waiting = ''; }
  let host = '';
  try { host = new URL(endpoint).hostname; } catch {}
  card.input.placeholder = card.record.turns.length ? 'Ask a follow-up' : card.record.whole ? 'Ask about the Paper' : 'Ask about these words';
  // While an answer streams, Ask is Stop.
  Object.assign(card.ask, {textContent: card.pending ? 'Stop' : 'Ask', type: card.pending ? 'button' : 'submit', onclick: card.pending ? () => card.controller?.abort() : null});
  const via = !host ? '' : PROVIDERS[host] ? `Asks ${PROVIDERS[host]} (${host})` : loopback(host) ? `Asks a model on this Mac (${host})` : `Asks ${host}`;
  // A card with no answers yet says once that answers can be wrong.
  card.host.textContent = [via, !card.record.turns.length && 'Answers can be wrong. Check the cited passages.'].filter(Boolean).join('. ');
  card.errorLine.replaceChildren(card.error || ''); card.errorLine.hidden = !card.error;
  if (card.error && card.confirm) {
    // The question waits in the field until the reader confirms the size of the prompt.
    const anyway = node('button', 'Ask Anyway', 'btn-quiet');
    anyway.type = 'button';
    anyway.onclick = () => { largeOK.add(paperId); card.form.requestSubmit(); };
    card.errorLine.append(' ', anyway);
  }
  const parts = ready ? [card.quoteBox, card.form, card.host, card.errorLine] : [blocked(card), card.errorLine];
  // Moving the field would take focus from it, so the parts are replaced only when they change.
  if (parts.some((part, index) => card.compose.children[index] !== part) || card.compose.children.length !== parts.length) card.compose.replaceChildren(...parts);
}
function blocked(card) {
  const box = node('div', undefined, 'lx-blocked'), row = node('div', undefined, 'lx-row');
  // The question that waits for a Chat model.
  if (card.waiting) box.append(node('p', card.waiting, 'lx-q'));
  box.append(node('p', 'Chat needs its own Chat model. Chat uses your Overview connection only when you select it. Chat then sends the Paper’s text, your Highlights and Notes, and your question to that provider.'));
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
  for (const each of marks.values()) drawCompose(each);
  if (card.waiting) { const question = card.waiting; card.waiting = ''; send(card, question); }
  else card.input?.focus();
}
export function drawActions(card) {
  const buttons = [];
  const button = (label, title, action) => {
    const element = node('button', label); element.type = 'button'; element.title = title; element.onclick = action;
    buttons.push(element);
  };
  const record = card.record;
  if (!card.draft && !record.kept) button('Keep as Note', 'Keep this question and its answers in the Paper.', () => keep(card));
  if (record.kept && record.turns.length) buttons.push(node('span', 'Kept as a Note', 'lx-meta'));
  if (record.kept && !card.editor) button(record.note ? 'Edit' : 'Add Note', 'Write a Note on these words.', () => editNote(card));
  if (record.kept && !asks(card)) button('Ask', 'Ask about these words.', () => openAsk(card));
  if (record.found === 'moved') button('Place Again', 'Select the words again in this version of the Paper.', () => placeAgain(card));
  // WebKit can refuse a clipboard write after an await, so the text is made before the copy starts.
  if (record.turns.some(turn => turn.answer.text)) button('Copy as Markdown', 'Copy this question and its answers as Markdown.', () => copy(markdown(card), 'Question card'));
  button(record.kept ? 'Delete' : 'Discard', record.kept ? 'Delete this Highlight. Press ⌘Z to undo.' : 'Remove this question. Press ⌘Z to undo.', () => remove(card));
  card.actions.replaceChildren(...buttons);
}
// The card as Markdown: the Paper and the words it asks about, each question with its answer, and the cited passages,
// numbered across the card.
function markdown(card) {
  const paper = detail?.paper || {}, record = card.record, texts = currentText(), numbers = new Map();
  const section = paper.passages?.find(item => item.id === record.passage)?.section;
  const title = paper.arxiv_id ? `[${paper.title}](https://arxiv.org/abs/${baseID(paper.arxiv_id)})` : paper.title;
  const lines = [[title, section].filter(Boolean).join(' · '),
    record.whole ? '> *Question about the Paper*' : record.quote.split('\n').map(line => `> ${line}`).join('\n')];
  for (const {question, quotes, answer} of record.turns) {
    const known = new Map((answer.cites || []).map(source => [source.id, source]));
    const number = id => {
      if (!known.has(id)) return '?';
      if (!numbers.has(id)) numbers.set(id, [numbers.size + 1, known.get(id)]);
      return numbers.get(id)[0];
    };
    lines.push('');
    for (const item of quotes || []) lines.push(...item.quote.split('\n').map(line => `> ${line}`), '');
    lines.push(`**${question}**`);
    if (answer.text) lines.push('', answer.text.replace(/\[\s*p\d+(?:\s*[,;]\s*p\d+)*\s*\]/g, group => `[${group.match(/p\d+/g).map(number).join(', ')}]`));
    if (answer.stopped) lines.push('*Stopped.*');
    if (answer.error) lines.push(`*${answer.error}*`);
  }
  if (numbers.size) lines.push('', 'Sources', ...[...numbers.values()].map(([n, source]) =>
    `[${n}] ${source.section || 'Passage'}: "${source.text.length > 200 ? `${source.text.slice(0, 200)}…` : source.text}"${earlier(source, texts) ? ' (from an earlier version)' : ''}`));
  return lines.join('\n');
}

// ---- Asking: the stream client ----
// The route answers 400 before it streams, or NDJSON lines: the card before the question, text deltas, blank
// heartbeats, and last the card with the new turn. Stop closes the response, and the server stops the provider.
// The server saves the answer only while the response is open, so the answer of a Paper that the reader leaves runs
// on. Its lines change nothing while the cards of another Paper show (`owner`), and its Paper reads the saved answer.
export async function send(card, question, quotes = card.quotes || []) {
  if (!state.settings?.chat_ready) { card.waiting = question; drawCompose(card); return; }
  // The question takes the added quotes with it. A Retry sends the quotes of its turn, and the list stays.
  if (quotes === card.quotes) card.quotes = [];
  const owner = paperId, body = card.draft ? {anchor: anchorOf(card.record), question} : {thread: card.id, question};
  body.large = largeOK.has(owner); body.quotes = quotes.map(({passage, quote}) => ({passage, quote}));
  const controller = card.controller = new AbortController();
  card.pending = {question, quotes, text: '', started: false}; card.error = ''; card.confirm = false;
  // Clear Chat is on while an answer runs.
  drawTurns(card); drawCompose(card); schedule(); syncReaderChrome();
  let ended = false;
  try {
    const response = await fetch(`${paperAPI(owner)}/chat`, {method: 'POST', signal: controller.signal, body: JSON.stringify(body),
      headers: {Authorization: `Bearer ${token}`, 'Content-Type': 'application/json'}});
    if (!response.ok) {
      const failure = await response.json().catch(() => ({}));
      card.confirm = failure.confirm === 'large';
      throw new Error(failure.error || `Request failed (${response.status})`);
    }
    const reader = response.body.getReader(), decoder = new TextDecoder();
    let buffer = '';
    while (!ended) {
      const {value, done} = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, {stream: true});
      for (let cut = buffer.indexOf('\n'); cut >= 0; cut = buffer.indexOf('\n')) {
        const text = buffer.slice(0, cut).trim();
        buffer = buffer.slice(cut + 1);
        if (text) ended = receive(card, JSON.parse(text), owner) || ended;
      }
    }
    if (!ended) throw new Error('The answer stopped before its end. Ask again.');
  } catch (error) {
    // A network failure is a TypeError, with a message that differs between browsers.
    if (card.pending) end(card, owner, controller.signal.aborted ? '' : error instanceof TypeError ? 'LocalXiv cannot reach its library service. Try again in a moment.' : error.message);
  } finally {
    if (card.controller === controller) card.controller = null;
    syncReaderChrome();
  }
}
// Returns true at the last line.
function receive(card, line, owner) {
  if (owner !== paperId) return ['done', 'error'].includes(line.type);
  if (line.type === 'thread') {
    adopt(card, line.thread);
    card.pending.started = true;
  } else if (line.type === 'wait') {
    // The cause and the wait of a rate limit, until the first words.
    card.pending.element?.querySelector('.lx-status span').replaceChildren(line.message);
  } else if (line.type === 'text') {
    // The status is in the live region, so it changes once, at the first words.
    if (!card.pending.text) card.pending.element?.querySelector('.lx-status span').replaceChildren('Answering…');
    card.pending.text += line.text; drawPending(card);
  } else if (line.type === 'error' && line.thread.turns.length === card.record.turns.length) {
    // The server could not store the turn, so its last line has the card without it.
    end(card, owner, line.message, false);
    return true;
  } else if (line.type === 'done' || line.type === 'error') {
    card.record = line.thread; card.pending = null;
    drawTurns(card); drawActions(card); drawCompose(card); schedule();
    return true;
  }
  return false;
}
// Ends a question with no last line, or with a turn that the server could not store. After the card is stored, a
// Stop keeps the words so far as a stopped turn, and a failure keeps the question with the message. Before that, or
// when the server could not store the turn, the question goes back to the field with the message.
function end(card, owner, message, stored = card.pending.started) {
  if (owner !== paperId) return;
  const {question, text, quotes} = card.pending;
  card.pending = null;
  if (stored) {
    const host = (() => { try { return new URL(state.settings?.chat_endpoint).hostname; } catch { return ''; } })();
    // The citations are checked against the Paper's passages, as the stream shows them (papers/passages.py
    // chat_citations), so only an ID that no passage has gets the unverified mark.
    const known = new Map((detail?.paper?.passages || []).map(item => [item.id, item]));
    const ids = [...new Set([...text.matchAll(/\[\s*p\d+(?:\s*[,;]\s*p\d+)*\s*\]/g)].flatMap(([group]) => group.match(/p\d+/g)))];
    card.record.turns = [...card.record.turns, {question, quotes, answer: {text, cites: ids.filter(id => known.has(id)).map(id => known.get(id)),
      unknown: ids.filter(id => !known.has(id)), model: state.settings?.chat_model || '',
      host, created_at: Date.now() / 1000, stopped: !message, error: message || null, dropped: 0}}];
  } else {
    if (card.input && !card.input.value) card.input.value = question;
    card.quotes = quotes; card.error = message;
  }
  drawTurns(card); drawCompose(card); schedule();
}
