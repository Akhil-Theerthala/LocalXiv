# Figure arrows and nested frames plan (2026-10-08)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** An arrow between two stacked cards runs straight down, and nested group frames read as surfaces instead of stacked borders.

**Architecture:** Four changes in the Figure library, `papers/figures/`. The router gets entry points across the shared span of two stacked boxes. The renderer falls back to a group's top edge when a card inside it cannot be reached from above, and draws arrow labels after it has routed every arrow of a panel. The group node draws a nested headed group as a filled surface with no stroke, and a chip takes the opposite fill of its surface. No model call changes.

**Tech stack:** Python 3 in `.venv`, `unittest`, the native renderer `papers/html-snapshot`, `uvx ruff`.

**Spec:** this file. The "Design" section is the specification. The evidence is in "Measured defects".

## Design

Rules the figure follows after this plan. Each rule names the task that builds it.

- **Stacked entry (Task 1).** When one box is above the other and their horizontal spans overlap by at least `OVERLAP_MIN`, the arrow may leave the source's bottom and enter the target's top at any point across the overlap. The centred straight path stays first. A path that enters off centre, straight or as a Z through the gap, comes before any path that leaves the overlap and loops down a side.
- **Frame fallback (Task 2).** When no stacked-entry path is clear and the target card lies inside a headed group that the source is outside, the arrow ends on that group's top edge instead of the card.
- **Labels after arrows (Task 3).** The renderer draws a panel's arrow labels after it has routed every arrow of the panel. A label whose box crosses any arrow of the panel is dropped, as a label over a card is dropped today.
- **Nested surfaces (Task 4).** A headed group with no headed group above it draws its frame as today. A headed group nested inside a headed group draws no stroke and a solid fill that alternates by level: the first nested level is `palette.sunk`, the next is `palette.page`, and so on. A toned group keeps its tone at any level. A chip on a sunk surface draws on `palette.page`; elsewhere it draws on `palette.sunk` as today.

Out of scope, by decision: the arrow between two side-by-side panels, the equation box inside a card, the sequence item arrow in the Attention How panel, and arrows that share a lane into one target.

## Measured defects

From `tests/story_fixtures.py` scenes through `overview_workflow.generate` on `main` at `18e9402`. Coordinates are in page units.

| Arrow | Source box | Target box | Path today | Defect |
|---|---|---|---|---|
| `enc_mha` to `ffn_core` (Attention, Model panel) | (80, 629, 362, 68) | (80, 779, 362, 50) | (80,663) (59,663) (59,804) (77,804) | Leaves the column, loops down the left gutter, enters the side. Cause: the centred straight path crosses the target group's heading text, and the router's only other entries are side lanes. |
| `dec_mask_mha` to `dec_cross_mha` (Attention, Model panel) | (558, 629, 362, 68) | (558, 797, 362, 50) | (920,663) (941,663) (941,822) (923,822) | Same loop on the right. The target group's heading and detail span the whole card width, so no top entry is clear. |
| `problems` to `u` (AI Control, Setup panel) | (38, 329, 431, 32) | (52, 411, 403, 32) | (254,361) (254,408) | None. Must stay one vertical segment. |

A prototype of the stacked entry on `main` turned the first arrow into (370,697) (370,776): one vertical segment beside the heading. The second arrow needs the frame fallback.

Nested frames: the Attention Model panel draws panel, stack, layer, sublayer, card, five rectangles deep, every one with a border. A prototype of the nested surfaces lost no information and removed two border levels. In that prototype the chips inside "Untrusted monitoring" in the AI Control Result panel vanished, because a chip and its sunk surface share one fill. The chip rule above is the fix.

## Global constraints

- Work in the worktree `/Users/silver/Developer/LocalXiv/.worktrees/figure-arrows` on the branch `figure-arrows`. Never run git commands in `/Users/silver/Developer/LocalXiv`.
- `tests` in the worktree is a symlink to the main checkout's `tests/`, which git ignores. Never `git add tests`. Never `git add -A` or `git add .`; name each file.
- Run `.venv/bin/python`, not `python3`. The `anthropic` package lives in the venv.
- Run `uvx ruff check papers tests` before each commit and fix what it reports.
- Commit messages describe the change in one line, in plain English, with no attribution line.
- After each Figure library task, run the saved-scene check and compare with the baseline. A new `ERROR` line, a new issue, or a new warning is a regression. A changed height is expected.

