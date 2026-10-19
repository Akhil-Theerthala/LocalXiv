# Release 2: Highlights and Notes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A reader marks words in a Paper in one of four named colours, writes Notes beside them, arranges the Notes, and takes them out of the app as Markdown or JSON. No Highlight is lost after a reimport.

**Architecture:** One table, `highlights`, holds every Highlight, Note, Paper note, and Question card of a Paper as one JSON record (Release 1's `chat_threads` rows move into it). The server finds each record's words again after a reimport with a new module, `papers/anchors.py`, on the first read. A new web module, `app/static/onetext.js`, gives the browser the same passage text as `papers/document.py`. The margin of Release 1 gets coloured marks, Note cards, and All Notes with search and arrangements. The library takes SQLite snapshots, and Notes leave as Markdown and JSON from server routes.

**Tech Stack:** Python 3.14 standard library (`sqlite3`, `difflib`, `http.server`), plain ES modules in `app/static/`, the CSS Custom Highlight API, AppKit in `app/macos/`, Node with `@xmldom/xmldom` for one test.

**Spec:** `docs/highlights-notes-chat-plan-2026-10-18.md`, sections 4, 5.4 to 5.7, 6.1, 7 (Release 2), and 9. The Release 1 plan is `docs/superpowers/plans/2026-10-18-chat-release-1.md`. The Release 1 ledger (rulings R1 to R18, the final review, and the native-check step generators) is in `/Users/silver/Developer/LocalXiv/.scratch/chat-release-1-ledger/`. The anchor spike report is `docs/verification/2026-10-19-anchor-spike.md` (Task 4 adds it).

## Global Constraints

- Read `CODING_STANDARDS.md` and follow the `ponytail` rules. Run `uvx ruff check .` before each Python commit.
- Tests are component end-to-end tests through a route or a tool command, in `tests/` (git ignores it, so test files are not committed). Run them with `.venv/bin/python -m unittest discover -s tests`. Release 2 adds seven tests in total, named in the tasks. Change an existing test only where a task names it. Paint, reflow, contrast, and Find are browser or `tools/native_shot.py` checks, not tests.
- Commit messages: the change only, no AI attribution line (user rule).
- The text of a passage is `paper['passages'][i]['text']` from the library row. Never search in `evidence_document` or `evidence_text`: they drop the bibliography and add ID prefixes. Never change Python `_text` in `papers/document.py`: a change alters the `document_digest` of every reimported Paper and deletes its Overview and Blog (`papers/library.py:240-241`). The JavaScript matches the Python.
- Never name a table `messages` or `passage_search` (`papers/library.py:54-55`). `user_version` stays at 1.
- Every write of a record goes through `check_record` (Task 1) and runs under `app.lock` as read, change, write. This includes restore, import, and a new Question card.
- Never serve an export as a `blob:` or `data:` URL. The Native shell cancels both with no message (`app/macos/PapersToKindle.swift:176-177`). Every file comes from a server route.
- Keep note text and chat text out of the Chrome state (`app/static/shell.js:28-35`). Booleans only.
- Every note field is a `textarea` or `input` in the page document, never in the Paper frame: `editing` (`app/static/shell.js:48-54`) sees only the page document. Show a saved Note as text, and show the editor only during an edit, so that ⌘F finds Note words (criterion 15).
- One undo stack: the margin's (`app/static/margin.js:33`). Swift knows one `canUndo`.
- UI rules from 2026-10-14: window minimum 700 pt, selection in the system accent, green only for content accents, a calm toolbar, no controls fixed to the bottom of the window.
- Copy is ASD-STE100 and uses the glossary terms of `CONTEXT.md`.
- The four colours, in this order: `key` "Key point" (yellow), `question` "Question" (purple), `use` "Use in my work" (orange), `disagree` "Disagree" (pink).

## Decisions this plan takes (smallest version that meets the spec)

- **One record type.** A Question card is a Highlight with turns (plan 6.1, B4), so Highlights, Notes, Paper notes, and Question cards share the table `highlights(id, paper, value)`. At start, rows of a Release 1 `chat_threads` table move into `highlights` once, and `chat_threads` is dropped. No released build has `chat_threads` today, but a build from `main` before the Release 2 merge can write it.
- **Note groups** are one row per Paper: `note_groups(paper PRIMARY KEY, value)`, where `value` is the ordered list `[{id, name}]`. A record outside every listed group is in no group.
- **Search on read.** `Application.highlights(paper_id)` searches again each record whose `document_digest` differs from the Paper's, writes the results in a short transaction of its own, and never raises. Every reader of records calls it: the Paper detail, the exports, and Chat. Nothing runs inside `save_paper` (it holds `BEGIN IMMEDIATE` inside the import's rollback path, `papers/library.py:218-243`).
- **The client makes Highlight IDs** (32 lowercase hex characters, `crypto.randomUUID()` without dashes), so a one-click Highlight paints at once. A new Question card keeps its server ID (Release 1 `adopt()`).
- **No "all" delete.** `/highlights/delete` takes a list of IDs. The Clear Chat control stays out (see Not in this plan).
- **Keys:** ⌃⌘H Highlight (with the last colour used, Key point at first) and ⌃⌘N Add Note…. Both are free in the app and in Apple's list. ⌘B, ⌘I, ⌘U, ⌘E, ⌘J, and ⌥⌘I are not used.
- **Library-wide commands** (Export All Notes, Back Up Notes, Restore Notes) are in a "Notes" group in Settings › General, so they work in both shells (decision 9) with no new menus.
- **The context menu on a selection**, as in Apple Books: the Native shell adds Highlight, Add Note…, Ask…, and Explain to WebKit's own menu, so Look Up and Translate stay. The browser shell opens the web menu (`openMenu`, `app/static/shell.js:162`) with the same items and Copy.
- **Export links** use the arXiv URL and the section name. No `localxiv://` scheme exists yet.

