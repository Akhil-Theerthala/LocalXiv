# Overview rebuild phase 2 verification

Date: 2026-09-13
Plan: `docs/superpowers/plans/2026-09-13-overview-rebuild-p2.md` (implementation plan)
Design: `docs/superpowers/specs/2026-09-13-overview-workflow-rebuild-design.md`
Status: offline implementation and verification complete. No live provider call was made or is
claimed here; the next live evaluation needs explicit authorization.

## Code identity

| Item | Value |
| --- | --- |
| Branch | `akhil/model-authored-svg-overviews` |
| HEAD at verification | `2b7afbd0c52676ea0d1fff2aaa7043c655855129` (`State every planner JSON contract explicitly`) |
| Final six-file-diff SHA-256 (working tree vs HEAD) | `bf3fb2048235d00c4b36d56871563c3c32280e2c3acca3fdca6693c256f38e0b` |
| Starting diff snapshot and digest | `.scratch/overview-rebuild-p2/baseline/six-file.diff`, SHA-256 `24776969a4e2d3c5244eff9d0e3f1847276ffa2328ba7775c45a779907b786d9` |
| Native helper | `.scratch/overview-rebuild-p2/html-snapshot`, SHA-256 `73287b6f11cf33a84c66e9aa52c990bf67d69c3bf6910c251861c9c60bb60def` |

Native helper built from the current source with the SDK resolved on this machine:

```sh
mkdir -p .scratch/overview-rebuild-p2
xcrun swiftc -sdk "$(xcrun --show-sdk-path)" \
  -module-cache-path /private/tmp/localxiv-p2-swift-module-cache \
  -O papers/HTMLSnapshot.swift -o .scratch/overview-rebuild-p2/html-snapshot
```

Files changed for phase 2: `papers/explanation.py`, `papers/overview_workflow.py`,
`papers/panel_authoring.py`, `papers/panel-guides/authoring.md`, `tests/test_explanation.py`,
`tests/test_overview_workflow.py`, `tests/test_panel_authoring.py`, `tests/test_ai.py`,
`tests/fixtures/overview-p2/` (new replay fixtures), and the design document. The six files that
were already modified before this work retained their prior edits.

## What was implemented

- **Task 1 — run lifecycle.** `generate` creates one run directory before planning, passes it to
  `plan_overview`, and reuses it for drawing, composition, and rendering. Every run writes an
  append-only `events.jsonl` and an atomically replaced `run.json` with `running`, `completed`,
  `failed`, or `cancelled` state. Failures record the failed stage, exception type, and message and
  never replace the original exception; unavailable responses and usage stay absent rather than
  invented. Drawing requests are recorded in the same store with stage, ordinal, options, timings,
  and usage.
- **Task 2 — Overview narrative contract.** `validate_overview_narrative` is separate from Blog's
  `validate_plan`: nonempty text without the shared 1,200-character cap, a 256 KiB candidate
  resource limit, array-of-string `visual_focus` normalized with newlines, optional relationships,
  and exact issue paths. Correction carries the rejected raw answer back as an assistant message
  and preserves valid claims. `recover_overview_narrative` accepts one candidate with four valid,
  source-linked claims, derives the focus from its contribution, drops only invalid optional
  relationships, and never borrows a field from another candidate. Supplemental evidence is sent
  with the existing draft; a failed supplemental call is disclosed as a planning reduction.
- **Task 3 — exact display text.** Shared facts may declare `exact_text`; the author-facing
  assignment carries the ordered union of referenced facts' exact strings, complete equations, and
  complete labels. Acceptance requires each declared string with the same grouping, signs,
  operators, units, and words after only whitespace normalization and XML entity decoding. Numeric
  tokens from ordinary `value` items keep a limited omission check that names its own limitation.
  The regex LaTeX rewriter was removed; unresolved source notation is preserved literally,
  XML-escaped, identified as source notation, and recorded as reduced presentation. The drawing
  guide now separates semantic content from exact display text.
- **Task 4 — planner issues and reductions.** A plan is accepted only when structural validation
  and its reported issue list are clear. Every refinement is built from the latest retrieved
  evidence, every structurally valid draft is retained, and the simplify pass records removed
  connections. `planning_reduced` and `planning_reduction_reasons` reach provenance. The
  independent-claim fallback is validated against a reduced narrative projection with relationships
  removed and is recorded as `assignment_source='narrative_fallback'`.
- **Task 5 — drawing request options.** `_author_once` computes the stage options and forwards them
  through `request_panel` to `Provider.complete`; malformed first output is repaired through the
  `panel_repair` stage even without a usable prior SVG. Effective options and timings are persisted
  per attempt and appear in the delivery report.
- **Task 6 — safe recovery and composition.** One `simple_panel` recovery remains, with XML
  escaping and measured native wrapping. The fallback passes the same geometry and exact-display
  checks as a drawn panel; its outcome is `simplified` and its original drawing defects are recorded
  separately from an empty active-issue list. The final composed-image `checks` are inspected
  before a completed run is returned; active geometry issues reject the run and preserve the
  assembled source and panel records. Missing renderers, fallback renderer exceptions, and
  unrecoverable exact-text mismatches are diagnosed failures.
