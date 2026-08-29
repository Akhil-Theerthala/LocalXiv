# Warm Journal Popup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the blue utility popup with the approved warm research-journal and index-card interface while improving job progress, settings affordance, single-paper identity, and form accessibility.

**Architecture:** Keep the popup's existing IDs and state flow, but move the status card ahead of page context and add narrowly scoped DOM nodes for progress and paper metadata. CSS owns the visual system and responsive state styling; `popup.js` only derives text, visibility, accessibility attributes, and progress values. The extension receives a small bookmark-style SVG source and four generated PNG icons.

**Tech Stack:** Chrome MV3, semantic HTML, vanilla CSS, vanilla JavaScript, Node's built-in test runner, SVG plus macOS Quick Look/SIPS for PNG export.

## Global Constraints

- Keep the existing MV3 popup, background worker, native-messaging host, Pandoc conversion, EPUB validation, and macOS Mail flow.
- Add no frontend framework, package, hosted service, private alphaXiv API, paper selector, drag reordering, queue, or persistent paper library.
- Keep one-click sending for a single paper after the Kindle address has been saved.
- Preserve the saved Kindle address, named job state, five-row collection preview, exact collection count, and 50-paper maximum.
- Use an ivory/graphite/rust palette with a quiet gray dotted grid; do not add blue, ruled lines, stains, tears, or a notebook margin stripe.
- Use Georgia for display type, Avenir Next/system sans for controls and prose, and SFMono-Regular/system monospace for metadata.
- Keep visible focus treatment, 44-pixel controls, dark mode, reduced motion, polite live regions, and non-text control contrast.
- Do not modify `native/host.py` or `tests/test_host.py`; both contain unrelated user changes.
- Verification must not trigger macOS Mail.

---

## File map

- Modify `extension/popup.html`: semantic order, status progress, paper ID, settings affordance, and manual-upload placement.
- Modify `extension/popup.css`: complete warm journal visual system, dotted texture, card hierarchy, progress, dark mode, focus, and reduced motion.
- Modify `extension/popup.js`: render paper identity, settings action, progress values, and `aria-invalid`.
- Create `extension/icons/bookmark-k.svg`: vector source for the rust bookmark identity.
- Create `extension/icons/icon-16.png`, `icon-32.png`, `icon-48.png`, and `icon-128.png`: Chrome extension icon assets.
- Modify `extension/manifest.json`: declare extension and action icons.
- Modify `tests/test_extension.js`: extend the popup harness and cover the new behavioral and static contracts.

### Task 1: Lock the semantic and behavioral UI contract

**Files:**
- Modify: `tests/test_extension.js`
- Modify: `extension/popup.html`
- Modify: `extension/popup.js`

**Interfaces:**
- Consumes: existing `renderContext()`, `renderSettings(value)`, and `renderJob(job)` functions in `popup.js`.
- Produces: DOM IDs `paper-id`, `settings-action`, `status-progress-wrap`, `status-progress`, and `status-progress-text`; the later CSS task styles these exact nodes.

- [ ] **Step 1: Extend the fake popup node and selector set**

Add attribute and progress support to `popupNode()`:

```js
attributes: {},
max: 1,
value: 0,
setAttribute(name, value) {
  this.attributes[name] = String(value);
},
removeAttribute(name) {
  delete this.attributes[name];
},
```

Add these selectors to `loadPopup()` and initialize the two wrappers as hidden:

```js
"#paper-id",
"#settings-action",
"#status-progress-wrap",
"#status-progress",
"#status-progress-text",
```

- [ ] **Step 2: Write failing behavior tests**

Add focused tests that initialize a paper popup, emit a collection progress job, and submit an invalid then valid Kindle address:

```js
test("popup shows the current paper identifier", async () => {
  const popup = loadPopup({
    tab: { id: 1, url: "https://arxiv.org/abs/2401.01234v2" },
    jobState: { state: "idle" },
  });
  await popupTick();
  await popupTick();
  assert.equal(popup.nodes["#paper-id"].textContent, "arXiv 2401.01234v2");
  assert.equal(popup.nodes["#paper-id"].hidden, false);
});

test("popup renders bounded collection progress", async () => {
  const popup = loadPopup({
    tab: { id: 1, url: "https://arxiv.org/abs/2401.01234" },
    jobState: {
      state: "working",
      message: "Converting paper 2 of 5.",
      current: 2,
      total: 5,
      job_label: "War Studies",
      paper_count: 5,
    },
  });
  await popupTick();
  await popupTick();
  assert.equal(popup.nodes["#status-progress-wrap"].hidden, false);
  assert.equal(popup.nodes["#status-progress"].max, 5);
  assert.equal(popup.nodes["#status-progress"].value, 2);
  assert.equal(popup.nodes["#status-progress-text"].textContent, "2 / 5 · 40%");
});
```

Extend the delivery test to assert `settings-action` is `Edit` for a saved address and `Add` otherwise. Add a popup form test that asserts invalid submission sets `email.attributes["aria-invalid"]` to `"true"`, then dispatches an `input` event and asserts the attribute is removed.

- [ ] **Step 3: Run the focused tests and confirm failure**

Run:

```bash
node --test --test-name-pattern="paper identifier|collection progress|delivery|aria-invalid" tests/test_extension.js
```

Expected: FAIL because the new selectors and render behavior do not exist.

- [ ] **Step 4: Add the semantic HTML**

Move `#status` immediately after the brand header and move `#manual` inside it. Add this progress block after `#status-message`:

```html
<div id="status-progress-wrap" class="status-progress" hidden>
  <div class="status-progress-copy">
    <span>Collection progress</span>
    <span id="status-progress-text"></span>
  </div>
  <progress id="status-progress" max="1" value="0" aria-label="Collection conversion progress"></progress>
</div>
```

Add `<p id="paper-id" class="paper-meta" hidden></p>` between the page title and description. Change the settings summary to include a visible action and chevron while retaining `#settings-summary`:

```html
<summary>
  <span class="settings-copy">
    <span>Delivery settings</span>
    <span id="settings-summary">Kindle address not set</span>
  </span>
  <span class="settings-affordance">
    <span id="settings-action">Add</span>
    <span class="chevron" aria-hidden="true">⌄</span>
  </span>
</summary>
```

- [ ] **Step 5: Implement minimal render behavior**

In `popup.js`, query the five new nodes. In `renderContext()`, show `paper-id` only for paper contexts and set it to ``arXiv ${context.id}``. In `renderSettings()`, set `settings-action` to `Edit` for a normalized saved address and `Add` otherwise.

In `renderJob()`, show progress only when state is `working`, `paper_count > 1`, and `current` and `total` are finite positive integers with `0 <= current <= total`. Set `max`, `value`, and text using:

```js
const percent = Math.round((current / total) * 100);
statusProgressText.textContent = `${current} / ${total} · ${percent}%`;
```

At submit start, remove `aria-invalid`. On invalid input set it to `true`. Add an `input` listener that clears the error text, hides the error, and removes `aria-invalid` once `normalizeKindleEmail(email.value)` succeeds.

- [ ] **Step 6: Run the extension suite**

Run:

```bash
node --test tests/test_extension.js
```

Expected: every extension test passes.

### Task 2: Apply the warm journal visual system

**Files:**
- Modify: `extension/popup.html`
- Modify: `extension/popup.css`
- Test: `tests/test_extension.js`

**Interfaces:**
- Consumes: the Task 1 DOM structure and existing state classes `working`, `success`, and `error`.
- Produces: the final 360-pixel light/dark popup presentation; no JavaScript API changes.

- [ ] **Step 1: Write a failing static style contract test**

Read `popup.html` and `popup.css` in the test file and assert:

```js
test("popup source keeps the approved journal structure and texture", () => {
  const html = fs.readFileSync(path.resolve(__dirname, "../extension/popup.html"), "utf8");
  const css = fs.readFileSync(path.resolve(__dirname, "../extension/popup.css"), "utf8");
  assert.ok(html.indexOf('id="status"') < html.indexOf('class="context"'));
  assert.match(css, /radial-gradient/);
  assert.match(css, /Georgia/);
  assert.match(css, /Avenir Next/);
  assert.match(css, /SFMono-Regular/);
  for (const oldBlue of ["#2458a6", "#194784", "#7eaae9", "#9bbcef"]) {
    assert.equal(css.includes(oldBlue), false);
  }
});
```

