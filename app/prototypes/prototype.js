// Read-only design study. All mutation and AI flows are explicitly simulated.
// The bundled paper is a local, sanitized conversion fixture, never remote HTML.
const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];
const variants = ['A', 'B', 'C'];
let variant = new URL(location.href).searchParams.get('variant') || 'A';
let textSize = matchMedia('(max-width:639px)').matches ? 18 : 20;
let theme = 'system';
let currentView = 'paper';
let toastTimer;
let importTimer;
let observer;
const titles = [
  ['Semantic Entropy Probes: Robust and Cheap Hallucination Detection in LLMs', 'Kossen et al.', '2406.15927v1'],
  ['Attention Is All You Need', 'Vaswani et al.', '1706.03762'],
  ['Semantic Uncertainty: Linguistic Invariances for Uncertainty Estimation in Natural Language Generation', 'Kuhn et al.', '2302.09664'],
  ['SelfCheckGPT: Zero-Resource Black-Box Hallucination Detection for Generative Large Language Models', 'Manakul et al.', '2303.08896']
];

function notify(message) {
  clearTimeout(toastTimer); $('#toast').textContent = message; $('#toast').hidden = false;
  toastTimer = setTimeout(() => $('#toast').hidden = true, 4200);
}
function animateLayout() {
  document.body.classList.remove('variant-enter');
  requestAnimationFrame(() => requestAnimationFrame(() => document.body.classList.add('variant-enter')));
}
function setVariant(next) {
  variant = variants.includes(next) ? next : 'A';
  const anchor = $$('.prose > section').find(node => node.getBoundingClientRect().bottom > 150);
  const oldOffset = anchor?.getBoundingClientRect().top;
  document.body.dataset.variant = variant;
  document.body.classList.remove('is-focused', 'hide-study');
  $$('.focus-button,.dock-focus').forEach(button => button.textContent = 'Focus mode');
  $$('button[data-variant]').forEach(button => button.dataset.variant === variant ? button.setAttribute('aria-current', 'page') : button.removeAttribute('aria-current'));
  const url = new URL(location.href); url.searchParams.set('variant', variant); history.replaceState(null, '', url);
  document.title = `Papers to Kindle | ${ {A:'Outline',B:'Focus',C:'Study'}[variant] } prototype`;
  if (anchor && window.scrollY > 100) window.scrollBy(0, anchor.getBoundingClientRect().top - oldOffset);
  animateLayout();
}
function setTheme() {
  const resolved = theme === 'system' ? matchMedia('(prefers-color-scheme:dark)').matches ? 'dark' : 'light' : theme;
  document.documentElement.dataset.theme = resolved;
  $('#theme').value = theme;
  $$('.theme-toggle').forEach(button => button.textContent = resolved === 'dark' ? 'Use light theme' : 'Use dark theme');
}
function setSize(change = 0) {
  textSize = Math.max(16, Math.min(26, textSize + change));
  document.documentElement.style.setProperty('--font-size', `${textSize}px`);
  $$('.size-value').forEach(value => value.textContent = `${textSize} px`);
  $$('[data-size]').forEach(button => button.disabled = Number(button.dataset.size) < 0 ? textSize === 16 : textSize === 26);
}
function showView(view) {
  currentView = view;
  $$('.view-panel').forEach(panel => panel.hidden = panel.id !== `${view}-view`);
  $$('[data-view]').forEach(button => button.dataset.view === view ? button.setAttribute('aria-current','page') : button.removeAttribute('aria-current'));
  $('.document-footer').hidden = view !== 'paper';
  if (view !== 'paper') window.scrollTo(0,0);
}
function openDialog(name) { $(`#${name}-dialog`).showModal(); }
function source(id) {
  $$('dialog[open]').forEach(dialog => dialog.close()); showView('paper');
  const target = document.getElementById(id);
  if (!target) return;
  target.scrollIntoView({behavior:'instant',block:'start'});
  const url = new URL(location.href);url.hash = id;history.replaceState(null,'',url);
  target.setAttribute('tabindex','-1');target.focus({preventScroll:true});
}
function renderLibrary() {
  for (const [container, query, grid] of [[$('.library-list'), $('#rail-search').value, false],[$('.library-grid'), $('#grid-search').value, true]]) {
    container.replaceChildren();
    const matches = titles.map((paper, index) => ({paper,index})).filter(({paper}) => paper.join(' ').toLowerCase().includes(query.toLowerCase()));
    for (const {paper,index} of matches) {
      const button = document.createElement('button'); button.className = grid ? 'paper-tile' : 'paper-list-item';
      button.style.setProperty('--index',index); if (!index) button.setAttribute('aria-current','true');
      const title = document.createElement(grid ? 'strong' : 'span');title.textContent=paper[0];
      const meta = document.createElement('small');meta.textContent=`${paper[1]} · ${paper[2]}`;
      button.append(title,meta);
      if (grid) {
        if (!index) {const img=document.createElement('img');img.src='assets/reader/media/file0.png';img.alt='Figure from Semantic Entropy Probes';img.className='tile-figure';button.append(img);}
        const action=document.createElement('span');action.className='tile-action';action.textContent=index ? 'Sample title' : 'Continue reading ↗';button.append(action);
      }
      button.onclick=() => {
        if (index) return notify('This is a sample title. Open Semantic Entropy Probes to test the reader.');
        $('#library-dialog').close(); showView('paper');
      };
      container.append(button);
    }
    if (!matches.length) {const empty=document.createElement('p');empty.className='library-help';empty.textContent='No matching papers. Try a different title.';container.append(empty);}
  }
}
document.addEventListener('click', event => {
  const button=event.target.closest('button'); if (!button) return;
  if (button.hasAttribute('data-close')) return button.closest('dialog').close();
  if (button.dataset.variant) return setVariant(button.dataset.variant);
  if (button.dataset.step) return setVariant(variants[(variants.indexOf(variant)+Number(button.dataset.step)+3)%3]);
  if (button.dataset.size) return setSize(Number(button.dataset.size));
  if (button.dataset.view) return showView(button.dataset.view);
  if (button.dataset.source) return source(button.dataset.source);
  if (button.dataset.companion) {
    $$('[data-companion]').forEach(tab=>tab === button ? tab.setAttribute('aria-current','page') : tab.removeAttribute('aria-current'));
    $('#companion-overview').hidden=button.dataset.companion!=='overview';$('#companion-contents').hidden=button.dataset.companion!=='contents';return;
  }
  const action=button.dataset.action;
  if (['library','appearance','contents','import','export'].includes(action)) return openDialog(action);
  if (action==='theme') {theme=document.documentElement.dataset.theme==='dark'?'light':'dark';return setTheme();}
  if (action==='focus') {
    document.body.classList.toggle('is-focused');
    $$('.focus-button,.dock-focus').forEach(item => item.textContent=document.body.classList.contains('is-focused')?'Exit focus':'Focus mode');
    animateLayout();return;
  }
  if (action==='hide-study') {document.body.classList.add('hide-study');notify('Companion hidden. Choose Study again to restore it.');return;}
  if (action==='example-question') {$('#question').value='What is the probe trained to predict?';$('#chat-form').requestSubmit();return;}
  if (action==='download-preview') $('#export-status').textContent='Download preview complete. No EPUB was created.';
  if (action==='send-preview') $('#export-status').textContent='Delivery preview complete. No message was sent.';
});
document.addEventListener('keydown', event => {
  if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey || event.target.closest('input,textarea,select,button,a,[contenteditable],dialog')) return;
  if (event.key==='ArrowLeft' || event.key==='ArrowRight') {event.preventDefault();setVariant(variants[(variants.indexOf(variant)+(event.key==='ArrowRight'?1:2))%3]);}
  if (event.key==='Escape' && document.body.classList.contains('is-focused')) $('.focus-button').click();
});
$('#theme').onchange=event=>{theme=event.target.value;setTheme();};
matchMedia('(prefers-color-scheme:dark)').addEventListener('change',setTheme);
$('#font-family').onchange=event=>document.documentElement.style.setProperty('--article-font',event.target.value==='serif' ? "Georgia,'Times New Roman',serif" : 'var(--ui-font)');
$('#line-width').onchange=event=>document.documentElement.style.setProperty('--reading-width',`${event.target.value}px`);
$('#rail-search').oninput=renderLibrary;$('#grid-search').oninput=renderLibrary;
$('#import-dialog').addEventListener('close',()=>{clearTimeout(importTimer);$('#import-form button').disabled=false;$('#import-status').hidden=true;$('#import-error').textContent='';});
$('#import-form').onsubmit=event=>{
  event.preventDefault();$('#import-error').textContent='';
  let url;try {url=new URL($('#paper-url').value);} catch {$('#import-error').textContent='Enter a valid paper link.';return;}
  if (url.protocol!=='https:' || !['arxiv.org','www.arxiv.org','alphaxiv.org','www.alphaxiv.org'].includes(url.hostname) || !/^\/(abs|pdf|html|overview)\/[^/]+/.test(url.pathname)) {$('#import-error').textContent='Use an HTTPS paper link from arXiv or alphaXiv.';return;}
  const status=$('#import-status');status.hidden=false;status.textContent='Preparing your paper…';$('#import-form button').disabled=true;
  clearTimeout(importTimer);importTimer=setTimeout(()=>{status.textContent='Import preview complete. Open the sample paper from Your library.';$('#import-form button').disabled=false;},1100);
};
$('#chat-form').onsubmit=event=>{
  event.preventDefault();const question=$('#question').value.trim();if (!question) return;
  const messages=$('#chat-messages');messages.replaceChildren();
  const heading=document.createElement('p');heading.textContent=question;messages.append(heading);
  const answer=document.createElement('div');answer.className='chat-answer';
  const label=document.createElement('span');label.className='example-label';label.textContent='Prepared example answer';
  const text=document.createElement('p');
  text.textContent=/probe.*predict|trained to predict/i.test(question) ? 'The probe is trained to predict a binarized semantic entropy target from model hidden states. It uses semantic entropy labels rather than direct correctness labels. Open the method section to check how the paper constructs that target.' : 'This preview has one prepared answer. Try “What is the probe trained to predict?” to test its source link. A connected AI provider would handle other questions in the app.';
  answer.append(label,text);
  if (/probe.*predict|trained to predict/i.test(question)) {const link=document.createElement('button');link.dataset.source='sec:seps';link.className='source-link';link.textContent='Source: Semantic Entropy Probes ↗';answer.append(link);}
  messages.append(answer);$('#question').value='';messages.scrollIntoView({block:'center',behavior:'instant'});
};
setTheme();setSize();setVariant(variant);renderLibrary();
Promise.all([fetch('paper.html').then(response=>{if(!response.ok)throw Error('paper');return response.text();}),fetch('paper.json').then(response=>{if(!response.ok)throw Error('metadata');return response.json();})]).then(([html, metadata])=>{
  const parsed=new DOMParser().parseFromString(html,'text/html');
  $('#paper-content').replaceChildren(...parsed.body.childNodes);
  $$('.toc').forEach(nav=>{
    metadata.chapters.forEach((chapter,index)=>{
      const link=document.createElement('a');link.href=`#${chapter.id}`;link.textContent=chapter.title;link.dataset.section=chapter.id;
      if(!index)link.setAttribute('aria-current','location');
      link.onclick=event=>{event.preventDefault();source(chapter.id);};nav.append(link);
    });
  });
  $('#paper-content').addEventListener('click',event=>{
    const link=event.target.closest('a');if(link?.getAttribute('href')?.startsWith('#')){event.preventDefault();source(decodeURIComponent(link.getAttribute('href').slice(1)));}
  });
  observer=new IntersectionObserver(entries=>{
    for(const entry of entries) if(entry.isIntersecting) $$('.toc a').forEach(link=>link.dataset.section===entry.target.id?link.setAttribute('aria-current','location'):link.removeAttribute('aria-current'));
  },{rootMargin:'-95px 0px -65% 0px',threshold:0});
  $$('#paper-content > section').forEach(section=>observer.observe(section));
  if(location.hash) source(decodeURIComponent(location.hash.slice(1)));
  document.body.dataset.ready='true';
}).catch(()=>{
  $('#paper-content').replaceChildren();const message=document.createElement('p');message.textContent='The sample paper could not load. Run the local preview server, then reload this page.';$('#paper-content').append(message);
});
