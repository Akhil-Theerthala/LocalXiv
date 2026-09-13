# Overview workflow rebuild implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task by task. Use Ponytail for code and Writing for Agents for prompts/documentation. Parallel panel generation is a product requirement; it does not request parallel implementation agents. Track execution with the checkboxes below.

**Goal:** Replace the accumulated visual Overview workflow with source-grounded planning, focused parallel SVG panel construction, and one freely sized, readable image.

**Architecture:** A new Overview coordinator owns evidence, planning, dispatch, and completion. A small panel-authoring module owns reference-guided requests and panel checks; existing arrangement and rendering modules assemble the result. Preserve provider, library, conversion, Blog, and export boundaries, then delete the replaced Overview branches.

**Tech Stack:** Python standard library, existing provider client, Swift/AppKit/WebKit, and the existing JavaScript viewer. No new runtime dependency.

**Spec:** [Overview workflow rebuild design](../specs/2026-09-13-overview-workflow-rebuild-design.md). Read it before implementation. The spec owns product requirements; this plan owns execution steps and verification.

## Global constraints

- The overview is one image with 1–7 numbered panels.
- Image dimensions follow content; there is no fixed page size, aspect ratio, or whole-image word budget.
- Panels read left to right, then top to bottom.
- Planning owns scientific meaning, shared examples, notation, and panel handoffs.
- Each panel author receives a complete drawing assignment and builds only that panel.
- Panel authors receive relevant SVG examples and concise construction references, without the paper, planning history, or other panel briefs.
- The first panel-plan refinement clarifies; the second simplifies and removes troublesome dependencies before drawing proceeds.
- Panel generation runs concurrently; completion order never changes reading order.
- The intended structure is 1–2 narrative calls, 1–3 panel-plan calls, and one creation call plus one repair call where needed per panel.
- Those call counts describe the normal workflow, not a universal request ceiling.
- Acceptance centres on the rendered images and their fidelity to the approved drawing assignments.
- Regeneration keeps the saved overview available until a complete replacement is ready.
- Reading, conversion, Blog generation, and existing saved artifacts remain usable.
- No new runtime dependency or generic agent framework is required.

## Status and execution boundary

This is a plan, not an implementation report. The user requested a fresh, focused rebuild of the existing workflow after discussing the design. Source changes, live model calls, installation, publication, and cleanup have not been performed by this planning task.

The deterministic simplified-panel recovery and exact typography/worker defaults are recommendations stated in the spec for review. They are not claimed as separately approved user choices. Review this plan before implementation; do not revive older efficiency targets or paid-call permissions from historical plans.

## Current evidence

Checked on branch `akhil/model-authored-svg-overviews` on 2026-09-13:

- `papers/agent_overviews.py:823` begins a shared Overview/Blog coordinator extending beyond 1700 lines. The visual path carries old whole-document prompts and repair bookkeeping.
- `papers/arrangement.py:278` still reads deleted `routes`.
- `papers/html_figures.py:281` calls missing `_card_markup`.
- Three arrangement tests still call the removed three-argument interface.
- The panel prompt appends `SVG_FIT_GUIDANCE`, including old page ratios and whole-paper explanation instructions.
- The renderer uses a 960px window, a 640px reading scale, and a 6000px height bound; Python adds a 960px compact-page gate.
- SVG checks currently reject the supplied examples' CSS classes/variables and inline styles. Normalise the references before using them, rather than asking the model to copy invalid examples.
- The existing figure dialog already has Fit/Actual size and scrolling. Extend it rather than introducing another viewer.
- `Provider.complete` invokes `on_usage` inside the calling thread. The new coordinator must own persistence of parallel request results.
- The previous focused run passed eight draft/metric tests and reproduced three arrangement errors. Browser UI checks and 63 extension tests passed. A broad native-backed Python run was interrupted after renderer timeouts; its total failure count is unverified.

These facts identify migration work, not a reason to fix every retired path before replacement.

## File responsibilities

