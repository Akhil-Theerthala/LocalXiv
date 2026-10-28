# Mermaid figures design (2026-10-28)

Status: proposed. The spike in `spikes/mermaid-overview/` ran on 2026-10-28. The owner accepted the level of detail in its second run, asked that neither the height nor the width dominate (run 3), asked for result charts (run 4), chose the checked layout, and chose plain images for saved Scene figures. This design replaces the Scene and the Figure library (`papers/figures/`) for the Overview and for every Blog figure. It supersedes the drawing parts of [the 2026-09-18 Figure library consolidation](2026-09-18-figure-library-consolidation-design.md), [the 2026-09-18 Overview scene layout](2026-09-18-overview-scene-layout-design.md), and [the 2026-10-08 Overview story](2026-10-08-overview-story-design.md). The Digest, the Blog narrative, and the Blog outline stay.

## Why

The model writes a Scene: a JSON tree in a private format with 10 node kinds. The model learns that format from one generated card and two examples. The application then lays out panels, routes arrows, measures text in WebKit, and checks density. This design came from an earlier failure: model-drawn SVG passed for only 25 to 55 percent of Blog figures, and its text density measured 13 against a floor of 40.

The Scene fixed that failure, but it sets a hard limit on what a figure can be. Every Overview is a column of 3 to 4 panels with cards, chips, stats, and bars. A paper whose idea is a sequence of messages, a state machine, a timeline, or a flow of quantities cannot get the figure it needs. Each new shape needs a new node kind, more layout code, and a longer card for the model to learn.