```sh
.venv/bin/python tests/relayout_saved_scenes.py > .scratch/relayout-after.txt
diff .scratch/relayout-before.txt .scratch/relayout-after.txt
```

`.scratch/relayout-before.txt` is the output on `main` at `18e9402`. It has 45 lines, 9 `ERROR` lines, and 5 lines with warnings. The run takes about 10 minutes. Start it in the background right after the task's tests pass and read the diff before the commit.

- Tests are component tests through a public entry point, as `docs/development.md` says under "Check changes". The entry points here are `overview_workflow.generate` through `tests.test_overview_composition._run`, and `papers.figures.Figure.build`. Write no test of a private helper.
- The composition tests take about 65 seconds. Run them with `.venv/bin/python -m unittest tests.test_overview_composition tests.test_figure_layout`.

## Review focus

Conditions no task's tests exercise, most likely to bite first:

1. A stacked pair where the source is below the target. The stacked entry must work upward too: the arrow leaves the source's top and enters the target's bottom. Task 1 covers it with a second test on a synthetic scene.
2. A stacked pair whose overlap is narrower than `OVERLAP_MIN`. The router must not add stacked candidates; the side lanes stay. Task 1's code guards it and the saved-scene check covers it.
3. A frame fallback where another card sits between the frame's top edge and the source. The fallback path must still pass `clear`, so the arrow loops as today instead of crossing that card. Task 2's code guards it.
4. A label whose own arrow is the only arrow near it. The label must still draw, because the crossing check skips the label's own arrow. Task 3's haiku test asserts that at least one label is drawn.
5. A nested toned group. It keeps its tone fill and tone stroke at any level, and it does not flip the surface for its chips. Task 4 covers it with a synthetic scene.

---

## Test helpers

Task 1 creates `tests/test_figure_layout.py` with these helpers at the top. Later tasks add test classes to the same file.

```python
"""Arrow routing and nested frames on the story scenes real models returned, through the public build path."""
import re
import tempfile
import unittest
from collections import namedtuple
from pathlib import Path

from papers.figures import Figure
from papers.figures.palette import LIGHT
from tests.story_fixtures import control_story, load, luna_story
from tests.test_overview_composition import _run
from tests.test_overview_workflow import _document

Box = namedtuple('Box', 'x y w h')
NODE = (r'<g data-node="[^"]*"><rect x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)"([^>]*)/>'
        r'(?:(?!</g>).)*?>{}<')
EDGE = re.compile(r'<path data-edge="([^"]+)" d="M ([^"]+)"')
LABEL = re.compile(r'<text data-label="([^"]+)" x="([\d.]+)" y="([\d.]+)"')


def box(svg, text):
    """The rect of the card, chip, or headed group that shows ``text``, and the rect's other attributes."""
    match = re.search(NODE.format(re.escape(text)), svg, re.S)
    assert match, text
    return Box(*(float(value) for value in match.groups()[:4])), match.group(5)


def arrows(svg):
    """Every arrow's points by "from:to"."""
    return {key: [tuple(float(value) for value in pair.split()) for pair in d.split(' L ')]
            for key, d in EDGE.findall(svg)}


def luna():
    return _run([load('attention-selection.json'), load('attention-luna-digest.json'),
                 load('attention-luna-scene.json'), luna_story()], _document(''))[3]


def control():
    return _run([load('control-sonnet-selection.json'), load('control-sonnet-digest.json'),
                 load('control-sonnet-scene.json'), control_story()], load('control-sonnet-document.json'))[3]


def build(scene):
    """The light SVG of a scene through the Figure library alone."""
    with tempfile.TemporaryDirectory() as directory:
        return Figure().build(scene, Path(directory), 'fig1').svg
```

`_run` returns `(provider, result, scene, svg)`. The svg is the light `overview.source.svg` of the run.

