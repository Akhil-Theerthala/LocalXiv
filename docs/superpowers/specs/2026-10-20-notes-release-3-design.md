# Release 3: Notes leave the Paper

Date: 2026-10-20. Main at `08ec449`. Branch `notes-release-3-plan`.

Source: [the Highlights, Notes, and Chat plan](../../highlights-notes-chat-plan-2026-10-18.md), sections 5.6, 5.8, 7 (Release 3), 8, and 9. Release 1 (Chat and Ask), Release 1.1 Part A, and Release 2 (Highlights and Notes) are on `main`. This document designs the third release of that plan, and the first major version that ships it.

Status: design for your review. Section 10 lists the decisions that are yours. The implementation plan is [the Release 3 plan](../plans/2026-10-20-notes-release-3.md). Nothing is built until you approve both.

## 1. What a reader gets

1. **The Notes go to the Kindle.** Export EPUB and Send to Kindle get an option to include the Highlights and Notes. In the book, each Highlight's words are marked in its colour, with a small number that links to a "Highlights and Notes" chapter at the end. The chapter lists each Highlight with its section, its quote, its colour name, its Note, and its questions with their answers. Each quote links back to its passage.
2. **One page for every Note in the Library.** A Notes row in the sidebar opens a page with every Highlight, Note, and Question card of every Paper, grouped by Paper. A search field finds a word in a quote, a Note, a question, an answer, or a Paper title. Four colour filters narrow the list. A click on a row opens the Paper at the words.
3. **A new version keeps the old Notes.** When a reader opens a new version of a Paper that has Highlights on an older version in the library, the margin offers to copy them. The copy searches for each Highlight's words in the new version, as a reimport does. A Highlight whose words are gone stays as Not found, with its quote and Note.
4. **Links back into LocalXiv** (your decision 3). Each quote in the Markdown export gets a `localxiv://` link that opens the Paper at the passage.

## 2. Where Release 2 left the work

On `main` today:

- The Markdown export, per Paper (`GET /files/<paper>/notes.md`) and for the library (`GET /files/library/notes.md`), in `papers/notes_export.py`. The order is the order of All Notes: Note groups first when the Paper has them, else reading order, with a Paper note first.
- The JSON backup and restore (`GET /files/library/notes.json`, `POST /api/notes/import`), with a library snapshot before each restore.
- Export Notes in the Remove dialog (plan decision 10).
- All Notes per Paper, with search, four arrangements, and Note groups (`app/static/notes.js`).
- The search for a record's words after a reimport, on the first read (`Application.highlights`, `papers/anchors.py`). A record whose `document_digest` differs from the Paper's is searched and saved as found, moved, or not-found.
- Chat reads the Highlights and Notes after the cached Paper.

Not built from plan section 5.6: the EPUB, and the `localxiv://` link in the Markdown export. Not built from plan section 7: E1, E2, and E3.

## 3. E1: Highlights and Notes in the EPUB

### Where it starts

- **Export EPUB with Notes** goes where Export EPUB is: in the browser shell in the Share submenu of More (the `share` list in `app/static/app.js`), and in the Native shell in File › Export (the static list in `app/macos/Menus.swift`). It is enabled when the Paper view shows, the Paper is not a PDF, and the Paper has at least one record. It exports the Kindle profile, as Export EPUB does.
- The Send to Kindle dialog gets a checkbox **Include Highlights and Notes**. It shows when the kind is Original paper or Paper and Blog, the Paper is not a PDF, and the Paper has at least one record. The Overview and the Blog have no Highlights.
- Both send `notes: true` in the body of `POST /api/papers/<id>/export` or `/send`. The server reads it as a boolean and ignores it for a PDF Paper, an Overview, or a Blog.

### What the server builds

`papers/exports.py` `artifact(library, paper, kind, profile, notes=None)`, where `notes` is `None` or the tuple `(records, groups)`. `artifact` has the Library only, not the app, so `Application.execute` reads the records through `Application.highlights` (so the words are searched first) and the Note groups, and passes them. With records and a kind that includes the Paper, `artifact` calls the new module `papers/notes_epub.py`:

`notes_epub(source: Path, paper: dict, records: list[dict], groups: list[dict], output: Path) -> Path`

The function reads the packaged EPUB (`paper.epub` for the Kindle profile, `semantic.epub` for the semantic profile) and writes `paper-notes.epub` or `semantic-notes.epub` beside it. It does not touch the source. For the kind Paper and Blog, `build_anthology` takes the notes EPUB as the Paper member. The steps:

1. **Marks.** For each record with `found` of found or moved, a passage, and a quote: open the chapter file named by the passage's `href` (`reader/<file>#<anchor>`), find the element with that id, and build its one text. The one text is the text that `papers/document.py` `_text()` builds: whitespace collapsed to one space, and each formula as `$tex$`. In the Kindle book a formula is an `<img class="math-image">`. Its `alt` is the TeX when the formula has one, else the formula's text. The one text has `$tex$` in the first case and the text alone in the second, so the map follows the stored passage text (`paper['passages']`): at an image, it takes `$alt$` when the stored text has `$` at that place, else `alt`. When the map's text and the stored text differ at the end, the record gets no mark. The map from each character to its text node is the map that `app/static/onetext.js` `textMap` builds in the browser, now in Python. The quote (or `match` for a moved record) is placed with `_offset` from `papers/notes_export.py`, which picks the occurrence whose prefix and suffix agree most, as the browser does. Each text node segment inside the range becomes `<mark class="lx-<colour>">`. A formula image inside the range gets no mark. After the last segment, `<a class="lx-ref" href="notes.xhtml#n<k>">[k]</a>` links to the chapter entry. A record across passages (`end`) marks the whole span, from the head in the first passage to the end quote in the last, as the browser paints it (`across` in `app/static/margin.js`).
2. **The chapter.** `notes.xhtml`, title "Highlights and Notes", in the order of the Markdown export (share `_arranged` from `papers/notes_export.py`, do not copy it). Each entry has the id `n<k>`: the section as a heading, the quote as a `<blockquote>` whose text links to `<file>#<anchor>`, the colour name, "Not found in this version" when it applies, the Note, and each question in bold with its answer with citations removed (`uncited`). A Paper note has no quote and no link. A record with no passage has no link.
3. **The package.** Add `notes.xhtml` to the manifest and to the end of the spine in `EPUB/content.opf`, and a `<li>` to `nav.xhtml`. Add the mark styles to `reading.css`: a light background in each colour, an underline, and the number in small text. Then `validate_epub(output)` and `epubcheck(output, log)`, as `_package` does. A failure raises `ValueError` with the EPUBCheck line, and the export shows it.

Sizes: the text map and the marks are the largest part, about 120 lines. The chapter and the package are about 80 lines.

### What a Kindle shows

Unknown until a person looks. The risk table of the plan names this as the cheapest test, and only you can run it. Task 1 of the plan builds the chapter and the marks, and its last step is: you send one EPUB with Notes to your Kindle and report what shows. The chapter and its links are standard EPUB, so they work. The marks are the question: an e-ink Kindle may drop the background colour, keep the underline, or drop both. The style is set after your report (decision 1). The Mac app and every other EPUB reader show both.

#### Kindle check

Not run from the app on 2026-10-21. You answered decision 1 ("marks") before the check, so the styles stay as section 3 sets them: a light background in the colour, an underline, and the number. The send to your Kindle is your step, and the Books check was skipped because a native window would take the front while you work.

### Limits

- A formula inside a Highlight is not marked. The text around it is.
- PDF-only Papers have no Highlights, so the option does not show for them.
- The Overview EPUB and the Blog EPUB do not change.
- In a Paper and Blog export, the combined book's contents list shows only the two Papers, because `build_anthology` drops each member's own contents list. The chapter stays in the reading order, and the number links and the quote links work.
- A Highlight made on an older version of the Paper is searched before the export, as it is before every read. A Not found record appears in the chapter without a mark.

## 4. E2: the Notes page

### Where it is

