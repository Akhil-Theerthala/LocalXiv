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

Behavior is documented in two places only: [`CONTEXT.md`](../CONTEXT.md) defines the terms, and
the code defines what happens. The current Overview and Blog design is
[the 2026-09-18 Overview scene layout design](superpowers/specs/2026-09-18-overview-scene-layout-design.md)
and [the 2026-09-18 figure library consolidation design](superpowers/specs/2026-09-18-figure-library-consolidation-design.md).
Read those before changing generation code; do not restate them here.

Some identifiers keep the product's earlier name on purpose, because installed apps and saved
data depend on them: the Keychain service `org.papers-to-kindle.provider` in `papers/settings.py`,
the health identity `papers-to-kindle` in `app/server.py`, and `app/macos/PapersToKindle.swift`.
Renaming any of them needs a migration.

Rebuild `papers/html-snapshot` after changing `papers/HTMLSnapshot.swift`. With the Command Line
Tools 26.x compiler, use the 15.4 SDK to avoid the known Swift module-version mismatch:
`xcrun swiftc -sdk /Library/Developer/CommandLineTools/SDKs/MacOSX15.4.sdk -O papers/HTMLSnapshot.swift -o papers/html-snapshot`.

## Find the relevant code

| Question | Start here |
| --- | --- |
| How does the Mac app start the reader? | `app/macos/PapersToKindle.swift`, the main file: service start, health check, navigation policy, downloads, opening a Paper's PDF outside the app, `localxiv://import` links, and Sparkle. Then `launch.command` |
| How does the Mac app draw its window? | `app/macos/Shell.swift` decodes the Chrome state, sends commands to the page, and holds the reader's find bar. `Sidebar.swift`, `Toolbar.swift`, `Menus.swift`, `ReadingPopover.swift`, and `SettingsWindow.swift` draw from that state. `Automation.swift` is the test harness and compiles only with `-D LOCALXIV_AUTOMATION` |
| How does the web app decide what the window shows? | `app/static/shell.js` holds the Chrome state, the command dispatcher, the key map, and the history, and draws its own sidebar and toolbar in a browser. `app.js` draws Home, the Library, search, Settings, and job notices. `reader.js` draws the reader. `appearance.js` maps Reading preferences to values |
| What happens when I import, export, or send a paper? | `Application.execute()` in `app/server.py` |
| Who owns retained Paper files and removal? | `Library.retain_paper()` and `remove_paper()` in `papers/library.py` |
| Where is the complete conversion recovery order? | `convert_import()` in `papers/convert.py` |
| How is an export format selected and checked? | `artifact()` in `papers/exports.py`, shared by export and send jobs |
| Where is conversion isolated from the app? | `papers/convert.py` starts the sandboxed `papers/worker.py` process |
| Where are TeX repairs and Pandoc conversion implemented? | `convert_source()` in `native/host.py` |
| How are reader pages and EPUBs assembled? | `papers/document.py` |
| Where are papers, jobs, and settings stored? | `papers/library.py`; provider keys use `papers/settings.py` |
| How is an Overview planned and drawn? | `OverviewWorkflow` in `papers/overview_workflow.py`, then `Figure` in `papers/figures/`; `app/static/app.js` displays it |
| How is a Blog generated? | `BlogWorkflow` in `papers/blog_workflow.py`; both workflows share `papers/coordinator.py` and draw through `papers/figures/` |
| How does a model learn the drawing vocabulary? | `card()` in `papers/figures/schema.py`, generated from the `field_docs` of each node class in `papers/figures/nodes.py` |
| What gets shipped in the DMG? | `app/macos/build-release.py` selects app files; `bundle_runtime.py` assembles external tools |

