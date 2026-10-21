/* No provider keys are retained by the browser. Paper and model text are always text nodes. */
import {commands, register, chrome, nav, openMenu, native, post} from './shell.js';
import {node, icon, figureFailure, expireToast, JobNotices, TERMINAL, inputKind, searchRows, rowState, authorList,
  authorNames, arxivDate, shortTitle, bibtex, readingState, libraryRow, baseID} from './render.js';
import {normalize, fromSettings, toSettings, readCopy, writeCopy, resolveTheme, rootProperties, SIZES, DEFAULTS, STORAGE_KEY} from './appearance.js';
import {openPaper, closeReader, syncReaderChrome, styleReader, swapFigureSources, generate, viewShows, selected, detail, activeTab, goPassage} from './reader.js';
import {askPaper, selectionCommand, marks, paperId, copyNotes, offerVersion, versionOf, clearChat} from './margin.js';
import {showAllNotes, drawNotesPage} from './notes.js';

const $ = id => document.getElementById(id);
const panel = new URLSearchParams(location.search).get('panel') === 'settings';
const fragment = new URLSearchParams(location.hash.slice(1));
const storage = (() => { try { return window.localStorage; } catch { return null; } })();
export const stored = key => { try { return storage?.getItem(key) || ''; } catch { return ''; } };
export const store = (key, value) => { try { storage?.setItem(key, value); } catch {} };
// The Chat stream in chat.js reads the token, because it needs the response itself and not its JSON.
export let token = fragment.get('token') || stored('papers-session');
if (fragment.has('token')) { store('papers-session', token); history.replaceState(null, '', location.pathname + location.search); }

const SAMPLE_ID = '1706.03762v7';
const FILTERS = {all: 'All Papers', new: 'New', reading: 'Reading', read: 'Read'};
const VIEW_LABELS = {overview: 'Overview', blog: 'Blog', paper: 'Paper'};
const PROVIDER_PRESETS = Object.freeze({
  openai: {endpoint: 'https://api.openai.com/v1'},
  openrouter: {endpoint: 'https://openrouter.ai/api/v1'},
  deepseek: {endpoint: 'https://api.deepseek.com'},
  gemini: {endpoint: 'https://generativelanguage.googleapis.com/v1beta/openai/'},
  anthropic: {endpoint: 'https://api.anthropic.com/v1'},
});
// Chat also offers a model on this Mac, which needs no key.
const CHAT_PRESETS = Object.freeze({...PROVIDER_PRESETS, local: {endpoint: 'http://127.0.0.1:11434/v1'}});
// The Context size that each Chat preset starts with. The app cannot ask a provider for it. The empty key is a Chat
// model that nobody set up, which holds the server default.
const CHAT_CONTEXT = Object.freeze({'': 200000, anthropic: 200000, openai: 128000, openrouter: 128000, deepseek: 128000, gemini: 1000000, local: 4096, custom: 32000});
export let state = {papers: [], jobs: [], settings: {}};
let stateSignature = '', jobSignature = '', stateInitialized = false, stateFailed = false;
const retries = new Map(), completedImports = new Set(), downloadedExports = new Set();

// ---- Server ----
export const paperAPI = id => `/api/papers/${encodeURIComponent(id)}`;
// keepalive lets a save that starts as the page closes, such as the Reading position, finish. Fetch refuses a keepalive
// body of 64 KiB or more, such as the undo of a long Question card, so a large body goes without it.
export async function api(path, payload) {
  let response, result;
  const body = payload === undefined ? undefined : JSON.stringify(payload);
  try { response = await fetch(path, {method: body === undefined ? 'GET' : 'POST', keepalive: body !== undefined && new Blob([body]).size < 60000, headers: {Authorization: `Bearer ${token}`, ...(body === undefined ? {} : {'Content-Type': 'application/json'})}, body}); }
  catch { throw new Error('LocalXiv cannot reach its library service. Try again in a moment.'); }
  try { result = await response.json(); }
  catch { console.error('api', path, response.status); throw new Error('The library service sent a reply that LocalXiv cannot read. Try again in a moment.'); }
  if (!response.ok) { console.error('api', path, response.status); throw new Error(result.error || 'LocalXiv could not finish this request. Try again in a moment.'); }
  // A record or a Note group changed: the sidebar count and the Notes page follow.
  if (body !== undefined && /\/(?:highlights\/\w+|chat\/clear|groups|notes\/import)$/.test(path)) notesChanged();
  return result;
}
function notesChanged() { refresh(); if (nav.current?.page === 'notes') drawNotesPage(); }
// `onError` shows a request error where the reader acted; a modal sheet would cover the global notice. A cancel keeps
// the request that started its job as the job's Retry.
export async function run(path, payload, onError = notice) {
  try { notice(''); const result = await api(path, payload); if (result.job && !path.endsWith('/cancel')) retries.set(result.job.id, {path, payload}); await refresh(); return result; }
  catch (error) { onError(error.message); return null; }
}
export function fileURL(path) {
  // Resolve only a relative file within the selected paper, never an external/model URL.
  if (!selected || typeof path !== 'string' || /^(?:[a-z]+:|\/|\\)/i.test(path) || path.split(/[\\/]/).includes('..')) return null;
  const [filename, anchor = ''] = path.split('#');
  const url = new URL(`/files/${encodeURIComponent(selected)}/${filename.split('/').map(encodeURIComponent).join('/')}`, location.origin);
  url.searchParams.set('token', token); if (anchor) url.hash = anchor; return url.href;
}
// The caller debounces; the record that comes back replaces the Paper's copy in the library state.
export async function saveReading(id, patch) {
  const {reading} = await api(`${paperAPI(id)}/reading`, patch);
  const paper = state.papers.find(item => item.id === id);
  if (paper) paper.reading = reading;
  // The next poll then finds nothing new and leaves the rows alone.
  stateSignature = JSON.stringify(state.papers); drawPages();
  if (selected) syncReaderChrome(); else syncChrome();
  return reading;
}
export const aiReady = () => Boolean(state.settings?.model && state.settings?.has_key);
export const runningJob = (kind, id = selected) => state.jobs.find(job => job.kind === kind && job.payload?.paper_id === id && !TERMINAL.has(job.state));
export const summary = id => state.papers.find(paper => paper.id === id);

// ---- Notices and jobs ----
let noticeTimer;
export function notice(message, autoDismiss = false) {
  noticeTimer?.(); $('notice').replaceChildren(); $('notice').hidden = !message;
  // A status line that exists from the start reads each notice to VoiceOver; the toast only shows it.
  $('notice-live').textContent = message;
  if (!message) return;
  const heading = node('div', undefined, 'toast-heading'), close = node('button');
  close.append(icon('xmark', 'i sm'));
  close.setAttribute('aria-label', 'Dismiss notification'); close.onclick = () => { $('notice').hidden = true; };
  heading.append(node('strong', message), close); $('notice').append(heading);
  // Every notice that does not dismiss itself reports an error.
  $('notice').dataset.state = autoDismiss ? 'ready' : 'failed';
  if (autoDismiss) noticeTimer = expireToast($('notice'), () => { $('notice').hidden = true; });
}
// A failure in the Native shell, such as a PDF that does not open or a download that is not saved.
register('notice', ({text}) => notice(text));
function downloadLink(path) {
  const url = new URL(path, location.origin);
  if (url.origin !== location.origin || !url.pathname.startsWith('/files/')) return null;
  url.searchParams.set('token', token);
  const ending = url.pathname.toLowerCase().split('.').pop();
  const link = node('a', {png: 'Save PNG', pdf: 'Save PDF', md: 'Save Markdown', json: 'Save JSON'}[ending] || 'Save EPUB'); link.href = url.href; link.download = '';
  return link;
}
// The server names the file. The Native shell asks where to save it.
function download(path) {
  const link = downloadLink(path);
  if (link) { document.body.append(link); link.click(); link.remove(); }
}
function downloadFinishedExports(jobs) {
  for (const job of jobs) {
    if (job.kind !== 'export' || job.state !== 'ready' || !job.result?.download_url || !retries.has(job.id) || downloadedExports.has(job.id)) continue;
    downloadedExports.add(job.id);
    download(job.result.download_url);
  }
}
// Open on a finished Overview or Blog shows the Paper in that view.
const openJob = async (id, kind) => { await commands.run({name: 'open', id}); if (kind !== 'import' && selected === id) commands.run({name: 'view', view: kind}); };
const jobNotices = new JobNotices({target: $('jobs'), run, paperAPI, downloadLink, retries, onUnseen: () => syncChrome(), open: openJob});
let jobList = null;
register('activity', () => {
  jobNotices.unseen.clear(); syncChrome();
  jobList = new JobNotices({target: $('jobs-list'), run, paperAPI, downloadLink, retries, list: true});
  $('jobs-list').replaceChildren(); drawJobList();
  if (!$('jobs-dialog').open) { $('jobs-dialog').showModal(); $('jobs-dialog').focus(); }
});
function drawJobList() {
  if (!jobList) return;
  jobList.render(state.jobs, state.papers);
  $('jobs-empty').hidden = $('jobs-list').children.length > 0;
}
$('jobs-close').onclick = () => $('jobs-dialog').close();
$('jobs-dialog').addEventListener('close', () => { jobList = null; });
function activity() {
  const active = state.jobs.filter(job => !TERMINAL.has(job.state));
  if (!active.length) {
    const failed = state.jobs.filter(job => jobNotices.unseen.has(job.id)).length;
    // `failed` draws the line as an error, with no bar, in both renderers.
    return failed ? {label: failed === 1 ? '1 task failed' : `${failed} tasks failed`, progress: 0, count: 1, failed: true} : null;
  }
  const job = active[0], title = shortTitle(summary(job.payload?.paper_id)?.title || job.payload?.paper_id || '');
  const target = job.payload?.url ? (job.payload.url.match(/(\d{4}\.\d{4,5}(?:v\d+)?)/)?.[1] || job.payload.url) : title;
  // The ellipsis follows the verb, because the Native shell's Activity line cuts the end of a long title.
  const label = {import: `Importing… · ${target}`, overview: `Making the Overview… · ${title}`, blog: `Writing the Blog… · ${title}`,
    export: `Exporting… · ${title}`, send: `Sending to Kindle… · ${title}`}[job.kind] || 'Running a task…';
  return {label, progress: typeof job.progress === 'number' ? job.progress / 100 : null, count: active.length};
}

