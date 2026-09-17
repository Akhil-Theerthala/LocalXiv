# Overview gap fitting

Status: implemented and locally verified. This is the accepted checkpoint for the later shrink-first refinement in [`docs/design/overview-layout-shrink-first.md`](../design/overview-layout-shrink-first.md).

The current task implements the geometry discussed with the user in [`docs/design/overview-layout-fitting.md`](../design/overview-layout-fitting.md). Panels retain their source content and uniform internal proportions. Text reflow is deferred. There is no preferred canvas aspect ratio.

## Evidence boundary

The replay inputs are the 13 completed runs under `.scratch/overview-rebuild/live/runs`, containing 59 panels. Every run has an original `arrangement.json` in its recorded run directory. Those coordinates and scales are the input to fitting. Outputs belong in `.scratch/overview-gap-fit`; original runs are preserved.

Before fitting, the union bounding rectangle of each panel's measured elements, scaled into its saved layout, occupies between 49.5% and 70.2% of the combined canvas across the 13 runs. This measures content bounding boxes, including any space inside them, rather than literal painted-pixel coverage.

The prior compact-frame implementation passed 143 focused tests and 13 native replays. Those results predate this gap-fitting algorithm and do not validate it.

## Geometry decisions

The seed canvas supplies a finite fitting envelope. Pair separation constraints preserve which side panels occupy. Longest-path placement establishes whether proposed scales fit; a reverse pass establishes the latest feasible positions. Final placement prefers original centres within those bounds. Progressive shared growth stops constrained panels while allowing other panels to continue.

This is a deterministic heuristic. Fixed proportions and spatial relationships can leave residual gaps greater than the requested padding. The implementation must record those gaps and identify any fallback instead of reporting complete filling.

The logic review identified and corrected four ambiguities before code review: retain seed centres when feasible, verify acyclic separation graphs, preserve saved scales in native source units, and revalidate coordinates after canvas trimming. A fallback retains its own diagnostic state and does not claim the fitted padding invariants passed.

## Verification results

- The focused native suite passed 147 tests in 64.216 seconds. The exact command and implementer report are in `.scratch/overview-gap-fit/luna-report.md`.
- Replay completed all 13 runs / 59 panels, with no skipped runs, infeasible fits, or native `issue_details`. These checks do not certify every internal diagram overlap or scientific claim.
- Mean frame occupancy within the same fitting envelope increased from 0.707896 to 0.821188. This includes fixed frame padding and number bands; it differs from the content-only baseline above.
- An independent audit of 40 deterministic random two-by-two layouts found no overlap, margin, or below-seed-scale violations.
- The production offline generation-and-save test passed, and `node tests/test_app_ui.js` passed after integration.
- All 13 original overview image hashes and 59 source hashes match the pre-fitting replay. New artifacts are under `.scratch/overview-gap-fit`.

The user accepted the current versions but identified remaining side gaps. Code review was paused at the user's request while the next shrink-first rule was discussed. Residual whitespace is recorded; the grow-only checkpoint does not claim to eliminate it.
