// The reader: the Paper view with its Reference previews, the outline, the Reading position, the Blog
// and Overview views, Split view, and the generation states.
// app.js imports this module and this module imports app.js. This module's top level only registers
// handlers, so neither module reads the other's bindings before both have run.
import {register, chrome, nav, keydown, commands, native} from './shell.js';
import {node, icon, renderProse, annotateFigure, figureFailure, TERMINAL, authorNames, byline, arxivDate, shortTitle, baseID, readingState, inputKind} from './render.js';
import {readerStylesheet} from './appearance.js';
import {mountMargin, unmountMargin, syncCards} from './margin.js';
import {api, paperAPI, fileURL, saveReading, notice, run, showPage, syncChrome, openSettings, openFigure, readerActions,
  aiReady, runningJob, summary, state, prefs} from './app.js';

const $ = id => document.getElementById(id);
const frame = $('paper-frame');
const VIEW_LABELS = {overview: 'Overview', blog: 'Blog', paper: 'Paper'};
const SPLIT_WIDTH = 1200;
export let selected = null, detail = null, activeTab = 'overview';
// `loaded` is the chapter in the frame; `chapter` is the one the reader is on. They differ only while a chapter loads.
let request = 0, chapter = '', loaded = '', frameReady = false, pending = null, resume = null, headings = [], panels = [], sources = new Map();
let split = false, current = '', explanations = '', chapnavSignature = '', stateSignature = '', observer = null, viewScroll = {};
// A jump moves the page, but the Reading position moves only after the reader's own input.
let jumpedAt = 0, lastInput = 0, saveTimer = 0, spyFrame = 0, spyTimer = 0, pinned = '', pinnedAt = 0;
// The web toolbar covers the page's top 52 px. The Native shell's toolbar and sidebar cover the web view too, but its
// obscured insets start WebKit's viewport below and beside them, so in the shell the page's edges are the visible edges.
const topInset = () => native ? 16 : 68;
const isPDF = () => detail?.paper?.format === 'pdf';
const chapters = () => detail?.paper?.chapters || [];
const knownChapter = path => chapters().some(item => item.path === path);
const chapterParts = title => { const match = String(title).match(/^(\d+(?:\.\d+)*)\.?\s+(.+)$/); return match ? [match[1], match[2]] : ['', String(title)]; };

// The view's own card shows its running job, and its last failure while nothing is saved, so that job needs no toast.
export const viewShows = job => Boolean(detail) && !$('reader-page').hidden && job.kind === activeTab && job.payload?.paper_id === selected
  && (!TERMINAL.has(job.state) || ['failed', 'interrupted'].includes(job.state) && !detail[job.kind]);
function viewState(kind) {
  if (kind === 'paper') return 'ready';
  return detail?.[kind] ? 'ready' : runningJob(kind) ? 'working' : aiReady() ? 'empty' : 'off';
}
const CONNECT = 'Connect an AI provider in Settings to make one.';
// A Paper with no passages has no text to explain, so it cannot have an Overview, and a PDF cannot have a Blog.
// A connection cannot change that, so this reason comes before CONNECT. Returns the reason or false.
// The warning stored at import is not used, because older imports name only the Overview.
const noText = kind => !detail.paper.passages?.length && (kind === 'overview' || isPDF()) && 'This Paper has no text that LocalXiv can read, so it cannot have an Overview or a Blog.';
// The web toolbar's tooltip for a view: the reason that the view itself gives.
function viewTip(kind) {
  const status = viewState(kind);
  return status === 'working' ? 'Being made now' : status === 'ready' ? '' : noText(kind) || (status === 'off' ? CONNECT : '');
}

// ---- Opening a Paper ----
// `position` comes from a history entry, so Back and Forward restore it also inside the same Paper.
export async function openPaper(id, {position, scroll} = {}) {
  const mine = ++request;
  let result;
  try { result = await api(paperAPI(id)); } catch (error) { notice(error.message); return; }
  if (mine !== request) return;
  const changed = selected !== id || $('reader-page').hidden;
  if (nav.current?.page !== 'reader' || nav.current.id !== id) nav.push({page: 'reader', id});
  showPage('reader');
  if (changed || detail?.paper?.document_digest !== result.paper.document_digest) { loaded = ''; documents.clear(); }
  selected = id; detail = result;
  const paper = result.paper, list = chapters();
  if (changed) { drawHeader(paper); closeSplit(); viewScroll = {}; resume = null; }
  drawExplanations(result);
  $('fallback-notice').hidden = !isPDF(); $('fallback-notice').textContent = isPDF() ? paper.report.warning : '';
  const reading = position || (changed ? summary(id)?.reading || {} : null);
  if (reading) {
    chapter = knownChapter(reading.chapter) ? reading.chapter : list[0]?.path || '';
    const view = VIEW_LABELS[reading.view] && (position || viewState(reading.view) !== 'off') ? reading.view
      : ['overview', 'blog'].find(kind => viewState(kind) === 'ready') || 'paper';
    activeTab = view;
  } else if (!knownChapter(chapter)) chapter = list[0]?.path || '';
  showView();
  // A fresh open with no passage shows the Paper's header; a saved or history passage scrolls to that paragraph.
  const target = reading && activeTab === 'paper' ? {anchor: reading.anchor, offset: reading.offset, page: !reading.anchor} : null;
  if (chapter && chapter !== loaded && (activeTab === 'paper' || !isPDF())) loadChapter(chapter, target);
  else if (target) scrollToTarget(target);
  if (reading && activeTab !== 'paper') {
    const section = !position && activeTab === 'blog' && reading.section ? entryTop(reading.section) : null;
    window.scrollTo(0, section === null ? scroll || 0 : window.scrollY + section - topInset());
    jumpedAt = Date.now(); resume = reading.anchor ? {anchor: reading.anchor, offset: reading.offset} : null;
  }
  // Opening a New Paper makes it Reading; every open moves it to the top of Recent.
  if (changed && !position) saveReading(id, {...(summary(id)?.reading ? {} : {state: 'reading'}), view: activeTab}).catch(() => {});
}
export function closeReader() { ++request; closePreview(); closeSplit(); unmountMargin(); selected = null; detail = null; }

