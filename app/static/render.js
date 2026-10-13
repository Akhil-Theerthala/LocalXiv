// Renderers draw into the elements they are handed and call back for every action. They read no page state.
export function node(tag, text, className) {
  const el = document.createElement(tag);
  if (text !== undefined) el.textContent = text;
  if (className) el.className = className;
  return el;
}

// Restart the exit animation, then remove the element once it ends.
export function expireToast(element, remove) {
  element.classList.remove('toast-expiring'); void element.offsetWidth;
  element.classList.add('toast-expiring');
  return setTimeout(remove, matchMedia('(prefers-reduced-motion: reduce)').matches ? 5000 : 5250);
}

export const TERMINAL = new Set(['ready', 'failed', 'cancelled', 'interrupted']);
const KINDS = {import:'Paper import',blog:'Blog',overview:'Overview',export:'File export',send:'Kindle delivery'};
const STATUSES = {ready:'ready',failed:'failed',interrupted:'interrupted',cancelled:'cancelled',running:'in progress',queued:'queued'};

// Toasts for the jobs of this run, or, with `list`, every recent job, kept until the list closes.
export class JobNotices {
  constructor({target, run, paperAPI, downloadLink, retries, list = false}) {
    Object.assign(this, {target, run, paperAPI, downloadLink, retries, list});
    this.records = new Map();
    this.initialized = list;
  }

  render(jobs, papers) {
    const success = job => ['ready','cancelled'].includes(job.state);
    for (const job of jobs) {
      const paperID = job.payload?.paper_id || job.result?.paper_id;
      const paperTitle = papers.find(paper => paper.id === paperID)?.title || paperID || '';
      const signature = JSON.stringify([job.state, job.progress, job.error, job.result, paperTitle]);
      let record = this.records.get(job.id);
      if (record?.signature === signature) continue;
      const finished = TERMINAL.has(job.state);
      // A new window starts a fresh notification run, including for saved errors.
      // Keep durable job/error records; only announce work active or changed in this run.
      if (!record) { record = {element:null, timer:null, finished, dismissed:!this.initialized && finished}; this.records.set(job.id, record); }
      if (finished && !record.finished) record.dismissed = false;
      record.signature = signature; record.finished = finished;
      if (record.dismissed) continue;
      const kind = KINDS[job.kind] || 'Task';
      const status = STATUSES[job.state] || 'in progress';
      if (!record.element) {
        const item = node('div', undefined, 'toast'), heading = node('div', undefined, 'toast-heading'), close = node('button', '×');
        record.element = item; record.title = node('strong'); record.description = node('p');
        record.progress = node('progress'); record.actions = node('div', undefined, 'toast-actions'); record.actionsSignature = null;
        record.dismiss = () => { clearTimeout(record.timer); record.dismissed = true; item.remove(); record.element = null; };
        close.setAttribute('aria-label', 'Dismiss ' + kind.toLowerCase()); close.onclick = record.dismiss; close.hidden = this.list;
        record.progress.setAttribute('aria-label', kind + ' progress'); record.progress.setAttribute('aria-live', 'off');
        heading.append(record.title, close); item.append(heading, record.description, record.progress, record.actions); this.target.append(item);
      }
      const item = record.element, actions = record.actions;
      item.setAttribute('data-state', job.state);
      const title = `${kind} ${status}${paperTitle ? ' · ' + paperTitle : ''}`;
      if (record.title.textContent !== title) record.title.textContent = title;
      const description = [job.error || job.result?.warning || (!finished && typeof job.progress === 'string' ? job.progress : ''),
        job.kind === 'send' && job.result?.delivery === 'handed_to_mail' && job.state === 'ready'
          ? 'Handed to Mail. Check your Kindle to confirm delivery.' : ''].filter(Boolean).join(' ');
      record.description.setAttribute('aria-live', finished ? 'polite' : 'off');
      if (record.description.textContent !== description) record.description.textContent = description;
      record.description.hidden = !description; record.progress.hidden = finished;
      if (typeof job.progress === 'number') { record.progress.max = 100; record.progress.value = job.progress; }
      else record.progress.removeAttribute('value');
      if (job.error || job.result?.warning) { clearTimeout(record.timer); item.classList.remove('toast-expiring'); item.onmouseleave = item.onfocusout = null; }
      const actionsSignature = JSON.stringify([finished ? job.state : 'active', job.result?.download_url]);
      if (record.actionsSignature === actionsSignature) continue;
      record.actionsSignature = actionsSignature; actions.replaceChildren();
      if (!finished) {
        const cancel = node('button','Cancel','quiet'); cancel.onclick = () => this.run(`/api/jobs/${encodeURIComponent(job.id)}/cancel`,{}); actions.append(cancel);
      } else if (['failed','interrupted','cancelled'].includes(job.state) && job.kind !== 'send') {
        let retry = this.retries.get(job.id);
        if (!retry && job.payload?.url && job.kind === 'import') retry = {path:'/api/import',payload:{url:job.payload.url}};
        if (!retry && job.payload?.paper_id && ['blog','overview','export'].includes(job.kind)) retry = {path:`${this.paperAPI(job.payload.paper_id)}/${job.kind}`,payload:job.payload};
        if (retry) { const button = node('button','Retry','quiet'); button.onclick = () => { record.dismiss(); this.run(retry.path,retry.payload); }; actions.append(button); }
      }
      if (job.result?.download_url) { const link = this.downloadLink(job.result.download_url); if (link) actions.append(link); }
      actions.hidden = !actions.children.length;
      clearTimeout(record.timer); item.classList.remove('toast-expiring');
      if (this.list || !success(job) || actions.children.length || job.error || job.result?.warning) continue;
      const expire = () => { item.classList.remove('toast-expiring'); record.timer = expireToast(item, record.dismiss); };
      item.onmouseenter = item.onfocusin = () => { clearTimeout(record.timer); item.classList.remove('toast-expiring'); };
      item.onmouseleave = item.onfocusout = expire; expire();
    }
    this.initialized = true;
  }
}