`convert_import()` owns the app's recovery order: Pandoc, arXiv HTML, LaTeXML, then the original PDF. It skips source engines when source retrieval failed and retains attempt diagnostics across worker runs. HTML retrieval happens outside the sandbox; each conversion attempt stays isolated. EPUB-only evaluations use the same recovery path with `epub_only=True` and stop before PDF. Calling `convert_paper()` directly without a mode still tries only Pandoc and LaTeXML for source diagnostics.

`Library.retain_paper()` promotes both successful and failed imports into owned Paper storage, preserving a ready Paper when a retry fails or falls back to PDF. Unchanged evidence keeps saved explanation files alongside the fresh import files, so retrying can repair missing originals without breaking overview exports. File promotion rolls back if saving the records fails. Removal also accepts failed Papers retained by older builds under `jobs/`, but only when a matching terminal import job proves ownership. Export code never decides where a Paper is retained.

## Check changes

Tests are component end-to-end tests: each one runs a whole component through its public entry point, such as `overview_workflow.generate`, `blog_workflow.generate`, or the server's job API. Write no unit tests of private helpers. Tests are not tracked in git; keep them under `tests/`. Run them from the repository root:

```sh
.venv/bin/python -m unittest discover -s tests
```

Check a front-end change by driving the running app in a browser.

Check a change to the Mac app's window with `tools/native_shot.py`, because AppKit draws the sidebar, the toolbar, and the menus, and a browser shows none of them. The tool builds the app with `-D LOCALXIV_AUTOMATION`, installs it under `--out`, runs it on a copy of `--library` with its own service, follows the steps in `--steps`, and prints the path of each snapshot and dump. It stops the scratch service at the end, and it refuses a library whose service is running.

```sh
python3 tools/native_shot.py --library LIBRARY --steps steps.json --out OUT
```

`python3 tools/native_shot.py --help` lists the steps. Three facts are not in that list:

- A `state` step gives the shell a Chrome state as the page would post it, so you can check the window without the web app. The page also posts its own states. To keep yours, first run `window.webkit.messageHandlers.shell.postMessage = () => {}` in a `js` step.
- The scratch app comes to the front during the run, because menus, keys, and clicks act on the key window.
- A snapshot can draw a selected view-switch segment or a selected sidebar row as a shape with no label. Read the state of those controls in a `dump` file.

For packaging changes, also run the [moved-app verifier](macos-release.md#verify-the-artifact). For conversion changes, compare real paper output with a known build, including equations, tables, figures, references and reading order. A valid EPUB alone does not establish that its content was preserved.

## Compare models on one Overview or Blog

`tools/overview_run.py` generates an Overview for one library paper with any provider and model and prints the request count, tokens, reasoning tokens, seconds, density, and the PNG path. It saves nothing to the library. `--provider` is `deepseek` (default), `gemini` (Google AI Studio), `openrouter`, `openai`, `claude`, or `custom` with `--endpoint`. The key is read from `.env` at the repository root under the provider's usual name (`DEEPSEEK_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) or the name passed with `--api_key`, and otherwise from the Keychain entry the app saved for that endpoint. `--out DIR` copies each run's PNG and editable SVG into that directory as `{provider}_{paper}.png` and `.svg`, with `_{model}` appended when one invocation compares several models; a later run with the same name replaces the file. `--kind blog` runs the Blog instead and prints each figure's status and correction count; `--out` then writes the article as Markdown and each accepted figure's PNG. `--library DIR` reads the paper from another library, such as the isolated library that `app.server --data-dir` creates, instead of the app library. `--reasoning auto|low|medium|high` sets the reasoning effort of every request, as the app's Reasoning effort setting does; the default, auto, is low for an Overview and medium for a Blog.

```
.venv/bin/python tools/overview_run.py --paper "Attention" --model deepseek-flash --model deepseek-reasoner
.venv/bin/python tools/overview_run.py --paper "Probabilities" --provider gemini --model gemini-2.5-pro
.venv/bin/python tools/overview_run.py --paper "Black-Box" --provider openrouter --api_key OR_KEY --model anthropic/claude-sonnet-4.5
```