function drawHeader(paper) {
  const id = baseID(paper.arxiv_id || paper.id), month = arxivDate(id)?.label;
  $('reader-meta').textContent = [paper.arxiv_id ? `arXiv ${id}` : paper.id, month].filter(Boolean).join(' · ');
  $('reader-title').textContent = paper.title || paper.id;
  $('reader-authors').textContent = authorNames(paper.authors).join(', ');
  if (paper.arxiv_id) $('reader-arxiv').href = `https://arxiv.org/abs/${id}`; else $('reader-arxiv').removeAttribute('href');
  $('reader-pdf').href = fileURL('original.pdf');
}

// ---- Views ----
function showView() {
  pinned = '';
  for (const view of Object.keys(VIEW_LABELS)) $(view).hidden = view !== activeTab && !(view === 'paper' && split);
  $('reader-page').dataset.view = activeTab;
  drawViewState();
  // A PDF viewer that loads in a hidden frame lays its pages out at zero width, so a PDF loads when it shows.
  if (activeTab === 'paper' && isPDF() && chapter && chapter !== loaded) loadChapter(chapter);
  if (activeTab === 'paper') styleReader();
  // Question cards need the Paper's text, so a PDF has none.
  if (activeTab === 'paper' && !split && !isPDF()) mountMargin(); else unmountMargin();
  syncReaderChrome();
}
function switchTab(name) {
  if (!detail || !VIEW_LABELS[name] || name === activeTab && !split) return;
  // From the Split view pane, the Paper view opens at the passage the pane shows.
  const fromPane = split && name === 'paper' ? topPassage() : null;
  flushPosition();
  viewScroll[activeTab] = window.scrollY;
  closeSplit(); activeTab = name; showView();
  if (fromPane) scrollToTarget({anchor: fromPane.anchor, user: true});
  else if (name === 'paper' && viewScroll.paper === undefined && resume) scrollToTarget(resume);
  else window.scrollTo(0, viewScroll[name] || 0);
  // A citation jump or the Split view pane sets `chapter` too, so the chapter saves only when the reader scrolls there
  // or opens the Paper view at the pane's passage.
  saveReading(selected, fromPane ? {view: name, chapter, anchor: fromPane.anchor} : {view: name}).catch(() => {});
}
register('view', ({view}) => switchTab(view));

function drawViewState() {
  const kind = activeTab;
  if (kind === 'paper') return;
  const box = $(`${kind}-state`), label = VIEW_LABELS[kind], status = viewState(kind), job = runningJob(kind);
  const last = state.jobs.find(item => item.kind === kind && item.payload?.paper_id === selected);
  // The poll calls this often; a rebuild would drop focus from the box's button.
  const signature = JSON.stringify([selected, kind, status, job?.state, job?.progress, last?.id, last?.state]);
  if (signature === stateSignature) return;
  stateSignature = signature;
  box.replaceChildren(); box.hidden = status === 'ready' && !job;
  if (box.hidden) return;
  if (job) {
    box.append(node('h2', `${status === 'ready' ? 'Making a new' : 'Making the'} ${label}`),
      node('p', `${typeof job.progress === 'string' ? job.progress + '. ' : ''}You can read the Paper meanwhile.`));
    const bar = node('progress'); bar.setAttribute('aria-label', `${label} progress`);
    if (typeof job.progress === 'number') { bar.max = 100; bar.value = job.progress; }
    box.append(bar);
    return;
  }
  const button = node('button', undefined, 'btn-accent');
  button.type = 'button';
  if (status === 'empty' && ['failed', 'interrupted'].includes(last?.state)) {
    box.append(node('h2', `The ${label} could not be made`), node('p', last.error || 'The job stopped before it finished.'));
    button.textContent = 'Retry'; button.onclick = () => generate(kind);
    box.append(button);
    return;
  }
  const reason = noText(kind);
  box.append(node('h2', `No ${label} yet`), node('p', kind === 'overview'
    ? 'An Overview is one figure that tells why the work was needed, how it works, and what it achieved.'
    : 'A Blog is an article that builds the context and links each claim to its passage in the Paper.'));
  // A Paper with no text can never have this view, so it gets the reason and no button.
  if (reason) return box.append(node('p', reason));
  if (status === 'off') {
    box.append(node('p', CONNECT));
    button.textContent = 'Connect AI…'; button.className = 'btn-quiet'; button.onclick = () => openSettings('ai');
  } else { button.textContent = `Generate ${label}`; button.onclick = () => generate(kind); }
  box.append(button);
}
export async function generate(kind) {
  if (!selected || !['overview', 'blog'].includes(kind)) return;
  const id = selected, result = await run(`${paperAPI(id)}/${kind}`, {});
  if (result && selected === id) { await openPaper(id); switchTab(kind); }
}

