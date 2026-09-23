# Figure library layout defects implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the five layout defects in `papers/figures/` that the 2026-09-23 audit reproduced, so an Overview panel fills its width, cards have no empty lines, one-line labels stay on one line, arrows keep clear of group frames and headings, and steps carry one number.

**Architecture:** Every fix lands in the Figure library (`papers/figures/`), which lays out a Scene deterministically after the model has authored it. The model, the Scene schema, and the provider requests do not change. Each task adds a regression test that runs with `FixedMeasurer` or pure geometry, so no task before the last one needs the native renderer. The last task runs the renderer and re-lays out the reference figure.

**Tech Stack:** Python 3 standard library, `unittest`, the native `papers/html-snapshot` WebKit helper for the final check.

**Spec:** [Overview scene layout design](../specs/2026-09-18-overview-scene-layout-design.md), Layout section. The five defects are restated under Defects below. The audit is recorded in the session memory of 2026-09-23 and reproduced in this plan's tests.

## Global constraints

- The model authors no geometry. No task adds a size, gap, or coordinate to the Scene schema.
- `MIN_PANEL_FILL` in `papers/overview_workflow.py` stays `0.4`, and `MIN_TEXT_DENSITY` in `papers/figures/checks.py` stays `40`. This plan fixes the layout, not the floors.
- Every test goes under `tests/`. Tests run with `python3 -m unittest tests.<module> -v`, not pytest.
- Commit messages carry no `Co-Authored-By` trailer.
- Work on a branch named `figure-library-layout-defects`. Merge with `git merge --no-ff`.
- Before the first task, commit or stash the uncommitted changes in `papers/ai.py`, `papers/blog_workflow.py`, `papers/overview.py`, and `papers/recommendations.py`. They belong to other work.

## Defects

1. **Reflow blocked by a mixed column.** `reflow_narrow` in `papers/figures/layout.py` flattens unheaded column groups only when every child is one. A column of `[sequence, group[card, card], steps]` keeps three children, never reaches `REFLOW_MIN_NODES`, and ships at 35% fill. `docs/attention_figure.png` panel 1 shows this.
2. **Stale card height after a stretch.** `place` widens a column child to its siblings' width but keeps the `h` that `size` computed at the natural width. `_draw` in `papers/figures/render.py` re-wraps at the final width, so the card has fewer lines than its box. Three cards in `tests/fixtures/overview/attention-run.json` measure 68 units tall with 50 units of text.
3. **Wrap off by rounding.** `Measurer.wrap` adds word widths and space widths while `size` measures the whole string. A 0.01-unit difference splits "Decoder layer" into two lines inside a card that was sized for one.
4. **Arrows along frames and labels on headings.** `_draw_edge` excludes group frames from the obstacles, so a lane may run along a frame edge with nothing to reject it. `label_fits` sees the frame but not the heading text, so an edge label lands on a group heading.
5. **Double numbering in steps.** The model writes "1. Project each token" and the renderer prepends "1." again.

## File structure

- Modify `papers/figures/measure.py`: `Measurer.wrap` returns one line when the whole string fits.
- Modify `papers/figures/layout.py`: `step_text`, `refit`, a `measure` parameter on `place`, per-child flattening in `reflow_narrow`.
- Modify `papers/figures/route.py`: `runs_along`, a `frames` parameter on `route`, lane offsets off the gap.
- Modify `papers/figures/render.py`: heading obstacles, frames passed to `route`, `step_text` in `_draw`, `measure` passed to `place`.
- Modify `papers/figures/schema.py`: the steps entry in `NODE_DOCS` says the renderer numbers the lines.
- Create `tests/test_layout_defects.py`: one test class per defect, plus the replica Scene the tests share.
- Modify `tests/test_measure.py`: the rounding test.

---

### Task 1: Wrap keeps a string on one line when it fits

**Files:**
- Modify: `papers/figures/measure.py:86-99`
- Test: `tests/test_measure.py`

**Interfaces:**
- Produces: `Measurer.wrap(text, width, size=BODY, weight=None) -> list[str]`, unchanged signature. When the width of the whole normalised string is at most `width`, the result is `[that string]`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_measure.py`:

```python
from papers.figures.measure import FixedMeasurer


