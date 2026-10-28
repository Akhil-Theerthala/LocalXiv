# Mermaid figures Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Scene and the Figure library with Mermaid diagrams that the model writes and Pele renders, for the Overview and for every Blog figure.

**Architecture:** A Node script (`papers/mermaid.js`) parses and renders one Mermaid source with Pele and reports what the checks need. A small Python module (`papers/diagrams.py`) calls it, runs the Diagram checks, and writes the PNG, the PDF, and the editable SVG through html-snapshot. The Overview gets a plan stage before its diagram stage. The page renders the saved Mermaid source with the vendored Pele browser build in the checked layout. `papers/figures/` is removed last.

**Tech Stack:** Python 3.14 (`unittest`), Node with `pele` 1.12.0 and `mathjax-full` 3.2.2, ES modules with no build step, Swift (`papers/HTMLSnapshot.swift`).

**Spec:** [docs/superpowers/specs/2026-10-28-mermaid-figures-design.md](../specs/2026-10-28-mermaid-figures-design.md). The spike that the spec measures is in `spikes/mermaid-overview/` (not committed): `render.mjs`, `generate.py`, and the run outputs in `out-v4/`.

## Global Constraints

- `pele` is pinned to exactly `1.12.0` in `package.json`. The browser build is `node_modules/pele/dist/pele.global.js`, copied to `app/static/pele.global.js`.
- Render options for every diagram: `autoDirection: false`, `links: false`, `images: false`, `maxWidth` = the target width.
- Target widths: 1000 units for the Overview, `BLOG_DISPLAY_WIDTH` (640) for a Blog figure.
- Overview plan: 1 to 7 items, 1 or 2 headline numbers, `chart` null or a type in `bar`, `line`, `pie`, `quadrant`, `radar`.
- Overview diagram: at most 12 nodes; Overview and Blog: at most 8 words per node label, no literal `*` in a drawn label, smallest text ≥ 11 units after the shrink to the target width, width ÷ height of the whole figure from 0.6 to 1.4.
- Result chart: Mermaid types `xychart`, `pie`, `quadrantChart`, `radar`. Its size is set by the application: `{xyChart: {width: W, height: 280}, quadrantChart: {chartWidth: min(W, 280), chartHeight: 280}}`, W = the drawn width of the main diagram; it sits 24 units below the main diagram.
- Every correction message is exact text the model can act on. The stage keeps at most 3 requests; Stage retry is unchanged.
- The saved Overview's `plan` key stays the Digest: the Blog reads components from it (`BlogWorkflow.basis_of`). The Overview plan is saved as `overview_plan`.
- A saved figure without `mermaid` shows as a plain image. No migration.
- Commit messages carry no AI attribution line. Merge to `main` with `git merge --no-ff`.
- Run `uvx ruff check .` before each commit that changes Python. Tests: `.venv/bin/python -m unittest discover -s tests` (tests are git-ignored; keep them under `tests/`).

## Review Focus

1. **A model writes a `click` statement or an `%%{init}%%` directive.** A `click A href "javascript:alert(1)"` must draw with no link, and an init directive must not change the render width. Test in Task 2.
2. **A label carries markup** such as `<img src=x onerror=alert(1)>` or `<script>`. Pele must escape it; the saved SVG and the page must contain no live element. Test in Task 2.
3. **Node is missing** on a development machine. Generation must fail with "Install Node.js to draw figures." and publish no partial Overview. Test in Task 4.
4. **Broken TeX in a label** (`$$\frac{$$`). The MathJax resolver must return nothing, so Pele shows the TeX source and the render does not fail. Test in Task 2.
5. **The reader changes the theme** with a Mermaid figure open. The figure must follow through the CSS variables with no new fetch, and a saved Scene figure must swap its light and dark image as today. Browser check in Task 6.

---

### Task 1: Move the shared validation code out of `papers/figures/`

`papers/explanation.py`, `papers/coordinator.py`, and `papers/blog_workflow.py` use Scene-package code for all validation. Move it first, so later tasks can delete the package.

**Files:**
- Modify: `papers/explanation.py:7-8` (imports) and its definitions
- Modify: `papers/overview_workflow.py:16-18`, `papers/blog_figures.py:10-11`, `papers/blog_workflow.py:25`, `papers/blog_prompts.py:10`
- Modify: `papers/coordinator.py` (only if it names `SceneError`)

