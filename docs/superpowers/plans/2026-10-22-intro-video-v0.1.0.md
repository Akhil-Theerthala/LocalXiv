# The v0.1.0 intro film Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the films, stills, carousel, and README loop of the spec from real captures of v0.1.0 and real Chat takes, and do the launch prep that the owner chose.

**Architecture:** `capture.mjs` drives the app through `window.localxiv.command` in headless Chromium, on a temporary server that patches the Keychain and Mail names. A loopback stub on `127.0.0.1:11434` records one stream of a model on this Mac, then replays it chunk by chunk while the capture takes a screenshot of each chunk. Remotion plays the saved states on the beat grid of `src/timeline.mjs`, which `check.mjs` asserts before every render and `music.mjs` scores.

**Tech Stack:** Node 22, Remotion 4.0.529, Playwright 1.63.0 on Remotion's chrome-headless-shell 149.0.7790.0, React 19.3.0, Python 3.14 (the repository `.venv`, `unittest.mock`), Ollama 0.40.8 with `granite4.1:8b` (only after the owner's yes), ffmpeg, epubcheck, gh.

**Spec:** [`docs/superpowers/specs/2026-10-22-intro-video-v0.1.0-design.md`](../specs/2026-10-22-intro-video-v0.1.0-design.md). Five readers checked its claims against the code on 2026-10-22. Where they found the spec wrong, the task follows the code and says so in one line that starts with "Map:".

## Global Constraints

- Read `CODING_STANDARDS.md` and follow the `ponytail` rules: the smallest change that fully works. Reuse `brand.jsx`, `Camera`, `Shot`, `Crop`, and `music.mjs`. Add no dependency, except the model server that the owner approves in Task 3. No app code changes.
- Work on the branch `intro-video-v0.1.0` in the worktree `/Users/silver/Developer/LocalXiv/.worktrees/intro-video-v0.1.0` (below: `<wt>`). Other sessions switch branches in the main checkout. Run the commands in `<wt>/tools/intro-video` unless a step names another folder.
- Commit with `test "$(git branch --show-current)" = intro-video-v0.1.0 && git add <each file by name> && git commit -m "<message>"`. Never use `git add -A` or `git add .`. The message describes the change only. Add no `Co-Authored-By` line and no "Generated with" line.
- Before a commit that changes Python, run `uvx ruff check .` in `<wt>`. Expected: no problems.
- The film shows v0.1.0. Before each capture, `git -C <wt> diff --quiet v0.1.0 -- app papers native` must exit 0. If it does not, stop and ask the owner (spec Section 10).
- Master: 1920×1080, 60 fps, H.264 and AAC, 90.0 s = 180 beats = 5,400 frames. Cutdown: 25.0 s = 50 beats = 1,500 frames. Highlights clip: 15 s = 900 frames. 120 BPM, 1 beat = 0.5 s = 30 frames.
- Card hold: full opacity for at least max(1.2 s, 0.35 s a word). The fade does not count. Enter 200 ms (opacity 0 to 1, 12 px rise, ease-out `(0.16, 1, 0.3, 1)`). Exit 150 ms (opacity 1 to 0, 6 px rise, ease-in `(0.7, 0, 0.84, 0)`). No word or letter stagger. At most 6 words a card, except the name card. At most 2 lines and 42 characters a line.
- Size floor: nothing that the viewer must read is under 56 px. Cards are Avenir Next Demi Bold 84 px in INK `#272820`. Safe area: 115 px at each side. Nothing to read below y = 880 px. At most two text zones at once (spec 4.2).
- Contrast: 4.5:1 or more under each card, label, strip verb, and end-card line.
- Camera: ease-in-out `(0.65, 0, 0.35, 1)`. Moves take 400–500 ms, except the S10 drift (1.75 s) and the S14 pull-back (1.8 s). Zoom changes start 3 s apart or more. A cut is not a zoom move. No zoom above 2.2x at 16:9. At 2.2x or less, Remotion never upscales the capture at deviceScaleFactor 3. The camera is still while the reader types or an answer streams. It pans only when a growing card leaves the frame (spec 4.3).
- Streams play at the captured speed. A wait is cut with a visible 4-frame dip to PAGE `#f5f1e8`. A stream is never sped up.
- Audio: −14 LUFS integrated and −1 dBTP or lower, measured with ffmpeg `ebur128` with `peak=true`. UI sounds sit about 18 dB under the music. D major, I-V-vi-IV, 120 BPM.
- Words never to use in the film, the stills, the README, and the GitHub texts (spec 3.4): "agent", "AI agent", "nothing leaves your Mac", "any paper", "every paper", "only" and "first" as a claim about LocalXiv, "no account", "no analytics", "accurate answers", "no hallucinations", "every answer shows its source", "free AI", "find papers anywhere", "works with VoiceOver", "local-first", "chat with your paper", "understand a paper in minutes", "close reading" as a lead, "cognitive debt", "brain rot", "AI makes you dumb", and a date for Linux.
- From Task 4 to Task 12, `npm run render` and `node music.mjs` do not run, because the new grid replaces the old exports. The branch merges only after Task 17.
- No figure or table of the sample. No window chrome, no web toolbar or sidebar, no New York font (Chromium draws it as Georgia).
- Every word in a Question card is real output of the model that the provenance line names. The film never edits, retypes, or speeds up an answer, and never adds a citation. Never option B.
- Safety (spec 7.4): Patch the Keychain names before `make_server`. Never click `#send`, never submit `#kindle-form`, never press Enter inside it, and keep `auto_send` false. Never click `#reader-pdf`, `#reader-arxiv`, Add on a search row, Explain, Copy All, Export Markdown…, Back Up Notes, `#chat-copy`, `#chat-delete-key`, or any Test Connection button. Never type in a key field. No real key and no real e-mail address on screen; the Kindle address is `your-name@kindle.com`. The capture uses a temporary library, never the owner's. Never run `tools/native_shot.py` or open a native app window without the owner's yes.
- Copy is in ASD-STE100 with the terms of `CONTEXT.md`: Paper, Highlight, Note, Question card, Ask, Chat, All Notes, Reading preferences, Reference preview. The owner is "the owner".

## Decisions this plan takes

The owner can change each one.

