# Review-First Library Jobs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent overlapping native jobs, make alphaXiv folder membership reviewable before delivery, label background results, and bound temporary anthology source data.

**Architecture:** Keep the current popup, MV3 service worker, native-messaging port, and Python host. Put URL, folder-entry, job-identity, and terminal-storage rules in `extension/shared.js`; let the worker own one local port per accepted job; let the popup render the normalized collection and named global job; remove only per-paper source inputs after each validated EPUB is complete.

**Tech Stack:** Manifest V3 JavaScript, Chrome extension storage and native messaging, Node's built-in test runner, Python standard library and `unittest`, Pandoc, macOS Quick Look, SIPS, and Mail.

## Global Constraints

- Keep the current MV3 popup, service worker, native-messaging host, Pandoc, and macOS Mail architecture.
- Add no dependency, hosted service, alphaXiv account access, private API, queue, cancellation protocol, or persistent paper cache.
- Keep `chrome.storage.local.kindleEmail` as the durable setting.
- Clear every stale `chrome.storage.session` key after a terminal response contains `epub_path`, while keeping the fresh terminal `jobState` visible.
- Keep the single-paper action as one click after the Kindle address has been saved.
- Keep collection order equal to first-seen DOM order and the existing 50-paper maximum.
- Continue to download TeX only from arXiv and fail before Mail when conversion or validation fails.
- Do not send Mail during automated or visual verification.
- Use only repository code, browser-native APIs, and the Python standard library.

---

### Task 1: Serialize terminal state and name every job

**Files:**
- Modify: `extension/shared.js:70-109`
- Modify: `extension/background.js:1-58`
- Test: `tests/test_extension.js:18-278`

**Interfaces:**
- Produces: `jobIdentity(request) -> { job_label: string, paper_count: number }`.
- Produces: `storeTerminalJob(response, sessionStorage, identity = {}) -> Promise<object>`.
- Produces: session `jobState` objects whose working, progress, and terminal forms retain `job_label` and `paper_count`.
- Preserves: `storeTerminalJob` removes prior non-`jobState` session keys only when the response has `epub_path`.

- [ ] **Step 1: Extend the in-memory session storage test double**

Add real `get`, `set`, `remove`, and `clear` behavior plus an operation log. Allow a test hook to delay selected `set` calls:

```js
function inMemoryStorage(initialState, { beforeSet } = {}) {
  const state = { ...initialState };
  const operations = [];
  return {
    state,
    operations,
    async get() {
      return { ...state };
    },
    async set(values) {
      await beforeSet?.(values);
      operations.push(["set", Object.keys(values)]);
      Object.assign(state, values);
    },
    async remove(keys) {
      const list = Array.isArray(keys) ? keys : [keys];
      operations.push(["remove", list]);
      for (const key of list) delete state[key];
    },
    async clear() {
      operations.push(["clear"]);
      for (const key of Object.keys(state)) delete state[key];
    },
  };
}
```

- [ ] **Step 2: Write failing shared-helper tests**

Import `jobIdentity`. Add literal assertions for one paper and one deduplicated collection. Change the terminal-storage assertions so a saved EPUB publishes `jobState` before removing `selectedPaper` and `progress`, never calls `clear`, and leaves only the terminal job. Keep the existing no-EPUB assertion that unrelated state survives.

```js
assert.deepEqual(jobIdentity({ url: "https://arxiv.org/abs/2503.15850v2" }), {
  job_label: "Paper 2503.15850v2",
  paper_count: 1,
});

assert.deepEqual(
  jobIdentity({
    urls: [
      "https://www.alphaxiv.org/abs/2503.15850",
      "https://arxiv.org/abs/2503.15850",
      "https://arxiv.org/abs/2401.01234",
    ],
    collection_title: " Uncertainty Lab | alphaXiv ",
  }),
  { job_label: "Uncertainty Lab", paper_count: 2 },
);
```

- [ ] **Step 3: Write the failing terminal-race test**

Delay the terminal `jobState` write, attempt a second `start`, and assert that it returns `A conversion is already running.` before releasing the write. Assert the first captured native port disconnects once and the terminal state keeps the same identity.

```js
const terminalWriteStarted = Promise.withResolvers();
const releaseTerminalWrite = Promise.withResolvers();
const storage = inMemoryStorage({}, {
  beforeSet: async ({ jobState }) => {
    if (jobState?.state === "success") {
      terminalWriteStarted.resolve();
      await releaseTerminalWrite.promise;
    }
  },
});
```

Use the repository's supported Node runtime syntax. If `Promise.withResolvers` is unavailable, replace it with two locally captured resolver functions in the test.

- [ ] **Step 4: Run the focused Node suite and confirm red**

Run: `node --test tests/test_extension.js`

Expected: failures because `jobIdentity` is absent, terminal storage still calls `clear`, and `working` becomes false before delayed terminal persistence completes.

- [ ] **Step 5: Implement the shared helpers minimally**

Add `jobIdentity`. Update `storeTerminalJob` to merge the supplied identity into the terminal job. For responses with `epub_path`, read prior keys, write `{ jobState: job }`, then remove prior keys other than `jobState`. Do not call `clear`.

