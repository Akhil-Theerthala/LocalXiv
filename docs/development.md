# Run LocalXiv from source

Use an Apple Silicon Mac with macOS 26 or newer for the current release build. Install Homebrew before you begin.

1. Install Apple Command Line Tools if they are missing:

```sh
xcode-select --install
```

2. Clone the repository:

```sh
git clone https://github.com/Akhil-Theerthala/LocalXiv.git
cd LocalXiv
```

3. Install the conversion tools:

```sh
brew install python@3.14 pandoc latexml librsvg ghostscript epubcheck node
```

4. Install the locked JavaScript dependencies:

```sh
npm ci --ignore-scripts --omit=dev
```

5. Build and install the development app:

```sh
./install-app.sh
```

6. Open the installed app:

```sh
open "$HOME/Applications/LocalXiv.app"
```

The development installer copies the runtime code into `~/Library/Application Support/LocalXiv/app`. Run the installer again after source changes. Let active jobs finish and stop the old background service before replacing its code.

To enable AI generation from a source checkout, install the pinned agent packages and build
the native, script-free HTML renderer:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-ai.txt
xcrun swiftc -O papers/HTMLSnapshot.swift -o papers/html-snapshot
```

To test the reader without installing the native app, start an isolated library:

```sh
.venv/bin/python -m app.server --port 8765 --data-dir /tmp/localxiv-dev --open
```

Keep release builds separate from the development install. Follow [Build and publish a macOS DMG](macos-release.md) to create a portable app.

Overview and Blog use `papers/agent_overviews.py`. The application owns the sequence:
local orientation → evidence selection and retrieval → evidence-linked narrative → candidate →
local validation/rendering → evidence review → repair or completion. The normal path uses four
provider requests: selection, narrative, authoring, and review. Supplemental evidence or a genuine
correction adds requests; no provider reads the complete paper before either output begins.
Each authoring stage uses smolagents ToolCallingAgent for source lookup and structured submission.
Submission ends that stage; no model call is needed to request review or announce completion.
No model-generated code executes. Reading and conversion do not import smolagents.

`papers/reading.py` builds a deterministic local orientation and resolves validated selections;
it does not create an AI reading cache. The retained paper and passage IDs stay intact.
Bibliography entries are excluded using XHTML bibliography markers
and reference-section headings. PDF evidence uses explicit reference and appendix headings
to filter portions of mixed pages. Unmarked lists or unusual PDF reading order can still
need better extraction; the filter does not guess a cutoff based on author names.
The same filtered view supplies selection, supplemental lookup, citation validation, and review.
Older `paper-reading.json` files are ignored. Older Overview references that may contain
bibliography-derived context are not reused for Blog generation.

`papers/explanation.py` defines the shared plan schema: question, contribution, finding and
limitation each cite their own passages; visual focus and relationships guide the illustration.
The application derives legacy generation metadata from this plan. Each review records the
digest of the exact candidate it checked. Only an approved candidate replaces a saved generation.

Repairs start a new author context with the current plan/candidate and outstanding issues.
Each repair decision must copy current issue IDs, exact `plan.*` paths it preserves, and retrieved
passage IDs. The application records the decision beside measured changed paths and resulting issues.
Provider failures end the attempt and preserve draft artifacts. An identical rejected candidate
or repeated identical tool action ends the attempt without another expensive review. There is
no fixed whole-job request cap; distinct repairs can continue. Native DeepSeek/OpenRouter reasoning
is preserved within each authoring stage. DeepSeek authoring uses explicit low effort; scientific
review retains the provider default. Gemini Flash retains its low-effort setting.

Blog generation can inspect the saved, reviewed HTML/SVG Overview when its document digest and
assets are valid. It must adapt focused figures for the article, rather than embed the whole
Overview unchanged. Missing or incompatible references leave Blog independent. Saved generations
remain readable, including older references with the previous word budget.

New Overview layouts fit within 960 × 960 pixels. The model authors one complete SVG teaching
scene; there is no target word count, while 600 visible SVG words is an extreme rejection ceiling.
Blog figures retain the 260-word budget. Titles allow 12 words, introductions 30 and captions 45.
Passage IDs remain in metadata. Geometry checks reject clipped, overlapping or undersized labels.
Review checks scientific claims and visual relationships.
`overview_vision` includes rendered PNGs in review and requires provider image support. Without
it, review checks text/source evidence and local geometry, not visual-model inspection.

New Overviews submit exactly one namespaced SVG through the schema in `papers/explanation.py`.
`papers/html_figures.py` normalizes a bounded static-SVG profile, rejects active content and
unresolved local references, and preserves the exact accepted source as `.source.svg`. The model
owns composition and geometry. WebKit returns structured bounds and font-size issues from the
actual rendered page; repairs receive those issues without replacing unresolved semantic review.

Planning and review require the narrative of the uploaded paper: question and contribution,
visible operations, then a supported finding or synthesis. Method names must be introduced
through their purpose and mechanism. A taxonomy or glossary alone is insufficient.

The three persistent SVG regression fixtures under `tests/fixtures/svg-overviews` exercise
architecture, worked-method and comparison compositions without becoming production templates.
Rebuild `HTMLSnapshot.swift` after changing its checks. With the Command Line Tools 26.x compiler,
use the 15.4 SDK to avoid the known Swift module-version mismatch:
`xcrun swiftc -sdk /Library/Developer/CommandLineTools/SDKs/MacOSX15.4.sdk -O papers/HTMLSnapshot.swift -o papers/html-snapshot`.

WebKit exports PNG/PDF; the compatibility SVG embeds the PNG. Editable source includes the
source SVG and compiled HTML. Author repairs and semantic reviews receive the SVG accepted by
local validation. The review digest still binds the complete compiled candidate. Blog figures
keep their existing HTML/SVG format. Older saved scene metadata remains inert and readable.
A separate experiment in `papers/prototypes/parallel_scene.py` lays out a shared input, two or
three parallel operations, and a combined output. It is tested locally but is not connected to
generation or packaged with the app.

Each attempt retains `plan.json`, the latest `draft.json`, any `rendered-draft.json`, `reviews.json`,
and a final `candidate.json` only on success. `failure.json` records failure. `agent-trace.jsonl`
contains call status, elapsed time, usage, response and input-size diagnostics, including failed
requests. It does not store repeated request bodies or native reasoning. Provider diagnostics
retain a bounded, credential-redacted error message. Usage preserves cache and reasoning counts
when the provider reports them.

The source map is complete for ordinary papers. Exceptionally large maps use explicit indexed
pages; the selection submission is not accepted until that session has read every page. A known
provider/account evidence allowance can reject an oversized selection before narrative planning,
reporting measured characters and passages without truncating source text. This is provider-specific,
not a universal context estimate or user-facing setting.

`papers/panel-guides/` holds the current Overview authoring material: one short common drawing
guide, concise SVG construction notes, and five complete reference examples (flow, mapping,
comparison, calculation, chart). A panel request carries the drawing assignment, at most two
relevant complete examples, the construction notes, and the output contract. `papers/diagram-style.md`
remains the Blog figure style; the older `papers/diagram-guides/` set is retained only for Blog.

Overview execution lives in `papers/overview_workflow.py` (evidence, planning, parallel panel
dispatch, completion) and `papers/panel_authoring.py` (assignment prompt, one request, local check,
simple recovery). Panels are drawn concurrently with at most three in-flight requests; rendering,
usage accounting, repair scheduling, and persistence stay on the coordinator thread.

Run offline tests with `.venv/bin/python -m unittest tests.test_svg_figures tests.test_agent_overviews tests.test_explanation tests.test_ai tests.test_reading tests.test_overview_workflow tests.test_panel_authoring`.
Set `LOCALXIV_HTML_RENDERER` to the compiled helper to run `tests.test_figure_readability tests.test_panel_guides tests.test_app`.

## Find the relevant code

| Question | Start here |
| --- | --- |
| How does the Mac app start the reader? | `app/macos/PapersToKindle.swift`, then `launch.command` |
| What happens when I import, export, or send a paper? | `Application.execute()` in `app/server.py` |
| Who owns retained Paper files and removal? | `Library.retain_paper()` and `remove_paper()` in `papers/library.py` |
| Where is the complete conversion recovery order? | `convert_import()` in `papers/convert.py` |
| How is an export format selected and checked? | `artifact()` in `papers/exports.py`, shared by export and send jobs |
| Where is conversion isolated from the app? | `papers/convert.py` starts the sandboxed `papers/worker.py` process |
| Where are TeX repairs and Pandoc conversion implemented? | `convert_source()` in `native/host.py` |
| How are reader pages and EPUBs assembled? | `papers/document.py` |
| Where are papers, jobs, and settings stored? | `papers/library.py`; provider keys use `papers/settings.py` |
| How is an Overview planned, drawn and composed? | `papers/overview_workflow.py`, then `papers/panel_authoring.py` and `papers/arrangement.py`; `app/static/app.js` displays it |
| How is a Blog generated? | `papers/agent_overviews.py`; `papers/ai.py` routes Blog and Overview separately |
| What gets shipped in the DMG? | `app/macos/build-release.py` selects app files; `bundle_runtime.py` assembles external tools |

`convert_import()` owns the app's recovery order: Pandoc, arXiv HTML, LaTeXML, then the original PDF. It skips source engines when source retrieval failed and retains attempt diagnostics across worker runs. HTML retrieval happens outside the sandbox; each conversion attempt stays isolated. EPUB-only evaluations use the same recovery path with `epub_only=True` and stop before PDF. Calling `convert_paper()` directly without a mode still tries only Pandoc and LaTeXML for source diagnostics.

`Library.retain_paper()` promotes both successful and failed imports into owned Paper storage, preserving a ready Paper when a retry fails or falls back to PDF. Unchanged evidence keeps saved explanation files alongside the fresh import files, so retrying can repair missing originals without breaking overview exports. File promotion rolls back if saving the records fails. Removal also accepts failed Papers retained by older builds under `jobs/`, but only when a matching terminal import job proves ownership. Export code never decides where a Paper is retained.

`native/host.py` serves both the browser extension and the desktop converter. In `papers/worker.py`, the Pandoc path replaces two functions on that imported module to use sandbox-compatible graphics tools. These replacements stay inside the worker process. Account for both callers before changing this code.

## Check changes

Run the Python and browser checks from the repository root:

```sh
python3 -m unittest discover -s tests
node tests/test_app_ui.js
node tests/test_extension.js
```

For packaging changes, also run the [moved-app verifier](macos-release.md#verify-the-artifact). For conversion changes, compare real paper output with a known build, including equations, tables, figures, references and reading order. A valid EPUB alone does not establish that its content was preserved.
