# Portable macOS build verification

Date: 2026-09-06. Build host: Apple Silicon, macOS 26.6.2. Initial supported target: arm64 macOS 26 or newer.

The existing desktop branch and pending LocalXiv fixes were merged into main at `56e091d` before release packaging began. Packaging was implemented separately and reviewed before integration. The unrelated trailer artwork was left unchanged.

## Observed checks

- Full Python suite: 221 tests passed, one skipped. Tests needing HTTP servers, macOS conversion sandbox, and Quick Look ran outside the tool sandbox. The first restricted run failed because those OS services were unavailable; it was not reported as a passing run.
- Extension JavaScript: 63 tests passed. Reader/setup UI checks and shell syntax checks passed.
- Runtime moved to a path containing spaces, with reads denied under Homebrew, `/usr/local`, and the developer's nvm directory: Python TLS/native extensions, Pandoc, LaTeXML mathematics, Java/EPUBCheck, SVG rasterization and Ghostscript PDF output passed.
- Bundled app copied to a new path and its service launched with a temporary library: authenticated health and reader HTTP checks passed.
- Actual bundled conversion worker with developer-tool paths denied: a local TeX fixture produced both validated EPUB profiles. Original app signature remained valid after checks.
- Bundled overview renderer produced PNG/SVG/editable scene files. PDFKit fallback extracted text from a local PDF. These fixture checks used no live provider or Mail delivery. The figure supervisor itself was not under the developer-path denial; the bundled runtime's independent smoke checks and the EPUB/PDF workers were.
- Native AppKit window launched with an isolated temporary home: optional setup and the rendered home screen were inspected. This caught a fixed-port conflict; the release now asks the OS for a free port. The test window and its temporary service were stopped afterwards.
- DMG creation and `hdiutil verify` passed. Local app signatures passed `codesign --verify --deep --strict`. These are ad hoc signatures, not Developer ID or notarization results.

The final local artifact is built under `dist/final/`. Its `release.json` identifies the exact source revision and whether runtime source files were dirty. `SHA256SUMS` covers the DMG, source archive, and release metadata. The standalone verifier emits an additional JSON report after the final build.

## Review fixes

Review found that moving the old library left stored absolute paper paths behind. Startup now repairs only missing paths beneath the exact old default root when the relocated directory exists. A real SQLite regression covers saved EPUB access, unrelated-path preservation, rollback, retry, and repeated startup.

Review also found that a verification subprocess could write Python bytecode into sealed app resources. Verification now disables bytecode writes and checks the signature again after conversion.

Python framework signing initially failed after symlink normalization. Preserving its canonical relative `Versions/Current` links fixed the issue. The runtime now signs and verifies nested containers after their Mach-O files.

The first TLS bundle came from the build machine's trust store. It was replaced with the exact versioned Mozilla CA bundle from the Homebrew keg, with a recorded checksum, source and MPL-2.0 license. Locally added trust roots are not shipped.

## Remaining release gates

No Developer ID signing identity is installed. Developer ID signing, Apple's notarization service, Gatekeeper acceptance, signed Mail permissions, and signed Keychain behavior have not been verified. The signing/notarization code is implemented but cannot be called verified until exercised with an actual identity.

This is not a test on a genuinely clean Mac. Independent-machine installation, Intel, older macOS versions, live AI output and real Kindle arrival are unverified.

The source collector downloaded 186 of 186 recorded source inputs without errors, covering 49 runtime components. Its inventory deliberately retains `correspondingSourceComplete: false`. Remaining gaps include Pandoc's unrecorded embedded Haskell dependency versions, exact installed-build provenance of Python/glib patches, EPUBCheck dependency JAR sources and additional preferred-source/relinking checks. See [dependency licensing](../dependency-licenses.md). A source-input download count alone does not establish complete corresponding source.

No Git remote is configured, so the GitHub workflow has not run and no assets or source were published. The manual workflow builds local-test artifacts only; it does not silently publish a release.
