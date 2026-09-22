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
