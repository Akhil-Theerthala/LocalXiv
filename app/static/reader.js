// The reader: the Paper view with its Reference previews, the outline, the Reading position, the Blog
// and Overview views, Split view, and the generation states.
// app.js imports this module and this module imports app.js. This module's top level only registers
// handlers, so neither module reads the other's bindings before both have run.
import {register, chrome, nav, keydown, commands, native} from './shell.js';
import {node, icon, renderProse, annotateFigure, authorNames, byline, arxivDate, shortTitle, baseID, readingState} from './render.js';
import {readerStylesheet} from './appearance.js';
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
let jumpedAt = 0, lastInput = 0, saveTimer = 0, spyFrame = 0, spyTimer = 0;
const topInset = () => native ? 16 : 68;
const isPDF = () => detail?.paper?.format === 'pdf';
const chapters = () => detail?.paper?.chapters || [];
const knownChapter = path => chapters().some(item => item.path === path);
const chapterParts = title => { const match = String(title).match(/^(\d+(?:\.\d+)*)\.?\s+(.+)$/); return match ? [match[1], match[2]] : ['', String(title)]; };

function viewState(kind) {
  if (kind === 'paper') return 'ready';
  return detail?.[kind] ? 'ready' : runningJob(kind) ? 'working' : aiReady() ? 'empty' : 'off';
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
  if (reading && activeTab !== 'paper') { window.scrollTo(0, scroll || 0); jumpedAt = Date.now(); resume = reading.anchor ? {anchor: reading.anchor, offset: reading.offset} : null; }
  // Opening a New Paper makes it Reading; every open moves it to the top of Recent.
  if (changed && !position) saveReading(id, {...(summary(id)?.reading ? {} : {state: 'reading'}), view: activeTab}).catch(() => {});
}
export function closeReader() { ++request; closePreview(); closeSplit(); selected = null; detail = null; }

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
  for (const view of Object.keys(VIEW_LABELS)) $(view).hidden = view !== activeTab && !(view === 'paper' && split);
  $('reader-page').dataset.view = activeTab;
  drawViewState();
  // A PDF viewer that loads in a hidden frame lays its pages out at zero width, so a PDF loads when it shows.
  if (activeTab === 'paper' && isPDF() && chapter && chapter !== loaded) loadChapter(chapter);
  if (activeTab === 'paper') styleReader();
  syncReaderChrome();
}
function switchTab(name) {
  if (!detail || !VIEW_LABELS[name] || name === activeTab && !split) return;
  // From the Split view pane, the Paper view opens at the passage the pane shows.
  const fromPane = split && name === 'paper' ? topPassage() : null;
  viewScroll[activeTab] = window.scrollY;
  closeSplit(); activeTab = name; showView();
  if (fromPane) scrollToTarget({anchor: fromPane.anchor, user: true});
  else if (name === 'paper' && viewScroll.paper === undefined && resume) scrollToTarget(resume);
  else window.scrollTo(0, viewScroll[name] || 0);
  saveReading(selected, {view: name, ...(chapter ? {chapter} : {})}).catch(() => {});
}
register('view', ({view}) => switchTab(view));