// ---- Chrome state and the outline ----
export function syncReaderChrome() {
  if (!detail) return;
  syncChrome();
  const paper = detail.paper, origin = nav.origin?.page, item = chapters().find(entry => entry.path === chapter);
  current = currentEntry();
  chrome.update({
    mode: 'reader', title: shortTitle(paper.title || paper.id), subtitle: activeTab === 'paper' ? item?.title || '' : VIEW_LABELS[activeTab],
    views: {current: activeTab, overview: viewState('overview'), blog: viewState('blog'), paper: 'ready'},
    sidebar: {selected: null, reader: {back: origin === 'search' ? 'Results' : origin === 'home' ? 'Home' : 'Library', title: paper.title || paper.id,
      byline: [byline(paper.authors), arxivDate(paper.arxiv_id || paper.id)?.label].filter(Boolean).join(' · '), outline: outline()}},
    actions: readerActions(),
  });
  for (const kind of ['overview', 'blog']) { const tip = viewTip(kind); $(`tb-view-${kind}`).title = tip; $(`tb-view-${kind}`).setAttribute('aria-description', tip); }
  drawViewState(); drawChapnav(); syncCards();
}
const blogHeadings = () => [...$('blog-text').querySelectorAll(':scope > h2, :scope > h3')];
function outline() {
  const row = (id, label, number, level) => ({id, label, number, level, current: id === current});
  if (activeTab === 'paper') {
    // The web sidebar draws an entry without an id as a note.
    if (isPDF()) return [{id: '', label: 'A PDF has no sections.', number: '', level: 1, current: false}];
    return chapters().flatMap(item => {
      const [number, label] = chapterParts(item.title || item.path);
      return [row(item.path, label, number, 1), ...(item.path === chapter ? headings.map(heading => row(`${item.path}#${heading.id}`, heading.label, heading.number, heading.level)) : [])];
    });
  }
  if (activeTab === 'blog') {
    const list = blogHeadings(), top = Math.min(...list.map(heading => Number(heading.localName[1])));
    return list.map(heading => row(heading.id, heading.textContent, '', Number(heading.localName[1]) - top + 1));
  }
  return panels.map(panel => {
    // A heading reads "Why: …", or "1 · …" in older Overviews; the lead goes in the number column.
    const [, lead, rest] = String(panel.title || panel.id).match(/^(\w+)(?::|\s·)\s*(.+)$/) || [, '', panel.title || panel.id];
    return row(`panel:${panel.id}`, rest[0].toUpperCase() + rest.slice(1), lead, 1);
  });
}
// The entry the reader is in: the last heading above the line under the toolbar. An entry the reader picked in
// the outline stays current, because the page may not scroll far enough to bring it up. It stays until the
// reader's next input, or until a scroll without input, such as from the find bar, takes its target out of view.
function currentEntry() {
  if (!detail) return '';
  if (pinned && lastInput <= pinnedAt) {
    const top = entryTop(pinned);
    if (top === null || top > topInset() - 32 && top < innerHeight) return pinned;
    pinned = '';
  }
  const atEnd = !split && innerHeight + window.scrollY >= document.documentElement.scrollHeight - 2;
  if (activeTab === 'paper') {
    const line = frameLine();
    if (atEnd && headings.length) return `${chapter}#${headings.at(-1).id}`;
    return headings.reduce((id, heading) => heading.element.getBoundingClientRect().top <= line + 8 ? `${chapter}#${heading.id}` : id, chapter);
  }
  const tops = activeTab === 'blog' ? blogHeadings().map(heading => [heading.id, heading.getBoundingClientRect().top])
    : panels.map(panel => [`panel:${panel.id}`, panelTop(panel)]).filter(([, top]) => top !== null);
  if (atEnd && tops.length) return tops.at(-1)[0];
  return tops.reduce((id, [entry, top]) => top <= topInset() + 8 ? entry : id, tops[0]?.[0] || '');
}
// The window position of an outline entry's target, or null while its chapter loads or when it has none.
function entryTop(id) {
  if (activeTab !== 'paper') {
    return (id.startsWith('panel:') ? panelTop(panels.find(panel => `panel:${panel.id}` === id)) : document.getElementById(id)?.getBoundingClientRect().top) ?? null;
  }
  const cut = id.indexOf('#'), path = cut < 0 ? id : id.slice(0, cut);
  if (path !== loaded || !frameReady) return null;
  const frameTop = frame.getBoundingClientRect().top, element = cut < 0 ? null : frame.contentDocument?.getElementById(id.slice(cut + 1));
  return cut < 0 ? frameTop : element ? frameTop + element.getBoundingClientRect().top : null;
}
function panelTop(panel) {
  const svg = $('overview-text').querySelector('.figure-inline svg'), box = svg?.viewBox.baseVal;
  if (!box?.height || typeof panel?.y !== 'number') return null;
  const rect = svg.getBoundingClientRect();
  return rect.top + (panel.y - box.y) * rect.height / box.height;
}
register('outline', ({id}) => {
  if (!detail || typeof id !== 'string' || !id) return;
  if (activeTab === 'paper') {
    const cut = id.indexOf('#'), path = cut < 0 ? id : id.slice(0, cut);
    if (!knownChapter(path)) return;
    goChapter(path, cut < 0 ? '' : id.slice(cut + 1));
  } else {
    const top = entryTop(id);
    if (top === null) return;
    // A native sidebar click is not page input, but it is the reader's own choice, so it moves the Reading position.
    lastInput = Date.now();
    window.scrollTo(0, window.scrollY + top - topInset());
  }
  pinned = id; pinnedAt = Date.now();
  syncReaderChrome();
});
// A hidden web view runs no animation frames, so a timer also runs the check there.
function spy() {
  cancelAnimationFrame(spyFrame); clearTimeout(spyTimer); spyFrame = 0;
  if (currentEntry() !== current) syncReaderChrome();
}

