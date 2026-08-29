# Initial arXiv Chronology Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Order every eligible alphaXiv collection oldest to newest by each paper's initial arXiv submission timestamp, and make the reviewed preview and compiled anthology use that same verified order.

**Architecture:** Add a focused `chronology.js` browser/CommonJS module that builds one official arXiv `id_list` request, parses Atom entry IDs and `<published>` timestamps with `DOMParser`, validates a complete one-to-one result, throttles and session-caches one batch, and returns stable oldest-first paper objects. The popup owns only loading/error/retry presentation and freshness checks; it derives both preview and request URLs from the returned paper array. The worker and native host stay unchanged because they already preserve request order.

**Tech Stack:** Chrome MV3 popup APIs, official arXiv Atom API, browser `fetch`, `AbortController`, `DOMParser`, `TextEncoder`, vanilla JavaScript, Node's built-in test runner.

## Global Constraints

- Use the Atom entry `<published>` timestamp as the initial arXiv submission time; never use entry `<updated>` or feed-level `<updated>`.
- Sort ascending by parsed timestamp, with original folder position as the stable tie-breaker.
- Make one batched request to `https://export.arxiv.org/api/query` with `id_list`, `start=0`, and explicit `max_results`.
- Ignore feed response order and join results by canonical base arXiv ID.
- Strip a trailing `vN` only for metadata lookup and matching; retain the original normalized conversion URL and display identifier.
- Support modern and legacy identifiers without weakening the existing trusted HTTPS page-link parser.
- Fail closed on timeout, network/HTTP failure, oversized content, malformed XML, API error entry, missing/duplicate/unknown ID, or invalid/missing `<published>`.
- Keep collection submission disabled until chronology is verified; do not fall back to folder order or ID order.
- Block a 51-paper collection before any API request; permit at most 50 papers.
- Respect a minimum three-second interval between request starts and keep at most one bounded session cache.
- Add only `https://export.arxiv.org/*` as a host permission.
- Keep the warm journal redesign, dark mode, reduced motion, 44-pixel controls, and polite live regions.
- Do not modify `native/host.py` or `tests/test_host.py`; both contain unrelated user changes.
- Verification must not trigger macOS Mail.

---

## File map

- Create `extension/chronology.js`: identifier matching, Atom parsing, strict ordering, request limits, timeout, session throttle, and one-batch cache.
- Modify `extension/popup.html`: load `chronology.js` and add the hidden retry action.
- Modify `extension/popup.css`: catalog-row date metadata and secondary retry-button styling.
- Modify `extension/popup.js`: collection chronology lifecycle, loading/error/ready rendering, freshness check, retry, and ordered submission.
- Modify `extension/manifest.json`: add the narrow arXiv API host permission.
- Modify `tests/test_extension.js`: module-level parser/order/request tests and popup integration/race/failure tests.
- Verify only `extension/background.js` and `native/host.py`: no changes; both already preserve input order.

### Task 1: Build strict chronology domain helpers

**Files:**
- Create: `extension/chronology.js`
- Modify: `tests/test_extension.js`

**Interfaces:**
- Consumes: paper objects shaped as `{ id: string, url: string, title: string }` from `XivKindle.pageContext()`.
- Produces:
  - `baseArxivId(value: string): string | null`
  - `parseAtomEntryId(value: string): string | null`
  - `chronologyFingerprint(papers: Paper[]): string`
  - `buildLookupUrl(papers: Paper[]): string`
  - `parseAtomFeed(xmlText: string, DOMParserImpl?: typeof DOMParser): PublishedRecord[]`
  - `orderPapersByInitialSubmission(papers: Paper[], records: PublishedRecord[]): OrderedPaper[]`
  - `PublishedRecord = { id: string, published: string }`
  - `OrderedPaper = Paper & { initialSubmittedAt: string, initialSubmittedDate: string }`

- [ ] **Step 1: Add a fixture-compatible Atom document helper to tests**

Build tiny namespace-aware test nodes rather than regex-parsing XML in production:

```js
function atomDocument(entries, { parserError = false } = {}) {
  const element = (text) => ({ textContent: text });
  return {
    getElementsByTagName(name) {
      return name === "parsererror" && parserError ? [element("Malformed XML")] : [];
    },
    getElementsByTagNameNS(_namespace, name) {
      if (name !== "entry") return [];
      return entries.map((entry) => ({
        getElementsByTagNameNS(_entryNamespace, field) {
          if (!(field in entry)) return [];
          return [element(entry[field])];
        },
      }));
    },
  };
}

function atomParser(documentValue) {
  return class {
    parseFromString() { return documentValue; }
  };
}
```

