# Figure library consolidation implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. AGENTS.md applies to every task: invoke `ponytail` before writing code and `pstack:unslop` before writing any prose, commit message, or comment.

**Goal:** One figure library, `papers/figures/`, draws every Overview and Blog figure from a model-authored Scene, and the Blog runs on the Overview's coordinator with direct structured requests.

**Architecture:** The model authors content and structure only; `Figure` validates, lays out, renders, and checks. `OverviewWorkflow` and `BlogWorkflow` are the two callers, both on `papers/coordinator.py`. The model-drawn SVG path, the four-attempt repair loop, and the smolagents agent loop are deleted.

**Tech Stack:** Python 3 standard library, the WebKit renderer `papers/html-snapshot` built from `papers/HTMLSnapshot.swift`, `unittest`.

**Spec:** [docs/superpowers/specs/2026-09-18-figure-library-consolidation-design.md](../specs/2026-09-18-figure-library-consolidation-design.md). Read it first. The scene layout design it builds on is [docs/superpowers/specs/2026-09-18-overview-scene-layout-design.md](../specs/2026-09-18-overview-scene-layout-design.md).

## Global constraints

- `tests/` is gitignored (`.gitignore` line `tests/`). Every task runs its tests locally. No commit step adds a test file. Fixtures under `tests/fixtures/` are local too.
- Commit messages are one imperative sentence in sentence case with no prefix, as in `git log`: `Collapse a repeated card locally instead of asking the model`. No `Co-Authored-By` or other trailer, per the user's CLAUDE.md.
- The renderer must exist before task 1. Build it and export its path in every shell that runs tests:

```sh
xcrun swiftc -O papers/HTMLSnapshot.swift -o papers/html-snapshot
export LOCALXIV_HTML_RENDERER="$PWD/papers/html-snapshot"
```

- Run tests with `.venv/bin/python -m unittest <module> -v` from the repository root. `.venv` is created per `docs/development.md` with `requirements-ai.txt` installed.
- The model authors no geometry. A Scene names no gap, size, or coordinate, and the validator rejects them. Nothing in this plan adds a coordinate field.
- Text is never scaled after layout. `Figure(width=...)` lays out at the width the reader sees: 1000 units for an Overview page, 640 for a Blog panel.
- Layout constants stay: body text 14, headings 15, title 26, palette `TONES`, `MARGIN = 24`.
- The author-facing card is generated from `papers/figures/schema.py` and stays under 1,200 tokens by `len(text) // 4`.
- CONTEXT.md terms are the vocabulary: Scene, Scene layout, Digest, Blog figure, Blog figure brief, Figure library, Figure render.

## Decisions made in this plan

The spec left these to the plan. Each is listed so the user can veto it before execution.

1. **Phase 1 changes no output.** `papers/html_figures.py` and its `normalize_svg` stay through phase 1 so the composed SVG is byte-identical to the baseline. Phase 2 deletes `html_figures.py` and takes a new baseline (task 15).
2. **Panel validation.** `schema.validate(value, frame='page')` validates a full Scene. `schema.validate(value, frame='panel')` validates one panel object `{id, heading, body, notes?, edges?}` with the same node rules. `Figure` wraps a panel into a page-shaped Scene internally with empty title, subtitle, and footer; `render` with `frame='panel'` draws no header line, no title, no subtitle, and no footer.
3. **Width threading.** A `Canvas` dataclass (`width`, `margin`, `column`, `stretch_max`) replaces the module constants `WIDTH`, `MARGIN`, `COLUMN`, and `COLUMN_STRETCH_MAX`. `stretch_max` is `round(column * 460 / 952)` so a 640-unit panel keeps the same proportion as today's 1000-unit page.
4. **Author response.** The Blog author returns either a draft or `{"action": "revise_narrative", "reason", "passage_ids"}`. One narrative revision is allowed per run. This replaces the `request_narrative_revision` tool.
5. **Selection.** `BlogWorkflow` uses `coordinator.select_evidence` with the Blog's own selection prompt. The Groq-only character guard from `_known_evidence_char_limit` becomes a post-retrieval check that fails the run with `ProviderError`; it sits outside the correction loop because `select_evidence` has already retrieved by then. The `read_index` paging tool is dropped; `_source_map` already pages a large map into one request.
6. **Review anchors.** A published Blog figure's `labels` are `Figure.text(panel)`, the visible strings of its Scene panel. `_review_response` is unchanged and reads them as before.
7. **Figure ceiling.** `MAX_FIGURE_CORRECTIONS = 3`. One request plus three corrections replaces `MAX_FIGURE_ATTEMPTS = 4`. The review verdict ceiling becomes `1 + (MAX_FIGURE_CORRECTIONS + 2) * len(figures) + 2`.
8. **Callers keep a thin `generate`.** `papers/overview_workflow.generate` and `papers/blog_workflow.generate` keep the signature `generate(provider, document, progress, **options)` so `papers/ai.py`, `app/server.py`, and `tools/overview_run.py` change one import line at most.
9. **Characterization tests.** The spec's unit 3 asked for fake-provider tests of the smolagents Blog coordinator. A fake would have to emulate the tool-call protocol that phase 2 deletes, so task 8 instead locks the pure functions that survive the move and task 14 adds an end-to-end fake-provider test of the new workflow.
10. **Release check.** `app/macos/verify-release.py` replaces the smolagents import and the stale `render` call with one `Figure` build of an inline two-card Scene, and the result keys `html_svg_rendering` and `smolagents_import` become `figure_rendering`.
11. **Overview basis.** The Blog's `overview_basis` becomes `{'digest': saved plan, 'run': provenance.run}` when the saved Overview has a `plan` with `components`. An older SVG-only Overview gives no reference.
12. **Blog figure dimensions.** A published Blog figure gains `dimensions` from `checks['canvas']`, as the Overview already has, so `app/static/app.js:533` stops falling back to the image size.
13. **Docs.** Per the user on 2026-09-18: delete `docs/blog_refactor.md` and the three superseded specs; keep the verification reports with one status line each; remove smolagents from `requirements-ai.txt`, packaging, and the release check.

## File map

| Path | Responsibility after this plan |
| --- | --- |
| `papers/figures/__init__.py` | `Figure`, `FigureResult`, `SceneError` |
| `papers/figures/schema.py` | Node kinds, limits, `validate`, `text`, `headings`, `collapse_repetitions`, `card`, `json_schema` |
| `papers/figures/measure.py` | `Measurer` (WebKit), `FixedMeasurer` (tests), `measure_text_widths` |
| `papers/figures/layout.py` | `Canvas`, `size`, `reflow_narrow`, `justify`, `place`, `prime` |
| `papers/figures/route.py` | `route`, segment and box geometry, label placement tests |
| `papers/figures/render.py` | `compose`, node and edge drawing, `SHARED_MARKERS`, `rasterize` |
| `papers/figures/checks.py` | `text_density`, `MIN_TEXT_DENSITY`, `native_issues` |
| `papers/coordinator.py` | `Coordinator`, `RunStore`, `create_run_directory`, `finalize_run`, `request_validated`, `select_evidence`, `supplement_evidence`, `provider_options`, `is_transient`, `panel_digest` |
| `papers/overview_workflow.py` | `OverviewWorkflow`, prompts for selection, digest, and the Scene wrapper, thin `generate` |
| `papers/blog_workflow.py` | `BlogWorkflow`, Blog prompts, figure states, omission cleanup, review loop, thin `generate` |
| `papers/explanation.py` | Digest and Blog contracts only |
| Deleted | `papers/scene_layout.py`, `papers/html_figures.py`, `papers/agent_overviews.py`, `papers/panel_authoring.py`, `papers/blog_figures.py`, `papers/panel-guides/` |

---

## Phase 1: the figure library and the coordinator, with no output change

### Task 1: Baseline the composed SVG of every saved scene

**Files:**
- Create: `tests/baseline_scenes.py` (local, untracked)
- Read: `papers/scene_layout.py:635-651` (`compose_scene`)

**Interfaces:**
- Produces: `.scratch/figure-baseline/<name>.svg`, one per scene, compared by later tasks.

- [ ] **Step 1: Build the renderer and run the existing suite**

```sh
xcrun swiftc -O papers/HTMLSnapshot.swift -o papers/html-snapshot
export LOCALXIV_HTML_RENDERER="$PWD/papers/html-snapshot"
.venv/bin/python -m unittest discover -s tests -v
```

Expected: every test in `test_scene_layout`, `test_scene_schema`, `test_panel_checks`, `test_panel_authoring`, and `test_provider_reasoning` passes.

- [ ] **Step 2: Write the baseline script**

```python
"""Compose every known scene and write the SVG to .scratch/figure-baseline/ for byte comparison."""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / '.scratch' / 'figure-baseline'
LIBRARY = Path.home() / 'Library' / 'Application Support' / 'LocalXiv' / 'library' / 'papers'


def scenes():
    fixtures = ROOT / 'tests' / 'fixtures' / 'overview'
    for path in sorted(fixtures.glob('*-scene.json')):
        yield path.stem, json.loads(path.read_text())
    for path in sorted(LIBRARY.glob('*/reader/overview-figures/*/scene.json')):
        yield path.parts[-4][:12] + '-' + path.parts[-2][:8], json.loads(path.read_text())


def main(compare):
    from papers.scene_layout import compose_scene
    OUT.mkdir(parents=True, exist_ok=True)
    failures = 0
    for name, scene in scenes():
        with tempfile.TemporaryDirectory() as directory:
            svg, _ = compose_scene(directory, 'Baseline', scene)
        target = OUT / (name + '.svg')
        if compare:
            if target.read_text() != svg:
                failures += 1
                print('DIFFERS', name)
            else:
                print('same   ', name)
        else:
            target.write_text(svg)
            print('wrote  ', name)
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    main(compare='--compare' in sys.argv)
```

- [ ] **Step 3: Write the baseline**

Run: `.venv/bin/python tests/baseline_scenes.py`
Expected: one `wrote` line per scene. At least the two fixtures. On the user's machine, five library scenes as well.

- [ ] **Step 4: Confirm the comparison mode passes against itself**

Run: `.venv/bin/python tests/baseline_scenes.py --compare`
Expected: every line `same`, exit code 0.

No commit. The script and its output are local.

### Task 2: Create `papers/figures/schema.py` from the Scene validator

**Files:**
- Create: `papers/figures/__init__.py`, `papers/figures/schema.py`
- Modify: `papers/explanation.py:705-918` (the `SCENE_*` constants, `validate_scene`, `_scene_node`, `_scene_id`, `_scene_lines`, and `collapse_repetitions` at 609-634 with `_walk_nodes`)
- Modify: `papers/scene_layout.py:735-776` (`_walk`, `scene_headings`, `scene_text`)
- Test: `tests/test_scene_schema.py`

**Interfaces:**
- Produces:
  - `class SceneError(ValueError)` with `.issues`, a list of `{'code', 'path', 'message', ...}` dicts, the same records `PanelPlanError` carries today.
  - `validate(value, *, frame='page') -> dict` returns a deep copy or raises `SceneError`.
  - `text(scene) -> list[str]`, `headings(scene) -> list[str]`, `collapse_repetitions(scene) -> list[str]`.
  - Constants `KINDS`, `TONES`, `MAX_PANELS`, `MAX_DEPTH`, `MAX_NODES`, `MAX_EDGES`, `MAX_ACCENTS`, `LIMITS`, `NODE_FIELDS`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_scene_schema.py`, replacing its import of `validate_scene`:

```python
from papers.figures.schema import SceneError, validate, text, headings, collapse_repetitions


class PanelFrameTests(unittest.TestCase):
    def setUp(self):
        self.attention = json.loads((FIXTURES / 'attention-scene.json').read_text())

    def test_a_panel_validates_without_page_fields(self):
        panel = self.attention['panels'][0]
        validate(panel, frame='panel')

    def test_a_panel_rejects_page_fields(self):
        panel = dict(self.attention['panels'][0], title='No')
        with self.assertRaises(SceneError) as caught:
            validate(panel, frame='panel')
        self.assertIn('panel.title', [issue['path'] for issue in caught.exception.issues])

    def test_page_frame_still_requires_title(self):
        scene = dict(self.attention)
        del scene['title']
        with self.assertRaises(SceneError) as caught:
            validate(scene, frame='page')
        self.assertIn('scene.title', [issue['path'] for issue in caught.exception.issues])

    def test_text_and_headings_read_a_panel(self):
        panel = self.attention['panels'][0]
        self.assertIn(panel['heading'], headings({'panels': [panel]}))
        self.assertIn('Query Q', text({'title': '', 'subtitle': '', 'footer': '', 'panels': [panel]}))
