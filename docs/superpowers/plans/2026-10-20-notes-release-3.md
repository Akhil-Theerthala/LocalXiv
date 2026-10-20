# Release 3: Notes leave the Paper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The reader's Highlights and Notes go to the Kindle inside the EPUB, every Note of the library is on one page, a new version of a Paper takes the Notes of the old one, and the first major version ships it all.

**Architecture:** A new module `papers/notes_epub.py` marks the words of each Highlight in the packaged EPUB and adds a "Highlights and Notes" chapter, then runs the existing EPUB checks. The Notes page is one more page of the web app, drawn by `app/static/notes.js` from the existing backup route. The copy between versions is one route on the `highlights` table, and the search-on-read of Release 2 places the copied records. The Native shell gets one sidebar row, one menu item, and, with decision 3, one URL host.

**Tech Stack:** Python 3.14 standard library (`zipfile`, `xml.etree`, `sqlite3`), EPUBCheck, plain ES modules in `app/static/`, AppKit in `app/macos/`.

**Spec:** `docs/superpowers/specs/2026-10-20-notes-release-3-design.md`. It builds on `docs/highlights-notes-chat-plan-2026-10-18.md` (sections 5.6, 7, and 9) and on the Release 2 plan `docs/superpowers/plans/2026-10-19-notes-release-2.md`. The Release 2 ledger, with its deferred minors, is in `/Users/silver/Developer/LocalXiv/.scratch/notes-release-2-ledger/`.

## Global Constraints

- Read `CODING_STANDARDS.md` and follow the `ponytail` rules. Run `uvx ruff check .` before each Python commit.
- Work on the branch `notes-release-3` in a worktree under `.worktrees/`. Set it up as the memory note says: copy `tests/`, `papers/html-snapshot`, and `node_modules/` from the main checkout, and symlink `.venv`. Run tests with `.venv/bin/python -m unittest discover -s tests -p <file>`. The full suite takes about 20 minutes with the corpus gate, so run it in the background.
- Tests are route-level, in `tests/test_notes.py` (`NotesTest`, a subclass of `ServerTest` in `tests/test_chat.py`). The test library holds the sample Paper `1706.03762v7` with `paper.epub` and `semantic.epub` (seeded from `app/sample/attention`). This plan adds three tests. Change an existing test only where a task names it. Tests are not tracked, so copy the changed test files into the main checkout's `tests/` after the merge.
- Both shells (plan decision 9). Every new control exists in the Native shell and in the browser shell.
- The Chrome state carries no Note text and no quote. Booleans and counts only (`app/static/shell.js:28-35`).
- No control fixed to the bottom of the window.
- Copy in ASD-STE100 with `CONTEXT.md` terms. The strings in the spec and in this plan are final.
- Commit messages describe the change only, with no attribution line (user rule).
- Merge with `git merge --no-ff notes-release-3` in the main checkout on `main`. Then delete the branch and prune the worktree.
- Decisions 1 to 6 of the spec (section 10) are the user's. Task 1 needs the user's Kindle report before its style step. Task 4 runs only with a yes on decision 3, and Task 5 only with a yes on decision 5. Task 7 needs decisions 4, 5, and 6.

## Decisions this plan takes

- **One text map in Python.** `papers/notes_epub.py` builds the map from each character of a passage element's one text to its text node, as `app/static/onetext.js` `textMap` does. It treats `<img class="math-image">` as `$alt$` and a MathML `math` element as `$tex$` (`papers/document.py` `_tex`, `:250`), so the same code serves `paper.epub` and `semantic.epub`.
- **Marks per text node.** A range that spans several text nodes gets one `<mark>` per node segment. A formula inside the range gets nothing. The number link goes after the last segment.
- **The chapter shares the Markdown order.** `papers/notes_export.py` `_arranged` and `_offset` lose their underscore and become `arranged` and `offset`, so both exports import them. No copy.
- **The OPF and nav are patched as XML**, not rebuilt. The EPUB keeps every other file byte for byte.
- **A formula image follows the stored passage text.** At an `<img class="math-image">` the map takes `$alt$` when `paper['passages']` has `$` at that place, else `alt` (a formula with no TeX). A map whose text differs from the stored text at the end gives no mark.
- **Marks across passages cover the whole span**, from the head to the end quote, as `across` in `app/static/margin.js` paints it.
- **Records of Papers that left the library** are hidden on the Notes page and not counted. The backup keeps them.
- **The Notes page reads `GET /files/library/notes.json`**, the backup route. It carries records of Papers that are no longer in the library, and the page leaves those out by matching `paper` against `state.papers`.
- **The copy refuses a target with records** (409). The offer and the menu item show only when the open Paper has no records.
- **The state count** is one `SELECT COUNT(*) FROM highlights`, read in `GET /api/state` beside the Paper summaries.
- **Keys:** no new key equivalents. The Notes page opens from the sidebar, and Copy Notes from v<n> from the menu.