// ---- Reading preferences: the server settings hold them; the localStorage copy paints the first frame ----
export let prefs = storage ? readCopy(storage) : {...DEFAULTS};
let serverPrefs = '', pendingPrefs = {}, prefsTimer, prefsWrites = 0;
const systemTheme = matchMedia('(prefers-color-scheme: dark)');
function applyPrefs() {
  const root = document.documentElement, theme = resolveTheme(prefs.theme, systemTheme.matches);
  // A theme change turns transitions off for its one style change, so no button fades after the rest of the window.
  if (root.dataset.theme !== theme) {
    const still = document.head.appendChild(node('style', '*,*::before,*::after{transition:none!important}'));
    root.dataset.theme = theme; getComputedStyle(root).color; still.remove();
  }
  for (const [name, value] of Object.entries(rootProperties(prefs))) root.style.setProperty(name, value);
  for (const field of document.querySelectorAll('[data-pref]')) field.value = prefs[field.dataset.pref];
  $('pref-size-value').textContent = prefs.size + ' px';
  $('pref-size').style.setProperty('--fillp', (prefs.size - SIZES[0]) / (SIZES[1] - SIZES[0]) * 100 + '%');
  chrome.update({prefs});
  swapFigureSources(theme); styleReader();
}
function setPrefs(patch) {
  const next = normalize({...prefs, ...patch});
  const changed = Object.fromEntries(Object.entries(next).filter(([field, value]) => prefs[field] !== value));
  if (!Object.keys(changed).length) return;
  prefs = next; if (storage) writeCopy(storage, prefs); applyPrefs();
  // A slider sends many values; only the last one goes to the server.
  pendingPrefs = {...pendingPrefs, ...changed}; clearTimeout(prefsTimer);
  prefsTimer = setTimeout(async () => {
    const values = toSettings(pendingPrefs); pendingPrefs = {}; prefsWrites++;
    try { state.settings = await api('/api/settings', values); serverPrefs = JSON.stringify(fromSettings(state.settings)); } catch (error) { notice(error.message); }
    prefsWrites++;
  }, 300);
}
// `writes` is the count when the state request started: a request that overlapped a write can carry the old values.
function adoptServerPrefs(writes) {
  const next = JSON.stringify(fromSettings(state.settings));
  if (writes !== prefsWrites || next === serverPrefs || Object.keys(pendingPrefs).length) return;
  serverPrefs = next; prefs = fromSettings(state.settings); if (storage) writeCopy(storage, prefs); applyPrefs();
}
register('prefs', ({patch}) => setPrefs(patch || {}));
register('text-size', ({step}) => setPrefs({size: step ? Math.min(SIZES[1], Math.max(SIZES[0], prefs.size + Math.sign(step))) : DEFAULTS.size}));
for (const field of document.querySelectorAll('[data-pref]')) field.addEventListener('input', () => setPrefs({[field.dataset.pref]: field.type === 'range' ? Number(field.value) : field.value}));
systemTheme.addEventListener('change', applyPrefs);
// The main window and the Settings window share this origin's storage, so a change in one applies in the other at once.
addEventListener('storage', event => { if (event.key === STORAGE_KEY && storage) { prefs = readCopy(storage); applyPrefs(); } });

// ---- Chrome state outside the reader ----
// The page shows a job when the reader's view shows its progress or failure, or a search result row shows its import.
const pageShows = job => viewShows(job) || job.kind === 'import' && !$('results').hidden && results.rows.some(row => rowState(row, [], [job]).adding);
export function syncChrome() {
  if (stateInitialized) jobNotices.render(state.jobs, state.papers, pageShows);
  const entry = nav.current || {page: 'home'}, counts = {all: state.papers.length, new: 0, reading: 0, read: 0, notes: state.notes || 0};
  for (const paper of state.papers) counts[readingState(paper)]++;
  const recent = state.papers.filter(paper => paper.reading).sort((a, b) => b.reading.opened_at - a.reading.opened_at).slice(0, 5)
    .map(paper => ({id: paper.id, title: shortTitle(paper.title || paper.id), current: paper.id === selected}));
  const selectedRow = entry.page === 'home' ? 'home' : entry.page === 'library' ? entry.filter : entry.page === 'notes' ? 'notes' : null;
  const patch = {mode: entry.page, sidebar: {selected: selectedRow, counts, recent}, activity: activity(), search: {query: entry.page === 'search' ? entry.query : ''}};
  if (entry.page === 'home') Object.assign(patch, {title: 'Home', subtitle: ''});
  if (entry.page === 'library') {
    const shown = entry.filter === 'all' ? counts.all : counts[entry.filter];
    Object.assign(patch, {title: 'Library', subtitle: `${FILTERS[entry.filter]} · ${shown} ${shown === 1 ? 'Paper' : 'Papers'}`});
  }
  if (entry.page === 'search') Object.assign(patch, {title: 'Search', subtitle: entry.query.trim()});
  if (entry.page === 'notes') Object.assign(patch, {title: 'Notes', subtitle: `${counts.notes} ${counts.notes === 1 ? 'Highlight or Note' : 'Highlights and Notes'}`});
  if (entry.page !== 'reader') { patch.views = null; patch.sidebar.reader = null; patch.actions = {share: [], more: []}; }
  chrome.update(patch);
}

// ---- Pages and history ----
const PAGES = {home: 'home', library: 'library', search: 'results', notes: 'notes-page', reader: 'reader-page'};
export function showPage(page) {
  for (const [name, id] of Object.entries(PAGES)) $(id).hidden = name !== page;
  if (page !== 'reader') closeReader();
}
function show(entry) {
  showPage(entry.page);
  if (entry.page === 'home') drawHome();
  if (entry.page === 'library') drawLibrary();
  if (entry.page === 'notes') drawNotesPage();
  // Back or Forward reruns a text search but never imports a link again.
  if (entry.page === 'search') runSearch({query: entry.query, submit: inputKind(entry.query.trim()) === 'search'});
  if (entry.page === 'reader') { openPaper(entry.id, {position: entry.position, scroll: entry.scroll}); return; }
  syncChrome();
  window.scrollTo(0, entry.scroll || 0);
}
nav.onShow(show);
function go(entry) {
  const current = nav.current;
  if (current && JSON.stringify({...current, scroll: undefined}) === JSON.stringify({...entry, scroll: undefined})) return show(current);
  nav.push(entry); show(entry);
}
register('go', ({to}) => go(to === 'home' ? {page: 'home'} : to === 'notes' ? {page: 'notes'} : FILTERS[to] ? {page: 'library', filter: to} : {page: 'home'}));
// A localxiv://open link names a passage; the Paper view goes there once the Paper is open.
register('open', async ({id, passage}) => {
  await openPaper(id);
  const href = passage && selected === id && detail?.paper?.passages?.find(item => item.id === passage)?.href;
  if (href) goPassage(href);
});
register('add', () => { go({page: 'home'}); $('home-url').focus(); });
function drawPages() {
  const page = nav.current?.page;
  if (page === 'home') drawHome();
  if (page === 'library') drawLibrary();
  if (page === 'notes') drawNotesPage();
}

