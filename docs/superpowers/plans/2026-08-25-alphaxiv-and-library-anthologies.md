# alphaXiv and Library Anthologies Implementation Plan

> **For agentic workers:** Execute inline with test-driven development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix valid compiled bibliography keys, support alphaXiv paper pages, compile alphaXiv library folders into one paper-title-only EPUB, and make Kindle delivery settings persistent but unobtrusive.

**Architecture:** Keep the standard-library Python converter as the single conversion authority. Add trusted alphaXiv URL aliases, build an anthology by namespacing already-validated member EPUB trees, and use a small MV3 background worker so batch work survives popup closure. The popup injects one read-only active-tab collector for alphaXiv folder links.

**Tech Stack:** Python 3 standard library, Pandoc EPUB3, ZIP/XML, Chrome Manifest V3, plain HTML/CSS/JavaScript, Node built-in test runner.

## Global Constraints

- Preserve each paper's source ordering, wording, figures, tables, equations, citations, bibliography, media, and valid links.
- Use no hosted service, alphaXiv account token, new Python package, or JavaScript dependency.
- Accept at most 50 papers per anthology and deduplicate by normalized arXiv identifier in first-seen order.
- Download source only from the existing arXiv export endpoint.
- Never send email during automated validation.
- Keep the saved Kindle address hidden behind progressive disclosure after first use.
- The anthology table of contents contains paper titles only, in folder order.

---

### Task 1: Compiled bibliography trivia parsing

**Files:**
- Modify: `tests/test_host.py`
- Modify: `native/host.py`

**Interfaces:**
- Produces: `_skip_tex_trivia(text: str, position: int) -> int`
- Changes: `prepare_compiled_bibliography(root: Path) -> list[BibliographyEntry]`

- [x] Add a regression fixture with `\bibitem[Label]% comment\n {key}` plus a commented-out `\bibitem`.
- [x] Run the focused test and confirm the current parser raises `A compiled bibliography key is malformed.`
- [x] Implement one whitespace/comment skipper and scan the comment-stripped BBL without changing key/label failure guarantees.
- [x] Add and fix the Pandoc regression where a multiline `\href` silently removes the full compiled bibliography.
- [x] Run bibliography parser and compiled-citation integration tests.

### Task 2: Shared arXiv and alphaXiv URL parsing

**Files:**
- Modify: `tests/test_host.py`
- Modify: `native/host.py`
- Create: `extension/shared.js`
- Create: `tests/test_extension.js`

**Interfaces:**
- Changes: `parse_arxiv_url(url: str) -> str`
- Produces in JS: `parsePaperUrl(url) -> { id, site } | null`
- Produces in JS: `normalizePaperUrls(urls) -> string[]`

- [x] Add failing Python and Node tests for alphaXiv query/fragment URLs, legacy/versioned IDs, lookalikes, invalid paths, order, and deduplication.
- [x] Run both focused test commands and verify the expected failures.
- [x] Add the two trusted alphaXiv hosts to the shared native parser and implement the dependency-free browser helpers.
- [x] Run the focused tests until green.

### Task 3: Strict anthology EPUB builder

**Files:**
- Modify: `tests/test_host.py`
- Modify: `native/host.py`

**Interfaces:**
- Produces: `build_anthology(papers: list[tuple[PaperMetadata, Path]], title: str, output: Path) -> None`
- Produces: `validate_anthology_toc(path: Path, expected_titles: list[str]) -> None`

- [x] Add two tiny member EPUB fixtures with separate sections, media, and cross-document fragments; specify duplicate filenames to prove namespacing.
- [x] Add a failing test requiring cover, nav, exact title-only ToC labels, member order, copied media, and resolved links.
- [x] Implement collection cover generation, namespaced package/spine assembly, paper-title anchor insertion, and EPUB3 navigation.
- [x] Reuse `validate_epub` for package/link validation and add exact anthology navigation validation.
- [x] Run anthology and existing strict EPUB tests.

### Task 4: Batch request processing and progress

**Files:**
- Modify: `tests/test_host.py`
- Modify: `native/host.py`

**Interfaces:**
- Changes: `process_request(message: dict, progress: Callable[[dict], None] | None = None) -> dict`
- Produces request form: `{urls: string[], collection_title: string, kindle_email: string, send: bool}`

- [x] Add failing tests for ordered deduplication, the 50-paper limit, sequential conversion, progress messages, failure attribution, one anthology build, and no send on conversion failure.
- [x] Extract the existing one-paper download/extract/convert path into one private helper used by both modes.
- [x] Implement batch processing, collection output naming, progress callbacks, and final Mail behavior.
- [x] Update native `main` to emit progress frames before one final response while retaining CLI and one-paper behavior.
- [x] Run process-request and native framing tests.

### Task 5: Popup workflow and background job

**Files:**
- Modify: `extension/manifest.json`
- Create: `extension/background.js`
- Modify: `extension/popup.html`
- Modify: `extension/popup.js`
- Modify: `extension/popup.css`
- Modify: `tests/test_extension.js`

**Interfaces:**
- Popup sends: `{type: "start", request: {...}}`
- Background stores: `{state: "idle"|"working"|"success"|"error", message: string, epub_path?: string}`
- Active-tab collector returns: `{title: string, urls: string[]}`

- [x] Add failing helper tests for page classification, action labels, folder title cleanup, email validation, and non-revealing settings summary.
- [x] Add background service worker and scripting permission, then relay one native port and session-stored progress state.
- [x] Rebuild the popup with context-first hierarchy, collapsed delivery settings, page/folder discovery, full loading/success/error/empty states, and manual-upload fallback.
- [x] Apply the approved accessibility tokens, 44px targets, focus treatment, light/dark variables, reduced motion, and one consistent radius/accent system.
- [x] Run Node tests and syntax-check all extension scripts.

### Task 6: Documentation, installation, and verification

**Files:**
- Modify: `README.md`
- Modify: installed native host through `install.sh` only after local checks pass

- [x] Document alphaXiv paper use, folder collection behavior, the 50-paper limit, exact anthology ToC, background progress, and delivery settings disclosure.
- [x] Run `python3 -m unittest -v`, Python compilation, Node tests/syntax checks, shell syntax, manifest JSON validation, and debug-marker scan.
- [x] Load the unpacked extension in an isolated browser; verify first-use/saved settings, keyboard focus, and light/dark contrast, with folder/job states covered by helper and request tests.
- [x] Reinstall the native host using the existing extension ID and compare the installed host with the workspace implementation.
- [x] Convert one real alphaXiv paper without sending, then build and inspect a real two-paper anthology without sending.
- [x] Re-read the design and report verified local behavior separately from real Mail/Kindle delivery, which remains user-environment dependent.
