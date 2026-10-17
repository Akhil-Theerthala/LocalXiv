# Architecture review of the workflows

Reviewed on 2026-10-17 at `main` (`cb86563`). This is a report only. No code changed. The items to remove are in `docs/cleanup.md`.

## Scope and method

The review compares six parts of the app with `CONTEXT.md` and with the current spec for each part.

| Part | Code | Design |
| --- | --- | --- |
| Overview and the shared generation core | `papers/overview_workflow.py`, `coordinator.py`, `ai.py`, `reading.py` | 2026-10-08 Overview story, 2026-09-18 Overview scene layout |
| Blog | `papers/blog_*.py`, `explanation.py`, `passages.py` | 2026-10-08 Blog checks, Blog sections, Blog readability |
| Figure library | `papers/figures/`, `papers/HTMLSnapshot.swift` | 2026-09-18 figure library consolidation, Overview scene layout |
| Import, Paper queue, library, export, search | `app/server.py`, `papers/library.py`, `acquire.py`, `convert.py`, `worker.py`, `arxiv_html.py`, `document.py`, `exports.py`, `search.py`, `native/host.py` | 2026-09-05 local paper library, 2026-09-08 parser robustness, 2026-09-29 Paper search |
| Native shell and web app | `app/macos/*.swift`, `app/static/*.js` | 2026-10-14 UI redesign, 2026-09-22 front-end deepening |
| Build and release | `.github/workflows/macos-build.yml`, `app/macos/*.py`, `install-app.sh` | `docs/macos-release.md`, `docs/sparkle-updates.md` |

One reviewer read each part. Two skeptics then checked each finding. A fact-checker tried to refute it in the code. A design judge looked for a spec or a reason that makes it intended or harmless. A second pass looked at four areas that no part owned: the security of the local service, storage durability, the provider layer, and the system as a whole. Its findings went through the same two skeptics.

The reviewers reported 79 findings. Seven repeat another finding, which leaves 72. No fact-checker found a finding to be false. The design judges found 8 findings to be true but intended or harmless; the last section lists them. That leaves 64 findings: 1 high, 11 medium, and 52 low.

The section that holds a finding gives its final rating. Each high and medium item gives the two skeptics' ratings as (fact, design). Where the two ratings differ, the item says why it is in its section.

These limits apply:

- No test run finished. The runs of `test_overview_workflow`, `test_blog_workflow`, and `test_figure_layout` each took more than 3 minutes, and the reviewers stopped them. The reviewers read the tests.
- No live provider run took place.
- The items under "What already holds" come from one reviewer's reading of the code. No skeptic checked them. The same applies to the "Native shell" correction under "Documents to correct".
- H1 comes from reading the code. No exploit ran. M1 was reproduced in a scratch folder with the same `pandoc` and `xelatex` commands as the export.
- Another session had uncommitted changes in `native/host.py`, `papers/math_fallback.py`, and `papers/tex_math.js`. The review read the committed versions of those files.
- The 2026-10-12 review removed dead code in `1cccf73`. This review does not repeat those items.

## Verdict

The architecture makes sense. Each workflow has clear stages, one owner for each decision, and a limit on every retry. Most findings are drift between the code and the documents, not design faults. The faults that matter are at two trust boundaries (the conversion sandbox and the Blog PDF export) and in a few failure paths that lose the reader's work.

| Part | Verdict | Largest risk |
| --- | --- | --- |
| Overview | Sound. Three provider stages (selection, Digest, Scene) come before a deterministic Scene layout. A Stage retry reuses the results of earlier stages. | Low risks only. The largest is O5: Evidence selection sees only the first page of a large source map. |
| Blog | Sound. Each stage has one output. The Section checks send exact messages. Sections and figures run in parallel, and one lock guards the shared log. | M3: a failed omission cleanup fails a Blog whose sections all passed. |
| Figure library | Sound. It has one entry point (`Figure`), one-way imports, and no import cycle. Two builds of one panel gave the same SVG bytes. | M4: a Chart caption does not wrap, so it can run out of its box, and no check reports it. |
| Import and jobs | Sound. The Paper queue, the conversion recovery order, and Paper retention match `CONTEXT.md`. | H1: the sandbox boundary leaks through symlinks. |
| Native shell and web app | Sound. The web app owns the Chrome state, the history, and the commands. The Swift side draws the state that it gets. | M5: a citation jump moves the saved Reading position. |
| Build and release | Sound for one maintainer. CI builds and checks the app. The signed publish step is local, because the Sparkle key stays in Keychain. | M10: the Sparkle key has no recorded backup. |