| File | Responsibility after rebuild |
| --- | --- |
| New `papers/overview_workflow.py` | Evidence preparation, narrative/panel planning, parallel scheduling, recovery, result/provenance |
| New `papers/panel_authoring.py` | Assignment prompt, reference selection, one-shot SVG request, render/check, simple local recovery |
| `papers/explanation.py` | Shared selection/narrative contracts plus replacement Overview panel-plan validation |
| `papers/arrangement.py` | Small row arrangement of measured panels in order |
| `papers/html_figures.py` | Safe SVG boundary, composition, native renderer invocation and artifact paths |
| `papers/HTMLSnapshot.swift` | Actual geometry/text measurement and variable-size image/PDF rendering |
| New `papers/panel-guides/` | Common authoring guide, SVG notes, five small reference SVGs |
| `papers/ai.py` | Route `visual=True` to new workflow; keep public API |
| `papers/agent_overviews.py` | Existing Blog path and legacy artifact handling; delete replaced visual generation |
| `app/static/app.js`, `app.css`, `index.html` | Existing dialog extended with panel focus, zoom/pan, accessible controls |
| `app/server.py`, `papers/exports.py`, `papers/document.py` | Preserve publication/export contracts; change only assumptions exposed by free-sized artifacts |

No generic stage registry, planner class hierarchy, provider router, layout DSL, or second persistence store.

## Task 1: Preserve the starting state and pin integration behaviour

**Files:** inspect `papers/ai.py`, `app/server.py`, `papers/library.py`, `papers/exports.py`, `papers/document.py`, `tests/test_reading.py`, `tests/test_app.py`, `tests/test_exports.py`, `tests/test_agent_overviews.py`.

**Interface to retain:** `generate_overview(provider, document, progress, *, visual=False, image_overview=None)` returns the generation dictionary consumed by `Application.execute()` and `Library.save_generation()`.

- [ ] Record `git status --short --branch`, `git diff --stat`, and the tracked source diff in an implementation checkpoint under `.scratch/overview-rebuild/`. Inventory untracked paths; copy only task-relevant source/test files needed for rollback. Exclude `.env`, credentials, and unrelated scratch directories. Do not use `git reset`, blanket restore, or `git clean`.
- [ ] Read the existing saved-generation fixtures and caller assertions. Identify tests requiring an approved new result, preserving a prior result after failure/cancellation, Blog generation without an Overview, and export of legacy SVG/HTML/Excalidraw assets.
- [ ] Add a focused contract test in `tests/test_app.py` that seeds an existing bento generation, makes replacement generation raise `ProviderError`, and verifies the stored generation is unchanged. Use the existing application fixture and mocked provider, with no external calls.
- [ ] Save the exact current generation result keys and figure asset keys as assertions in `tests/test_exports.py`; later tasks must satisfy them with the new result.
- [ ] Run the existing app/export/reading checks and record source failures separately from unavailable native rendering. Retain failing legacy evidence; do not spend this task repairing the soon-to-be-deleted router/composer.

```sh
.scratch/overview-agent-env/bin/python -m unittest tests.test_app tests.test_exports tests.test_reading tests.test_reading_bibliography
node tests/test_app_ui.js
node tests/test_extension.js
```

**Done when:** the baseline is recoverable, publication/export expectations are explicit, and no installed application or private library has changed.

## Task 2: Establish a working SVG construction and rendering contract

**Files:** create `papers/panel-guides/authoring.md`, `svg-reference.md`, `flow.svg`, `mapping.svg`, `comparison.svg`, `calculation.svg`, `chart.svg`; modify `papers/html_figures.py`, `papers/HTMLSnapshot.swift`; test in `tests/test_panel_authoring.py` and `tests/test_figure_readability.py`.

**Interfaces:** extend `normalize_svg(source, *, external_markers=frozenset(), profile='legacy')`; extend `render(directory, figure, paper_title, *, compact=False, mode='legacy')`. Modes are `legacy`, `panel`, and `overview`. Existing defaults retain current Blog behaviour. New-mode returns retain asset keys and add measured canvas, text runs, and element bounds under `checks`.