**Interfaces:**
- Produces, in `papers/explanation.py`: `class ValidationError(ValueError)` with the same constructor and `.issues` (a list of dicts with `path` and `message`) as `SceneError` in `papers/figures/schema.py:8`; `NOTATION` (the text of `schema.py:107`); `_flatten_text`, `_check_text`, `_identifier`, `_panel_error`, `_subtree`, `PANEL_ID_RE` (moved unchanged from `papers/figures/nodes.py` and `schema.py`).

- [ ] **Step 1: Run the suite before the change** — `.venv/bin/python -m unittest discover -s tests`. Note the result; this task changes no behaviour, so the same tests must pass after it.
- [ ] **Step 2: Move the definitions** into `papers/explanation.py`, rename `SceneError` to `ValidationError` at every user outside `papers/figures/`, and import `NOTATION` from `papers.explanation` in `blog_prompts.py` and `overview_workflow.py`. `papers/figures/` imports these names back from `papers.explanation`, so it keeps working until Task 7.
- [ ] **Step 3: Run the suite** — same command. Expected: the same result as Step 1.
- [ ] **Step 4: Commit** — `git commit -m "Move the shared validation code out of the Figure library"`

### Task 2: Render and check one Mermaid source

**Files:**
- Modify: `package.json`, `package-lock.json` (add `"pele": "1.12.0"`)
- Create: `papers/mermaid.js` (from `spikes/mermaid-overview/render.mjs`)
- Create: `papers/diagrams.py`
- Test: `tests/test_diagrams.py`

**Interfaces:**
- Produces, in `papers/diagrams.py`:
  - `draw(source: str, width: int, config: dict | None = None) -> dict`. Returns `{'ok': True, 'type', 'width', 'height', 'labels': [str], 'nodes': [{'id', 'text'}], 'min_font': float, 'svg': str}` or `{'ok': False, 'error': str}`. Raises `ValueError('Install Node.js to draw figures.')` when `shutil.which('node')` is None.
  - `chart_config(width: float) -> dict` — the Global Constraints value.
  - `check(answer: dict, *, width: int, required: list[str], chart_wanted: bool = False, max_nodes: int | None = None) -> dict`. Draws `answer['mermaid']` and, when present, `answer['chart']`. Raises `ValidationError` whose issues are `{'code': 'diagram', 'path': 'mermaid' | 'chart', 'message': ...}`. Returns `{'diagram': drawn, 'chart': drawn or None, 'chart_config': dict or None, 'figure': {'width': int, 'height': int}}`, where `chart_config` is the size the chart was drawn at.
  - Constants `MIN_FONT = 11`, `SHAPE = (0.6, 1.4)`, `MAX_WORDS = 8`, `CHART_HEIGHT = 280`, `CHART_GAP = 24`, `CHART_TYPES`.
- `papers/mermaid.js` reads `{source, width, config}` on stdin and writes the `draw` result on stdout. It renders with the Global Constraints options and a MathJax TeX resolver that returns `null` when MathJax throws.

- [ ] **Step 1: Write the failing tests** in `tests/test_diagrams.py`:

