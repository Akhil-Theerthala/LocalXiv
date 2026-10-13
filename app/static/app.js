/* No provider keys are retained by the browser. Paper and model text are always text nodes. */
import {commands, register, chrome, nav, openMenu, keydown} from './shell.js';
import {node, expireToast, JobNotices, TERMINAL, renderProse, cleanOverviewCitations, annotateFigure, inputKind, searchRows, rowState, authorList,
  authorNames, byline, arxivDate, shortTitle, bibtex, readingState, libraryRow, baseID} from './render.js';
import {normalize, fromSettings, toSettings, readCopy, writeCopy, resolveTheme, rootProperties, readerStylesheet, SIZES, DEFAULTS} from './appearance.js';

const $ = id => document.getElementById(id);
const panel = new URLSearchParams(location.search).get('panel') === 'settings';
const fragment = new URLSearchParams(location.hash.slice(1));
const storage = (() => { try { return window.localStorage; } catch { return null; } })();
const stored = key => { try { return storage?.getItem(key) || ''; } catch { return ''; } };
const store = (key, value) => { try { storage?.setItem(key, value); } catch {} };
let token = fragment.get('token') || stored('papers-session');
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
let state = {papers: [], jobs: [], settings: {}}, selected = null, detail = null, detailRequest = 0;
let stateSignature = '', jobSignature = '', stateInitialized = false;
const retries = new Map(), completedImports = new Set(), downloadedExports = new Set();

// ---- Server ----
const paperAPI = id => `/api/papers/${encodeURIComponent(id)}`;
export async function api(path, payload) {
  const response = await fetch(path, {method: payload === undefined ? 'GET' : 'POST', headers: {Authorization: `Bearer ${token}`, ...(payload === undefined ? {} : {'Content-Type': 'application/json'})}, ...(payload === undefined ? {} : {body: JSON.stringify(payload)})});
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || `Request failed (${response.status})`);
  return result;
}
async function run(path, payload) {
  try { notice(''); const result = await api(path, payload); if (result.job) retries.set(result.job.id, {path, payload}); await refresh(); return result; }
  catch (error) { notice(error.message); return null; }
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
  stateSignature = ''; drawPages(); syncChrome();
  return reading;
}
const aiReady = () => Boolean(state.settings?.model && state.settings?.has_key);
const runningJob = (kind, id = selected) => state.jobs.find(job => job.kind === kind && job.payload?.paper_id === id && !TERMINAL.has(job.state));
const summary = id => state.papers.find(paper => paper.id === id);

// ---- Notices and jobs ----
let noticeTimer;
function notice(message, autoDismiss = false) {
  clearTimeout(noticeTimer); $('notice').replaceChildren(); $('notice').hidden = !message;
  if (!message) return;
  const heading = node('div', undefined, 'toast-heading'), close = node('button', '×');
  close.setAttribute('aria-label', 'Dismiss notification'); close.onclick = () => { $('notice').hidden = true; };
  heading.append(node('strong', message), close); $('notice').append(heading);
  $('notice').classList.remove('toast-expiring');
  if (autoDismiss) noticeTimer = expireToast($('notice'), () => { $('notice').hidden = true; });
}
function downloadLink(path) {
  const url = new URL(path, location.origin);
  if (url.origin !== location.origin || !url.pathname.startsWith('/files/')) return null;
  url.searchParams.set('token', token);
  const ending = url.pathname.toLowerCase();
  const link = node('a', ending.endsWith('.png') ? 'Save PNG' : ending.endsWith('.pdf') ? 'Save PDF' : 'Save EPUB'); link.href = url.href; link.download = '';
  return link;
}
function downloadFinishedExports(jobs) {
  for (const job of jobs) {
    if (job.kind !== 'export' || job.state !== 'ready' || !job.result?.download_url || !retries.has(job.id) || downloadedExports.has(job.id)) continue;
    downloadedExports.add(job.id);
    const link = downloadLink(job.result.download_url);
    if (link) { document.body.append(link); link.click(); link.remove(); }
  }
}
const jobNotices = new JobNotices({target: $('jobs'), run, paperAPI, downloadLink, retries});
let jobList = null;
register('activity', () => {
  jobList = new JobNotices({target: $('jobs-list'), run, paperAPI, downloadLink, retries, list: true});
  $('jobs-list').replaceChildren(); drawJobList();
  if (!$('jobs-dialog').open) $('jobs-dialog').showModal();
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
  if (!active.length) return null;
  const job = active[0], title = shortTitle(summary(job.payload?.paper_id)?.title || job.payload?.paper_id || '');
  const target = job.payload?.url ? (job.payload.url.match(/(\d{4}\.\d{4,5}(?:v\d+)?)/)?.[1] || job.payload.url) : title;
  const label = {import: `Importing ${target}`, overview: `Making the Overview · ${title}`, blog: `Writing the Blog · ${title}`,
    export: `Exporting · ${title}`, send: `Sending to Kindle · ${title}`}[job.kind] || 'Working';
  return {label, progress: typeof job.progress === 'number' ? job.progress / 100 : null, count: active.length};
}

// ---- Reading preferences: the server settings hold them; the localStorage copy paints the first frame ----
let prefs = storage ? readCopy(storage) : {...DEFAULTS}, serverPrefs = '', pendingPrefs = {}, prefsTimer;
const systemTheme = matchMedia('(prefers-color-scheme: dark)');
function applyPrefs() {
  const root = document.documentElement, theme = resolveTheme(prefs.theme, systemTheme.matches);
  root.dataset.theme = theme;
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
    const values = toSettings(pendingPrefs); pendingPrefs = {};
    try { state.settings = await api('/api/settings', values); serverPrefs = JSON.stringify(fromSettings(state.settings)); } catch (error) { notice(error.message); }
  }, 300);
}
function adoptServerPrefs() {
  const next = JSON.stringify(fromSettings(state.settings));
  if (next === serverPrefs || Object.keys(pendingPrefs).length) return;
  serverPrefs = next; prefs = fromSettings(state.settings); if (storage) writeCopy(storage, prefs); applyPrefs();
}
register('prefs', ({patch}) => setPrefs(patch || {}));
register('text-size', ({step}) => setPrefs({size: step ? Math.min(SIZES[1], Math.max(SIZES[0], prefs.size + Math.sign(step))) : DEFAULTS.size}));
for (const field of document.querySelectorAll('[data-pref]')) field.addEventListener('input', () => setPrefs({[field.dataset.pref]: field.type === 'range' ? Number(field.value) : field.value}));
systemTheme.addEventListener('change', applyPrefs);

