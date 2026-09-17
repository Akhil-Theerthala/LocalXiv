# Overview rebuild, phase 2 implementation plan

> **For agentic workers:** Use `superpowers:executing-plans` to implement this plan task by task. Steps use checkboxes for tracking. Read the linked design first; this document supplies the corrections identified by the subsequent error analysis.

**Goal:** Recover from harmless planner formatting errors, preserve the meaning of panel content, and report accurately what the workflow delivered.

**Architecture:** Keep the current narrative → panel planning → parallel SVG authoring → local rendering pipeline. Correct its contracts and recovery at their existing boundaries. Persist diagnostics from the first request and keep delivery status separate from independent assessment of the explanation.

**Tech stack:** Python standard library, existing provider client, JSON contracts, SVG, native WebKit rendering, and `unittest`.

**Spec:** [Overview rebuild design](docs/superpowers/specs/2026-09-13-overview-workflow-rebuild-design.md). The [first implementation plan](docs/superpowers/plans/2026-09-13-overview-workflow-rebuild.md) describes the original migration. Phase 2 supersedes their contract, recovery, and reporting details only where this document says so.

**Status:** Implementation proposal written after inspection on 2026-09-13. Creating this plan does not execute it or authorize paid provider runs.

> **Implementation status 2026-09-13:** phase 2 is implemented and verified offline. Every task's
offline acceptance tests pass; no live provider run was made. Live-evaluation checkboxes below
remain unticked on purpose. See `docs/verification/2026-09-13-overview-rebuild-p2.md` for results,
inspected artifacts, and remaining live-validation needs.

## Scope and constraints

- The overview is one image with 1–7 numbered panels.
- Image dimensions follow content; there is no fixed page size, aspect ratio, or whole-image word budget.
- Panels read left to right, then top to bottom.
- Planning owns scientific meaning, shared examples, notation, and panel handoffs.
- Each panel author receives a complete drawing assignment and builds only that panel.
- The first panel-plan refinement clarifies; the second simplifies and removes troublesome dependencies before drawing proceeds.
- Panel generation runs concurrently; completion order never changes reading order.
- The intended structure is 1–2 narrative calls, 1–3 panel-plan calls, and one creation call plus one repair call where needed per panel.
- Those call counts describe the normal workflow, not a universal request ceiling. Selection, retrieval-related requests, and transport retries are reported separately.
- Regeneration keeps the saved overview available until a complete replacement is ready.
- Reading, conversion, Blog generation, and existing saved artifacts remain usable.
- No new runtime dependency or generic agent framework is required.
- Keep the existing SVG reference examples and construction notes. Panel framing, compositor bounding boxes, viewer redesign, and broad provider optimisation are outside this phase.

The six currently modified files are the starting point, not disposable work. Preserve unrelated changes and historical run artifacts. Retain the useful XML escaping, safe 32-character IDs, explicit output contracts, error reasons, and timing changes after testing their actual call paths. Replace the unsafe notation conversion and incomplete recovery behaviour described below.

## Confirmed failures driving this plan

| Observation | Consequence | Task |
| --- | --- | --- |
| Overview narrative uses the shared 1,200-character validator; correction omits the rejected answer | Usable content fails or gets regenerated unnecessarily | 2 |
| Shared facts are checked as verbatim sentences, while equations are often checked only for numbers | Faithful diagrams get repaired; changed operators can pass | 3 |
| Planner fallback is absent from simplified-panel counts; unresolved planner issues can survive acceptance | Reduced or conflicted explanations look like ordinary success | 4, 7 |
| Recovery previously emitted raw `<`; the new fraction conversion drops grouping | A late crash or a readable but wrong formula | 3, 6 |
| Planner events are written only after planning succeeds | Early failures lose the evidence needed to diagnose them | 1 |
| Drawing requests omit the configured thinking arguments | Run labels do not establish actual drawing configuration | 5 |

The existing matrix establishes failures and costs for those runs. It does not establish the cause of the unknown Gemini rejection, the scientific quality of every successful image, or a controlled reasoning-on/off comparison.

## File responsibilities

