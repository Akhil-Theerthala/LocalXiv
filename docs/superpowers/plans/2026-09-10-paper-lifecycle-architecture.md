# Paper lifecycle architecture implementation plan

> Execute sequentially in the current checkout. The user authorized all three candidates, starting with retention. No release or publication is included.

**Goal:** Concentrate Paper retention, conversion recovery and export decisions in modules tested through their caller interfaces.

**Architecture:** Extend Library to own retained files as well as records. Keep conversion isolation in papers/convert.py and consolidate import recovery there. Move export policy into papers/exports.py and retain the existing format implementations.

**Constraints:** Preserve the existing fallback order, cancellation checkpoints, ready Papers on failed retry, outside-directory protection, content checks and offline conversion. No new dependencies. Preserve existing untracked work.

## 1. Paper retention

- [x] Reproduce failed retention followed by removal in a temporary Library.
- [x] Add Library.retain_paper(document, directory, error=None), concentrating file promotion and replacement rules; route successful and failed imports through it.
- [x] Allow removal of legacy failed Papers only when a terminal import job proves directory ownership. Keep arbitrary and symlinked paths rejected.
- [x] Verify failed retention/removal, legacy removal, successful retention, failed retry protection and rollback after a database failure.

## 2. Conversion recovery

- [x] Add route-outcome tests for Pandoc, HTML, LaTeXML, PDF, unavailable source, cancellation and accumulated diagnostics.
- [x] Add convert_import(directory, metadata, progress, source_error=None) beside the sandbox runner. Remove fallback sequencing and report manipulation from Application.
- [x] Preserve worker attempt diagnostics and explicit single-engine conversion. Make cancellation distinct from conversion failures.
- [x] Run recovery, app import and real conversion fixtures.

## 3. Paper export

- [x] Add representation-selection tests through the export interface, including invalid combinations and missing or unsafe artifacts.
- [x] Concentrate generation lookup, format selection and final checks in papers/exports.py. Move PDF export and shared figure-path validation out of the Bento layout module.
- [x] Route export/send jobs through the same implementation. Retain real EPUB/PDF/PNG regressions and combined EPUB validation.
- [x] Update the development code map and domain glossary where terminology needs clarification.

## Completion

- [x] Run focused tests, the Python suite, browser checks and relevant robustness tests.
- [x] Review the final diff for behavior drift, test gaps and packaging inclusion.
- [x] Report verified results and any remaining limitations. Leave changes uncommitted.

## Verification results

- Python discovery: 284 tests, passed; one opt-in Keychain mutation test skipped.
- Robustness discovery: 83 tests passed.
- Browser UI checks passed; extension checks: 63 tests passed.
- Real sandboxed LaTeXML fixture: both EPUB profiles passed EPUBCheck; six retained passages, one equation, and prior Pandoc/HTML attempt diagnostics preserved in the returned document and saved reports.
- Retention regressions cover failed-import removal, legacy ownership checks, unchanged-evidence overview assets, restoration of missing originals, and database-failure rollback.
- Two stale local app fixtures also failed against unchanged HEAD; updated them to account for the bundled sample and explicit automatic-overview preference. Restored the app/PDF integration tests and new regressions to the test allowlist so they remain reviewable.
- Changes remain uncommitted. The installed app was not replaced.
