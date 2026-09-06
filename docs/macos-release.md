# macOS distribution

The initial portable build targets Apple Silicon and macOS 26 or newer. It contains the local service, reader, Python, Node, Pandoc, LaTeXML, librsvg, Ghostscript, and EPUBCheck with Java. Users do not need Homebrew, npm, Python, or Command Line Tools. MacTeX is not included; papers requiring unavailable TeX packages may fall back to the original PDF. The optional Chrome extension is distributed separately.

[v0.0.1 is available as a public preview](https://github.com/Akhil-Theerthala/LocalXiv/releases/tag/v0.0.1). It has an ad hoc signature, without Developer ID signing or Apple notarization. The release includes the DMG, exact app source, collected dependency source inputs, inventory, verification report and checksums. The source inventory remains marked for review; see the release notes for the outstanding provenance questions.

## Install and update

Open the release DMG, drag LocalXiv to Applications, and launch the copy in Applications. Configure the optional AI provider and Kindle address in Settings. Mail must be configured for email delivery, and its sender must be approved in Amazon's Kindle settings. Exporting files does not require Mail or an API key.

The app keeps papers and settings in `~/Library/Application Support/LocalXiv/library`; API keys stay in Keychain. An older `PapersToKindle/library` is moved only when the destination does not exist and neither library is in use. Separate existing libraries are never merged. Deleting the app leaves the library intact.

Closing the window or quitting leaves the current background service running so jobs can finish. Before replacing the app, let jobs finish and restart the Mac to stop the old service. Then replace the app and open the new copy. If an older build is still serving the library, the new app reports it instead of silently loading old code. Automatic updates are not included in this release.

## Build locally

Build on Apple Silicon with macOS 26+, Apple Command Line Tools, Homebrew and Node. Only developers need these prerequisites:

```sh
brew install python@3.14 pandoc latexml librsvg ghostscript epubcheck node
npm ci --ignore-scripts --omit=dev
python3 app/macos/build-release.py --version 0.1.0-beta.1
```

The builder copies the installed dependency versions and records them in `Contents/Resources/runtime/manifest.json`. It relocates dynamic libraries and executable wrappers, includes notices and certificates, and checks tools with access to Homebrew and nvm denied by the macOS sandbox. The native window is compiled before signing. The source checkout is never needed at runtime.

The default output is under `dist/LocalXiv-0.1.0-beta.1-macOS26-arm64-unsigned-local/`. It includes the app, DMG, release metadata and SHA-256 checksum. "Unsigned local" means ad hoc signed for testing, without an Apple Developer ID identity or notarization. It is not a public release and cannot demonstrate Gatekeeper acceptance.

The build refuses to overwrite a completed output. Use another output directory for a repeated build. `--runtime /path/to/runtime` reuses a previously assembled runtime by copying and checking it. Builds use the installed versions, not a reproducible dependency lock; keep the runtime manifest and corresponding source bundle with each release.

Run the actual artifact check:

```sh
python3 app/macos/verify-release.py \
  dist/LocalXiv-0.1.0-beta.1-macOS26-arm64-unsigned-local/LocalXiv.app \
  --report dist/verification.json
```

This copies the app into a different path containing spaces, verifies its code signature, starts the service against a temporary library, loads the reader, and performs a real sandboxed conversion with both EPUB profiles checked. Homebrew and nvm paths are denied. It sends no email and uses no AI provider. A test on a genuinely clean Mac is still required before claiming clean-machine compatibility.

## Sign and notarize

Enroll in the Apple Developer Program and install a Developer ID Application certificate with its private key in Keychain. Confirm availability using `security find-identity -v -p codesigning`. Set up a `notarytool` Keychain profile using Apple's documented workflow; do not put private keys, certificate passwords or app-specific passwords in this repository.

```sh
python3 app/macos/build-release.py \
  --version 0.1.0 --build-number 1 \
  --identity 'Developer ID Application: YOUR DEVELOPER NAME (TEAMID)' \
  --notarize --keychain-profile localxiv-notary
```

This explicitly uploads the signed app and DMG to Apple. Nested executable code is signed before enclosing bundles, with the hardened runtime enabled. Node and Java receive the JIT entitlement; the app and Python receive the Apple Events entitlement used for Mail. Both notarization submissions must report `Accepted`. The builder staples and validates tickets and checks the app with Gatekeeper. Signing without `--notarize` produces a clearly named signed but unnotarized artifact.

Signed Mail automation and Keychain access must be checked on the signed build. Success of local ad hoc builds does not establish permission behavior of a Developer ID build. No signing identity was available during the initial packaging work.

Apple references: [Developer ID](https://developer.apple.com/developer-id/), [notarization](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution), [notarization troubleshooting](https://developer.apple.com/documentation/security/resolving-common-notarization-issues).

## Publish through GitHub

The `Build and publish macOS DMG` workflow uses the same builder and moved-app verification as the local build. It runs on GitHub's macOS 26 arm64 runner.

- **Manual build:** open Actions, select the workflow, choose Run workflow, and enter a version such as `0.0.2`. The verified DMG, app source, runtime manifest, report, and checksums are retained as a workflow artifact for 14 days. This does not publish a GitHub Release.
- **Publish a preview:** commit and push the intended source and workflow, then push a version tag such as `v0.0.2`. The workflow builds the tagged commit, checks the app, collects matching dependency source inputs, and publishes a GitHub prerelease with all assets. Source-collection errors stop publication.
- **Retries:** an unfinished draft can be resumed. An already published release is never overwritten; use a new version tag.

The workflow uses the repository's automatic `GITHUB_TOKEN`, with release write permission limited to the publish job. No personal access token or Apple credentials are required. Releases keep the existing ad hoc signing status and are marked as previews, not notarized stable releases. The generated dependency inventory still requires review.

```sh
# After committing and pushing the version you want to distribute:
git tag -a v0.0.2 -m "LocalXiv 0.0.2"
git push origin v0.0.2
```

Runner reference: [GitHub-hosted macOS runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners). Publication uses the [GitHub CLI release commands](https://cli.github.com/manual/gh_release_create).

Before a stable release, complete the signed-build and clean-Mac checks and the dependency source review in [dependency licensing](dependency-licenses.md). Attach the notarized DMG, SHA256SUMS, the exact LocalXiv source and corresponding dependency sources to the same versioned GitHub Release. Keep release notes explicit about Apple Silicon/macOS 26 support and conversion limits. GitHub-generated source archives alone do not contain bundled third-party sources. The preview label does not resolve dependency licensing or source obligations.

The GitHub remote is `git@github.com:Akhil-Theerthala/LocalXiv.git`. The v0.0.1 preview was published at the owner's request. Its anonymous direct-download URL and uploaded checksums were verified after publication.
