# Local repository cleanup, 9 September 2026

Removed 28.4 GiB of obsolete builds and generated verification files. The repository footprint fell from 47.4 GiB to 19.0 GiB. These are allocated sizes reported by `du -sk`, not a measurement of physical disk space freed on APFS.

| Directory | Before | After | Removed |
| --- | ---: | ---: | ---: |
| `dist` | 15.0 GiB | 2.2 GiB | 12.8 GiB |
| `.verification` | 32.2 GiB | 16.6 GiB | 15.6 GiB |
| Whole repository | 47.4 GiB | 19.0 GiB | 28.4 GiB |

## Removed

- Superseded release bundles, old DMGs and installation backup bundles.
- Unpacked dependency sources, after all 561 files matched the retained source archive by SHA-256.
- Repeated conversion intermediates, reader exports, EPUBs and visual renders from superseded verification runs.
- Installed Node dependencies in old code snapshots and Python bytecode caches.

Original inputs, reports and source snapshots remain in superseded runs. Some paths in those historical reports now point to removed generated outputs. Reproducing those runs requires reinstalling snapshot dependencies and regenerating the outputs.

## Retained

- Final build 9 app and 261.2 MiB DMG under `dist/lean-final-20260909`.
- Published v0.0.2 rollback release under `dist/releases/v0.0.2-published`.
- Dependency source archive and checksum under `dist/final`.
- All 192 paper directories referenced by the current robustness, link and known-issue result reports, plus the first holdout run.
- Final lean-build comparison outputs, original paper inputs, conversion reports and code snapshots.
- Active development data under `.verification/overview-math/library`.
- Working source changes, tests, Git history, worktrees, development dependencies and storyboard assets.

The installed application, user library and settings outside the repository were not modified. The remaining 16.6 GiB of verification files is retained evidence and input material, not content shipped inside the app.

## Verification

- SHA-256 comparison confirmed that all tracked and non-ignored untracked files present before cleanup were unchanged. This report was added afterward.
- Final DMG checksum remained `09183698148d8361e58607a9f448484f99095cf9030644298a133f8e8ffe5eae`.
- All protected evidence directories, the active development library and storyboard files remain present.
- Three bundle-size tests and the UI check script passed. `git diff --check` passed.

The local deletion manifest, before/after measurements, source hashes and saved release metadata are in `.verification/cleanup-20260909`. This cleanup did not rebuild or install the application.