```

Replace every `validate_scene(` in the file with `validate(` and every `PanelPlanError` with `SceneError`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m unittest tests.test_scene_schema -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'papers.figures'`.

- [ ] **Step 3: Create the package and move the validator**

Create `papers/figures/__init__.py` containing only a docstring for now:

```python
"""The figure library: a Scene in, laid-out SVG, PNG, checks, and issues out."""
```

Create `papers/figures/schema.py`. Move these from `papers/explanation.py` unchanged except for the renames below: `SCENE_KINDS` to `KINDS`, `SCENE_TONES` to `TONES`, `SCENE_MAX_PANELS` to `MAX_PANELS`, `SCENE_MAX_DEPTH` to `MAX_DEPTH`, `SCENE_MAX_NODES` to `MAX_NODES`, `SCENE_MAX_EDGES` to `MAX_EDGES`, `SCENE_MAX_ACCENTS` to `MAX_ACCENTS`, `SCENE_LIMITS` to `LIMITS`, `SCENE_NODE_FIELDS` to `NODE_FIELDS`, `validate_scene` to `validate`, `PanelPlanError` to `SceneError` (define the class in `schema.py` with the same body), plus `_scene_node`, `_scene_id`, `_scene_lines`, `_panel_error`, `_text`, `_identifier`, `PANEL_ID_RE`, `collapse_repetitions`, and `_walk_nodes`. `explanation.py` keeps its own `_panel_error`, `_text`, `_identifier`, and `PANEL_ID_RE` because the digest validator uses them.

Move `_walk`, `scene_headings` (renamed `headings`), and `scene_text` (renamed `text`) from `papers/scene_layout.py` into `schema.py`. `text` must tolerate a scene whose `title`, `subtitle`, or `footer` is empty; it already drops blank strings.

Give `validate` its frame:

```python
def validate(value, *, frame='page'):
    """Validate one Scene (frame 'page') or one panel object (frame 'panel')."""
    if frame not in ('page', 'panel'):
        raise ValueError('frame must be page or panel')
    if frame == 'panel':
        errors = []
        if not isinstance(value, dict):
            raise SceneError([{'code': 'scene_validation', 'path': 'panel', 'message': 'panel must be an object.'}])
        _validate_panel(value, 'panel', errors)
        if errors:
            raise SceneError(errors[:20])
        return copy.deepcopy(value)
    ...  # the existing body of validate_scene, with the per-panel block extracted into _validate_panel
```

Extract the existing per-panel block of `validate_scene` (from `for name in sorted(set(panel) - {...})` through the edge checks) into `_validate_panel(panel, path, errors)` so both frames share it. The page frame keeps its `seen_panels` duplicate check around the call.

- [ ] **Step 4: Point the old names at the new module**

In `papers/explanation.py`, delete the moved code and add at the top:

```python
from papers.figures.schema import (KINDS as SCENE_KINDS, SceneError as PanelPlanError,
                                   collapse_repetitions, validate as validate_scene)
```

In `papers/scene_layout.py`, delete `_walk`, `scene_headings`, and `scene_text`, and add:

```python
from papers.figures.schema import headings as scene_headings, text as scene_text
```

These aliases keep `overview_workflow.py` and the tests importing from the old places until task 7 removes them.

- [ ] **Step 5: Run the tests**

Run: `.venv/bin/python -m unittest tests.test_scene_schema tests.test_scene_layout -v`
Expected: PASS.

- [ ] **Step 6: Compare the baseline**

Run: `.venv/bin/python tests/baseline_scenes.py --compare`
Expected: every line `same`.

- [ ] **Step 7: Commit**

```sh
git add papers/figures/__init__.py papers/figures/schema.py papers/explanation.py papers/scene_layout.py
git commit -m "Move the Scene validator into papers/figures/schema.py with a panel frame"
```

### Task 3: Create `papers/figures/measure.py` with an injectable measurer

**Files:**
- Create: `papers/figures/measure.py`
- Modify: `papers/scene_layout.py:56-98` (`Measurer`)
- Test: `tests/test_measure.py` (new, local)

**Interfaces:**
- Produces:
  - `class Measurer` with `width(text, size=14, weight=None) -> float`, `prime(strings, size, weight)`, `wrap(text, width, size, weight) -> list[str]`, `close()`. Constructor `Measurer(directory)`.
  - `class FixedMeasurer` with the same methods and no renderer: `width` is `len(text) * size * 0.55`, or `* 0.60` when `weight` is `700`.
  - `measure_text_widths(directory, strings, *, font_size=18, font_family='Arial, sans-serif', font_weight=None)` re-exported from `papers.html_figures` for phase 1.

- [ ] **Step 1: Write the failing test**

```python
"""Measurers agree on the wrap algorithm; only the width source differs."""
import unittest

from papers.figures.measure import FixedMeasurer


class FixedMeasurerTests(unittest.TestCase):
    def test_bold_is_wider_than_regular(self):
        measurer = FixedMeasurer()
        self.assertGreater(measurer.width('Query', 14, 700), measurer.width('Query', 14))

    def test_wrap_breaks_at_the_width(self):
        measurer = FixedMeasurer()
        lines = measurer.wrap('one two three four five six', 60, 14)
        self.assertGreater(len(lines), 1)
        self.assertEqual(' '.join(lines), 'one two three four five six')

    def test_close_is_safe_to_call(self):
        FixedMeasurer().close()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/python -m unittest tests.test_measure -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write the module**

```python
"""Text measurement for layout. Production measures in WebKit; tests use fixed widths."""
import shutil
import tempfile

from papers.html_figures import measure_text_widths

BODY = 14


class Measurer:
    """Measure every string once per size and weight in the renderer's font."""

    def __init__(self, directory):
        self.directory = tempfile.mkdtemp(prefix='measure-', dir=str(directory))
        self.cache = {}

    def close(self):
        shutil.rmtree(self.directory, ignore_errors=True)

    def _measure(self, strings, size, weight):
        return measure_text_widths(self.directory, strings, font_size=size, font_weight=weight)

    def width(self, text, size=BODY, weight=None):
        key = (text, size, weight)
        if key not in self.cache:
            self.cache[key] = self._measure([text], size, weight)[0]
        return self.cache[key]

    def prime(self, strings, size=BODY, weight=None):
        missing = [text for text in dict.fromkeys(strings) if (text, size, weight) not in self.cache]
        if missing:
            for text, value in zip(missing, self._measure(missing, size, weight)):
                self.cache[(text, size, weight)] = value

    def wrap(self, text, width, size=BODY, weight=None):
        words = str(text).split()
        self.prime(words, size, weight)
        space = self.width(' ', size, weight)
        lines, current, used = [], [], 0.0
        for word in words:
            size_of = self.width(word, size, weight)
            if current and used + space + size_of > width:
                lines.append(' '.join(current))
                current, used = [], 0.0
            current.append(word)
            used += (space if used else 0.0) + size_of
        if current:
            lines.append(' '.join(current))
        return lines or ['']


class FixedMeasurer(Measurer):
    """Widths from character counts, for layout tests that need no renderer."""

    def __init__(self):
        self.cache = {}

    def close(self):
        pass

    def _measure(self, strings, size, weight):
        factor = 0.60 if weight == 700 else 0.55
        return [len(text) * size * factor for text in strings]
```

- [ ] **Step 4: Replace the class in `scene_layout.py`**

Delete `class Measurer` from `papers/scene_layout.py` and add `from papers.figures.measure import Measurer`.

- [ ] **Step 5: Run the tests and the baseline**

Run: `.venv/bin/python -m unittest tests.test_measure tests.test_scene_layout -v && .venv/bin/python tests/baseline_scenes.py --compare`
Expected: PASS, every baseline line `same`.

- [ ] **Step 6: Commit**

```sh
git add papers/figures/measure.py papers/scene_layout.py
git commit -m "Move the measurer into papers/figures and add a fixed-width one for tests"
```

### Task 4: Split `scene_layout.py` into `layout.py`, `route.py`, and `render.py` with a `Canvas`

**Files:**
- Create: `papers/figures/layout.py`, `papers/figures/route.py`, `papers/figures/render.py`
- Modify: `papers/scene_layout.py` (becomes a thin alias module until task 7)
- Test: `tests/test_scene_layout.py`, `tests/test_layout_canvas.py` (new, local)

**Interfaces:**
- Produces:
  - `layout.Canvas(width: int, margin: int = 24)` dataclass with derived `column = width - 2 * margin` and `stretch_max = round(column * 460 / 952)`.
  - `layout.prime(measure, scene, frame)`, `layout.size(node, avail, measure, canvas)`, `layout.reflow_narrow(node, inner, measure)`, `layout.justify(node, inner, measure)`, `layout.place(node, x, y, canvas, stretch=None)`.
  - `route.route(source, target, obstacles)` and the helpers `segments`, `crosses`, `clear`, `label_fits`, `inside`, `overlaps`, all public, all pure.
  - `render.compose(measure, scene, canvas, *, frame='page', page_title='') -> (svg, placements)`.
  - `render.SHARED_MARKERS`, `render.SVG_NAMESPACE`.

- [ ] **Step 1: Write the failing test**

`tests/test_layout_canvas.py`:

```python
"""A narrower canvas lays out the same scene at the same text size."""
import json
import re
import unittest
from pathlib import Path

from papers.figures.layout import Canvas
from papers.figures.measure import FixedMeasurer
from papers.figures.render import compose

FIXTURES = Path(__file__).resolve().parent / 'fixtures' / 'overview'


class CanvasTests(unittest.TestCase):
    def test_canvas_derives_column_and_stretch(self):
        canvas = Canvas(1000)
        self.assertEqual(canvas.column, 952)
        self.assertEqual(canvas.stretch_max, 460)
        self.assertEqual(Canvas(640).column, 592)

    def test_a_panel_frame_at_640_keeps_body_text_at_14(self):
        scene = json.loads((FIXTURES / 'attention-scene.json').read_text())
        panel_scene = {'title': '', 'subtitle': '', 'footer': '', 'illustrative': False,
                       'layout': 'stack', 'panels': [scene['panels'][0]]}
        svg, placements = compose(FixedMeasurer(), panel_scene, Canvas(640), frame='panel')
        self.assertIn('viewBox="0 0 640 ', svg)
        self.assertNotIn('LOCALXIV', svg)
        self.assertNotIn('Paper-grounded diagram', svg)
        self.assertEqual(len(placements), 1)
        self.assertEqual(set(re.findall(r'font-size="(\d+)"', svg)) - {'15'}, {'14'})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/python -m unittest tests.test_layout_canvas -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Create `layout.py`**

Move from `papers/scene_layout.py` into `papers/figures/layout.py`: the constants at lines 18-45 except `WIDTH`, `MARGIN`, `COLUMN`, and `COLUMN_STRETCH_MAX`; `_prime_scene` as `prime`; `_size` as `size`; `REFLOW_FILL`, `REFLOW_MIN_NODES`, `_reflow_narrow` as `reflow_narrow`; `_justify` as `justify`; `_stretch_limit`, `_grow_group`, `_place` as `place`. Add:

```python
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Canvas:
    """The width a figure lays out at. Text is never scaled, so this is the reader's width."""
    width: int
    margin: int = 24
    column: int = field(init=False)
    stretch_max: int = field(init=False)

    def __post_init__(self):
        object.__setattr__(self, 'column', self.width - 2 * self.margin)
        object.__setattr__(self, 'stretch_max', round(self.column * 460 / 952))
```

Thread `canvas` through the four uses of `COLUMN_STRETCH_MAX` (today at `scene_layout.py:329, 339, 346, 361`): `_stretch_limit(node, canvas)`, `_grow_group(node, width, canvas)`, `place(node, x, y, canvas, stretch=None)`. Every recursive call passes `canvas` along.

`prime(measure, scene, frame)` primes the title, subtitle, footer, and the `'LOCALXIV · '` and lead strings only when `frame == 'page'`.

- [ ] **Step 4: Create `route.py`**

Move `_segments`, `_crosses`, `_clear`, `route`, `_label_fits`, `_inside`, `_overlaps` and `ARROW_CLEARANCE` into `papers/figures/route.py` without the leading underscores. No other change.

- [ ] **Step 5: Create `render.py`**

Move `esc`, `_text`, `_draw`, `_draw_edge`, `SceneLayoutError` (renamed `LayoutError`, still a `ValueError`), and `_compose` into `papers/figures/render.py`. Import `SHARED_MARKERS` and `SVG_NAMESPACE` from `papers.html_figures` for now. Rewrite `_compose` as:

```python
def compose(measure, scene, canvas, *, frame='page', page_title=''):
    """Lay out and draw one Scene at the canvas width. Returns the SVG and the panel frames."""
    scene = copy.deepcopy(scene)
    prime(measure, scene, frame)
    out = [SHARED_MARKERS]
    y = canvas.margin + 12
    if frame == 'page':
        out.append(_text(canvas.margin, y, 'LOCALXIV · ' + str(page_title), fill=MUTED))
        y += 30
        for line in measure.wrap(scene['title'], canvas.column, TITLE, 700):
            out.append(_text(canvas.margin, y, line, size=TITLE, weight=700))
            y += LINE[TITLE]
        y += 4
        for line in measure.wrap(scene['subtitle'], canvas.column, SUBTITLE):
            out.append(_text(canvas.margin, y, line, size=SUBTITLE))
            y += LINE[SUBTITLE]
        y += 12
    ...  # the panel loop, with COLUMN -> canvas.column, MARGIN -> canvas.margin, WIDTH -> canvas.width
    if frame == 'page':
        ...  # the divider line and footer, unchanged
    height = int(y + canvas.margin - 8)
    document = (f'<svg xmlns="{SVG_NAMESPACE}" viewBox="0 0 {canvas.width} {height}" font-family="Arial, sans-serif" '
                f'font-size="{BODY}" fill="{TEXT}">' + ''.join(out) + '</svg>')
    return normalize_svg(document, profile='overview'), placements
```

When `frame == 'panel'`, after the panel loop set `y = max(bottoms) - 18` so the panel frame ends `canvas.margin` above the bottom edge.

`normalize_svg(..., profile='overview')` accepts a 640-wide document: `SVG_PROFILES['overview']` in `papers/html_figures.py:29` allows a viewBox width from 40 to 20000 and five times the panel element budget, checked on 2026-09-18.

- [ ] **Step 6: Reduce `scene_layout.py` to aliases**

Replace the body of `papers/scene_layout.py` with:

```python
"""Compatibility aliases until the workflows import papers.figures directly."""
from papers.figures.layout import Canvas
from papers.figures.measure import Measurer
from papers.figures.render import LayoutError as SceneLayoutError, compose
from papers.figures.schema import headings as scene_headings, text as scene_text


def compose_scene(directory, paper_title, scene, *, with_tree=False):
    measure = Measurer(directory)
    try:
        svg, placements = compose(measure, scene, Canvas(1000), frame='page', page_title=paper_title)
    finally:
        measure.close()
    return (svg, placements, scene) if with_tree else (svg, placements)
```

`with_tree` returned the laid-out copy before. Check with `grep -rn "with_tree" papers tests`; if nothing outside `scene_layout.py` passes it, drop the parameter.

Update `tests/test_scene_layout.py` imports: `_crosses`, `_segments`, and `route` come from `papers.figures.route` as `crosses`, `segments`, `route`.

- [ ] **Step 7: Run the tests and the baseline**

Run: `.venv/bin/python -m unittest tests.test_layout_canvas tests.test_scene_layout tests.test_scene_schema -v && .venv/bin/python tests/baseline_scenes.py --compare`
Expected: PASS, every baseline line `same`. If a baseline differs, the cause is a changed float format or a changed constant; fix the move, never the baseline.

- [ ] **Step 8: Commit**

```sh
git add papers/figures/layout.py papers/figures/route.py papers/figures/render.py papers/scene_layout.py
git commit -m "Split the scene layout into layout, route, and render modules with a Canvas width"
```

### Task 5: Add `checks.py` and the `Figure` class

**Files:**
- Create: `papers/figures/checks.py`
- Modify: `papers/figures/__init__.py`
- Test: `tests/test_figure.py` (new, local)

**Interfaces:**
- Produces:
  - `checks.text_density(checks) -> float`, `checks.MIN_TEXT_DENSITY = 30`, `checks.native_issues(checks) -> list[str]`.
  - `Figure(measurer_factory=None, *, width=1000)`. `measurer_factory(directory)` returns a `Measurer`; `None` means the WebKit `Measurer`.
  - `Figure.validate(value, *, frame='page') -> dict`
  - `Figure.text(value, *, frame='page') -> list[str]`
  - `Figure.headings(value, *, frame='page') -> list[str]`
  - `Figure.missing(value, required, *, frame='page') -> list[str]`
  - `Figure.build(value, directory, figure_id, *, frame='page', page_title='') -> FigureResult`
  - `FigureResult` dataclass: `svg: str`, `assets: dict` (`html`, `svg`, `png`, `pdf`, `svg_source` relative paths), `checks: dict`, `placements: list`, `density: float`, `issues: list[str]`.
  - `SceneError` re-exported from `schema`; `LayoutError` re-exported from `render`.

- [ ] **Step 1: Write the failing test**

```python
"""Figure builds a page or a panel from a Scene and reports issues without raising."""
import json
import tempfile
import unittest
from pathlib import Path

from papers.figures import Figure, FigureResult, SceneError
from papers.figures.measure import FixedMeasurer

FIXTURES = Path(__file__).resolve().parent / 'fixtures' / 'overview'


class FigureTests(unittest.TestCase):
    def setUp(self):
        self.scene = json.loads((FIXTURES / 'attention-scene.json').read_text())

    def test_missing_reports_absent_strings_only(self):
        figure = Figure(lambda directory: FixedMeasurer())
        self.assertEqual(figure.missing(self.scene, ['Query Q', 'not in the scene']), ['not in the scene'])

    def test_validate_raises_scene_error(self):
        with self.assertRaises(SceneError):
            Figure().validate({'panels': []})

    def test_build_page_renders_through_the_native_helper(self):
        with tempfile.TemporaryDirectory() as directory:
            result = Figure(width=1000).build(self.scene, directory, 'fig1', frame='page',
                                              page_title='Attention Is All You Need')
            self.assertIsInstance(result, FigureResult)
            self.assertEqual(result.issues, [])
            self.assertGreater(result.density, 30)
            self.assertTrue((Path(directory) / result.assets['png']).is_file())
            self.assertTrue((Path(directory) / result.assets['svg_source']).is_file())

    def test_build_panel_at_640(self):
        with tempfile.TemporaryDirectory() as directory:
            result = Figure(width=640).build(self.scene['panels'][0], directory, 'fig1', frame='panel')
            self.assertEqual(result.checks['canvas']['width'], 640)
            self.assertEqual([issue for issue in result.issues if 'too small' in issue], [])
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/python -m unittest tests.test_figure -v`
Expected: FAIL with `ImportError: cannot import name 'Figure'`.

- [ ] **Step 3: Write `checks.py`**

Move `text_density` and `MIN_TEXT_DENSITY` from `papers/overview_workflow.py:45, 675-680` and add `native_issues`:

```python
"""Checks on a rendered figure: native renderer defects and text density."""
MIN_TEXT_DENSITY = 30


def text_density(checks):
    """Text runs per million square units of the rendered canvas."""
    canvas = checks.get('canvas') or {}
    area = float(canvas.get('width') or 0) * float(canvas.get('height') or 0)
    if area <= 0:
        return 0.0
    return len(checks.get('text_runs') or []) / (area / 1e6)


def native_issues(checks):
    """One message per native defect, in the renderer's order."""
    return [str(issue.get('message') or issue.get('code')) for issue in checks.get('issue_details') or []]
```

- [ ] **Step 4: Write the `Figure` class in `__init__.py`**

```python
"""The figure library: a Scene in, laid-out SVG, PNG, checks, and issues out."""
import re
from dataclasses import dataclass, field

from papers import html_figures
from papers.figures import schema
from papers.figures.checks import MIN_TEXT_DENSITY, native_issues, text_density
from papers.figures.layout import Canvas
from papers.figures.measure import Measurer
from papers.figures.render import LayoutError, compose
from papers.figures.schema import SceneError

__all__ = ['Figure', 'FigureResult', 'SceneError', 'LayoutError']
_SPACE = re.compile(r'\s+')


def _flat(value):
    return _SPACE.sub(' ', str(value)).strip().lower()


@dataclass
class FigureResult:
    svg: str
    assets: dict
    checks: dict
    placements: list
    density: float
    issues: list = field(default_factory=list)


class Figure:
    """Lay out, render, and check Scenes at one width. Makes no provider call."""

    def __init__(self, measurer_factory=None, *, width=1000):
        self.measurer_factory = measurer_factory or Measurer
        self.canvas = Canvas(width)

    @staticmethod
    def _page(value, frame):
        if frame == 'panel':
            return {'title': '', 'subtitle': '', 'footer': '', 'illustrative': False,
                    'layout': 'stack', 'panels': [value]}
        return value

    def validate(self, value, *, frame='page'):
        return schema.validate(value, frame=frame)

    def text(self, value, *, frame='page'):
        return schema.text(self._page(value, frame))

    def headings(self, value, *, frame='page'):
        return schema.headings(self._page(value, frame))

    def missing(self, value, required, *, frame='page'):
        shown = _flat(' '.join(self.text(value, frame=frame)))
        return [item for item in required if _flat(item) not in shown]

    def build(self, value, directory, figure_id, *, frame='page', page_title=''):
        """Compose, rasterize, and check. Raises SceneError or LayoutError; defects are issues."""
        if frame == 'panel' and page_title:
            raise ValueError('page_title applies to frame page only')
        scene = self._page(self.validate(value, frame=frame), frame)
        measure = self.measurer_factory(directory)
        try:
            svg, placements = compose(measure, scene, self.canvas, frame=frame, page_title=page_title)
        finally:
            measure.close()
        assets = html_figures.render(directory, {'id': figure_id, 'title': scene.get('title') or figure_id,
                                                 'source_svg': svg}, page_title, mode='overview')
        checks = assets.pop('checks')
        density = text_density(checks)
        issues = native_issues(checks)
        if frame == 'page' and density < MIN_TEXT_DENSITY:
            issues.append('The figure is too sparse: ' + str(round(density, 1))
                          + ' text runs per million square units; the floor is ' + str(MIN_TEXT_DENSITY))
        return FigureResult(svg=svg, assets=assets, checks=checks, placements=placements,
                            density=density, issues=issues)
```

- [ ] **Step 5: Run the tests**

Run: `.venv/bin/python -m unittest tests.test_figure -v`
Expected: PASS. The two `build` tests need `LOCALXIV_HTML_RENDERER`.

- [ ] **Step 6: Commit**

```sh
git add papers/figures/__init__.py papers/figures/checks.py
git commit -m "Add the Figure class that validates, lays out, renders, and checks a Scene"
```

### Task 6: Extract `papers/coordinator.py` and make `OverviewWorkflow`

**Files:**
- Create: `papers/coordinator.py`
- Modify: `papers/overview_workflow.py` (whole file)
- Test: `tests/test_overview_workflow.py` (new, local)

**Interfaces:**
- Produces in `papers/coordinator.py`, moved unchanged from `papers/overview_workflow.py`: `RunStore` (189-237), `create_run_directory` (238), `is_cancelled` (246, underscore dropped), `finalize_run` (250, underscore dropped), `panel_digest` (269), `provider_options` (276), `is_transient` (287), `Coordinator` (295-402), `validation_paths`, `validation_messages`, `request_object`, `request_validated` (405-484, underscores dropped), `evidence_text`, `source_map`, `merge_evidence`, `select_evidence`, `supplement_evidence` (486-570, underscores dropped), `TRANSIENT_MARKERS`, `RETRY_BACKOFF_SECONDS`, `RETRY_SUFFIX`, `RUN_STATES`, `TERMINAL_RUN_STATES`, `iso`, `read_json`, `write_json`.
- `select_evidence(coordinator, document, orientation, *, vision, instruction=SELECTION_INSTRUCTION)` gains the `instruction` keyword so the Blog can pass its own prompt. `SELECTION_INSTRUCTION` moves with it.
- Produces in `papers/overview_workflow.py`: `class OverviewWorkflow` with `__init__(self, provider, document, progress, *, vision=False, run_directory=None)` and `run(self) -> dict` (the saved generation), plus the thin `generate(provider, document, progress, *, vision=False)` that returns `OverviewWorkflow(...).run()`. `plan_overview` stays as a function for `tools/overview_run.py` only if that tool imports it; check with `grep -n plan_overview tools/overview_run.py`. It imports `generate` only, so `plan_overview` becomes the method `OverviewWorkflow.plan`.

- [ ] **Step 1: Write the failing test**

```python
"""OverviewWorkflow runs selection, digest, scene, and render against a fake provider."""
import json
import tempfile
import unittest
from pathlib import Path

from papers.overview_workflow import OverviewWorkflow, generate

FIXTURES = Path(__file__).resolve().parent / 'fixtures' / 'overview'


class FakeProvider:
    """Answers each stage from a queue of JSON texts, in request order."""

    def __init__(self, answers):
        self.answers = list(answers)
        self.settings = {'model': 'fake', 'endpoint': 'https://fake.test/v1'}
        self.requests = []

    def complete(self, messages, **options):
        self.requests.append(messages)
        return {'text': json.dumps(self.answers.pop(0)), 'usage': {'total_tokens': 1}}


class OverviewWorkflowTests(unittest.TestCase):
    def test_run_saves_scene_and_figure(self):
        scene = json.loads((FIXTURES / 'attention-scene.json').read_text())
        digest = json.loads((FIXTURES / 'attention-digest.json').read_text())
        selection = json.loads((FIXTURES / 'attention-selection.json').read_text())
        document = json.loads((FIXTURES / 'attention-document.json').read_text())
        with tempfile.TemporaryDirectory() as directory:
            document['directory'] = directory
            provider = FakeProvider([selection, digest, scene])
            result = generate(provider, document, lambda label: None)
            self.assertEqual(result['figures'][0]['id'], 'fig1')
            self.assertEqual(result['plan'], digest)
            run = Path(directory) / result['provenance']['run']
            self.assertTrue((run / 'scene.json').is_file())
            self.assertEqual(len(provider.requests), 3)
```

The three fixture files `attention-digest.json`, `attention-selection.json`, and `attention-document.json` do not exist yet. Paper records and saved generations live in `library.sqlite3`, not in files (`tools/overview_run.py:load` reads `select value from papers`). Write `tests/make_fixtures.py` (local) once and run it:

```python
"""Extract the Attention paper, its saved Overview digest, and its selection into tests/fixtures/overview/."""
import json
import sqlite3
from pathlib import Path

LIBRARY = Path.home() / 'Library' / 'Application Support' / 'LocalXiv' / 'library' / 'library.sqlite3'
OUT = Path(__file__).resolve().parent / 'fixtures' / 'overview'
db = sqlite3.connect(LIBRARY)
paper = next(json.loads(row[0]) for row in db.execute('select value from papers')
             if 'attention is all you need' in json.loads(row[0]).get('title', '').lower())
generation = json.loads(db.execute('select value from generations where paper=? and kind=?',
                                   (paper['id'], 'overview')).fetchone()[0])
paper.pop('directory', None)
(OUT / 'attention-document.json').write_text(json.dumps(paper, ensure_ascii=False, indent=1))
(OUT / 'attention-digest.json').write_text(json.dumps(generation['plan'], ensure_ascii=False, indent=1))
(OUT / 'attention-selection.json').write_text(json.dumps(generation['provenance']['selection'], ensure_ascii=False, indent=1))
```

The saved Overview must be a Scene-era one (`plan` has `components`); the sample paper shipped with the app qualifies after the 2026-09-18 regeneration. The three files come from one paper, so every passage ID in the digest and the selection exists in the document.

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/python -m unittest tests.test_overview_workflow -v`
Expected: FAIL with `ImportError: cannot import name 'OverviewWorkflow'`.

- [ ] **Step 3: Create `papers/coordinator.py`**

Move the symbols listed under Interfaces from `papers/overview_workflow.py` into `papers/coordinator.py`, dropping the leading underscores where named. Add the `instruction` keyword to `select_evidence`:

```python
def select_evidence(coordinator, document, orientation, *, vision, instruction=SELECTION_INSTRUCTION):
    messages = [{'role': 'user', 'content': instruction + '\n\nSOURCE MAP:\n'
                 + json.dumps(source_map(orientation), ensure_ascii=False)}]
    ...
```

- [ ] **Step 4: Rewrite `papers/overview_workflow.py` around `OverviewWorkflow`**

Keep `GENERATION_KEYS`, `PROVENANCE_KEYS`, `FIGURE_ASSET_KEYS`, `PROMPT_REVISION`, `PANEL_WORKFLOW`, `MIN_PANEL_FILL`, `ATTENTION_EXAMPLE`, `VARIETY_EXAMPLE`, `DIGEST_INSTRUCTION`, `SCENE_INSTRUCTION`, `document_digest_of`. Import the rest from `papers.coordinator` and `papers.figures`.

```python
class OverviewWorkflow:
    """Select, digest, scene, layout, render. One run directory owns every request."""

    def __init__(self, provider, document, progress, *, vision=False, run_directory=None):
        if not document.get('passages'):
            raise ProviderError(document.get('report', {}).get('text_warning')
                                or 'This paper has no retained passages for an overview.')
        if not document.get('directory'):
            raise ProviderError('Save the paper before generating an overview.')
        self.provider = provider
        self.document = document
        self.progress = progress
        self.vision = vision
        self.run = Path(run_directory) if run_directory else create_run_directory(document)
        RunStore(self.run)
        self.coordinator = Coordinator(provider, progress, run_directory=self.run)
        self.figure = Figure(width=1000)

    def plan(self):
        """Selection and digest. Returns digest, evidence, selection, orientation."""
        orientation = build_orientation(self.document)
        selection, evidence = select_evidence(self.coordinator, self.document, orientation, vision=self.vision)
        digest = self._digest(evidence)
        return {'digest': digest, 'evidence': evidence, 'selection': selection, 'orientation': orientation}

    def _digest(self, evidence):
        ...  # the body of plan_digest

    def _scene(self, digest):
        """A validated, covering, laid-out scene in at most three requests plus one layout correction."""
        ...  # the body of plan_scene, with these replacements:
        #   validate_scene(value)                      -> self.figure.validate(value)
        #   scene_text(scene) / scene_headings(scene)  -> self.figure.text(scene) / self.figure.headings(scene)
        #   compose_scene(directory, title, scene)     -> self.figure.build(scene, self.document['directory'], 'fig1',
        #                                                  frame='page', page_title=self.document.get('title', ''))
        #   SceneLayoutError                           -> LayoutError
        #   the density check on result.issues replaces the separate MIN_TEXT_DENSITY branch in generate

    def run_workflow(self):
        ...  # the body of generate from `plan = plan_overview(...)` to the return, using self.plan() and self._scene()

    def run(self):
        try:
            return self.run_workflow()
        except BaseException as error:
            try:
                finalize_run(self.coordinator.store, error, stage=self.coordinator.active_stage)
            except Exception:
                pass
            raise


def generate(provider, document, progress, *, vision=False):
    return OverviewWorkflow(provider, document, progress, vision=vision).run()
```

Keep the containment rule in `_scene`'s `validate` closure:

```python
        def validate(value):
            scene = self.figure.validate(value)
            collapsed = collapse_repetitions(scene)
            if collapsed:
                self.coordinator.note('scene_repetitions_collapsed', labels=collapsed[:12])
            strings = self.figure.text(scene)
            issues = (scene_coverage_issues(digest, strings, self.figure.headings(scene))
                      + example_coverage_issues(digest, strings))
            if issues:
                raise SceneError(issues[:20])
            return scene
```

`scene_coverage_issues` stays in `papers/explanation.py` because it is digest-shaped. Task 16 narrows it to the containment rule and uses `Figure.missing` for strings.

The layout loop in `_scene` becomes:

```python
        for attempt in range(2):
            try:
                result = self.figure.build(scene, self.document['directory'], 'fig1', frame='page',
                                           page_title=self.document.get('title', ''))
            except LayoutError as error:
                problem = str(error)
            else:
                narrow = [item for item in result.placements if item['fill'] < MIN_PANEL_FILL]
                if not narrow and not result.issues:
                    return scene, result
                problem = ('; '.join(...narrow message as today...) if narrow
                           else '; '.join(result.issues[:3]))
            ...  # the correction request as today
```

`run_workflow` then uses `result.assets`, `result.checks`, `result.density`, and `result.placements` where `generate` used `assets`, `checks`, `density`, and `placements`. The figure dict keeps `source_svg = result.svg`.

- [ ] **Step 5: Run the tests and the baseline**

Run: `.venv/bin/python -m unittest tests.test_overview_workflow tests.test_scene_layout -v && .venv/bin/python tests/baseline_scenes.py --compare`
Expected: PASS, every baseline line `same`.

- [ ] **Step 6: Run the CLI against a library paper**

Run: `.venv/bin/python tools/overview_run.py --paper "Attention" --model deepseek-flash`
Expected: the tool prints request count, tokens, seconds, density, and a PNG path. This spends money; skip it if no key is in `.env`, and say so in the task report.

- [ ] **Step 7: Commit**

```sh
git add papers/coordinator.py papers/overview_workflow.py
git commit -m "Extract the coordinator and run the Overview through OverviewWorkflow and Figure"
```

### Task 7: Delete `scene_layout.py` and the explanation aliases

**Files:**
- Delete: `papers/scene_layout.py`
- Modify: `papers/explanation.py` (remove the alias import from task 2 and every use of `validate_scene`, `PanelPlanError`, `SCENE_KINDS`), `papers/overview_workflow.py` (import from `papers.figures`), `tests/test_scene_layout.py`, `tests/baseline_scenes.py`

- [ ] **Step 1: Find every remaining import**

Run: `grep -rn "scene_layout\|validate_scene\|PanelPlanError\|SCENE_KINDS" papers app tools tests`
Expected: a short list. Each line is one edit in the next step.

- [ ] **Step 2: Rewrite the imports**

`papers/overview_workflow.py` imports `Figure`, `SceneError`, `LayoutError` from `papers.figures` and `collapse_repetitions` from `papers.figures.schema`. `papers/explanation.py` raises `PlanValidationError` where it raised `PanelPlanError` in digest code, and `scene_coverage_issues` returns issue dicts without raising. `tests/baseline_scenes.py` composes through `Figure`:

```python
from papers.figures.layout import Canvas
from papers.figures.measure import Measurer
from papers.figures.render import compose

def compose_scene(directory, title, scene):
    measure = Measurer(directory)
    try:
        return compose(measure, scene, Canvas(1000), frame='page', page_title=title)
    finally:
        measure.close()
```

- [ ] **Step 3: Delete the file and run everything**

```sh
git rm papers/scene_layout.py
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python tests/baseline_scenes.py --compare
grep -rn "scene_layout" papers app tools tests docs README.md
```

Expected: tests pass, baseline `same`, the grep prints only `docs/` lines (task 20 rewrites the docs).

- [ ] **Step 4: Commit**

```sh
git add papers/explanation.py papers/overview_workflow.py
git commit -m "Delete scene_layout.py now that papers/figures owns layout"
```

Phase 1 ends here. The Overview produces byte-identical SVG, the library has a boundary, and the coordinator is shared.

---

## Phase 2: the Blog on the coordinator with Scene panels, then delete the old path

### Task 8: Lock the Blog helpers that survive the move

**Files:**
- Read: `papers/agent_overviews.py:482-540, 555-660, 684-722` and `papers/blog_figures.py:119-174`
- Test: `tests/test_blog_helpers.py` (new, local)

**Interfaces:**
- Consumes the functions as they are today, by their current names. Task 10 moves them into `papers/blog_workflow.py` and this test file changes only its import line.

- [ ] **Step 1: Write the tests against the current module**

```python
"""Blog helpers: review parsing, anchors, no-progress counting, omission findings, exact edits."""
import unittest

from papers.agent_overviews import (_figure_anchor_error, _figure_issue_target, _review_response,
                                    _update_no_progress, _with_issue_ids, omission_continuity_finding)
from papers.blog_figures import apply_text_edits, remove_omitted_markers
from papers.explanation import candidate_digest

EVIDENCE = {'passages': [{'id': 'p1', 'text': 'Attention weights sum to one.'}]}


class ReviewResponseTests(unittest.TestCase):
    def _verdict(self, **overrides):
        value = {'action': 'verdict', 'approved': False, 'candidate_digest': 'd', 'issues': [],
                 'resolutions': []}
        value.update(overrides)
        return value

    def test_verdict_with_matching_digest_passes(self):
        result = _review_response(self._verdict(), EVIDENCE, candidate_digest_expected='d', findings=[],
                                  figure_ids=['fig1'], figure_labels={'fig1': 'query q keys'},
                                  article_text='Prose.')
        self.assertEqual(result['action'], 'verdict')

    def test_stale_digest_is_rejected(self):
        with self.assertRaises(ValueError):
            _review_response(self._verdict(candidate_digest='old'), EVIDENCE, candidate_digest_expected='d',
                             findings=[], figure_ids=[], figure_labels={}, article_text='')

    def test_anchor_must_be_visible_in_the_named_figure(self):
        self.assertIsNone(_figure_anchor_error('Query Q', 'fig1', {'fig1': 'query q keys'}))
        self.assertIsNotNone(_figure_anchor_error('Softmax', 'fig1', {'fig1': 'query q keys'}))

    def test_issue_target_reads_figure_ids(self):
        self.assertEqual(_figure_issue_target('fig2', ['fig1', 'fig2']), 'fig2')
        self.assertIsNone(_figure_issue_target('article', ['fig1']))


class NoProgressTests(unittest.TestCase):
    def test_a_repeated_issue_counts_up_and_a_fixed_one_drops(self):
        first = _with_issue_ids([{'code': 'plan_validation', 'path': 'text', 'message': 'too long',
                                  'actual': 1500, 'limit': 1400}])
        counters = _update_no_progress([], first, {})
        second = _with_issue_ids([{'code': 'plan_validation', 'path': 'text', 'message': 'too long',
                                   'actual': 1500, 'limit': 1400}])
        counters = _update_no_progress(first, second, counters)
        self.assertEqual(counters[second[0]['id']], 1)
        self.assertEqual(_update_no_progress(second, [], counters), {})


class OmissionTests(unittest.TestCase):
    def test_omission_finding_names_the_figure(self):
        finding = omission_continuity_finding({'id': 'fig1', 'attempts': 4, 'brief': {'title': 'Heads'}})
        self.assertEqual(finding['path'], 'article')
        self.assertIn('fig1', finding['message'])

    def test_markers_are_removed_and_edits_apply(self):
        text = 'Intro.\n\n{{figure:fig1}}\n\nSee the branch above. {{figure:fig2}} End.'
        stripped = remove_omitted_markers(text, ['fig1'])
        self.assertNotIn('fig1', stripped)
        self.assertIn('{{figure:fig2}}', stripped)
        edited = apply_text_edits(stripped, [{'old': 'See the branch above. ', 'new': ''}],
                                  base_digest=candidate_digest(stripped))
        self.assertNotIn('branch', edited)
```

- [ ] **Step 2: Run the tests**

Run: `.venv/bin/python -m unittest tests.test_blog_helpers -v`
Expected: PASS. If `_review_response` needs more of the verdict shape than the test supplies, read `papers/agent_overviews.py:585-656` and add the missing field to `_verdict`; the test documents the contract, it does not change it.

No commit; the test file is local.

### Task 9: Change the Blog contracts in `papers/explanation.py`

**Files:**
- Modify: `papers/explanation.py:45-85` (families, brief schema), `1043-1123` (`_validate_blog_brief`, `validate_blog_brief`), `919-944` (`blog_figure_assignment`, deleted)
- Test: `tests/test_blog_contracts.py` (new, local)

**Interfaces:**
- Produces:
  - `BLOG_BRIEF_SCHEMA` without `construction` and `layout_intent`.
  - `BLOG_AUTHOR_RESPONSE_SCHEMA = {'anyOf': [BLOG_DRAFT_SCHEMA, BLOG_REVISION_REQUEST_SCHEMA]}` where `BLOG_REVISION_REQUEST_SCHEMA = object_schema({'action': {'type': 'string', 'enum': ['revise_narrative']}, 'reason': PLAN_TEXT, 'passage_ids': ID_ARRAY})`.
  - `blog_panel_required(brief) -> list[str]`: `exact_text + illustrative_values`.
  - `PANEL_CONSTRUCTION_FAMILIES` and `blog_figure_assignment` are deleted.

- [ ] **Step 1: Write the failing test**

```python
"""Blog briefs carry content and required strings; construction and layout intent are gone."""
import unittest

from papers.explanation import (BLOG_AUTHOR_RESPONSE_SCHEMA, BLOG_BRIEF_SCHEMA, PlanValidationError,
                                blog_panel_required, validate_blog_brief)

DOCUMENT = {'passages': [{'id': 'p1', 'text': 'x'}]}
BRIEF = {'id': 'fig1', 'title': 'Heads', 'paper_connection': 'Section 3.', 'caption': 'Eight heads.',
         'illustrative': False, 'passages': ['p1'], 'purpose': 'Show the split.',
         'entry_context': ['The reader knows Q, K, V.'], 'exit_state': 'Sees eight heads.',
         'content': [{'text': 'h = 8', 'kind': 'value', 'passages': ['p1']}],
         'exact_text': ['h = 8', 'd_k = 64'], 'illustrative_values': ['0.62']}


class BriefTests(unittest.TestCase):
    def test_brief_validates_without_construction_and_layout_intent(self):
        validate_blog_brief(BRIEF, DOCUMENT)
        self.assertNotIn('construction', BLOG_BRIEF_SCHEMA['properties'])
        self.assertNotIn('layout_intent', BLOG_BRIEF_SCHEMA['properties'])

    def test_old_fields_are_rejected(self):
        with self.assertRaises(PlanValidationError) as caught:
            validate_blog_brief(dict(BRIEF, construction='flow'), DOCUMENT)
        self.assertIn('brief.construction', [issue['path'] for issue in caught.exception.issues])

    def test_required_strings(self):
        self.assertEqual(blog_panel_required(BRIEF), ['h = 8', 'd_k = 64', '0.62'])

    def test_author_response_allows_a_revision_request(self):
        self.assertEqual(len(BLOG_AUTHOR_RESPONSE_SCHEMA['anyOf']), 2)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/python -m unittest tests.test_blog_contracts -v`
Expected: FAIL with `ImportError: cannot import name 'BLOG_AUTHOR_RESPONSE_SCHEMA'`.

- [ ] **Step 3: Edit the contracts**

In `papers/explanation.py`: delete `PANEL_CONSTRUCTION_FAMILIES`; remove the `'construction'` and `'layout_intent'` entries from `BLOG_BRIEF_SCHEMA`; in `_validate_blog_brief` delete the `construction` check, the `_blog_text(brief, 'layout_intent', ...)` line, and both keys from the returned dict; delete `blog_figure_assignment`. Add:

```python
BLOG_REVISION_REQUEST_SCHEMA = object_schema({
    'action': {'type': 'string', 'enum': ['revise_narrative']},
    'reason': PLAN_TEXT,
    'passage_ids': ID_ARRAY,
})
BLOG_AUTHOR_RESPONSE_SCHEMA = {'anyOf': [BLOG_DRAFT_SCHEMA, BLOG_REVISION_REQUEST_SCHEMA]}


def blog_panel_required(brief):
    """Every string a Blog figure's Scene panel must show verbatim."""
    return list(brief.get('exact_text') or []) + list(brief.get('illustrative_values') or [])
```

- [ ] **Step 4: Run the tests**

Run: `.venv/bin/python -m unittest tests.test_blog_contracts tests.test_blog_helpers -v`
Expected: PASS. `test_blog_helpers` still imports from `papers.agent_overviews`, which still imports `blog_figure_assignment`; if that import now fails, remove that name from the import at `papers/agent_overviews.py:22-26` (the module is deleted in task 15 anyway).

- [ ] **Step 5: Commit**

```sh
git add papers/explanation.py papers/agent_overviews.py
git commit -m "Drop construction and layout intent from Blog briefs and add the author response schema"
```

### Task 10: Start `papers/blog_workflow.py`: setup, selection, narrative

**Files:**
- Create: `papers/blog_workflow.py`
- Move from `papers/agent_overviews.py`: the prompt constants at 30-151 (`SHARED_RULES`, `SELECTION_PROMPT`, `NARRATIVE_PROMPT`, `REVIEW_PROMPT`, `AUTHORING`, `CLEANUP_PROMPT`, `BRIEF_CORRECTION_PROMPT`, `TEXT_EDITS_SCHEMA`, `BRIEF_CORRECTION_SCHEMA`, `FIGURE_SCIENCE_CATEGORIES`), `_context_disk_value`, `write_generation_context`, `_navigation_payload`, `_known_evidence_char_limit`, `_issue_id`, `_with_issue_ids`, `omission_continuity_finding`, `_figure_issue_target`, `_ANCHOR_SEPARATOR`, `_normalized_text`, `_visible_text`, `_figure_anchor_error`, `_review_response`, `_mechanical_distance`, `_MISSING`, `_path_value`, `_update_no_progress`. Move `remove_omitted_markers` and `apply_text_edits` from `papers/blog_figures.py`.
- Test: `tests/test_blog_workflow.py` (new, local), `tests/test_blog_helpers.py` (import line)

**Interfaces:**
- Produces:
  - `PROMPT_REVISION = 'blog-scene-v1'`, `CONTEXT_REVISION = 'generation-context-v2'`, `MAX_FIGURE_CORRECTIONS = 3`.
  - `class BlogWorkflow` with `__init__(self, provider, document, progress, *, image_overview=None)`, attributes `coordinator`, `run` (the run directory), `figure = Figure(width=640)`, `language`, `length`, `shared_rules`, `orientation`, `evidence`, `selection`, `plan`, `context` (the checkpoint dict), and methods `select(self)`, `narrate(self, reason='')`, `checkpoint(self, stage, **updates)`.
  - `generate(provider, document, progress, *, image_overview=None)` thin wrapper, completed in task 14.
- Consumes: `Coordinator`, `RunStore`, `create_run_directory`, `finalize_run`, `request_validated`, `select_evidence`, `supplement_evidence`, `source_map` from `papers.coordinator`; `Figure` from `papers.figures`.

- [ ] **Step 1: Write the failing test**

`tests/test_blog_workflow.py` starts with the fake provider from task 6 (copy the class; the two test files stay independent) and:

```python
from papers.blog_workflow import BlogWorkflow

FIXTURES = Path(__file__).resolve().parent / 'fixtures' / 'overview'


def _document(directory):
    document = json.loads((FIXTURES / 'attention-document.json').read_text())
    document['directory'] = directory
    return document


def _selection():
    return json.loads((FIXTURES / 'attention-selection.json').read_text())


def _plan():
    return json.loads((FIXTURES / 'attention-blog-plan.json').read_text())


class SelectionAndNarrativeTests(unittest.TestCase):
    def test_selection_and_narrative_take_one_request_each(self):
        with tempfile.TemporaryDirectory() as directory:
            provider = FakeProvider([_selection(), _plan()])
            workflow = BlogWorkflow(provider, _document(directory), lambda label: None)
            workflow.select()
            self.assertTrue(workflow.evidence['passages'])
            workflow.narrate()
            self.assertEqual(workflow.plan['paper_type'], _plan()['paper_type'])
            self.assertEqual(len(provider.requests), 2)
            self.assertEqual(workflow.context['stage'], 'author')

    def test_an_invalid_plan_gets_one_correction(self):
        with tempfile.TemporaryDirectory() as directory:
            bad = _plan()
            bad['visual_focus'] = 'x' * 1300
            provider = FakeProvider([_selection(), bad, _plan()])
            workflow = BlogWorkflow(provider, _document(directory), lambda label: None)
            workflow.select()
            workflow.narrate()
            self.assertEqual(len(provider.requests), 3)
            self.assertEqual(provider.requests[2][-1]['role'], 'user')
            self.assertIn('rejected', provider.requests[2][-1]['content'])
```

`attention-blog-plan.json` is a valid `PLAN_SCHEMA` object for the Attention paper. Build it once by hand from the fixture document: `paper_type` `architecture`, the four claims (`question`, `contribution`, `finding`, `limitation`) each with `text` and `passages` drawn from `attention-selection.json`'s passage IDs, a `visual_focus` under 1,200 characters, and two `relationships`. `validate_plan` in `papers/explanation.py:1239` is the acceptance test; run it once in a Python shell on the file before continuing.

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/python -m unittest tests.test_blog_workflow -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'papers.blog_workflow'`.

- [ ] **Step 3: Write the module**

```python
"""The Blog: select, narrate, author, draw each figure as a Scene panel, review, repair."""
import base64
import copy
import datetime
import json
import os
import re
import tempfile
from pathlib import Path

from papers.ai import ProviderError, _evidence, _sources
from papers.coordinator import (Coordinator, RunStore, create_run_directory, finalize_run,
                                request_validated, select_evidence, supplement_evidence, write_json)
from papers.explanation import (BLOG_AUTHOR_RESPONSE_SCHEMA, BLOG_BRIEF_SCHEMA, BLOG_DRAFT_SCHEMA,
                                PLAN_SCHEMA, PlanValidationError, REVIEW_RESPONSE_SCHEMA, SELECTION_SCHEMA,
                                TEXT, blog_panel_required, candidate_digest, object_schema,
                                validate_blog_brief, validate_blog_draft, validate_plan, validate_selection)
from papers.figures import Figure, LayoutError, SceneError
from papers.figures.schema import card as scene_card, json_schema as scene_json_schema
from papers.library import document_digest
from papers.overview import LANGUAGES, LENGTHS, NARRATIVE_TIPS, WRITING_TIPS, clean_citations, overview_preferences
from papers.reading import REVISION as READING_REVISION, build_orientation, retrieve_evidence

PROMPT_REVISION = 'blog-scene-v1'
CONTEXT_REVISION = 'generation-context-v2'
MAX_FIGURE_CORRECTIONS = 3
BLOG_DISPLAY_WIDTH = 640

# ... the moved prompt constants and helpers, unchanged ...


class BlogWorkflow:
    """Owns one Blog run: its evidence, plan, article, figure states, and review loop."""

    def __init__(self, provider, document, progress, *, image_overview=None):
        if not document.get('passages'):
            raise ProviderError(document.get('report', {}).get('text_warning')
                                or 'This paper has no retained passages for an overview.')
        if not document.get('directory'):
            raise ProviderError('Save the paper before generating an overview.')
        self.provider = provider
        self.document = document
        self.progress = progress
        self.vision = bool(provider.settings.get('overview_vision', False))
        self.language, self.length = overview_preferences(provider.settings)
        self.shared_rules = (SHARED_RULES + '\n\nBLOG PREFERENCES\n' + LANGUAGES[self.language]
                             + '\nRequested Blog length: ' + LENGTHS[self.length] + '.')
        self.maximum_words = {'short': 1000, 'medium': 1400, 'large': 2600}[self.length]
        self.run = create_run_directory(document)
        self.coordinator = Coordinator(provider, progress, run_directory=self.run)
        self.figure = Figure(width=BLOG_DISPLAY_WIDTH)
        self.orientation = build_orientation(document)
        self.source_digest = document_digest(document)
        self.overview_basis = self._overview_basis(image_overview)
        self.selection = None
        self.evidence = {'passages': [], 'images': [], 'coverage': {}}
        self.plan = None
        self.plan_digest = None
        self.text = ''
        self.briefs = []
        self.figures = []          # one state dict per brief, see task 12
        self.omitted = {}
        self.cleaned_ids = set()
        self.cleanup_edits = []
        self.reviews = []
        self.open_findings = {}
        self.revised_narrative = False
        self.context_path = self.run / 'generation_context.json'
        self.context = {'run_id': self.run.name, 'context_revision': CONTEXT_REVISION,
                        'document_digest': self.source_digest, 'source_digest': document.get('source_digest'),
                        'provider': {'endpoint': provider.settings.get('endpoint'),
                                     'model': provider.settings.get('model'), 'vision': self.vision},
                        'prompt_revision': PROMPT_REVISION, 'schema_revision': PROMPT_REVISION,
                        'stage': 'selection', 'selection': None, 'evidence': self.evidence,
                        'accepted_plan': None, 'plan_digest': None, 'article_digest': None, 'briefs': [],
                        'figure_states': [], 'omitted_figures': [], 'cleanup_edits': [],
                        'draft_issues': [], 'reviews': [], 'open_findings': []}

    @staticmethod
    def _overview_basis(image_overview):
        """The saved Overview's digest and run, when it has a Scene-era plan; otherwise None."""
        if not isinstance(image_overview, dict):
            return None
        plan = image_overview.get('plan')
        if not isinstance(plan, dict) or not plan.get('components'):
            return None
        return {'digest': plan, 'run': (image_overview.get('provenance') or {}).get('run'),
                'created_at': (image_overview.get('provenance') or {}).get('created_at')}

    def checkpoint(self, stage, **updates):
        self.context.update(stage=stage, **updates)
        write_generation_context(self.context_path, self.context)

    def _stage_prompt(self, stage, body):
        return self.shared_rules + '\n\nSTAGE: ' + stage + '\n' + body + '\nOUTPUT MODE: Blog\nPAPER: ' + self.document.get('title', '')

    def select(self):
        """One validated selection request, then local retrieval, then the evidence guard."""
        limit = _known_evidence_char_limit(self.context['provider'])
        allowance = ('\nPROVIDER EVIDENCE ALLOWANCE: Select support resolving to at most ' + str(limit)
                     + ' evidence characters, using the source-map character hints.' if limit else '')
        instruction = self._stage_prompt('EVIDENCE SELECTION', SELECTION_PROMPT + allowance)
        self.selection, self.evidence = select_evidence(self.coordinator, self.document, self.orientation,
                                                        vision=self.vision, instruction=instruction)
        retrieved = len(_evidence(self.evidence['passages']))
        if limit is not None and retrieved > limit:
            raise ProviderError('The selection resolves to ' + str(retrieved) + ' evidence characters, above '
                                'the ' + str(limit) + '-character allowance for this provider account.')
        self.evidence['coverage']['revision'] = READING_REVISION
        self.checkpoint('narrative', selection=self.selection, evidence=self.evidence)

    def narrate(self, reason=''):
        """One validated plan request with the coordinator's correction loop."""
        messages = [{'role': 'user', 'content': self._stage_prompt('NARRATIVE PLANNING', NARRATIVE_PROMPT)
                     + '\n<source_map>\n' + json.dumps(_navigation_payload(self.orientation), ensure_ascii=False)
                     + '\n</source_map>\n<retrieved_evidence>\n' + _evidence(self.evidence['passages'])
                     + '\n</retrieved_evidence>\n<narrative_reason>' + reason + '</narrative_reason>'
                     + '\nReturn one JSON object matching this contract: ' + json.dumps(PLAN_SCHEMA)}]
        _, self.plan = request_validated(self.coordinator, 'narrative', messages,
                                         lambda value: validate_plan(value, {'passages': self.evidence['passages']}),
                                         stage='narrative', attempts=3, describe='plan object')
        self.plan_digest = candidate_digest(self.plan)
        write_json(self.run / 'plan.json', self.plan)
        self.checkpoint('author', accepted_plan=self.plan, plan_digest=self.plan_digest, evidence=self.evidence)
        return self.plan
```

The narrative prompt's sentence "batch all known missing IDs into one read_evidence call" describes a tool that no longer exists. Change it to: "If evidence is missing, return {"action": "read_evidence", "section_ids": [], "passage_ids": [], "figure_ids": []} naming the IDs, and the plan will be requested again with them." `request_validated` re-sends a fixed `messages` list, so a supplement cannot go through its correction loop: the retry would carry the old evidence. Handle it with a rebuild loop instead:

```python
class _EvidenceSupplemented(Exception):
    pass

    def narrate(self, reason=''):
        supplemented = False
        for _ in range(2):
            messages = self._narrative_messages(reason)

            def validate(value):
                nonlocal supplemented
                if isinstance(value, dict) and value.get('action') == 'read_evidence':
                    if supplemented:
                        raise PlanValidationError([{'code': 'plan_validation', 'path': 'plan',
                                                    'message': 'one evidence supplement per plan; return the plan'}])
                    supplemented = True
                    self.evidence = supplement_evidence(self.coordinator, self.document, self.orientation,
                                                        self.selection, self.evidence, value, vision=self.vision)
                    raise _EvidenceSupplemented()
                return validate_plan(value, {'passages': self.evidence['passages']})

            try:
                _, self.plan = request_validated(self.coordinator, 'narrative', messages, validate,
                                                 stage='narrative', attempts=3, describe='plan object')
                break
            except _EvidenceSupplemented:
                continue
        else:
            raise ProviderError('The narrative was not planned after one evidence supplement. Draft retained.')
        ...  # digest, plan.json, checkpoint as above
```

`_narrative_messages(reason)` builds the list shown earlier from the current `self.evidence`.

- [ ] **Step 4: Point the helper tests at the new module**

Change the import in `tests/test_blog_helpers.py` to `from papers.blog_workflow import (...)` with the same names.

- [ ] **Step 5: Run the tests**

Run: `.venv/bin/python -m unittest tests.test_blog_workflow tests.test_blog_helpers -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```sh
git add papers/blog_workflow.py
git commit -m "Start BlogWorkflow on the coordinator with selection and narrative as direct requests"
```

### Task 11: The authoring stage with one narrative revision

**Files:**
- Modify: `papers/blog_workflow.py`
- Test: `tests/test_blog_workflow.py`

**Interfaces:**
- Produces: `BlogWorkflow.author(self) -> dict` returning the validated draft from `validate_blog_draft`, and setting `self.plan`, `self.text`, `self.briefs`.

- [ ] **Step 1: Write the failing tests**

```python
def _draft(plan, figures=()):
    text = 'The Transformer [p1].\n\n' + '\n\n'.join('{{figure:' + brief['id'] + '}}' for brief in figures) + '\n\nEnd [p1].'
    return {'plan': plan, 'text': text, 'figures': list(figures)}


class AuthoringTests(unittest.TestCase):
    def test_author_returns_a_validated_draft(self):
        with tempfile.TemporaryDirectory() as directory:
            provider = FakeProvider([_selection(), _plan(), _draft(_plan(), [BRIEF])])
            workflow = BlogWorkflow(provider, _document(directory), lambda label: None)
            workflow.select(); workflow.narrate()
            article = workflow.author()
            self.assertEqual([brief['id'] for brief in article['figures']], ['fig1'])
            self.assertEqual(workflow.briefs[0]['id'], 'fig1')

    def test_one_narrative_revision_is_allowed(self):
        with tempfile.TemporaryDirectory() as directory:
            revision = {'action': 'revise_narrative', 'reason': 'The finding is misattributed.', 'passage_ids': ['p1']}
            provider = FakeProvider([_selection(), _plan(), revision, _plan(), _draft(_plan())])
            workflow = BlogWorkflow(provider, _document(directory), lambda label: None)
            workflow.select(); workflow.narrate()
            workflow.author()
            self.assertTrue(workflow.revised_narrative)
            self.assertEqual(len(provider.requests), 5)

    def test_a_second_revision_request_fails_the_run(self):
        with tempfile.TemporaryDirectory() as directory:
            revision = {'action': 'revise_narrative', 'reason': 'Again.', 'passage_ids': ['p1']}
            provider = FakeProvider([_selection(), _plan(), revision, _plan(), revision])
            workflow = BlogWorkflow(provider, _document(directory), lambda label: None)
            workflow.select(); workflow.narrate()
            with self.assertRaises(ProviderError):
                workflow.author()
```

`BRIEF` is the brief dict from `tests/test_blog_contracts.py`, with `passages` and content passages set to IDs that exist in `attention-document.json`. Import `ProviderError` from `papers.ai`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m unittest tests.test_blog_workflow -v`
Expected: FAIL with `AttributeError: 'BlogWorkflow' object has no attribute 'author'`.

- [ ] **Step 3: Write `author`**

```python
    def author(self):
        """Author the cited article plus zero to three briefs, within three submissions."""
        manifest = self.overview_basis['digest'] if self.overview_basis else None

        def validate(value):
            if isinstance(value, dict) and value.get('action') == 'revise_narrative':
                if self.revised_narrative:
                    raise ProviderError('The author requested a second narrative revision. Draft retained.')
                known = {item['id'] for item in self.evidence['passages']}
                refs = value.get('passage_ids')
                if (not isinstance(value.get('reason'), str) or not value['reason'].strip()
                        or not isinstance(refs, list) or not refs or set(refs) - known):
                    raise PlanValidationError([{'code': 'plan_validation', 'path': 'revise_narrative',
                                                'message': 'a revision needs a reason and known passage ids'}])
                self.revised_narrative = True
                self.narrate(value['reason'])
                raise PlanValidationError([{'code': 'plan_validation', 'path': 'plan',
                                            'message': 'the narrative was revised; author against the new plan'}])
            if not isinstance(value, dict) or value.get('plan') != self.plan:
                raise PlanValidationError([{'code': 'plan_validation', 'path': 'plan',
                                            'message': 'preserve the accepted plan unchanged'}])
            return validate_blog_draft(value, {'passages': self.evidence['passages']}, self.length)

        messages = [{'role': 'user', 'content': self._stage_prompt('AUTHOR', AUTHORING + '\n' + NARRATIVE_TIPS + '\n' + WRITING_TIPS)
                     + '\n<accepted_narrative>' + json.dumps(self.plan, ensure_ascii=False) + '</accepted_narrative>'
                     + '\n<retrieved_evidence>' + _evidence(self.evidence['passages']) + '</retrieved_evidence>'
                     + '\n<overview_digest>' + json.dumps(manifest, ensure_ascii=False) + '</overview_digest>'
                     + '\nReturn one JSON object matching this contract: ' + json.dumps(BLOG_AUTHOR_RESPONSE_SCHEMA)}]
        _, article = request_validated(self.coordinator, 'author', messages, validate, stage='author',
                                       attempts=4, describe='draft object')
        self.text = article['text']
        self.briefs = copy.deepcopy(article['figures'])
        write_json(self.run / 'draft.json', article)
        self.checkpoint('figures', accepted_plan=self.plan, plan_digest=self.plan_digest,
                        article_digest=candidate_digest(self.text), briefs=self.briefs)
        return article
```

The revision path re-asks the author through the correction loop, and the correction message carries the new plan because `messages` is rebuilt from `self.plan` on the retry. Rebuild `messages` inside a small closure called on each attempt: `request_validated` takes a fixed list, so wrap it: after a revision, call `self.author()` once more recursively with `attempts` still bounded by `revised_narrative`. The simplest implementation that passes the three tests is to catch the revision inside `validate`, run `narrate`, and then raise `ProviderError` only when a second revision arrives; the recursion happens in `validate` through `self.narrate`, and the retry uses the same `messages` list with the stale plan in `<accepted_narrative>`. That is wrong. Rebuild the messages instead:

```python
        for _ in range(2):
            messages = self._author_messages(manifest)
            try:
                _, article = request_validated(self.coordinator, 'author', messages, validate,
                                               stage='author', attempts=3, describe='draft object')
                break
            except _NarrativeRevised:
                continue
        else:
            raise ProviderError('The author did not submit a valid Blog draft. Draft retained.')
```

with `class _NarrativeRevised(Exception)` raised by `validate` after `self.narrate(reason)` instead of the second `PlanValidationError`, and `_author_messages(manifest)` building the list above. Update AUTHORING's last paragraph: replace the sentences that name `submit_draft` and `request_narrative_revision` with "Return the draft object, or {"action": "revise_narrative", "reason", "passage_ids"} when the accepted narrative is wrong. One revision is allowed."

- [ ] **Step 4: Run the tests**

Run: `.venv/bin/python -m unittest tests.test_blog_workflow -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```sh
git add papers/blog_workflow.py
git commit -m "Author the Blog as one direct request with a single narrative revision"
```

### Task 12: Draw each Blog figure as a Scene panel through `Figure`

**Files:**
- Modify: `papers/blog_workflow.py`
- Test: `tests/test_blog_workflow.py`

**Interfaces:**
- Produces:
  - `BlogWorkflow.draw_figure(self, state, issues=()) -> dict`. A state is `{'id', 'brief', 'status': 'pending'|'accepted'|'omitted', 'requests': int, 'corrections': int, 'panel': dict|None, 'result': FigureResult|None, 'labels': list[str], 'issues': list, 'history': list}`.
  - `BlogWorkflow.draw_all(self)`: draws every pending state, records omissions, runs `cleanup_omitted`.
  - `BlogWorkflow.publish_figures(self) -> list[dict]` with keys `id`, `title`, `paper_connection`, `caption`, `illustrative`, `passages`, `source_svg`, the asset keys, `checks`, `dimensions`, `alt`, `brief`, `panel`, `labels`.
  - `PANEL_WRAPPER` and `PANEL_EXAMPLE` constants: the Blog's wrapper text and one single-panel example.
  - `BlogWorkflow.cleanup_omitted(self, new_ids)` and `text_edit_request(self, stage, label, task, *, base_text, figure_ids)`, moved from the closures with `self.` in place of the nonlocals.
- Consumes: `Figure.validate/missing/build` with `frame='panel'`; `scene_card()` from task 16 does not exist yet, so this task sends `SCENE_INSTRUCTION`'s node-kind section verbatim as `VOCABULARY` and task 16 replaces it.

- [ ] **Step 1: Write the failing tests**

```python
PANEL = json.loads((FIXTURES / 'attention-scene.json').read_text())['panels'][0]


def _panel_with(strings):
    panel = copy.deepcopy(PANEL)
    panel['notes'] = [' · '.join(strings)]
    return panel


class FigureTests(unittest.TestCase):
    def _workflow(self, directory, answers):
        provider = FakeProvider([_selection(), _plan(), _draft(_plan(), [BRIEF]), *answers])
        workflow = BlogWorkflow(provider, _document(directory), lambda label: None)
        workflow.select(); workflow.narrate(); workflow.author()
        return provider, workflow

    def test_a_covering_panel_is_accepted_on_the_first_request(self):
        with tempfile.TemporaryDirectory() as directory:
            provider, workflow = self._workflow(directory, [_panel_with(BRIEF['exact_text'] + BRIEF['illustrative_values'])])
            workflow.draw_all()
            state = workflow.figures[0]
            self.assertEqual(state['status'], 'accepted')
            self.assertEqual(state['requests'], 1)
            published = workflow.publish_figures()
            self.assertEqual(published[0]['dimensions']['width'], 640)
            self.assertIn('h = 8', ' '.join(published[0]['labels']))

    def test_missing_strings_get_a_correction(self):
        with tempfile.TemporaryDirectory() as directory:
            provider, workflow = self._workflow(directory, [PANEL, _panel_with(BRIEF['exact_text'] + BRIEF['illustrative_values'])])
            workflow.draw_all()
            self.assertEqual(workflow.figures[0]['status'], 'accepted')
            self.assertEqual(workflow.figures[0]['corrections'], 1)
            self.assertIn('d_k = 64', provider.requests[-1][-1]['content'])

    def test_four_failures_omit_and_clean(self):
        with tempfile.TemporaryDirectory() as directory:
            edits = {'base_digest': None, 'edits': [{'old': 'The Transformer [p1].', 'new': 'The Transformer [p1]. Prose.'}]}
            provider, workflow = self._workflow(directory, [PANEL, PANEL, PANEL, PANEL, edits])
            provider.digest_edits = True
            workflow.draw_all()
            self.assertEqual(workflow.figures[0]['status'], 'omitted')
            self.assertEqual(workflow.figures[0]['requests'], 4)
            self.assertNotIn('{{figure:fig1}}', workflow.text)
```

The last test needs the fake to fill `base_digest` from the request, because the digest is only known at request time. Extend `FakeProvider.complete`: when `getattr(self, 'digest_edits', False)` and the next answer has `'base_digest': None`, read `CURRENT TEXT DIGEST: <digest>` from the last user message with a regular expression and set it.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m unittest tests.test_blog_workflow -v`
Expected: FAIL with `AttributeError: 'BlogWorkflow' object has no attribute 'draw_all'`.

- [ ] **Step 3: Write the figure stage**

```python
PANEL_WRAPPER = '''Draw one Blog figure as one panel object: {"id": the figure id, "heading" ≤80,
"body": one node, "notes"?: [≤2 lines ≤160], "edges"?: [≤12 arrows between cards in this panel]}.
The panel is 640 units wide; the application decides every size, gap, and coordinate. Every
string in <required> must appear verbatim in a card label, a card detail, a step, or a note.
Show the content items in order. Draw no title, subtitle, caption, or footer: the article
carries them. Return the panel object only.'''

PANEL_EXAMPLE = json.dumps({
    'id': 'fig1', 'heading': 'Scaled dot-product attention on three tokens',
    'body': {'kind': 'group', 'arrange': 'row', 'children': [
        {'kind': 'sequence', 'items': [{'text': 'The', 'sub': 'k1'}, {'text': 'Law', 'sub': 'k2'},
                                       {'text': 'its', 'sub': 'q', 'tone': 'green', 'hot': True}]},
        {'kind': 'steps', 'lines': ['scores q·k = [3.0, 1.0, 0.4]', 'scale ÷ √d_k = ÷ 8',
                                    'softmax → [0.62, 0.23, 0.15]']}]},
    'notes': ['Weights sum to 1'], 'edges': []}, ensure_ascii=False)


def new_figure_state(brief):
    return {'id': brief['id'], 'brief': copy.deepcopy(brief), 'status': 'pending', 'requests': 0,
            'corrections': 0, 'panel': None, 'result': None, 'labels': [], 'issues': [], 'history': []}


class BlogWorkflow:
    ...

    def _panel_messages(self, brief, vocabulary):
        return [{'role': 'user', 'content': self.shared_rules + '\n\nSTAGE: FIGURE\n' + vocabulary + '\n\n' + PANEL_WRAPPER
                 + '\n\nOne complete example of the object:\n' + PANEL_EXAMPLE
                 + '\n\n<brief>\n' + json.dumps({key: brief[key] for key in ('id', 'title', 'purpose', 'entry_context',
                                                                              'exit_state', 'content')}, ensure_ascii=False)
                 + '\n</brief>\n<required>\n' + json.dumps(blog_panel_required(brief), ensure_ascii=False) + '\n</required>'}]

    def draw_figure(self, state, issues=()):
        """One panel request plus corrections, bounded by MAX_FIGURE_CORRECTIONS over the run."""
        state = copy.deepcopy(state)
        brief = state['brief']
        required = blog_panel_required(brief)
        remaining = 1 + MAX_FIGURE_CORRECTIONS - state['requests']
        if remaining <= 0:
            state['status'] = 'omitted'
            return state
        pending = [str(issue.get('message') if isinstance(issue, dict) else issue) for issue in issues]

        def validate(value):
            panel = self.figure.validate(value, frame='panel')
            if panel.get('id') != brief['id']:
                raise SceneError([{'code': 'scene_validation', 'path': 'panel.id', 'message': 'must be ' + brief['id']}])
            missing = self.figure.missing(panel, required, frame='panel')
            if missing:
                raise SceneError([{'code': 'scene_coverage', 'path': 'panel', 'value': item,
                                   'message': 'the panel does not show ' + json.dumps(item) + ' verbatim'} for item in missing])
            return panel

        messages = self._panel_messages(brief, VOCABULARY)
        if pending:
            messages.append({'role': 'user', 'content': 'A review found: ' + '; '.join(pending) + '. Return the corrected panel object.'})
        before = self.coordinator.requests
        try:
            raw, panel = request_validated(self.coordinator, 'figure_' + brief['id'], messages, validate,
                                           stage='figures', attempts=min(remaining, 3), describe='panel object')
            result = self.figure.build(panel, self.document['directory'], brief['id'], frame='panel')
            if result.issues:
                remaining -= self.coordinator.requests - before
                correction = 'The panel rendered with defects: ' + '; '.join(result.issues[:3]) + ' Return the corrected panel object.'
                raw, panel = request_validated(self.coordinator, 'figure_' + brief['id'] + '_layout', messages + [
                    {'role': 'assistant', 'content': json.dumps(raw, ensure_ascii=False)},
                    {'role': 'user', 'content': correction}], validate, stage='figures',
                    attempts=max(1, min(remaining, 1)), describe='panel object')
                result = self.figure.build(panel, self.document['directory'], brief['id'], frame='panel')
        except (ProviderError, LayoutError) as error:
            state['requests'] += self.coordinator.requests - before
            state['issues'] = [str(error)[:400]]
            state['status'] = 'omitted' if state['requests'] >= 1 + MAX_FIGURE_CORRECTIONS else 'pending'
            state['history'].append({'requests': state['requests'], 'status': state['status'], 'error': str(error)[:400]})
            if state['status'] == 'pending':
                return self.draw_figure(state)
            return state
        state['requests'] += self.coordinator.requests - before
        state['corrections'] = state['requests'] - 1
        state['panel'] = panel
        state['result'] = result
        state['labels'] = self.figure.text(panel, frame='panel')
        state['issues'] = list(result.issues)
        state['status'] = 'accepted' if not result.issues else 'omitted'
        state['history'].append({'requests': state['requests'], 'status': state['status'], 'issues': state['issues']})
        return state
```

After a `ProviderError` the recursive `draw_figure` call re-sends the original messages without the rejected answer, so a request after a transport failure starts from the brief again. This is accepted; the pilot's correction counts include those requests.

`VOCABULARY` for this task is the text of `SCENE_INSTRUCTION` from `papers/overview_workflow.py` between the line `Node kinds, all with "kind":` and the line before `The running example from the digest`, copied into `papers/blog_workflow.py` as a constant. Task 16 replaces it with `scene_card()`.

`draw_all`, `publish_figures`, `cleanup_omitted`, `text_edit_request`, `_text_edits_response`, and `_validate_article_text` are the closures from `papers/agent_overviews.py:1120-1330` rewritten as methods: `nonlocal current_text` becomes `self.text`, `figure_states` becomes `self.figures`, `request(...)` becomes `request_validated(self.coordinator, ..., validate, ...)` with a validator that runs `_text_edits_response` and `apply_text_edits` and `_validate_article_text`, and `cleanup_edits.append` becomes `self.cleanup_edits.append`. `publish_figures` builds each figure from the state:

```python
    def publish_figures(self):
        published = []
        for state in self.figures:
            if state['status'] != 'accepted' or state['result'] is None:
                continue
            brief, result = state['brief'], state['result']
            figure = {key: brief[key] for key in ('id', 'title', 'paper_connection', 'caption', 'illustrative', 'passages')}
            figure.update(result.assets, source_svg=result.svg, checks=result.checks,
                          dimensions=result.checks['canvas'], alt=brief['title'] + '. ' + brief['caption'],
                          brief=copy.deepcopy(brief), panel=copy.deepcopy(state['panel']), labels=list(state['labels']))
            published.append(figure)
        return published
```

The checkpoint's `figure_states` must stay JSON: write `{key: value for key, value in state.items() if key != 'result'}` plus `result_assets` when a result exists.

- [ ] **Step 4: Run the tests**

Run: `.venv/bin/python -m unittest tests.test_blog_workflow -v`
Expected: PASS. The build tests need `LOCALXIV_HTML_RENDERER`.

- [ ] **Step 5: Commit**

```sh
git add papers/blog_workflow.py
git commit -m "Draw each Blog figure as a Scene panel through Figure with bounded corrections"
```

### Task 13: Port the review loop, article cleanup, and brief correction

**Files:**
- Modify: `papers/blog_workflow.py`
- Test: `tests/test_blog_workflow.py`

**Interfaces:**
- Produces: `BlogWorkflow.review(self) -> dict` (one verdict), `BlogWorkflow.cleanup_article(self, issues)`, `BlogWorkflow.correct_brief(self, state, issues) -> dict`, `BlogWorkflow.review_loop(self)`.
- Consumes: `_review_response`, `_figure_issue_target`, `omission_continuity_finding`, `FIGURE_SCIENCE_CATEGORIES`, `MAX_FIGURE_CORRECTIONS`.

- [ ] **Step 1: Write the failing tests**

```python
def _verdict(digest_placeholder=True, approved=True, issues=()):
    return {'action': 'verdict', 'approved': approved, 'candidate_digest': None if digest_placeholder else 'x',
            'issues': list(issues), 'resolutions': []}


class ReviewTests(unittest.TestCase):
    def _workflow(self, directory, answers):
        provider = FakeProvider([_selection(), _plan(), _draft(_plan(), [BRIEF]),
                                 _panel_with(BRIEF['exact_text'] + BRIEF['illustrative_values']), *answers])
        provider.digest_edits = True
        workflow = BlogWorkflow(provider, _document(directory), lambda label: None)
        workflow.select(); workflow.narrate(); workflow.author(); workflow.draw_all()
        return provider, workflow

    def test_an_approving_verdict_ends_the_loop(self):
        with tempfile.TemporaryDirectory() as directory:
            provider, workflow = self._workflow(directory, [_verdict()])
            workflow.review_loop()
            self.assertTrue(workflow.reviews[-1]['approved'])

    def test_a_figure_finding_spends_one_scene_correction(self):
        with tempfile.TemporaryDirectory() as directory:
            finding = {'category': 'readability', 'path': 'fig1', 'message': 'The arrow direction is unclear.',
                       'passages': [], 'anchor': 'Query Q'}
            provider, workflow = self._workflow(directory, [
                _verdict(approved=False, issues=[finding]),
                _panel_with(BRIEF['exact_text'] + BRIEF['illustrative_values']),
                _verdict()])
            workflow.review_loop()
            self.assertEqual(workflow.figures[0]['requests'], 2)
            self.assertTrue(workflow.reviews[-1]['approved'])

    def test_an_article_finding_is_fixed_with_exact_edits(self):
        with tempfile.TemporaryDirectory() as directory:
            finding = {'category': 'unsupported_claim', 'path': 'article', 'message': 'Quote: "End [p1]."',
                       'passages': ['p1'], 'anchor': ''}
            edits = {'base_digest': None, 'edits': [{'old': 'End [p1].', 'new': 'End, per the paper [p1].'}]}
            provider, workflow = self._workflow(directory, [_verdict(approved=False, issues=[finding]), edits, _verdict()])
            workflow.review_loop()
            self.assertIn('per the paper', workflow.text)
```

Extend `FakeProvider` again: when an answer has `'candidate_digest': None`, fill it from `CURRENT CANDIDATE DIGEST: <digest>` in the last user message. The review request content is a list of parts when vision is on; the fake reads the text of the first part in that case.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m unittest tests.test_blog_workflow -v`
Expected: FAIL with `AttributeError: 'BlogWorkflow' object has no attribute 'review_loop'`.

- [ ] **Step 3: Port the closures as methods**

Move `review_blog` (as `review`), `review_read_evidence`, `_prose_no_progress`, `cleanup_article`, `correct_brief`, `figure_outcomes`, `close_omitted_figure`, and the `while True` verdict loop (as `review_loop`) from `papers/agent_overviews.py:1330-1520` into `BlogWorkflow`. Replace every `request(stage, label, messages, digest=..., issue_codes=...)` with `request_validated(self.coordinator, label, messages, validate, stage=stage, attempts=2, describe=...)`, where `validate` is the function the old code called on `raw`. The review's `figure_labels` are `{state['id']: _visible_text(state['labels']) for state in self.figures if state['status'] == 'accepted'}`. The verdict ceiling is `1 + (MAX_FIGURE_CORRECTIONS + 2) * len(self.briefs) + 2`. A figure finding on an accepted state with requests left calls `self.draw_figure(state, issues=target_issues)`; on a state with `requests >= 1 + MAX_FIGURE_CORRECTIONS` it omits and cleans as today. `correct_brief` stays: a science-category finding first corrects the brief, then draws again with the new required strings.

Vision review attaches each published figure's PNG from `result.assets['png']` exactly as before.

- [ ] **Step 4: Run the tests**

Run: `.venv/bin/python -m unittest tests.test_blog_workflow tests.test_blog_helpers -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```sh
git add papers/blog_workflow.py
git commit -m "Port the Blog review loop, article cleanup, and brief correction to BlogWorkflow"
```

### Task 14: Save the Blog, route the app to it, and run it end to end

**Files:**
- Modify: `papers/blog_workflow.py`, `papers/ai.py:238-243`, `papers/overview_workflow.py:35-36` (`PROVENANCE_KEYS`)
- Test: `tests/test_blog_workflow.py`

**Interfaces:**
- Produces: `BlogWorkflow.run(self) -> dict` with the keys in `GENERATION_KEYS`, and `generate(provider, document, progress, *, image_overview=None)`.
- Provenance keys: as today minus `agent_type` and `svg_profile_revision`, plus `run`, `figure_outcomes` (`id`, `status`, `requests`, `corrections`, `issues`), `overview_basis` from `_overview_basis`.

- [ ] **Step 1: Write the failing test**

```python
class EndToEndTests(unittest.TestCase):
    def test_generate_returns_a_saved_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            provider = FakeProvider([_selection(), _plan(), _draft(_plan(), [BRIEF]),
                                     _panel_with(BRIEF['exact_text'] + BRIEF['illustrative_values']), _verdict()])
            provider.digest_edits = True
            result = generate(provider, _document(directory), lambda label: None)
            self.assertEqual(sorted(result), sorted(['text', 'explanation', 'plan', 'cited_text', 'figures', 'evidence', 'provenance']))
            self.assertEqual(result['figures'][0]['id'], 'fig1')
            self.assertNotIn('agent_type', result['provenance'])
            self.assertEqual(result['provenance']['prompt_revision'], 'blog-scene-v1')
            self.assertEqual(result['provenance']['figure_outcomes'][0]['requests'], 1)
            self.assertTrue((Path(directory) / result['provenance']['run'] / 'candidate.json').is_file())

    def test_ai_routes_the_blog_here(self):
        from papers import ai
        import inspect
        self.assertIn('papers.blog_workflow', inspect.getsource(ai.generate_overview))
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/python -m unittest tests.test_blog_workflow.EndToEndTests -v`
Expected: FAIL with `ImportError: cannot import name 'generate'`.

- [ ] **Step 3: Write `run` and `generate`, and route**

```python
    def run_workflow(self):
        self.checkpoint('selection')
        self.select()
        self.narrate()
        self.author()
        self.figures = [new_figure_state(brief) for brief in self.briefs]
        self.draw_all()
        self.review_loop()
        write_json(self.run / 'candidate.json', {'plan': self.plan, 'text': self.text, 'figures': self.briefs,
                                                 'figure_states': self._figure_records()})
        reading = dict(self.evidence['coverage'], revision=READING_REVISION,
                       document_digest=self.source_digest, selection=self.selection)
        events = self.coordinator.events
        return {'text': clean_citations(self.text),
                'explanation': {key: self.article[key] for key in ('paper_type', 'question', 'contribution', 'finding', 'limitation', 'passages')},
                'plan': self.plan, 'cited_text': self.text, 'figures': self.publish_figures(),
                'evidence': self.evidence['passages'],
                'provenance': {'model': self.provider.settings.get('model'), 'document_digest': self.source_digest,
                               'source_digest': self.document.get('source_digest'), 'arxiv_id': self.document.get('arxiv_id'),
                               'evidence_format': self.document.get('format', 'epub'), 'pdf_digest': self.document.get('pdf_digest'),
                               'passages': [item['id'] for item in self.evidence['passages']],
                               'prompt_revision': PROMPT_REVISION, 'reading': reading,
                               'usage': [event for event in events if event.get('usage')], 'events': events,
                               'overview_basis': self.overview_basis, 'overview_language': self.language,
                               'overview_length': self.length, 'reviews': self.reviews, 'vision_review': self.vision,
                               'figure_outcomes': self.figure_outcomes(),
                               'omitted_figures': [{'id': state['id'], 'requests': state['requests'], 'issues': state['issues']}
                                                   for state in self.figures if state['status'] == 'omitted'],
                               'cleanup_edits': self.cleanup_edits, 'verdict_count': len(self.reviews),
                               'created_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                               'run': str(self.run.relative_to(Path(self.document['directory'])))}}

    def run(self):
        try:
            return self.run_workflow()
        except BaseException as error:
            try:
                finalize_run(self.coordinator.store, error, stage=self.coordinator.active_stage)
            except Exception:
                pass
            if isinstance(error, ProviderError):
                raise
            raise ProviderError(str(error)) from None


def generate(provider, document, progress, *, image_overview=None):
    return BlogWorkflow(provider, document, progress, image_overview=image_overview).run()
```

`self.article` is the validated draft `author` returned; store it there in task 11's `author`.

In `papers/ai.py` replace `from papers.agent_overviews import generate` with `from papers.blog_workflow import generate`. In `papers/overview_workflow.py` remove `'svg_profile_revision'` from `PROVENANCE_KEYS` and its entry from the Overview's provenance dict. Check `grep -rn svg_profile_revision papers app` prints nothing.

- [ ] **Step 4: Run every test**

Run: `.venv/bin/python -m unittest discover -s tests -v`
Expected: PASS, including `test_panel_authoring` and `test_panel_checks`, which still exercise the old modules until task 15.

- [ ] **Step 5: Commit**

```sh
git add papers/blog_workflow.py papers/ai.py papers/overview_workflow.py
git commit -m "Save the Blog from BlogWorkflow and route the app to it"
```

### Task 15: Delete the model-drawn SVG path and smolagents

**Files:**
- Delete: `papers/agent_overviews.py`, `papers/panel_authoring.py`, `papers/blog_figures.py`, `papers/panel-guides/` (six files), `papers/html_figures.py`, `tests/test_panel_authoring.py`, `tests/test_panel_checks.py`
- Modify: `papers/figures/render.py`, `papers/figures/measure.py`, `papers/figures/__init__.py`, `requirements-ai.txt`, `app/macos/verify-release.py:96-101, 134`, `docs/cleanup.md`
- Test: `tests/test_figure.py`, `tests/baseline_scenes.py`

**Interfaces:**
- Produces: `render.rasterize(directory, svg, figure_id, title) -> dict` with the asset paths and `checks`, moved from `html_figures.render` minus the profile normalization and the `mode` switch; `measure.measure_text_widths` moved from `html_figures`; `render.SHARED_MARKERS` and `render.SVG_NAMESPACE` moved.

- [ ] **Step 1: Move the two survivors**

Move `measure_text_widths` and `SVG_DEFAULT_FONT_FAMILY` from `papers/html_figures.py:548-584` into `papers/figures/measure.py`. Move `PANEL_PAGE_STYLE`, `SHARED_MARKERS`, `SVG_NAMESPACE`, and the body of `render` (from `relative = Path('reader/overview-figures') ...` to the return) into `papers/figures/render.py` as:

```python
def rasterize(directory, svg, figure_id, title):
    """Write the SVG page, run the native renderer, and return asset paths plus checks."""
    relative = Path('reader/overview-figures') / uuid.uuid4().hex / figure_id
    target = Path(directory) / relative
    target.parent.mkdir(parents=True)
    target.with_suffix('.source.svg').write_text(svg)
    page = ('<!doctype html><html><head><meta charset="utf-8">'
            '<meta name="localxiv-render-mode" content="overview">'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'">'
            '<style>' + PANEL_PAGE_STYLE + '</style></head><body><main class="overview-image">' + svg + '</main></body></html>')
    ...  # the subprocess call, checks, png, compatibility svg, and assets dict exactly as today
```

`compose` returns `document` directly instead of `normalize_svg(document, profile='overview')`, after `xml.etree.ElementTree.fromstring(document)` proves it is well formed (raise `LayoutError('the composed SVG is not well formed')` otherwise). `Figure.build` calls `rasterize(directory, svg, figure_id, page_title or figure_id)` instead of `html_figures.render`.

- [ ] **Step 2: Delete the modules and the dependency**

```sh
git rm -r papers/agent_overviews.py papers/panel_authoring.py papers/blog_figures.py papers/panel-guides papers/html_figures.py
rm tests/test_panel_authoring.py tests/test_panel_checks.py
```

Remove the `smolagents==1.24.0` line from `requirements-ai.txt`. In `app/macos/verify-release.py`, replace lines 96-101 with:

```python
sys.path.insert(0, str(Path.cwd() / 'python-packages'))
from papers.figures import Figure
scene = {'title': 'Portable renderer', 'subtitle': 'A packaging fixture.', 'footer': 'No research claim.',
         'illustrative': True, 'layout': 'stack', 'panels': [{'id': 'p1', 'heading': 'Two cards',
         'body': {'kind': 'group', 'arrange': 'row', 'children': [
             {'kind': 'card', 'id': 'a', 'label': 'Input', 'detail': 'x'},
             {'kind': 'card', 'id': 'b', 'label': 'Output', 'detail': 'f(x)'}]},
         'edges': [{'from': 'a', 'to': 'b'}]}]}
built = Figure().build(scene, Path(sys.argv[1]), 'render-check', frame='page', page_title='Packaging check')
assert built.checks['issue_details'] == [], built.checks
html_figure = dict(built.assets, id='render-check', title='Portable renderer')
assert (Path(sys.argv[1]) / html_figure['pdf']).read_bytes().startswith(b'%PDF-')
```

and change the result keys `'html_svg_rendering': 'passed', 'smolagents_import': 'passed'` to `'figure_rendering': 'passed'`. Check `grep -n "html_svg_rendering\|smolagents_import" app docs` for any reader of those keys and update it.

- [ ] **Step 3: Update `tests/test_figure.py` and re-baseline**

`test_figure.py` needs no import change. `tests/baseline_scenes.py` composes through `compose` already. Run:

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python tests/baseline_scenes.py --compare
```

Expected: tests pass. The baseline comparison now DIFFERS only by what `normalize_svg` used to change; inspect one diff with `diff <(.venv/bin/python -c "...") .scratch/figure-baseline/attention-scene.svg | head` and confirm every change is attribute order or number formatting, not geometry. Then rewrite the baseline: `.venv/bin/python tests/baseline_scenes.py`.

- [ ] **Step 4: Run the deletion checks from `docs/cleanup.md`**

```sh
grep -rn "panel_authoring\|blog_figures\|panel-guides\|agent_overviews" papers app tests
test -e papers/html_figures.py && echo STILL THERE
grep -n "SCENE_\|construction\|layout_intent" papers/explanation.py
grep -rn svg_profile_revision papers app
grep -rn smolagents papers app requirements-ai.txt
```

Expected: every grep prints nothing and the `test -e` prints nothing. Tick the matching boxes in `docs/cleanup.md` (local file, gitignored).

- [ ] **Step 5: Commit**

```sh
git add -A papers requirements-ai.txt app/macos/verify-release.py
git commit -m "Delete the model-drawn SVG path, the four-attempt loop, and smolagents"
```

### Task 16: Generate the author-facing card from the schema

**Files:**
- Modify: `papers/figures/schema.py`, `papers/overview_workflow.py:111-170` (`SCENE_INSTRUCTION`), `papers/blog_workflow.py` (`VOCABULARY`), `papers/explanation.py:659-692` (`scene_coverage_issues`)
- Test: `tests/test_scene_card.py` (new, local)

**Interfaces:**
- Produces:
  - `schema.NODE_DOCS`: one dict per kind with `fields` (name, type, limit, note) and a `summary` sentence, the single source the validator limits, the card, and the JSON schema read.
  - `schema.card() -> str`: the vocabulary text, under 1,200 tokens by `len // 4`.
  - `schema.json_schema(frame='page'|'panel') -> dict`: a JSON schema for structured output.
  - `overview_workflow.SCENE_WRAPPER`: the Overview's wrapper paragraphs (containment, structure, running example, density, the return line), with the node-kind list removed.
  - `explanation.scene_coverage_issues(digest, strings, headings)` keeps only the containment rule; the string check is `Figure.missing`.

- [ ] **Step 1: Write the failing tests**

```python
"""The card, the JSON schema, and the validator come from one node table."""
import json
import unittest
from pathlib import Path

from papers.figures import Figure
from papers.figures.schema import KINDS, LIMITS, NODE_DOCS, card, json_schema

FIXTURES = Path(__file__).resolve().parent / 'fixtures' / 'overview'


class CardTests(unittest.TestCase):
    def test_card_is_under_budget(self):
        self.assertLess(len(card()) // 4, 1200)

    def test_card_names_every_kind_and_limit(self):
        text = card()
        for kind in KINDS:
            self.assertIn('- ' + kind + ':', text)
        self.assertIn('≤' + str(LIMITS['label']), text)
        self.assertIn('no size, gap, or coordinate', text)

    def test_json_schema_accepts_the_fixtures(self):
        page = json_schema('page')
        self.assertEqual(page['type'], 'object')
        self.assertIn('panels', page['properties'])
        panel = json_schema('panel')
        self.assertNotIn('title', panel['properties'])

    def test_docs_cover_every_node_field(self):
        from papers.figures.schema import NODE_FIELDS
        for kind in KINDS:
            documented = {field['name'] for field in NODE_DOCS[kind]['fields']} | {'kind'}
            self.assertEqual(documented, NODE_FIELDS[kind], kind)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m unittest tests.test_scene_card -v`
Expected: FAIL with `ImportError: cannot import name 'NODE_DOCS'`.

- [ ] **Step 3: Write the node table and the generators**

```python
NODE_DOCS = {
    'card': {'summary': 'one labelled box',
             'fields': [{'name': 'id', 'type': 'id', 'optional': True, 'note': 'needed when an edge joins it'},
                        {'name': 'label', 'type': 'text', 'limit': 'label'},
                        {'name': 'detail', 'type': 'text', 'limit': 'detail', 'optional': True, 'note': 'muted second line'},
                        {'name': 'tone', 'type': 'tone', 'optional': True},
                        {'name': 'dashed', 'type': 'bool', 'optional': True, 'note': 'a discarded or optional state'},
                        {'name': 'plain', 'type': 'bool', 'optional': True, 'note': 'a non-bold label'}]},
    'group': {'summary': 'a container; with a heading it draws a frame, for a component that holds parts',
              'fields': [{'name': 'heading', 'type': 'text', 'limit': 'group_heading', 'optional': True},
                         {'name': 'repeat', 'type': 'text', 'limit': 'repeat', 'optional': True, 'note': 'such as "(N = 6)"'},
                         {'name': 'arrange', 'type': 'enum', 'values': ('row', 'column')},
                         {'name': 'tone', 'type': 'tone', 'optional': True},
                         {'name': 'children', 'type': 'nodes', 'range': (1, 8)}]},
    'note': {'summary': 'a small text block; the first line is bold',
             'fields': [{'name': 'lines', 'type': 'texts', 'range': (1, 4), 'limit': 'note_line'}]},
    'sequence': {'summary': 'tokens, values, or steps in a row, each with an optional caption',
                 'fields': [{'name': 'items', 'type': 'items', 'range': (2, 8),
                             'note': '{"id"?, "text" ≤16, "sub"? ≤20, "tone"?, "hot"? true}'}]},
    'grid': {'summary': 'a small matrix, at most 6×6; a cell is a number, a string ≤12, "*value" to highlight, or null when masked',
             'fields': [{'name': 'rows', 'type': 'cells'},
                        {'name': 'col_labels', 'type': 'texts', 'limit': 'grid_label', 'optional': True},
                        {'name': 'row_labels', 'type': 'texts', 'limit': 'grid_label', 'optional': True},
                        {'name': 'caption', 'type': 'text', 'limit': 'caption', 'optional': True}]},
    'steps': {'summary': 'a numbered calculation; the last line is the result',
              'fields': [{'name': 'lines', 'type': 'texts', 'range': (1, 6), 'limit': 'step'}]},
    'bars': {'summary': 'a comparison of values',
             'fields': [{'name': 'items', 'type': 'pairs', 'range': (2, 8), 'note': '["label" ≤28, number]'},
                        {'name': 'caption', 'type': 'text', 'limit': 'caption', 'optional': True}]},
    'divider': {'summary': 'a dashed line, for a threshold or a boundary',
                'fields': [{'name': 'label', 'type': 'text', 'limit': 'divider', 'optional': True}]},
}


def _field_text(field):
    name = '"' + field['name'] + '"' + ('?' if field.get('optional') else '')
    if field['type'] == 'enum':
        body = ' | '.join('"' + value + '"' for value in field['values'])
    elif field['type'] == 'tone':
        body = '|'.join(TONES)
    elif field['type'] in ('text', 'texts') and field.get('limit'):
        body = ('[' if field['type'] == 'texts' else '') + '≤' + str(LIMITS[field['limit']]) + (']' if field['type'] == 'texts' else '')
    elif field['type'] == 'nodes':
        body = '[%d-%d nodes]' % field['range']
    else:
        body = field.get('note', '')
    if field.get('range') and field['type'] in ('texts', 'items', 'pairs'):
        body = '[%d-%d of %s]' % (*field['range'], body or field.get('note', ''))
    note = field.get('note') if field['type'] not in ('items', 'pairs') else None
    return name + ': ' + body + ((' ' + note) if note and note not in body else '')


def card():
    """The vocabulary a model reads before it authors a Scene. Generated, so it cannot drift."""
    lines = ['You decide content and structure; the application decides every size, gap, and coordinate. '
             'A scene names no size, gap, or coordinate; the validator rejects them.',
             'Node kinds, all with "kind":']
    for kind in KINDS:
        docs = NODE_DOCS[kind]
        lines.append('- ' + kind + ': {' + ', '.join(_field_text(field) for field in docs['fields']) + '} ' + docs['summary'] + '.')
    lines.append('Groups nest at most %d deep. At most %d nodes and %d toned nodes per panel; a tone marks a thing to notice, not a category.'
                 % (MAX_DEPTH, MAX_NODES, MAX_ACCENTS))
    lines.append('Edges: {"from": card id, "to": card id, "label"? ≤%d, "accent"? true}. Arrows join cards of the same panel, for data flow, not reading order. At most %d per panel.'
                 % (LIMITS['edge_label'], MAX_EDGES))
    lines.append('A panel: {"id", "heading" ≤%d, "tone"?, "body": one node, "notes"?: [≤2 lines ≤%d], "edges"?}.'
                 % (LIMITS['heading'], LIMITS['panel_note']))
    return '\n'.join(lines)


def json_schema(frame='page'):
    """A JSON schema for structured output, from the same node table."""
    node = {'type': 'object', 'properties': {'kind': {'type': 'string', 'enum': list(KINDS)}}, 'required': ['kind']}
    panel = {'type': 'object', 'required': ['id', 'heading', 'body'],
             'properties': {'id': {'type': 'string'}, 'heading': {'type': 'string', 'maxLength': LIMITS['heading']},
                            'tone': {'type': 'string', 'enum': ['blue', 'green', 'peach']}, 'body': node,
                            'notes': {'type': 'array', 'maxItems': 2, 'items': {'type': 'string', 'maxLength': LIMITS['panel_note']}},
                            'edges': {'type': 'array', 'maxItems': MAX_EDGES, 'items': {'type': 'object'}}}}
    if frame == 'panel':
        return panel
    return {'type': 'object', 'required': ['title', 'subtitle', 'footer', 'illustrative', 'layout', 'panels'],
            'properties': {'title': {'type': 'string', 'maxLength': LIMITS['title']},
                           'subtitle': {'type': 'string', 'maxLength': LIMITS['subtitle']},
                           'footer': {'type': 'string', 'maxLength': LIMITS['footer']},
                           'illustrative': {'type': 'boolean'}, 'layout': {'type': 'string', 'enum': ['stack', 'columns']},
                           'panels': {'type': 'array', 'minItems': 1, 'maxItems': MAX_PANELS, 'items': panel}}}
```

The node schema stays loose on purpose: the validator is the contract, and providers reject deeply recursive schemas. Providers that accept a schema get the panel and page shape; the node bodies are checked locally.

- [ ] **Step 4: Replace the hand-written vocabulary in both workflows**

In `papers/overview_workflow.py`, split `SCENE_INSTRUCTION` into `SCENE_WRAPPER`, which is the current text minus the block from `Node kinds, all with "kind":` through the `Edges:` paragraph, and build the request content as `scene_card() + '\n\n' + SCENE_WRAPPER` with one example chosen by `digest['paper_type']`: `ATTENTION_EXAMPLE` for `architecture`, `VARIETY_EXAMPLE` otherwise. In `papers/blog_workflow.py`, delete `VOCABULARY` and pass `scene_card()` to `_panel_messages`.

Narrow `scene_coverage_issues` in `papers/explanation.py` to the containment loop only, and in `OverviewWorkflow._scene`'s validator add before it:

```python
            missing = self.figure.missing(scene, digest_requirements(digest))
            issues = [{'code': 'scene_coverage', 'path': 'scene', 'value': value,
                       'message': 'scene does not show the digest string ' + json.dumps(value)
                                  + '; put it in a card label, detail, step, or note exactly as written'} for value in missing]
            issues += scene_coverage_issues(digest, strings, self.figure.headings(scene)) + example_coverage_issues(digest, strings)
```

- [ ] **Step 5: Run the tests**

Run: `.venv/bin/python -m unittest discover -s tests -v`
Expected: PASS. Print the budget for the task report:

```sh
.venv/bin/python -c "from papers.figures.schema import card; t=card(); print(len(t), len(t)//4)"
```

- [ ] **Step 6: Commit**

```sh
git add papers/figures/schema.py papers/overview_workflow.py papers/blog_workflow.py papers/explanation.py
git commit -m "Generate the Scene card and JSON schema from one node table"
```

Phase 2 ends here. One figure path, one coordinator, no model-drawn SVG, no smolagents.

---

## Phase 3: vocabulary, docs, and the pilot

### Task 17: Arrows between adjacent panels

**Files:**
- Modify: `papers/figures/schema.py` (page validation, `NODE_DOCS` is unchanged, `card` gains one sentence), `papers/figures/render.py` (`compose`), `papers/overview_workflow.py` (`SCENE_WRAPPER`, one sentence)
- Test: `tests/test_scene_schema.py`, `tests/test_layout_canvas.py`

**Interfaces:**
- Produces: `scene.edges`, optional, a list of at most `MAX_PANELS - 1` objects `{"from": panel id, "to": panel id, "accent"?: true}` where the two panels are adjacent in `panels` order and `layout` is `columns`. The renderer draws one horizontal arrow in the gap between the two frames at the height of the shorter frame's vertical middle.

- [ ] **Step 1: Write the failing tests**

In `tests/test_scene_schema.py`:

```python
class PanelEdgeTests(unittest.TestCase):
    def setUp(self):
        self.variety = json.loads((FIXTURES / 'variety-scene.json').read_text())

    def test_adjacent_panel_edges_validate_in_columns(self):
        scene = dict(self.variety, edges=[{'from': 'score', 'to': 'mask'}, {'from': 'mask', 'to': 'result'}])
        validate(scene)

    def test_non_adjacent_and_stack_edges_are_rejected(self):
        scene = dict(self.variety, edges=[{'from': 'score', 'to': 'result'}])
        with self.assertRaises(SceneError) as caught:
            validate(scene)
        self.assertIn('scene.edges[0]', [issue['path'] for issue in caught.exception.issues])
        stacked = dict(self.variety, layout='stack', edges=[{'from': 'score', 'to': 'mask'}])
        with self.assertRaises(SceneError):
            validate(stacked)
```

In `tests/test_layout_canvas.py`:

```python
    def test_a_panel_edge_draws_one_arrow_in_the_gap(self):
        scene = json.loads((FIXTURES / 'variety-scene.json').read_text())
        scene['edges'] = [{'from': 'score', 'to': 'mask'}]
        svg, placements = compose(FixedMeasurer(), scene, Canvas(1000), frame='page')
        first, second = placements[0]['frame'], placements[1]['frame']
        x1 = first['x'] + first['width']
        self.assertIn(f'class="panel-edge" d="M {x1:g} ', svg)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m unittest tests.test_scene_schema.PanelEdgeTests tests.test_layout_canvas -v`
Expected: FAIL, `scene.edges is unsupported`.

- [ ] **Step 3: Validate and draw**

In `validate` (page frame), add `'edges'` to `allowed`, then after the panel loop:

```python
    edges = scene.get('edges', [])
    order = [panel.get('id') for panel in panels if isinstance(panel, dict)]
    if not isinstance(edges, list) or len(edges) > max(0, MAX_PANELS - 1):
        _panel_error(errors, 'scene.edges', f'needs at most {MAX_PANELS - 1} arrows between panels')
        edges = edges if isinstance(edges, list) else []
    for position, edge in enumerate(edges):
        path = f'scene.edges[{position}]'
        if not isinstance(edge, dict) or set(edge) - {'from', 'to', 'accent'}:
            _panel_error(errors, path, 'must be {"from", "to", "accent"?}')
            continue
        if scene.get('layout') != 'columns':
            _panel_error(errors, path, 'joins panels only when layout is columns')
        if (edge.get('from') not in order or edge.get('to') not in order
                or order.index(edge['to']) != order.index(edge['from']) + 1):
            _panel_error(errors, path, 'must join a panel to the next panel in order')
```

In `compose`, after every panel is placed and before the footer, when `frame == 'page'`:

```python
    frames = {item['id']: item['frame'] for item in placements}
    for edge in scene.get('edges', []):
        a, b = frames[edge['from']], frames[edge['to']]
        if b['x'] <= a['x']:
            continue  # the panels wrapped onto separate rows; no room for a horizontal arrow
        y = min(a['y'] + a['height'], b['y'] + b['height']) / 2 + max(a['y'], b['y']) / 2
        x1, x2 = a['x'] + a['width'], b['x'] - 3
        colour = ACCENT if edge.get('accent') else TEXT
        out.append(f'<path class="panel-edge" d="M {x1:g} {y:g} L {x2:g} {y:g}" fill="none" stroke="{colour}" '
                   f'stroke-width="1.6" marker-end="url(#{"arrow-accent" if edge.get("accent") else "arrow"})"/>')
```

Two panels that fell onto separate rows (the `per_row` halving in `compose`) get no arrow, and `placements` gains `'row': column_index` so a test can tell. `PANEL_GAP` is 16 units; the arrowhead is 6, so the line spans the gap.

Add to `card()` after the panel line: `'A page may add "edges": [{"from": panel id, "to": the next panel id}] for an arrow between side-by-side panels.'` Add to `SCENE_WRAPPER`'s structure paragraph: "In a columns layout, join a stage to the next with a scene-level edge when the story flows left to right."

- [ ] **Step 4: Run the tests**

Run: `.venv/bin/python -m unittest discover -s tests -v`
Expected: PASS. `test_card_is_under_budget` still passes; print the count.

- [ ] **Step 5: Commit**

```sh
git add papers/figures/schema.py papers/figures/render.py papers/overview_workflow.py
git commit -m "Draw an arrow between adjacent side-by-side panels"
```

### Task 18: The `chart` node for line and scatter data

**Files:**
- Modify: `papers/figures/schema.py` (`KINDS`, `NODE_FIELDS`, `NODE_DOCS`, `LIMITS`, `_scene_node`, `text`), `papers/figures/layout.py` (`size`, `prime`), `papers/figures/render.py` (`_draw`)
- Test: `tests/test_scene_schema.py`, `tests/test_chart_node.py` (new, local)

**Interfaces:**
- Produces: node kind `chart`: `{"kind": "chart", "series": [1-4 of {"label" ≤28, "points": [2-12 of [x, y]]}], "x_label"? ≤24, "y_label"? ≤24, "caption"? ≤90, "marks"?: "line" | "dots"}`. Default `marks` is `line`. Layout: width 300 units or the available width when narrower, plot height 140, plus one legend row per series at 14 units and the caption. Every visible string (series labels, axis labels, tick labels, caption) is 14-unit text. `text()` returns series labels, axis labels, and the caption.

- [ ] **Step 1: Write the failing tests**

```python
"""A chart node lays out at a fixed height and draws axes, ticks, series, legend, and caption."""
import re
import unittest

from papers.figures import Figure
from papers.figures.layout import Canvas
from papers.figures.measure import FixedMeasurer
from papers.figures.render import compose
from papers.figures.schema import SceneError, validate

CHART = {'kind': 'chart', 'series': [{'label': 'Transformer (big)', 'points': [[1, 25.2], [2, 27.3], [3, 28.4]]},
                                     {'label': 'ConvS2S', 'points': [[1, 24.0], [2, 25.0], [3, 25.2]]}],
         'x_label': 'training steps (×100k)', 'y_label': 'BLEU', 'caption': 'WMT 2014 EN-DE', 'marks': 'line'}
PANEL = {'id': 'p1', 'heading': 'Result', 'body': CHART}


class ChartTests(unittest.TestCase):
    def test_chart_validates_and_rejects_geometry(self):
        validate(PANEL, frame='panel')
        with self.assertRaises(SceneError):
            validate({'id': 'p1', 'heading': 'x', 'body': dict(CHART, width=300)}, frame='panel')
        with self.assertRaises(SceneError):
            validate({'id': 'p1', 'heading': 'x', 'body': dict(CHART, series=[])}, frame='panel')

    def test_chart_draws_two_polylines_and_the_legend(self):
        scene = {'title': '', 'subtitle': '', 'footer': '', 'illustrative': False, 'layout': 'stack', 'panels': [PANEL]}
        svg, _ = compose(FixedMeasurer(), scene, Canvas(640), frame='panel')
        self.assertEqual(len(re.findall(r'<polyline class="series"', svg)), 2)
        self.assertIn('Transformer (big)', svg)
        self.assertIn('BLEU', svg)
        self.assertIn('WMT 2014 EN-DE', svg)

    def test_chart_strings_are_visible_text(self):
        self.assertIn('ConvS2S', Figure().text(PANEL, frame='panel'))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m unittest tests.test_chart_node -v`
Expected: FAIL, `kind must be one of card, group, ...`.

- [ ] **Step 3: Add the kind**

`schema.py`: append `'chart'` to `KINDS`; add `'chart': {'kind', 'series', 'x_label', 'y_label', 'caption', 'marks'}` to `NODE_FIELDS`; add `'series_label': 28, 'axis_label': 24` to `LIMITS`; add the `NODE_DOCS['chart']` entry with `summary` "a line or scatter plot of 1 to 4 series; the application draws axes and ticks"; in `_scene_node` add:

```python
    elif kind == 'chart':
        series = node.get('series')
        if not isinstance(series, list) or not 1 <= len(series) <= 4:
            _panel_error(errors, path + '.series', 'needs 1 through 4 series')
            return
        for index, item in enumerate(series):
            item_path = f'{path}.series[{index}]'
            if not isinstance(item, dict) or set(item) - {'label', 'points'}:
                _panel_error(errors, item_path, 'must be {"label", "points"}')
                continue
            _text(item, 'label', item_path, errors, maximum=LIMITS['series_label'])
            points = item.get('points')
            if (not isinstance(points, list) or not 2 <= len(points) <= 12
                    or any(not isinstance(point, list) or len(point) != 2
                           or any(not isinstance(value, (int, float)) or isinstance(value, bool) for value in point)
                           for point in points)):
                _panel_error(errors, item_path + '.points', 'needs 2 through 12 [x, y] number pairs')
        for name in ('x_label', 'y_label'):
            if name in node:
                _text(node, name, path, errors, maximum=LIMITS['axis_label'])
        if 'caption' in node:
            _text(node, 'caption', path, errors, maximum=LIMITS['caption'])
        if 'marks' in node and node['marks'] not in ('line', 'dots'):
            _panel_error(errors, path + '.marks', 'must be line or dots')
```

In `text`, add `elif kind == 'chart': strings += [item['label'] for item in node['series']] + [node.get('x_label', ''), node.get('y_label', ''), node.get('caption', '')]`.

`layout.py`: in `prime`, add the chart strings to `plain` (series labels, axis labels, caption, and the tick labels the renderer will produce: `_chart_ticks(node)` returns them). In `size`:

```python
    elif kind == 'chart':
        node['w'] = min(CHART_WIDTH, avail)
        node['h'] = CHART_HEIGHT + LINE[BODY] * (len(node['series']) + (1 if node.get('caption') else 0)) + (LINE[BODY] if node.get('x_label') else 0) + 8
```

with `CHART_WIDTH = 300` and `CHART_HEIGHT = 140` beside `GRID_CELL` and `BAR_ROW`. Add `_chart_ticks(node)`: four evenly spaced y ticks from the rounded minimum to the rounded maximum across all series (`round` to the magnitude of the range, so 24 to 28.4 gives 24, 25.5, 27, 28.5), and the x ticks at the minimum and maximum x.

`render.py`: in `_draw`, add the chart branch: a left axis line and a bottom axis line inset 36 units from the left (room for tick labels) and 18 from the bottom; y tick labels right-aligned at `x - 6`; a hairline gridline per y tick; each series as `<polyline class="series" points="..." fill="none" stroke="{colour}" stroke-width="1.6"/>` when `marks` is `line`, or one `<circle r="3">` per point when `dots`; series colours cycle through `TONES['blue'][2]`, `TONES['green'][2]`, `TONES['peach'][2]`, then `MUTED`; a legend row per series under the plot with a 14-unit swatch line and the label; `x_label` centred under the axis; `caption` last in `MUTED`. Every text goes through `_text(..., size=BODY)`.

- [ ] **Step 4: Update the card and run everything**

`NODE_DOCS['chart']` makes `card()` list it. Run:

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -c "from papers.figures.schema import card; t=card(); print(len(t)//4)"
```

Expected: PASS, and the card stays under 1,200 tokens. If it does not, shorten summaries in `NODE_DOCS`, never drop a field.

- [ ] **Step 5: Commit**

```sh
git add papers/figures/schema.py papers/figures/layout.py papers/figures/render.py
git commit -m "Add a chart node that draws line and scatter series at 14-unit text"
```

### Task 19: Raise the density floor to 40 for pages

**Files:**
- Modify: `papers/figures/checks.py`, `papers/overview_workflow.py` (`SCENE_WRAPPER` density sentence)
- Test: `tests/test_scene_layout.py`, `tests/test_figure.py`

- [ ] **Step 1: Change the tests first**

In `tests/test_scene_layout.py`, change `self.assertGreater(_density(checks), 30)` to `40` in both golden tests. In `tests/test_figure.py`, change `assertGreater(result.density, 30)` to `40`.

- [ ] **Step 2: Run them**

Run: `.venv/bin/python -m unittest tests.test_scene_layout tests.test_figure -v`
Expected: PASS already, because the fixtures measure 47 and above. If one fails, the fixture is sparser than the reference figures and the floor stays at 30 for this plan; report it.

- [ ] **Step 3: Raise the floor**

`MIN_TEXT_DENSITY = 40` in `papers/figures/checks.py`. In `SCENE_WRAPPER`, the sentence beginning "Density is the goal" keeps its wording; it names no number.

- [ ] **Step 4: Run everything and commit**

```sh
.venv/bin/python -m unittest discover -s tests -v
git add papers/figures/checks.py
git commit -m "Raise the Overview density floor to 40 text runs per million square units"
```

### Task 20: Docs, terms, and the superseded specs

**Files:**
- Modify: `docs/development.md:60-66, 89-90`, `README.md:97-101`, `CONTEXT.md:37, 43, 51, 55`, `docs/superpowers/specs/2026-09-18-figure-library-consolidation-design.md:3`, `docs/superpowers/specs/2026-09-18-overview-simplification-design.md:3`, `docs/superpowers/specs/2026-09-18-overview-scene-layout-design.md` (any link to a deleted spec)
- Delete: `docs/blog_refactor.md`, `docs/superpowers/specs/2026-09-13-overview-workflow-rebuild-design.md`, `docs/superpowers/specs/2026-09-13-panel-svg-reference-inputs.md`, `docs/superpowers/specs/2026-09-14-blog-workflow-update-design.md`
- Prepend a status line to: `docs/verification/2026-09-13-overview-edge-alignment.md`, `2026-09-13-overview-gap-fitting.md`, `2026-09-13-overview-mixed-scaling.md`, `2026-09-13-overview-rebuild-p2.md`, `2026-09-13-overview-workflow-rebuild.md`, `2026-09-14-blog-live-pilot.md`, `2026-09-14-blog-live-pilot-rerun.md`, `2026-09-14-blog-workflow-update.md`, `2026-09-15-blog-checkpoint.md`, `2026-09-16-svg-reliability.md`

- [ ] **Step 1: Record the commit that last held the deleted docs**

Run: `git rev-parse --short HEAD` and keep the hash for the status lines.

- [ ] **Step 2: Delete and mark**

```sh
git rm docs/blog_refactor.md docs/superpowers/specs/2026-09-13-overview-workflow-rebuild-design.md docs/superpowers/specs/2026-09-13-panel-svg-reference-inputs.md docs/superpowers/specs/2026-09-14-blog-workflow-update-design.md
```

Insert as line 2 of each listed verification report, after its `#` title line: `Status: historical. The model-drawn SVG path this report verifies was deleted by the [figure library consolidation](../superpowers/specs/2026-09-18-figure-library-consolidation-design.md); the code is at commit <hash>.`

- [ ] **Step 3: Rewrite the developer docs**

`docs/development.md` rows 89-90 become:

```
| How is an Overview planned and drawn? | `OverviewWorkflow` in `papers/overview_workflow.py`, then `Figure` in `papers/figures/`; `app/static/app.js` displays it |
| How is a Blog generated? | `BlogWorkflow` in `papers/blog_workflow.py`; both workflows share `papers/coordinator.py` and draw through `papers/figures/` |
```

Lines 63-64 name the two deleted specs; replace them with a sentence naming the scene layout design and the figure library consolidation design with their links. Add one row to the table: `| How does a model learn the drawing vocabulary? | `card()` in `papers/figures/schema.py`, generated from `NODE_DOCS` |`.

`README.md` rows 97-99 become:

```
| Overview generation | [papers/overview_workflow.py](papers/overview_workflow.py) |
| Blog generation | [papers/blog_workflow.py](papers/blog_workflow.py) |
| Figure layout and rendering | [papers/figures/](papers/figures/) |
```

and line 101 drops the clause "and the [Blog workflow status and pilot limitations](docs/blog_refactor.md)". Lines 63 and 65 describe Blog figures as drawn separately; rewrite line 63's last sentence to "Blog figures are laid out by the application from a model-authored Scene panel, the same way the Overview is."

`CONTEXT.md`: delete the Drawing assignment entry (line 51). Replace the Blog drawing brief entry (37) with:

`**Blog figure brief**: The article author's assignment for one Blog figure: purpose, entry context, exit state, ordered content items, exact text, and illustrative values. The model authors one Scene panel from it, and every exact text and illustrative value must appear in that panel.`

Replace the Omitted Blog figure entry (43) with:

`**Omitted Blog figure**: A planned figure whose Scene panel still fails validation, coverage, layout, or the native checks after one request and three corrections. The delivered article excludes its caption, marker, and dependent discussion; essential scientific explanation remains understandable in prose.`

Replace the Overview composition entry (55) with:

`**Figure render**: The laid-out Scene rendered by the Figure library as one SVG document, with the page frame for an Overview or as a bare panel for a Blog figure, from which the PNG, PDF, and editable SVG are rendered. It must pass the native checks, and an Overview must reach 40 text runs per million square units.`

Add after Scene layout (53):

`**Figure library**: `papers/figures/`, the one path from a Scene to SVG, PNG, PDF, checks, and issues, used by the Overview and every Blog figure. It makes no provider call and knows nothing about papers or prompts.`

Update the Overview entry's density sentence if it names 30. Replace "Overview composition" with "Figure render" wherever CONTEXT.md, the two 2026-09-18 specs, or `docs/development.md` use it: `grep -rn "Overview composition" CONTEXT.md docs`.

- [ ] **Step 4: Fix links to the deleted specs**

Run: `grep -rn "2026-09-13-overview-workflow-rebuild\|2026-09-13-panel-svg\|2026-09-14-blog-workflow-update\|blog_refactor" docs README.md CONTEXT.md`. For each hit in a kept file, replace the link with plain text naming the design and the commit hash from step 1, for example "the 2026-09-14 Blog workflow update design (deleted; at commit <hash>)".

- [ ] **Step 5: Check and commit**

```sh
grep -rn "agent_overviews\|panel_authoring\|html_figures\|scene_layout\|panel-guides\|four drawing\|four attempts" docs README.md CONTEXT.md | grep -v "^docs/verification/\|^docs/superpowers/plans/"
```

Expected: nothing. Tick the CONTEXT.md box in `docs/cleanup.md`.

```sh
git add -A docs README.md CONTEXT.md
git commit -m "Point the docs at the figure library and retire the model-drawn SVG terms"
```

### Task 21: Let the CLI run a Blog

**Files:**
- Modify: `tools/overview_run.py`, `docs/development.md` (the "Compare models on one Overview" section)

**Interfaces:**
- Produces: `--kind overview|blog` (default `overview`). For `blog`, the tool calls `papers.blog_workflow.generate`, prints the same request, token, and second counts, prints `figures` as a list of `{id, status, requests, corrections}` from `provenance.figure_outcomes`, and with `--out` writes the article as `{provider}_{paper}.md` and each accepted figure's PNG as `{provider}_{paper}_{id}.png`.

- [ ] **Step 1: Add the option**

In `main()`, add `parser.add_argument('--kind', choices=('overview', 'blog'), default='overview')` and pass it to `run`. In `run`, import both generators at the top of the file:

```python
from papers.blog_workflow import generate as generate_blog  # noqa: E402
from papers.overview_workflow import generate as generate_overview  # noqa: E402
```

and branch:

```python
    if kind == 'blog':
        result = generate_blog(provider, paper, progress)
        summary = {'model': model, 'requests': len(usage), 'tokens': tokens, 'reasoning_tokens': reasoning_tokens,
                   'seconds': seconds, 'figures': [{key: item[key] for key in ('id', 'status', 'requests', 'corrections')}
                                                    for item in result['provenance']['figure_outcomes']],
                   'words': len(result['text'].split()), 'verdicts': result['provenance']['verdict_count']}
        if out:
            out.mkdir(parents=True, exist_ok=True)
            stem = provider_name + '_' + _slug(paper.get('title', 'paper')[:60]) + ('_' + _slug(model) if compare else '')
            (out / (stem + '.md')).write_text(result['text'])
            for figure in result['figures']:
                shutil.copyfile(Path(paper['directory']) / figure['png'], out / (stem + '_' + figure['id'] + '.png'))
                summary.setdefault('png', []).append(str(out / (stem + '_' + figure['id'] + '.png')))
        print(json.dumps(summary, indent=1))
        return
```

`figure_outcomes` entries need a `corrections` key; task 14's `figure_outcomes` returns `id`, `status`, `requests`, `corrections`, `issues`. Confirm with `grep -n "def figure_outcomes" -A 6 papers/blog_workflow.py`.

- [ ] **Step 2: Run it against the fake**

No fake provider fits the CLI. Run the real thing once if a key is in `.env`, otherwise `.venv/bin/python tools/overview_run.py --help` and confirm `--kind` is listed.

- [ ] **Step 3: Document and commit**

Rename the `docs/development.md` section to "Compare models on one Overview or Blog" and add one line: "`--kind blog` runs the Blog instead and prints each figure's status and correction count; `--out` then writes the article as Markdown and each accepted figure's PNG."

```sh
git add tools/overview_run.py docs/development.md
git commit -m "Let overview_run generate a Blog and report its figure outcomes"
```

### Task 22: The live pilot

**Files:**
- Create: `docs/verification/2026-09-<day>-figure-library-pilot.md`
- Read: the spec's Migration unit 7 and the numbers it asks for

This spends money. Confirm with the user before starting, and state the ceiling.

- [ ] **Step 1: Run the Overview on the three reference papers**

```sh
.venv/bin/python tools/overview_run.py --paper "Attention" --model deepseek-flash --out .scratch/pilot
.venv/bin/python tools/overview_run.py --paper "Probabilities" --model deepseek-flash --out .scratch/pilot
.venv/bin/python tools/overview_run.py --paper "Black-Box" --model deepseek-flash --out .scratch/pilot
```

Record per run: requests, tokens, seconds, density, panels, and whether the native checks passed. Open each PNG and compare it with `docs/reference_images/` for density and style only.

- [ ] **Step 2: Run the Blog on LoRA and Mamba**

```sh
.venv/bin/python tools/overview_run.py --kind blog --paper "LoRA" --model deepseek-flash --out .scratch/pilot
.venv/bin/python tools/overview_run.py --kind blog --paper "Mamba" --model deepseek-flash --out .scratch/pilot
```

If either paper is not in the library, import it through the app first (`2106.09685v2`, `2312.00752v2`). Record per run: delivered or not, verdict count, and per figure the status and correction count.

- [ ] **Step 3: Write the report**

The report has four tables and nothing else: Overview runs (paper, requests, tokens, seconds, density, checks), Blog runs (paper, delivered, verdicts, words), Blog figures (paper, figure id, status, corrections, density of the panel), and the spec's acceptance question answered in one line each: did every Overview reach density 40 and pass the native checks; what fraction of Blog figures was accepted with zero, one, two, or three corrections; how many Blogs were delivered, counting a delivered Blog after an omission as a recovered article and not an accepted figure. Record the panel densities so the Open item on the panel floor can be settled.

- [ ] **Step 4: Refresh the README figure**

If the Attention Overview passed, copy its PNG to `docs/attention_figure.png` and update the date sentence at `README.md:31`.

- [ ] **Step 5: Commit**

```sh
git add docs/verification/2026-09-<day>-figure-library-pilot.md docs/attention_figure.png README.md
git commit -m "Record the figure library pilot on three Overviews and two Blogs"
```

---

## Self-review

**Spec coverage.** Library and `Figure` API: tasks 2 to 5 and 15. Author-facing card generated from the schema with a budget: task 16. Vocabulary additions, panel edges and chart: tasks 17 and 18. Measurer kept on WebKit, injectable, stub for tests: task 3. Workflow classes on one coordinator: tasks 6, 10 to 14. Blog figure at 640 with one request plus three corrections and omission: task 12. Review finding as a Scene correction: task 13. Deletions with grep checks: task 15. Compatibility of saved keys: tasks 6 and 14 keep the dicts; `dimensions` added in task 12. Migration order and byte-identical check: tasks 1, 4, 7, 15. Density floor to 40 for pages: task 19. Terms: task 20. Pilot with the reported fractions: task 22. Open items: the panel density floor is measured in task 22; the brief `content` lines stay as prompt context (task 12 sends them in `<brief>`); a Blog figure is one panel.

**Deviation from the spec.** Unit 3's characterization tests of the agent loop are replaced by tests of the surviving pure functions (task 8) and an end-to-end fake-provider test of the new workflow (task 14). Decision 9 states why.

**Type consistency.** `Figure.build(value, directory, figure_id, *, frame, page_title)` is used with that signature in tasks 5, 6, 12, and 15. `FigureResult` fields `svg`, `assets`, `checks`, `placements`, `density`, `issues` are read by name in tasks 6, 12, and 14. `request_validated(coordinator, label, messages, validate, *, stage, attempts, describe)` matches `papers/overview_workflow.py:441` and is used that way in tasks 10 to 13. Figure state keys `id`, `brief`, `status`, `requests`, `corrections`, `panel`, `result`, `labels`, `issues`, `history` are the same in tasks 12, 13, 14, and 21.
