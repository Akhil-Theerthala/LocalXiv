<p align="center">
  <img src="app/assets/icon.png" alt="LocalXiv logo" width="112" height="112">
</p>

<h1 align="center">LocalXiv</h1>

Read arXiv papers on your Mac or Kindle. LocalXiv saves papers from arXiv and alphaXiv to a local library and converts them to EPUB. AI overviews and related-paper recommendations are optional.

**[Download v0.0.8 for Mac](https://github.com/Akhil-Theerthala/LocalXiv/releases/download/v0.0.8/LocalXiv-0.0.8-macOS26-arm64-unsigned-local.dmg)**

Apple Silicon · macOS 26 or newer

## Install LocalXiv

1. Download and open the DMG.
2. Drag **LocalXiv** into **Applications**.
3. Open **LocalXiv** from **Applications**.

The app includes its conversion tools. You do not need Homebrew, Python, or Terminal setup.

This preview is ad hoc signed and is not notarized by Apple. macOS may block the first launch. See the [release notes, checksums, and source archives](https://github.com/Akhil-Theerthala/LocalXiv/releases/tag/v0.0.8).

To replace an older version, follow the [update instructions](docs/macos-release.md#update-an-installed-app).

## Read a paper

1. Paste an arXiv or alphaXiv link into LocalXiv.
2. Open the saved paper in the reader.
3. Adjust the font, text size, margins, or appearance to suit your reading.

If EPUB conversion fails, LocalXiv opens the original PDF when it is available. Check equations, tables, and figures against the original when fidelity matters.

Papers and settings are stored in `~/Library/Application Support/LocalXiv/library`. Removing the app leaves this library in place. To delete an individual paper, open Library, choose Remove and confirm. This also deletes its saved files, overview, blog and chat history; exported copies are unaffected.

## Generate an overview

1. Open **Settings**, then expand **AI connection**.
2. Enter your provider endpoint, model, and API key.
3. Select **Test connection**, then **Save settings**.
4. Open a paper and select **Generate overview**.

**Overview** explains the paper through HTML and SVG illustrations. The explanation adapts to the paper: architecture components, a method in action, or a survey's families and comparisons. Enable **Generate a visual overview after importing** in Settings to create one automatically. New installations leave this off; saved preferences are preserved.

Open **Blog** and select **Generate blog** for a longer explanation with cited prose and useful figures. Blog generation is manual. When a current, reviewed overview exists, the Blog can reuse its explanation and figures alongside the paper. Otherwise it generates directly from the paper. An overview image is never required to generate a Blog. Settings control its language and length.

Open **Share** beside the reader tabs to export the current view as EPUB or PDF. Overview also offers PNG and editable HTML source. Existing Excalidraw overviews retain their original assets until regenerated. Papers retained only as PDFs offer PDF export. Blog PDF export requires XeLaTeX, available through MacTeX.

API keys are stored in macOS Keychain. Overviews send paper text to your provider, and related-paper recommendations also use that provider. Reading and EPUB export work without AI.

## Take a paper to Kindle

Open **Share** and expand **Send to Kindle**. Choose the original paper, visual overview, blog, or paper and blog. Choose an EPUB profile and send through Mail. Papers retained as PDFs are sent in their original format.

To send through Mail, add your Kindle email under **Settings → Kindle delivery**. Configure Mail and approve its sending address in your Amazon account first. Check your Kindle to confirm delivery.

## Build and contribute

- [Run from source and find the relevant code](docs/development.md)
- [Build, verify, and publish a DMG](docs/macos-release.md)
- [Changes in v0.0.8](docs/releases/v0.0.8.md)
- [Verification results and limits](docs/verification/macos-release.md)
- [Dependency licenses and source distribution](docs/dependency-licenses.md)

LocalXiv's original source is licensed under [AGPL-3.0-or-later](LICENSE). Third-party components retain their own licenses, listed in [NOTICE](NOTICE).

Overview and Blog use a bounded smolagents ToolCallingAgent workflow to retrieve evidence, submit HTML/SVG, and review the result. Native WebKit produces static exports and checks layout. Model review checks claims against retained passages and can inspect rendered figures when vision review is enabled. See the [workflow diagram](docs/overview-workflow.html).
