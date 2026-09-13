> **Superseded 2026-09-13.** The phase 2 implementation continued from this checkpoint and is
> complete. For the final state, test results, inspected artifacts, and remaining live-validation
> needs, read `docs/verification/2026-09-13-overview-rebuild-p2.md`. This file is kept as the
> historical handoff record of the partial state and is not a completion report.

# Overview rebuild phase 2 — partial implementation checkpoint

Status: **incomplete; implementation paused during Task 1/2/3, with Task 4 partially rewritten.**
This file records what has actually been changed, what has been tested, and what remains. It is a
handoff checkpoint, not a completion report and not a substitute for
`docs/verification/2026-09-13-overview-rebuild-p2.md`.

## Starting point and baseline

- Branch: `akhil/model-authored-svg-overviews`
- Head commit at checkpoint start: `2b7afbd0c52676ea0d1fff2aaa7043c655855129`
  (`State every planner JSON contract explicitly`)
- Starting dirty worktree: the six files the phase 2 plan names as the starting point are still
  modified in place; no unrelated tracked file was reverted.
- Starting six-file diff snapshot and digest:
  - `.scratch/overview-rebuild-p2/baseline/six-file.diff`
  - SHA-256: `24776969a4e2d3c5244eff9d0e3f1847276ffa2328ba7775c45a779907b786d9`
  - `.scratch/overview-rebuild-p2/baseline/git-state.txt` records `git status --short --branch`
    and the starting diffstat.
- Current partial six-file diff snapshot:
  - `.scratch/overview-rebuild-p2/partial-six-file.diff`
  - SHA-256: `7b77b4f4b6584c1a2a481134f3cb6f53a555717765a4b0cf6403a417ab4abe87`

The six starting files are `papers/explanation.py`, `papers/overview_workflow.py`,
`papers/panel_authoring.py`, `papers/panel-guides/authoring.md`,
`tests/test_overview_workflow.py`, and `tests/test_panel_authoring.py`. They already contained the
phase 1 follow-up changes described in `overview-rebuild-p2.md`; those changes were treated as the
starting point and not reverted.

## Implemented so far

### Task 1 — run lifecycle and request evidence (partial)

`papers/overview_workflow.py` now contains:

- `RunStore`, writing an append-only `events.jsonl` and an atomically replaced `run.json` under
  each run directory.
- `create_run_directory(document)`.
- `Coordinator(..., *, run_directory=None)` with:
  - `run_directory` / `store`,
  - `call_with_event(...)` (the existing `call(...)` response-only wrapper remains),
  - `record_normalization(...)` for parsed/normalized candidates and validator issue paths,
  - `active_stage` tracking.
- `plan_overview(..., run_directory=None)`, which creates a run directory if the caller does not
  supply one, passes it to `Coordinator`, and on exception writes a terminal failed/cancelled
  `run.json` without replacing the original exception.
- Model request events include `stage`, request ordinal, actual provider options, start/end times,
  elapsed seconds, reported usage, response availability, response file reference, and
  normalization status/issue paths. Raw response text is stored separately under
  `requests/NNNN-response.txt`; parsed and normalized candidates are stored under
  `requests/NNNN-candidate.json` and `requests/NNNN-normalized.json`.
- Transport/authentication failures record `has_response=False`, `usage=None`, and no candidate
  rather than inventing a response or usage estimate.
- Response text is scrubbed of base64 image payloads before being written.

**Still required for Task 1:**

- `generate` must create the run directory **before** planning, pass it to `plan_overview`, and
  reuse the same directory for drawing/composition. It currently calls `plan_overview` with no
  `run_directory` and creates a *second* run directory afterward.
- The full `generate` lifecycle must be wrapped in failure/cancellation finalization.
- Drawing-stage request options/timings are not yet written into the run record.
- No Task 1 regression tests have been added.
- Existing run-directory creation after planning is still present in `generate`.

### Task 2 — Overview narrative contract and correction (partial)

`papers/explanation.py` now contains:

- `OVERVIEW_CANDIDATE_MAX_BYTES = 256 * 1024`; the limit is checked before processing and reported
  as a resource-limit validator issue.
- `validate_overview_narrative(value, document)`, separate from Blog's `validate_plan`:
  - nonempty text without the shared 1,200-character cap,
  - list-of-string `visual_focus` normalised to newline-separated text,
  - mixed-type list rejection,
  - unknown passage ID, empty claim, invalid relationship, and unsupported paper type rejection,
  - zero relationships allowed,
  - exact issue paths suitable for correction.
- `recover_overview_narrative(candidates, document)`:
  - narrow recovery only when one candidate has all four valid, source-linked claims,
  - derives `visual_focus` from that candidate's contribution,
  - drops invalid optional relationships and records them under `_recovery`,
  - never borrows claims from another candidate,
  - returns `None` when no candidate qualifies.
- `narrative_claim_keys` remains usable for panel-plan ownership.

