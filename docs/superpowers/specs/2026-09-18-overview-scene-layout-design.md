# Overview scene layout

Status: implemented on 2026-09-18 after the user reviewed the first stacked-column output. Supersedes the Data, Stages, and Composition sections of the [Overview simplification design](2026-09-18-overview-simplification-design.md); the Requirements there on readability, the reader invariant, and no page budget in the prompt still hold. Reference images are in `docs/reference_images/`.

## Why

The stacked-column Overview was accurate-looking but sparse, 13 text runs per million square units against 42 to 64 in the user's reference figures, and its plan schema (flat labels plus pairwise relations) could not say "B is inside A" or "this equation is what A computes". The first live figure drew `softmax(QKᵀ/√d_k)V` as a step after the scaled dot-product block. Four designs in this repository let the model author geometry; all produced overflow, tall canvases, or sparse chains. The prototype in the session scratchpad reproduced the Attention reference from a hand-authored tree at 47 runs per Mpx, so the model now authors content and structure, and the application lays it out.

## What the Overview is

The first Pareto pass over a paper: the core content a reader needs, dense, at one small text size. For an architecture paper, every component and how they nest, with the operation each computes. For a method paper, the mechanism as a worked example. For a survey, the taxonomy of families and their representative methods. The Blog is the second pass, the journey narrative; the paper is the third.

## Data

**Digest** (`validate_digest`, `papers/explanation.py`). One object per paper: `paper_type`, `contribution`, `result`, `qualification` (each with passages), `example` (required for architecture and method), `hyperparameters` (at most 12 short strings), and 4 to 24 `components`, each with `id`, `name` (≤40), `role` (≤120), optional `computes` (≤80), `values` (≤60), `repeat`, `contains` (ids), `feeds` (ids), and passages. An architecture must nest at least one component; an architecture or method must give at least one `computes`. The digest is saved as the generation's `plan`, and `narrative_digest` is its digest, so Blog reference admission keeps working.

**Scene** (`validate_scene`). `title`, `subtitle`, `footer`, `illustrative`, `layout` (`stack` or `columns`), and 1 to 4 panels. A panel has `id`, `heading` (≤80), optional `tone`, one body node, at most 2 `notes`, and at most 12 `edges` between card ids in the same panel. Eight node kinds: `card` (label ≤40, detail ≤80, tone, dashed, plain), `group` (heading, repeat, arrange row or column, 1 to 8 children, at most 3 deep), `note` (1 to 4 lines), `sequence` (2 to 8 items with sub-labels), `grid` (up to 6×6 cells, labels ≤16, cells ≤12, highlighted or masked), `steps` (1 to 6 numbered lines), `bars` (2 to 8 label and number pairs), `divider`. At most 24 leaf nodes per panel. A scene names no gap, size, or coordinate; those fields are rejected.

**Coverage** (`scene_coverage_issues`). Every component name and every `computes` string must appear in the scene. A component with two or more parts of its own must be a group heading; parts shared by several components are drawn once.

## Layout (`papers/scene_layout.py`)

One 1000-unit column, 14-unit text, headings at 15, title at 26. Text is measured in the renderer's font. Cards are as wide as their label or detail up to 300 units and never narrower than their longest word; labels and details wrap. A row shares its width among its children before it falls back to a column. A column is as wide as its widest child; a narrow column of four or more nodes reflows into two, and unheaded nested columns flatten first. Top-level rows justify to the panel width with a 460-unit cap per child, and children re-wrap at their justified width. Every node reports its true width: a sequence wraps its items into rows, a grid sizes cells to content, bars keep room for labels and values, steps never wrap. Side-by-side panels flow into the column that ends highest; panels that cannot sit four across go two per row, then stack. Arrows route orthogonally around every other card (straight, through the gap, along a lane, or down a side) or the layout raises; labels appear only where their box overlaps no card.

## Stages

