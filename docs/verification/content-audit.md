# Content fidelity audit

2026-09-05T20:43:39.889218+00:00

These checks compare retained source/PDF evidence with completed reader artifacts. They detect specific omissions and identify review candidates; they do not certify full fidelity.

Audited 16 of 16 corpus documents. Found 0 empty figures, 0 unparsed table blocks, 0 missing abstract anchors, 0 missing caption anchors, and 0 missing note anchors confirmed in both source and PDF. The bibliography check found 0 missing fragments among 71 braced source fragments checked against their corresponding entries.

9,426 of 9,494 exact source/PDF text anchors occur in the reader; the remaining 68 are review candidates, not a measured content-loss rate.

| Paper | Status | Source figures / graphics | Reader figures / images | MathML | Tables | Shared PDF/source anchors retained |
|---|---|---:|---:|---:|---:|---:|
| 2503.14477v2 | needs_review | 12 / 13 | 13 / 13 | 63 | 7 | 733/741 |
| 2511.00280v1 | no_flags_in_checks | 21 / 57 | 74 / 57 | 75 | 6 | 584/588 |
| 2510.13290v1 | no_flags_in_checks | 16 / 12 | 16 / 12 | 978 | 5 | 358/362 |
| 1506.02142v6 | no_flags_in_checks | 5 / 13 | 14 / 13 | 242 | 2 | 277/280 |
| 1612.01474v3 | no_flags_in_checks | 11 / 19 | 22 / 19 | 306 | 4 | 390/393 |
| 1706.04599v2 | no_flags_in_checks | 8 / 9 | 12 / 9 | 227 | 4 | 251/255 |
| 2107.07511v6 | no_flags_in_checks | 41 / 39 | 42 / 53 | 830 | 2 | 965/968 |
| 2205.14334v2 | no_flags_in_checks | 13 / 18 | 12 / 16 | 61 | 6 | 442/442 |
| 2207.05221v4 | needs_review | 41 / 108 | 41 / 108 | 68 | 4 | 872/885 |
| 2302.09664v3 | no_flags_in_checks | 6 / 11 | 17 / 11 | 117 | 9 | 565/568 |
| 2406.15927v1 | no_flags_in_checks | 19 / 21 | 21 / 21 | 93 | 4 | 544/544 |
| 2608.26703v1 | no_flags_in_checks | 9 / 17 | 15 / 17 | 1252 | 4 | 438/438 |
| 2505.07309v1 | needs_review | 17 / 11 | 21 / 11 | 30 | 9 | 722/733 |
| 2504.18346v4 | needs_review | 7 / 32 | 7 / 33 | 172 | 9 | 804/811 |
| 2410.20199v1 | no_flags_in_checks | 1 / 2 | 2 / 2 | 1 | 1 | 571/575 |
| 2606.19868v1 | no_flags_in_checks | 8 / 8 | 8 / 8 | 326 | 5 | 910/911 |

## Automated review candidates, adjudicated below

- 2503.14477v2: source_pdf_prose_anchors_missing; 8 missing text anchors. See JSON for page numbers and exact text.
- 2207.05221v4: source_pdf_prose_anchors_missing; 13 missing text anchors. See JSON for page numbers and exact text.
- 2505.07309v1: source_pdf_prose_anchors_missing; 11 missing text anchors. See JSON for page numbers and exact text.
- 2504.18346v4: source_pdf_prose_anchors_missing; 7 missing text anchors. See JSON for page numbers and exact text.

## Limits

- Source inventory follows simple input/include commands and does not evaluate TeX conditionals or macros.
- Counts are inventories, not equality gates: math environments expand differently and one figure may contain many images.
- Exact 10-word anchors must occur in both retained PDF text and source before checking reader text. Missing matches are review candidates, not proof of dropped content.
- PDF extraction and punctuation, ligature, hyphenation, and reading-order differences can cause false positives.
- No rendered image, equation semantics, numeric table-cell, or visual-layout comparison is claimed.
- Running conversions can invalidate a snapshot; SHA256 identifies the audited completed artifacts.

