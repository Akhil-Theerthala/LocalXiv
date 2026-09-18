# Overview workflow rebuild — verification report

Status: historical. The model-drawn SVG path this report verifies was deleted by the [figure library consolidation](../superpowers/specs/2026-09-18-figure-library-consolidation-design.md); the code is at commit 9abae74.

Date: 2026-09-13
Design: [Overview workflow rebuild](../superpowers/specs/2026-09-13-overview-workflow-rebuild-design.md)
Plan: Overview workflow rebuild implementation plan (plan removed; in git history)

## What was delivered

| Area | Where | Notes |
| --- | --- | --- |
| Panel guides | `papers/panel-guides/` | `authoring.md`, `svg-reference.md`, and five complete examples: flow, mapping, comparison, calculation, chart |
| Renderer contract | `papers/html_figures.py`, `papers/HTMLSnapshot.swift` | `normalize_svg(..., profile=)` with `legacy`/`panel`/`overview`; `render(..., mode='panel'|'overview')`; intrinsic sizing, canvas measurement, element bounds, tiled raster above the safe threshold; a `measure` mode for application-owned wrapping |
| Overview coordinator | `papers/overview_workflow.py` | Evidence selection, narrative planning, panel planning with clarify/simplify refinement, independent-brief fallback, parallel panel authoring, local repair, simple recovery, composition, provenance |
| Panel author | `papers/panel_authoring.py` | Assignment prompt, at most two reference examples, one structured request, local check, measured wrapping for the simplified panel |
| Contracts | `papers/explanation.py` | Flat panel plan (`validate_panel_plan`, `panel_assignments`); the draft/group/bridge contracts and their validators are deleted |
| Arrangement | `papers/arrangement.py` | Ordered rows, 1–3 columns, body-text normalisation, free canvas; legacy packing helpers deleted |
| Reader | `app/static/app.js`, `app.css`, `index.html` | Fit-to-window start, zoom controls, pointer pan, panel focus, numbered panel buttons, transcript |
| Routing | `papers/ai.py` | `visual=True` runs the new workflow; Blog keeps the existing `agent_overviews.py` path |
| Blog references | `papers/agent_overviews.py` | New provenance branch admits panel-workflow artifacts as drawing references by digest and clean local checks, without a fabricated scientific review |

Deleted with the replaced path: the whole-document Overview author, panel draft/bridge/group schemas,
whole-image word and page-ratio enforcement, `_fit_diagnostic*`, `_repair_evidence`, the visual prompts,
and `papers/prototypes/parallel_scene.py`.

## Offline verification

Run on 2026-09-13 with the renderer built from the current `papers/HTMLSnapshot.swift`:

```sh
xcrun swiftc -sdk /Library/Developer/CommandLineTools/SDKs/MacOSX15.4.sdk \
  -module-cache-path /private/tmp/localxiv-swift-module-cache -O papers/HTMLSnapshot.swift \
  -o .scratch/overview-rebuild/html-snapshot
LOCALXIV_HTML_RENDERER="$PWD/papers/html-snapshot" .scratch/overview-agent-env/bin/python -m unittest discover -s tests
node tests/test_app_ui.js
node tests/test_extension.js
git diff --check
```

| Check | Result |
| --- | --- |
| `unittest discover -s tests` | 411 tests, 0 failures, 1 skip |
| `node tests/test_app_ui.js` | passed (including the new figure-dialog cases) |
| `node tests/test_extension.js` | passed, 63 tests |
| `git diff --check` | clean |

New and rewritten suites:

| Suite | Tests | Covers |
| --- | --- | --- |
| `tests/test_panel_guides.py` | 14 | Guide examples validate and render cleanly; panel/overview profiles; intrinsic canvases; escaped paths; strokes, arrowheads, tspans; tiled raster reassembly across a text seam; over-960px composition |
| `tests/test_panel_authoring.py` | 24 | Prompt contract and order, one-shot request outcomes, local checks, missing display values, simple recovery, ordered arrangement, composition, id namespacing, root-attribute preservation |
| `tests/test_overview_workflow.py` | 28 | Panel-plan validation and ownership, assignment projection, planner state sequence, evidence supplement, protocol correction, independent-brief fallback, cancellation, transient retry, parallel overlap with a barrier, coordinator-thread usage accounting, repair, simplified recovery |
| `tests/test_figure_readability.py` | 11 | Legacy Blog readability plus composed panel size/position preservation and export-size agreement |
| `tests/test_app.py` (new cases) | 4 | Offline end-to-end route, prior overview preserved during replacement, failure preservation, generation-key contract |
| `tests/test_exports.py` (new cases) | 3 | Free-sized PNG/PDF/SVG/EPUB export |
| `tests/test_agent_overviews.py` (new cases) | 2 | Blog reference admission for the new provenance and its rejections |