A **Notes** row under Library in the sidebar, after Read, in both shells (`LIBRARY` in `app/static/shell.js` and the `library` list in `app/macos/Sidebar.swift`). Its count is the number of records in the library. `GET /api/state` adds `notes: <count>` from one `SELECT COUNT(*) FROM highlights`, and the sidebar counts get a `notes` key. The command is `{name: 'go', to: 'notes'}`, and the page is `notes` in the navigation, beside `home`, `library`, `search`, and `reader`.

### What it shows

A section `#notes-page` in `index.html`, drawn by `app/static/notes.js` (the module that owns All Notes), with:

- A search field. It filters rows by a word in the quote, the Note, a question, an answer, or the Paper's title. The match is case-insensitive and needs no whole word.
- Four colour toggles, named Key point, Question, Use in my work, and Disagree. All on at the start.
- Rows grouped by Paper. Each group has the Paper's title as a heading and an **Open** button that opens the Paper. Inside a group the rows are in reading order: a Paper note first, then by passage id, then by `created_at`. The groups are in the library's order (newest Paper first, as the Library page starts).
- Each row: the colour stripe, the quote (or "Question about the Paper" or "Paper note"), the Note, and the first line of each question. A Not found record says "Not found in this version". A click on a row opens the Paper and selects the record's card at its words. The margin selects it as a click on a marker does.
- **Export All Notes** and **Back Up Notes**, the two existing library downloads.

The page reads `GET /files/library/notes.json`, the existing backup route, once when it opens and again after a Paper's records change. The route runs the search-on-read for every Paper, so the first open after a reimport can take a moment. The page says "Loading…" until then. The route also lists records of Papers that are not in the library (a restore can bring them). The page leaves those out, and the sidebar count counts only the records of Papers in the library (`WHERE paper IN (SELECT id FROM papers)`), so the count and the page agree.

Editing stays in the Paper: the margin cards and All Notes own the Note editor, the colour, and Delete. The page has no editor, so there is one editor in the app. A row's keyboard use is the library list's: arrows move the selection, Return opens.

### Tags on Notes (your decision 2)

No Tag model exists in the code. `CONTEXT.md` names a Tag for Papers, and no table, route, or page has one. The smallest version that gives Tags on Notes is this: a word that starts with `#` in a Note's text is a tag. The page collects every tag from every Note and shows them as toggles beside the colours. A toggle filters the rows to the Notes that carry the tag. No table, no editor, no route. The Markdown export already carries the words. The alternatives are no Tags in this release, or a Tag field with its own table and editor (a later release).

## 5. E3: copy the Highlights to a new version

### The rule

A version of a Paper is a Paper of its own in the library: the id is the arXiv id with its version, such as `1706.03762v7`. Two versions share the arXiv id without the version (strip `v\d+$`, as `papers/notes_export.py` and `papers/acquire.py` do). A copy is allowed from an older or a newer version. The target must have no records, so a copy never mixes two sets.

### The route

`POST /api/papers/<new>/highlights/copy` with the body `{from: <old id>}`. The server checks that both Papers exist, that they share the arXiv id, and that the target has no records (else 409 with "This version already has Highlights."). In one transaction under `app.lock`, it writes each record of the old Paper with a new 32-hex id, `paper` set to the new id, and every other field as it is, including `document_digest`, `turns`, `group`, and `order`. It copies the Note groups row. Then `Application.highlights(new)` runs, so each record is searched in the new version and saved as found, moved, or not-found. The answer is `{copied, found, moved, not_found}`.

The old digest stays on the copied record on purpose: the search-on-read sees that it differs from the new Paper's digest and runs the search. A Question card keeps its answers. A citation to a passage whose text changed shows the Release 1.1 "from an earlier version" mark, as after a reimport.

### Where it shows

`GET /api/papers/<id>` adds `versions: [{id, highlights: <count>}]` for the other versions of the same Paper in the library, with one count query each.

When a Paper opens with no records and a version with records exists, the margin shows an offer card at its top: "LocalXiv has 12 Highlights and Notes on version 7 of this Paper. Copy them to this version?" with **Copy** and **Not Now**. The copy runs the route, reloads the records, and says "Copied 12. 10 found, 1 moved, 1 not found." in a notice. Not Now hides the card for this page session. With several versions, the card names the one with the most records.

