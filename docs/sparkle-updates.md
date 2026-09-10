# In-app updates

Portable builds include Sparkle 2.9.6 and a native **LocalXiv > Check for Updates…**
menu command. Sparkle provides download, verification, installation and relaunch.
Background checks use Sparkle's standard permission flow; installation requires
the user's confirmation. Developer ID signing is unchanged.

The framework archive is pinned by SHA-256 in `app/macos/sparkle.py`. The build
embeds the framework with its symlinks intact, includes its license, signs its
helpers, and adds the framework runpath. The development `install-app.sh` remains
a source installation without Sparkle; updater testing uses the portable build.

## Signing setup

An Ed25519 key was generated in the local login Keychain under account
`localxiv-sparkle`. The public key is in `app/macos/sparkle.py`; private material
must not be committed. Preserve this Keychain item across development-machine
migrations. Every update must use the matching private key.

Keep the private key in Keychain. CI never receives it, and the signing tool
has no environment-variable private-key fallback. Keep an encrypted backup using
your chosen secure backup process; this workflow does not export the key.

## Release flow

1. Push an approved version tag through the existing release process. CI builds,
   verifies and checksums the app and creates an **unpublished draft** on GitHub.
   Manual workflow runs continue to produce build artifacts only.
2. On the Mac holding the signing key, authenticate `gh` and configure Git HTTPS
   authentication with `gh auth setup-git` if it is not already configured.
3. Run the command below with the actual draft tag and a new output directory.
   It downloads the draft assets, checks their SHA-256 checksums, mounts the DMG
   read-only, checks the embedded trust configuration, and signs through Keychain.
   It also verifies the generated archive and feed signatures.

```sh
python3 app/macos/release-local.py v0.0.5 .scratch/signed-v0.0.5 --publish
```

`--publish` explicitly uploads the signed feed and revised checksums, publishes the
preview release, then updates the `updates` branch. Only signed public artifacts
leave the Mac. The existing draft DMG is not rebuilt or replaced. Run this from
the release checkout so embedded release notes match the release.

Omit `--publish` for a local signing rehearsal. This retains the signed assets but
does not change GitHub. A later full run needs a new output directory. Existing
output directories and already-published releases are rejected to avoid overwrites.
If release publication succeeds but the feed push fails, retry only that step:

```sh
python3 app/macos/release-local.py v0.0.5 .scratch/signed-v0.0.5 --feed-only
```

The retry downloads the already-published feed. Increasing build-number checks
prevent rollback; concurrent pushes can fail safely and be retried. No force-push
is used. GitHub needs no Sparkle signing secret.

For a build already on this Mac, feed generation remains available with
`python3 app/macos/sparkle.py --appcast <release-directory>`.
Archive signatures are verified before extraction; the feed is signed too.
Preview feeds use direct tag download URLs, so GitHub's stable-only `latest`
redirect is not involved.

## Local service and data

Before an update terminates LocalXiv, the native app requests an authenticated,
version-matched shutdown of its loopback service. Active or queued jobs block
installation with an explanation. Once idle, shutdown reserves the service so
new jobs cannot race the update. Relaunch waits for the service's session file
to disappear. The app does not kill conversion or provider processes.

The library remains in Application Support, and credentials remain in Keychain.
The updater only replaces the application bundle. Ad hoc signing can still cause
macOS approval prompts across versions; that work is outside this change.

The existing installed version needs one manual replacement with an updater-enabled
release. The initial release/feed publication has not been performed by this source change.