// ---- Chrome state outside the reader ----
function syncChrome() {
  const entry = nav.current || {page: 'home'}, counts = {all: state.papers.length, new: 0, reading: 0, read: 0};
  for (const paper of state.papers) counts[readingState(paper)]++;
  const recent = state.papers.filter(paper => paper.reading).sort((a, b) => b.reading.opened_at - a.reading.opened_at).slice(0, 5)
    .map(paper => ({id: paper.id, title: shortTitle(paper.title || paper.id), current: paper.id === selected}));
  const selectedRow = entry.page === 'home' ? 'home' : entry.page === 'library' ? entry.filter : null;
  const patch = {mode: entry.page, sidebar: {selected: selectedRow, counts, recent}, activity: activity(), search: {query: entry.page === 'search' ? entry.query : ''}};
  if (entry.page === 'home') Object.assign(patch, {title: 'Home', subtitle: ''});
  if (entry.page === 'library') {
    const shown = entry.filter === 'all' ? counts.all : counts[entry.filter];
    Object.assign(patch, {title: 'Library', subtitle: `${FILTERS[entry.filter]} · ${shown} ${shown === 1 ? 'Paper' : 'Papers'}`});
  }
  if (entry.page === 'search') Object.assign(patch, {title: 'Search', subtitle: entry.query.trim()});
  if (entry.page !== 'reader') { patch.views = null; patch.sidebar.reader = null; patch.actions = {share: [], more: []}; }
  chrome.update(patch);
}

// ---- Pages and history ----
const PAGES = {home: 'home', library: 'library', search: 'results', reader: 'reader-page'};
function showPage(page) {
  for (const [name, id] of Object.entries(PAGES)) $(id).hidden = name !== page;
  if (page !== 'reader') { ++detailRequest; selected = null; detail = null; }
}
function show(entry) {
  showPage(entry.page);
  if (entry.page === 'home') drawHome();
  if (entry.page === 'library') drawLibrary();
  if (entry.page === 'search') runSearch({query: entry.query, submit: true});
  if (entry.page === 'reader') { openPaper(entry.id, {position: entry.position}); return; }
  syncChrome();
  window.scrollTo(0, entry.scroll || 0);
}
nav.onShow(show);
function go(entry) {
  const current = nav.current;
  if (current && JSON.stringify({...current, scroll: undefined}) === JSON.stringify({...entry, scroll: undefined})) return show(current);
  nav.push(entry); show(entry);
}
register('go', ({to}) => go(to === 'home' ? {page: 'home'} : FILTERS[to] ? {page: 'library', filter: to} : {page: 'home'}));
register('open', ({id}) => openPaper(id));
register('add', () => { go({page: 'home'}); $('home-url').focus(); });
function drawPages() {
  const page = nav.current?.page;
  if (page === 'home') drawHome();
  if (page === 'library') drawLibrary();
}

// ---- Home and the Library ----
const rowHandlers = {onOpen: paper => openPaper(paper.id), onMenu: (paper, event) => paperMenu(paper, event)};
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
  card.type = 'button';
  if (eyebrow) meta.append(node('span', 'Continue reading', 'eyebrow'));
  meta.append(node('span', paper.title || paper.id, 'title'), node('span', authorList(authorNames(paper.authors), 3), 'authors'), node('span', lastSection(paper), 'where'));
  for (const span of meta.children) span.style.display = 'block';
  card.append(meta);
  if (eyebrow) card.append(node('span', 'Resume', 'btn-accent'));
  card.onclick = () => openPaper(paper.id);
  card.oncontextmenu = event => { event.preventDefault(); paperMenu(paper, event); };
  return card;
}
const byOpened = (a, b) => (b.reading?.opened_at || 0) - (a.reading?.opened_at || 0);
function drawHome() {
  const papers = state.papers, onlySample = papers.every(paper => paper.id === SAMPLE_ID);
  const continuing = papers.filter(paper => readingState(paper) === 'reading').sort(byOpened).slice(0, 3);
  const recent = [...papers].sort((a, b) => (b.added_at || 0) - (a.added_at || 0)).slice(0, 5);
  $('home-welcome').hidden = !onlySample || !papers.length && !stateInitialized;
  $('welcome-sample').hidden = !papers.some(paper => paper.id === SAMPLE_ID);
  $('home-continue').hidden = !continuing.length;
  $('home-continue-list').replaceChildren(...continuing.map(paper => resumeCard(paper)));
  $('home-recent').hidden = onlySample || !recent.length;
  $('home-recent-list').replaceChildren(...recent.map(paper => libraryRow(paper, rowHandlers)));
}
$('welcome-sample').onclick = () => openPaper(SAMPLE_ID);
const SORTS = {
  added: (a, b) => (b.added_at || 0) - (a.added_at || 0),
  read: byOpened,
  title: (a, b) => (a.title || a.id).localeCompare(b.title || b.id),
  published: (a, b) => (arxivDate(b.arxiv_id || b.id)?.key || 0) - (arxivDate(a.arxiv_id || a.id)?.key || 0),
};
$('library-sort').value = SORTS[stored('localxiv-sort')] ? stored('localxiv-sort') : 'added';
$('library-sort').onchange = () => { store('localxiv-sort', $('library-sort').value); drawLibrary(); };
function drawLibrary() {
  const filter = nav.current?.filter || 'all';
  const papers = state.papers.filter(paper => filter === 'all' || readingState(paper) === filter).sort(SORTS[$('library-sort').value]);
  const last = filter === 'all' && state.papers.filter(paper => readingState(paper) === 'reading').sort(byOpened)[0];
  $('library-continue').replaceChildren(...(last ? [resumeCard(last, {eyebrow: true})] : []));
  const empty = {all: 'Papers you add appear here. Search for one, or paste an arXiv link.', new: 'No new papers. Every paper here has been opened.',
    reading: 'No papers in progress. Open a paper to start reading.', read: 'No papers marked as read. Use Mark as Read in a paper’s More menu.'}[filter];
  $('library-list').replaceChildren(...(papers.length ? papers.map(paper => libraryRow(paper, rowHandlers)) : [node('p', empty, 'empty')]));
}
// The arrow keys move the selection through a list of rows; Return opens the selected row's Paper.
for (const list of [$('library-list'), $('home-recent-list')]) {
  list.addEventListener('focusin', event => { const row = event.target.closest('.prow'); if (row) for (const item of list.querySelectorAll('.prow')) item.classList.toggle('is-selected', item === row); });
  list.addEventListener('keydown', event => {
    if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return;
    const rows = [...list.querySelectorAll('.prow')], index = rows.indexOf(document.activeElement);
    const next = {ArrowDown: Math.min(rows.length - 1, index + 1), ArrowUp: Math.max(0, index - 1), Home: 0, End: rows.length - 1}[event.key];
    rows[next]?.focus(); rows[next]?.scrollIntoView({block: 'nearest'}); event.preventDefault();
  });
}

