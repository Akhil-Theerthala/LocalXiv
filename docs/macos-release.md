# Build and publish a macOS DMG

The portable app targets Apple Silicon and macOS 26 or newer. For installation, start with the [README](../README.md). For release scope, see the [v0.0.2 notes](releases/v0.0.2.md).

## Update an installed app

1. Let active import, overview, export, and delivery jobs finish.
2. Restart the Mac to stop the old background service. Quitting the app window alone leaves that service running.
3. Open the new DMG.
4. Replace **LocalXiv** in **Applications**.
5. Open the copy in **Applications**.

Papers and settings remain in `~/Library/Application Support/LocalXiv/library`. API keys remain in Keychain. Automatic updates are not included.

## Build a portable app

Use an Apple Silicon Mac running macOS 26 or newer. Install Apple Command Line Tools and Homebrew first.

1. Install the build tools:

```sh
brew install python@3.14 pandoc latexml librsvg ghostscript epubcheck node
```

2. Install the locked JavaScript dependencies from the repository root:

```sh
npm ci --ignore-scripts --omit=dev
```

3. Commit the source you intend to distribute. A clean checkout lets the builder include an exact source archive.
4. Build the app and DMG:

```sh
python3 app/macos/build-release.py --version 0.0.2 --build-number 5
```

The output is `dist/LocalXiv-0.0.2-macOS26-arm64-unsigned-local/`. The `unsigned-local` suffix means ad hoc signed, without Apple Developer ID signing or notarization.

To repeat a build, choose a new `--output` directory. The builder refuses to overwrite completed output. To reuse an assembled runtime, pass `--runtime /path/to/runtime`. The builder copies and checks that runtime again.

The runtime manifest records the installed tool versions. Homebrew dependencies are not locked across builds. Keep the matching manifest and dependency source bundle with each release.

## Verify the artifact

Run the verifier against the built app:

```sh
python3 app/macos/verify-release.py \
	dist/LocalXiv-0.0.2-macOS26-arm64-unsigned-local/LocalXiv.app \
	--report dist/verification.json
```

The verifier moves the app to a path with spaces, checks its signature, starts an isolated library, and converts a local paper. It also checks PDF text extraction and SVG figure output. Conversion runs with access to Homebrew and nvm blocked.

Read the generated report before publication. These checks do not test installation on a separate Mac, live AI responses, or Mail delivery. The [verification reference](verification/macos-release.md) records those limits.

## Build with GitHub Actions

1. Open the repository's **Actions** page.
2. Select **Build and publish macOS DMG**.
3. Select **Run workflow** and enter the version.
4. Download the verified artifact from the completed run.

Manual runs retain artifacts for 14 days and do not publish a release. The workflow uses GitHub's [macOS 26 arm64 runner](https://docs.github.com/en/actions/reference/runners/github-hosted-runners).

## Publish a preview

1. Commit and push the source, version metadata, and release notes.
2. Create a version tag on that commit:

```sh
git tag -a v0.0.2 -m "LocalXiv 0.0.2"
```

3. Push the tag:

```sh
git push origin v0.0.2
```

4. Check the workflow run on GitHub.

The tag workflow builds the app, verifies it, collects dependency source inputs, and publishes a prerelease with all assets. Source-collection errors stop publication. An unfinished draft can be retried. Use a new version tag for an already published release.

The workflow uses the automatic `GITHUB_TOKEN`. Release write permission is limited to the publish job. It requires no personal access token or Apple credentials. Review the [dependency source inventory](dependency-licenses.md) before treating a build as a completed stable distribution.

## Sign and notarize a release

1. Install your Developer ID Application certificate and private key in Keychain.
2. Confirm the identity with `security find-identity -v -p codesigning`.
3. Create a `notarytool` Keychain profile using [Apple's notarization instructions](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution).
4. Build with the identity and profile:

```sh
python3 app/macos/build-release.py \
	--version 0.0.2 --build-number 5 \
	--identity 'Developer ID Application: YOUR DEVELOPER NAME (TEAMID)' \
	--notarize --keychain-profile localxiv-notary
```

The `--notarize` option uploads the signed app and DMG to Apple. The builder requires accepted results, staples the tickets, and checks the app with Gatekeeper. Keep credentials out of the repository.

Test Mail permissions and Keychain access on the signed build. An ad hoc build does not establish how those permissions behave with a Developer ID signature.