- [ ] **Step 2: Run the static test and confirm failure**

Run:

```bash
node --test --test-name-pattern="approved journal" tests/test_extension.js
```

Expected: FAIL because the current CSS still contains the blue palette and no dotted texture.

- [ ] **Step 3: Replace the CSS tokens and texture**

Use these light-mode foundations:

```css
:root {
  color-scheme: light dark;
  font-family: "Avenir Next", Avenir, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  --page: #f1ede3;
  --paper: #fbf8ef;
  --paper-strong: #fffdf7;
  --text: #2c2924;
  --muted: #665f55;
  --border: #8d8375;
  --accent: #9b432b;
  --accent-hover: #7d311f;
  --accent-text: #fffaf2;
  --focus: #a84b2e;
  --error: #962f2f;
  --error-surface: #f8e9e4;
  --success: #42664b;
  --success-surface: #e7efe5;
  --working-surface: #f3e8dc;
  --shadow: 0 8px 22px rgba(56, 43, 31, 0.08);
  --radius: 8px;
}
```

Set `body` to a 360-pixel warm surface with a low-contrast 18-pixel dotted grid:

```css
background-color: var(--page);
background-image: radial-gradient(circle, rgba(92, 87, 79, 0.22) 0 0.65px, transparent 0.8px);
background-size: 18px 18px;
```

Use Georgia for `h1` and the brand name, SFMono-Regular for `.paper-meta`, preview metadata hooks, status counters, and progress copy. Render the mark as a rust bookmark with `clip-path: polygon(0 0, 100% 0, 100% 100%, 50% 78%, 0 100%)`.

- [ ] **Step 4: Style the hierarchy and controls**

Give `main` 16-pixel padding and 12-pixel vertical gaps. Treat `.context`, `#status`, and `details` as warm paper cards with one-pixel borders, 8-pixel radii, and the shared restrained shadow. Make `#status` visually stronger through a rust top rule and state-specific surface colors. Style progress with `accent-color: var(--accent)` plus WebKit track/value selectors.

Make preview rows compact catalog entries: remove default list markers, add a two-column counter gutter with CSS counters, use a faint row divider, and keep title wrapping. Keep `+ N more` monospace. Give summary a grid with the setting copy on the left and `Add`/`Edit` plus chevron on the right. Rotate the chevron when details is open. Keep all inputs and buttons at least 44 pixels high, use a three-pixel rust focus outline, and give disabled buttons an opaque paper/rust treatment instead of relying only on opacity.

- [ ] **Step 5: Add dark and reduced-motion rules**

Use this dark foundation:

```css
@media (prefers-color-scheme: dark) {
  :root {
    --page: #1f1e1b;
    --paper: #292824;
    --paper-strong: #302e29;
    --text: #f1ede3;
    --muted: #bbb3a6;
    --border: #7c7569;
    --accent: #d17a59;
    --accent-hover: #e28f6d;
    --accent-text: #211915;
    --focus: #e3aa75;
    --error: #f0a09a;
    --error-surface: #422825;
    --success: #a7c5a8;
    --success-surface: #26362a;
    --working-surface: #3b3027;
    --shadow: 0 8px 24px rgba(0, 0, 0, 0.24);
  }
  body {
    background-image: radial-gradient(circle, rgba(210, 204, 191, 0.16) 0 0.65px, transparent 0.8px);
  }
}
```

Under `prefers-reduced-motion: reduce`, remove transitions from buttons and the settings chevron.

- [ ] **Step 6: Run tests and syntax checks**

Run:

```bash
node --test tests/test_extension.js
node --check extension/popup.js
```

Expected: all tests pass and syntax checking is silent.

### Task 3: Add the bookmark extension icons

**Files:**
- Create: `extension/icons/bookmark-k.svg`
- Create: `extension/icons/icon-16.png`
- Create: `extension/icons/icon-32.png`
- Create: `extension/icons/icon-48.png`
- Create: `extension/icons/icon-128.png`
- Modify: `extension/manifest.json`
- Test: `tests/test_extension.js`