## Not in this plan

- Everything in spec section 8, with its reasons there.
- A Notes page editor. Editing stays in the margin and All Notes.
- Marks on formulas in the EPUB.
- Release 1.1 Part B. Its own plan runs before Task 7.

## Review Focus

1. A Highlight whose quote occurs twice in a passage: the EPUB marks the occurrence that the reader chose, by prefix and suffix, not the first one. Pinned in Task 1's test with a quote that occurs twice.
2. A Highlight across two text nodes (a quote that crosses an `<em>` or a citation link) and one that contains a formula: every text segment is marked, the formula is not, and the number link follows the last segment. Pinned in Task 1's test.
3. A Not found record and a Paper note: the chapter lists both, with no mark and no link for them, and EPUBCheck still passes. Pinned in Task 1's test.
4. A copy from a Paper with a different arXiv id, or to a target with records: refused, nothing written. Pinned in Task 3's test.
5. The Notes page with a record of a Paper that is not in the library (restored from a backup): the page shows no row of it and no empty group, and the count agrees. Pinned in Task 2's test (the count) and browser check (the page).

---

### Task 1: Highlights and Notes in the EPUB

**Files:**
- Create: `papers/notes_epub.py`
- Modify: `papers/notes_export.py` (rename `_arranged` and `_offset`), `papers/exports.py` (`artifact` signature and the Paper branch), `app/server.py` (the export and send payload `:822-841`, and `execute` `:498`, which passes the records), `app/static/app.js` (`exportView` `:379`, the `export-epub` action `:385` and the `share` item `:404`, the Kindle form `:439-451`), `app/macos/Menus.swift` (the File › Export list `:53-54`), `app/static/index.html` (the Kindle dialog `:92-96`)
- Test: `tests/test_notes.py`