class RoundingMeasurer(FixedMeasurer):
    """A whole string measures 0.01 narrower than its words plus spaces, as WebKit sometimes reports."""

    def _measure(self, strings, size, weight):
        return [width - (0.01 if ' ' in text else 0.0)
                for text, width in zip(strings, super()._measure(strings, size, weight))]


class WrapRoundingTests(unittest.TestCase):
    def test_a_label_sized_for_one_line_stays_on_one_line(self):
        measure = RoundingMeasurer()
        width = measure.width('Decoder layer', 14, 700)
        self.assertEqual(measure.wrap('Decoder layer', width, 14, 700), ['Decoder layer'])

    def test_a_label_wider_than_the_box_still_wraps(self):
        measure = RoundingMeasurer()
        width = measure.width('Decoder', 14, 700)
        self.assertEqual(measure.wrap('Decoder layer', width, 14, 700), ['Decoder', 'layer'])
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m unittest tests.test_measure -v`
Expected: `test_a_label_sized_for_one_line_stays_on_one_line` fails with `['Decoder', 'layer'] != ['Decoder layer']`.

- [ ] **Step 3: Add the whole-string check to `wrap`**

Replace `Measurer.wrap` in `papers/figures/measure.py` with:

```python
    def wrap(self, text, width, size=BODY, weight=None):
        whole = ' '.join(str(text).split())
        if not whole:
            return ['']
        # The card was sized from this same whole-string measurement, so a string that fits
        # whole stays on one line even when its words plus spaces add up 0.01 wider.
        if self.width(whole, size, weight) <= width:
            return [whole]
        words = whole.split()
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
        return lines
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m unittest tests.test_measure tests.test_scene_layout tests.test_figure -v`
Expected: all pass. `test_scene_layout` and `test_figure` need `papers/html-snapshot`; build it first with the command in `docs/development.md` if it is missing.

- [ ] **Step 5: Commit**

```bash
git add papers/figures/measure.py tests/test_measure.py
git commit -m "Keep a label that fits whole on one line"
```

---

### Task 2: Steps carry one number

**Files:**
- Modify: `papers/figures/layout.py:1-3` (imports), `papers/figures/layout.py:73-75` (`prime`), `papers/figures/layout.py:180-186` (`size`)
- Modify: `papers/figures/render.py:224-230` (`_draw`)
- Modify: `papers/figures/schema.py:122`
- Create: `tests/test_layout_defects.py`

**Interfaces:**
- Produces: `layout.step_text(line) -> str`, the line without a leading `1.` or `1)` number. `schema.text` keeps the raw line, so Digest coverage still matches the model's string.

- [ ] **Step 1: Write the failing test**

Create `tests/test_layout_defects.py`:

```python
"""Regression tests for the five layout defects reproduced on 2026-09-23. No renderer needed."""
import copy
import unittest

from papers.figures.layout import BODY, CARD_PAD_Y, Canvas, GAP, LINE, step_text
from papers.figures.measure import FixedMeasurer
from papers.figures.render import compose


def page(body, edges=()):
    return {'title': 'Title', 'subtitle': 'Subtitle', 'footer': 'Footer', 'illustrative': False,
            'layout': 'stack', 'panels': [{'id': 'p1', 'heading': 'Heading', 'body': body, 'edges': list(edges)}]}


def compose_page(scene):
    scene = copy.deepcopy(scene)
    svg, placements = compose(FixedMeasurer(), scene, Canvas(1000), frame='page', page_title='Paper')
    return svg, placements, scene


class StepNumberTests(unittest.TestCase):
    def test_step_text_strips_one_leading_number(self):
        self.assertEqual(step_text('1. Project each token'), 'Project each token')
        self.assertEqual(step_text('2) scores = Q K^T'), 'scores = Q K^T')
        self.assertEqual(step_text('softmax → [0.62, 0.23]'), 'softmax → [0.62, 0.23]')
        self.assertEqual(step_text('3.5 days on 8 GPUs'), '3.5 days on 8 GPUs')

    def test_the_renderer_numbers_each_step_once(self):
        svg, _, _ = compose_page({'kind': 'steps', 'lines': ['1. Project each token', '2. scores = Q K^T']})
        self.assertEqual(svg.count('>1.</text>'), 1)
        self.assertEqual(svg.count('>2.</text>'), 1)
        self.assertIn('>Project each token</text>', svg)
        self.assertNotIn('1. Project', svg)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m unittest tests.test_layout_defects -v`
Expected: `ImportError: cannot import name 'step_text'`.

- [ ] **Step 3: Add `step_text` and use it in `prime`, `size`, and `_draw`**

At the top of `papers/figures/layout.py`, after `import math`, add:

```python
import re
```

After the constants block (after `NOTES_GAP = 24`), add:

```python
# The renderer numbers steps itself. A model that numbers them too gets its number removed
# here, not in the schema, so coverage still matches the raw line. "3.5 days" keeps its 3.
STEP_NUMBER = re.compile(r'^\s*\d{1,2}[.)]\s+')