1. Selection (1 call, 1 correction).
2. Digest (1 call, 1 correction).
3. Scene (1 call, up to 2 corrections for validation and coverage). A scene the layout cannot route, or whose panel spans under 40% of its width, gets one more correction.
4. Layout, render, checks. Native checks must be clean and the figure must reach 30 text runs per million square units.

Live runs on 2026-09-18 with deepseek-flash, end to end on commit `1767f89` plus the digest-limit change: Attention in 5 requests, 78,271 tokens, 189 seconds, four panels, density 49 (55 after the reflow fix that followed, re-laid out from the same scene; that render is `docs/attention_figure.png`); PRO in 5 requests, 55,596 tokens, 111 seconds, four panels two by two, density 53; the black-box survey in 5 requests, 71,543 tokens, 335 seconds, three panels, density 48. Every figure passed the native checks. In the Attention figure `softmax((QKᵀ)/√d_k)V` sits inside the scaled dot-product component and `LayerNorm(x + Sublayer(x))` at the layer, where the earlier label plan drew them as a chain.

## Decisions

- The model authors no geometry. Gaps and sizes are rejected by the validator.
- The digest replaces the four-claim narrative for the Overview. `explanation` carries contribution, finding, and qualification from it.
- Density has a floor, not a band. Sparse is the failure mode; the node budget bounds dense.
- Blog figures keep the model-drawn SVG path (`papers/panel_authoring.py`) until their own wave.
- No `drawing` escape hatch until a paper needs one.
- Every provider is asked for low reasoning effort on every request (`Provider.complete(reasoning='low')`), in the vendor's own field, with one retry without it when a model rejects the field. The user asked for this after seeing panels planned with DeepSeek's default, which turned out to be thinking off; the first run with reasoning on recorded 8,310 reasoning tokens on the scene request and finished in 104 seconds.

## Open

- The method digest's running example is not required to appear in the scene; the PRO figure omitted the Russia and Canada values that the reference shows.
- The Blog journey narrative (problem, obstacles, decisions, failures and successes, result) is a separate wave in `papers/agent_overviews.py`.
- Blog figures were verified by unit tests only after `check_panel` and the display-width change.
- 2026-09-24: the five layout defects from the 2026-09-23 audit (mixed-column reflow, stale card height, wrap rounding, arrows along frames and labels on headings, double step numbers) are fixed in `papers/figures/` with regression tests in `tests/test_layout_defects.py`. `docs/attention_figure.png` is re-laid out from the 2026-09-18 Scene. An arrow crosses a group heading only when no other path is clear.
- A Z-route between two cards side by side turns in the middle of the 14-unit gap, so its last segment is about 4 units long and the arrowhead sits on the corner. Panel 1 of `docs/attention_figure.png` shows this for Positional encoding to Scaled dot-product attention. 2026-09-24: a gap an arrow crosses widens to 32 units from the row's spare width; a row with no spare width keeps the 14-unit gap and this defect.
- 2026-09-24: the reader shows the Overview as inline SVG with the Component hover (`docs/superpowers/plans/2026-09-24-inline-overview-figure.md`). The Figure library adds only `data-node` hooks, and `compose` names them once per page, so one hook names one node even when two panels repeat a Scene id. Open: Blog figures still display as images because of their portrait variant, and the dark file stays until `rsvg-convert` is shown to honour CSS `var()` in exports.
- 2026-09-24: the Figure library's node kinds are classes in `papers/figures/nodes.py`, one per kind, each holding its fields, card entry, validation, sizing, and drawing. The Scene dict stays the state; a class is a view over it. Output was byte-identical across the move (`tests/baseline_scenes.py --compare`).
- 2026-09-24: laid out against `docs/reference_images/Attention is all you need.jpeg`, whose Scene is `ATTENTION_EXAMPLE`: a headed group no longer splits into two columns when its parent reflows (the ENCODER and DECODER stacks stay single columns with their arrows running up), a grown row group shares its width with its children, and a row gap an arrow crosses widens. `docs/attention_figure.png` still shows the layout from before these changes; re-lay it out with the native renderer.