In the upward test, the chip under the top card keeps its natural width and sits at the left, so it covers the centre of the two cards' shared span and blocks the centred straight path. Without the stacked entry the router loops down a side; with it the arrow enters the top card's bottom to the right of the chip.

### Task 1: Stacked entry

**Files:**
- Modify: `papers/figures/route.py` (`route`, the `if ty + th <= sy` and `elif sy + sh <= ty` blocks, lines 123-141)
- Modify: `papers/figures/render.py` (`_draw_edge`, the `out.append(f'<path d=...` line, about line 93)
- Create: `tests/test_figure_layout.py`

**Interfaces:**
- Produces: every arrow `<path>` carries `data-edge="<from>:<to>"`. Tests and later tasks read arrows by that attribute.
- Produces: `papers.figures.route._stacked(source, target, y1, y2)`, used only inside `route`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_figure_layout.py` with the helpers above, then:

```python
class StackedEntryTests(unittest.TestCase):
    """gpt-6-luna's Attention Model panel: cards in sibling sublayers, one above the other."""

    @classmethod
    def setUpClass(cls):
        cls.svg = luna()

    def test_an_arrow_into_a_sibling_sublayer_runs_straight_down_beside_the_heading(self):
        source, _ = box(self.svg, 'Encoder multi-head self-attention')
        target, _ = box(self.svg, 'Position-wise feed-forward network')
        (x1, y1), (x2, y2) = arrows(self.svg)['enc_mha:ffn_core']
        self.assertEqual(x1, x2)
        self.assertTrue(max(source.x, target.x) <= x1 <= min(source.x + source.w, target.x + target.w))
        self.assertAlmostEqual(y1, source.y + source.h, delta=0.5)
        self.assertAlmostEqual(y2, target.y - 3, delta=0.5)

    def test_an_arrow_upward_into_a_sibling_group_enters_the_bottom_across_the_overlap(self):
        scene = {
            'title': 'Upward', 'subtitle': 'one arrow up', 'footer': 'none', 'illustrative': True,
            'layout': 'stack', 'panels': [{
                'id': 'why', 'heading': 'Why: up',
                'body': {'kind': 'group', 'arrange': 'column', 'children': [
                    {'kind': 'group', 'heading': 'Upper group with a heading across the card', 'arrange': 'column',
                     'children': [{'kind': 'card', 'id': 'top', 'label': 'Top card',
                                   'detail': 'the target of the arrow, wide enough for an entry beside the chip'},
                                  {'kind': 'card', 'label': 'a chip in the way of the centred straight path',
                                   'minor': True}]},
                    {'kind': 'card', 'id': 'bottom', 'label': 'Bottom card',
                     'detail': 'the source of the arrow, as wide as the target card above it is'}]},
                'edges': [{'from': 'bottom', 'to': 'top'}]}]}
        svg = build(scene)
        source, _ = box(svg, 'Bottom card')
        target, _ = box(svg, 'Top card')
        points = arrows(svg)['bottom:top']
        self.assertLessEqual(len(points), 4)
        for x, _ in points:
            self.assertTrue(max(source.x, target.x) <= x <= min(source.x + source.w, target.x + target.w))
        self.assertAlmostEqual(points[0][1], source.y, delta=0.5)
        self.assertAlmostEqual(points[-1][1], target.y + target.h + 3, delta=0.5)

    def test_a_straight_arrow_into_a_group_stays_one_segment(self):
        svg = control()
        (x1, y1), (x2, y2) = arrows(svg)['problems:u']
        self.assertEqual(x1, x2)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m unittest tests.test_figure_layout -v`
Expected: three failures. `arrows()` returns `{}` because no path carries `data-edge` yet.

- [ ] **Step 3: Tag every arrow path**

In `papers/figures/render.py`, in `_draw_edge`, change the path line to:

```python
    out.append(f'<path data-edge="{esc(str(edge["from"]))}:{esc(str(edge["to"]))}" d="{path}" fill="none" '
               f'stroke="{palette.accent if accent else palette.text}" stroke-width="1.6" '
               f'marker-end="url(#{"arrow-accent" if accent else "arrow"})"/>')