export function cleanOverviewCitations(text) {
  return String(text || '').replace(/[ \t]*\[\s*p\d+(?:\s*[,;]\s*p\d+)*\s*\]/g, '');
}
// Protect code and math pipes such as P(y|x) before finding table cell boundaries.
export function tableCells(value) {
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
export function tableDivider(value) {
  const cells = tableCells(value || '');
  return cells.length > 1 && cells.every(cell => /^:?-+:?$/.test(cell));
}

export function renderProse(target, text, io) {
  const {node, references = [], figures = [], fileURL, openSource, openFigure, renderMath} = io;
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
        citation.onclick = () => openSource(source.href);
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
        const block = node('div'); renderProse(block, content.join('\n'), io); target.append(block);
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
        const block = node('figure', undefined, 'overview-figure');
        const alt = figure.alt || figure.caption || 'Paper explanation';
        const source = fileURL(figure.svg_source);
        if (source && io.inlineFigure) {
          // The Scene's own SVG goes into the page, so its text is selectable and its cards can
          // carry the component hover. The enlarge dialog keeps zooming the image file.
          const container = node('div', undefined, 'figure-inline');
          container.dataset.lightSrc = source;
          const dark = fileURL(figure.svg_dark); if (dark) container.dataset.darkSrc = dark;
          container.setAttribute('aria-busy', 'true');
          const expand = node('button', 'Enlarge figure ↗', 'figure-open quiet'); expand.type = 'button';
          expand.onclick = () => openFigure(image, alt, '', figure.panels, figure.dimensions);
          // The Overview's footer is drawn in the figure, so it gets no second caption here.
          block.append(container, expand);
          target.append(block);
          io.inlineFigure(container, figure);
        } else {
          const img = node('img');
          img.src = image; img.dataset.lightSrc = image; const dark = fileURL(figure.svg_dark); if (dark) img.dataset.darkSrc = dark; img.alt = alt; img.loading = 'lazy';
          const expand = node('button', undefined, 'figure-open'); expand.type = 'button'; expand.setAttribute('aria-label', 'Enlarge figure: ' + alt); const picture = node('picture');
          if (figure.portrait?.svg) { const source = node('source'); source.media = '(max-width: 600px)'; source.srcset = fileURL(figure.portrait.svg); picture.append(source); }
          picture.append(img); expand.append(picture, node('span', 'Enlarge figure ↗'));
          // An Overview draws its footer in the image; only a Blog figure gets a caption.
          const caption = io.inlineFigure ? '' : figure.caption;
          expand.onclick = () => openFigure(img.currentSrc || image, img.alt, caption, figure.panels, figure.dimensions);
          block.append(expand); if (caption) block.append(node('figcaption', caption));
          target.append(block);
        }
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

// Library search and the library group of Paper search: every word of the query must appear.
export function matchesLibrary(paper, query) {
  const text = `${paper.title || ''} ${[].concat(paper.authors || []).join(', ')} ${paper.arxiv_id || paper.id}`.toLowerCase();
  return query.toLowerCase().split(/\s+/).every(word => text.includes(word));
}
// The ID pattern of paper_id() in papers/acquire.py.
const ARXIV_ID = /(?:[0-9]{4}\.[0-9]{4,5}|[A-Za-z][A-Za-z.\-]*\/[0-9]{7})(?:v[1-9][0-9]*)?/;
export function inputKind(text) {
  const value = text.trim();
  if (!value) return '';
  return /^https?:\/\/|(?:ar|alpha)xiv\.org\//i.test(value) || new RegExp(`^${ARXIV_ID.source}$`).test(value) ? 'import' : 'search';
}
export const baseID = id => String(id || '').replace(/v\d+$/, '');
// A library Paper keeps its authors as one "Last, First, Last, First" string, so only a list is cut.
export const authorList = (authors, count) => !Array.isArray(authors) ? authors || ''
  : authors.slice(0, count).join(', ') + (authors.length > count ? ' et al.' : '');
// Library rows first, then remote rows. A remote row whose Paper is already a library row is dropped.
export function searchRows(papers, query, remote, libraryCount, total) {
  const library = papers.filter(paper => matchesLibrary(paper, query)).slice(0, libraryCount)
    .map(paper => ({id: paper.id, title: paper.title || paper.id, authors: paper.authors, arxiv_id: paper.arxiv_id || paper.id}));
  const shown = new Set(library.map(row => baseID(row.arxiv_id)));
  return [...library, ...(remote || []).filter(row => !shown.has(row.arxiv_id))].slice(0, total);
}
// A row opens its library Paper, waits for an active import of the same arXiv ID, or offers Add.
export function rowState(row, papers, jobs) {
  const paper = papers.find(p => row.id ? p.id === row.id : baseID(p.arxiv_id || p.id) === row.arxiv_id);
  return {paper, adding: !paper && jobs.some(job => job.kind === 'import' && !TERMINAL.has(job.state)
    && baseID(String(job.payload?.url).match(ARXIV_ID)?.[0]) === baseID(row.arxiv_id))};
}

const SVG = 'http://www.w3.org/2000/svg';
// An SF Symbols-style icon from the sprite in index.html.
export function icon(name, className = 'i') {
  const svg = document.createElementNS(SVG, 'svg'), use = document.createElementNS(SVG, 'use');
  svg.setAttribute('class', className); svg.setAttribute('aria-hidden', 'true');
  use.setAttribute('href', '#i-' + name); svg.append(use);
  return svg;
}

// A library Paper stores "Last, First, Last, First"; an odd number of parts cannot be paired, so it stays as stored.
function authorPairs(authors) {
  if (Array.isArray(authors)) return authors.map(name => [String(name)]);
  const text = String(authors || '').trim(), parts = text.split(',').map(part => part.trim());
  if (!text) return [];
  if (parts.length % 2 || parts.some(part => !part)) return [[text]];
  return Array.from({length: parts.length / 2}, (_, index) => [parts[index * 2], parts[index * 2 + 1]]);
}
export const authorNames = authors => authorPairs(authors).map(([last, first]) => first ? `${first} ${last}` : last);
const lastName = ([last, first]) => first ? last : last.split(',')[0].trim().split(/\s+/).at(-1);
export function byline(authors) {
  const pairs = authorPairs(authors);
  return pairs.length > 2 ? `${lastName(pairs[0])} et al.` : pairs.map(lastName).join(' and ');
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
// The publication month from the arXiv ID: 2511.01689 is Nov 2025, hep-th/9901001 is Jan 1999.
export function arxivDate(id) {
  const match = String(id || '').match(/^(?:([a-z][a-z.-]*)\/)?(\d{2})(\d{2})(?:\.?\d{3,5})(?:v\d+)?$/i);
  const month = Number(match?.[3]);
  if (!match || month < 1 || month > 12) return null;
  const year = Number(match[2]) + (match[1] && Number(match[2]) > 90 ? 1900 : 2000);
  return {year, month, key: year * 100 + month, label: `${MONTHS[month - 1]} ${year}`};
}
function dayLabel(seconds) {
  if (!Number(seconds)) return '';
  const date = new Date(seconds * 1000);
  return date.toLocaleDateString(undefined, {day: 'numeric', month: 'short', ...(date.getFullYear() === new Date().getFullYear() ? {} : {year: 'numeric'})});
}
// The title up to its colon, so a sidebar row or a window title stays short.
export const shortTitle = title => { const text = String(title || ''); const head = text.split(': ')[0]; return head.length >= 4 && head.length <= 60 ? head : text; };

// A TeX special in a title or a name breaks the entry. A $…$ span from the arXiv title stays math.
const TEX = {'\\': '\\textbackslash{}', '^': '\\^{}', '~': '\\~{}'};
const texText = text => String(text).split(/(\$[^$]+\$)/).map((part, index) => index % 2 ? part : part.replace(/[\\{}$&%#_^~]/g, char => TEX[char] || '\\' + char)).join('');
export function bibtex(paper) {
  const id = baseID(paper.arxiv_id || paper.id), pairs = authorPairs(paper.authors);
  const author = pairs.map(pair => pair.map(texText).join(', ')).join(' and ');
  const year = arxivDate(id)?.year;
  // The inner braces keep the title's capitals in styles that lowercase titles.
  const fields = [['title', `{${texText(paper.title || id)}}`], ['author', author], ['year', year], ['eprint', id], ['archivePrefix', 'arXiv']].filter(([, value]) => value);
  return `@misc{${id},\n${fields.map(([key, value]) => `  ${key} = {${value}}`).join(',\n')}\n}`;
}

export function readingState(paper) { return paper.reading?.state || 'new'; }

// One Library row: Reading state, title, authors, Overview and Blog marks, publication month, added date.
export function libraryRow(paper, {onOpen, onMenu}) {
  const row = node('button', undefined, 'prow'), state = readingState(paper), title = paper.title || paper.id;
  row.type = 'button'; row.dataset.id = paper.id;
  const mark = node('span', undefined, 'st');
  if (state === 'new') { mark.append(node('span', undefined, 'dot')); mark.title = 'New'; }
  if (state === 'reading') { mark.append(icon('progress', 'i ring')); mark.title = 'Reading'; }
  const text = node('span', undefined, 'ptext');
  text.append(node('span', title, 'pt'), node('span', authorList(authorNames(paper.authors), 3), 'pa'));
  const marks = node('span', undefined, 'marks');
  for (const [kind, label] of [['overview', 'Overview'], ['blog', 'Blog']]) {
    const glyph = icon(kind); if (!paper[kind]) glyph.classList.add('off');
    marks.append(glyph);
  }
  row.append(mark, text, marks, node('span', arxivDate(paper.arxiv_id || paper.id)?.label || '', 'pub'), node('span', dayLabel(paper.added_at), 'add'));
  const explained = ['overview', 'blog'].filter(kind => paper[kind]).map(kind => kind === 'overview' ? 'Overview' : 'Blog');
  row.setAttribute('aria-label', [title, {new: 'New', reading: 'Reading', read: 'Read'}[state], explained.length ? explained.join(' and ') + ' saved' : ''].filter(Boolean).join(', '));
  row.onclick = () => onOpen(paper);
  row.oncontextmenu = event => { event.preventDefault(); onMenu(paper, event); };
  return row;
}

// Component hover: the Digest fields for one drawn card or group heading, as the SVG title the
// browser shows on hover and the label a screen reader announces.
export function componentSummary({name, role, computes, values}) {
  return [name + (computes ? ' computes ' + computes : ''), role, values ? 'Values: ' + values : ''].filter(Boolean).join('. ');
}

export function annotateFigure(elements, components, {svgNode, onPassage}) {
  const byNode = new Map((components || []).map(item => [item.node, item]));
  let count = 0;
  for (const element of elements) {
    const component = byNode.get(element.dataset.node);
    if (!component) continue;
    const summary = componentSummary(component);
    const title = svgNode('title'); title.textContent = summary;
    element.append(title);
    element.classList.add('has-component');
    element.setAttribute('tabindex', '0'); element.setAttribute('role', 'link'); element.setAttribute('aria-label', summary);
    const passage = component.passages?.[0];
    if (passage && onPassage) {
      element.onclick = () => onPassage(passage);
      element.onkeydown = event => { if (['Enter', ' '].includes(event.key)) { event.preventDefault(); onPassage(passage); } };
    }
    count++;
  }
  return count;
}
