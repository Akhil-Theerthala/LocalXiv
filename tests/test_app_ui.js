// Run with node tests/test_app_ui.js. Checks the browser's untrusted URL boundary.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const elements = new Map();
const storage = new Map();
function element(tag) {
  return {tagName:tag.toUpperCase(), children:[], attributes:{}, textContent:'',
    append(...children){children.forEach(child=>child.parent=this);this.children.push(...children);}, replaceChildren(){this.children=[];this.textContent='';}, remove(){if(this.parent)this.parent.children=this.parent.children.filter(child=>child!==this);}, querySelectorAll(){return this.children.filter(child=>['H2','H3'].includes(child.tagName));}, dataset:{},style:{setProperty(){}},classList:{add(){},remove(){},toggle(){}},
    setAttribute(name,value){this.attributes[name]=value;}, removeAttribute(name){delete this.attributes[name];}, getAttribute(name){return name==='src' ? this.src : this.attributes[name];}, addEventListener(){},focus(){},showModal(){this.open=true;},close(){this.open=false;}};
}
const timers = [];
const timerDelays = [];
const documentEvents = new Map();
const context = vm.createContext({
  URL, URLSearchParams, Map, Set, JSON,
  setTimeout:(fn,delay)=>{timers.push(fn);timerDelays.push(delay);return timers.length;},clearTimeout(){},
  window:{requestAnimationFrame:fn=>fn(),scrollTo(){},matchMedia:()=>({matches:false,addEventListener(){}}),addEventListener(){},innerHeight:900},
  location: {hash:'#token=test-session', pathname:'/', origin:'http://127.0.0.1:8765'},
  localStorage: {getItem:key=>storage.get(key), setItem:(key,value)=>storage.set(key,value)},
  history:{replaceState(){}},
  document:{addEventListener(type,handler){documentEvents.set(type,handler);},querySelector(){return null;},querySelectorAll(){return [];},body:element('body'),documentElement:element('html'),createElement:element,getElementById(id){if (!elements.has(id)) elements.set(id,element('div')); return elements.get(id);}},
  fetch:()=>new Promise(()=>{}),
});
const script = fs.readFileSync(require('node:path').join(__dirname, '../app/static/app.js'),'utf8');
vm.runInContext(script, context);
const originalRefresh = vm.runInContext('refresh', context);
// Library metadata remains readable; keyboard dismissal never waits for animation.
vm.runInContext("state.papers=[{id:'preview',title:'Preview',authors:['First Author','Second Author']}];$('search').value='';renderLibrary()",context);
assert.equal(elements.get('paper-list').children[0].children[0].children[1].textContent,'First Author, Second Author');
const previewActions = elements.get('paper-list').children[0].children[1];
assert.equal(previewActions.children[0].attributes['aria-label'],'Actions for Preview');
previewActions.open = true;
previewActions.onkeydown({key:'Escape',stopPropagation(){}});
assert.equal(previewActions.open,false);
vm.runInContext("state.papers=[];let testClosed=0;dismissDialog({close(){testClosed++},animate(){throw Error('Keyboard must not animate')}},{detail:0})",context);
assert.equal(vm.runInContext('testClosed',context),1);
vm.runInContext("activeTab='paper';renderContents()",context);
assert.equal(elements.get('contents-title').textContent,'Paper sections');
vm.runInContext("activeTab='blog';detail={overview:{text:'Preview'}};renderContents();detail=null;activeTab='overview'",context);
assert.equal(elements.get('contents-title').textContent,'Blog sections');
vm.runInContext("detail={paper:{chapters:[{title:'Original chapter',path:'reader/a.xhtml'}]},bento:{text:'Figure'}};activeTab='overview';renderContents();updateViewActions()",context);
assert.equal(elements.get('contents').children.length,0,'Overview must not borrow original-paper chapters');
assert.equal(elements.get('reading-companion').hidden,true);
assert.equal(elements.get('mobile-contents').hidden,true);
assert.equal(elements.get('generate-bento').hidden,true,'Saved overview moves regeneration into the toolbar');
assert.equal(elements.get('view-actions').hidden,false);
vm.runInContext("detail=null;updateViewActions()",context);
assert.equal(elements.get('generate-bento').hidden,false,'Empty overview retains its Generate button');
assert.equal(elements.get('view-actions').hidden,true);
vm.runInContext("$('bento-text').append(node('h2','Overview heading'));renderContents()",context);
assert.equal(elements.get('contents').children[0].textContent,'Overview heading');
assert.equal(elements.get('reading-companion').hidden,false);
vm.runInContext("$('bento-text').replaceChildren();renderContents()",context);