// ---- Paper actions: the Library context menu, Share, and More ----
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
async function copy(text, what) {
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
    open: () => openPaper(paper.id),
    'mark-read': () => saveReading(paper.id, {state: 'read'}).catch(error => notice(error.message)),
    'mark-unread': () => saveReading(paper.id, {state: 'new'}).catch(error => notice(error.message)),
    'copy-link': () => copy(`https://arxiv.org/abs/${baseID(paper.arxiv_id)}`, 'arXiv link'),
    'copy-bibtex': () => copy(bibtex(paper), 'BibTeX'),
    'open-arxiv': () => window.open(`https://arxiv.org/abs/${baseID(paper.arxiv_id)}`, '_blank', 'noopener'),
    remove: () => confirmRemove(paper, returnFocus),
  };
  actions[id]?.();
}
function confirmRemove(paper, returnFocus) {
  const dialog = $('remove-paper-dialog');
  dialog.dataset.paperId = paper.id;
  $('remove-paper-name').textContent = paper.title || paper.id;
  $('remove-paper-error').textContent = '';
  dialog.addEventListener('close', () => { if (returnFocus?.isConnected) returnFocus.focus(); }, {once: true});
  dialog.showModal(); $('remove-paper-cancel').focus();
}
$('remove-paper-cancel').onclick = () => $('remove-paper-dialog').close();
$('remove-paper-confirm').onclick = async () => {
  const dialog = $('remove-paper-dialog'), id = dialog.dataset.paperId;
  $('remove-paper-confirm').disabled = true; $('remove-paper-error').textContent = '';
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
  } finally { $('remove-paper-confirm').disabled = false; }
};
function exportView(profile) { if (selected) run(`${paperAPI(selected)}/export`, {kind: activeTab, profile}); }
register('action', ({id}) => {
  // A menu or a key can name an action that the current view disables.
  if (!detail || !Object.values(readerActions()).flat().some(action => action.id === id && action.enabled)) return;
  const paper = {...summary(selected), ...detail.paper}, generation = detail[activeTab];
  const actions = {
    'export-epub': () => exportView('kindle'), 'export-pdf': () => exportView('pdf'), 'export-png': () => exportView('png'),
    'export-svg': () => { const link = node('a'); link.href = fileURL(generation?.figures?.[0]?.svg_source); link.download = ''; document.body.append(link); link.click(); link.remove(); },
    'send-kindle': openKindle,
    'open-pdf': () => window.open(fileURL('original.pdf'), '_blank', 'noopener'),
    regenerate: () => generate(activeTab),
  };
  (actions[id] || (() => paperAction(paper, id, null)))();
});
function readerActions() {
  const paper = detail.paper, view = activeTab, generation = view === 'paper' ? null : detail[view];
  const ready = view === 'paper' || Boolean(generation), read = readingState(summary(selected) || {}) === 'read';
  return {
    share: [
      {id: 'export-epub', label: 'Export EPUB', enabled: ready && !(view === 'paper' && paper.format === 'pdf')},
      {id: 'export-pdf', label: 'Export PDF', enabled: ready},
      {id: 'export-png', label: 'Export PNG', enabled: view === 'overview' && ready},
      {id: 'export-svg', label: 'Export Editable SVG', enabled: Boolean(fileURL(generation?.figures?.[0]?.svg_source))},
      {id: 'send-kindle', label: 'Send to Kindle…', enabled: true, separatorBefore: true},
      {id: 'copy-link', label: 'Copy arXiv Link', enabled: Boolean(paper.arxiv_id), separatorBefore: true},
      {id: 'copy-bibtex', label: 'Copy BibTeX', enabled: true},
    ],
    more: [
      {id: read ? 'mark-unread' : 'mark-read', label: read ? 'Mark as Unread' : 'Mark as Read', enabled: true},
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
  $('kindle-destination').textContent = state.settings?.kindle_email ? 'To ' + state.settings.kindle_email : 'Add your Kindle email in Settings › Kindle to send.';
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
  $('kindle-format-note').textContent = sendPDF ? detail.paper.report.warning : 'The selected document goes as an EPUB.';
}
$('artifact-kind').onchange = updateDeliveryControls;
$('kindle-cancel').onclick = () => $('kindle-dialog').close();
$('kindle-form').onsubmit = async event => {
  event.preventDefault();
  if (selected && await run(`${paperAPI(selected)}/send`, {kind: $('artifact-kind').value, profile: $('profile').value})) $('kindle-dialog').close();
};

// ---- Search: the toolbar field (web or native) shows the results page live; Home keeps Suggestions ----
const DOWN = 'Search is down. You can still paste a link.';
async function paperSearch(query, limit) {
  try { return await api('/api/search', {query, limit}); } catch { return {results: [], error: 'unavailable'}; }
}
let results = {query: '', remote: [], request: 0, timer: 0, updates: []};
function leaveSearch() { if (nav.current?.page !== 'search') return; if (nav.previous) nav.step(-1); else go({page: 'home'}); }
function runSearch({query = '', submit = false}) {
  const text = String(query), trimmed = text.trim(), kind = inputKind(trimmed), mine = ++results.request;
  clearTimeout(results.timer);
  if (!trimmed) return leaveSearch();
  if (nav.current?.page === 'search') nav.replace({page: 'search', query: text}); else nav.push({page: 'search', query: text});
  showPage('search'); syncChrome();
  if (results.query !== trimmed) { results.query = trimmed; $('results-title').textContent = kind === 'import' ? 'Add a paper' : `Results for “${trimmed}”`; }
  if (kind === 'import') {
    results.remote = []; drawResults(submit ? 'Adding the paper…' : 'Press Return to add this paper.');
    if (submit) run('/api/import', {url: trimmed}).then(result => { if (result && nav.current?.page === 'search') leaveSearch(); });
    return;
  }
  const live = submit || trimmed.length >= 3 && state.settings.search_suggestions !== false;
  if (!live) { results.remote = []; drawResults(''); return; }
  drawResults(results.remote.length ? '' : 'Searching…');
  results.timer = setTimeout(async () => {
    const response = await paperSearch(trimmed, submit ? 20 : 8);
    // A newer keystroke started another search; its rows win.
    if (mine === results.request) { results.remote = response.results; drawResults(response.error ? DOWN : ''); }
  }, submit ? 0 : 400);
}
register('search', runSearch);
function drawResults(status) {
  const rows = searchRows(state.papers, results.query, results.remote, 5, 25), local = rows.filter(row => row.id), remote = rows.filter(row => !row.id);
  results.updates = [];
  $('results-library').replaceChildren(...local.map(resultRow));
  $('results-list').replaceChildren(...remote.map(resultRow));
  $('results-library-title').hidden = !local.length; $('results-remote-title').hidden = !remote.length;
  $('results-status').textContent = status || (rows.length ? '' : 'No papers found. Papers from the last few days may not appear yet. Paste the link instead.');
  $('results-credit').hidden = !remote.length;
}
function resultRow(row) {
  const item = node('article', undefined, 'result'), text = node('div'), action = node('button'), mark = node('span', 'In library', 'library-mark');
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
    const {paper, adding} = rowState(row, state.papers, state.jobs);
    action.textContent = paper ? 'Open' : adding ? 'Adding…' : 'Add'; action.disabled = adding; action.className = paper ? 'btn-quiet' : 'btn-accent';
    action.setAttribute('aria-label', `${action.textContent} ${row.title}`); mark.hidden = !paper;
    action.onclick = () => paper ? openPaper(paper.id) : run('/api/import', {url: 'https://arxiv.org/abs/' + row.arxiv_id});
  };
  update(); results.updates.push(update); item.append(text, action);
  return item;
}
// The Home field: the input rules, Suggestions, keys, and the ARIA combobox.
function bindSearch(form) {
  const input = form.querySelector('input'), popup = node('div', undefined, 'suggestions'), list = node('div'), note = node('p', DOWN), credit = node('p', $('results-credit').textContent);
  let rows = [], remote = [], down = false, active = -1, request = 0, timer;
  list.id = input.id + '-suggestions'; list.setAttribute('role', 'listbox'); list.setAttribute('aria-label', 'Suggestions');
  popup.hidden = true; popup.append(list, note, credit); form.append(popup);
  for (const [name, value] of [['role', 'combobox'], ['aria-autocomplete', 'list'], ['aria-controls', list.id], ['aria-expanded', 'false'], ['autocomplete', 'off']]) input.setAttribute(name, value);
  const highlight = index => {
    active = index;
    for (const [at, option] of [...list.children].entries()) option.setAttribute('aria-selected', String(at === index));
    if (index < 0) input.removeAttribute('aria-activedescendant');
    else { input.setAttribute('aria-activedescendant', list.children[index].id); list.children[index].scrollIntoView({block: 'nearest'}); }
  };
  const draw = query => {
    rows = searchRows(state.papers, query, remote, 3, 8);
    list.replaceChildren(...rows.map((row, index) => {
      const option = node('div', undefined, 'suggestion'), meta = node('span', [row.year, row.arxiv_id].filter(Boolean).join(' · '), 'suggestion-meta');
      option.id = `${list.id}-${index}`; option.setAttribute('role', 'option');
      if (rowState(row, state.papers, []).paper) meta.append(node('span', 'In library', 'library-mark'));
      option.append(node('span', row.title, 'suggestion-title'), node('span', authorList(row.id ? authorNames(row.authors) : row.authors, 3), 'search-authors'), meta);
      option.onclick = () => choose(row);
      return option;
    }));
    note.hidden = !down; credit.hidden = !rows.some(row => !row.id);
    popup.hidden = !rows.length && !down; input.setAttribute('aria-expanded', String(!popup.hidden));
    highlight(Math.min(active, rows.length - 1));
  };
  // Closing also drops a Suggestions response still on its way.
  const close = () => { clearTimeout(timer); request++; remote = []; down = false; popup.hidden = true; input.setAttribute('aria-expanded', 'false'); highlight(-1); };
  const choose = row => {
    const paper = rowState(row, state.papers, state.jobs).paper;
    close(); input.value = '';
    return paper ? openPaper(paper.id) : run('/api/import', {url: 'https://arxiv.org/abs/' + row.arxiv_id});
  };
  input.oninput = () => {
    const query = input.value.trim();
    if (inputKind(query) !== 'search') return close();
    clearTimeout(timer); const mine = ++request, live = query.length >= 3 && state.settings.search_suggestions !== false;
    if (!live) { remote = []; down = false; }
    active = -1; draw(query);
    if (live) timer = setTimeout(async () => {
      const response = await paperSearch(query, 8);
      // The rows change under the highlight, so keeping its index would point at another Paper.
      if (mine === request) { remote = response.results; down = Boolean(response.error); active = -1; draw(query); }
    }, 400);
  };
  input.onkeydown = event => {
    if (popup.hidden || !['ArrowDown', 'ArrowUp', 'Escape'].includes(event.key)) return;
    event.preventDefault(); event.stopPropagation(); // Escape would also clear a search field.
    const count = rows.length;
    if (event.key === 'Escape') close();
    else if (count) highlight(event.key === 'ArrowDown' ? (active + 2) % (count + 1) - 1 : (active + count + 1) % (count + 1) - 1);
  };
  // WebKit does not focus a clicked button, so without this Go would close the list and lose the highlight.
  popup.onmousedown = form.querySelector('button').onmousedown = event => event.preventDefault();
  form.addEventListener('focusout', event => { if (!form.contains(event.relatedTarget)) close(); });
  form.onsubmit = async event => {
    event.preventDefault();
    const row = rows[active], text = input.value.trim(), kind = inputKind(text);
    close();
    if (row) choose(row);
    else if (kind === 'search') { input.value = ''; commands.run({name: 'search', query: text, submit: true}); }
    else if (kind === 'import' && await run('/api/import', {url: text})) input.value = '';
  };
}
bindSearch($('home-form'));

// ---- Settings: one view with panes, a dialog in the main window, or the whole page in ?panel=settings ----
const PANES = ['general', 'reading', 'ai', 'kindle', 'search', 'help'];
let settingsPane = 'general';
function showPane(pane) {
  settingsPane = PANES.includes(pane) ? pane : settingsPane;
  for (const section of document.querySelectorAll('.pane')) section.hidden = section.dataset.pane !== settingsPane;
  for (const button of document.querySelectorAll('.settings-panes button')) button.setAttribute('aria-selected', String(button.dataset.pane === settingsPane));
  $('settings-save').hidden = ['reading', 'help'].includes(settingsPane);
}
for (const button of document.querySelectorAll('.settings-panes button')) button.onclick = () => showPane(button.dataset.pane);
const normalizedEndpoint = endpoint => (endpoint || '').trim().replace(/\/+$/, '');
const providerControls = setup => { const prefix = setup ? 'setup-' : ''; return {preset: $(prefix + 'provider-preset'), endpoint: $(prefix + 'endpoint'), custom: $(prefix + 'custom-endpoint'), limits: $(prefix + 'provider-limits')}; };
function renderProvider(setup, endpoint) {
  const fields = providerControls(setup), normalized = normalizedEndpoint(endpoint);
  const match = Object.entries(PROVIDER_PRESETS).find(([, value]) => normalizedEndpoint(value.endpoint) === normalized);
  fields.preset.value = match ? match[0] : normalized ? 'custom' : 'openai';
  fields.endpoint.value = match ? match[1].endpoint : normalized ? endpoint : PROVIDER_PRESETS.openai.endpoint;
  fields.endpoint.dataset.provider = fields.preset.value;
  if (fields.preset.value === 'custom') fields.endpoint.dataset.customValue = fields.endpoint.value;
  updateProviderDetails(setup);
}
function updateProviderDetails(setup) {
  const fields = providerControls(setup), preset = PROVIDER_PRESETS[fields.preset.value];
  fields.custom.hidden = Boolean(preset);
  const limits = state.provider_limits?.[preset ? new URL(preset.endpoint).hostname : 'custom'];
  fields.limits.textContent = limits ? 'Automatic limit: ' + limits + '. Paper input is not capped.' : '';
}
function changeProvider(setup) {
  const fields = providerControls(setup);
  if (fields.endpoint.dataset.provider === 'custom') fields.endpoint.dataset.customValue = fields.endpoint.value;
  const preset = PROVIDER_PRESETS[fields.preset.value];
  fields.endpoint.value = preset?.endpoint || fields.endpoint.dataset.customValue || '';
  fields.endpoint.dataset.provider = fields.preset.value;
  updateProviderDetails(setup);
  $(setup ? 'setup-connection-status' : 'connection-status').textContent = '';
  if (setup) updateSetupKeyStatus();
}
const connectionEndpoint = setup => providerControls(setup).endpoint.value.trim();
const KEY_SAVED = 'A key is saved in macOS Keychain. Leave blank to keep it.', KEY_NONE = 'Keys are stored in macOS Keychain, never in this page.';
function fillSettings() {
  const settings = state.settings || {};
  $('connection-status').textContent = ''; $('settings-error').textContent = '';
  renderProvider(false, settings.endpoint || PROVIDER_PRESETS.openai.endpoint);
  $('model').value = settings.model || ''; $('kindle-email').value = settings.kindle_email || '';
  // Any other stored value reads as Auto: true or false from before the levels, and the retired Off.
  $('overview-reasoning').value = ['low', 'medium', 'high'].includes(settings.overview_reasoning) ? settings.overview_reasoning : 'auto';
  $('overview-language').value = settings.overview_language || 'casual'; $('overview-length').value = settings.overview_length || 'medium';
  $('auto-summary').checked = Boolean(settings.auto_summary); $('auto-send').checked = Boolean(settings.auto_send);
  $('resume-reading').checked = Boolean(settings.resume_reading); $('open-imports').checked = settings.open_imports !== false;
  $('search-suggestions').checked = settings.search_suggestions !== false;
  $('api-key').value = ''; $('s2-api-key').value = '';
  $('key-status').textContent = settings.has_key ? KEY_SAVED : KEY_NONE;
  $('s2-key-status').textContent = settings.has_s2_key ? KEY_SAVED : KEY_NONE;
  const missing = Object.entries(state.dependencies || {}).filter(([, available]) => !available).map(([name]) => name);
  $('dependencies').textContent = missing.length ? `Not installed: ${missing.join(', ')}. Install these tools before converting papers.` : 'All conversion tools are available.';
}
// A pane switch keeps unsaved edits; only opening the dialog reads the saved settings again.
function openSettings(pane) {
  showPane(pane || settingsPane);
  if (panel || $('settings-dialog').open) return;
  fillSettings(); $('settings-dialog').showModal();
}
register('settings', ({pane} = {}) => openSettings(pane));
const clearKeys = () => { $('api-key').value = ''; $('s2-api-key').value = ''; };
$('settings-close').onclick = () => $('settings-dialog').close();
$('settings-dialog').addEventListener('close', clearKeys);
$('settings-form').addEventListener('invalid', event => { const pane = event.target.closest('.pane'); if (pane) showPane(pane.dataset.pane); }, true);
$('settings-form').onsubmit = async event => {
  event.preventDefault();
  const payload = {endpoint: connectionEndpoint(false), model: $('model').value.trim(), kindle_email: $('kindle-email').value.trim(), auto_summary: $('auto-summary').checked, auto_send: $('auto-send').checked,
    overview_reasoning: $('overview-reasoning').value, overview_language: $('overview-language').value, overview_length: $('overview-length').value,
    resume_reading: $('resume-reading').checked, open_imports: $('open-imports').checked, search_suggestions: $('search-suggestions').checked};
  if ($('api-key').value) payload.api_key = $('api-key').value;
  if ($('s2-api-key').value.trim()) payload.s2_api_key = $('s2-api-key').value.trim();
  try {
    state.settings = await api('/api/settings', payload); clearKeys(); fillSettings();
    if (panel) { $('settings-save').textContent = 'Saved'; setTimeout(() => { $('settings-save').textContent = 'Save'; }, 1500); }
    else { $('settings-dialog').close(); await refresh(); notice('Settings saved.', true); }
  } catch (error) { clearKeys(); $('settings-error').textContent = error.message; }
};
async function testConnection(setup) {
  const button = $(setup ? 'setup-test-connection' : 'test-connection'), status = $(setup ? 'setup-connection-status' : 'connection-status');
  const values = () => ({endpoint: connectionEndpoint(setup), model: $(setup ? 'setup-model' : 'model').value.trim(), api_key: $(setup ? 'setup-key' : 'api-key').value.trim()});
  const payload = values();
  button.disabled = true; status.textContent = 'Testing connection…'; status.dataset.state = 'testing';
  try {
    const result = await api('/api/test-connection', payload);
    const unchanged = JSON.stringify(values()) === JSON.stringify(payload);
    status.textContent = unchanged ? result.message : 'Connection fields changed. Test again.'; status.dataset.state = unchanged ? 'success' : 'changed';
  } catch (error) { status.textContent = error.message; status.dataset.state = 'error'; }
  finally { button.disabled = false; }
}
$('test-connection').onclick = () => testConnection(false);
$('setup-test-connection').onclick = () => testConnection(true);
for (const [prefix, fields, status] of [['', ['endpoint', 'model', 'api-key'], 'connection-status'], ['setup-', ['endpoint', 'model', 'key'], 'setup-connection-status']]) {
  for (const field of fields) $(prefix + field).addEventListener('input', () => { $(status).textContent = ''; });
}
$('provider-preset').onchange = () => changeProvider(false);
$('setup-provider-preset').onchange = () => changeProvider(true);

// ---- Setup: once, on the first launch ----
function openSetup() {
  $('setup-connection-status').textContent = '';
  if ($('settings-dialog').open) $('settings-dialog').close();
  const settings = state.settings || {};
  renderProvider(true, settings.endpoint || PROVIDER_PRESETS.openai.endpoint);
  $('setup-model').value = settings.model || ''; $('setup-key').value = '';
  $('setup-kindle').value = settings.kindle_email || ''; $('setup-resume').checked = Boolean(settings.resume_reading);
  $('setup-error').textContent = ''; updateSetupKeyStatus(); $('setup-dialog').showModal();
}
function updateSetupKeyStatus() {
  const sameEndpoint = normalizedEndpoint(connectionEndpoint(true)) === normalizedEndpoint(state.settings?.endpoint);
  $('setup-key-status').textContent = sameEndpoint && state.settings?.has_key ? 'Your key is already saved. Leave blank to keep it.' : 'Saved securely in macOS Keychain.';
}
$('setup-open').onclick = openSetup;
$('setup-endpoint').oninput = updateSetupKeyStatus;
$('setup-dialog').addEventListener('close', () => { $('setup-key').value = ''; });
async function completeSetup(values = {}) {
  $('setup-save').disabled = true; $('setup-skip').disabled = true;
  try {
    state.settings = await api('/api/settings', {...values, onboarding_complete: true});
    $('setup-key').value = ''; $('setup-dialog').close();
    if (!panel) syncChrome();
  } catch (error) { $('setup-key').value = ''; $('setup-error').textContent = error.message; }
  finally { $('setup-save').disabled = false; $('setup-skip').disabled = false; }
}
$('setup-form').onsubmit = async event => {
  event.preventDefault();
  const endpoint = connectionEndpoint(true), model = $('setup-model').value.trim(), key = $('setup-key').value;
  if ((key || model) && (!endpoint || !model)) { $('setup-error').textContent = 'Add a base URL and model name for your AI connection, or leave the AI fields blank.'; return; }
  const values = {kindle_email: $('setup-kindle').value.trim(), resume_reading: $('setup-resume').checked};
  if (endpoint) values.endpoint = endpoint;
  if (model) values.model = model;
  if (key) values.api_key = key;
  await completeSetup(values);
};
$('setup-skip').onclick = $('setup-close').onclick = () => completeSetup({resume_reading: $('setup-resume').checked});
$('setup-dialog').addEventListener('cancel', event => { event.preventDefault(); completeSetup({resume_reading: $('setup-resume').checked}); });

// ---- The reader. Until reader.js replaces this block, it shows the header and the views as before. ----
let activeTab = 'overview', currentChapter = '', overviewSignature = '', readerObserver;
function viewState(kind) {
  if (kind === 'paper') return 'ready';
  return detail?.[kind] ? 'ready' : runningJob(kind) ? 'working' : aiReady() ? 'empty' : 'off';
}
export async function openPaper(id, {position} = {}) {
  const request = ++detailRequest;
  try {
    const result = await api(paperAPI(id)); if (request !== detailRequest) return;
    const changedPaper = selected !== id || $('reader-page').hidden;
    const documentChanged = !changedPaper && detail?.paper?.document_digest !== result.paper.document_digest;
    if (nav.current?.page !== 'reader' || nav.current.id !== id) nav.push({page: 'reader', id});
    showPage('reader'); selected = id; detail = result;
    const paper = result.paper, reading = position || summary(id)?.reading || {};
    if (changedPaper) drawReaderHeader(paper);
    const nextOverview = JSON.stringify([id, result.blog?.text, result.blog?.figures, result.overview]);
    if (nextOverview !== overviewSignature) {
      overviewSignature = nextOverview;
      prose($('blog-text'), cleanOverviewCitations(result.blog?.text), [], result.blog?.figures || []);
      prose($('overview-text'), result.overview?.text, [], result.overview?.figures || [], {inlineFigure});
      swapFigureSources(document.documentElement.dataset.theme);
    }
    const blogTitle = result.blog?.explanation?.title || result.blog?.explanation?.question || '';
    $('blog-title').textContent = blogTitle; $('blog-title').hidden = !blogTitle;
    for (const kind of ['overview', 'blog']) { const line = generationDetails(result[kind]); $(`${kind}-provenance`).textContent = line ? 'Generated with ' + line : ''; $(`${kind}-provenance`).hidden = !line; }
    const pdf = paper.format === 'pdf', chapters = paper.chapters || [];
    $('fallback-notice').hidden = !pdf; $('fallback-notice').textContent = pdf ? paper.report.warning : '';
    if (changedPaper) currentChapter = chapters.some(chapter => chapter.path === reading.chapter) ? reading.chapter : chapters[0]?.path || '';
    else if (!chapters.some(chapter => chapter.path === currentChapter)) currentChapter = chapters[0]?.path || '';
    const nextURL = fileURL(currentChapter), frame = $('paper-frame');
    if (nextURL && (documentChanged || changedPaper || !frame.getAttribute('src'))) {
      if (pdf) frame.removeAttribute('sandbox'); else frame.setAttribute('sandbox', 'allow-same-origin');
      frame.style.height = pdf ? '75vh' : ''; frame.src = nextURL;
    }
    if (!nextURL) frame.removeAttribute('src');
    if (changedPaper) {
      const start = ['overview', 'blog', 'paper'].includes(reading.view) && viewState(reading.view) !== 'off' ? reading.view : ['overview', 'blog'].find(kind => viewState(kind) === 'ready') || 'paper';
      switchTab(start, {save: false}); window.scrollTo(0, 0);
      // Opening a New Paper makes it Reading; every open moves it to the top of Recent.
      saveReading(id, {...(summary(id)?.reading ? {} : {state: 'reading'}), view: start}).catch(() => {});
    } else switchTab(activeTab, {save: false});
  } catch (error) { notice(error.message); }
}
function drawReaderHeader(paper) {
  const id = baseID(paper.arxiv_id || paper.id), month = arxivDate(id)?.label;
  $('reader-meta').textContent = [paper.arxiv_id ? `arXiv ${id}` : paper.id, month].filter(Boolean).join(' · ');
  $('reader-title').textContent = paper.title || paper.id;
  $('reader-authors').textContent = authorNames(paper.authors).join(', ');
  if (paper.arxiv_id) $('reader-arxiv').href = `https://arxiv.org/abs/${id}`; else $('reader-arxiv').removeAttribute('href');
  $('reader-pdf').href = fileURL('original.pdf');
}
function switchTab(name, {save = true} = {}) {
  if (!detail || !VIEW_LABELS[name] || viewState(name) === 'off' && name !== activeTab) return;
  activeTab = viewState(name) === 'off' ? 'paper' : name;
  for (const view of Object.keys(VIEW_LABELS)) $(view).hidden = view !== activeTab;
  $('reader-page').dataset.view = activeTab;
  drawViewState();
  if (activeTab === 'paper') styleReader();
  syncReaderChrome();
  if (save && selected) saveReading(selected, {view: activeTab, ...(currentChapter ? {chapter: currentChapter} : {})}).catch(() => {});
}
register('view', ({view}) => switchTab(view));
function drawViewState() {
  const kind = activeTab;
  if (kind === 'paper') return;
  const box = $(`${kind}-state`), label = VIEW_LABELS[kind], status = viewState(kind), paper = detail.paper, job = runningJob(kind);
  box.replaceChildren(); box.hidden = status === 'ready' && !job;
  if (box.hidden) return;
  if (status === 'ready' || status === 'working') {
    box.append(node('p', `${status === 'ready' ? 'Making a new' : 'Making the'} ${label}. ${typeof job?.progress === 'string' ? job.progress + '. ' : ''}You can read the Paper meanwhile.`));
    return;
  }
  const blocked = kind === 'overview' ? !paper.passages?.length : paper.format === 'pdf' && !paper.passages?.length;
  box.append(node('h2', `No ${label} yet`), node('p', kind === 'overview'
    ? 'An Overview is one figure that tells why the work was needed, how it works, and what it achieved.'
    : 'A Blog is an article that builds the context and links each claim to its passage in the Paper.'));
  const button = node('button', status === 'off' ? 'Connect AI…' : `Generate ${label}`, status === 'off' ? 'btn-quiet' : 'btn-accent');
  button.type = 'button';
  if (status === 'off') { box.append(node('p', 'Connect an AI provider in Settings to generate one.')); button.onclick = () => openSettings('ai'); }
  else if (blocked) { button.disabled = true; box.append(node('p', paper.report?.text_warning || 'This paper has no text to explain.')); }
  else button.onclick = () => generate(kind);
  box.append(button);
}
async function generate(kind) {
  if (!selected || !['overview', 'blog'].includes(kind)) return;
  const id = selected, result = await run(`${paperAPI(id)}/${kind}`, {});
  if (result && selected === id) { await openPaper(id); switchTab(kind); }
}
const chapterParts = title => { const match = String(title).match(/^(\d+(?:\.\d+)*)\.?\s+(.+)$/); return match ? [match[1], match[2]] : ['', String(title)]; };
function outline() {
  if (activeTab === 'paper') return (detail.paper.chapters || []).map(chapter => {
    const [number, label] = chapterParts(chapter.title || chapter.path);
    return {id: chapter.path, label, number, level: 1, current: chapter.path === currentChapter};
  });
  return [...$(`${activeTab}-text`).querySelectorAll(':scope > h2, :scope > h3')].map((heading, index) => {
    heading.id = `${activeTab}-section-${index}`;
    return {id: heading.id, label: heading.textContent, number: '', level: heading.tagName === 'H2' ? 1 : 2, current: false};
  });
}
function syncReaderChrome() {
  if (!detail) return;
  syncChrome();
  const paper = detail.paper, previous = nav.previous?.page, chapter = (paper.chapters || []).find(item => item.path === currentChapter);
  chrome.update({
    mode: 'reader', title: shortTitle(paper.title || paper.id), subtitle: activeTab === 'paper' ? chapter?.title || '' : VIEW_LABELS[activeTab],
    views: {current: activeTab, overview: viewState('overview'), blog: viewState('blog'), paper: 'ready'},
    sidebar: {selected: null, reader: {back: previous === 'search' ? 'Results' : previous === 'home' ? 'Home' : 'Library', title: paper.title || paper.id,
      byline: [byline(paper.authors), arxivDate(paper.arxiv_id || paper.id)?.label].filter(Boolean).join(' · '), outline: outline()}},
    actions: readerActions(),
  });
}
register('outline', ({id}) => {
  const chapter = (detail?.paper?.chapters || []).find(item => item.path === id);
  if (chapter) { currentChapter = chapter.path; const url = fileURL(chapter.path); if (url) $('paper-frame').src = url; syncReaderChrome(); window.scrollTo(0, 0); saveReading(selected, {view: 'paper', chapter: chapter.path}).catch(() => {}); }
  else document.getElementById(id)?.scrollIntoView({block: 'start'});
});
// What made a saved Overview or Blog: its model, reasoning effort, requests, tokens, time, and
// date. An older record lacks some of these, and the line names only what the record holds.
function generationDetails(generation) {
  const record = generation?.provenance || {};
  const usage = Array.isArray(record.usage) ? record.usage : [];
  const parts = record.model ? [record.model] : [];
  const options = usage.find(event => event.options)?.options;
  if (options) parts.push(options.reasoning ? options.reasoning[0].toUpperCase() + options.reasoning.slice(1) + ' reasoning' : 'No reasoning');
  const made = Date.parse(record.created_at);
  if (Number.isFinite(made)) parts.push(new Date(made).toLocaleDateString(undefined, {day: 'numeric', month: 'short', year: 'numeric'}));
  return parts.join(' · ');
}
const SVG_NS = 'http://www.w3.org/2000/svg';
const inlineFigures = new WeakMap();
// The Overview's Figure render goes into the page as SVG, in the Figure palette that matches the
// theme. The file is the application's own render; the parser still refuses anything that is not
// one SVG document, and the page's CSP runs no script from it.
async function inlineFigure(container, figure) {
  inlineFigures.set(container, figure);
  const theme = document.documentElement.dataset.theme;
  const url = theme === 'dark' && container.dataset.darkSrc ? container.dataset.darkSrc : container.dataset.lightSrc;
  if (!url) return;
  try {
    const response = await fetch(url, {credentials: 'same-origin'});
    if (!response.ok) throw new Error(response.statusText);
    const parsed = new DOMParser().parseFromString(await response.text(), 'image/svg+xml');
    const svg = parsed.documentElement;
    if (svg.namespaceURI !== SVG_NS || svg.tagName !== 'svg' || parsed.querySelector('parsererror')) throw new Error('not an SVG document');
    // A theme change while this file loaded started a newer call; that call draws the figure.
    if (document.documentElement.dataset.theme !== theme) return;
    svg.removeAttribute('width'); svg.removeAttribute('height');
    // The page above already names the paper, so the figure's "LOCALXIV · title" line and the 30
    // units papers/figures/render.py gives it are cut here. Exported files keep the line.
    const chromeLine = svg.querySelector('text'), box = svg.viewBox.baseVal;
    if (chromeLine?.textContent.startsWith('LOCALXIV · ') && box?.height > 30) {
      chromeLine.remove(); svg.setAttribute('viewBox', `${box.x} ${box.y + 30} ${box.width} ${box.height - 30}`);
    }
    svg.setAttribute('role', 'img'); svg.setAttribute('aria-label', figure.alt || figure.caption || 'Paper explanation');
    annotateFigure(svg.querySelectorAll('[data-node]'), figure.components, {svgNode: tag => document.createElementNS(SVG_NS, tag), onPassage: openPassage});
    container.replaceChildren(svg); container.dataset.theme = theme; container.removeAttribute('aria-busy');
  } catch {
    container.replaceChildren(node('p', 'Figure unavailable. Regenerate this view to restore it.', 'help'));
    container.removeAttribute('aria-busy');
  }
}
function swapFigureSources(theme) {
  for (const img of document.querySelectorAll('img[data-dark-src]')) {
    const next = theme === 'dark' ? img.dataset.darkSrc : img.dataset.lightSrc;
    if (img.getAttribute('src') !== next) img.src = next;
  }
  for (const container of document.querySelectorAll('.figure-inline[data-dark-src]')) {
    if (container.dataset.theme !== theme && inlineFigures.has(container)) inlineFigure(container, inlineFigures.get(container));
  }
}
function openPassage(id) {
  const passage = (detail?.overview?.evidence || []).find(item => item.id === id);
  jumpToPaper(passage && fileURL(passage.href));
}
function jumpToPaper(url) { if (!url) return; $('paper-frame').src = url; switchTab('paper'); }
// MathJax is bundled locally. Only formula text reaches its restricted TeX parser.
let mathQueue = Promise.resolve();
function renderMath(element, tex, display) {
  if (!window.MathJax?.startup?.promise) return;
  mathQueue = mathQueue.then(async () => {
    await window.MathJax.startup.promise;
    if (!element.isConnected) return;
    const rendered = await window.MathJax.tex2svgPromise(tex, {display});
    if (rendered.querySelector('[data-mjx-error]')) return; // Keep readable source for invalid TeX.
    window.MathJax.startup.document.addStyleSheet();
    element.replaceChildren(rendered);
  }).catch(() => {}); // A malformed expression must not stop the rest of the article.
}
// Only the Overview passes inlineFigure: a Blog figure keeps the image path and its portrait variant.
const prose = (target, text, references, figures, extra = {}) => renderProse(target, text, {node, references, figures, fileURL, renderMath, openFigure, ...extra,
  openSource: href => jumpToPaper(fileURL(href))});
const cssToken = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
function styleReader() {
  if (detail?.paper?.format === 'pdf') return;
  const doc = $('paper-frame').contentDocument;
  if (!doc?.body || !doc.head) return;
  let style = doc.getElementById('app-reading-style');
  if (!style) { style = doc.createElement('style'); style.id = 'app-reading-style'; doc.head.append(style); }
  style.textContent = readerStylesheet({theme: document.documentElement.dataset.theme, prefs,
    tokens: {paper: cssToken('--paper'), ink: cssToken('--ink'), label: cssToken('--label'), label2: cssToken('--label-2'), accent: cssToken('--accent'), figureMaxHeight: Math.round(innerHeight * .55)}});
  resizeReader();
}
function resizeReader() {
  if (detail?.paper?.format === 'pdf') return;
  const frame = $('paper-frame');
  if (frame.contentDocument?.body && !$('paper').hidden) frame.style.height = Math.ceil(frame.contentDocument.body.getBoundingClientRect().height + 20) + 'px';
}
$('paper-frame').onload = () => {
  readerObserver?.disconnect();
  if (detail?.paper?.format === 'pdf') return;
  styleReader();
  const doc = $('paper-frame').contentDocument; if (!doc?.body) return;
  doc.addEventListener('keydown', keydown);
  readerObserver = new ResizeObserver(resizeReader); readerObserver.observe(doc.body);
  const chapter = (detail?.paper?.chapters || []).find(item => doc.location.pathname.endsWith('/' + item.path));
  if (chapter && chapter.path !== currentChapter) { currentChapter = chapter.path; syncReaderChrome(); }
  if (doc.location.hash && activeTab === 'paper') {
    requestAnimationFrame(() => {
      const target = doc.getElementById(decodeURIComponent(doc.location.hash.slice(1)));
      if (target) window.scrollTo(0, window.scrollY + $('paper-frame').getBoundingClientRect().top + target.getBoundingClientRect().top - 72);
    });
  }
  for (const image of doc.querySelectorAll('figure img')) {
    image.tabIndex = 0; image.setAttribute('role', 'button'); image.setAttribute('aria-label', 'Enlarge figure');
    const open = () => openFigure(image.src, image.alt, image.closest('figure')?.querySelector('figcaption')?.textContent);
    image.onclick = open; image.onkeydown = event => { if (['Enter', ' '].includes(event.key)) { event.preventDefault(); open(); } };
  }
};
addEventListener('resize', styleReader);

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
function openFigure(url, alt, caption, panels, dimensions) {
  const list = figurePanels(panels), image = $('figure-image');
  figureView = {url, alt, caption, panels: list, dimensions: dimensions || null, unit: 0, fit: true};
  image.src = url; image.alt = alt || 'Paper figure'; image.removeAttribute('style');
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
    const next = await api('/api/state'); state = next;
    adoptServerPrefs();
    if (panel) return;
    if (selected && !next.papers.some(paper => paper.id === selected)) go({page: 'library', filter: 'all'});
    if (!stateInitialized) { for (const job of next.jobs) if (job.kind === 'import' && TERMINAL.has(job.state)) completedImports.add(job.id); stateInitialized = true; }
    const papers = JSON.stringify(next.papers), jobs = JSON.stringify(next.jobs);
    if (papers !== stateSignature) { stateSignature = papers; drawPages(); }
    if (jobs !== jobSignature) {
      jobSignature = jobs; jobNotices.render(state.jobs, state.papers); drawJobList();
      downloadFinishedExports(next.jobs);
      const imported = next.jobs.find(job => job.kind === 'import' && job.state === 'ready' && job.result?.paper_id && next.papers.some(paper => paper.id === job.result.paper_id) && !completedImports.has(job.id));
      for (const job of next.jobs) if (job.kind === 'import' && TERMINAL.has(job.state)) completedImports.add(job.id);
      if (imported && next.settings.open_imports !== false) await openPaper(imported.result.paper_id);
      else if (selected) await openPaper(selected);
    }
    for (const update of results.updates) update();
    syncChrome(); if (selected) syncReaderChrome();
  } catch (error) { notice(error.message); }
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