## What already holds

- **Paper queue.** The queue key is the arXiv ID without its version. Each key gets one thread, and a job leaves the queue only after `execute` returns (`app/server.py:77`, `:84-91`, `:166-168`).
- **Conversion recovery.** The order is Pandoc, arXiv HTML, LaTeXML, then the PDF. The source engines do not run after the source download fails. Each attempt runs in its own worker on a fresh extraction (`papers/convert.py:38-77`, `papers/worker.py:159-172`).
- **Separate jobs.** Conversion and generation are separate jobs. A generation is saved only when its run succeeds (`app/server.py:207-217`, `:234-236`).
- **Overview stages.** The Stage retry reuses earlier results (`papers/coordinator.py:217-233`, `papers/overview_workflow.py:264-266`). The coverage rules and the chips match `CONTEXT.md` (`papers/overview_workflow.py:300-310`).
- **Blog checks.** Each Section check failure sends an exact message back (`papers/explanation.py:794-823`, `papers/coordinator.py:422-435`). Six workers share one event log under one lock (`papers/coordinator.py:253-268`).
- **Figure library.** No module in `papers/figures/` imports another `papers` module, and none calls a provider. The same WebKit binary measures and draws the text.
- **Local service.** The server checks the Host header, the Origin, and a bearer token before any route runs. It sends no CORS headers (`app/server.py:315-331`). A web page in a browser cannot use the API.
- **Untrusted content.** The paper frame is sandboxed, and each `/files` reply has a strict CSP (`app/server.py:292-305`, `app/static/reader.js:265-267`). Model text reaches the page only as `textContent`, and the Figure library escapes every model string in the SVG.
- **Keys.** API keys stay in Keychain. The page gets only booleans (`app/server.py:62-70`), and error text has the key removed (`papers/ai.py:62-80`).
- **Release.** CI never replaces a published release (`.github/workflows/macos-build.yml:137-142`). The app requires a signed feed and signed archives (`app/macos/build-release.py:164-165`).
- **Paper search.** Search tries Semantic Scholar, then arXiv. When both fail, the page shows "Search is down" with **Try Again** (`papers/search.py:154-166`, `app/static/app.js:429`, `:456`).

## High

### H1. A hostile paper source can write files outside the conversion sandbox

Skeptics: high, medium. The fact-checker found that a hostile source needs no exploit to plant the symlink, so the item is high.

- The sandbox profile lets the worker write anywhere in the job folder (`papers/convert.py:102`).
- After the worker stops, the parent process writes `worker.log` with `write_text` (`papers/convert.py:201`). The parent has no sandbox, and `write_text` follows a symlink. Before each attempt, the parent also writes `metadata.json` and `worker.sb` into the same folder (`:131`, `:133`). Later, it writes `report.json` (`papers/library.py:148`) and the exports (`papers/exports.py:148`, `:183`).
- `worker.log` holds the worker's output. When LaTeXML fails, the worker prints up to 1,600 characters of the LaTeXML log (`papers/worker.py:42-60`, `:207`). So the paper source controls part of what the parent writes.
- LaTeXML loads a `<name>.ltxml` Perl binding from the source folder. The archive extraction rejects links but does not remove these files (`native/host.py:84` at HEAD). LaTeXML runs when Pandoc and arXiv HTML both fail, and a hostile source can make them fail.
- Result: a hostile arXiv source can make the parent write text that it chooses to any path that the user can write, for example a shell start-up file. The 2026-09-05 spec requires that a converter get no general access to the home folder.
- The same Perl code can call `setsid`. Its processes then leave the memory check and the `killpg` cleanup (`papers/convert.py:180-191`).

