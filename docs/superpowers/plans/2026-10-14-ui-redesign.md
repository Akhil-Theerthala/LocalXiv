# UI redesign implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the LocalXiv front end with a native Mac reading app: an AppKit shell (sidebar, toolbar, menus, Settings window) around a rewritten web app with Reading state, Reading position, Reference previews, Split view, and evidence-based reading typography.

**Architecture:** The web app owns all state and computes one Chrome state object. In the Native shell it posts the object to Swift, which draws the sidebar, toolbar, title, and menus and sends every action back as a command. In a browser it draws its own chrome from the same object. The server adds a `reading` table, Reading preference settings, and `allow-scripts` in the paper sandbox.

**Tech stack:** Python 3.14 standard library server, SQLite, plain ES modules and CSS in `app/static/` (no build step, no framework, system fonts only), Swift with AppKit and WebKit.

**Spec:** `docs/superpowers/specs/2026-10-14-ui-redesign-design.md`. Read it in full before any task. The Chrome state contract, the commands, the menus, the toolbar, and "Done when" are defined there and are not repeated here.

**Visual reference:** the Native prototype at `/private/tmp/claude-501/-Users-silver-Developer-LocalXiv/63f34276-610d-429a-8383-7b623bcf039b/scratchpad/prototypes/native/index.html`, with its screenshots in `shots/` beside it. Copy its tokens, spacing, and component styles. It is throwaway code: copy the look, not its structure.

## Global constraints