// ---- Home and the Library ----
const requestOpen = id => commands.run({name: 'open', id});
const rowHandlers = {onOpen: paper => requestOpen(paper.id), onMenu: (paper, event) => paperMenu(paper, event)};
// The last section needs chapter titles, which only the Paper detail holds.
const chapterTitles = new Map();
function lastSection(paper) {
  const reading = paper.reading || {};
  if (reading.view === 'overview' || reading.view === 'blog') return VIEW_LABELS[reading.view];
  const cached = chapterTitles.get(paper.id);
  if (!cached || cached.digest !== paper.document_digest) {
    if (!cached?.pending) {
      chapterTitles.set(paper.id, {pending: true});
      api(paperAPI(paper.id)).then(({paper: full}) => {
        chapterTitles.set(paper.id, {digest: full.document_digest, chapters: full.chapters || []}); drawPages();
      }).catch(() => chapterTitles.set(paper.id, {digest: paper.document_digest, chapters: []}));
    }
    return 'Paper';
  }
  return cached.chapters.find(chapter => chapter.path === reading.chapter)?.title || 'Paper';
}
function resumeCard(paper, {eyebrow = false} = {}) {
  const card = node('button', undefined, 'resume'), meta = node('span', undefined, 'meta');
  card.type = 'button'; card.dataset.id = paper.id;
  if (eyebrow) meta.append(node('span', 'Continue reading', 'eyebrow'));
  meta.append(Object.assign(node('span', paper.title || paper.id, 'title'), {title: paper.title || paper.id}), node('span', authorList(authorNames(paper.authors), 3), 'authors'), node('span', lastSection(paper), 'where'));
  for (const span of meta.children) span.style.display = 'block';
  card.append(meta);
  if (eyebrow) card.append(node('span', 'Resume', 'btn-accent'));
  card.onclick = () => requestOpen(paper.id);
  card.oncontextmenu = event => { event.preventDefault(); paperMenu(paper, event); };
  return card;
}
const byOpened = (a, b) => (b.reading?.opened_at || 0) - (a.reading?.opened_at || 0);
function drawHome() {
  const papers = state.papers, onlySample = papers.every(paper => paper.id === SAMPLE_ID);
  const continuing = papers.filter(paper => readingState(paper) === 'reading').sort(byOpened).slice(0, 3);
  const recent = [...papers].sort((a, b) => (b.added_at || 0) - (a.added_at || 0)).slice(0, 5);
  $('home-welcome').hidden = !onlySample || !papers.length && !stateInitialized;
  const sample = papers.some(paper => paper.id === SAMPLE_ID);
  $('welcome-sample').hidden = !sample;
  $('welcome-next').textContent = sample ? 'Search for a paper above, or open the sample paper to try the reader.' : 'Search for a paper above.';
  $('home-continue').hidden = !continuing.length;
  replaceRows($('home-continue-list'), continuing.map(paper => resumeCard(paper)));
  $('home-recent').hidden = onlySample || !recent.length;
  replaceRows($('home-recent-list'), recent.map(paper => libraryRow(paper, rowHandlers)));
}
$('welcome-sample').onclick = () => requestOpen(SAMPLE_ID);
const SORTS = {
  added: (a, b) => (b.added_at || 0) - (a.added_at || 0),
  read: byOpened,
  title: (a, b) => (a.title || a.id).localeCompare(b.title || b.id),
  published: (a, b) => (arxivDate(b.arxiv_id || b.id)?.key || 0) - (arxivDate(a.arxiv_id || a.id)?.key || 0),
};
$('library-sort').value = SORTS[stored('localxiv-sort')] ? stored('localxiv-sort') : 'added';
$('library-sort').onchange = () => { store('localxiv-sort', $('library-sort').value); drawLibrary(); };
function drawLibrary() {
  // With no state yet, the list stays empty while the first state request runs, and says so after it fails.
  if (!stateInitialized) {
    if (!stateFailed) return;
    const failed = node('div', undefined, 'empty'), again = node('button', 'Try Again', 'btn-quiet');
    again.type = 'button'; again.onclick = refresh;
    failed.append(node('strong', 'LocalXiv could not load your library'), again);
    return replaceRows($('library-list'), [failed]);
  }
  const filter = nav.current?.filter || 'all';
  const papers = state.papers.filter(paper => filter === 'all' || readingState(paper) === filter).sort(SORTS[$('library-sort').value]);
  const last = filter === 'all' && state.papers.filter(paper => readingState(paper) === 'reading').sort(byOpened)[0];
  replaceRows($('library-continue'), last ? [resumeCard(last, {eyebrow: true})] : []);
  const [title, hint] = {all: ['No Papers', 'Papers you add appear here. Search for one, or paste an arXiv link.'], new: ['No New Papers', 'Every paper here has been opened.'],
    reading: ['No Papers in Progress', 'Open a paper to start reading.'], read: ['No Papers Marked as Read', 'Use Mark as Read in a paper’s More menu.']}[filter];
  const empty = node('div', undefined, 'empty'), action = filter === 'all' ? node('button', 'Find a Paper', 'btn-accent') : node('button', 'Show All Papers', 'btn-quiet');
  action.type = 'button'; action.onclick = () => filter === 'all' ? commands.run({name: 'add'}) : go({page: 'library', filter: 'all'});
  empty.append(node('strong', title), node('p', hint), action);
  replaceRows($('library-list'), papers.length ? papers.map(paper => libraryRow(paper, rowHandlers)) : [empty]);
}
// A redraw makes new rows, so the selection and focus move to the new row of the same Paper.
function replaceRows(list, rows) {
  const selectedID = list.querySelector('.is-selected')?.dataset.id, focusedID = list.contains(document.activeElement) ? document.activeElement.dataset.id : undefined;
  list.replaceChildren(...rows);
  const find = id => id && rows.find(row => row.dataset?.id === id);
  find(selectedID)?.classList.add('is-selected');
  find(focusedID)?.focus({preventScroll: true});
}
// The arrow keys move the selection through a list of rows; Return opens the selected row's Paper.
for (const list of [$('library-list'), $('home-recent-list'), $('notes-list')]) {
  list.addEventListener('focusin', event => { const row = event.target.closest('.prow'); if (row) for (const item of list.querySelectorAll('.prow')) item.classList.toggle('is-selected', item === row); });
  // WebKit does not focus a clicked button and clears focus on a press, so the press focuses the row itself. The row
  // then shows as selected before its Paper opens or its menu shows.
  list.addEventListener('mousedown', event => { const row = event.target.closest('.prow'); if (row) { event.preventDefault(); row.focus({preventScroll: true}); } });
  list.addEventListener('keydown', event => {
    if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return;
    const rows = [...list.querySelectorAll('.prow, .an-go, .an-paper button')], index = rows.indexOf(document.activeElement);
    const next = {ArrowDown: Math.min(rows.length - 1, index + 1), ArrowUp: Math.max(0, index - 1), Home: 0, End: rows.length - 1}[event.key];
    rows[next]?.focus(); rows[next]?.scrollIntoView({block: 'nearest'}); event.preventDefault();
  });
}

// ---- Paper actions: the Library context menu, and More with its Share submenu ----
function paperMenu(paper, event) {
  const read = readingState(paper) === 'read';
  const point = event.clientX || event.clientY ? event : event.currentTarget || event.target;
  openMenu(point, [
    {id: 'open', label: 'Open', enabled: true},
    {id: read ? 'mark-unread' : 'mark-read', label: read ? 'Mark as Unread' : 'Mark as Read', enabled: true, separatorBefore: true},
    {id: 'copy-link', label: 'Copy arXiv Link', enabled: Boolean(paper.arxiv_id), separatorBefore: true},
    {id: 'copy-bibtex', label: 'Copy BibTeX', enabled: true},
    {id: 'remove', label: 'Remove from Library…', enabled: true, role: 'destructive', separatorBefore: true},
  ], id => paperAction(paper, id, point instanceof Element ? point : null));
}
export async function copy(text, what) {
  try { await navigator.clipboard.writeText(text); }
  catch {
    const area = node('textarea'); area.value = text; area.style.position = 'fixed'; area.style.opacity = '0';
    document.body.append(area); area.select();
    const copied = document.execCommand('copy'); area.remove();
    if (!copied) { notice(`${what} could not be copied.`); return; }
  }
  notice(`${what} copied.`, true);
}
// "Mark as Unread" makes the Paper New again: the server deletes its record, with its Reading position.
function paperAction(paper, id, returnFocus) {
  const actions = {
    open: () => requestOpen(paper.id),
    'mark-read': () => saveReading(paper.id, {state: 'read'}).catch(error => notice(error.message)),
    'mark-unread': () => saveReading(paper.id, {state: 'new'}).catch(error => notice(error.message)),
    'copy-link': () => copy(`https://arxiv.org/abs/${baseID(paper.arxiv_id)}`, 'arXiv link'),
    'copy-bibtex': () => copy(bibtex(paper), 'BibTeX'),
    remove: () => confirmRemove(paper, returnFocus),
  };
  actions[id]?.();
}
// A record with a question is a Question card, as the margin names it when it goes.
function recordCounts(records) {
  const count = {Highlight: 0, Note: 0, 'Question card': 0};
  for (const {kept, turns, note} of records) count[!kept || turns.length ? 'Question card' : note ? 'Note' : 'Highlight']++;
  const parts = Object.entries(count).filter(([, n]) => n).map(([word, n]) => `${n} ${word}${n === 1 ? '' : 's'}`);
  return parts.length ? `This Paper has ${new Intl.ListFormat('en').format(parts)}.` : '';
}
function confirmRemove(paper, returnFocus) {
  const dialog = $('remove-paper-dialog');
  dialog.dataset.paperId = paper.id;
  $('remove-paper-title').textContent = `Remove “${shortTitle(paper.title || paper.id)}”?`;
  $('remove-paper-counts').textContent = ''; $('remove-paper-error').textContent = '';
  // The counts come with the Paper's records. The line stays empty when they do not come.
  api(paperAPI(paper.id)).then(({highlights = []}) => {
    if (dialog.open && dialog.dataset.paperId === paper.id) $('remove-paper-counts').textContent = recordCounts(highlights);
  }).catch(() => {});
  dialog.addEventListener('close', () => { if (returnFocus?.isConnected) returnFocus.focus(); }, {once: true});
  // The focus goes on the dialog, so Return confirms nothing and the reader clicks Remove Paper.
  dialog.showModal(); dialog.focus();
}
$('remove-paper-cancel').onclick = () => $('remove-paper-dialog').close();
// The dialog stays open, so Remove is a separate click.
$('remove-paper-export').onclick = () => download(`/files/${encodeURIComponent($('remove-paper-dialog').dataset.paperId)}/notes.md`);
// A second click while the request runs does nothing, and the button keeps the focus.
$('remove-paper-confirm').onclick = async () => {
  const dialog = $('remove-paper-dialog'), id = dialog.dataset.paperId, button = $('remove-paper-confirm');
  if (button.ariaBusy === 'true') return;
  button.ariaBusy = 'true'; $('remove-paper-error').textContent = '';
  try {
    await api(`${paperAPI(id)}/remove`, {});
    dialog.close();
    if (selected === id) go({page: 'library', filter: 'all'});
    if (refreshing) await refreshing;
    await refresh();
    notice('Paper removed from your library.', true);
  } catch (error) {
    $('remove-paper-error').textContent = error.message;
    await refresh();
  } finally { button.ariaBusy = 'false'; }
};
function exportView(profile, notes = false) { if (selected) run(`${paperAPI(selected)}/export`, {kind: activeTab, profile, notes}); }
// The Highlights and Notes of the Paper as Markdown (papers/notes_export.py), as a file or as text. WebKit refuses a
// clipboard write after an await, so the write starts at the click and waits for the text. `report` takes notice()'s
// arguments; All Notes, a modal dialog, says the result in its own status line.
export const exportRecords = () => download(fileURL('notes.md'));
export function copyRecords(report = notice) {
  const text = fetch(fileURL('notes.md')).then(response => response.ok ? response.text() : Promise.reject(new Error()))
    .then(value => new Blob([value], {type: 'text/plain'}));
  navigator.clipboard.write([new ClipboardItem({'text/plain': text})])
    .then(() => report('Highlights and Notes copied.', true), () => report('Highlights and Notes could not be copied.', false));
}
// Whether the Paper has a Highlight, Note, or Question card that the server keeps: the margin's marks once it has
// mounted for this Paper (a draft has no record yet), else the records that came with the Paper.
const hasRecords = () => paperId === selected ? [...marks.values()].some(mark => !mark.draft) : detail?.highlights?.length > 0;
// Whether Clear Chat has something to clear: an answer that runs (also a draft's first one), an open Question card,
// or turns.
const hasChat = () => paperId === selected
  ? [...marks.values()].some(mark => mark.pending || mark.record.turns.length > 0 || !mark.draft && !mark.record.kept)
  : Boolean(detail?.highlights?.some(record => !record.kept || record.turns.length > 0));
