<p align="center">
  <img src="app/assets/icon.png" alt="LocalXiv logo" width="112" height="112">
</p>

<h1 align="center">LocalXiv</h1>

LocalXiv saves arXiv and alphaXiv papers to a local library on your Mac. Read the full paper, generate an illustrated overview, or export an EPUB for Kindle.

**[Download v0.0.2 for Mac](https://github.com/Akhil-Theerthala/LocalXiv/releases/download/v0.0.2/LocalXiv-0.0.2-macOS26-arm64-unsigned-local.dmg)**

Apple Silicon · macOS 26 or newer

## Install LocalXiv

1. Download and open the DMG.
2. Drag **LocalXiv** into **Applications**.
3. Open **LocalXiv** from **Applications**.

The app includes its conversion tools. You do not need Homebrew, Python, or Terminal setup.

This preview is ad hoc signed and is not notarized by Apple. macOS may block the first launch. See the [release notes, checksums, and source archives](https://github.com/Akhil-Theerthala/LocalXiv/releases/tag/v0.0.2).

To replace an older version, follow the [update instructions](docs/macos-release.md#update-an-installed-app).

## Read a paper

1. Paste an arXiv or alphaXiv link into LocalXiv.
2. Open the saved paper in the reader.
3. Adjust the font, text size, margins, or appearance to suit your reading.

If conversion fails, LocalXiv keeps the original PDF available. Check equations, tables, and figures against the original when fidelity matters.

## Generate an overview

1. Open **Settings**, then expand **AI connection**.
2. Enter your provider endpoint, model, and API key.
3. Select **Test connection**, then **Save settings**.
4. Open a paper and select **Generate overview**.

Under **Overviews**, choose the language and article length independently. The defaults are **Casual** and **Medium**. Overviews develop a narrative with technical detail and SVG figures. Changes apply when you generate or regenerate an overview.

Your library stays on your Mac, and API keys are stored in macOS Keychain. AI overviews send paper text to your provider. Related-paper recommendations also use the provider. Reading and EPUB export work without AI.

## Take a paper to Kindle

Open **Send to Kindle** in the reader to download an EPUB. To send it through Mail, add your Kindle email under **Settings → Kindle delivery**. Configure Mail and approve its sending address in your Amazon account first.

## Build and contribute

- [Run from source](docs/development.md)
- [Build, verify, and publish a DMG](docs/macos-release.md)
- [Changes in v0.0.2](docs/releases/v0.0.2.md)
- [Verification results and limits](docs/verification/macos-release.md)
- [Dependency licenses and source distribution](docs/dependency-licenses.md)

LocalXiv's original source is licensed under [AGPL-3.0-or-later](LICENSE). Third-party components retain their own licenses, listed in [NOTICE](NOTICE).
