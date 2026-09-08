# Parser robustness evaluation

The user approved autonomous design and implementation, including online random sampling of 50–60 conference papers and all three previously proposed improvements.

## Scope

Select approximately 76 papers: three each from NeurIPS, ICML, ICLR, CVPR, ICCV, ECCV, ACL, EMNLP, NAACL, AAAI, IJCAI, KDD. This is an explicit AI/ML interpretation of tier-1, not a universal ranking. Use arXiv metadata sampling frames from 2024, with 2023 for ICCV. Conference membership must appear in the paper metadata; record this as author-reported membership until independently verified. Add four each from mathematics, statistics, condensed matter, astrophysics, high-energy theory, quantitative biology, and economics; add twelve lecture-note/tutorial documents across fields. Record query populations and random ranks. This samples arXiv-hosted documents, not all published proceedings. Use seed 20260908 and sorted stable identifiers. Freeze selection before conversion; do not replace failures or unavailable arXiv sources with convenient successes. Keep source-availability and conversion denominators separate. Split the last selected document per stratum for held-out evaluation before observing conversions.

Retain historical error reports and untouched source/PDF files. Historical examples supplement the random sample and never enter its denominator. Record hashes, exact arXiv versions, parser revision, conversion results, and elapsed times. Persist progress so interrupted work resumes without resampling or rerunning completed work unnecessarily.

## Implementation decisions

Reuse acquisition, the sandboxed worker, EPUBCheck, and the existing corpus audit. Add a command-line evaluation runner with machine-readable results. Group failures by cause and preserve diagnostics. Test each repair on minimal related examples and the original paper. Add content checks and prove their sensitivity by deliberately removing content or altering table values and symbols in fixtures. Where document structure is reliable, evaluate per-equation alternate rendering before falling back to the entire PDF. Never call PDF fallback a successful reflowable conversion.

Random expansion alone would discover bugs but perpetuate manual triage. A wholesale converter replacement is too risky before measurement. The selected approach combines broad sampling with focused repairs, content checks, and bounded fallback.

## Completion evidence

A frozen approximately 76-paper manifest with verifiable venue membership and reproducible draws; downloads and unavailable cases accounted for; before/after conversion results; related-example regression tests; mutation checks for missing prose, symbol/numeric changes, missing figures, and broken links; bounded fallback checks; content and rendered review for the passing majority; a final report with per-paper outcomes, unresolved defects, and limits. More than half of the entire selected sample must have verified usable reflowable output, and the goal is substantially higher coverage. No count or validator result alone proves flawless content. No publication, email delivery, or replacement of the installed release is implied.

## Sampling amendment before non-CS selection

The arXiv API returned repeated 500/429 responses for deep non-CS query offsets, including after cooldown and smaller query partitions. No non-CS paper had been selected. Use public monthly listings instead: choose one year from 2020–2025 and one month per field with an independent seeded generator, then four documents without replacement from the complete listing. Draw twelve notes/lecture/tutorial keyword matches from the union of those monthly frames, excluding previously selected identities. This is cluster sampling, not uniform sampling over all years or all arXiv. Persist listing snapshots and draft identities before resolving versions. Conference selections stay unchanged. Label Findings papers as companion-track selections.

## Efficiency requirement

After correctness repairs, measure and improve parsing efficiency. Record per-paper end-to-end conversion timings and identify repeated work within acquisition, normalization, rendering, and validation. Compare an unchanged input set under the same runtime; distinguish cold and cached timings. Re-run content and rendered checks after optimization. Faster conversion does not compensate for missing content. Final evidence must report timing changes and completeness findings separately.

## Recovery amendment from observed development failures

The source-only baseline rejected many sampled documents, often after a 180-second LaTeXML timeout. The retained arXiv HTML for `2303.10665v2` preserved the unsupported TikZ diagram, 866 MathML expressions, and 15 external figure assets. A local prototype passed both EPUB profiles, a source/PDF anchor audit with 99.12% coverage, and an inspected diagram rendering. This is development evidence, not a held-out result or proof of every page.

Add arXiv HTML recovery after source conversion fails. Download only the exact version's article and figure assets. Preserve original HTML and byte hashes; strip site navigation by extracting the article; preserve MathML and SVG namespaces; adapt non-rendering MathML 4 intent hints for EPUB 3 while retaining their original values in the HTML. Reuse the existing sandboxed packaging, math renderer, and validation. If HTML retrieval or validation fails, keep the existing PDF fallback. Successful source conversions incur no additional network work. Evaluate this route independently on development inputs before opening the holdout. Reordering expensive fallback attempts remains an efficiency decision to measure after correctness.