**Fix.** Let the sandbox write only a `work/` subfolder. Keep `worker.sb`, `worker.log`, the reports, and a read-only copy of `metadata.json` in the parent's folder. Pass the profile inline with `sandbox-exec -p`. Before `retain_paper`, walk the job folder with `lstat` and reject every symlink. Remove `*.ltxml` and `*.latexml` from the extracted source before LaTeXML runs. Before that change, search the parser corpus for papers that ship their own binding.

## Medium

### M1. The Blog PDF export lets model-written TeX read local files

Skeptics: medium, medium.

- `export_pdf` sends the Blog Markdown through `pandoc` and XeLaTeX with only `-no-shell-escape` (`papers/exports.py:71-101`). The option `markdown-raw_html-raw_tex` removes raw TeX blocks, but it keeps `$...$` math as TeX. XeLaTeX runs in the service process, outside the sandbox (`app/server.py:239`).
- The math `$\text{\input{/path}}$` puts the text of any file that the user can read into `blog.pdf`. A skeptic reproduced this with the export's own commands. `openin_any=p` does not stop it, because TeX Live 2026 ignores that setting.
- The model writes this math from the paper content, so a prompt injection in a paper can choose the file. The text leaves the Mac only when the reader shares the PDF or clicks a crafted link in it. Send to Kindle sends only to the reader's own address.
- The comment at `papers/exports.py:81` says that this cannot occur.

**Fix.** Run the Blog `pandoc` and XeLaTeX command under `sandbox-exec` with `sandbox_profile(work, app)` from `papers/convert.py`. Set `HOME`, `TMPDIR`, `TEXMFOUTPUT`, and `TEXMFVAR` to paths in `work`. A skeptic tested an equivalent profile: the `\input` export failed, and a normal Blog still exported with its figure. Correct the comment at `papers/exports.py:81`, and correct `native/host.py:2079` at HEAD, which sets `openin_any=p` for the same wrong reason.

### M2. A reimport through another link form deletes the saved Overview and Blog

Skeptics: medium, medium.

- `document_digest` hashes all metadata except `id`, `directory`, `document_digest`, and `report` (`papers/library.py:21-22`). The hash therefore includes `original_url` (`papers/acquire.py:97`), `conversion_revision` (`papers/convert.py:127`), and `pdf_error`.
- An import of the same arXiv version through an alphaXiv link, a `/pdf/` link, or a link with no version gets a new digest. So does an import after an app update that changed one of the 13 hashed converter files. `save_paper` then deletes the saved generations (`papers/library.py:198-199`). The reader loses paid work and gets no warning.
- `docs/development.md` says that unchanged evidence keeps the saved explanation files.

**Fix.** Add `original_url`, `conversion_revision`, and `pdf_error` to the exclusion tuple at `papers/library.py:22`. The chapters and passages stay in the hash, so a converter change that alters the content still clears the explanations.

### M3. A failed omission cleanup fails a Blog whose sections all passed

Skeptics: medium, low. A local run record shows this failure: one run on 2026-09-18 stopped at the stage `omission_cleanup`. So the item is medium.

- When a figure becomes an Omitted Blog figure, `write()` calls `remove_figures` with no guard and outside `run_stage` (`papers/blog_workflow.py:230-232`, `:243`). The join has a guard (`:225-229`), but the cleanup does not.
- The cleanup must return at least one edit (`papers/blog_article.py:25-26`). `JOIN_TASK` tells the model how to return an edit that changes nothing, but `CLEANUP_PROMPT` does not (`papers/blog_prompts.py:218-226`). Section prose already stands without its figure (`:179-180`), so the cleanup often has nothing to change.
- The cleanup also gets no list of allowed sentences (`papers/blog_article.py:147-148`). It can edit any sentence, including the only explanation of a term. The 2026-10-08 Blog checks design fixed that defect for the join.

**Fix.** Catch `ProviderError` around `remove_figures`, then ship `Article.without_markers(...)` and record a note, as the join does. Add the no-change rule from `JOIN_TASK` to the cleanup task. Pass `allowed` as the sentences of the sections that held the omitted figures.

### M4. A Chart caption runs out of its box, and no check reports it

Skeptics: medium, medium.