assert.equal(elements.get('reading-font').value,'palatino','Default reader font');
assert.equal(elements.get('reading-margin').value,'narrow','Default reading margins');
vm.runInContext("selected = 'hep-th/9901001v1'", context);
const url = value => vm.runInContext(`fileURL(${JSON.stringify(value)})`, context);
assert.equal(url('reader/ch01.xhtml#p10'), 'http://127.0.0.1:8765/files/hep-th%2F9901001v1/reader/ch01.xhtml?token=test-session#p10');
assert.equal(vm.runInContext("downloadLink('/files/paper1/original.pdf').textContent",context),'Save PDF');
assert.equal(vm.runInContext("downloadLink('/files/paper1/paper.epub').textContent",context),'Save EPUB');
for (const input of ['https://evil.test/x','javascript:alert(1)','//evil.test/x','../secret','reader/../../secret','\\evil','/api/settings',null]) assert.equal(url(input),null);
assert.equal(storage.get('papers-session'),'test-session');
assert.equal(script.includes('innerHTML'),false,'Untrusted text must never be interpreted as HTML');
const html = fs.readFileSync(require('node:path').join(__dirname,'../app/static/index.html'),'utf8');
assert.match(html,/sandbox="allow-same-origin"/);
assert.doesNotMatch(html,/allow-scripts/);
assert.match(html,/id="api-key" type="password"/);
const target = element('article'); context.proseTarget = target;
const writing = '# A concrete result\n\nA **strong** result with *limits*, `code`, $x_i$, and [p00001].\n\n- First finding\n- Second finding\n\n1. Measure\n2. Compare\n\n```tex\ny = x^2\n```\n\n<img src=x onerror=alert(1)> [bad](javascript:alert(1)) [p99999]';
vm.runInContext(`renderProse(proseTarget, ${JSON.stringify(writing)}, [{id:'p00001',section:'Results',text:'Evidence',href:'reader/ch01.xhtml#p10'}])`,context);
const descendants = root => [root,...root.children.flatMap(descendants)];
const all = descendants(target), tags = all.map(node=>node.tagName);
for (const tag of ['H2','P','STRONG','EM','CODE','UL','OL','LI','BUTTON']) assert.ok(tags.includes(tag),tag);
assert.ok(!tags.includes('IMG') && !tags.includes('SCRIPT') && !tags.includes('A'));
const text = all.map(node=>node.textContent).join('');
assert.ok(text.includes('<img src=x onerror=alert(1)>'));
assert.ok(text.includes('[bad](javascript:alert(1))'));
assert.ok(text.includes('[p99999]'));