Source and output inventories for headings, appendix markers, captions, bibliography entries, and equation layout tables are retained in `content-audit.json`. LaTeXML equation layout tables are counted separately from data tables; generated cover and navigation documents are excluded from the semantic EPUB comparison.

Reproduce with a Python environment containing `pypdf`: `PYTHONPATH=. python3 tests/audit_corpus.py`. The `--self-test` fixture verifies that a missing graphic is flagged while an intentional textual figure is retained.
## Final adjudication of the content findings

All 108 text candidates from the preceding audit have now been reviewed against retained source, PDF text, and canonical reader artifacts. Forty match exactly after the repairs. The remaining 68 have individual evidence-backed explanations in the JSON: formatting, accent extraction, MathML tokenization, chapter boundaries, or author metadata ordering. Across the original 108 candidates, the final verdicts are 100 retained formatting and eight retained metadata, with no unresolved candidate or confirmed omission remaining in this reviewed set. The status table above preserves the automated detector's flags; these are superseded by the per-anchor manual verdicts for those candidates.

This review found and rechecked real defects. Thirty-six anchors identified paragraph labels consumed after `\noindent` in 2504.18346v4. Every affected label is now present with its following prose. Two anchors identified missing reference-type words in 2302.09664v3, and one identified a dropped boxed answer example in 2505.07309v1. Those three are also repaired. The review separately found an omitted algorithm caption and lost pseudocode control flow in 2302.09664v3; the final reader retains the caption, loop and conditional structure, comments, and return instruction. The Anthropic affiliation in 2207.05221v4 is now explicit in the opening chapter, resolving the earlier frontmatter concern. Some anchors point to the same omitted label, so anchor counts are not counts of unique defects.

The final source/PDF-confirmed checks retain the restored abstract, methodological footnotes, author notes, and table caption. All ten author-note failures from the earlier snapshot remain resolved. All 71 checked braced bibliography fragments appear in their corresponding entries, including the 70 previously missing fragments. The graphics repairs retain 11 images in 2505.07309v1 and 16 in 2205.14334v2. The latter source contains 18 literal graphics commands because two panels occur in both branches of a TeX conditional; 16 distinct assets is the expected count. Its prose-only prompt figure is intentional.

The JSON embeds all 108 adjudications and the two additional algorithm findings, including source/PDF evidence, reader excerpts, and final artifact hashes. The three reviewers' working reports are `.verification/anchor-review-a.json`, `.verification/anchor-review-b.json`, and `.verification/anchor-review-c.json`. The original reviews were checked against their completed snapshot before integration; the final export recheck preserves that provenance and adds current artifact hashes and reader excerpts. Running the audit script regenerates the automated inventory; this manual adjudication is tied to the recorded artifact hashes and must be refreshed if those artifacts change.

These results support recovery of the identified omissions and retention of the reviewed passages. They do not certify every equation, image, numeric table cell, or layout decision. The audit does not compare complete rendered pages or prove whole-document semantic equivalence.

The final export snapshot contains 4841 MathML elements across all 16 documents. All documents use the same conversion revision, `4885826715d23aea4e74a52a912611dfd25029a71d63007b6a74f66a6e30686e`. The 108 adjudication records include refreshed final document and semantic EPUB hashes and current reader excerpts.

Separate rendered inspection found missing checkmarks and a leaked `cmidrule` range in the semantic-equivalence table of 2302.09664v3, defects that the ten-word anchor check did not detect. A final source-to-cell check confirms all five checkmarks in the expected cells: three for Paris/Paris, Syntactic only for Berlin, and Semantic only for France’s capital. The stray `3-5` is absent. This targeted check does not constitute an exhaustive numeric or symbol-cell comparison across the corpus.
