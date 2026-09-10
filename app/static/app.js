/* No provider keys are retained by the browser. Paper and model text are always text nodes. */
'use strict';
const $ = id => document.getElementById(id);
const fragment = new URLSearchParams(location.hash.slice(1));
let token = fragment.get('token') || localStorage.getItem('papers-session') || '';
if (fragment.has('token')) { localStorage.setItem('papers-session', token); history.replaceState(null, '', location.pathname); }
let state = {papers: [], jobs: [], settings: {}}, selected = null, detail = null, stateSignature = '', jobSignature = '', detailRequest = 0;
const retries = new Map();
const completedImports = new Set();
const downloadedExports = new Set();
const jobNotices = new Map();
let recommendationsSignature = '', stateInitialized = false;
let jobsInitialized = false, activeTab = 'overview', overviewSignature = '', noticeTimer;
let readerObserver, tourStep = null, currentChapter = '';
const TOUR_ID = '1706.03762v7';
const terminal = new Set(['ready', 'completed', 'succeeded', 'failed', 'cancelled', 'interrupted']);
const node = (tag, text, className) => { const el = document.createElement(tag); if (text !== undefined) el.textContent = text; if (className) el.className = className; return el; };
const paperAPI = id => `/api/papers/${encodeURIComponent(id)}`;
function fileURL(path) {
  // Resolve only a relative file within the selected paper, never an external/model URL.
  if (!selected || typeof path !== 'string' || /^(?:[a-z]+:|\/|\\)/i.test(path) || path.split(/[\\/]/).includes('..')) return null;
  const [filename, anchor = ''] = path.split('#');
  const url = new URL(`/files/${encodeURIComponent(selected)}/${filename.split('/').map(encodeURIComponent).join('/')}`, location.origin);
  url.searchParams.set('token', token); if (anchor) url.hash = anchor; return url.href;
}
function notice(message, autoDismiss = false) {
  clearTimeout(noticeTimer); $('notice').replaceChildren(); $('notice').hidden = !message;
  if (!message) return;
  const heading = node('div', undefined, 'toast-heading'), close = node('button', '×');
  close.setAttribute('aria-label', 'Dismiss notification'); close.onclick = () => { $('notice').hidden = true; };
  heading.append(node('span', message), close); $('notice').append(heading);
  $('notice').classList.remove('toast-expiring');
  if (autoDismiss) noticeTimer = expireToast($('notice'),() => { $('notice').hidden = true; });
}
function expireToast(element, remove) {
  element.classList.remove('toast-expiring'); void element.offsetWidth;
  element.classList.add('toast-expiring');
  return setTimeout(remove,window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 5000 : 5250);
}
function downloadLink(path) {
  const url = new URL(path, location.origin);
  if (url.origin !== location.origin || !url.pathname.startsWith('/files/')) return null;
  url.searchParams.set('token', token);
  const link = node('a', url.pathname.toLowerCase().endsWith('.png') ? 'Save PNG' : url.pathname.toLowerCase().endsWith('.pdf') ? 'Save PDF' : 'Save EPUB'); link.href = url.href; link.download = '';
  return link;
}
function downloadFinishedExports(jobs) {
  for (const job of jobs) {
    if (job.kind !== 'export' || !['ready','completed','succeeded'].includes(job.state) || !job.result?.download_url || !retries.has(job.id) || downloadedExports.has(job.id)) continue;
    downloadedExports.add(job.id);
    const link = downloadLink(job.result.download_url);
    if (link) { document.body.append(link); link.click(); link.remove(); }
  }
}
async function api(path, payload) {
  const response = await fetch(path, {method: payload === undefined ? 'GET' : 'POST', headers: {Authorization: `Bearer ${token}`, ...(payload === undefined ? {} : {'Content-Type': 'application/json'})}, ...(payload === undefined ? {} : {body: JSON.stringify(payload)})});
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || `Request failed (${response.status})`);
  return result;
}
async function run(path, payload) {
  try { notice(''); const result = await api(path, payload); if (result.job) retries.set(result.job.id, {path, payload}); await refresh(); return result; }
  catch (error) { notice(error.message); return null; }
}
function switchTab(name) {
  activeTab = ['overview', 'blog', 'paper'].includes(name) ? name : 'overview';
  for (const view of ['overview', 'blog', 'paper']) { const active = view === activeTab; $(view).hidden = !active; $(`tab-${view}`).setAttribute('aria-selected', String(active)); $(`tab-${view}`).tabIndex = active ? 0 : -1; }
  renderContents();
  updateViewActions();
  if (activeTab === 'paper') styleReader();
}
for (const [index, name] of ['overview', 'blog', 'paper'].entries()) {
  $(`tab-${name}`).onclick = () => switchTab(name);
  $(`tab-${name}`).onkeydown = event => { if (!['ArrowLeft','ArrowRight','Home','End'].includes(event.key)) return; event.preventDefault(); const tabs = ['overview','blog','paper']; const next = event.key === 'Home' ? 0 : event.key === 'End' ? 2 : (index + (event.key === 'ArrowLeft' ? 2 : 1)) % 3; switchTab(tabs[next]); $(`tab-${tabs[next]}`).focus(); };
}
function renderLibrary() {
  $('paper-count').textContent = state.papers.length;
  const query = $('search').value.toLowerCase();
  $('paper-list').replaceChildren();
  const papers = state.papers.filter(p => `${p.title} ${p.authors} ${p.arxiv_id || p.id}`.toLowerCase().includes(query));
  if (tourStep !== null) papers.sort((a,b) => Number(b.id === TOUR_ID)-Number(a.id === TOUR_ID));
  for (const paper of papers) {
    const button = node('button'); button.append(node('span',paper.title || paper.id,'library-paper-title'));
    if (paper.id === TOUR_ID) button.id = 'tour-paper';
    button.setAttribute('aria-current', String(paper.id === selected)); button.title = paper.title || paper.id;
    if (paper.authors) button.append(node('span', Array.isArray(paper.authors) ? paper.authors.join(', ') : paper.authors, 'library-paper-authors'));
    button.append(node('small', paper.arxiv_id || paper.id));
    button.onclick = () => tourStep === 1 && paper.id === TOUR_ID ? showTourStep(2) : openPaper(paper.id);
    const card = node('div', undefined, 'library-card');
    const actions = node('details', undefined, 'library-actions');
    const summary = node('summary', '•••');
    summary.setAttribute('aria-label', `Actions for ${paper.title || paper.id}`);
    actions.append(summary);
    actions.onkeydown = event => { if (event.key === 'Escape') { actions.open = false; summary.focus(); event.stopPropagation(); } };
    const remove = node('button', 'Remove paper', 'remove-paper');
    remove.setAttribute('aria-label', `Remove ${paper.title || paper.id} from library`);
    remove.onclick = () => {
      actions.open = false;
      $('remove-paper-dialog').dataset.paperId = paper.id;
      $('remove-paper-name').textContent = paper.title || paper.id;
      $('remove-paper-error').textContent = '';
      $('remove-paper-dialog').addEventListener('close', () => { if (summary.isConnected) summary.focus(); }, {once:true});
      $('remove-paper-dialog').showModal();
      $('remove-paper-cancel').focus();
    };
    actions.append(remove); card.append(button, actions); $('paper-list').append(card);
  }
  if (!$('paper-list').children.length) $('paper-list').append(node('p', state.papers.length ? 'No matching papers. Try another title or author.' : 'Your imported papers will appear here.', 'muted'));
}
$('remove-paper-cancel').onclick = () => $('remove-paper-dialog').close();
$('remove-paper-confirm').onclick = async () => {
  const dialog = $('remove-paper-dialog'), id = dialog.dataset.paperId;
  $('remove-paper-confirm').disabled = true;
  $('remove-paper-error').textContent = '';
  try {
    await api(`${paperAPI(id)}/remove`, {});
    dialog.close();
    if (selected === id) showLibrary();
    if (refreshing) await refreshing;
    await refresh();
    $('library-title').focus({preventScroll:true});
    notice('Paper removed from your library.', true);
  } catch (error) {
    $('remove-paper-error').textContent = error.message;
    await refresh();
  } finally { $('remove-paper-confirm').disabled = false; }
};
function sources(target, values) {
  target.replaceChildren();
  for (const source of values || []) { if (!fileURL(source.href)) continue; const button = node('button', source.section || source.id || 'Source'); button.title = source.text || 'Read supporting passage'; button.onclick = () => { $('reader').src = fileURL(source.href); switchTab('paper'); }; target.append(button); }
}
function cleanOverviewCitations(text) {
  return String(text || '').replace(/[ \t]*\[\s*p\d+(?:\s*[,;]\s*p\d+)*\s*\]/g, '');
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
// Protect code and math pipes such as P(y|x) before finding table cell boundaries.
function tableCells(value) {
  const cells = []; let cell = '';
  const tokens = value.trim().match(/`+[^`]*`+|\$\$[\s\S]*?\$\$|(?<!\\)\$[^$\n]+(?<!\\)\$|\\\([\s\S]*?\\\)|\\\[[\s\S]*?\\\]|\\\||\||[^|`$\\]+|[\s\S]/g) || [];
  for (const token of tokens) {
    if (token === '|') { cells.push(cell.trim()); cell = ''; }
    else cell += token === '\\|' ? '|' : token;
  }
  cells.push(cell.trim());
  if (value.trim().startsWith('|')) cells.shift();
  if (value.trim().endsWith('|') && !value.trim().endsWith('\\|')) cells.pop();
  return cells;
}
function tableDivider(value) {
  const cells = tableCells(value || '');
  return cells.length > 1 && cells.every(cell => /^:?-+:?$/.test(cell));
}
function renderProse(target, text, references = [], figures = []) {
  const known = new Map(references.map(source => [source.id, source]));
  const numbers = new Map(references.map((source, index) => [source.id, index + 1]));
  const formulas = [];
  function formula(parent, source, tex, display = false) {
    const element = node('span', source, display ? 'math-formula math-display' : 'math-formula');
    parent.append(element); formulas.push([element, tex, display]);
  }
  function inline(parent, value) {
    const pattern = /(`[^`\n]+`|(?<!\\)\$\$[\s\S]*?\$\$|(?<!\\)\$[^$\n]+(?<!\\)\$|\\\([\s\S]*?\\\)|\\\[[\s\S]*?\\\]|\*\*[^*]+\*\*|\*[^*\n]+\*|\[p\d+\])/g;
    let offset = 0;
    for (const match of value.matchAll(pattern)) {
      if (match.index > offset) parent.append(node('span', value.slice(offset, match.index)));
      const part = match[0], source = known.get(part.slice(1, -1));
      if (source && fileURL(source.href)) {
        const number = numbers.get(source.id);
        const citation = node('button', `[${number}]`, 'citation');
        citation.type = 'button'; citation.title = source.text || source.section || source.id;
        citation.setAttribute('aria-label', `Read source ${number}: ${source.section || 'supporting passage'}`);
        citation.onclick = () => { $('reader').src = fileURL(source.href); switchTab('paper'); };
        parent.append(citation);
      } else if (part.startsWith('`')) parent.append(node('code', part.slice(1, -1)));
      else if (part.startsWith('$') || part.startsWith('\\')) {
        const display = part.startsWith('$$') || part.startsWith('\\[');
        const size = part.startsWith('$') && !display ? 1 : 2;
        formula(parent, part, part.slice(size, -size), display);
      } else if (part.startsWith('**')) { const strong = node('strong'); inline(strong, part.slice(2, -2)); parent.append(strong); }
      else if (part.startsWith('*')) { const em = node('em'); inline(em, part.slice(1, -1)); parent.append(em); }
      else parent.append(node('span', part));
      offset = match.index + part.length;
    }
    if (offset < value.length) parent.append(node('span', value.slice(offset)));
  }
  target.replaceChildren();
  const lines = String(text || '').replace(/\r\n?/g, '\n').split('\n');
  let paragraph = [], list = null;
  const flush = () => { if (paragraph.length) { const p = node('p'); inline(p, paragraph.join(' ')); target.append(p); paragraph = []; } };
  for (let index = 0; index < lines.length; index++) {
    const line = lines[index], heading = line.match(/^(#{1,6})\s+(.+)$/), item = line.match(/^\s*(?:([-+*])|\d+[.)])\s+(.+)$/);
    const displayStart = line.trim().match(/^(\$\$|\\\[|\\begin\{(equation\*?|align\*?|gather\*?)\})/);
    if (line.trim().startsWith('```')) {
      flush(); list = null;
      const language = line.trim().slice(3).trim().toLowerCase(), content = [];
      while (++index < lines.length && !lines[index].trim().startsWith('```')) content.push(lines[index]);
      if (['math','tex','latex'].includes(language)) formula(target, content.join('\n'), content.join('\n'), true);
      else if (['markdown','md'].includes(language) || !language && content.some(tableDivider)) {
        const block = node('div'); renderProse(block, content.join('\n'), references, figures); target.append(block);
      } else { const pre = node('pre'); pre.append(node('code', content.join('\n'))); target.append(pre); }
    } else if (displayStart) {
      flush(); list = null;
      const start = displayStart[1], end = start === '$$' ? '$$' : start === '\\[' ? '\\]' : `\\end{${displayStart[2]}}`;
      let content = line.trim().slice(start.length);
      while (!content.includes(end) && index + 1 < lines.length) content += '\n' + lines[++index];
      const closing = content.indexOf(end);
      if (closing < 0) target.append(node('p', start + content));
      else {
        const tex = content.slice(0, closing);
        formula(target, start + tex + end, displayStart[2] ? start + tex + end : tex, true);
        if (content.slice(closing + end.length).trim()) paragraph.push(content.slice(closing + end.length).trim());
      }
    } else if (line.includes('|') && tableDivider(lines[index + 1]) && tableCells(line).length === tableCells(lines[index + 1]).length) {
      flush(); list = null;
      const cells = tableCells;
      const headers = cells(line), table = node('table'), head = node('thead'), row = node('tr'), body = node('tbody');
      for (const value of headers) { const cell = node('th'); cell.setAttribute('scope','col'); inline(cell,value); row.append(cell); }
      head.append(row); table.append(head,body); table.tabIndex = 0; table.setAttribute('aria-label', 'Article table'); index++;
      while (index + 1 < lines.length && lines[index + 1].includes('|') && cells(lines[index + 1]).length === headers.length) {
        const row = node('tr'); for (const value of cells(lines[++index])) { const cell = node('td'); inline(cell,value); row.append(cell); } body.append(row);
      }
      target.append(table);
    } else if (/^\{\{figure:fig\d+\}\}$/.test(line.trim())) {
      flush(); list = null;
      const figure = figures.find(f => `{{figure:${f.id}}}` === line.trim());
      const image = figure && fileURL(figure.svg || figure.png);
      if (image) {
        const block = node('figure', undefined, 'overview-figure'), img = node('img');
        img.src = image; img.alt = figure.alt || figure.caption || 'Paper explanation'; img.loading = 'lazy';
        const expand = node('button', undefined, 'figure-open'); expand.type = 'button'; expand.setAttribute('aria-label', 'Enlarge figure: ' + (figure.alt || figure.caption || 'Paper explanation')); const picture = node('picture');
        if (figure.portrait?.svg) { const source = node('source'); source.media = '(max-width: 600px)'; source.srcset = fileURL(figure.portrait.svg); picture.append(source); }
        picture.append(img); expand.append(picture, node('span', 'Enlarge figure ↗')); expand.onclick = () => openFigure(img.currentSrc || image, img.alt, figure.caption);
        block.append(expand, node('figcaption', figure.caption));
        if (figure.design?.layout === 'bento') {
          const transcript = node('details', undefined, 'bento-transcript');
          transcript.append(node('summary', 'Read overview text'));
          const panels = figure.design.nodes || [];
          const readingOrder = figure.design.packing?.rows?.flatMap(row => row.cards) || panels.map((_, i) => i);
          for (const index of readingOrder) {
            const panel = panels[index];
            if (panel.title) transcript.append(node('h3', panel.title));
            transcript.append(node('p', panel.body));
            if (panel.visual) {
              const visual = panel.visual;
              if (visual.kind === 'flow') transcript.append(node('p', visual.steps.join(' → ')));
              if (visual.kind === 'illustration' && visual.alt) transcript.append(node('p', visual.alt));
              if (visual.kind === 'metrics') {
                const values = node('ul');
                for (const item of visual.items) values.append(node('li', `${item.label}: ${item.value}`));
                transcript.append(values);
              }
              transcript.append(node('p', visual.caption));
            }
          }
          transcript.append(node('p', figure.design.scope));
          block.append(transcript);
        }
        target.append(block);
      } else target.append(node('p', 'Figure unavailable. Regenerate this view to restore it.', 'muted'));
    } else if (heading) {
      flush(); list = null; const h = node(`h${Math.min(heading[1].length + 1, 6)}`); inline(h, heading[2]); target.append(h);
    } else if (item) {
      flush(); const tag = item[1] ? 'ul' : 'ol';
      if (!list || list.tagName.toLowerCase() !== tag) { list = node(tag); target.append(list); }
      const li = node('li'); inline(li, item[2]); list.append(li);
    } else if (!line.trim()) { flush(); list = null; }
    else { list = null; paragraph.push(line.trim()); }
  }
  flush();
  for (const args of formulas) renderMath(...args);
}
async function openPaper(id) {
  const request = ++detailRequest;
  try {
    const result = await api(paperAPI(id)); if (request !== detailRequest) return;
    const changedPaper = selected !== id;
    const documentChanged = selected === id && detail?.paper?.document_digest !== result.paper.document_digest;
    selected = id; detail = result; const paper = result.paper;
    $('empty').hidden = true; $('library-page').hidden = true; $('reader-home').hidden = false; $('workspace').hidden = false; $('reading-bar').hidden = false; document.body.classList.remove('is-library'); document.body.classList.add('is-reading');
    $('paper-id').textContent = paper.arxiv_id || paper.id;
    $('paper-title').textContent = paper.title || paper.id;
    $('paper-authors').textContent = Array.isArray(paper.authors) ? paper.authors.join(', ') : paper.authors || '';
    $('paper-authors').hidden = $('paper-authors').textContent.length > 140;
    const nextOverview = JSON.stringify([id, result.overview?.text, result.overview?.figures, result.bento]);
    if (nextOverview !== overviewSignature) {
      overviewSignature = nextOverview;
      renderProse($('overview-text'), cleanOverviewCitations(result.overview?.text), [], result.overview?.figures || []);
      renderProse($('bento-text'), result.bento?.text, [], result.bento?.figures || []);
    }
    $('overview-note').textContent = result.overview ? '' : 'Generate a blog for a longer explanation of this paper.';
    $('overview-note').hidden = Boolean(result.overview);
    $('generate').textContent = result.overview ? 'Regenerate blog' : 'Generate blog';
    $('bento-note').textContent = result.bento ? '' : 'Generate a visual overview, or open Paper to start reading.';
    $('bento-note').hidden = Boolean(result.bento);
    $('generate-bento').textContent = result.bento ? 'Regenerate overview' : 'Generate overview';
    $('generate-bento').disabled = !paper.passages?.length;

    const pdf = paper.format === 'pdf';
    $('fallback-notice').hidden = !pdf;
    $('fallback-notice').textContent = pdf ? paper.report.warning : '';
    $('generate').disabled = pdf && !paper.passages?.length;
    if (pdf && paper.report.text_warning && !result.overview) $('overview-note').textContent = paper.report.text_warning;
    $('overview-sources').replaceChildren();
    if (changedPaper || !(paper.chapters || []).some(chapter => chapter.path === currentChapter)) currentChapter = paper.chapters?.[0]?.path || '';
    const nextURL = fileURL(currentChapter);
    if (nextURL && (documentChanged || changedPaper || !$('reader').getAttribute('src'))) {
      if (pdf) $('reader').removeAttribute('sandbox');
      else $('reader').setAttribute('sandbox', 'allow-same-origin');
      $('reader').style.height = pdf ? '75vh' : '';
      $('reader').src = nextURL;
    }
    if (!nextURL) $('reader').removeAttribute('src');
    updateDeliveryControls();
    updateShareControls();
    renderContents();
    updateViewActions();
    if (changedPaper) { setReadingPreferences(false); closeMobilePanels(); switchTab('overview'); window.scrollTo(0,0); }
    renderLibrary();
  } catch (error) { notice(error.message); }
}
function renderJobs() {
  const success = job => ['ready','completed','succeeded','cancelled'].includes(job.state);
  for (const job of state.jobs) {
    const signature = JSON.stringify([job.state, job.progress, job.error, job.result]);
    let record = jobNotices.get(job.id);
    if (record?.signature === signature) continue;
    if (!record) { record = {signature, element:null, timer:null}; jobNotices.set(job.id, record); }
    else { clearTimeout(record.timer); record.element?.remove(); record.signature = signature; }
    // A new window starts a fresh notification run, including for saved errors.
    // Keep durable job/error records; only announce work active or changed in this run.
    if (!jobsInitialized && terminal.has(job.state)) continue;
    const item = node('div', undefined, 'toast glass'); item.setAttribute('data-state', job.state); record.element = item;
    const heading = node('div', undefined, 'toast-heading'), close = node('button', '×');
    const kind = {import:'Paper import',reading:'Paper understanding',summary:'Blog',bento:'Overview',chat:'Question',export:'File export',send:'Kindle delivery',recommend:'Recommendations'}[job.kind] || 'Task';
    const status = {ready:'ready',completed:'ready',succeeded:'ready',failed:'failed',interrupted:'interrupted',cancelled:'cancelled',running:'in progress',queued:'queued'}[job.state] || 'in progress';
    heading.append(node('strong', `${kind} ${status}`), close); close.setAttribute('aria-label', 'Dismiss ' + kind.toLowerCase());
    close.onclick = () => { clearTimeout(record.timer); item.remove(); updateNotificationToggle(); }; item.append(heading);
    const description = job.error || job.result?.warning || (typeof job.progress === 'string' ? job.progress : '');
    if (description) item.append(node('p', description));
    const actions = node('div', undefined, 'toast-actions');
    if (!terminal.has(job.state)) {
      const progress = node('progress'); progress.setAttribute('aria-label', kind + ' progress');
      if (typeof job.progress === 'number') { progress.max = 100; progress.value = job.progress; }
      item.append(progress); const cancel = node('button','Cancel','quiet'); cancel.onclick = () => run(`/api/jobs/${encodeURIComponent(job.id)}/cancel`,{}); actions.append(cancel);
    }
    if (['failed','interrupted','cancelled'].includes(job.state) && job.kind !== 'send') {
      let retry = retries.get(job.id);
      if (!retry && job.payload?.url && job.kind === 'import') retry = {path:'/api/import',payload:{url:job.payload.url}};
      if (!retry && job.payload?.paper_id && ['summary','bento','export'].includes(job.kind)) retry = {path:`${paperAPI(job.payload.paper_id)}/${job.kind}`,payload:job.payload};
      if (retry) { const button = node('button','Retry','quiet'); button.onclick = () => { item.remove(); updateNotificationToggle(); run(retry.path,retry.payload); }; actions.append(button); }
    }
    if (job.result?.download_url) { const link = downloadLink(job.result.download_url); if (link) actions.append(link); }
    if (job.kind === 'send' && success(job)) item.append(node('p','Handed to Mail. Check your Kindle to confirm delivery.'));
    if (actions.children.length) item.append(actions); $('jobs').append(item);
    if (!success(job) || actions.children.length || job.error || job.result?.warning) continue;
    const expire = () => { item.classList.remove('toast-expiring'); record.timer = expireToast(item,() => { item.remove(); updateNotificationToggle(); }); };
    item.onmouseenter = item.onfocusin = () => { clearTimeout(record.timer); item.classList.remove('toast-expiring'); };
    item.onmouseleave = item.onfocusout = expire; expire();
  }
  jobsInitialized = true; updateNotificationToggle();
}
function updateNotificationToggle() {
  const count = $('jobs').children.length; $('notifications-toggle').hidden = count === 0;
  $('notifications-toggle').textContent = `${count} update${count === 1 ? '' : 's'}`;
}
$('notifications-toggle').onclick = () => {
  const open = $('notifications-toggle').getAttribute('aria-expanded') !== 'true';
  document.body.classList.toggle('notifications-open',open); $('notifications-toggle').setAttribute('aria-expanded',String(open));
};
let refreshing = null;
function refresh() {
  if (!refreshing) refreshing = refreshState().finally(() => { refreshing = null; });
  return refreshing;
}
async function refreshState() {
  try {
    const next = await api('/api/state'); state = next;
    if (selected && !next.papers.some(p => p.id === selected)) showLibrary();
    renderRecommendations();
    if (!stateInitialized) { for (const job of next.jobs) if (job.kind === 'import' && terminal.has(job.state)) completedImports.add(job.id); stateInitialized = true; }
    const papers = JSON.stringify(next.papers), jobs = JSON.stringify(next.jobs);
    if (papers !== stateSignature) { stateSignature = papers; renderLibrary(); }
    if (jobs !== jobSignature) {
      jobSignature = jobs; renderJobs();
      downloadFinishedExports(next.jobs);
      const imported = next.jobs.find(job => job.kind === 'import' && ['ready','completed','succeeded'].includes(job.state) && job.result?.paper_id && next.papers.some(p => p.id === job.result.paper_id) && !completedImports.has(job.id));
      for (const job of next.jobs) if (job.kind === 'import' && terminal.has(job.state)) completedImports.add(job.id);
      if (tourStep === null) { if (imported) await openPaper(imported.result.paper_id); else if (selected) await openPaper(selected); }
    }
    const missing = Object.entries(next.dependencies || {}).filter(([, available]) => !available).map(([name]) => name);
    $('dependencies').textContent = missing.length ? `Not installed: ${missing.join(', ')}. Install these tools before converting papers.` : 'All conversion tools are available.';
  } catch (error) { notice(error.message); }
}
$('search').oninput = renderLibrary;
function goHome() { setReadingPreferences(false); ++detailRequest; selected = null; detail = null; $('empty').hidden = false; $('library-page').hidden = true; $('reader-home').hidden = true; $('workspace').hidden = true; closeMobilePanels(); $('reading-bar').hidden = true; document.body.classList.remove('is-focused','is-reading','is-library'); $('mobile-home').setAttribute('aria-current','page'); $('mobile-library').removeAttribute('aria-current'); $('exit-focus').hidden = true; window.scrollTo(0,0); }
$('home-open').onclick = event => { event.preventDefault(); if (tourStep !== null) finishTour(); else goHome(); };
$('reader-home').onclick = () => tourStep !== null ? finishTour() : goHome();
function showLibrary() { goHome(); $('empty').hidden = true; $('library-page').hidden = false; document.body.classList.add('is-library'); $('mobile-home').removeAttribute('aria-current'); $('mobile-library').setAttribute('aria-current','page'); $('reader-home').hidden = false; renderLibrary(); $('library-title').focus({preventScroll:true}); }
$('library-open').onclick = () => { if (tourStep !== null) finishTour(); showLibrary(); };
$('library-add').onclick = () => { goHome(); $('home-url').focus(); };
$('home-form').onsubmit = async event => { event.preventDefault(); const result = await run('/api/import', {url:$('home-url').value.trim()}); if (result) $('home-url').value = ''; };
function renderRecommendations() {
  const items = state.recommendations?.items || [], signature = JSON.stringify(items);
  $('recommendations').hidden = !items.length;
  if (signature === recommendationsSignature) return;
  recommendationsSignature = signature; $('recommendation-list').replaceChildren();
  for (const item of items) {
    // Only server-verified arXiv IDs can become links or import actions.
    if (!/^(?:\d{4}\.\d{4,5}|[A-Za-z][A-Za-z.\-]*\/\d{7})(?:v[1-9]\d*)?$/.test(item.id)) continue;
    const url = 'https://arxiv.org/abs/' + item.id;
    const card = node('article',undefined,'recommendation glass'), heading = node('h3'), link = node('a',item.title);
    link.href = url; link.target = '_blank'; link.rel = 'noopener'; heading.append(link);
    const venue = node('a',`${item.venue} · ${item.year}`,'paper-meta');
    if (/^https:\/\/dblp\.org\/rec\/conf\/[a-zA-Z0-9/_.-]+$/.test(item.venue_url || '')) { venue.href = item.venue_url; venue.target = '_blank'; venue.rel = 'noopener'; }
    card.append(venue,heading,node('p',item.summary));
    const add = node('button','Add to library ↗','quiet'); add.onclick = async () => { add.disabled = true; await run('/api/import',{url}); add.disabled = false; }; card.append(add); $('recommendation-list').append(card);
  }
}
$('generate-bento').onclick = () => selected && run(`${paperAPI(selected)}/bento`, {});
$('generate').onclick = () => selected && run(`${paperAPI(selected)}/summary`, {});
$('send').onclick = () => selected && run(`${paperAPI(selected)}/send`, {kind:$('artifact-kind').value, profile:$('profile').value});
function openSettings() {
  $('connection-status').textContent = '';
  const settings = state.settings || {};
  for (const [element, key] of [['endpoint','endpoint'],['model','model'],['kindle-email','kindle_email']]) $(element).value = settings[key] || '';
  for (const [element, key, fallback] of [['max-context-chars','max_context_chars',480000],['max-output-tokens','max_output_tokens',24576],['request-timeout','timeout',150]]) $(element).value = settings[key] ?? fallback;
  $('overview-vision').checked = Boolean(settings.overview_vision);
  $('overview-language').value = settings.overview_language || 'casual'; $('overview-length').value = settings.overview_length || 'medium';
  $('auto-summary').checked = Boolean(settings.auto_summary); $('auto-send').checked = Boolean(settings.auto_send); $('api-key').value = '';
  $('key-status').textContent = settings.has_key || settings.api_key_configured ? 'A key is saved in macOS Keychain. Leave blank to keep it.' : 'Keys are stored in macOS Keychain, never in this page.';
  $('settings-ai-summary').textContent = settings.model ? settings.model + (settings.has_key || settings.api_key_configured ? ' · Key saved' : ' · Add an API key') : 'Set up a provider for AI features';
  $('settings-kindle-summary').textContent = settings.kindle_email || 'Send papers through Mail on this Mac';
  $('settings-error').textContent = ''; $('settings-dialog').showModal();
  $('settings-body').scrollTop = 0;
}
$('settings-open').onclick = openSettings;
$('settings-close').onclick = event => { $('api-key').value = ''; dismissDialog($('settings-dialog'), event); };
$('settings-dialog').addEventListener('close', () => { $('api-key').value = ''; });
$('skip-ai').onclick = $('settings-close').onclick;
$('settings-form').addEventListener('invalid', event => {
  for (let section = event.target.closest('details'); section; section = section.parentElement.closest('details')) section.open = true;
}, true);
$('settings-form').onsubmit = async event => {
  event.preventDefault(); const payload = {endpoint:$('endpoint').value.trim(), model:$('model').value.trim(), kindle_email:$('kindle-email').value.trim(), auto_summary:$('auto-summary').checked, auto_send:$('auto-send').checked};
  payload.max_context_chars = Number($('max-context-chars').value); payload.max_output_tokens = Number($('max-output-tokens').value); payload.timeout = Number($('request-timeout').value);
  payload.overview_vision = $('overview-vision').checked;
  payload.overview_language = $('overview-language').value; payload.overview_length = $('overview-length').value;
  if ($('api-key').value) payload.api_key = $('api-key').value;
  try { await api('/api/settings', payload); $('api-key').value = ''; localStorage.setItem('papers-setup-seen', 'yes'); $('settings-dialog').close(); await refresh(); notice('Settings saved.', true); } catch(error) { $('api-key').value = ''; $('settings-error').textContent = error.message; }
};
function renderContents() {
  const label = {overview:'Overview sections',blog:'Blog sections',paper:'Paper sections'}[activeTab];
  $('contents-title').textContent = label; $('contents-sheet-title').textContent = label;
  $('contents').setAttribute('aria-label', label);
  $('contents').replaceChildren();
  if (activeTab !== 'paper') {
    const target = $(activeTab === 'blog' ? 'overview-text' : 'bento-text');
    for (const [index, heading] of Array.from(target.children).filter(el => ['H2','H3'].includes(el.tagName)).entries()) {
      heading.id = `${activeTab}-section-${index}`;
      const button = node('button', heading.textContent);
      button.onclick = () => { closeMobilePanels(); heading.scrollIntoView({block:'start'}); };
      $('contents').append(button);
    }
  } else {
    for (const chapter of detail?.paper?.chapters || []) {
      const button = node('button',chapter.title || chapter.path);
      button.setAttribute('aria-current',String(currentChapter === chapter.path));
      button.onclick = () => { currentChapter = chapter.path; const url = fileURL(currentChapter); if (url) $('reader').src = url; renderContents(); closeMobilePanels(); window.scrollTo(0,0); };
      $('contents').append(button);
    }
  }
  const hasContents = $('contents').children.length > 0;
  $('reading-companion').hidden = !hasContents;
  $('mobile-contents').hidden = !hasContents;
  $('workspace').classList.toggle('without-contents', !hasContents);
  $('workspace').dataset.view = activeTab;
}
function updateViewActions() {
  const ready = activeTab === 'overview' ? Boolean(detail?.bento) : activeTab === 'blog' && Boolean(detail?.overview);
  $('view-actions').hidden = !ready;
  $('view-actions').open = false;
  $('regenerate-view').textContent = activeTab === 'blog' ? 'Regenerate blog' : 'Regenerate overview';
  $('regenerate-view').disabled = $(activeTab === 'blog' ? 'generate' : 'generate-bento').disabled;
  $('generate-bento').hidden = Boolean(detail?.bento);
  $('generate').hidden = Boolean(detail?.overview);
}
$('regenerate-view').onclick = () => {
  $('view-actions').open = false;
  $(activeTab === 'blog' ? 'generate' : 'generate-bento').click();
};
// Pointer dismissals follow the entrance; keyboard and Escape remain immediate.
function dismissDialog(dialog, event) {
  if (!event?.detail || !dialog.animate) { dialog.close(); return; }
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  dialog.getAnimations().forEach(animation => animation.cancel());
  const frames = reduced ? [{opacity:1},{opacity:0}] :
    [{opacity:1,transform:'none'},{opacity:0,transform:'translateY(12px) scale(.98)'}];
  dialog.animate(frames, {duration:reduced ? 100 : 150, easing:'cubic-bezier(.23,1,.32,1)'})
    .finished.then(() => dialog.close()).catch(() => {});
}
function openFigure(url, alt, caption) {
  $('figure-image').src = url; $('figure-image').alt = alt || 'Paper figure'; $('figure-caption').textContent = caption || '';
  $('figure-dialog').classList.remove('zoomed'); $('figure-zoom').textContent = 'Actual size'; $('figure-dialog').showModal();
}
$('figure-close').onclick = event => dismissDialog($('figure-dialog'), event);
$('figure-zoom').onclick = () => { const zoomed = $('figure-dialog').classList.toggle('zoomed'); $('figure-zoom').textContent = zoomed ? 'Fit to window' : 'Actual size'; };
$('focus-toggle').onclick = () => { document.body.classList.add('is-focused'); $('exit-focus').hidden = false; };
$('exit-focus').onclick = () => { document.body.classList.remove('is-focused'); $('exit-focus').hidden = true; };
function sharedKind() { return activeTab === 'overview' ? 'bento' : activeTab === 'blog' ? 'overview' : 'paper'; }
function updateShareControls() {
  const kind = sharedKind(), generation = kind === 'bento' ? detail?.bento : detail?.overview;
  const ready = kind === 'paper' ? Boolean(detail?.paper) : Boolean(generation);
  $('share-description').textContent = (kind === 'bento' ? 'Visual overview' : kind === 'overview' ? 'Blog' : 'Original paper') + ' · ' + (detail?.paper?.title || '');
  $('share-epub').hidden = kind === 'paper' && detail?.paper?.format === 'pdf';
  $('share-png').hidden = kind !== 'bento';
  for (const id of ['share-epub','share-png','share-pdf']) $(id).disabled = !ready;
  $('share-note').textContent = !ready ? 'Generate this view before exporting it.' : kind === 'overview' ? 'PDF export requires XeLaTeX on this Mac.' : '';
  const source = kind === 'bento' && fileURL(generation?.figures?.[0]?.excalidraw);
  $('share-source').hidden = !source;
  if (source) $('share-excalidraw').href = source; else $('share-excalidraw').removeAttribute('href');
}
$('share-open').onclick = () => {
  $('share-kindle').open = false; $('share-source').open = false;
  $('artifact-kind').value = sharedKind();
  $('kindle-destination').textContent = state.settings?.kindle_email ? 'To ' + state.settings.kindle_email : 'Add your Kindle email in Settings to send.';
  updateShareControls(); updateDeliveryControls(); $('share-dialog').showModal();
};
$('share-close').onclick = event => dismissDialog($('share-dialog'), event);
for (const [id, profile] of [['share-epub','kindle'],['share-png','png'],['share-pdf','pdf']]) {
  $(id).onclick = async () => {
    if (!selected) return;
    const result = await run(`${paperAPI(selected)}/export`, {kind:sharedKind(), profile});
    if (result) $('share-dialog').close();
  };
}
function updateDeliveryControls() {
  const pdf = detail?.paper?.format === 'pdf';
  $('artifact-both').disabled = pdf;
  if (pdf && $('artifact-kind').value === 'both') $('artifact-kind').value = 'paper';
  const sendPDF = pdf && $('artifact-kind').value === 'paper';
  $('profile').disabled = sendPDF;
  $('profile').hidden = sendPDF; $('profile-label').hidden = sendPDF;
  const kind = $('artifact-kind').value;
  $('send').disabled = !state.settings?.kindle_email || (kind === 'bento' && !detail?.bento) || (['overview','both'].includes(kind) && !detail?.overview);
  $('send').textContent = sendPDF ? 'Send PDF to Kindle' : 'Send to Kindle';
  $('kindle-format-note').textContent = sendPDF ? detail.paper.report.warning : 'The selected document will be sent as an EPUB.';
}
$('artifact-kind').onchange = updateDeliveryControls;
let readingSize = localStorage.getItem('papers-text-size') || '16';
if (!['14','16','18','20','22'].includes(readingSize)) readingSize = '16';
let readingTheme = localStorage.getItem('papers-theme') || 'system';
if (!['system','light','dark'].includes(readingTheme)) readingTheme = 'system';
const readingFonts = {georgia:'Georgia,serif', charter:'Charter,Georgia,serif', palatino:'Palatino,"Palatino Linotype",serif', system:'-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif'};
const readingWidths = {wide:'560px',balanced:'720px',narrow:'880px'};
let readingFont = localStorage.getItem('papers-font') || 'palatino';
if (!Object.hasOwn(readingFonts,readingFont)) readingFont = 'palatino';
let readingMargin = localStorage.getItem('papers-margin') || 'narrow';
if (!Object.hasOwn(readingWidths,readingMargin)) readingMargin = 'narrow';
const systemTheme = window.matchMedia('(prefers-color-scheme: dark)');
function applyAppearance() {
  const theme = readingTheme === 'system' ? (systemTheme.matches ? 'dark' : 'light') : readingTheme;
  const themeChanged = document.documentElement.dataset.theme !== theme;
  if (themeChanged) document.documentElement.classList.add('theme-changing');
  document.documentElement.dataset.theme = theme;
  document.documentElement.style.setProperty('--reading-size', readingSize+'px');
  document.documentElement.style.setProperty('--reading-font',readingFonts[readingFont]);
  document.documentElement.style.setProperty('--reading-width',readingWidths[readingMargin]);
  document.documentElement.style.setProperty('--mobile-reading-gutter',{wide:'34px',balanced:'24px',narrow:'16px'}[readingMargin]);
  $('text-size').value = readingSize; $('reading-font').value = readingFont; $('reading-margin').value = readingMargin;
  const label = theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode';
  $('options-theme').textContent = label; $('theme-toggle').setAttribute('aria-label',label); $('theme-toggle').title = label;
  $('theme-toggle').setAttribute('aria-pressed',String(theme === 'dark'));
  $('theme-moon').hidden = theme === 'dark'; $('theme-sun').hidden = theme !== 'dark';
  styleReader();
  if (themeChanged) {
    void document.documentElement.offsetHeight;
    window.requestAnimationFrame(() => document.documentElement.classList.remove('theme-changing'));
  }
}
function styleReader() {
  if (detail?.paper?.format === 'pdf') return;
  // The sandbox remains allow-same-origin only. No paper script is enabled.
  const frame = $('reader'), doc = frame.contentDocument;
  if (!doc?.body || !doc.head) return;
  let style = doc.getElementById('app-reading-style');
  if (!style) { style = doc.createElement('style'); style.id = 'app-reading-style'; doc.head.append(style); }
  const dark = document.documentElement.dataset.theme === 'dark';
  const canvas = window.innerWidth <= 850 ? (dark ? '#000' : '#f5f1e8') : (dark ? '#10120f' : '#fffdf7');
  style.textContent = `html{font-size:${readingSize}px!important;color-scheme:${dark?'dark':'light'};height:auto!important;background:${canvas}!important;color:${dark?'#eeeede':'#272820'}!important}body{font:inherit!important;font-family:${readingFonts[readingFont]}!important;font-size:${readingSize}px!important;line-height:1.85!important;max-width:none!important;margin:0!important;padding:12px 0 25px!important;height:auto!important;min-height:0!important;background:inherit!important;color:inherit!important}h1,h2,h3,h4{font-family:'Avenir Next',sans-serif!important;line-height:1.35!important;font-weight:600!important}h1{font-size:1.5em!important}h2{font-size:1.3em!important}a{color:${dark?'#d1dea8':'#3f573d'}!important}img,svg{max-width:100%;height:auto;object-fit:contain}figure img{max-height:${Math.round(window.innerHeight*.55)}px!important;width:100%!important;cursor:zoom-in;background:#fffdf7;border-radius:10px}figcaption{font:12px/1.65 'Avenir Next',sans-serif!important;margin:12px 0!important}math[display=block]{display:block;overflow-x:auto;max-width:100%;padding:10px 0}table{display:block;overflow:auto;max-width:100%;font-size:.85em}pre{overflow:auto;white-space:pre-wrap}p{margin:0 0 1.2em!important}body>:first-child{margin-top:0!important}*{scrollbar-width:thin;scrollbar-color:${dark?'#34392e':'#dedbcf'} transparent}::-webkit-scrollbar{width:5px;height:5px}::-webkit-scrollbar-thumb{background:${dark?'#34392e':'#dedbcf'};border-radius:8px}`;
  resizeReader();
}
function resizeReader() {
  if (detail?.paper?.format === 'pdf') return;
  const frame = $('reader'); if (frame.contentDocument?.body && !$('paper').hidden) frame.style.height = Math.ceil(frame.contentDocument.body.getBoundingClientRect().height + 20)+'px';
}
$('reader').onload = () => {
  if (detail?.paper?.format === 'pdf') { readerObserver?.disconnect(); return; }
  readerObserver?.disconnect(); styleReader();
  const doc = $('reader').contentDocument; if (!doc?.body) return;
  readerObserver = new ResizeObserver(resizeReader); readerObserver.observe(doc.body);
  const chapter = (detail?.paper?.chapters || []).find(chapter => doc.location.pathname.endsWith('/' + chapter.path));
  if (chapter) { currentChapter = chapter.path; renderContents(); }
  if (doc.location.hash && activeTab === 'paper') {
    requestAnimationFrame(() => {
      const target = doc.getElementById(decodeURIComponent(doc.location.hash.slice(1)));
      if (target) window.scrollTo(0, window.scrollY + $('reader').getBoundingClientRect().top + target.getBoundingClientRect().top - 90);
    });
  }
  for (const image of doc.querySelectorAll('figure img')) {
    image.tabIndex = 0; image.setAttribute('role','button'); image.setAttribute('aria-label','Enlarge figure');
    const open = () => openFigure(image.src,image.alt,image.closest('figure')?.querySelector('figcaption')?.textContent);
    image.onclick = open; image.onkeydown = event => { if (['Enter',' '].includes(event.key)) { event.preventDefault(); open(); } };
  }
};
$('text-size').onchange = () => { readingSize = $('text-size').value; localStorage.setItem('papers-text-size',readingSize); applyAppearance(); };
$('theme-toggle').onclick = () => { readingTheme = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark'; localStorage.setItem('papers-theme',readingTheme); applyAppearance(); };
$('reading-font').onchange = () => { readingFont = $('reading-font').value; localStorage.setItem('papers-font',readingFont); applyAppearance(); };
$('reading-margin').onchange = () => { readingMargin = $('reading-margin').value; localStorage.setItem('papers-margin',readingMargin); applyAppearance(); };
function openSetup() {
  $('setup-connection-status').textContent = '';
  $('settings-dialog').close();
  const settings = state.settings || {};
  $('setup-endpoint').value = settings.model ? settings.endpoint || '' : '';
  $('setup-model').value = settings.model || ''; $('setup-key').value = '';
  $('setup-kindle').value = settings.kindle_email || '';
  $('setup-error').textContent = ''; updateSetupKeyStatus(); $('setup-dialog').showModal();
}
function updateSetupKeyStatus() {
  const sameEndpoint = $('setup-endpoint').value.trim().replace(/\/$/,'') === (state.settings?.endpoint || '').replace(/\/$/,'');
  $('setup-key-status').textContent = sameEndpoint && state.settings?.has_key ? 'Your key is already saved. Leave blank to keep it.' : 'Saved securely in macOS Keychain.';
}
$('setup-open').onclick = openSetup;
$('setup-endpoint').oninput = updateSetupKeyStatus;
$('setup-gemini').onclick = () => {
  $('setup-endpoint').value = 'https://generativelanguage.googleapis.com/v1beta/openai/';
  $('setup-model').value = 'gemini-3.8-flash'; updateSetupKeyStatus(); $('setup-key').focus();
};
$('setup-dialog').addEventListener('close',() => { $('setup-key').value = ''; });
async function completeSetup(takeTour, values = {}) {
  $('setup-save').disabled = true; $('setup-skip').disabled = true;
  try {
    state.settings = await api('/api/settings', {...values,onboarding_complete:true});
    $('setup-key').value = ''; $('setup-dialog').close();
    if (takeTour) await showTourStep(0);
  } catch (error) { $('setup-key').value = ''; $('setup-error').textContent = error.message; }
  finally { $('setup-save').disabled = false; $('setup-skip').disabled = false; }
}
$('setup-form').onsubmit = async event => {
  event.preventDefault();
  const endpoint = $('setup-endpoint').value.trim(), model = $('setup-model').value.trim(), key = $('setup-key').value;
  if ((key || model) && (!endpoint || !model)) { $('setup-error').textContent = 'Add a base URL and model name for your AI connection, or leave the AI fields blank.'; return; }
  const values = {kindle_email:$('setup-kindle').value.trim()};
  if (endpoint) values.endpoint = endpoint;
  if (model) values.model = model;
  if (key) values.api_key = key;
  await completeSetup(true,values);
};
$('setup-skip').onclick = () => completeSetup(true);
$('setup-close').onclick = () => completeSetup(false);
$('setup-dialog').addEventListener('cancel',event => { event.preventDefault(); completeSetup(false); });
function setReadingPreferences(expanded) {
  $('reader-launcher').setAttribute('aria-expanded', String(expanded));
  if (expanded) $('reading-preferences-dialog').showModal();
  else $('reading-preferences-dialog').close();
}
$('reader-launcher').onclick = () => setReadingPreferences(true);
$('reading-preferences-close').onclick = event => dismissDialog($('reading-preferences-dialog'), event);
$('reading-preferences-dialog').addEventListener('close', () => $('reader-launcher').setAttribute('aria-expanded','false'));
async function testConnection(setup) {
  const button = $(setup ? 'setup-test-connection' : 'test-connection');
  const status = $(setup ? 'setup-connection-status' : 'connection-status');
  const values = () => ({endpoint:$(setup ? 'setup-endpoint':'endpoint').value.trim(),model:$(setup ? 'setup-model':'model').value.trim(),api_key:$(setup ? 'setup-key':'api-key').value.trim()});
  const payload = values();
  button.disabled = true; status.textContent = 'Testing connection…'; status.dataset.state = 'testing';
  try {
    const result = await api('/api/test-connection',payload);
    const unchanged = JSON.stringify(values()) === JSON.stringify(payload);
    status.textContent = unchanged ? result.message : 'Connection fields changed. Test again.'; status.dataset.state = unchanged ? 'success':'changed';
  } catch (error) { status.textContent = error.message; status.dataset.state = 'error'; }
  finally { button.disabled = false; }
}
$('test-connection').onclick = () => testConnection(false);
$('setup-test-connection').onclick = () => testConnection(true);
for (const [prefix,fields,status] of [['',['endpoint','model','api-key'],'connection-status'],['setup-',['endpoint','model','key'],'setup-connection-status']]) {
  for (const field of fields) $(prefix+field).addEventListener('input',() => { $(status).textContent = ''; });
}
function closeMobilePanels() {
  document.body.classList.remove('notifications-open'); $('notifications-toggle').setAttribute('aria-expanded','false');
  $('contents-sheet').close();
  setReadingPreferences(false);
  $('mobile-contents').setAttribute('aria-expanded','false');
}
$('mobile-contents').onclick = () => {
  closeMobilePanels();
  $('contents-sheet-body').append($('reading-companion'));
  $('contents-sheet').showModal();
  $('mobile-contents').setAttribute('aria-expanded','true');
};
$('contents-sheet-close').onclick = event => dismissDialog($('contents-sheet'), event);
$('contents-sheet').addEventListener('close',() => {
  document.querySelector('.study-layout').append($('reading-companion'));
  $('mobile-contents').setAttribute('aria-expanded','false');
});
$('mobile-home').onclick = () => tourStep !== null ? finishTour() : goHome();
$('mobile-library').onclick = () => $('library-open').onclick();
function openPaperOptions() {
  closeMobilePanels();
  $('options-title').textContent = detail?.paper.title || '';
  $('options-authors').textContent = $('paper-authors').textContent;
  $('options-pdf').href = fileURL('original.pdf');
  $('paper-options-dialog').showModal();
}
$('mobile-more').onclick = openPaperOptions;
$('paper-details').onclick = openPaperOptions;
$('paper-options-close').onclick = event => dismissDialog($('paper-options-dialog'), event);
$('options-library').onclick = () => { $('paper-options-dialog').close(); $('library-open').onclick(); };
$('options-settings').onclick = () => { $('paper-options-dialog').close(); openSettings(); };
$('options-theme').onclick = () => $('theme-toggle').onclick();
window.matchMedia('(max-width:850px)').addEventListener('change',closeMobilePanels);
const tourSteps = [
  ['Start with a paper','Paste an arXiv or alphaXiv link here. Your papers stay in your library on this Mac.','.home-bar'],
  ['Your papers, together','Find saved papers here. Open “Attention Is All You Need” to try the reader.','#tour-paper'],
  ['Make reading comfortable','Use Paper for the text and Overview for an explanation. Change font, size, and margins below, or open Share to export or send a saved paper to Kindle.','#reading-bar'],
  ['You’re ready','Add your first paper whenever you like. Settings holds your connections and this tour.','#settings-open']
];
async function showTourStep(index) {
  if (index >= tourSteps.length) { finishTour(); return; }
  tourStep = index;
  document.body.append($('tour'));
  $('settings-dialog').close(); $('share-dialog').close();
  for (const element of document.querySelectorAll('.tour-target')) element.classList.remove('tour-target');
  if (index === 0 || index === 3) goHome();
  if (index === 1) {
    $('search').value = ''; showLibrary();
    if (!state.papers.some(p => p.id === TOUR_ID)) {
      $('tour-title').textContent = 'Adding the paper'; $('tour-text').textContent = 'Downloading and preparing the complete Attention Is All You Need paper. You can keep it in your library.';
      $('tour-count').textContent = '2 of 4'; $('tour-next').disabled = true; $('tour').hidden = false;
      $('tour').style.left = '12px'; $('tour').style.top = '160px';
      try {
        const result = await api('/api/tutorial', {});
        if (result.job) {
          retries.set(result.job.id,{path:'/api/tutorial',payload:{}});
          let job = result.job;
          while (!terminal.has(job.state) && tourStep === index) {
            await new Promise(resolve => setTimeout(resolve,1000));
            await refresh(); job = state.jobs.find(j => j.id === job.id) || job;
          }
          if (tourStep !== index) return;
          if (job.state !== 'ready') throw new Error(job.error || 'Paper import stopped. Retry the tour to try again.');
        }
        await refresh();
      } catch (error) { notice(error.message); finishTour(); return; }
      finally { $('tour-next').disabled = false; }
    }
    if (tourStep !== index) return;
    renderLibrary();
  }
  if (index === 2) { await openPaper(TOUR_ID); if (tourStep !== index) return; switchTab('paper'); setReadingPreferences(true); window.scrollTo(0,0); }
  const [title,text,selector] = tourSteps[index];
  $('tour-count').textContent = `${index+1} of ${tourSteps.length}`;
  $('tour-title').textContent = title; $('tour-text').textContent = text;
  $('tour-next').textContent = index === tourSteps.length-1 ? 'Done' : index === 1 ? 'Open paper' : 'Next';
  $('tour-back').hidden = index === 0; $('tour').hidden = false;
  document.querySelector(selector)?.classList.add('tour-target');
  requestAnimationFrame(() => {
    positionTour(); $('tour-title').focus({preventScroll:true});
    if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      $('tour').getAnimations().forEach(animation => animation.cancel());
      $('tour').animate([{opacity:0,filter:'blur(4px)',transform:'translateY(10px) scale(.98)'},{opacity:1,filter:'blur(0px)',transform:'translateY(0) scale(1)'}],{duration:280,easing:'cubic-bezier(.22,1,.36,1)'});
      $('tour').querySelector('path').animate([{strokeDasharray:45,strokeDashoffset:45},{strokeDasharray:45,strokeDashoffset:0}],{duration:420,easing:'ease-out'});
    }
  });
}
function positionTour() {
  if (tourStep === null) return;
  const target = document.querySelector(tourSteps[tourStep][2]); if (!target) return;
  const rect = target.getBoundingClientRect(), panel = $('tour');
  const width = panel.offsetWidth, height = panel.offsetHeight;
  const left = Math.max(12,Math.min(window.innerWidth-width-12,rect.left+rect.width/2-width/2));
  const below = rect.bottom + height + 30 < window.innerHeight;
  panel.dataset.side = below ? 'below' : 'above';
  panel.style.left = left+'px';
  panel.style.top = Math.max(80,Math.min(window.innerHeight-height-12,below ? rect.bottom+25 : rect.top-height-25))+'px';
  panel.style.setProperty('--arrow-x',Math.max(22,Math.min(width-22,rect.left+rect.width/2-left))+'px');
}
function finishTour() {
  tourStep = null; $('tour').hidden = true; document.body.append($('tour'));
  for (const element of document.querySelectorAll('.tour-target')) element.classList.remove('tour-target');
  renderLibrary(); goHome(); $('home-url').focus({preventScroll:true});
}
$('tour-open').onclick = () => showTourStep(0);
$('tour-next').onclick = () => showTourStep(tourStep+1);
$('tour-back').onclick = () => showTourStep(Math.max(0,tourStep-1));
$('tour-skip').onclick = finishTour;
document.addEventListener('keydown',event => {
  if (event.key !== 'Escape' || event.defaultPrevented || document.querySelector('dialog[open]')) return;
  setReadingPreferences(false); closeMobilePanels();
  if (tourStep !== null) finishTour();
});
window.addEventListener('resize',positionTour);
window.addEventListener('scroll',positionTour,{passive:true});

systemTheme.addEventListener('change',applyAppearance);
window.addEventListener('resize',styleReader);
applyAppearance();
let pollTimer;
function schedulePoll() {
  clearTimeout(pollTimer);
  const active = state.jobs.some(job => !terminal.has(job.state));
  pollTimer = setTimeout(poll, document.hidden ? 30000 : active ? 2000 : 10000);
}
async function poll() { await refresh(); schedulePoll(); }
document.addEventListener('visibilitychange', () => { if (!document.hidden) poll(); else schedulePoll(); });
(async () => {
  await refresh();
  const example = state.papers.find(paper => paper.id === '1706.03762v7');
  if (example) await openPaper(example.id);
  else if (stateInitialized && !state.settings.onboarding_complete && !state.papers.length && !state.settings.model && !state.settings.kindle_email) openSetup();
  schedulePoll();
})();

$('view-actions').onkeydown = event => { if (event.key === 'Escape') { $('view-actions').open = false; $('view-actions').querySelector('summary').focus(); event.stopPropagation(); } };
document.addEventListener('click', event => {
  for (const actions of document.querySelectorAll('.library-actions[open], .view-actions[open]')) {
    if (!actions.contains(event.target)) actions.open = false;
  }
  const summary = event.target.closest('summary');
  if (!event.detail || !summary || summary.parentElement.open) return;
  const disclosure = summary.parentElement;
  if (!disclosure.matches('.share-sheet details, .settings-disclosure, .bento-transcript')) return;
  window.requestAnimationFrame(() => {
    if (!disclosure.open) return;
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    for (const child of disclosure.children) {
      if (child === summary || !child.animate) continue;
      child.getAnimations().forEach(animation => animation.cancel());
      child.animate([{opacity:0},{opacity:1}], {duration:reduced ? 100 : 160, easing:'cubic-bezier(.23,1,.32,1)'});
    }
  });
});