```

Run the tests again. Expected: the third test passes. The first two fail on the path shape.

- [ ] **Step 4: Add the stacked candidates to the router**

In `papers/figures/route.py`, add under the constants:

```python
# Where an arrow between two stacked boxes may enter the target, as fractions of their shared span.
# The centre first; then the right half, where a group heading rarely reaches; then the left.
STACKED_FRACTIONS = (0.5, 0.65, 0.8, 0.35, 0.2, 0.9, 0.1)
```

Add after `_overlap_middle`:

```python
def _stacked(source, target, y1, y2):
    """Paths between a box and one above or below it that enter the target across their shared span.

    ``y1`` is the source edge the arrow leaves and ``y2`` the target edge it enters. A path is
    straight when it leaves where it enters, else a Z through the middle of the gap. The entry
    beside a group heading is what lets an arrow into a sibling group run down instead of around.
    """
    sx, _, sw, _ = source
    tx, _, tw, _ = target
    low, high = max(sx, tx), min(sx + sw, tx + tw)
    if high - low < OVERLAP_MIN:
        return []
    mid = (y1 + y2) / 2
    paths = []
    for fraction in STACKED_FRACTIONS:
        x_in = low + (high - low) * fraction
        for x_out in (x_in, low + (high - low) / 2):
            paths.append([(x_out, y1), (x_out, y2)] if abs(x_out - x_in) < 1
                         else [(x_out, y1), (x_out, mid), (x_in, mid), (x_in, y2)])
    return paths
```

In `route`, in the `if ty + th <= sy:` block, after the line that appends the straight or centred-Z candidate and before `for side in (-14, 14, -21, 21, -35, 35):`, add:

```python
        candidates.extend(_stacked(source, target, y1, y2))
```

Add the same line at the same place in the `elif sy + sh <= ty:` block. Update the `route` docstring's candidate list: "straight, a Z through the gap between the boxes, an entry across the shared span of two stacked boxes, an L, and a detour down the side of the source".

- [ ] **Step 5: Run the tests to verify they pass**

Run: `.venv/bin/python -m unittest tests.test_figure_layout tests.test_overview_composition -v`
Expected: all pass.

- [ ] **Step 6: Saved-scene check, lint, commit**

```sh
.venv/bin/python tests/relayout_saved_scenes.py > .scratch/relayout-after.txt
diff .scratch/relayout-before.txt .scratch/relayout-after.txt
uvx ruff check papers tests
git add papers/figures/route.py papers/figures/render.py
git commit -m "Let an arrow between stacked cards enter the target across their shared span"
```

Expected diff: height or warning changes only, no new `ERROR`, no new issue. If a warning count rises on a scene, open that scene's arrows with the dump in the next step and decide whether the new path is the loop or the entry; an entry that is longer than the loop is not possible, so a rise is a bug in the candidates.

### Task 2: Frame fallback

**Files:**
- Modify: `papers/figures/render.py` (`_draw_edge`, between the `search` fallback and `drawn.append`)
- Modify: `tests/test_figure_layout.py`

**Interfaces:**
- Produces: `papers.figures.render._own_frame(source, target, boxes)` and `_stays_in(points, span)`, used only inside `_draw_edge`.

- [ ] **Step 1: Write the failing test**

Add to `StackedEntryTests`:

```python
    def test_an_arrow_blocked_by_the_whole_heading_ends_on_the_group_frame(self):
        source, _ = box(self.svg, 'Masked multi-head self-attention')
        frame, _ = box(self.svg, 'Encoder–decoder attention sublayer')
        target, _ = box(self.svg, 'Encoder–decoder multi-head attention')
        (x1, y1), (x2, y2) = arrows(self.svg)['dec_mask_mha:dec_cross_mha']
        self.assertEqual(x1, x2)
        self.assertTrue(max(source.x, target.x) <= x1 <= min(source.x + source.w, target.x + target.w))
        self.assertAlmostEqual(y1, source.y + source.h, delta=0.5)
        self.assertAlmostEqual(y2, frame.y - 3, delta=0.5)
```

The en dash in both group names is the character the scene uses. Copy it from `tests/fixtures/overview/attention-luna-scene.json`.

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/python -m unittest tests.test_figure_layout.StackedEntryTests -v`
Expected: the new test fails with four points on the arrow.

