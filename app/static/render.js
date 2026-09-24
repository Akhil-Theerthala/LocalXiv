// Renderers draw into the elements they are handed and call back for every action. They read no page state.
export const createNode = document => (tag, text, className) => {
  const el = document.createElement(tag);
  if (text !== undefined) el.textContent = text;
  if (className) el.className = className;
  return el;
};

// Restart the exit animation, then remove the element once it ends.
export function expireToast(element, remove, {setTimeout, reducedMotion}) {
  element.classList.remove('toast-expiring'); void element.offsetWidth;
  element.classList.add('toast-expiring');
  return setTimeout(remove, reducedMotion() ? 5000 : 5250);
}

export const TERMINAL = new Set(['ready', 'completed', 'succeeded', 'failed', 'cancelled', 'interrupted']);
const KINDS = {import:'Paper import',reading:'Paper indexing',blog:'Blog',overview:'Overview',chat:'Question',export:'File export',send:'Kindle delivery',recommend:'Recommendations'};
const STATUSES = {ready:'ready',completed:'ready',succeeded:'ready',failed:'failed',interrupted:'interrupted',cancelled:'cancelled',running:'in progress',queued:'queued'};

export class JobNotices {
  constructor({target, toggle, node, run, paperAPI, downloadLink, retries, setTimeout, clearTimeout, reducedMotion}) {
    Object.assign(this, {target, toggle, node, run, paperAPI, downloadLink, retries, setTimeout, clearTimeout, reducedMotion});
    this.records = new Map();
    this.initialized = false;
  }

  expire(element, remove) {
    return expireToast(element, remove, this);
  }

  updateToggle() {
    const count = this.target.children.length;
    this.toggle.hidden = count === 0;
    this.toggle.textContent = `${count} update${count === 1 ? '' : 's'}`;
  }

  render(jobs, papers) {
    const success = job => ['ready','completed','succeeded','cancelled'].includes(job.state);
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
        const item = this.node('div', undefined, 'toast glass'), heading = this.node('div', undefined, 'toast-heading'), close = this.node('button', '×');
        record.element = item; record.title = this.node('strong'); record.description = this.node('p');
        record.progress = this.node('progress'); record.actions = this.node('div', undefined, 'toast-actions'); record.actionsSignature = null;
        record.dismiss = () => { this.clearTimeout(record.timer); record.dismissed = true; item.remove(); record.element = null; this.updateToggle(); };
        close.setAttribute('aria-label', 'Dismiss ' + kind.toLowerCase()); close.onclick = record.dismiss;
        record.progress.setAttribute('aria-label', kind + ' progress'); record.progress.setAttribute('aria-live', 'off');
        heading.append(record.title, close); item.append(heading, record.description, record.progress, record.actions); this.target.append(item);
      }
      const item = record.element, actions = record.actions;
      item.setAttribute('data-state', job.state);
      const title = `${kind} ${status}${paperTitle ? ' · ' + paperTitle : ''}`;
      if (record.title.textContent !== title) record.title.textContent = title;
      const description = [job.error || job.result?.warning || (!finished && typeof job.progress === 'string' ? job.progress : ''),
        job.kind === 'send' && job.result?.delivery === 'handed_to_mail' && ['ready','completed','succeeded'].includes(job.state)
          ? 'Handed to Mail. Check your Kindle to confirm delivery.' : ''].filter(Boolean).join(' ');
      record.description.setAttribute('aria-live', finished ? 'polite' : 'off');
      if (record.description.textContent !== description) record.description.textContent = description;
      record.description.hidden = !description; record.progress.hidden = finished;
      if (typeof job.progress === 'number') { record.progress.max = 100; record.progress.value = job.progress; }
      else record.progress.removeAttribute('value');
      if (job.error || job.result?.warning) { this.clearTimeout(record.timer); item.classList.remove('toast-expiring'); item.onmouseleave = item.onfocusout = null; }
      const actionsSignature = JSON.stringify([finished ? job.state : 'active', job.result?.download_url]);
      if (record.actionsSignature === actionsSignature) continue;
      record.actionsSignature = actionsSignature; actions.replaceChildren();
      if (!finished) {
        const cancel = this.node('button','Cancel','quiet'); cancel.onclick = () => this.run(`/api/jobs/${encodeURIComponent(job.id)}/cancel`,{}); actions.append(cancel);
      } else if (['failed','interrupted','cancelled'].includes(job.state) && job.kind !== 'send') {
        let retry = this.retries.get(job.id);
        if (!retry && job.payload?.url && job.kind === 'import') retry = {path:'/api/import',payload:{url:job.payload.url}};
        if (!retry && job.payload?.paper_id && ['blog','overview','export'].includes(job.kind)) retry = {path:`${this.paperAPI(job.payload.paper_id)}/${job.kind}`,payload:job.payload};
        if (retry) { const button = this.node('button','Retry','quiet'); button.onclick = () => { record.dismiss(); this.run(retry.path,retry.payload); }; actions.append(button); }
      }
      if (job.result?.download_url) { const link = this.downloadLink(job.result.download_url); if (link) actions.append(link); }
      actions.hidden = !actions.children.length;
      this.clearTimeout(record.timer); item.classList.remove('toast-expiring');
      if (!success(job) || actions.children.length || job.error || job.result?.warning) continue;
      const expire = () => { item.classList.remove('toast-expiring'); record.timer = this.expire(item, record.dismiss); };
      item.onmouseenter = item.onfocusin = () => { this.clearTimeout(record.timer); item.classList.remove('toast-expiring'); };
      item.onmouseleave = item.onfocusout = expire; expire();
    }
    this.initialized = true; this.updateToggle();
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
        const block = node('figure', undefined, 'overview-figure'), img = node('img');
        img.src = image; img.dataset.lightSrc = image; const dark = fileURL(figure.svg_dark); if (dark) img.dataset.darkSrc = dark; img.alt = figure.alt || figure.caption || 'Paper explanation'; img.loading = 'lazy';
        const expand = node('button', undefined, 'figure-open'); expand.type = 'button'; expand.setAttribute('aria-label', 'Enlarge figure: ' + (figure.alt || figure.caption || 'Paper explanation')); const picture = node('picture');
        if (figure.portrait?.svg) { const source = node('source'); source.media = '(max-width: 600px)'; source.srcset = fileURL(figure.portrait.svg); picture.append(source); }
        picture.append(img); expand.append(picture, node('span', 'Enlarge figure ↗'));
        expand.onclick = () => openFigure(img.currentSrc || image, img.alt, figure.caption, figure.panels, figure.dimensions);
        block.append(expand, node('figcaption', figure.caption));
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

