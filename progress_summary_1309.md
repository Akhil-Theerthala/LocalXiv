# Progress summary — 2026-09-13 (checkpoint)

Panel-level ("modular") model-authored SVG overviews. Branch `akhil/model-authored-svg-overviews`.
Nothing has been committed; 46 paths are modified or new in the working tree.

This file is a factual checkpoint. It lists observations, the current build state, the open issues and
a plan skeleton. It deliberately does not state conclusions about why any figure looks the way it
does; the evidence needed to judge that is referenced below.

---

## 1. Where the work stands

| Area | State |
| --- | --- |
| Monolithic SVG path hardening (overflow check, overlap relaxation, font-size messages, page fit CSS, ratio contract, DeepSeek thinking toggle, repair-payload trimming) | Done earlier, superseded by the modular pivot, still in the tree |
| Modular core: draft schema and validation (`papers/explanation.py`) | Done, tested |
| Modular core: measurement, label-unit packing, arrangement (`papers/arrangement.py`) | Done, tested |
| Modular core: composer with app-drawn chrome (`papers/html_figures.py`) | Done, tested |
| Modular pipeline wired into `generate()` (`papers/agent_overviews.py`) | Done, orchestration tests migrated |
| Orchestration test migration (counts/stages, repair flows, three retirements) | Done |
| Bridgeless design (no bridges, no canvas text, serial numbers, panel isolation) | **In flight, tree is red** |
| Parallel panel construction | **Not started** (panels are drawn sequentially) |
| Efficiency work (concurrency, request accounting, context size) | **Not started** |
| Page budget in label units per panel | **Not started** |
| Frozen live matrix, provider comparison | **Not started** |
| Independent visual acceptance | **Not started** |
| Docs: ADR 0003, `CONTEXT.md`, plan doc, verification report | Partly updated (see §7) |

---

## 2. Build state right now

Command:

```
LOCALXIV_HTML_RENDERER="$PWD/papers/html-snapshot" \
  .scratch/overview-agent-env/bin/python -m unittest discover -s tests
```

* Last fully green run before the in-flight change: **378 tests, 1 skip, OK**.
* Current run: **5 failures, 31 errors, 1 skip**. Every failure traces to two mechanical breakages
  left by the in-flight change:
  1. `papers/arrangement.py:278` still reads `'routed': all(route['rects'] for route in routes)`
     while the bridge router it refers to was deleted (`NameError: name 'routes' is not defined`).
  2. `tests/test_panel_authoring.py` lines 135, 146, 157 still call `arrange(panels, groups, bridges)`
     (`TypeError: arrange() takes 2 positional arguments but 3 were given`).
  Nothing else in the failure list is independent of these two.

---

## 3. Files changed in this session

| Path | What it contains now |
| --- | --- |
| `papers/explanation.py` | Draft schema (`title`, `paper_connection`, `caption`, `groups`, `panels`), `validate_draft` with coverage/membership/bridge sections, `validate_shell`, `SHELL_SCHEMA`, panel and group validation. Bridge schema/validation removed in flight. |
| `papers/arrangement.py` | `panel_metrics` (viewBox, smallest effective label through transforms/tspans, words), `label_ratio_floor`, `panel_bounds` (in-flight addition), deterministic packing (`_stack`/`_row`/`_columns`), readability prediction, `compress` candidates. Bridge routing removed in flight. |
| `papers/html_figures.py` | `SHARED_MARKERS`/`SHARED_MARKER_IDS`, `normalize_panel_svg`, `normalize_svg`, `svg_visible_text`, `compose_figure` (card frames, numbered panels in flight), `render`. Bridge markup deleted in flight. |
| `papers/agent_overviews.py` | Modular stages inside `generate()`: `plan_draft`, `review_draft`, `author_leaf` with in-stage guard, `build_candidate`, `composed_candidate` (readability gate), `attribute`, `repair_shell`, `repair_overview`. New prompts `DRAFT_PROMPT`, `DRAFT_REVIEW_PROMPT`, `PANEL_PROMPT`, `SHELL_REPAIR_PROMPT`. `PROMPT_REVISION = 'smolagents-panel-svg-v1'`. |
| `tests/test_panel_authoring.py` | 15 tests: draft validation, panel metrics, arrangement, composition (native end-to-end, viewBox limits, uncomposable page). |
| `tests/test_agent_overviews.py` | Orchestration tests migrated to the modular protocol, including the new panel/guard/shell cases. |
| `tests/test_reading.py`, `tests/test_reading_bibliography.py`, `tests/test_app.py`, `tests/test_pdf_fallback.py` | Shared `scripted_provider` fixture and request-count expectations migrated. |
| `docs/verification/2026-09-13-svg-overview-migration.md` | Extended with the modular wiring status, retired-test mapping, live evidence table, artifact paths and remaining gaps (487 lines). |
| `docs/adr/0003-panel-level-svg-authoring.md`, `CONTEXT.md`, `docs/superpowers/plans/2026-09-13-model-authored-svg-overviews.md` | Pivot rationale and glossary (need a pass for the bridgeless amendment). |
| `.scratch/svg-overview-live-v4/` | Live runner (`driver.py`, `supervise.py`, `run_case.py`, `collect_artifacts.py`, `describe_image.py`), `manifest.json` (revision, `request_limit_per_generation: 30`, authoring description), `panel-wiring.patch` (the earlier 342-line patch, applied). |