- [ ] **Step 2: Write failing ID, feed, and ordering tests**

Import the six planned functions from `../extension/chronology.js`. Add tests proving:

```js
assert.equal(baseArxivId("2503.15850v7"), "2503.15850");
assert.equal(baseArxivId("cond-mat/0207270v2"), "cond-mat/0207270");
assert.equal(parseAtomEntryId("http://arxiv.org/abs/2503.15850v3"), "2503.15850");
assert.equal(parseAtomEntryId("https://arxiv.org/api/errors#incorrect_id_format_for_foo"), null);
assert.equal(parseAtomEntryId("https://example.com/abs/2503.15850"), null);
assert.equal(XivKindle.parsePaperUrl("http://arxiv.org/abs/2503.15850"), null);
```

Use feed records returned newest first and conflicting `updated` fixture fields, then assert the result is ordered only by `published` and preserves each title/URL. Add equal-timestamp papers and assert their original positions are retained. Add a versioned modern paper and a legacy paper and assert matching uses base IDs while the returned `id` and `url` remain unchanged.

- [ ] **Step 3: Write failing strict-validation tests**

For `orderPapersByInitialSubmission`, assert throws matching clear internal messages for missing, duplicate, unknown, and invalid-date records. For `parseAtomFeed`, assert parser errors, zero/multiple `<id>` fields, zero/multiple `<published>` fields, and `/api/errors` entries throw. The popup later replaces these internal messages with concise user copy.

- [ ] **Step 4: Run domain tests and confirm failure**

Run:

```bash
node --test --test-name-pattern="base arXiv|Atom|initial submission|chronology" tests/test_extension.js
```

Expected: FAIL because `chronology.js` does not exist.

- [ ] **Step 5: Implement the UMD module and identifier helpers**

Use the repository's browser/CommonJS pattern:

```js
(function (root, factory) {
  const api = factory();
  root.XivChronology = api;
  if (typeof module === "object" && module.exports) module.exports = api;
})(globalThis, function () {
  "use strict";
  const MODERN_ID = /^\d{4}\.\d{4,5}(?:v\d+)?$/;
  const LEGACY_ID = /^[A-Za-z][A-Za-z.-]*\/\d{7}(?:v\d+)?$/;
  const ATOM_NS = "http://www.w3.org/2005/Atom";
  return { baseArxivId, parseAtomEntryId, chronologyFingerprint, buildLookupUrl,
    parseAtomFeed, orderPapersByInitialSubmission };
});
```

`parseAtomEntryId` accepts only `http:` or `https:`, an exact `arxiv.org`/`www.arxiv.org` host, and an `/abs/{id}` path. It returns `baseArxivId(id)` and has no effect on `XivKindle.parsePaperUrl`.

Build the query with `URL` and `URLSearchParams`; deduplicate base IDs in first-seen order. `chronologyFingerprint` is `JSON.stringify(baseIds)` so order and boundaries are unambiguous.

- [ ] **Step 6: Implement strict Atom parsing and stable ordering**

Parse with `new DOMParserImpl().parseFromString(xmlText, "application/xml")`. Reject any `parsererror`. For each Atom `entry`, require exactly one Atom `id` and one Atom `published`, reject API-error IDs before normal ID parsing, and return trimmed record strings.

In `orderPapersByInitialSubmission`, build the requested unique base-ID set, reject records outside it and duplicate records, parse timestamps with `Date.parse`, and require one record for every requested base ID. Decorate each paper with its source index and timestamp, sort by timestamp then source index, and return copies containing:

```js
{
  ...paper,
  initialSubmittedAt: new Date(timestamp).toISOString(),
  initialSubmittedDate: new Date(timestamp).toISOString().slice(0, 10),
}
```

- [ ] **Step 7: Run the domain tests**

Run:

```bash
node --test --test-name-pattern="base arXiv|Atom|initial submission|chronology" tests/test_extension.js
node --check extension/chronology.js
```

Expected: all chronology domain tests pass and syntax checking is silent.