register('action', ({id, colour}) => {
  // A menu or a key can name an action that the current view disables.
  if (!detail || !Object.values(readerActions()).flat().some(action => action.id === id && action.enabled)) return;
  const paper = {...summary(selected), ...detail.paper}, generation = detail[activeTab];
  const actions = {
    'export-epub': () => exportView('kindle'), 'export-epub-notes': () => exportView('kindle', true), 'export-pdf': () => exportView('pdf'), 'export-png': () => exportView('png'),
    'export-svg': () => { const link = node('a'); link.href = fileURL(generation?.figures?.[0]?.svg_source); link.download = ''; document.body.append(link); link.click(); link.remove(); },
    'send-kindle': openKindle,
    // A link click, unlike window.open, reaches the Native shell's navigation policy.
    'open-pdf': () => $('reader-pdf').click(), 'open-arxiv': () => $('reader-arxiv').click(),
    regenerate: () => generate(activeTab),
    'ask-paper': askPaper, 'all-notes': showAllNotes, 'clear-chat': clearChat, 'copy-notes': copyNotes,
    'export-records': exportRecords, 'copy-records': copyRecords,
    highlight: () => selectionCommand('highlight', colour), 'add-note': () => selectionCommand('add-note'),
    ask: () => selectionCommand('ask'), explain: () => selectionCommand('explain'),
  };
  (actions[id] || (() => paperAction(paper, id, null)))();
});
export function readerActions() {
  const paper = detail.paper, view = activeTab, generation = view === 'paper' ? null : detail[view];
  const ready = view === 'paper' || Boolean(generation), read = readingState(summary(selected) || {}) === 'read';
  // The selection commands and a question about the whole Paper need the Paper view's text, which a PDF does not have.
  const text = view === 'paper' && paper.format !== 'pdf', offer = offerVersion();
  return {
    share: [
      {id: 'export-epub', label: 'Export EPUB', enabled: ready && !(view === 'paper' && paper.format === 'pdf')},
      {id: 'export-epub-notes', label: 'Export EPUB with Notes', enabled: text && hasRecords()},
      {id: 'export-records', label: 'Export Highlights and Notes…', enabled: hasRecords()},
      {id: 'export-pdf', label: 'Export PDF', enabled: ready},
      {id: 'export-png', label: 'Export PNG', enabled: view === 'overview' && ready},
      {id: 'export-svg', label: 'Export Editable SVG', enabled: Boolean(fileURL(generation?.figures?.[0]?.svg_source))},
      {id: 'send-kindle', label: 'Send to Kindle…', enabled: true, separatorBefore: true},
      {id: 'copy-link', label: 'Copy arXiv Link', enabled: Boolean(paper.arxiv_id), separatorBefore: true},
      {id: 'copy-bibtex', label: 'Copy BibTeX', enabled: true},
      {id: 'copy-records', label: 'Copy Highlights and Notes', enabled: hasRecords()},
    ],
    more: [
      {id: 'highlight', label: 'Highlight', enabled: text}, {id: 'add-note', label: 'Add Note…', enabled: text},
      {id: 'ask', label: 'Ask…', enabled: text}, {id: 'explain', label: 'Explain', enabled: text},
      // A question about the whole Paper anchors to the top passage of the Paper view.
      {id: 'ask-paper', label: 'Ask About the Paper…', enabled: text, separatorBefore: true},
      {id: 'all-notes', label: 'All Notes', enabled: true},
      {id: 'clear-chat', label: 'Clear Chat', enabled: text && hasChat()},
      {id: 'copy-notes', label: offer ? `Copy Notes from v${versionOf(offer.id)}` : 'Copy Notes from an Older Version', enabled: text && Boolean(offer) && !hasRecords()},
      {id: read ? 'mark-unread' : 'mark-read', label: read ? 'Mark as Unread' : 'Mark as Read', enabled: true, separatorBefore: true},
      {id: 'open-pdf', label: 'Open PDF', enabled: true, separatorBefore: true},
      {id: 'open-arxiv', label: 'Open on arXiv', enabled: Boolean(paper.arxiv_id)},
      {id: 'regenerate', label: view === 'paper' ? 'Regenerate' : `Regenerate ${VIEW_LABELS[view]}`, enabled: Boolean(generation) && aiReady() && !runningJob(view), separatorBefore: true},
      {id: 'remove', label: 'Remove from Library…', enabled: true, role: 'destructive', separatorBefore: true},
    ],
  };
}

// ---- Send to Kindle ----
function openKindle() {
  $('artifact-kind').value = activeTab;
  $('kindle-destination').textContent = state.settings?.kindle_email ? 'To ' + state.settings.kindle_email : 'Add your Send-to-Kindle email in Settings › Kindle.';
  $('kindle-settings').hidden = Boolean(state.settings?.kindle_email); $('kindle-error').textContent = '';
  updateDeliveryControls(); $('kindle-dialog').showModal();
}
function updateDeliveryControls() {
  const pdf = detail?.paper?.format === 'pdf';
  $('artifact-both').disabled = pdf;
  if (pdf && $('artifact-kind').value === 'both') $('artifact-kind').value = 'paper';
  const kind = $('artifact-kind').value, sendPDF = pdf && kind === 'paper';
  $('profile').hidden = $('profile-label').hidden = sendPDF;
  $('send').disabled = !state.settings?.kindle_email || (kind === 'overview' && !detail?.overview) || (['blog', 'both'].includes(kind) && !detail?.blog);
  $('send').textContent = sendPDF ? 'Send PDF' : 'Send';
  $('kindle-notes-label').hidden = pdf || !['paper', 'both'].includes(kind) || !hasRecords();
  $('kindle-format-note').textContent = sendPDF ? detail.paper.report.warning : 'LocalXiv sends the selected document as an EPUB.';
}
$('artifact-kind').onchange = updateDeliveryControls;
$('kindle-cancel').onclick = () => $('kindle-dialog').close();
$('kindle-settings').onclick = () => { $('kindle-dialog').close(); openSettings('kindle'); };
$('kindle-form').onsubmit = async event => {
  event.preventDefault();
  $('kindle-error').textContent = '';
  const showError = message => { $('kindle-error').textContent = message; };
  if (selected && await run(`${paperAPI(selected)}/send`, {kind: $('artifact-kind').value, profile: $('profile').value, notes: !$('kindle-notes-label').hidden && $('kindle-notes').checked}, showError)) $('kindle-dialog').close();
};