- **Task 7 — fixtures, report, verification.** Replay fixtures live in `tests/fixtures/overview-p2/`
  and are labelled as synthetic where the historical raw responses were never saved.
  `run_report` reads `run.json` and `events.jsonl` on success or failure and reports delivery,
  failed stage, assignment source, planning reductions, panel outcomes, active local issues,
  request options, usage, and elapsed time separately from `independent_inspection`, which stays
  `not_reviewed` unless a caller supplies a status, artifact, digest, and findings. The local pilot
  consumes that report on failure as well as success.

## Commands and actual results

All Python runs below used
`LOCALXIV_HTML_RENDERER="$PWD/.scratch/overview-rebuild-p2/html-snapshot"`.

| Command | Result |
| --- | --- |
| `python3 -m unittest tests.test_explanation tests.test_overview_workflow tests.test_agent_overviews` | 108 tests, OK, 17 skipped |
| `python3 -m unittest tests.test_overview_workflow tests.test_panel_authoring tests.test_panel_guides` | 115 tests, OK |
| `python3 -m unittest tests.test_overview_workflow tests.test_panel_authoring tests.test_ai` | 120 tests, OK, 1 skipped |
| `python3 -m unittest tests.test_panel_authoring tests.test_panel_guides tests.test_overview_workflow -v` (native helper) | 115 tests, OK |
| Post-live-fix focused set (six modules) | 178 tests, OK, 18 skipped |
| `python3 -m unittest discover -s tests` | 476 tests, 2 failures, 2 errors, 19 skipped |
| `node tests/test_app_ui.js` | UI reading controls, setup, Library navigation, rendering, and sandbox checks passed |
| `node tests/test_extension.js` | 0 failures, 0 skipped |

Regression coverage added in this phase includes: narrative length/array/mixed-type/size-limit and
recovery cases; assistant-message correction and candidate saving; exact display text through the
projection, the request prompt, and visible SVG text; changed operators, changed units, and missing
labels; literal source-notation recovery; planner unresolved handoffs, malformed clarification, and
supplemental evidence visibility; actual `Provider.complete` kwargs and encoded request bodies for
drawing and repair; run-lifecycle failure/cancellation records; recovery, composition, and
missing-renderer failures; delivery reports for reduced plans and failed runs.

## Fixture replays

`tests/fixtures/overview-p2/` contains one labelled synthetic fixture per reproduced defect:
`narrative-long-focus.json`, `narrative-array-focus.json`, `encoder-paragraph.json`,
`changed-equation.json`, `raw-less-than.json`, `unresolved-handoff.json`, and
`request-options.json`. `P2ReplayTests` asserts every fixture labels its synthetic origin and
replays each defect; `P2NativeReplayTests` delivers the raw-`<` fallback through the native
renderer. The unknown cause of the historical Gemini rejection remains unknown and is not claimed
here.

## Delivered-image inspection (historical artifacts)

These images were produced by the pilot before this phase's code, so they carry their original
status and are not evidence that the phase 2 changes improved output quality. They were inspected
against the design's questions (central contribution, mechanism, panel handoffs, brief fidelity,
readability).

| Case | Artifact | SHA-256 (first 16) | Local checks | Finding |
| --- | --- | --- | --- | --- |
| Architecture (`1706.03762v7`) | `.scratch/overview-rebuild/live/library/papers/1706.03762v7/reader/overview-figures/f2c66665506b4f61afce3efd3428bc3c/fig1.png` | `6536805ed1b6168d` | 0 issues, 940×1855 | Central question and the attention-vs-recurrence mechanism are clear; the finding's 28.4 BLEU En–De, 41.8 BLEU En–Fr, and >2.0 BLEU margin match the paper; the final panel gives the O(n²·d) cost with the sequence-length qualification. |
| Method (`2511.07694v1`) | `.scratch/overview-rebuild/live/library/papers/2511.07694v1/reader/overview-figures/cff86beaac7948e5bb59fc7350522812/fig1.png` | `07a33cc8b3c8033a` | 0 issues, 940×3220.9 | Panels 1, 3, and 4 match the approved brief exactly, including 11 of 15 cases, 0.739/0.715/0.646, 2.4%, and the per-dataset AUC pairs. The mechanism panel's concrete probabilities (0.55, 0.22, 0.11, 0.05, 0.03, α = 0.05) are teaching values the brief did not declare as illustrative, so a reader could mistake them for paper numbers. Earliest source: the panel brief, which left the example values to the drawing. |
| Survey/comparison (`2606.19868v1`) | `.scratch/overview-rebuild/live/library/papers/2606.19868v1/reader/overview-figures/baf40cd4e06f46ed934b2f58308f806a/fig1.png` | `d28032aeeff8cc15` | 0 issues, 1171.4×3116.1 | The organising question and scoring target come first, the paradigm/estimator taxonomy is shown as a comparison, the SteerConf hybrid-fusion panel demonstrates the mechanism, the evaluation panel carries the standardization table, and the final panel lists surrogate dependence, sensitivity, latency/cost, and multi-agent consensus limitations. Secondary table text is small at the intended scale. |

