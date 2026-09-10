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
evidence-linked plan → candidate → local validation/rendering → evidence review → repair or completion.
Each authoring stage uses smolagents ToolCallingAgent for source lookup and structured submission.
Submission ends that stage; no model call is needed to request review or announce completion.
No model-generated code executes. Reading and conversion do not import smolagents.

`papers/explanation.py` defines the shared plan schema: question, contribution, finding and
limitation each cite their own passages; visual focus and relationships guide the illustration.
The application derives legacy generation metadata from this plan. Each review records the
digest of the exact candidate it checked. Only an approved candidate replaces a saved generation.

Repairs start a new author context with the current plan/candidate and outstanding issues.
Provider failures end the attempt and preserve draft artifacts. An identical rejected candidate
or repeated identical tool action ends the attempt without another expensive review. There is
no fixed whole-job request cap; distinct repairs can continue. Native DeepSeek/OpenRouter reasoning
is preserved within each authoring stage. DeepSeek authoring uses explicit low effort; scientific
review retains the provider default. Gemini Flash retains its low-effort setting.

Blog generation can inspect the saved, reviewed HTML/SVG Overview when its document digest and
assets are valid. It must adapt focused figures for the article, rather than embed the whole
Overview unchanged. Missing or incompatible references leave Blog independent. Saved generations
remain readable, including older references with the previous word budget.

New Overview layouts fit within 960 × 960 pixels, including header and caption, and at most
180 visible authored words. Blog figures retain the 260-word budget. Titles allow 12 words,
introductions 30 and captions 45. Passage IDs remain in metadata. Geometry checks reject clipped,
overlapping or undersized SVG labels. Review checks scientific claims and visual relationships.
`overview_vision` includes rendered PNGs in review and requires provider image support. Without
it, review checks text/source evidence and local geometry, not visual-model inspection.

WebKit exports PNG/PDF; the compatibility SVG embeds the PNG. Editable source is HTML.
A separate experiment in `papers/prototypes/parallel_scene.py` lays out a shared input, two or
three parallel operations, and a combined output. It is tested locally but is not connected to
generation or packaged with the app.

Each attempt retains `plan.json`, the latest `draft.json`, any `rendered-draft.json`, `reviews.json`,
and a final `candidate.json` only on success. `failure.json` records failure. `agent-trace.jsonl`
contains call status, elapsed time, usage, response and input-size diagnostics, including failed
requests. It does not store repeated request bodies or native reasoning. Provider diagnostics
retain a bounded, credential-redacted error message. Usage preserves cache and reasoning counts
when the provider reports them.

The seven bundled layout guides are concise LocalXiv adaptations of diagram-design (MIT),
with upstream provenance in `papers/diagram-guides/source.json`. They describe supported visual
relationships and avoid incompatible typography/geometry examples.

Run offline tests with `.venv/bin/python -m unittest tests.test_agent_overviews tests.test_explanation tests.test_ai tests.test_reading`.
Set `LOCALXIV_HTML_RENDERER` to a compiled `HTMLSnapshot.swift` executable to run `tests.test_figure_readability`.

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
| How are overviews generated and displayed? | `papers/ai.py` generates them; `papers/overview.py` validates them; `app/static/app.js` displays them |
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