// ---- The Paper frame ----
function loadChapter(path, target = null) {
  const url = fileURL(path);
  if (!url) return;
  chapter = loaded = path; pending = target; frameReady = false; headings = [];
  if (isPDF()) frame.removeAttribute('sandbox'); else frame.setAttribute('sandbox', 'allow-same-origin allow-scripts');
  frame.style.height = isPDF() ? 'calc(100vh - 140px)' : '';
  frame.src = url;
  $('split-title').textContent = chapters().find(item => item.path === path)?.title || 'Paper';
  syncReaderChrome();
}
// Outline and chapter links are the reader's own choice, so they move the Reading position.
function goChapter(path, anchor) {
  if (path === loaded) scrollToTarget({anchor, user: true});
  else { loadChapter(path, {anchor, user: true}); saveReading(selected, {view: 'paper', chapter: path, anchor: ''}).catch(() => {}); }
}
// The line under the toolbar, in the frame's own coordinates. In Split view the frame scrolls by itself.
const frameLine = () => split ? 8 : topInset() - frame.getBoundingClientRect().top;
function scrollToTarget(target) {
  if (!frameReady && !isPDF()) { pending = target; return; }
  const {anchor, offset = 0, page = false, flash = false, user = false} = target;
  // A jump also drops a pending save: a frame that swaps its chapter scrolls the window before the jump starts here.
  if (!user) { jumpedAt = Date.now(); clearTimeout(saveTimer); saveTimer = 0; } else lastInput = Date.now();
  if (page && !split) return window.scrollTo(0, 0);
  const element = anchor && frame.contentDocument?.getElementById(anchor), top = element ? element.getBoundingClientRect().top - offset : 0;
  if (split) frame.contentWindow?.scrollTo(0, element ? frame.contentWindow.scrollY + top - 40 : 0);
  else window.scrollTo(0, window.scrollY + frame.getBoundingClientRect().top + top - topInset() + (element ? 0 : 16));
  if (flash && element) { element.classList.add('lx-flash'); setTimeout(() => element.classList.remove('lx-flash'), 1600); }
}
// The first passage that reaches below the line, and how far its top sits from the line. A passage's `href` names its
// element: the converter's own ID, or `p` and digits where the element has none.
function topPassage() {
  const doc = frame.contentDocument;
  if (isPDF() || !doc?.body) return null;
  const line = frameLine();
  for (const {href} of detail.paper.passages || []) {
    const cut = href.indexOf('#'), anchor = href.slice(cut + 1);
    if (href.slice(0, cut) !== loaded) continue;
    const box = doc.getElementById(anchor)?.getBoundingClientRect();
    if (box && box.bottom > line) return {anchor, offset: box.top - line};
  }
  return null;
}
// The Blog saves its section and leaves the Paper's chapter and anchor as they are.
function savePosition() {
  if (!selected || lastInput < jumpedAt || $('reader-page').hidden) return;
  if (activeTab === 'blog') return saveReading(selected, {view: 'blog', section: currentEntry()}).catch(() => {});
  if (activeTab !== 'paper' || split || isPDF()) return;
  return saveReading(selected, {view: 'paper', chapter, anchor: topPassage()?.anchor || ''}).catch(() => {});
}
// The position saves two seconds after scrolling stops, or at once when the reader leaves the page or the page hides.
// Leaving hides the reader, and a hidden reader has no passage at the top, so the save must come first.
function flushPosition() {
  if (!saveTimer) return;
  clearTimeout(saveTimer); saveTimer = 0;
  return savePosition();
}
document.addEventListener('visibilitychange', () => { if (document.hidden) flushPosition(); });
// The Native shell quits with no pagehide or visibilitychange, so it sends this and waits for the save.
register('flush', flushPosition);
// Back returns to the same paragraph: the history entry the reader leaves keeps the passage and its offset.
nav.onLeave(entry => {
  flushPosition();
  if (entry.page !== 'reader' || entry.id !== selected || !detail) return;
  const top = activeTab === 'paper' && !split ? topPassage() : null;
  entry.position = {view: activeTab, chapter, ...(top ? {anchor: top.anchor, offset: top.offset} : {})};
});

const cssToken = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
export function styleReader() {
  if (isPDF()) return;
  const doc = frame.contentDocument;
  if (!doc?.body || !doc.head) return;
  let style = doc.getElementById('app-reading-style');
  if (!style) { style = doc.createElement('style'); style.id = 'app-reading-style'; doc.head.append(style); }
  style.textContent = readerStylesheet({theme: document.documentElement.dataset.theme, prefs,
    tokens: {paper: cssToken('--paper'), ink: cssToken('--ink'), label: cssToken('--label'), label2: cssToken('--label-2'), accent: cssToken('--accent'),
      accentTint: cssToken('--accent-tint-2'), question: cssToken('--question'), questionTint: cssToken('--question-tint'), figureMaxHeight: Math.round(innerHeight * .55)}});
  resizeReader();
}
function resizeReader() {
  if (isPDF() || split || $('paper').hidden) return;
  const body = frame.contentDocument?.body;
  if (body) frame.style.height = Math.ceil(body.getBoundingClientRect().height + 20) + 'px';
}
frame.onload = () => {
  observer?.disconnect();
  const doc = frame.contentDocument;
  if (!detail || isPDF() || !doc?.body) return;
  styleReader();
  wire(doc);
  observer = new ResizeObserver(resizeReader); observer.observe(doc.body);
  frameReady = true;
  headings = [...doc.querySelectorAll('h2[id], h3[id]')].map(element => {
    const number = element.querySelector('.header-section-number')?.textContent.trim() || '';
    return {element, id: element.id, number, label: headingText(element).slice(number.length).trim(), level: element.localName === 'h2' ? 2 : 3};
  });
  if (pending) { scrollToTarget(pending); pending = null; }
  syncReaderChrome();
  // The selection toolbar and the Question cards wire each chapter's document.
  dispatchEvent(new CustomEvent('lx-chapter', {detail: {path: loaded, doc, paper: selected}}));
};
addEventListener('resize', () => {
  if (split && innerWidth < SPLIT_WIDTH) { closeSplit(); syncReaderChrome(); }
  styleReader();
});