```js
const stale = await sessionStorage.get(null);
await sessionStorage.set({ jobState: job });
const staleKeys = Object.keys(stale).filter((key) => key !== "jobState");
if (staleKeys.length) await sessionStorage.remove(staleKeys);
```

- [ ] **Step 6: Fix the worker race at its owner**

Keep the synchronous `working = true` reservation. Inside each accepted start, use `const port = chrome.runtime.connectNative(HOST)` and a local `let terminalReceived = false`. Merge one `identity` into every stored working and progress state. On a terminal message, set `terminalReceived = true`, await terminal storage, then set `working = false` and disconnect `port`. The disconnect listener must ignore the port after a terminal message and must never reference another job's port.

- [ ] **Step 7: Run the focused Node suite and confirm green**

Run: `node --test tests/test_extension.js`

Expected: all extension tests pass, including the deliberately delayed terminal-state interleaving.

- [ ] **Step 8: Run JavaScript syntax and whitespace checks**

Run:

```sh
node --check extension/shared.js
node --check extension/background.js
git diff --check
```

Expected: every command exits 0.

- [ ] **Step 9: Commit the task**

```sh
git add extension/shared.js extension/background.js tests/test_extension.js
git commit -m "fix: serialize terminal native jobs"
```

---

### Task 2: Review alphaXiv folders before sending

**Files:**
- Modify: `extension/shared.js:8-109`
- Modify: `extension/popup.js:1-153`
- Modify: `extension/popup.html:14-57`
- Modify: `extension/popup.css:59-265`
- Modify: `README.md:34-45`
- Test: `tests/test_extension.js`

**Interfaces:**
- Consumes: `jobState.job_label` and `jobState.paper_count` from Task 1.
- Produces: `isAlphaXivFolderUrl(value) -> boolean`.
- Produces: `normalizePaperEntries(values) -> Array<{ id: string, url: string, title: string }>`.
- Produces: collection contexts with `papers`, `urls`, and `overLimit` fields.
- Preserves: `normalizePaperUrls(values) -> string[]` for native-host request construction and job identity.

- [ ] **Step 1: Write failing folder-contract tests**

Add literal tests proving:

```js
assert.equal(
  isAlphaXivFolderUrl("https://www.alphaxiv.org/library/folders/uncertainty?sort=added"),
  true,
);
assert.equal(isAlphaXivFolderUrl("https://www.alphaxiv.org/search?q=uncertainty"), false);
assert.equal(isAlphaXivFolderUrl("https://www.alphaxiv.org/library/folders/"), false);
```

Pass `{ url, title }` objects through `pageContext`. Assert first-seen order, normalized URLs, collapsed labels, `Paper {id}` fallback, and rejection of a non-folder alphaXiv page even when it contains valid paper links. Build a literal 51-entry collection and assert `overLimit === true`.

- [ ] **Step 2: Run the focused Node suite and confirm red**

Run: `node --test tests/test_extension.js`

Expected: failures because folder-route validation, labeled entries, and `overLimit` do not exist.

- [ ] **Step 3: Implement shared folder normalization**

Add `MAX_COLLECTION_PAPERS = 50`, `isAlphaXivFolderUrl`, and `normalizePaperEntries`. Accept either legacy string inputs or `{ url, title }` objects so `normalizePaperUrls` remains compatible. Normalize the output URL from the trusted parsed site, collapse label whitespace, cap it at 160 characters, and fall back to `Paper {id}`. Make `pageContext` create a collection only for `isAlphaXivFolderUrl(activeUrl)` and return:

```js
{
  kind: "collection",
  title: cleanCollectionTitle(title),
  papers,
  urls: papers.map((paper) => paper.url),
  overLimit: papers.length > MAX_COLLECTION_PAPERS,
}
```

- [ ] **Step 4: Run the shared-helper tests and confirm green**

Run: `node --test tests/test_extension.js`

Expected: all helper and background tests pass before popup markup changes.

- [ ] **Step 5: Add the compact review markup and accessibility state**

Add `aria-live="polite"` to the context section. Add a hidden ordered list `#paper-preview` and paragraph `#paper-preview-more` after the context description. Add `#status-source` inside the job card. Give the Amazon link `rel="noopener"` and an assistive label that says it opens a new tab.

- [ ] **Step 6: Wire the popup to real collection entries**

Change the injected active-tab function to return `{ url: anchor.href, title: anchor.textContent }` entries. Render the first five `context.papers` as native list items and show `+ N more` for the remainder. For an over-limit folder, keep the preview visible, describe the exact 50-paper limit, set button copy to `50 paper limit`, and disable submission. Render `job.job_label` as the active or last-job source without hiding the current-page context.

- [ ] **Step 7: Add only the CSS needed by the new elements**

Use the existing type, color, radius, and spacing variables. Keep the list compact, make long titles wrap, and do not add icons, animation, selection controls, or a second panel.

- [ ] **Step 8: Update the usage documentation**

