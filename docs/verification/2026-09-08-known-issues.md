# Known-issue parser repairs

This pass reuses the 36 CS-conference selections and 28 non-CS subject selections. Notes and lectures are excluded. The non-CS group is selected by discipline, not verified conference membership. This is a repair evaluation on already inspected inputs, not a new independent holdout.


The final rerun produced **49/64 validated EPUBs**, up from **45/64**. All 45 previously successful conversions still succeed. Of the 61 inputs with usable source, 49 convert and 12 still fail processing. Three inputs have only their original PDFs available to this pipeline.

| Group | Before | After | Source unavailable | Remaining processing failures |
| --- | ---: | ---: | ---: | ---: |
| CS conference papers | 28/36 | 29/36 | 1 | 6 |
| Non-CS subject papers | 17/28 | 20/28 | 2 | 6 |
| Total | 45/64 | 49/64 | 3 | 12 |

The recovered papers are `2401.16270v2`, `2207.06970v1`, `2311.03037v1`, and `2310.00260v2`. This measures EPUB conversion coverage, not exhaustive fidelity.

## Repairs

- Use MathJax's native macro parser for text superscripts/subscripts, bold symbols, overbars, and text inside equations. Preserve original TeX annotations. Unknown commands and malformed expressions still fail. Small-caps text retains its words and spaces but uses ordinary text styling in the alternate equation renderer.
- Ignore TeX expansion protection and page-width glue inside isolated equations. Remove an invalid empty MathML column-spacing attribute while preserving explicit spacing values.
- Preserve repeat/until loop bodies and termination conditions, including nested control flow and uppercase algorithmic spelling. Reject unbalanced blocks and missing conditions.
- Map Zapf Dingbats circled digits 1–10 to their corresponding Unicode characters. Unsupported glyphs still fail.
- Preserve the image, caption, and reference target when a source table consists of one image. This retains a raster table; it does not reconstruct editable cells.
- Detect HTML image types from their bytes rather than URL extensions. Existing cached JPEGs named `.png` are packaged with the correct extension after their retained hash is checked. Signature recognition is not a complete image decoder.
- Remove retained TeX underscore escapes from HTTP/HTTPS link targets without changing displayed reference text or accepting unsafe schemes.
- Preserve the first institution after an explicit `affiliations` marker, alongside later institutions and email addresses.
- Supply standard `say` and `acks` text macros so quoted definitions and acknowledgements survive Pandoc. Preserve INFORMS `ACKNOWLEDGMENT` only for explicitly nonblind output. Explicit source definitions are preserved.
- Exclude LaTeX comment environments from the audit's source inventory. Two apparent missing graphics in a previously accepted paper were inside an excluded source section, not lost content.

## Tests and evidence

Metamorphic checks compare equivalent source forms: algorithm command case, math grouping and whitespace, escaped braces, macro forms versus explicit text, image bytes served under different extensions, and source comments containing inactive graphics or includes. Normalization is checked for idempotency. Invalid control flow, malformed or unknown math, unsafe links, changed cached assets, and deliberately corrupted output remain rejection tests.

The existing integrity tests mutate prose, mathematical operators, table cells/spans, figures, and links. Their purpose is to verify that the checker detects corruption; an unchanged snapshot is not proof that its baseline was correct.

The recovered clinical-ML paper initially still omitted a quoted definition and an acknowledgement. Targeted source/output review found both omissions, and the final repair retains their complete text. The recovered IJCAI paper initially omitted its first institution; the final repair retains both institutions, while its authors remain in document metadata, OPF, and the EPUB cover. Earlier outputs and review findings are retained.

Detailed evidence lives in `.verification/robustness/known-issues-recovery-review.json`, `known-issues-prose-review.json`, and `known-issues-graphics-review.json`. The latter records the correction of an initial reviewer mistake about figures inside a comment environment.

## Reproduction and scope

`known-issues-03` reruns all 64 inputs with a frozen converter. `known-issues-04` reruns the six inputs containing explicit affiliation markers; `known-issues-05` reruns the one input containing the two newly supported text macros. `known-issues-06` reruns the one input using the INFORMS acknowledgement macro. Source scans and revision hashes are retained in `known-issues-04-scope.json`, `known-issues-05-scope.json`, and `known-issues-06-scope.json`. The merged results use stage 06 over stage 05 over stage 04 over stage 03. Original `runs/final/results.json` remains unchanged.

No new dependency was added. These are local source changes. The installed app bundle and physical Kindle delivery are outside this verification. Cached rerun timings include concurrent validation activity and are not an isolated performance benchmark.

## Final validation

- Application suite: 230 tests run, passing with one skipped. Robustness suite: 67 tests passed. `git diff --check` passed.
- All 49 generated EPUBs have fresh source/PDF/reader audits. Automated results are 28 without flags and 21 requiring review; the original heuristic flags remain visible rather than being rewritten as clean passes.
- The eight outstanding non-note reviews from the prior evaluation are explained by source comments, text-only figures, metadata placement, or extraction boundaries. Their evidence remains separate from package validity.
- All 45 previously successful outputs were compared. Forty-one have identical content snapshots. Four have reviewed differences: `2402.09450v3` changes from hosted HTML to a source conversion, `2405.14358v1` and `2308.07899v2` restore affiliations, and `2109.03115v1` changes two `.jpeg` paths to `.jpg` with all ordered image hashes unchanged. No conversion regression occurred.
- The original UniAD paper converts and has an identical content snapshot to its previous verified output. The later affiliation and acknowledgement constructs are absent from its source.
- Targeted recovered-paper review verifies equation annotations, image-table captions and targets, source acknowledgements, algorithm termination conditions, and nine proof-square markers. Selected recovered-paper previews were rendered and inspected. These are bounded checks, not a proof of every character or physical-device layout.

Merged records, audit results, revision checks, and all prior-output comparisons are in `.verification/robustness/known-issues-final/`. See `known-issues-per-paper.md` for the final per-paper table. Review evidence is in `known-issues-recovery-review.json` and `known-issues-changed-output-review.json` alongside the earlier graphics/prose reviews.

## Remaining limits

The twelve processing failures still include unsupported diagrams, complicated table/citation targets, malformed source or hosted mathematical markup, and converter/package incompatibilities. Repairs can expose a second error in the same paper; removing an initial error is not counted as a recovered EPUB. No paper-specific bypass or weakened content gate was introduced. The original PDFs and failed attempt logs remain available.
