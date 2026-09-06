# macOS release verification

This reference records local checks for v0.0.2 on Apple Silicon running macOS 26.6.2, performed on 2026-09-06. The supported release target is Apple Silicon with macOS 26 or newer.

Each release includes `verification.json`, `release.json`, `runtime-manifest.json`, and `SHA256SUMS`. Those files identify the artifact, source revision, tool versions, and checks for that build.

## Passed local checks

- App signature validation with `codesign --verify --deep --strict`.
- DMG creation and integrity validation with `hdiutil verify`.
- Startup after copying the bundled app into a different path containing spaces.
- Authenticated local service access and reader loading against a temporary library.
- Sandboxed conversion of a local TeX fixture, with EPUB validation for the generated profiles.
- PDF text extraction and SVG overview rendering from bundled tools.
- Installed-app startup after replacement, with the new service identity confirmed and the existing three-paper library preserved.
- Desktop and mobile Settings layouts, light and dark themes, saved preferences, cancellation, and validation of fields inside collapsed sections.
- Seven release and version-handoff regression tests, plus the affected generation, export, and reader checks.
- GitHub Actions workflow validation with `actionlint`.

The artifact verifier sends no email and makes no AI provider calls. The figure-rendering check runs through the bundled runtime. The conversion workers and independent runtime smoke checks deny access to developer tool paths.

To repeat the artifact checks, use the commands in [Verify the artifact](../macos-release.md#verify-the-artifact).

## Not verified

- Apple Developer ID signing, notarization, and Gatekeeper acceptance. Preview builds use ad hoc signatures.
- Installation on an independent clean Mac.
- Intel Macs or macOS versions older than 26.
- Live-model narrative quality and actual Kindle delivery for v0.0.2.
- Mail and Keychain permission behavior under a Developer ID signature.

## Dependency source inventory

The source collector verifies downloaded inputs against recorded checksums where available. Its inventory retains `correspondingSourceComplete: false` until the remaining source review is complete.

Outstanding items include Pandoc's embedded Haskell dependency versions, installed-build provenance for some patches, EPUBCheck dependency JAR sources, and replacement or relinking requirements. Download counts alone do not establish complete corresponding source. See [dependency licenses and source distribution](../dependency-licenses.md).