export function renderLibrary(target, papers, {node, query, selected, tourPaperId, tourFirst = false, onOpen, onRemove}) {
  query = query.toLowerCase();
  target.replaceChildren();
  let drawn = 0;
  const shown = papers.filter(p => `${p.title} ${p.authors} ${p.arxiv_id || p.id}`.toLowerCase().includes(query));
  if (tourFirst) shown.sort((a,b) => Number(b.id === tourPaperId)-Number(a.id === tourPaperId));
  for (const paper of shown) {
    const button = node('button'); button.append(node('span',paper.title || paper.id,'library-paper-title'));
    if (paper.id === tourPaperId) button.id = 'tour-paper';
    button.setAttribute('aria-current', String(paper.id === selected)); button.title = paper.title || paper.id;
    if (paper.authors) button.append(node('span', Array.isArray(paper.authors) ? paper.authors.join(', ') : paper.authors, 'library-paper-authors'));
    button.append(node('small', paper.arxiv_id || paper.id));
    button.onclick = () => onOpen(paper);
    const card = node('div', undefined, 'library-card');
    const actions = node('details', undefined, 'library-actions');
    const summary = node('summary', '•••');
    summary.setAttribute('aria-label', `Actions for ${paper.title || paper.id}`);
    actions.append(summary);
    actions.onkeydown = event => { if (event.key === 'Escape') { actions.open = false; summary.focus(); event.stopPropagation(); } };
    const remove = node('button', 'Remove paper', 'remove-paper');
    remove.setAttribute('aria-label', `Remove ${paper.title || paper.id} from library`);
    remove.onclick = () => { actions.open = false; onRemove(paper, summary); };
    actions.append(remove); card.append(button, actions); target.append(card); drawn++;
  }
  if (!drawn) target.append(node('p', papers.length ? 'No matching papers. Try another title or author.' : 'Your imported papers will appear here.', 'muted'));
  return drawn;
}

export function renderRecommendations(target, items, {node, onAdd}) {
  target.replaceChildren();
  for (const item of items) {
    // Only server-verified arXiv IDs can become links or import actions.
    if (!/^(?:\d{4}\.\d{4,5}|[A-Za-z][A-Za-z.\-]*\/\d{7})(?:v[1-9]\d*)?$/.test(item.id)) continue;
    const url = 'https://arxiv.org/abs/' + item.id;
    const card = node('article',undefined,'recommendation glass'), heading = node('h3'), link = node('a',item.title);
    link.href = url; link.target = '_blank'; link.rel = 'noopener'; heading.append(link);
    const venue = node('a',`${item.venue} · ${item.year}`,'paper-meta');
    if (/^https:\/\/dblp\.org\/rec\/conf\/[a-zA-Z0-9/_.-]+$/.test(item.venue_url || '')) { venue.href = item.venue_url; venue.target = '_blank'; venue.rel = 'noopener'; }
    card.append(venue,heading,node('p',item.summary));
    const add = node('button','Add to library ↗','quiet'); add.onclick = () => onAdd(url, add); card.append(add); target.append(card);
  }
}

export function renderContents(target, entries, {node}) {
  target.replaceChildren();
  for (const entry of entries) {
    const button = node('button', entry.label);
    button.setAttribute('aria-current', String(Boolean(entry.current)));
    button.onclick = entry.onSelect;
    target.append(button);
  }
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
