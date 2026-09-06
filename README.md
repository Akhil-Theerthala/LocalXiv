# LocalXiv

A local macOS paper library for importing arXiv and alphaXiv links, reading retained papers, generating illustrated technical overviews, finding related papers, and exporting or sending EPUBs to Kindle.

## Install the local app

For portable DMG builds, signing, and release validation, see [macOS distribution](docs/macos-release.md). The initial portable target is Apple Silicon on macOS 26+. The source installation below remains available for development. Local ad hoc builds are not notarized public releases.

Install Apple Command Line Tools with `xcode-select --install` if needed. The installer compiles a small native macOS window using AppKit and WebKit; it does not require Electron. Install the conversion tools and JavaScript dependencies, then create the app bundle:

```sh
brew install python pandoc latexml librsvg ghostscript epubcheck node
cd /path/to/arxiv-paper-to-kindle
npm ci --ignore-scripts --omit=dev
./install-app.sh
open "$HOME/Applications/LocalXiv.app"
```