| File | Phase 2 responsibility |
| --- | --- |
| `papers/explanation.py` | Separate Overview narrative validation from Blog; validate exact display requirements and project complete assignments |
| `papers/overview_workflow.py` | Persist the run lifecycle; preserve correction candidates; resolve planner failures; forward request options; recover and compose safely |
| `papers/panel_authoring.py` | Enforce declared display requirements; preserve notation; escape and render fallback text |
| `papers/panel-guides/authoring.md` | Explain canonical notation and freedom to express prose visually |
| `papers/ai.py` | Existing request encoding; change only if a request-boundary test exposes a client defect |
| `tests/test_explanation.py`, `tests/test_overview_workflow.py`, `tests/test_panel_authoring.py`, `tests/test_ai.py` | Regression and request-boundary tests |
| `tests/fixtures/overview-p2/` | Small, credential-free replay inputs and SVGs for the reproduced defects |
| `docs/verification/2026-09-13-overview-rebuild-p2.md` | Commands, actual results, artifact inspection, and remaining limitations |

Use the current local pilot at `.scratch/overview-rebuild/live/pilot.py` for a later authorized evaluation. Its reporting must consume phase 2 records on failure as well as success. Keep reproducible assertions in tracked tests; `.scratch` is evidence, not a production dependency.

## Task 1: Preserve evidence before any request can fail

**Files:** `papers/overview_workflow.py`, `tests/test_overview_workflow.py`.

**Interface:** Add optional keyword-only `run_directory=None` to `plan_overview` and `Coordinator`. `generate` creates the run directory before planning and passes it down. Existing direct test callers may omit it. The coordinator remains the sole shared-artifact writer.

- [ ] Capture the starting `git status --short` and six-file diff in the local verification directory. Record the commit and dirty-diff digest so later results identify the code actually tested.
- [ ] Add regression tests for failure on the first narrative response, failure on correction, provider failure before a response, and cancellation. Assert that each leaves a terminal run record and all available completed-request diagnostics.
- [ ] Add an append-only `events.jsonl` and atomically updated `run.json` inside each run directory. Use `running`, `completed`, `failed`, and `cancelled` as run states. Store the failed stage and exception type/message separately.
- [ ] Persist request stage, ordinal, actual options, start/end times, reported usage, response text, normalized candidate, and validator issue paths as they become available. Use separate response files referenced by events. Exclude credentials, authorization headers, and base64 image payloads.
- [ ] Record normalization separately from the raw response. When no response exists, record that fact rather than constructing a candidate or usage estimate.
- [ ] Finalize failure/cancellation in `finally` without replacing the original exception if diagnostic writing also fails. Preserve the prior overview through the existing publication boundary.

Extract the existing directory creation and move its call ahead of planning:

```python
def create_run_directory(document):
    directory = (Path(document['directory']) / 'reader' / 'overview-figures'
                 / uuid.uuid4().hex)
    directory.mkdir(parents=True, exist_ok=True)
    _write_json(directory / 'run.json', {'status': 'running'})
    return directory


run_directory = create_run_directory(document)
plan = plan_overview(provider, document, progress,
                     vision=vision, run_directory=run_directory)
```

Keep drawing and composition in `generate`; wrap its full run lifecycle in the failure/cancellation finalization specified above. Directory creation must happen once per run, including a failed run.

**Done when:** A narrative failure can be diagnosed from that run's directory without a returned generation result. Failure records identify unavailable evidence honestly. Test with `python3 -m unittest tests.test_overview_workflow -v`.

## Task 2: Give Overview a suitable narrative contract and real correction

**Files:** `papers/explanation.py`, `papers/overview_workflow.py`, `tests/test_explanation.py`, `tests/test_overview_workflow.py`.

**Interfaces:** Add `validate_overview_narrative(value, document) -> dict`. Keep `validate_plan` and `PLAN_SCHEMA` behaviour for Blog. Add `recover_overview_narrative(candidates, document) -> dict | None` for the narrow recovery below. Continue returning the existing narrative field names to downstream callers.