- `Chart` draws its caption as one line (`papers/figures/nodes.py:690-691`) and sizes its box for one line at 300 units (`:628-633`). `Bars` and `Grid` wrap their captions (`:514`, `:451`). The caption limit is 90 characters (`:24`), so a caption of more than about 45 characters overflows.
- The router avoids the box, not the caption (`papers/figures/nodes.py:637`). A probe drew an arrow through a caption and got no issue and no warning. The native checks compare text with the rectangle that holds its centre (`papers/HTMLSnapshot.swift:150-169`), so they do not find the overflow.
- `CONTEXT.md` "Scene correction" says that "geometry defects cannot occur". That is false. Also, both workflows already send native-check issues to the model as a correction (`papers/overview_workflow.py:341-349`, `papers/blog_figures.py:124-125`).

**Fix.** In `Chart.size`, wrap the caption with `measure.wrap(caption, self.w)` and count its lines. In `Chart.draw`, draw each line as `Bars` does (`papers/figures/nodes.py:533-535`). In `CONTEXT.md`, remove "geometry defects cannot occur" and add native-check issues to the correction triggers.

### M5. A citation jump moves the saved Reading position

Skeptics: medium, medium.

- `follow()` and `openPassage()` set the module-level `chapter` at once (`app/static/reader.js:264`, `:406-411`, `:647`). `switchTab()` saves `{view, chapter}` and does not check whether the reader scrolled after the jump (`:115`). The server keeps the anchor from the old chapter (`papers/library.py:123`).
- Example: click a citation into References, switch to the Blog, then reopen the Paper. The Paper view opens at the top of References. `CONTEXT.md` "Reading position" says that a jump does not move the position until the reader scrolls there.

**Fix.** At `app/static/reader.js:115`, save only the view: `saveReading(selected, {view: name})`. Each chapter change that the reader chooses already saves through `goChapter` and the guarded scroll save.

### M6. One Mail handoff stops progress for every Paper

Skeptics: medium, low. It breaks the Paper queue rule that different papers run concurrently, and it blocks cancel, so the item is medium.

- `Application.execute` holds the process lock for the whole Mail handoff (`app/server.py:243-257`). `send_with_mail` runs `osascript` with no timeout (`native/host.py:5065-5069` at HEAD).
- `checkpoint()` takes the same lock (`app/server.py:127`), and each conversion calls it about once a second (`papers/convert.py:164`). Submit, cancel, and remove also take the lock.
- While Mail shows its Automation prompt or hangs, no conversion or generation reports progress, and cancel hangs. A conversion fails if the stop lasts longer than its 11-minute limit.

**Fix.** Release the lock around `send_with_mail`, and take it again to record the result. Make `cancel()` refuse a job whose delivery is `attempting_mail`. Add a timeout to the `osascript` call.

### M7. The app reads both API secrets from Keychain on every poll

Skeptics: medium, medium.

- `public_settings()` calls `get_key()` for the provider key and the Semantic Scholar key only to compute `has_key` and `has_s2_key` (`app/server.py:62-70`). `get_key()` asks Keychain for the password data (`papers/settings.py:30-62`).
- The page polls `/api/state` every 2 s during a job, every 10 s when no job runs, and every 30 s when the page is hidden.
- Release builds are ad hoc signed, and the bundled Python can change between builds. After an update, the Keychain access list can stop matching. Each poll can then ask the reader for approval, and a refusal shows AI as not connected.

**Fix.** Add `has_key(endpoint)`. It calls `SecKeychainFindGenericPassword` with no password buffer and returns whether the item exists. Use it in `public_settings()`. Keep `get_key()` for the paths that send a request.

### M8. A second copy of the app cannot start while the first copy's service runs

Skeptics: medium, medium.

- Quit does not stop the service, by design. `RUNTIME_ID` includes the install path, and both the Swift app and the server refuse a service with another `RUNTIME_ID` (`app/macos/PapersToKindle.swift:134-136`).
- Example: open the app from the DMG, quit, then open the same version from `/Applications`. The launch fails with "An older background service is running". The only stop path is the Sparkle update path.

**Fix.** In the mismatch branch of `checkService`, send `POST /api/update/shutdown` with the session token and the old service's own `runtime_id`. Wait for the old service to exit, then start the new one. Show the alert only if the shutdown fails.