State that the extension recognizes explicit alphaXiv folder routes, shows the first five collected papers before submission, fails closed on other alphaXiv list pages, and disables collections above 50 before native conversion starts.

- [ ] **Step 9: Run focused verification**

Run:

```sh
node --test tests/test_extension.js
node --check extension/shared.js
node --check extension/background.js
node --check extension/popup.js
python3 -m json.tool extension/manifest.json
git diff --check
```

Expected: every command exits 0.

- [ ] **Step 10: Commit the task**

```sh
git add README.md extension/shared.js extension/popup.js extension/popup.html extension/popup.css tests/test_extension.js
git commit -m "feat: review alphaXiv folders before sending"
```

---

### Task 3: Release converted paper sources during anthology builds

**Files:**
- Modify: `native/host.py:2443-2464`
- Test: `tests/test_host.py:2315-2371`

**Interfaces:**
- Preserves: `process_request(message, progress=None) -> dict` and `build_anthology(papers, title, output)`.
- Produces: before `build_anthology` runs, every retained `paper.epub` exists while its sibling downloaded `source` file and extracted `paper` directory do not.

- [ ] **Step 1: Write the failing cleanup assertion in the anthology test**

Make the mocked download write a source file and the mocked extractor create a source directory with one file. In the `build` side effect, assert for every received paper EPUB:

```python
self.assertTrue(epub.exists())
self.assertFalse((epub.parent / "source").exists())
self.assertFalse((epub.parent / "paper").exists())
```

Keep the existing order, progress, output, and no-Mail assertions.

- [ ] **Step 2: Run the focused Python test and confirm red**

Run:

```sh
python3 -m unittest -v tests.test_host.HostTests.test_process_request_builds_ordered_anthology_with_progress
```

Expected: failure because each paper's downloaded archive and extracted directory still exist when anthology assembly starts.

- [ ] **Step 3: Add the two best-effort cleanup operations**

Immediately after `convert_source` returns successfully and before appending the paper tuple, remove only the no-longer-needed inputs:

```python
payload.unlink(missing_ok=True)
shutil.rmtree(source_dir, ignore_errors=True)
```

Retain `paper_epub`, metadata, the outer temporary directory, and every existing failure boundary.

- [ ] **Step 4: Run the focused test and confirm green**

Run:

```sh
python3 -m unittest -v tests.test_host.HostTests.test_process_request_builds_ordered_anthology_with_progress
```

Expected: the test passes with the ordered EPUB inputs intact and their source inputs removed.

- [ ] **Step 5: Run the full Python suite with macOS rendering access**

Run: `python3 -m unittest -v`

Expected: all tests pass with Quick Look and SIPS available.

- [ ] **Step 6: Run syntax and whitespace checks**

Run:

```sh
python3 -m py_compile native/host.py tests/test_host.py
git diff --check
```

Expected: every command exits 0.

- [ ] **Step 7: Commit the task**

```sh
git add native/host.py tests/test_host.py
git commit -m "fix: release anthology source data early"
```

---

### Task 4: Verify the complete user path and installation contract

**Files:**
- Modify only if verification finds a defect in files already listed above.
- Inspect: `extension/popup.html`, `extension/popup.css`, `extension/popup.js`, `extension/manifest.json`, `install.sh`.

**Interfaces:**
- Consumes: all Task 1 through Task 3 behavior.
- Produces: one reviewed, clean feature branch ready for a local fast-forward into `main`.

- [ ] **Step 1: Run every repository check from a clean command invocation**

Run:

```sh
python3 -m unittest -v
python3 -m py_compile native/host.py tests/test_host.py
bash -n install.sh
python3 -m json.tool extension/manifest.json
node --test tests/test_extension.js
node --check extension/shared.js
node --check extension/background.js
node --check extension/popup.js
git diff --check main...HEAD
```

Expected: Python and Node report zero failures and every syntax, manifest, shell, and whitespace command exits 0.

- [ ] **Step 2: Inspect all required popup states at 360 CSS pixels**

Use temporary fixtures or the installed unpacked extension without committing generated files. Inspect light and dark paper, valid folder, over-limit folder, named working job, named success, and named Mail-error states. Confirm five preview entries, `+ N more`, readable wrapping, visible disabled state, disclosure marker, status label, focus outline, and no horizontal overflow.

- [ ] **Step 3: Verify installed-host provenance before updating it**

Read the installed native-host manifest, confirm its allowed Chrome extension origin matches the installed unpacked extension, and run `./install.sh` with that exact extension ID. Compare the installed host body with workspace `native/host.py` apart from the generated shebang. Do not send Mail.

- [ ] **Step 4: Review the branch diff against the design**

Check every requirement in `docs/superpowers/specs/2026-08-29-review-first-library-jobs-design.md`. Confirm no dependency, queue, cancellation protocol, private API, cloud service, persistent paper cache, selection control, or unrelated refactor was added.

- [ ] **Step 5: Commit verification-only repairs if any**

If verification required a source repair, stage only the repaired source and its covering test, then commit:

```sh
git commit -m "fix: complete library job verification"
```

If verification required no repair, create no empty commit.