- [ ] Turn the [user reference inputs](../specs/2026-09-13-panel-svg-reference-inputs.md) into the flow/mapping/comparison examples. Resolve CSS tokens to literal colours and fonts. Keep examples complete, small, and accepted by the production profile. Write small original calculation and chart examples using the same visual language.
- [ ] Write the common guide in the exact prompt order specified by the design. Write concise original construction notes with a W3Schools source link. Include text wrapping with explicit lines, known connector endpoints, generous text boxes, and canvas growth. Attach at most two relevant complete examples per panel.
- [ ] Introduce a new SVG profile for panels/overview that permits content-sized finite viewBoxes and the guide's actual typography. Preserve active-content/resource rejection. Keep bounded source bytes/elements as resource protections; allow the composed document's aggregate budget to cover up to seven individually bounded panels.
- [ ] Add native tests for all five examples, wide/tall canvases, paths extending beyond their panel, circles with large radii, transformed groups, long labels, strokes, arrowheads, and tspans. Include this escaped path regression:

```python
source = '<svg viewBox="0 0 300 200" font-size="18"><path d="M 0 0 L 900 900" stroke="black"/><text x="20" y="40">Example</text></svg>'
result = render(directory, {'id': 'p1', 'title': 'Example', 'source_svg': source}, '', mode='panel')
self.assertTrue(any(issue['code'] == 'out_of_bounds'
                    for issue in result['checks']['issue_details']))
```

- [ ] In Swift, select measurement mode through application-generated document metadata. Resolve intrinsic width/height before snapshot, preserve scale, and measure against the relevant panel canvas. Replace whole-page reading-scale checks only in new modes. Use actual transformed geometry and font metrics; remove the attribute-only panel guard from the new call path.
- [ ] Keep new panel SVG roots self-contained and preserve inherited root attributes when composing. A nested transform or root font must render identically in isolation and after composition.
- [ ] Test a composed render larger than 960px in both axes. For raster allocations above a measured safe threshold, render tiles and assemble the PNG at the same scale using AppKit. Keep one PDF with the complete image extent. Test tile boundaries on text and connectors; do not quietly downsample.
- [ ] Compile to an isolated binary and run native checks. If restricted execution times out, repeat the same bounded test through normal macOS execution before diagnosing a renderer defect.

```sh
mkdir -p .scratch/overview-rebuild
xcrun swiftc -sdk /Library/Developer/CommandLineTools/SDKs/MacOSX15.4.sdk -module-cache-path /private/tmp/localxiv-swift-module-cache -O papers/HTMLSnapshot.swift -o .scratch/overview-rebuild/html-snapshot
LOCALXIV_HTML_RENDERER="$PWD/.scratch/overview-rebuild/html-snapshot" .scratch/overview-agent-env/bin/python -m unittest tests.test_svg_figures tests.test_figure_readability
```

**Done when:** the examples render correctly in the real helper, geometry defects are localised, legacy tests still pass, and free-sized images preserve readable text.

## Task 3: Rebuild narrative and panel planning around complete assignments

**Files:** create `papers/overview_workflow.py`; replace Overview-specific definitions in `papers/explanation.py`; create `tests/test_overview_workflow.py`; update `tests/test_panel_authoring.py`.

**Interfaces:** `validate_panel_plan(value, narrative, evidence) -> dict`; `panel_assignments(panel_plan) -> list[dict]`; `plan_overview(provider, document, progress) -> dict` returning `narrative`, `panel_plan`, `evidence`, and `events`. Contract fields are defined in the spec.

- [ ] Implement the new schema and validation without changing Blog's candidate schema. Enforce 1–7 panels, safe IDs, known claim/evidence ownership, canonical shared facts, and earlier-only handoffs. Replace passage-union coverage and nested bridge/group structures for new Overviews.
- [ ] Add tests for zero/eight panels, duplicate/path-like IDs, unknown passages, later-panel dependencies, orphaned central claims, and shared example values. Include a test that copying all citations to an unrelated panel cannot replace explicit ownership of a required claim.
- [ ] Implement assignment projection. Test that panel B inherits panel A's exact endpoint and values, while unrelated evidence and briefs never appear:

