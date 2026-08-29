# Pandoc Caption and Extension Cache Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert arXiv `2510.13290` with faithful captions and metadata, and clear transient extension session cache after every persisted EPUB.

**Architecture:** Add narrow TeX preprocessors that unwrap pure environment/font wrappers and translate caption-local, single-line small-caps environments before Pandoc. Match only against a length-preserving view that masks comments and literal code environments. Add an ICML-only metadata fallback and one storage helper used by the MV3 background worker to clear `chrome.storage.session` at the EPUB-result boundary and republish the current terminal state.

**Tech Stack:** Python 3.14, Pandoc 3.10, `unittest`, Chrome Manifest V3 JavaScript, Node's built-in test runner.

## Global Constraints

- Preserve all existing uncommitted alphaXiv, anthology, citation, and inline-math work.
- Preserve `chrome.storage.local.kindleEmail`; it is a setting, not cache.
- Treat any terminal native response with a non-empty `epub_path` as completed EPUB generation, including Mail delivery errors.
- Do not clear the fresh terminal `jobState` that drives completion and manual-upload UI.
- Do not add dependencies, publish, push, or send a real email.
- Do not commit overlapping dirty files automatically.

---

### Task 1: Preserve text from environment-backed caption macros

**Files:**
- Modify: `tests/test_host.py`
- Modify: `native/host.py`

**Interfaces:**
- Consumes: existing `_braced_argument(text: str, position: int)` and `convert_source(...)` preprocessing pipeline.
- Produces: `prepare_inline_box_commands(source_dir: Path) -> int`, returning the number of safely unwrapped definitions.

- [x] **Step 1: Write the failing integration regression**

Add `test_convert_source_preserves_environment_backed_caption_markers`. Its TeX fixture must contain the real `\kw → \rawstepcolor → \stepone/\steptwo/\stepthree` chain and the failing multiline figure caption. Run real `convert_source`, open the resulting EPUB, find the `figcaption`, and assert the literal text includes:

```text
Visualisation of MERA methodology to mechanistically steer LMs: 1. cache activations, and errors, 2. train error estimators, 3. calibrate steering thresholds.
```

- [x] **Step 2: Run the focused test and verify RED**

Run:

```sh
python3 -m unittest -v tests.test_host.HostTests.test_convert_source_preserves_environment_backed_caption_markers
```

Expected: `ConversionError` containing Pandoc's `unexpected \begin` at `\stepone`.

- [x] **Step 3: Implement the narrow preprocessor**

Scan each `.tex` file for command definitions with one or more required arguments. Parse the definition body with `_braced_argument`; after removing TeX comments for matching only, accept exactly this shape:

```text
\begin{environment}[optional formatting options]{#N}\end{environment}\xspace
```

Replace only the original body content with `#N`, reject argument indexes outside the declared arity, preserve all other definitions byte-for-byte, and call the preprocessor before Pandoc in `convert_source`.

- [x] **Step 4: Run the focused test and verify GREEN**

Run the same focused command and require one passing test with no warnings.

- [x] **Step 5: Run related converter regressions**

Run the caption regression together with prompt-block, table, inline-math, and code-block conversion tests to ensure the preprocessor does not consume meaningful structure.

- [x] **Step 6: Preserve the paper's remaining caption formatting**

Normalize only the paper's pure `\usefont` wrapper and caption-local, single-line
`sc` environments. Protect TeX comments plus literal `verbatim`, `verbatim*`,
`Verbatim`, `lstlisting`, `minted`, and `alltt` bodies from all three scanners,
including inline fake terminators and odd/even slash-run cases.

### Task 2: Clear transient extension cache at the completed-EPUB boundary

**Files:**
- Modify: `tests/test_extension.js`
- Modify: `extension/shared.js`
- Modify: `extension/background.js`

**Interfaces:**
- Produces: `storeTerminalJob(response, sessionStorage) -> Promise<object>` in `XivKindle`.
- Consumes: a Chrome-compatible storage area exposing async `clear()` and `set(object)` methods.

- [x] **Step 1: Write failing storage-state regressions**

Use an in-memory storage area with real mutable state, not assertions on mock call counts. Verify:

```text
ok + epub_path       -> stale session keys removed; fresh success job remains
Mail error + path    -> stale session keys removed; fresh error job and path remain
conversion error     -> unrelated session state remains; fresh error job is stored
```

- [x] **Step 2: Run the Node suite and verify RED**

Run:

```sh
node --test tests/test_extension.js
```

Expected: failure because `storeTerminalJob` is not exported.

- [x] **Step 3: Implement and wire the storage helper**

In `extension/shared.js`, build the terminal job from `response`, clear the supplied session storage only when `response.epub_path` is non-empty, set `{ jobState: job }`, and return the job. In `extension/background.js`, import `shared.js` with `importScripts`, then replace the terminal `setJob` block with `storeTerminalJob(response, chrome.storage.session)`.

- [x] **Step 4: Run the Node suite and verify GREEN**

Require all extension tests to pass, then run `node --check` on all three JavaScript files.

### Task 3: Recover ICML front-matter metadata

**Files:**
- Modify: `tests/test_host.py`
- Modify: `native/host.py`

- [x] **Step 1: Add ICML metadata regressions**

Cover the full `\icmltitle`, repeated `\icmlauthor` commands inside
`icmlauthorlist`, ordinary-field precedence, author scoping, nested braces, and
the paper's `Hedstr\"om` accent.

- [x] **Step 2: Implement the narrow fallback**

Use balanced command arguments, never the running title, ignore affiliations and
commands outside the author-list environment, and normalize standard one-letter
TeX accents to Unicode NFC.

### Task 4: Verify the untouched paper and repository

**Files:**
- No production edits expected.

**Interfaces:**
- Consumes: official arXiv `2510.13290` source archive and the completed implementation.
- Produces: a locally retained, validated EPUB plus fresh verification evidence.

- [x] **Step 1: Re-extract the official source into a fresh temporary directory**

Use the downloaded arXiv archive so no preprocessed source from the red run is reused.

- [x] **Step 2: Convert and inspect the real output**

Run `convert_source` with installed Pandoc, validate the EPUB, and inspect XHTML to confirm the method figure caption includes all three numbered step texts and contains no raw `kwColorBox`, `stepone`, `steptwo`, or `stepthree` TeX.

- [x] **Step 3: Run full validation**

```sh
python3 -m unittest -v
node --test tests/test_extension.js
python3 -m py_compile native/host.py tests/test_host.py
node --check extension/shared.js
node --check extension/background.js
node --check extension/popup.js
bash -n install.sh
python3 -m json.tool extension/manifest.json
git diff --check
```

- [x] **Step 4: Review the final diff**

Confirm only the intended converter, extension storage, regressions, and plan/spec additions are new; distinguish them from the pre-existing dirty alphaXiv/anthology work.