### Task 2: Add the bounded official API request, throttle, and cache

**Files:**
- Modify: `extension/chronology.js`
- Modify: `tests/test_extension.js`

**Interfaces:**
- Consumes: Task 1 `buildLookupUrl`, `parseAtomFeed`, `chronologyFingerprint`, and `orderPapersByInitialSubmission`.
- Produces:
  - `fetchInitialSubmissionRecords(papers, options): Promise<PublishedRecord[]>`
  - `resolveInitialSubmissionOrder(papers, options): Promise<OrderedPaper[]>`
  - `options = { fetchImpl, DOMParserImpl, sessionStorage, timeoutMs?, now?, sleep? , bypassCache? }`
  - session keys `chronologyLastRequestAt` and `chronologyCache`.

- [ ] **Step 1: Write failing fetch boundary tests**

Use a response helper with `ok`, `status`, `headers.get()`, and `text()`. Assert one call uses the exact host and includes encoded `id_list`, `start=0`, and `max_results` equal to the unique base-ID count. Assert a successful response is parsed into records.

Add rejection cases for HTTP 429, HTTP 500, `content-length` above `2 * 1024 * 1024`, body bytes above that limit, a rejected fetch, and a timeout. The timeout fetch stub must listen for `options.signal.abort` and reject with an `AbortError`, so the test completes without a real network call.

- [ ] **Step 2: Write failing throttle and cache tests**

Use `inMemoryStorage`, a mutable clock, and a `sleep(ms)` stub that records `ms` and advances the clock. Prove:

- a first lookup writes `chronologyLastRequestAt` before fetch and stores one `{ fingerprint, records }` cache;
- an identical second lookup returns newly decorated paper objects from cache without fetching;
- a changed fingerprint waits for the remaining portion of 3000 milliseconds and makes one new request;
- `bypassCache: true` refetches but still waits;
- a malformed cache is ignored and replaced by a verified network result.

- [ ] **Step 3: Run request tests and confirm failure**

Run:

```bash
node --test --test-name-pattern="chronology request|chronology cache|chronology throttle" tests/test_extension.js
```

Expected: FAIL because the request functions do not exist.

- [ ] **Step 4: Implement request limits and timeout**

Add constants:

```js
const API_ORIGIN = "https://export.arxiv.org";
const MAX_RESPONSE_BYTES = 2 * 1024 * 1024;
const REQUEST_INTERVAL_MS = 3000;
const REQUEST_TIMEOUT_MS = 30000;
```

In `fetchInitialSubmissionRecords`, reject an empty or over-50 paper array before fetch. Race `fetchImpl(url, { signal, headers: { Accept: "application/atom+xml" } })` against a timeout promise that aborts its controller. Require `response.ok`, check numeric `content-length` before reading, measure the final UTF-8 body with `new TextEncoder().encode(xmlText).byteLength`, then call `parseAtomFeed`.

- [ ] **Step 5: Implement one session cache and request spacing**

In `resolveInitialSubmissionOrder`, read both session keys. Validate an exact fingerprint cache by passing its records through `orderPapersByInitialSubmission`; if valid and not bypassed, return it. Otherwise wait for `max(0, REQUEST_INTERVAL_MS - (now() - lastRequestAt))`, store the fresh request-start timestamp, fetch records, validate/order them, and replace the single cache object. Do not append records or create per-paper cache keys.

- [ ] **Step 6: Run the request and full extension suites**

Run:

```bash
node --test --test-name-pattern="chronology request|chronology cache|chronology throttle" tests/test_extension.js
node --test tests/test_extension.js
```

Expected: all tests pass.

### Task 3: Integrate chronology into collection discovery and review

**Files:**
- Modify: `extension/popup.html`
- Modify: `extension/popup.css`
- Modify: `extension/popup.js`
- Modify: `tests/test_extension.js`

**Interfaces:**
- Consumes: `XivChronology.resolveInitialSubmissionOrder(papers, { fetchImpl, DOMParserImpl, sessionStorage, bypassCache })`.
- Produces: collection contexts with `chronologyState` equal to `loading`, `ready`, or `error`; only `ready` contexts can submit.

- [ ] **Step 1: Extend the popup harness for chronology**

