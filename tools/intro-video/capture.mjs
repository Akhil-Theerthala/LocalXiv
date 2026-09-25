// Captures app screenshots into public/ from a temporary server seeded with the bundled sample paper.
import {spawn} from 'node:child_process';
import {copyFileSync, mkdtempSync, writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {randomBytes} from 'node:crypto';
import {chromium} from 'playwright';

const repo = new URL('../../', import.meta.url).pathname;
const browserPath = new URL('node_modules/.remotion/chrome-headless-shell/mac-arm64/chrome-headless-shell-mac-arm64/chrome-headless-shell', import.meta.url).pathname;
const out = new URL('public/', import.meta.url).pathname;
const token = randomBytes(24).toString('hex');

const server = spawn(join(repo, '.venv/bin/python'), ['-c',
  'import os,sys; from app.server import make_server; s = make_server(sys.argv[1], 0, os.environ["CAPTURE_TOKEN"]); print(s.server_port, flush=True); s.serve_forever()',
  mkdtempSync(join(tmpdir(), 'localxiv-capture-'))], {cwd: repo, env: {...process.env, CAPTURE_TOKEN: token}, stdio: ['ignore', 'pipe', 'inherit']});
const port = await new Promise(resolve => server.stdout.once('data', data => resolve(String(data).trim())));

const browser = await chromium.launch({executablePath: browserPath});
const page = await browser.newPage({viewport: {width: 1440, height: 900}, deviceScaleFactor: 2});
const rects = {};
const shot = async (name, options = {}) => {
  await page.waitForTimeout(700);
  await page.screenshot({path: out + name + '.png', ...options});
};
const rect = async (name, selector) => {
  rects[name] = await page.locator(selector).first().boundingBox();
};

// Shows the saved Overview and Blog tabs without a real AI connection. No provider call is made.
const connected = settings => ({...settings, model: 'demo', has_key: true});
await page.route('**/api/state', async route => {
  const response = await route.fetch(), state = await response.json();
  await route.fulfill({response, json: {...state, settings: connected(state.settings)}});
});
await page.route('**/api/settings', async route => {
  const response = await route.fetch();
  await route.fulfill({response, json: connected(await response.json())});
});

try {
  await page.goto(`http://127.0.0.1:${port}/#token=${token}`);
  await page.waitForLoadState('networkidle');
  await page.getByRole('button', {name: 'Skip setup'}).click();
  await page.click('#tour-skip');
  await shot('home');
  await page.fill('#home-url', 'https://arxiv.org/abs/1706.03762');
  await rect('homeUrl', '#home-url');
  await rect('homeAdd', '#empty-import');
  // Prefix widths let the video reveal the typed link one character at a time.
  Object.assign(rects.homeUrl, await page.$eval('#home-url', input => {
    const context = document.createElement('canvas').getContext('2d'), style = getComputedStyle(input);
    context.font = style.font;
    return {padding: parseFloat(style.paddingLeft) + parseFloat(style.borderLeftWidth),
      prefixes: [...input.value].map((_, i) => context.measureText(input.value.slice(0, i + 1)).width)};
  }));
  await shot('home-filled');
  await page.fill('#home-url', '');
  await page.click('#library-open');
  await shot('library');
  await page.locator('#paper-list .library-card>button').first().click();
  await page.click('#tab-paper');
  await shot('paper');
  await page.click('#reader-launcher');
  await shot('paper-preferences');
  await page.selectOption('#text-size', '20');
  await page.selectOption('#reading-margin', 'balanced');
  await page.keyboard.press('Escape');
  await shot('paper-large');
  await page.click('#reader-launcher');
  await page.selectOption('#text-size', '16');
  await page.selectOption('#reading-margin', 'narrow');
  await page.keyboard.press('Escape');
  await page.click('#theme-toggle');
  await shot('paper-dark');
  await page.click('#theme-toggle');
  await page.click('#tab-overview');
  await shot('overview');
  await page.click('#tab-blog');
  await shot('blog');
  await shot('blog-full', {fullPage: true});
  await page.click('#share-open');
  await shot('share');
  await page.click('summary:has-text("Send to Kindle")');
  await shot('share-kindle');
  await page.keyboard.press('Escape');
} finally {
  writeFileSync(out + 'rects.json', JSON.stringify(rects, null, 2));
  copyFileSync(join(repo, 'app/assets/icon.svg'), out + 'icon.svg');
  copyFileSync(join(repo, 'docs/attention_figure.png'), out + 'attention_figure.png');
  await browser.close();
  server.kill();
}
