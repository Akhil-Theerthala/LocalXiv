# Robustness evaluation

The design is in `docs/superpowers/specs/2026-09-08-parser-robustness-design.md`.

The sample combines conference papers, seven non-CS subject groups, and notes.
It is a stratified random sample of documented arXiv query populations, not a
representative estimate for all scientific publishing. Conference membership
comes from author-reported metadata; companion tracks must be labeled as such.
No paper is replaced because downloading or conversion fails.

Run from the repository root:

```sh
python3 tools/robustness/sample.py sample
python3 tools/robustness/sample_listings.py
python3 tools/robustness/sample.py download
python3 tools/robustness/evaluate.py --stage baseline --split development
python3 tools/robustness/evaluate.py --stage candidate --split development --combined
python3 tools/robustness/audit_run.py --stage candidate
python3 -m unittest discover -s tools/robustness -p 'test_*.py'
```

Network requests need outbound access. Conversion needs the existing macOS
sandbox, process inspection, and installed conversion tools. Downloads, inputs,
logs, and outputs live in `.verification/robustness`. The sample manifest and
code are tracked separately. Each stage copies the converter and its existing dependencies before running. A changed converter requires a new stage name;
earlier output is evidence and must not be overwritten.

Do not open held-out conversion results during the development repair loop.
Use `--split holdout` after freezing the candidate converter. If failures from
that evaluation are repaired, report the original held-out result separately
and describe the rerun as a post-evaluation repair, not unseen validation.

`audit_run.py` requires a Python environment with `pypdf`. It compares original source/PDF anchors with output. Missing matches
are review candidates, not automatic proof of loss. `integrity.py` detects
changes from a previously reviewed output snapshot. It does not certify the
snapshot itself. Its tests deliberately corrupt content to verify detection.
Every passing paper still needs source/PDF checks and rendered review before a
claim of faithful output. A PDF fallback is not a passing EPUB conversion.

`--combined` exercises the application recovery order: Pandoc, exact-version arXiv HTML, then LaTeXML. Each route still passes both EPUB profiles and content validation. `--html` evaluates HTML independently for diagnosis. These modes retain failed attempts and never count the PDF fallback as a successful EPUB. Cached HTML and figures carry version checks and byte hashes.

`benchmark_math.py` compares the current equation renderer with a frozen stage on identical ordered chapters. It alternates variants and compares every generated PNG and rewritten chapter exactly. Its timings cover equation images only; report whole-import timing separately. Run it without concurrent conversion jobs.

## Repeatable repair and verification loop

Keep development and held-out evidence separate. Freeze a candidate revision, run the development split, and record exact source and output hashes. Repair only from development findings. Then run the untouched holdout and preserve that first result. If a holdout issue is repaired afterward, give the rerun a new stage suffix and label it a post-evaluation repair. Do not use it to rewrite the first holdout result.

Encode recurring parser failures as small fixtures and keep the real paper that exposed each failure. Add metamorphic checks when a source transformation should preserve meaning, and mutation tests for validators and content checks. For every converted paper, compare source and PDF anchors, inspect the rendered output, and retain exact witness paths for findings. A missing-anchor flag identifies a review candidate; it does not prove loss by itself.

Profile isolated conversion stages with fixed inputs. Compare output content hashes, chapter order, equation PNG hashes, and figure bytes before interpreting a timing change. The report generator keeps candidate-01 and holdout-01 for comparison while `--stage-suffix 03` selects a later rerun:

```sh
python3 tools/robustness/report.py --stage-suffix 03 --output /tmp/robustness-run-table-03.md
```