// ---- Search: the toolbar field (web or native) shows the results page live; Home keeps Suggestions ----
// With no connection, an import from a link also fails, so that message names what still works.
const downMessage = () => navigator.onLine ? 'Search is down. You can still paste a link.' : 'No internet connection. Your library still opens.';
async function paperSearch(query, limit) {
  try { return await api('/api/search', {query, limit}); } catch { return {results: [], error: 'unavailable'}; }
}
let results = {query: '', remote: [], rows: [], request: 0, timer: 0, updates: []};
function leaveSearch() { if (nav.current?.page !== 'search') return; if (nav.previous) nav.step(-1); else go({page: 'home'}); }
// `link` comes from a localxiv://import URL: the text is always imported, so the service checks it.
function runSearch({query = '', submit = false, link = false}) {
  const text = String(query), trimmed = text.trim(), kind = link ? 'import' : inputKind(trimmed), mine = ++results.request;
  clearTimeout(results.timer);
  if (!trimmed) return leaveSearch();
  if (nav.current?.page === 'search') nav.replace({page: 'search', query: text}); else nav.push({page: 'search', query: text});
  showPage('search'); syncChrome();
  if (results.query !== trimmed) { results.query = trimmed; $('results-title').textContent = kind === 'import' ? 'Add a paper' : `Results for “${trimmed}”`; }
  if (kind === 'import') {
    results.remote = []; drawResults(submit ? 'Adding the paper…' : 'Press Return to add this paper.');
    const showError = message => drawResults(message, {retry: () => runSearch({query: text, submit: true, link})});
    if (submit) run('/api/import', {url: trimmed}, showError).then(result => { if (result && nav.current?.page === 'search') leaveSearch(); });
    return;
  }
  const live = submit || trimmed.length >= 3 && state.settings.search_suggestions !== false;
  if (!live) { results.remote = []; drawResults('Press Return to search arXiv.'); return; }
  drawResults('Searching…', {busy: true});
  results.timer = setTimeout(async () => {
    const response = await paperSearch(trimmed, submit ? 20 : 8);
    // A newer keystroke started another search; its rows win.
    if (mine !== results.request) return;
    results.remote = response.results;
    drawResults(response.error ? downMessage() : '', response.error ? {retry: () => runSearch({query: text, submit: true})} : {});
  }, submit ? 0 : 400);
}
register('search', runSearch);
// `busy` dims the arXiv rows while they are still the previous query's; `retry` makes the status a problem row.
function drawResults(status, {busy = false, retry} = {}) {
  const rows = searchRows(state.papers, results.query, results.remote, 5, 25), local = rows.filter(row => row.id), remote = rows.filter(row => !row.id);
  results.updates = []; results.rows = rows;
  $('results-library').replaceChildren(...local.map(resultRow));
  $('results-list').replaceChildren(...remote.map(resultRow));
  $('results-library-title').hidden = !local.length; $('results-remote-title').hidden = !remote.length;
  const text = status || (rows.length ? '' : 'No papers found. Papers from the last few days may not appear yet. If you have the arXiv link, paste it instead.');
  const again = node('button', 'Try Again', 'btn-quiet'), arxiv = node('a', 'Search arXiv.org');
  again.type = 'button'; again.onclick = retry;
  arxiv.href = `https://arxiv.org/search/?query=${encodeURIComponent(results.query)}&searchtype=all`; arxiv.target = '_blank'; arxiv.rel = 'noopener noreferrer';
  $('results-status').replaceChildren(...(retry ? [icon('exclaim'), node('span', text), again] : status ? [text] : text ? [text, ' ', arxiv] : []));
  $('results-status').classList.toggle('problem', Boolean(retry));
  $('results-list').setAttribute('aria-busy', String(busy));
  $('results-credit').hidden = !remote.length;
}
function resultRow(row) {
  const item = node('article', undefined, 'result'), text = node('div'), action = node('button'), mark = node('span', 'In library', 'library-mark');
  const side = node('div', undefined, 'result-side'), adding = node('span', undefined, 'adding'), error = node('p', undefined, 'error');
  error.setAttribute('role', 'alert');
  adding.append(node('span', 'Adding…'), node('progress'));
  const meta = node('p', [row.year, row.arxiv_id].filter(Boolean).join(' · '), 'result-meta');
  action.type = 'button';
  meta.append(mark); text.append(node('h3', row.title), node('p', authorList(row.id ? authorNames(row.authors) : row.authors, 6), 'search-authors'), meta);
  if (row.abstract) {
    const abstract = node('p', row.abstract, 'result-abstract');
    abstract.tabIndex = 0; abstract.setAttribute('role', 'button'); abstract.setAttribute('aria-expanded', 'false');
    abstract.onclick = () => abstract.setAttribute('aria-expanded', String(abstract.getAttribute('aria-expanded') === 'false'));
    abstract.onkeydown = event => { if (['Enter', ' '].includes(event.key)) { event.preventDefault(); abstract.onclick(); } };
    text.append(abstract);
  }
  // Rows update in place from state.papers and state.jobs, so focus and open abstracts survive a refresh.
  const update = () => {
    const {paper, adding: busy} = rowState(row, state.papers, state.jobs);
    action.hidden = busy; adding.hidden = !busy; item.setAttribute('aria-busy', String(busy));
    action.textContent = paper ? 'Open' : 'Add'; action.className = paper ? 'btn-quiet' : 'btn-tinted';
    action.setAttribute('aria-label', `${action.textContent} ${row.title}`); mark.hidden = !paper;
    action.onclick = () => {
      error.textContent = '';
      if (paper) requestOpen(paper.id); else run('/api/import', {url: 'https://arxiv.org/abs/' + row.arxiv_id}, message => { error.textContent = message; });
    };
  };
  update(); results.updates.push(update); side.append(action, adding); item.append(text, side, error);
  return item;
}
// The Home field: the input rules, Suggestions, keys, and the ARIA combobox.
function bindSearch(form) {
  const input = form.querySelector('input'), popup = node('div', undefined, 'suggestions'), list = node('div'), note = node('p'), credit = node('p', $('results-credit').textContent);
  const hint = $('home-hint'), help = hint.textContent;
  const showHint = (message = help) => { hint.textContent = message; hint.classList.toggle('error', message !== help); };
  let rows = [], remote = [], down = false, active = -1, request = 0, timer;
  list.id = input.id + '-suggestions'; list.setAttribute('role', 'listbox'); list.setAttribute('aria-label', 'Suggestions');
  popup.hidden = true; popup.append(list, note, credit); form.append(popup);
  for (const [name, value] of [['role', 'combobox'], ['aria-autocomplete', 'list'], ['aria-controls', list.id], ['aria-expanded', 'false'], ['autocomplete', 'off']]) input.setAttribute(name, value);
  // The pointer and the arrow keys move one highlight. A pointer move does not scroll the list under the pointer.
  const highlight = (index, {scroll = true} = {}) => {
    active = index;
    for (const [at, option] of [...list.children].entries()) option.setAttribute('aria-selected', String(at === index));
    if (index < 0) input.removeAttribute('aria-activedescendant');
    else { input.setAttribute('aria-activedescendant', list.children[index].id); if (scroll) list.children[index].scrollIntoView({block: 'nearest'}); }
  };
  const draw = query => {
    rows = searchRows(state.papers, query, remote, 3, 8);
    list.replaceChildren(...rows.map((row, index) => {
      const option = node('div', undefined, 'suggestion'), meta = node('span', [row.year, row.arxiv_id].filter(Boolean).join(' · '), 'suggestion-meta');
      option.id = `${list.id}-${index}`; option.setAttribute('role', 'option');
      if (rowState(row, state.papers, []).paper) meta.append(node('span', 'In library', 'library-mark'));
      option.append(node('span', row.title, 'suggestion-title'), node('span', authorList(row.id ? authorNames(row.authors) : row.authors, 3), 'search-authors'), meta);
      option.onclick = () => choose(row);
      // WebKit sends a mousemove with no movement when the list scrolls or opens under a still pointer. Only a real move counts.
      option.onmousemove = event => { if ((event.movementX || event.movementY) && active !== index) highlight(index, {scroll: false}); };
      return option;
    }));
    note.hidden = !down; note.textContent = downMessage(); credit.hidden = !rows.some(row => !row.id);
    popup.hidden = !rows.length && !down; input.setAttribute('aria-expanded', String(!popup.hidden));
    highlight(Math.min(active, rows.length - 1));
  };
  // Closing also drops a Suggestions response still on its way.
  const close = () => { clearTimeout(timer); request++; remote = []; down = false; popup.hidden = true; input.setAttribute('aria-expanded', 'false'); highlight(-1); };
  // A failed import keeps the text in the field.
  const choose = async row => {
    const paper = rowState(row, state.papers, state.jobs).paper;
    close();
    if (paper) { input.value = ''; requestOpen(paper.id); }
    else if (await run('/api/import', {url: 'https://arxiv.org/abs/' + row.arxiv_id}, showHint)) input.value = '';
  };
  input.oninput = () => {
    showHint();
    const query = input.value.trim();
    if (inputKind(query) !== 'search') return close();
    clearTimeout(timer); const mine = ++request, live = query.length >= 3 && state.settings.search_suggestions !== false;
    if (!live) { remote = []; down = false; }
    active = -1; draw(query);
    if (live) timer = setTimeout(async () => {
      const response = await paperSearch(query, 8);
      // The rows change under the highlight, so keeping its index would point at another Paper.
      if (mine === request) { remote = response.results; down = Boolean(response.error); active = -1; draw(query); if (down) showHint(downMessage()); }
    }, 400);
  };
  input.onkeydown = event => {
    if (popup.hidden || !['ArrowDown', 'ArrowUp', 'Escape'].includes(event.key)) return;
    event.preventDefault(); event.stopPropagation(); // Escape would also clear a search field.
    const count = rows.length;
    if (event.key === 'Escape') close();
    else if (count) highlight(event.key === 'ArrowDown' ? (active + 2) % (count + 1) - 1 : (active + count + 1) % (count + 1) - 1);
  };
  // WebKit does not focus a clicked button, so without this Search would close the list and lose the highlight.
  popup.onmousedown = form.querySelector('button').onmousedown = event => event.preventDefault();
  form.addEventListener('focusout', event => { if (!form.contains(event.relatedTarget)) close(); });
  form.onsubmit = async event => {
    event.preventDefault();
    const row = rows[active], text = input.value.trim(), kind = inputKind(text);
    close();
    if (row) choose(row);
    else if (kind === 'search') { input.value = ''; commands.run({name: 'search', query: text, submit: true}); }
    else if (kind === 'import' && await run('/api/import', {url: text}, showHint)) input.value = '';
  };
}
bindSearch($('home-form'));