```python
assignments = panel_assignments(valid_panel_plan)
self.assertEqual([valid_panel_plan['panels'][0]['exit_state']],
                 assignments[1]['entry_context'])
self.assertEqual(valid_panel_plan['shared_facts']['candidate_probabilities']['text'],
                 assignments[1]['shared_facts']['candidate_probabilities'])
self.assertNotIn('passages', assignments[1]['content'][0])
```

- [ ] Use existing `build_orientation`, `orientation_page`, `retrieve_evidence`, and `Provider.complete`. Extract only the selection logic actually needed from the legacy coordinator, including full map traversal and validated supplemental retrieval. Keep selection calls visible in accounting. Do not reintroduce paid full-paper reading caches or silently truncate evidence.
- [ ] Use plain structured requests for narrative and panel planning. The panel planner's second call receives the draft and evidence, checks handoffs/completeness/support, and returns a clarified replacement plus remaining issues. Call three is conditional and explicitly simplifies unresolved dependencies. These are review-and-revision passes within one planner, not additional reviewer agents.
- [ ] Test the actual state sequence with a scripted provider. First response contains the three-to-five-candidate conflict; second still reports unresolved dependence; third produces independent briefs. Assert `panel_plan`, `panel_plan_clarify`, `panel_plan_simplify` request labels and that panel creation starts only afterward.
- [ ] Keep a usable narrative when a response is malformed. Use the next planned refinement for protocol correction; record the reason. After the final simplification, build independent briefs from valid narrative claims if necessary. Do not submit unvalidated JSON to authors or invent missing facts.
- [ ] Test paper without retained text, unavailable provider, and cancellation separately. Return the existing failure contract for unrecoverable infrastructure problems while preserving prior artifacts. Do not record those as successful simplified plans.

```sh
.scratch/overview-agent-env/bin/python -m unittest tests.test_overview_workflow tests.test_explanation tests.test_reading_bibliography
```

**Done when:** a planner produces source-linked, self-contained drawing assignments; clarification and simplification differ observably; no drawing stage must resolve missing story context.

## Task 4: Build focused panel creation, local checking, and repair

**Files:** create `papers/panel_authoring.py`; update `tests/test_panel_authoring.py` and guide examples as needed.

**Interfaces:** `panel_messages(assignment, *, previous=None, issues=(), image=None) -> list[dict]`; `request_panel(provider, assignment, *, previous=None, issues=(), image=None) -> dict` returning `source`, `error`, `usage`, and `diagnostics`. Source is null on failure; error distinguishes invalid output from transport/authentication failure. `check_panel(source, directory, panel_id) -> dict` returns normalised `source`, `assets`, `checks`; `simple_panel(assignment, directory) -> dict` returns the same checked artifact shape.

- [ ] Build the prompt from the assignment, relevant example(s), construction notes, and JSON submission format. Call `Provider.complete(..., json_object=True)` directly. Validate returned panel ID and safe SVG. One request produces one response; remove tool-submission/prose-only conversational loops from this stage.
- [ ] Assert that the panel prompt contains the inherited example values and selected construction reference, but not raw evidence, an entire narrative, other panel briefs, old ratio instructions, or planning tools:

```python
messages = panel_messages(assignment)
serialized = json.dumps(messages)
self.assertIn('8,532,412', serialized)
self.assertNotIn('retrieved_evidence', serialized)
self.assertNotIn('request_narrative_revision', serialized)
self.assertNotIn('0.75 and 1.33', serialized)
```