const parse = value => {vm.runInContext(`renderProse(proseTarget, ${JSON.stringify(value)})`,context); return descendants(target);};
const math = parse(String.raw`Inline $x_i$ and \(\frac{a}{b}\), **$z^2$**.

$$
\sum_{i=1}^n x_i
$$

\[a^2+b^2=c^2\]

\begin{align}x&=1\\y&=2\end{align}

` + '```tex\ny=x^2\n```\n\n```js\nconst x = 1;\n```');
assert.equal(math.filter(e=>e.className?.includes('math-formula')).length,7);
assert.equal(math.filter(e=>e.className?.includes('math-display')).length,4);
assert.equal(math.filter(e=>e.tagName==='PRE').length,1,'Ordinary code remains code');
const table = parse('```markdown\n| Method | Meaning |\n| :- | -: |\n| $P(y|x)$ | **$x_i$** |\n| `a|b` | a\\|b |\n```');
assert.equal(table.filter(e=>e.tagName==='TABLE').length,1);
assert.equal(table.filter(e=>e.tagName==='TD').length,4,'Pipes within code and math must not split cells');
assert.equal(table.filter(e=>e.className?.includes('math-formula')).length,2);
assert.ok(table.some(e=>e.textContent==='a|b'));
assert.equal(parse('A | B\nwords | words').filter(e=>e.tagName==='TABLE').length,0);
vm.runInContext(`renderProse(proseTarget, ${JSON.stringify(writing)}, [{id:'p00001',section:'Results',text:'Evidence',href:'reader/ch01.xhtml#p10'}])`,context);
const citation = all.find(node=>node.tagName==='BUTTON');
assert.match(citation.attributes['aria-label'],/Read source 1:/);
assert.equal(citation.textContent, '[1]');
citation.onclick();
assert.match(elements.get('reader').src,/reader\/ch01.xhtml\?token=test-session#p10$/);
assert.equal(elements.get('tab-paper').attributes['aria-selected'],'true');
(async () => {
  elements.get('search').value = '';
  let reloads = 0, readerURL = 'http://127.0.0.1:8765/files/paper1/reader/main.xhtml?token=test-session';
  Object.defineProperty(elements.get('reader'),'src',{get(){return readerURL;},set(value){readerURL=value;reloads++;},configurable:true});
  context.paperFixture = {paper:{id:'paper1',title:'Example',document_digest:'same',chapters:[{path:'reader/main.xhtml'}]},overview:{text:'Example.',provenance:{model:'recorded-model',usage:[{total_tokens:100},{total_tokens:200}]}},messages:[{role:'assistant',content:'An answer.',sources:[],metadata:{usage:{total_tokens:42}}}]};
  vm.runInContext("selected='paper1'; detail={paper:{document_digest:'same'}}; state={papers:[]}; api=async()=>paperFixture",context);
  await vm.runInContext("openPaper('paper1')",context);
  assert.equal(reloads,0,'Polling the same document must preserve reading position');
  assert.equal(elements.get('overview-note').textContent,'');
  assert.equal(elements.get('overview-note').hidden,true);
  assert.doesNotMatch(html,/id="tab-chat"|id="messages"|id="report"/);
  assert.doesNotMatch(script,/Reported usage:|Generated with/);
  context.paperFixture = {...context.paperFixture,paper:{...context.paperFixture.paper,document_digest:'changed'}};
  await vm.runInContext("openPaper('paper1')",context);
  assert.equal(reloads,1,'A replaced document must reload the reader');
  await vm.runInContext("openPaper('paper1')",context);
  assert.equal(reloads,1,'Later polls must not reload the replaced document again');
  elements.get('artifact-kind').value = 'both';
  context.paperFixture = {paper:{id:'paper1',title:'PDF fixture',format:'pdf',document_digest:'pdf',
    chapters:[{path:'original.pdf#page=1'}],passages:[{text:'Page evidence'}],report:{warning:'Template parsing failed. Sending this paper will send the PDF.'}}};
  await vm.runInContext("openPaper('paper1')",context);
  assert.match(elements.get('reader').src,/original\.pdf\?token=test-session#page=1$/);
  assert.equal(elements.get('reader').attributes.sandbox,undefined);
  assert.equal(elements.get('fallback-notice').hidden,false);
  assert.match(elements.get('fallback-notice').textContent,/will send the PDF/);
  assert.equal(elements.get('generate').disabled,false);
  assert.equal(elements.get('artifact-kind').value,'paper');
  assert.equal(elements.get('artifact-both').disabled,true);
  vm.runInContext("switchTab('paper'); updateShareControls()",context);
  assert.equal(elements.get('share-epub').hidden,true);
  assert.equal(elements.get('share-png').hidden,true);
  assert.equal(elements.get('send').textContent,'Send PDF to Kindle');
  assert.equal(elements.get('profile').hidden,true);
  const pdfReloads=reloads;
  await vm.runInContext("openPaper('paper1')",context);
  assert.equal(reloads,pdfReloads,'PDF reading position survives polling');
  elements.get('artifact-kind').value='overview'; elements.get('artifact-kind').onchange();
  vm.runInContext("switchTab('blog'); updateShareControls()",context);
  assert.equal(elements.get('share-epub').hidden,false);
  assert.equal(elements.get('share-png').hidden,true);
  assert.equal(elements.get('profile').hidden,false);
  context.paperFixture = {paper:{id:'paper1',title:'EPUB fixture',document_digest:'epub',chapters:[{path:'reader/main.xhtml'}]}};
  await vm.runInContext("openPaper('paper1')",context);
  assert.equal(elements.get('reader').attributes.sandbox,'allow-same-origin');
  assert.equal(elements.get('fallback-notice').hidden,true);
  assert.equal(elements.get('artifact-both').disabled,false);
  vm.runInContext('state.settings={}; openSettings()',context);
  assert.equal(elements.get('overview-language').value,'casual');
  assert.equal(elements.get('overview-length').value,'medium');
  assert.equal(elements.get('max-context-chars').value,480000);
  assert.equal(elements.get('max-output-tokens').value,24576);
  assert.equal(elements.get('request-timeout').value,150);
  elements.get('api-key').value='unsaved-test-key';
  elements.get('overview-language').value='formal';
  elements.get('skip-ai').onclick();
  assert.equal(elements.get('api-key').value,'');
  vm.runInContext('openSettings()',context);
  assert.equal(elements.get('overview-language').value,'casual','Cancel discards unsaved preferences');
  vm.runInContext("state.settings={max_context_chars:96000,max_output_tokens:8192,timeout:120,overview_language:'formal',overview_length:'large'}; openSettings()",context);
  assert.equal(elements.get('max-context-chars').value,96000);
  const posted = []; context.posted=posted;
  vm.runInContext("api=async(path,payload)=>{posted.push({path,payload});return {};}; refresh=async()=>{}",context);
  await elements.get('settings-form').onsubmit({preventDefault(){}});
  assert.equal(posted[0].path,'/api/settings');
  assert.equal(posted[0].payload.max_context_chars,96000);
  assert.equal(posted[0].payload.max_output_tokens,8192);
  assert.equal(posted[0].payload.timeout,120);
  assert.equal(posted[0].payload.overview_language,'formal');
  assert.equal(posted[0].payload.overview_length,'large');
  context.document.getElementById('artifact-kind').value='both'; context.document.getElementById('profile').value='semantic';
  await elements.get('send').onclick();
  assert.equal(posted[1].path,'/api/papers/paper1/send');
  assert.equal(posted[1].payload.kind,'both');
  assert.equal(posted[1].payload.profile,'semantic');
  assert.match(html,/id="max-context-chars" type="number" min="4000" max="1000000"/);
  assert.match(html,/id="max-output-tokens" type="number" min="256" max="32000"/);
  assert.match(html,/id="request-timeout" type="number" min="1" max="300"/);
  assert.doesNotMatch(html,/id="appearance-open"|id="appearance-side"|Settings &amp; setup/);
  elements.get('reading-font').value='palatino'; elements.get('reading-font').onchange();
  elements.get('reading-margin').value='wide'; elements.get('reading-margin').onchange();
  assert.equal(storage.get('papers-font'),'palatino'); assert.equal(storage.get('papers-margin'),'wide');
  elements.get('theme-toggle').onclick(); assert.equal(storage.get('papers-theme'),'dark');
  vm.runInContext('goHome()',context); assert.equal(elements.get('reading-bar').hidden,true);
  vm.runInContext('setReadingPreferences(true)',context);
  assert.equal(elements.get('reader-launcher').getAttribute('aria-expanded'),'true');
  assert.equal(elements.get('reading-preferences-dialog').open,true);
  vm.runInContext('setReadingPreferences(false)',context);
  assert.equal(elements.get('reader-launcher').getAttribute('aria-expanded'),'false');
  assert.equal(elements.get('reading-preferences-dialog').open,false);
  assert.doesNotMatch(html,/id="import-open"|id="library-dialog"|Your library/);
  assert.match(html,/id="library-page"/);
  vm.runInContext('showLibrary()',context);
  assert.equal(elements.get('library-page').hidden,false);
  assert.equal(elements.get('workspace').hidden,true);
  assert.equal(elements.get('reader-home').hidden,false);
  vm.runInContext('goHome()',context);
  assert.equal(elements.get('library-page').hidden,true);
  assert.equal(elements.get('reader-home').hidden,true);
  vm.runInContext("tourStep=1;state.papers=[{id:'other',title:'Other'},{id:TOUR_ID,title:'Attention Is All You Need'}];renderLibrary()",context);
  assert.equal(elements.get('paper-list').children[0].children[0].id,'tour-paper');
  assert.equal(elements.get('paper-list').children.length,2,'Tour uses an actual library record, without a fake sample');
  vm.runInContext('tourStep=null',context);
  const remove = elements.get('paper-list').children[1].children[1].children[1];
  const countBeforeRemove = posted.length;
  remove.onclick();
  assert.equal(elements.get('remove-paper-name').textContent, 'Other');
  assert.equal(posted.length, countBeforeRemove, 'Opening confirmation does not delete');
  elements.get('remove-paper-cancel').onclick();
  assert.equal(posted.length, countBeforeRemove, 'Cancel does not delete');
  remove.onclick();
  await elements.get('remove-paper-confirm').onclick();
  assert.equal(posted.at(-1).path, '/api/papers/other/remove');
  assert.equal(elements.get('remove-paper-confirm').disabled, false);
  vm.runInContext("api=async()=>{throw new Error('Paper is busy')}",context);
  await elements.get('remove-paper-confirm').onclick();
  assert.equal(elements.get('remove-paper-error').textContent, 'Paper is busy');
  vm.runInContext("api=async(path,payload)=>{posted.push({path,payload});return {}}",context);

  vm.runInContext("state.settings={endpoint:'https://example.test',model:'saved',has_key:true,kindle_email:'reader@kindle.com'}; openSetup()",context);
  assert.equal(elements.get('setup-model').value,'saved'); assert.equal(elements.get('setup-kindle').value,'reader@kindle.com');
  elements.get('setup-key').value='temporary-test-key';
  await vm.runInContext('completeSetup(false)',context);
  assert.equal(posted.at(-1).payload.onboarding_complete,true);
  assert.equal(elements.get('setup-key').value,'');

vm.runInContext("selected='paper1'; detail={paper:{title:'Fixture'},bento:{figures:[{png:'reader/grid.png',excalidraw:'reader/grid.excalidraw'}]}}; switchTab('overview'); updateShareControls()",context);
assert.equal(elements.get('share-png').hidden,false);
assert.equal(elements.get('share-pdf').disabled,false);
context.document.getElementById('share-kindle').open=true;
elements.get('share-open').onclick();
assert.equal(elements.get('share-kindle').open,false);
assert.equal(elements.get('artifact-kind').value,'bento');
vm.runInContext("switchTab('blog'); updateShareControls()",context);
assert.equal(elements.get('share-png').hidden,true);
assert.equal(elements.get('share-epub').disabled,true);
assert.equal(script.includes('figure-downloads'),false);

  console.log('UI reading controls, setup, Library navigation, rendering, and sandbox checks passed.');
})().catch(error=>{console.error(error);process.exitCode=1;});

// Each new window suppresses all finished history, but announces new failures and live work.
const timersBeforeJobs = timers.length;
vm.runInContext(`state.jobs = [
 ...Array.from({length:8}, (_, i) => ({id:'done'+i,kind:'import',state:'ready',progress:'Imported'})),
 {id:'active',kind:'import',state:'running',progress:'Converting'},
 {id:'failed',kind:'import',state:'failed',error:'Source unavailable',payload:{url:'https://arxiv.org/abs/2501.00001'}}
]; renderJobs()`, context);
const activity = elements.get('jobs');
assert.equal(activity.children.length,1,'Old failures and successes must not replay on launch');
vm.runInContext("state.jobs.push({id:'new-failure',kind:'import',state:'failed',error:'Source unavailable',payload:{url:'https://arxiv.org/abs/2501.00002'}});renderJobs()",context);
assert.equal(activity.children.length,2,'A failure in the current run must appear');
assert.equal(timers.length,timersBeforeJobs,'Active jobs and failures must not schedule dismissal');
assert.equal(elements.get('notifications-toggle').textContent,'2 updates');
elements.get('notifications-toggle').onclick();
assert.equal(elements.get('notifications-toggle').attributes['aria-expanded'],'true');
assert.match(descendants(activity.children[0]).map(e=>e.textContent).join(' '),/in progress/);
assert.match(descendants(activity.children[1]).map(e=>e.textContent).join(' '),/Source unavailable/);
vm.runInContext('renderJobs()',context);
assert.equal(activity.children.length,2,'Unchanged polling cannot duplicate notifications');
const failure=activity.children[1];
descendants(failure).find(e=>e.attributes['aria-label']==='Dismiss paper import').onclick();
vm.runInContext('renderJobs()',context);
assert.equal(activity.children.length,1,'Dismissed failures stay dismissed until their job changes');
vm.runInContext("state.jobs=state.jobs.map(job=>job.id==='active'?{...job,state:'ready',progress:'Saved'}:job);renderJobs()",context);
assert.equal(activity.children.length,1);
assert.match(descendants(activity).map(e=>e.textContent).join(' '),/Paper import ready/);
timers.at(-1)();
assert.equal(activity.children.length,0,'New success toasts expire');
assert.equal(elements.get('notifications-toggle').hidden,true);
vm.runInContext('renderJobs()',context);
assert.equal(activity.children.length,0,'Expired completion does not reappear on polling');
vm.runInContext('jobNotices.clear(); jobsInitialized=false; renderJobs()',context);
assert.equal(activity.children.length,0,'Reopening must not replay even failures from the previous run');
assert.ok(vm.runInContext("state.jobs.some(j=>j.id==='new-failure' && j.error)",context),'Error records remain available');
assert.equal(vm.runInContext("downloadLink('https://evil.test/files/book.epub')",context),null);
assert.equal(vm.runInContext("downloadLink('/api/settings')",context),null);
const timersBeforeActions = timers.length;
vm.runInContext(`state.jobs=[
 {id:'download-action',kind:'export',state:'ready',result:{download_url:'/files/paper/book.epub'}},
 {id:'warning-result',kind:'import',state:'ready',result:{warning:'PDF fallback: EPUB unavailable.'}}
];renderJobs();notice('Could not open paper. Try again.')`,context);
assert.equal(timers.length,timersBeforeActions,'Download links, warnings, and request errors must stay until dismissed');
vm.runInContext('setReadingPreferences(true)',context);
context.document.querySelector = selector => selector === 'dialog[open]' ? element('dialog') : null;
documentEvents.get('keydown')({key:'Escape'});
assert.equal(elements.get('reader-launcher').getAttribute('aria-expanded'),'true','Escape in a dialog must preserve its reading-control trigger');
context.document.querySelector = () => null;
documentEvents.get('keydown')({key:'Escape'});
assert.equal(elements.get('reader-launcher').getAttribute('aria-expanded'),'false','Escape outside a dialog resets reading controls');
assert.match(vm.runInContext("downloadLink('/files/paper/book.epub').href",context), /book.epub\?token=test-session$/);
let downloads = 0;
context.document.body = {...element('body'),append(link){link.click=()=>downloads++;link.remove=()=>{};}};
vm.runInContext(`retries.set('requested-download',{}); state.jobs=[
{id:'requested-download',kind:'export',state:'ready',result:{download_url:'/files/paper/book.epub'}},
{id:'old-download',kind:'export',state:'ready',result:{download_url:'/files/paper/book.epub'}}
]; downloadFinishedExports(state.jobs); downloadFinishedExports(state.jobs);`,context);
assert.equal(downloads,1,'Only a newly requested export starts a download, exactly once');
const clean = value => vm.runInContext(`cleanOverviewCitations(${JSON.stringify(value)})`,context);
assert.equal(clean('Finding [p00001, p00007, p00053]. Another [p00001]. Keep [2025] and x[0].'), 'Finding. Another. Keep [2025] and x[0].');
vm.runInContext(`renderProse(proseTarget, '# Mechanism\\n\\n{{figure:fig1}}', [], [{id:'fig1',png:'reader/overview-figures/a/fig1.png',excalidraw:'reader/overview-figures/a/fig1.excalidraw',caption:'A schematic comparison.',alt:'Confidence and correctness'}])`,context);
assert.ok(descendants(target).some(n=>n.tagName==='FIGURE'));
assert.ok(descendants(target).some(n=>n.tagName==='IMG' && n.alt==='Confidence and correctness'));
vm.runInContext(`renderProse(proseTarget, '{{figure:fig1}}', [], [{id:'fig1',svg:'reader/overview-figures/a/fig1.svg',png:'reader/overview-figures/a/fig1.png',caption:'SVG figure',alt:'SVG explanation'}])`,context);
assert.ok(descendants(target).some(n=>n.tagName==='IMG' && new URL(n.src).pathname.endsWith('fig1.svg')));
assert.ok(!descendants(target).some(n=>n.tagName==='A' && n.textContent==='Download editable Excalidraw'));
vm.runInContext(`renderProse(proseTarget, '{{figure:fig1}}', [], [{id:'fig1',svg:'reader/overview-figures/a/fig1.svg',design:{layout:'bento',packing:{rows:[{cards:[1,0]}]},nodes:[
{title:'Results',body:'Measured comparison.',visual:{kind:'metrics',items:[{label:'Model',value:'0.7'}],caption:'Held-out AUROC.'}},
{title:'Mechanism',body:'A supported process.',visual:{kind:'flow',steps:['Input','Output'],caption:'Input feeds output.'}}
]}}])`,context);
assert.deepEqual(descendants(target).filter(n=>n.tagName==='H3').map(n=>n.textContent),['Mechanism','Results']);
for (const text of ['Input → Output','Input feeds output.','Model: 0.7','Held-out AUROC.']) {
  assert.ok(descendants(target).some(n=>n.textContent===text),'Transcript preserves '+text);
}
vm.runInContext(`renderProse(proseTarget, '{{figure:fig1}}', [], [{id:'fig1',svg:'https://evil.test/track'}])`,context);
assert.ok(!descendants(target).some(n=>n.tagName==='IMG'));
vm.runInContext(`renderProse(proseTarget, '{{figure:fig1}}', [], [{id:'fig1',png:'https://evil.test/track',excalidraw:'../secret'}])`,context);
assert.ok(!descendants(target).some(n=>n.tagName==='IMG'));

vm.runInContext("renderProse(proseTarget, '| Method | Evidence |\\n| --- | --- |\\n| Probe | **Held-out** results |')",context);
assert.ok(descendants(target).some(n=>n.tagName==='TABLE'));
assert.ok(descendants(target).some(n=>n.tagName==='TH' && n.attributes.scope==='col'));
assert.ok(descendants(target).some(n=>n.tagName==='STRONG'));

vm.runInContext("state.jobs=[]; document.hidden=false; schedulePoll()", context);
assert.equal(timerDelays.at(-1),10000,'Idle polling backs off');
vm.runInContext("state.jobs=[{state:'running'}]; schedulePoll()", context);
assert.equal(timerDelays.at(-1),2000,'Active jobs remain responsive');
vm.runInContext("document.hidden=true; schedulePoll()", context);
assert.equal(timerDelays.at(-1),30000,'Hidden windows back off further');
(async () => {
  let finish;
  context.testGate = new Promise(resolve => { finish = resolve; });
  vm.runInContext('refreshing=null; var testRefreshCalls=0; refreshState=async()=>{testRefreshCalls++;await testGate}',context);
  const first = originalRefresh(), second = originalRefresh();
  assert.equal(first,second,'Concurrent refreshes share one request');
  assert.equal(vm.runInContext('testRefreshCalls',context),1);
  finish(); await first; await originalRefresh();
  assert.equal(vm.runInContext('testRefreshCalls',context),2,'Refresh becomes available after completion');
})().catch(error=>{console.error(error);process.exitCode=1;});

vm.runInContext("switchTab('blog')", context);
assert.equal(elements.get('blog').hidden, false);
assert.equal(elements.get('overview').hidden, true);
assert.equal(elements.get('tab-blog').attributes['aria-selected'], 'true');
elements.get('tab-blog').onkeydown({key:'ArrowLeft',preventDefault(){}});
assert.equal(elements.get('overview').hidden, false);
elements.get('tab-overview').onkeydown({key:'ArrowLeft',preventDefault(){}});
assert.equal(elements.get('paper').hidden, false);
assert.match(html, /Generate a visual overview after importing/);
assert.doesNotMatch(html, /id="(?:blog-pdf|bento-pdf|paper-pdf|kindle-open)"/);
assert.match(html, /id="share-open".*aria-label="Share"/);
assert.match(html, /<details id="share-kindle">/);
assert.equal(vm.runInContext("downloadLink('/files/paper1/reader/fig1.png').textContent",context), 'Save PNG');

(async () => {
  const originalMatchMedia = context.window.matchMedia;
  let closed = 0, options, frames;
  context.motionDialog = {
    close(){ closed++; }, getAnimations(){ return []; },
    animate(nextFrames,nextOptions){ frames=nextFrames;options=nextOptions;return {finished:Promise.resolve()}; }
  };
  vm.runInContext('dismissDialog(motionDialog,{detail:1})',context);
  await Promise.resolve();
  assert.equal(closed,1);
  assert.equal(options.duration,150);
  assert.ok(frames[1].transform);
  context.window.matchMedia = () => ({matches:true});
  vm.runInContext('dismissDialog(motionDialog,{detail:1})',context);
  await Promise.resolve();
  assert.equal(closed,2);
  assert.equal(options.duration,100);
  assert.equal(frames[1].transform,undefined,'Reduced motion fades without movement');
  context.window.matchMedia = originalMatchMedia;
})().catch(error=>{console.error(error);process.exitCode=1;});
