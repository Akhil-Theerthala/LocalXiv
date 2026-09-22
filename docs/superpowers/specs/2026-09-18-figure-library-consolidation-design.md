# Figure library consolidation

Status: implemented on 2026-09-18 on the branch `figure-library-consolidation`. Builds on the [Overview scene layout design](2026-09-18-overview-scene-layout-design.md) and replaces the drawing sections of the 2026-09-14 Blog workflow update design (deleted; at commit 6e2533d). The cleanup that accompanies it is in [docs/cleanup.md](../../cleanup.md).

## Why

LocalXiv draws figures two ways. The Overview has the model author a Scene and the application lay it out. A Blog figure has the model draw SVG, which the application measures and sends back for repair up to three times. In the 2026-09-14 pilots, 25 to 55 percent of planned Blog figures were accepted. The Overview path produced three figures on 2026-09-18 in five requests each, all passing the native checks. Two paths for one product means two prompts, two check sets, two repair policies, and two places to fix a defect.

The figure code is also spread out. `papers/scene_layout.py` lays out, `papers/explanation.py` validates the Scene next to the Blog schemas, `papers/html_figures.py` renders next to the model-drawn SVG sanitizer, and `papers/agent_overviews.py` is one 1,606-line function that reimplements the request, checkpoint, and trace helpers that `papers/overview_workflow.py` already has as `Coordinator`, `RunStore`, and `_request_validated`.

The model must learn the drawing vocabulary from the prompt alone. A new model has never seen this library, so the author-facing contract has to fit a few thousand tokens and stay one source of truth with the validator.

## Goal

Every figure LocalXiv generates, Overview or Blog, has the density and style of the three figures in `docs/reference_images/`. Their content is not a target. Those figures may contain scientific mistakes, and the digest and evidence checks own correctness.

The style is fixed by the layout constants: 14-unit body text, 15-unit headings, 26-unit title, the paper palette in `TONES`, cards with a bold label and a muted detail, framed panels with a heading chip, and a footer. The density is measured. The references measure 42 to 64 text runs per million square units. The three 2026-09-18 Overview runs measured 48, 49, and 53. The floor rises from 30 to 40 in this design.

## The library

`papers/figures/` is one package with one public class. It knows nothing about papers, prompts, providers, digests, or briefs.

```
papers/figures/
	__init__.py    exports Figure, FigureResult, SceneError
	schema.py      typed node kinds, validate(), card(), json_schema()
	measure.py     Measurer protocol, the WebKit measurer, a fixed-width stub for tests
	layout.py      sizing, rows and columns, reflow, justification, panel flow
	route.py       arrow routing around obstacles, edge labels
	render.py      laid-out tree to SVG, with or without the page frame
	checks.py      native checks, density, required strings
```

### The `Figure` class

```python
figure = Figure(measurer, width=1000)            # or width=640 for a Blog figure
figure.validate(scene)                           # raises SceneError with issue records
figure.missing(scene, required)                  # strings absent from the scene text
figure.headings(scene)                           # every panel and group heading
result = figure.build(scene, directory, frame='page', page_title=paper_title)
result.svg, result.png, result.pdf, result.checks, result.density, result.issues
```

`validate` raises `SceneError` with the same issue records `validate_scene` produces today. `missing` and `headings` are the two views a caller needs for coverage before it spends a render. `build` lays out, renders, and checks, and raises `SceneError` when an arrow cannot be routed. Nothing in the class calls a provider. A caller that wants a correction reads the issues and asks its own model.

`frame='page'` is the Overview: header line, title, subtitle, panels, footer. `page_title` is the paper title on the header line. `frame='panel'` is a Blog figure: one panel with its heading chip and nothing else, and `page_title` is not accepted. The article carries the caption.

`width` is the layout width in units, and text is never scaled. A Blog figure lays out at 640 units so its 14-unit labels display at the size the reader sees. Today `WIDTH = 1000` is a module constant and a Blog figure would have to scale, which recreates the `text_too_small` defect this design removes.