Supporting commands used throughout:

```
# tests
LOCALXIV_HTML_RENDERER="$PWD/papers/html-snapshot" .scratch/overview-agent-env/bin/python -m unittest discover -s tests
# Swift renderer rebuild after touching HTMLSnapshot.swift
xcrun swiftc -sdk /Library/Developer/CommandLineTools/SDKs/MacOSX15.4.sdk \
  -module-cache-path /private/tmp/localxiv-swift-module-cache -O papers/HTMLSnapshot.swift -o papers/html-snapshot
# live run
.scratch/overview-agent-env/bin/python .scratch/svg-overview-live-v4/driver.py --phase modular --filter <case>
```

---

## 4. What the modular pipeline does today

Visual path inside `generate()`:

1. **Selection** and **narrative plan** (unchanged stages).
2. **Draft** — one model call producing `{title, paper_connection, caption, groups, panels}`;
   validated against the accepted plan and the retrieved evidence, with the same
   cycle detection and two-non-improving-corrections rule as the narrative stage. Draft issues are
   checkpointed for diagnosis.
3. **Draft review** — one evidence-grounded verdict before anything is drawn; a rejected draft gets
   exactly one bounded revision.
4. **Panels** — one model call per leaf, returning `{panel_id, svg}`. An in-stage guard validates the
   SVG profile, rejects local `defs`/markers, rejects a canvas whose smallest label is below the
   ratio floor for its shape, and rejects geometry that leaves the canvas. Guard messages are
   returned to the model inside the same stage. The paper's selected figure is attached as image
   evidence to this stage.
5. **Arrange and compose** — the application measures the accepted panels, packs them
   deterministically, draws the chrome, and produces the figure the renderer and reviewer see.
6. **Render, review, repair** — the existing loop: native check, then the figure review; issues are
   attributed back to panels (namespaced id, mentioned id, visible label text, else all leaves) and
   only those panels are re-drawn; metadata paths (`figures[0].title|paper_connection|caption`)
   go to a metadata repair instead. Unreadable arrangements are repaired through the `compress`
   candidates before the page is composed.
7. **Failure semantics** — a leaf that fails after its corrections fails the run; panels are never
   dropped. There is no fallback to single-document authoring.

Per-run artifacts written next to the generation: `plan.json`, `draft.json`, `panel-draft` data in
`generation_context.json`, `panels/<id>.svg` (in flight), `arrangement.json` (in flight),
`composed.svg` (in flight), `rendered-draft.json`, `reviews.json`, `agent-trace.jsonl`,
`failure.json`.

---

## 5. Live runs (facts)

Five runs, frozen credentials, ceiling 30 requests / 600 s per run. None produced an accepted figure.
Command used: `driver.py --phase modular --filter <case>`; results under
`.scratch/svg-overview-live-v4/modular/<provider>/<paper>/run-1/`.

| Case | Requests | Elapsed | Terminal message recorded in `summary.json` |
| --- | --- | --- | --- |
| `gemini/1706.03762v7/run-1` | 30 | 280 s | `Diagnostic request ceiling reached (30).` |
| `gemini/2606.19868v1/run-1` | 6 | 54 s | `panels must cite the evidence behind every accepted claim; missing p00001, p00019, p00048, p00069, p00071, p00086, p00088 It did not improve after two corrections.` |
| `deepseek/1706.03762v7/run-1` | 6 | 138 s | `panels must cite the evidence behind every accepted claim; missing p00016, p00054, p00064 It did not improve after two corrections.` |
| `gemini/2511.07694v1/run-1` (earlier) | 7 | 34 s | `panels must cite the evidence behind every accepted claim; missing p00001, p00042 It did not improve after two corrections.` |
| `gemini/2511.07694v1/run-1` (latest) | 30 | 300 s | `Author returned prose without a tool call. Draft retained; no automatic retry.` |

Stage sequences are in each run's `agent-trace.jsonl` (request number, stage, label, status, error).

### 5.1 The one run that reached composition

Directory:

```
.scratch/svg-overview-live-v4/modular/gemini/2511.07694v1/run-1/paper/reader/overview-figures/45818ad0efa545bc8adb912921631d15/
```