### M9. Blog sections lose corrections to the JSON wrapper

Skeptics: medium, medium.

- `call_with_event` asks every provider request for a JSON object (`papers/coordinator.py`). So a Blog section must return its Markdown inside `{"text": ...}`.
- In the saved runs, 36 of 279 section answers did not parse. 31 of them were plain Markdown from Claude models. Each one uses a correction from the section's budget.
- No request sends a schema. The strict schemas reach the model only as prompt text through `shape()` (`papers/explanation.py:24-51`).

**Fix.** Give the section request a plain-text answer. Add a text option to `request_validated` that skips `parse_json` and sends the raw text, without a code fence, to the validator. Keep JSON for the other stages.

### M10. The Sparkle signing key has no recorded backup

Skeptics: medium, medium.

- The EdDSA private key is only in the login Keychain (`docs/sparkle-updates.md:15-22`). On 2026-09-10, no backup existed (`docs/verification/sparkle-updates.md:50`), and no later record shows one.
- Every release pins the public key and requires a signed feed (`app/macos/build-release.py:164-165`). Releases are ad hoc signed, so Sparkle cannot change the key. If the key is lost, the in-app updater stops on every installed copy, and each user must install a new DMG by hand.

**Fix (no code).** Export the key once with `.sparkle/2.9.6/bin/generate_keys --account localxiv-sparkle -x <file>`. Keep the file in encrypted storage on another device, and delete the plain file. Write the date of the backup in `docs/verification/sparkle-updates.md`.

### M11. Releases ship with Pandoc's GPL corresponding source still open

Skeptics: medium, low. This is a licence duty, so the item is medium.

- `docs/dependency-licenses.md:81-82` says to resolve every `reviewRequired` item before you publish. The v0.0.19 source inventory has the status `review-required` and 9 open items. One item is the source of the Haskell packages that are linked into Pandoc, which GPL corresponding source requires.
- `collect_sources.py` reads only the runtime manifest and `package-lock.json` (`app/macos/collect_sources.py:101`, `:108`). So the inventory does not list the 15 PyPI packages. Their licences are permissive and the app ships their licence files, so that gap has no legal weight.

**Fix.** Recover the Cabal build plan for the shipped Pandoc and fetch its Hackage sources in the `pandoc` branch of `collect_sources.py`. As an alternative, build Pandoc from a committed freeze file. Until then, change the policy text to say what a release does.

## Low

Each item gives the finding, where it is, and the smallest fix.

### Overview and the generation core

- **O1.** `is_authentication` looks for the word "authentication" in the error text (`papers/coordinator.py:207-209`). A Scene error that quotes a component such as "Mutual authentication handshake" then skips the Stage retry. Fix: add `AuthenticationError(ProviderError)` to `papers/errors.py`, raise it at `papers/ai.py:162` and `:190`, and test with `isinstance`.
- **O2.** The layout correction uses the default `attempts=2` (`papers/overview_workflow.py:357-359`). One Scene pass can send 5 requests, but `CONTEXT.md` allows 4. Fix: pass `attempts=1`, as `papers/blog_figures.py:171` does.
- **O3.** A missing renderer or a renderer crash starts a full Scene Stage retry, which a new Scene cannot fix (`papers/overview_workflow.py:322`, `papers/coordinator.py:225-231`). Fix: raise `FileNotFoundError` for a missing renderer in `papers/figures/measure.py:27-29`, and do not retry an `OSError` in `run_stage`.
- **O4.** A cancel during the last request leaves `run.json` with `delivery: completed`, although the server saves nothing (`papers/overview_workflow.py:397`). Fix: call `self.progress(...)` before the delivery write, in both workflows.
- **O5.** Evidence selection sees only the first page of a large source map (`papers/coordinator.py:451-464`). Above 200 entries or 24,000 characters, the Overview gets the first 50 entries, which are all sections, with no figure captions. Only the Blog can ask for more. Fix: before you page, try a compact full map with no caption previews.
- **O6.** No code deletes figure asset folders (`papers/figures/render.py:413-415`). Each build writes 0.4 to 2.2 MB, and rejected builds, failed runs, and replaced generations stay until the Paper is removed. The Figure library also names the app's storage path, `reader/overview-figures`. Fix: delete the folder of a rejected build. Let the caller give the output folder.
- **O7.** `overview_workflow.py` and `explanation.py` import private helpers from the Figure library (`_subtree`, `_flatten_text`, `_check_text`, `_identifier`, `_panel_error`). Fix: give the two helpers that cross the boundary public names.