// ---- Settings: one view with panes, a dialog in the main window, or the whole page in ?panel=settings ----
const PANES = ['general', 'reading', 'ai', 'chat', 'kindle', 'search', 'help'];
let settingsPane = 'general';
function showPane(pane) {
  settingsPane = PANES.includes(pane) ? pane : settingsPane;
  for (const section of document.querySelectorAll('.pane')) section.hidden = section.dataset.pane !== settingsPane;
  for (const button of document.querySelectorAll('.settings-panes button')) {
    if (button.dataset.pane === settingsPane) button.setAttribute('aria-current', 'page'); else button.removeAttribute('aria-current');
  }
}
for (const button of document.querySelectorAll('.settings-panes button')) button.onclick = () => showPane(button.dataset.pane);
const normalizedEndpoint = endpoint => (endpoint || '').trim().replace(/\/+$/, '');
// A prefix picks the fields of the AI pane (''), the Setup dialog ('setup-'), or the Chat pane ('chat-').
const providerControls = prefix => ({preset: $(prefix + 'provider-preset'), endpoint: $(prefix + 'endpoint'), custom: $(prefix + 'custom-endpoint'), limits: $(prefix + 'provider-limits'), presets: prefix === 'chat-' ? CHAT_PRESETS : PROVIDER_PRESETS});
function renderProvider(prefix, endpoint) {
  const fields = providerControls(prefix), normalized = normalizedEndpoint(endpoint);
  const match = Object.entries(fields.presets).find(([, value]) => normalizedEndpoint(value.endpoint) === normalized);
  // Chat starts with no provider, so a save from another pane does not choose one.
  const none = prefix === 'chat-' ? '' : 'openai';
  fields.preset.value = match ? match[0] : normalized ? 'custom' : none;
  fields.endpoint.value = match ? match[1].endpoint : normalized ? endpoint : fields.presets[none]?.endpoint || '';
  fields.endpoint.dataset.provider = fields.preset.value;
  if (fields.preset.value === 'custom') fields.endpoint.dataset.customValue = fields.endpoint.value;
  updateProviderDetails(prefix);
}
function updateProviderDetails(prefix) {
  const fields = providerControls(prefix), preset = fields.presets[fields.preset.value];
  fields.custom.hidden = fields.preset.value !== 'custom';
  if (!fields.limits) return;
  const limits = state.provider_limits?.[preset ? new URL(preset.endpoint).hostname : 'custom'];
  fields.limits.textContent = limits ? 'Automatic limit: ' + limits + '. Paper input is not capped.' : '';
}
function changeProvider(prefix) {
  const fields = providerControls(prefix), before = fields.endpoint.dataset.provider;
  if (before === 'custom') fields.endpoint.dataset.customValue = fields.endpoint.value;
  const preset = fields.presets[fields.preset.value];
  fields.endpoint.value = preset?.endpoint || fields.endpoint.dataset.customValue || '';
  fields.endpoint.dataset.provider = fields.preset.value;
  updateProviderDetails(prefix);
  $(prefix + 'connection-status').textContent = '';
  if (prefix === 'setup-') updateSetupKeyStatus();
  if (prefix === 'chat-') { followChatContext(before); showChat(); }
}
// A Context size that the reader typed stays. One that still holds the previous provider's default follows the new one.
function followChatContext(before) {
  const context = $('chat-context');
  if (Number(context.value) === CHAT_CONTEXT[before]) context.value = CHAT_CONTEXT[$('chat-provider-preset').value];
}
const connectionEndpoint = prefix => providerControls(prefix).endpoint.value.trim();
const KEY_SAVED = 'A key is saved in macOS Keychain. Leave blank to keep it.', KEY_NONE = 'No key saved. LocalXiv keeps keys in macOS Keychain.';
function fillSettings() {
  const settings = state.settings || {};
  $('connection-status').textContent = ''; settingsError('');
  renderProvider('', settings.endpoint || PROVIDER_PRESETS.openai.endpoint);
  $('model').value = settings.model || ''; $('kindle-email').value = settings.kindle_email || '';
  $('chat-connection-status').textContent = '';
  renderProvider('chat-', settings.chat_endpoint);
  $('chat-model').value = settings.chat_model || ''; $('chat-reasoning').value = settings.chat_reasoning || 'low';
  $('chat-context').value = settings.chat_context || CHAT_CONTEXT[''];
  // Any other stored value reads as Auto: true or false from before the levels, and the retired Off.
  $('overview-reasoning').value = ['low', 'medium', 'high'].includes(settings.overview_reasoning) ? settings.overview_reasoning : 'auto';
  $('overview-language').value = settings.overview_language || 'casual'; $('overview-length').value = settings.overview_length || 'medium';
  $('auto-summary').checked = Boolean(settings.auto_summary); $('auto-send').checked = Boolean(settings.auto_send);
  $('resume-reading').checked = Boolean(settings.resume_reading); $('open-imports').checked = settings.open_imports !== false;
  $('search-suggestions').checked = settings.search_suggestions !== false;
  clearKeys();
  showKeyStatus();
  const missing = Object.entries(state.dependencies || {}).filter(([, available]) => !available).map(([name]) => name);
  $('dependencies').textContent = missing.length ? `Not installed: ${missing.join(', ')}. Install these tools before converting papers.` : 'All conversion tools are available.';
  savedSettings = JSON.stringify(settingsPayload());
}
// The placeholder asks for a key only when none is saved; the status line says how to keep a saved one.
function showKeyStatus() {
  for (const [field, status, saved] of [['api-key', 'key-status', state.settings?.has_key], ['s2-api-key', 's2-key-status', state.settings?.has_s2_key]]) {
    $(status).textContent = saved ? KEY_SAVED : KEY_NONE; $(field).placeholder = saved ? '' : 'Paste your API key';
  }
  showChat();
}
// A Chat key goes with its Chat URL or not at all, so a key typed before the Custom URL waits in its field.
const chatKeyWaits = () => Boolean($('chat-api-key').value) && $('chat-provider-preset').value === 'custom' && !connectionEndpoint('chat-');
const hostOf = endpoint => { try { return new URL(endpoint).hostname; } catch { return ''; } };
// What follows the Chat provider and the saved settings: the key field, the line that names the key of each role, the
// help line, and the Test, Copy, and Remove buttons. A saved Chat key belongs to the saved Chat provider, so a
// provider that is not saved yet shows none.
function showChat() {
  const settings = state.settings || {}, endpoint = connectionEndpoint('chat-'), host = hostOf(endpoint);
  const local = $('chat-provider-preset').value === 'local', saved = settings.has_chat_key && normalizedEndpoint(endpoint) === normalizedEndpoint(settings.chat_endpoint);
  $('chat-key-field').hidden = local; if (local) $('chat-api-key').value = '';
  $('chat-api-key').placeholder = saved ? '' : 'Paste your API key';
  const overviewHost = hostOf(settings.endpoint);
  $('chat-key-status').textContent = (overviewHost ? `Overview and Blog use the key for ${overviewHost}${settings.has_key ? '' : ' (none saved)'}.` : 'No AI connection is saved for Overviews and Blogs.') + ' '
    + (local ? 'A Local Chat model uses no key.' : host ? `Chat uses its own key for ${host}. ${saved ? KEY_SAVED : KEY_NONE}` : 'Choose a provider to save a Chat key.');
  $('chat-help').textContent = `Chat sends the Paper’s text, your Highlights and Notes, your question, and the earlier questions on its Question card to ${host || 'your Chat provider'}.${local ? ' Nothing leaves this Mac.' : ''}`;
  $('chat-delete-key').hidden = local || !saved;
  $('chat-endpoint-wait').hidden = !chatKeyWaits();
  $('chat-test-connection').disabled = !endpoint; $('chat-copy').disabled = !aiReady();
  $('chat-copy').title = aiReady() ? '' : 'Connect Overviews and Blogs in the AI pane first.';
}
// What a save sends. A blank key field means "keep the saved key", so it is left out. A Chat URL that is empty
// (Custom with no URL yet) and a Context size that is empty or not a whole number are left out too, so the server
// keeps the saved values. A Chat key typed with no Chat URL is left out too: the server would save it under the
// account of the saved provider.
function settingsPayload() {
  const chatEndpoint = connectionEndpoint('chat-'), chatContext = $('chat-context').valueAsNumber;
  const payload = {endpoint: connectionEndpoint(''), model: $('model').value.trim(), kindle_email: $('kindle-email').value.trim(), auto_summary: $('auto-summary').checked, auto_send: $('auto-send').checked,
    overview_reasoning: $('overview-reasoning').value, overview_language: $('overview-language').value, overview_length: $('overview-length').value,
    resume_reading: $('resume-reading').checked, open_imports: $('open-imports').checked, search_suggestions: $('search-suggestions').checked,
    ...chatEndpoint && {chat_endpoint: chatEndpoint}, chat_model: $('chat-model').value.trim(), chat_reasoning: $('chat-reasoning').value, ...Number.isInteger(chatContext) && {chat_context: chatContext}};
  if ($('api-key').value) payload.api_key = $('api-key').value;
  if ($('s2-api-key').value.trim()) payload.s2_api_key = $('s2-api-key').value.trim();
  if ($('chat-api-key').value && chatEndpoint) payload.chat_api_key = $('chat-api-key').value;
  return payload;
}
let savedSettings = '';
// A pane switch keeps unsaved edits; only opening the dialog reads the saved settings again.
// The Native shell shows Settings in its own window, so the main page asks Swift to open it.
export function openSettings(pane) {
  if (native && !panel) return post(PANES.includes(pane) ? {type: 'settings', pane} : {type: 'settings'});
  showPane(pane || settingsPane);
  if (panel || $('settings-dialog').open) return;
  // showModal focuses the first pane button, so focus moves to the pane that shows.
  // .instant is on while a key runs its command, so ⌘, shows the dialog with no animation.
  $('settings-dialog').classList.toggle('by-key', document.body.classList.contains('instant'));
  fillSettings(); $('settings-dialog').showModal(); document.querySelector('.settings-panes [aria-current]').focus();
}
register('settings', ({pane} = {}) => openSettings(pane));
const clearKeys = () => { for (const id of ['api-key', 's2-api-key', 'chat-api-key']) $(id).value = ''; };
$('settings-dialog').addEventListener('close', clearKeys);
$('settings-form').addEventListener('invalid', event => { const pane = event.target.closest('.pane'); if (pane) showPane(pane.dataset.pane); }, true);
// The dialog shows an error beside Done. The Settings window has no footer, so the error shows under the field that
// the reader committed, or else at the end of the pane.
function settingsError(message, field) {
  document.querySelector('#settings-form [aria-invalid]')?.removeAttribute('aria-invalid');
  const line = $('settings-error'), active = document.activeElement;
  line.textContent = message;
  if (!panel || !message) return;
  field ||= active?.matches('.pane :is(input, select)') ? active : null;
  if (!field) return document.querySelector('.pane:not([hidden])').append(line);
  (field.closest('.check') || field).after(line); field.setAttribute('aria-invalid', 'true');
}
// Returns false when the form or the server rejects the edits. The dialog saves on Done and closes; the Settings
// window saves each field that the reader commits.
async function saveSettings(field) {
  if (!(field || $('settings-form')).reportValidity()) return false;
  const payload = settingsPayload();
  try { state.settings = await api('/api/settings', payload); }
  catch (error) { clearKeys(); settingsError(error.message, field); return false; }
  if (!panel) { clearKeys(); fillSettings(); $('settings-dialog').close(); await refresh(); return true; }
  // A refill would overwrite a field that the reader is still editing, so the window clears only the keys it sent.
  settingsError('');
  for (const [id, key] of [['api-key', 'api_key'], ['s2-api-key', 's2_api_key'], ['chat-api-key', 'chat_api_key']]) if (payload[key]) { $(id).value = ''; delete payload[key]; }
  savedSettings = JSON.stringify(payload); showKeyStatus();
  return true;
}
// Mac settings windows save a change when the reader commits it. Reading preferences apply as they change, and
// Custom with no base URL yet waits for the URL field.
$('settings-form').addEventListener('change', event => {
  const waits = event.target.id.endsWith('provider-preset') && !connectionEndpoint(event.target.id.replace('provider-preset', ''));
  if (!panel || event.target.matches('[data-pref], [type=file]') || waits) return;
  saveSettings(event.target);
});
// Notes leave the app as Markdown of all Papers, or as a JSON backup that Restore Notes… reads back.
$('notes-export').onclick = () => download('/files/library/notes.md');
$('notes-backup').onclick = () => download('/files/library/notes.json');
$('notes-page-export').onclick = () => download('/files/library/notes.md');
$('notes-page-backup').onclick = () => download('/files/library/notes.json');
$('notes-restore-button').onclick = () => $('notes-restore').click();
$('notes-restore').onchange = async () => {
  const input = $('notes-restore'), file = input.files[0], status = $('settings-notes-status');
  // A cleared input sends 'change' again when the reader picks the same file.
  input.value = '';
  if (!file) return;
  const say = (text, failed = false) => { status.textContent = text; status.dataset.state = failed ? 'error' : ''; };
  let backup;
  try { backup = JSON.parse(await file.text()); }
  catch { say('This file is not a LocalXiv Notes backup.', true); return; }
  say('Restoring Notes…');
  try {
    const {highlights, papers} = await api('/api/notes/import', backup);
    say(`LocalXiv restored ${highlights} ${highlights === 1 ? 'Highlight or Note' : 'Highlights and Notes'} of ${papers} ${papers === 1 ? 'Paper' : 'Papers'}.`);
  } catch (error) { say(error.message, true); }
};
// Done, and Return in the Settings window's text fields, which commits that field.
$('settings-form').onsubmit = event => { event.preventDefault(); closeSettings(); };
// Closing Settings saves unsaved edits, so a rejected save keeps Settings open. In the dialog, a Chat key that waits
// for its URL keeps Settings open too, with the line under the URL field showing. The Settings window cannot follow
// a pane change from the page (its toolbar, title, and height stay), so it closes and drops that key with the page.
// The Settings window waits for 'close-settings' before it closes, and the answer is true when nothing is unsaved;
// the dialog closes here.
async function closeSettings() {
  if (!panel && chatKeyWaits()) { showPane('chat'); showChat(); return false; }
  if (JSON.stringify(settingsPayload()) !== savedSettings) return saveSettings();
  if (!panel) $('settings-dialog').close();
  return true;
}
register('close-settings', closeSettings);
$('settings-dialog').addEventListener('cancel', event => { event.preventDefault(); closeSettings(); });
// In Chromium, a second Escape with no other input between them closes the dialog, and 'cancel' cannot stop it, so
// Escape is handled on keydown. ⌘. cancels each dialog as Escape does, as in Mac dialogs. The listener is on the
// document because focus can be on the body.
document.addEventListener('keydown', event => {
  const period = event.metaKey && event.key === '.';
  if (event.key !== 'Escape' && !period || event.defaultPrevented) return;
  if ($('settings-dialog').open) { event.preventDefault(); closeSettings(); return; }
  const open = period && document.querySelector('dialog[open]');
  if (open) { event.preventDefault(); if (open.dispatchEvent(new Event('cancel', {cancelable: true}))) open.close(); }
});
// Chat tests its own provider, model, and key.
async function testConnection(prefix) {
  const button = $(prefix + 'test-connection'), status = $(prefix + 'connection-status');
  const values = () => ({...prefix === 'chat-' && {role: 'chat'}, endpoint: connectionEndpoint(prefix), model: $(prefix + 'model').value.trim(),
    api_key: $(prefix === 'setup-' ? 'setup-key' : prefix + 'api-key').value.trim()});
  if (button.ariaBusy === 'true') return;
  const payload = values();
  button.ariaBusy = 'true'; status.textContent = 'Testing connection…'; status.dataset.state = 'testing';
  try {
    const result = await api('/api/test-connection', payload);
    const unchanged = JSON.stringify(values()) === JSON.stringify(payload);
    status.textContent = unchanged ? result.message : 'Connection fields changed. Test again.'; status.dataset.state = unchanged ? 'success' : 'changed';
  } catch (error) { status.textContent = error.message; status.dataset.state = 'error'; }
  finally { button.ariaBusy = 'false'; }
}
for (const prefix of ['', 'setup-', 'chat-']) {
  $(prefix + 'test-connection').onclick = () => testConnection(prefix);
  $(prefix + 'provider-preset').onchange = () => changeProvider(prefix);
}
for (const [prefix, fields] of [['', ['endpoint', 'model', 'api-key']], ['setup-', ['endpoint', 'model', 'key']], ['chat-', ['endpoint', 'model', 'api-key']]]) {
  for (const field of fields) $(prefix + field).addEventListener('input', () => { $(prefix + 'connection-status').textContent = ''; });
}
$('chat-endpoint').addEventListener('input', showChat);
// One copy of the Overview and Blog provider, model, and key. Chat then keeps its own, so the key line stays true.
$('chat-copy').onclick = async () => {
  const before = $('chat-provider-preset').value;
  try { state.settings = await api('/api/settings', {chat_copy: true}); }
  catch (error) { settingsError(error.message); return; }
  settingsError('');
  renderProvider('chat-', state.settings.chat_endpoint); $('chat-model').value = state.settings.chat_model;
  $('chat-api-key').value = ''; $('chat-connection-status').textContent = '';
  followChatContext(before); showChat();
  if (panel) saveSettings();
};
// Removes the saved Chat key. The Overview key stays.
$('chat-delete-key').onclick = async () => {
  try { state.settings = await api('/api/settings', {chat_delete_key: true}); }
  catch (error) { settingsError(error.message); return; }
  settingsError(''); showChat(); $('chat-api-key').focus();
};

