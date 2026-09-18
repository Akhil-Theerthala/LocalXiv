# Blog live pilot re-run (post-fix): three models, two papers, PDFs

Status: historical. The model-drawn SVG path this report verifies was deleted by the [figure library consolidation](../superpowers/specs/2026-09-18-figure-library-consolidation-design.md); the code is at commit 9abae74.

Date: 2026-09-14
Session: `.scratch/blog-live-e2e/2026-09-14-blog-pilot-rerun/`
First pilot: [Blog live pilot](2026-09-14-blog-live-pilot.md)
Plan: Blog workflow update (plan removed; in git history)

Status: authorized re-run of the full 6-Blog matrix on the fixed code, same scope, settings, models,
papers, and $10 ceiling. This is a separate session record; the first pilot's results are unchanged.

## Why re-run

The first pilot delivered 2 of 6 Blogs but exposed a real defect: a review finding on a figure that
had already spent four drawing attempts started a fifth and sixth draw (`gpt-terra` / LoRA, 6
attempts). The fix in `papers/agent_overviews.py` omits the exhausted figure and cleans the article
instead. This re-run checks that behavior live and gives a post-fix delivery sample.

## Code identities

| Stage | Identity |
| --- | --- |
| Generation (all 6 Blogs) | tracked diff SHA-256 `0a3bffe7ab51ebf9806070c71b986d5fd7297332928626a0d235c9dc8279f6be` (`agent_overviews.py` SHA-256 `b2816b54a1068ddf…`) |
| PDF re-export of gemini/Mamba | tracked diff SHA-256 `512136f1ebd7ed04e86841c53796d22a60d3a9c639de1fd64130a45f4328148e` (adds the `\bm` export fix below) |

The generation identity differs from the first pilot (`2f14dcb0…`) only by the exhausted-figure
guard; see the first pilot document for that fix and its regression test.

## Results

Two of six Blogs delivered, for $3.1314 of the $10 ceiling. Figure retention improved: 5 of 9 planned
figures were accepted, all within attempts two or three, and **no figure exceeded four attempts**.

| Model | Paper | Status | Figures (status/attempts) | Verdicts | Cost | Wall | PDF |
| --- | --- | --- | --- | --- | --- | --- | --- |
| gemini-3.8-flash | LoRA | ready, approved | `fig1` accepted/2 | 1 | $0.1586 | 361 s | [194 kB](artifacts/2026-09-14-blog-live-pilot-rerun/gemini-3.8-flash-LoRA-2106.09685v2.pdf) |
| gemini-3.8-flash | Mamba | ready, approved | `fig1` accepted/3, `fig2` accepted/3 | 1 | $0.4138 | 480 s | [302 kB](artifacts/2026-09-14-blog-live-pilot-rerun/gemini-3.8-flash-Mamba-2312.00752v2.pdf) |
| gpt-luna | LoRA | failed at review | `fig1` omitted/4 | — | $0.1451 | 360 s | — |
| gpt-luna | Mamba | failed at brief correction | `fig1` pending/2, `fig2` accepted/2 | — | $0.0564 | 225 s | — |
| gpt-terra | LoRA | failed at review | `fig1` omitted/4 | — | $0.5899 | 285 s | — |
| gpt-terra | Mamba | failed at review | `fig1` omitted/4, `fig2` accepted/3 | — | $1.7676 | 450 s | — |

Figure completion, all 9 planned figures as the denominator:

| Attempt | Accepted on this attempt | Cumulative accepted | Cumulative share |
| --- | --- | --- | --- |
| 1 | 0 | 0 | 0.0% |
| 2 | 2 | 2 | 22.2% |
| 3 | 3 | 5 | 55.6% |
| 4 | 0 | 5 | 55.6% |

Status counts: 5 accepted, 3 omitted, 1 pending. The plan's target — usable figures within two or
three attempts — is met for 5 of 9 planned figures in this sample. The pending figure belongs to an
article that failed during brief correction, so it was never drawn again.

## Fix confirmed live

The exhausted-figure path ran twice, in `gpt-terra`/LoRA and `gpt-terra`/Mamba. The saved traces show
exactly four drawing requests each, then the omission path:

```
figure_draw pending  attempts 3  figure fig1  request 7
figure_draw accepted attempts 4  figure fig1  request 7
review      completed                            request 8
omission_cleanup completed                       request 9   <- new guard, no fifth draw
review      completed                            request 10
```