The Paper menu gets **Copy Notes from v7** (the version in the label), after **All Notes**, enabled under the same rule, so a reader who said Not Now can copy later. In the browser shell the item is in the More menu.

## 6. E4: links back into LocalXiv (your decision 3)

The plan's 5.6 gives each quote in the Markdown export a `localxiv://` link "once the URL scheme exists". The scheme exists on the branch `claude/fervent-hawking-cc2925` (one commit, 2026-10-17, not reviewed, 95 commits behind `main`): `localxiv://import?url=<link>` adds a Paper from a bookmarklet. It registers the scheme in both `Info.plist` files and handles it in `application(_:open:)`.

If you decide to merge it, E4 adds a second host: `localxiv://open?paper=<id>&passage=<passage id>`. Swift sends `{name: 'open', id, passage}`, the web app's `open` command takes the optional passage and calls `goPassage` after the Paper loads, and `notes_markdown` writes the link under each quote that has a passage. The browser shell has no scheme, so the Markdown keeps the arXiv link too. Size: S, after a native check of the branch's import link with `tools/native_shot.py`.

If you decide not to merge it, E4 is out, and the Markdown export stays as it is.

## 7. Rules for every part

- Both shells (plan decision 9): every control is in the Native shell and in the browser shell.
- The Chrome state carries no Note text and no quote (plan section 7). The Notes page sends its mode and the sidebar selection. The offer card sends nothing.
- No control fixed to the bottom of the window (the UI spec). The offer card is in the margin.
- Copy in ASD-STE100 with `CONTEXT.md` terms. The strings in this document are final.
- Tests are route-level and few, in `tests/test_notes.py`: one for the EPUB, one for the copy route, one for the state count. The page, the offer card, and the menu items are browser and `tools/native_shot.py` checks.
- `ponytail` before code. `uvx ruff check .` before each Python commit. `--no-ff` merges.

## 8. Not in this release

| Item | Reason |
| --- | --- |
| Kindle highlights back into LocalXiv (`My Clippings.txt`) | Set aside in plan 5.8. Its cheapest test needs a Kindle in hand. A later release after E1 shows what a Kindle keeps |
| Suggested Highlights from the Overview's evidence | Set aside in plan 5.8 |
| A Tag table with its own editor | Decision 2 picks the smallest version |
| Highlights on PDF-only Papers, on the Overview, or on the Blog | Out of scope in plan 5.8 |
| Chat across Papers, sync, sharing | Out of scope in plan 5.8 |
| Release 1.1 Part B (several quotes in one question, Clear Chat with undo) | Its own plan, Tasks 8 to 10 of `docs/superpowers/plans/2026-10-19-chat-release-1-1.md`. It is unblocked now and ships before the major version (decision 5) |
| The active card that follows the view and covers a Find match (Release 2 verification, F1), and the 40-character column at 700 pt with the sidebar shown | Follow-up cards of Release 2. Decision 5 says whether they ship in the major version |
| A VoiceOver pass and a Reduce Motion pass | Only your eye and ears check them. The plan's last task asks you for both |
| The Chat live run V2 | Needs your key and your yes |

## 9. The first major version

You said on 2026-10-20 that the next update is a major one. `main` is 105 commits past v0.0.19 and holds the architecture review fixes, Chat (Release 1 and 1.1 Part A), and Highlights and Notes (Release 2). The major version ships those with Release 3 and, by decision 5, Release 1.1 Part B.

The release follows `docs/macos-release.md` and the release notes in the memory: one "Prepare vX.Y.Z" commit on a branch (six files), merged with `--no-ff`, the annotated tag pushed after `main`, the CI draft, and `release-local.py --publish` on this Mac. Two things are new:

- The branch `release-source-cache-main` (one commit, 2026-10-15) lets a manual workflow run on `main` fill the dependency source cache that a tag run restores. Merge it before the tag, then run the workflow by hand on `main` once (decision 6).
- The version number is yours (decision 4). The plan assumed `1.0.0`; you chose `0.1.0` on 2026-10-21, and decision 6 keeps the dependency cache off `main`.