Mermaid is a public diagram language that models already know. One Mermaid source gives the model about 30 diagram types and a free layout, with nothing new to learn. [Pele](https://pele.run) renders Mermaid 12.1 to SVG with no runtime dependencies. It runs in Node and in the browser and takes its colours from CSS variables. With Pele, the application stops owning layout. The effort moves to the step that decides what a figure says.

The spike showed where that step must be. When the Digest went straight to the diagram, with a check that every Digest component is drawn, the model drew 18 to 40 nodes and 188 to 280 words. The Digest is complete by design (4 to 24 components), and the Scene had hidden most components as chips. A plan request that chooses at most 7 items cut the diagrams to 9 or 10 nodes and 28 to 64 words.

## Goals

- An Overview is one Mermaid diagram, drawn from a plan that chooses what the first pass needs. The model chooses the diagram type, the layout, and the styling.
- A Blog figure is one Mermaid diagram for each figure brief.
- `papers/figures/`, the Scene format, its prompts and examples, and the Scene checks are removed.
- The application accepts a diagram when it parses, shows the planned items, stays within the caps, and is readable at its target width.

## Non-goals

- Research into how to extract the key information of a paper. The plan request is where that research will go, and it is the next project. That project also decides whether the Digest extracts the baseline numbers that a result chart needs.
- Changing the Digest, the Blog sections, the Section check, the join, Tone, or Blog length.
- Supporting Mermaid diagrams that the reader writes.

## Anti-goals

- A second layout engine. When Pele draws a diagram badly, the fix is a correction message or a prompt change, not application layout code.
- Text density as a gate.
- A private Mermaid dialect. The model writes standard Mermaid 12.1 syntax, so mermaid.js can replace Pele if Pele stops.

## Decisions the owner made

1. The Overview stops being a column of panels. It is one diagram.
2. Density is not a check. A diagram that makes sense and is readable at its dimensions is acceptable.
3. A Blog figure is one Mermaid render for each brief. The model decides what the figure shows.
4. `papers/figures/` and the dependencies that only it needs are removed.
5. Component hover stays for flowchart and block diagrams. Other diagram types have no Component hover.
6. The Overview has a plan request before the diagram, and caps on nodes and label length (the spike's second run).
7. For now, the model styles the diagram freely: markdown bold and italic, and `classDef` and `style` with font sizes, weights, and colours. The application does not limit it to named styles.
8. Neither the height nor the width of the figure dominates (the Shape check).
9. An Overview can have one result chart below its main diagram, when the plan asks for one.
10. The page uses the checked layout (see "Layout on the page").
11. Saved Scene figures show as plain images until the reader regenerates them. The Scene inline-SVG code goes.

## The Overview

Stages: selection, Digest, plan, diagram. The selection and Digest stages are unchanged.

### Plan

The plan request sends the Digest and asks for the reader's first pass: one image a reader understands in about 30 seconds. It returns one JSON object:

```json
{"through_line": "one sentence from the problem to the result",
 "items": [{"name": "a Digest component name, or a phrase of at most 6 words", "why": "..."}],
 "headline_numbers": [{"value": "28.4 BLEU", "measures": "English→German, WMT 2014"}],
 "chart": null}
```

`chart` is null, or `{"type": "bar|line|pie|quadrant|radar", "shows": "...", "values": [["label", number], ...]}`. The plan asks for a chart only when the Digest has at least 3 numbers on one measure that a reader should compare: methods, model sizes, steps, or conditions. Bar compares methods or conditions, line shows a trend along an ordered factor, pie shows shares of one whole, quadrant places methods on two axes, and radar compares methods across 3 or more metrics.

| Check | Rule |
| --- | --- |
| Items | 1 to 7 items, each with a `name` string. |
| Headline numbers | 1 or 2. |
| Chart | Null, or an object whose `type` is one of the five above. |

The plan is saved with the Overview, and the Blog can read it.

### Diagram

The diagram request sends the plan and the Digest, and asks for one JSON object:

```json
{"title": "...", "subtitle": "...", "footer": "...", "illustrative": true, "mermaid": "flowchart TB\n  ...",
 "chart": "xychart\n  ..." or null}
```

`title`, `subtitle`, and `footer` keep their meaning and their limits from the Scene. The page and the exports draw them as text around the diagram.

The prompt tells the model to draw the plan and nothing else: its through-line, its items in order, and its headline numbers. It names the diagram types that suit each paper type. It invites free styling, for example large bold headline numbers and a strong colour for the paper's idea. It gives the syntax for bold and italic: a Mermaid markdown string, ``A["`**28.4 BLEU** on WMT 2014`"]``. In a plain label, asterisks show as asterisks. The prompt in `spikes/mermaid-overview/generate.py` is the starting point.

The application accepts the object when every check below passes. A failed check returns its exact message in the existing correction loop of `request_validated`, with at most 3 requests for the stage. Stage retry stays as it is.

| Check | Rule |
| --- | --- |
| Parse | Pele parses the source. On failure, the correction message is the `PeleError` message. |
| Type | The diagram type is one that Pele supports. The model can use any of them. |
| Coverage | Every plan item `name` appears in the diagram's label text. |
| Nodes | At most 12 nodes. |
| Labels | At most 8 words in a node label, and no literal asterisk in a drawn label. |
| Readable | At the target width, the smallest text draws at 11 units or larger. |
| Shape | Width divided by height of the whole figure, with its result chart, is from 0.6 to 1.4. The correction message says which way the figure is too long and how to fold it. |
| Size | The source is within Pele's limits. |

Coverage compares label text after whitespace and case normalisation, and without backticks and the `$$` math delimiters.

The Readable check uses the `width` and `height` that Pele returns at the target width: 1000 units for the Overview and 640 for a Blog figure. The smallest text is the smallest `font-size` in the SVG, or 16 when the diagram sets none. If the diagram must shrink to fit, that size is multiplied by the shrink factor.

The Shape check uses Pele's natural `width` and `height`. The three reference figures in `docs/reference_images/` measure 0.60 to 1.06. A literal asterisk in a drawn label means the model wrote markdown in a plain label, or a `*` in a markdown string turned part of a label into italics (for example `p*₁ ≥ p*₂`).

The caps (7 items, 12 nodes, 8 words) and the numbers (11 units, 0.6 to 1.4) come from the spike. Change them from live runs.

### Result chart

One Mermaid source is one diagram type, so a flowchart cannot hold a chart. When the plan has a chart, the model writes it as a second Mermaid source in `chart`: `xychart` (bar or line), `pie`, `quadrantChart`, or `radar-beta`, with the plan's values and a short title. When the plan's chart is null, `chart` is null. The main diagram still shows the headline numbers.

The application sets the chart's size, not the model. It renders the chart with `config: {xyChart: {width: W, height: 280}, quadrantChart: {chartWidth: min(W, 280), chartHeight: 280}}`, where W is the drawn width of the main diagram. A pie or a radar keeps Pele's natural size. The page, the dialog, and the exports draw the chart 24 units below the main diagram, inside the same frame.

| Check | Rule |
| --- | --- |
| Chart present | When the plan has a chart, `chart` is a string. |
| Chart parse | Pele parses the chart source. |
| Chart type | `xychart`, `pie`, `quadrantChart`, or `radar`. |
| Chart readable | The chart's smallest text draws at 11 units or larger. |

The Shape check covers the whole figure: width is the larger of the two widths, and height is the main diagram's height plus 24 plus the chart's height.

### Notation

The Digest and the Blog brief keep `NOTATION` (Unicode, `d_k`, `W^Q`). `NOTATION` moves from `papers/figures/schema.py` to `papers/explanation.py`. In a diagram label, the model writes a name as the plan wrote it. It can write an equation as `$$TeX$$`, which Pele typesets. In the spike the model used no `$$` in 6 diagrams: it wrote equations such as `softmax(QKᵀ/√d_k)V` as plain text.

## Blog figures

The Blog outline still plans the figures and writes one brief for each. The brief is the plan of its figure. The section writer still puts the `{{figure:figN}}` marker in its section. Each figure is still one request plus at most `MAX_FIGURE_CORRECTIONS` corrections. A figure that fails all of them becomes an Omitted Blog figure.

The brief keeps `id`, `title`, `purpose`, `entry_context`, `exit_state`, `content`, `illustrative_values`, `caption`, `paper_connection`, `illustrative`, and `passages`. `exact_text` is removed. The model returns `{"id": ..., "mermaid": ...}` and styles freely, as in the Overview. The figure gets the Parse, Type, Labels, Readable, Shape, and Size checks at 640 units, and a Coverage check over the brief's `illustrative_values`, so the values in the figure match the values in the prose.

## Rendering

The source of truth for a figure is its Mermaid text. The saved Overview and Blog keep it in the figure record as `mermaid`, and an Overview's result chart as `chart`.

| Where | How |
| --- | --- |
| Checks during generation | A Node script, `papers/mermaid.js`, beside `papers/math.js`. It reads the source and the target width from stdin. It writes the parse result, the diagram type, the label text, each node's ID and text, the smallest font size, `width`, `height`, and the SVG to stdout. The release already bundles Node. `spikes/mermaid-overview/render.mjs` is the starting point. |
| The page | The vendored Pele browser build renders the source into the figure's place. Pele's CSS variables take their values from the Figure palette, so one render follows the reader's theme. Math labels use the page's local MathJax as Pele's `math` resolver. It uses the checked layout below. |
| The figure dialog | The same render at its full size, with Pele's zoom. |
| PNG and PDF | During generation, html-snapshot loads an HTML page with the light palette, the title, the subtitle, the footer, the Node SVG, and the result chart's Node SVG when there is one, and writes the PNG and the PDF. Kindle, PDF, and PNG exports read these files, as they do now. |

Render options are `links: false` and `images: false`. Pele escapes label text and filters styles. The page CSP stays `default-src 'self'`, and `style-src` already allows inline styles, so the Pele build is a file in `app/static/`, not a CDN script.

The Pele CSS variables are `--pele-bg`, `--pele-fg`, `--pele-muted`, `--pele-line`, `--pele-surface`, `--pele-surface-alt`, `--pele-border`, `--pele-accent`, `--pele-radius`, `--pele-font`, and `--pele-font-mono`.

### Fixed colours in the dark theme

The model's `classDef` and `style` colours are fixed hex values. They do not follow the reader's theme, so in the dark theme a styled node keeps its light-theme colours. This is accepted for now (decision 7). Revisit it when the owner reviews dark-theme figures.

## Component hover

For flowchart and block diagrams, the hover keeps its current behaviour. A drawn node whose label contains a Digest component name gets that component's fields. The longest matching name wins, as in `component_hooks` now. Pele draws each node as `<g class="pele-node …" data-id="<Mermaid ID>">`, and the page finds the node through it. A click opens the Paper at the component's first passage.

Other diagram types draw with no Component hover.

## What is removed

- `papers/figures/` (10 files, about 2,700 lines).
- The Scene prompts, `ATTENTION_EXAMPLE`, `VARIETY_EXAMPLE`, `PANEL_EXAMPLE`, and `PANEL_WRAPPER`.
- The Scene checks in `papers/explanation.py`: `scene_coverage_issues`, `example_coverage_issues`, `example_structure_issues`, `series_text_issues`, `story_issues`, `focus`, `digest_requirements`, and `blog_panel_required`.
- The `measure` mode of `papers/HTMLSnapshot.swift`. The snapshot mode stays for PNG and PDF.
- The layout correction (`scene_layout`, `figure_*_layout`), `MIN_TEXT_DENSITY`, `MIN_PANEL_FILL`, and the detour warning.
- `tests/relayout_saved_scenes.py`, `tests/test_figure_layout.py`, and the tests that import `papers.figures`. The import in `app/macos/verify-release.py` changes to a Mermaid render.
- The Overview panel outline, the "N panels" provenance, and the 1–9 panel keys in the figure dialog.
- The inline-SVG path for Scene figures in `app/static/reader.js`, with the code that cuts the `LOCALXIV ·` line (see "Saved Overviews and Blogs").

## What is added

- `pele` 1.12.0, pinned exactly, in `package.json`, and its browser build in `app/static/`. Its MIT licence goes in `docs/dependency-licenses.md`.
- `papers/mermaid.js`, and one small Python function that calls it, in the place of the `Figure` class.
- The plan request and its checks in `papers/overview_workflow.py`.

## Saved Overviews and Blogs

A saved figure with `mermaid` renders through Pele. A saved figure without `mermaid`, from the Scene, shows its stored PNG as a plain image, with the dark SVG in the dark theme when it has one. It has no Component hover, and it shows its `LOCALXIV ·` title line. The reader regenerates the Overview or the Blog to get a Mermaid figure. No migration runs.

So the inline-SVG path for Scene figures in `app/static/reader.js` goes: `inlineFigure`, the `[data-node]` annotation of the Scene SVG, and the code that cuts the title line. The Mermaid figure has its own render and its own Component hover.

## Export Editable SVG

The menu item stays. The exported SVG contains a `<style>` element that sets the Pele CSS variables to the light palette, so the file draws correctly outside the page.

## Domain language

`CONTEXT.md` changes with this design:

- **Overview**: one Mermaid diagram, with a title, a subtitle, a footer, and an optional result chart below it, drawn from the Overview plan. It tells why the work was needed, how it works, and what it achieved.
- **Overview plan**: new. The through-line, at most 7 items on the mechanism's path, 1 or 2 headline numbers, and an optional result chart, chosen from the Digest for the first pass.
- **Blog figure brief**: loses `exact_text`.
- **Scene**, **Scene layout**, **Scene math**, **Scene correction**, **Overview panel**, **Chip**, **Stat**, **Figure library**: removed.
- **Figure render**: the Pele render of a figure's Mermaid source.
- **Diagram check**: new. The Parse, Type, Coverage, Nodes, Labels, Readable, Shape, and Size checks above, and the four result chart checks.

## Spike results (2026-10-28)

The spike used the saved Digests of the three Papers in `docs/reference_images/`, on `claude-opus-5-5` at medium reasoning.

Run 1 (no plan; every Digest component required; the prompt asked for dense labels):

| Paper | Requests | Nodes | Words | Natural size |
| --- | --- | --- | --- | --- |
| Attention Is All You Need | 2 | 21 | 229 | 1142 × 1964 |
| Probabilities Are All You Need (PRO) | 3 | 18 | 188 | 893 × 1278 |
| Black-box uncertainty estimation evaluation | 2 | 40 | 280 | 1286 × 2043 |

The owner found run 1 over-detailed.

Run 2 (plan, caps, free styling):

| Paper | Requests (plan + diagram) | Nodes | Words | Natural size | Smallest text |
| --- | --- | --- | --- | --- | --- |
| Attention Is All You Need | 1 + 1 | 9 | 58 | 560 × 1289 | 14 |
| Probabilities Are All You Need (PRO) | 1 + 2 | 9 | 64 | 734 × 983 | 13 |
| Black-box uncertainty estimation evaluation | 1 + 1 | 10 | 28 | 958 × 572 | 13 |

The owner accepted the detail of run 2, but not its shapes: Attention was 0.43 (a tall strip) and the survey 1.67 (a wide band).

Run 3 (this design: run 2 plus the Shape check and the markdown-string syntax):

| Paper | Requests (plan + diagram) | Nodes | Words | Natural size | Shape |
| --- | --- | --- | --- | --- | --- |
| Attention Is All You Need | 1 + 3 | 9 | 60 | 818 × 910 | 0.90 |
| Probabilities Are All You Need (PRO) | 1 + 2 | 8 | 54 | 730 × 786 | 0.93 |
| Black-box uncertainty estimation evaluation | 1 + 1 | 9 | 48 | 987 × 723 | 1.37 |

Attention used all 3 diagram requests: its first two drafts were too tall (0.37, then 0.50). In an earlier run 3 without the markdown-string syntax, the model wrote `**bold**` in plain labels, and the asterisks showed; that is why the prompt gives the syntax and the Labels check rejects literal asterisks.

Run 4 (this design: run 3 plus the result chart):

| Paper | Requests (plan + diagram) | Plan's chart | Figure size | Shape | Accepted |
| --- | --- | --- | --- | --- | --- |
| Attention Is All You Need | 1 + 3 | none | 538 × 854 | 0.63 | no: one label had 9 words after 3 requests |
| Probabilities Are All You Need (PRO) | 1 + 2 | bar: average AUC of PRO, NLL, and semantic diversity | 736 × 1141 (diagram 736 × 837, chart 736 × 280) | 0.65 | yes |
| Black-box uncertainty estimation evaluation | 1 + 2 | none | 754 × 676 | 1.12 | yes |

The plan chose a chart only for PRO. The Attention Digest has two result numbers and no baseline scores, and the survey's source gives rankings only, so the 3-number rule left them without a chart. The Scene Overview of Attention had a bar chart of baselines, but its values came from the prompt's example, not from the Digest. In the live workflow, the Attention failure gets one Stage retry.

Every Mermaid source parsed on its first request in all runs. The model chose a flowchart with subgraphs for all three Papers, including the survey. In run 2 it used `classDef` and `style` in every diagram, for example large bold headline numbers on a green fill.

Facts confirmed with Pele 1.12.0:

1. Each flowchart node is `<g class="pele-node …" data-id="<Mermaid ID>">`.
2. Pele's Node width table is within about 2% of WebKit: 1142, 893, and 1286 against 1161, 902, and 1296 in the page.
3. A `math` resolver with `mathjax-full` 3.2.2 typesets `$$…$$` in Node and in the page.
4. Bold and italic in labels, and `font-size`, `font-weight`, `fill`, and `color` in `classDef` and `style`, render, and Pele sizes each box to its text.

## Layout on the page

The page, the figure dialog, and the exports show the checked layout: the layout the Diagram checks measured. Pele renders with `autoDirection: false` and `maxWidth` set to the target width (1000 for the Overview, 640 for a Blog figure), and the SVG scales down to fit a narrower container. So the on-screen figure and every export are the same figure, and the `CONTEXT.md` rule about that stays.

A narrow pane shrinks the figure. The figure dialog shows it at full size with Pele's zoom, and Enlarge stays on the inline figure.

The spike compared this route with a relayout at each container width (`mount()`). At 390 px both routes drew text at 4.3 to 6.2 px in run 1: Pele shrank the flowcharts with subgraphs and did not rearrange them. So a relayout gave almost no gain and cost the same-figure rule.

## Left to the builder

- The final prompt text for the plan, the Overview diagram, and the Blog figure.
- The list of diagram types the prompt suggests for each paper type.
- A node cap and a Shape range for Blog figures, from the first live runs. A Blog figure can itself be a chart type.
- A rule for the chart's value axis. In run 4 the bar chart's axis started at 0.68, which makes a 0.03 AUC difference look large.
- The base font size of the render.