`papers/overview_workflow.py` now contains a custom `_narrative(...)` flow that:

- makes up to two narrative requests,
- stores both parsed candidates,
- sends the rejected answer back as an `assistant` message before the correction request,
- includes exact issue paths and preservation instructions in the correction,
- attempts `recover_overview_narrative` after a second rejection,
- returns a specific `ProviderError` when no candidate contains the required valid claims.

`plan_overview` now calls this flow, records a reduction reason for narrative recovery, and
attempts supplemental retrieval by sending the new evidence with the existing draft to a second
narrative call.

**Still required for Task 2:**

- Regression tests for the 1,324-character focus, array normalization, mixed arrays, unknown
  passage IDs, empty claims, unsupported paper types, candidate-size limit, assistant-message
  correction, candidate saving, and narrow recovery.
- Confirm/update the exact second-call failure behavior when supplemental evidence cannot be
  incorporated.
- Blog compatibility remains structurally unchanged but needs a final regression run.
- No `tests/test_explanation.py` changes have been written for the new contract.

### Task 3 — exact display text (partial)

`papers/explanation.py` now contains:

- optional `exact_text` on shared facts (schema + manual collector validation),
- `EXACT_TEXT_ITEM` cap of 120 characters,
- validation that each exact entry is copied from the same fact text using whitespace-normalized
  comparison,
- `panel_assignments` projection of `exact_text` as the ordered union of referenced facts' exact
  strings, complete `equation` items, and complete `label` items.
- `_flatten_text` helper used for that validation.

`papers/overview_workflow.py` prompt text now:

- includes `exact_text` in the panel-plan contract,
- distinguishes semantic `text` from exact display strings,
- tells the clarification pass to choose short exact strings and establish canonical linear
  notation rather than leaving source notation ambiguous.

`papers/panel_authoring.py` now prints an `exact display text that must appear in the drawing
unchanged` section in `assignment_block` when the assignment carries `exact_text`.

**Still required for Task 3 (most of the task):**

- Replace whole-shared-fact substring checks in `panel_authoring.required_values` /
  `missing_values` with declared exact-display checks plus numeric token omission checks. The old
  implementation is still in place.
- Compare canonical equation/label text with whitespace normalization and XML entity decoding only.
- Remove `LATEX_SYMBOLS`, the regex-based `plain_notation`, and all semantic LaTeX rewriting from
  authoring; recovery must preserve unresolved source notation literally, XML-escaped, visibly
  identified as source notation, and recorded as reduced presentation.
- Update `simple_panel_source` / `simple_panel` so every recovery path preserves illustrative
  labels and source notation.
- Add the encoder-paragraph, changed-operator, changed-value/unit, missing-label, and
  `\frac{a+b}{c+d}` recovery fixtures/regressions.
- Update `papers/panel-guides/authoring.md` to distinguish semantic content from exact labels and
  equations. The current guide still has the phase 1 equation section and does not make the full
  distinction.
- No new Task 3 tests have been written; the existing old tests still pass because they exercise
  the old helper behavior.

### Task 4 — planner issues and reductions (partial)

`papers/overview_workflow.py` now contains a rewritten `plan_panels` that:

- builds each refinement's context from the latest retrieved evidence,
- retains structurally valid drafts when clarification is malformed,
- carries active issues forward when the next plan content is unchanged,
- uses the final simplify pass to remove dependencies and records removed connections,
- validates the independent-claim fallback against a reduced narrative projection with
  relationships removed,
- returns `assignment_source`, `remaining_issues`, `planning_reduced`, and
  `planning_reduction_reasons`; `plan_overview` combines planner reductions with narrative
  recovery reductions,
- records planner pass, validation-error, dependency-removal, and fallback events.

**Still required for Task 4:**

- Add the required regressions for:
  - a structurally valid final plan with unresolved reported handoffs,
  - a valid draft followed by malformed clarification,
  - supplemental evidence requested during the first planner pass.
- Prove the fallback fixture cannot pass by selecting an unrelated clean draft.
- Review the `_carry_forward_issues` heuristic against the "later issue applies to an earlier
  draft" rule; it is implemented but not independently tested.
- The returned `plan_panels` shape changed internally to a 6-tuple; confirm no test or caller
  depends on the old shape.
- Preserve original issues/actions in events satisfying the exact phase 2 reporting contract.

### Task 5 — drawing request options (not implemented, aside from the starting-point work)

The starting worktree already forwards `provider_options` through planner requests and contains
existing stage options. The actual drawing request path is still incomplete:

- `request_panel(...)` does not accept `options=None`.
- `_author_once(...)` does not compute or pass `panel` / `panel_repair` options.
- Effective drawing options are not recorded per attempt alongside timings.
- No capturing-provider tests exist for `Provider.complete` kwargs or the encoded request body.

### Task 6 — safe local recovery and preserved work (not implemented)

Still in their old form:

