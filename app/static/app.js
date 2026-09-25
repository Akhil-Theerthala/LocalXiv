/* No provider keys are retained by the browser. Paper and model text are always text nodes. */
import {HOME, applyView} from './view.js';
import {createNode, expireToast, JobNotices, TERMINAL, renderProse, renderLibrary as drawLibrary, renderRecommendations as drawRecommendations, renderContents as drawContents, cleanOverviewCitations, annotateFigure} from './render.js';
import {readPreferences, resolveTheme, rootProperties, readerStylesheet, READING_FONTS} from './appearance.js';
const $ = id => document.getElementById(id);
const fragment = new URLSearchParams(location.hash.slice(1));
let token = fragment.get('token') || localStorage.getItem('papers-session') || '';
if (fragment.has('token')) { localStorage.setItem('papers-session', token); history.replaceState(null, '', location.pathname); }
let state = {papers: [], jobs: [], settings: {}}, selected = null, detail = null, stateSignature = '', jobSignature = '', detailRequest = 0;
const retries = new Map();
const completedImports = new Set();
const downloadedExports = new Set();
let recommendationsSignature = '', stateInitialized = false;
let activeTab = 'overview', overviewSignature = '', noticeTimer;
let readerObserver, tourStep = null, currentChapter = '';
let view = {...HOME};
function setView(patch) { view = {...view, ...patch}; applyView(document, view); }
const TOUR_ID = '1706.03762v7';
const PROVIDER_PRESETS = Object.freeze({
  openai:{endpoint:'https://api.openai.com/v1',limits:'65,536 output tokens and 10 minutes per request'},
  openrouter:{endpoint:'https://openrouter.ai/api/v1',limits:'96,000 output tokens and 15 minutes per request'},
  deepseek:{endpoint:'https://api.deepseek.com',limits:'64,000 output tokens and 15 minutes per request'},
  gemini:{endpoint:'https://generativelanguage.googleapis.com/v1beta/openai/',limits:'65,536 output tokens and 10 minutes per request'},
});
const CUSTOM_PROVIDER_LIMITS = '64,000 output tokens and 15 minutes per request';
const node = createNode(document);
const timing = {setTimeout: window.setTimeout.bind(window), reducedMotion: () => window.matchMedia('(prefers-reduced-motion: reduce)').matches};
const paperAPI = id => `/api/papers/${encodeURIComponent(id)}`;
const jobNotices = new JobNotices({target: $('jobs'), toggle: $('notifications-toggle'), node, run, paperAPI, downloadLink, retries, clearTimeout: window.clearTimeout.bind(window), ...timing});
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
  if (autoDismiss) noticeTimer = expireToast($('notice'), () => { $('notice').hidden = true; }, timing);
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
  drawLibrary($('paper-list'), state.papers, {node, query: $('search').value, selected, tourPaperId: TOUR_ID, tourFirst: tourStep !== null,
    onOpen: paper => tourStep === 1 && paper.id === TOUR_ID ? showTourStep(2) : openPaper(paper.id),
    onRemove: (paper, summary) => {
      $('remove-paper-dialog').dataset.paperId = paper.id;
      $('remove-paper-name').textContent = paper.title || paper.id;
      $('remove-paper-error').textContent = '';
      $('remove-paper-dialog').addEventListener('close', () => { if (summary.isConnected) summary.focus(); }, {once: true});
      $('remove-paper-dialog').showModal();
      $('remove-paper-cancel').focus();
    }});
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
    svg.setAttribute('role', 'img'); svg.setAttribute('aria-label', figure.alt || figure.caption || 'Paper explanation');
    annotateFigure(svg.querySelectorAll('[data-node]'), figure.components, {svgNode: tag => document.createElementNS(SVG_NS, tag), onPassage: openPassage});
    container.replaceChildren(svg); container.dataset.theme = theme; container.removeAttribute('aria-busy');
  } catch (error) {
    container.replaceChildren(node('p', 'Figure unavailable. Regenerate this view to restore it.', 'muted'));
    container.removeAttribute('aria-busy');
  }
}
function openPassage(id) {
  const passage = (detail?.overview?.evidence || []).find(item => item.id === id);
  const url = passage && fileURL(passage.href);
  if (!url) return;
  $('reader').src = url; switchTab('paper');
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
  openSource: href => { $('reader').src = fileURL(href); switchTab('paper'); }});