`missing` and `headings` replace `scene_coverage_issues`, which is digest-shaped. The Overview passes every component name and `computes` string to `missing`, and keeps its containment rule, that a digest component with two or more parts of its own is a group or panel heading, as its own check over `headings`. That rule is what put `softmax((QKᵀ)/√d_k)V` inside the scaled dot-product component instead of after it, and it stays in `OverviewWorkflow`. The Blog passes every `exact_text` and `illustrative_values` string from the brief. The library compares after whitespace normalisation.

### The measurer

`Measurer` stays an injectable object. Production uses the WebKit measurer that `papers/scene_layout.py` has today, because layout widths must match the renderer's text shaping. Unit tests use a stub with fixed per-character widths. Measuring with Pillow is not part of this design. If it is wanted later, it lands as its own unit with a measured tolerance against WebKit.

### The author-facing card

`schema.card()` returns the text a model reads before it authors a Scene. `schema.json_schema()` returns the structured-output schema. Both are generated from the node definitions in `schema.py`, so the card, the schema, and the validator cannot drift. Today the card is `SCENE_INSTRUCTION` in `papers/overview_workflow.py`, hand-written beside the limits in `papers/explanation.py`.

Measured on 2026-09-18 with `len(text) // 4` as the token estimate:

| Part | Characters | Tokens |
| --- | --- | --- |
| Card without examples | 4,357 | 1,089 |
| Architecture example | 4,399 | 1,099 |
| Method example | 2,008 | 502 |
| Full instruction | 10,764 | 2,691 |

Budget: the card stays under 1,200 tokens. A request carries one example, chosen by the caller for its purpose, so a request is under 2,400 tokens. The card has two parts. The vocabulary part lists the node kinds, their fields and limits, and the edge rule, and both workflows send it unchanged. The wrapper part says what object to return, and each workflow supplies its own: the Overview asks for title, subtitle, footer, layout, and 1 to 4 panels; the Blog asks for one panel.

Regenerate the table with:

```sh
python3 -c "from papers.figures import schema; print(len(schema.card()))"
```

### Vocabulary

The eight node kinds stay as they are: `card`, `group`, `note`, `sequence`, `grid`, `steps`, `bars`, `divider`. Two additions land after the refactor, each as its own unit.

Panel edges. Both the PRO and the survey reference figures draw an arrow from one panel to the next. Today an edge joins cards of the same panel only. `scene.edges` gains entries `{"from": panel id, "to": panel id}` between adjacent panels of a `columns` scene, drawn as one horizontal arrow in the panel gap at mid-height.

Chart. A `chart` node draws a line or scatter plot: `{"kind": "chart", "series": [1-4 of {"label" ≤28, "points": [2-12 of [x, y]]}], "x_label"? ≤24, "y_label"? ≤24, "caption"? ≤90}`. The library draws axes, ticks, and a legend at 14-unit text. This is the only chart form beyond `bars`. Vega-Lite and every other chart grammar were considered and rejected because they bring a renderer and a look that does not match the references.

The Blog construction families map onto the vocabulary and stop being a field:

| Family | Scene form |
| --- | --- |
| flow | a group with edges |
| mapping | a row of two column groups with edges across |
| comparison | a row of two headed groups |
| calculation | `steps`, or `sequence` with `grid` |
| chart | `bars` or `chart` |

## The workflows

Two workflow classes call `Figure`. Neither names a coordinate.

`papers/coordinator.py` holds `Coordinator`, `RunStore`, `create_run_directory`, `provider_options`, `is_transient`, and `request_validated`, moved out of `papers/overview_workflow.py` unchanged. `request_validated` keeps its correction pattern: the rejected answer goes back as an assistant message with the issue paths.

`OverviewWorkflow` in `papers/overview_workflow.py` runs selection, digest, and the Scene request, then `Figure(width=1000)`: `validate`, `missing` with the digest strings, the containment rule over `headings`, and `build(frame='page', page_title=paper title)`. Its stages, corrections, and saved shape are the ones in the scene layout design.

`BlogWorkflow` in `papers/blog_workflow.py` replaces `papers/agent_overviews.py`. It runs on the same coordinator.