Add `#chronology-retry` to the fake selector set and initialize it hidden. Give `loadPopup()` optional `fetchImpl`, `DOMParserImpl`, and `sessionState` arguments. Its session storage must implement `get(keys)` and `set(values)`, and the VM context must include `fetch`, `DOMParser`, `AbortController`, `TextEncoder`, `setTimeout`, and `clearTimeout`. Load `chronology.js` through `require` as `XivChronology` in the VM globals.

Change the fake node's `append(child)` helper to `append(...children)` and push every supplied child so title and metadata spans can be asserted independently.

Add `chrome.tabs.get(id)` that returns the current test tab. Permit tests to replace that returned tab before a deferred lookup resolves.

- [ ] **Step 2: Rewrite the collection submission test to fail on old order**

Supply folder papers in newer-first DOM order and an Atom document whose entries are also intentionally reversed. Resolve published dates so `2503.15850` is newer than `2401.01234`. Before submit, assert:

```js
assert.equal(popup.nodes["#paper-preview"].children[0].children[0].textContent, "Older paper");
assert.equal(popup.nodes["#paper-preview"].children[0].children[1].textContent,
  "2024-01-03 · arXiv 2401.01234");
```

After submit, assert the `urls` payload is oldest first. Assert fetch was called exactly once.

- [ ] **Step 3: Add loading, failure, retry, limit, and freshness tests**

Add popup tests proving:

- while a deferred lookup is pending, copy says `Checking initial arXiv dates`, send is disabled, and submit sends no runtime message;
- malformed/incomplete metadata produces `chronologyState: error` presentation, a visible `Retry dates` button, a disabled send button, and no runtime message;
- clicking Retry makes one later successful request and enables submission in verified order;
- a 51-paper folder makes zero fetch calls;
- if `chrome.tabs.get()` reports a different URL before lookup completion, the result is discarded, submission stays disabled, and no runtime message is sent;
- a newer retry generation wins over an older deferred response.

- [ ] **Step 4: Run popup chronology tests and confirm failure**

Run:

```bash
node --test --test-name-pattern="collection.*chronolog|initial arXiv|Retry dates|51-paper.*fetch|stale.*lookup" tests/test_extension.js
```

Expected: FAIL because the popup still submits discovery order and has no chronology state.

- [ ] **Step 5: Add the retry UI and script**

Load `chronology.js` after `shared.js` and before `popup.js`. Add this hidden button after the preview summary:

```html
<button id="chronology-retry" class="secondary-action" type="button" hidden>Retry dates</button>
```

Style it as a 44-pixel paper/rust outlined button. Add `.preview-title` and `.preview-meta` styles; the latter uses the metadata font, muted color, and 11-pixel size.

- [ ] **Step 6: Add popup chronology state and rendering**

Destructure `resolveInitialSubmissionOrder` from `XivChronology`. Track `chronologyRevision`, `chronologyBusy`, `collectionSource`, and `inspectedTabId`.

Change `canSubmitContext()` so collections require `!overLimit && chronologyState === "ready"`. In `renderContext()`:

- `loading`: describe checking initial dates and label the primary button `Checking submission dates`;
- `ready`: say ``${count} papers ordered oldest to newest by first arXiv submission.``;
- `error`: explain that the dates could not be verified, show Retry, and label the primary button `Dates required`;
- over-limit: retain the existing limit behavior and never show Retry.

In `renderPreview()`, build two spans per collection row when date metadata exists:

```js
const title = document.createElement("span");
title.className = "preview-title";
title.textContent = paper.title;
const meta = document.createElement("span");
meta.className = "preview-meta";
meta.textContent = `${paper.initialSubmittedDate} · arXiv ${paper.id}`;
item.append(title, meta);
```

- [ ] **Step 7: Resolve, validate freshness, and retry**

Add `prepareCollectionChronology(discovered, { bypassCache = false } = {})`. It increments a revision, stores an immutable discovery source, sets/render loading state, and awaits `resolveInitialSubmissionOrder` with the popup's fetch, DOM parser, and session storage. Before accepting the result, require the same revision and call `chrome.tabs.get(inspectedTabId)`; its current URL must still equal the inspected folder URL.

On success, replace `papers` and derive `urls` from those same ordered objects. On failure for the current revision, set `chronologyState: "error"` and never alter membership. Ignore stale resolutions. Disable Retry while `chronologyBusy`; its click calls the function with `bypassCache: true`.