def step_text(line):
    return STEP_NUMBER.sub('', str(line)) or str(line)
```

In `prime`, replace the `steps` branch with:

```python
        elif kind == 'steps':
            plain.extend(step_text(line) for line in node['lines'])
            bold.append(step_text(node['lines'][-1]))
```

In `size`, replace the `steps` branch's first line with:

```python
        lines = [step_text(line) for line in node['lines']]
```

In `papers/figures/render.py`, import `step_text` from `papers.figures.layout` in the existing import list, and replace the `steps` branch of `_draw` with:

```python
    elif kind == 'steps':
        out.append(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="6" fill="{palette.sunk}" stroke="{palette.hairline}"/>')
        for index, line in enumerate(node['lines']):
            last = index == len(node['lines']) - 1
            baseline = y + CARD_PAD_Y + 13 + index * LINE[BODY]
            out.append(_text(x + CARD_PAD_X, baseline, f'{index + 1}.', fill=palette.muted))
            out.append(_text(x + CARD_PAD_X + 20, baseline, step_text(line), weight=700 if last else None,
                             fill=palette.accent if last else palette.text))
```

In `papers/figures/schema.py`, change the `steps` summary in `NODE_DOCS` to:

```python
    'steps': {'summary': 'a calculation the renderer numbers 1., 2., …; write the lines without numbers; the last line is the result',
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m unittest tests.test_layout_defects tests.test_scene_card -v`
Expected: all pass. `test_card_is_under_budget` must still pass with the longer summary.

- [ ] **Step 5: Commit**

```bash
git add papers/figures/layout.py papers/figures/render.py papers/figures/schema.py tests/test_layout_defects.py
git commit -m "Number each step once"
```

---

### Task 3: A stretched card recomputes its height

**Files:**
- Modify: `papers/figures/layout.py:296-330` (`place`)
- Modify: `papers/figures/render.py:291` (the `place` call)
- Test: `tests/test_layout_defects.py`

**Interfaces:**
- Produces: `layout.place(node, x, y, canvas, measure, stretch=None)`. The `measure` argument is new and required. `layout.refit(node, measure)` recomputes the wrapped lines and `h` of a `card` or `note` at its current `w`.
- Consumes: `Measurer.wrap` from Task 1.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_layout_defects.py`:

```python
def card_heights_match_their_lines(node, failures, path='body'):
    if node['kind'] == 'card':
        want = (len(node['label_lines']) + len(node['detail_lines'])) * LINE[BODY] + 2 * CARD_PAD_Y
        if abs(node['h'] - want) > 0.01:
            failures.append((path, node['label'], node['h'], want))
    elif node['kind'] == 'group':
        pad = GAP if node.get('heading') is not None else 0
        head = LINE[BODY] + 4 if node.get('heading') is not None else 0
        children = node['children']
        if node['arrange'] == 'row':
            want = max(child['h'] for child in children) + 2 * pad + head
        else:
            want = sum(child['h'] for child in children) + node['gap'] * (len(children) - 1) + 2 * pad + head
        if abs(node['h'] - want) > 0.01:
            failures.append((path, node.get('heading'), node['h'], want))
        for index, child in enumerate(children):
            card_heights_match_their_lines(child, failures, f'{path}.children[{index}]')


STRETCHED = page({'kind': 'group', 'arrange': 'row', 'children': [
    {'kind': 'group', 'heading': 'Encoder layer', 'arrange': 'column', 'children': [
        {'kind': 'card', 'id': 'wide', 'label': 'Encoder self-attention',
         'detail': 'MultiHead(Q, K, V) from one sequence of five hundred twelve dimensional token vectors'},
        {'kind': 'card', 'id': 'short', 'label': 'FFN', 'detail': 'max(0, xW_1 + b_1)W_2 + b_2 applied to every position'}]},
    {'kind': 'card', 'id': 'aside', 'label': 'Residual connection', 'detail': 'LayerNorm(x + Sublayer(x))'}]})


class StaleHeightTests(unittest.TestCase):
    def test_every_placed_card_is_as_tall_as_its_lines(self):
        for scene in (STRETCHED,):
            _, _, laid_out = compose_page(scene)
            failures = []
            card_heights_match_their_lines(laid_out['panels'][0]['body'], failures)
            self.assertEqual(failures, [])

    def test_the_fixtures_have_no_stale_heights(self):
        import json
        from pathlib import Path
        fixtures = Path(__file__).resolve().parent / 'fixtures' / 'overview'
        for name in ('attention-run.json', 'attention-scene.json', 'variety-scene.json'):
            _, _, laid_out = compose_page(json.loads((fixtures / name).read_text()))
            failures = []
            for panel in laid_out['panels']:
                card_heights_match_their_lines(panel['body'], failures, panel['id'])
            self.assertEqual(failures, [], name)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m unittest tests.test_layout_defects.StaleHeightTests -v`
Expected: `test_the_fixtures_have_no_stale_heights` fails on `attention-run.json` with three cards at 68 against 50. If `test_every_placed_card_is_as_tall_as_its_lines` passes before the fix, widen the `short` card's detail until the row stretches it, then continue.

- [ ] **Step 3: Add `refit` and recompute heights in `place`**

In `papers/figures/layout.py`, add before `place`:

```python
def refit(node, measure):
    """Wrap a card or note again at its current width and set ``h`` from the result."""
    if node['kind'] == 'card':
        weight = None if node.get('plain') else 700
        node['label_lines'] = measure.wrap(node['label'], node['w'] - 2 * CARD_PAD_X, BODY, weight)
        node['detail_lines'] = (measure.wrap(node['detail'], node['w'] - 2 * CARD_PAD_X)
                                if node.get('detail') else [])
        node['h'] = (len(node['label_lines']) + len(node['detail_lines'])) * LINE[BODY] + 2 * CARD_PAD_Y
    elif node['kind'] == 'note':
        lines = [str(line) for line in node['lines']]
        node['wrapped'] = [wrapped for index, line in enumerate(lines)
                           for wrapped in measure.wrap(line, node['w'] - 2 * CARD_PAD_X - 4, BODY,
                                                       700 if index == 0 else None)]
        node['h'] = len(node['wrapped']) * LINE[BODY] + 2 * CARD_PAD_Y + 4
```

Replace `place` with:

```python
def place(node, x, y, canvas, measure, stretch=None):
    """Set absolute ``x`` and ``y``; column children stretch to the column width.

    A card or note that grows re-wraps at its final width, and every group takes the height of
    its placed children, so no box is taller than its text.
    """
    node['x'], node['y'] = x, y
    if stretch is not None and node['kind'] in ('card', 'group', 'note', 'steps', 'divider'):
        wanted = max(node['w'], min(stretch, canvas.stretch_max))
        if wanted != node['w']:
            node['w'] = wanted
            refit(node, measure)
    if node['kind'] != 'group':
        return
    pad = GAP if node.get('heading') is not None else 0
    head = LINE[BODY] + 4 if node.get('heading') is not None else 0
    gap = node['gap']
    cx, cy = x + pad, y + pad + head
    if node['arrange'] == 'row':
        for child in node['children']:
            place(child, cx, cy, canvas, measure, stretch=child.get('justified'))
            cx += child['w'] + gap
        node['h'] = max(child['h'] for child in node['children']) + 2 * pad + head
    else:
        inner = node['w'] - 2 * pad
        widest = max(child['w'] for child in node['children'])
        for child in node['children']:
            place(child, cx, cy, canvas, measure, stretch=min(inner, max(widest, canvas.stretch_max)))
            cy += child['h'] + gap
        node['h'] = sum(child['h'] for child in node['children']) + gap * (len(node['children']) - 1) + 2 * pad + head
```

In `papers/figures/render.py`, change the call in `compose` to:

```python
        place(body, x + PANEL_PAD, body_y, canvas, measure)
```

The `_draw` branches for `card` and `note` still wrap at the final width. Leave them; after this task they compute the same lines `refit` stored.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m unittest tests.test_layout_defects tests.test_scene_layout tests.test_layout_canvas -v`
Expected: all pass. If a test in `test_scene_layout` or `test_layout_canvas` calls `place` directly, add the `measure` argument there.

- [ ] **Step 5: Commit**

```bash
git add papers/figures/layout.py papers/figures/render.py tests/test_layout_defects.py
git commit -m "Recompute a stretched card's height at its final width"
```

---

### Task 4: A mixed column reflows into two

**Files:**
- Modify: `papers/figures/layout.py:222-236` (`reflow_narrow`)
- Test: `tests/test_layout_defects.py`

**Interfaces:**
- Produces: `layout.reflow_narrow(node, inner, measure)`, unchanged signature. Every unheaded column group that is a direct child of a column is flattened into its parent before the node count is checked.
- Consumes: `place` with `measure` from Task 3, since the split by height uses child heights.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_layout_defects.py`:

```python
MIXED_COLUMN = page({'kind': 'group', 'arrange': 'column', 'children': [
    {'kind': 'sequence', 'items': [{'text': 'x_1', 'sub': '"The"'}, {'text': 'x_2', 'sub': '"Law"'},
                                   {'text': 'x_3', 'sub': '"will"'}, {'text': 'x_4', 'sub': '"never"'}]},
    {'kind': 'group', 'arrange': 'column', 'children': [
        {'kind': 'card', 'id': 'pe', 'label': 'Positional encoding',
         'detail': 'PE(pos,2i) = sin(pos/10000^(2i/d_model)); PE(pos,2i+1) = cos(pos/10000^(2i/d_model))'},
        {'kind': 'card', 'id': 'sdpa', 'label': 'Scaled dot-product attention',
         'detail': 'softmax(QK^T / sqrt(d_k)) V', 'tone': 'blue'}]},
    {'kind': 'steps', 'lines': ['Project each token to Q = xW^Q, K = xW^K, V = xW^V',
                                'scores = Q K^T (n x n compatibility of queries and keys)',
                                'scale by 1/sqrt(d_k) with d_k = 64, then softmax each row',
                                'output = weights · V']}]},
    edges=[{'from': 'pe', 'to': 'sdpa'}])


class ReflowTests(unittest.TestCase):
    def test_a_column_with_an_unheaded_group_reflows_into_two_columns(self):
        _, placements, laid_out = compose_page(MIXED_COLUMN)
        body = laid_out['panels'][0]['body']
        self.assertEqual(body['arrange'], 'row')
        self.assertEqual(len(body['children']), 2)
        self.assertGreaterEqual(placements[0]['fill'], 0.55)

    def test_flattening_keeps_every_card_and_its_id(self):
        _, _, laid_out = compose_page(MIXED_COLUMN)
        ids = []

        def walk(node):
            if node['kind'] == 'card':
                ids.append(node['id'])
            for child in node.get('children', []):
                walk(child)
        walk(laid_out['panels'][0]['body'])
        self.assertEqual(sorted(ids), ['pe', 'sdpa'])
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m unittest tests.test_layout_defects.ReflowTests -v`
Expected: `test_a_column_with_an_unheaded_group_reflows_into_two_columns` fails with `'column' != 'row'`. On 2026-09-24 this Scene measured 0.346 fill with `FixedMeasurer`.

- [ ] **Step 3: Flatten each unheaded column child on its own**

In `papers/figures/layout.py`, replace the first flattening block of `reflow_narrow` (the `if node['arrange'] == 'column' and len(node['children']) > 1 and all(...)` statement and its body) with:

```python
    def unheaded_column(child):
        return child['kind'] == 'group' and child['arrange'] == 'column' and child.get('heading') is None

    if node['arrange'] == 'column' and any(unheaded_column(child) for child in node['children']):
        # An unheaded column group inside a column draws no frame, so its children are this
        # column's children. Flatten each one so the node count and the split see them all.
        node['children'] = [grandchild for child in node['children']
                            for grandchild in (child['children'] if unheaded_column(child) else [child])]
        size(node, inner, measure)
```

Leave the rest of the function as it is.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m unittest tests.test_layout_defects tests.test_scene_layout -v`
Expected: all pass, including `test_a_narrow_column_reflows_into_two` in `test_scene_layout`.

- [ ] **Step 5: Commit**

```bash
git add papers/figures/layout.py tests/test_layout_defects.py
git commit -m "Flatten every unheaded column so a mixed column reflows"
```

---

### Task 5: Arrows keep clear of frames and labels keep clear of headings

**Files:**
- Modify: `papers/figures/route.py` (`runs_along`, `route`, `clear`)
- Modify: `papers/figures/render.py:73-84` (`_draw` group branch), `papers/figures/render.py:233-240` (`_draw_edge`)
- Test: `tests/test_layout_defects.py`

**Interfaces:**
- Produces: `route.runs_along(segment, frame) -> bool`. `route.route(source, target, obstacles, frames=()) -> list[tuple]`, where a candidate is rejected when a segment runs along a frame edge. `_draw` registers a headed group's heading text box under a `!` key. `route` takes the headings as `soft` boxes and avoids them when another path is clear; `label_fits` rejects a label over one.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_layout_defects.py`:

```python
from papers.figures.palette import LIGHT
from papers.figures.render import _draw
from papers.figures.route import crosses, route, runs_along, segments
from papers.figures.layout import place, size


class FrameRoutingTests(unittest.TestCase):
    def test_runs_along_detects_a_segment_on_a_frame_edge(self):
        frame = (100, 100, 300, 200)
        self.assertTrue(runs_along(((50, 100), (250, 100)), frame))    # on the top edge
        self.assertTrue(runs_along(((400, 150), (400, 250)), frame))   # on the right edge
        self.assertTrue(runs_along(((50, 103), (250, 103)), frame))    # within the clearance
        self.assertFalse(runs_along(((50, 150), (450, 150)), frame))   # crosses the frame
        self.assertFalse(runs_along(((50, 100), (90, 100)), frame))    # beside the frame

    def test_a_route_never_runs_along_a_frame(self):
        source, target = (0, 0, 80, 30), (400, 0, 80, 30)
        frame = (150, 15, 150, 200)  # its top edge lies on the straight path at y = 15
        points = route(source, target, [], frames=[frame])
        self.assertFalse(any(runs_along(segment, frame) for segment in segments(points)))

    def test_a_card_inside_a_frame_reaches_a_card_above_the_frame(self):
        # The ENCODER case from tests/fixtures/overview/attention-scene.json: the source sits in a
        # headed group with a 14-unit pad, a sibling blocks the straight way up, and the target is
        # above the frame. The old lane at 14 lay on the frame's edge; the route needs a lane past it.
        frame = (100, 100, 200, 300)
        blocker = (114, 150, 172, 40)
        source, target = (114, 250, 172, 40), (114, 40, 172, 40)
        points = route(source, target, [blocker], frames=[frame])
        self.assertFalse(any(runs_along(segment, frame) for segment in segments(points)))
        self.assertFalse(any(crosses(segment, blocker) for segment in segments(points)))

class HeadingObstacleTests(unittest.TestCase):
    def test_a_group_heading_is_an_obstacle(self):
        measure = FixedMeasurer()
        group = {'kind': 'group', 'heading': 'Decoder layer', 'arrange': 'column', 'children': [
            {'kind': 'card', 'id': 'a', 'label': 'Masked self-attention'},
            {'kind': 'card', 'id': 'b', 'label': 'Cross-attention'}]}
        size(group, 400, measure)
        place(group, 10, 20, Canvas(1000), measure)
        out, boxes = [], {}
        _draw(group, out, boxes, measure, LIGHT)
        heading_w = measure.width('Decoder layer', BODY, 700)
        heading_box = (10 + GAP, 20 + 4, heading_w, LINE[BODY])
        obstacles = [box for key, box in boxes.items() if key.startswith('#')]
        self.assertIn(heading_box, obstacles)
        self.assertIn('a', boxes)
        self.assertEqual(len([key for key in boxes if key.startswith('@')]), 1)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m unittest tests.test_layout_defects.FrameRoutingTests tests.test_layout_defects.HeadingObstacleTests -v`
Expected: `ImportError: cannot import name 'runs_along'`.

- [ ] **Step 3: Add `runs_along` and the `frames` parameter**

In `papers/figures/route.py`, add after `crosses`:

```python
def runs_along(segment, frame):
    """A segment that lies on a frame edge, within the arrow clearance, for more than a corner."""
    (x1, y1), (x2, y2) = segment
    left, top, w, h = frame
    right, bottom = left + w, top + h
    if y1 == y2:
        near_edge = abs(y1 - top) <= ARROW_CLEARANCE or abs(y1 - bottom) <= ARROW_CLEARANCE
        overlap = min(max(x1, x2), right) - max(min(x1, x2), left)
        return near_edge and overlap > 2 * ARROW_CLEARANCE
    if x1 == x2:
        near_edge = abs(x1 - left) <= ARROW_CLEARANCE or abs(x1 - right) <= ARROW_CLEARANCE
        overlap = min(max(y1, y2), bottom) - max(min(y1, y2), top)
        return near_edge and overlap > 2 * ARROW_CLEARANCE
    return False
```

Change `clear` to:

```python
def clear(points, obstacles, frames=()):
    return (not any(crosses(segment, box) for segment in segments(points) for box in obstacles)
            and not any(runs_along(segment, frame) for segment in segments(points) for frame in frames))
```

Change the signature of `route` to `def route(source, target, obstacles, frames=()):`, extend its docstring with one sentence, "``frames`` are group frames an arrow may cross but never run along.", and change the final loop to:

```python
    for points in candidates:
        if clear(points, obstacles, frames):
            return points
```

Add lanes past the frame. With the frame rule, the lane at 14 outside a padded group lies on the frame's edge and is rejected, so an arrow needs a lane further out. On 2026-09-24 a check with the native Measurer showed that `mhsa → kv` in `attention-scene.json` loses its only lane under the frame rule, and `dffn → lsm` loses its lane once headings are obstacles; both route again with the candidates below, and no fixture Scene loses an arrow. In the "target on the right" branch replace `for offset in (14, 28, 42, -14, -28, -42):` with:

```python
        for offset in (14, 28, 42, -14, -28, -42, 21, 35, -21, -35):
```

In the "target above" and "target below" branches replace both `for side in (-14, 14):` with:

```python
        for side in (-14, 14, -21, 21, -35, 35):
```

A lane on a card's edge is already rejected by `crosses`, which applies the 4-unit clearance, so the offsets stay in the same order and the new ones only apply when the old ones fail.

Implementation note (2026-09-24): these lanes were not enough.

- After Tasks 3 and 4, `kv1 → matmul` in `attention-scene.json` lost its route with both measurers, because the gutter turn at `tx - 12` lies 2 units inside the target's frame edge. The "target on the right" branch now also tries a gutter 7 units before that frame, the middle of the 14-unit gap to a sibling frame, after the original gutter. `test_a_card_reaches_a_card_inside_a_frame_on_its_right` and `test_a_card_reaches_a_card_inside_the_next_frame` cover it.
- Heading obstacles broke three library Scenes (`reader-e7ed22b3`, `reader-f0627474`, `reader-f77ab019`). A heading sits 22 units above the first card of its group and starts at the card's left edge, so every path into or out of that card's top center passes the heading text. On `main` these arrows ran 2 to 5 units under the heading text, or through it. Headings are soft boxes: `route` tries every candidate with them as obstacles, then again without them. `test_a_route_crosses_a_heading_when_nothing_else_is_clear` covers it.

- [ ] **Step 4: Register the heading box and pass frames to `route`**

In `papers/figures/render.py`, in the `group` branch of `_draw`, after the line that appends the heading text (`out.append(_text(x + GAP, y + 16, heading, weight=700, fill=colour))`), add:

```python
            # The heading text is a leaf: an arrow does not cross it and a label does not cover it.
            boxes['#' + str(len(boxes))] = (x + GAP, y + 4, measure.width(heading, BODY, 700), LINE[BODY])
```

In `_draw_edge`, change the route call to:

```python
    points = route(source, target, obstacles, frames)
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python3 -m unittest tests.test_layout_defects tests.test_scene_layout -v`
Expected: all pass. The three fixture Scenes were checked against these exact candidates with the native Measurer on 2026-09-24. If a Scene from the local library raises `LayoutError` in Task 6, add `-49, 49` to both loops. Do not remove the frame rule.

- [ ] **Step 6: Commit**

```bash
git add papers/figures/route.py papers/figures/render.py tests/test_layout_defects.py
git commit -m "Route arrows clear of frames and labels clear of headings"
```

---

### Task 6: Render every known Scene and refresh the reference figure

**Files:**
- Modify: `docs/attention_figure.png`
- Modify: `docs/superpowers/specs/2026-09-18-overview-scene-layout-design.md` (Open list)

**Interfaces:**
- Consumes: every change above. This task proves them in the native renderer.

- [ ] **Step 1: Run the whole Python suite with the renderer**

Run: `python3 -m unittest discover -s tests -v 2>&1 | tail -20`
Expected: every test passes. `tests/test_figure.py` and `tests/test_scene_layout.py` exercise `papers/html-snapshot`.

- [ ] **Step 2: Compose every stored Scene**

Run: `python3 tests/baseline_scenes.py`
Expected: one `wrote` line per fixture Scene and per Scene in the local library, exit code 0, no `LayoutError`. A `LayoutError` names a stored Scene whose arrows no longer route; add `-49, 49` to both lane loops in `route` as Task 5 step 5 says, and run again.

- [ ] **Step 3: Check the Attention fixture in the renderer**

Run:

```bash
python3 - <<'EOF'
import json, tempfile
from papers.figures import Figure
scene = json.load(open('tests/fixtures/overview/attention-run.json'))
with tempfile.TemporaryDirectory() as directory:
    result = Figure(width=1000).build(scene, directory, 'fig1', frame='page', page_title='Attention Is All You Need')
    print('issues', result.issues)
    print('density', round(result.density, 1))
    print('fill', [(item['id'], item['fill']) for item in result.placements])
EOF
```

Expected: `issues []`, density at or above 40, every fill at or above 0.4. Record the three numbers in the commit message of step 5.

- [ ] **Step 4: Re-lay out the reference figure**

The figure in `docs/attention_figure.png` came from the live run of 2026-09-18. Its Scene is in the local library under `~/Library/Application Support/LocalXiv/library/papers/*/reader/overview-figures/*/scene.json` for the Attention paper. Find it with:

```bash
grep -l "Attention Is All You Need" ~/Library/Application\ Support/LocalXiv/library/papers/*/reader/overview-figures/*/scene.json
```

Then render it and copy the PNG:

```bash
python3 - <<'EOF'
import json, sys, tempfile, shutil
from pathlib import Path
from papers.figures import Figure
path = Path(sys.argv[1] if len(sys.argv) > 1 else input('scene.json path: ').strip())
scene = json.loads(path.read_text())
with tempfile.TemporaryDirectory() as directory:
    result = Figure(width=1000).build(scene, directory, 'fig1', frame='page', page_title='Attention Is All You Need')
    print('issues', result.issues, 'density', round(result.density, 1), 'fill', [item['fill'] for item in result.placements])
    shutil.copyfile(Path(directory) / result.assets['png'], 'docs/attention_figure.png')
EOF
```

Open `docs/attention_figure.png` and check by eye: panel 1 is two columns, no card has an empty line, every step has one number, and no arrow lies on a group border.

- [ ] **Step 5: Record the result in the design's Open list**

In `docs/superpowers/specs/2026-09-18-overview-scene-layout-design.md`, add to the Open section:

```markdown
- 2026-09-24: the five layout defects from the 2026-09-23 audit (mixed-column reflow, stale card height, wrap rounding, arrows along frames and labels on headings, double step numbers) are fixed in `papers/figures/` with regression tests in `tests/test_layout_defects.py`. `docs/attention_figure.png` is re-laid out from the 2026-09-18 Scene.
```

- [ ] **Step 6: Commit and merge**

```bash
git add docs/attention_figure.png docs/superpowers/specs/2026-09-18-overview-scene-layout-design.md
git commit -m "Re-lay out the reference figure after the layout fixes"
git checkout main
git merge --no-ff figure-library-layout-defects
```

Write the density, fill, and issue counts from step 3 in the merge commit body.

## Self-review

- Spec coverage: each of the five defects has one task with a test that fails before and passes after. Task 6 covers the renderer and the reference figure.
- Placeholders: none. Every code step is complete.
- Type consistency: `place(node, x, y, canvas, measure, stretch=None)` in Task 3 matches the call in Task 3 step 3 and the test in Task 5. `route(source, target, obstacles, frames=())` in Task 5 matches `_draw_edge`. `step_text` in Task 2 is imported by the test file's first line, so Task 2 must land before the file is run.
