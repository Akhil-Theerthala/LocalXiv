// The reader: the Paper view with its Reference previews, the outline, the Reading position, the Blog
// and Overview views, Split view, and the generation states.
// app.js imports this module and this module imports app.js. This module's top level only registers
// handlers, so neither module reads the other's bindings before both have run.
import {register, setBackHook, chrome, nav, keydown, commands, native} from './shell.js';
import {node, icon, renderProse, glueFormula, annotateFigure, figureFailure, TERMINAL, authorNames, byline, arxivDate, shortTitle, baseID, readingState, inputKind, rowState,
  referenceArxivID} from './render.js';
import {readerStylesheet} from './appearance.js';
import {mountMargin, unmountMargin, syncCards, drawBlogChat, COLOURS} from './margin.js';
import {flushNotes} from './notes.js';
import {sketch} from './sketch.js';
import {openEarlier} from './chat.js';
import {api, paperAPI, fileURL, saveReading, notice, run, showPage, syncChrome, openSettings, openFigure, readerActions,
  aiReady, runningJob, summary, state, prefs} from './app.js';

const $ = id => document.getElementById(id);
const frame = $('paper-frame');
const VIEW_LABELS = {overview: 'Overview', blog: 'Blog', paper: 'Paper'};
const SPLIT_WIDTH = 1200;
export let selected = null, detail = null, activeTab = 'overview';
// `loaded` is the chapter in the frame; `chapter` is the one the reader is on. They differ only while a chapter loads.
let request = 0, chapter = '', loaded = '', frameReady = false, pending = null, resume = null, headings = [], sources = new Map();
let split = false, splitFrom = null, current = '', explanations = '', chapnavSignature = '', stateSignature = '', observer = null, viewScroll = {};
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
  if (changed) closePreview();
  if (nav.current?.page !== 'reader' || nav.current.id !== id) nav.push({page: 'reader', id});
  showPage('reader');
  if (changed || detail?.paper?.document_digest !== result.paper.document_digest) { loaded = ''; held = null; documents.clear(); }
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
    const view = activeTab, restore = () => {
      const section = !position && view === 'blog' && reading.section ? entryTop(reading.section) : null;
      window.scrollTo(0, section === null ? scroll || 0 : window.scrollY + section - topInset());
      jumpedAt = Date.now();
    };
    restore(); resume = reading.anchor ? {anchor: reading.anchor, offset: reading.offset} : null;
    // The formulas render later and change the height above the section, so the restore runs again after them, unless
    // the reader moved, or another view or Paper opened. A view switch from the Native toolbar is not page input.
    const at = jumpedAt;
    mathQueue.then(() => { if (mine === request && activeTab === view && !split && jumpedAt === at && lastInput < at) restore(); });
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
  const code = $('reader-code');
  code.removeAttribute('href'); code.hidden = true; delete code.dataset.kind;
  api(`${paperAPI(paper.id)}/code`).then(({code: found}) => {
    if (selected !== paper.id || !found) return;
    code.href = found.url; code.dataset.kind = found.kind; code.hidden = false;
    code.firstChild.textContent = found.kind === 'project' ? 'Project page ' : 'Code ';
    code.title = found.stars === undefined ? '' : `${found.stars} stars on GitHub, from Papers with Code`;
    syncReaderChrome();
  }).catch(() => {});
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
  // A figure drawn in a hidden view could not measure its group labels.
  for (const container of $(activeTab).querySelectorAll('.figure-diagram')) nudgeClusterLabels(container);
  // Question cards need the Paper's text, so a PDF has none.
  if (activeTab === 'paper' && !split && !isPDF()) mountMargin(); else unmountMargin();
  drawBlogChat();
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
// Edit › Find › Use Selection for Find in the Native shell: the selected text of the Paper frame when it has the focus,
// as in the Split view, else of the page.
register('selection', () => String((document.activeElement === frame ? frame.contentDocument : document)?.getSelection() ?? '').trim());

