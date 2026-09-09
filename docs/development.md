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

To test the reader without installing the native app, start an isolated library:

```sh
python3 -m app.server --port 8765 --data-dir /tmp/localxiv-dev --open
```

Keep release builds separate from the development install. Follow [Build and publish a macOS DMG](macos-release.md) to create a portable app.

## Find the relevant code

| Question | Start here |
| --- | --- |
| How does the Mac app start the reader? | `app/macos/PapersToKindle.swift`, then `launch.command` |
| What happens when I import, export, or send a paper? | `Application.execute()` in `app/server.py` |
| Where is conversion isolated from the app? | `papers/convert.py` starts the sandboxed `papers/worker.py` process |
| Where are TeX repairs and Pandoc conversion implemented? | `convert_source()` in `native/host.py` |
| How are reader pages and EPUBs assembled? | `papers/document.py` |
| Where are papers, jobs, and settings stored? | `papers/library.py`; provider keys use `papers/settings.py` |
| How are overviews generated and displayed? | `papers/ai.py` generates them; `papers/overview.py` validates them; `app/static/app.js` displays them |
| What gets shipped in the DMG? | `app/macos/build-release.py` selects app files; `bundle_runtime.py` assembles external tools |

The app's import order is Pandoc, arXiv HTML, LaTeXML, then the original PDF. `Application.execute()` starts the first attempt; `source_fallback()` and `pdf_fallback()` handle recovery. Calling `convert_paper()` directly without a mode tries only the source engines, Pandoc and LaTeXML. A source-only test therefore does not exercise the app's full recovery path.

`native/host.py` serves both the browser extension and the desktop converter. In `papers/worker.py`, the Pandoc path replaces two functions on that imported module to use sandbox-compatible graphics tools. These replacements stay inside the worker process. Account for both callers before changing this code.

## Check changes

Run the Python and browser checks from the repository root:

```sh
python3 -m unittest discover -s tests
node tests/test_app_ui.js
node tests/test_extension.js
```

For packaging changes, also run the [moved-app verifier](macos-release.md#verify-the-artifact). For conversion changes, compare real paper output with a known build, including equations, tables, figures, references and reading order. A valid EPUB alone does not establish that its content was preserved.