### Blog

- **B3.** After a rejected key, each running section and figure sends more requests (`papers/blog_workflow.py:196-202`, `papers/blog_figures.py:174-175`). Fix: re-raise when `is_authentication(error)`.
- **B5.** The join can add a linking sentence before a section's answer (`papers/blog_prompts.py:214-215`). Fix: tell the join to edit the first sentence so that it links and still answers the heading.
- **B7.** `requests_made` counts transient retries, so one HTTP 429 uses a figure correction (`papers/blog_figures.py:107-116`). Sections and figures share `active_stage`, so a run can record the wrong failed stage (`papers/coordinator.py:264`). Fix: count only the first attempt of each call, and pass the failed stage explicitly.
- **B8.** `illustrative_values` has no item limit and allows 1,200 characters for each item (`papers/explanation.py:98`, `:611-612`), but each value must appear in a 640-unit panel. Fix: give it the limits of `exact_text`.
- **B9.** The docstring of `papers/explanation.py` and its comment at `:70-73` describe a review and an article word limit that no longer exist. Fix: rewrite both.

### Provider layer

- **A2.** OpenRouter treats `max_tokens` as a credit reservation. A low-credit account gets HTTP 402 on every request, and the message gives advice that the reader cannot follow (`papers/ai.py:161-164`). Fix: give 402 its own message.
- **A3.** Gemini returns its error object inside a JSON list. The error branch of `Provider._complete` reads it as a dictionary, so the detail is lost and the reasoning fallback cannot fire for Gemini. Fix: unwrap a list body before you read `error`.
- **A4.** The reader no longer sees the token use that the app records. The 2026-10-14 redesign removed it. Fix: add the request and token counts to `provenance()` in `app/static/reader.js`, with no currency.
- **A5.** A failed job does not link to its run record, and `run.json` does not name the workflow, the model, or the endpoint host. Fix: write them in `Coordinator.__init__` with `self.store.update(...)`, and keep the run ID in the job.
- **A6.** The connection test sends no `json_object`, so a custom endpoint that rejects it shows "Connection verified" and then fails each generation. Fix: make the test send the same request shape as a generation.

### Figure library

- **G4.** `PANEL_WRAPPER` repeats the heading, note, and edge limits by hand (`papers/blog_prompts.py:62-64`). It also says that the panel is 640 units wide, but the drawn panel is 592. Fix: build the text from `LIMITS`, `MAX_EDGES`, and `BLOG_DISPLAY_WIDTH`.
- **G7.** When `auto` puts two panels on different rows, `compose` drops the arrow between them and records nothing (`papers/figures/render.py:375-376`). Fix: draw a vertical arrow when the frames overlap horizontally, or reject page edges.
- **X3.** An Overview has no text alternative. The SVG gets `role="img"` with the footer as its name, and `annotateFigure` puts focusable links inside it. Fix: write `alt` from the title and the panel headings (`papers/overview_workflow.py:382`), and keep focusable cards out of the `img` role.

### Import, jobs, and storage