// ---- Setup: once, on the first launch ----
function openSetup() {
  $('setup-connection-status').textContent = '';
  const settings = state.settings || {};
  renderProvider('setup-', settings.endpoint || PROVIDER_PRESETS.openai.endpoint);
  $('setup-model').value = settings.model || ''; $('setup-key').value = '';
  $('setup-kindle').value = settings.kindle_email || ''; $('setup-resume').checked = Boolean(settings.resume_reading);
  $('setup-error').textContent = ''; setupFieldError(''); updateSetupKeyStatus(); $('setup-dialog').showModal();
}
// An AI field error shows under Model, and each empty AI field gets a red edge. A server error shows at the foot.
function setupFieldError(message) {
  $('setup-field-error').textContent = message;
  for (const id of ['setup-endpoint', 'setup-model']) if (message && !$(id).value.trim()) $(id).setAttribute('aria-invalid', 'true'); else $(id).removeAttribute('aria-invalid');
}
function updateSetupKeyStatus() {
  const saved = state.settings?.has_key && normalizedEndpoint(connectionEndpoint('setup-')) === normalizedEndpoint(state.settings?.endpoint);
  $('setup-key-status').textContent = saved ? 'Your key is already saved. Leave blank to keep it.' : 'Saved securely in macOS Keychain.';
  $('setup-key').placeholder = saved ? '' : 'Paste your API key';
}
// Setup reads the saved settings, so Settings saves its edits first, as when it closes.
$('setup-open').onclick = async () => { if (await closeSettings()) openSetup(); };
$('setup-endpoint').oninput = updateSetupKeyStatus;
$('setup-dialog').addEventListener('close', () => { $('setup-key').value = ''; });
// Save, Skip Setup, and Esc all come here, so one flag ignores a second one while the first runs.
let setupBusy = false;
async function completeSetup(values = {}) {
  if (setupBusy) return;
  setupBusy = true;
  try {
    state.settings = await api('/api/settings', {...values, onboarding_complete: true});
    $('setup-key').value = ''; $('setup-dialog').close();
    if (panel) fillSettings(); else syncChrome();
  } catch (error) { $('setup-key').value = ''; $('setup-error').textContent = error.message; }
  finally { setupBusy = false; }
}
$('setup-form').onsubmit = async event => {
  event.preventDefault();
  const endpoint = connectionEndpoint('setup-'), model = $('setup-model').value.trim(), key = $('setup-key').value;
  if ((key || model) && (!endpoint || !model)) return setupFieldError('Add a base URL and a model for your AI connection, or leave the AI fields blank.');
  setupFieldError('');
  const values = {kindle_email: $('setup-kindle').value.trim(), resume_reading: $('setup-resume').checked};
  if (endpoint) values.endpoint = endpoint;
  if (model) values.model = model;
  if (key) values.api_key = key;
  await completeSetup(values);
};
$('setup-skip').onclick = () => completeSetup({resume_reading: $('setup-resume').checked});
$('setup-dialog').addEventListener('cancel', event => { event.preventDefault(); completeSetup({resume_reading: $('setup-resume').checked}); });

