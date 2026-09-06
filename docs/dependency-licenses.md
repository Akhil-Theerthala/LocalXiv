# LocalXiv release licenses and source

LocalXiv's original source is licensed under **AGPL-3.0-or-later**. The complete
GNU license is in `LICENSE`; `NOTICE` states the version choice. Third-party
components keep their own licenses and copyright notices.

This choice fits the open-source distribution plan and the bundled Ghostscript
runtime, whose installed Homebrew metadata declares AGPL-3.0-or-later.
It does not make the other dependencies AGPL or settle every distribution
obligation. Pandoc, Java, shared libraries, fonts, Node's embedded dependencies,
Perl modules and npm packages still need their own notices and source review.

## What to ship

Alongside each downloadable app, provide:

- The exact LocalXiv source used to build it, including the launcher, runtime
  relocation scripts, package lockfile and build instructions.
- The runtime's `manifest.json`, its `licenses/` directory, and all additional
  notices found while reviewing statically bundled dependencies and data files.
- Required corresponding source for the exact third-party versions shipped,
  including applied patches and build scripts. Make it available from the same
  download location with clear directions beside the binary download.

Keep source available for as long as the chosen license distribution method
requires. A link to an upstream project's current release is not a substitute
for providing matching source. An inventory of license names is not a substitute
for the full license texts and copyright notices.

The runtime executes third-party command-line programs and bundles shared
libraries. The source and notices for these components must be reviewed against
the actual release, including libraries embedded inside Pandoc, Node, Java,
EPUBCheck and LaTeXML. For LGPL libraries, confirm that recipients can replace
or relink the covered library as required by the applicable license version.
Document the rebuild and signing steps needed for a modified local app.

## Collect source inputs

Run this on the same Mac that built the runtime, while its installed Homebrew
kegs still exist:

```sh
python3 app/macos/collect_sources.py build/runtime build/third-party-sources --metadata-only
python3 app/macos/collect_sources.py build/runtime build/third-party-sources
```

Replace `build/runtime` with the runtime directory passed to the release
builder. Network access is required for the second command. Downloads can be
large, especially Java and Node. The collector reuses files only after verifying
their checksums and records failures in `source-inventory.json`. If the GNU
redirector or NIST host fails, it tries source mirrors and accepts a file only
when it matches the original formula checksum. The inventory records the URL
that supplied each archive.

For each Homebrew dependency recorded in the runtime manifest, the collector:

1. Checks that the current formula version and revision match the runtime.
2. Copies the installed `.brew` formula recipe and installation receipt.
3. Uses Homebrew to read that installed recipe's source, resources and patches.
4. Downloads archives and external patches with their recorded SHA-256 hashes.
   Embedded patches remain in the copied recipe.

Version mismatches stop collection for that component. Restore matching
metadata or rebuild the runtime from an intentionally selected version. Do not
silently replace old source with the latest upstream archive. Recipes that use
Git checkouts or unpinned resources require manual resolution and produce
errors instead of a source-complete claim. For local Homebrew patch files, the
collector saves a candidate from the recorded current tap commit. If the bottle
receipt has no source commit, confirm that candidate matches the installed build
before treating the source bundle as complete.

The collector also downloads the exact Node version's source tarball and its
upstream checksum list. It downloads production npm package archives according
to the root `package-lock.json` and verifies each lockfile integrity hash. npm
archives may contain generated JavaScript without the preferred source used to
edit it. Review those packages and add matching upstream source where needed.
Preserve the package license files in the app as well as the source archive.

The output always starts with `correspondingSourceComplete: false`. A successful
command means that the supported source inputs were collected, not that a
lawyer or an automated audit has approved distribution. Resolve every `errors`
entry and each `reviewRequired` item before publishing. The collector cannot
infer the complete source of every library embedded in a prebuilt bottle.

## Known gaps in the current Homebrew build

The installed Pandoc recipe runs `cabal v2-update` and `cabal v2-install` without
a frozen dependency list. Its SBOM does not enumerate the embedded Haskell
packages. The Pandoc source archive alone cannot establish that all exact
embedded dependency sources have been provided. Recover that build's dependency
versions or make a controlled source build that records them before publication.

The EPUBCheck formula downloads a binary ZIP. The collector therefore also
fetches the matching upstream source tag. Its dependency JARs still need a
version and notice check against that binary ZIP.

Python and glib use local Homebrew patch files that are absent from their
installed kegs. Their receipts do not identify the source tap commit. The
collector preserves patch candidates from the recorded current tap commit;
confirm they match the bottle build before declaring the source set complete.

## Primary references

- [GNU AGPLv3 text](https://www.gnu.org/licenses/agpl-3.0.html), especially the
  definition of Corresponding Source and sections 5, 6 and 13.
- [Ghostscript licensing FAQ](https://ghostscript.com/faq/).
- [GNU GPL FAQ on distributing downloaded binaries](https://www.gnu.org/licenses/gpl-faq.html#UnchangedJustBinary).
- [Homebrew formula cookbook](https://docs.brew.sh/Formula-Cookbook) for source,
  resources, patches and formula build instructions.

The canonical `LICENSE` text was downloaded from
<https://www.gnu.org/licenses/agpl-3.0.txt>. The GNU text's copyright notice
belongs to the license document and does not name a LocalXiv copyright holder.