// The app's handlers on paper elements run because the frame's sandbox has allow-scripts; the paper CSP
// still blocks every paper script.
function wire(doc) {
  for (const type of ['pointerdown', 'wheel', 'keydown', 'touchstart']) doc.addEventListener(type, noteInput, {passive: true});
  doc.addEventListener('keydown', event => {
    if (event.key === 'Escape' && closePreview() || enterPreview(event)) { event.preventDefault(); return; }
    const image = event.target.closest?.('figure img');
    if (image && ['Enter', ' '].includes(event.key)) { event.preventDefault(); enlarge(image); return; }
    keydown(event);
  });
  doc.addEventListener('mouseover', event => hover(event.target.closest?.('a[href]'), showLinkPreview));
  doc.addEventListener('mouseout', event => leave(event, 'a[href]'));
  doc.addEventListener('focusin', event => hover(event.target.closest?.('a[href]'), showLinkPreview));
  doc.addEventListener('focusout', () => leave());
  doc.addEventListener('pointerdown', event => { if (!previewFor?.contains(event.target)) closePreview(); });
  doc.defaultView.addEventListener('scroll', dropPreview, {passive: true});
  doc.addEventListener('click', event => {
    const link = event.target.closest?.('a[href]'), image = event.target.closest?.('figure img');
    if (!link) { if (image) enlarge(image); return; }
    event.preventDefault();
    const target = linkTarget(link);
    if (target) follow(target);
    else if (/^https?:/i.test(link.href) && new URL(link.href).origin !== location.origin) openOutside(link.href);
  });
  for (const image of doc.querySelectorAll('figure img')) {
    image.tabIndex = 0; image.setAttribute('role', 'button'); image.setAttribute('aria-label', 'Enlarge Figure');
  }
}
const enlarge = image => openFigure(image.src, image.alt, image.closest('figure')?.querySelector('figcaption')?.textContent);
// The frame's sandbox blocks new windows, and a link in the app page reaches the Native shell's link policy.
function openOutside(url) {
  const link = node('a'); link.href = url; link.target = '_blank'; link.rel = 'noopener noreferrer';
  document.body.append(link); link.click(); link.remove();
}
// A link to a chapter of this Paper, as {chapter, id}; anything else is null.
function linkTarget(link) {
  let url;
  try { url = new URL(link.getAttribute('href'), link.ownerDocument.location.href); } catch { return null; }
  const prefix = `/files/${encodeURIComponent(selected)}/`, path = decodeURIComponent(url.pathname.slice(prefix.length));
  if (url.origin !== location.origin || !url.pathname.startsWith(prefix) || !url.hash || !knownChapter(path)) return null;
  return {chapter: path, id: decodeURIComponent(url.hash.slice(1))};
}
// A link in the Paper adds a history entry, so Back returns to the paragraph the reader left. A link whose target is
// missing would scroll to the chapter top, so it keeps the reader's place and says why.
async function follow({chapter: path, id}) {
  closePreview(); pinned = '';
  if (!(await chapterDocument(path))?.getElementById(id)) return notice('This link has no target in the Paper.', true);
  if (!split) nav.push({page: 'reader', id: selected, position: {view: 'paper', chapter: path, anchor: id}});
  if (path === loaded) scrollToTarget({anchor: id, flash: true}); else loadChapter(path, {anchor: id, flash: true});
}
function noteInput() { lastInput = Date.now(); }
for (const type of ['pointerdown', 'wheel', 'keydown', 'touchstart']) addEventListener(type, noteInput, {passive: true, capture: true});
addEventListener('scroll', () => {
  dropPreview();
  if (!detail || $('reader-page').hidden) return;
  if (!spyFrame) { spyFrame = requestAnimationFrame(spy); spyTimer = setTimeout(spy, 100); }
  // The scroll that a jump makes arms no save, so a later click on the toolbar cannot save the jump's chapter.
  if (lastInput < jumpedAt) return;
  clearTimeout(saveTimer); saveTimer = setTimeout(flushPosition, 2000);
}, {passive: true});

// ---- Previous and next chapter, and the one Mark as Read prompt ----
function drawChapnav() {
  const list = chapters(), index = list.findIndex(item => item.path === chapter), read = readingState(summary(selected) || {}) === 'read';
  const signature = JSON.stringify([selected, chapter, read, list.length]);
  if (signature === chapnavSignature) return;
  chapnavSignature = signature;
  const box = $('chapnav');
  box.replaceChildren();
  if (isPDF() || index < 0) return;
  const link = (item, label, className) => {
    const button = node('button', undefined, className);
    button.type = 'button'; button.append(node('span', label, 'k'), node('span', item.title || item.path, 'v'));
    button.onclick = () => goChapter(item.path, '');
    return button;
  };
  if (list[index - 1]) box.append(link(list[index - 1], 'Previous', 'prev'));
  if (list[index + 1]) box.append(link(list[index + 1], 'Next', 'next'));
  // ponytail: the chapter before References ends the body; a paper with no References chapter ends at its last chapter.
  const references = list.findIndex(item => /^(references|bibliography)$/i.test(chapterParts(item.title || '')[1].trim()));
  if (read || index !== (references > 0 ? references - 1 : list.length - 1)) return;
  const prompt = node('div', undefined, 'done'), mark = node('button', 'Mark as Read', 'btn-quiet');
  mark.type = 'button';
  mark.onclick = () => saveReading(selected, {state: 'read'}).catch(error => notice(error.message));
  prompt.append(node('span', 'You reached the end of the Paper.'), mark);
  box.append(prompt);
}