- [ ] Add a regression that accepts a 1,324-character Overview `visual_focus`, while Blog retains its existing validation. Add array-of-strings normalization, mixed-type array rejection, unknown passage ID, empty claim, and unsupported paper type cases.
- [ ] Use nonempty strings for Overview narrative text without the shared per-field 1,200-character cap. Retain resource protection as a 256 KiB UTF-8 JSON candidate limit, checked before processing; report it as a resource limit. This is an implementation bound, not an editorial length target.
- [ ] Normalize a list of string steps to a newline-separated string without changing their words or order. Keep invalid non-string elements visible to correction rather than silently dropping them.
- [ ] Keep the four evidence-linked claims. Allow zero relationships for a deliberately independent narrative; validate every supplied relationship and passage reference. Shared Blog rules remain unchanged.
- [ ] Include the rejected response as an assistant message before the correction request. Include exact issue paths and instruct the correction to preserve valid claims, citations, and relationships. Save both candidates.
- [ ] After correction fails, examine each saved candidate independently. If all four claims are valid and source-linked, recover it by deriving a plain focus from the existing contribution and dropping invalid optional relationships. Record each discarded relationship and the reduced planning status. Prefer a fully valid candidate over recovery.
- [ ] If no candidate contains the required valid claims, preserve partial work and the saved overview, and return a specific failure. Do not fill missing findings or limitations with invented prose. This is outside harmless-format recovery.
- [ ] Ensure supplemental retrieval stays within the existing narrative correction allocation where practical: send the new evidence with the existing draft to the second call. Account explicitly for any extra request rather than hiding it as retrieval.

Regression example using the current fixtures:

```python
value = copy.deepcopy(NARRATIVE)
value['visual_focus'] = 'x' * 1324
accepted = validate_overview_narrative(value, EVIDENCE)
self.assertEqual(value['visual_focus'], accepted['visual_focus'])
with self.assertRaises(PlanValidationError):
    validate_plan(value, EVIDENCE)
```

Also assert the second recorded request includes the first raw answer as an assistant message, and that recovery never borrows unrelated claims from another candidate.

**Done when:** The known array and length inputs no longer abort a usable Overview. Correction can edit its prior answer. Invalid evidence still fails explicitly. Run `python3 -m unittest tests.test_explanation tests.test_overview_workflow tests.test_agent_overviews -v`.

## Task 3: Separate semantic facts from exact display text

**Files:** `papers/explanation.py`, `papers/overview_workflow.py`, `papers/panel_authoring.py`, `papers/panel-guides/authoring.md`, `tests/test_overview_workflow.py`, `tests/test_panel_authoring.py`.

**Contract:** Add optional `exact_text: list[str]` to Overview shared facts, defaulting to `[]`. These are planner-selected names, values with units, or notation that must appear unchanged. `text` remains the semantic fact a panel can express visually. Add `exact_text` to the author-facing assignment as the resolved union of referenced facts' exact strings, complete `equation` items, and complete `label` items. Preserve the existing `shared_facts` and `illustrative_values` projections.

- [ ] Add a failing regression where an encoder paragraph is expressed by labelled layer boxes without reproducing the paragraph. Its absence as a verbatim sentence must not trigger repair.
- [ ] Add failing regressions for an altered equation operator, a changed value/unit, and a missing declared label. Test the assignment projection and visible SVG text path, not only a helper in isolation.
- [ ] Update the panel-plan prompt, validator, and projection together. Require `exact_text` entries to come from the approved fact text in the same display notation. The clarification pass chooses short exact strings; an entire explanatory paragraph is not an exact label.
- [ ] Replace whole-shared-fact substring checks with the declared exact requirements. Retain numerical token checks for ordinary `value` content as a limited omission check, and name that limitation in diagnostics.
- [ ] Compare canonical equation and label text with only whitespace normalization and XML entity decoding. Preserve grouping, signs, operators, and units. Require frozen equations to use a readable, linear notation that the SVG text extractor can compare. Equivalent reformulation belongs in planning, before the assignment freezes.
- [ ] Remove regex-based semantic LaTeX rewriting from authoring and recovery. Use the existing planner clarification to establish plain display notation, including parentheses around compound numerators and denominators. Retain the original in provenance.
- [ ] If unsupported source notation survives all planning passes, preserve it literally and XML-escaped in the simple recovery, visibly identify it as source notation, and record reduced presentation. Do not silently rewrite mathematics or claim that its scientific meaning was checked.
- [ ] Update the common guide to distinguish content the author may explain visually from exact labels/equations it must reproduce. Keep the existing small SVG examples and author context boundary.

