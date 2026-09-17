# SVG reliability: offline integration verification

Executed on 2026-09-17 in `.worktrees/svg-reliability`; the filename follows the plan date.
Production baseline for Task 3: `aa4a2e1`; combined regression commit: `1456b2c`. Scope: SVG reliability plan (plan removed; in git history), Tasks 1–3.

## Result

Task 3 adds one combined regression in `tests/test_overview_workflow.py`:
`GenerateLifecycleTests.test_planner_correction_and_local_drawing_repair_deliver_native_assets`.
No production change was needed. Planning, validation, assignment projection, concurrent drawing coordination, native WebKit measurements, composition, asset rendering, and PDF export run for real. Only provider responses are scripted; no paid calls, installs, or credentials access occurred.

The synthetic three-panel fixture deliberately returns a mismatched shared-fact `exact_text` (`0.75` instead of approved `0.73`/`0.27`) in both draft and clarification. The last allocated planner response corrects it without removing any panel, handoff, shared fact, or relationship owner. Panel p2 then returns 9-unit text; native checks request one local repair with the measured 14-unit minimum, and the corrected drawing is accepted.

Assertions cover:

- Five planning calls: selection, narrative, draft, clarification, final structural correction (the existing `panel_plan_simplify` trace label). Four drawing calls: three creations and one p2 repair. No whole-document repair or extra completion/review request.
- Recorded start/finish intervals of all three initial requests overlap. Initial creations rendezvous at a three-party barrier with a five-second timeout; local repairs bypass it. No timing sleep is used to manufacture overlap. Delivered panel order remains p1, p2, p3.
- Saved narrative and approved plan remain equal to the fixture, including the source-linked relationship and both handoffs. Shared story reaches every creation/repair prompt; layout intent reaches p2 repair; source handles and retained passage text do not leak to authors.
- Outcomes are `created=[p1,p3]`, `repaired=[p2]`, `simplified=[]`; planning is not reduced. Planner/drawing/composition active issues are empty.
- Real nonempty HTML, SVG, editable SVG source, PNG and PDF files exist. PNG/PDF signatures are checked; SVG/PNG/PDF paths pass the owned export selector; `export_pdf` produces a byte-identical copy of the native PDF.
- Per-panel and composition checks are read from disk. Run delivery is completed, local checks pass, nine usage entries total 47 **synthetic** tokens, and the local repair appears in persisted request accounting.
- Scientific inspection remains `not_reviewed`; no fabricated approved review is attached. `drawing_defects` is empty after successful repair (it records defects retained for simplified fallback, not a history of every resolved defect).

Assets are generated inside the test's temporary document directory and removed on completion, not committed as a purported scientific evaluation corpus.

## Test-first record

The regression was written before any potential production edits. First run failed on an incorrect test assumption that successfully repaired panels populate `run_report()['drawing_defects']`. Inspection of `PanelRun.accept` and `build_panels` established that this field preserves defects for fallback; repaired outcome and attempts are recorded separately. The test was corrected to the existing contract, including the nested on-disk checks schema and `Path` export argument. This was **not a production RED** and is not claimed as one.

The corrected regression passed on unchanged production. A subsequent assertion checks actual request interval overlap rather than relying only on multiple thread names. That final regression also passed. This is integration coverage of Tasks 1–2, not an invented bug fix.

## Commands and observed evidence

All commands run from the worktree root with system Python 3.14.7. The existing locally built `papers/html-snapshot` is a Mach-O arm64 executable. The controller previously built it with `swiftc -O papers/HTMLSnapshot.swift -o papers/html-snapshot`; Task 3 reused it rather than claiming a new build.

```sh
python3 --version
# Python 3.14.7
file papers/html-snapshot
# Mach-O 64-bit executable arm64

env LOCALXIV_HTML_RENDERER=$PWD/papers/html-snapshot python3 -m unittest tests.test_overview_workflow.GenerateLifecycleTests.test_planner_correction_and_local_drawing_repair_deliver_native_assets
# First: 1 test, FAILED (1 incorrect drawing_defects expectation), 1.155s.
# Corrected: 1 test, OK, 1.414s.
# With interval-overlap assertion: 1 test, OK, 1.216s.
# Final pre-commit repeat after removing dependency symlink: 1 test, OK, 1.153s.

env LOCALXIV_HTML_RENDERER=$PWD/papers/html-snapshot python3 -m unittest tests.test_explanation tests.test_overview_workflow tests.test_panel_authoring
# 181 tests, OK, no skips, 42.193s.
# Final repeat including interval assertion: 181 tests, OK, no skips, 44.728s.

env LOCALXIV_HTML_RENDERER=$PWD/papers/html-snapshot python3 -m unittest tests.test_blog_figures tests.test_panel_guides tests.test_svg_figures tests.test_exports tests.test_agent_overviews tests.test_algorithm_and_prompt_fidelity
# 117 tests, OK (skipped=43), 27.864s.
# Final repeat: 117 tests, OK (skipped=43), 36.996s.
# All 43 skips are smolagents-gated agent integration tests.

node tests/test_app_ui.js
# Exit 0: UI reading controls, setup, Library navigation, rendering, and sandbox checks passed.

git diff --check
# Exit 0, no output.
```