## Not in this plan

Each item has a reason. A reviewer can reject an omission here.

- Clear Chat control: the spec moved it to a later release (plan section 7).
- Chat on PDF-only Papers: the same.
- Highlights in Split view: the margin mounts only on the Paper view (`app/static/reader.js:105`), and the spec does not ask for it.
- Release 1 items that the build did not include: several quotes in one question, Copy as Markdown on a card, Retry on a stopped answer, the rate-limit message, the OpenRouter cache breakpoint, the 100,000-token warning, the earlier-version citation mark. None blocks a Release 2 item. They go to a Release 1.1 list.
- The 40-character column at 700 pt with the sidebar shown: a separate follow-up task covers it.
- A LaTeXML anchor gate: no corpus run has the LaTeXML route. The gate reports "no sample" for it.
- `docs/cleanup.md` (main checkout only): the user said "Not now" on 2026-10-19. Its `usage` item touches the same schema block as Task 1.

## Review Focus

1. A quote that occurs two times in a passage, or in two passages ("the model"): the Highlight paints the occurrence the reader selected, after a reload and after a reimport. Pinned in Task 3 (the parity script checks `findOffset`) and Task 4 (`test_reimport_finds_moves_and_keeps_highlights`).
2. A selection across an inline formula, or across two passages: the same words stay painted at every text size, font, margin, spacing, and theme (criterion 3). Pinned in Task 8 browser check 2 and Task 13 step 2.
3. A reader deletes a Highlight while its Question card streams an answer, or deletes a card larger than 64 KiB: the answer stops, and ⌘Z brings back one record with no duplicate turn. Pinned in Task 1 (`test_highlights_round_trip`) and Task 8 browser check 5.
4. ⌘⌫ and ⌘Z in a Note editor edit the text. They do not open Remove from Library or undo a Highlight (criterion 12). Pinned in Task 12 step 2.
5. A JSON backup that was edited by hand, or imported two times: a bad file changes nothing, and a good file gives no duplicates. Pinned in Task 11 (`test_json_backup_round_trip`).

---

### Task 1: One table for Highlights and Notes

**Files:**
- Modify: `papers/library.py` (schema `:44-56`, `remove_paper` `:271-274`, the `*_chat_thread*` methods `:144-169`)
- Modify: `app/server.py` (`ask` `:146-230`, Paper detail `:480-486`, the routes `:688-717`, the body limit `:520-522`)
- Modify: `app/static/app.js:41-49` (`api()`), `app/static/margin.js` (Release 1 calls to `/chat/update`, `/chat/delete`, `/chat/restore`, `detail.chat`, and the Ask body at `:486`), `app/static/index.html:90` (Remove dialog text)
- Modify: `CONTEXT.md` (new entries; change the "Question card" entry), `docs/highlights-notes-chat-plan-2026-10-18.md` (F2 line: "Migration under `user_version < 3`" becomes "Release 1 rows move into the new table at start; `user_version` stays 1")
- Test: `tests/test_notes.py` (new; imports `ServerTest` and `thread` from `test_chat`), `tests/test_chat.py`

**Interfaces:**
- Record (the `value` JSON of a `highlights` row): `{id: str (32 lowercase hex), paper: str, colour: 'key'|'question'|'use'|'disagree', note: str (≤ 10,000 characters), kept: bool, whole: bool, passage: str|None, href: str|None, quote: str (the selected words in the one text, ≤ 20,000 characters; '' for a Paper note), head: str|None, prefix: str, suffix: str (each ≤ 32 characters), section: str|None, end: {passage, href, quote, suffix}|None, document_digest: str|None, found: 'found'|'moved'|'not-found', match: str|None, group: str|None, order: int|float|None (never a bool), created_at: float, turns: [Turn]}`. Turn is the Release 1 shape. `kept` is false only for an open Question card. When `end` is set, the selection crosses passages: `head` is the part of `quote` in the start passage `passage`, `end.quote` is the part in the end passage, and the passages between are covered whole. Display, export, and Chat use `quote`.
- Kinds: a **Highlight** has a `quote`. A **Note** is a Highlight with a `note`. A **Paper note** has no `quote` and no `passage`. A **Question card** has `turns` or waits for its first answer.
- `RECORD_DEFAULTS = {colour: 'question', note: '', head: None, prefix: '', suffix: '', section: None, end: None, found: 'found', match: None, group: None, order: None}` in `papers/library.py`. Every `Library` method and every route returns records with these defaults under their own fields, so a Release 1 record reads as a Question card and a stored record equals a listed one.
- `check_record(record: dict, paper_id: str) -> dict` in `app/server.py`: the types and limits above, the ID form, the colour, and `turns` as a list of objects. It raises `ValueError` with the record ID. Add, update, restore, the new Question card, and the import (Task 11) call it.
- `Library.save_highlight(record) -> dict`, `get_highlight(paper_id, id) -> dict|None`, `list_highlights(paper_id) -> list[dict]` (creation order), `delete_highlights(paper_id, ids: list[str]) -> list[dict]`, `get_groups(paper_id) -> list[dict]`, `save_groups(paper_id, groups) -> list[dict]`. The `*_chat_thread*` methods go. The table key is `id` alone, so the 409 check looks up `id` in every Paper.
- `Application.highlights(paper_id) -> list[dict]`: in this task, `list_highlights`. Task 4 adds the search.
- `api(path, payload)` in `app/static/app.js` sets `keepalive` only when the JSON body is under 60,000 bytes (the Fetch limit for a keepalive body is 64 KiB).
- Routes:
  - `GET /api/papers/<id>` returns `{paper, blog, overview, highlights, groups}` (the key `chat` goes).
  - `POST /api/papers/<id>/highlights/add` `{highlight: record}` → `{highlight}`. The server sets `paper`, `created_at`, `document_digest`, `found: 'found'`, and `turns: []`. 400 on a bad field; 409 when the ID exists.
  - `POST /api/papers/<id>/highlights/update` `{updates: [{id, colour?, note?, kept?, group?, order?, anchor?}]}` → `{highlights: [records]}`. `anchor` is `{passage, href, quote, head, prefix, suffix, section, end}`; it sets `found: 'found'`, `match: None`, and the Paper's `document_digest` (Place Again).
  - `POST /api/papers/<id>/highlights/delete` `{ids: [str]}` → `{removed: [records]}`. It stops a running answer of each ID first (`drop_chats`).
  - `POST /api/papers/<id>/highlights/restore` `{highlights: [records]}` → `{highlights: [records]}`. Each record must pass `check_record` and belong to `<id>`. Body limit 16 MiB, as the old `chat/restore`.
  - `POST /api/papers/<id>/groups` `{groups: [{id, name (1 to 80 characters)}]}` → `{groups}`.
  - `POST /api/papers/<id>/chat` reads and writes `highlights`. A new card takes `anchor` (the `update` shape) with the question; it gets `colour: 'question'`, `kept: False`, and the anchor fields. The 2,000-character Ask limit applies to `anchor.quote`.