Today the Blog is not a sequence of requests. `papers/agent_overviews.py` runs selection, narrative, authoring, and review as a smolagents `ToolCallingAgent` with a read tool, an index tool, a reference tool, and one submit tool per stage. `request_validated` carries no tools. `BlogWorkflow` therefore changes how the prose stages talk to the model, not only how figures are drawn. Each stage becomes one direct structured request with the rejected-answer correction, and supplemental reading goes through `supplement_evidence`, as the Overview has done since the 2026-09-13 rebuild. `smolagents` then has no caller under `papers/` and stays only in `app/macos/verify-release.py`. The alternative, tool-request support in the coordinator as its own unit, keeps the agent loop and the second request path it needs. This design takes the direct-request route. It is the one change here that reaches beyond figures, and it needs the user's confirmation before unit 4.

The Blog's reference admission of an existing Overview, `panel_workflow_figures` and `reusable_overview_figures`, validated the old Overview's SVG. It reads the saved `plan` digest and the run's `scene.json` instead. `validate_candidate` and `overview_word_counts` have no caller outside the deleted module and go with it.

Its stages:

1. Selection, with bibliography filtering at every boundary. Unchanged.
2. Narrative. Unchanged.
3. Article and briefs. One authoring request returns cited Markdown and zero to three briefs. A brief keeps `id`, `title`, `caption`, `passages`, `purpose`, `illustrative`, `content`, `exact_text`, and `illustrative_values`. It loses `construction` and `layout_intent`, because `arrange` in the Scene says the same thing in the model's own object.
4. One panel request per brief, carrying the vocabulary card, the Blog wrapper, one example, and the brief. Then `Figure(width=640)`: `validate`, `missing` with `exact_text` and `illustrative_values`, and `build(frame='panel')`.
5. Corrections per figure follow the Overview rule: up to two for validation and required strings, one more when the panel cannot be routed or is too sparse. One request plus three corrections is the same ceiling as today's four attempts. A figure that still fails is omitted, and the omission cleanup, `remove_omitted_markers` and `apply_text_edits`, moves into `BlogWorkflow` unchanged.
6. Review. A review finding on a figure becomes one more Scene correction with the finding as the reason, inside the same ceiling. Today it triggers a redraw.

## Deletions

Each item names its check. The run is recorded in [docs/cleanup.md](../../cleanup.md).

- `papers/panel_authoring.py`, `papers/panel-guides/`, and `papers/agent_overviews.py`. `papers/blog_figures.py` goes too, after `remove_omitted_markers` and `apply_text_edits` move into `papers/blog_workflow.py`. Check: `grep -rn "panel_authoring\|blog_figures\|panel-guides\|agent_overviews" papers app tests` prints nothing.
- In `papers/html_figures.py`: the model-drawn SVG profiles, `normalize_svg`, `svg_visible_text`, `sanitize`, `fit_canvas`, `with_shared_markers`, the `panel` render mode, `BLOG_DISPLAY_WIDTH`, and `measure_text_widths` after the measurer moves. The native render call and `SHARED_MARKERS` move into `papers/figures/render.py`, which keeps one well-formedness check on its own output. No module outside the deleted ones calls the sanitizer or the profiles (checked on 2026-09-18 with `grep -rn "normalize_svg\|sanitize\|svg_visible_text" app papers`), and the reader serves saved figure assets as files, so old figures do not pass through them. Check: `test -e papers/html_figures.py` fails.
- In `papers/explanation.py`: `validate_scene`, the `SCENE_*` constants, `PANEL_CONSTRUCTION_FAMILIES`, `blog_figure_assignment`, and the `construction` and `layout_intent` fields of `BLOG_BRIEF_SCHEMA`. Keep `scene_coverage_issues`, which checks that the Scene covers the Digest. Check: `grep -n "SCENE_\|construction\|layout_intent" papers/explanation.py` prints nothing.
- In `papers/overview_workflow.py`: `SCENE_INSTRUCTION` and the coordinator classes after they move. Keep `ATTENTION_EXAMPLE` and `VARIETY_EXAMPLE`; the Scene request selects one by paper type. Check: `grep -n "SCENE_INSTRUCTION\|class Coordinator\|class RunStore" papers/overview_workflow.py` prints nothing.
- `PROVENANCE_KEYS` loses `svg_profile_revision`. Saved generations that carry it still load.

## Compatibility

