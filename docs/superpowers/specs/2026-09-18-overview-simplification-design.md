# Overview simplification

Status: agreed with the user on 2026-09-18. Later the same day the [Overview scene layout design](2026-09-18-overview-scene-layout-design.md) replaced the Data, Stages, and Composition sections below and the Live result; the model no longer draws panels. Replaces the Overview requirements in the [2026-09-13 rebuild design](2026-09-13-overview-workflow-rebuild-design.md) where they conflict. The cleanup that accompanies it is in [docs/cleanup.md](../../cleanup.md).

## Why

The rebuilt Overview ships in one of two shapes, and readers found both hard to use. When the planner's plan validates, it uses the full seven-panel budget with up to eight content items each, and the composed image runs to 1,000 by 5,900 units. When the plan fails validation, which happened in 11 of 20 live runs, the run falls back to one sentence per narrative claim, and the drawing model invents box-and-arrow geometry for prose. No stage can reduce content. The simplify pass copies content into panels. Every repair remedy grows a box, a font, or the canvas. The checks reject only what is missing.

The target is the older single-figure look: a header, a title, one short subtitle, two to four stacked levels with a few labelled boxes and arrows each, one text size, and a one-line footer.

## Requirements

- The Overview is one image, 960 units wide, with 1 to 4 stacked panels. Three panels is the default. A fourth panel is allowed only when the story cannot be told in three.
- The plan schema bounds content. A panel has at most 12 labels of at most 48 characters, at most 8 relations, and one optional note. The validator rejects excess, never absence beyond the minimum.
- Labels are the exact display text. There are no shared facts, no exact-text substrings, no entry states, and no exit states.
- The drawing prompt carries no size budget. The model draws each panel at the size it chooses, and the application scales the panel to the column width after generation.
- Readability is checked after scaling, at the size the reader sees.
- Repair subtracts before it adds. The excess check fails a panel with more visible words than its assignment supports, and the repair instruction orders removal before enlargement.
- There is no planning fallback and no prose fallback panel. A plan that fails validation twice fails the run. A panel that fails after two repairs fails the run.
- The application draws the header, title, subtitle, panel headings, frames, and footer. The model draws panel bodies only.
- The saved generation keeps its shape. `GENERATION_KEYS`, `PROVENANCE_KEYS`, `FIGURE_ASSET_KEYS`, `provenance.workflow`, `narrative_digest`, `figure_digests`, `figure.checks`, `figure.dimensions`, and `figure.panels[].{x,y,width,height}` stay, because `panel_workflow_figures` and `app.js` read them. `PROMPT_REVISION` changes.
- Blog figures keep their own brief schema and attempt budget. They share the drawing prompt, the label check, the excess check, and the display-scale check.

## Data

### Overview plan

The planner returns this object. `validate_overview_plan` in `papers/explanation.py` enforces every limit.

```
{
  "title": string, 1-80 characters,
  "subtitle": string, 1-160 characters, one sentence on what the figure shows,
  "footer": string, 1-240 characters, one sentence of qualification,
  "illustrative": boolean, true when any label carries a teaching value that is not a paper result,
  "panels": [1-4 of {
    "id": safe identifier,
    "heading": string, 1-60 characters,
    "construction": "flow" | "mapping" | "comparison" | "calculation" | "chart",
    "purpose": string, 1-200 characters, the one idea the panel shows,
    "labels": [2-12 unique strings, 1-48 characters each],
    "relations": [0-8 of {"from": a label, "to": a label, "label": optional string, 1-24 characters}],
    "note": optional string, 1-120 characters,
    "passages": [1 or more retained passage IDs]
  }]
}
```

### Drawing assignment

`panel_assignments` projects each panel into the author-facing assignment. `blog_figure_assignment` projects a Blog brief into the same shape.

```
{
  "id", "heading", "construction", "purpose",
  "labels": [exact display text],
  "relations": [{"from", "to", "label"}],
  "note": optional,
  "content": optional semantic lines (Blog only),
  "story": "title. subtitle" (Overview only)
}
```

### Checks on a returned panel

1. The static `panel` profile in `papers/html_figures.py` is unchanged.
1a. `fit_canvas` grows the viewBox of a drawing whose elements spill past it, with a 16-unit margin, and the panel is rendered again. This is a local resize, not a repair, and costs no request.
2. The native render scales the panel to the display width (920 units for an Overview panel, 640 for a Blog figure) before it measures text. Both axes scale by the same factor, so a narrow panel grows and a wide panel shrinks. `text_too_small`, `out_of_bounds`, and `text_overlap` keep their meaning.
3. `missing_value_details` requires every label verbatim after whitespace normalisation and entity decoding. The search runs over the space-joined text of every visible `text` element, so a label wrapped across `tspan` lines inside one `text` element passes.
4. `excess_text_details` counts visible words in an Overview panel. The budget is 1.5 times the words in labels, relation labels, and the note, plus 12. More words than the budget is a defect whose remedy names removal. Blog figures skip this check because their briefs carry semantic content the author must express in text.
5. `tall_panel_details` fails an Overview panel whose scaled height exceeds 1.25 times its width. The remedy names more columns and fewer rows.