- [ ] **Step 1: Write the failing test** `test_highlights_round_trip` in `tests/test_notes.py`. Through the routes, on the sample Paper: add a Highlight with a client ID, colour `key`, a quote, prefix, and suffix; the detail lists it with `found == 'found'` and the Paper's digest; update its colour, note, group, and order; save two groups and read them back in order; delete it, and `removed` holds the record; restore it, and the detail lists it again; a Question card that waits on a silent `ChatStub` answer is deleted, its stream ends, and a restore gives one record with no extra turn; a restore of a record with a 70,000-byte answer succeeds; Remove from Library leaves no `highlights` and no `note_groups` row. A loop sends seven bad bodies (a 31-character ID, an unknown colour, a quote of 20,001 characters, a group name of 81 characters, a record of another Paper to restore, `turns: null` to restore, an existing ID to add) and expects 400 or 409 each. A library made with a `chat_threads` row (written with `sqlite3` before the server starts) lists that row as an open Question card.
- [ ] **Step 2: Run** `.venv/bin/python -m unittest discover -s tests -p test_notes.py`. Expected: FAIL (404 on `/highlights/add`).
- [ ] **Step 3: Implement** the table, the start move of `chat_threads` rows (in `__init__`, after the `executescript`: when `sqlite_master` has `chat_threads`, `INSERT OR IGNORE INTO highlights SELECT id, paper, value FROM chat_threads`, then `DROP TABLE chat_threads`, in one transaction), `note_groups`, the methods, `check_record`, the routes, the detail keys, and `api()`. Add one `DELETE … WHERE paper=?` per table to the `remove_paper` transaction. Change the Release 1 client to the new routes, the `highlights` key, and the `anchor` body (with Release 1's anchor fields until Task 8). Change `index.html:90` to name "Highlights, Notes, and Chat questions".
- [ ] **Step 4: Change `tests/test_chat.py`:** delete `ChatStorageTest` (`:68-101`) and `test_delete_and_restore_threads` (`:821-840`), which `test_highlights_round_trip` covers; build expected records with `dict(RECORD_DEFAULTS, **thread(...))`; give `thread()` a `digest` argument and pass the Paper's `document_digest`; replace `'all'` and `None` (`:833`, `:849`, `:918`, `:961`) with the list of IDs; keep the reimport assertion (`:974-984`) until Task 4.
- [ ] **Step 5: Add glossary entries** to `CONTEXT.md`: **Highlight** (words of a Paper that the reader marked in one of four named colours), **Note** (the reader's text on a Highlight; not the sidebar's information line, `Row.Kind.note`, and not the Overview node kind `note`), **Paper note** (a Note on the whole Paper, with no words), **Note group** (a named, ordered group of Notes that the reader makes in All Notes), **Not found** (a Highlight whose words the app cannot find in this version of the Paper; it keeps its quote and Note). Change **Question card**: "a Highlight with a question and its answers"; All Notes lists every Highlight, Note, and Question card.
- [ ] **Step 6: Run all tests and check the margin in the browser** (dev server `notes-release-2`, port 8792): Ask, Keep as Note, Discard, and ⌘Z work as in Release 1. **Commit** `Keep Highlights, Notes, and Question cards in one table`.

### Task 2: Library snapshots

**Files:**
- Modify: `papers/library.py` (`__init__` `:40-69`), `app/server.py` (`/api/state` `:471-477`)
- Test: `tests/test_notes.py`

**Interfaces:**
- `Library.backup(name: str) -> pathlib.Path`: copies the database with `sqlite3.Connection.backup` into `<root>/backups/<name>.<uuid4 hex>.tmp`, then renames it to `<name>.sqlite3`. Returns the path.
- `Library.daily_backup() -> None`: writes `daily-YYYY-MM-DD` (local date) when that file does not exist, then keeps the 7 newest `daily-*` files. It catches `OSError` and `sqlite3.Error` and returns, so a full disk never stops the app. Pre-migration snapshots are never deleted.

- [ ] **Step 1: Write the failing test** `test_library_keeps_snapshots`: make a database at `user_version` 0 with one `papers` row; open `Library` on it; `backups/` holds one `before-v1-*.sqlite3` file whose `user_version` is 0 and whose `papers` row is the same. `backups/` also holds today's `daily-*` file. With 8 older `daily-*` files written first, `backups/` then holds 7 `daily-*` files: today's and the 6 newest of the 8. A new, empty library gets a daily snapshot and no pre-migration snapshot. With `sqlite3.Connection.backup` patched to raise `sqlite3.OperationalError`, `Library` still opens.
- [ ] **Step 2: Run.** Expected: FAIL (no `backups/`).
- [ ] **Step 3: Implement.** In `__init__`, read `existed = path.exists()` before the first connect. When it existed and `PRAGMA user_version` is below 1, take `before-v1-<date>` before the `executescript`; this snapshot raises on an error, so a failed snapshot stops the migration. Call `daily_backup()` at the end of `__init__` and in the `/api/state` handler under `app.lock` (a missing file is the only check, so the call is cheap; the service runs for days).
- [ ] **Step 4: Run the tests.** Expected: PASS. **Commit** `Take a library snapshot before a migration and once a day`.

### Task 3: The one text in the browser

**Files:**
- Create: `app/static/onetext.js` (no imports, so Node can load it)
- Modify: `app/static/selection.js` (`tex` `:10-13`, `textMap` `:18-39`, `findWords` `:57-65` move to `onetext.js`), `app/static/margin.js:8` (import from `onetext.js`)
- Create: `tests/one_text_parity.mjs`, `tests/test_one_text.py`

**Interfaces:**
- `tex(element) -> string` (`''` when absent), as `papers/document.py:250-251`.
- `textMap(root: Element) -> {text, map}` as today, with four fixes: (a) a root `math` element gives `$tex$` with no padding, and each character maps to that element; (b) whitespace is Python's `str.isspace` set, written with escapes: `[\t\n\v\f\r\x1c-\x1f \x85\xa0  -     　]`; (c) formula text maps per UTF-16 unit; (d) see `findOffset`.
- `findOffset(text, quote, prefix = '', suffix = '') -> number` (-1 when the quote is absent): the occurrence whose surrounding text agrees with the most characters of `prefix` (read backwards) and `suffix`, then the first.
- `findWords(root, quote, prefix = '', suffix = '') -> {range, formulas}|null`: `textMap`, then `findOffset`, then the Range.

- [ ] **Step 1: Write the parity script** `tests/one_text_parity.mjs <run folder>`: for each Paper of the run, for each passage of `document.json`, parse the file that the `href` path names (`reader/main.xhtml` or `reader/text/chNNN.xhtml`; one parse per file) with `@xmldom/xmldom` and a `Node` constant shim, find the element by the `href` fragment, and compare `textMap(element).text` with the passage `text`. Exit 1 when a passage has no file or no element, or when the texts differ; print the first 10 differences and the number of passages checked per Paper. Also, for 200 passages that hold a repeated group of three or more words, check that `findOffset` with the prefix and suffix of the second occurrence returns its offset. Exit 1 when no passage was compared.
- [ ] **Step 2: Write** `test_one_text_matches_python` in `tests/test_one_text.py`: run the script with `node` on the run folder with the newest modification time under `/Users/silver/Developer/LocalXiv/.verification/parser-corpus/runs/` (skip the test when no run exists) and assert exit 0.
- [ ] **Step 3: Run.** Expected: FAIL (0706.3366v3 `p00053` gives `(L−1)(L-1)` against `$(L-1)$`).
- [ ] **Step 4: Implement** `onetext.js`. Change `selection.js` and `margin.js` to import from it.
- [ ] **Step 5: Run the test and check** an Ask across an inline formula in the browser (the card finds its words). Expected: PASS. **Commit** `Give the browser the same passage text as the server`.

### Task 4: Find the words again after a reimport

**Files:**
- Create: `papers/anchors.py`, `docs/verification/2026-10-19-anchor-spike.md` (the spike report)
- Modify: `app/server.py` (`Application.highlights`), `tools/robustness/corpus.py` (`compare` `:870-892`), `docs/highlights-notes-chat-plan-2026-10-18.md` (section 5.4: the measured rates and the threshold)
- Reference: the spike run of 2026-10-19 in `/Users/silver/Developer/LocalXiv/.scratch/anchor-spike-2026-10-19/` (`report.md`, `anchors_spike.py`, `results.txt`). Git ignores `.scratch/`, so Step 0 copies the report into the repository. The script stays there: `papers/anchors.py` is the one copy of the search, and `compare` calls it.
- Test: `tests/test_notes.py`, `tests/test_chat.py:974-984`

**Interfaces:**
- `locate(passages: list[dict], record: dict) -> dict` in `papers/anchors.py`. It never raises. It returns the record's new `{passage, href, section, found, match}` (and `end` with its new `passage` and `href`). Search order, for `quote` (or `head` and `end.quote` when `end` is set): exact in the passage with the same `href`, then exact in the passage with the same ID (at these two steps a hit counts only when its prefix and suffix agree in full, because Pandoc IDs are positions); exact in the same section (heading text nearest the old index); exact anywhere (ties: prefix and suffix agreement, then distance from the old index). An exact match is `found`. The section and the ID are hints only: the spike found 4.0% of exact hits in another section, mostly after a heading number changed. Then a normalized exact step (NFKC, case fold, letters and digits only; it found 720 of 1,382 exact misses in the spike with no false hit, mostly `m_{0}` against `m_0`): `moved`, with the new words in `match`. Then the fuzzy match, section first, then the whole Paper: in each candidate passage, `difflib.SequenceMatcher(autojunk=False)` puts a window at the longest common substring, trims it to the matching blocks, and takes `ratio()`; at a ratio of at least **0.85** the result is `moved`, with the new words in `match`. The candidates are the passages with the old `href` and ID, plus the 10 passages with the most inverse-document-frequency overlap among those that hold one of the quote's 3 rarest words (plain difflib on every passage took 30.5 s for 50 quotes; this pre-filter took at most 884 ms and lost 0.4% of moved matches). Else `not-found`, and the old `passage` and `href` stay. A record with no `passage` (a Paper note, or text outside a passage, which the client anchors by the nearest element `id`) is not searched. Budget: 50 Highlights of one Paper in less than 1 s.
- The spike's measures, for the plan's section 5.4: same route (Pandoc to Pandoc), 97.4% found exactly, 2.4% moved, 0.1% not found at 0.85; a route change, 4.7% (arXiv HTML to Pandoc) and 11.0% (Pandoc to arXiv HTML) not found, mostly display equations; at 0.85, 0 of 1,850 quotes from an unrelated Paper matched, against 3 at 0.8.
- `Application.highlights(paper_id)`: records whose `document_digest` is not the Paper's go through `locate`. Under `app.lock`, each is read again, and only `passage`, `href`, `section`, `end`, `found`, `match`, and `document_digest` are written. An error in `locate` leaves the record as it was.
- `corpus.py compare`: for each same-route pair, sample quotes from the base run as the spike does (one quote of 6 to 15 whole words from the middle of each passage with 40 or more characters, plus one quote around a formula when the passage has one; a ` $tex$ ` formula counts as one word; prefix and suffix of 32 characters), `locate` them in the new run, and add a change `{key: 'anchor:<route>', item: <passage id>, new: 'not-found:<passage id>:<first 8 hex of sha256(quote)>'}` for each not-found quote, so that one allow-list entry allows one quote. A pair whose route changed gets a report line with its not-found rate only. A route with no pair gets a "no sample" line and does not block.

- [ ] **Step 0: Copy the spike report** into `docs/verification/2026-10-19-anchor-spike.md`, and put its threshold and rates into the plan's section 5.4.
- [ ] **Step 1: Write the failing test** `test_reimport_finds_moves_and_keeps_highlights` (the import-job pattern of `tests/test_reimport.py:18-108`): five Highlights and one Question card on the sample Paper. The import adds a passage before them and changes passages. Results: one has the same words at the next ID (`found`, new `href`); one has two words changed (`moved`, `match` holds the new words); one has its words removed (`not-found`; the quote, Note, and colour unchanged); one quote that also occurs, with other context, in the passage that now has its old ID gets its own moved passage; one across two passages is `found` with its new `passage` and `end`; the Question card is `found` at its new passage. A Place Again `update` with a new `anchor` gives `found`. Change `tests/test_chat.py:982-984` to expect the searched record, and check the lookup count at `:895-911`.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement** `locate`, `Application.highlights`, and the `compare` change. Release 2 does not change the converter, so the gate against `main` shows no anchor change. Run `compare` once on the runs `9de5a74f849f` and `dc9176a69f38` (their converters differ) and check that anchor changes appear in its report; do not copy entries from that run into the allow-list.
- [ ] **Step 4: Run all tests.** Expected: PASS. **Commit** `Find Highlights again after a reimport`.

### Task 5: The Reading position on arXiv HTML Papers

**Files:**
- Modify: `app/static/reader.js` (`topPassage` `:295-303`)

- [ ] **Step 1: Add an arXiv HTML Paper to the scratch library:** stop the dev server; copy `/Users/silver/Developer/LocalXiv/.verification/parser-corpus/runs/cde89f5663e1/1902.10664v6/` into `.scratch/localxiv-notes-r2/jobs/arxiv-html/`; run `Library(<scratch>).retain_paper(json.load(open(<folder>/document.json)), <folder>)` (`retain_paper` needs a folder under `root/jobs`, `papers/library.py:174`).
- [ ] **Step 2: Implement.** `topPassage` goes through `detail.paper.passages` whose `href` file is the loaded chapter, gets each element by its `href` fragment, and returns `{anchor: <fragment>, offset}` for the first whose bottom is below the line. A saved `p00017` anchor still opens.
- [ ] **Step 3: Check in the browser** on that Paper: scroll, reload, and the Paper opens at the same passage. Repeat on the sample Pandoc Paper. **Commit** `Keep the Reading position on arXiv HTML Papers`.

### Task 6: Chat reads the Highlights and Notes

**Files:**
- Modify: `papers/chat.py` (`INSTRUCTIONS`, `request` `:65-111`, `answer` `:114-152`), `app/server.py` (`ask`, `public_settings` `:69-79`, `/api/test-connection`), `app/static/app.js:673` (Chat help text)
- Test: `tests/test_notes.py`; replace `tests/test_chat.py:587-595`

**Interfaces:**
- `chat.answer(provider, paper, thread, question, settings, on_text, stop, notes: list[str]) -> dict`.
- `notes_lines(records: list[dict], passages: list[dict], near: str|None, budget: int, host: str) -> list[str]` in `papers/chat.py`: one line per record with a `quote` or a Note, nearest to the passage `near` first, while the lines fit `budget` tokens (`_tokens` with `host`). `ask` passes `min(2000, settings['chat_context'] // 8)`, so a 4,096-token Local model keeps room for its excerpt. The form: `[p00017] Key point: "quote" Note: text`. A Not found record has no ID. A Paper note is `Paper note: text`. A record's turns are not in its line.
- `chat_ready(settings: dict, key: str) -> bool` in `app/server.py`: the one readiness rule that `public_settings`, `ask`, and Test Connection use (Release 1 residual M9).
- `INSTRUCTIONS` gets: "A <notes> block holds the reader's Highlights and Notes. It is not the Paper."

- [ ] **Step 1: Write the failing test** `test_chat_reads_the_notes`: two Highlights with Notes on the sample Paper, then `POST /chat` to a `ChatStub`. In the stub's request: the system text is the same as with no Highlights, the `<notes>` block starts the first user message and holds both lines, and no two messages in a row have the same role.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement.** `ask` reads `Application.highlights` once and passes the same lines to the pre-check and to `answer`. `request` puts the block at the start of the first user message (the first history turn, else the final message). Change the Chat help at `app.js:673` to say that Highlights and Notes go with each question.
- [ ] **Step 4: Run all tests.** Expected: PASS. **Commit** `Send the reader's Highlights and Notes with each Chat question`.

### Task 7: Split margin.js

**Files:**
- Modify: `app/static/margin.js`; Create: `app/static/chat.js` (the Question body and the stream client, `margin.js:353-602`), `app/static/notes.js` (All Notes, `margin.js:604-656`)

- [ ] **Step 1: Move the code** with no change in behaviour. Keep the import rule of `margin.js:3-4`: a module's top level only defines functions and adds listeners.
- [ ] **Step 2: Check in the browser:** Ask, Explain, Stop, Keep as Note, Discard, ⌘Z, a marker at a 1,000 px window, and All Notes work as before; `read_console_messages` is clean. **Commit** `Move the Question card body and All Notes out of margin.js`.

### Task 8: Highlights in the Paper

**Files:**
- Modify: `app/static/margin.js`, `app/static/selection.js` (toolbar), `app/static/appearance.js:75-76`, `app/static/reader.js:340`, `app/static/app.css` (colour tokens near `:26`, `:38`, `:53`; the `var(--question)` rules `:445-476`)

**Interfaces:**
- Two sets in `margin.js`: **marks** (every record with words: painted and hit-tested) and **cards** (the marks with a margin card: a Note, a Question card, or the active record). A Highlight with no Note is a mark only.
- `selectionToolbar(items: [{label, ariaLabel, action}])`: in this task, the four colour swatches, then Ask and Explain (Task 9 adds Note). It stays one toolbar: a second call must not add a second bar or second listeners.
- `anchor(range) -> {passage, href, quote, head, prefix, suffix, section, end}` replaces `fromRange`'s anchor part, with `findOffset`'s text. Text outside a passage gets `passage: null` and the `href` of the nearest element with an `id`. Ask and Explain send `anchor(range)` with the question.
- `lastColour` in `margin.js`: `key` at start, set by each swatch and each popover colour. Task 12's Highlight item uses it.
- Paint: one Custom Highlight name per colour (`lx-key`, `lx-question`, `lx-use`, `lx-disagree`) plus `lx-open` (dashed) for an open Question card, registered on the frame's own `Highlight`; a formula in the words gets the class `lx-h-<colour>`. `styleReader` passes four `{colour, tint}` pairs.
- Undo: Delete pushes `{paper, records: [record], question: ''}` (the Release 1 entry shape plus `paper`). `reset()` no longer clears the stack; `restore()` and `syncUndo()` use only the entries of the selected Paper (criterion 11: "during the session").

- [ ] **Step 1: Build** the colour tokens (Light, Sepia, Dark; each passes the rule at `app.css:23-25`: 3:1 for the stripe and marker on the paper, the card, and the tint, and 9:1 for ink on the tint), the toolbar, the one-click Highlight (`/highlights/add`, with nothing else on screen moving), the paint, a cache of `textMap` per element (a `WeakMap`, cleared on `lx-chapter`; `paint()` runs only when the marks change — Release 1 residual M12), and the card at the mark: a click on painted words (`caretRangeFromPoint` and `isPointInRange`, only with a collapsed selection) opens a small popover with the four colours and Delete (Task 9 adds Note and Ask). The frame `pointerdown` (`margin.js:85`) runs `deselect()` before the click, so the popover opens on `click`; add the popover to the exclusion list of the page `pointerdown` (`margin.js:108`).
- [ ] **Step 2: Check in the browser,** with `read_console_messages` clean:
  1. One click on a swatch paints the words in that colour, and nothing else moves.
  2. A Highlight across an inline formula and one across two passages paint the same words after a reload.
  3. The card at the mark changes the colour, and the paint follows.
  4. Delete removes the paint; ⌘Z brings it back. Delete, open another Paper, come back, and ⌘Z brings the Highlight back.
  5. Delete a Highlight whose Question card streams: the answer stops; ⌘Z restores one card. Repeat with a card whose answers are over 64 KiB (made through `/highlights/restore`).
  6. A Paper with 200 Highlights (made by a script through `/highlights/add`): a click elsewhere and a scroll stay under 16 ms of script time in a performance profile.
- [ ] **Step 3: Commit** `Highlight words in four colours`.

### Task 9: Note cards in the margin

**Files:**
- Modify: `app/static/margin.js`, `app/static/chat.js`, `app/static/notes.js`, `app/static/selection.js`, `app/static/reader.js:322`, `app/static/app.css`

**Interfaces:**
- The toolbar gets Note after the swatches; the popover at the mark gets Note and Ask.
- A Note card: the colour stripe, the quote, the Note as text, Edit (a `textarea` until Save or Escape), Ask, Delete. The client refuses a Note over 10,000 characters before Save and keeps the text in the editor. A Note saves on Save, on a blur, and in the `flush` handler (chain it inside `reader.js:322`; a second `register('flush')` replaces the first).
- Ask on a Note card adds turns to the same record ("an answer joins its Highlight", plan 5.5). Keep as Note on a new selection's Question card gives a Question Highlight (`colour: 'question'`).
- Markers (B2) and the card stripe use the record's colour through one custom property, `--c`.
- `moved` records paint `match`, and the card says "The words changed in this version." `not-found` records have no paint and no margin card; All Notes lists them (Task 10). A record with no `passage` (text outside a passage) that the client cannot find at its `href` is treated as `not-found` in the page.
- Place Again: the command sets a waiting state; the next selection's toolbar shows Place Here and Cancel; Place Here sends `update` with `anchor(range)`.
- An answer that runs when the reader leaves its Paper keeps running (Release 1 residual M11): remove the abort at `margin.js:72`. `send()` keeps `const owner = paperId`; `receive`, `adopt`, and `end` return at once when `owner !== paperId`, and the response stays open, because the server saves the turn only while the connection lives (`app/server.py:684-686`).

- [ ] **Step 1: Build** the Note card, the colours of cards and markers, Ask on a Note card, the Paper note (Add Paper Note in All Notes; it shows only there), Place Again, the owner rule above, and two Release 1 residuals: the blocked draft card shows its waiting question (`card.waiting` in `blocked()` and in the signature at `margin.js:420`), and ⌘Z in the browser acts only while the margin is mounted (`mounted &&` at `margin.js:114`).
- [ ] **Step 2: Make a reimport in the scratch library:** change the same words in the row's passage text and in the chapter XHTML in the Paper folder, and set the row's `document_digest` with `papers.library.document_digest`.
- [ ] **Step 3: Check in the browser:**
  1. Note on the toolbar makes a Highlight with its editor open; Save shows the Note as text.
  2. ⌘F finds a word that is only in a saved Note.
  3. A 1,000 px window: markers in each colour; a marker opens its card.
  4. After the Step 2 reimport, a moved card paints the new words; Place Again on it paints a new selection.
  5. Leave a Paper during an answer, and come back after it ends: the answer shows, and the other Paper's All Notes does not list it.
- [ ] **Step 4: Commit** `Show Notes beside their words in the margin`.

### Task 10: All Notes

**Files:**
- Modify: `app/static/notes.js`, `app/static/app.css`

**Interfaces:**
- All Notes lists every record of the Paper: the Paper notes first, then the rest, with the colour name as visible text, the section, the quote, the Note, and the questions. Not found records show "Not found in this version" and Place Again.
- Each row has Edit Note (a `textarea` in the page, saved with `update`) and Delete (`/highlights/delete`, which pushes an undo entry; ⌘Z restores it while All Notes is open).
- A search field filters on the quote, the Note, and the question and answer text.
- Four arrangements: Position (passage index, then the start of the quote in the passage), Colour (the four colours in order, then position), Date (`created_at`), Groups (the groups in order, then "In no group"; inside a group, by `order`). The margin always shows reading order.
- In Groups: New Group, Rename, Move Up and Move Down for a group and for a record, a group picker on each record, Delete Group (its records go to no group), and Add Written Note (a Paper note in that group). Each change is one `update` or `groups` call. Every control is a button or a field that Tab reaches.

- [ ] **Step 1: Build** the list, the controls, the search, and the arrangements. The chosen arrangement is per Paper, in `localStorage` with `try`/`catch`.
- [ ] **Step 2: Check in the browser:** each arrangement orders 8 test records as specified; search finds a word in an answer; a record moved in Groups keeps its place after a reload; delete a Paper note and a Not found record, and ⌘Z restores each one; Place Again on the Not found record of Task 9 Step 2 paints a new selection; `read_page` shows the colour name in each row.
- [ ] **Step 3: Commit** `Search and arrange All Notes`.

### Task 11: Notes leave the app

**Files:**
- Create: `papers/notes_export.py`
- Modify: `app/server.py` (`respond()` `:419-448` gets a `headers` parameter; `/files` routing `:487-500`; a JSON import route; the body limit `:520-522`), `app/static/app.js` (`downloadLink` `:90-96`; the Remove dialog handlers `:346-368`; the Settings › General Notes group), `app/static/index.html` (Remove dialog `:90`; General pane `:109-113`), `app/macos/PapersToKindle.swift` (`webView(_:runOpenPanelWith:initiatedByFrame:completionHandler:)` on the `uiDelegate`, which both the main and the Settings windows use)
- Test: `tests/test_notes.py`

**Interfaces:**
- `notes_markdown(items: list[tuple[dict, list[dict], list[dict]]]) -> str` (each item: the Paper, its records, its groups). Per Paper: `# <title>`, the arXiv link, then each record in Groups order when the Paper has groups, else in Position order: `## <section>`, `> quote`, `*<colour name>*`, "Not found in this version" when it applies, the Note, and each question with its answer (citations removed with `uncited()`, `papers/passages.py:30-32`).
- `attachment(name: str) -> str` in `app/server.py`: `attachment; filename="<ASCII fallback>"; filename*=UTF-8''<urllib.parse.quote(name, safe='')>`. In `name`, control characters, `"`, `\`, `/`, and `:` become spaces; in the fallback, each non-ASCII character becomes `_`. `send_header` encodes Latin-1 only.
- `GET /files/<paper>/notes.md` and `GET /files/library/notes.md` (handled before the Paper lookup at `:487`; `library` is not an arXiv ID): `text/markdown; charset=utf-8`, attachments `"<title> Notes.md"` and `"LocalXiv Notes.md"`.
- `GET /files/library/notes.json`: `{format: 'localxiv-notes', version: 1, highlights: [every row], groups: {<paper>: [groups]}}`, attachment `"LocalXiv Notes.json"`. It holds every `highlights` and `note_groups` row, also rows of Papers that are not in the library; only Papers in the library go through `Application.highlights`.
- `POST /api/notes/import` (body limit 64 MiB) with that JSON: it checks `format` and `version`, every record with `check_record` (plus `paper` as text), and every group list; one bad item gives 400 with its index, and nothing is written. Then, under `app.lock` and in one transaction, it upserts each record by `id` and replaces the groups of each Paper in the file. Returns `{highlights: <count>, papers: <count>}`.
- Remove dialog: the text names Highlights, Notes, and Chat questions, and an **Export Notes** button downloads the Paper's `notes.md`. Remove stays a separate click.
- Settings › General, group "Notes": **Export All Notes** (Markdown), **Back Up Notes** (JSON), **Restore Notes…** (an `<input type="file" accept=".json">`).

- [ ] **Step 1: Write the failing tests:**
  - `test_notes_markdown_per_paper_and_library`: set the sample Paper's title to one with `—`, `β`, and `"`; with two groups and three records, both routes answer 200 with `?token=`, the content type, the `attachment` header with `filename*`, and the lines in Groups order; a Not found record has its line.
  - `test_json_backup_round_trip`: export the JSON; import a file with one bad record, and get 400 with nothing written; remove the Paper; import the good file two times; a second `notes.json` export holds each record and each group once.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement.** Add `.md` and `.json` labels to `downloadLink`.
- [ ] **Step 4: Check** in the browser (both downloads, Restore, the Remove dialog) and with `tools/native_shot.py` (the Settings window's Restore Notes… opens the open panel; Export Notes in the Remove dialog opens the save panel). **Commit** `Export Notes as Markdown and back them up as JSON`.

### Task 12: Native shell for Notes

**Files:**
- Modify: `app/static/app.js` (`readerActions().more` `:400-402`), `app/static/shell.js` (key map `:100-106`), `app/static/selection.js` (`contextmenu` in `wire(doc)` `:96-106`), `app/static/margin.js` and `notes.js` (labels), `app/macos/Shell.swift:122` (a `WKWebView` subclass), `app/macos/Menus.swift` (`firstPaperActions` `:80-85`, `paperKeys` `:98-99`, `validateMenuItem` `:161-164`), `app/macos/Automation.swift:74` and `tools/native_shot.py:18` (named keys `left` and `right`; a step that dumps the context menu items)

**Interfaces:**
- Actions `highlight` "Highlight" (⌃⌘H, with `lastColour`), `add-note` "Add Note…" (⌃⌘N), `ask` "Ask…", and `explain` "Explain", enabled when `view === 'paper' && paper.format !== 'pdf'`. They read the live frame selection. With no selection, they show a notice: "Select words in the Paper first." `validateMenuItem` disables all four while `state.editing` is true.
- Native context menu: the `WKWebView` subclass adds the four items, after a separator, to WebKit's menu in `willOpenMenu(_:with:)` when the Paper view shows; each sends `{name: 'action', id}`. A real right-click blocks the step runner, so an automation step builds the menu as `willOpenMenu` does and dumps the titles.
- Browser context menu: on a `contextmenu` event with a selection that is not collapsed, `openMenu` with the four items and Copy. Add the frame's `getBoundingClientRect()` to the event position.
- VoiceOver: the margin label "Notes"; a card label "<Colour name> Highlight: <first 80 characters>"; a marker title "Show the Note"; All Notes rows name the colour as text.

- [ ] **Step 1: Build** the actions, keys, both context menus, the labels, and the automation steps.
- [ ] **Step 2: Check with** `tools/native_shot.py` (start from the step generators in `.scratch/chat-release-1-ledger/task-8-native-check/`): the Paper menu shows the four items, with ⌃⌘H and ⌃⌘N, enabled in a Paper and disabled on Home; ⌘⌫ in a Note editor deletes text and does not open Remove; ⌘Z in a Note editor undoes typing and does not restore a Highlight; ⌥⌘N opens All Notes and Escape closes it; ⌘F, Return, Escape, then ⌃⌘H makes a Highlight on the found words; the context menu dump holds Look Up and the four items. In the browser, a `contextmenu` event on a selection shows the five items.
- [ ] **Step 3: Commit** `Add Highlight and Add Note to the Paper menu and the context menu`.

### Task 13: Release 2 verification

- [ ] **Step 1: Run** `uvx ruff check .` and `.venv/bin/python -m unittest discover -s tests` (this runs the corpus gate with the anchor changes). Expected: all pass.
- [ ] **Step 2: Reflow (criterion 3):** a js step on a Paper with 10 Highlights, one across a formula and one across two passages: for each text size 15, 18, and 26, each font, each margin, each spacing, and each theme, the text of each painted range equals its stored words.
- [ ] **Step 3: Contrast (criterion 13):** measure the four colours in Light, Sepia, and Dark against the rule at `app.css:23-25`, and record the ratios.
- [ ] **Step 4: Native screenshots (V4)** at 700, 1000, 1200, and 1440 pt, with the sidebar shown and hidden, on a Paper with Note cards, an open Question card, and markers (start from `.scratch/chat-release-1-ledger/task-9-native-check/`): no overlap, and each card and marker is at its words.
- [ ] **Step 5: Report** the results in the plan's section 7, and ask the user about the merge into `main` (`--no-ff`).
