# Citation, table-anchor, and abstract repairs

The retained 64-paper sample now has 51 validated EPUBs, up from 49. Two of the three targeted papers are recovered. All 49 previous successes still convert. This is a result on the retained development corpus, not an estimate of failure probability across arXiv.

## Target results

| Paper | Original blocker | Final result |
| --- | --- | --- |
| 2404.00636v4, ECCV, portrait animation | Empty citations; missing figure links | Recovered through Pandoc. 154 nonempty citation spans cover 72 distinct cited keys. Separately captioned figures, table captions, and the literal method name are retained. |
| 2402.11406v3, ACL, implicit hate-speech detection | Missing calibration-table link | Recovered through Pandoc. All 243 numeric values in the calibration and three prompt-comparison tables match the original source archive in order. Nested grids share one outer anchor and caption. |
| 2407.01400v2, ECCV, GalLoP | Abstract rejected because a title/contribution note preceded it | Abstract and table-anchor checks now pass. Conversion still rejects a missing TikZ method diagram, `fig:figure_method`. It remains a failed EPUB conversion with its original PDF retained. |

The other 12 previously failed inputs were not rerun in this pass. Combining their retained results with the 52 rerun documents gives 51 validated EPUBs and 13 failures: three source-acquisition failures and ten processing failures. The CS conference subset moves from 29/36 to 31/36; the non-CS subject sample remains 20/28. The latter is not a verified non-CS conference sample.

## Shared fixes

- Normalize valid parenthesized BibTeX `@String` declarations before Pandoc bibliography processing. Preserve values, comments, nested entries, malformed inputs, and source bytes. Empty-citation validation remains enabled.
- Parse nested custom column declarations with balanced braces. Handle `tabularx`, bare siunitx numeric columns, and comments before column specifications. Remove the standard `tabcolsep` spacing command that made Pandoc consume an adjacent braced table grid.
- For duplicate anchors on nested tables, require source evidence, one enclosing table containing all targets, the expected grid count, and identical captions. Retain the outer anchor/caption and every inner grid. Unproven duplicates still fail.
- Separate independently captioned center groups within a float. Preserve `captionof` text and its declared table/figure type. Restore literal text macros that Pandoc otherwise drops from prose.
- Allow title/contribution notes before the abstract. Continue rejecting missing or empty abstracts, duplicate abstracts, and abstracts after a numbered paper section. Cover and contents ordering checks remain enabled.

No new conversion engine, network request, or dependency was introduced for these repairs. This pass does not establish a speed improvement. Concurrent conversion timing was noisy; one graphics timeout recovered through HTML, then passed through Pandoc on a separate rerun.

## Verification

- Application tests: 231 run, passed with one skipped.
- Robustness tests: 86 passed, including source-variant/metamorphic tests, idempotency, and rejection tests for malformed inputs or ambiguous anchors.
- Both recovered papers pass EPUBCheck in both output profiles, local resource/link validation, reading-order checks, and equation-image packaging checks.
- Both recovered outputs pass the automated content audit without flags. Remaining phrase mismatches were reviewed as numbered-heading/formatting boundaries, not missing prose. This audit is heuristic and is not an exhaustive semantic proof.
- Browser renders of both recovered outputs were inspected. The caption/name omissions found during initial review were repaired and the outputs rerun.
- All 49 previous successes were rerun. Final caption/text changes were checked against all 49 source trees; the three affected papers were rerun against final code. Three changed conversion routes were also rerun separately. The final comparison finds 47 outputs unchanged in prose, headings, tables, math, images, and links. Two now use Pandoc instead of HTML; their audits and changed content were reviewed. All 49 have no missing resources or internal link targets.
- WebCiteS, one of those route changes, retains a heuristic prose-anchor flag because numbered headings interrupt 23 sampled phrases. Context review found the surrounding prose present, including the three examples marked for further review. This flag is retained in its audit rather than erased.
- `git diff --check` passed. Current source matches the final target snapshot.

Final code revision: `643a9b101f22cf376a4c0e6253b7a791cde36aaa3f2113953c2e28b3c18c8151`.

## Retained evidence

- Combined sample results: `.verification/robustness/links-final/results.json` and `summary.json`.
- Final target outputs and reports: `.verification/robustness/runs/links-06/`.
- Exact numeric table comparison with original source archives: `.verification/robustness/links-final-table-fidelity.json` and `verify-link-tables.py`.
- Regression content comparisons: `.verification/robustness/links-regression-integrity.json` and `links-regression-integrity/`.
- Final-change applicability scan: `.verification/robustness/links-final-affected.json`.
- Final regression reruns: `links-final-regression` and `links-final-route-check` under the runs directory.
- Test logs: `.verification/robustness/links-final-application-tests.log` and `links-final-robustness-tests.log`.
- Visual review: `visual-review/review.png` within each recovered target directory.

Changes are in the local checkout. The installed application bundle has not been updated.