// ---- Find in the open view, for the Native shell's find bar ----
// WKWebView's find does not step from the Paper's header into the Paper frame, gives no count, and keeps its mark after
// Done, so the page finds. It paints all matches and the current one with CSS Custom Highlights in each document.
// shortcut: a match must sit in one text node, so words that markup splits, such as a link, are not found; upgrade when a reader misses one.
let finding = {text: '', view: '', index: -1};
const windowTop = range => range.getBoundingClientRect().top + (range.startContainer.ownerDocument === document ? 0 : frame.getBoundingClientRect().top);
function paintFind(ranges = [], current = null) {
  for (const doc of [document, frame.contentDocument]) {
    const win = doc?.defaultView;
    if (!win?.CSS?.highlights || !win.Highlight) continue;
    const mine = ranges.filter(range => range.startContainer.ownerDocument === doc), all = new win.Highlight(...mine), one = new win.Highlight();
    if (current?.startContainer.ownerDocument === doc) one.add(current);
    all.priority = 1; one.priority = 2;
    win.CSS.highlights.set('lx-find', all); win.CSS.highlights.set('lx-find-current', one);
  }
}
register('find-clear', () => { finding = {text: '', view: '', index: -1}; paintFind(); });
// A first text starts at the first match below the top of the view. A changed text starts at the current match, so the
// page does not move back at each keystroke. The same text steps to the next or the previous match, and wraps.
register('find', ({text = '', backwards = false}) => {
  const needle = String(text).toLowerCase(), view = `${selected} ${activeTab} ${loaded}`, ranges = [];
  const roots = !detail ? [] : [$('reader-header'), activeTab !== 'paper' ? $(activeTab) : isPDF() ? null : frame.contentDocument?.body];
  for (const root of roots.filter(Boolean)) {
    const walker = root.ownerDocument.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    for (let node; needle && (node = walker.nextNode());) {
      const hay = node.data.toLowerCase();
      for (let at = hay.indexOf(needle); at >= 0; at = hay.indexOf(needle, at + needle.length)) {
        // A figure label has a halo copy with no fill. Count the label once.
        if (!node.parentElement?.checkVisibility() || node.parentElement.closest('text[fill="none"]')) break;
        const range = root.ownerDocument.createRange();
        range.setStart(node, at); range.setEnd(node, at + needle.length);
        ranges.push(range);
      }
    }
  }
  const count = ranges.length;
  if (!count) { finding = {text: '', view: '', index: -1}; paintFind(); return {index: -1, count: 0}; }
  let index;
  if (needle === finding.text && view === finding.view) index = (finding.index + (backwards ? -1 : 1) + count) % count;
  else {
    const from = view === finding.view && finding.range ? windowTop(finding.range) : topInset();
    const first = ranges.findIndex(range => windowTop(range) >= from);
    index = first < 0 ? (backwards ? count - 1 : 0) : backwards ? (first - 1 + count) % count : first;
  }
  finding = {text: needle, view, index, range: ranges[index]};
  paintFind(ranges, ranges[index]);
  // The match goes to the centre of the view. In Split view the frame scrolls by itself.
  const range = ranges[index], doc = range.startContainer.ownerDocument;
  if (doc !== document && split) doc.defaultView.scrollBy(0, range.getBoundingClientRect().top - doc.defaultView.innerHeight / 2);
  else window.scrollBy(0, windowTop(range) - innerHeight / 2);
  return {index, count};
});