In `initialize()`, render ordinary paper/unsupported/over-limit contexts immediately. For an in-limit collection, await `prepareCollectionChronology` after showing the loading state.

- [ ] **Step 8: Run popup chronology and full extension tests**

Run:

```bash
node --test --test-name-pattern="collection.*chronolog|initial arXiv|Retry dates|51-paper.*fetch|stale.*lookup" tests/test_extension.js
node --test tests/test_extension.js
```

Expected: all tests pass, and no test calls the native host for failed or pending chronology.

### Task 4: Add the narrow host permission and verify order preservation

**Files:**
- Modify: `extension/manifest.json`
- Modify: `tests/test_extension.js`
- Verify: `extension/background.js`
- Verify: `native/host.py`

**Interfaces:**
- Consumes: one popup-side HTTPS request to `export.arxiv.org` and the sorted `context.urls` payload.
- Produces: manifest permission `host_permissions: ["https://export.arxiv.org/*"]`; no worker/native protocol change.

- [ ] **Step 1: Write a failing permission test**

Parse the manifest and assert:

```js
assert.deepEqual(manifest.host_permissions, ["https://export.arxiv.org/*"]);
```

Also retain the exact existing `permissions` array assertion so the change cannot accidentally add broader capabilities.

- [ ] **Step 2: Run the permission test and confirm failure**

Run:

```bash
node --test --test-name-pattern="arXiv API host permission" tests/test_extension.js
```

Expected: FAIL because `host_permissions` is absent.

- [ ] **Step 3: Add only the official API permission**

Add this root-level manifest field without changing normal extension permissions:

```json
"host_permissions": ["https://export.arxiv.org/*"]
```

- [ ] **Step 4: Run boundary checks**

Run:

```bash
node --test tests/test_extension.js
python3 -m json.tool extension/manifest.json
rg -n "urls: context.urls|postMessage\(\{ \.\.\.message.request|for index, arxiv_id in enumerate\(arxiv_ids" extension/popup.js extension/background.js native/host.py
```

Expected: tests pass; the popup submits its sorted URLs, the worker forwards them, and the host iterates them in received order.

### Task 5: Visual QA, full verification, and isolated commit

**Files:**
- Verify: `extension/chronology.js`
- Verify: `extension/popup.html`
- Verify: `extension/popup.css`
- Verify: `extension/popup.js`
- Verify: `extension/manifest.json`
- Verify: `tests/test_extension.js`

**Interfaces:**
- Consumes: the finished warm journal popup plus strict chronology pipeline.
- Produces: a test-passing oldest-first collection flow with visual evidence and no unrelated staged changes.

- [ ] **Step 1: Inspect no-send collection fixtures**

At 360 CSS pixels in light and dark mode, inspect collection loading, ready, chronology error, retry loading, 51-paper limit, and working conversion. Confirm dates and IDs scan as quiet catalog metadata, the dot grid remains subordinate, the first five rows match oldest-first payload order, retry is visually secondary, and no state overflows horizontally.

- [ ] **Step 2: Run complete repository-safe verification**

Run:

```bash
node --test tests/test_extension.js
node --check extension/shared.js
node --check extension/chronology.js
node --check extension/background.js
node --check extension/popup.js
python3 -m json.tool extension/manifest.json
bash -n install.sh
PYTHONPYCACHEPREFIX=/private/tmp/arxiv-chronology-pycache python3 -m py_compile native/host.py tests/test_host.py
python3 -B -m unittest -q
git diff --check
```

Expected: all extension and Python tests pass, syntax/JSON/shell/whitespace checks are clean, and no Mail message is sent.

- [ ] **Step 3: Inspect scope and user-owned changes**

Run:

```bash
git status --short
git diff -- native/host.py tests/test_host.py
git diff -- extension tests/test_extension.js
```

Expected: the pre-existing Python diffs remain present and unchanged; chronology changes are confined to the listed extension/test files.

- [ ] **Step 4: Commit only chronology work**

```bash
git add extension/chronology.js extension/popup.html extension/popup.css extension/popup.js extension/manifest.json tests/test_extension.js docs/superpowers/plans/2026-08-29-initial-arxiv-chronology.md
git commit -m "feat: order collections by initial arXiv submission"
```

Before committing, run `git diff --cached --name-only` and confirm it does not list `native/host.py` or `tests/test_host.py`.