- [ ] **Step 3: Add the fallback**

In `papers/figures/render.py`, add after `_within`:

```python
def _own_frame(source, target, boxes):
    """The smallest group frame that holds the target and not the source, or None."""
    frames = [box for key, box in boxes.items()
              if key.startswith('@') and inside(target, box) and not inside(source, box)]
    return min(frames, key=lambda box: box[2] * box[3]) if frames else None


def _stacked_span(source, target):
    """The horizontal span two boxes share when one is above the other, or None."""
    sx, sy, sw, sh = source
    tx, ty, tw, th = target
    if not (sy + sh <= ty or ty + th <= sy):
        return None
    low, high = max(sx, tx), min(sx + sw, tx + tw)
    return (low, high) if high - low >= OVERLAP_MIN else None


def _stays_in(points, span):
    low, high = span
    return all(low <= x <= high for x, _ in points)
```

Import `OVERLAP_MIN` from `papers.figures.route`. In `_draw_edge`, after the `search` block and before `if points is None: raise LayoutError(...)`, add:

```python
    span = _stacked_span(source, target)
    if span is not None and (points is None or not _stays_in(points, span)):
        # The card cannot be entered from above, because its group's heading spans the whole
        # overlap: the arrow ends on the group's top edge instead, where the reader sees it enter
        # the group that holds the card.
        frame = _own_frame(source, target, boxes)
        if frame is not None:
            try:
                fallback = route(source, frame, obstacles, frames, headings)
            except LayoutError:
                fallback = None
            if fallback is not None and _stays_in(fallback, span) and not any(rank(fallback)[:3]):
                points = fallback
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m unittest tests.test_figure_layout tests.test_overview_composition -v`
Expected: all pass.

- [ ] **Step 5: Saved-scene check, lint, commit**

Same commands as Task 1 Step 6. Commit message: `End an arrow on the group frame when its card's heading blocks every entry from above`.

### Task 3: Labels after arrows