function drawViewState() {
  const kind = activeTab;
  if (kind === 'paper') return;
  const box = $(`${kind}-state`), label = VIEW_LABELS[kind], status = viewState(kind), job = runningJob(kind);
  const last = state.jobs.find(item => item.kind === kind && item.payload?.paper_id === selected);
  // The poll calls this often; a rebuild would drop focus from the box's button, so progress, and a queued job that
  // starts, change only the line and the bar.
  const signature = JSON.stringify([selected, kind, status, job ? job.id : [last?.id, last?.state]]);
  if (signature === stateSignature) return job && showProgress(box, job);
  stateSignature = signature;
  // A rebuild removes the focused button, so the focus goes to the new one (Cancel, Retry, or Generate), or to the main
  // area when the box has none, once the box is filled.
  if (box.contains(document.activeElement)) queueMicrotask(() => (box.querySelector('button') || $('main')).focus({preventScroll: true}));
  // The job hides its toast here, and the box hides, so the region that is always there says a start or a failure once.
  const heading = `${status === 'ready' ? 'Making a new' : 'Making the'} ${label}…`, error = last?.error || 'The job stopped before it finished.';
  const failed = !job && status === 'empty' && ['failed', 'interrupted'].includes(last?.state);
  const said = job ? heading : failed ? `The ${label} could not be made. ${error}` : '';
  if ($('view-status').textContent !== said) $('view-status').textContent = said;
  box.replaceChildren(); box.hidden = status === 'ready' && !job;
  if (box.hidden) return;
  if (job) {
    const bar = node('progress'), cancel = node('button', 'Cancel', 'btn-quiet');
    bar.setAttribute('aria-label', `${label} progress`);
    cancel.type = 'button'; cancel.onclick = () => run(`/api/jobs/${encodeURIComponent(job.id)}/cancel`, {});
    box.append(node('h2', heading), node('p'), bar, cancel);
    showProgress(box, job);
    return;
  }
  const button = node('button', undefined, 'btn-accent');
  button.type = 'button';
  if (failed) {
    box.append(node('h2', `The ${label} could not be made`), node('p', error));
    // The raw text, such as an HTTP status or the provider's own words, stays out of the main line.
    if (last.error_detail) { const details = node('details'); details.append(node('summary', 'Details'), node('p', last.error_detail)); box.append(details); }
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
function showProgress(box, job) {
  box.querySelector('p').textContent = `${typeof job.progress === 'string' ? job.progress + '. ' : ''}You can read the Paper meanwhile.`;
  const bar = box.querySelector('progress');
  if (typeof job.progress === 'number') { bar.max = 100; bar.value = job.progress; } else bar.removeAttribute('value');
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
  // The subtitle names the section that the reader is in. In a one-chapter Paper the chapter title is the Paper title,
  // so above the first heading the subtitle is that heading. Every view keeps a subtitle, so the title keeps its height.
  const here = activeTab === 'paper' ? headings.find(heading => `${chapter}#${heading.id}` === current) || (chapters().length > 1 ? null : headings[0]) : null;
  const blogHere = activeTab === 'blog' ? blogHeadings().find(heading => heading.id === current) || blogHeadings()[0] : null;
  chrome.update({
    mode: 'reader', title: shortTitle(paper.title || paper.id),
    subtitle: activeTab === 'paper' ? (isPDF() ? 'PDF' : here ? [here.number, here.label].filter(Boolean).join(' ') : item?.title || '')
      : activeTab === 'blog' ? blogHere?.textContent.trim() || 'Blog' : VIEW_LABELS[activeTab],
    views: {current: activeTab, overview: viewState('overview'), blog: viewState('blog'), paper: 'ready'},
    sidebar: {selected: null, reader: {back: origin === 'search' ? 'Results' : origin === 'home' ? 'Home' : 'Library', title: paper.title || paper.id,
      byline: [byline(paper.authors), arxivDate(paper.arxiv_id || paper.id)?.label].filter(Boolean).join(' · '), outline: outline(),
      link: paper.arxiv_id ? `https://arxiv.org/abs/${baseID(paper.arxiv_id)}` : ''}},
    actions: readerActions(),
  });
  for (const kind of ['overview', 'blog']) { const tip = viewTip(kind); $(`tb-view-${kind}`).title = tip; $(`tb-view-${kind}`).setAttribute('aria-description', tip); }
  drawViewState(); drawChapnav(); syncCards();
}
const blogHeadings = () => [...$('blog-text').querySelectorAll(':scope > h2, :scope > h3')];
// The Overview's numbered steps, the figure groups labelled "1 · Encoder". drawDiagram gives each group its id.
// Pele does not keep the groups in step order, so the step numbers set the order.
const overviewSteps = () => [...$('overview-text').querySelectorAll('.figure-main .pele-cluster[id]')].flatMap(group => {
  // Pele moves a label that an arrow would cross into the titles layer, after a halo copy of it.
  const text = group.querySelector(':scope > .pele-cluster-label')
    || group.ownerSVGElement?.querySelector(`.pele-cluster-title[data-id="${CSS.escape(group.dataset.id || '')}"] > .pele-cluster-label`);
  const parts = [...text?.childNodes || []];
  // Each line of a label that wraps starts with a tspan that has an x, so a space joins the lines.
  const words = parts.map(part => (part.getAttribute?.('x') ? ' ' : '') + part.textContent).join('');
  const [, number, label] = words.match(/^\s*(\d+)\s*·\s*(.+)$/s) || [];
  return number ? [{id: group.id, number, label: label.replace(/\s+/g, ' ').trim(), top: () => group.getBoundingClientRect().top}] : [];
}).sort((a, b) => a.number - b.number);
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
  // The Overview's outline is its numbered steps. A figure with no numbered steps has no outline.
  return overviewSteps().map(step => row(step.id, step.label, step.number, 1));
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
    : overviewSteps().map(step => [step.id, step.top()]);
  if (atEnd && tops.length) return tops.at(-1)[0];
  return tops.reduce((id, [entry, top]) => top <= topInset() + 8 ? entry : id, tops[0]?.[0] || '');
}
// The window position of an outline entry's target, or null while its chapter loads or when it has none.
function entryTop(id) {
  if (activeTab !== 'paper') {
    return document.getElementById(id)?.getBoundingClientRect().top ?? null;
  }
  const cut = id.indexOf('#'), path = cut < 0 ? id : id.slice(0, cut);
  if (path !== loaded || !frameReady) return null;
  const frameTop = frame.getBoundingClientRect().top, element = cut < 0 ? null : frame.contentDocument?.getElementById(id.slice(cut + 1));
  return cut < 0 ? frameTop : element ? frameTop + element.getBoundingClientRect().top : null;
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
let stylePoll = 0;
function loadChapter(path, target = null) {
  const url = fileURL(path);
  if (!url) return;
  chapter = loaded = path; pending = target; frameReady = false; headings = []; held = null;
  if (isPDF()) frame.removeAttribute('sandbox'); else frame.setAttribute('sandbox', 'allow-same-origin allow-scripts');
  frame.style.height = isPDF() ? 'calc(100vh - 140px)' : '';
  const old = frame.contentDocument;
  frame.src = url;
  // The load event waits for every image, so the reading style goes in as soon as the chapter is parsed, and the chapter
  // never paints with the Paper's own styles. A hidden web view runs no animation frames, so a timer checks.
  clearTimeout(stylePoll);
  const poll = () => {
    const doc = frame.contentDocument;
    if (doc && doc !== old && doc.readyState !== 'loading' && doc.body) dress(doc); else stylePoll = setTimeout(poll, 16);
  };
  if (!isPDF()) poll();
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
// The Split view bar names the section that the pane shows, found as currentEntry() finds it for the Paper view. Above
// the first heading it shows the chapter title, or in a one-chapter Paper, which has the Paper title, the first heading.
function splitTitle() {
  const line = frameLine(), heading = headings.reduce((found, item) => item.element.getBoundingClientRect().top <= line + 8 ? item : found, null)
    || (chapters().length > 1 ? null : headings[0]);
  $('split-title').textContent = heading ? [heading.number, heading.label].filter(Boolean).join(' ') : chapters().find(item => item.path === loaded)?.title || 'Paper';
}
function scrollToTarget(target) {
  if (!frameReady && !isPDF()) { pending = target; return; }
  const {anchor, offset = 0, page = false, flash = false, user = false} = target;
  // A jump also drops a pending save: a frame that swaps its chapter scrolls the window before the jump starts here.
  if (!user) { jumpedAt = Date.now(); clearTimeout(saveTimer); saveTimer = 0; } else lastInput = Date.now();
  if (page && !split) return window.scrollTo(0, 0);
  const element = anchor && frame.contentDocument?.getElementById(anchor), top = element ? element.getBoundingClientRect().top - offset : 0;
  if (split) { frame.contentWindow?.scrollTo(0, element ? frame.contentWindow.scrollY + top - 40 : 0); splitTitle(); }
  else window.scrollTo(0, window.scrollY + frame.getBoundingClientRect().top + top - topInset() + (element ? 0 : 16));
  // The tint holds, then fades. A second jump to the same passage starts it again.
  if (flash && element) {
    clearTimeout(element.lxFlash); element.classList.remove('lx-flash'); void element.offsetWidth; element.classList.add('lx-flash');
    element.lxFlash = setTimeout(() => element.classList.remove('lx-flash'), 1200);
  }
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
// A text size, Margins, spacing, or window change, or a late image, reflows the Paper, and the passage at the top stays
// at the top. A resize event comes after the reflow, so the passage is found before it: once a scroll stops. A scroll
// that the restore did not make drops it. At the top of the page nothing is held, so the Paper's header stays in view.
let held = null, heldY = NaN, heldTimer = 0;
function hold() {
  const shows = detail && activeTab === 'paper' && !split && frameReady && !$('reader-page').hidden;
  held = shows && frame.getBoundingClientRect().top < topInset() ? topPassage() : null; heldY = window.scrollY;
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
// An open Note editor saves too: a closed page or a quit sends no blur.
const flushAll = () => Promise.all([flushPosition(), flushNotes()]);
document.addEventListener('visibilitychange', () => { if (document.hidden) flushAll(); });
// The Native shell quits with no pagehide or visibilitychange, so it sends this and waits for the saves.
register('flush', flushAll);
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
  style.textContent = readerStylesheet({theme: document.documentElement.dataset.theme, prefs, split,
    tokens: {paper: cssToken('--paper'), ink: cssToken('--ink'), label: cssToken('--label'), label2: cssToken('--label-2'), accent: cssToken('--accent'),
      accentTint: cssToken('--accent-tint-2'), figureCard: cssToken('--figure-card'), figureMaxHeight: Math.round(innerHeight * .55),
      find: {fill: cssToken('--find'), ink: cssToken('--on-find'), line: cssToken('--find-line')},
      marks: Object.fromEntries(Object.keys(COLOURS).map(name => [name, {colour: cssToken(`--${name}`), tint: cssToken(`--${name}-tint`)}]))}});
  resizeReader();
}
function resizeReader() {
  if (isPDF() || split || $('paper').hidden) return;
  const body = frame.contentDocument?.body;
  if (body) frame.style.height = Math.ceil(body.getBoundingClientRect().height + 20) + 'px';
  // The restore leaves the save timer and the last jump as they are, so the next Reading position save still runs.
  const element = held && activeTab === 'paper' && !$('reader-page').hidden && frame.contentDocument?.getElementById(held.anchor);
  if (!element) return;
  window.scrollTo(0, window.scrollY + frame.getBoundingClientRect().top + element.getBoundingClientRect().top - held.offset - topInset());
  heldY = window.scrollY;
}
// The reading style goes in, and from then on the frame follows the chapter's height as its images arrive.
function dress(doc) {
  // A number and its ± in a table cell stay on one line: the ± and the word before and after it.
  for (const math of doc.querySelectorAll('td math, th math')) {
    if (math.getAttribute('alttext') !== '\\pm' || math.parentElement.classList.contains('lx-nobr')) continue;
    const box = doc.createElementNS('http://www.w3.org/1999/xhtml', 'span'), prev = math.previousSibling, next = math.nextSibling;
    const before = prev?.nodeType === 3 ? prev.data.match(/\S+\s*$/) : null, after = next?.nodeType === 3 ? next.data.match(/^\s*\S+/) : null;
    box.className = 'lx-nobr'; math.before(box);
    if (before) { prev.data = prev.data.slice(0, before.index); box.append(before[0]); }
    box.append(math);
    if (after) { next.data = next.data.slice(after[0].length); box.append(after[0]); }
  }
  observer?.disconnect(); styleReader();
  observer = new ResizeObserver(resizeReader); observer.observe(doc.body);
}
frame.onload = () => {
  clearTimeout(stylePoll); observer?.disconnect();
  const doc = frame.contentDocument;
  if (!detail || isPDF() || !doc?.body) return;
  dress(doc);
  wire(doc);
  frameReady = true;
  headings = [...doc.querySelectorAll('h2[id], h3[id]')].map(element => {
    const number = element.querySelector('.header-section-number, .ltx_tag_section, .ltx_tag_subsection, .ltx_tag_subsubsection')?.textContent.trim() || '';
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
// The frame gets the colours as values, so Increase Contrast, which changes them, styles the frame again.
matchMedia('(prefers-contrast: more)').addEventListener('change', () => styleReader());

// The app's handlers on paper elements run because the frame's sandbox has allow-scripts; the paper CSP
// still blocks every paper script.
function wire(doc) {
  for (const type of ['pointerdown', 'wheel', 'keydown', 'touchstart']) doc.addEventListener(type, noteInput, {passive: true});
  doc.addEventListener('keydown', event => {
    // As in the page, Escape closes the open preview, or else Split view.
    if (event.key === 'Escape' && (closePreview() || split && (leaveSplit(), true)) || enterPreview(event)) { event.preventDefault(); return; }
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
  // The page's scroll spy does not see the frame scroll in Split view.
  doc.defaultView.addEventListener('scroll', () => { if (split) requestAnimationFrame(splitTitle); }, {passive: true});
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
  // An inline formula, or the image that stands for it in some Papers, keeps the punctuation that touches it on its line.
  for (const formula of doc.querySelectorAll('math:not([display=block]), img.math-image')) glueFormula(formula, formula.previousSibling, formula.nextSibling);
}
const enlarge = image => {
  const caption = image.closest('figure')?.querySelector('figcaption');
  openFigure(image.src, image.alt, caption ? headingText(caption) : '');
  // In Dark, app.css dims a Paper figure; Overview and Blog figures have their own dark palette.
  $('figure-image').dataset.paper = '';
};
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
  if (window.scrollY !== heldY) { held = null; clearTimeout(heldTimer); heldTimer = setTimeout(hold, 150); }
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
  showTimer = setTimeout(() => { waitingFor = null; show(element); }, 350);
}
function leave(event, selector) {
  const from = selector ? event.target.closest?.(selector) : null;
  if (selector && (!from || from.contains(event.relatedTarget))) return;
  clearTimeout(showTimer); waitingFor = null;
  clearTimeout(hideTimer); hideTimer = setTimeout(closePreview, 550);
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
  preview.onmouseleave = () => { if (!preview.contains(document.activeElement)) hideTimer = setTimeout(closePreview, 550); };
  // The preview stays open while it has focus. Focus that leaves it for anything but its link closes it, and the link's
  // own focusin keeps it open.
  preview.addEventListener('focusin', () => clearTimeout(hideTimer));
  preview.addEventListener('focusout', event => { if (!preview?.contains(event.relatedTarget)) hideTimer = setTimeout(closePreview, 550); });
  preview.onkeydown = event => {
    const stops = [...preview.querySelectorAll('[tabindex="0"], button')], at = stops.indexOf(document.activeElement);
    if (event.key !== 'Escape' && !(event.key === 'Tab' && at === (event.shiftKey ? 0 : stops.length - 1))) return;
    event.preventDefault(); event.stopPropagation(); previewFor.focus({preventScroll: true});
  };
  // A preview that keyboard focus opens shows at once, also over the fade of Reduce Motion.
  if (anchor.ownerDocument.activeElement === anchor) preview.style.setProperty('animation', 'none', 'important');
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
    const centre = (box.left + box.right) / 2, left = Math.max(8, Math.min(innerWidth - width - 8, centre - width / 2));
    preview.style.left = left + 'px';
    preview.style.top = (under ? box.bottom + 10 : Math.max(ceiling, box.top - height - 10)) + 'px';
    // The popover grows from its link.
    preview.style.transformOrigin = `${centre - left}px ${under ? 'top' : 'bottom'}`;
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
  if (kind !== 'Reference') return openPreview(link, label, content, [], '', ['Figure', 'Table', 'Equation'].includes(kind));
  // copy() drops links, so the entry's hrefs come from the chapter.
  const id = referenceArxivID(element.textContent, [...element.querySelectorAll('a[href]')].map(a => a.getAttribute('href')));
  const go = ['Go to Reference', 'chev-r', () => follow(target), true];
  if (!id) return openPreview(link, label, content, [go, ['Find Paper', 'search', () => findReference(link, element, label, go)]]);
  const [actions, note] = paperActions(id);
  openPreview(link, label, content, [go, ...actions], note);
}
// Open for a cited Paper in the Library, else Add to Library, or a note while its import runs.
function paperActions(id) {
  const {paper, adding} = rowState({arxiv_id: id}, state.papers, state.jobs);
  if (paper) return [[['Open', 'doc', () => { closePreview(); commands.run({name: 'open', id: paper.id}); }]], ''];
  if (adding) return [[], 'Adding…'];
  return [[['Add to Library', 'plus', () => { closePreview(); run('/api/import', {url: 'https://arxiv.org/abs/' + id}); }]], ''];
}
// What a preview shows for each kind of target: the entry, figure, table, equation, footnote, or section start.
function previewContent(element, base) {
  const name = element.localName, inside = selector => element.closest(selector), fragment = document.createDocumentFragment();
  if (element.id.startsWith('ref-') || inside('#refs, .references, .csl-bib-body, .ltx_bibitem, .ltx_bibliography, [role=doc-biblioentry]')) return ['Reference', copy(element, base)];
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
// A heading's or a caption's text without the TeX source that a formula keeps in its annotation, which copy() also leaves out.
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
  // A table cell keeps the author's alignment, from its style or its LaTeXML class, so numbers stay right-aligned. The
  // style goes through CSSOM, which the CSP allows.
  const align = source.style?.textAlign || /\bltx_align_(center|right)\b/.exec(source.getAttribute('class') || '')?.[1];
  if (/^t[dh]$/.test(source.localName) && align) element.style.textAlign = align;
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
function localReferenceQuery(element) {
  const entry = element.textContent.replace(/^\s*\[\d+\]\s*/, '').replace(/(?:\bURL:?\s+)?\S*(?:https?:\/\/|(?:ar|alpha)xiv\.org\/)\S*/gi, ' ').replace(/\s+/g, ' ').trim();
  const title = entry.split(/(?<=[^\s.]{2})\.\s+/)[1];
  return (title?.split(' ').length >= 3 ? title : entry).slice(0, 300);
}
// Find Paper asks the service for the cited Paper. It drops a reply for another Paper or for a preview that has closed.
// A job poll opens the same Paper again, so the check is the Paper, not the open request.
async function findReference(link, element, label, go) {
  const asked = selected;
  openPreview(link, label, node('p', 'Finding the Paper…'), [go]);
  let reply;
  try { reply = await api('/api/reference', {text: element.textContent}); } catch { reply = {query: localReferenceQuery(element)}; }
  if (asked !== selected || !link.isConnected || previewFor !== link) return;
  if (reply.arxiv_id) {
    const [actions, note] = paperActions(reply.arxiv_id);
    return openPreview(link, label, node('p', reply.title), [go, ...actions], note);
  }
  closePreview();
  if (inputKind(reply.query) === 'search') commands.run({name: 'search', query: reply.query, submit: true});
}
function showPassage(citation) {
  const source = sources.get(citation.dataset.passage);
  if (!source || !citation.isConnected) return;
  if (source.earlier) return openEarlier(citation, source);
  openPreview(citation, source.section || 'Passage', node('p', source.text, 'clamp'), [['Open in Paper', 'doc', event => openPassage(source.href, event.detail > 0), true]], `Source ${citation.textContent}`);
}
$('blog-text').addEventListener('mouseover', event => hover(event.target.closest('.cn .citation'), showPassage));
$('blog-text').addEventListener('mouseout', event => leave(event, '.cn .citation'));
$('blog-text').addEventListener('focusin', event => hover(event.target.closest('.cn .citation'), showPassage));
$('blog-text').addEventListener('focusout', () => leave());
// A Chat answer's citation in a margin card shows its passage too. A citation from an earlier version shows its text
// at a click (chat.js openEarlier), and a streaming answer draws its citations again at each frame.
const CHAT = '.lx-card .lx-turn:not(.is-pending) .lx-answer .cn .citation:not(.is-earlier)';
function showCited(citation) {
  const source = detail?.paper?.passages?.find(item => item.id === citation.dataset.passage);
  if (!source || !citation.isConnected) return;
  openPreview(citation, source.section || 'Passage', node('p', source.text, 'clamp'), [['Open in Paper', 'doc', () => goPassage(source.href), true]], `Source ${citation.textContent}`);
}
document.addEventListener('mouseover', event => hover(event.target.closest?.(CHAT), showCited));
document.addEventListener('mouseout', event => leave(event, CHAT));
document.addEventListener('focusin', event => hover(event.target.closest?.(CHAT), showCited));
document.addEventListener('focusout', event => { if (event.target.closest?.(CHAT)) leave(); });
document.addEventListener('pointerdown', event => { if (preview && !preview.contains(event.target) && !previewFor?.contains(event.target)) closePreview(); });
document.addEventListener('keydown', event => {
  if (enterPreview(event)) return event.preventDefault();
  if (event.key !== 'Escape' || event.defaultPrevented || document.querySelector('dialog[open]')) return;
  if (closePreview()) event.preventDefault();
  else if (split) { leaveSplit(); event.preventDefault(); }
});

// ---- Opening a passage: Split view on a wide window, the Paper view below that ----
// `pointer` is true for a pointer click, which opens Split view with motion.
function openPassage(href, pointer = false) {
  const [path, id = ''] = String(href || '').split('#');
  if (!isPDF() && innerWidth >= SPLIT_WIDTH && knownChapter(path)) { splitFrom = previewFor || document.activeElement; closePreview(); return openSplit(path, id, pointer); }
  goPassage(href);
}
// When Split view closes with the focus in the pane, which hides, the focus goes back to the citation or card that
// opened the pane, or else to the main area.
function leaveSplit() {
  const inPane = $('paper').contains(document.activeElement);
  closeSplit(); syncReaderChrome();
  if (inPane) ($(activeTab).contains(splitFrom) ? splitFrom : $('main')).focus({preventScroll: true});
}
// Back closes Split view first, as Escape does, so a second Back leaves the Paper.
setBackHook(() => split && (leaveSplit(), true));
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
  // The page cannot read where the reader scrolls in a PDF, so the page of the jump is its Reading position.
  if (pdf) saveReading(selected, {view: 'paper', chapter: target, anchor: ''}).catch(() => {});
}
function openPassageByID(id, pointer = false) {
  const passage = [...(detail?.overview?.evidence || []), ...(detail?.paper?.passages || [])].find(item => item.id === id);
  if (passage) openPassage(passage.href, pointer);
}
// An open that a pointer starts moves the article and slides the pane in, so the eye follows the passage. A key opens
// it in the same frame, as does Reduce Motion. Every close is in one frame. The chapter title in the bar is replaced
// by the section title when the passage scrolls into view (splitTitle).
function openSplit(path, id, animate = false) {
  const change = () => {
    split = true;
    $('reader-page').classList.add('split'); $('paper').hidden = false; frame.style.height = '';
    if (path === loaded) { styleReader(); scrollToTarget({anchor: id, flash: true}); } else loadChapter(path, {anchor: id, flash: true});
    syncReaderChrome();
  };
  if (animate && !split && document.startViewTransition && !matchMedia('(prefers-reduced-motion: reduce)').matches) document.startViewTransition(change);
  else change();
}
function closeSplit() {
  if (!split) return;
  split = false;
  $('reader-page').classList.remove('split'); $('paper').hidden = activeTab !== 'paper';
  styleReader();
}
$('split-close').onclick = leaveSplit;
$('split-full').onclick = () => switchTab('paper');

// ---- The Blog and the Overview ----
function drawExplanations(result) {
  const signature = JSON.stringify([selected, result.paper.document_digest, result.blog?.cited_text, result.blog?.figures, result.blog?.explanation, result.overview?.text, result.overview?.figures?.map(figure => figure.mermaid || figure.svg_source)]);
  if (signature === explanations) return;
  explanations = signature;
  drawBlog(result.blog); drawOverview(result.overview);
  swapFigureSources(document.documentElement.dataset.theme);
}
// "Generated with <model>" and the accuracy note, and "<date> · <extra>" on the next line.
function provenance(generation, extra) {
  const record = generation.provenance || {}, made = Date.parse(record.created_at);
  const date = Number.isFinite(made) ? new Date(made).toLocaleDateString(undefined, {day: 'numeric', month: 'short', year: 'numeric'}) : '';
  return `Generated with ${record.model || generation.model || 'an unknown model'}. AI text can contain errors.\n${[date, extra].filter(Boolean).join(' · ')}`.trim();
}
function drawBlog(blog) {
  const explanation = blog?.explanation || {}, paper = detail.paper, text = blog?.cited_text || blog?.text || '';
  // As in Chat, a cited passage that this version of the Paper has with other text, or not at all, is from an earlier version.
  const texts = new Map((paper.passages || []).map(item => [item.id, item.text]));
  // A PDF chapter path keeps its '#page=N', and the evidence of a PDF page has its bibliography lines removed, so a PDF
  // passage is from an earlier version only when its page is gone.
  const earlier = source => isPDF() ? !knownChapter(source.href) : texts.get(source.id) !== source.text || !knownChapter(String(source.href).split('#')[0]);
  sources = new Map([...(paper.passages || []), ...(blog?.evidence || []).map(source => earlier(source) ? {...source, earlier: true} : source)]
    .map(source => [source.id, source]));
  $('blog-head').hidden = !blog; $('blog-limit').hidden = !explanation.limitation;
  $('blog-title').textContent = explanation.title || paper.title || paper.id;
  // The lead is the first sentence of the outline's through-line. A Blog saved before the lead uses its contribution,
  // without the planning note "Added parts: (1)" that the narrative prompt puts first.
  const leadText = String(explanation.lead || explanation.contribution || '').replace(/^\s*(?:added parts|parts added)\s*:\s*(?:\(\d+\)\s*)?/i, '').trim();
  const lead = leadText.match(/^.*?[.!?](?=\s|$)/s)?.[0] || leadText;
  $('blog-lead').textContent = lead.charAt(0).toUpperCase() + lead.slice(1);
  $('blog-lead').hidden = !lead;
  const words = text.replace(/\[p\d+[^\]]*\]/g, '').split(/\s+/).filter(Boolean).length;
  if (blog) $('blog-provenance').textContent = provenance(blog, `${Math.max(1, Math.round(words / 200))} min read`);
  prose($('blog-text'), text, [...sources.values()], blog?.figures || []);
  // The outline and the Reading position name a Blog section by this id.
  blogHeadings().forEach((heading, index) => { heading.id = `blog-section-${index}`; });
  $('blog-limit-text').textContent = explanation.limitation || '';
}
// The AI note and the hint go under the figure's title and subtitle, as the Blog's note goes under its title and lead.
// prose() empties #overview-text, so the header leaves the figure first.
const overviewHead = $('overview-head');
function drawOverview(overview) {
  $('overview-text').before(overviewHead);
  overviewHead.hidden = !overview;
  if (overview) $('overview-provenance').textContent = provenance(overview, '');
  prose($('overview-text'), overview?.text, [], overview?.figures || [], {overview: true});
  $('overview-text').querySelector('.overview-figure > .figure-diagram')?.before(overviewHead);
}
let diagrams = 0;
// $$TeX$$ in a diagram label, through the page's MathJax. Broken TeX returns nothing, so Pele shows the source.
function diagramMath(tex, size) {
  try {
    const svg = window.MathJax.tex2svg(tex, {display: false}).querySelector('svg');
    const width = parseFloat(svg?.getAttribute('width')) * size / 2, height = parseFloat(svg?.getAttribute('height')) * size / 2;
    if (!(width > 0 && height > 0) || svg.querySelector('[data-mjx-error]')) return null;
    svg.setAttribute('width', width + 'px'); svg.setAttribute('height', height + 'px');
    return {svg: svg.outerHTML, width, height};
  } catch { return null; }
}
// Excalifont starts to load with this module. A figure waits for it up to 300 ms, so that it draws once, in its own font.
const figureFont = Promise.race([document.fonts.load('16px Excalifont').catch(() => {}), new Promise(resolve => setTimeout(resolve, 300))]);
// The colours that a figure's classDef lines give for a light page, which Pele writes into style attributes, change in
// Dark: a light fill mixes into the dark surface, and dark text or a dark line gets lighter with the same hue. A dark
// fill, such as the key box, stays as it is. The exports keep the light colours.
// shortcut: lightness is the cube root of the luminance, near OKLCH L for these classes, and a named colour such as
// "black" stays as it is; upgrade if a colour lands wrong.
const lightness = colour => {
  const [r, g, b] = (String(colour).match(/^rgba?\(([\d.]+), ([\d.]+), ([\d.]+)/)?.slice(1) || []).map(value => ((value / 255 + .055) / 1.055) ** 2.4);
  return Math.cbrt(.2126 * r + .7152 * g + .0722 * b);
};
function darkColours(svg) {
  for (const element of svg.querySelectorAll('[style]')) {
    const style = element.style, text = ['text', 'tspan'].includes(element.localName);
    if (text && lightness(style.fill) < .6) style.fill = `oklch(from ${style.fill} .78 c h)`;
    if (!text && lightness(style.fill) > .6) style.fill = `color-mix(in oklab, ${style.fill} 22%, var(--pele-surface))`;
    if (lightness(style.stroke) < .6) style.stroke = `oklch(from ${style.stroke} .78 c h)`;
  }
}
// Pele moves a group's label left, off the arrow into the group's top, and the label can then touch the group's edge.
// The label moves right to a 10-unit inset. A label that Pele moved is in the titles layer, with its halo, in the same
// coordinates. A figure in a hidden view measures zero, so showView() calls this again.
function nudgeClusterLabels(container) {
  for (const group of container.querySelectorAll('.pele-cluster')) {
    const rect = group.querySelector(':scope > rect'), label = group.querySelector(':scope > .pele-cluster-label')
      || container.querySelector(`.pele-cluster-title[data-id="${CSS.escape(group.dataset.id || '')}"]`);
    if (!rect || !label) continue;
    const box = rect.getBBox(), text = label.getBBox();
    if (!box.width || !text.width) continue;
    const base = label.dataset.base ??= label.getAttribute('transform') || '', shift = box.x + 10 - text.x;
    if (shift > 0) label.setAttribute('transform', `translate(${shift} 0) ${base}`.trim());
  }
}
// A Mermaid figure, drawn by Pele in the layout the Diagram checks measured, sketched, and scaled down to fit. Its colours
// are Pele's CSS variables, which app.css sets from the Figure palette. Its own classDef colours change only in Dark, so
// swapFigureSources() draws it again when Dark starts or ends.
function drawDiagram(container, figure, waited = false) {
  container.figure = figure;
  if (!waited && !document.fonts.check('16px Excalifont')) {
    figureFont.then(() => { if (container.isConnected) drawDiagram(container, figure, true); });
    return;
  }
  // Pele measures labels in the page font, so a figure drawn before Excalifont loads is drawn again after it.
  if (!document.fonts.check('16px Excalifont')) document.fonts.load('16px Excalifont').then(faces => {
    if (faces.length && container.isConnected) { window.pele.forgetTextWidths(); drawDiagram(container, figure); }
  });
  const options = {maxWidth: figure.layout_width || 1000, autoDirection: false, links: false, images: false,
    fontFamily: getComputedStyle(container).fontFamily || undefined, ...(window.MathJax?.tex2svg ? {math: diagramMath} : {})};
  const dark = document.documentElement.dataset.theme === 'dark';
  container.dark = dark;
  try {
    // The main diagram has no config of its own, so it gets the wrap that its Diagram check measured.
    container.replaceChildren(...[[figure.mermaid], [figure.chart, figure.chart_config]].filter(([source]) => source).map(([source, config]) => {
      const part = node('div', undefined, config ? 'figure-chart' : 'figure-main');
      part.innerHTML = sketch(window.pele.render(source, {...options, config: config || figure.layout_config, idPrefix: `diagram${++diagrams}-`}).svg, window.rough);
      if (dark && !config) darkColours(part);
      return part;
    }));
    nudgeClusterLabels(container);
    const nodes = [...container.querySelectorAll('.pele-node[data-id]')];
    for (const item of nodes) item.dataset.node = item.dataset.id;
    annotateFigure(nodes, figure.components, {onPassage: openPassageByID});
    const components = new Map((figure.components || []).map(item => [item.node, item]));
    // Not the onfocusin property: Chromium has none, so only a listener fires there. A redraw replaces the map.
    container.components = components;
    if (!('hover' in container.dataset)) {
      container.dataset.hover = '';
      container.addEventListener('focusin', event => hover(event.target.closest?.('.has-component'), card => showComponent(card, container.components.get(card.dataset.node))));
      container.addEventListener('focusout', () => leave());
      container.addEventListener('mouseover', event => hover(event.target.closest?.('.has-component'), card => showComponent(card, container.components.get(card.dataset.node), true)));
      container.addEventListener('mouseout', event => leave(event, '.has-component'));
    }
  } catch {
    container.replaceChildren(figureFailure(() => drawDiagram(container, figure)));
  }
  // The Overview outline names a step by this id. The figure can draw after the last Chrome state, and again when
  // Excalifont loads, so the outline is sent again. This is outside the try, so an error here does not hide the figure.
  if (container.closest('#overview-text')) {
    $('overview-text').querySelectorAll('.figure-main .pele-cluster').forEach((group, index) => { group.id = `overview-step-${index}`; });
    syncReaderChrome();
  }
}
// The Component hover, for a pointer that rests on a card and for keyboard focus. A click also focuses the card, so focus
// opens this preview only when the focus shows.
function showComponent(card, component, pointer = false) {
  if (!component || !pointer && !card.matches(':focus-visible')) return;
  const body = document.createDocumentFragment(), passage = component.passages?.[0];
  for (const line of [component.computes && `Computes ${component.computes}`, component.role, component.values && `Values: ${component.values}`]) if (line) body.append(node('p', line));
  openPreview(card, component.name, body, passage ? [['Open in Paper', 'doc', event => openPassageByID(passage, event.detail > 0), true]] : []);
}
export function swapFigureSources(theme) {
  for (const img of document.querySelectorAll('img[data-dark-src]')) {
    const next = theme === 'dark' ? img.dataset.darkSrc : img.dataset.lightSrc;
    if (img.getAttribute('src') !== next) img.src = next;
  }
  // A Mermaid figure drawn for the other side of Dark draws again. One that waits for its font draws later in any case.
  for (const container of document.querySelectorAll('.figure-diagram')) {
    if (container.figure && container.dark === (theme !== 'dark')) drawDiagram(container, container.figure);
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
// Only the Overview passes overview: its figure shows its title and subtitle, and a Scene Overview image has no caption.
const prose = (target, text, references, figures, extra = {}) => renderProse(target, text, {node, references, figures, fileURL, renderMath, openFigure, drawDiagram, ...extra,
  openSource: openPassage, openEarlier});