- **P3.** No code deletes an abandoned job folder or the folder of a replaced Paper (`papers/library.py:154`, `:188`, `:238`). The user's library already has orphaned Paper folders. Fix: after `save_paper` commits, delete the previous folder if it is owned. At startup, delete each `jobs/<id>` folder that no Paper names.
- **P5.** Startup job recovery runs in the `Library` constructor (`papers/library.py:51-56`). Any process that opens the live library marks the service's running jobs `interrupted`; `tests/live_generate.py` does this. Fix: move the loop to `Library.recover_jobs()`, and call it from `main()` while the flock is held.
- **P10.** No limit applies to concurrent conversions (`app/server.py:84-91`). A burst of imports from search results runs one conversion for each Paper, and the fixed time limits can then stop conversions that would succeed. Fix: add a `BoundedSemaphore` around the worker start in `convert_paper`.
- **D2.** The library has no schema version contract. An older build that saves settings deletes the settings keys that it does not know (`papers/library.py:309`). Fix: merge the incoming values into the stored JSON and keep unknown keys.
- **D4.** If `library.sqlite3` cannot be read, the service exits, and the app shows a general alert after 30 s. Fix: catch `sqlite3.DatabaseError` in `main()` and exit with a message that names the file and the recovery.
- **D5.** A kill between two folder renames leaves a Paper record that points at a missing folder, and startup does not repair it (`papers/library.py:175-179`, `:228`). Fix: name the staged folders after the folders they hold, and restore them at startup.
- **K2.** The Swift app and `server.py` send the session token to the saved port and trust any reply with the expected `runtime_id`, which any local process can build. Fix: make the health reply prove that the server holds the token with an HMAC of a nonce.
- **K3.** One token is the API bearer, the file cookie, and the `?token=` of every file URL. Fix: derive a file-only token for `/files`.
- **X6.** Every Paper and every EPUB is tagged as English (`papers/document.py:700-701`, `:377`). Fix: keep a language that the converter supplies.

### Native shell and web app

- **S1.** Swift and JavaScript keep their own copies of the view names, preference values, panes, and action IDs. A renamed action ID leaves its menu item disabled with no error, and `shell.js:59` drops an unknown command. Fix: log an unknown command and a state that does not decode.
- **S4.** The figure dialog is in `app.js` (`:763-876`), but only the reader uses it. Fix: move it to `app/static/figure.js`.
- **S5.** `SettingsWindow.swift:104-113` runs a script that knows the page's `.pane` class to size the window. Fix: let the `settings` command return the pane height.
- **S8.** After Mark as Unread on an open Paper, the next position save sets Reading again (`papers/library.py:122`). Fix: in `save_reading`, do not create a record from a save that has no state.

### Build and release

- **R2.** `release-local.py` checks the version but not that the draft was built from the tag's commit (`app/macos/release-local.py:29`). After a tag move whose CI run failed, it can sign the old assets. It also reads the release notes from the shared working tree (`app/macos/sparkle.py:96-98`). Fix: compare `source_commit` with the tag's commit, and read the notes from the release.
- **R4.** CI takes the current Homebrew bottles and the first `node` on `PATH`, and it runs only on tags. Upstream changes show up on release day. Fix: add a weekly `schedule` trigger that builds and verifies only.
- **R5.** `verify-release.py` never starts the app binary, so a build without Sparkle passes. Fix: add `-D LOCALXIV_RELEASE` to the release build and an `#error` when Sparkle is missing.
- **R8.** The release build installs PyPI pins with no hashes and without `--only-binary` (`app/macos/build-release.py:147-148`). Fix: add `--only-binary=:all:`.
- **R10.** The development `Info.plist` has no `NSAppleEventsUsageDescription` (`install-app.sh:48-50`), so the Mail handoff in a development install has no purpose string. Fix: add the key.
- **R11.** Source collection does not cache Node's `SHASUMS256.txt` (`app/macos/collect_sources.py:171`). If nodejs.org is down, a release stops even with the Node tarball in the cache. Fix: cache that file.

## Documents to correct

These findings need only a document change.

- **`docs/development.md`.** Lines 61-65 name the 2026-09-18 designs as the current Overview and Blog design. `CONTEXT.md` names the 2026-10-08 designs. Point to the `CONTEXT.md` entries instead. Add table rows for `papers/search.py` and for `acquire.py`, `arxiv_html.py`, and `pdf.py` (P8). Line 81 says that `SettingsWindow.swift` draws from the Chrome state, which is false (S7).
- **`CONTEXT.md`.**
  - Overview: the entry says "3–4 panels", but the story spec and the prompt allow 2 to 4 panels (O9).
  - Scene correction: remove "geometry defects cannot occur" (M4). Say how many layout requests a pass can send (O2).
  - Accepted narrative: limit the term to the Blog plan, and delete its last sentence (O8, B6).
  - Library search: the Library page has no text filter now. Library matches show on the results page (up to 5) and in Suggestions (up to 3) (S3).
  - Reflowed PDF fallback: no code builds it. Define the PDF fallback that exists (P6).
  - Element repair: it covers equations, diagrams, and figures, not tables (P6).
  - Section check: add the figure marker on its own line and the dash rule (B8).
  - Native shell: the find bar, the sidebar toggle, Help, the Settings panes, and opening a PDF are native actions, not commands.