Report semantics recorded for these historical images: delivery `completed`, drawing outcomes as
reported by the pilot, `local_checks` pass from their persisted geometry checks, and independent
inspection recorded as an agent review only. The application default remains `not_reviewed`;
no inspection pass is inferred from empty geometry issues.

## Pre-existing failures and environment limits

- `tests/test_app.py::ApplicationHTTPTests::test_cancel_running_overview_keeps_existing_generation`
  and `::test_real_overview_and_combined_exports` fail on a clean worktree at HEAD
  (`2b7afbd`) with the same assertions, so they are not caused by phase 2. The first is a timing
  failure waiting for a mocked provider call; the second fails the Blog export job.
- `tests/test_pdf_fallback.py::PDFFallbackTests::test_overview_pipeline_uses_pdf_pages_and_records_format`
  and the `visual=False` subtest of
  `tests/test_reading_bibliography.py::BibliographyTests::test_planning_and_authoring_use_filtered_evidence_in_both_modes`
  error because the optional `smolagents` dependency from `requirements-ai.txt` is not installed in
  this environment. Local reading, conversion, and the visual Overview path remain available.
- An unavailable native renderer still cannot count as a native pass. The runs above used the
  freshly built helper, and the native fixtures were exercised.

## Live evaluation follow-up (2026-09-13)

An authorized live evaluation ran five providers across the three retained papers (architecture
`1706.03762v7`, method/PRO `2511.07694v1`, and UQ survey `2606.19868v1`). The compiled results —
final PNG paths and digests, turns, tokens, elapsed time, panel outcomes, planning reductions,
per-stage options, and image checks — are in `docs/verification/overview-rebuild-observations.md`. The live run set
confirmed the phase 2 recovery paths: Gemini's previously failing narrative cells for the
architecture and method papers completed, DeepSeek's architecture run that had died on a malformed
SVG completed, and DeepSeek's 1,324-character-focus survey cell completed. It also exposed two
implementation defects and one contract gap:

1. **Bold fallback wrapping.** The simplified fallback measured regular weight while drawing bold
text, so a DeepSeek survey Brier-score line overflowed the panel canvas by 11.8 px and the run
failed with no recoverable panel. `measure_text_widths` now takes the drawn `font_weight`, and
`_wrap` forwards it. Regression: `tests/fixtures/overview-p2/bold-wrap-overflow.json` and
`P2NativeReplayTests.test_the_bold_equation_replay_fits_the_fallback_canvas`.
2. **Unusable supplemental-evidence request.** A planner `request_evidence` naming handles absent
from the source map raised an uncaught `ValueError` and killed the Terra method run.
`supplement_evidence` now records `evidence_supplement_unresolved` and keeps the existing evidence,
and `plan_overview` discloses an unincorporated narrative supplement as a planning reduction.
Regressions: `test_an_invalid_supplemental_narrative_request_is_disclosed_not_fatal` and
`test_an_invalid_planner_supplement_is_disclosed_not_fatal`.
3. **Numbers inside semantic statements are unprotected.** The Luna method drawing changed the
approved results (3.3 %→3.1 %, 6.5 %→0.5 %, 0.819→0.841, 0.806→0.816) because the brief put them
in a `statement` with no `exact_text`; the numeric omission check deliberately covers only `value`
items and declared exact text. The panel-plan and clarify prompts now require result numbers to be
exact shared facts or `value` items. A stricter numeric check for prose is a possible follow-up,
not implemented.
4. Sol's architecture and method runs were stopped after hanging at the first selection request for
about 11.5 minutes; Sol survey completed in 377 s. Both stopped cells left a run directory in
`running` state with no model events. No dollar costs were recorded.

Focused suites after the two fixes: `tests.test_overview_workflow tests.test_panel_authoring
tests.test_panel_guides tests.test_explanation tests.test_ai tests.test_agent_overviews` — 178
tests, OK, 18 skipped.

## Remaining live validation

No further provider call is authorized by this report. What remains:

1. Re-run the two stopped Sol cells with a larger per-request timeout or a smaller selection
   prompt, and, if the planner contract changes for statement numbers, re-run one Luna paper to
   confirm result numbers survive drawing.
2. Inspect the new complete images as a human reviewer and record `independent_inspection` with
   artifact path, digest, and findings. The agent image checks are recorded in
   `docs/verification/overview-rebuild-observations.md`; the strongest open item there is the Luna method number
   change above, followed by deepseek's fallback-heavy panels and Terra survey's garbled simplified
   finding text.
3. Run a controlled reasoning-on/off comparison holding paper, evidence, model, prompt revision,
   code/diff digest, and output settings fixed, changing only the reasoning setting, and record
   cache differences and run-level fallback.

Improved novice understanding remains an empirical result for that inspection; the offline checks
and the live matrix establish contracts, recovery, reporting, and delivery, not image quality.
