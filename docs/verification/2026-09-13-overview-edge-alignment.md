# Final exposed-edge alignment

Status: historical. The model-drawn SVG path this report verifies was deleted by the [figure library consolidation](../superpowers/specs/2026-09-18-figure-library-consolidation-design.md); the code is at commit 9abae74.

The user accepted the coordinated resizing experiment and requested a final pass to align exposed left and right panel edges, allowing stretching along one axis when the gap is large. This explicitly supersedes the earlier uniform-scaling restriction for this final pass.

Latest ordering decision: align outer panels by translation before the coordinated resize search. Then run the search, and apply bounded one-axis stretching afterward for residual gaps. The initial alignment does not stretch content. The temporary proposal to score aligned copies during every search step is not part of this implementation.

## Scope

Use a translation-only initialization before mixed resizing, retaining original growth scales and the canvas-area budget as reference values. Candidate placement must use the aligned working positions so the search does not silently undo the initialization by restoring old centres. Preserve the accepted result as a fallback when initialization does not help.

Run the final stretching pass after mixed resizing, preserving its canvas and reading order. Detect exposed edges using the actual frame intervals and all neighbouring frames. An edge can face the canvas in one horizontal band and a neighbouring panel in another; the nearest collision still limits the whole panel's expansion.

Prefer useful translation before stretching. Stretch the panel content horizontally with its frame, keeping vertical scale, frame padding, and panel-number styling unchanged. A global minimum-gap threshold and a modest maximum stretch bound prevent small adjustments and excessive distortion. Apply the same rules to every layout, with no paper-specific or provider-specific conditions.

The new transform must update content origins, frame bounds, and click rectangles together. Validate canvas containment, inter-panel padding, readable text, and repeat-call stability. Preserve the accepted mixed layout when the pass cannot improve it safely.

## Verification

Replay all 13 saved runs / 59 panels into `.scratch/overview-edge-fit`, retaining the original and mixed outputs. Inspect final native render checks and compare exposed-edge gaps. Independently audit varied synthetic arrangements, including left- and right-side gaps, interior panels, partially exposed edges, already aligned panels, and nonzero source bounds.

Luna max owns implementation and corpus replay. The parent owns the independent geometry audit and visual assessment. Preserve comparison artifacts separately. After verification, integrate the accepted passes into generation with backward-compatible compositor support for the new two-axis transform.

## Delivered implementation

`papers/overview_workflow.py` now runs the existing growth and shrink checkpoints, translation-only outer alignment, coordinated resizing, and final edge stretching. It compares the aligned search against the original mixed search and retains the original when alignment worsens gap discrepancy or occupancy. That comparison uses the numerical fitting tolerance, not the larger coordinate-rounding tolerance.

`papers/mixed_fit.py` contains the accepted bounded resize search. `papers/edge_align.py` handles exposed-edge translation and final stretching. Neither module calls a model or changes panel source content. `papers/html_figures.py` accepts absolute horizontal and vertical scales while preserving the existing uniform-transform output. Final frame bounds continue to supply the reader's panel click rectangles.

The stretch threshold is 32 layout units with the default padding, and the maximum horizontal stretch is 1.05 times the accepted uniform scale. Vertical scale, frame padding, and number badges remain unchanged. Initial translation may redistribute whitespace before resizing; final output must preserve or improve the accepted mixed result.

## Measured results at the final 5% cap

The current replay covers all 13 saved runs and 59 panels. Every final native render has zero reported geometry issues. The smallest measured text size is 14.716286 pixels. Compared with the accepted mixed checkpoint, three runs improve the gap score and ten remain unchanged. Four runs retain the original search result because the aligned initialization does not help.

| Case | Previous gap score | Final gap score | Previous occupancy | Final occupancy |
| --- | ---: | ---: | ---: | ---: |
| Terra architecture | 0.078913 | 0.066954 | 85.54% | 86.85% |
| Terra method | 0.005046 | 0.003744 | 92.36% | 92.82% |
| DeepSeek architecture | 0.002275 | 0.002258 | 92.91% | 92.91% |

Occupancy measures panel-frame area relative to the canvas. Gap score measures whitespace discrepancy; neither metric alone proves visual quality. The parent inspected the final Terra architecture and method renders. Horizontal stretching reduces the exposed gaps but mildly widens text and shapes. Remaining whitespace is acceptable when closing it would exceed the stretch limit or violate neighbouring-panel clearance.

The parent independently verified all 59 original SVG hashes against both the saved runs and accepted mixed replay. Original images and sources remain available. The gallery is `.scratch/overview-edge-fit/index.html`; per-case results include native checks, frame geometry, scales, and source hashes.

Verification before the final cap reduction, retained as pipeline evidence:

- 56 synthetic edge cases covering one to seven panels and nonzero source bounds passed scale, padding, containment, source-origin, readability, input-immutability, and repeat-call checks. Sixteen improved.
- 28 complete-pipeline cases passed gap and occupancy non-regression, area, padding, containment, readability, input-immutability, and deterministic-output checks. Nine improved.
- 155 focused native tests passed in 66.124 seconds across panel authoring, guides, overview workflow, readability, and exports.
- The offline app generation test passed in 1.070 seconds.
- The app UI checks passed.
- Seven focused edge and mixed-layout regression tests passed after review fixes. The search now derives scale limits and source measurements explicitly from the original growth checkpoint, accepting only validated working positions. The parent reran all 28 pipeline cases and confirmed exact final placement and canvas equality with all 13 native replay artifacts after that change.
- Luna's bounded code rereview confirmed all three findings resolved, with no remaining geometry blocker.

These are local saved-source and offline checks. No paid generation or installed-app modification was used. The prior checkpoint remains commit `35260f3`; the new changes are not committed.

Final cap adjustment: the user found both 25% and 15% too stretched and selected a smaller bound. The final maximum is 5%. Seven focused regression tests passed, and all 13 saved runs / 59 panels were rendered again with zero native issues. Every final horizontal-to-vertical scale ratio is at most 1.05 within rounding tolerance. Earlier 25% images and result metadata remain beside the current artifacts with `-25pct` filenames.