// ---- Reference previews, and Blog citation previews ----
let preview = null, previewFor = null, waitingFor = null, showTimer = 0, hideTimer = 0;
const documents = new Map();
function chapterDocument(path) {
  if (path === loaded && frame.contentDocument?.body) return Promise.resolve(frame.contentDocument);
  if (!documents.has(path)) {
    documents.set(path, fetch(fileURL(path), {credentials: 'same-origin'}).then(response => response.ok ? response.text() : null)
      .then(text => text && new DOMParser().parseFromString(text, 'application/xhtml+xml')).catch(() => null));
  }
  return documents.get(path);
}
function hover(element, show) {
  if (!element) return;
  clearTimeout(hideTimer);
  if (element === previewFor || element === waitingFor) return;
  clearTimeout(showTimer); waitingFor = element;
  showTimer = setTimeout(() => { waitingFor = null; show(element); }, 250);
}
function leave(event, selector) {
  const from = selector ? event.target.closest?.(selector) : null;
  if (selector && (!from || from.contains(event.relatedTarget))) return;
  clearTimeout(showTimer); waitingFor = null;
  clearTimeout(hideTimer); hideTimer = setTimeout(closePreview, 220);
}
// The keyboard path into a preview: Down Arrow on its link focuses the preview's body when it scrolls, or else its first
// action. Escape, or Tab past either end, returns focus to the link with the preview still open, and Escape there closes it.
function enterPreview(event) {
  if (event.key !== 'ArrowDown' || !preview || previewFor !== event.target) return false;
  const body = preview.querySelector('.pb');
  if (body.scrollHeight > body.clientHeight) body.tabIndex = 0;
  preview.querySelector('[tabindex="0"], button')?.focus({preventScroll: true});
  return true;
}
export function closePreview() {
  clearTimeout(showTimer); clearTimeout(hideTimer); waitingFor = null;
  return dropPreview();
}
// A scroll takes the open preview away from its link. It keeps a preview that is still to show, because moving focus
// to a link or a card out of view scrolls it into view first.
function dropPreview() {
  if (!preview) return false;
  preview.remove(); preview = null; previewFor?.classList.remove('is-open'); previewFor = null;
  return true;
}
// `anchor` is a link in the Paper frame or a citation in the page; the popover stays inside the viewport.
export function openPreview(anchor, label, content, actions, note = '', wide = false) {
  closePreview();
  preview = node('div', undefined, wide ? 'pop preview wide' : 'pop preview');
  preview.setAttribute('role', 'dialog'); preview.setAttribute('aria-label', label);
  const head = node('div', undefined, 'ph'), body = node('div', undefined, 'pb');
  head.append(node('span', label)); body.append(content);
  preview.append(head, body);
  if (actions.length || note) {
    const foot = node('div', undefined, 'pf');
    for (const [text, glyph, action, primary] of actions) {
      const button = node('button', undefined, primary ? 'pri' : '');
      button.type = 'button'; button.append(icon(glyph, 'i sm'), node('span', text)); button.onclick = action;
      foot.append(button);
    }
    if (note) foot.append(node('span', note, 'r'));
    preview.append(foot);
  }
  preview.onmouseenter = () => clearTimeout(hideTimer);
  preview.onmouseleave = () => { if (!preview.contains(document.activeElement)) hideTimer = setTimeout(closePreview, 220); };
  // The preview stays open while it has focus. Focus that leaves it for anything but its link closes it, and the link's
  // own focusin keeps it open.
  preview.addEventListener('focusin', () => clearTimeout(hideTimer));
  preview.addEventListener('focusout', event => { if (!preview?.contains(event.relatedTarget)) hideTimer = setTimeout(closePreview, 220); });
  preview.onkeydown = event => {
    const stops = [...preview.querySelectorAll('[tabindex="0"], button')], at = stops.indexOf(document.activeElement);
    if (event.key !== 'Escape' && !(event.key === 'Tab' && at === (event.shiftKey ? 0 : stops.length - 1))) return;
    event.preventDefault(); event.stopPropagation(); previewFor.focus({preventScroll: true});
  };
  document.body.append(preview);
  // The popover goes below the link, or above it when there is more room there. Its body shrinks to fit that
  // side, so the popover never covers the link or the toolbar.
  const ceiling = native ? 8 : 60;
  const place = () => {
    let box = anchor.getBoundingClientRect();
    if (anchor.ownerDocument !== document) {
      const outer = frame.getBoundingClientRect();
      box = {left: outer.left + box.left, right: outer.left + box.right, top: outer.top + box.top, bottom: outer.top + box.bottom};
    }
    const below = innerHeight - 8 - box.bottom - 10, above = box.top - 10 - ceiling;
    body.style.maxHeight = '';
    const extra = preview.offsetHeight - Math.max(below, above);
    if (extra > 0) body.style.maxHeight = Math.max(60, body.offsetHeight - extra) + 'px';
    const width = preview.offsetWidth, height = preview.offsetHeight, under = height <= below || below >= above;
    preview.style.left = Math.max(8, Math.min(innerWidth - width - 8, (box.left + box.right) / 2 - width / 2)) + 'px';
    preview.style.top = (under ? box.bottom + 10 : Math.max(ceiling, box.top - height - 10)) + 'px';
  };
  place();
  // An image changes the popover's height when it arrives.
  for (const image of preview.querySelectorAll('img')) image.onload = place;
  previewFor = anchor; anchor.classList.add('is-open');
}
async function showLinkPreview(link) {
  const target = linkTarget(link);
  if (!target?.id || isPDF()) return;
  const doc = await chapterDocument(target.chapter), element = doc?.getElementById(target.id);
  // A link that does not resolve shows no popover. Nor does a link during a text selection, because the popover would
  // cover the selection toolbar.
  if (!element || !link.isConnected || preview && previewFor === link || link.ownerDocument.getSelection()?.isCollapsed === false) return;
  const [kind, content] = previewContent(element, fileURL(target.chapter));
  if (!content) return;
  const text = link.textContent.trim(), label = kind + (/\d/.test(text) && text.length <= 8 ? ' ' + text.replace(/^\[|\]$/g, '') : '');
  openPreview(link, label, content, kind === 'Reference'
    ? [['Go to Reference', 'chev-r', () => follow(target), true], ['Search', 'search', () => searchReference(element)]] : [], '', ['Figure', 'Table', 'Equation'].includes(kind));
}
// What a preview shows for each kind of target: the entry, figure, table, equation, footnote, or section start.
function previewContent(element, base) {
  const name = element.localName, inside = selector => element.closest(selector), fragment = document.createDocumentFragment();
  if (element.id.startsWith('ref-') || inside('#refs, .references, .csl-bib-body')) return ['Reference', copy(element, base)];
  const table = name === 'table' ? element : ['div', 'figure'].includes(name) && element.querySelector('table');
  if (table) return ['Table', copy(element, base)];
  if (inside('figure')) return ['Figure', copy(inside('figure'), base)];
  const note = inside('[role=doc-footnote], .footnotes li');
  if (note) return ['Footnote', copy(note, base)];
  // An equation label can sit on a span around the math.
  const math = name === 'math' ? element : inside('math') || (name === 'span' ? element.querySelector('math') : null);
  if (math) return ['Equation', copy(math, base)];
  if (name === 'section' || /^h[1-6]$/.test(name)) {
    const heading = name === 'section' ? element.querySelector('h1, h2, h3, h4, h5, h6') : element;
    const scope = name === 'section' ? element : element.parentElement, paragraph = scope?.querySelector(':scope > p') || scope?.querySelector('p');
    if (heading) fragment.append(node('h3', headingText(heading)));
    if (paragraph) fragment.append(copy(paragraph, base));
    return ['Section', fragment];
  }
  return ['Passage', copy(element.closest('p') || element, base)];
}
// A heading's text without the TeX source that a formula keeps in its annotation, which copy() also leaves out.
function headingText(element) {
  const clone = element.cloneNode(true);
  for (const note of clone.querySelectorAll('annotation, annotation-xml')) note.remove();
  return clone.textContent.trim();
}
// Paper DOM reaches the app page only through this copy: known tags, no ids, links, styles, or handlers,
// and images only from this Paper's files.
const MATHML = 'http://www.w3.org/1998/Math/MathML';
const TAGS = new Set(['p', 'span', 'a', 'em', 'i', 'strong', 'b', 'u', 'sub', 'sup', 'br', 'code', 'small', 'cite', 'q', 'figure', 'figcaption', 'img',
  'table', 'caption', 'colgroup', 'col', 'thead', 'tbody', 'tfoot', 'tr', 'th', 'td', 'div', 'ul', 'ol', 'li', 'dl', 'dt', 'dd', 'blockquote', 'pre',
  'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'section', 'aside']);
function copy(source, base) {
  if (source.nodeType === Node.TEXT_NODE) return document.createTextNode(source.data);
  if (source.nodeType !== Node.ELEMENT_NODE || source.matches('[role=doc-backlink], annotation, annotation-xml')) return null;
  const math = source.namespaceURI === MATHML;
  if (!math && !TAGS.has(source.localName)) return null;
  const element = math ? document.createElementNS(MATHML, source.localName) : document.createElement(source.localName === 'a' ? 'span' : source.localName);
  for (const {name, value} of source.attributes) {
    if (math ? !/^(on|href|src|xlink|xmlns|style$|id$|class$)/i.test(name) : ['alt', 'colspan', 'rowspan'].includes(name)) element.setAttribute(name, value);
  }
  if (source.localName === 'img') {
    const src = mediaURL(source.getAttribute('src'), base);
    if (!src) return null;
    element.src = src;
  }
  for (const child of source.childNodes) { const next = copy(child, base); if (next) element.append(next); }
  return element;
}
function mediaURL(src, base) {
  try {
    const url = new URL(src, base), prefix = `/files/${encodeURIComponent(selected)}/`;
    return url.origin === location.origin && url.pathname.startsWith(prefix) ? fileURL(decodeURIComponent(url.pathname.slice(prefix.length))) : null;
  } catch { return null; }
}
// The title is the second sentence of most entries; an initial such as "N." does not end a sentence.
// Links leave the entry first, because the shared search turns text with a link into a Direct import.
function searchReference(element) {
  const entry = element.textContent.replace(/^\s*\[\d+\]\s*/, '').replace(/(?:\bURL:?\s+)?\S*(?:https?:\/\/|(?:ar|alpha)xiv\.org\/)\S*/gi, ' ').replace(/\s+/g, ' ').trim();
  const title = entry.split(/(?<=[^\s.]{2})\.\s+/)[1], query = (title?.split(' ').length >= 3 ? title : entry).slice(0, 300);
  closePreview();
  if (inputKind(query) === 'search') commands.run({name: 'search', query, submit: true});
}
function showPassage(citation) {
  const source = sources.get(citation.dataset.passage);
  if (!source || !citation.isConnected) return;
  openPreview(citation, source.section || 'Passage', node('p', source.text, 'clamp'), [['Open in Paper', 'doc', () => openPassage(source.href), true]], `Source ${citation.textContent}`);
}
$('blog-text').addEventListener('mouseover', event => hover(event.target.closest('.cn .citation'), showPassage));
$('blog-text').addEventListener('mouseout', event => leave(event, '.cn .citation'));
$('blog-text').addEventListener('focusin', event => hover(event.target.closest('.cn .citation'), showPassage));
$('blog-text').addEventListener('focusout', () => leave());
document.addEventListener('pointerdown', event => { if (preview && !preview.contains(event.target) && !previewFor?.contains(event.target)) closePreview(); });
document.addEventListener('keydown', event => {
  if (enterPreview(event)) return event.preventDefault();
  if (event.key !== 'Escape' || event.defaultPrevented || document.querySelector('dialog[open]')) return;
  if (closePreview()) event.preventDefault();
  else if (split) { closeSplit(); syncReaderChrome(); event.preventDefault(); }
});

// ---- Opening a passage: Split view on a wide window, the Paper view below that ----
function openPassage(href) {
  const [path, id = ''] = String(href || '').split('#');
  if (!isPDF() && innerWidth >= SPLIT_WIDTH && knownChapter(path)) { closePreview(); return openSplit(path, id); }
  goPassage(href);
}
// The Paper view at a passage, which flashes. Back returns to the place the reader left.
export function goPassage(href) {
  const [path, id = ''] = String(href || '').split('#'), pdf = isPDF();
  // A PDF's chapters are its pages, and the page is in the path.
  const target = pdf ? chapters().find(item => item.path === href)?.path : knownChapter(path) && path;
  if (!target) return;
  // All Notes can open a card's words from Split view, and the Paper view has no pane.
  closePreview(); closeSplit();
  nav.push({page: 'reader', id: selected, position: {view: 'paper', chapter: target, anchor: pdf ? '' : id}});
  viewScroll[activeTab] = window.scrollY;
  chapter = target; activeTab = 'paper'; showView();
  if (target === loaded) scrollToTarget({anchor: id, flash: true}); else loadChapter(target, {anchor: id, flash: true});
}
function openPassageByID(id) {
  const passage = [...(detail?.overview?.evidence || []), ...(detail?.paper?.passages || [])].find(item => item.id === id);
  if (passage) openPassage(passage.href);
}
function openSplit(path, id) {
  split = true;
  $('reader-page').classList.add('split'); $('paper').hidden = false; frame.style.height = '';
  if (path === loaded) { styleReader(); scrollToTarget({anchor: id, flash: true}); } else loadChapter(path, {anchor: id, flash: true});
  $('split-title').textContent = chapters().find(item => item.path === path)?.title || 'Paper';
  syncReaderChrome();
}
function closeSplit() {
  if (!split) return;
  split = false;
  $('reader-page').classList.remove('split'); $('paper').hidden = activeTab !== 'paper';
  resizeReader();
}
$('split-close').onclick = () => { closeSplit(); syncReaderChrome(); };
$('split-full').onclick = () => switchTab('paper');

// ---- The Blog and the Overview ----
function drawExplanations(result) {
  const signature = JSON.stringify([selected, result.blog?.cited_text, result.blog?.figures, result.blog?.explanation, result.overview?.text, result.overview?.figures?.map(figure => figure.svg_source)]);
  if (signature === explanations) return;
  explanations = signature;
  drawBlog(result.blog); drawOverview(result.overview);
  swapFigureSources(document.documentElement.dataset.theme);
}
// "Generated with <model>", and "<date> · <extra>" on the next line.
function provenance(generation, extra) {
  const record = generation.provenance || {}, made = Date.parse(record.created_at);
  const date = Number.isFinite(made) ? new Date(made).toLocaleDateString(undefined, {day: 'numeric', month: 'short', year: 'numeric'}) : '';
  return `Generated with ${record.model || generation.model || 'an unknown model'}\n${[date, extra].filter(Boolean).join(' · ')}`.trim();
}
function drawBlog(blog) {
  const explanation = blog?.explanation || {}, paper = detail.paper, text = blog?.cited_text || blog?.text || '';
  sources = new Map([...(paper.passages || []), ...(blog?.evidence || [])].map(source => [source.id, source]));
  $('blog-head').hidden = !blog; $('blog-limit').hidden = !explanation.limitation;
  $('blog-title').textContent = explanation.title || paper.title || paper.id;
  // The lead is the contribution's first sentence; the rest of it is in the article.
  $('blog-lead').textContent = String(explanation.contribution || '').match(/^.*?[.!?](?=\s|$)/s)?.[0] || explanation.contribution || '';
  $('blog-lead').hidden = !explanation.contribution;
  const words = text.replace(/\[p\d+[^\]]*\]/g, '').split(/\s+/).filter(Boolean).length;
  if (blog) $('blog-provenance').textContent = provenance(blog, `${Math.max(1, Math.round(words / 200))} min read`);
  prose($('blog-text'), text, [...sources.values()], blog?.figures || []);
  // The outline and the Reading position name a Blog section by this id.
  blogHeadings().forEach((heading, index) => { heading.id = `blog-section-${index}`; });
  $('blog-limit-text').textContent = explanation.limitation || '';
}
function drawOverview(overview) {
  const figure = overview?.figures?.[0];
  panels = (Array.isArray(figure?.panels) ? figure.panels : []).filter(panel => panel && typeof panel.id === 'string' && typeof panel.y === 'number');
  $('overview-head').hidden = !overview;
  if (overview) $('overview-provenance').textContent = provenance(overview, panels.length ? `${panels.length} panels` : '');
  prose($('overview-text'), overview?.text, [], overview?.figures || [], {inlineFigure});
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
    annotateFigure(svg.querySelectorAll('[data-node]'), figure.components, {svgNode: tag => document.createElementNS(SVG_NS, tag), onPassage: openPassageByID});
    const components = new Map((figure.components || []).map(item => [item.node, item]));
    container.onfocusin = event => hover(event.target.closest?.('.has-component'), card => showComponent(card, components.get(card.dataset.node)));
    container.onfocusout = () => leave();
    container.replaceChildren(svg); container.dataset.theme = theme; container.removeAttribute('aria-busy');
    container.style.aspectRatio = ''; container.classList.remove('is-failed');
  } catch {
    // The figure keeps its place, and Enlarge hides, because it would open the same missing file.
    container.replaceChildren(figureFailure(() => inlineFigure(container, figure)));
    container.removeAttribute('aria-busy'); container.classList.add('is-failed');
  }
}
// The Component hover for the keyboard. The pointer has the SVG title, and a click also focuses the card, so only
// keyboard focus opens this preview.
function showComponent(card, component) {
  if (!component || !card.matches(':focus-visible')) return;
  const body = document.createDocumentFragment();
  for (const line of [component.computes && `Computes ${component.computes}`, component.role, component.values && `Values: ${component.values}`]) if (line) body.append(node('p', line));
  openPreview(card, component.name, body, []);
}
export function swapFigureSources(theme) {
  for (const img of document.querySelectorAll('img[data-dark-src]')) {
    const next = theme === 'dark' ? img.dataset.darkSrc : img.dataset.lightSrc;
    if (img.getAttribute('src') !== next) img.src = next;
  }
  for (const container of document.querySelectorAll('.figure-inline[data-dark-src]')) {
    if (container.dataset.theme !== theme && inlineFigures.has(container)) inlineFigure(container, inlineFigures.get(container));
  }
}
// MathJax is bundled locally. Only formula text reaches its restricted TeX parser.
let mathQueue = Promise.resolve();
export function renderMath(element, tex, display) {
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
  openSource: openPassage});
