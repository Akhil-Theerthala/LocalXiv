<p align="center">
  <img src="app/assets/icon.png" alt="LocalXiv logo" width="112" height="112">
</p>

<h1 align="center">LocalXiv</h1>

Read arXiv papers on your Mac or Kindle. LocalXiv saves papers from arXiv and alphaXiv to a local library and converts them to EPUB. AI overviews and related-paper recommendations are optional.

**[Download v0.0.4 for Mac](https://github.com/Akhil-Theerthala/LocalXiv/releases/download/v0.0.4/LocalXiv-0.0.4-macOS26-arm64-unsigned-local.dmg)**

Apple Silicon · macOS 26 or newer

## Install LocalXiv

1. Download and open the DMG.
2. Drag **LocalXiv** into **Applications**.
3. Open **LocalXiv** from **Applications**.

The app includes its conversion tools. You do not need Homebrew, Python, or Terminal setup.

This preview is ad hoc signed and is not notarized by Apple. macOS may block the first launch. See the [release notes, checksums, and source archives](https://github.com/Akhil-Theerthala/LocalXiv/releases/tag/v0.0.4).

To replace an older version, follow the [update instructions](docs/macos-release.md#update-an-installed-app).

## Read a paper

1. Paste an arXiv or alphaXiv link into LocalXiv.
2. Open the saved paper in the reader.
3. Adjust the font, text size, margins, or appearance to suit your reading.

If EPUB conversion fails, LocalXiv opens the original PDF when it is available. Check equations, tables, and figures against the original when fidelity matters.

Papers and settings are stored in `~/Library/Application Support/LocalXiv/library`. Removing the app leaves this library in place. To delete an individual paper, open Library, choose Remove and confirm. This also deletes its saved files, overview and chat history; exported copies are unaffected.

## Generate an overview

1. Open **Settings**, then expand **AI connection**.
2. Enter your provider endpoint, model, and API key.
3. Select **Test connection**, then **Save settings**.
4. Open a paper and select **Generate overview**.

Under **Overviews**, choose the writing style and length. The defaults are **Casual** and **Medium**. Overviews include explanations and diagrams; changing these settings affects the next overview you generate.

Once AI is configured, new imports generate an overview by default. Turn off **Generate an overview after importing** to generate them manually.

API keys are stored in macOS Keychain. Overviews send paper text to your provider, and related-paper recommendations also use that provider. Reading and EPUB export work without AI.

## Take a paper to Kindle

Open **Send to Kindle** in the reader, choose the paper, overview, or both, then select **Download EPUB**. Papers kept as PDFs offer **Download PDF** instead.

To send through Mail, add your Kindle email under **Settings → Kindle delivery**. Configure Mail and approve its sending address in your Amazon account first. Check your Kindle to confirm delivery.

## Build and contribute

- [Run from source and find the relevant code](docs/development.md)
- [Build, verify, and publish a DMG](docs/macos-release.md)
- [Changes in v0.0.4](docs/releases/v0.0.4.md)
- [Verification results and limits](docs/verification/macos-release.md)
- [Dependency licenses and source distribution](docs/dependency-licenses.md)

LocalXiv's original source is licensed under [AGPL-3.0-or-later](LICENSE). Third-party components retain their own licenses, listed in [NOTICE](NOTICE).