## Stages

1. Paper orientation and evidence selection. Unchanged.
2. Accepted narrative. Unchanged in contract. The prompt asks for at most four teaching steps in `visual_focus`, and the validator enforces the 1200-character field limit.
3. Overview plan. One call with `OVERVIEW_PLAN_INSTRUCTION`, validated by `validate_overview_plan`. One correction call carries the rejected answer and the issue paths. A second rejection fails the run.
4. Panel authoring. `build_panels` runs the panels in parallel. Each panel gets one creation request and at most two repair requests. A repair request carries the previous SVG, the defects, and the rendered PNG when the model accepts images. A panel that still fails ends the run with the defects in the error.
5. Composition. `compose_overview` in `papers/html_figures.py` draws the header, title, subtitle, one frame per panel with a numbered heading chip, the panel body scaled to the 920-unit column, and the footer. Text wraps by measured width.
6. Render and check. `render(mode='overview')` renders the 960-unit canvas at 1:1 and re-runs the native checks.

Call count for a normal run: 1 selection, 1 narrative, 1 plan, 3 panels, so 6. Worst case: 2 selection, 4 narrative, 2 plan, 12 panel requests.

## Delivery order

Each step lands as one commit with its own check. Steps 1 and 2 change no user-visible behaviour. Steps 3 through 5 each replace a stage; between step 3 and step 5 the Overview runs with the new planner and the old composition, which is planned breakage of the image layout, not of delivery.

1. Subtract. Remove `diagram-style.md` from the Blog author prompt and the `legacy` render mode. Check: the commands in `docs/cleanup.md`.
2. Scaffold. Build `papers/html-snapshot`, add the `localxiv-display-width` meta tag to the renderer, and add `tests/test_overview_plan.py`, `tests/test_panel_checks.py`, and `tests/test_compose_overview.py` with fixtures under `tests/fixtures/overview/`. Check: `python3 -m unittest discover -s tests` passes with the renderer built.
3. Plan schema and planner. Land `validate_overview_plan`, `OVERVIEW_PLAN_INSTRUCTION`, the one-correction planner, and the new `panel_assignments`. Delete the old plan schema, validator, passes, and the planning fallback in the same commit. Check: unit tests reject a five-panel plan, a 13-label panel, a 49-character label, and a relation whose endpoint is not a label.
4. Authoring and repair. Land the new `assignment_block`, the label check, the excess check, the subtract-first repair instruction, and the rewritten `papers/panel-guides/authoring.md`. Delete `simple_panel`. Check: unit tests show the excess check firing on a fixture with 40 extra words and the repair prompt listing removal before enlargement.
5. Composition. Land `compose_overview` and the stacked layout. Delete `arrangement.py`, `mixed_fit.py`, `edge_align.py`, and their design docs. Check: a fixture of three panels composes to a 960-wide SVG whose render passes the native checks and whose PNG shows header, three framed panels, and footer.
6. Rename and correct. Generation and job kinds, the narrative length limit, the Blog assignment mismatch, the vision setting label, `CONTEXT.md`, and `README.md`. Check: `grep -rn bento papers app` prints nothing and the app opens a library with migrated rows.
7. Live run. Generate the Overview for the bundled Attention paper with the user's configured provider and inspect the PNG. Replace `docs/attention_figure.png` with it. Done; see Live result.

## Decisions

- Budgets stay out of the drawing prompt. The user removed them after live runs showed models could not hit a page size while drawing. The application scales after generation and checks at display scale instead.
- Three panels by default, four at most. The user's target has three levels.
- No planning fallback. The user chose this: a plan that fails validation twice fails the run.
- No prose fallback panel. This is the implementer's call, not the user's. A panel that fails after two repairs fails the run with its defects, because a prose card presented as a diagram is the "reads as notes" defect the live pilots recorded. The cost is that a run can fail after paying for its planning calls.
- Every panel scales to the column width in both axes. Also the implementer's call. Shrink-only scaling would leave narrow panels small and centred, which is not the target look, and would need a second rule in the renderer beside the Blog rescale.
- The narrative stage stays. Blog reference reuse (`panel_workflow_figures`) and the reader's explanation text depend on it. Merging it into the plan call is a later decision.
- The `overview_vision` setting stays as the declaration that the model accepts images. There is no provider-side detection, so a repair PNG cannot be sent unconditionally.
- DeepSeek drawing requests keep thinking on. The old policy turned it off for latency; the first live run drew each panel in five seconds and failed one panel three times, the second drew each in about fifty seconds and passed all three at the first attempt.

## Live result

2026-09-18, deepseek-flash, the bundled Attention paper: 6 requests, 60,725 tokens, 158 seconds, one 1000 by 2485 canvas with three panels of eight or nine labels each, no repairs. The image is `docs/attention_figure.png`. The first live run, before `fit_canvas` and with thinking off, failed on one panel after two repairs; its second and third attempts each fixed one defect and introduced another.

## Open

- Provenance of `docs/attention_figure.png`. It is replaced in step 7.