Regression example:

```python
value = assignment(shared_facts={}, exact_text=['reply = 0.73 v1 + 0.27 v2'],
                   content=[{'kind': 'equation',
                             'text': 'reply = 0.73 v1 + 0.27 v2'}])
self.assertTrue(missing_values(value, ['reply = 0.73 v1 - 0.27 v2']))
self.assertEqual([], missing_values(value, ['reply = 0.73 v1 + 0.27 v2']))
```

Keep the public `missing_values(assignment, labels)` signature during this phase; update its docstring to describe exact-display and numeric omission checks. It is not a scientific-equivalence test. Add a fallback fixture containing `\frac{a+b}{c+d}` and assert that rendering preserves that literal text if no canonical replacement was approved.

**Done when:** Semantic prose no longer requires verbatim display, the changed-operator regression fails acceptance, and recovery cannot change fraction grouping. Run `python3 -m unittest tests.test_overview_workflow tests.test_panel_authoring tests.test_panel_guides -v`.

## Task 4: Resolve planner problems before dispatch and report reductions

**Files:** `papers/overview_workflow.py`, `papers/explanation.py`, `tests/test_overview_workflow.py`.

**Interface:** Keep the current `plan_panels` return shape. `remaining_issues` means active issues in the accepted plan, so successful dispatch requires it to be empty. Preserve original issues and the action taken in events. Keep `assignment_source` and add `planning_reduced: bool` plus `planning_reduction_reasons: list[str]` to planning results and provenance.

- [ ] Add regressions for a structurally valid final plan with unresolved reported handoffs, a valid draft followed by malformed clarification, and supplemental evidence requested during the first planner pass.
- [ ] Build each refinement's evidence context from the latest retrieved evidence. The current prebuilt context must not hide newly retrieved passages from the next request.
- [ ] Retain every structurally valid draft. Accept a final plan only when its structural validation and reported issue list are clear. A later issue also applies to an earlier draft unless the earlier content demonstrably removes its cause.
- [ ] Use the final model pass to make conflicting panels independent while retaining their source-supported content. Record which connections changed. Panel authors receive only the frozen result.
- [ ] If the final plan still fails, use a complete, validated narrative to produce the existing independent-claim fallback. Validate fallback against a reduced narrative projection with relationships removed, while keeping the original narrative and removed relationships in provenance. This prevents an orphan-relationship validation failure from defeating the fallback itself.
- [ ] Mark this path `assignment_source='narrative_fallback'`, `planning_reduced=True`, and preserve the triggering reasons. Do not relabel it as a rich teaching plan or conflate it with drawing repair.

Required acceptance assertions for the unresolved-handoff replay:

```python
self.assertEqual([], result['remaining_issues'])
self.assertTrue(result['planning_reduced'])
self.assertEqual('narrative_fallback', result['assignment_source'])
self.assertTrue(result['planning_reduction_reasons'])
self.assertTrue(all(not panel['entry_from']
                    for panel in result['panel_plan']['panels']))
```

The fixture must contain valid source-linked claims and an unresolved issue on every model-authored candidate, so the test cannot pass by selecting an unrelated clean draft.

**Done when:** No conflicted plan silently reaches panel authors, and every narrative fallback is visible independently of panel simplification. Run `python3 -m unittest tests.test_overview_workflow -v`.

## Task 5: Apply reasoning settings at the actual drawing request

**Files:** `papers/overview_workflow.py`, `papers/panel_authoring.py`, `tests/test_overview_workflow.py`, `tests/test_panel_authoring.py`, `tests/test_ai.py`.