1. **No web toolbar, by a Native stub.** `capture/app.mjs` installs `window.webkit.messageHandlers.shell` before load. Then `body.native` hides the web toolbar and sidebar (`app/static/app.css:207`), and the Native insets apply (`reader.js:26`, `margin.js:26`, `selection.js:43`). This is the content that Mac users see. As a result, `settings` posts to the stub and draws nothing (`app.js:812`), so S08 uses `?panel=settings&pane=chat`. The key map is off, so every change goes through `window.localxiv.command`, and its CSS transitions play.
2. **Figure 2 is not on screen.** The figure `fig:multi-head-att` sits one heading below p00024 (`ch004.xhtml:44-56`), so it is beside the Question card in every Ask frame. Task 2 hides every figure and table, and `shot()` asserts it. p00026 moves up into the space. No Highlight moves, because every Highlight is above the figure.
3. **Document coordinates.** Every rect and point in `rects.json` is in document CSS px. Each shot records where its image starts in the document, and `Shot` draws the image there. So shots taken at different scroll positions line up under one camera. The PNGs and `page.mouse` use viewport px: `toViewport` (Task 2) is the one place that converts.
4. **The flash from two real states.** A screenshot at deviceScaleFactor 3 cannot be taken every 100 ms. The capture takes the tinted passage and the passage after the flash. The film holds the tint for 975 ms and then crossfades for 225 ms with ease-out, which is the app's own keyframes (`appearance.js:79,84`). This replaces the 0.1 s steps of spec 7.3.
5. **Typing as one shot per character.** The Note and both questions are one line each, so 94 shots are enough.
6. **Units.** `CUES` are in beats from the scene's start, as `music.mjs` reads them today. Cards, labels, the strip, and camera zooms are in seconds on the whole film, as spec 5.2 and 5.3 print them, so a reviewer can compare them line by line. `check.mjs` converts both to frames in one place.
7. **Shared shots.** `AskShot`, `CitationShot`, `ChatModelShot`, and `EndCard` serve the master and the cutdown. K1 holds the cues before the Ask click; K2 holds the cues from the click (`ask: 0`). `AskShot` merges them with K2 shifted by 5 beats.
8. **Strict replay.** The replay stub compares each incoming request with the recorded request. A difference stops the capture. So the words on screen answer exactly the request that the app sent.
9. **The Chat clock.** The capture server reads Chat's time from a file that the capture writes before each Ask. Each turn's date is the date of its own recording.
10. **The model.** Ollama with `granite4.1:8b` and a 16,384-token context, so the whole Paper fits (about 10,150 tokens by the app's count). Task 3 Step 1.
11. **Mail.** The capture server also patches `app.server.send_with_mail` to raise. Task 2.
12. **Two more Papers for S12.** Both have a CC BY 4.0 licence on their arXiv page. They come from the parser corpus inputs, so they are known to convert.
13. **Carousel slide 12** is the end-card frame with no slip, because the end card already shows "Free and open source", "Coming soon to Linux", and the URL.
14. **The verb strip sits on the Card's PAPER scrim, and its earlier verbs are INK at 70%** (5.5:1 on PAPER). Map: spec 4.2 sets INK at 45% with no scrim over Paper text. That is 2.7:1, which breaks the spec's own 4.5:1 rule.
15. **The Highlights clip moves one card.** The clip cuts at 29.0 s, but "Notes sit beside the words." is full from 28.1 s. In the clip, it is full from 27.1 to 28.85 s (`CLIP_CARDS`, Task 4), so it holds 1.75 s and exits before the cut. The clip stays 15 s.

## Not in this plan

- Options B, C, and D of spec 7.5. D needs the owner's yes and a plan change, because the host line and the provenance line change.
- The two-column hook of spec 5.4, the inserts of spec 6.5, the extended cut, and 9:16.
- Spec 8.7 items 3, 4, and 7, and notarization.
- The posts themselves. The owner posts by hand. Pushing `main` is the owner's call.

## Review Focus

1. A take with no citation, or with a citation in `ch009`, on Figure 2 (`p00025`), or outside the request's `<paper>` block (the app shows that one as `?`): `judgeTake` rejects the take. The capture also stops before S07 when the finished answer has no `.cn .citation` or has a `.unverified` citation. Pinned in Task 3 Step 7 and Task 6 Step 2.
2. A stream longer than its window: the answer plays at its recorded speed and loses its middle behind one more dip. The new content shows from the dip's third frame, and the last chunk lands on the window's `end` frame. S09 cuts at the end of its window with no dip. Pinned in Task 8 Step 1.
3. A capture in which the margin folds to markers (a narrower window, a larger text size, the web sidebar): `shot()` throws and saves nothing. Pinned in Task 2 Step 3 (the harness check), in Gate 2, and in Task 6 Step 4 at the S14 capture with two turns.
4. A dialog open when a page command runs: `command()` throws "`<name>` while a dialog is open", where the app drops the command with no message (`shell.js:60-62`). Pinned in Task 2 Step 3.
5. A replay on a later day, or with a request that differs from the take: the provenance line shows the date of the recording, and a changed request stops the capture with "request differs from take `<name>`". Pinned in Task 3 Step 14.

---

## Part 1: Setup and the three gates

A failed gate stops the work. Report it to the owner and wait.

### Task 1: Worktree and dependencies

**Files:**
- No tracked file changes. The task adds two symbolic links and `tools/intro-video/node_modules`, which git ignores (root `.gitignore:8,13`, `.git/info/exclude:7`).

**Interfaces:**
- Produces: `<wt>`, `<wt>/.venv` (a link to `/Users/silver/Developer/LocalXiv/.venv`, Python 3.14.9), `<wt>/node_modules` (a link to the root `node_modules`, which serves `/static/mathjax.js`, `app/server.py:713-715`), and Remotion's browser at `<wt>/tools/intro-video/node_modules/.remotion/chrome-headless-shell/mac-arm64/chrome-headless-shell-mac-arm64/chrome-headless-shell`.

- [ ] **Step 1: Check main.** Run `git -C /Users/silver/Developer/LocalXiv log -1 --format=%h -- docs/superpowers/plans/2026-10-22-intro-video-v0.1.0.md docs/superpowers/specs/2026-10-22-intro-video-v0.1.0-design.md` and `git -C /Users/silver/Developer/LocalXiv status --short -- docs/superpowers`. Expected: a hash, then no output. If the spec or this plan is not committed on `main`, stop and ask the owner.
- [ ] **Step 2: Make the worktree.** `git -C /Users/silver/Developer/LocalXiv worktree add .worktrees/intro-video-v0.1.0 -b intro-video-v0.1.0 main`.
- [ ] **Step 3: Link** `ln -s /Users/silver/Developer/LocalXiv/.venv <wt>/.venv` and `ln -s /Users/silver/Developer/LocalXiv/node_modules <wt>/node_modules`.
- [ ] **Step 4: Install.** `npm install`, then `npx remotion browser ensure`. Run both in `<wt>/tools/intro-video`, because Remotion puts the browser under the nearest `package.json`.
- [ ] **Step 5: Check** that everything starts:
  - In `<wt>`: `.venv/bin/python -c "import app.server; print(app.server.__file__)"`. Expected: a path under `<wt>/app/`.
  - In `<wt>/tools/intro-video`: `node -e "import('playwright').then(async ({chromium}) => { const b = await chromium.launch({executablePath: 'node_modules/.remotion/chrome-headless-shell/mac-arm64/chrome-headless-shell-mac-arm64/chrome-headless-shell'}); console.log(b.version()); await b.close(); })"`. Expected: `149.0.7790.0`.
  - `ffmpeg -version` and `epubcheck --version` print versions.
  - `git -C <wt> diff --quiet v0.1.0 -- app papers native && echo same` prints `same`.
- [ ] **Step 6: Check** that `git -C <wt> status --short` prints nothing. No commit in this task.

### Task 2: The capture harness, Gate 1, and Gate 2

**Files:**
- Create: `tools/intro-video/capture_server.py`, `tools/intro-video/capture/app.mjs`, `tools/intro-video/capture/records.mjs`, `tools/intro-video/capture/flow.mjs`, `tools/intro-video/capture/gates.mjs`

**Interfaces:**
- Produces `capture_server.py <data-dir>`. Environment: `CAPTURE_TOKEN` (required) and `CAPTURE_CLOCK` (optional: the path of a file that holds a Unix time). Inside `main()`, it does these steps in this order:
  1. `sys.path.insert(0, str(Path(__file__).resolve().parents[2]))`. The script's own folder is first on `sys.path`, so without this line `import app.server` fails. Import inside `main()`, so ruff gives no E402.
  2. Start these patches: `app.server.get_key` returns `''`; `app.server.set_key` and `app.server.delete_key` are plain mocks; `papers.search.get_key` returns `''`; `app.server.send_with_mail` raises `RuntimeError('The capture never sends mail.')`.
  3. When `CAPTURE_CLOCK` is set, patch `papers.chat.time` with `types.SimpleNamespace(time=lambda: float(Path(clock).read_text()))`. This replaces only the name in `papers.chat` (`chat.py:3,208,244`), not the `time` module.
  4. `s = make_server(argv[1], 0, os.environ['CAPTURE_TOKEN'])`, print `s.server_port` with flush, and `s.serve_forever()`.
  - Map: spec 7.2 patches only the three names that `app.server` imports. `papers/search.py:13` imports its own `get_key` and reads it at `:156` on each search, so the plan patches it too.
  - `capture_server.py --check` starts the patches of step 2 and asserts that `app.server.get_key('x')` is `''` and that `app.server.send_with_mail(None, None, None)` raises the capture's `RuntimeError`. It prints `patches ok` and exits. It starts no server and sends nothing.
- Produces in `capture/app.mjs`:
  - `REPO` (the checkout root), `PUBLIC` (`tools/intro-video/public`), `SAMPLE = '1706.03762v7'`.
  - `startApp({model = 'granite4.1:8b', clock = null}) -> Promise<{base, token, dir, clock, stop()}>`. It makes a `localxiv-capture-` temporary folder and spawns `REPO/.venv/bin/python REPO/tools/intro-video/capture_server.py <dir>` with `cwd: REPO`, `PATH` plus `:/opt/homebrew/bin` (for epubcheck), a 48-hex-character `CAPTURE_TOKEN`, and, when `clock` is set, `CAPTURE_CLOCK: path.resolve(clock)`. The server runs in `REPO` and Node runs in `tools/intro-video`, so a relative path would name two files. It returns that absolute path as `clock`, and every writer of the clock uses it. It reads the port from stdout and then POSTs `SETTINGS` to `/api/settings`. `stop()` kills the server and removes `dir`.
  - `SETTINGS = {onboarding_complete: true, auto_send: false, open_imports: false, search_suggestions: false, kindle_email: 'your-name@kindle.com', chat_endpoint: 'http://127.0.0.1:11434/v1', chat_model: model, chat_context: 16384, reading_font: 'sf-pro', reading_size: 16, reading_theme: 'light', reading_margins: 'normal'}`. A new library opens `#setup-dialog` until `onboarding_complete` is true (`app.js:1166`). `search_suggestions: false` keeps every search off.
  - `api(app, path, body?) -> Promise<object>`: `fetch` with `Authorization: Bearer <token>` and JSON. It throws on a status that is not 2xx. A GET of settings is `GET /api/state` → `.settings`; there is no GET `/api/settings` (`server.py:716-722`).
  - `openBrowser({engine = 'chromium'}) -> Promise<{browser, context}>`: Remotion's chrome-headless-shell, or Playwright WebKit. The context has `viewport {width: 1440, height: 900}`, `deviceScaleFactor: 3`, `locale: 'en-US'`, `timezoneId` set to this Mac's zone, and `acceptDownloads: false`. Its init script installs the Native stub `window.webkit = {messageHandlers: {shell: {postMessage: m => (window.__posts ||= []).push(m)}}}`.
  - `loadApp(context, app, query = '') -> Promise<Page>`: goes to `${base}/${query}#token=${token}` and waits until `window.__posts` holds `{type: 'ready'}`. The main page posts it from `chrome.ready()` after the first refresh (`shell.js:43`, `app.js:1168`), and the `?panel=settings…` page after `fillSettings()` (`app.js:1159`). With no `query`, it asserts that `body.native` is set and that `#toolbar` and `#sidebar` are not visible. With `?panel=settings…`, it asserts that `#chat-model` has a value; that page shows the form alone (`app.css:689`). Map: under the stub, nothing sets `body.dataset.mode`, because `flush()` calls `draw()` only in browser mode (`shell.js:33-34`).
  - `toViewport(rectOrPoint, scrollY)`: the same rect or point with `scrollY` subtracted from its `y`. It is the one conversion from document px to the viewport px of a PNG or of `page.mouse`.
  - `command(page, c) -> Promise<any>`: when `c.name` is one of `go, open, view, outline, back, forward, leave, search, add` and a `dialog[open]` exists, it throws `` `${c.name} while a dialog is open` ``. Else it returns `page.evaluate(c => window.localxiv.command(c), c)`.
  - `openPaper(page, {id = SAMPLE, passage = 'p00020'})`: `open` (it shows the Overview first, `reader.js:69-70`), then `view` `paper`, then `outline` `reader/text/ch004.xhtml#<passage>`, which scrolls with the app's own formula and inset. It waits for `#paper-frame`'s document to hold the passage, then waits 200 ms with no scroll, so the app holds that passage through later text-size changes (`reader.js:355-358,497-499`). Then it adds the style `figure,table{display:none}` to that document. It adds the style again after each `lx-chapter` event on `window` (`reader.js:428`).
  - `findWords(page, {passage, quote, prefix = '', suffix = ''}) -> Promise<{rects: Rect[]}>`: runs `await import('/static/onetext.js')` in the top page (the frame's CSP blocks `import()`), calls `findWords(frameDocument.getElementById(passage), quote, prefix, suffix)` (`onetext.js:63`), and returns the range's client rects plus the frame's rect plus `scrollY`, in document px. It throws `no words: <quote>` on `null`. A quote is in one-text form: each formula reads as ` $tex$ ` (`onetext.js:15-18`).
  - `drag(page, words, {ms = 700, steps = 24, stops = [], onStop = async () => {}}) -> Promise<Path>`: presses the mouse at mid-height, 1 px inside the left edge of the first rect. It moves in `steps` steps to 1 px inside the right edge of the last rect, and releases. Before each `page.mouse` call, it converts the point with `toViewport` and the current `window.scrollY`. It calls `onStop(i)` at each step index in `stops` while the button is down. It returns `[[x, y, ms], …]` in document px. A selection made in JavaScript paints grey in Chromium, so the drag uses the real mouse.
  - `clickOn(page, selector, {frame = false}) -> Promise<Point>` and `hoverOn(page, selector, {frame = false}) -> Promise<Point>`: move the mouse in 10 steps to the centre of the element's viewport rect and click or stop there. They return the document point.
  - `drag`, `clickOn`, and `hoverOn` throw `off-screen: <quote or selector>` when a viewport point is outside [0, 900).
  - `shot(page, name, {clip, fullPage, settle = true} = {}) -> Promise<string>`: with `settle`, it takes each animation of the page and the frame whose `playState` is `running` and whose iteration count is finite. It waits for their `finished` promises (3 s at most), then for two animation frames. So the infinite `lx-march` of the card line (`app.css:520`), which every selected card draws (`margin.js:528-531`), does not block, and neither does a finished `forwards` fill (`app.css:524`). `settle: false` shoots at once; S07 `flash` needs it, because the flash animation lives for its whole 1.2 s. When a Paper is open, it asserts that no `.lx-card.is-marker` exists (`margin.js:509`) and that no `figure img` in the frame has a non-zero rect. It writes `public/<name>.png`, stores `rects.shots[name] = {x: clip?.x ?? 0, y: fullPage ? (clip?.y ?? 0) : scrollY + (clip?.y ?? 0), width: clip?.width ?? page.viewportSize().width}` (where the image starts in the document, and its CSS width), and returns the path.
  - `rects` (an object) and `saveRects()`. The file `public/rects.json` has the shape `{shots: {[name]: {x, y, width}}, [scene]: {[key]: Rect | Point | Path}}`. `Rect = {x, y, width, height}`, `Point = [x, y]`, `Path = [[x, y, ms], …]`, all in document CSS px.
  - `meanColour(context, png, rect, shotY) -> Promise<[r, g, b]>`: decodes the PNG in a new blank page with `createImageBitmap` and `OffscreenCanvas`, and averages the pixels of `toViewport(rect, shotY)` × 3. `shotY` is `rects.shots[<png name>].y`.
- Produces in `capture/records.mjs` the film's Highlights and questions, which every later task uses:
  - `MARKS`, in this order:
    - `{scene: 'S01', passage: 'p00020', colour: 'key', quote: <the S01 sentence of spec 5.3>}`
    - `{scene: 'S04', passage: 'p00023', colour: 'disagree', quote: <S04 drag 1>, top: 16}`
    - `{scene: 'S04', passage: 'p00024', colour: 'use', quote: <S04 drag 2, which ends after "[3]">}`
    - `{scene: 'S04', passage: 'p00024', colour: 'question', quote: <S04 drag 3, which ends at "gradients", before the footnote link>, note: 'A guess, not a result. #attention', noteScene: 'S05'}`
  - `ASKS`:
    - `{scene: 'S06', passage: 'p00024', quote: <the S06 sentence>, question: 'Why does this scaling help?', take: 'q1', top: 100}`
    - `{scene: 'S09', passage: 'p00023', quote: <the S09 sentence>, question: 'Why does additive need no scaling?', take: 'q2', top: 16}`
  - Copy each quote in one-text form from the output of `textMap` (`onetext.js:19`). Do not retype it from the PDF.
  - `top` is the viewport y of the passage's top after `scrollToPassage`. At Charter 20, p00020 to p00024 are taller than the 900 px viewport. Tune `ASKS[0].top` so that the S06 sentence is about 250 px from the top and the finished card ends inside the viewport (Task 6 Step 2 asserts it). Tune `ASKS[1].top` so that the S09 words and the card's first answer show.
- Produces in `capture/flow.mjs`:
  - `scrollToPassage(page, passage, top)`: `window.scrollTo(0, <the passage's document top> − top)`, then a wait of 200 ms with no scroll, so the app holds the new top passage. A scroll hides every bar (`selection.js:12`) and drops a preview (`reader.js:497`), so call it only before a drag or a hover.
  - `mark(page, m, on = async () => {}, {drags = 0, beforePaint = async () => {}}) -> Promise<object>`. When `m.top` is set, it first calls `scrollToPassage`. It calls `findWords` and `drag` with `stops = Array.from({length: drags}, (_, i) => Math.round((i + 1) * 24 / (drags + 1)))` and `onStop` → `on('drag-<n>')`. It waits for `div.selbar[aria-label=Selection]` and calls `on('toolbar')`, then `beforePaint()`. It clicks `div.selbar[aria-label=Selection] button.swatch[data-colour=<colour>]` and calls `on('painted')`. The Highlight bar has swatches of the same class (`margin.js:389`), and the first Note leaves it in the page, hidden. It reads the saved Highlight from the response of `POST …/highlights/add` and throws `quote differs: <saved>` when its `quote` is not `m.quote`. When `m.note` is set, it clicks the painted words (no movement over 3 px, not on a link, `margin.js:377-386`) and waits for `div.selbar[aria-label=Highlight]` (`on('bar')`). Then it clicks `div.selbar[aria-label=Highlight] [aria-label="Add a Note"]` and waits for `textarea[aria-label=Note]` (`on('editor')`). It types one character at a time (`on('type-<nn>')`), clicks the editor's Save, and waits for the card's `p.lx-note-text` (`on('saved')`). It returns the rects of the words, the toolbar, each toolbar button, the bar, and the card.
- Produces `node capture/gates.mjs [--engine webkit]`. It prints one line for each check, `paint`, `margin`, and `harness`, each with `PASS` or `FAIL` and its numbers, and exits 1 on any `FAIL`. It saves `public/gates/paint-before.png`, `public/gates/paint.png`, and `public/gates/margin.png`.

- [ ] **Step 1: Write `capture_server.py`.**
- [ ] **Step 2: Check it** in `<wt>`. Start `CAPTURE_TOKEN=x .venv/bin/python tools/intro-video/capture_server.py "$(mktemp -d)"` in the background. It prints a port. `curl -s -H 'Authorization: Bearer x' http://127.0.0.1:<port>/api/state` must show `"has_key": false` and `"has_chat_key": false` in `.settings`. Stop the server. Run `.venv/bin/python tools/intro-video/capture_server.py --check`. Expected: `patches ok`.
- [ ] **Step 3: Write `capture/gates.mjs`.** Run it. Expected: FAIL, because `capture/app.mjs` does not exist yet.
  - **paint (Gate 1, spec 7.3 item 1):** Open the sample on p00020. Find the words of `MARKS[0]` and take `shot(page, 'gates/paint-before')` on plain paper. Run `mark` on `MARKS[0]`, move the mouse away, and take `shot(page, 'gates/paint')`. Compare `meanColour` of the first rect of the words in the two PNGs, each with its own `rects.shots[…].y`. It passes when the mean blue falls by 15 or more. The Light Key point tint is `rgba(255,200,0,.32)` (`app.css:27`), so it lowers blue.
  - **margin (Gate 2, spec 7.3 item 2):** Send `{name: 'prefs', patch: {font: 'charter'}}`, `{name: 'text-size', step: 1}` four times, and `{name: 'prefs', patch: {theme: 'sepia', margins: 'normal'}}` (`app.js:190-191`). Run `mark` on `MARKS[1..3]` (with the Note). Call `scrollToPassage(page, 'p00024', ASKS[0].top)`, drag the S06 sentence, and click `div.selbar[aria-label=Selection] [aria-label="Ask about the selected text"]`, so a draft Question card opens. Type nothing; no request goes. It passes when every `.lx-card` is 210 px wide or more (expected 300, `margin.js:19-20`), no `.is-marker` exists, and each card's top is 200 px or less below the top of its words. Print the widths and the offsets.
  - **harness:** (a) Send `{name: 'action', id: 'all-notes'}`. Then `command(page, {name: 'view', view: 'overview'})` must throw `/while a dialog is open/`. Press Escape. (b) Set the viewport to 1100×900 and send `{name: 'prefs', patch: {size: 36}}`. Then `shot(page, 'gates/fold')` must throw `/marker/`. Restore 1440×900 and `{name: 'prefs', patch: {size: 20}}`. (c) `api(app, '/api/state')` has `settings.has_key === false` and `settings.has_chat_key === false`, and `capture_server.py --check` prints `patches ok`.
- [ ] **Step 4: Write `capture/app.mjs`, `capture/records.mjs`, and `capture/flow.mjs`** with the interfaces above.
- [ ] **Step 5: Run** `node capture/gates.mjs`. Expected: `paint PASS`, `margin PASS`, `harness PASS`. Read `public/gates/paint.png` and `public/gates/margin.png`. Expected: the Key point tint on the sentence; Charter on Sepia; the Note card and the draft Question card beside their words; no toolbar, no sidebar, no Figure 2.
- [ ] **Step 6: If paint fails, stop and report to the owner.** Ask before the WebKit download, and show the command `npx playwright install webkit`. With a yes, run `node capture/gates.mjs --engine webkit`. If paint fails again, stop and ask the owner about a native run (spec 7.3, Section 10). Do not run `tools/native_shot.py` without that yes.
- [ ] **Step 7: If margin fails, stop and report** the widths and the offsets to the owner.
- [ ] **Step 8: Run** `uvx ruff check .` in `<wt>`. Expected: no problems.
- [ ] **Step 9: Commit** `capture_server.py`, `capture/app.mjs`, `capture/records.mjs`, `capture/flow.mjs`, and `capture/gates.mjs` with the message `Add the capture harness on window.localxiv.command and its first two gates`.

### Task 3: The take gate (option A)

**Files:**
- Create: `tools/intro-video/capture/chat.mjs`, `tools/intro-video/takes/q1.json`, `tools/intro-video/takes/q2.json`
- Modify: `tools/intro-video/capture.mjs` (a new script: `--record` and `--replay-check` now; the film capture comes in Tasks 5–7), `tools/intro-video/capture/flow.mjs` (`ask`, `addQuote`)

**Interfaces:**
- Consumes: `startApp`, `openBrowser`, `loadApp`, `openPaper`, `scrollToPassage`, `drag`, `mark`, `MARKS`, and `ASKS` from Task 2.
- Produces the take file `takes/<q>.json`:
  ```json
  {"question": "q1", "text": "Why does this scaling help?", "model": "granite4.1:8b",
   "server": "Ollama 0.40.8, OLLAMA_CONTEXT_LENGTH=16384", "recorded_at": 1792680000.123,
   "before": [{"request": {}, "status": 400, "body": "…"}],
   "request": {},
   "chunks": [{"ms": 1834, "data": "{\"choices\":[…]}"}, {"ms": 6120, "data": "[DONE]"}]}
  ```
  `recorded_at` is the Unix time in seconds when the streamed request arrived. `ms` counts from that moment. `before` holds the exchanges that the model server refused first, such as the HTTP 400 for `reasoning_effort` after which the app retries without the field (`papers/ai.py:61-64`, `papers/chat.py:218-225`). `request` is the parsed JSON body.
- Produces in `capture/chat.mjs`:
  - `startChat({upstream = null, takes = [], record = null}) -> Promise<{close(), written(): Promise<Chunk | null>, release(), candidates: Take[]}>` on `127.0.0.1:11434`. `takes` holds parsed take objects. `record` is `{name: 'q1' | 'q2', text: ASKS[i].question, server: 'Ollama 0.40.8, OLLAMA_CONTEXT_LENGTH=16384'}`. It throws when the port is in use. It serves requests in order:
    - **Replay.** While a take has exchanges left, the incoming body must equal the next recorded request (`before[i].request`, then `request`) as `JSON.stringify(JSON.parse(body))`. On a difference, it answers 500 with `{"error": {"message": "capture: request differs from take <q>"}}`, prints the first path that differs, and rejects `written()`. A `before` exchange gets its recorded status and body. The stream calls `res.writeHead(200, {'Content-Type': 'text/event-stream'})` and writes `data: <data>\n\n` for chunk n only after `release()` for chunk n−1. It calls `res.end()` after `[DONE]`. `written()` resolves `{take, index, ms, data, content}` after each write, where `content` is the joined `choices[].delta.content`, and resolves `null` after `[DONE]` and the close.
    - **Record.** After the takes, with `upstream`, it forwards the method, the path, the headers (without `host`), and the body. It passes a refusal through and keeps it in `before`. It passes a 200 stream through line by line and saves each `data:` line with its `ms`. On `[DONE]`, it writes `public/candidates/<record.name>-<YYYYMMDD-HHMMSS>.json` with `question: record.name`, `text: record.text`, `server: record.server`, `model` from the request, and `recorded_at` from the arrival of the streamed request.
    - With no take left and no `upstream`, it answers 500.
  - `judgeTake(take) -> {ok, words, cites, seconds, reasons}`. Reasons:
    - no `[DONE]`;
    - a `finish_reason` of `length` or `error`;
    - no citation that matches `/\[p\d+(?:\s*[,;]\s*p\d+)*\]/` (the client form, `render.js:184`);
    - a cited ID that is not in `ch004` (`sample.json` `href`), that is `p00025` (Figure 2), or that is not in the request's `<paper>` block;
    - fewer than 40 or more than 70 words, without the citations;
    - any `$` or `\`, because TeX stays raw while the answer streams (`chat.js:57`).
    `seconds` is the time from the first chunk with content to the last one.
  - `node capture/chat.mjs judge <file>…` prints one line for each file: `<file> ok|NO words=<n> cites=<ids> seconds=<s> <reasons>`. `node capture/chat.mjs --self-test` judges five takes that it builds in memory.
- Produces in `capture/flow.mjs`:
  - `ask(page, a, chat, on, {clock, take, drags = 6})`. It replays when `take` is given and records when it is not. When `a.top` is set, it first calls `scrollToPassage`. It drags `a.quote` (`on('drag-<n>')`, as `mark` does) and calls `on('toolbar')`. It hovers the gap between the swatches and Note (`on('rest')`), hovers Ask (`on('ask-hover')`), and clicks `div.selbar[aria-label=Selection] [aria-label="Ask about the selected text"]` (`on('card')`). When `clock` and `take` are both given, it writes `take.recorded_at` to `clock`. It types the question (`on('type-<nn>')`) and presses Enter. It reads the app's `POST …/chat` and throws `quote differs: <sent>` when `anchor.quote` is not `a.quote` (`chat.js:243-245`). It waits for "Reading the Paper…" (`on('pending')`). When it replays, it runs the stream loop. For each `written()` chunk with content, it waits until the HTML of `.lx-turn.is-pending .lx-answer` changes (3 s at most), waits two animation frames, calls `on('stream', chunk)`, and calls `release()`. It releases a chunk with no content at once. When it records, it releases nothing. At the end, it waits until the card has no `.lx-turn.is-pending` and has n `.lx-turn` elements, where n is the turn number (1 for q1, 2 for q2). Then it calls `on('done')`. Map: the finished q1 turn already matches `.lx-turn:not(.is-pending)` while q2 streams (`chat.js:20-29,63`).
  - `addQuote(page, a, chat, on, {clock, take, drags = 6})`. When `a.top` is set, it first calls `scrollToPassage`. It calls `on('before')` and clicks `.lx-quotes > button.btn-quiet` "Add Quote" (`on('notice')`). It drags `a.quote`, waits for `[aria-label="Add the selected text to the question"]` (`on('toolbar')`), and clicks it (`on('quote')`). Then it types, sends, and streams as `ask` does. It checks the last entry of `quotes` in the Chat request, not `anchor`.
- Produces `node capture.mjs --record q1|q2`. It runs `startChat({upstream: 'http://127.0.0.1:11435', takes: q2 ? [<takes/q1.json, parsed>] : [], record: <q1 or q2>})`, then `startApp` with no clock, `loadApp`, and `openPaper`. It runs `mark` for each of `MARKS`. For q1, it runs `ask(page, ASKS[0], chat, noop, {})`. For q2, it runs `ask(page, ASKS[0], chat, noop, {take: q1})` and then `addQuote(page, ASKS[1], chat, noop, {})`. It takes no screenshot.
- Produces `node capture.mjs --replay-check [--takes <dir>]` (default `takes/`). It runs the flow of `--record q2` with `startApp({clock: 'public/clock.txt'})` and no `upstream`, and it replays q1 and q2 with `{clock: app.clock, take}`. It takes no screenshot, and prints each `p.lx-meta`. It asserts that each line has the take's model, ` · this Mac · `, and the date of `recorded_at` as `toLocaleDateString('en-US', {day: 'numeric', month: 'short', year: 'numeric'})`. It prints `replay PASS` or exits 1.

- [ ] **Step 1: Ask the owner first.** Show this and wait for a clear yes:
  - Server: Ollama 0.40.8, binary only, `brew install --cask ollama-binary` (about 166 MB). No app, and nothing starts on its own on port 11434. Never Ollama.app, never `brew services`.
  - Model: `granite4.1:8b` (Q4_K_M, about 5.3 GB) by `ollama pull granite4.1:8b`. Memory: about 8.5 GB at a 16k context, inside the about 10.7 GB that the GPU of this 16 GB Mac can use.
  - Command: `OLLAMA_HOST=127.0.0.1:11435 OLLAMA_CONTEXT_LENGTH=16384 OLLAMA_KEEP_ALIVE=-1 OLLAMA_NO_CLOUD=1 ollama serve`.
  - The app's Context size is 16384, so the whole Paper goes with `max_tokens` 4096. Map: the Local preset starts at 4096 (`app.js:34`), which sends only an excerpt.
  On a no, stop and report.
- [ ] **Step 2: Install.** Run the install command. Expected: `ollama --version` prints 0.40.8.
- [ ] **Step 3: Serve.** Run the serve command in the background.
- [ ] **Step 4: Pull.** In a second shell, `export OLLAMA_HOST=127.0.0.1:11435` and `ollama pull granite4.1:8b`.
- [ ] **Step 5: Verify the server.**
  - `curl -s http://127.0.0.1:11435/api/show -d '{"model":"granite4.1:8b"}'`. Print its `capabilities`.
  - `curl -sN http://127.0.0.1:11435/v1/chat/completions -H 'Content-Type: application/json' -d '{"model":"granite4.1:8b","messages":[{"role":"user","content":"Say hi."}],"stream":true,"stream_options":{"include_usage":true}}'`. Expected: `data:` lines with `delta.content`, a usage chunk, and `data: [DONE]`.
  - `ollama ps`. Expected: CONTEXT `16384` and PROCESSOR `100% GPU`.
- [ ] **Step 6: Write the failing check.** Write `node capture/chat.mjs --self-test` with five takes built in memory: a good take (a `[p00024]` citation, 50 words), the same take with no citation, a take that cites `[p00025]`, a take that cites a `ch009` ID from `sample.json`, and a take with `$d_k$`. Run it. Expected: FAIL, because `judgeTake` does not exist yet.
- [ ] **Step 7: Implement `capture/chat.mjs`.** Run `node capture/chat.mjs --self-test`. Expected: `5 of 5` (the good take is `ok`; the others have the reasons `no citation`, `figure`, `not in ch004`, and `raw TeX`).
- [ ] **Step 8: Implement** `ask` and `addQuote` in `capture/flow.mjs`, and `capture.mjs` with `--record` and `--replay-check`.
- [ ] **Step 9: Check the port.** `lsof -nP -iTCP:11434 -sTCP:LISTEN` prints nothing.
- [ ] **Step 10: Record q1** with `node capture.mjs --record q1`, 3 to 5 times.
- [ ] **Step 11: Choose q1.** Judge with `node capture/chat.mjs judge public/candidates/q1-*.json`. Choose an `ok` take. Prefer `seconds` of 4.2 or less, which is the S06 window. Copy it to `takes/q1.json`.
- [ ] **Step 12: If no q1 take is `ok` after 5 runs, stop and ask the owner.** Offer two ways, and wait for the answer:
  - (a) The fallback model: `brew install llama.cpp` and `unsloth/Qwen3.5-4B-GGUF:Q4_K_M` (about 2.8 GB). Serve it with `llama-server -hf unsloth/Qwen3.5-4B-GGUF:Q4_K_M -c 32768 -np 1 --port 11435 --reasoning-budget 0`. Set Context size 32768 and the model name in `SETTINGS`.
  - (b) Option D: the owner's key, with a billed call per take. It needs a plan change (spec 7.5).
- [ ] **Step 13: Record q2** with `node capture.mjs --record q2`, 3 to 5 times. The stub replays `takes/q1.json` first. Judge the candidates and copy the chosen one to `takes/q2.json`.
- [ ] **Step 14: Check the replay** (Review Focus 5):
  - `node capture.mjs --replay-check`. Expected: `replay PASS` with today's date.
  - Copy both takes to `public/check-takes/` and set their `recorded_at` to `1790856000` (2026-10-01 12:00 UTC). Run `node capture.mjs --replay-check --takes public/check-takes`. Expected: `replay PASS`, and each line shows `Oct 1, 2026`.
  - In the copy of q1, change one character of the question in `request`. Run the same command. Expected: exit 1 with `request differs from take q1`.
- [ ] **Step 15: Keep the model server running** until Task 6 Step 6. Task 6 Step 5 is the first film replay. If it stops with `request differs`, find the cause and record the takes again.
- [ ] **Step 16: Commit** `capture/chat.mjs`, `capture/flow.mjs`, `capture.mjs`, `takes/q1.json`, and `takes/q2.json` with the message `Record two Chat takes from a model on this Mac and replay them chunk by chunk`.

## Part 2: The timeline and its check

### Task 4: The beat grids and `check.mjs`

**Files:**
- Modify: `tools/intro-video/src/timeline.mjs`, `tools/intro-video/package.json` (scripts)
- Create: `tools/intro-video/check.mjs`

**Interfaces:**
- Produces in `src/timeline.mjs`: `BPM = 120`, `FPS = 60`, `BEAT = 30`, `frames(seconds) -> number` (`Math.round(seconds * 60)`), and `grid(def) -> Grid`. `grid` adds `start` (scene id to its first beat), `total` (beats), `at(scene, beats) -> frame` on the grid, and `local(scene, seconds) -> frame` from the scene's start. Exports `MASTER`, `CUT`, `CLIP_END`, `CLIP_CARDS`, `TEXTS`, and `zoomsFor`. Keep each grid's `def`, so that `check.mjs` can mutate it and call `grid` again.
- `zoomsFor(grid, first, last = first) -> [frame, zoom, move][]`: the zoom keys from the start of scene `first` to the end of scene `last`, plus the key in effect at that start as a key at frame 0. `frame` counts from the start of `first`, and `move` is in frames (0.5 s is 30). Every scene and shared shot takes its zoom keys from it, and adds the `x` and `y` of each key from its own rects to make the `cameraAt` keys (Task 8).
- `TEXTS`: every on-screen string that is not a card or a label: the strip verbs, the hero line, and the end-card lines. `Captions`, S14, and `EndCard` read them from here.
- `CLIP_CARDS` (Decision 15): the `MASTER` cards that show inside 17.0–29.0 s, with "Notes sit beside the words." full from 27.1 to 28.85 s.
- The shape of `def`:
  - `scenes: [{id, beats}]`.
  - `cues: {[scene]: {[name]: number | number[] | number[][] | [number, string][]}}`, in beats from the scene's start. A cue named `stream` is a stream window. Its wait dip starts 2 frames before the window (Task 8), so no cue names the dip.
  - `cards: [{scene, lines: string[], full: [s, s], top?: true, name?: true, build?: [[text, s]]}]`, in seconds on the film.
  - `labels: [{text, colour, full: [s, s]}]`, `strip: [{verbs, from, to}]`, and `zooms: [{at, zoom, move}]`, in seconds on the film. `move: 0` is a cut.
  - `end: {scene, cues}`: the end card, which is the `center` text zone.
- `MASTER.scenes`: S01 13, S02 12, S03 9, S04 14, S05 10, S06 29, S07 12, S08 10, S09 15, S10 7, S11 9, S12 10, S13 8, S14 8, S15 14. `CUT.scenes`: K1 5, K2 16, K3 11, K4 8, K5 10. Spec 7.1.
- `MASTER.cues`. Check each value against the `b` numbers of spec 5.2 (beat = scene start + cue):

  | Scene | Cues |
  | --- | --- |
  | S01 | `drag: [-0.5, 1.2]`, `toolbar: 1.2`, `toAsk: [1.5, 2.7]`, `toKey: [4.5, 5.7]`, `key: 6` |
  | S02 | `font: 1`, `size: [3, 3.5, 4, 4.5]`, `theme: 6` |
  | S03 | `pan: [0, 1]`, `toCite: [1, 2.2]`, `preview: 2.9`, `leave: 7.6`, `close: 8.7` |
  | S04 | `drags: [[1, 2.4], [3.8, 5.2], [6.8, 8.4]]`, `toolbars: [2.6, 5.4, 8.6]`, `clicks: [3, 6, 9]` |
  | S05 | `toWords: [0, 0.8]`, `bar: 1`, `note: 2`, `type: [3.4, 7]`, `save: 8` |
  | S06 | `drag: [0.6, 2.2]`, `toolbar: 2.6`, `toGap: [2.8, 3.8]`, `toAsk: [7, 7.5]`, `ask: 8`, `type: [10, 13.2]`, `enter: 14`, `stream: [15.6, 24]` |
  | S07 | `toCitation: [0, 1]`, `preview: 1.7`, `click: 5`, `back: 8` |
  | S08 | `steps: [[2, 'openai'], [3, 'openrouter'], [4, 'deepseek'], [5, 'gemini'], [6, 'anthropic'], [7, 'local']]` |
  | S09 | `addQuote: 1`, `drag: [1.6, 3.6]`, `toolbar: 3.8`, `add: 4`, `type: [5.4, 9.2]`, `enter: 10`, `stream: [11.6, 15]` |
  | S10 | `blog: 3.5` |
  | S11 | `open: 1`, `colour: 4`, `close: 8` |
  | S12 | `tag: 3` |
  | S13 | `chapter: 2`, `dialog: 4` |
  | S14 | `pull: [0, 3.6]`, `verbs: 3.2`, `gather: [4, 5]` |
  | S15 | `panelOut: [0, 0.6]`, `verbs: 0`, `icon: 0`, `wordmark: 0.8`, `pills: 2`, `platform: 3`, `url: 4`, `dim: 8`, `linux: 9` |

- `CUT.cues`: K1 `{drag: [-1, 1], toolbar: 1.4, toGap: [1.6, 2.4], toAsk: [4.5, 5]}`; K2 `{ask: 0, type: [1.4, 4.6], enter: 5, stream: [6.6, 15]}`; K3 `{toCitation: [0, 0.8], preview: 1.5, click: 5, back: 8}`; K4 `{steps: [[2, 'anthropic'], [4, 'local']]}`; K5 `{icon: 0, wordmark: 0, verbs: 0.6, pills: 1.2, url: 2, dim: 4.6, linux: 5.2}`. `CLIP_END` (the 3 s end card of the thread clips, 6 beats): `{icon: 0, wordmark: 0, url: 0.6, dim: 2.4, linux: 2.6}`.
- `MASTER.cards`: the 19 cards of the Cards column of spec 5.2, with the times of spec 5.3. The S01 name card has `name: true`. The S02 card has `build: [['Your font.', 7.0], ['Your size.', 8.0], ['Your theme.', 9.5]]`. `CUT.cards`: K1 to K4 of spec 6.1.
- `MASTER.labels`: Disagree from 18.8, Use in my work from 20.3, Question from 21.8, all until 23.6 (spec 5.3 S04). `MASTER.strip`: `[1, 6.5, 9.65]`, `[2, 17.0, 20.15]`, `[3, 33.0, 36.15]`, `[4, 65.5, 68.65]`, `[4, 80.6, 81.0]`.
- `MASTER.zooms` (`at`, `zoom`, `move`):
  - S01: (0, 2.2, 0), (3.2, 1.5, 0.5)
  - S02: (10.5, 1.2, 0.5)
  - S03: (13.6, 2.0, 0.45), (16.6, 1.4, 0.5)
  - S05: (24.5, 2.0, 0.45), (28.3, 1.5, 0.5)
  - S06: (33.1, 2.2, 0.5), (41.5, 1.5, 0.5)
  - S07: (44.5, 2.0, 0.45), (47.9, 2.2, 0.5)
  - S08: (49.5, 1.6, 0)
  - S09: (54.5, 1.6, 0), (56.6, 2.0, 0.5)
  - S10: (62.0, 1.0, 0), (62.0, 1.08, 1.75), (63.75, 1.0, 0)
  - S11: (65.5, 1.2, 0), (66.4, 1.4, 0.5)
  - S12: (70.0, 1.2, 0), (71.6, 1.4, 0.5)
  - S13: (75.0, 1.0, 0), (77.0, 1.3, 0)
  - S14: (79.0, 2.0, 0), (79.0, 0.75, 1.8)
  
  `CUT.zooms`: (0, 1.5, 0), (2.6, 2.2, 0.5), (16.0, 1.6, 0). K3 has no key: it holds 2.2x, and its camera moves are pans.
- Produces `check.mjs` with `check(grid, name)`. It throws an `AssertionError` whose message names the rule:
  - `scenes`: the ids and their order; 180 beats for MASTER and 50 for CUT.
  - `cue`: every cue number n is in [−2, beats of its scene].
  - `hold`: `full[1] − full[0] ≥ max(1.2, 0.35 × words) − 1e-9`; at most 2 lines and 42 characters a line; at most 6 words, except a name card. It also runs on `CLIP_CARDS`, and each of them exits by 29.0 s.
  - `words`: the never-words of the Global Constraints, as `\b` patterns, match no card line, label, or `TEXTS` entry.
  - `zoom`: no zoom above 2.2. The starts (`at`) of two moves (`move > 0`) that follow each other are 3.0 s apart or more.
  - `stream`: no card is visible during a `stream` cue. A card is visible from `full[0] − 0.2` (or from `build[0][1] − 0.2`) to `full[1] + 0.15`; a label is visible for the same span.
  - `zones`: at each frame, at most two of `card`, `strip`, `labels`, and `center` are visible. `center` starts at S14 `gather` and at the start of K5.
  It prints `MASTER ok: 180 beats, 19 cards, 25 zoom keys` and `CUT ok: 50 beats, 4 cards`. `--self-test` mutates copies of `MASTER.def`. Each copy must throw its rule:
  1. "So far, no AI." full for 1.0 s → `hold`
  2. S07's 44.5 move at 44.4 → `zoom`
  3. "A Question card, beside the words." full from 40.9 → `stream`
  4. a label during S06's strip and card → `zones`
  5. S06 at 28 beats → `scenes`
  6. a zoom of 2.3 → `zoom`
  7. S06 `stream` written in seconds, `[36.8, 41.0]` → `cue`
  It prints `7 of 7 bad timelines rejected`.
- `package.json` scripts: `"check": "node check.mjs && node check.mjs --self-test"`. `render` starts with `npm run check &&`.

- [ ] **Step 1: Write `check.mjs`** with the rules and the self-test.
- [ ] **Step 2: Run** `node check.mjs`. Expected: FAIL, `timeline.mjs exports no MASTER grid` (the old 88-beat file).
- [ ] **Step 3: Write `src/timeline.mjs`** with the grids above. From here, the old scenes and the old `music.mjs` do not run. Tasks 8 to 12 replace them.
- [ ] **Step 4: Run** `node check.mjs` and `node check.mjs --self-test`. Expected: the two `ok` lines, then `7 of 7 bad timelines rejected`.
- [ ] **Step 5: Change the scripts** in `package.json`. Run `npm run check`. Expected: the same three lines.
- [ ] **Step 6: Commit** `src/timeline.mjs`, `check.mjs`, and `package.json` with the message `Put the 180-beat film and the 50-beat cutdown on one checked beat grid`.

## Part 3: Captures, components, scenes, music, and compositions

The checks of a visual task are stills. Render one with `npx remotion still src/index.jsx <composition> <out.png> --frame=<n>` and read the PNG. Frame n = seconds × 60. In every look step, also check that no card covers the cursor's target (spec 4.2).

### Task 5: Capture the Read and Mark acts (S01–S05)

**Files:**
- Modify: `tools/intro-video/capture.mjs` (film mode and `--until <scene>`)

**Interfaces:**
- Consumes: `startApp`, `openBrowser`, `loadApp`, `command`, `openPaper`, `hoverOn`, `shot`, `rects`, `mark`, and `MARKS` (Task 2); `startChat`, `ask`, `addQuote`, and the two takes (Task 3).
- Produces `node capture.mjs [--until <scene>]`, the film capture. It reads `takes/q1.json` and `takes/q2.json`, runs `startChat({takes: [q1, q2]})` and `startApp({model: q1.model, clock: 'public/clock.txt'})`, and passes `app.clock` to `ask` and `addQuote`. It goes through the scenes in this order: setup (Task 7), S01–S07, S09, S14, S10, S11, S13, S12, S08. S08 is last, because each change in the Chat pane of Settings writes `chat_endpoint` at once (`app.js:851-855`). It ends with `saveRects()`. `on(state)` writes `public/<scene>/<state>.png`.
- States (spec 7.3) and rects:
  - **S01:** `drag-1`…`drag-8`, `toolbar`, `ask-hover`, `painted`, from `mark(page, MARKS[0], on, {drags: 8, beforePaint})`. `beforePaint` hovers `div.selbar[aria-label=Selection] [aria-label="Ask about the selected text"]` with `hoverOn` and calls `on('ask-hover')`; it never clicks Ask. Rects: `words`, `drag` (the path), `toolbar`, and the buttons `key`, `note`, `ask`, `explain`, `copy`.
  - **S02:** `charter16`, `charter17`, `charter18`, `charter19`, `charter20`, `sepia`, after `{name: 'prefs', patch: {font: 'charter'}}`, `{name: 'text-size', step: 1}` × 4, and `{name: 'prefs', patch: {theme: 'sepia'}}`. `S01/painted` is the SF Pro 16 Light state. Rects `anchor` (the rect of `#p00020`) and `words` (the first rect of the Key point words) in each state. The app holds the passage at its viewport height by a scroll (`reader.js:404-407`), so its document y grows as the lines above it rewrap. Assert that `anchor.y − rects.shots['S02/<state>'].y` is the same within 1 px in all six states, and print it. `openPaper` armed the hold, and nothing may scroll between S01 and S02. Spec S02 says the sentence stays at the same height; it moves down a little as the lines above it rewrap, and the S02 camera locks on the passage top. Map: nothing draws an "(1)" label on the equation in p00022; it stays typeset.
  - **S03:** `base`, `preview`. Hover `#p00023 span.citation[data-cites="bahdanau2014neural"] a` with `hoverOn` and no selection. Wait for `div.pop.preview[aria-label="Reference 2"]`, not only 350 ms, because the first preview also loads ch009 (`reader.js:537-543`). Rects: `cite`, `preview`. Never hover `a[data-reference-type="ref"]` or `#p00024 a.footnote-ref`.
  - **S04:** for each of the three Highlights, `m<k>-drag-1`…`m<k>-drag-4`, `m<k>-toolbar`, `m<k>-painted`, from `mark(…, {drags: 4})`. `MARKS[1].top` scrolls p00023 to the top before the first drag. Rects: `m<k>.words`, `m<k>.toolbar`, `m<k>.swatch`.
  - **S05:** `bar`, `editor`, `type-01`…`type-33`, `saved`. Rects: `bar`, `noteButton`, `card`, `save`.
- `--until S05` stops after S05 and still writes `rects.json`.

- [ ] **Step 1: Implement** film mode and the S01–S05 states in `capture.mjs`. Use `MARKS` with an `on` that maps each state to its scene (`noteScene` for the Note states).
- [ ] **Step 2: Run** `node capture.mjs --until S05`. Expected: exit 0, and the line `S02 anchor viewport y: <y> ×6 PASS`.
- [ ] **Step 3: Look** at these files in `public/`. `S01/drag-4.png`: a selection in progress. `S01/toolbar.png`: four swatches, Note, Ask, Explain, Copy. `S01/ask-hover.png`: Ask in its hover state. `S01/painted.png`: the Key point tint. `S02/sepia.png`: Charter 20 on Sepia. `S03/preview.png`: the entry for Bahdanau, Cho, and Bengio. `S04/m3-painted.png`: three colours. `S05/bar.png`: the name "Question" and the Question swatch pressed. `S05/saved.png`: the Note card beside its words. None shows a toolbar, a sidebar, or a figure.
- [ ] **Step 4: Commit** `capture.mjs` with the message `Capture the Read and Mark acts from real drags and commands`.

### Task 6: Capture the Ask act (S06, S07, S09, S14)

**Files:**
- Modify: `tools/intro-video/capture.mjs`, `tools/intro-video/capture/flow.mjs`, `tools/intro-video/src/timeline.mjs` (the S14 key of `MASTER.zooms`, only if Step 4 lowers it)

**Interfaces:**
- Consumes: the film capture of Task 5, `ask` and `addQuote` (Task 3), and `ASKS`.
- Produces these states:
  - **S06:** `drag-1`…`drag-6`, `toolbar`, `rest`, `ask-hover`, `card`, `type-01`…`type-27`, `pending`, the stream, and `done`. The stream writes `public/takes/q1/<nnn>.png` and `public/takes/q1/frames.json` as `[{ms, file}]`, where `ms` is the chunk's recorded time. The last entry is `{ms: <the [DONE] chunk's ms>, file: 'S06/done'}`, so `streamFrames` places the finished card at its recorded time. Rects: `words`, `gap`, `ask`, `card`, `field`, `answer`, `meta`, and `done` (the card at `done`).
  - **S07:** `preview`, `flash`, `after-flash`, `back`. Rects: `citation`, `preview`, `passage`, `meta`, and `thisMac` (the rect of the text ` · this Mac · ` in `p.lx-meta`, from a Range).
  - **S09:** `before`, `notice`, `drag-1`…`drag-6`, `toolbar`, `quote`, `type-01`…`type-34`, `pending`, the stream into `public/takes/q2/` (its `frames.json` ends with `S09/done`), and `done`. Rects: `addQuote`, `words`, `add`, `card`, `field`.
  - **S14:** `full`, one tall capture with `fullPage: true` and `clip` from 48 px above p00019 to 48 px below the lowest card. Each tile records its own clip in `rects.shots`. Rects: the words of each Highlight, each card, and `span` (the clip). Map: p00019 is in section 3.2, not 3.2.1 (spec 5.1, S14).

- [ ] **Step 1: Implement S06** with `ask(ASKS[0])`. Asserts at `card`: `p.lx-host` reads "Asks a model on this Mac (127.0.0.1). Answers can be wrong. Check the cited passages." (`chat.js:12,151-153`), and the field's placeholder is "Ask about these words". Map: a new Question card shows no quote; its words carry the `lx-question` paint with the dashed `lx-open` underline (`margin.js:290,641-642`).
- [ ] **Step 2: Assert at S06 `done`** (Review Focus 1): at least one `.lx-answer .cn .citation`, no `.unverified`, and `p.lx-meta` has `q1.model` and `this Mac`. The `done` card ends inside the 900 px viewport; if not, tune `ASKS[0].top`. Map: the line also ends with `Tokens: … cached, … new, … output` when usage is not zero (`chat.js:94-99`); keep it as the app draws it. The S07 push still centres on ` · this Mac · `.
- [ ] **Step 3: Implement S07 and S09.**
  - S07: Hover the first `.lx-card .lx-turn:not(.is-pending) .lx-answer .cn .citation:not(.is-earlier)`. Wait for `div.pop.preview`. Assert that its section name is not "References". Click the citation and take `flash` at once with `settle: false`. Assert that `.lx-flash` was still in the frame and that less than 900 ms passed since the click; if not, send `back` and try one more time. After 1.4 s, take `after-flash`. Send `{name: 'back'}`, then take `back`.
  - S09: Run `addQuote(ASKS[1])`. Assert the notice text "Select the words in the Paper, then choose Add to Question. Press Escape to cancel." (`margin.js:428`). Map: after the first turn, the field's placeholder is "Ask a follow-up", and the host line keeps only its first sentence (`chat.js:146-153`).
- [ ] **Step 4: Implement S14.** After q2 is `done`, press Escape and move the mouse to an empty part of the page. Assert the real Gate 2 with two turns (Review Focus 3): every card is 210 px wide or more, no `.is-marker`, and each card's top is 200 px or less below its words. Print `S14 span: <h> CSS px, <3h> device px, end zoom <z>` with `z = min(0.75, 810 / (h + 96))`. If `3h` is more than 16,384, take the capture in tiles of 5,400 CSS px or less (`full-1`, `full-2`, …). If `z` is below 0.75, write it into the S14 zoom key of `MASTER.zooms`.
- [ ] **Step 5: Run** `node capture.mjs --until S14`. Expected: exit 0 and the span line.
- [ ] **Step 6: Stop the model server.** The replay now works, and the film capture needs only the takes. Tell the owner that Ollama and the model stay installed, and that `ollama rm granite4.1:8b` frees about 5.3 GB.
- [ ] **Step 7: Look** at `S06/rest.png` (no hover, toolbar open), `S06/card.png`, a middle frame of `takes/q1/`, `S06/done.png` (citations and the provenance line), `S07/preview.png`, `S07/flash.png`, `S07/back.png`, `S09/quote.png`, and `S14/full.png`. In `S14/full.png`, every Highlight and card is beside its words, and Figure 2 is not there.
- [ ] **Step 8: Commit** `capture.mjs`, `capture/flow.mjs`, and `src/timeline.mjs` (if Step 4 changed the zoom) with the message `Capture the Ask act from the replayed takes`.

### Task 7: Capture the Keep act (S10–S13), two more Papers, and S08

**Files:**
- Modify: `tools/intro-video/capture.mjs`, `tools/intro-video/capture/records.mjs` (`EXTRA`)

**Interfaces:**
- Consumes: the film capture of Tasks 5 and 6, `api`, `mark`, and `scrollToPassage` (Task 2).
- Produces in `records.mjs`: `EXTRA = [{id, title, authors, licence, passage, quote, colour, note}]` for two Papers.
  - Choose them from `/Users/silver/Developer/LocalXiv/.verification/parser-corpus/inputs`: papers about attention or Transformers whose arXiv abstract page links `creativecommons.org/licenses/by/4.0/`, and which open as reflowed text in a trial import.
  - The first Note ends with `#attention`. The second Note ends with another tag, so the S12 toggle removes its row.
  - Each Note is at most 8 words, in the reader's voice, and true about its quoted words.
- Produces the setup, which runs before the page loads. Assert `settings.auto_send === false`, because each finished import queues a send when it is true (`server.py:510-511`). `POST /api/import {url: <id>}` for each Paper. Poll `GET /api/state` until both jobs are `ready` (10 minutes at most). After load and before S01, open each Paper and run `mark` with its Note. Then `openPaper` the sample. A Chat request carries only the Highlights of the open Paper (`server.py:320`), so these Notes do not change it. The strict replay proves this on the first film run.
- Produces these states:
  - **S10:** `overview`, `blog` (`view` `overview`, then `blog`). Map: the `has_key`/`model: 'demo'` rewrite of spec 7.2 is not needed. A saved generation shows whatever the key (`reader.js:37`), and the Blog's model line comes from the generation (`reader.js:803-806`). The capture has no route rewrite.
  - **S11:** `base`, `position`, `colour`. S10 left the Blog open, and All Notes opens over any view (`app.js:493`). So send `{name: 'view', view: 'paper'}` and call `scrollToPassage` so that the four colours and both cards show. Take `base`. Send `{name: 'action', id: 'all-notes'}`. If the pressed `.segs button` is not `position`, click Position. Take `position`. Then click `.segs button[data-value=colour]` and take `colour`. Rects: `dialog`, `rows`. Task 11 crops the dialog from `S11/position` over `S11/base`. Press Escape. Map: All Notes has no close animation (`app.css:622,627`), so the film cuts on the close.
  - **S13:** `epub-page`, `epub-notes`, `kindle`.
    - Send `{name: 'action', id: 'export-epub-notes'}`. The action runs only in the Paper view of a Paper with Highlights (`app.js:454,478`). Poll `/api/state` until the export job is `ready`. Fetch `result.download_url` with `?token=` into `public/S13/paper-notes.epub`. Run `/usr/bin/unzip -q -o public/S13/paper-notes.epub -d public/S13/epub`.
    - In a new page (viewport 720×780), open `file://…/EPUB/text/ch004.xhtml`. Add `figure,table{display:none}`. Scroll `mark.lx-question` to 30% of the height, and take `epub-page`. Open `EPUB/notes.xhtml` and take `epub-notes`. These two shots are 720 px wide, and Task 11 draws them in a panel at that width, not under the document camera.
    - Wait until the job list stops changing, because the app opens the Paper again (`app.js:1132`). Send `action` `{id: 'send-kindle'}`. Click `#kindle-notes`. Map: it is not checked by default (`index.html:104`). Assert that `#kindle-destination` reads "To your-name@kindle.com" and that the box is checked. Move the mouse away from `#send`, take `kindle`, and press Escape.
  - **S12:** `all`, `attention`. Send `{name: 'go', to: 'notes'}`. Assert two or more `div.an-part` groups. Click the `#notes-tags > button` whose text is `#attention`. Rects: `tag`, `rows`.
  - **S08:** `local`, `openai`, `openrouter`, `deepseek`, `gemini`, `anthropic`, `local-again`, on a second page `loadApp(context, app, '?panel=settings&pane=chat')`.
    - Assert `#chat-provider-preset` is `local`, `#chat-model` is `q1.model`, and `#chat-key-status` ends with "A Local Chat model uses no key."
    - Use `selectOption` for each provider; an open select list does not paint headless. In each cloud state, assert that `#chat-api-key` is empty with the placeholder "Paste your API key".
    - Rects: `provider` (`label[for=chat-provider-preset]`), `keyLine`, `help`.
    - Map: the Model field keeps `q1.model` in every cloud state, because `changeProvider` does not touch it (`app.js:727-737`).

- [ ] **Step 1: Choose the two Papers.** Check each licence on its arXiv page and run a trial import in a temporary library. Write `EXTRA`.
- [ ] **Step 2: Implement** the setup and the S10–S13 and S08 states.
- [ ] **Step 3: Run** the whole capture, `node capture.mjs`. Expected: exit 0, the shot count, `public/rects.json`, and the temporary library removed.
- [ ] **Step 4: Look** at `S10/overview.png`, `S10/blog.png` (the line "Generated with <model>. AI text can contain errors." and its date), `S11/colour.png`, `S12/attention.png` (rows of two Papers), `S13/epub-page.png` (the Question Highlight and its number), `S13/epub-notes.png`, `S13/kindle.png`, `S08/local.png`, and `S08/anthropic.png`. No figure shows, no key shows, and no e-mail address other than `your-name@kindle.com` shows.
- [ ] **Step 5: Commit** `capture.mjs` and `capture/records.mjs` with the message `Capture the Keep act, the Chat pane, and two CC BY Papers for the Notes page`.

### Task 8: The stage and the components

**Files:**
- Create: `tools/intro-video/src/colours.mjs`, `tools/intro-video/src/stream.mjs`, `tools/intro-video/src/Stream.jsx`, `tools/intro-video/src/Captions.jsx`, `tools/intro-video/src/scenes/S01.jsx`
- Modify: `tools/intro-video/src/brand.jsx`, `tools/intro-video/src/stage.jsx`, `tools/intro-video/src/Intro.jsx`, `tools/intro-video/src/index.jsx`, `tools/intro-video/check.mjs`, `tools/intro-video/package.json`, `tools/intro-video/package-lock.json`
- Delete: `tools/intro-video/src/scenes/{Title,Add,Library,Read,Overview,Blog,Kindle,Outro}.jsx`

**Interfaces:**
- `colours.mjs`: the palette of `brand.jsx:4` (`INK`, `MUTED`, `PAPER`, `PAGE`, `LINE`, `ACCENT`, `TINT`); `INKS = {key: '#8a6500', question: '#8a3fd1', use: '#b04a00', disagree: '#c0306f'}` (the Light inks, `app.css:27-28`; 5.2–5.6:1 on PAPER); and `contrast(fg, bg, alpha = 1) -> number` (WCAG, with `fg` blended over `bg` at `alpha`). `brand.jsx` imports them.
- `brand.jsx`: keep the fonts, `EASE_OUT`, `EASE_IN`, `EASE_IN_OUT`, `clamp`, `beats`, `Icon`, and `arc`. Remove `BACK` and `Caption`. `Background({kick = []})`: the glow pulses only inside the `kick` beat ranges (Task 12 passes them).
- `stage.jsx`: remove `Window`, `LAYOUTS`, `ORDER`, `MOVE`, `pose`, `mix`, `EXIT`, `toStage`, and `BAR`.
  - `cameraAt(keys, frame) -> {x, y, zoom}`. Keys are `[frame, x, y, zoom, move = 27]`: `frame` is from the Sequence start, `x` and `y` are document px, and `move` is in frames (24–30, 105 for the S10 drift, or 108 for S14). The easing is `EASE_IN_OUT`, and the zoom blends geometrically as it does now (`stage.jsx:70`). A `move` of 0 is a cut: apply the key at its frame and never pass it to `interpolate`, which refuses an input range of equal values.
  - `Camera({cam, children})`: a 1920×1080 layer with `transformOrigin '0 0'`, `translate(960 − x·k, 540 − y·k)`, and `scale(k)`, with `k = zoom × 4/3`. At 1.0x this crops 60 stage px at the top and the bottom.
  - `contentToStage(cam, [x, y]) -> [sx, sy]` and `visibleRect(cam) -> Rect` (1440/zoom × 810/zoom document px).
  - `Shot({name, opacity = 1})`: draws `public/<name>.png` at `left: rects.shots[name].x`, `top: rects.shots[name].y`, and `width: rects.shots[name].width`, with radius 20 px and the shadow `0 24px 60px #1f281729`. The edges show only below 1.0x.
  - Keep `Crop`.
  - `Cursor({cam, track})`. `track` is a list of `{from, to, move: [a, b, lift] | path: Path | press: true | ibeam: bool}` in frames. It is drawn in stage space at a constant 44 px height (the 34×44 arrow, now at `Add.jsx:44-47`), with an I-beam over text. Moves use `arc` with `EASE_IN_OUT`. A drag follows its recorded path, retimed to its cue. A press scales the cursor to 0.94 for 6 frames and grows one 2 px ring from 0.6 to 1.4 in 18 frames. The cursor hides after 36 idle frames.
  - `Dip({at})`: a PAGE layer at opacity 0.5, 1, 1, 0.5 on frames `at` to `at + 3`. The new content shows from the third frame, `at + SWAP` (`stream.mjs`).
- `Captions.jsx`: `Card({lines, full, top, name, build})`, `Strip({verbs, from, to})`, `Label({text, colour, full, anchor})`, and `Captions({grid, cards = grid.cards})`, which draws each card of `cards` and each strip entry of the grid. A React context `TextOn` hides all three for the Poster stills.
  - Card: the Card surface of spec 4.2 and the type, place, and hold of the Global Constraints. Enter 12 frames, exit 9 frames. `top` puts it in the top band. `name` puts the static `Icon` at 72 px before "LocalXiv" (spec 4.2).
  - Strip: the `TEXTS` verbs up to `verbs`, at 64 px, x 115, top 65, on the Card's PAPER scrim. The current verb is ACCENT; earlier verbs are INK at 70% (Decision 14).
  - Label: 56 px in `INKS[colour]` on a PAPER slip in the left gutter, with a 1.5 px leader to `anchor` (stage px).
- `stream.mjs`: `streamFrames(chunks, [start, end], {fps = 60, tail = true}) -> {shots: [{from, file}], dips: number[]}`. This is the one algorithm that the tests do not fix:
  ```js
  export const DIP = 4, SWAP = 2; // New content shows from the dip's third frame.
  export function streamFrames(chunks, [start, end], {fps = 60, tail = true} = {}) {
    const t0 = chunks[0].ms, at = c => Math.round((c.ms - t0) * fps / 1000);
    const length = at(chunks.at(-1)), room = end - start;
    if (length <= room || !tail)
      return {shots: chunks.filter(c => at(c) <= room).map(c => ({from: start + at(c), file: c.file})), dips: []};
    // Too long: play the head, dip, then play the tail at the same speed, so the last chunk lands on `end`.
    const head = Math.floor((room - DIP) / 2), land = start + head + SWAP, cut = length - (end - land);
    const shots = chunks.filter(c => at(c) <= head).map(c => ({from: start + at(c), file: c.file}));
    shots.push({from: land, file: chunks.findLast(c => at(c) <= cut).file});
    for (const c of chunks) if (at(c) > cut) shots.push({from: land + at(c) - cut, file: c.file});
    return {shots, dips: [start + head]};
  }
  ```
- `Stream({frames, window, tail})` draws each shot from its `from` until the next one, and a `Dip` at each `dips` frame. It also draws the wait dip at `window[0] − SWAP`, so the first chunk lands on that dip's third frame.
- `check.mjs` adds the rules `contrast` and `streamFrames`:
  - `contrast`: INK/PAPER 14 or more; ACCENT/PAPER and PAPER on ACCENT (the URL pill) 4.5 or more; each `INKS` value on PAPER 4.5 or more; INK at 70% on PAGE and on PAPER (the end card and the strip) 4.5 or more.
  - `streamFrames` self-tests:
    - a 3 s take in a 252-frame window whose last entry is `done`: no dip, and `done` at `start + 180`;
    - a 6 s take with a chunk every 100 ms in a 252-frame window: one dip, every shot inside the window, the first shot after the dip at `dips[0] + SWAP`, the shots after it 6 frames apart, and the last shot at `end`;
    - the same take with `tail: false`: no dip and no shot after `end`.
- `index.jsx` registers `Intro` (1920×1080, 60 fps, 5,400 frames). `Intro({text = true, cards = MASTER.cards})` draws `Background`, one `Sequence` for each scene at `MASTER.at(id, 0)` (only S01 has content in this task), and `Captions` with `cards`.
- `S01.jsx` uses the S01 shots and rects, `MASTER.cues.S01`, and `zoomsFor(MASTER, 'S01')`. The camera starts at 2.2x with the words and the toolbar in the upper right two thirds and drifts 12 px a second.
- Remove `@remotion/transitions` with `npm uninstall @remotion/transitions`, because nothing imports it any more.

- [ ] **Step 1: Write the failing checks.** Add the `contrast` and `streamFrames` rules to `check.mjs`. Run `npm run check`. Expected: FAIL, because `src/colours.mjs` and `src/stream.mjs` do not exist.
- [ ] **Step 2: Implement** `colours.mjs` and `stream.mjs`. Run `npm run check`. Expected: the two `ok` lines, the contrast lines, `7 of 7 bad timelines rejected`, and `3 of 3 stream cases`.
- [ ] **Step 3: Remove the old stage.** Delete the eight old scenes with `git rm`, and run `npm uninstall @remotion/transitions`. Expected: `git status --short` shows the eight deletions, `package.json`, and `package-lock.json`.
- [ ] **Step 4: Implement** `brand.jsx`, `stage.jsx`, `Captions.jsx`, `Stream.jsx`, `S01.jsx`, `Intro.jsx`, and `index.jsx`.
- [ ] **Step 5: Look** at the stills of `Intro` at frames 0, 108, 186, and 240.
  - 0: mid-drag with the I-beam at 2.2x.
  - 108: the arrow on Ask in its hover state, and the card "AI waits until you ask." in the lower left.
  - 186: the Key point paint and the press ring.
  - 240: the name card at 1.5x, with the 72 px icon.
  None shows a window, a toolbar, or a sidebar.
- [ ] **Step 6: Commit** each file of this task by name, with the deletions, and the message `Replace the window stage with a full-bleed camera, cards, a stage-space cursor, and a stream player`.

### Task 9: Scenes S02–S05 (Read and Mark)

**Files:**
- Create: `tools/intro-video/src/scenes/S02.jsx`, `S03.jsx`, `S04.jsx`, `S05.jsx`
- Modify: `tools/intro-video/src/Intro.jsx`

**Interfaces:**
- Consumes: the S02–S05 shots and rects (Task 5), `MASTER` and `zoomsFor` (Task 4), and the components of Task 8.
- Each scene is `S0n = () => JSX`. It reads its shots, `rects[S0n]`, `MASTER.cues.S0n`, and `zoomsFor(MASTER, 'S0n')`. Spec 5.3 gives the content of each scene. The plan adds only these points:
  - **S02:** crossfades of 9 frames for the font and the size, and 15 frames for the theme. The card is built with `build`.
  - **S03:** the preview enters with opacity and a scale from 0.97 to 1 from the `cite` anchor in 10–12 frames, and leaves the same way at `close`.
  - **S04:** the three `Label`s, anchored at the left middle of the first rect of each Highlight. Pans take 24 frames.
  - **S05:** the bar and the editor enter like the S03 preview. One typing shot per character, spaced evenly across `type`.

- [ ] **Step 1: Implement** the four scenes and add them to `Intro`.
- [ ] **Step 2: Run** `npm run check`. Expected: PASS.
- [ ] **Step 3: Look** at frames 420, 510, 690 (S02); 900, 930 (S03); 1110, 1380 (S04); and 1560, 1734 (S05).
  - In 420 and 690, the top of p00020 is at the same height on the screen.
  - The labels are inside the left safe area and do not cover a Highlight.
- [ ] **Step 4: Commit** the four scenes and `Intro.jsx` with the message `Add the Read and Mark scenes`.

### Task 10: Scenes S06–S09 (Ask)

**Files:**
- Create: `tools/intro-video/src/scenes/S06.jsx` (exports `S06` and `AskShot`), `S07.jsx` (`S07`, `CitationShot`), `S08.jsx` (`S08`, `ChatModelShot`), `S09.jsx`
- Modify: `tools/intro-video/src/Intro.jsx`, `tools/intro-video/src/timeline.mjs` (the S06 and K2 keys, only if the `done` card does not fit at 2.2x)

**Interfaces:**
- Consumes: the S06–S09 shots, rects, and `frames.json` files (Task 6), the S08 shots (Task 7), `MASTER`, `CUT`, and `zoomsFor` (Task 4), and the components of Task 8.
- `AskShot({cues, zooms})` uses the S06 cue names. The master passes `MASTER.cues.S06` and `zoomsFor(MASTER, 'S06')`. The cutdown passes `{...CUT.cues.K1, ...shift(CUT.cues.K2, 5)}`, where `shift` adds 5 beats to every value, and `zoomsFor(CUT, 'K1', 'K2')`. `CitationShot({cues, zooms})` and `ChatModelShot({cues, zooms})` use the S07 and S08 names, and the zooms of S07 and S08, or of K3 and K4. The camera of a shared shot comes only from `zooms`.
- **S06:** no hover during the rest. The `Stream` uses `public/takes/q1/frames.json` with `window` from the `stream` cue and `tail: true`. Its last entry is `S06/done`, so the finished card shows at its recorded time, or at `end` after a tail cut. Frame the 33.1 s key (and the 2.6 s key of K2) on `rects.S06.done`, and assert that it fits `visibleRect` at that zoom. If it does not, lower the key in `MASTER.zooms` and `CUT.zooms` to the largest zoom at which it fits, so the camera stays still while the answer grows.
- **S07:** cut on the click to `flash`. Hold `flash` for 975 ms, then crossfade to `after-flash` in 225 ms with ease-out (Decision 4). Cut on `back`. The last zoom key centres on `rects.S07.thisMac`; in K3, which holds 2.2x, this is a pan.
- **S08:** a match cut from `thisMac` to the shots of the Chat pane of Settings, with hard cuts at each step. Assert that `visibleRect(cam).y` is at `rects.S08.provider.y − 8` or below in every frame, so the help line with "Nothing leaves this Mac." (`app.js:787`) is never on screen. If the key line does not fit the crop whole, crop it out whole; never cut it in the middle.
- **S09:** a 12-frame crossfade from `S09/before`. The `Stream` uses `public/takes/q2/frames.json` with `tail: false`, and the scene cuts away at the end of its window.

- [ ] **Step 1: Implement** the four scenes and add them to `Intro`.
- [ ] **Step 2: Run** `npm run check`. Expected: PASS.
- [ ] **Step 3: Look** at frames 1896, 1980, 2220, 2526 (S06); 2670, 2796, 2934 (S07); 3000, 3150, 3210 (S08); and 3330, 3480, 3660 (S09).
  - 2220 has no card.
  - 2526 shows the Note above the answer and a citation.
  - 2934 is centred on " · this Mac · ".
  - S08 shows no help line and no key.
  - The model in the provenance line is the model in the Model field.
- [ ] **Step 4: Commit** the four scenes, `Intro.jsx`, and `src/timeline.mjs` (if the S06 fit check lowered a key) with the message `Add the Ask scenes on the replayed takes`.

### Task 11: Scenes S10–S15 (Keep and Close)

**Files:**
- Create: `tools/intro-video/src/scenes/S10.jsx` … `S14.jsx`, `S15.jsx` (exports `S15` and `EndCard`)
- Modify: `tools/intro-video/src/Intro.jsx`

**Interfaces:**
- Consumes: the S10–S14 shots and rects (Tasks 6 and 7), `MASTER`, `TEXTS`, and `zoomsFor` (Task 4), and the components of Task 8.
- `EndCard({cues})` draws the stack of spec 5.3 S15, items 1–8, from `TEXTS`, between y = 65 and y = 880. Each line enters with the card recipe, the wordmark letters rise 2 frames apart, and the icon uses the existing `Icon` spring (`brand.jsx:30-48`). A line shows only when its cue exists, so K5 and the clip end have no platform line, and the clip end has no verb line. With a `panelOut` cue (S15 only), the verb line does not enter: it starts as the S14 hero line (160 px, centre) and shrinks to 64 px in its stack slot over `panelOut`. S14 stops drawing the hero line at its last frame.
- **S10:** a 12-frame crossfade to the Blog at `blog`.
- **S11:** the dialog, cropped from `S11/position` at `rects.S11.dialog`, enters over `S11/base` from the centre with opacity and a scale from 0.97 to 1 in 12 frames. The arrangement change is a cut, and the close is a cut.
- **S12:** a 12-frame crossfade in. The tag change is a cut.
- **S13:** the EPUB shots in a panel at their own 720 px width on `Background`, not under the document camera, with a cut at `chapter`. At `dialog`, a cut to `S13/kindle` at 1.3x.
- **S14:** the 1.8 s pull-back to the end zoom of Task 6, then the gather of spec 5.3 S14, with the hero line from `TEXTS`.

- [ ] **Step 1: Implement** the six scenes and add them to `Intro`.
- [ ] **Step 2: Run** `npm run check`. Expected: PASS.
- [ ] **Step 3: Look** at frames 3780, 3870 (S10); 4020, 4080 (S11); 4290, 4350 (S12); 4560, 4680 (S13); 4800, 4854, 4920 (S14); and 4990, 5100, 5280, 5399 (S15).
  - 4990: the hero line shrinks toward its subtitle slot.
  - 5399 is the complete end card: the subtitle "Read. Mark. Ask. Keep." at 64 px under the wordmark, the URL pill at full opacity, and the Linux line last.
  - Every line is inside the safe area.
- [ ] **Step 4: Commit** the six scenes and `Intro.jsx` with the message `Add the Keep and Close scenes and the end card`.

### Task 12: The music on the new acts

**Files:**
- Modify: `tools/intro-video/music.mjs`, `tools/intro-video/src/timeline.mjs` (`music` on `MASTER` and `CUT`), `tools/intro-video/src/Intro.jsx` (`Audio`, `Background kick`)

**Interfaces:**
- `grid.music = {sus, kickSoft, hats, kick, bass, light, arpOff: [[from, to]], stop, end, notes: [[beat, midi, 'pluck' | 'bell', cue]], ui: [[beat, kind, cue, gainDb?]]}`, in beats on the whole grid. `cue` names the scene cue of the event, such as `'S04.clicks[0]'`. `kind` is one of `tick`, `pop`, `thump`, `whoosh`, `swell`, `pen`, `lift`, `tap`, `shimmer`.
- `MASTER.music` (spec 7.7, and the Sound accent column of spec 5.2):
  - pad from beat 0 at full level;
  - `sus` [[2.7, 4.5], [61, 66]] (G over D while the cursor rests on Ask; Dsus4 before the click);
  - `kickSoft` [[16, 61]] on bar downbeats; `hats` [[34, 61]];
  - `kick` and `bass` [[66, 131]]; `light` [[131, 158]];
  - `arpOff` [[61, 74], [119, 121]]; `stop` 158; `end` 166;
  - plucks D b6, F# b37, A b40, high D b43; the motif D, F#, A, D at b162, 162.5, 163, 163.5; a low bell at b170; the high G bell at b175;
  - the other notes and the UI sounds from spec 5.2 and 5.3.
- `CUT.music`: `sus` [[0, 5]], `kick` and `bass` [[5, 40]], `arpOff` [[10, 12]], `end` 40, the G bell at b45.2, and the K-scene accents of the master's S06–S08.
- `music.mjs` keeps its voices, `chordAt`, and the reverb. Changes:
  - It renders each grid from beat −4 and drops the first 4 beats, so the pad is at full level on frame 0. Map: the pad re-attacks from silence at frame 0 today (`music.mjs:51-71`), which spec 7.7 does not allow.
  - The UI sounds go on their own bus at `UI_DB = -18`.
  - The master is `out = c × tanh(g × x / c)`, with `c = 10 ** (CEILING_DB / 20)`, `CEILING_DB = -1.5`, and `g = 10 ** (GAIN_DB / 20)`. This replaces the −3 dBFS peak scale (`music.mjs:229`).
  - It keeps the 3-beat fade at the end.
  - It runs `mkdirSync('public', {recursive: true})` and writes `public/music.wav` (90.00 s) and `public/music-ask.wav` (25.00 s).
  - `node music.mjs --list` writes no file. It prints `<event beat> <cue beat> <delta frames> <cue>` for each `notes` and `ui` event of both grids.
- `Intro({text = true, audio = true})` adds `{audio && <Audio src={staticFile('music.wav')} />}` and passes `MASTER.music.kick` and `kickSoft` to `Background`.

- [ ] **Step 1: Implement** the changes above.
- [ ] **Step 2: Run** `node music.mjs`. Expected: `Wrote public/music.wav: 90.00 s at 120 BPM` and `Wrote public/music-ask.wav: 25.00 s at 120 BPM`.
- [ ] **Step 3: Measure** with `ffmpeg -nostats -i public/music.wav -filter_complex ebur128=peak=true -f null - 2>&1 | grep -E "I:|Peak:"`, and the same for `music-ask.wav`. Expected: I from −14.5 to −13.5 LUFS, and Peak −1.0 dBFS or lower. If I is off, change `GAIN_DB` by (−14 − I). If Peak is too high, lower `CEILING_DB` by 0.5 dB. Measure again.
- [ ] **Step 4: Check the cues.** Run `node music.mjs --list`. Expected: every delta is 1 frame or less.
- [ ] **Step 5: Commit** `music.mjs`, `src/timeline.mjs`, and `src/Intro.jsx` with the message `Score the new acts at -14 LUFS with the Ask click as the downbeat`.

### Task 13: The compositions, the stills, and the carousel

**Files:**
- Create: `tools/intro-video/src/AskCutdown.jsx`, `tools/intro-video/src/HighlightsClip.jsx`, `tools/intro-video/src/Poster.jsx`, `tools/intro-video/src/posters.mjs`, `tools/intro-video/stills.mjs`
- Modify: `tools/intro-video/src/index.jsx`, `tools/intro-video/package.json`, `tools/intro-video/check.mjs` (`words` on the poster texts)

**Interfaces:**
- Consumes: `Intro`, `AskShot`, `CitationShot`, `ChatModelShot`, `EndCard`, `Captions`, `CUT`, `CLIP_END`, `CLIP_CARDS`, `zoomsFor`, and the two music files (Tasks 4 and 8–12).
- **`AskCutdown`** (1920×1080, 60 fps, 1,500 frames): K1+K2 `AskShot`, K3 `CitationShot`, K4 `ChatModelShot`, each with its cues and `zoomsFor(CUT, …)` (Task 10), K5 `EndCard`; `Captions grid={CUT}`; `<Audio src={staticFile('music-ask.wav')} />`.
- **`HighlightsClip`** (900 frames):
  - `<Sequence from={-1020}>` draws `Intro audio={false} cards={CLIP_CARDS}` for frames 0–719 (master 17.0–29.0 s, Decision 15).
  - `EndCard cues={CLIP_END}` for frames 720–899.
  - Audio: `music.wav` with `trimBefore={1020}` for 720 frames, then `music.wav` with `trimBefore={5172}` (b172.4) for 180 frames. So the master's G bell (b175) lands on clip frame 798, which is `CLIP_END.linux` (2.6 beats), as spec 4.4 ties the bell to the Linux line.
- **`Poster`** (a `Still`, 1920×1080, `defaultProps {poster: 'thumbnail'}`): `<Freeze frame={POSTERS[poster].frame}>` around `Intro` with `TextOn` false, plus a PAPER slip with `text` at `size` px in the lower left (left 115, bottom 880 or above). With `text: null`, there is no slip.
- **`posters.mjs`:**
  - `thumbnail: {frame: 2526, text: 'Read the paper. Ask in the margin.', size: 96}`.
  - `slide-01` to `slide-12` at frames 4854, 108, 690, 930, 1380, 1734, 1896, 2526, 2796, 3210, 4350, 5399, with the texts of spec 6.4 at 72 px.
  - `slide-12` has `text: null` (Decision 13).
  - `check.mjs` also runs the `words` rule on every poster `text`.
- **`stills.mjs`:**
  - Runs `npx remotion still src/index.jsx Poster ../../dist/intro-video/<name>.png --props='{"poster":"<name>"}'` for each poster.
  - Runs `Intro` stills at frame 3210 (`still-chat-pane.png`), 5399 (`still-end-card.png`), and 4854 (`still-full-margin.png`).
  - Joins `slide-01.png`…`slide-12.png` into `carousel.pdf`. It uses Playwright on Remotion's browser: an HTML page with `@page{size:1920px 1080px;margin:0}` and one full-page image for each slide, then `page.pdf({width: '1920px', height: '1080px', printBackground: true})`.
- **Scripts**, each of which starts with `npm run check &&`:
  - `render:ask`: `AskCutdown` into `../../dist/intro-video/localxiv-ask-25s.mp4` with `--audio-codec=aac`.
  - `render:highlights`: `HighlightsClip` into `../../dist/intro-video/localxiv-highlights-15s.mp4` with `--audio-codec=aac`.
  - `render:loop`: `Intro` with `--frames=1758-2477 --muted` (S06 from 29.3 to 41.3 s) into `../../dist/intro-video/localxiv-loop-12s.mp4`.
  - `stills`: `node stills.mjs`.

- [ ] **Step 1: Implement** the compositions, `posters.mjs`, `stills.mjs`, and the scripts.
- [ ] **Step 2: Render** with `npm run render`, `npm run render:ask`, `npm run render:highlights`, `npm run render:loop`, and `npm run stills`. Expected: the four MP4s, the PNGs, and `carousel.pdf` in `../../dist/intro-video/`.
- [ ] **Step 3: Make the GIF** with `ffmpeg -i ../../dist/intro-video/localxiv-loop-12s.mp4 -vf "fps=15,scale=800:-1:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse" -loop 0 ../../dist/intro-video/localxiv-loop-12s.gif`.
- [ ] **Step 4: Check the lengths** with `ffprobe -v error -show_entries format=duration -of csv=p=0 <file>`. Expected: 90.0, 25.0, 15.0, and 12.0 s (±0.02). Count the carousel pages with `.venv/bin/python -c "import re,sys; print(len(re.findall(rb'/Type\s*/Page[^s]', open(sys.argv[1],'rb').read())))" ../../dist/intro-video/carousel.pdf`. Expected: `12`.
- [ ] **Step 5: Look** at `thumbnail.png` (no film card, the tagline slip, a citation in the answer), `slide-05.png`, `still-chat-pane.png`, and frames 0, 300, and 1200 of the cutdown (`npx remotion still src/index.jsx AskCutdown … --frame=<n>`).
- [ ] **Step 6: Commit** each new and changed file by name with the message `Add the Ask cutdown, the Highlights clip, the stills, and the carousel`.

### Task 14 (optional): The 4:5 master

Do this task only if the owner wants the 4:5 test now. The captures stay in the main checkout (Task 17), so it can also run a week after launch.

**Files:**
- Modify: `tools/intro-video/src/index.jsx` (`Intro45`), `tools/intro-video/src/stage.jsx` (a `Format` context), `tools/intro-video/src/Captions.jsx`, the scene files (a `zoom45` on their camera keys), `tools/intro-video/package.json` (`render:4x5`)

**Interfaces:**
- `Intro45` is 1080×1350, 60 fps, 5,400 frames, with `defaultProps {format: '4:5'}`. `Format` gives the stage size and `k = zoom × 0.75`.
- Cards are 72 px in the top band, from y = 150 to 360, under the strip at y = 70. Keep the bottom 230 px clear. The side margins are 65 px. The URL pill and the Linux line are 52 px.
- Use the camera table of spec 6.3. No zoom above 3.0.

- [ ] **Step 1: Implement** `Intro45`, `Format`, the 4:5 cards, and the `zoom45` keys.
- [ ] **Step 2: Look** at the `Intro45` stills at frames 108, 1380, 2526, 4854, and 5399.
- [ ] **Step 3: Render** with `npm run render:4x5`.
- [ ] **Step 4: Commit** the changed files with the message `Add the optional 4:5 master`.

## Part 4: Checks before posting, the README, and launch prep

### Task 15: The checks before posting (spec 7.9)

**Files:** none. Checks only, so this task has no commit. A failed check goes back to the task that owns the code, and that task commits the fix.

**Interfaces:**
- Consumes: the MP4s, stills, and `carousel.pdf` of Task 13 in `<wt>/dist/intro-video/`, and the shots of Tasks 5–7 in `public/`. Step 3 and the step sheets of Step 4 run in `<wt>/dist/intro-video`. The `public/` PNGs are in `<wt>/tools/intro-video`.

- [ ] **Step 1 (item 3):** `npm run check`. Expected: PASS.
- [ ] **Step 2 (item 9):** Measure `localxiv-intro.mp4`, `localxiv-ask-25s.mp4`, and `localxiv-highlights-15s.mp4` in `../../dist/intro-video/` with `ffmpeg -nostats -i <file> -filter_complex ebur128=peak=true -f null - 2>&1 | grep -E "I:|Peak:"`. Expected: I from −14.5 to −13.5 LUFS, and Peak −1.0 dBFS or lower. Fix it in `music.mjs` (Task 12), never in the render.
- [ ] **Step 3 (items 2 and 6):** Make the 720p copy with `ffmpeg -i localxiv-intro.mp4 -vf scale=-2:720 -c:a copy localxiv-intro-720p.mp4`. Make contact sheets with `ffmpeg -i localxiv-intro-720p.mp4 -vf "fps=1,tile=5x3" sheet-%d.png`. Look at all six. Expected: every card reads at 720p, and there is no window chrome, no toolbar, no sidebar, no Georgia face, and no figure or table of the sample.
- [ ] **Step 4 (item 5):** Every frame of S06–S09 and K2–K4 draws one capture under the camera. So look at each PNG in `public/S06/`, `public/S07/`, `public/S08/`, `public/S09/`, `public/takes/q1/`, and `public/takes/q2/`. Then, for the crops and the cuts, make step sheets with `ffmpeg -ss 29 -to 62 -i localxiv-intro.mp4 -vf "fps=4,scale=960:-2,tile=4x4" step-%d.png` and `ffmpeg -ss 2.5 -to 20 -i localxiv-ask-25s.mp4 -vf "fps=4,scale=960:-2,tile=4x4" step-k-%d.png`. Look at each one. Expected: no key, no e-mail address other than `your-name@kindle.com`, no "Nothing leaves this Mac.", no "demo", and the provenance model equals the Model field.
- [ ] **Step 5 (item 4):** Read the contrast lines of `npm run check`. Look at the stills of frames 1980, 4350, and 5399 for each card, label, and end-card line on its background, and at frames 420, 1080, 1990, and 3960 for the strip.
- [ ] **Step 6 (item 7):** The `streamFrames` self-tests pass. Look at the S06 wait dip, frames 2206–2209 (`npx remotion still … --frame=2207`). Expected: a visible dip.
- [ ] **Step 7 (item 8):** The `words` rule of `npm run check` passes on every card, label, `TEXTS` entry, and poster text. Then check the posts.
  - Test the word boundaries of this Mac's grep: `echo 'the only one' | grep -E -i '\bonly\b'` prints the line, and `echo commonly | grep -E -i '\bonly\b'` prints nothing.
  - Run `sed -n '/^### 8.2/,/^### 8.4/p' <wt>/docs/superpowers/specs/2026-10-22-intro-video-v0.1.0-design.md | grep '^>' | grep -n -i -E "agent|any paper|every paper|nothing leaves|\bonly\b|\bfirst\b|no account|free ai|linux.*20[0-9]{2}"`. The first grep keeps only the post lines. Expected: one hit, "the first launch" in Reply 4. It is not a claim about LocalXiv.
- [ ] **Step 8 (items 1 and 10, the owner):** Ask the owner to do these checks, and record the answers in the task report:
  - Watch `localxiv-intro-720p.mp4` on a phone at arm's length, with the sound off.
  - Listen to it one time with the sound on.
  - Run the three-to-five-viewer test of spec 1.3.

### Task 16: The tools README and the launch prep (spec 8.7 items 1, 2, 5, 6)

Run this task in `<wt>`.

**Files:**
- Modify: `tools/intro-video/README.md`, `README.md`, `docs/macos-release.md`
- Create: `docs/media/localxiv-loop-12s.gif`

**Interfaces:**
- Consumes: `dist/intro-video/localxiv-loop-12s.gif` (Task 13), the commands of Tasks 2–13, `EXTRA` (Task 7), and the never-word pattern of Task 15 Step 7.

- [ ] **Step 1: Rewrite `tools/intro-video/README.md`:**
  - what the film is;
  - the commands in order: `node capture/gates.mjs`, `node capture.mjs --record q1|q2`, `node capture/chat.mjs judge`, `node capture.mjs`, `node music.mjs`, the `npm run` scripts;
  - the capture modes and the safety rules of spec 7.4, with the search and Mail patches;
  - why the takes are in git;
  - Credits: the title, the authors, the arXiv link, and the licence of the two CC BY Papers and of the sample;
  - the Remotion licence note.
- [ ] **Step 2: Change the top of `README.md`** (item 1). The lead line becomes "Read the paper. Ask in the margin." and the next line "A free, open-source Mac reader for arXiv papers." The feature list adds:
  - Highlights in four named colours, with Notes in the margin;
  - Ask, with Question cards whose citations open the passage;
  - Chat with your key or a model on your Mac, and no LocalXiv account;
  - All Notes and the library Notes page;
  - Export EPUB with Notes.
  The Kindle line moves down.
- [ ] **Step 3: Embed the loop.** Copy the GIF to `docs/media/` and embed it in `README.md`. If the GIF is over 8 MB, make it again at 640 px and 12 fps.
- [ ] **Step 4: Check the words.** Run `git diff -U0 README.md | grep '^+' | grep -n -i -E "<the pattern of Task 15 Step 7>"`. Expected: no output.
- [ ] **Step 5: First launch (item 5, the owner).** Ask the owner to download the v0.1.0 DMG in a browser and to do these steps on macOS 26:
  1. Open the DMG, and drag LocalXiv to Applications.
  2. Open LocalXiv.
  3. When macOS blocks it, open System Settings › Privacy & Security, click Open Anyway, and confirm.
  4. Open LocalXiv again.
  Ask for the exact name of each dialog and button, and for each step that is different. Wait for the report.
- [ ] **Step 6: Write the checked steps** from that report under the download line of `README.md` and as a section "Open an app that is not notarized" in `docs/macos-release.md`.
- [ ] **Step 7: Commit** `tools/intro-video/README.md`, `README.md`, `docs/macos-release.md`, and `docs/media/localxiv-loop-12s.gif` with the message `Lead the README with the reader and add the checked first-launch steps`.
- [ ] **Step 8: The repository description (item 2). Ask first.** Show the exact command and wait for a yes: `gh repo edit Akhil-Theerthala/LocalXiv --description "A free, open-source Mac reader for arXiv papers. Highlights and Notes in the margin. Ask when you choose."`. Then run it, and check that `gh repo view Akhil-Theerthala/LocalXiv --json description -q .description` prints the same text.
- [ ] **Step 9: The Linux issue (item 6). Ask first.** Show the exact title and body and wait for a yes.
  - Title: "A Linux build of LocalXiv".
  - Body: "LocalXiv runs on Apple Silicon Macs with macOS 26 or newer. We plan a Linux build, but it has no date yet. If you want a Linux build, add a thumbs-up reaction to this issue. In a comment, tell us your distribution and how you read papers today."
  Then run `gh issue create --repo Akhil-Theerthala/LocalXiv --title "<title>" --body-file <file>`. Give the owner the URL for X reply 5.

### Task 17: Merge

**Files:** no new change. The merge commit joins the branch to `main`.

**Interfaces:**
- Consumes: the branch `intro-video-v0.1.0`, `<wt>/dist/intro-video/`, and `<wt>/tools/intro-video/public/`.

- [ ] **Step 1: Keep the outputs.** `mkdir -p /Users/silver/Developer/LocalXiv/dist/intro-video-v0.1.0 && cp -R <wt>/dist/intro-video/. /Users/silver/Developer/LocalXiv/dist/intro-video-v0.1.0/`. This is a new folder, so the old 44 s render stays. If `/Users/silver/Developer/LocalXiv/tools/intro-video/public` does not exist, move `<wt>/tools/intro-video/public` there. Git ignores it. It lets a later render, such as the 4:5 test, run with no new capture.
- [ ] **Step 2: Check the main checkout.** In `/Users/silver/Developer/LocalXiv`: `test "$(git branch --show-current)" = main && git status --short`. If the checkout is not on `main`, or if a changed file is also changed on the branch, stop and ask the owner.
- [ ] **Step 3: Merge.** `git merge --no-ff intro-video-v0.1.0 -m "Merge the v0.1.0 intro film"`. Do not pipe the output.
- [ ] **Step 4: Clean up.** `git worktree remove .worktrees/intro-video-v0.1.0`, `git branch -d intro-video-v0.1.0`, and `git worktree prune`. Check that `git worktree list` has no `intro-video` line.
- [ ] **Step 5: Ask the owner** whether to push `main`. Also give the owner the posting rules of the spec: upload no `.srt` (spec 4.2), turn off LinkedIn auto captions, and upload the thumbnail by hand on X desktop and on LinkedIn (spec 6.4).