function drawViewState() {
  const kind = activeTab;
  if (kind === 'paper') return;
  const box = $(`${kind}-state`), label = VIEW_LABELS[kind], status = viewState(kind), paper = detail.paper, job = runningJob(kind);
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
  const blocked = kind === 'overview' ? !paper.passages?.length : isPDF() && !paper.passages?.length;
  box.append(node('h2', `No ${label} yet`), node('p', kind === 'overview'
    ? 'An Overview is one figure that tells why the work was needed, how it works, and what it achieved.'
    : 'A Blog is an article that builds the context and links each claim to its passage in the Paper.'));
  if (status === 'off') {
    box.append(node('p', 'Connect an AI provider in Settings to make one.'));
    button.textContent = 'Connect AI…'; button.className = 'btn-quiet'; button.onclick = () => openSettings('ai');
  } else if (blocked) {
    button.textContent = `Generate ${label}`; button.disabled = true;
    box.append(node('p', paper.report?.text_warning || 'This paper has no text to explain.'));
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
  const paper = detail.paper, previous = nav.previous?.page, item = chapters().find(entry => entry.path === chapter);
  current = currentEntry();
  chrome.update({
    mode: 'reader', title: shortTitle(paper.title || paper.id), subtitle: activeTab === 'paper' ? item?.title || '' : VIEW_LABELS[activeTab],
    views: {current: activeTab, overview: viewState('overview'), blog: viewState('blog'), paper: 'ready'},
    sidebar: {selected: null, reader: {back: previous === 'search' ? 'Results' : previous === 'home' ? 'Home' : 'Library', title: paper.title || paper.id,
      byline: [byline(paper.authors), arxivDate(paper.arxiv_id || paper.id)?.label].filter(Boolean).join(' · '), outline: outline()}},
    actions: readerActions(),
  });
  drawViewState(); drawChapnav();
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
    return list.map((heading, index) => {
      heading.id = `blog-section-${index}`;
      return row(heading.id, heading.textContent, '', Number(heading.localName[1]) - top + 1);
    });
  }
  return panels.map(panel => {
    // A heading reads "Why: …", or "1 · …" in older Overviews; the lead goes in the number column.
    const [, lead, rest] = String(panel.title || panel.id).match(/^(\w+)(?::|\s·)\s*(.+)$/) || [, '', panel.title || panel.id];
    return row(`panel:${panel.id}`, rest[0].toUpperCase() + rest.slice(1), lead, 1);
  });
}
// The entry the reader is in: the last heading above the line under the toolbar.
function currentEntry() {
  if (!detail) return '';
  if (activeTab === 'paper') {
    const line = frameLine();
    return headings.reduce((id, heading) => heading.element.getBoundingClientRect().top <= line + 8 ? `${chapter}#${heading.id}` : id, chapter);
  }
  const tops = activeTab === 'blog' ? blogHeadings().map(heading => [heading.id, heading.getBoundingClientRect().top])
    : panels.map(panel => [`panel:${panel.id}`, panelTop(panel)]).filter(([, top]) => top !== null);
  return tops.reduce((id, [entry, top]) => top <= topInset() + 8 ? entry : id, tops[0]?.[0] || '');
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
    if (knownChapter(path)) goChapter(path, cut < 0 ? '' : id.slice(cut + 1));
    return;
  }
  const top = id.startsWith('panel:') ? panelTop(panels.find(panel => `panel:${panel.id}` === id)) : document.getElementById(id)?.getBoundingClientRect().top;
  if (typeof top === 'number') window.scrollTo(0, window.scrollY + top - topInset());
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
  if (!user) jumpedAt = Date.now(); else lastInput = Date.now();
  if (page && !split) return window.scrollTo(0, 0);
  const element = anchor && frame.contentDocument?.getElementById(anchor), top = element ? element.getBoundingClientRect().top - offset : 0;
  if (split) frame.contentWindow?.scrollTo(0, element ? frame.contentWindow.scrollY + top - 40 : 0);
  else window.scrollTo(0, window.scrollY + frame.getBoundingClientRect().top + top - topInset() + (element ? 0 : 16));
  if (flash && element) { element.classList.add('lx-flash'); setTimeout(() => element.classList.remove('lx-flash'), 1600); }
}
// The first passage that reaches below the line, and how far its top sits from the line.
function topPassage() {
  const doc = frame.contentDocument;
  if (isPDF() || !doc?.body) return null;
  const line = frameLine();
  for (const element of doc.querySelectorAll('[id^="p"]')) {
    if (!/^p\d+$/.test(element.id)) continue;
    const box = element.getBoundingClientRect();
    if (box.bottom > line) return {anchor: element.id, offset: box.top - line};
  }
  return null;
}
function savePosition() {
  if (!selected || activeTab !== 'paper' || split || isPDF() || lastInput < jumpedAt || $('reader-page').hidden) return;
  saveReading(selected, {view: 'paper', chapter, anchor: topPassage()?.anchor || ''}).catch(() => {});
}
// Back returns to the same paragraph: the history entry the reader leaves keeps the passage and its offset.
nav.onLeave(entry => {
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
      accentTint: cssToken('--accent-tint-2'), figureMaxHeight: Math.round(innerHeight * .55)}});
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
    return {element, id: element.id, number, label: element.textContent.trim().slice(number.length).trim(), level: element.localName === 'h2' ? 2 : 3};
  });
  if (pending) { scrollToTarget(pending); pending = null; }
  syncReaderChrome();
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
    if (event.key === 'Escape' && closePreview()) { event.preventDefault(); return; }
    const image = event.target.closest?.('figure img');
    if (image && ['Enter', ' '].includes(event.key)) { event.preventDefault(); enlarge(image); return; }
    keydown(event);
  });
  doc.addEventListener('mouseover', event => hover(event.target.closest?.('a[href]'), showLinkPreview));
  doc.addEventListener('mouseout', event => leave(event, 'a[href]'));
  doc.addEventListener('focusin', event => hover(event.target.closest?.('a[href]'), showLinkPreview));
  doc.addEventListener('focusout', () => leave());
  doc.addEventListener('pointerdown', event => { if (!previewFor?.contains(event.target)) closePreview(); });
  doc.defaultView.addEventListener('scroll', () => closePreview(), {passive: true});
  doc.addEventListener('click', event => {
    const link = event.target.closest?.('a[href]'), image = event.target.closest?.('figure img');
    if (!link) { if (image) enlarge(image); return; }
    event.preventDefault();
    const target = linkTarget(link);
    if (target) follow(target);
    else if (/^https?:/i.test(link.href) && new URL(link.href).origin !== location.origin) openOutside(link.href);
  });
  for (const image of doc.querySelectorAll('figure img')) {
    image.tabIndex = 0; image.setAttribute('role', 'button'); image.setAttribute('aria-label', 'Enlarge figure');
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
// A link in the Paper adds a history entry, so Back returns to the paragraph the reader left.
function follow({chapter: path, id}) {
  closePreview();
  if (!split) nav.push({page: 'reader', id: selected, position: {view: 'paper', chapter: path, anchor: id}});
  if (path === loaded) scrollToTarget({anchor: id, flash: true}); else loadChapter(path, {anchor: id, flash: true});
}
function noteInput() { lastInput = Date.now(); }
for (const type of ['pointerdown', 'wheel', 'keydown', 'touchstart']) addEventListener(type, noteInput, {passive: true, capture: true});
addEventListener('scroll', () => {
  closePreview();
  if (!detail || $('reader-page').hidden) return;
  if (!spyFrame) { spyFrame = requestAnimationFrame(spy); spyTimer = setTimeout(spy, 100); }
  clearTimeout(saveTimer); saveTimer = setTimeout(savePosition, 2000);
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
export function closePreview() {
  clearTimeout(showTimer); clearTimeout(hideTimer); waitingFor = null;
  if (!preview) return false;
  preview.remove(); preview = null; previewFor?.classList.remove('is-open'); previewFor = null;
  return true;
}
// `anchor` is a link in the Paper frame or a citation in the page; the popover stays inside the viewport.
function openPreview(anchor, label, content, actions, note = '', wide = false) {
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
  preview.onmouseleave = () => { hideTimer = setTimeout(closePreview, 220); };
  document.body.append(preview);
  const place = () => {
    let box = anchor.getBoundingClientRect();
    if (anchor.ownerDocument !== document) {
      const outer = frame.getBoundingClientRect();
      box = {left: outer.left + box.left, right: outer.left + box.right, top: outer.top + box.top, bottom: outer.top + box.bottom};
    }
    const width = preview.offsetWidth, height = preview.offsetHeight, below = box.bottom + 10 + height <= innerHeight - 8;
    preview.style.left = Math.max(8, Math.min(innerWidth - width - 8, (box.left + box.right) / 2 - width / 2)) + 'px';
    preview.style.top = Math.max(8, below ? box.bottom + 10 : box.top - height - 10) + 'px';
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
  // A link that does not resolve shows no popover.
  if (!element || !link.isConnected || preview && previewFor === link) return;
  const [kind, content] = previewContent(element, fileURL(target.chapter));
  if (!content) return;
  const text = link.textContent.trim(), label = kind + (/\d/.test(text) && text.length <= 8 ? ' ' + text.replace(/^\[|\]$/g, '') : '');
  openPreview(link, label, content, kind === 'Reference'
    ? [['Go to reference', 'chev-r', () => follow(target), true], ['Search', 'search', () => searchReference(element)]] : [], '', ['Figure', 'Table', 'Equation'].includes(kind));
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
    if (heading) fragment.append(node('h3', heading.textContent.trim()));
    if (paragraph) fragment.append(copy(paragraph, base));
    return ['Section', fragment];
  }
  return ['Passage', copy(element.closest('p') || element, base)];
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
function searchReference(element) {
  const entry = element.textContent.replace(/^\s*\[\d+\]\s*/, '').replace(/\s+/g, ' ').trim(), title = entry.split(/(?<=[^\s.]{2})\.\s+/)[1];
  closePreview();
  commands.run({name: 'search', query: (title?.split(' ').length >= 3 ? title : entry).slice(0, 300), submit: true});
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
  if (event.key !== 'Escape' || event.defaultPrevented || document.querySelector('dialog[open]')) return;
  if (closePreview()) event.preventDefault();
  else if (split) { closeSplit(); syncReaderChrome(); event.preventDefault(); }
});

// ---- Opening a passage: Split view on a wide window, the Paper view below that ----
function openPassage(href) {
  const [path, id = ''] = String(href || '').split('#'), pdf = isPDF();
  // A PDF's chapters are its pages, and the page is in the path.
  const target = pdf ? chapters().find(item => item.path === href)?.path : knownChapter(path) && path;
  if (!target) return;
  closePreview();
  if (!pdf && innerWidth >= SPLIT_WIDTH) return openSplit(target, id);
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
// "Generated with <model> · <date> · <extra>"
function provenance(generation, extra) {
  const record = generation.provenance || {}, made = Date.parse(record.created_at);
  return ['Generated with ' + (record.model || generation.model || 'an unknown model'),
    Number.isFinite(made) ? new Date(made).toLocaleDateString(undefined, {day: 'numeric', month: 'short', year: 'numeric'}) : '', extra].filter(Boolean).join(' · ');
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
    container.replaceChildren(svg); container.dataset.theme = theme; container.removeAttribute('aria-busy');
  } catch {
    container.replaceChildren(node('p', 'Figure unavailable. Regenerate this view to restore it.', 'help'));
    container.removeAttribute('aria-busy');
  }
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
  openSource: openPassage});