**Interface:** Add keyword-only `options=None` to `request_panel`. `_author_once` computes stage options from the worker settings and passes them through. Use `panel_repair` when there are repair issues even if the invalid first response supplied no usable SVG.

- [ ] Add a capturing provider to the worker-path tests. Verify actual `complete` kwargs for initial creation, repair with a prior SVG, and repair after malformed output.
- [ ] Forward options without importing the workflow module from panel authoring:

```python
# Inside _author_once:
stage = 'panel_repair' if previous is not None or issues else 'panel'
options = provider_options(worker.settings, stage)
result = request_panel(worker, assignment, previous=previous,
                       issues=issues, image=image, options=options)

# Inside request_panel:
response = provider.complete(
    panel_messages(assignment, previous=previous, issues=issues, image=image),
    json_object=True, **(options or {}))
```

- [ ] Verify the intended existing policy: DeepSeek drawing has thinking disabled; `overview_reasoning=False` also disables its planning thinking; supported Gemini Flash requests receive the configured low level. Preserve unrelated provider behaviour.
- [ ] Test request JSON encoding with the existing mocked transport tests in `test_ai.py`. A helper returning the correct dictionary is insufficient.
- [ ] Record the effective options per drawing attempt alongside its timings. Distinguish requested reasoning mode from provider-reported reasoning usage; absent usage stays unknown.

**Done when:** Tests observe the options at `Provider.complete` and in the encoded body, and the trace records those same options. Run `python3 -m unittest tests.test_overview_workflow tests.test_panel_authoring tests.test_ai -v`.

## Task 6: Make local recovery safe and preserve completed work

**Files:** `papers/panel_authoring.py`, `papers/overview_workflow.py`, `tests/test_panel_authoring.py`, `tests/test_overview_workflow.py`.

**Interface:** Keep one `simple_panel` recovery using escaped text and native measured wrapping. Remove the overlapping reduced-recovery branch once its required behaviour is incorporated. Creation, repair, and recovery all pass through `_panel_issues` before acceptance. Infrastructure failure preserves artifacts and the prior published overview.

- [ ] Add native-render fixtures containing `<`, `>`, `&`, quotes, non-ASCII text, long labels, source notation, and illustrative values. Verify visible text as well as XML parsing.
- [ ] Keep XML escaping at SVG serialization. Perform measured wrapping without dropping words or altering mathematical text. Preserve the illustrative label on every recovery path.
- [ ] Check the fallback with the same geometry and exact-display checks as generated panels. Record its outcome as simplified and retain the original drawing defects separately from the accepted fallback's empty active issue list.
- [ ] Inject a fallback renderer exception after other panels complete. Verify sibling source files, diagnostics, and usage remain accessible, and the previously published overview remains unchanged. Cancellation must also prevent publication.
- [ ] Inspect final composed-image `checks` before returning a publishable result. Reject active geometry issues even if rendering returned files successfully. Preserve the assembled source and panel records on failure.
- [ ] Test composition failure, missing renderer, and fallback exact-text mismatch explicitly. Keep these as diagnosed infrastructure/content failures rather than repeatedly invoking the same failed renderer or reporting successful recovery.

Required recovery assertions:

```python
self.assertEqual('simplified', panel['outcome'])
self.assertEqual([], panel['checks']['issue_details'])
self.assertIn('positions $<i$', ' '.join(panel['labels']))
self.assertIn('illustrative', ' '.join(panel['labels']).lower())
```

Use an assignment containing both the source-notation text and an illustrative value. Test unrecoverable failures separately; an exception is not evidence of a delivered image.

**Done when:** The raw-`<` reproduction delivers a checked fallback with unchanged text, composition issues cannot publish, and a renderer outage preserves completed work. Run the two focused suites with the native helper enabled.

## Task 7: Evaluate delivered images without hiding fallback or quality gaps

**Files:** `tests/test_overview_workflow.py`, `tests/fixtures/overview-p2/`, `docs/verification/2026-09-13-overview-rebuild-p2.md`; update the local pilot's report extraction when evaluating it.