```python
class DrawTests(unittest.TestCase):
    def test_a_flowchart_reports_its_nodes_and_size(self):
        drawn = draw('flowchart LR\n  attn["Scaled dot-product attention"] --> law["0.62 to Law"]', 1000)
        self.assertTrue(drawn['ok'])
        self.assertEqual(drawn['type'], 'flowchart')
        self.assertEqual([n['id'] for n in drawn['nodes']], ['attn', 'law'])
        self.assertIn('class="pele-node', drawn['svg'])

    def test_a_parse_error_is_returned_not_raised(self):
        drawn = draw('flowchart LR\n  a --> \n  xychart\n  bar [1,2]', 1000)
        self.assertFalse(drawn['ok']); self.assertIn('Parse error', drawn['error'])

    def test_a_link_and_markup_draw_inert(self):           # Review Focus 1, 2
        drawn = draw('flowchart LR\n  a["<img src=x onerror=alert(1)>"]\n  click a href "javascript:alert(1)"', 1000)
        self.assertNotIn('<img', drawn['svg']); self.assertNotIn('javascript:', drawn['svg'])

    def test_an_init_directive_does_not_widen_the_render(self):   # Review Focus 1
        drawn = draw('%%{init: {"flowchart": {"nodeSpacing": 900}}}%%\nflowchart LR\n  a --> b --> c', 1000)
        self.assertLessEqual(drawn['width'], 1000)

    def test_broken_tex_shows_its_source(self):            # Review Focus 4
        drawn = draw('flowchart LR\n  a["$$\\frac{$$"]', 1000)
        self.assertTrue(drawn['ok'])

    def test_the_chart_size_is_the_applications(self):
        drawn = draw('xychart\n  x-axis ["A", "B", "C"]\n  bar [1, 2, 3]', 1000, chart_config(736))
        self.assertEqual((round(drawn['width']), round(drawn['height'])), (736, 280))

class CheckTests(unittest.TestCase):
    def test_each_rule_names_its_fix(self):
        # One source per rule, each asserting the message substring:
        # missing item  -> 'does not show the plan item "Encoder stack"'
        # 13 nodes      -> 'has 13 nodes; the limit is 12'
        # 9-word label  -> 'more than 8 words'
        # '**bold**' in a plain label -> 'literal asterisks'
        # tall chain of 8 TB nodes    -> 'too tall for its width'
        # wide chain of 8 LR nodes    -> 'too wide for its height'
        # chart_wanted and no chart   -> 'write it as a Mermaid source in "chart"'
        # chart 'flowchart LR ...'    -> 'use xychart, pie, quadrantChart, or radar-beta'
        # Write one self.subTest per row, each with check(...) inside assertRaises(ValidationError).

    def test_the_shape_counts_the_chart(self):
        result = check(PRO_ANSWER, width=1000, required=PRO_ITEMS, chart_wanted=True, max_nodes=12)
        self.assertEqual(result['figure'], {'width': 736, 'height': 1141})
```

`PRO_ANSWER` and `PRO_ITEMS` are the `answer` and the plan item names of `spikes/mermaid-overview/out-v4/2511.07694v1.json`, copied to `tests/fixtures/overview/pro-mermaid-run.json`. The expected size comes from that run; allow ±2 units if Pele's width table differs on the build machine.

- [ ] **Step 2: Run** `.venv/bin/python -m unittest tests.test_diagrams -v`. Expected: FAIL, `ModuleNotFoundError: papers.diagrams`.
- [ ] **Step 3: Implement** `npm install --save-exact pele@1.12.0`, `papers/mermaid.js` (CommonJS like `papers/math.js`, or ESM through a dynamic `import('pele')`), and `papers/diagrams.py`. The check messages are the spike's messages in `spikes/mermaid-overview/generate.py` `issues()`.
- [ ] **Step 4: Run** the same command. Expected: PASS.
- [ ] **Step 5: Commit** — `git commit -m "Render and check Mermaid figures with Pele"`

### Task 3: Write the figure assets

**Files:**
- Modify: `papers/HTMLSnapshot.swift` (new mode `page`)
- Modify: `papers/diagrams.py`
- Test: `tests/test_diagrams.py`

**Interfaces:**
- Consumes: `check()` result from Task 2.
- Produces: `write_assets(directory, figure_id: str, result: dict, *, title='', subtitle='', footer='') -> dict` returning `{'png', 'pdf', 'svg_source'}`, paths relative to the Paper directory under `reader/overview-figures/<uuid>/`, so `papers/exports.py:figure_source` accepts them unchanged. `LIGHT_VARIABLES: dict[str, str]` — the `--pele-*` values of the light Figure palette.

The `page` mode sizes the canvas from the bounding box of `<main>` instead of the first `<svg>`, runs no issue checks, and writes `<prefix>.png`, `<prefix>.pdf`, and `<prefix>.checks.json` with `{mode, width, height}`. The HTML page is 1000 units wide (640 for a Blog figure), sets `LIGHT_VARIABLES` on `:root`, and holds the title, subtitle, main SVG, chart SVG 24 units below it, and footer. Content JavaScript stays disabled: the SVGs come from Node. `svg_source` is the main diagram's SVG with a `<style>` element that sets `LIGHT_VARIABLES`; it backs Export Editable SVG and has no chart (shortcut: the editable export carries the main diagram only, upgrade if readers ask for the chart).

`LIGHT_VARIABLES` (from `papers/figures/palette.py` LIGHT): `--pele-bg #ffffff`, `--pele-fg #243b32`, `--pele-muted #627168`, `--pele-line #7f9fb5`, `--pele-surface #fbfcfa`, `--pele-surface-alt #f3f6f0`, `--pele-border #c3ccbd`, `--pele-accent #2f6f5e`.