Contents to inspect:

| File | What it shows |
| --- | --- |
| `composed.svg` | The composed figure as produced by the pipeline (viewBox `0 0 1155.65 1319.468`) |
| `composed-page.png`, `composed-page.html` | The same figure rendered through `papers.html_figures.render` |
| `panels/{seq_prob,topk_select,pro_bound,eval_auroc}.svg` | The four accepted model-authored panels (450–920 unit canvases, font-size 24) |
| `panels-png/*.png` | Those panels rasterized for direct viewing |
| `arrangement.json` | Placements, cards, canvas, `displayed_px`, `readable`, `compress` |
| `plan.json`, `draft.json`, `generation_context.json`, `failure.json`, `agent-trace.jsonl` | Plan, narrative draft, checkpoints (including the panel draft and draft issues), failure record, per-request trace |

Measurements recorded by the native checker for that composed page: page height **960 px** (limit
960), **71 labels, displayed sizes 6.8–9.5 px**, floor 14 px, reading scale 0.667. The arrangement
recorded `displayed_px` **6.7** for the same canvas.

Panel-level facts for the same run: every panel's declared geometry is inside its own viewBox
(`panel_bounds(...)['inside'] is True` for all four).

### 5.2 Defects found by the live runs (six)

Listed as observations with the recorded evidence. Changes already made in response are named; no
causal claim is made about the figure appearance.

1. Composing a canvas beyond the platform's 2000-unit viewBox limit produced
   `SVG needs viewBox="0 0 width height", dimensions 100-2000 by 80-2000.` with no attribution.
   Change made: the unit scale respects the viewBox and source font-size limits; a canvas with no
   valid scale raises `cannot be composed at a readable label size`.
2. `svg_visible_text` rejected a panel that referenced `url(#arrow)` (`Marker reference does not
   resolve to a marker: arrow.`), which reached the first repair round. Change made:
   `svg_visible_text` accepts `external_markers` and the attribution call passes `SHARED_MARKER_IDS`.
3. After a native failure, a caption issue re-triggered the metadata repair and the recomposed
   content was byte-identical, producing `Author resubmitted a previously rejected candidate.`
   Change made: metadata repairs re-arm only when a review has run again, and only
   `figures[0].title|paper_connection|caption` reach the metadata repair.
4. The draft coverage requirement carried no measurable distance, so runs stopped with
   `It did not improve after two corrections.` after two attempts. Change made: the issue carries
   `constraint='uncovered_passages', actual=<count>, limit=0`, and the draft prompt states the
   coverage rule.
5. The panel label ratio was in the prompt but not in the guard, so a panel with a small label could
   be composed. Change made: the panel guard rejects a canvas whose smallest label is below
   `label_ratio_floor(width, height)` and returns the canvas width or font size that would pass.
6. One panel stage ended with prose instead of a submission:
   `Author returned prose without a tool call. Draft retained; no automatic retry.` No change made
   yet; the stage has no retry.

### 5.3 Observations about the composed page (for human inspection)

Described, not diagnosed:

* Card frames, group frames and their overlapping text; the panel titles appear twice (a card
  heading drawn by the application and the model's own title inside the panel).
* Two bridge label texts appear together near the bottom of the canvas, overlapping each other, and
  a bridge line crosses the lower group's heading area.
* The four panels themselves read as a coherent worked example: sample N=3 candidates, softmax token
  probabilities, the NLL factorisation, ranking 0.82/0.12/0.01; a bar chart with sorted
  probabilities and an α = 0.10 cutoff line; the PRO lower bound with K=1 and K>1 cases; an AUROC
  table with 0.739 / 0.715 / 0.705.
* Every label on the composed page measures 6.8–9.5 px at the recorded reading scale.

### 5.4 In-flight design change (requested at this checkpoint)

Direction given: remove inter-panel bridges; panels are isolated; serial numbers define the reading
order; no additional canvas-level text.

Applied so far in the working tree:

* `papers/explanation.py`: `PANEL_BRIDGE_KINDS`, `DRAFT_BRIDGE_SCHEMA`, the `bridges` schema property,
  `_validate_bridges` and the "needs at least one bridge" rule removed; `_draft_sections` now returns
  panels and groups.
* `papers/arrangement.py`: `_route_endpoints` removed; `arrange(panels, groups)`; panel cards carry
  `order`; `HEADING_BAND` replaced by `NUMBER_BAND = 2.4`; group content offset no longer reserves a
  heading band; `panel_bounds` added.
* `papers/html_figures.py`: bridge colours, label units, router and markup removed; `_card_markup`
  draws the frame plus the reading-order number only; `compose_figure(panels, arrangement)`.
* `papers/agent_overviews.py`: wiring passes `order` and drops bridges; draft, draft-review and panel
  prompts rewritten for isolated numbered panels (title inside the panel, nothing outside the
  viewBox, no connectors between panels); the panel guard now rejects geometry that leaves the
  canvas.
* Tests: `draft_for` no longer emits bridges in `tests/test_panel_authoring.py`,
  `tests/test_agent_overviews.py`'s `draft_submission` likewise.

Not yet applied, and the reason the tree is red: the two mechanical breakages in §2, plus a pass over
test names/assertions that still speak of bridges (for example
`test_unknown_ids_and_duplicates_are_rejected`, `test_two_panels_arrange_readably`,
`test_oversized_panels_report_compression_candidates`, `test_grouped_panels_stay_inside_their_card`).

---

## 6. Open issues (no causes stated)

1. Composed page label sizes versus the 14 px floor, with the arrangement prediction and the native
   measurement agreeing for the observed case (6.7 vs 6.8–9.5 px) — see §5.1.
2. No panel-level budget in label units is communicated to the draft or the panel authors.
3. Card headings duplicate the panel's own title; canvas-level text collides with panel and bridge
   content in the observed page.
4. Bridge labels collided with each other and a bridge line crossed a heading area in the observed
   page. (Direction now: remove bridges entirely.)
5. Panels are drawn sequentially; no concurrency, no fan-out, no per-stage latency accounting.
6. The frozen ceiling of 30 requests was reached twice; three runs stopped in the draft stage after
   two non-improving corrections.
7. One panel stage ended with prose instead of a submission and failed the run.
8. Draft coverage stops were reported for three different papers, both providers, with different
   missing-passage sets.
9. Docs still describe bridges as part of the design (`docs/adr/0003-panel-level-svg-authoring.md`,
   `CONTEXT.md`, `docs/superpowers/plans/2026-09-13-model-authored-svg-overviews.md`), and the
   verification report's live-evidence section predates the bridgeless change.
10. `.scratch/svg-overview-live-v4/manifest.json` records the modular revision, the 30-request
    ceiling and the composed-page checker; the frozen matrix itself has not been run.

---

## 7. Plan skeleton

To be replaced by the detailed plan you bring back. Ordering here is by dependency, not by value
judgement.

**P0 — restore a green tree**
* Remove the `routes` reference at `papers/arrangement.py:278`.
* Update the three `arrange()` call sites in `tests/test_panel_authoring.py` (lines 135, 146, 157).
* Rename/retarget the remaining bridge wording in tests.

**P1 — finish the bridgeless design**
* Serial numbers: where they are drawn, their size, and whether panel frames stay or go.
* Isolation enforcement: keep `panel_bounds` in the guard; decide the tolerance and the message.
* Group frames: keep as layout-only frames, or drop the frames and keep grouping as packing only.
* Prompt contract for the draft, draft review and panel stages; `SVG_FIT_GUIDANCE` wording for panels.
* Tests: composition (numbers, no bridges, no canvas text), arrangement, isolation guard.
* Docs: ADR amendment, `CONTEXT.md` glossary, plan doc, verification report.

**P2 — parallel panel construction and efficiency (not started)**
* Fan-out policy for the panel stage, provider concurrency limits, 429 handling, ordering guarantees.
* Per-stage request and latency accounting; context/prompt size accounting; what parallelism does to
  the 30-request ceiling and to the wall clock.
* Whether the draft review and the metadata repair stay as separate calls.

**P3 — panel and page budget**
* Allocate a width/height budget in label units per panel from the panel count.
* Express it in the panel brief and enforce it in the guard.
* Recalibrate the ceiling and the prompt guidance against a measured pilot.

**P4 — live evaluation and acceptance**
* Pilot with both providers; then the frozen matrix (3 papers × 2 providers).
* Independent inspection of accepted figures (`describe_image.py` plus human review).
* Update the verification report and the manifest; record what changed and what remains.

**P5 — hygiene**
* Decide the fate of the monolith-only code paths that remain in the tree, the superseded report
  sections, and the `.scratch` artifacts that are no longer referenced.

---

## 8. Open questions for the plan

1. Serial numbers: inside each panel's own canvas, or drawn by the application in the card? Should the
   panel frames remain at all?
2. Should group frames remain (layout-only) or should grouping affect packing without any visible
   frame?
3. Panel budget: is it acceptable for the draft to assign an explicit label-unit budget per panel, and
   for the guard to reject panels that exceed it?
4. Parallelism: is bounded concurrency in the panel stage the target, and is the 30-request ceiling a
   hard constraint or a number to re-derive?
5. Retry policy: how many prose-only or truncated turns should a stage absorb before the run fails?
6. Which artifact set must a run leave behind for acceptance, and is `composed.svg` plus rendered
   PNG/HTML enough?