async function openPaper(id) {
  const request = ++detailRequest;
  try {
    const result = await api(paperAPI(id)); if (request !== detailRequest) return;
    const changedPaper = selected !== id;
    const documentChanged = selected === id && detail?.paper?.document_digest !== result.paper.document_digest;
    selected = id; detail = result; const paper = result.paper;
    setView({page: 'reading'});
    $('paper-id').textContent = paper.arxiv_id || paper.id;
    $('paper-title').textContent = paper.title || paper.id;
    $('paper-authors').textContent = Array.isArray(paper.authors) ? paper.authors.join(', ') : paper.authors || '';
    $('paper-authors').hidden = $('paper-authors').textContent.length > 140;
    const nextOverview = JSON.stringify([id, result.blog?.text, result.blog?.figures, result.overview]);
    if (nextOverview !== overviewSignature) {
      overviewSignature = nextOverview;
      prose($('blog-text'), cleanOverviewCitations(result.blog?.text), [], result.blog?.figures || []);
      prose($('overview-text'), result.overview?.text, [], result.overview?.figures || [], {inlineFigure});
      swapFigureSources(document.documentElement.dataset.theme);
    }
    $('blog-note').textContent = result.blog ? '' : 'Generate a blog for a longer explanation of this paper.';
    $('blog-note').hidden = Boolean(result.blog);
    $('generate-blog').textContent = result.blog ? 'Regenerate blog' : 'Generate blog';
    $('overview-note').textContent = result.overview ? '' : 'Generate a visual overview, or open Paper to start reading.';
    $('overview-note').hidden = Boolean(result.overview);
    $('generate-overview').textContent = result.overview ? 'Regenerate overview' : 'Generate overview';
    $('generate-overview').disabled = !paper.passages?.length;

    const pdf = paper.format === 'pdf';
    $('fallback-notice').hidden = !pdf;
    $('fallback-notice').textContent = pdf ? paper.report.warning : '';
    $('generate-blog').disabled = pdf && !paper.passages?.length;
    if (pdf && paper.report.text_warning && !result.blog) $('blog-note').textContent = paper.report.text_warning;
    $('blog-sources').replaceChildren();
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
    if (!stateInitialized) { for (const job of next.jobs) if (job.kind === 'import' && TERMINAL.has(job.state)) completedImports.add(job.id); stateInitialized = true; }
    const papers = JSON.stringify(next.papers), jobs = JSON.stringify(next.jobs);
    if (papers !== stateSignature) { stateSignature = papers; renderLibrary(); }
    if (jobs !== jobSignature) {
      jobSignature = jobs; jobNotices.render(state.jobs, state.papers);
      downloadFinishedExports(next.jobs);
      const imported = next.jobs.find(job => job.kind === 'import' && ['ready','completed','succeeded'].includes(job.state) && job.result?.paper_id && next.papers.some(p => p.id === job.result.paper_id) && !completedImports.has(job.id));
      for (const job of next.jobs) if (job.kind === 'import' && TERMINAL.has(job.state)) completedImports.add(job.id);
      if (tourStep === null) { if (imported) await openPaper(imported.result.paper_id); else if (selected) await openPaper(selected); }
    }
    const missing = Object.entries(next.dependencies || {}).filter(([, available]) => !available).map(([name]) => name);
    $('dependencies').textContent = missing.length ? `Not installed: ${missing.join(', ')}. Install these tools before converting papers.` : 'All conversion tools are available.';
  } catch (error) { notice(error.message); }
}
$('search').oninput = renderLibrary;
function goHome() { setReadingPreferences(false); ++detailRequest; selected = null; detail = null; closeMobilePanels(); setView({page: 'home', focused: false}); window.scrollTo(0,0); }
$('home-open').onclick = event => { event.preventDefault(); if (tourStep !== null) finishTour(); else goHome(); };
$('reader-home').onclick = () => tourStep !== null ? finishTour() : goHome();
function showLibrary() { goHome(); setView({page: 'library'}); renderLibrary(); $('library-title').focus({preventScroll:true}); }
$('library-open').onclick = () => { if (tourStep !== null) finishTour(); showLibrary(); };
$('library-add').onclick = () => { goHome(); $('home-url').focus(); };
$('home-form').onsubmit = async event => { event.preventDefault(); const result = await run('/api/import', {url:$('home-url').value.trim()}); if (result) $('home-url').value = ''; };
function renderRecommendations() {
  const items = state.recommendations?.items || [], signature = JSON.stringify(items);
  $('recommendations').hidden = !items.length;
  if (signature === recommendationsSignature) return;
  recommendationsSignature = signature;
  drawRecommendations($('recommendation-list'), items, {node, onAdd: async (url, button) => { button.disabled = true; await run('/api/import', {url}); button.disabled = false; }});
}
$('generate-overview').onclick = () => selected && run(`${paperAPI(selected)}/overview`, {});
$('generate-blog').onclick = () => selected && run(`${paperAPI(selected)}/blog`, {});
$('send').onclick = () => selected && run(`${paperAPI(selected)}/send`, {kind:$('artifact-kind').value, profile:$('profile').value});
function normalizedEndpoint(endpoint) { return (endpoint || '').trim().replace(/\/+$/,''); }
function providerControls(setup) {
  const prefix = setup ? 'setup-' : '';
  return {preset:$(prefix+'provider-preset'), endpoint:$(prefix+'endpoint'), custom:$(prefix+'custom-endpoint'), limits:$(prefix+'provider-limits')};
}
function renderProvider(setup, endpoint) {
  const fields = providerControls(setup), normalized = normalizedEndpoint(endpoint);
  const match = Object.entries(PROVIDER_PRESETS).find(([,value]) => normalizedEndpoint(value.endpoint) === normalized);
  fields.preset.value = match ? match[0] : normalized ? 'custom' : 'openai';
  fields.endpoint.value = match ? match[1].endpoint : normalized ? endpoint : PROVIDER_PRESETS.openai.endpoint;
  fields.endpoint.dataset.provider = fields.preset.value;
  if (fields.preset.value === 'custom') fields.endpoint.dataset.customValue = fields.endpoint.value;
  updateProviderDetails(setup);
}
function updateProviderDetails(setup) {
  const fields = providerControls(setup), preset = PROVIDER_PRESETS[fields.preset.value];
  fields.custom.hidden = Boolean(preset);
  fields.limits.textContent = 'Automatic limit: ' + (preset?.limits || CUSTOM_PROVIDER_LIMITS) + '. Paper input is not capped.';
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
function connectionEndpoint(setup) { return providerControls(setup).endpoint.value.trim(); }
function openSettings() {
  $('connection-status').textContent = '';
  const settings = state.settings || {};
  renderProvider(false, settings.endpoint || PROVIDER_PRESETS.openai.endpoint);
  for (const [element, key] of [['model','model'],['kindle-email','kindle_email']]) $(element).value = settings[key] || '';
  $('overview-vision').checked = Boolean(settings.overview_vision);
  $('overview-reasoning').value = {true: 'low', false: 'off'}[settings.overview_reasoning] || settings.overview_reasoning || 'low';
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
  event.preventDefault(); const payload = {endpoint:connectionEndpoint(false), model:$('model').value.trim(), kindle_email:$('kindle-email').value.trim(), auto_summary:$('auto-summary').checked, auto_send:$('auto-send').checked};
  payload.overview_vision = $('overview-vision').checked; payload.overview_reasoning = $('overview-reasoning').value;
  payload.overview_language = $('overview-language').value; payload.overview_length = $('overview-length').value;
  if ($('api-key').value) payload.api_key = $('api-key').value;
  try { await api('/api/settings', payload); $('api-key').value = ''; localStorage.setItem('papers-setup-seen', 'yes'); $('settings-dialog').close(); await refresh(); notice('Settings saved.', true); } catch(error) { $('api-key').value = ''; $('settings-error').textContent = error.message; }
};
function renderContents() {
  const label = {overview: 'Overview sections', blog: 'Blog sections', paper: 'Paper sections'}[activeTab];
  $('contents-title').textContent = label; $('contents-sheet-title').textContent = label;
  $('contents').setAttribute('aria-label', label);
  let entries;
  if (activeTab !== 'paper') {
    const target = $(activeTab === 'blog' ? 'blog-text' : 'overview-text');
    entries = Array.from(target.children).filter(el => ['H2', 'H3'].includes(el.tagName)).map((heading, index) => {
      heading.id = `${activeTab}-section-${index}`;
      return {label: heading.textContent, current: false, onSelect: () => { closeMobilePanels(); heading.scrollIntoView({block: 'start'}); }};
    });
  } else {
    entries = (detail?.paper?.chapters || []).map(chapter => ({label: chapter.title || chapter.path, current: currentChapter === chapter.path,
      onSelect: () => { currentChapter = chapter.path; const url = fileURL(currentChapter); if (url) $('reader').src = url; renderContents(); closeMobilePanels(); window.scrollTo(0, 0); }}));
  }
  drawContents($('contents'), entries, {node});
  setView({tab: activeTab, contents: entries.length > 0});
}
// What made a saved Overview or Blog: its model, reasoning effort, requests, tokens, time, and
// date. An older record lacks some of these, and the line names only what the record holds.
function generationDetails(generation) {
  const record = generation?.provenance || {};
  const usage = Array.isArray(record.usage) ? record.usage : [];
  const parts = record.model ? [record.model] : [];
  const options = usage.find(event => event.options)?.options;
  if (options) parts.push(options.reasoning ? options.reasoning[0].toUpperCase() + options.reasoning.slice(1) + ' reasoning' : 'No reasoning');
  const tokens = usage.reduce((sum, event) => sum + ((event.usage || event).total_tokens || 0), 0);
  if (usage.length) parts.push(usage.length + (usage.length === 1 ? ' request' : ' requests'));
  if (tokens) parts.push(Math.max(1, Math.round(tokens / 1000)) + 'k tokens');
  const made = Date.parse(record.created_at), started = Math.min(...usage.map(event => Date.parse(event.started_at)).filter(Number.isFinite));
  if (Number.isFinite(made) && Number.isFinite(started)) parts.push(Math.max(1, Math.round((made - started) / 60000)) + ' min');
  if (Number.isFinite(made)) parts.push(new Date(made).toLocaleDateString(undefined, {day: 'numeric', month: 'short', year: 'numeric'}));
  return parts.join(' · ');
}
function updateViewActions() {
  const ready = activeTab === 'overview' ? Boolean(detail?.overview) : activeTab === 'blog' && Boolean(detail?.blog);
  $('view-details').textContent = ready ? generationDetails(activeTab === 'blog' ? detail.blog : detail.overview) : '';
  $('view-details').hidden = !$('view-details').textContent;
  $('view-actions').hidden = !ready;
  $('view-actions').open = false;
  $('regenerate-view').textContent = activeTab === 'blog' ? 'Regenerate blog' : 'Regenerate overview';
  $('regenerate-view').disabled = $(activeTab === 'blog' ? 'generate-blog' : 'generate-overview').disabled;
  $('generate-overview').hidden = Boolean(detail?.overview);
  $('generate-blog').hidden = Boolean(detail?.blog);
}
$('regenerate-view').onclick = () => {
  $('view-actions').open = false;
  $(activeTab === 'blog' ? 'generate-blog' : 'generate-overview').click();
};
// Pointer dismissals follow the entrance; keyboard and Escape remain immediate.
function dismissDialog(dialog, event) {
  if (!event?.detail || !dialog.animate) { dialog.close(); return; }
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  dialog.getAnimations().forEach(animation => animation.cancel());
  const frames = reduced ? [{opacity:1},{opacity:0}] :
    [{opacity:1,transform:'none'},{opacity:0,transform:'translateY(12px) scale(.98)'}];
  dialog.animate(frames, {duration:reduced ? 100 : motion().quick, easing:motion().easing})
    .finished.then(() => dialog.close()).catch(() => {});
}
let figureView = null;
let figureDrag = null;
function figurePanels(value) {
  if (!Array.isArray(value)) return [];
  return value.filter(panel => panel && typeof panel.id === 'string' && [panel.x, panel.y, panel.width, panel.height]
    .every(number => typeof number === 'number' && Number.isFinite(number)) && panel.width > 0 && panel.height > 0);
}
function figureSize(dimensions, image) {
  const width = dimensions && dimensions.width > 0 ? dimensions.width : (image.naturalWidth || 960);
  const height = dimensions && dimensions.height > 0 ? dimensions.height : (image.naturalHeight || 640);
  return {width, height};
}
function figureFitUnit() {
  const stage = $('figure-canvas'), image = $('figure-image');
  if (!figureView) return 1;
  const box = stage.getBoundingClientRect();
  const size = figureSize(figureView.dimensions, image);
  const available = {width: Math.max(120, box.width - 16), height: Math.max(120, box.height - 16)};
  return Math.max(0.05, Math.min(available.width / size.width, available.height / size.height));
}
function applyFigureUnit(unit, {keepCentre = true} = {}) {
  const stage = $('figure-canvas'), image = $('figure-image');
  if (!figureView) return;
  const size = figureSize(figureView.dimensions, image);
  const centre = {x: stage.scrollLeft + stage.clientWidth / 2, y: stage.scrollTop + stage.clientHeight / 2};
  const previous = figureView.unit || figureFitUnit();
  const chosen = Math.max(0.02, Math.min(8, unit));
  figureView.unit = chosen;
  figureView.fit = Math.abs(chosen - figureFitUnit()) < 1e-6;
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
  const stage = $('figure-canvas');
  const box = stage.getBoundingClientRect();
  const unit = Math.max(0.05, Math.min(4, Math.min((box.width - 48) / panel.width, (box.height - 48) / panel.height)));
  applyFigureUnit(unit, {keepCentre: false});
  stage.scrollLeft = Math.max(0, (panel.x - 24) * unit);
  stage.scrollTop = Math.max(0, (panel.y - 24) * unit);
  stage.focus({preventScroll: true});
}
function figurePoint(event) {
  const image = $('figure-image'), box = image.getBoundingClientRect();
  if (!figureView || !box.width || !box.height) return null;
  if (event.clientX < box.left || event.clientX > box.right
      || event.clientY < box.top || event.clientY > box.bottom) return null;
  const size = figureSize(figureView.dimensions, image);
  return {x: (event.clientX - box.left) / box.width * size.width,
          y: (event.clientY - box.top) / box.height * size.height};
}
function figurePanelAt(point) {
  return point && figureView ? figureView.panels.find(panel =>
    point.x >= panel.x && point.x <= panel.x + panel.width
    && point.y >= panel.y && point.y <= panel.y + panel.height) : null;
}
function figurePanelLabel(panel, index) { return 'Panel ' + (index + 1) + (panel.title ? ': ' + panel.title : ''); }
function openFigure(url, alt, caption, panels, dimensions) {
  const list = figurePanels(panels);
  figureView = {url, alt, caption, panels: list, dimensions: dimensions || null, unit: 0, fit: true};
  const image = $('figure-image');
  image.src = url; image.alt = alt || 'Paper figure'; image.removeAttribute('style');
  $('figure-caption').textContent = caption || '';
  const targets = $('figure-panels'); targets.replaceChildren(); targets.hidden = !list.length;
  list.forEach((panel, index) => {
    const button = node('button', figurePanelLabel(panel, index), 'quiet');
    button.type = 'button'; button.setAttribute('aria-label', 'Focus ' + figurePanelLabel(panel, index));
    button.onclick = () => focusFigurePanel(panel);
    targets.append(button);
  });
  const transcripts = list.filter(panel => panel.text);
  const details = $('figure-transcript'); details.hidden = !transcripts.length;
  const body = $('figure-transcript-body'); body.replaceChildren();
  if (transcripts.length) {
    const items = node('ol');
    transcripts.forEach((panel, index) => {
      const entry = node('li');
      entry.append(node('strong', figurePanelLabel(panel, index)), node('p', panel.text));
      items.append(entry);
    });
    body.append(items); details.open = false;
  }
  const reset = () => { const stage = $('figure-canvas'); stage.scrollLeft = 0; stage.scrollTop = 0; applyFigureUnit(figureFitUnit(), {keepCentre: false}); };
  reset();
  image.onload = reset;
  $('figure-dialog').showModal();
  $('figure-canvas').focus({preventScroll: true});
}
$('figure-close').onclick = event => dismissDialog($('figure-dialog'), event);
$('figure-fit').onclick = () => applyFigureUnit(figureFitUnit());
$('figure-zoom').onclick = () => applyFigureUnit(1);
$('figure-zoom-in').onclick = () => applyFigureUnit((figureView?.unit || 1) * 1.25);
$('figure-zoom-out').onclick = () => applyFigureUnit((figureView?.unit || 1) * 0.8);
$('figure-image').onclick = event => { const panel = figurePanelAt(figurePoint(event)); if (panel) focusFigurePanel(panel); };
$('figure-canvas').onpointerdown = event => {
  if (event.button !== 0 || !figureView) return;
  const stage = $('figure-canvas');
  figureDrag = {x: event.clientX, y: event.clientY, left: stage.scrollLeft, top: stage.scrollTop, moved: false};
  if (stage.setPointerCapture) { try { stage.setPointerCapture(event.pointerId); } catch (_) {} }
};
$('figure-canvas').onpointermove = event => {
  if (!figureDrag) return;
  const dx = event.clientX - figureDrag.x, dy = event.clientY - figureDrag.y;
  if (Math.abs(dx) + Math.abs(dy) > 4) figureDrag.moved = true;
  if (!figureDrag.moved) return;
  const stage = $('figure-canvas');
  stage.scrollLeft = figureDrag.left - dx; stage.scrollTop = figureDrag.top - dy;
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
  if (event.key === '+' || event.key === '=') { applyFigureUnit((figureView.unit || 1) * 1.25); }
  else if (event.key === '-') { applyFigureUnit((figureView.unit || 1) * 0.8); }
  else if (event.key === '0') { applyFigureUnit(figureFitUnit()); }
  else if (event.key === 'ArrowLeft') { stage.scrollLeft -= 48; }
  else if (event.key === 'ArrowRight') { stage.scrollLeft += 48; }
  else if (event.key === 'ArrowUp') { stage.scrollTop -= 48; }
  else if (event.key === 'ArrowDown') { stage.scrollTop += 48; }
  else if (/^[1-9]$/.test(event.key)) { focusFigurePanel(figureView.panels[Number(event.key) - 1]); }
  else return;
  event.preventDefault();
};
window.addEventListener('resize', () => { if (figureView && figureView.fit && $('figure-dialog').open) applyFigureUnit(figureFitUnit(), {keepCentre: false}); });
$('focus-toggle').onclick = () => setView({focused: true});
$('exit-focus').onclick = () => setView({focused: false});
function sharedKind() { return activeTab === 'overview' ? 'overview' : activeTab === 'blog' ? 'blog' : 'paper'; }
function updateShareControls() {
  const kind = sharedKind(), generation = kind === 'overview' ? detail?.overview : detail?.blog;
  const ready = kind === 'paper' ? Boolean(detail?.paper) : Boolean(generation);
  $('share-description').textContent = (kind === 'overview' ? 'Visual overview' : kind === 'blog' ? 'Blog' : 'Original paper') + ' · ' + (detail?.paper?.title || '');
  $('share-epub').hidden = kind === 'paper' && detail?.paper?.format === 'pdf';
  $('share-png').hidden = kind !== 'overview';
  for (const id of ['share-epub','share-png','share-pdf']) $(id).disabled = !ready;
  $('share-note').textContent = !ready ? 'Generate this view before exporting it.' : kind === 'overview' ? 'PDF export requires XeLaTeX on this Mac.' : '';
  const figure = generation?.figures?.[0];
  const source = fileURL(figure?.svg_source);
  $('share-source').hidden = !source;
  if (source) $('share-svg').href = source; else $('share-svg').removeAttribute('href');
  if (ready && figure && !source) $('share-note').textContent = 'Regenerate this ' + (kind === 'overview' ? 'Overview' : 'Blog') + ' to export its editable source.';
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
  $('send').disabled = !state.settings?.kindle_email || (kind === 'overview' && !detail?.overview) || (['blog','both'].includes(kind) && !detail?.blog);
  $('send').textContent = sendPDF ? 'Send PDF to Kindle' : 'Send to Kindle';
  $('kindle-format-note').textContent = sendPDF ? detail.paper.report.warning : 'The selected document will be sent as an EPUB.';
}
$('artifact-kind').onchange = updateDeliveryControls;
const preferences = readPreferences(localStorage);
const systemTheme = window.matchMedia('(prefers-color-scheme: dark)');
const cssToken = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const motion = () => ({easing: cssToken('--ease-out'), quick: parseFloat(cssToken('--duration-quick')), slow: parseFloat(cssToken('--duration-slow'))});
function swapFigureSources(theme) {
  for (const img of document.querySelectorAll('img[data-dark-src]')) {
    const next = theme === 'dark' ? img.dataset.darkSrc : img.dataset.lightSrc;
    if (img.getAttribute('src') !== next) img.src = next;
  }
  for (const container of document.querySelectorAll('.figure-inline[data-dark-src]')) {
    if (container.dataset.theme !== theme && inlineFigures.has(container)) inlineFigure(container, inlineFigures.get(container));
  }
}
function applyAppearance() {
  const theme = resolveTheme(preferences.theme, systemTheme.matches);
  const themeChanged = document.documentElement.dataset.theme !== theme;
  if (themeChanged) document.documentElement.classList.add('theme-changing');
  document.documentElement.dataset.theme = theme;
  for (const [name, value] of Object.entries(rootProperties(preferences))) document.documentElement.style.setProperty(name, value);
  $('text-size').value = preferences.size; $('reading-font').value = preferences.font; $('reading-margin').value = preferences.margin;
  const label = theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode';
  $('options-theme').textContent = label; $('theme-toggle').setAttribute('aria-label', label); $('theme-toggle').title = label;
  $('theme-toggle').setAttribute('aria-pressed', String(theme === 'dark'));
  $('theme-moon').hidden = theme === 'dark'; $('theme-sun').hidden = theme !== 'dark';
  swapFigureSources(theme);
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
  style.textContent = readerStylesheet({
    theme: document.documentElement.dataset.theme, size: preferences.size, fontStack: READING_FONTS[preferences.font],
    canvas: getComputedStyle(document.querySelector('.document-pane')).backgroundColor,
    ink: cssToken('--ink'), paper: cssToken('--paper'), accent: cssToken('--accent'), line: cssToken('--line'),
    figureMaxHeight: Math.round(window.innerHeight * .55)});
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
const savePreference = (key, field, value) => { preferences[field] = value; localStorage.setItem(key, value); applyAppearance(); };
$('text-size').onchange = () => savePreference('papers-text-size', 'size', $('text-size').value);
$('theme-toggle').onclick = () => savePreference('papers-theme', 'theme', document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark');
$('reading-font').onchange = () => savePreference('papers-font', 'font', $('reading-font').value);
$('reading-margin').onchange = () => savePreference('papers-margin', 'margin', $('reading-margin').value);
function openSetup() {
  $('setup-connection-status').textContent = '';
  $('settings-dialog').close();
  const settings = state.settings || {};
  renderProvider(true, settings.endpoint || PROVIDER_PRESETS.openai.endpoint);
  $('setup-model').value = settings.model || ''; $('setup-key').value = '';
  $('setup-kindle').value = settings.kindle_email || '';
  $('setup-error').textContent = ''; updateSetupKeyStatus(); $('setup-dialog').showModal();
}
function updateSetupKeyStatus() {
  const sameEndpoint = normalizedEndpoint(connectionEndpoint(true)) === normalizedEndpoint(state.settings?.endpoint);
  $('setup-key-status').textContent = sameEndpoint && state.settings?.has_key ? 'Your key is already saved. Leave blank to keep it.' : 'Saved securely in macOS Keychain.';
}
$('setup-open').onclick = openSetup;
$('setup-endpoint').oninput = updateSetupKeyStatus;
$('provider-preset').onchange = () => changeProvider(false);
$('setup-provider-preset').onchange = () => changeProvider(true);
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
  const endpoint = connectionEndpoint(true), model = $('setup-model').value.trim(), key = $('setup-key').value;
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
  const values = () => ({endpoint:connectionEndpoint(setup),model:$(setup ? 'setup-model':'model').value.trim(),api_key:$(setup ? 'setup-key':'api-key').value.trim()});
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
          while (!TERMINAL.has(job.state) && tourStep === index) {
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
      $('tour').animate([{opacity:0,filter:'blur(4px)',transform:'translateY(10px) scale(.98)'},{opacity:1,filter:'blur(0px)',transform:'translateY(0) scale(1)'}],{duration:motion().slow,easing:motion().easing});
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
  const active = state.jobs.some(job => !TERMINAL.has(job.state));
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
  if (!disclosure.matches('.share-sheet details, .settings-disclosure')) return;
  window.requestAnimationFrame(() => {
    if (!disclosure.open) return;
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    for (const child of disclosure.children) {
      if (child === summary || !child.animate) continue;
      child.getAnimations().forEach(animation => animation.cancel());
      child.animate([{opacity:0},{opacity:1}], {duration:reduced ? 100 : motion().quick, easing:motion().easing});
    }
  });
});