- [ ] Check successful responses through `check_panel` in the native renderer. Keep SVG syntax/security validation separate from image geometry. Check required exact display values against extracted text, without claiming that string presence proves a correct visual explanation.
- [ ] Repair receives the same assignment/reference, the previous source, and only this panel's concrete issues. Include the rendered image when image input is configured and supported; otherwise provide measured defects. Treat malformed initial JSON/SVG as a repairable first attempt. Do not send successful sibling drawings or reopen planning.
- [ ] Implement the proposed simple-panel recovery using the approved content. Use application-owned wrapping measured in the same WebKit font, then emit static SVG text/equation lines. The application may use HTML internally to measure wrapping; the model still outputs only SVG. Render and check the recovery through the same path. Preserve facts and identify illustrative values.
- [ ] Test first-attempt success, one repaired success, and simplified recovery after the second invalid image. Verify all required content survives and provenance distinguishes these outcomes. Never pass an unrenderable SVG through as success.

```sh
LOCALXIV_HTML_RENDERER="$PWD/.scratch/overview-rebuild/html-snapshot" .scratch/overview-agent-env/bin/python -m unittest tests.test_panel_authoring
```

**Done when:** a complete assignment reliably reaches a checked image through creation, targeted repair, or the proposed simple recovery, with no story-management responsibility in the author.

## Task 5: Replace page fitting with ordered image composition

**Files:** rewrite `papers/arrangement.py`; modify `papers/html_figures.py`; update `tests/test_panel_authoring.py` and `tests/test_figure_readability.py`.

**Interfaces:** `arrange(panels) -> dict`, where panels is an ordered list of `{id, width, height, body_size}` measured records; output contains `canvas`, `placements`, and `scales`. `compose_figure(panels, arrangement) -> str` retains the existing source-map argument convention.

- [ ] Replace the old combinatorial group/bridge packing and readability-compression loops with row placement. Evaluate one to three columns, keep array order, use actual row heights and gaps, and grow the canvas. Prefer the least unused row area, then fewer rows. Zero panels is invalid; one panel is valid.
- [ ] Remove `routes`, bridge fields, shape-band penalties, fixed `COLUMN_PX`/`AVAILABLE_PX`/`READING_SCALE`, and width-based compression candidates from the new arranger. No panel is redrawn merely to fit the complete image into a square.
- [ ] Draw serial numbers in a reserved band, without repeating the authored title or drawing nested group frames. Namespace SVG IDs and preserve inherited font/fill/transform attributes. Store panel rectangles in the same coordinate system as the composed source.
- [ ] Test 1, 4, and 7 panels with different dimensions. Verify sequential row order, nonintersection, identical source content, and label-size preservation before/after composition:

```python
layout = arrange(measured_panels)
self.assertEqual([p['id'] for p in measured_panels],
                 [p['id'] for p in layout['placements']])
for placement in layout['placements']:
    self.assertGreaterEqual(placement['x'], 0)
    self.assertLessEqual(placement['x'] + placement['width'], layout['canvas']['width'])
```

- [ ] Add a native regression that compares the same panel rendered alone and in a large composition. Check measured body sizes and paths rather than assuming equal declared font sizes imply equal rendering.
- [ ] Verify complete PNG/PDF exports, source SVG, and compatibility SVG agree on dimensions and content. Whole-image fit inside the viewer must not feed into authoring or export dimensions.

**Done when:** seven panels compose without shrinking text, losing content, changing order, or drawing between panels.

## Task 6: Wire parallel requests and switch the production Overview path

**Files:** `papers/overview_workflow.py`, `papers/ai.py`, `app/server.py`; tests `tests/test_overview_workflow.py`, `tests/test_app.py`, `tests/test_ai.py`.

**Interfaces:** `build_panels(provider, assignments, directory, progress) -> dict` returns ordered `panels` and `events`; `generate(provider, document, progress) -> dict` returns the retained generation result contract. The public `generate_overview` signature stays unchanged.

