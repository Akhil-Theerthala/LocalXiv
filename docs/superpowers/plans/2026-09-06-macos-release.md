# LocalXiv macOS release plan

Goal: produce a portable Apple Silicon macOS app and a DMG, with a repeatable signing and notarization path. The user approved desktop packaging and asked to merge the existing desktop work into main first. iPhone, sync, cloud hosting, and automatic updates are outside this release.

Architecture: retain the AppKit/WebKit window and Python service. Ship immutable runtime code and conversion dependencies inside Contents/Resources; keep the library in Application Support. Resolve bundled paths at runtime. Optional MacTeX remains optional. Target macOS 26 for the initial artifact because its native dependencies were built for that platform. Do not claim older-system compatibility without testing it.

- [x] Review and commit the pending desktop fixes; fast-forward main. Completed at 56e091d. Leave untracked trailer artwork alone.
- [ ] Build a relocated dependency runtime in app/macos/bundle_runtime.py. Include Python, Node, Pandoc, LaTeXML, librsvg, Ghostscript and EPUBCheck/Java with dependent libraries, data and license notices. Reject unresolved external libraries and symlinks. Run tool smoke checks with a restricted PATH.
- [ ] Update PapersToKindle.swift and launch.command to locate the bundled runtime, keep user data external, migrate the old library under its lock, and support a moved app without development tools. Preserve the source-install workflow.
- [ ] Add app/macos/build-release.py and release entitlements. Build a versioned app, sign nested executable code, create a DMG and checksums. Unsigned local builds must be named explicitly. Require Developer ID identity for distribution builds and notarization credentials for notarized output.
- [ ] Add a release validation script that launches the moved bundled service with a temporary library, checks health and resource serving, and exercises conversion without Homebrew paths. Do not send Mail or use provider credentials during checks.
- [ ] Document build prerequisites, tested platform, dependency provenance and licenses, signing and notarization, install/update behavior and remaining external gates. Add a manual GitHub Actions workflow that produces artifacts but does not publish without explicit release authorization.
- [ ] Run existing native checks and focused new packaging checks, build and inspect the actual artifact, and record results honestly. Apple signing identities and a Git remote are currently absent. Public signing, Gatekeeper approval and upload remain external gates until supplied.

Validation must distinguish local ad hoc signing from Developer ID/notarization, restricted-environment tests from a genuinely clean Mac, and artifact export from actual Kindle delivery.
