# Front-end deepening implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. AGENTS.md applies to every task: invoke `ponytail` before writing code and `pstack:unslop` before writing any prose, commit message, or comment.

**Goal:** The browser front end reads its palette, reading typography, layout state and markup from five deep modules instead of one 1,019-line script and two appended stylesheets, and every Figure render can follow the reader's theme.

**Architecture:** `app.css :root` stays the one source of colour. `app/static/appearance.js` maps Reading preferences to values with no DOM; the page root and the Paper's reader iframe are its adapters. `app/static/view.js` owns the reading layout state. `app/static/render.js` draws job notices, prose, library, recommendations and contents into elements it is handed. `papers/figures/palette.py` gives the Figure library a `Palette`, and `Figure.build` writes a dark SVG beside the light assets. `app.js` keeps state and wiring and becomes an ES module so the tests can import what they test.

**Tech Stack:** Vanilla HTML, CSS and JavaScript ES modules with no build step; Node 22 plain scripts with `node:assert`; Python 3 `unittest`; the WebKit renderer `papers/html-snapshot`.

**Spec:** [docs/superpowers/specs/2026-09-22-front-end-deepening-design.md](../specs/2026-09-22-front-end-deepening-design.md). Read it first. The review that produced it lives outside the repository; the spec carries everything the plan argues from.

## Global constraints

- **Precondition.** The working tree has uncommitted edits to `app/server.py`, `app/static/app.js`, `app/static/index.html`, `papers/coordinator.py` and others. The user commits or stashes them before execution starts. Every line number in this plan was read from that working tree on 2026-09-22; the executor branches from the resulting commit with `git switch -c front-end-deepening` and treats each line number as an anchor to confirm with the named function or selector, not as a fact.
- `tests/` is gitignored (`.gitignore` line `tests/`). Every task runs its tests locally. No commit step adds a test file.
- Run Python tests with `.venv/bin/python -m unittest tests.<module> -v` from the repository root. Run node tests with `node tests/<file>` from the repository root. Node is 22; `package.json` has no `"type"` field, so `.js` files are CommonJS and every new node test is a `.mjs` file that uses `import`.
- Phase 6 needs the renderer. Build it and export its path in every shell that runs those tests:

```sh
xcrun swiftc -O papers/HTMLSnapshot.swift -o papers/html-snapshot
export LOCALXIV_HTML_RENDERER="$PWD/papers/html-snapshot"
```

- Until Task 10 rewrites it, `tests/test_job_notices.js` slices `app.js` by string index: from `function expireToast(` to `function downloadFinishedExports(`, and from `function renderJobs(` to `$('notifications-toggle').onclick`. Run `node tests/test_job_notices.js` after every `app.js` edit in Tasks 1 to 9, and do not insert statements inside those two ranges.
- Commit messages are one imperative sentence in sentence case with no prefix and no trailer, as in `git log`: `Read the reader stylesheet from the page tokens`. The user's CLAUDE.md forbids `Co-Authored-By` lines; that rule wins over any session reminder.
- Merge the branch with `git merge --no-ff`. Never fast-forward.
- `CONTEXT.md` terms are the vocabulary: Paper, Overview, Blog, Blog figure, Figure library, Figure render, Scene, Scene layout. Task 15 adds Reading preferences and Figure palette.
- Zero visual change is the default. A task that moves a pixel says so in its own text; every other task's browser check expects the page to look the same.
- Manual browser checks name the widths 1280, 800 and 390. An executor without a browser writes `Not verified: browser` in the task report instead of claiming the check.

## Decisions made in this plan

The spec left these to the plan. Each is listed so the user can veto it before execution.

1. **`app.js` becomes `type="module"`.** Nothing outside `app.js` reads its globals: `index.html` has no inline handlers (the CSP forbids them), and `window.MathJax` is set by `math-config.js`, a classic script. Module scripts and `defer` classic scripts share one execution list in document order, so `math-config.js` and `mathjax.js` still run first.
2. **The palette has one source, `app.css :root`.** `appearance.js` never holds a colour. The reader iframe adapter reads `getComputedStyle(document.documentElement).getPropertyValue('--ink')` and friends, and reads the computed `backgroundColor` of `.document-pane` for the canvas, which already resolves page-versus-paper by breakpoint and the dark mobile `--paper:#000` override at `reader-layout.css:78`. The `window.innerWidth <= 850` test in `styleReader` goes away.
3. **The iframe stylesheet keeps `!important`.** The converted Paper ships its own `reading.css`; the app must win.
4. **Two adapters, not three.** `papers/document.py:26` stays the light-only EPUB adapter (it holds no colour; Kindle applies its own typography). `app/macos/PapersToKindle.swift:98` keeps its one hex value.
5. **Tokens by exact value.** Type sizes 11, 12, 13, 14 and 16 px; radii 10, 16, 20, 24, 999 px and `50px` pills; the three scrims; the three easing curves. Shadows are the one deliberate visual normalisation: nine one-off tints become three roles, listed in Task 5 with their before and after values.
6. **Durations round to three tokens.** 150 ms covers today's 150 and 160; 200 ms covers 180 and 200; 280 ms covers 250, 280 and 320. No change exceeds 40 ms.
7. **Spacing, letter-spacing and line-height stay raw.** Tokenising them touches hundreds of declarations for no behaviour a test can check.
8. **Breakpoint blocks merge only when a script proves the cascade is unchanged.** Moving a rule to the end of the file can only change the outcome where an unscoped rule of equal specificity sets the same property later in the file. Task 7 ships a script that lists same-selector collisions; the executor deletes the properties that are already dead, moves the blocks, reruns the script, and checks the page at three widths. Equal-specificity collisions with different selector text are not detected; that residual risk is why the task ends with a browser check.
9. **`view.js` derives, it does not decide.** The module maps a view value to flags. Which view to show stays in `app.js`.
10. **Renderers receive the document and an actions object.** No renderer reads `document`, `state`, `selected`, or `detail` from module scope. `app.js` computes what to draw (filtered papers, contents entries) and passes it in.
11. **`LIGHT` is byte-identical to today's constants** so `tests/baseline_scenes.py --compare` reports `same` through Task 13. `DARK` is new. Hue alignment with the app tokens is one later edit in `palette.py`.
12. **The figure font stays `Arial, sans-serif`.** The editable SVG export opens on machines without the app's fonts.
13. **The dark figure is a real SVG; the light one stays a PNG wrapped in SVG.** They render differently: the dark one is drawn by the browser's text engine from Arial, the light one is a raster. That is acceptable for an on-screen theme; exports stay light.
14. **Old figures have no dark source.** `app.js` swaps only images that carry `data-dark-src`, so figures saved before Task 14 keep their light source in dark mode.
15. **The dead-rule deletion is recorded in `docs/cleanup.md`**, as AGENTS.md requires for planned cleanup runs. That file is fully checked off today, so no prior cleanup blocks this plan.
16. **Test stubs live in one file.** `tests/dom_stub.mjs` holds the fake `Element` and `document` every node test shares.

## File map

| Path | Responsibility after this plan |
| --- | --- |
| `app/static/index.html` | Page shell; loads `app.js` as a module |
| `app/static/app.css` | Token tier, then every rule; one `@media(max-width:850px)` block and one `@media(max-width:600px)` block at the end |
| `app/static/reader-layout.css` | Reader layout; references tokens only |
| `app/static/appearance.js` | Reading preferences to values: validation, theme resolution, root properties, reader stylesheet. No DOM |
| `app/static/view.js` | One view value to every hidden flag, body class and `aria-current`. Takes the document |
| `app/static/render.js` | `createNode`, `JobNotices`, `renderProse`, `renderLibrary`, `renderRecommendations`, `renderContents`. Takes elements and actions |
| `app/static/app.js` | State, fetches, wiring, dialogs, figure viewer, tour, reader iframe adapter |
| `app/server.py:396` | Static map gains the three modules |
| `papers/figures/palette.py` | `Palette`, `LIGHT`, `DARK` |
| `papers/figures/layout.py` | Geometry constants only; colours move out |
| `papers/figures/render.py` | Drawers take a `palette`; `markers(palette)`, `page_style(palette)`; `rasterize` writes the dark SVG |
| `papers/figures/__init__.py` | `Figure.build` composes light and dark |
| `papers/overview_workflow.py:29` | `FIGURE_ASSET_KEYS` gains `svg_dark` |
| `tests/dom_stub.mjs` | Shared fake DOM for node tests (local, untracked) |
| `tests/test_appearance.mjs`, `tests/test_view.mjs`, `tests/test_render.mjs`, `tests/test_css.mjs`, `tests/css_collisions.mjs` | Node tests and the cascade script (local, untracked) |
| `tests/test_job_notices.js` | Rewritten to import `JobNotices` (local, untracked) |
| `tests/test_palette.py` | Palette tests (local, untracked) |

## Phase 1: modules

### Task 1: Load `app.js` as an ES module and serve the new files

**Files:**
- Modify: `app/static/index.html:2` (the three `<script>` tags)
- Modify: `app/static/app.js:1-3`
- Modify: `app/server.py:396` (the static map)
- Test: `node --check app/static/app.js`, `node tests/test_job_notices.js`, browser

**Interfaces:**
- Produces: `app.js` may use `import` from `./appearance.js`, `./view.js` and `./render.js`; the server answers `/static/appearance.js`, `/static/view.js`, `/static/render.js`.

- [ ] **Step 1: Change the script tag**

In `app/static/index.html:2` replace `<script src="/static/app.js" defer></script>` with `<script src="/static/app.js" type="module"></script>`. Leave `math-config.js` and `mathjax.js` as `defer` classic scripts.

- [ ] **Step 2: Drop the strict-mode directive**

Modules are strict. In `app/static/app.js` delete line 2, `'use strict';`. Keep the comment on line 1.

- [ ] **Step 3: Extend the static map**

In `app/server.py:396` change the map to:

```python
static = {'/static/math-config.js': 'math-config.js', '/': 'index.html', '/static/app.js': 'app.js',
          '/static/appearance.js': 'appearance.js', '/static/view.js': 'view.js', '/static/render.js': 'render.js',
          '/static/app.css': 'app.css', '/static/reader-layout.css': 'reader-layout.css'}.get(url.path)
```

- [ ] **Step 4: Create the three empty modules**

Create `app/static/appearance.js`, `app/static/view.js` and `app/static/render.js`, each containing one line: `// Filled in by the front-end deepening plan.` Tasks 2, 8 and 10 replace them.

- [ ] **Step 5: Run the checks**

Run: `node --check app/static/app.js && node tests/test_job_notices.js`
Expected: no syntax error; `Job notification regressions passed.`

- [ ] **Step 6: Browser check**