- [ ] Use `ThreadPoolExecutor(max_workers=min(3, len(assignments)))` for model requests. Give each worker a provider instance with copied settings and a callback that appends usage only to that request's local list. Return that list even if response parsing later fails. Preserve endpoint options used by the existing provider. Perform no native rendering, common-file writes, persistence callbacks, or UI callbacks inside request workers.
- [ ] On each completed future, have the coordinator record its request/usage, invoke the original usage callback exactly once, render/check the result, and schedule that panel's repair where necessary. Retain futures by panel ID and attempt. Keep completed results indexed by ID, then emit them in assignment order.
- [ ] Test overlap using a `threading.Barrier(2)` inside two fake requests. The test must fail under sequential execution. Return panel 2 before panel 1 and assert the final array still begins with panel 1. Assert persistence callbacks run on the coordinator thread and each response is counted once, including a billed response that the provider subsequently rejects as malformed.
- [ ] Check cancellation while futures are pending. Stop submission, cancel unstarted work, preserve usage for requests already completed, and prevent late responses from publishing a cancelled generation. Test an exception from one panel without discarding successful siblings. Retry only an explicitly transient request once with backoff; record transport retries separately and do not retry authentication failures.
- [ ] Persist planner/assignment/source/render/check/arrangement artifacts in the existing run directory. Coordinator owns the JSONL trace. Use unique panel paths and atomic common-JSON replacement; no cross-worker shared writes.
- [ ] Preserve return fields and evidence provenance. New review records state planner checks and native drawing checks explicitly. Never fabricate a successful full-image scientific review. Record normal, repaired, and simplified panel IDs separately.
- [ ] Switch the public route only after an end-to-end offline generation passes:

```python
def generate_overview(provider, document, progress, *, visual=False, image_overview=None):
    if visual:
        from papers.overview_workflow import generate
        return generate(provider, document, progress)
    from papers.agent_overviews import generate
    return generate(provider, document, progress, image_overview=image_overview)
```

- [ ] Test generated output through `Application.execute`, cancellation checkpoint, and `Library.save_generation`. Confirm a prior overview remains until every required new panel and the complete artifact are ready.

**Done when:** independent panel requests overlap, retries stay local, accounting is correct, and the application uses the new Overview path with unchanged Blog routing.

## Task 7: Make free-sized overviews usable in the reader and exports

**Files:** `app/static/app.js`, `app/static/app.css`, `app/static/index.html`, `papers/exports.py`, `papers/document.py`, `papers/agent_overviews.py`; tests `tests/test_app_ui.js`, `tests/test_exports.py`, `tests/test_agent_overviews.py`.

**Interface:** figure metadata adds `dimensions: {width, height}` and ordered `panels: [{id, title, x, y, width, height}]`; `openFigure(url, alt, caption, panels=[])` retains three-argument callers.

- [ ] Extend the existing dialog with a scrollable stage and scale state. Start at fit-to-window, click a panel to focus its rectangle, pan/zoom with pointer and trackpad, and expose Fit image plus keyboard zoom controls. Keep Escape/close and focus return. Use existing controls/styles rather than a new viewer dependency.
- [ ] Convert click coordinates through the displayed image rectangle and scale before locating the panel. Test nonzero dialog offsets, fit zoom, actual-size zoom, and resized windows. Do not attach panel hitboxes to a raster resolution different from metadata coordinates.
- [ ] Provide keyboard-accessible numbered panel targets and a text transcript from accepted assignments. Old figures without panel metadata keep whole-image zoom.
- [ ] Run UI checks and manually inspect a seven-panel mixed-aspect artifact in the actual macOS webview. Verify trackpad gestures and keyboard focus there; a DOM-only test is insufficient.
- [ ] Verify PNG, PDF, editable SVG, and EPUB via the existing export entry point. Remove fixed dimensions only where new Overview packaging assumes them. Preserve legacy export inputs and independent original-paper export.
- [ ] Adapt Blog reference admission for the new provenance version without manufacturing a scientific-review flag. Require matching document/plan/source digests, safe existing assets, and clean local checks. Use the new SVG profile for these artifacts, rather than reapplying the legacy word/viewBox/page limits through `validate_candidate`. Present new artifacts as drawing references with the original evidence; Blog retains its own grounded review. Retain the older reviewed-artifact branch, and default to independent Blog when references are missing or incompatible.

