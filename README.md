<p align="center">
  <img src="app/assets/icon.png" alt="LocalXiv logo: a stack of papers" width="128" height="128">
</p>

<h1 align="center">LocalXiv</h1>

<p align="center">Read research papers on your Mac. Keep them in your library. Take them to Kindle.</p>

<p align="center">
  <a href="https://github.com/Akhil-Theerthala/LocalXiv/releases/download/v0.0.1/LocalXiv-0.0.1-macOS26-arm64-unsigned-local.dmg"><strong>Download v0.0.1 for Mac</strong></a><br>
  Apple Silicon · macOS 26 or newer · Unsigned preview
</p>

LocalXiv turns arXiv and alphaXiv links into a local paper library, with a built-in reader, optional AI overviews, and EPUB export.

## What you can do

- Save papers and read them locally with adjustable typography and light or dark appearance.
- Generate illustrated overviews and find related papers using your own AI provider.
- Export EPUBs with equations rendered for Kindle, or send them through macOS Mail.
- Read the original PDF when a paper cannot be converted to EPUB.

Your library stays on your Mac, and API keys are stored in macOS Keychain. AI features are optional; generating an overview sends paper text to your configured provider.

## Install

Download the [v0.0.1 DMG](https://github.com/Akhil-Theerthala/LocalXiv/releases/download/v0.0.1/LocalXiv-0.0.1-macOS26-arm64-unsigned-local.dmg), open it, and drag LocalXiv into Applications. It targets **Apple Silicon on macOS 26 or newer** and bundles the conversion tools, so no Terminal setup is needed.

This is an unsigned preview: Apple Developer ID signing and notarization are pending, so macOS may block it on first launch. Source archives, checksums, and known limitations are on the [release page](https://github.com/Akhil-Theerthala/LocalXiv/releases/tag/v0.0.1). See the [macOS release guide](docs/macos-release.md) for build and update details.

### Run from source

Install Apple Command Line Tools with `xcode-select --install` if needed. The installer compiles a small native macOS window using AppKit and WebKit; it does not require Electron. Install the conversion tools and JavaScript dependencies, then create the app bundle:

```sh
brew install python pandoc latexml librsvg ghostscript epubcheck node
cd /path/to/arxiv-paper-to-kindle
npm ci --ignore-scripts --omit=dev
./install-app.sh
open "$HOME/Applications/LocalXiv.app"
```

## Get started

1. Open LocalXiv and paste an arXiv or alphaXiv paper link.
2. Read the paper in the app, or configure an AI provider in Settings to generate an overview.
3. Export an EPUB, or add your Kindle address to send it through Mail. For email delivery, configure Mail and add its sender to Amazon's approved personal-document senders.

Conversion depends on the paper's source and LaTeX template. Check figures, equations, and references when fidelity matters; the original PDF remains available when conversion falls back.

## Development and releases

- [Build and sign a DMG](docs/macos-release.md)
- [GitHub Actions build workflow](.github/workflows/macos-build.yml)
- [Packaging verification and known limits](docs/verification/macos-release.md)
- [Dependency licenses and source distribution](docs/dependency-licenses.md)

## License

LocalXiv's original source is licensed under [AGPL-3.0-or-later](LICENSE). Third-party components retain their own licenses; see [NOTICE](NOTICE).