Run: `.venv/bin/python -m app.server --port 8765 --data-dir /tmp/localxiv-dev --open`
Open the page. Expected: the home page renders, the theme toggle flips the page, and the sample Paper's Overview and Blog prose render; any formula in them typesets, which shows MathJax still loads before the module. Check the console for no error.

- [ ] **Step 7: Commit**

```sh
git add app/static/index.html app/static/app.js app/server.py app/static/appearance.js app/static/view.js app/static/render.js
git commit -m "Load the front end as ES modules and serve the module files"
```

## Phase 2: Appearance module

### Task 2: `appearance.js` maps Reading preferences to values

**Files:**
- Create: `app/static/appearance.js`
- Test: `tests/test_appearance.mjs` (new, local)

**Interfaces:**
- Produces:
  - `READING_SIZES = ['14','16','18','20','22']`, `THEMES = ['system','light','dark']`
  - `READING_FONTS`, `READING_WIDTHS`, `MOBILE_GUTTERS`: the three maps now at `app.js:734-735,749`
  - `readPreferences(storage) -> {size, theme, font, margin}`: reads the four `papers-*` keys with `storage.getItem` and falls back to `'16'`, `'system'`, `'palatino'`, `'narrow'` for a missing or unknown value.
  - `resolveTheme(preference, systemDark) -> 'light' | 'dark'`
  - `rootProperties({size, font, margin}) -> object` of the four custom properties `applyAppearance` sets today.
  - `readerStylesheet({theme, size, fontStack, canvas, ink, paper, accent, line, figureMaxHeight}) -> string`: the stylesheet `styleReader` builds today, with every colour taken from the arguments.

- [ ] **Step 1: Write the failing test**

```js
// tests/test_appearance.mjs
import assert from 'node:assert/strict';
import {readPreferences, resolveTheme, rootProperties, readerStylesheet, READING_FONTS} from '../app/static/appearance.js';

const storage = values => ({getItem: key => values[key] ?? null});

assert.deepEqual(readPreferences(storage({})), {size: '16', theme: 'system', font: 'palatino', margin: 'narrow'});
assert.deepEqual(readPreferences(storage({'papers-text-size': '20', 'papers-theme': 'dark', 'papers-font': 'georgia', 'papers-margin': 'wide'})),
  {size: '20', theme: 'dark', font: 'georgia', margin: 'wide'});
assert.equal(readPreferences(storage({'papers-text-size': '99'})).size, '16', 'an unknown size falls back');
assert.equal(readPreferences(storage({'papers-font': 'comic'})).font, 'palatino', 'an unknown font falls back');

assert.equal(resolveTheme('system', true), 'dark');
assert.equal(resolveTheme('system', false), 'light');
assert.equal(resolveTheme('light', true), 'light');

assert.deepEqual(rootProperties({size: '18', font: 'georgia', margin: 'balanced'}), {
  '--reading-size': '18px', '--reading-font': 'Georgia,serif', '--reading-width': '720px', '--mobile-reading-gutter': '24px'});

const css = readerStylesheet({theme: 'dark', size: '18', fontStack: READING_FONTS.charter, canvas: 'rgb(16, 18, 15)',
  ink: 'rgb(238, 238, 222)', paper: 'rgb(16, 18, 15)', accent: 'rgb(209, 222, 168)', line: 'rgb(52, 57, 46)', figureMaxHeight: 400});
assert.match(css, /html\{font-size:18px!important;color-scheme:dark;/);
assert.match(css, /background:rgb\(16, 18, 15\)!important/);
assert.match(css, /a\{color:rgb\(209, 222, 168\)!important\}/);
assert.match(css, /figure img\{max-height:400px!important/);
assert.match(css, /font-family:Charter,Georgia,serif!important/);
assert.doesNotMatch(css, /#[0-9a-f]{3,8}\b/i, 'the stylesheet carries no colour of its own');
console.log('Appearance mapping passed.');
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `node tests/test_appearance.mjs`
Expected: FAIL with `SyntaxError: The requested module ... does not provide an export named 'readPreferences'`.

- [ ] **Step 3: Write the module**

```js
// Reading preferences to values. No DOM: the page root and the reader iframe apply what this returns,
// and app.css :root is the one place a colour is written.
export const READING_SIZES = ['14', '16', '18', '20', '22'];
export const THEMES = ['system', 'light', 'dark'];
export const READING_FONTS = {georgia: 'Georgia,serif', charter: 'Charter,Georgia,serif', palatino: 'Palatino,"Palatino Linotype",serif', system: '-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif'};
export const READING_WIDTHS = {wide: '560px', balanced: '720px', narrow: '880px'};
export const MOBILE_GUTTERS = {wide: '34px', balanced: '24px', narrow: '16px'};

const pick = (value, allowed, fallback) => allowed.includes(value) ? value : fallback;

export function readPreferences(storage) {
  return {
    size: pick(storage.getItem('papers-text-size'), READING_SIZES, '16'),
    theme: pick(storage.getItem('papers-theme'), THEMES, 'system'),
    font: pick(storage.getItem('papers-font'), Object.keys(READING_FONTS), 'palatino'),
    margin: pick(storage.getItem('papers-margin'), Object.keys(READING_WIDTHS), 'narrow'),
  };
}

export function resolveTheme(preference, systemDark) {
  return preference === 'system' ? (systemDark ? 'dark' : 'light') : preference;
}

export function rootProperties({size, font, margin}) {
  return {'--reading-size': size + 'px', '--reading-font': READING_FONTS[font], '--reading-width': READING_WIDTHS[margin], '--mobile-reading-gutter': MOBILE_GUTTERS[margin]};
}