- [ ] Replay the known length, array, verbatim-paragraph, changed-equation, raw-`<`, unresolved-handoff, and request-option failures offline. Use synthetic fixtures where historical raw responses were never saved; label their origin. Preserve the unknown Gemini cause as unknown.
- [ ] Make the report read the persisted run record on both success and failure. Report delivery status, failed stage, assignment source, planning reductions, created/repaired/simplified panels, active local issues, actual request options, usage, and elapsed time.
- [ ] Add a report regression where four panels render without drawing simplification but `assignment_source='narrative_fallback'`. The report must show reduced planning.
- [ ] Record independent inspection separately with `not_reviewed`, `pass`, or `fail`, plus artifact path/digest and specific findings. The application must not infer an inspection pass from empty geometry issues.
- [ ] Inspect the complete architecture, method, and survey images already on disk against these questions: Is the central contribution clear? Does the mechanism panel demonstrate a relationship or change the novice can follow? Do adjacent panels connect without unexplained jumps? Do numbers, equations, directions, and qualifications match the approved briefs? Is the image readable at its intended viewing scale?
- [ ] For each failure, identify whether its earliest source is the narrative, panel brief, drawing, fallback, or composition. Change only the implicated prompt section; preserve the short relevant reference examples. Do not add a new runtime scientific-review loop in this phase.
- [ ] After offline checks pass, record any live evidence still needed. New calls require explicit authorization. A later comparison must hold paper, source evidence, model, prompt revision, code/diff digest, and output settings fixed, and change only the setting being tested. Record cache differences and run-level fallback.

Report semantics example:

```json
{
  "delivery": "completed",
  "assignment_source": "narrative_fallback",
  "planning_reduced": true,
  "panel_outcomes": {"created": ["p1", "p2", "p4"], "repaired": ["p3"], "simplified": []},
  "local_checks": "pass",
  "independent_inspection": "not_reviewed"
}
```

These are report fields, not a replacement for the application's saved-generation format. Successful repair alone does not imply reduced planning or poor quality. A completed, reduced overview may be useful; it must be reported accurately.

**Done when:** The report distinguishes a checked image, a reduced explanation, an independently inspected explanation, and a failed run. No quality or reasoning-performance conclusion rests only on mocked tests or run labels.

## Final verification and handoff

Execute tasks in order. Finish each focused test cycle before starting the next. Preserve pre-existing edits when preparing reviewable changes; do not commit or revert unrelated work.

- [ ] Run the focused contract, coordinator, authoring, provider, and Blog regression suites listed above.
- [ ] Build the native helper from the current source and use that exact binary for rendering tests. Resolve the installed SDK rather than copying a historical absolute SDK path:

```sh
mkdir -p .scratch/overview-rebuild-p2
xcrun swiftc -sdk "$(xcrun --show-sdk-path)" \
  -module-cache-path /private/tmp/localxiv-p2-swift-module-cache \
  -O papers/HTMLSnapshot.swift -o .scratch/overview-rebuild-p2/html-snapshot
LOCALXIV_HTML_RENDERER="$PWD/.scratch/overview-rebuild-p2/html-snapshot" \
  python3 -m unittest tests.test_panel_authoring tests.test_panel_guides \
  tests.test_overview_workflow -v
```

- [ ] Run `python3 -m unittest discover -s tests` in the repository's working test environment, with the same helper configured for native cases. Record failures and skips explicitly; an unavailable renderer does not count as a native pass.
- [ ] Verify out-of-order parallel completion, one normal repair per panel, cancellation, prior-overview preservation, Blog compatibility, and final composition acceptance. Existing meaningful tests can supply this evidence.
- [ ] Update the design's narrative/display contract and recovery sections to match the final implementation, and link the phase 2 verification report. Preserve historical pilot results with their original status.
- [ ] Deliver a change summary with actual test results, inspected image paths, resolved reproductions, and remaining live-validation needs. Stop implementation here unless further work is authorized.

Phase 2 is technically complete when the known offline failure cases have regression coverage, all required native checks pass, and reporting exposes reductions and failures accurately. Improved novice understanding remains an empirical result to establish through inspection of new outputs; fixing contracts alone does not prove it.