// ---- Figure dialog ----
let figureView = null, figureDrag = null;
function figurePanels(value) {
  if (!Array.isArray(value)) return [];
  return value.filter(panel => panel && typeof panel.id === 'string' && [panel.x, panel.y, panel.width, panel.height]
    .every(number => typeof number === 'number' && Number.isFinite(number)) && panel.width > 0 && panel.height > 0);
}
function figureSize(dimensions, image) {
  return {width: dimensions?.width > 0 ? dimensions.width : (image.naturalWidth || 960), height: dimensions?.height > 0 ? dimensions.height : (image.naturalHeight || 640)};
}
function figureFitUnit() {
  if (!figureView) return 1;
  const box = $('figure-canvas').getBoundingClientRect(), size = figureSize(figureView.dimensions, $('figure-image'));
  return Math.max(0.05, Math.min(Math.max(120, box.width - 16) / size.width, Math.max(120, box.height - 16) / size.height));
}
function applyFigureUnit(unit, {keepCentre = true} = {}) {
  const stage = $('figure-canvas'), image = $('figure-image');
  if (!figureView) return;
  const size = figureSize(figureView.dimensions, image);
  const centre = {x: stage.scrollLeft + stage.clientWidth / 2, y: stage.scrollTop + stage.clientHeight / 2};
  const previous = figureView.unit || figureFitUnit(), chosen = Math.max(0.02, Math.min(8, unit));
  figureView.unit = chosen; figureView.fit = Math.abs(chosen - figureFitUnit()) < 1e-6;
  image.style.width = Math.round(size.width * chosen * 100) / 100 + 'px';
  image.style.height = Math.round(size.height * chosen * 100) / 100 + 'px';
  if (keepCentre && previous > 0) {
    stage.scrollLeft = centre.x * (chosen / previous) - stage.clientWidth / 2;
    stage.scrollTop = centre.y * (chosen / previous) - stage.clientHeight / 2;
  }
  $('figure-fit').setAttribute('aria-pressed', String(figureView.fit));
}
function focusFigurePanel(panel) {
  if (!figureView || !panel) return;
  const stage = $('figure-canvas'), box = stage.getBoundingClientRect();
  const unit = Math.max(0.05, Math.min(4, Math.min((box.width - 48) / panel.width, (box.height - 48) / panel.height)));
  applyFigureUnit(unit, {keepCentre: false});
  stage.scrollLeft = Math.max(0, (panel.x - 24) * unit); stage.scrollTop = Math.max(0, (panel.y - 24) * unit);
  stage.focus({preventScroll: true});
}
function figurePoint(event) {
  const image = $('figure-image'), box = image.getBoundingClientRect();
  if (!figureView || !box.width || !box.height || event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) return null;
  const size = figureSize(figureView.dimensions, image);
  return {x: (event.clientX - box.left) / box.width * size.width, y: (event.clientY - box.top) / box.height * size.height};
}
const figurePanelAt = point => point && figureView ? figureView.panels.find(panel => point.x >= panel.x && point.x <= panel.x + panel.width && point.y >= panel.y && point.y <= panel.y + panel.height) : null;
const figurePanelLabel = (panel, index) => 'Panel ' + (index + 1) + (panel.title ? ': ' + panel.title : '');
export function openFigure(url, alt, caption, panels, dimensions) {
  const list = figurePanels(panels), image = $('figure-image');
  figureView = {url, alt, caption, panels: list, dimensions: dimensions || null, unit: 0, fit: true};
  $('figure-canvas').querySelector('.figure-failed')?.remove();
  image.onerror = () => {
    const failed = figureFailure(() => { failed.remove(); image.hidden = false; image.src = url; });
    image.hidden = true; $('figure-canvas').append(failed);
  };
  image.hidden = false; image.src = url; image.alt = alt || 'Paper figure'; image.removeAttribute('style'); delete image.dataset.paper;
  $('figure-caption').textContent = caption || '';
  const targets = $('figure-panels'); targets.replaceChildren(); targets.hidden = !list.length;
  list.forEach((panel, index) => {
    const button = node('button', figurePanelLabel(panel, index));
    button.type = 'button'; button.setAttribute('aria-label', 'Focus ' + figurePanelLabel(panel, index));
    button.onclick = () => focusFigurePanel(panel);
    targets.append(button);
  });
  const reset = () => { const stage = $('figure-canvas'); stage.scrollLeft = 0; stage.scrollTop = 0; applyFigureUnit(figureFitUnit(), {keepCentre: false}); };
  reset(); image.onload = reset;
  $('figure-dialog').showModal(); $('figure-canvas').focus({preventScroll: true});
}
$('figure-close').onclick = () => $('figure-dialog').close();
$('figure-fit').onclick = () => applyFigureUnit(figureFitUnit());
$('figure-zoom').onclick = () => applyFigureUnit(1);
$('figure-zoom-in').onclick = () => applyFigureUnit((figureView?.unit || 1) * 1.25);
$('figure-zoom-out').onclick = () => applyFigureUnit((figureView?.unit || 1) * 0.8);
$('figure-image').onclick = event => { const panel = figurePanelAt(figurePoint(event)); if (panel) focusFigurePanel(panel); };
$('figure-canvas').onpointerdown = event => {
  if (event.button !== 0 || !figureView) return;
  const stage = $('figure-canvas');
  figureDrag = {x: event.clientX, y: event.clientY, left: stage.scrollLeft, top: stage.scrollTop, moved: false};
  try { stage.setPointerCapture(event.pointerId); } catch {}
};
$('figure-canvas').onpointermove = event => {
  if (!figureDrag) return;
  const dx = event.clientX - figureDrag.x, dy = event.clientY - figureDrag.y;
  if (Math.abs(dx) + Math.abs(dy) > 4) figureDrag.moved = true;
  if (!figureDrag.moved) return;
  $('figure-canvas').scrollLeft = figureDrag.left - dx; $('figure-canvas').scrollTop = figureDrag.top - dy;
};
$('figure-canvas').onpointerup = event => {
  const drag = figureDrag; figureDrag = null;
  if (!drag || drag.moved || !figureView) return;
  // Pointer capture retargets the release event to the stage, so hit-test by position.
  const panel = figurePanelAt(figurePoint(event));
  if (panel) focusFigurePanel(panel);
};
$('figure-canvas').onpointercancel = () => { figureDrag = null; };
$('figure-canvas').onwheel = event => {
  if (!event.ctrlKey && !event.metaKey) return;
  event.preventDefault();
  applyFigureUnit((figureView?.unit || 1) * (event.deltaY < 0 ? 1.12 : 1 / 1.12));
};
$('figure-canvas').onkeydown = event => {
  if (!figureView) return;
  const stage = $('figure-canvas');
  if (event.key === '+' || event.key === '=') applyFigureUnit((figureView.unit || 1) * 1.25);
  else if (event.key === '-') applyFigureUnit((figureView.unit || 1) * 0.8);
  else if (event.key === '0') applyFigureUnit(figureFitUnit());
  else if (event.key === 'ArrowLeft') stage.scrollLeft -= 48;
  else if (event.key === 'ArrowRight') stage.scrollLeft += 48;
  else if (event.key === 'ArrowUp') stage.scrollTop -= 48;
  else if (event.key === 'ArrowDown') stage.scrollTop += 48;
  else if (/^[1-9]$/.test(event.key)) focusFigurePanel(figureView.panels[Number(event.key) - 1]);
  else return;
  event.preventDefault();
};
addEventListener('resize', () => { if (figureView?.fit && $('figure-dialog').open) applyFigureUnit(figureFitUnit(), {keepCentre: false}); });

// ---- State polling ----
let refreshing = null;
function refresh() {
  if (!refreshing) refreshing = refreshState().finally(() => { refreshing = null; });
  return refreshing;
}
async function refreshState() {
  try {
    const writes = prefsWrites, next = await api('/api/state'); state = next;
    adoptServerPrefs(writes);
    if (panel) return;
    if (selected && !next.papers.some(paper => paper.id === selected)) go({page: 'library', filter: 'all'});
    if (!stateInitialized) { for (const job of next.jobs) if (job.kind === 'import' && TERMINAL.has(job.state)) completedImports.add(job.id); stateInitialized = true; }
    const papers = JSON.stringify(next.papers), jobs = JSON.stringify(next.jobs);
    if (papers !== stateSignature) { stateSignature = papers; drawPages(); }
    if (jobs !== jobSignature) {
      jobSignature = jobs; drawJobList();
      downloadFinishedExports(next.jobs);
      const imported = next.jobs.find(job => job.kind === 'import' && job.state === 'ready' && job.result?.paper_id && next.papers.some(paper => paper.id === job.result.paper_id) && !completedImports.has(job.id));
      for (const job of next.jobs) if (job.kind === 'import' && TERMINAL.has(job.state)) completedImports.add(job.id);
      if (imported && next.settings.open_imports !== false) await openPaper(imported.result.paper_id);
      else if (selected) await openPaper(selected);
    }
    for (const update of results.updates) update();
    syncChrome(); if (selected) syncReaderChrome();
  } catch (error) { stateFailed = true; notice(error.message); }
}
let pollTimer;
function schedulePoll() {
  clearTimeout(pollTimer);
  pollTimer = setTimeout(poll, document.hidden ? 30000 : state.jobs.some(job => !TERMINAL.has(job.state)) ? 2000 : 10000);
}
async function poll() { await refresh(); schedulePoll(); }

// ---- Keys that no menu holds ----
document.addEventListener('keydown', event => {
  if (event.key !== 'Escape' || event.defaultPrevented || document.querySelector('dialog[open]')) return;
  if (nav.current?.page === 'search' && !event.target.closest?.('input, select, textarea')) { event.preventDefault(); leaveSearch(); }
});

// ---- Start ----
applyPrefs();
(async () => {
  if (panel) {
    document.body.classList.add('panel'); document.body.append($('settings-form'));
    await refresh(); fillSettings(); openSettings(new URLSearchParams(location.search).get('pane'));
    addEventListener('focus', refresh);
    // The Settings window has no sidebar or toolbar to draw, so it sends no Chrome state.
    window.webkit?.messageHandlers?.shell?.postMessage({type: 'ready'});
    return;
  }
  document.addEventListener('visibilitychange', () => { if (!document.hidden) poll(); else schedulePoll(); });
  await refresh();
  nav.push({page: 'home'}); show(nav.current);
  const last = state.papers.filter(paper => paper.reading).sort(byOpened)[0];
  if (stateInitialized && !state.settings.onboarding_complete) openSetup();
  else if (state.settings.resume_reading && last) await openPaper(last.id);
  chrome.ready();
  schedulePoll();
})();
