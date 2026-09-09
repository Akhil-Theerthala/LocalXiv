# Reduced macOS build and repository review

Completed 2026-09-09. LocalXiv v0.0.3 build 9 is a local, ad hoc-signed review build from commit `d05af4c` plus the uncommitted changes described here. It has not been installed or published. The machine-readable results are in [lean-release-2026-09-09.json](lean-release-2026-09-09.json).

## Final artifact

`dist/lean-final-20260909/LocalXiv-0.0.3-macOS26-arm64-unsigned-local/LocalXiv-0.0.3-macOS26-arm64-unsigned-local.dmg`

| Measurement | Before | Final build |
| --- | ---: | ---: |
| App file contents | 1,093.5 MiB | 610.3 MiB |
| Compressed DMG | 516–549 MiB in retained older releases | 261.2 MiB |
| Java runtime | 380.3 MiB | 46.8 MiB |
| Ghostscript | 127.1 MiB | 46.9 MiB |
| Python | 73.3 MiB | 40.7 MiB |
| JavaScript packages | 61.5 MiB | 15.4 MiB |

The app contains 639,961,145 bytes, a 44% reduction from the installed build. The DMG contains 273,896,256 bytes. MiB measures file contents in units of 1,048,576 bytes, not allocated filesystem blocks. There was no matching v0.0.3 DMG locally, so the download comparison uses retained older releases rather than a same-version control.

DMG SHA-256: `09183698148d8361e58607a9f448484f99095cf9030644298a133f8e8ffe5eae`.

## Changes

- Generate a small Java runtime with `jlink`, retaining EPUBCheck and its XML/image support.
- Exclude Ghostscript's unused executables and libraries before native dependency discovery. Preserve `gs`, resources, fonts and required linked libraries.
- Omit CPython's test suite.
- Select the installed JavaScript dependency tree needed for MathJax, XML parsing and SVG overview rendering. Preserve nested npm dependencies, licenses and the embedded diagram font. Exclude MathJax's unused distributions and Excalidrawer's MCP/PNG dependency branches. No dependencies were added.
- Write `size-report.json` for each release and enforce component, app and DMG budgets. CI includes this report in its artifacts.
- Return lightweight paper summaries and all active jobs plus the latest 100 completed jobs when polling. Full paper records and job history remain stored. Completion timestamps ensure an older long-running job stays visible when it finishes.
- Use one shared refresh request, polling at 2 seconds for active jobs, 10 seconds when idle and 30 seconds while hidden. Replace repeated modulo-based process-memory checks with a monotonic deadline.
- Include the packaging, library, browser UI and local-handoff regression tests in Git. These had otherwise been hidden by the blanket `tests/` ignore rule. Correct two handoff fixtures that accidentally discovered the real installed app.

## Verification

The final app was copied to a path containing spaces. Signature verification, isolated service startup, normal source conversion, a separate LaTeXML conversion, both EPUB profiles, PDF text extraction and SVG overview rendering passed. Runtime checks cover PDF/EPS/PS rasterization and rejection of an EPUB with an invalid mimetype. Developer tool paths were blocked during the relevant portability checks.

The final DMG was mounted read-only. All 6,576 packaged files and links matched the verified app, and the mounted app's signature passed. All 37 packaged application source/assets files matched the working checkout.

The full Python run completed 235 tests with no failures and one skipped opt-in real Keychain test. After the final job-completion correction, all eight focused library/packaging tests passed. Browser UI checks and 63 extension tests passed. The dependency-source collector's self-test passed. Live providers, Mail delivery, notarization and a separate clean Mac were not tested.

### Paired paper comparison

Ran the same 16 saved regression papers and two saved source holdout papers through both the installed app and the reduced build, with matching input hashes and developer paths blocked. This deliberately tests source conversion directly, rather than fetching HTML or invoking the app's subsequent PDF fallback.

- All 18 source-conversion outcomes matched.
- Twelve papers converted successfully in both apps. Ordered passages and equation counts matched exactly. All 24 resulting EPUBs matched after normalizing XML attribute order and the OPF build timestamp. Binary assets matched byte-for-byte.
- Six papers failed source conversion in both apps with the same first error. Their identifiers are `1612.01474v3`, `1706.04599v2`, `2410.20199v1`, `2504.18346v4`, `2510.13290v1` and `2608.26703v1`. Existing limitations include algorithm anchors, custom boxes, TeX parsing and forest diagrams requiring unavailable TeX support. These remain separate conversion issues, not new package regressions.

The temporary runner initially asserted an EPUB result field that does not exist. That assertion was corrected, and the paired checks above were rerun with fresh outputs. Earlier saved corpus reports also differ from current installed behavior; this report uses the fresh installed-app control rather than claiming those historical results still hold.

Detailed paired evidence remains in `.verification/lean-corpus-comparison.json`, with logs and outputs under `.verification/lean-control-20260909/` and `.verification/lean-final-corpus-20260909/`.

### Polling measurement

A temporary library containing 100 copies of one converted paper returned 14,532,290 bytes through the full-record list and 33,290 bytes through the new summary list, a 99.8% reduction in paper-list JSON. This is a controlled payload-size example, not a production battery or latency benchmark.

## Repository after the build

The application still uses system WKWebView and a small Python service. Packaging remains in the existing build scripts; no new framework, service or build dependency was introduced. The reduced app preserves the conversion engines and validator.

Pandoc remains the largest component at 265 MiB. The selected Node executable is approximately 105 MiB, and shared libraries occupy 28 MiB. Node's distribution differs from the installed control, whose smaller launcher links to a separate Node library and ICU. Both versions are recorded in their runtime manifests. The paired checks found no content differences from that change. A measured smaller Pandoc build is the next size investigation; removing conversion or validation features is unnecessary for this build.

Removed 1.87 GiB of temporary runtime and candidate-release copies created during this work. The final DMG/app, comparison evidence and pre-existing releases/corpus were retained. Older `dist` and `.verification` contents remain developer storage, excluded from the DMG. Other historical tests are still ignored; the specific regressions needed for this change are now included in Git and CI.

Source changes remain uncommitted for review. The build manifest correctly records `source_dirty: true`, so this local build does not include a misleading clean-commit source archive. Commit the reviewed changes and rebuild before publishing a release that needs an exact source archive.