- **Specs.**
  - 2026-09-18 Overview scene layout: the density floor is 40, not 30 at line 30. The Digest gets 2 corrections, not 1 (O9, O11).
  - 2026-09-18 figure library consolidation: the module table, `checks.py`, and `json_schema()` are out of date. The stub measurer was removed on 2026-10-11 (G6).
  - 2026-10-14 UI redesign: add `flush`, `close-settings`, the Paper menu, and the theme copy in UserDefaults (S6).
  - 2026-09-22 front-end deepening: add a status line that says which parts the redesign replaced (S7).
- **Release documents.** List the six files of a release prep commit in `docs/macos-release.md` (R3). Replace the stale paragraph at `docs/sparkle-updates.md:76-77` with a procedure to withdraw a bad update (R7).

## Tests that do not exist

`docs/development.md` asks for component end-to-end tests. No test covers these paths:

- Paper retention through `retain_paper`, and an import through `execute('import')` on a fixture.
- Startup job recovery.
- An Omitted Blog figure and `remove_figures`.
- A cancel or a rejected key during a run.
- The Chrome state and the commands between Swift and the web app.
- The arXiv HTML route, and the formats that `artifact()` makes.

## Requests for each generation

The counts below have no transient retries. One transient retry for each request can double every count except the figure counts.

| Workflow | Best case | Worst case | Design text |
| --- | --- | --- | --- |
| Overview | 3 | 20 | 16 |
| Blog, short | 8 | 100 | none |
| Blog, medium | 9 | 108 | none |
| Blog, large | 10 | 116 | none |

The Overview's extra 4 come from the third Digest attempt, which was deliberate, and from O2.

## What to revisit as the library grows

- **The state poll.** The summary query finds each Paper's added date with a subquery over all jobs (`papers/library.py:99-101`), so its cost is papers times jobs. It takes 3 ms at 14 Papers, about 1 s at 400 Papers, and about 7 s at 1,000 Papers. A slow poll also delays every job commit. Keep `added_at` on the Paper record. That change also fixes the old added date that a Paper keeps after a remove and a new import.
- **Unbounded tables.** No code deletes job rows or `usage` rows. `docs/cleanup.md` removes the `usage` table.
- **Cancel.** Cancel is cooperative. A provider request that is running holds its Paper queue for up to 900 s. Streamed answers with a checkpoint between chunks would fix this if it becomes a problem.
- **The process lock.** One lock serves every Paper. Use one lock for each Paper if more job kinds appear.
- **`native/host.py`.** The file holds archive extraction, metadata, EPUB packaging, about 70 TeX passes, and Mail. Move Mail out when a second caller needs it, as the 2026-09-05 spec says. Then move the extraction and EPUB code.

## True but intended

The design judges found these findings to be true but intended or harmless:

- **R9.** The Developer ID path in `build-release.py` never runs. `docs/macos-release.md` keeps it for a future notarized release.
- **B4.** Every Blog length allows 3 to 8 sections. The 2026-10-08 Blog sections design names this cost.
- **B10.** The Blog request counts are high, but every loop has a limit.
- **O10.** The code accepts a Result panel stat anywhere in the panel. This matches the "Scene" entry in `CONTEXT.md`.
- **G3.** The stub measurer from the consolidation spec is gone. It was removed on purpose when the project moved to end-to-end tests.
- **G5.** The on-screen figure has no header line and uses the dark palette. The palette changes only colours.
- **G8.** `render.js` and `exports.py` read keys that new figures do not have. Saved generations and the bundled sample need those reads.
- **P7.** The Mail code is in `native/host.py`. The 2026-09-05 spec says to move it when a second caller needs it.