- [ ] **Step 1: Write the failing test** `test_assets_are_a_png_a_pdf_and_a_standalone_svg`: with `PRO_ANSWER` checked, `write_assets(tmp, 'fig1', result, title='T', subtitle='S', footer='F')` returns three paths that exist; the PNG starts with `b'\x89PNG'`; its pixel width is 2000 (2x of 1000); the PDF starts with `b'%PDF'`; `svg_source` contains `--pele-fg: #243b32`.
- [ ] **Step 2: Run** `.venv/bin/python -m unittest tests.test_diagrams -v`. Expected: FAIL on `write_assets`.
- [ ] **Step 3: Implement** the `page` mode, rebuild with `xcrun swiftc -O papers/HTMLSnapshot.swift -o papers/html-snapshot`, and implement `write_assets`.
- [ ] **Step 4: Run** the same command. Expected: PASS.
- [ ] **Step 5: Commit** — `git commit -m "Write Mermaid figure PNG, PDF, and editable SVG"`

### Task 4: The Overview plan and diagram stages

**Files:**
- Modify: `papers/overview_workflow.py` (replace `_scene`, `_build`, `focus`, `ATTENTION_EXAMPLE`, `VARIETY_EXAMPLE`, `SCENE_WRAPPER`; keep `DIGEST_INSTRUCTION`, `plan()`, `_digest`)
- Modify: `papers/coordinator.py:37-40` (`PROGRESS_STAGES`: replace `'scene'` with `'overview_plan': 'Planning the Overview'` and `'diagram': 'Drawing the Overview'`)
- Modify: `papers/explanation.py` (delete `digest_requirements`, `example_coverage_issues`, `example_structure_issues`, `series_text_issues`, `story_issues`, `scene_coverage_issues`)
- Test: `tests/test_overview_workflow.py`, `tests/test_overview_composition.py` (rewrite), `tests/story_fixtures.py` (drop Scene fixtures)