export function readerStylesheet({theme, size, fontStack, canvas, ink, paper, accent, line, figureMaxHeight}) {
  return `html{font-size:${size}px!important;color-scheme:${theme};height:auto!important;background:${canvas}!important;color:${ink}!important}`
    + `body{font:inherit!important;font-family:${fontStack}!important;font-size:${size}px!important;line-height:1.85!important;max-width:none!important;margin:0!important;padding:12px 0 25px!important;height:auto!important;min-height:0!important;background:inherit!important;color:inherit!important}`
    + `h1,h2,h3,h4{font-family:'Avenir Next',sans-serif!important;line-height:1.35!important;font-weight:600!important}h1{font-size:1.5em!important}h2{font-size:1.3em!important}`
    + `a{color:${accent}!important}img,svg{max-width:100%;height:auto;object-fit:contain}`
    + `figure img{max-height:${figureMaxHeight}px!important;width:100%!important;cursor:zoom-in;background:${paper};border-radius:10px}`
    + `figcaption{font:12px/1.65 'Avenir Next',sans-serif!important;margin:12px 0!important}`
    + `math[display=block]{display:block;overflow-x:auto;max-width:100%;padding:10px 0}table{display:block;overflow:auto;max-width:100%;font-size:.85em}pre{overflow:auto;white-space:pre-wrap}`
    + `p{margin:0 0 1.2em!important}body>:first-child{margin-top:0!important}`
    + `*{scrollbar-width:thin;scrollbar-color:${line} transparent}::-webkit-scrollbar{width:5px;height:5px}::-webkit-scrollbar-thumb{background:${line};border-radius:8px}`;
}
```

Compare the template against `app.js:770` line by line before committing. The only differences are the six colour substitutions and the `${theme}` in `color-scheme`.

- [ ] **Step 4: Run the test to verify it passes**

Run: `node tests/test_appearance.mjs`
Expected: `Appearance mapping passed.`

- [ ] **Step 5: Commit**

```sh
git add app/static/appearance.js
git commit -m "Map reading preferences to values in one module with no DOM"
```

### Task 3: The page root and the reader iframe become adapters

**Files:**
- Modify: `app/static/app.js:730-772` (`readingSize` through `styleReader`) and `:795-798` (the four preference handlers)
- Modify: `app/static/reader-layout.css:40,43`
- Modify: `app/static/app.css:94,97`
- Test: `tests/test_appearance.mjs`, `tests/test_job_notices.js`, browser

**Interfaces:**
- Consumes: everything Task 2 exports.
- Produces: `preferences` (module-level object in `app.js`), `applyAppearance()`, `styleReader()`, `token(name)`.

- [ ] **Step 1: Replace the preference state**

Delete `app.js:730-740` (from `let readingSize = ...` through `const systemTheme = ...`) and write:

```js
import {readPreferences, resolveTheme, rootProperties, readerStylesheet, READING_FONTS} from './appearance.js';
const preferences = readPreferences(localStorage);
const systemTheme = window.matchMedia('(prefers-color-scheme: dark)');
const token = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
```

Put the `import` line at the top of the file, after the comment on line 1. Module imports are hoisted, but the file reads better with the import first.

- [ ] **Step 2: Rewrite `applyAppearance`**

```js
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
  styleReader();
  if (themeChanged) {
    void document.documentElement.offsetHeight;
    window.requestAnimationFrame(() => document.documentElement.classList.remove('theme-changing'));
  }
}
```

- [ ] **Step 3: Rewrite `styleReader`**

```js
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
    ink: token('--ink'), paper: token('--paper'), accent: token('--accent'), line: token('--line'),
    figureMaxHeight: Math.round(window.innerHeight * .55)});
  resizeReader();
}
```

- [ ] **Step 4: Rewrite the four handlers**

Replace `app.js:795-798` with:

```js
const savePreference = (key, field, value) => { preferences[field] = value; localStorage.setItem(key, value); applyAppearance(); };
$('text-size').onchange = () => savePreference('papers-text-size', 'size', $('text-size').value);
$('theme-toggle').onclick = () => savePreference('papers-theme', 'theme', document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark');
$('reading-font').onchange = () => savePreference('papers-font', 'font', $('reading-font').value);
$('reading-margin').onchange = () => savePreference('papers-margin', 'margin', $('reading-margin').value);
```

`$('options-theme').onclick = () => $('theme-toggle').onclick();` at `app.js:897` still works. Run `grep -n "readingSize\|readingTheme\|readingFont\b\|readingMargin\|readingWidths\|readingFonts" app/static/app.js` and expect no output.

- [ ] **Step 5: Point the figure frames at the tokens**

`app/static/reader-layout.css:40`: `background:#fffdf7` becomes `background:var(--paper)`.
`app/static/reader-layout.css:43`: `color:#51594a` becomes `color:var(--muted)`.
`app/static/app.css:94` and `:97`: `background:#fffdf7` becomes `background:var(--paper)`.

This is a deliberate visual change in dark mode only: the frame around a figure follows the paper colour instead of staying cream.

- [ ] **Step 6: Run the checks**

Run: `node --check app/static/app.js && node tests/test_appearance.mjs && node tests/test_job_notices.js && grep -c '#[0-9a-f]\{6\}' app/static/app.js`
Expected: both tests pass; the grep prints `0`.

- [ ] **Step 7: Browser check**

Open the sample Paper's Paper tab at 1280 and 390. Expected: the reader canvas matches the document pane in light and dark; toggling the theme recolours the iframe text and links; changing the size and font changes the iframe. At 390 the canvas is the page colour, as before.

- [ ] **Step 8: Commit**

```sh
git add app/static/app.js app/static/reader-layout.css app/static/app.css
git commit -m "Read the reader stylesheet from the page tokens"
```

## Phase 3: stylesheet scale tier

### Task 4: Delete dead rules and contradictions, guarded by a selector test

**Files:**
- Modify: `app/static/app.css` (lines listed below), `app/static/index.html:18-19`
- Modify: `docs/cleanup.md` (append a section)
- Test: `tests/test_css.mjs` (new, local)

**Interfaces:**
- Produces: `tests/test_css.mjs`, which later tasks extend. It parses both stylesheets and asserts every `.class` and `#id` in a selector appears in `index.html` or a file under `app/static/*.js`.

- [ ] **Step 1: Write the failing test**

```js
// tests/test_css.mjs
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'app', 'static');
const read = name => fs.readFileSync(path.join(root, name), 'utf8');
const sheets = {'app.css': read('app.css'), 'reader-layout.css': read('reader-layout.css')};
const usage = read('index.html') + fs.readdirSync(root).filter(name => name.endsWith('.js')).map(read).join('\n');
// Classes the native window adds from Swift (app/macos/PapersToKindle.swift:71).
const external = new Set(['native-window']);

function selectors(css) {
  const out = [];
  const stripped = css.replace(/\/\*[\s\S]*?\*\//g, '');
  const pattern = /([^{}]+)\{/g;
  for (const match of stripped.matchAll(pattern)) {
    const prelude = match[1].trim();
    if (prelude.startsWith('@')) continue;
    out.push(prelude);
  }
  return out;
}

const dead = [];
for (const [name, css] of Object.entries(sheets)) {
  for (const selector of selectors(css)) {
    for (const [, kind, ident] of selector.matchAll(/([.#])([A-Za-z_][\w-]*)/g)) {
      if (external.has(ident)) continue;
      if (!usage.includes(ident)) dead.push(`${name}: ${kind}${ident} in "${selector}"`);
    }
  }
}
assert.deepEqual(dead, [], 'selectors that match nothing in index.html or the scripts');
console.log('Stylesheet selectors are all in use.');
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `node tests/test_css.mjs`
Expected: FAIL listing `.chapter-bar`, `.export`, `.export-body`, `#appearance-open`, `#appearance-dialog`, `.empty`, `.privacy`, `.figure-downloads` and `.toast-fading`. If it lists another selector, confirm with `grep -rn <name> app/static` that nothing sets it, then delete that rule too and name it in the commit message.

- [ ] **Step 3: Delete the dead groups**

Delete these lines from `app/static/app.css`, confirming each selector before deleting: 38 (`#appearance-open`), 45, 46, 47 (`.export`), 66, 67 (`.chapter-bar`), 69, 70, 71, 72 (`.empty`), 84 (`.privacy`), 92 (`#appearance-dialog`), 142 (`#appearance-open`), 145, 146 (`.export`), 147, 148 (`.chapter-bar`), 149, 150, 151 (`.empty`), 291, 306, 307, 308, 369 (`.chapter-bar`), 481 (`.figure-downloads`), 482 (`.chapter-bar`). In line 284 remove `,.chapter-bar` from the selector list. Delete lines 409 and 412 (`.toast-fading`; nothing adds that class).

- [ ] **Step 4: Delete the redundant and contradicted rules**

- Line 50 `.reading{...}` duplicates `.prose` on the same elements. Delete it, and in `index.html:18-19` change `class="reading prose overview-view"` to `class="prose"` and `class="reading prose"` to `class="prose"`.
- Line 266 `.icon-button:hover{transform:translateY(-1px)}` is cancelled by line 525 `.icon-button:hover{transform:none}`. Delete both.
- Lines 161 and 310 repeat `.native-window .app-header{padding-left:85px}` inside 600px blocks; the 850px block at 133 already covers them. Delete 161 and 310.
- Line 117 animates `dialog[open]` with `enter`; line 526 animates it again with `dialog-in`. Change line 117 to `.toast{animation:enter .32s cubic-bezier(.16,1,.3,1)}`.

- [ ] **Step 5: Run the test to verify it passes**

Run: `node tests/test_css.mjs && node tests/test_job_notices.js`
Expected: `Stylesheet selectors are all in use.`

- [ ] **Step 6: Record the cleanup**

Append to `docs/cleanup.md`:

```markdown
## Front-end deepening (planned 2026-09-22)

Status: in progress on branch `front-end-deepening`. Ran with the [front-end deepening design](superpowers/specs/2026-09-22-front-end-deepening-design.md).

- [x] `app/static/app.css` loses the selector groups that match nothing: `.chapter-bar`, `.export`, `.export-body`, `#appearance-open`, `#appearance-dialog`, `.empty`, `.privacy`, `.figure-downloads`, `.toast-fading`, and the `.reading` duplicate of `.prose`. Check: `node tests/test_css.mjs` passes.
- [x] `.icon-button:hover` no longer lifts and cancels in the same file; `dialog[open]` animates once. Check: `grep -c "icon-button:hover" app/static/app.css` prints `0`.
```

- [ ] **Step 7: Browser check**

Open home, library and the sample Paper at 1280 and 390. Expected: no visible change.

- [ ] **Step 8: Commit**

```sh
git add app/static/app.css app/static/index.html docs/cleanup.md
git commit -m "Delete the stylesheet rules that match nothing and the ones that cancel each other"
```

### Task 5: Colour, scrim, shadow and motion tokens, with a no-literal test

**Files:**
- Modify: `app/static/app.css:3-4,7,27-28,73-74,106,121,240,244,335,376,401` and the motion lines listed below
- Modify: `app/static/app.js:536-546` (`dismissDialog`), `:948-949`, `:1016` (the `.animate()` calls)
- Test: `tests/test_css.mjs` (extend)

**Interfaces:**
- Produces: tokens `--glow`, `--glass-edge`, `--scrim`, `--scrim-opaque`, `--scrim-sheet`, `--shadow-float`, `--shadow-modal`, `--ease-out`, `--duration-quick`, `--duration`, `--duration-slow` on `:root`, with dark overrides for `--glass-edge` and `--shadow-float`. In `app.js`: `motion()` returning `{easing, quick, standard}`.

- [ ] **Step 1: Extend the test**

Append to `tests/test_css.mjs`, before the final `console.log`:

```js
// Every colour, shadow and easing is a token. A hex literal may appear only in a custom-property declaration.
const literals = [];
for (const [name, css] of Object.entries(sheets)) {
  const body = css.replace(/\/\*[\s\S]*?\*\//g, '');
  for (const declaration of body.split(/[;{}]/)) {
    if (/#[0-9a-fA-F]{3,8}\b/.test(declaration) && !/^\s*--[\w-]+\s*:/.test(declaration)) literals.push(`${name}: ${declaration.trim()}`);
    if (/cubic-bezier\(/.test(declaration) && !/^\s*--[\w-]+\s*:/.test(declaration)) literals.push(`${name}: ${declaration.trim()}`);
  }
}
for (const name of fs.readdirSync(root).filter(name => name.endsWith('.js'))) {
  for (const line of read(name).split('\n')) if (/#[0-9a-fA-F]{6}\b|cubic-bezier\(/.test(line)) literals.push(`${name}: ${line.trim().slice(0, 80)}`);
}
assert.deepEqual(literals, [], 'colour or easing literals outside the token tier');
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `node tests/test_css.mjs`
Expected: FAIL listing the `body::before` gradients, `.glass` edge, `dialog` shadow and backdrop, toast, field-help, tour, mobile navigation, sheet backdrop, notifications toggle, the three keyframe easings, and the `app.js` `.animate()` calls.

- [ ] **Step 3: Add the tokens**

Change `app.css:3` so the `:root` block ends with these additional declarations (keep everything already there):

```css
--glow:radial-gradient(ellipse at 0% 12%,#a9be8970,transparent 43%),radial-gradient(ellipse at 100% 75%,#d4b07942,transparent 44%),radial-gradient(ellipse at 78% 0%,#9cb7bd3d,transparent 35%);--glass-edge:#ffffff70;--scrim:#1b241d40;--scrim-opaque:#18211bb0;--scrim-sheet:#0007;--shadow-float:0 8px 30px #162a1820;--shadow-modal:0 25px 90px #20281740;--ease-out:cubic-bezier(.22,1,.36,1);--duration-quick:150ms;--duration:200ms;--duration-slow:280ms
```

Add to the dark block on `app.css:4`: `--glass-edge:#ffffff0d;--shadow-float:0 8px 30px #0005`. The modal shadow keeps one value in both themes, as today.

- [ ] **Step 4: Replace the literals**

| Line | Before | After |
| --- | --- | --- |
| 7 | the three `radial-gradient(...)` values | `background:var(--glow)` |
| 27 | `inset 0 1px 0 #ffffff70` | `inset 0 1px 0 var(--glass-edge)` |
| 28 | whole rule | delete (the dark token covers it) |
| 73 | `box-shadow:0 25px 90px #20281740` | `box-shadow:var(--shadow-modal)` |
| 74 | `background:#1b241d40` | `background:var(--scrim)` |
| 106 | `box-shadow:0 8px 30px #162a1820` | `box-shadow:var(--shadow-float)` |
| 121 | `background:#18211bb0` | `background:var(--scrim-opaque)` |
| 240 | `box-shadow:0 8px 24px #0002` | `box-shadow:var(--shadow-float)` |
| 244 | `box-shadow:0 16px 55px #28321e25` | `box-shadow:var(--shadow)` |
| 335 | `box-shadow:0 12px 45px #0002` | `box-shadow:var(--shadow-float)` |
| 363 | `box-shadow:0 5px 25px #20251006` | delete this declaration (line 505 already resets it to `none`) |
| 376 | `background:#0007` | `background:var(--scrim-sheet)` |
| 401 | `box-shadow:0 5px 20px #0002` | `box-shadow:var(--shadow-float)` |

Shadow deltas are the plan's one deliberate normalisation (Decision 5): the field-help popover, mobile navigation and updates toggle gain a slightly larger, tinted float shadow; the tour takes the page shadow.

Motion:

| Line | Before | After |
| --- | --- | --- |
| 116 | `transition:background-color .18s,transform .2s` | `transition:background-color var(--duration),transform var(--duration)` |
| 117 | `.32s cubic-bezier(.16,1,.3,1)` | `var(--duration-slow) var(--ease-out)` |
| 265 | `transition:background .18s,transform .18s` | `transition:background var(--duration),transform var(--duration)` |
| 276, 282, 284 | `.28s` | `var(--duration-slow)` |
| 384 | `.28s cubic-bezier(.22,1,.36,1)` | `var(--duration-slow) var(--ease-out)` |
| 414 | `.32s cubic-bezier(.16,1,.3,1),toast-expire .25s ease 5s` | `var(--duration-slow) var(--ease-out),toast-expire var(--duration-slow) ease 5s` |
| 526 | `200ms cubic-bezier(.23,1,.32,1)` | `var(--duration) var(--ease-out)` |

- [ ] **Step 5: Read the tokens from `app.js`**

Add after the `token` helper from Task 3:

```js
const motion = () => ({easing: token('--ease-out'), quick: parseFloat(token('--duration-quick')), standard: parseFloat(token('--duration'))});
```

In `dismissDialog` (`app.js:536-546`) replace `{duration:reduced ? 100 : 150, easing:'cubic-bezier(.23,1,.32,1)'}` with `{duration:reduced ? 100 : motion().quick, easing:motion().easing}`. In the disclosure fade at `app.js:1016` replace `{duration:reduced ? 100 : 160, easing:'cubic-bezier(.23,1,.32,1)'}` the same way. In `showTourStep` at `app.js:948-949` replace the `cubic-bezier(.22,1,.36,1)` strings with `motion().easing`.

- [ ] **Step 6: Run the tests**

Run: `node tests/test_css.mjs && node tests/test_job_notices.js && node --check app/static/app.js`
Expected: `Stylesheet selectors are all in use.` and no listed literals.

- [ ] **Step 7: Browser check**

Open a dialog, a mobile sheet at 390, the tour, and a toast in both themes. Expected: scrims and shadows as listed above; motion feels the same at 10% speed in the Animations panel.

- [ ] **Step 8: Commit**

```sh
git add app/static/app.css app/static/app.js
git commit -m "Name every colour, scrim, shadow and easing once"
```

### Task 6: Radius and type-size tokens

**Files:**
- Modify: `app/static/app.css:3` (tokens) and every `border-radius` or `font-size` with a matching value in `app.css` and `reader-layout.css`
- Test: `tests/test_css.mjs` (extend)

**Interfaces:**
- Produces: `--radius-control:10px`, `--radius-card:16px`, `--radius-panel:20px`, `--radius-sheet:24px`, `--radius-pill:999px`, `--text-caption:11px`, `--text-small:12px`, `--text-ui:13px`, `--text-body:14px`, `--text-lead:16px`.

- [ ] **Step 1: Extend the test**

Append to `tests/test_css.mjs` before the final `console.log`:

```js
// The repeated sizes are tokens. Values outside the scale stay raw by decision.
const raw = [];
for (const [name, css] of Object.entries(sheets)) {
  for (const match of css.matchAll(/font-size:(1[1-46])px|border-radius:(10|16|20|24|999|50)px(?![ ])|font:(1[1-46])px/g)) raw.push(`${name}: ${match[0]}`);
}
assert.deepEqual(raw, [], 'sizes that have a token');
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `node tests/test_css.mjs`
Expected: FAIL listing about a hundred declarations.

- [ ] **Step 3: Add the tokens**

Append to the `:root` block on `app.css:3`:

```css
--radius-control:10px;--radius-card:16px;--radius-panel:20px;--radius-sheet:24px;--radius-pill:999px;--text-caption:11px;--text-small:12px;--text-ui:13px;--text-body:14px;--text-lead:16px
```

- [ ] **Step 4: Replace by exact value**

Run these from the repository root, then review the diff:

```sh
sed -i '' -E \
  -e 's/font-size:11px/font-size:var(--text-caption)/g' -e 's/font-size:12px/font-size:var(--text-small)/g' \
  -e 's/font-size:13px/font-size:var(--text-ui)/g' -e 's/font-size:14px/font-size:var(--text-body)/g' \
  -e 's/font-size:16px/font-size:var(--text-lead)/g' \
  -e 's/font:11px/font:var(--text-caption)/g' -e 's/font:12px/font:var(--text-small)/g' -e 's/font:14px/font:var(--text-body)/g' \
  -e 's/border-radius:10px([;}])/border-radius:var(--radius-control)\1/g' -e 's/border-radius:16px([;}])/border-radius:var(--radius-card)\1/g' \
  -e 's/border-radius:20px([;}])/border-radius:var(--radius-panel)\1/g' -e 's/border-radius:24px([;}])/border-radius:var(--radius-sheet)\1/g' \
  -e 's/border-radius:999px/border-radius:var(--radius-pill)/g' -e 's/border-radius:50px/border-radius:var(--radius-pill)/g' \
  -e 's/border-radius:24px 24px 0 0/border-radius:var(--radius-sheet) var(--radius-sheet) 0 0/g' \
  app/static/app.css app/static/reader-layout.css
```

Two declarations need a hand edit: `font:600 11px/1 ui-sans-serif` at line 238 becomes `font:600 var(--text-caption)/1 ui-sans-serif`, and `font:14px/1.75 Georgia,serif` at line 186 is covered by the `font:14px` rule. A `font` shorthand with a `var()` size is valid CSS; the browser substitutes before parsing the shorthand.

`border-radius:50px` becomes the pill token: on every element that uses it the box is under 100px tall, so the rendered corner is identical.

- [ ] **Step 5: Run the tests**

Run: `node tests/test_css.mjs && node tests/test_job_notices.js`
Expected: pass.

- [ ] **Step 6: Browser check**

Home, library, reader and settings at 1280 and 390. Expected: no visible change.

- [ ] **Step 7: Commit**

```sh
git add app/static/app.css app/static/reader-layout.css
git commit -m "Give the repeated radii and text sizes one name each"
```

### Task 7: One 850px block and one 600px block per file

**Files:**
- Create: `tests/css_collisions.mjs` (local script)
- Modify: `app/static/app.css` (the `@media(max-width:850px)` blocks at 130, 288, 324, 387, 390, 392, 410, 432 and the `@media(max-width:600px)` blocks at 136, 208, 216, 294, 427, 490, 517; line numbers drift after Tasks 4 to 6, so find them by the prelude)
- Test: `tests/css_collisions.mjs`, `tests/test_css.mjs`, browser

**Interfaces:**
- Produces: `node tests/css_collisions.mjs app/static/app.css 850` prints `DEAD` for each rule inside a `max-width:850px` block whose property a later unscoped rule with the same selector text already overrides, and `INSPECT` where the later rule sits in a different `@media`. `no same-selector collisions` means moving the blocks to the end cannot change the cascade for same-selector rules.

- [ ] **Step 1: Write the collision script**

```js
// tests/css_collisions.mjs — list same-selector property collisions between a breakpoint block and later rules.
import fs from 'node:fs';

const [file, width] = process.argv.slice(2);
const css = fs.readFileSync(file, 'utf8').replace(/\/\*[\s\S]*?\*\//g, '');
const rules = []; // {selector, props, scope, order}; scope is 'target', 'other' (another @media) or 'none'
let depth = 0, scope = 'none', index = 0;
for (const match of css.matchAll(/([^{}]*)\{|\}/g)) {
  if (match[0] === '}') { depth--; if (depth === 0) scope = 'none'; continue; }
  const prelude = match[1].trim();
  depth++;
  if (prelude.startsWith('@media')) { scope = /max-width:\s*(\d+)px/.exec(prelude)?.[1] === width ? 'target' : 'other'; continue; }
  if (prelude.startsWith('@')) continue;
  const body = css.slice(match.index + match[0].length, css.indexOf('}', match.index));
  const props = new Set(body.split(';').map(part => part.split(':')[0].trim()).filter(Boolean));
  for (const selector of prelude.split(',')) rules.push({selector: selector.trim(), props, scope, order: index++});
}
let dead = 0, inspect = 0;
for (const inner of rules.filter(rule => rule.scope === 'target')) {
  for (const later of rules.filter(rule => rule.scope !== 'target' && rule.order > inner.order && rule.selector === inner.selector)) {
    const shared = [...inner.props].filter(prop => later.props.has(prop));
    if (!shared.length) continue;
    if (later.scope === 'none') { dead++; console.log(`DEAD ${inner.selector}\n  the ${width}px rule sets ${shared.join(', ')} but a later unscoped rule wins today; delete them from the ${width}px rule`); }
    else { inspect++; console.log(`INSPECT ${inner.selector}\n  the ${width}px rule and a later rule in another @media both set ${shared.join(', ')}; decide by hand which must win`); }
  }
}
console.log(dead || inspect ? `${dead} dead, ${inspect} to inspect` : 'no same-selector collisions');
process.exit(dead || inspect ? 1 : 0);
```

- [ ] **Step 2: Run it before moving anything**

Run: `node tests/css_collisions.mjs app/static/app.css 850; node tests/css_collisions.mjs app/static/app.css 600`
Expected: at least one `DEAD` line for the library card: `.library-page #paper-list .library-card>button:first-child` sets `min-height, padding, border, border-radius, background, font-size, line-height` inside the 850px block and the unscoped rule at (today's) line 505 wins.

- [ ] **Step 3: Delete the dead properties**

For every `DEAD` line, delete the shared properties from the rule inside the media block. They have no effect today, so deleting them changes nothing. For every `INSPECT` line, keep the property in the rule that must win when both media queries match, and delete it from the other; note each such decision in the commit message. Rerun both commands until each prints `no same-selector collisions`.

- [ ] **Step 4: Move the blocks**

Cut every `@media(max-width:850px){...}` block and paste their bodies, in their original order, into one block placed after the last unscoped rule of `app.css`. Do the same for `@media(max-width:600px)`, placed after the 850px block so the narrower breakpoint still wins. Leave the 1100, 700, 540 and 360 px blocks where they are. Repeat for the one 850px block in `reader-layout.css` only if a second one exists (there is one today; nothing to do).

- [ ] **Step 5: Run the tests**

Run: `node tests/css_collisions.mjs app/static/app.css 850 && node tests/css_collisions.mjs app/static/app.css 600 && node tests/test_css.mjs && grep -c "max-width:850px" app/static/app.css && grep -c "max-width:600px" app/static/app.css`
Expected: `no same-selector collisions` twice, the selector test passes, and each grep prints `1`.

- [ ] **Step 6: Browser check**

This task carries the plan's one residual risk (Decision 8). Open home, library, reader Overview, reader Paper, settings and the share dialog at 1280, 800 and 390 in both themes, comparing against the same pages on `main`. Expected: identical. Any difference means an equal-specificity collision the script cannot see; restore that rule's original position and note it in the commit message.

- [ ] **Step 7: Commit**

```sh
git add app/static/app.css
git commit -m "Open each breakpoint once in the stylesheet"
```

## Phase 4: view module

### Task 8: `view.js` derives every layout flag from one value

**Files:**
- Create: `app/static/view.js`
- Create: `tests/dom_stub.mjs` (local)
- Test: `tests/test_view.mjs` (new, local)

**Interfaces:**
- Produces:
  - `HOME = Object.freeze({page: 'home', tab: 'overview', focused: false, contents: false})`
  - `applyView(document, view)`: `view.page` is `'home' | 'library' | 'reading'`, `view.tab` is `'overview' | 'blog' | 'paper'`, `view.focused` and `view.contents` are booleans. Writes `hidden` on `#empty`, `#library-page`, `#workspace`, `#reading-bar`, `#reader-home`, `#exit-focus`, `#reading-companion`, `#mobile-contents`; toggles `is-library`, `is-reading`, `is-focused` on `document.body`; toggles `without-contents` and sets `data-view` on `#workspace`; sets `aria-current="page"` on `#mobile-home` or `#mobile-library`.
  - `tests/dom_stub.mjs` exports `class Element` and `createDocument(ids)`.

- [ ] **Step 1: Write the shared stub**

```js
// tests/dom_stub.mjs — the smallest DOM the renderers and the view module touch.
export class Element {
  constructor(tag) {
    this.tagName = tag.toUpperCase(); this.children = []; this.attributes = {}; this.parentNode = null; this.dataset = {};
    this._text = ''; this.textWrites = 0; this.appendCount = 0; this.hidden = false; this.className = ''; this.isConnected = true;
    const classes = new Set();
    this.classList = {add: (...names) => names.forEach(name => classes.add(name)), remove: (...names) => names.forEach(name => classes.delete(name)),
      contains: name => classes.has(name), toggle: (name, force) => { const on = force ?? !classes.has(name); on ? classes.add(name) : classes.delete(name); return on; }};
  }
  set textContent(value) { this._text = value; this.textWrites++; this.replaceChildren(); }
  get textContent() { return this._text + this.children.map(child => child.textContent).join(''); }
  append(...children) { for (const child of children) { child.remove(); child.parentNode = this; this.children.push(child); this.appendCount++; } }
  remove() { if (this.parentNode) this.parentNode.children.splice(this.parentNode.children.indexOf(this), 1); this.parentNode = null; }
  replaceChildren(...children) { for (const child of [...this.children]) child.remove(); this.append(...children); }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  removeAttribute(name) { delete this.attributes[name]; }
  getAttribute(name) { return this.attributes[name]; }
  querySelector() { return null; }
}
export const all = root => [root, ...root.children.flatMap(child => all(child))];
export const find = (root, predicate) => all(root).find(predicate);
export function createDocument(ids) {
  const elements = new Map(ids.map(id => [id, new Element('div')]));
  return {elements, body: new Element('body'), getElementById: id => elements.get(id), createElement: tag => new Element(tag)};
}
```

- [ ] **Step 2: Write the failing test**

```js
// tests/test_view.mjs
import assert from 'node:assert/strict';
import {createDocument} from './dom_stub.mjs';
import {HOME, applyView} from '../app/static/view.js';

const ids = ['empty', 'library-page', 'workspace', 'reading-bar', 'reader-home', 'exit-focus', 'reading-companion', 'mobile-contents', 'mobile-home', 'mobile-library'];
const doc = createDocument(ids), $ = id => doc.elements.get(id);

applyView(doc, HOME);
assert.equal($('empty').hidden, false); assert.equal($('library-page').hidden, true); assert.equal($('workspace').hidden, true);
assert.equal($('reading-bar').hidden, true); assert.equal($('reader-home').hidden, true); assert.equal($('exit-focus').hidden, true);
assert.equal($('mobile-home').getAttribute('aria-current'), 'page'); assert.equal($('mobile-library').getAttribute('aria-current'), undefined);
assert.equal(doc.body.classList.contains('is-reading'), false);

applyView(doc, {...HOME, page: 'library'});
assert.equal($('empty').hidden, true); assert.equal($('library-page').hidden, false); assert.equal($('reader-home').hidden, false);
assert.equal(doc.body.classList.contains('is-library'), true);
assert.equal($('mobile-library').getAttribute('aria-current'), 'page'); assert.equal($('mobile-home').getAttribute('aria-current'), undefined);

applyView(doc, {page: 'reading', tab: 'blog', focused: true, contents: true});
assert.equal($('workspace').hidden, false); assert.equal($('reading-bar').hidden, false); assert.equal($('exit-focus').hidden, false);
assert.equal($('reading-companion').hidden, false); assert.equal($('mobile-contents').hidden, false);
assert.equal(doc.body.classList.contains('is-reading'), true); assert.equal(doc.body.classList.contains('is-focused'), true);
assert.equal(doc.body.classList.contains('is-library'), false);
assert.equal($('workspace').classList.contains('without-contents'), false); assert.equal($('workspace').dataset.view, 'blog');

applyView(doc, {page: 'reading', tab: 'paper', focused: false, contents: false});
assert.equal($('exit-focus').hidden, true); assert.equal($('reading-companion').hidden, true);
assert.equal($('workspace').classList.contains('without-contents'), true); assert.equal($('workspace').dataset.view, 'paper');

applyView(doc, HOME);
assert.equal(doc.body.classList.contains('is-focused'), false, 'leaving the reader clears focus');
console.log('View flags passed.');
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `node tests/test_view.mjs`
Expected: FAIL with `does not provide an export named 'applyView'`.

- [ ] **Step 4: Write the module**

```js
// One reading layout value. Every hidden flag, body class and aria-current derives from it here and nowhere else.
export const HOME = Object.freeze({page: 'home', tab: 'overview', focused: false, contents: false});

export function applyView(document, view) {
  const $ = id => document.getElementById(id), reading = view.page === 'reading', focused = reading && view.focused;
  $('empty').hidden = view.page !== 'home';
  $('library-page').hidden = view.page !== 'library';
  $('workspace').hidden = !reading;
  $('reading-bar').hidden = !reading;
  $('reader-home').hidden = view.page === 'home';
  $('exit-focus').hidden = !focused;
  $('reading-companion').hidden = !view.contents;
  $('mobile-contents').hidden = !view.contents;
  document.body.classList.toggle('is-library', view.page === 'library');
  document.body.classList.toggle('is-reading', reading);
  document.body.classList.toggle('is-focused', focused);
  $('workspace').classList.toggle('without-contents', !view.contents);
  $('workspace').dataset.view = view.tab;
  for (const [id, page] of [['mobile-home', 'home'], ['mobile-library', 'library']]) {
    if (view.page === page) $(id).setAttribute('aria-current', 'page'); else $(id).removeAttribute('aria-current');
  }
}
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `node tests/test_view.mjs`
Expected: `View flags passed.`

- [ ] **Step 6: Commit**

```sh
git add app/static/view.js
git commit -m "Derive every reading layout flag from one view value"
```

### Task 9: The five writers become callers of the view module

**Files:**
- Modify: `app/static/app.js:275` (in `openPaper`), `:410` (`goHome`), `:413` (`showLibrary`), `:516-520` (end of `renderContents`), `:686-687` (focus toggles)
- Test: `tests/test_job_notices.js`, browser

**Interfaces:**
- Consumes: `HOME`, `applyView` from Task 8.
- Produces: `let view` and `setView(patch)` in `app.js`.

- [ ] **Step 1: Add the state**

Near the other `let` declarations at the top of `app.js` add:

```js
import {HOME, applyView} from './view.js';
let view = {...HOME};
function setView(patch) { view = {...view, ...patch}; applyView(document, view); }
```

- [ ] **Step 2: Replace the writers**

- `openPaper`, line 275: replace the whole line (`$('empty').hidden = true; ... document.body.classList.add('is-reading');`) with `setView({page: 'reading'});`.
- `goHome`, line 410: delete `$('empty').hidden = false; $('library-page').hidden = true; $('reader-home').hidden = true; $('workspace').hidden = true;`, `$('reading-bar').hidden = true; document.body.classList.remove('is-focused','is-reading','is-library'); $('mobile-home').setAttribute('aria-current','page'); $('mobile-library').removeAttribute('aria-current'); $('exit-focus').hidden = true;` and insert `setView({page: 'home', focused: false});` after `closeMobilePanels();`.
- `showLibrary`, line 413: delete `$('empty').hidden = true; $('library-page').hidden = false; document.body.classList.add('is-library'); $('mobile-home').removeAttribute('aria-current'); $('mobile-library').setAttribute('aria-current','page'); $('reader-home').hidden = false;` and insert `setView({page: 'library'});` after `goHome();`.
- `renderContents`, lines 516-520: replace the five lines from `const hasContents = ...` with `setView({tab: activeTab, contents: $('contents').children.length > 0});`.
- Lines 686-687: `$('focus-toggle').onclick = () => setView({focused: true});` and `$('exit-focus').onclick = () => setView({focused: false});`.

- [ ] **Step 3: Confirm nothing else writes the flags**

Run: `grep -n "is-library\|is-reading\|is-focused\|without-contents\|dataset.view\|aria-current','page'" app/static/app.js`
Expected: no matches outside `view.js` (the grep is on `app.js`, so: no output).

- [ ] **Step 4: Run the checks**

Run: `node --check app/static/app.js && node tests/test_job_notices.js && node tests/test_view.mjs`
Expected: pass.

- [ ] **Step 5: Browser check**

Home, Library, open a Paper, switch the three tabs, Focus and Exit focus, back Home, at 1280 and 390. Expected: identical to `main`, including the mobile navigation's current item and the companion column hiding when a tab has no headings.

- [ ] **Step 6: Commit**

```sh
git add app/static/app.js
git commit -m "Route every layout change through the view module"
```

## Phase 5: renderers behind a seam

### Task 10: `render.js` holds the node factory and job notices

**Files:**
- Create: `app/static/render.js`
- Modify: `app/static/app.js:24` (`node`), `:42-46` (`expireToast`), `:317-380` (`renderJobs`, `updateNotificationToggle`). The `$('notifications-toggle').onclick` handler at `:381-384` stays in `app.js`.
- Test: `tests/test_job_notices.js` (rewritten, local)

**Interfaces:**
- Produces:
  - `createNode(document) -> (tag, text, className) => Element`, the factory now at `app.js:24`.
  - `class JobNotices` with `constructor({target, toggle, node, run, paperAPI, downloadLink, retries, setTimeout, clearTimeout, reducedMotion})` and `render(jobs, papers)`. `reducedMotion` is `() => boolean`. `target` is the `#jobs` element, `toggle` the `#notifications-toggle` button. `render` draws the toasts exactly as `renderJobs` does today and updates the toggle's text and `hidden`.
- Consumes in `app.js`: `run`, `paperAPI`, `downloadLink`, `retries`.

- [ ] **Step 1: Rewrite the test to import**

Replace `tests/test_job_notices.js` with `tests/test_job_notices.mjs`:

```js
// Run the production notification renderer without a browser or a provider.
import assert from 'node:assert/strict';
import {Element, createDocument, find} from './dom_stub.mjs';
import {createNode, JobNotices} from '../app/static/render.js';

const doc = createDocument(['jobs', 'notifications-toggle']);
const calls = [], timers = new Map();
const node = createNode(doc);
const downloadLink = url => { const link = node('a', url.toLowerCase().endsWith('.png') ? 'Save PNG' : 'Save PDF'); link.href = url + '?token=test'; return link; };
const notices = new JobNotices({target: doc.elements.get('jobs'), toggle: doc.elements.get('notifications-toggle'), node,
  run: (url, payload) => calls.push({url, payload}), paperAPI: id => `/api/papers/${encodeURIComponent(id)}`, downloadLink, retries: new Map(),
  setTimeout: fn => { const id = {}; timers.set(id, fn); return id; }, clearTimeout: id => timers.delete(id), reducedMotion: () => false});

const button = (root, text) => find(root, element => element.tagName === 'BUTTON' && element.textContent === text);
const papers = [{id: 'a', title: 'Paper A'}, {id: 'b', title: 'Paper B'}];
let jobs = [{id: 'old', kind: 'overview', state: 'failed', error: 'Old failure', payload: {paper_id: 'a'}}];
const render = () => notices.render(jobs, papers);
const target = doc.elements.get('jobs');

render();
assert.equal(target.children.length, 0, 'historical failures stay in records without a launch toast');
jobs[0].error = 'Updated diagnostic'; render();
assert.equal(target.children.length, 0, 'a changed historical diagnostic must not replay a failure');
```

Then keep every assertion from the old file from `const a = {id: 'a1', ...}` to the end, with these substitutions: `context.state.jobs = [a, b]` becomes `jobs = [a, b]`; `context.state.jobs.push(...)` becomes `jobs.push(...)`; `jobs` (the old element) becomes `target`; `element.tagName === 'button'` becomes `'BUTTON'` and `'strong'` becomes `'STRONG'`, `'a'` becomes `'A'`; `find` comes from the stub. Delete the old `Element` class, `vm` context and `source.slice` lines. Add one assertion after the delivery warning: `assert.equal(delivery.classList.contains('toast-expiring'), false, 'a warning stops the expiry animation');`.

- [ ] **Step 2: Run the test to verify it fails**

Run: `node tests/test_job_notices.mjs`
Expected: FAIL with `does not provide an export named 'JobNotices'`.

- [ ] **Step 3: Write the module**

```js
// Renderers draw into the elements they are handed and call back for every action. They read no page state.
export const createNode = document => (tag, text, className) => {
  const el = document.createElement(tag);
  if (text !== undefined) el.textContent = text;
  if (className) el.className = className;
  return el;
};

const TERMINAL = new Set(['ready', 'completed', 'succeeded', 'failed', 'cancelled', 'interrupted']);
const KINDS = {import: 'Paper import', reading: 'Paper indexing', blog: 'Blog', overview: 'Overview', chat: 'Question', export: 'File export', send: 'Kindle delivery', recommend: 'Recommendations'};
const STATUSES = {ready: 'ready', completed: 'ready', succeeded: 'ready', failed: 'failed', interrupted: 'interrupted', cancelled: 'cancelled', running: 'in progress', queued: 'queued'};

export class JobNotices {
  constructor({target, toggle, node, run, paperAPI, downloadLink, retries, setTimeout, clearTimeout, reducedMotion}) {
    Object.assign(this, {target, toggle, node, run, paperAPI, downloadLink, retries, setTimeout, clearTimeout, reducedMotion});
    this.records = new Map();
    this.initialized = false;
  }

  expire(element, remove) {
    element.classList.remove('toast-expiring'); void element.offsetWidth;
    element.classList.add('toast-expiring');
    return this.setTimeout(remove, this.reducedMotion() ? 5000 : 5250);
  }

  updateToggle() {
    const count = this.target.children.length;
    this.toggle.hidden = count === 0;
    this.toggle.textContent = `${count} update${count === 1 ? '' : 's'}`;
  }

  render(jobs, papers) {
    // Body: app.js renderJobs, lines 317-376, moved verbatim with the substitutions below.
  }
}
```

Move the body of `renderJobs` (`app.js:318-375`, everything between the function's braces) into `render()` and apply:

| In the moved body | Becomes |
| --- | --- |
| `state.jobs` | `jobs` |
| `state.papers` | `papers` |
| `jobNotices` | `this.records` |
| `jobsInitialized` | `this.initialized` |
| `terminal` | `TERMINAL` |
| the inline `kind` map | `KINDS[job.kind] \|\| 'Task'` |
| the inline `status` map | `STATUSES[job.state] \|\| 'in progress'` |
| `node(` | `this.node(` |
| `$('jobs')` | `this.target` |
| `updateNotificationToggle()` | `this.updateToggle()` |
| `run(` | `this.run(` |
| `paperAPI(` | `this.paperAPI(` |
| `downloadLink(` | `this.downloadLink(` |
| `retries` | `this.retries` |
| `clearTimeout(` | `this.clearTimeout(` |
| `expireToast(item,record.dismiss)` | `this.expire(item, record.dismiss)` |

`expire` is `expireToast` from `app.js:42-46` with `window.matchMedia('(prefers-reduced-motion: reduce)').matches` replaced by `this.reducedMotion()`.

- [ ] **Step 4: Point `app.js` at the module**

- Delete `app.js:24` (`const node = ...`) and add `import {createNode, JobNotices} from './render.js';` plus `const node = createNode(document);` in its place.
- Delete `expireToast` (`:42-46`), `renderJobs` (`:317-376`) and `updateNotificationToggle` (`:377-380`), and the `const jobNotices = new Map();` and `let jobsInitialized = false` declarations.
- Add, after `retries` is declared: `const jobNotices = new JobNotices({target: $('jobs'), toggle: $('notifications-toggle'), node, run, paperAPI, downloadLink, retries, setTimeout: window.setTimeout.bind(window), clearTimeout: window.clearTimeout.bind(window), reducedMotion: () => window.matchMedia('(prefers-reduced-motion: reduce)').matches});`
- Every call `renderJobs()` becomes `jobNotices.render(state.jobs, state.papers)`. Every call `updateNotificationToggle()` becomes `jobNotices.updateToggle()`.
- `terminal` is still used by `schedulePoll` (`:988`). Keep `const terminal` in `app.js`.

- [ ] **Step 5: Run the tests**

Run: `node --check app/static/app.js && node tests/test_job_notices.mjs && node tests/test_css.mjs`
Expected: `Job notification regressions passed.`; the selector test still finds `toast`, `toast-heading`, `toast-actions`, `toast-expiring` and `quiet` because it reads every `app/static/*.js`.

- [ ] **Step 6: Browser check**

Import a Paper and watch the toast progress, cancel, retry and dismiss. Expected: identical to `main`.

- [ ] **Step 7: Commit**

```sh
git add app/static/render.js app/static/app.js
git commit -m "Draw job notices from a module the tests can import"
```

### Task 11: Prose, library, recommendations and contents move behind the seam

**Files:**
- Modify: `app/static/render.js`
- Modify: `app/static/app.js:83-116` (`renderLibrary`), `:139-143` (`cleanOverviewCitations`), `:156-171` (`tableCells`, `tableDivider`), `:172-267` (`renderProse`), `:417-436` (`renderRecommendations`), `:495-515` (`renderContents`)
- Test: `tests/test_render.mjs` (new, local)

**Interfaces:**
- Produces in `render.js`:
  - `renderProse(target, text, {node, references = [], figures = [], fileURL, openSource, openFigure, renderMath})`. `openSource(href)` replaces `$('reader').src = fileURL(source.href); switchTab('paper')`. Every figure image gets `dataset.lightSrc = image` and, when `figure.svg_dark` resolves, `dataset.darkSrc`.
  - `renderLibrary(target, papers, {node, query, selected, tourPaperId, onOpen, onRemove})`: `onOpen(paper)` on click, `onRemove(paper, summary)` from the remove action. Returns the number of cards drawn.
  - `renderRecommendations(target, items, {node, onAdd})`: `onAdd(url, button)`; the arXiv id and dblp checks stay inside.
  - `renderContents(target, entries, {node})`: `entries` is `[{label, current, onSelect}]`.
  - `cleanOverviewCitations`, `tableCells`, `tableDivider` exported as they are.
- `app.js` keeps `renderLibrary()` and `renderContents()` as thin functions that compute the arguments and call the module.

- [ ] **Step 1: Write the failing test**

```js
// tests/test_render.mjs
import assert from 'node:assert/strict';
import {Element, createDocument, find, all} from './dom_stub.mjs';
import {createNode, renderProse, renderLibrary, renderRecommendations, renderContents} from '../app/static/render.js';

const doc = createDocument([]), node = createNode(doc);
const opened = [], figures = [], math = [];
const io = {node, fileURL: path => path ? '/files/x/' + path : null, openSource: href => opened.push(href),
  openFigure: (...args) => figures.push(args), renderMath: (el, tex, display) => math.push([tex, display])};

let target = new Element('div');
renderProse(target, '## Heading\n\nA line with $x^2$ and [p1].\n\n{{figure:fig1}}', {...io,
  references: [{id: 'p1', href: 'reader/a.xhtml#p1', section: 'Method'}],
  figures: [{id: 'fig1', svg: 'reader/f.svg', svg_dark: 'reader/f.dark.svg', caption: 'Cap', alt: 'Alt'}]});
assert.equal(target.children[0].tagName, 'H3', 'a level-two heading renders one level down');
const citation = find(target, el => el.className === 'citation');
citation.onclick(); assert.deepEqual(opened, ['reader/a.xhtml#p1']);
assert.deepEqual(math, [['x^2', false]]);
const img = find(target, el => el.tagName === 'IMG');
assert.equal(img.dataset.lightSrc, '/files/x/reader/f.svg'); assert.equal(img.dataset.darkSrc, '/files/x/reader/f.dark.svg');
find(target, el => el.className === 'figure-open').onclick();
assert.equal(figures.length, 1);

target = new Element('div');
renderProse(target, '{{figure:fig9}}', {...io, figures: []});
assert.match(target.textContent, /Figure unavailable/);

target = new Element('nav');
const papers = [{id: '1', title: 'Alpha', authors: ['A']}, {id: '2', title: 'Beta', authors: 'B'}];
const openedPapers = [];
assert.equal(renderLibrary(target, papers, {node, query: 'beta', selected: '2', tourPaperId: 'x', onOpen: p => openedPapers.push(p.id), onRemove: () => {}}), 1);
assert.equal(find(target, el => el.tagName === 'BUTTON').getAttribute('aria-current'), 'true');
find(target, el => el.tagName === 'BUTTON').onclick(); assert.deepEqual(openedPapers, ['2']);
assert.equal(renderLibrary(target, papers, {node, query: 'zzz', selected: null, tourPaperId: 'x', onOpen() {}, onRemove() {}}), 0);
assert.match(target.textContent, /No matching papers/);
assert.equal(renderLibrary(target, [], {node, query: '', selected: null, tourPaperId: 'x', onOpen() {}, onRemove() {}}), 0);
assert.match(target.textContent, /will appear here/);

target = new Element('div');
const added = [];
renderRecommendations(target, [{id: '2401.00001', title: 'Good', venue: 'V', year: 2024, summary: 's'}, {id: 'javascript:alert(1)', title: 'Bad', venue: 'V', year: 2024, summary: 's'}], {node, onAdd: url => added.push(url)});
assert.equal(target.children.length, 1, 'only a verified arXiv id becomes a card');
find(target, el => el.tagName === 'BUTTON').onclick(); assert.deepEqual(added, ['https://arxiv.org/abs/2401.00001']);

target = new Element('nav');
const selected = [];
renderContents(target, [{label: 'One', current: false, onSelect: () => selected.push(1)}, {label: 'Two', current: true, onSelect: () => selected.push(2)}], {node});
assert.equal(target.children.length, 2); assert.equal(target.children[1].getAttribute('aria-current'), 'true');
target.children[0].onclick(); assert.deepEqual(selected, [1]);
console.log('Renderers passed.');
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `node tests/test_render.mjs`
Expected: FAIL with `does not provide an export named 'renderProse'`.

- [ ] **Step 3: Move the functions**

Move `cleanOverviewCitations` (`app.js:139-143`), `tableCells` and `tableDivider` (`:156-171`) into `render.js` verbatim with `export` added.

Move `renderProse` (`:172-267`) into `render.js` as `export function renderProse(target, text, io) { const {node, references = [], figures = [], fileURL, openSource, openFigure, renderMath} = io;` and apply:

| In the moved body | Becomes |
| --- | --- |
| `citation.onclick = () => { $('reader').src = fileURL(source.href); switchTab('paper'); };` | `citation.onclick = () => openSource(source.href);` |
| `renderProse(block, content.join('\n'), references, figures);` | `renderProse(block, content.join('\n'), io);` |
| `img.src = image;` | `img.src = image; img.dataset.lightSrc = image; const dark = fileURL(figure.svg_dark); if (dark) img.dataset.darkSrc = dark;` |
| `if (figure.portrait?.svg) { ... }` | delete (no workflow writes `portrait` any more; confirm with `grep -rn portrait papers app`) |

`node`, `openFigure` and `renderMath` are now the destructured names, so the calls read the same.

Move `renderLibrary` (`:83-116`) as `export function renderLibrary(target, papers, {node, query, selected, tourPaperId, onOpen, onRemove})` and apply:

| In the moved body | Becomes |
| --- | --- |
| `$('paper-count').textContent = state.papers.length;` | delete (stays in `app.js`) |
| `const query = $('search').value.toLowerCase();` | `query = query.toLowerCase();` |
| `$('paper-list').replaceChildren();` | `target.replaceChildren();` |
| `state.papers` | `papers` |
| `tourStep !== null` in the sort | `tourPaperId !== null` |
| `TOUR_ID` | `tourPaperId` |
| `button.onclick = () => tourStep === 1 && paper.id === TOUR_ID ? showTourStep(2) : openPaper(paper.id);` | `button.onclick = () => onOpen(paper);` |
| the whole `remove.onclick = () => { ... };` block | `remove.onclick = () => { actions.open = false; onRemove(paper, summary); };` |
| `$('paper-list').append(card)` | `target.append(card); drawn++;` |
| the final `if (!$('paper-list').children.length) ...` | `if (!drawn) target.append(node('p', papers.length ? 'No matching papers. Try another title or author.' : 'Your imported papers will appear here.', 'muted'));\n  return drawn;` |

Declare `let drawn = 0;` before the `for` loop.

Move `renderRecommendations` (`:417-436`) as `export function renderRecommendations(target, items, {node, onAdd})`; delete the `$('recommendations').hidden`, signature and `recommendationsSignature` lines (they stay in `app.js`), replace `$('recommendation-list')` with `target`, and replace `add.onclick = async () => { add.disabled = true; await run('/api/import',{url}); add.disabled = false; }` with `add.onclick = () => onAdd(url, add)`.

Add `renderContents`:

```js
export function renderContents(target, entries, {node}) {
  target.replaceChildren();
  for (const entry of entries) {
    const button = node('button', entry.label);
    button.setAttribute('aria-current', String(Boolean(entry.current)));
    button.onclick = entry.onSelect;
    target.append(button);
  }
}
```

- [ ] **Step 4: Rewrite the callers in `app.js`**

Extend the import Task 10 added, then replace the three functions:

```js
import {createNode, JobNotices, renderProse, renderLibrary as drawLibrary, renderRecommendations as drawRecommendations, renderContents as drawContents, cleanOverviewCitations} from './render.js';
const prose = (target, text, references, figures) => renderProse(target, text, {node, references, figures, fileURL, renderMath,
  openSource: href => { $('reader').src = fileURL(href); switchTab('paper'); }, openFigure});

function renderLibrary() {
  $('paper-count').textContent = state.papers.length;
  drawLibrary($('paper-list'), state.papers, {node, query: $('search').value, selected, tourPaperId: tourStep === null ? null : TOUR_ID,
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

function renderRecommendations() {
  const items = state.recommendations?.items || [], signature = JSON.stringify(items);
  $('recommendations').hidden = !items.length;
  if (signature === recommendationsSignature) return;
  recommendationsSignature = signature;
  drawRecommendations($('recommendation-list'), items, {node, onAdd: async (url, button) => { button.disabled = true; await run('/api/import', {url}); button.disabled = false; }});
}

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
```

The two `renderProse(...)` calls in `openPaper` (`:284-285`) become `prose(...)`. Delete the moved functions from `app.js`.

- [ ] **Step 5: Run the tests**

Run: `node --check app/static/app.js && node tests/test_render.mjs && node tests/test_job_notices.mjs && node tests/test_view.mjs && node tests/test_css.mjs`
Expected: all pass.

- [ ] **Step 6: Browser check**

Open the sample Paper: Overview and Blog prose with a formula, a table, a figure that enlarges, a citation that opens the Paper tab; the library search, empty states and remove flow; recommendations on home; the contents column on each tab. Expected: identical to `main`.

- [ ] **Step 7: Commit**

```sh
git add app/static/render.js app/static/app.js
git commit -m "Move prose, library, recommendation and contents drawing behind one seam"
```

## Phase 6: Figure palette

### Task 12: `palette.py` with `LIGHT` equal to today's constants

**Files:**
- Create: `papers/figures/palette.py`
- Modify: `papers/figures/layout.py:22-27` (delete the colour constants)
- Modify: `papers/figures/render.py:11-13` (imports), `:20-31` (`SHARED_MARKERS`, `PANEL_PAGE_STYLE`), `:49-240` (`_draw`, `_draw_edge`), `:241-350` (`compose`), `:351` (`rasterize`)
- Test: `tests/test_palette.py` (new, local), `tests/baseline_scenes.py --compare`, existing figure tests

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) class Palette` with fields `name, text, muted, accent, hairline, page, card, sunk, cell_masked, cell_hot, bar, tones` where `tones` is `dict[str, tuple[str, str, str]]` of fill, stroke, text.
  - `LIGHT`, `DARK`: `Palette` values. `ACCENT_TONES = ('blue', 'green', 'peach')` moves here.
  - `render.markers(palette) -> str`, `render.page_style(palette) -> str`.
  - `compose(measure, scene, canvas, *, frame='page', page_title='', palette=LIGHT)`.
  - `_draw(node, out, boxes, measure, palette)`, `_draw_edge(edge, boxes, out, measure, palette)`.

- [ ] **Step 1: Write the failing test**

```python
"""The figure palette is one value; light keeps today's colours and dark defines every role."""
import dataclasses
import unittest

from papers.figures.palette import DARK, LIGHT, Palette


class PaletteTests(unittest.TestCase):
    def test_light_keeps_the_established_ramp(self):
        self.assertEqual((LIGHT.text, LIGHT.muted, LIGHT.accent, LIGHT.hairline), ('#243b32', '#627168', '#2f6f5e', '#dce1d8'))
        self.assertEqual(LIGHT.tones['plain'], ('#ffffff', '#c3ccbd', '#243b32'))
        self.assertEqual(LIGHT.page, '#ffffff')

    def test_dark_defines_every_role(self):
        for field in dataclasses.fields(Palette):
            self.assertTrue(getattr(DARK, field.name), field.name)
        self.assertEqual(set(DARK.tones), set(LIGHT.tones))
        self.assertNotEqual(DARK.page, LIGHT.page)

    def test_palettes_are_frozen(self):
        with self.assertRaises(dataclasses.FrozenInstanceError):
            LIGHT.text = '#000000'
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/python -m unittest tests.test_palette -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'papers.figures.palette'`.

- [ ] **Step 3: Write the module**

```python
"""The colours a Figure render draws with. Light is the export palette; dark follows the reader's theme."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Palette:
    name: str
    text: str
    muted: str
    accent: str
    hairline: str
    page: str
    card: str
    sunk: str
    cell_masked: str
    cell_hot: str
    bar: str
    # fill, stroke, text for each tone. The plain card is the page colour; ``muted`` is the sunk surface.
    tones: dict


ACCENT_TONES = ('blue', 'green', 'peach')

LIGHT = Palette(
    name='light', text='#243b32', muted='#627168', accent='#2f6f5e', hairline='#dce1d8',
    page='#ffffff', card='#fbfcfa', sunk='#f3f6f0', cell_masked='#eef1ea', cell_hot='#dce8cf', bar='#c3ccbd',
    tones={'blue': ('#e1ebf1', '#7f9fb5', '#2b5876'), 'green': ('#dce8cf', '#8aa87a', '#2f5d3a'),
           'peach': ('#f1e3d8', '#c9a08a', '#7a4a2e'), 'muted': ('#f3f6f0', '#dce1d8', '#243b32'),
           'plain': ('#ffffff', '#c3ccbd', '#243b32')})

DARK = Palette(
    name='dark', text='#e6ebe4', muted='#a9b3a8', accent='#8fc7b0', hairline='#3a463f',
    page='#10120f', card='#171b16', sunk='#1d231c', cell_masked='#1a201b', cell_hot='#2f4a3a', bar='#4a5a4e',
    tones={'blue': ('#1f2c36', '#5f7f95', '#b9d3e6'), 'green': ('#22301f', '#6f8f62', '#c5dcb8'),
           'peach': ('#332822', '#a07a62', '#ebcdb9'), 'muted': ('#1d231c', '#3a463f', '#e6ebe4'),
           'plain': ('#10120f', '#4a5a4e', '#e6ebe4')})
```

- [ ] **Step 4: Thread the palette through `render.py`**

- `layout.py:22-27`: delete `TEXT, MUTED, ACCENT, HAIRLINE`, `TONES` and `ACCENT_TONES`.
- `render.py:11-13`: remove `ACCENT, ACCENT_TONES, HAIRLINE, MUTED, TEXT, TONES` from the `layout` import and add `from papers.figures.palette import ACCENT_TONES, LIGHT`.
- Replace `SHARED_MARKERS` (`:20-28`) with:

```python
def markers(palette):
    marker = ('<marker id="{id}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" '
              'orient="auto-start-reverse"><path d="M 1 2 L 8 5 L 1 8 Z" fill="{fill}"/></marker>')
    return ('<defs>' + marker.format(id='arrow', fill=palette.text) + marker.format(id='arrow-muted', fill=palette.muted)
            + marker.format(id='arrow-accent', fill=palette.accent) + '</defs>')


def page_style(palette):
    return ('*{box-sizing:border-box}html,body{margin:0;padding:0;background:' + palette.page + '}'
            'main{margin:0;padding:0}svg{display:block}')
```

- `_draw(node, out, boxes, measure)` becomes `_draw(node, out, boxes, measure, palette)`; `_draw_edge(edge, boxes, out, measure)` becomes `_draw_edge(edge, boxes, out, measure, palette)`; every recursive call and the calls in `compose` pass `palette`. Then apply inside both functions and `compose`:

| Before | After |
| --- | --- |
| `TEXT` | `palette.text` |
| `MUTED` | `palette.muted` |
| `ACCENT` | `palette.accent` |
| `HAIRLINE` | `palette.hairline` |
| `TONES[` | `palette.tones[` |
| `'#fbfcfa'` (lines 78, 88) | `palette.card` |
| `'#f3f6f0'` (line 134) | `palette.sunk` |
| `'#eef1ea'` (line 125) | `palette.cell_masked` |
| `'#dce8cf'` (line 125) | `palette.cell_hot` |
| `'#ffffff'` (lines 125, 299) | `palette.page` |
| `"#c3ccbd"` (line 152) | `palette.bar` |

Where a literal sits inside an f-string, interpolate it: `fill="#ffffff" stroke="{HAIRLINE}"` at line 299 becomes `fill="{palette.page}" stroke="{palette.hairline}"`.
| `out = [SHARED_MARKERS]` | `out = [markers(palette)]` |
| `fill="{TEXT}"` in the root `<svg>` at line 343 | `fill="{palette.text}"` |

`compose` gains `palette=LIGHT` as its last keyword argument. `rasterize` uses `page_style(LIGHT)` in place of `PANEL_PAGE_STYLE`. Any other importer of `SHARED_MARKERS`, `PANEL_PAGE_STYLE`, `TEXT`, `MUTED`, `ACCENT`, `HAIRLINE` or `TONES` (`grep -rn "SHARED_MARKERS\|PANEL_PAGE_STYLE\|from papers.figures.layout import" papers tests tools`) switches to the new names.

- [ ] **Step 5: Run the tests and the baseline**

Run: `.venv/bin/python -m unittest tests.test_palette tests.test_figure tests.test_scene_layout tests.test_layout_canvas tests.test_chart_node -v && .venv/bin/python tests/baseline_scenes.py --compare`
Expected: PASS; every baseline line `same`.

- [ ] **Step 6: Commit**

```sh
git add papers/figures/palette.py papers/figures/layout.py papers/figures/render.py
git commit -m "Draw every figure from one palette value"
```

### Task 13: `Figure.build` writes a dark SVG beside the light assets

**Files:**
- Modify: `papers/figures/__init__.py:58-75` (`build`)
- Modify: `papers/figures/render.py:351` (`rasterize`)
- Modify: `papers/overview_workflow.py:29` (`FIGURE_ASSET_KEYS`)
- Test: `tests/test_figure.py` (extend)

**Interfaces:**
- Produces: `rasterize(directory, svg, figure_id, title, dark_svg=None)`; when `dark_svg` is given the assets gain `svg_dark`, the path of `<figure_id>.dark.svg`. `FigureResult.assets['svg_dark']` for every build. `FIGURE_ASSET_KEYS` includes `'svg_dark'`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_figure.py`:

```python
    def test_build_writes_a_dark_svg_from_the_same_layout(self):
        with tempfile.TemporaryDirectory() as directory:
            result = Figure(width=1000).build(self.scene, directory, 'fig1', frame='page', page_title='Attention Is All You Need')
            dark = (Path(directory) / result.assets['svg_dark']).read_text()
            self.assertTrue(result.assets['svg_dark'].endswith('.dark.svg'))
            self.assertIn('#10120f', dark)
            self.assertNotIn('#ffffff', dark)
            light = (Path(directory) / result.assets['svg_source']).read_text()
            self.assertEqual(light.count('<rect'), dark.count('<rect'), 'the dark variant repeats the light layout')
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/python -m unittest tests.test_figure.FigureTests.test_build_writes_a_dark_svg_from_the_same_layout -v`
Expected: FAIL with `KeyError: 'svg_dark'`.

- [ ] **Step 3: Compose the dark variant**

In `papers/figures/__init__.py` add `import copy` and `from papers.figures.palette import DARK`, then change the compose block of `build` to:

```python
        measure = self.measurer_factory(directory)
        try:
            dark_svg, _ = compose(measure, copy.deepcopy(scene), self.canvas, frame=frame, page_title=page_title, palette=DARK)
            svg, placements = compose(measure, scene, self.canvas, frame=frame, page_title=page_title)
        finally:
            measure.close()
        assets = rasterize(directory, svg, figure_id, scene.get('title') or figure_id, dark_svg=dark_svg)
```

The dark pass runs first on a copy, so the light pass still annotates `scene` in place as it does today. The measurer caches every string, so the second compose makes no renderer call.

- [ ] **Step 4: Write the file in `rasterize`**

Change the signature to `def rasterize(directory, svg, figure_id, title, dark_svg=None):` and, after `target.with_suffix('.source.svg').write_text(svg)`, add:

```python
    if dark_svg is not None:
        target.with_suffix('.dark.svg').write_text(dark_svg)
```

After `assets['svg_source'] = ...` add:

```python
    if dark_svg is not None:
        assets['svg_dark'] = str(relative) + '.dark.svg'
```

- [ ] **Step 5: Record the key**

`papers/overview_workflow.py:29`: `FIGURE_ASSET_KEYS = ('html', 'svg', 'png', 'pdf', 'svg_source', 'svg_dark')`. Check `grep -rn FIGURE_ASSET_KEYS papers app` for any consumer that enumerates the keys and confirm each tolerates the new one.

- [ ] **Step 6: Run the tests**

Run: `.venv/bin/python -m unittest tests.test_figure tests.test_overview_workflow tests.test_blog_workflow -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```sh
git add papers/figures/__init__.py papers/figures/render.py papers/overview_workflow.py
git commit -m "Write a dark figure beside every light one"
```

### Task 14: The app swaps figure sources with the theme

**Files:**
- Modify: `app/static/app.js` (`applyAppearance` from Task 3, and `openPaper` after the two `prose(...)` calls)
- Test: `tests/test_render.mjs` (already asserts the data attributes), browser

**Interfaces:**
- Produces: `swapFigureSources(theme)` in `app.js`.

- [ ] **Step 1: Add the swap**

```js
function swapFigureSources(theme) {
  for (const img of document.querySelectorAll('img[data-dark-src]')) {
    const next = theme === 'dark' ? img.dataset.darkSrc : img.dataset.lightSrc;
    if (img.getAttribute('src') !== next) img.src = next;
  }
}
```

Call `swapFigureSources(theme)` in `applyAppearance` right before `styleReader();`, and call `swapFigureSources(document.documentElement.dataset.theme)` in `openPaper` immediately after the two `prose(...)` calls.

- [ ] **Step 2: Run the checks**

Run: `node --check app/static/app.js && node tests/test_render.mjs && node tests/test_css.mjs`
Expected: pass.

- [ ] **Step 3: Browser check**

Generate an Overview (or regenerate the sample's) so a `.dark.svg` exists, then toggle the theme on the Overview and Blog tabs. Expected: the figure and its frame both follow the theme; the enlarged figure dialog shows the current variant; Share still exports the light PNG and PDF. A Paper whose figures predate this task keeps its light figure in dark mode with a dark frame.

- [ ] **Step 4: Commit**

```sh
git add app/static/app.js
git commit -m "Show the dark figure when the reader's theme is dark"
```

## Phase 7: docs and merge

### Task 15: Terms, developer docs, cleanup record, merge

**Files:**
- Modify: `CONTEXT.md` (two entries), `docs/development.md:102-107`, `docs/cleanup.md` (the Task 4 section)

- [ ] **Step 1: Add the terms**

Append to the language list in `CONTEXT.md`, after **Figure render**:

```markdown
**Reading preferences**: The reader's theme, text size, font, and margin choice. One module maps them to values; the page and the Paper's reader iframe apply those values and hold no colour of their own.

**Figure palette**: The named colours a Figure render draws with. The light palette is the export palette for PNG, PDF, and Kindle; the dark palette follows the reader's theme on screen.
```

- [ ] **Step 2: Fix the test instructions**

In `docs/development.md:102-107` replace the node line with:

```sh
python3 -m unittest discover -s tests
for test in tests/test_*.mjs; do node "$test"; done
```

and add one sentence after the block: "Front-end tests import the modules under `app/static/` directly; `tests/dom_stub.mjs` is the only fake DOM."

- [ ] **Step 3: Close the cleanup record**

In the section Task 4 added to `docs/cleanup.md`, change `Status: in progress on branch` to `Status: completed on <today's date> on branch`.

- [ ] **Step 4: Run everything**

Run: `for test in tests/test_*.mjs; do node "$test" || exit 1; done && .venv/bin/python -m unittest discover -s tests`
Expected: every node test prints its passed line; the Python suite passes.

- [ ] **Step 5: Commit and merge**

```sh
git add CONTEXT.md docs/development.md docs/cleanup.md
git commit -m "Name reading preferences and the figure palette in the language"
git switch main
git merge --no-ff front-end-deepening
```

## Open after this plan

- Align the figure `LIGHT` hues with the app tokens (`--accent` `#3f573d` against the figure accent `#2f6f5e`). One edit in `palette.py`, then a new baseline.
- Spacing, letter-spacing and line-height tokens, if a later change needs them.
- The `readingWidths` keys name margins (`narrow` is the widest measure). Renaming them means migrating the stored `papers-margin` value.
- `docs/development.md:106` named a test file that did not exist; the node tests are now listed by glob.