**Files:**
- Modify: `papers/figures/render.py` (`_draw_edge` label block, lines 96-114, and the per-panel edge loop in `compose`, about line 329)
- Modify: `tests/test_figure_layout.py`
- Fixture: `tests/fixtures/overview/control-haiku-scene.json` (exists; haiku-5.5's AI Control scene of 2026-10-08 with twelve edges in the How panel)

**Interfaces:**
- Produces: every arrow label `<text>` carries `data-label="<from>:<to>"`.
- Changes: `_draw_edge` returns `(points, label)` where `label` is `None` or `(text, box, x, y, anchor)`; `compose` draws the labels after the panel's edge loop with `_draw_labels(labels, drawn, out, palette, measure)`.

- [ ] **Step 1: Write the failing test**

```python
def crosses(segment, rect):
    (x1, y1), (x2, y2) = segment
    x, y, w, h = rect
    if x1 == x2:
        return x < x1 < x + w and min(y1, y2) < y + h and max(y1, y2) > y
    return y < y1 < y + h and min(x1, x2) < x + w and max(x1, x2) > x


class ArrowLabelTests(unittest.TestCase):
    """haiku-5.5's AI Control scene: twelve edges in the How panel, six into one lane."""

    @classmethod
    def setUpClass(cls):
        cls.scene = load('control-haiku-scene.json')
        cls.svg = build(cls.scene)

    def test_no_label_sits_on_an_arrow(self):
        from papers.figures.layout import BODY, LINE
        from papers.figures.measure import Measurer
        paths = arrows(self.svg)
        labels = {f"{edge['from']}:{edge['to']}": edge['label'] for panel in self.scene['panels']
                  for edge in panel.get('edges', []) if edge.get('label')}
        with tempfile.TemporaryDirectory() as directory:
            measure = Measurer(directory)
            measure.prime(list(labels.values()), BODY)
            drawn = LABEL.findall(self.svg)
            self.assertTrue(drawn)
            for key, x, y in drawn:
                width = measure.width(labels[key], BODY)
                rect = (float(x) - width / 2 if '"middle"' in self.svg.split(f'data-label="{key}"')[1][:80]
                        else float(x), float(y) - LINE[BODY] + 4, width, LINE[BODY])
                for other, points in paths.items():
                    if other == key:
                        continue
                    for segment in zip(points, points[1:]):
                        self.assertFalse(crosses(segment, rect), f'{labels[key]!r} sits on the arrow {other}')
            measure.close()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/python -m unittest tests.test_figure_layout.ArrowLabelTests -v`
Expected: fails on `self.assertTrue(drawn)` because no label carries `data-label` yet. After Step 3's tag alone, it must fail on a crossing; if it passes with the tag alone, the fixture no longer shows the defect: then print each label's rect and the arrows and pick a label the arrows cross in the rendered PNG of the scene, and assert on that one.

- [ ] **Step 3: Defer the labels**

In `_draw_edge`, replace the label block so it computes the label's position and returns it instead of drawing it:

```python
    label = None
    if edge.get('label'):
        text = str(edge['label'])
        needed = measure.width(text, BODY) + 12
        longest = max(segments(points), key=lambda seg: abs(seg[1][0] - seg[0][0]) + abs(seg[1][1] - seg[0][1]))
        (ax, ay), (bx, by) = longest
        # A label needs room on its segment: above a long horizontal run, beside a tall vertical
        # one. A short arrow carries no label rather than a label on top of a card.
        label_w = needed - 12
        if ay == by and abs(bx - ax) >= needed:
            box = ((ax + bx) / 2 - label_w / 2, ay - 5 - LINE[BODY] + 4, label_w, LINE[BODY])
            if label_fits(box, obstacles + headings + [source, target], frames):
                label = (text, box, (ax + bx) / 2, ay - 5, 'middle')
        elif ax == bx and abs(by - ay) >= LINE[BODY] + 8:
            box = (ax + 6, (ay + by) / 2 + 5 - LINE[BODY] + 4, label_w, LINE[BODY])
            if label_fits(box, obstacles + headings + [source, target], frames):
                label = (text, box, ax + 6, (ay + by) / 2 + 5, None)
    return points, ((edge['from'], edge['to']), label)
```

Add after `_draw_edge`:

```python
def _draw_labels(labels, drawn, out, palette, measure):
    """Draw the panel's arrow labels, after every arrow is routed: a label an arrow crosses is dropped."""
    for key, label in labels:
        if label is None:
            continue
        text, box, x, y, anchor = label
        others = [piece for (other, points) in drawn if other != key for piece in segments(points)]
        if any(crosses(piece, box) for piece in others):
            continue
        tag = esc(key[0]) + ':' + esc(key[1])
        element = _text(x, y, text, anchor=anchor, fill=palette.muted, measure=measure)
        out.append(element.replace('<text ', f'<text data-label="{tag}" ', 1))
```

Import `crosses` from `papers.figures.route`. Check `_text`'s signature in `papers/figures/text.py` for how `anchor=None` is handled before you call it with `None`; if it needs omission, pass `anchor='middle'` only when set.

In `compose`, change the edge loop to:

```python
        drawn, detours, labels = [], [], []
        for edge in panel.get('edges', []):
            points, label = _draw_edge(edge, boxes, out, measure, palette, drawn, bounds)
            labels.append(label)
            extra = detour(points, boxes[edge['from']], boxes[edge['to']])
            if extra > 0:
                detours.append({'from': edge['from'], 'to': edge['to'], 'extra': round(extra)})
        _draw_labels(labels, drawn, out, palette, measure)
```

Search the repository for other callers of `_draw_edge` and update them: `grep -rn "_draw_edge" papers tests`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m unittest tests.test_figure_layout tests.test_overview_composition -v`
Expected: all pass. The haiku scene still draws at least one label, which `self.assertTrue(drawn)` checks. The AI Control story draws none: its four labels sit on 11-unit arrows, which carry no label by the existing rule.

- [ ] **Step 5: Saved-scene check, lint, commit**

Same commands as Task 1 Step 6. Commit message: `Draw arrow labels after routing, and drop a label that an arrow crosses`.

### Task 4: Nested surfaces

**Files:**
- Modify: `papers/figures/nodes.py` (`Group.draw`, lines 854-885; `Card.draw`, the `minor` branch about line 183)
- Modify: `tests/test_figure_layout.py`

**Interfaces:**
- Produces: the layout annotations `nesting` (int) and `surface` (`'page'` or `'sunk'`) on every child spec, set by `Group.draw` before it draws the child. `Card.draw` reads `surface`.

- [ ] **Step 1: Write the failing tests**

```python
class NestedSurfaceTests(unittest.TestCase):
    """Attention: stack, layer, sublayer, card. AI Control: chips inside a nested group."""

    @classmethod
    def setUpClass(cls):
        cls.luna = luna()
        cls.control = control()

    def test_the_outermost_headed_group_keeps_its_frame(self):
        _, attributes = box(self.luna, 'Encoder stack')
        self.assertIn(f'stroke="{LIGHT.hairline}"', attributes)

    def test_nested_groups_alternate_sunk_and_page_with_no_stroke(self):
        _, layer = box(self.luna, 'Encoder layer')
        _, sublayer = box(self.luna, 'Encoder self-attention sublayer')
        self.assertIn(f'fill="{LIGHT.sunk}"', layer)
        self.assertIn('stroke="none"', layer)
        self.assertNotIn('fill-opacity', layer)
        self.assertIn(f'fill="{LIGHT.page}"', sublayer)
        self.assertIn('stroke="none"', sublayer)

    def test_a_chip_takes_the_opposite_fill_of_its_surface(self):
        _, on_page = box(self.control, 'Upfront auditing')
        _, on_sunk = box(self.control, 'Realistic synthetic inputs')
        self.assertIn(f'fill="{LIGHT.sunk}"', on_page)
        self.assertIn(f'fill="{LIGHT.page}"', on_sunk)

    def test_a_nested_toned_group_keeps_its_tone(self):
        scene = {
            'title': 'Toned', 'subtitle': 'a toned group inside a group', 'footer': 'none', 'illustrative': True,
            'layout': 'stack', 'panels': [{
                'id': 'why', 'heading': 'Why: tone',
                'body': {'kind': 'group', 'heading': 'Outer', 'arrange': 'column', 'children': [
                    {'kind': 'group', 'heading': 'Inner', 'tone': 'green', 'arrange': 'column',
                     'children': [{'kind': 'card', 'label': 'Inside', 'minor': True}]}]}}]}
        svg = build(scene)
        _, inner = box(svg, 'Inner')
        _, chip = box(svg, 'Inside')
        fill, stroke, _ = LIGHT.tones['green']
        self.assertIn(f'fill="{fill}"', inner)
        self.assertIn(f'stroke="{stroke}"', inner)
        self.assertIn(f'fill="{LIGHT.sunk}"', chip)
```

`minor` is a field the schema accepts on a card. If `Figure.validate` rejects it, set it after validation instead: build the scene with `Figure().validate`, then set `minor` on the card dict, then call `compose` through `Figure.build` on the annotated scene. Prefer the direct route if it validates.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m unittest tests.test_figure_layout.NestedSurfaceTests -v`
Expected: the first test passes; the other three fail on the fill or stroke.

- [ ] **Step 3: Draw nested groups as surfaces and flip the chip fill**

In `Group.draw`, replace the frame drawing with:

```python
    def draw(self, out, boxes, measure, palette):
        x, y, w, h = self.x, self.y, self.w, self.h
        nesting = self.spec.get('nesting', 0)
        surface = self.spec.get('surface', 'page')
        if self.spec.get('heading') is not None:
            if self.spec.get('hook'):
                out.append(f'<g data-node="{esc(self.spec["hook"])}">')
            tone = self.spec.get('tone')
            if tone in ACCENT_TONES:
                fill, stroke, colour = palette.tones[tone]
                style = f'fill="{fill}" fill-opacity="0.35" stroke="{stroke}" stroke-width="1.2"'
            elif nesting == 0:
                fill, stroke, colour = palette.card, palette.hairline, palette.text
                style = f'fill="{fill}" fill-opacity="0.35" stroke="{stroke}" stroke-width="1.2"'
            else:
                # A nested frame is a surface, not a line: it alternates between the sunk and the
                # page colours, so three levels read as three steps and not three borders.
                surface = 'sunk' if surface == 'page' else 'page'
                colour = palette.text
                style = f'fill="{palette.sunk if surface == "sunk" else palette.page}" stroke="none"'
            out.append(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="10" {style}/>')
            nesting += 1
            ... the heading, detail, and heading box code stays as it is ...
        for child in self.children():
            child.spec['nesting'] = nesting
            child.spec['surface'] = surface
            child.draw(out, boxes, measure, palette)
```

In `Card.draw`, change the `minor` branch to:

```python
        if self.spec.get('minor'):
            # A chip is a fill with no line, so on a sunk surface it takes the page colour.
            fill = palette.page if self.spec.get('surface') == 'sunk' else palette.sunk
            stroke, colour = 'none', palette.muted
```

The dark pass composes on a deep copy with `DARK`, so both palettes get the rule for free.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m unittest tests.test_figure_layout tests.test_overview_composition tests.test_blog_workflow -v`
Expected: all pass. The Blog tests cover the `panel` frame, where a Blog figure's top group is also at nesting 0.

- [ ] **Step 5: Look at the result**

Render the two story scenes and look at the PNGs. `_run` deletes its directory, so build the PNGs with `Figure().build` on the story scenes after `_run` returned them, into `.scratch/`:

```python
import sys
sys.path.insert(0, '.'); sys.path.insert(0, 'tests')
from pathlib import Path
from papers.figures import Figure
from tests.test_overview_composition import _run
from tests.story_fixtures import control_story, load, luna_story
from tests.test_overview_workflow import _document
for name, answers, doc in (
        ('luna', [load('attention-selection.json'), load('attention-luna-digest.json'),
                  load('attention-luna-scene.json'), luna_story()], _document('')),
        ('control', [load('control-sonnet-selection.json'), load('control-sonnet-digest.json'),
                     load('control-sonnet-scene.json'), control_story()], load('control-sonnet-document.json'))):
    scene = _run(answers, doc)[2]
    print(name, Figure().build(scene, Path('.scratch'), name).assets['png'])
```

Open each PNG with the Read tool. Check: the Attention Model panel shows two arrows that run straight down into the sublayers, the stack frame has a border, the layer is grey with no border, the sublayer is white with no border, and the chips in the AI Control Result panel are visible on both surfaces. If a chip or a frame is not visible, fix the rule before you commit.

- [ ] **Step 6: Saved-scene check, lint, commit**

Same commands as Task 1 Step 6. Commit message: `Draw a nested headed group as an alternating surface with no stroke, and flip chips on a sunk surface`.

### Task 5: Vocabulary

**Files:**
- Modify: `CONTEXT.md` (the "Scene layout" and "Chip" entries)

- [ ] **Step 1: Update the entries**

In the "Scene layout" entry, replace "and arrows routed around every other card" with "and arrows routed around every other card: an arrow between two stacked cards enters the lower card from above across their shared span, or ends on the frame of the group that holds it when the group heading spans the whole card; a label is dropped when an arrow crosses it". Add one sentence at the end: "A headed group inside a headed group draws as a surface with no border, sunk and page by turns."

In the "Chip" entry, change "drawn as its label only on a sunk fill" to "drawn as its label only on a sunk fill, or on the page fill when it sits on a sunk surface".

- [ ] **Step 2: Commit**

```sh
git add CONTEXT.md
git commit -m "Describe stacked arrow entry, the frame fallback, and nested surfaces in the vocabulary"
```

## Done when

- `.venv/bin/python -m unittest tests.test_figure_layout tests.test_overview_composition tests.test_blog_workflow` passes.
- `diff .scratch/relayout-before.txt .scratch/relayout-after.txt` shows no new `ERROR`, issue, or warning.
- `uvx ruff check papers tests` is clean.
- The two PNGs from Task 4 Step 5 show what that step describes.
- Five commits on `figure-arrows`, none touching `tests/`.

Leave the branch unmerged. The reviewer merges with `git merge --no-ff figure-arrows` after review.