**Interfaces:**
- `notes_epub(source: Path, paper: dict, records: list[dict], groups: list[dict], output: Path) -> Path` in `papers/notes_epub.py`. `records` are the Paper's records after `Application.highlights` (searched). It raises `ValueError` with the EPUBCheck line when the result fails.
- `artifact(library, paper, kind, profile, notes=None)` in `papers/exports.py`. `notes` is `None` or the tuple `(records, groups)`. With the tuple, a kind of `paper` or `both`, and a Paper whose `format` is not `pdf`, the Paper member is the notes EPUB (`paper-notes.epub` or `semantic-notes.epub` in the Paper directory). The server builds the tuple from `app.highlights(paper['id'])` (so the words are searched first) and `app.library.get_groups(paper['id'])` when the body's `notes` is true.
- `POST /api/papers/<id>/export` and `/send` accept `notes` (boolean, default false) in the body, beside `kind` and `profile`.
- Action `export-epub-notes` "Export EPUB with Notes", after `export-epub` in the `share` list (the browser's Share submenu) and as a static item after Export EPUB in File › Export in Swift, enabled when `view === 'paper' && paper.format !== 'pdf' && detail.highlights.length > 0`. Checkbox `kindle-notes` "Include Highlights and Notes" in the Kindle dialog, shown under the same rule and when `artifact-kind` is `paper` or `both`.
- Mark classes `lx-key`, `lx-question`, `lx-use`, `lx-disagree` on `<mark>`, the link class `lx-ref`, the chapter file `notes.xhtml` with entry ids `n1`, `n2`, … in chapter order.

- [ ] **Step 1: Write the failing test** `test_epub_with_notes_marks_the_words_and_adds_a_chapter` in `NotesTest`. Make four records with `self.mark`: one on a quote that occurs twice in its passage (pick the second occurrence by prefix and suffix), one that contains a formula (`$...$` in the one text), one across two text nodes (a quote that spans a citation link in `text/ch004.xhtml`), one across two passages (`end` set, as `self.mark` of the reimport test builds it), and one Not found record (a quote that is in no passage, saved with `found: 'not-found'` through the add route). Add a Paper note and a question with a stub answer on the first record. Export with `self.call(self.route + '/export', dict(kind='paper', profile='kindle', notes=True))`, open the EPUB that the answer names, and assert: `EPUB/notes.xhtml` is in the manifest, last in the spine, and in `nav.xhtml`. The chapter has four entries in All Notes order plus the Paper note first, the Not found line, the Note, the question in bold and the answer with no `[p0…]` citation. The twice-quote's second occurrence is inside `<mark class="lx-key">` and its first is not. The formula quote has marks on the text around the `<img class="math-image">` and none on it. The cross-node quote has two marks and one `<a class="lx-ref" href="notes.xhtml#n…">`. The cross-passage quote has marks in both passages and the text between them. The Not found record has no mark. The `.epubcheck.log` beside the output has no `ERROR`. Then export with `notes=False` and assert the answer names `paper.epub`, unchanged. Then export a `semantic` profile with `notes=True` and assert `semantic-notes.epub` has the same chapter and the formula quote's marks sit around a `math` element.
- [ ] **Step 2: Run** `.venv/bin/python -m unittest discover -s tests -p test_notes.py -k test_epub_with_notes`. Expected: FAIL (the route ignores `notes` and names `paper.epub`).
- [ ] **Step 3: Implement.** Rename `_arranged` and `_offset` in `papers/notes_export.py` and their two call sites. Write `papers/notes_epub.py` with the text map, the marks, the chapter, and the package patch, in that order, and the `reading.css` addition: `mark.lx-key{background:#fff3b0}`, `mark.lx-question{background:#e9d8ff}`, `mark.lx-use{background:#ffe0c2}`, `mark.lx-disagree{background:#ffd6e0}`, `mark[class^=lx-]{text-decoration:underline}`, `a.lx-ref{font-size:0.7em;vertical-align:super;text-decoration:none}`. Thread `notes` through `artifact` and the two routes. Add the menu item and the checkbox.
- [ ] **Step 4: Run** the test and `uvx ruff check .`. Expected: PASS, no problems.
- [ ] **Step 5: Check in the browser** (`.claude/launch.json` entry for the worktree, port of your choice): Export EPUB with Notes downloads `paper-notes.epub`, and Send to Kindle shows the checkbox for the Paper and hides it for the Overview. Open the EPUB in Books: the marks show in colour, each number opens the chapter entry, and each quote in the chapter opens the passage. **Commit** `Mark the Highlights in the EPUB and add a Highlights and Notes chapter`.
- [ ] **Step 6: The Kindle check (the user).** Send one EPUB with Notes to the user's Kindle through the app, with a Highlight that has a Note and a question. Ask the user what the Kindle shows: the colour, the underline, both, or neither, and whether the number and the chapter links work. Record the answer in the spec under a `#### Kindle check` heading in section 3. Then apply decision 1: keep the styles, drop the background, or drop the marks and keep the chapter. **Commit** `Set the EPUB mark style from the Kindle check` when a change is needed.

### Task 2: The Notes page

**Files:**
- Modify: `app/server.py` (`GET /api/state` `:606-615`), `app/static/shell.js` (`counts` `:14`, `LIBRARY` `:194`), `app/macos/Sidebar.swift` (`library` `:63-64`, the `counts` dictionary that `ChromeState` decodes), `app/static/app.js` (`FILTERS` `:21`, the state patch `:187-199`, the `go` handler `:225`, the page switch that hides and shows `.page` sections), `app/static/notes.js` (the page), `app/static/index.html` (the section), `app/static/app.css`
- Test: `tests/test_notes.py`

**Interfaces:**
- `GET /api/state` adds `notes: <int>`, the count of `highlights` rows whose `paper` is in `papers`.
- Sidebar row `['notes', 'Notes', 'note']` in `LIBRARY` (web) and `("notes", "Notes", "note.text")` in Swift, after Read, with the count `counts.notes`.
- Page `notes` in the navigation: `go({page: 'notes'})`, `nav.current.page === 'notes'`. The Chrome state sends `mode: 'notes'` and `sidebar.selected: 'notes'`.
- `drawNotesPage()` in `app/static/notes.js`: fetches `/files/library/notes.json` with the token, keeps records whose `paper` is in `state.papers` (the route also lists records of Papers that left the library), groups them by Paper in `state.papers` order, sorts each group as the spec says, and draws the search field, the four colour toggles, the `#tag` toggles (decision 2), the groups, and the two download buttons. It runs when the page opens and after `/api/papers/<id>/highlights/*` or `/groups` returns 200 while the page is open.
- A row click: `requestOpen(paper.id)` then, when the Paper's margin mounts, `select` the card of the record id (export a `selectRecord(id)` from `app/static/margin.js` that selects the card and scrolls to its words once the records are loaded).

- [ ] **Step 1: Write the failing test** `test_state_counts_the_notes` in `NotesTest`: with no records, `/api/state` has `notes: 0`. Add two records through the add route and one Paper note. `notes` is 3. Delete one. `notes` is 2. Import a backup with one record whose `paper` is `0000.00000v1` (not in the library). `notes` stays 2.
- [ ] **Step 2: Run.** Expected: FAIL with a `KeyError` on `notes`.
- [ ] **Step 3: Implement** the count, the sidebar row in both shells, the page, and the draw. Reuse the row shape of All Notes (`drawAllNotes`) for the rows, with the Paper heading added. Empty state: "No Notes yet. Select words in a Paper and choose a colour."
- [ ] **Step 4: Run** the test and ruff. Expected: PASS.
- [ ] **Step 5: Check in the browser:** the Notes row shows the count. The page lists two Papers' records in the right order. A search for a word that is only in one Note leaves one row. A colour toggle hides the rows of that colour. A `#tag` toggle (decision 2) leaves the Notes that carry it. A row click opens the Paper with that card selected at its words. Remove a Paper that has records: the page shows no row of it and no empty group (Review Focus 5). **Check with `tools/native_shot.py`:** the sidebar shows Notes with its count, a click opens the page, and the Paper menu items are disabled on it. **Commit** `Add a Notes page for every Highlight and Note of the library`.

### Task 3: Copy the Highlights to a new version

**Files:**
- Modify: `app/server.py` (the Paper detail `:618-625`, a route beside `highlights/restore` `:911`), `papers/library.py` (a `count_highlights(paper_id)` beside `list_highlights` `:212`, and `copy_highlights(source, target)` beside `import_notes` `:243`), `app/static/margin.js` (`mountMargin` `:62`, the offer card), `app/static/app.js` (`readerActions().more`, a `copy-notes` action), `app/macos/Menus.swift` (`firstPaperActions` `:80-85`)
- Test: `tests/test_notes.py`

**Interfaces:**
- `GET /api/papers/<id>` adds `versions: [{id: str, highlights: int}]`, the other Papers in the library whose arXiv id without `v\d+$` equals this Paper's, newest version first. Empty when there is none.
- `POST /api/papers/<new>/highlights/copy` with `{from: <old id>}`. 404 when either Paper is missing. 400 "These Papers are different Papers." when the arXiv ids differ. 409 "This version already has Highlights." when the target has records. On success `{copied: int, found: int, moved: int, not_found: int}` after `app.highlights(new)` ran.
- `Library.copy_highlights(source: str, target: str) -> int`: in one `BEGIN IMMEDIATE` transaction, inserts each record of `source` with `id = uuid4().hex`, `paper = target`, and every other field as it is, and replaces the target's `note_groups` row with the source's. Returns the count.
- Offer card in the margin, class `lx-offer`, text "LocalXiv has {n} Highlights and Notes on version {v} of this Paper. Copy them to this version?" with buttons **Copy** and **Not Now**. Shown when `detail.highlights.length === 0` and `detail.versions` has an entry with `highlights > 0`, picking the largest count. Not Now sets a module flag for the page session. After Copy: `notice('Copied 12. 10 found, 1 moved, 1 not found.')`, the records reload, and the card goes.
- Action `copy-notes`, label `Copy Notes from v{v}`, after `all-notes`, enabled under the same rule. In Swift, `.init(id: "copy-notes", label: "Copy Notes from an Older Version")` holds the place until a Paper opens.

- [ ] **Step 1: Write the failing test** `test_copy_highlights_to_a_new_version` in `NotesTest`. Make a second Paper in the test library that is version 8 of the sample: copy the sample's row with `id` and `arxiv_id` set to `1706.03762v8` and the same passages, but with the text of `p00015` changed by one word and the passage of the formula quote removed, through `Library.retain_paper` or a direct row insert (the implementer picks the way that `test_reimport_finds_moves_and_keeps_highlights` uses). On v7 make three records (found, moved, not found cases), a group, and a question with a stub answer. Then: the v8 detail has `versions: [{id: '1706.03762v7', highlights: 3}]`. Copy from a Paper with another arXiv id: 400. Copy: 200 with `{copied: 3, found: 1, moved: 1, not_found: 1}`, the v8 records have new ids, the same `turns`, the same `group`, and `found` values that match, and the v8 groups equal v7's. Copy again: 409. v7 still has its three records.
- [ ] **Step 2: Run.** Expected: FAIL with 404 on the copy route.
- [ ] **Step 3: Implement** the library methods, the two route changes, the offer card, and the menu item in both shells.
- [ ] **Step 4: Run** the test and ruff. Expected: PASS.
- [ ] **Step 5: Check in the browser:** open v8 with no records: the card shows and names v7 and the count. Not Now hides it, and the More menu still offers Copy Notes from v7. Copy: the notice shows the counts, the margin shows the found and moved cards at their words, and All Notes lists the Not found record with its quote. **Check with `tools/native_shot.py`:** the Paper menu shows Copy Notes from v7, enabled on v8 and disabled on v7. **Commit** `Offer to copy the Highlights and Notes of another version of the Paper`.

### Task 4: Links back into LocalXiv (with a yes on decision 3)

**Files:**
- Merge first: `claude/fervent-hawking-cc2925` into `notes-release-3` (`git merge --no-ff`), after a `tools/native_shot.py` run that opens `localxiv://import?url=https://arxiv.org/abs/1706.03762` and dumps the search page. The harness has no URL step, so add `{"url": "..."}` to `app/macos/Automation.swift` (it calls `application(_:open:)` with that URL) and to the help text of `tools/native_shot.py`.
- Modify: `app/macos/PapersToKindle.swift` (`application(_:open:)`), `app/macos/Automation.swift` and `tools/native_shot.py` (the `url` step), `app/static/app.js` (the `open` command handler), `papers/notes_export.py` (`notes_markdown`)
- Test: `tests/test_notes.py` (`test_notes_markdown_per_paper_and_library`, one assertion added)

**Interfaces:**
- `localxiv://open?paper=<id>&passage=<passage id>`. Swift sends `{name: 'open', id, passage}`. The web `open` handler takes an optional `passage` and calls `goPassage(passage)` once the Paper's frame has loaded. An unknown Paper id shows the usual "not in the library" notice.
- `notes_markdown` writes `<localxiv://open?paper=<id>&passage=<passage>>` on its own line after the quote of each record that has a passage, before the colour line. A Paper note and a record with no passage get no line. The arXiv link at the top stays.

- [ ] **Step 1: Add to** `test_notes_markdown_per_paper_and_library`: the per-Paper export has the line `<localxiv://open?paper=1706.03762v7&passage=p00015>` after the quote of the first record, and the Paper note has no `localxiv://` line. **Run.** Expected: FAIL.
- [ ] **Step 2: Implement** the three changes. **Run** the test and ruff. Expected: PASS.
- [ ] **Step 3: Check with `tools/native_shot.py`:** a `url` step with `localxiv://open?paper=1706.03762v7&passage=p00024` opens the Paper, and a `js` step reads the frame's scroll position at the passage. In the browser the exported Markdown has the lines. **Commit** `Link each exported quote back to its passage with a localxiv:// URL`.

### Task 5: The following card keeps its place (with a yes on decision 5)

**Files:**
- Modify: `app/static/margin.js` (the layout, where the active card that follows the view is placed outside the others)

**Interfaces:**
- The following card stops at the top of the margin when its words are above the view, and the layout places the other cards under it, pushed down as any card pushes the next. No card is under another card in any state.

- [ ] **Step 1: Reproduce** with the Release 2 steps `.scratch/notes-release-2-ledger/task-13-check/steps-follow.json` on a copy of `.scratch/localxiv-notes-r2` through `tools/native_shot.py`: the `COVER` checks fail as the ledger recorded.
- [ ] **Step 2: Implement** the one change to the layout rule.
- [ ] **Step 3: Run** the same steps. Expected: the following card is at the top of the margin, the Key point card of `p00019` is under it with an 8 px gap, and the ⌘F match for "zebrafinch" is visible (`elementFromPoint` at the match is the Note text). Then the Release 2 V4 states: no card over another card still holds. **Commit** `Keep the following card from covering other cards`.

### Task 6: Release 3 verification

**Files:** `docs/highlights-notes-chat-plan-2026-10-18.md` (a `#### Release 3 verification` heading under the Release 3 table, as Release 2 did)

- [ ] **Step 1:** `uvx ruff check .` and the full suite in the background with the corpus inputs and runs cloned into the worktree (`cp -Rc` from the main checkout's `.verification/parser-corpus/inputs` and `runs`), as the Release 2 Task 13 report describes. Expected: no ruff problem, every test OK, the gate 0 of 25 new problems.
- [ ] **Step 2:** The browser checks of Tasks 1 to 4 again on the final branch, in the Native shell with `tools/native_shot.py` where a task names it, in Light, Sepia, and Dark for the Notes page and the offer card.
- [ ] **Step 3: Ask the user** for a VoiceOver pass on the Notes page and the offer card, and a Reduce Motion look at the offer card. Record both answers.
- [ ] **Step 4:** Write the verification section with the same table shape as Release 2's: check, result, with the numbers. **Commit** `Record the Release 3 verification results in the plan`. Then the final whole-branch review, the fix wave, the merge with `--no-ff` in the main checkout, the branch delete, and the test copy.

### Task 7: Prepare the major version (decisions 4, 5, and 6)

**Files:** `package.json`, `package-lock.json`, `.github/workflows/macos-build.yml` (`default:` `:11`), `README.md` (`:11`), `docs/macos-release.md` (`:3`), `docs/releases/v1.0.0.md`

- [ ] **Step 1:** With decision 5 done (Release 1.1 Part B merged by its own plan, and Task 5 if chosen) and decision 6 done (`release-source-cache-main` merged with `--no-ff` and one manual workflow run on `main` finished green), start the branch `release-v1.0.0` in a worktree.
- [ ] **Step 2:** Write `docs/releases/v1.0.0.md` in the shape of `docs/releases/v0.0.19.md`: an opening paragraph, Changes (Chat and Ask with your own model, Highlights and Notes in the margin, the Notes page, the Kindle export with Notes, the copy between versions, the architecture review fixes, the conversion changes since 0.0.19), Verification and limitations (the suite count, the gate, the Kindle check, what was not checked), Installation. Numbers come from Task 6.
- [ ] **Step 3:** `npm version 1.0.0 --no-git-tag-version`, the workflow default, the README download link, and the notes pointer. Stage the six files by name (never `git add -A`). **Commit** `Prepare v1.0.0`.
- [ ] **Step 4:** Merge with `--no-ff` in the main checkout, with `git branch --show-current` in the same command. Push `main`. Tag `v1.0.0` on the merge commit with an explicit target, push the tag, and watch the CI run (about 13 minutes). A CI failure needs the tag moved while the draft is unpublished.
- [ ] **Step 5 (the user):** `python3 app/macos/release-local.py v1.0.0 .scratch/signed-v1.0.0 --publish` on this Mac. Then update the memory note `project-release-process`.