**Interfaces:**
- Consumes: the rust bookmark mark established in Task 2.
- Produces: Chrome manifest `icons` and `action.default_icon` maps for sizes 16, 32, 48, and 128.

- [ ] **Step 1: Write a failing manifest/icon test**

Add a test that parses `manifest.json`, compares both icon maps to the exact four relative paths, and asserts each PNG exists with a nonzero size:

```js
const expectedIcons = {
  "16": "icons/icon-16.png",
  "32": "icons/icon-32.png",
  "48": "icons/icon-48.png",
  "128": "icons/icon-128.png",
};
assert.deepEqual(manifest.icons, expectedIcons);
assert.deepEqual(manifest.action.default_icon, expectedIcons);
```

- [ ] **Step 2: Run the icon test and confirm failure**

Run:

```bash
node --test --test-name-pattern="manifest.*icon" tests/test_extension.js
```

Expected: FAIL because no icon declarations or files exist.

- [ ] **Step 3: Create the vector source**

Create a 512-by-512 SVG with a transparent canvas, a `#9b432b` bookmark silhouette inset by 72 pixels, a warm `#fffaf2` capital `K` centered in Georgia Bold, and a downward center notch. Do not add gradients, shadows, blue, fine lines, or small secondary details that disappear at 16 pixels.

- [ ] **Step 4: Export and resize the PNG assets**

Render the SVG to a temporary 512-pixel PNG with Quick Look, then resize copies with SIPS:

```bash
qlmanage -t -s 512 -o /private/tmp extension/icons/bookmark-k.svg
sips -z 16 16 /private/tmp/bookmark-k.svg.png --out extension/icons/icon-16.png
sips -z 32 32 /private/tmp/bookmark-k.svg.png --out extension/icons/icon-32.png
sips -z 48 48 /private/tmp/bookmark-k.svg.png --out extension/icons/icon-48.png
sips -z 128 128 /private/tmp/bookmark-k.svg.png --out extension/icons/icon-128.png
```

Inspect the 16- and 128-pixel results before continuing.

- [ ] **Step 5: Declare the icons in the manifest**

Add the exact `icons` map at the manifest root and the same object as `action.default_icon`. Keep the existing action title and popup.

- [ ] **Step 6: Run tests and validate the manifest**

Run:

```bash
node --test tests/test_extension.js
python3 -m json.tool extension/manifest.json
```

Expected: all tests pass and the manifest prints as valid JSON.

### Task 4: Visual QA and isolated commit

**Files:**
- Verify: `extension/popup.html`
- Verify: `extension/popup.css`
- Verify: `extension/popup.js`
- Verify: `extension/manifest.json`
- Verify: `extension/icons/*`
- Verify: `tests/test_extension.js`

**Interfaces:**
- Consumes: the completed warm journal popup.
- Produces: a visually inspected, test-passing redesign commit that chronology can build on.

- [ ] **Step 1: Serve a no-send popup fixture**

Open `popup.html` through the local project server with a fixture that supplies `chrome` state for paper, folder, over-limit, working progress, success, and Mail-error states. The fixture must stub `runtime.sendMessage` and native messaging so no Mail request is possible.

- [ ] **Step 2: Inspect all states at 360 CSS pixels**

Check light and dark modes for: quiet dots behind copy, status-before-context hierarchy, long title wrapping, five preview rows plus remainder, progress bar and numbers, single-paper arXiv ID, disabled controls, Add/Edit settings affordance, error text, manual link, focus outlines, and no horizontal overflow.

- [ ] **Step 3: Run the visual implementation checks**

Run:

```bash
node --test tests/test_extension.js
node --check extension/shared.js
node --check extension/background.js
node --check extension/popup.js
python3 -m json.tool extension/manifest.json
git diff --check
```

Expected: every test passes, syntax/JSON/whitespace checks are silent, and the unrelated Python files remain unstaged.

- [ ] **Step 4: Commit only the visual redesign**

```bash
git add extension/popup.html extension/popup.css extension/popup.js extension/manifest.json extension/icons tests/test_extension.js docs/superpowers/plans/2026-08-29-warm-journal-popup.md
git commit -m "feat: redesign popup as warm research journal"
```

Before committing, run `git diff --cached --name-only` and confirm it does not list `native/host.py` or `tests/test_host.py`.