The F1 fix of decision 5 has no definition yet, so here is the smallest one. The active card that follows the view (Release 1 rule) takes its place among the other cards when it reaches the top of the view: it stops at the top of the margin, and the cards there move down under it, as any card pushes the next one. It covers no card, so a Find match is never under it. It is one change to the layout rule in `app/static/margin.js`, checked with the Release 2 `run-follow` steps. The plan's Task 5 builds it with a yes on decision 5.

## 10. Decisions

Decided by the plan on 2026-10-18 and kept here: B Margin, the release order, one history per Paper, both shells, Export Notes before Remove.

My calls in this document, which you can change while you read:

- The Notes page is a sidebar row, and it opens the Paper to edit. It has no editor of its own.
- Export EPUB with Notes is a second menu item, so Export EPUB keeps its one click. Send to Kindle gets a checkbox.
- The copy offer is a margin card plus a Paper menu item. It refuses a target that has records.
- The Notes page reads the existing backup route, so no new route.
- A formula inside a marked Highlight gets no mark in the EPUB.

Yours, answered on 2026-10-21: 1 keep the marks; 2 `#tags` in the Note text; 3 yes, and only `main` remains when the release is done; 4 `0.1.0`, because many refinements are still to come; 5 Release 3 and the F1 fix ship, Release 1.1 Part B does not, and the other branches and the files that are not needed go; 6 no: no dependency cache goes to `main` or GitHub, so `release-source-cache-main` is not merged.

| # | Question | Recommendation |
| --- | --- | --- |
| 1 | After Task 1's Kindle check: keep the marks as the Kindle shows them, or ship the chapter only? | Keep the marks if the underline or the colour shows. The chapter alone still works everywhere |
| 2 | Tags on Notes: `#tags` in the Note text, none, or a Tag table? | `#tags` in the Note text. It costs one filter row and no schema |
| 3 | Merge `claude/fervent-hawking-cc2925` and build E4? | Yes, after a native check of its import link. It closes the loop from the Markdown back to the passage |
| 4 | The version number of the next release? | `1.0.0` |
| 5 | What else ships in it: Release 1.1 Part B, the F1 following-card fix, the 700 pt column? | Part B yes, by its own plan, before the prep commit. F1 yes, it hides a Find match. The 700 pt column no, it is a layout rework |
| 6 | Merge `release-source-cache-main` before the tag? | Yes. Without it, every tag run downloads every dependency source again |

## 11. Risks and the cheapest test

| Risk | If it is wrong | Cheapest test |
| --- | --- | --- |
| A Kindle shows the marks and the chapter links | The reader sees plain text on the Kindle, and the chapter is the only trace | Task 1's last step: you send one EPUB with Notes and look |
| The Python text map agrees with the browser's on every chapter | A mark lands on the wrong words | The EPUB test marks a quote with a formula and a quote across two text nodes, and `tests/one_text_parity.mjs` already pins the one text |
| EPUBCheck accepts `<mark>` and the added chapter | The export fails after the user asks for it | The EPUB test runs EPUBCheck on the output |
| The Notes page is slow on a large library | The first open after a reimport waits on the search of every Paper | The page says Loading… and the search is saved after one run |
| The copy sends records to the wrong Paper | Highlights appear on another Paper | The copy test checks the arXiv id rule and the 409 |

## 12. Done when

1. Export EPUB with Notes and Send to Kindle with the checkbox produce an EPUB that passes EPUBCheck, and the "Highlights and Notes" chapter and its links show on your Kindle.
2. The Notes row shows the count, the page lists every record of the library grouped by Paper, the search finds a word that is only in one Note, and a click on a row opens the Paper at the words in both shells.
3. A Paper opened with no records and an older version with records shows the offer. After Copy, All Notes lists each record as found, moved, or Not found, and the Question cards keep their answers.
4. With decision 3: a `localxiv://open` link in the Markdown export opens the Paper at the passage.
5. `uvx ruff check .` passes, the full suite passes, and the corpus gate reports 0 new problems.
6. The major version is prepared, tagged, built by CI, and published from this Mac, with release notes that name Chat, Highlights and Notes, the Kindle export, and the Notes page.