```sh
node tests/test_app_ui.js
node tests/test_extension.js
.scratch/overview-agent-env/bin/python -m unittest tests.test_exports tests.test_app tests.test_agent_overviews
```

**Done when:** a reader can inspect the whole overview and individual panels intuitively, all existing export routes work, and Blog does not confuse geometry acceptance with scientific verification.

## Task 8: Delete superseded machinery and validate delivered overviews

**Files:** `papers/agent_overviews.py`, `papers/explanation.py`, old guide references, migrated tests, `.github/workflows/macos-build.yml`, `app/macos/build-release.py`, `CONTEXT.md`, `docs/development.md`, `docs/adr/0003-panel-level-svg-authoring.md`; create `docs/verification/2026-09-13-overview-workflow-rebuild.md`.

- [ ] Trace callers before deleting each old visual symbol. Remove Overview-only tool-agent authoring, whole-image semantic repair/replanning, digest/no-progress repair machinery that has no Blog caller, bridge/group schemas, whole-image word/page/ratio enforcement, and obsolete reference loading. Preserve every helper still required by Blog or legacy artifacts.
- [ ] Migrate or retire tests according to behaviour, not merely to obtain green results. Document tests replaced by free-size rendering, planner simplification, and parallel/local repair. Keep source safety, actual bounds, preservation, cancellation, bibliography filtering, and compatibility coverage.
- [ ] Verify new modules and `panel-guides` are included in the application copy and source archive rules. Add the new workflow/panel suites to CI, including native checks after the renderer exists. Do not change installed applications or create a public release.
- [ ] Give `CONTEXT.md` one concise pointer to the current design and update obsolete domain definitions. Mark ADR 0003 and older workflow plans as superseded for new Overview execution. Replace conflicting development instructions instead of appending another amendment. Preserve historical verification reports and reference them as historical.
- [ ] Run the required offline suite once in the correct environment after cutover and deletion. Investigate failures before broadening tests:

```sh
LOCALXIV_HTML_RENDERER="$PWD/.scratch/overview-rebuild/html-snapshot" .scratch/overview-agent-env/bin/python -m unittest discover -s tests
node tests/test_app_ui.js
node tests/test_extension.js
git diff --check
```

- [ ] Run a later explicitly authorized live pilot on the retained architecture, methodology, and survey/comparison cases. Start with one model and three papers; add a provider comparison only if requested. Use an isolated diagnostic library. Do not carry forward historical request ceilings or execute paid calls under this planning request.
- [ ] Inspect every final image, including simplified panels, against its accepted brief and source-linked narrative. Record whether the central contribution is understandable to the intended novice; exact example continuity; visible equations/values; panel order; geometry; export fidelity; and recovery outcomes. Include full images and per-panel crops in the report.
- [ ] Report the actual call breakdown, including selection, planner passes, initial drawings, repairs, transport retries, and any explicitly authorized external image inspection. Distinguish normal success, simplified success, and infrastructure failure. A 14-call run is not success if the delivered overview is wrong or unreadable.
- [ ] Commit only reviewed implementation changes in coherent task-sized commits after local validation. Check staged paths before every commit; never stage `.env` or unrelated work. Pushing, installation, and release are separate actions requiring user instruction.

**Done when:** the old Overview path is removed, the new path is the only production route, offline/native/UI checks pass, and authorized live artifacts demonstrate the intended result. If live evaluation has not been authorized or native execution is unavailable, report those portions as unverified rather than marking the rebuild fully validated.

## Plan review checklist

- [ ] Confirm the focused rebuild boundary and the recommended simple-panel recovery.
- [ ] Confirm reference SVGs, planner refinement roles, and panel-only prompts are covered by Tasks 2–4.
- [ ] Confirm free-sized composition, parallel requests, and the reader/export path are covered by Tasks 5–7.
- [ ] Confirm Task 8 deletes displaced code and conflicting instructions rather than leaving a second workflow.

Implementation should proceed inline with `superpowers:executing-plans` after plan approval. Product-level parallel panel requests do not depend on agent delegation during implementation.
