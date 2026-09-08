# Parser robustness implementation plan

> Execute inline using the approved design. The user cannot intervene; ordinary design and validation choices are delegated.

**Goal:** Improve and evaluate parsing on approximately 76 randomly selected conference, cross-disciplinary, and lecture-note documents while detecting content loss and containing local rendering failures.

**Architecture:** Preserve frozen input metadata and source files separately from revision-specific conversion outputs. Reuse the existing sandboxed worker and audit helpers; implement only missing sampling, comparison, and local fallback functions.

**Stack:** Python standard library, existing Pandoc/MathJax/LaTeXML tools, EPUBCheck, existing PDF extraction and browser rendering tools.

- [x] Capture arXiv sampling frames and venue evidence, seed, random selections, development/held-out assignments, and official provenance in `docs/verification/robustness-sample.json`; cached public downloads live under `.verification/robustness`.
- [x] Resolve selected titles to exact arXiv versions, retaining mismatches and unavailable records. Download immutable sources/PDFs with hashes using existing acquisition.
- [x] Add resumable `tools/robustness` commands for conversion and audit. Preserve baseline outputs and historical reports before fixing further failures.
- [x] Group observed failures. For each repair: reproduce a minimal failing example, test related spellings/contexts and meaning-preserving transformations, repair the shared layer, rerun the original paper.
- [x] Add independent content checks and deliberate-corruption tests for paragraph removal, numeric/symbol alteration, figure deletion, and link breakage. Flag uncertainty rather than silently passing it.
- [x] Evaluate a per-equation renderer fallback using preserved TeX, bounded to trustworthy math nodes; retain original PDF fallback when structure or rendering cannot be validated.
- [x] Freeze fixes, evaluate held-out papers, and separately label any post-holdout repairs. Re-evaluate the historical corpus and all selected papers on the final revision.
- [x] Inspect selected rendered outputs, review source/PDF evidence and flagged discrepancies, and record exact locations. The final report distinguishes 40 no-flag or explained-flag inputs from nine converted inputs with unresolved heuristic findings; it does not claim exhaustive fidelity. Produce per-paper results and repeatable commands.
- [x] Measure repeated equation rendering on two real papers and compare the recovery order on one controlled cached-input failure path. Accept speed changes only with matching content. Report the unchanged physics timing and the limited benchmark scope; a corpus-wide isolated timing distribution was not measured.

## Execution outcome

The frozen evaluation and targeted post-evaluation repairs are complete: 49/76 sampled EPUBs, 17/17 historical regressions, 193 existing tests and 51 focused tests pass. Controlled timing comparisons preserve content. The final report documents 21 remaining heuristic audit flags and the limits of selected rendered review. The selected review and controlled timing cases must not be read as exhaustive coverage or a universal performance guarantee.
