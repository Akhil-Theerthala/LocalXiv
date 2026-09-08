/* Render completed local artifacts for human review; never fetch web resources. */
const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const {execFileSync} = require('node:child_process');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || '/Users/silver/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const escape = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

(async () => {
  const records = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const wanted = new Set(process.argv.slice(3));
  const browser = await chromium.launch({headless:true});
  const page = await browser.newPage({viewport:{width:1440,height:1320}, deviceScaleFactor:1});
  await page.route(/^https?:/, route => route.abort());
  try {
    for (const [id, record] of Object.entries(records)) {
      if (record.status !== 'converted' || (wanted.size && !wanted.has(id))) continue;
      const root = path.resolve(record.directory);
      const output = path.join(root, 'visual-review');
      if (fs.existsSync(path.join(output, 'review.png'))) continue;
      fs.mkdirSync(output, {recursive:true});
      const document = JSON.parse(fs.readFileSync(path.join(root, 'document.json'), 'utf8'));
      const chapters = document.chapters.map(c => ({...c, html:fs.readFileSync(path.join(root,c.path),'utf8')}));
      const first = chapters[0];
      const figure = chapters.find(c => /<figure\b[\s\S]*?<img\b/.test(c.html));
      const table = chapters.find(c => /<table\b(?![^>]*ltx_eqn_table)/.test(c.html));
      const code = chapters.find(c => /<pre\b/.test(c.html));
      const math = chapters.find(c => /<(?:\w+:)?math\b[^>]*display="block"/.test(c.html));
      const panels = [{kind:'Opening', chapter:first, selector:'body'}];
      if (figure) panels.push({kind:'Figure', chapter:figure, selector:'figure:has(img)'});
      if (table || code) panels.push({kind:table?'Table':'Code', chapter:table||code, selector:table?'table:not(.ltx_eqn_table)':'pre'});
      if (math) {
        const compatibility = path.join(output, 'compatibility');
        fs.mkdirSync(compatibility, {recursive:true});
        execFileSync('/usr/bin/unzip', ['-qo', path.join(root,'paper.epub'), '-d', compatibility]);
        panels.push({kind:'Kindle equation images', chapter:math, selector:'.display-math',
          file:path.join(compatibility,'EPUB',math.path.replace(/^reader\//,''))});
      } else panels.push({kind:'Ending', chapter:chapters.at(-1), selector:'body', ending:true});
      const html = '<!doctype html><meta charset="utf-8"><style>body{margin:20px;font:15px system-ui;background:#eee}h1{font-size:22px}main{display:grid;grid-template-columns:1fr 1fr;gap:16px}section{background:white}header{padding:8px}iframe{border:0;width:100%;height:560px}</style>' +
        '<h1>'+escape(id+' · '+document.title)+'</h1><main>'+panels.map((p,i) => '<section><header>'+escape(p.kind+' · '+p.chapter.path)+'</header><iframe name="panel'+i+'" src="'+escape(pathToFileURL(p.file||path.join(root,p.chapter.path)).href)+'"></iframe></section>').join('')+'</main>';
      const gallery = path.join(output, 'review.html');
      fs.writeFileSync(gallery, html);
      await page.goto(pathToFileURL(gallery).href, {waitUntil:'load'});
      for (let i=0; i<panels.length; i++) {
        const frame = page.frame({name:'panel'+i});
        let choices = frame.locator(panels[i].selector);
        if (panels[i].kind === 'Table') choices = choices.filter({hasText:/\S/});
        const locator = choices.first();
        if (await locator.count()) await locator.scrollIntoViewIfNeeded();
        if (panels[i].ending) await frame.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
      }
      await page.screenshot({path:path.join(output,'review.png'), fullPage:true});
      fs.writeFileSync(path.join(output,'locations.json'), JSON.stringify(panels.map(({kind,chapter,selector,ending,file}) => ({kind,chapter:chapter.path,selector,ending,file})), null,2));
      console.log('RENDERED', id, panels.length);
    }
  } finally { await browser.close(); }
})().catch(error => {console.error(error); process.exitCode=1;});