Verification of the renderer itself is native: every panel example and composed overview in these
suites is measured by the real WebKit helper, not by a Python attribute scan.

## Baseline and test migration

Baseline recorded in `.scratch/overview-rebuild/baseline/`. Before the rebuild, the four focused
modules failed with two `NameError: name 'routes' is not defined` errors from the retired router in
`papers/arrangement.py`; the browser and extension checks passed.

Tests retired with the behaviour they specified, and what covers that behaviour now:

| Retired | Replaced by |
| --- | --- |
| Visual-mode agent-loop tests (31 methods: panel drafts, bridges, layout repair loops, no-progress counters, overview word budget, `_fit_diagnostic`, `_repair_evidence`, parallel-scene prototype) | `tests/test_overview_workflow.py` (planner refinement, fallback, cancellation), `tests/test_panel_authoring.py` (local checks and simple recovery), `tests/test_panel_guides.py` (free-size rendering and raster bounds) |
| `test_both_modes_complete_after_structured_review` | `test_blog_completes_after_a_structured_review`, plus the new end-to-end Overview test |
| `test_fresh_import_to_automatic_overview_uses_four_generation_requests_only` | `test_fresh_import_to_automatic_overview_runs_the_panel_workflow_once` |
| `test_overview_author_contract_accepts_one_fixed_svg_figure` | Panel-plan schema and ownership tests in `tests/test_overview_workflow.py` |
| Parallel-scene prototype test | Deleted with `papers/prototypes/parallel_scene.py` |

Kept and still green: source safety and profile rejection, actual geometry bounds, cancellation,
prior-generation preservation, bibliography filtering, legacy reviewed-artifact admission, and
export compatibility.

## Deviations from the plan, and why

1. **Column choice metric.** "Least unused row area" is degenerate as written: any per-row slack
   metric always prefers one column, because a one-panel row wastes nothing sideways. The arranger
   ranks candidates by unused area of the whole composed canvas (equivalently, the smallest canvas,
   since the panel area is fixed) and breaks ties by fewer rows. Wide panels stack; a mixed-width
   plan uses columns. Reading order, non-intersection, canvas bounds, and text size are all asserted.
2. **`illustrative_values` on the drawing assignment.** The design fixes the assignment fields, and
   the assignment's `shared_facts` maps a key to its display text. To let the simplified recovery
   mark illustrative numbers without changing that mapping, the projection adds a list of the
   illustrative display values. It is drawn from `shared_facts[].kind` and never invented.
3. **Sequence tests for repair and recovery** were written in the coordinator suite (Task 6) rather
   than as separate Task 4 cases, because the create → repair → simplified sequence lives in
   `build_panels`; the Task 4 units (prompt, request, check, simple panel) are tested directly.
4. **Reader interaction check** ran in a real Chromium engine (agent-browser) against the real
   `index.html` and `app.js` with a seven-panel composed artifact, not in WKWebView. The composed
   image itself is measured and rasterized by WKWebView in every native test. Evidence:
   `.scratch/overview-rebuild/webview/dialog-fit.png`, `dialog-panel-4.png`, `figure.png`.
   It found and fixed one real defect: pointer capture retargets the release event, so panel focus
   now hit-tests by position instead of relying on `event.target`.

## Not verified

- **Live pilot.** No provider call was authorized, so there are no delivered live artifacts. The
  intended call breakdown (selection, narrative, 1–3 planner passes, one creation plus one repair
  per panel) is exercised only with scripted providers.
- **Human inspection of delivered overviews.** The design requires a person to confirm that a novice
  can follow the central contribution and that brief content survived drawing. The offline fixture
  images are readable and defect-free by measurement, but that is not the same claim, and no such
  claim is made here.
- **Interactive WKWebView inspection.** Trackpad pinch and gesture behaviour in the macOS webview
  was not exercised by hand; the keyboard, click, and control paths are covered by the browser check
  and the DOM suite.
- **Installed application and release.** Nothing was installed, published, or signed.
