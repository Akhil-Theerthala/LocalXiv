# Coordinated shrinking and enlargement experiment

Status: historical. The model-drawn SVG path this report verifies was deleted by the [figure library consolidation](../superpowers/specs/2026-09-18-figure-library-consolidation-design.md); the code is at commit 9abae74.

Baseline commit: `35260f3`, the current Overview rebuild and shrink-first checkpoint. The user requested this commit before the experiment and explicitly required a general algorithm rather than fixes for selected panel states.

## Question

Can coordinated uniform shrinking and enlargement reduce uneven gaps more effectively than the shrink-first checkpoint, while preserving readable text, panel geometry, reading order, and padding?

The hypothesis is that a mixed move can shrink a panel that controls the canvas width while enlarging another panel into the space released. Either change alone may be rejected, so the search must consider joint candidates.

## Boundaries

- Keep the experiment under `.scratch/overview-mixed-fit` until its results are evaluated. Production remains at the committed checkpoint during the comparison.
- Reuse measured bounds, native text measurements, separation graphs, placement, and gap scoring from `papers/arrangement.py`.
- Allow uniform panel scaling in both directions, bounded relative to the original growth checkpoint. Preserve the 14-unit text floor and fixed frame padding.
- Let the used canvas follow the result, with its area bounded by the growth checkpoint's canvas area. Do not cap width and height independently or choose a target aspect ratio. A narrower arrangement may need extra height when its lower panels enlarge.
- Preserve the unchanged checkpoint as a candidate. No provider names, paper identifiers, hard-coded coordinates, or special layout cases belong in the algorithm.
- Keep original sources and all previous previews untouched. No provider calls are needed.

## Evaluation

Compare all 13 saved runs, containing 59 panels, against the current shrink-first output and the earlier growth checkpoint. Report directional gap scores, frame occupancy, scale changes, canvas dimensions, native rendering results, and search time. Inspect rendered results, especially the unresolved Terra architecture example. A lower geometry score alone does not establish better visual quality.

The parent separately generated 28 synthetic arrangements containing 112 panels before seeing experimental outputs. These cover one through seven panels in rows, columns, shelves, and staggered placements with varied dimensions. Use these as held-out checks for separation, readable scales, bounded changes, deterministic behavior, and improvement or unchanged fallback. They test broader geometry, not every possible layout.

Luna max owns the experimental implementation and corpus replay. The parent owns the independent synthetic audit and visual assessment. A scoped code review follows the experiment. This is a bounded local search; global optimality is not a requirement or a claim.

## Results

The experiment uses 4% single-panel and paired steps, with factors bounded to 0.80–1.50 of each panel's growth-checkpoint scale. It retains native text limits, fixed padding, the original separation graph, and the unchanged shrink checkpoint. The same settings apply to every case.

An initial 256-candidate cap stopped several searches early. A corpus-wide comparison with 1,024 candidates improved five cases further with no gap or occupancy regressions. Pure search took at most 0.267 seconds in that comparison. The final experiment therefore uses 1,024 candidates globally; the score and scale bounds did not change. The earlier results remain under `.scratch/overview-mixed-fit/budget-256`.

The final native replay covered all 13 runs and 59 panels. Eight layouts improved their gap score over shrink-first, and five stayed unchanged. All final native checks reported no issues; minimum measured text was 14.7163. The parent checked the final gap and occupancy comparisons and candidate limits independently. The final replay recorded a maximum search time of 0.290 seconds.

For `terra/1706.03762v7`, the gap score fell from 0.157803084 to 0.078912760 and frame occupancy rose from 76.84% to 85.54%. The parent inspected the final rendered image: the lower panels enlarge and the canvas becomes taller, reducing the empty right-hand region. Some whitespace remains. The parent also inspected the Terra method and OpenRouter survey comparisons; their phase boundaries fill the available space more consistently, although internal SVG text and geometry remain unchanged.

All 28 independent synthetic cases passed separation, containment, readable-scale, area-budget, scale-bound, input-preservation, and gap/occupancy checks with the final 1,024-candidate cap. Twenty-two improved, and six stayed unchanged. Repeated calls and panel-ID renaming preserved geometry in all 28 cases at both budgets. Three focused prototype unit tests passed, including skipping an unusable mixed result before native rendering. Original SVG hashes for all 59 panels and byte equality of 26 copied baseline images were independently verified.

The result supports mixed resizing over shrink-only refinement for this corpus and these synthetic arrangements. It does not prove that every arrangement will improve: the fixed separation graph, uniform scaling, scale bounds, and single/pair search can leave gaps. The seven-panel DeepSeek method case reached the final budget. No provider-specific or paper-specific branches were added.

The code and three-way gallery are in `.scratch/overview-mixed-fit`; the independent audits and budget comparison are in `.scratch/overview-mixed-audit`. Production remains unchanged at `35260f3` so this experiment can be assessed separately.

Scoped review found no geometry blocker. It identified an invalid-result reporting path that could access absent metrics after rendering. The replay now records that case as skipped before rendering, and the fitter preserves an available feasible shrink checkpoint on failure. The report distinguishes recorded native text measurements used during search from native checks on the final image. The retained `fit` metadata describes the growth checkpoint; `mixed.final_scales` describes the selected result.