- Page CSP is `default-src 'self'; style-src 'self' 'unsafe-inline'`: no CDN, no web font, no inline script. Fonts: `-apple-system`/`system-ui`, `ui-serif`, `ui-monospace`, "Charter", "Iowan Old Style", "Palatino". Never the family name "New York".
- Paper and model text are always text nodes or parsed and sanitized DOM, never `innerHTML` of model output.
- No provider key ever reaches the page.
- The executable stays `PapersToKindle`. The Keychain service `org.papers-to-kindle.provider` and the health identity `papers-to-kindle` do not change.
- Release builds target `arm64-apple-macosx26.0`. The development build moves from 11.3 to 26.0.
- Merge with `--no-ff`. Stage files by name; `.claude/launch.json` is modified for local previews and is never staged. Commit messages carry no AI attribution line.
- Run `uvx ruff check .` before committing Python. Run `node tests/test_paper_search_ui.mjs` after changing `render.js`; its six imports (`matchesLibrary`, `inputKind`, `baseID`, `authorList`, `searchRows`, `rowState`) stay exported.
- Tests are component tests through public entry points and live in `tests/` (untracked; in a worktree, link it to the main checkout's `tests/`).
- Never press Generate or Regenerate against a library that has a saved provider key: it spends the user's money. Check those flows with the request blocked or with no key configured.

## Review focus

1. A Paper that fell back to PDF has no chapters and no passages. The Paper view shows the PDF, the outline says that a PDF has no sections, previews and Split view are off, and Overview generation explains why it is blocked.
2. A Paper with no Overview or Blog and no AI connection shows each view as `off` with a way to connect a provider, not a broken tab.
3. A saved Reading position whose chapter or passage no longer exists after a reimport opens the chapter start, or the first chapter, without an error.
4. Author strings with an odd number of parts, no authors, or 30 or more authors keep the row at two lines.
5. A window narrower than 1000 px turns the sidebar into an overlay, and a window at the 700 px minimum keeps every control reachable.

---

### Task 1: Server foundation

**Files:**
- Modify: `papers/library.py` (schema, `list_papers`, `remove_paper`, new `get_reading` and `save_reading`, `SETTING_KEYS`)
- Modify: `app/server.py` (reading route, settings validation, static files, paper CSP)
- Create: `tests/test_reading_state.py`

**Interfaces:**
- Produces: `POST /api/papers/<id>/reading` with a JSON body of any subset of `{state: 'reading'|'read'|'new', view: 'overview'|'blog'|'paper', chapter: str, anchor: str}`, returning `{reading: {...}}`. `state: 'new'` deletes the record. `GET /api/state` papers gain `reading: {...} | null`. Settings accept `reading_theme` (`system`, `light`, `sepia`, `dark`), `reading_font` (`new-york`, `charter`, `iowan`, `palatino`, `sf-pro`), `reading_size` (integer 15 to 26), `reading_width` (`short`, `medium`, `long`), `reading_spacing` (`compact`, `normal`, `relaxed`). The server serves any `/static/<name>.js` or `/static/<name>.css` that exists directly in `app/static/`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_reading_state.py
"""Reading state, Reading preferences, static files, and the paper sandbox, through the server API."""
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from app.server import make_server


class ReadingStateTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.server = make_server(self.root, 0, 'token')
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def call(self, path, body=None):
        request = urllib.request.Request(
            self.base + path, data=None if body is None else json.dumps(body).encode(),
            headers={'Authorization': 'Bearer token', 'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as error:
            return error.code, json.load(error)

    def sample(self):
        return self.call('/api/state')[1]['papers'][0]

    def test_a_new_paper_has_no_reading_record(self):
        self.assertIsNone(self.sample()['reading'])

    def test_reading_record_merges_and_appears_in_state(self):
        paper = self.sample()['id']
        status, body = self.call(f'/api/papers/{paper}/reading',
                                 {'state': 'reading', 'view': 'paper', 'chapter': 'reader/text/ch004.xhtml'})
        self.assertEqual(status, 200)
        self.call(f'/api/papers/{paper}/reading', {'anchor': 'p00015'})
        reading = self.sample()['reading']
        self.assertEqual((reading['state'], reading['view'], reading['anchor']), ('reading', 'paper', 'p00015'))
        self.assertEqual(reading['chapter'], 'reader/text/ch004.xhtml')
        self.assertIsInstance(reading['opened_at'], float)

    def test_read_sets_read_at_and_new_clears_the_record(self):
        paper = self.sample()['id']
        self.call(f'/api/papers/{paper}/reading', {'state': 'read'})
        self.assertIsInstance(self.sample()['reading']['read_at'], float)
        self.call(f'/api/papers/{paper}/reading', {'state': 'new'})
        self.assertIsNone(self.sample()['reading'])

    def test_reading_rejects_unknown_keys_values_and_papers(self):
        paper = self.sample()['id']
        self.assertEqual(self.call(f'/api/papers/{paper}/reading', {'state': 'done'})[0], 400)
        self.assertEqual(self.call(f'/api/papers/{paper}/reading', {'colour': 'red'})[0], 400)
        self.assertEqual(self.call(f'/api/papers/{paper}/reading', {'chapter': 7})[0], 400)
        self.assertEqual(self.call('/api/papers/0000.00000v1/reading', {'state': 'reading'})[0], 404)

    def test_removing_a_paper_removes_its_reading_record(self):
        paper = self.sample()['id']
        self.call(f'/api/papers/{paper}/reading', {'state': 'reading'})
        self.call(f'/api/papers/{paper}/remove', {})
        self.assertIsNone(self.server.app.library.get_reading(paper))

    def test_reading_preferences_round_trip_and_validate(self):
        prefs = {'reading_theme': 'sepia', 'reading_font': 'charter', 'reading_size': 20,
                 'reading_width': 'long', 'reading_spacing': 'relaxed'}
        status, settings = self.call('/api/settings', prefs)
        self.assertEqual(status, 200)
        self.assertEqual({key: settings[key] for key in prefs}, prefs)
        for bad in ({'reading_theme': 'blue'}, {'reading_size': 40}, {'reading_size': '18'},
                    {'reading_font': 'comic'}, {'reading_width': 'huge'}, {'reading_spacing': 2}):
            self.assertEqual(self.call('/api/settings', bad)[0], 400, bad)

    def test_static_files_serve_only_top_level_scripts_and_styles(self):
        for path in ('/static/app.js', '/static/app.css'):
            with urllib.request.urlopen(self.base + path) as response:
                self.assertEqual(response.status, 200)
        for path in ('/static/package.json', '/static/../server.py', '/static/missing.js'):
            with self.assertRaises(urllib.error.HTTPError):
                urllib.request.urlopen(self.base + path)

    def test_paper_files_allow_handlers_but_no_paper_script(self):
        paper = self.sample()
        detail = self.call(f"/api/papers/{paper['id']}")[1]['paper']
        chapter = detail['chapters'][0]['path']
        with urllib.request.urlopen(f"{self.base}/files/{paper['id']}/{chapter}?token=token") as response:
            policy = response.headers['Content-Security-Policy']
        self.assertIn("default-src 'none'", policy)
        self.assertIn('sandbox allow-same-origin allow-scripts', policy)
        self.assertNotIn('script-src', policy)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run the test to see it fail**

Run: `python3 -m unittest tests.test_reading_state -v`
Expected: failures on `reading` keys, the reading route (405 or 404), settings validation, static files, and the CSP.

- [ ] **Step 3: Add the reading table and record functions in `papers/library.py`**

Add `'reading_theme', 'reading_font', 'reading_size', 'reading_width', 'reading_spacing'` to `SETTING_KEYS`. In `__init__`'s `executescript`, add `CREATE TABLE IF NOT EXISTS reading (paper TEXT PRIMARY KEY, value TEXT NOT NULL);`. In `list_papers(summaries=True)`, add `'reading',(SELECT json(value) FROM reading WHERE paper=papers.id)` to the `json_object` call. In `remove_paper`, add `db.execute('DELETE FROM reading WHERE paper=?', (paper_id,))` beside the `generations` delete. Add:

```python
    def get_reading(self, paper_id):
        with self._connect() as db:
            row = db.execute('SELECT value FROM reading WHERE paper=?', (paper_id,)).fetchone()
            return json.loads(row[0]) if row else None

    def save_reading(self, paper_id, values):
        """Merge a validated partial record; state 'new' deletes it, so no record means New."""
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if values.get('state') == 'new':
                db.execute('DELETE FROM reading WHERE paper=?', (paper_id,))
                return None
            row = db.execute('SELECT value FROM reading WHERE paper=?', (paper_id,)).fetchone()
            record = json.loads(row[0]) if row else {'state': 'reading'}
            record.update(values, opened_at=time.time())
            if values.get('state') == 'read':
                record['read_at'] = time.time()
            elif values.get('state') == 'reading':
                record.pop('read_at', None)
            db.execute('INSERT OR REPLACE INTO reading VALUES (?,?)', (paper_id, json.dumps(record)))
            return record
```

- [ ] **Step 4: Add the route, validation, static files, and CSP in `app/server.py`**

Beside the `blog`/`overview`/`export`/`send` route, add:

```python
        if len(parts) == 4 and parts[:2] == ['api', 'papers'] and parts[3] == 'reading':
            if not app.library.get_paper(parts[2]):
                raise KeyError(parts[2])
            allowed = {'state': ('new', 'reading', 'read'), 'view': ('overview', 'blog', 'paper')}
            if set(body) - {'state', 'view', 'chapter', 'anchor'}:
                raise ValueError('Unknown reading field.')
            for key, value in body.items():
                if key in allowed and value not in allowed[key] or not isinstance(value, str) or len(value) > 300:
                    raise ValueError(f'Invalid {key}.')
            return self.respond(200, {'reading': app.library.save_reading(parts[2], body)})
```

In the settings handler, after the existing boolean checks:

```python
            choices = {'reading_theme': ('system', 'light', 'sepia', 'dark'),
                       'reading_font': ('new-york', 'charter', 'iowan', 'palatino', 'sf-pro'),
                       'reading_width': ('short', 'medium', 'long'),
                       'reading_spacing': ('compact', 'normal', 'relaxed')}
            for field, options in choices.items():
                if field in values and values[field] not in options:
                    raise ValueError('Reading preference out of range.')
            size = values.get('reading_size', 18)
            if type(size) is not int or not 15 <= size <= 26:
                raise ValueError('Text size must be a whole number from 15 to 26.')
```

Add the five keys with their defaults (`'system'`, `'new-york'`, `18`, `'medium'`, `'normal'`) to `DEFAULTS`. Replace the `static = {...}.get(url.path)` lookup with:

```python
            name = 'index.html' if url.path == '/' else url.path.removeprefix('/static/')
            if (url.path == '/' or url.path.startswith('/static/') and '/' not in name
                    and name.endswith(('.js', '.css')) and (STATIC / name).is_file()):
                path = STATIC / name
                return self.respond(200, path.read_bytes(),
                                     mimetypes.guess_type(path.name)[0] or 'application/octet-stream')
```

In `respond`, change the paper policy's sandbox to `sandbox allow-same-origin allow-scripts`, with this comment above it: `# allow-scripts lets the app's own handlers run on paper elements in WebKit; default-src 'none' still blocks every paper script.`

- [ ] **Step 5: Run the tests**

Run: `python3 -m unittest tests.test_reading_state tests.test_paper_jobs -v`
Expected: all pass. `test_paper_jobs` proves the job API did not regress.

- [ ] **Step 6: Lint and commit**

```bash
uvx ruff check .
git add papers/library.py app/server.py
git commit -m "Store Reading state and Reading preferences, and let the app handle paper links"
```

---

### Task 2: Native snapshot harness and shell spike

**Files:**
- Create: `app/macos/Automation.swift` (compiled only with `-D LOCALXIV_AUTOMATION`; the whole file is inside `#if LOCALXIV_AUTOMATION`)
- Create: `tools/native_shot.py`
- Modify: `app/macos/PapersToKindle.swift` (call the automation hook after the first page load, inside `#if LOCALXIV_AUTOMATION`)
- Modify: `install-app.sh`, `app/macos/build-release.py` (compile `app/macos/*.swift`; development target and plist minimum 26.0)

**Interfaces:**
- Produces: `python3 tools/native_shot.py --library DIR --steps STEPS.json --out DIR`. It builds an automation copy of the app into a scratch root (`PAPERS_INSTALL_ROOT`, `PAPERS_APPLICATIONS_DIR`), rewrites the scratch copy's `launch.command` to `port=0`, copies `node_modules` as a real tree (`rsync -aL`), copies the library, refuses to start when the library's `session.json` names a live service, runs the app with `LOCALXIV_AUTOMATION=STEPS.json`, waits for it to quit, stops the scratch service (`pkill -f -- "--data-dir <scratch library>"`), and prints the snapshot paths.
- Step file: a JSON list. Each item is one of `{"js": "..."}`, `{"command": {...}}` (calls `window.localxiv.command` when it exists), `{"state": {...}}` (delivers a Chrome state to the shell as if the page posted it), `{"toolbar": "<item identifier>"}` (performs the item's action), `{"menu": "View/Paper"}`, `{"wait": seconds}`, `{"size": [width, height]}`, `{"appearance": "light" | "dark"}`, `{"snapshot": "name.png"}`, `{"quit": true}`.
- A snapshot draws `window.contentView!.superview!` with `cacheDisplay(in:to:)` at 2x, then draws the web view's `takeSnapshot` image at the web view's frame, and writes a PNG into the run's output folder.

- [ ] **Step 1:** Write `Automation.swift` with the step runner and snapshot, `tools/native_shot.py`, and the build-script changes.
- [ ] **Step 2:** Spike the shell in `PapersToKindle.swift`: an `NSSplitViewController` with a full-height sidebar item holding an `NSOutlineView` source list with two static rows, a content item holding the existing WKWebView, a unified `NSToolbar` with the sidebar toggle and one `NSToolbarItemGroup`, and one View menu item.
- [ ] **Step 3:** Run `tools/native_shot.py` with steps that wait for the page, snapshot in light, switch to dark, snapshot again, and quit.
  Expected: two PNGs that show the traffic lights, the toolbar items, the sidebar rows, and the current web page in the content area. Read both PNGs and confirm. Confirm that `lsof -nP -iTCP -sTCP:LISTEN` shows no scratch service afterwards.
- [ ] **Step 4:** Compile both ways: `xcrun swiftc -D LOCALXIV_AUTOMATION ... app/macos/*.swift` and the production command from `install-app.sh` without the flag. Confirm with `nm` that the production binary has no `Automation` symbols.
- [ ] **Step 5:** Commit: `Add a native snapshot harness and spike the split-view shell`.

---

### Task 3: Native shell

**Files:**
- Create: `app/macos/Shell.swift` (window, split view, Chrome state model, bridge), `app/macos/Sidebar.swift`, `app/macos/Toolbar.swift`, `app/macos/Menus.swift`, `app/macos/ReadingPopover.swift`, `app/macos/SettingsWindow.swift`
- Modify: `app/macos/PapersToKindle.swift` (keep service start, health check, downloads, navigation policy, Sparkle; delete `WindowDragView`, the drag-region script, and its message handler)
- Modify: `docs/development.md` (file list, harness usage)

**Interfaces:**
- Consumes: the Chrome state and command contract in the spec; Task 2's harness.
- Produces: a `shell` script-message handler that accepts `{type: 'ready'}` and `{type: 'state', state}`; `PapersApp.send(_ command: [String: Any])`, which calls `window.localxiv.command(...)` with JSON-encoded arguments and queues commands until `ready`.

Behavior (each line is a check in the harness):

- [ ] Decode `ChromeState` with `JSONDecoder` into Swift structs; an unknown or missing field never crashes the shell.
- [ ] Sidebar, Library mode: Home; a LIBRARY section with All Papers, New, Reading, and Read with count badges; a RECENT section with up to five Papers; selection follows `sidebar.selected` or the current recent Paper without sending a command; a click sends `go` or `open`. An Activity view pinned under the outline shows `activity.label` and an `NSProgressIndicator` (indeterminate when `progress` is null) and sends `activity` on click; it is hidden when `activity` is null.
- [ ] Sidebar, Reader mode: a back row "‹ Library" (or the `back` value) that sends `back`; the title and byline; a CONTENTS section with the outline, indented by `level`, with `number` in the secondary colour; the `current` entry is selected and scrolled into view without sending a command; a click sends `outline`.
- [ ] Toolbar: identifiers `sidebar`, `history`, `addPaper`, `views`, `reading`, `share`, `more`, `search`, plus the system sidebar toggle and tracking separator. Items that the mode does not show are hidden with `isHidden`. `views` disables a segment whose state is `off`. `share` and `more` rebuild their menus from `actions`, with `separatorBefore` and destructive roles. `search` sends `search` on each change and `search` with `submit: true` on Return; it shows `search.query` when the page changes it.
- [ ] Window title and subtitle from `title` and `subtitle`.
- [ ] Menus as the spec's table, each sending its command and enabled from the state. `⌘,` opens the Settings window.
- [ ] Aa popover: theme swatches (Light, Sepia, Dark, Match system), font pop-up with each name in its own face, size slider 15 to 26 with the value, line length and line spacing segmented controls; each change sends `prefs` with one field.
- [ ] Settings window: preference-style toolbar with General, Reading, AI, Kindle, Search, and Help panes; one WKWebView on `/?panel=settings&pane=<pane>#token=<token>`; a pane click sends `settings` with the pane to that web view; it reopens on the last pane.
- [ ] Harness snapshots for "Done when" item 7: Library mode and Reader mode (light and dark), the Aa popover, and the Settings window, driven by `state` steps before Task 5 lands and by the real page after.
- [ ] Commit per item group; final message `Draw the window with a native split view, toolbar, and menus`.

---

### Task 4: Web foundation

**Files:**
- Rewrite: `app/static/index.html`, `app/static/app.css` (absorbs `reader-layout.css`, which is deleted), `app/static/app.js`
- Rewrite: `app/static/appearance.js` (Reading preferences: themes, fonts, sizes, widths, spacing; server persistence with a `localStorage` copy)
- Create: `app/static/shell.js` (Chrome state, web chrome renderer, command dispatcher, key map, bridge)
- Modify: `app/static/render.js` (keep the six search exports; library rows; job notices; author names; dates)
- Delete: `app/static/view.js` (its job moves into `shell.js`)

**Interfaces:**
- Consumes: Task 1's API.
- Produces for Task 5:
  - `import {commands, register, chrome} from './shell.js'`. `register(name, handler)` adds a command handler. `commands.run({name, ...})` runs one. `chrome.update(patch)` merges into the Chrome state and schedules one render or post per animation frame.
  - In `app.js`: `openPaper(id, {position})`, `api(path, payload)`, `fileURL(path)`, `saveReading(id, patch)` (debounced by the caller), and the element `#reader` (a `<section>` that Task 5 fills), plus `#reader-header` already rendered with the arXiv ID and month, title, authors, and links.
  - CSS tokens on `:root`: `--paper`, `--label`, `--label-2`, `--label-3`, `--separator`, `--card`, `--accent`, `--accent-tint`, `--popover`, `--measure`, `--reading-size`, `--reading-leading`, `--reading-font`, for Light, Sepia, and Dark.

Behavior (each line is checked in the browser pane and with `wkshot`):

- [ ] Browser mode draws a sidebar and a toolbar that match the Native prototype, from the Chrome state, including the 760 px overlay sidebar. Native mode (`window.webkit?.messageHandlers?.shell`) draws none of them and posts `ready` then each state.
- [ ] Home: the search field, Continue reading (up to three Papers in the Reading state, last section), Recently added, and the first-run welcome while the library holds only the sample.
- [ ] Library views All Papers, New, Reading, and Read; the Continue reading card on All Papers; rows per the spec; four sorts; arrow keys and Return; a context menu (a web menu in both modes) with Open, Mark as Read or Unread, Copy arXiv Link, Copy BibTeX, and Remove from Library with the existing confirmation dialog.
- [ ] Search: the shared component from the old `bindSearch` and results page, live as the reader types, with Escape returning to the previous page; Direct import of links.
- [ ] Settings: one settings view with panes General, Reading, AI, Kindle, Search, and Help that holds every existing field and the connection test; a dialog with its own pane list in a browser; the whole page in `?panel=settings` mode, showing the pane from the `settings` command.
- [ ] Setup dialog as today; the tour removed.
- [ ] Share and More actions as `actions` in the Chrome state and as web menus in browser mode; export, Send to Kindle (a small sheet for Include and EPUB format), Copy arXiv Link, Copy BibTeX (`@misc{<arXiv id>, title, author, year, eprint, archivePrefix = {arXiv}}`), Mark as Read or Unread, Open PDF, Open on arXiv, Regenerate, Remove.
- [ ] Job notices: toasts at the top right of the content with Cancel, Retry, and download links; `activity` in the Chrome state; the `activity` command opens the job list.
- [ ] Reading preferences from the server settings, a `localStorage` copy for the first paint, the Aa popover in browser mode, and `⌘+`, `⌘-`, `⌘0`.
- [ ] One history for page changes; `back` and `forward`; `canBack` and `canForward` in the Chrome state.
- [ ] `node tests/test_paper_search_ui.mjs` passes.
- [ ] Commit per behavior group.

---

### Task 5: Reader

**Files:**
- Create: `app/static/reader.js` (Paper view, Reference previews, outline, Reading position, Blog view, Overview view, Split view)
- Modify: `app/static/app.css` (reader section), `app/static/render.js` (Blog citations, figure rendering)

**Interfaces:**
- Consumes: Task 4's `register`, `chrome.update`, `openPaper`, `api`, `fileURL`, `saveReading`, `#reader`, `#reader-header`, and the CSS tokens.
- Produces: commands `view`, `outline`, and the in-reader history entries; `chrome.update({views, sidebar: {reader}, actions})` while a Paper is open.

Behavior:

- [ ] The paper iframe has `sandbox="allow-same-origin allow-scripts"`. The reader stylesheet injected into it uses the Reading preference tokens: measure in em, 18 px default, leading 1.55, `text-wrap: pretty`, `hyphens: auto`, centred display math with sideways scroll, figures and tables up to 1.5 times the measure, tabular numerals in tables, light cards for figures in Dark and Sepia.
- [ ] Outline: every chapter; the current chapter expanded to its `h2` and `h3` headings; scroll-spy on the page scroll that sets `current` at most once per frame.
- [ ] Reference previews for citations (`#ref-`), cross-references (`data-reference-type`), footnotes, and section links, after 250 ms, from a cached `fetch` and `DOMParser` of the target chapter; none for a link that does not resolve; Go to reference and Search; kept inside the viewport.
- [ ] Clicking a link inside the paper goes to its target with a history entry; Back returns to the same scroll position; external links open outside the app.
- [ ] Clicking a paper figure opens the figure dialog.
- [ ] Previous and next chapter at the end of each chapter.
- [ ] Reading position: view, chapter, and the passage ID at the top of the viewport, saved two seconds after scrolling stops and on view change; restored on open, falling back to the chapter start or the first chapter; not moved by a jump until the reader scrolls there; state Reading set on first open; one "Mark as read" prompt at the end of the last body chapter.
- [ ] Blog view: header with title, lead, and provenance with reading time; body from `cited_text` with superscript citation markers; passage preview on hover; open the Paper at the passage on click; the `limitation` at the end; the outline lists the question headings.
- [ ] Overview view: the inline figure with no frame inside a frame, the provenance line, the Component hover as today, and the outline of panels.
- [ ] Split view at 1200 px and wider; a switch to the Paper view with Back below that.
- [ ] Generation states inside the view: empty with Generate, working with progress, failed with Retry, off with Connect AI.
- [ ] PDF fallback: the PDF in the frame, an outline note, previews and Split view off.
- [ ] Commit per behavior group.

---

### Task 6: Integration and verification

- [ ] Run the native harness against the real web app on a copy of the library: Home, Library, search, the reader in each view, the Aa popover, the Settings window, light and dark. Fix every mismatch between the Chrome state and the native drawing.
- [ ] Walk every flow in "Done when" item 1 in the browser pane. Check items 2 to 8 with their tools. Record each result in the decision log.
- [ ] Commit fixes per flow.

### Task 7: Documentation and review

- [ ] Update `README.md` (Home, Library, the reader, Settings paths, Share and Kindle), `docs/development.md` (Swift file list, the harness, browser mode), and record the open items of the 2026-09-25 UX audit that this change closes.
- [ ] Run the `code-review` skill against `main` (standards and spec), then `deslop` and `no-comments`, and fix what they find.
- [ ] Revert `.claude/launch.json`. Merge only on the user's word.