`fig1` ends `omitted` with `attempts 4`; the article's dependent prose was removed in the same
single cleanup request. Pre-fix, the same sequence produced attempts 5 and 6. Across the whole
session the maximum attempts for any figure is 4.

## Second defect found and fixed: `\bm` broke PDF export

The gemini/Mamba Blog passed review but its PDF export failed:

```
PDF export failed: Error producing PDF.
! Undefined control sequence.
<argument> \bm {A}
```

The article used `\bm{A}` 32 times. MathJax renders `\bm`, but the pandoc/XeLaTeX export pipeline
cannot load the `bm` package because pandoc's default Unicode math setup conflicts with it; adding
`\usepackage{bm}` or `--include-in-header` did not help. `papers/exports.py` now normalizes
`\bm` → `\boldsymbol` (provided by amsmath) for the PDF text only; the saved article text is
unchanged, so the reader still sees the original macro.

Regression test:
`tests/test_exports.py::BlogSparseFigureExportTests.test_bold_math_macros_export_after_normalization`,
which also asserts the substitution does not touch `bmatrix` or `\bmx`. The gemini/Mamba PDF was
re-exported through the application after the fix and is included above.

Post-fix checks: full offline suite **569 tests, OK, 1 unrelated skip**; `git diff --check` clean.

## Pre-fix vs post-fix comparison

| Metric | Pilot 1 (pre-fix) | Pilot 2 (post-fix) |
| --- | --- | --- |
| Blogs delivered | 2 of 6 | 2 of 6 |
| Delivered by | gemini/LoRA, terra/Mamba | gemini/LoRA, gemini/Mamba |
| Planned figures | 8 | 9 |
| Figures accepted | 3 (37.5%) | 5 (55.6%) |
| Accepted by attempt 2 or 3 | 2 (25.0%) | 5 (55.6%) |
| Budget violations (> 4 draws) | 1 figure, 6 attempts | none, max 4 |
| PDF exports | 2 of 2 delivered | 3 of 3 delivered (after math fix) |
| Spend | $1.8738 | $3.1314 |

Delivery rate is unchanged in this small sample, and the composition differs (gemini/Mamba passed
this time; terra/Mamba failed this time), so no model ranking follows from two papers. What the
re-run establishes is the budget behavior and the PDF fix.

## Remaining failures

- **gpt-luna / LoRA**, **gpt-terra / LoRA**, **gpt-terra / Mamba** — bounded review stopped after
  two prose corrections with unresolved findings, as in the first pilot. The reviewer's findings are
  substantive (the α/r scaling omitted from the displayed forward pass, loss-direction wording,
  figure connectors implying activation merging, symbol-definition gaps), and the policy correctly
  withholds unreviewed prose.
- **gpt-luna / Mamba** — the corrected drawing brief was rejected twice and the run failed before
  any review. A different bounded-repair path than the first pilot hit.

## Artifacts

| Artifact | Path |
| --- | --- |
| LoRA Blog PDF (gemini) | `docs/verification/artifacts/2026-09-14-blog-live-pilot-rerun/gemini-3.8-flash-LoRA-2106.09685v2.pdf` |
| Mamba Blog PDF (gemini, re-exported after the math fix) | `docs/verification/artifacts/2026-09-14-blog-live-pilot-rerun/gemini-3.8-flash-Mamba-2312.00752v2.pdf` |
| Full re-run report | `docs/verification/artifacts/2026-09-14-blog-live-pilot-rerun/report.md` |
| Session records | `results.json`, `events.jsonl`, `manifest.json` beside the report |
| First page renders | `gemini-Mamba-page-1.png` (math rendering), first-pilot PNGs for comparison |
| Raw session | `.scratch/blog-live-e2e/2026-09-14-blog-pilot-rerun/` |

## Limitations

- Two papers and three models per session; delivery differences between the sessions are within
  model nondeterminism and are not attributable to the fix.
- The `\bm` fix covers the demonstrated macro. Other reader-valid LaTeX macros that XeLaTeX does not
  define could still fail PDF export; no exhaustive sweep was run.
- Vision review was enabled; reviewer findings were not independently re-verified against the papers.
- No provider failure, cancellation, or authentication error occurred in either session, so those
  live paths remain covered only by offline tests.