Task 3's original two requested Python suite groups: **298 discovered, 255 passed, 43 skipped**. The final fix wave below supersedes these counts. This includes the existing malformed-output fallback, exact-text safety, cancellation, failed-run, renderer-failure, composition-rejection, and legacy/Blog contract coverage; those tests were not weakened or removed.

### Adjacent app limitation, not a green app claim

```sh
env LOCALXIV_HTML_RENDERER=$PWD/papers/html-snapshot python3 -m unittest tests.test_app
# 31 tests, FAILED (failures=4), 27.648s: 27 passed, no skips.

test -f /Users/silver/Developer/arxiv-paper-to-kindle/node_modules/mathjax-full/es5/tex-svg.js && ln -s /Users/silver/Developer/arxiv-paper-to-kindle/node_modules node_modules
# Exit 0; temporary worktree-only symlink to existing dependencies, read-only use.

env LOCALXIV_HTML_RENDERER=$PWD/papers/html-snapshot python3 -m unittest tests.test_app
# 31 tests, FAILED (failures=3), 26.105s: 28 passed, no skips.

env LOCALXIV_HTML_RENDERER=$PWD/papers/html-snapshot python3 -m unittest -v tests.test_app.ApplicationHTTPTests.test_a_no_figure_blog_delivers_without_figure_assets
# 1 test, FAILED (failures=1), 0.547s:
# AI generation requires requirements-ai.txt. Local reading and conversion remain available.
```

The MathJax static-asset 404 (`test_auth_host_origin_and_static`) disappeared with the existing dependency symlink. The three remaining failures are `test_a_no_figure_blog_delivers_without_figure_assets`, `test_cancel_running_overview_keeps_existing_generation`, and `test_real_overview_and_combined_exports`: the unavailable AI dependency prevents reaching their intended job paths. The controller had already recorded the four failures at the pre-Task-3 baseline. Task 3 independently reproduced them, then isolated the MathJax failure; it did not rerun an archived baseline or install `smolagents`. The temporary symlink was removed after verification.

## Final fix wave (2026-09-17)

Three additional regression methods in `tests/test_overview_workflow.py` cover the final review findings:

- Oversized factorial, question-mark operator, decimal/number/single-letter punctuation, and bracketed expressions cannot leave partial expressions in shared orientation. Extraction uses conservative prose boundaries and bracket checks; uncertain oversized fields may be omitted. Original narrative and exact display text remain untouched.
- Invalid draft → invalid clarification → accepted correction discloses missing original panels/handoffs as well as missing intermediate additions. Restored items are not reported as losses. The existing defensive raw-container reader is reused; request count stays at five.
- Evidence added after clarification can make an identical final payload structurally valid, but cannot clear a prior semantic report. The result falls back with the semantic reason, not the now-resolved unknown-passage diagnostic; no extra requests.

The integration regression's 50 ms delays were replaced by bounded creation-only barrier synchronization, preserving actual interval overlap and the successful local repair/native export assertions.

Test-first evidence:

```sh
python3 -m unittest tests.test_overview_workflow.AssignmentProjectionTests.test_oversized_scientific_punctuation_never_yields_expression_fragments tests.test_overview_workflow.PlannerSequenceTests.test_final_correction_discloses_losses_across_invalid_candidates tests.test_overview_workflow.PlannerSequenceTests.test_supplemented_evidence_does_not_clear_a_reported_semantic_issue
# Before production edits: 3 tests, FAILED (5 subtest/assertion failures), 0.016s.
# Factorial/operator/bracket fragments and missing original losses reproduced.
# The evidence test initially asserted against request diagnostics too early.

python3 -m unittest tests.test_overview_workflow.PlannerSequenceTests.test_supplemented_evidence_does_not_clear_a_reported_semantic_issue
# Corrected assertion, still before production edits: 1 test FAILED, 0.006s.
# Actual source was planner instead of narrative_fallback.

python3 -m unittest tests.test_overview_workflow.AssignmentProjectionTests.test_oversized_scientific_punctuation_never_yields_expression_fragments
# Additional numeric/single-letter period cases before hardening: 1 test,
# FAILED (2 subtests), 0.001s. Conservative boundary rules fixed these too.

env LOCALXIV_HTML_RENDERER=$PWD/papers/html-snapshot python3 -m unittest tests.test_overview_workflow.AssignmentProjectionTests tests.test_overview_workflow.PlannerSequenceTests tests.test_overview_workflow.GenerateLifecycleTests.test_planner_correction_and_local_drawing_repair_deliver_native_assets
# Initial fix: 44 tests, OK, no skips, 2.798s.

env LOCALXIV_HTML_RENDERER=$PWD/papers/html-snapshot python3 -m unittest tests.test_explanation tests.test_overview_workflow tests.test_panel_authoring
# Final after punctuation hardening: 184 tests, OK, no skips, 44.937s.

env LOCALXIV_HTML_RENDERER=$PWD/papers/html-snapshot python3 -m unittest tests.test_blog_figures tests.test_panel_guides tests.test_svg_figures tests.test_exports tests.test_agent_overviews tests.test_algorithm_and_prompt_fidelity
# Final: 117 tests, OK (skipped=43), 36.953s.

node tests/test_app_ui.js
# Exit 0: UI reading controls, setup, Library navigation, rendering, and sandbox checks passed.

env LOCALXIV_HTML_RENDERER=$PWD/papers/html-snapshot python3 -m unittest tests.test_app
# 31 tests, FAILED (failures=4), 26.623s; same four failures documented above.
# No dependency symlink or installation in this fix wave.

git diff --check
# Exit 0.
```

Final requested Python groups: **301 discovered, 258 passed, 43 skipped**. Separately, app suite: **27 passed, 4 failed**. Native renderer reused, not rebuilt. No paid calls, subagents, credentials access, installs, merges, or pushes. These offline scripted-provider checks do not establish live-model or scientific quality.

## Fresh combined-suite verification (2026-09-17)

The controller's fresh combined 301-test run failed only the combined recovery regression's strict interval assertion: `max(started_at) == min(finished_at) == 188291.87`. Production records these monotonic timestamps rounded to three decimal places, so overlapping requests can have equal recorded endpoints. The test now uses `assertLessEqual` with a precision comment; the three-party creation barrier, multiple-thread check, request counts, and repair/native-export assertions remain intact. This follow-up changes only the test and this document, not production.

```sh
env LOCALXIV_HTML_RENDERER=$PWD/papers/html-snapshot python3 -m unittest tests.test_overview_workflow.GenerateLifecycleTests.test_planner_correction_and_local_drawing_repair_deliver_native_assets
# After the assertion fix: 1 test, OK, 1.099s.

env LOCALXIV_HTML_RENDERER=$PWD/papers/html-snapshot python3 -m unittest tests.test_explanation tests.test_overview_workflow tests.test_panel_authoring tests.test_blog_figures tests.test_panel_guides tests.test_svg_figures tests.test_exports tests.test_agent_overviews tests.test_algorithm_and_prompt_fidelity
# Fresh combined rerun: 301 tests, OK (skipped=43), 69.004s.
```

Fresh combined result: **301 discovered, 258 passed, 43 skipped**, exit 0. The 43 skips remain smolagents-gated integration tests. This rerun supersedes the controller's quantized-timestamp assertion failure; the earlier split-suite and separate app/UI results above are historical, not fresh reruns of those separate commands.

## Limits and review handoff

- Scripted provider output establishes integration behavior and bounded call accounting, not live-model reliability, latency, token cost, visual quality, or scientific correctness. The simple text-based SVG fixture is deliberately not a high-quality explanatory diagram.
- Native geometry and exact-display checks do not establish that the central mechanism is scientifically correct or understandable to a novice. No image inspection or live-model evaluation is claimed.
- The full app and smolagents agent integration paths remain incompletely verified in this environment. UI checks are the existing Node script, not an interactive browser test.
- No extra request, gate, reasoning policy, or dependency was added. Production recovery and shared-context behavior did change across this branch, including correction-loss disclosure, semantic-issue retention, and conservative scientific-expression boundaries. Prior-generation preservation still depends on the existing save boundary; the app-level cancellation test is among the dependency-blocked failures.
- The implementing worker reviewed its scoped diff. Independent whole-branch review remains with the controller, as this task explicitly prohibited spawning subagents. Do not treat this report as that independent review.