`GENERATION_KEYS`, `FIGURE_ASSET_KEYS`, `figure.checks`, `figure.dimensions`, and `figure.panels[].{x,y,width,height}` keep their shape, because `app/static/app.js` reads them and saved generations carry them. Saved Blogs and Overviews from every earlier revision display and export without regeneration. `PROMPT_REVISION` changes for both workflows so an old context cannot be mistaken for a new one. Export paths for SVG, PNG, PDF, and EPUB are unchanged. A Blog figure's editable SVG is the library's own output, the same as the Overview's.

## Migration

Every unit ends with a check that passes before the next unit starts. The suite in this checkout is five files: `test_panel_authoring`, `test_panel_checks`, `test_provider_reasoning`, `test_scene_layout`, and `test_scene_schema`. The Blog coordinator has no tests here, so unit 3 writes them before unit 4 touches it.

1. Extract `papers/figures/` from `scene_layout.py`, `explanation.py`, and `html_figures.py` with no behavior change. The inputs are the `scene.json` files under `~/Library/Application Support/LocalXiv/library/papers/<paper>/reader/overview-figures/<run>/` (five runs over three papers on this machine on 2026-09-18) plus `ATTENTION_EXAMPLE` and `VARIETY_EXAMPLE`. Check: `compose_scene` output for each is byte-identical before and after, and the five test files pass. Compare the composed SVG, not `render` output, which carries a `uuid4` path and wraps a PNG.
2. Extract `papers/coordinator.py` from `overview_workflow.py` and turn the Overview stages into `OverviewWorkflow`. Check: the same three scenes and the same tests, plus one fake-provider run of `OverviewWorkflow` end to end.
3. Write fake-provider tests for the Blog coordinator as it is: draft, briefs, one accepted figure, one omitted figure with cleanup, one review finding. The fake answers at `Provider.complete`, including the tool calls the agent loop makes. These are characterization tests. Check: they pass against `papers/agent_overviews.py`.
4. Write `BlogWorkflow` on the coordinator with Scene panels. Port the unit 3 tests to it, with the figure stage replaced by a canned panel object. Delete the model-drawn SVG path. Check: the deletion greps above print nothing, and every test passes.
5. Generate the card from the schema, and delete `SCENE_INSTRUCTION`. Check: the card is under 1,200 tokens by the command above, and the fake-provider runs still pass.
6. Add panel edges, then the chart node, then raise the density floor to 40 for `frame='page'`. Each with its own layout and schema tests. Check: the three reference scenes still route, and a scene with a chart renders through the native helper with no issues.
7. Live pilot. The Overview on the three reference papers and the Blog on LoRA (`2106.09685v2`) and Mamba (`2312.00752v2`). Report separately: figures accepted with zero, one, two, or three corrections; density per figure; Blogs delivered. A delivered Blog after an omission is a recovered article, not an accepted figure.

## Terms

Proposed `CONTEXT.md` changes, to apply with unit 4:

- Retire Drawing assignment and Blog drawing brief. Add Blog figure brief: the article author's assignment for one Blog figure, with its purpose, content lines, exact text, and illustrative values, from which the model authors one Scene panel.
- Omitted Blog figure: a planned figure whose Scene still fails after one request and three corrections.
- Overview composition becomes Figure render: a laid-out Scene rendered as one SVG document by the figure library, with or without the page frame.
- Add Figure library: `papers/figures/`, the one path from a Scene to SVG, PNG, PDF, checks, and issues, used by the Overview and every Blog figure.

## Decisions

- The model authors no geometry, in either workflow. Excalidraw, TikZ, matplotlib, Mermaid, D2, and raw HTML were considered on 2026-09-18 and rejected. Each either puts coordinates back in the model's hands or renders a look that is not the reference look.
- Text is never scaled after layout. Width is a layout input.
- One coordinator. The Blog adopts the Overview's request, checkpoint, and correction machinery instead of its own closures.
- The vocabulary grows by two kinds and no more until a paper needs another. A `drawing` escape hatch is still out.
- The library is an internal package under `papers/`, not a published one.

## Open

- Whether the Blog's `content` lines stay in the brief or fold into `required` strings. Decide after the unit 3 characterization tests show how the author uses them.
- Whether a Blog figure may use `columns` with two panels. This design allows one panel.
- The density floor for `frame='panel'`. No single 640-unit panel has been measured. The floor applies to `frame='page'` until the unit 7 pilot reports panel densities.
