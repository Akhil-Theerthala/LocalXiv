# Sparkle integration verification

Checked locally on 2026-09-10. Developer ID signing was not changed. No installed
app was replaced, no release was published, and no private key was sent to GitHub.

## Implemented

- Native Sparkle Check for Updates command and standard update UI.
- Sparkle 2.9.6 distribution pinned to its official SHA-256; framework, helper
  signing, runpath and license included in portable builds.
- Public trust key embedded in the app; private signing key in login Keychain
  under `localxiv-sparkle`.
- Signed feeds and signed archives verified before extraction.
- Authenticated idle-only service shutdown before update termination; active,
  queued or still-exiting cancelled jobs prevent shutdown. New submissions are
  refused after shutdown is reserved.
- Tagged release CI stages an unpublished draft. Local Keychain signing and
  optional publication use `app/macos/release-local.py`; no CI signing secret.

## Observed checks

- Native launcher compiled with Sparkle, and the SDK successfully initialized
  against the final built app's feed/trust configuration.
- Built two isolated test DMGs. Final bundle is in
  `.scratch/sparkle-build/LocalXiv-0.0.5-sparkle.2-macOS26-arm64-unsigned-local`.
  Bundle is about 610 MiB and remains inside the existing 650 MiB budget.
- Code-signature validation, DMG integrity, moved service startup, sandboxed
  conversion and EPUB validation passed. Final relocation report is
  `.scratch/sparkle-build/verification.json`.
- Generated a signed appcast for the first test DMG. Sparkle's `sign_update`
  verified the DMG and feed; a modified feed was rejected.
- Full release test selection: 59 tests, one intentionally skipped Keychain
  smoke test, no failures. UI checks, shell syntax and diff whitespace checks passed.
- Older AI fixtures were updated for cached reading, synthesis and independent
  temporary libraries; production reading behavior was not changed in this step.

## Local signing revision

- Removed private-key secrets from CI and the environment-key signing fallback.
- Re-signed the existing test DMG through Keychain; public-key match, archive
  signature verification and signed-feed verification passed.
- All three update tests passed, including draft-only local preparation and
  no-publication behavior. Workflow YAML, Python compilation and diff checks passed.
- The local publisher has not been exercised against a real GitHub draft.

## Not yet exercised

No GUI-driven old-to-new app replacement/relaunch was performed. The public feed
does not exist until the first updater-enabled release is published. See `docs/sparkle-updates.md` for local signing and release publication.
No private-key export or backup was created.