- `_simplified_panel` still contains the overlapping reduced-recovery branch.
- `reduced_assignment` still exists.
- `simple_panel_source` still runs the old LaTeX normaliser and old value handling.
- `build_panels` records simplified panels but does not separate original drawing defects from
  the accepted fallback's active issue list in the required way.
- Final composed-image `checks` are not inspected/rejected before returning a publishable result.
- No fallback-renderer-exception, composition-failure, missing-renderer, or exact-text-mismatch
  regressions have been added.

### Task 7, verification, and handoff (not started)

- No `tests/fixtures/overview-p2/` replay fixtures.
- No report function/regression distinguishing delivery, reduced planning, checked image, and
  independent inspection.
- No `docs/verification/2026-09-13-overview-rebuild-p2.md`.
- No design-document update.
- No complete offline replay or full test suite run.
- No independent human image inspection; that must remain `not_reviewed` until actually performed.

## Test status at this checkpoint

These are the focused runs performed; they are not the phase 2 completion suite.

| Command | Result |
| --- | --- |
| `python3 -m unittest tests.test_explanation tests.test_overview_workflow` | 39 tests, **2 failures**, 0 errors. The failures are outdated assertions, not hidden-task execution. |
| `python3 -m unittest tests.test_panel_authoring tests.test_ai` | 45 tests, 0 failures, 12 skipped (native renderer env not configured in this run). |
| `python3 -m unittest tests.test_agent_overviews` | OK; 24 tests, 17 skipped in this environment. |
| `git diff --check` | clean. |
| `python3 -m py_compile` / AST parse of the three changed Python files | parses; two pre-existing invalid-escape `SyntaxWarning`s remain in `overview_workflow.py` prompt strings. |

The two known failures:

1. `tests/test_overview_workflow.py::AssignmentProjectionTests.test_every_assignment_carries_the_fields_a_panel_author_needs`
   expects the old assignment field set and does not yet expect the new `exact_text` field.
2. `tests/test_overview_workflow.py::PlannerSequenceTests.test_a_step_list_for_visual_focus_is_joined_and_recorded`
   expects the old space-joined focus; phase 2 now joins the ordered steps with newlines.

Both tests need to be updated to the phase 2 contract as part of Task 2/3.

Not run yet: `unittest discover -s tests`, the native renderer suites with
`LOCALXIV_HTML_RENDERER` set, `tests.test_app`, `tests.test_exports`, `node tests/test_app_ui.js`,
or `node tests/test_extension.js`.

## Important risks and incomplete integration points

- **`generate` is not yet lifecycle-safe.** It creates a new directory after planning while
  `plan_overview` may already have created one. The same run must own planning, drawing,
  composition, and finalization.
- **New Task 1 persistence has no assertions yet.** `RunStore`, `events.jsonl`, `run.json`,
  terminal-state finalization, and response/candidate files are implemented but only exercised
  incidentally by the existing planning tests.
- **`recover_overview_narrative` returns a private `_recovery` key.** The workflow pops it, but
  its exact external contract needs a tracked regression.
- **`plan_panels` heuristic correctness is unproven.** The draft-retention and issue-carry-forward
  rules pass the old scripted tests but do not yet cover the phase 2 required scenarios.
- **Task 3 is not wired into acceptance.** `exact_text` reaches the assignment and prompt, but
  `missing_values` still enforces the old behavior, so changed operators, changed units, and
  missing labels are not yet caught by `_panel_issues`.
- **Recovery still rewrites LaTeX.** The unsafe `plain_notation` normaliser and overlapping
  reduced recovery are still present, so the raw-`<`/fraction-grouping failures are only partly
  mitigated.
- **Drawing options are not actually applied.** The pre-existing `provider_options` function and
  its tests exist, but `request_panel` ignores them, so the Task 5 symptom remains.
- **No composition or delivery reporting.** A render that succeeds with active geometry issues
  can still become a publishable result, and no report reads the new run record.
- The complete phase 2 work is not authorized to make live provider calls at this checkpoint.

## Recommended resume order

1. Finish Task 1: make `generate` create one run directory before planning, pass it down, reuse it
   for drawing/composition, and move failure/cancellation finalization into its `finally` path;
   add the four required lifecycle regressions.
2. Finish Task 2 tests and tighten recovery/second-call behavior.
3. Finish Task 3 end to end in `papers/explanation.py`, `papers/panel_authoring.py`,
   `papers/panel-guides/authoring.md`, and the authoring prompt; remove the old LaTeX conversion.
4. Complete Task 4 tests and the required unresolved-handoff fallback fixture.
5. Complete Task 5 options forwarding and request-boundary tests.
6. Complete Task 6 recovery/composition checks and regressions.
7. Add fixtures/reporting/verification for Task 7 and finish the full focused + discover suite.

Do not revert the six starting files or the partial changes above. The next implementation should
continue from this checkpoint and keep the existing phase 1 edits intact.