**Interfaces:**
- Consumes: `diagrams.check`, `diagrams.write_assets`, `ValidationError`.
- Produces: `PROMPT_REVISION = 'overview-mermaid-v1'`; `PLAN_PROMPT` and `DIAGRAM_PROMPT` (from the spike's `PLAN_PROMPT` and `PROMPT`, run 4); `component_hooks(digest: dict, nodes: list[dict]) -> list[dict]` with the same output keys as today (`node`, `name`, `role`, `computes`, `values`, `passages`), where `node` is the Mermaid node ID. The result dict keeps every key it has today except that `figures[0]` changes to: `id`, `title`, `paper_connection`, `caption`, `illustrative`, `passages`, `mermaid`, `chart`, `chart_config`, `layout_width: 1000`, `dimensions: result['figure']`, `components`, plus the `write_assets` paths. The result adds `overview_plan`. Provenance `checks` becomes `{'components', 'nodes', 'shape'}`.
- The run directory keeps `digest.json` and adds `overview-plan.json` and `diagram.json` (the accepted answer). `scene.json`, `overview.source.svg`, `placements.json`, and `composition-checks.json` are no longer written.

- [ ] **Step 1: Write the failing tests.** Fixtures: the run 4 plan and answers from `spikes/mermaid-overview/out-v4/*.json` with the saved Digest of each Paper (read once from the Library and saved under `tests/fixtures/overview/`, as `make_fixtures.py` does). Tests through `generate(provider, document, progress)`:
  - `test_run_saves_plan_diagram_and_figure`: answers `[selection, digest, plan, answer]`; `result['plan'] == digest`; `result['overview_plan'] == plan`; `figures[0]['mermaid'] == answer['mermaid']`; the PNG file exists; `components` has an entry whose `node` is a Mermaid node ID of the answer and whose `name` is a Digest component name.
  - `test_a_failed_check_sends_one_exact_correction`: Attention from `spikes/mermaid-overview/out-v3/1706.03762v7.json` (run 4's Attention was not accepted): its plan, its second answer (508 × 1007, too tall only), then its third, accepted answer; 5 requests; the 5th request's last message contains `too tall for its width`.
  - `test_a_wanted_chart_is_drawn_below`: PRO fixtures; `figures[0]['chart']` starts with `xychart`; `dimensions == {'width': 736, 'height': 1141}` (±2).
  - `test_a_bad_plan_is_corrected`: a plan with 9 items, then the good plan; the correction contains `the limit is 7`.
  - `test_a_failed_plan_stage_retries_without_a_new_digest`: as the existing digest retry test, for stage `overview_plan`.
  - `test_no_node_fails_without_a_partial_overview` (Review Focus 3): patch `papers.diagrams.shutil.which` to return None; `generate` raises with `Install Node.js to draw figures.`
- [ ] **Step 2: Run** `.venv/bin/python -m unittest tests.test_overview_workflow tests.test_overview_composition -v`. Expected: FAIL.
- [ ] **Step 3: Implement** `OverviewWorkflow._overview_plan(digest) -> dict` (stage `overview_plan`, `request_validated` with the plan checks, `attempts=3`) and `OverviewWorkflow._diagram(digest, plan) -> tuple[dict, dict]` (stage `diagram`; `validate` calls `diagrams.check(answer, width=1000, required=[item['name'] for item in plan['items']], chart_wanted=bool(plan.get('chart')), max_nodes=12)` and returns the answer; keep the check result for `run_workflow`). `run_workflow` writes the files and builds the result above.
- [ ] **Step 4: Run** the same command, then the whole suite. Expected: PASS, except the Blog and figure-layout tests that still use Scenes (Tasks 5 and 7).
- [ ] **Step 5: Commit** — `git commit -m "Draw the Overview as one Mermaid diagram from a plan"`

### Task 5: Blog figures as Mermaid

**Files:**
- Modify: `papers/blog_figures.py` (`messages`, `build`, `draw`, `publish`)
- Modify: `papers/blog_prompts.py:62-81` (replace `PANEL_WRAPPER`, `PANEL_EXAMPLE` with `FIGURE_PROMPT`) and `:150-160` (the brief: delete the `exact_text` line)
- Modify: `papers/explanation.py` (`BLOG_BRIEF_SCHEMA` and `_validate_blog_brief`: delete `exact_text`; delete `EXACT_TEXT_ITEM`; rename `blog_panel_required` to `blog_figure_required`, returning `illustrative_values` only)
- Test: `tests/test_blog_workflow.py`, `tests/test_blog_omission.py`

**Interfaces:**
- Consumes: `diagrams.check`, `diagrams.write_assets`.
- Produces: the model answers `{"id": ..., "mermaid": ...}`. A published Blog figure keeps `id`, `title`, `paper_connection`, `caption`, `illustrative`, `passages`, `alt`, `brief`, and adds `mermaid`, `layout_width: 640`, `dimensions`, `components: []`, plus the `write_assets` paths (no title, subtitle, or footer: the article carries the caption). `panel` and `labels` go.
- `FIGURE_PROMPT` asks for one Mermaid diagram of the brief, any diagram type including charts, free styling with the markdown-string syntax, and the Global Constraints rules at 640 units.

- [ ] **Step 1: Write the failing tests.** Replace `_good_panel` with a Mermaid answer fixture. `test_a_figure_is_one_mermaid_diagram`: the published figure has `mermaid` and a PNG; the request contains the brief and no `exact_text`. `test_a_missing_value_is_corrected`: an answer without one `illustrative_values` string, then a good one; the correction contains the missing value. Update the omission test so four failing answers (for example four parse errors) omit the figure.
- [ ] **Step 2: Run** `.venv/bin/python -m unittest tests.test_blog_workflow tests.test_blog_omission -v`. Expected: FAIL.
- [ ] **Step 3: Implement.** `draw` keeps its request budget and omission rules; `validate` calls `diagrams.check(answer, width=BLOG_DISPLAY_WIDTH, required=blog_figure_required(brief))` after the `id` check and `uncited`. The layout correction request goes: every defect is a check.
- [ ] **Step 4: Run** the same command, then the whole suite. Expected: PASS, except `tests/test_figure_layout.py` and `tests/relayout_saved_scenes.py` (Task 7).
- [ ] **Step 5: Commit** — `git commit -m "Draw Blog figures as Mermaid diagrams"`

### Task 6: Show Mermaid figures on the page

**Files:**
- Create: `app/static/pele.global.js` (copy of `node_modules/pele/dist/pele.global.js` 1.12.0)
- Modify: `app/static/index.html` (load it before the module scripts; delete `#figure-panels`)
- Modify: `app/static/render.js:276-319` (marker branch)
- Modify: `app/static/reader.js` (delete `inlineFigure`, `inlineFigures`, `showComponent` wiring for Scene SVGs, the panel outline at `:227-246`, `:262-283`, the `panels` state at `:21`, and the "N panels" provenance at `:867-873`; add `drawDiagram`)
- Modify: `app/static/app.js:1005-1118` (delete `figurePanels`, `focusFigurePanel`, `figurePanelAt`, the 1–9 keys; add `openDiagram`)
- Modify: `app/static/app.css` (`--pele-*` variables per theme; delete `#figure-panels` and `.figure-inline` rules)

**Interfaces:**
- Consumes: the figure record of Tasks 4 and 5.
- Produces: `drawDiagram(container: HTMLElement, figure: object)` in `reader.js`, passed to `prose` through `io` (as `inlineFigure` is today), so `render.js` stays free of DOM and Pele at import time. It renders `figure.mermaid` and `figure.chart` (with `figure.chart_config`) through `pele.render` with the Global Constraints options and `maxWidth: figure.layout_width`, copies each `.pele-node`'s `data-id` into `data-node`, and calls `annotateFigure` with `figure.components`. A math resolver is passed only when `window.MathJax?.tex2svg` exists. `openDiagram(figure)` in `app.js` renders the same diagram at full size into `#figure-dialog` and calls `pele.enableZoom` on it; the Enlarge button calls it.
- In `render.js`, a figure with `mermaid` takes the `drawDiagram` path. A figure without `mermaid` (a saved Scene figure, Overview or Blog) takes the existing `<img>` path with `data-dark-src`, so `swapFigureSources` keeps working for it.
- CSS variables: light (and sepia) `--pele-bg #ffffff; --pele-fg #243b32; --pele-muted #627168; --pele-line #7f9fb5; --pele-surface #fbfcfa; --pele-surface-alt #f3f6f0; --pele-border #c3ccbd; --pele-accent #2f6f5e`; dark `#10120f; #e6ebe4; #a9b3a8; #5f7f95; #171b16; #1d231c; #4a5a4e; #8fc7b0`; `--pele-font: var(--ui)`. A comment names `papers/diagrams.py` `LIGHT_VARIABLES` as the export copy of the light values.

- [ ] **Step 1: Generate test data.** Start the `localxiv-dev` preview with a copy of the Library that holds the three reference Papers, and generate a new Overview and Blog for PRO.
- [ ] **Step 2: Implement** the files above.
- [ ] **Step 3: Check in the browser** (`.claude/launch.json` `localxiv-dev`): the PRO Overview shows the diagram and the bar chart below it; Tab to a node opens the Component hover and a click opens its passage; Enlarge opens the dialog with zoom; the Blog figures show with their captions; Export Editable SVG saves `svg_source`; the dark theme recolours the figure with no new request in `read_network_requests` (Review Focus 5); the Attention Overview, still a Scene figure, shows as an image and swaps with the theme; `read_console_messages` shows no errors; the CSP blocks nothing.
- [ ] **Step 4: Run** `node tests/test_paper_search_ui.mjs` (imports `render.js`). Expected: PASS.
- [ ] **Step 5: Commit** — `git commit -m "Show Mermaid figures on the page"`

### Task 7: Remove the Figure library and the Scene

**Files:**
- Delete: `papers/figures/`, `tests/test_figure_layout.py`, `tests/relayout_saved_scenes.py`, the Scene fixtures under `tests/fixtures/overview/`
- Modify: `papers/HTMLSnapshot.swift` (delete the `measure` mode and `captureMeasure`)
- Modify: `app/macos/verify-release.py:99-111,143-145` (render `tests/fixtures/overview/pro-mermaid-run.json`'s answer through `diagrams.check` and `write_assets`, then `export_pdf`; keep the report keys)
- Modify: `tests/test_overview_composition.py:94` (delete the `DETOUR_ALLOWANCE` patch if any test still has it)
- Modify: `CONTEXT.md:45-83,121-125` (the Domain language section of the spec), `docs/development.md:50,63-65,72-74,91-93` (point at `papers/diagrams.py` and the new spec), `docs/dependency-licenses.md` (Pele, MIT)

- [ ] **Step 1: Delete and edit** the files above. `rg "papers.figures|papers/figures|SceneError|scene_card|Scene\b" papers app tests tools docs/development.md CONTEXT.md` lists nothing outside the superseded specs.
- [ ] **Step 2: Run** `uvx ruff check .` and `.venv/bin/python -m unittest discover -s tests`. Expected: both clean.
- [ ] **Step 3: Run** `.venv/bin/python app/macos/verify-release.py` against a release build as `docs/macos-release.md` says. Expected: `figure_rendering` and `overview_figure_rendering` pass.
- [ ] **Step 4: Commit** — `git commit -m "Remove the Figure library and the Scene"`
