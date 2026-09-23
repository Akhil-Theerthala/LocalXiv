# Figure library node classes implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `kind` if/elif chains in `papers/figures/layout.py`, `papers/figures/render.py`, and `papers/figures/schema.py` with one class per Scene node kind, so a node kind is defined in one place, and the SVG output stays byte-identical.

**Architecture:** `papers/figures/nodes.py` holds a `Node` base class and nine subclasses, one per kind in `schema.KINDS`. A node object is a view over its Scene dict. It reads its fields from the dict and writes its measurements (`w`, `h`, `x`, `y`, wrapped lines) into the same dict, so `compose` still annotates the Scene in place and every test that reads `scene['panels'][0]['body']['w']` keeps passing. `Node.of(spec)` returns the subclass registered for `spec['kind']`. Migration goes one kind at a time. While a kind is migrating, the old chains delegate to its class for that kind, and `tests/baseline_scenes.py --compare` proves after each task that every known Scene renders to the same bytes. The last task deletes the chains.

**Tech Stack:** Python 3 standard library and `unittest`.

**Spec:** [Overview scene layout design](../specs/2026-09-18-overview-scene-layout-design.md), Data and Layout sections. The behaviour is fixed by that design and by the current code; this plan changes structure only.

## Global constraints

- Byte-identical output. After every task, `python3 tests/baseline_scenes.py --compare` prints `same` for every Scene. A `DIFFERS` line fails the task.
- No behaviour change. No new node kind, no new field, no new layout rule. Bug fixes belong in the layout defects plan, which lands before this one.
- The Scene JSON stays the input and the annotated dict stays the state. Classes hold behaviour, not state, so a node object may be rebuilt at any time with `Node.of(spec)`.
- Tests go under `tests/` and run with `python3 -m unittest tests.<module> -v`.
- Commit messages carry no `Co-Authored-By` trailer. Work on a branch named `figure-library-node-classes` and merge with `git merge --no-ff`.
- Run this plan after [the layout defects plan](2026-09-24-figure-library-layout-defects.md) and [the inline figure plan](2026-09-24-inline-overview-figure.md), so `place` takes `measure`, `refit` exists, and the `data-node` hooks are already in `_draw`. Those hooks move into `Card.draw` and `Group.draw` here.

## Where classes pay and where they do not

Classes pay where the code branches on `kind`: `prime`, `size`, `refit`, `_draw`, `schema.text`, `schema._scene_node`, `NODE_FIELDS`, and `NODE_DOCS`. Today a change to one kind touches six places in three files; the layout defects plan had to apply `step_text` in three of them. After this plan, `Steps` is one class.

Classes do not pay for `route.py`, which is geometry with no variants, for `Palette` and `Canvas`, which are already dataclasses, or for `Measurer` and `FixedMeasurer`, which are already a two-class hierarchy. Leave them.

## The move rules

Every per-kind task applies the same mechanical transformation to the branch it moves. The plan states the rules once here.

1. Copy the `kind` branch from `size` into `size(self, avail, measure)`, from `prime`'s `walk` into `prime_texts(self)`, from `refit` into `refit(self, measure)`, from `_draw` into `draw(self, out, boxes, measure, palette)`, and from `schema.text` into `texts(self)`.
2. Replace `node[...]` with `self.spec[...]` and `node.get(...)` with `self.spec.get(...)`.
3. Replace `node['w']`, `node['h']`, `node['x']`, and `node['y']` with `self.w`, `self.h`, `self.x`, and `self.y`. They are properties that read and write the dict.
4. `prime_texts` returns `(bold, plain)` lists instead of extending outer lists.
5. `texts` returns the list of strings instead of extending `strings`.
6. In `draw`, `x, y, w, h = self.x, self.y, self.w, self.h` replaces the unpacking at the top of `_draw`, and the leaf obstacle registration stays in the base class.
7. Do not rename a local variable, reorder an `out.append`, or change a format string. The baseline compare catches any slip.

## File structure

- Create `papers/figures/nodes.py`: `Node`, `REGISTRY`, and the nine subclasses.
- Modify `papers/figures/layout.py`: delegation to the registry during migration; `prime`, `size`, `refit`, `reflow_narrow`, `justify`, and `place` become thin or move into `Group`.
- Modify `papers/figures/render.py`: `_draw` delegates and then disappears; `compose` builds a `Node` for each panel body.
- Modify `papers/figures/schema.py`: node validation, `NODE_FIELDS`, and `NODE_DOCS` derive from the classes.
- Create `tests/test_nodes.py`: the registry and the view contract.
- Modify `docs/cleanup.md`: the deletions this plan makes, with their checks.

---

### Task 0: Write the baseline

- [ ] **Step 1: Branch and record every Scene's SVG**

```bash
git checkout -b figure-library-node-classes
python3 tests/baseline_scenes.py
```

Expected: one `wrote` line per fixture Scene and per Scene in the local library. The files land in `.scratch/figure-baseline/`, which git ignores. Every later task compares against these files.

---

### Task 1: `Node`, the registry, and `Card`

**Files:**
- Create: `papers/figures/nodes.py`
- Modify: `papers/figures/layout.py` (`prime`, `size`, `refit`), `papers/figures/render.py` (`_draw`), `papers/figures/schema.py` (`text`)
- Create: `tests/test_nodes.py`

**Interfaces:**
- Produces: `nodes.Node` with `spec`, properties `x`, `y`, `w`, `h`, methods `children()`, `prime_texts()`, `size(avail, measure)`, `refit(measure)`, `draw(out, boxes, measure, palette)`, `texts()`, and class attributes `kind`, `fields`, `summary`, `field_docs`, `stretches`. `nodes.REGISTRY: dict[str, type[Node]]`. `Node.of(spec) -> Node`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_nodes.py`:

```python
"""Node classes are views over Scene dicts: behaviour on the class, state in the dict."""
import unittest

from papers.figures.layout import BODY, CARD_PAD_X, CARD_PAD_Y, LINE
from papers.figures.measure import FixedMeasurer
from papers.figures.nodes import REGISTRY, Node


class NodeViewTests(unittest.TestCase):
    def test_of_returns_the_registered_class_for_the_kind(self):
        spec = {'kind': 'card', 'label': 'Query Q'}
        self.assertIs(type(Node.of(spec)), REGISTRY['card'])
        self.assertIs(Node.of(spec).spec, spec)

    def test_geometry_lives_in_the_dict(self):
        spec = {'kind': 'card', 'label': 'Query Q'}
        node = Node.of(spec)
        node.w = 120
        node.x = 10
        self.assertEqual(spec['w'], 120)
        self.assertEqual(spec['x'], 10)
        self.assertEqual(Node.of(spec).w, 120)

    def test_a_card_sizes_to_its_label(self):
        measure = FixedMeasurer()
        spec = {'kind': 'card', 'label': 'Query Q', 'detail': 'd = 512'}
        node = Node.of(spec)
        node.size(400, measure)
        self.assertEqual(spec['w'], measure.width('Query Q', BODY, 700) + 2 * CARD_PAD_X)
        self.assertEqual(spec['h'], 2 * LINE[BODY] + 2 * CARD_PAD_Y)
        self.assertEqual(node.texts(), ['Query Q', 'd = 512'])

    def test_an_unknown_kind_is_a_key_error(self):
        with self.assertRaises(KeyError):
            Node.of({'kind': 'sparkline'})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m unittest tests.test_nodes -v`
Expected: `ModuleNotFoundError: No module named 'papers.figures.nodes'`.

- [ ] **Step 3: Move the SVG text helpers out of the renderer**

`nodes.py` needs `_text` and `esc`, and `render.py` will import `nodes.py` in step 5. Break the cycle first. Create `papers/figures/text.py`:

```python
"""SVG text helpers shared by the renderer and the node classes."""
import html

from papers.figures.layout import BODY


def esc(value):
    return html.escape(str(value), quote=True)


def _text(x, y, text, *, size=BODY, weight=None, fill=None, anchor=None):
    attributes = f'x="{x:g}" y="{y:g}" font-size="{size}"'
    if weight:
        attributes += f' font-weight="{weight}"'
    if fill:
        attributes += f' fill="{fill}"'
    if anchor:
        attributes += f' text-anchor="{anchor}"'
    return f'<text {attributes}>{esc(text)}</text>'
```

Delete the two definitions from `papers/figures/render.py` and add `from papers.figures.text import _text, esc` there. Run `python3 tests/baseline_scenes.py --compare`; every Scene prints `same`.

- [ ] **Step 4: Write `Node` and `Card`**

Create `papers/figures/nodes.py`:

```python
"""One class per Scene node kind: its fields, its card entry, its sizing, and its drawing.

A node object is a view over its Scene dict. Fields come from the dict, and measurements go back
into it, so ``compose`` still annotates the Scene in place and a node can be rebuilt from its
dict at any time with ``Node.of``.
"""
from papers.figures.layout import BODY, CARD_MAX_DETAIL, CARD_PAD_X, CARD_PAD_Y, LINE
from papers.figures.palette import ACCENT_TONES
from papers.figures.text import _text, esc

REGISTRY = {}


def _slot(name):
    return property(lambda self: self.spec[name], lambda self, value: self.spec.__setitem__(name, value))


class Node:
    kind = ''
    fields = frozenset()
    summary = ''
    field_docs = ()
    # Whether a column stretches this node to its siblings' width.
    stretches = False

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.kind:
            REGISTRY[cls.kind] = cls

    def __init__(self, spec):
        self.spec = spec

    @classmethod
    def of(cls, spec):
        return REGISTRY[spec['kind']](spec)

    x, y, w, h = _slot('x'), _slot('y'), _slot('w'), _slot('h')

    def children(self):
        return []

    def prime_texts(self):
        """The (bold, plain) strings to measure before layout."""
        return [], []

    def size(self, avail, measure):
        raise NotImplementedError

    def refit(self, measure):
        """Wrap again at the current width after a stretch. Leaves that never wrap do nothing."""

    def draw(self, out, boxes, measure, palette):
        raise NotImplementedError

    def texts(self):
        """Every string a reader can see on this node, for coverage and density checks."""
        return []


class Card(Node):
    kind = 'card'
    fields = frozenset({'kind', 'id', 'label', 'detail', 'tone', 'dashed', 'plain'})
    summary = 'one labelled box'
    field_docs = (('id', 'needed when an edge joins it', True), ('label', '≤{label}', False),
                  ('detail', '≤{detail} muted second line', True), ('tone', '{tone}', True),
                  ('dashed', 'true for a discarded or optional state', True),
                  ('plain', 'true for a non-bold label', True))
    stretches = True

    def prime_texts(self):
        return [str(self.spec['label'])], str(self.spec.get('detail', '')).split()

    def size(self, avail, measure):
        weight = None if self.spec.get('plain') else 700
        label_w = measure.width(str(self.spec['label']), BODY, weight)
        detail_w = measure.width(str(self.spec['detail']), BODY) if self.spec.get('detail') else 0.0
        width = min(max(label_w, min(detail_w, CARD_MAX_DETAIL)) + 2 * CARD_PAD_X, avail)
        words = str(self.spec['label']).split() + str(self.spec.get('detail', '')).split()
        measure.prime(words, BODY, 700)
        longest = max((measure.width(word, BODY, 700) for word in words), default=0.0)
        self.w = max(width, longest + 2 * CARD_PAD_X)
        self.refit(measure)

    def refit(self, measure):
        weight = None if self.spec.get('plain') else 700
        self.spec['label_lines'] = measure.wrap(self.spec['label'], self.w - 2 * CARD_PAD_X, BODY, weight)
        self.spec['detail_lines'] = (measure.wrap(self.spec['detail'], self.w - 2 * CARD_PAD_X)
                                     if self.spec.get('detail') else [])
        self.h = (len(self.spec['label_lines']) + len(self.spec['detail_lines'])) * LINE[BODY] + 2 * CARD_PAD_Y

    def draw(self, out, boxes, measure, palette):
        x, y, w, h = self.x, self.y, self.w, self.h
        hook = self.spec.get('id') or 'n' + str(len(boxes))
        self.spec['hook'] = hook
        out.append(f'<g data-node="{esc(hook)}">')
        tone = self.spec.get('tone') or 'plain'
        fill, stroke, colour = palette.tones[tone]
        dash = ' stroke-dasharray="5 3"' if self.spec.get('dashed') else ''
        stroke_width = 1.5 if tone in ACCENT_TONES else 1
        out.append(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="7" fill="{fill}" '
                   f'stroke="{stroke}" stroke-width="{stroke_width}"{dash}/>')
        # Wrap at the final width: a stretched card has more room than it was sized for.
        self.spec['label_lines'] = measure.wrap(self.spec['label'], w - 2 * CARD_PAD_X, BODY, None if self.spec.get('plain') else 700)
        if self.spec.get('detail'):
            self.spec['detail_lines'] = measure.wrap(self.spec['detail'], w - 2 * CARD_PAD_X)
        for index, line in enumerate(self.spec['label_lines']):
            out.append(_text(x + CARD_PAD_X, y + CARD_PAD_Y + 13 + index * LINE[BODY], line,
                             weight=None if self.spec.get('plain') else 700,
                             fill=colour if tone in ACCENT_TONES else palette.text))
        offset = len(self.spec['label_lines'])
        for index, line in enumerate(self.spec['detail_lines']):
            out.append(_text(x + CARD_PAD_X, y + CARD_PAD_Y + 13 + (offset + index) * LINE[BODY], line, fill=palette.muted))
        boxes[self.spec.get('id') or '#' + str(len(boxes))] = (x, y, w, h)
        out.append('</g>')

    def texts(self):
        return [self.spec['label'], self.spec.get('detail', '')]
```

Compare `Card.size`, `Card.refit`, and `Card.draw` line by line with the `card` branches of `size`, `refit`, and `_draw` on the branch. The `size` branch computes the lines inline; here `refit` computes them, which is the same arithmetic. If the branch on your checkout differs from the code above, the branch is right; copy it.

- [ ] **Step 5: Delegate the `card` kind to the class**

In `papers/figures/layout.py`, at the top of `size`:

```python
    from papers.figures.nodes import REGISTRY, Node
    if node['kind'] in REGISTRY:
        return Node.of(node).size(avail, measure)
```

The import is inside the function only during migration. Task 11 lifts it to module level once `layout.py` no longer defines `size`.

At the top of `refit`:

```python
    from papers.figures.nodes import REGISTRY, Node
    if node['kind'] in REGISTRY:
        return Node.of(node).refit(measure)
```

In `prime`, at the top of `walk`:

```python
        from papers.figures.nodes import REGISTRY, Node
        kind = node.get('kind')
        if kind in REGISTRY:
            view = Node.of(node)
            more_bold, more_plain = view.prime_texts()
            bold.extend(more_bold)
            plain.extend(more_plain)
            for child in view.children():
                walk(child.spec)
            return
```

In `papers/figures/render.py`, at the top of `_draw`:

```python
    from papers.figures.nodes import REGISTRY, Node
    if node['kind'] in REGISTRY:
        return Node.of(node).draw(out, boxes, measure, palette)
```

Move the leaf obstacle line (`if kind not in ('group', 'card', 'sequence'): boxes['#' + ...] = ...`) into `Node.draw` callers later; for now the `card` kind never hit it, so nothing changes.

In `papers/figures/schema.py`, in `text`, at the top of the `for node in _walk(panel['body'])` loop body:

```python
            if node['kind'] in REGISTRY:
                strings += Node.of(node).texts()
                continue
```

with `from papers.figures.nodes import REGISTRY, Node` inside the function during migration.

- [ ] **Step 6: Run the tests and the baseline compare**

```bash
python3 -m unittest tests.test_nodes tests.test_scene_layout tests.test_layout_defects tests.test_figure_hooks tests.test_scene_schema -v
python3 tests/baseline_scenes.py --compare
```

Expected: all tests pass and every Scene prints `same`.

- [ ] **Step 7: Commit**

```bash
git add papers/figures/nodes.py papers/figures/text.py papers/figures/layout.py papers/figures/render.py papers/figures/schema.py tests/test_nodes.py
git commit -m "Add Node classes and move the card kind"
```

---

### Task 2: `Note`

**Files:**
- Modify: `papers/figures/nodes.py`
- Test: `tests/test_nodes.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_nodes.py`:

```python
class LeafKindTests(unittest.TestCase):
    @unittest.expectedFailure
    def test_every_kind_in_the_schema_has_a_class(self):
        from papers.figures.schema import KINDS
        self.assertEqual(sorted(REGISTRY), sorted(KINDS))
```

This test is the migration's progress bar. It is marked as an expected failure so `unittest discover` stays green on every intermediate commit; Task 9 removes the decorator when `Group` registers the last kind.

Add:

```python
    def test_a_note_wraps_and_sizes(self):
        measure = FixedMeasurer()
        spec = {'kind': 'note', 'lines': ['Weights sum to 1', 'The output stays inside the value vectors']}
        node = Node.of(spec)
        node.size(200, measure)
        self.assertEqual(spec['w'], 200)
        self.assertGreater(len(spec['wrapped']), 2)
        self.assertEqual(spec['h'], len(spec['wrapped']) * LINE[BODY] + 2 * CARD_PAD_Y + 4)
        self.assertEqual(node.texts(), spec['lines'])
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m unittest tests.test_nodes.LeafKindTests.test_a_note_wraps_and_sizes -v`
Expected: `KeyError: 'note'`.

- [ ] **Step 3: Write `Note` by the move rules**

Add to `papers/figures/nodes.py`:

```python
class Note(Node):
    kind = 'note'
    fields = frozenset({'kind', 'lines'})
    summary = 'a small text block; the first line is bold'
    field_docs = (('lines', '[1-4 strings ≤{note_line}]', False),)
    stretches = True
```

Then move the `note` branches of `prime` (`prime_texts`), `size`, `refit`, `_draw` (`draw`), and `schema.text` (`texts`) into it by the move rules. In `draw`, the obstacle line from the top of `_draw` applies to a note, so `draw` begins:

```python
    def draw(self, out, boxes, measure, palette):
        x, y, w, h = self.x, self.y, self.w, self.h
        boxes['#' + str(len(boxes))] = (x, y, w, h)
```

followed by the moved branch.

- [ ] **Step 4: Run the tests and the baseline compare**

```bash
python3 -m unittest tests.test_nodes.NodeViewTests tests.test_nodes.LeafKindTests.test_a_note_wraps_and_sizes tests.test_scene_layout tests.test_layout_defects -v
python3 tests/baseline_scenes.py --compare
```

Expected: pass and `same` everywhere.

- [ ] **Step 5: Commit**

```bash
git add papers/figures/nodes.py tests/test_nodes.py
git commit -m "Move the note kind into its class"
```

---

### Task 3: `Steps`

Same shape as Task 2. Class header:

```python
class Steps(Node):
    kind = 'steps'
    fields = frozenset({'kind', 'lines'})
    summary = 'a calculation the renderer numbers 1., 2., …; write the lines without numbers; the last line is the result'
    field_docs = (('lines', '[1-6 strings ≤{step}]', False),)
    stretches = True
```

`step_text` stays in `layout.py` and is imported. `refit` is inherited and does nothing, because step lines never wrap. Test to add:

```python
    def test_steps_strip_the_model_number_when_sizing(self):
        measure = FixedMeasurer()
        spec = {'kind': 'steps', 'lines': ['1. scores = Q K^T', '2. softmax']}
        node = Node.of(spec)
        node.size(600, measure)
        self.assertEqual(spec['w'], measure.width('scores = Q K^T', BODY) + 40)
        self.assertEqual(node.texts(), spec['lines'])
```

Run the same commands as Task 2 step 4, then commit with `Move the steps kind into its class`.

---

### Task 4: `Sequence`

Class header:

```python
class Sequence(Node):
    kind = 'sequence'
    fields = frozenset({'kind', 'items'})
    summary = 'tokens, values, or steps in a row, each with an optional caption under it'
    field_docs = (('items', '[2-8 of {{"id"?, "text" ≤{item}, "sub"? ≤{sub}, "tone"?, "hot"? true}}]', False),)
```

The `_draw` branch for a sequence reassigns `y` inside its loop and restores it with `y = node['y']` at the end. Keep both lines as they are; only the spelling of the lookups changes. A sequence registers each item as a box, so it does not take the leaf obstacle line. Test to add:

```python
    def test_a_sequence_wraps_its_items_into_rows(self):
        measure = FixedMeasurer()
        spec = {'kind': 'sequence', 'items': [{'text': 'x_1', 'sub': '"The"'}, {'text': 'x_2', 'sub': '"Law"'},
                                              {'text': 'x_3', 'sub': '"will"'}]}
        node = Node.of(spec)
        cell = max(measure.width('x_1', BODY, 700) + 16, measure.width('"will"', BODY) + 8)
        node.size(cell * 2 + 6, measure)
        self.assertEqual(spec['per_row'], 2)
        self.assertEqual(node.texts(), ['x_1', 'x_2', 'x_3', '"The"', '"Law"', '"will"'])
```

Commit with `Move the sequence kind into its class`.

---

### Task 5: `Grid`

Class header:

```python
class Grid(Node):
    kind = 'grid'
    fields = frozenset({'kind', 'rows', 'col_labels', 'row_labels', 'caption'})
    summary = 'a small matrix, at most 6×6; a cell is a number, a string ≤{cell}, "*value" to highlight it, or null when masked'
    field_docs = (('rows', '[[cell]]', False), ('col_labels', '[≤{grid_label} each]', True),
                  ('row_labels', '[≤{grid_label} each]', True), ('caption', '≤{caption}', True))
```

`draw` takes the leaf obstacle line. Test to add:

```python
    def test_a_grid_sizes_its_cells_to_the_widest_text(self):
        measure = FixedMeasurer()
        spec = {'kind': 'grid', 'rows': [['*1.0', None], ['0.4', '*0.6']], 'col_labels': ['y1', 'y2']}
        node = Node.of(spec)
        node.size(600, measure)
        self.assertEqual(spec['cell'], max(34, measure.width('1.0', BODY, 700) + 12))
        self.assertEqual(spec['w'], 2 * spec['cell'])
        self.assertEqual(node.texts(), ['1.0', '0.4', '0.6', 'y1', 'y2', ''])
```

Commit with `Move the grid kind into its class`.

---

### Task 6: `Bars`

Class header:

```python
class Bars(Node):
    kind = 'bars'
    fields = frozenset({'kind', 'items', 'caption'})
    summary = 'a comparison of values'
    field_docs = (('items', '[2-8 of ["label" ≤{bar_label}, number]]', False), ('caption', '≤{caption}', True))
```

`draw` takes the leaf obstacle line. Test to add:

```python
    def test_bars_keep_room_for_labels_and_values(self):
        measure = FixedMeasurer()
        spec = {'kind': 'bars', 'items': [['ConvS2S', 25.2], ['Transformer (big)', 28.4]]}
        node = Node.of(spec)
        node.size(600, measure)
        self.assertEqual(spec['label_w'], measure.width('Transformer (big)', BODY))
        self.assertEqual(spec['h'], 2 * 22)
        self.assertEqual(node.texts(), ['ConvS2S', 'Transformer (big)', ''])
```

Commit with `Move the bars kind into its class`.

---

### Task 7: `Divider`

Class header:

```python
class Divider(Node):
    kind = 'divider'
    fields = frozenset({'kind', 'label'})
    summary = 'a dashed line, for a threshold or a boundary'
    field_docs = (('label', '≤{divider}', True),)
    stretches = True
```

`draw` takes the leaf obstacle line. Test to add:

```python
    def test_a_divider_takes_the_available_width(self):
        spec = {'kind': 'divider', 'label': 'Threshold cutoff α = 0.10'}
        node = Node.of(spec)
        node.size(420, FixedMeasurer())
        self.assertEqual((spec['w'], spec['h']), (420, LINE[BODY]))
        self.assertEqual(node.texts(), ['Threshold cutoff α = 0.10'])
```

Commit with `Move the divider kind into its class`.

---

### Task 8: `Chart`

Class header:

```python
class Chart(Node):
    kind = 'chart'
    fields = frozenset({'kind', 'series', 'x_label', 'y_label', 'caption', 'marks'})
    summary = 'a line or scatter plot of 1 to 4 series; the application draws axes and ticks'
    field_docs = (('series', '[1-4 of {{"label" ≤{series_label}, "points": [2-12 of [x, y]]}}]', False),
                  ('x_label', '≤{axis_label}', True), ('y_label', '≤{axis_label}', True),
                  ('caption', '≤{caption}', True), ('marks', '"line" | "dots"', True))
```

`chart_ticks` stays a module function in `layout.py`; import it. `draw` takes the leaf obstacle line. Test to add:

```python
    def test_a_chart_reports_its_lead_and_height(self):
        from papers.figures.layout import CHART_HEIGHT, chart_ticks
        measure = FixedMeasurer()
        spec = {'kind': 'chart', 'series': [{'label': 'loss', 'points': [[0, 1.0], [1, 0.5], [2, 0.25]]}], 'caption': 'per epoch'}
        node = Node.of(spec)
        node.size(600, measure)
        self.assertEqual(spec['lead'], max(measure.width(label, BODY) for label in chart_ticks(spec)[0]) + 10)
        self.assertEqual(spec['h'], CHART_HEIGHT + LINE[BODY] * 2 + 8)
        self.assertEqual(node.texts(), ['loss', '', '', 'per epoch'])
```

Run `python3 -m unittest tests.test_chart_node -v` as well; it covers the chart's existing behaviour. Commit with `Move the chart kind into its class`.

---

### Task 9: `Group`, with `reflow_narrow`, `justify`, and `place`

**Files:**
- Modify: `papers/figures/nodes.py`, `papers/figures/layout.py`, `papers/figures/render.py`
- Test: `tests/test_nodes.py`

**Interfaces:**
- Produces: `Group(Node)` with `children() -> list[Node]`, `size`, `draw`, `texts`, `prime_texts`, and the group-only methods `reflow_narrow(inner, measure)`, `justify(inner, measure, canvas)`, and `grow(width, canvas)` (the old `_grow_group`). `Node.place(x, y, canvas, measure, stretch=None)` on the base class does the stretch and `refit`; `Group.place` places children and recomputes `h`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_nodes.py`:

```python
class GroupTests(unittest.TestCase):
    def test_children_are_node_views_over_the_child_dicts(self):
        spec = {'kind': 'group', 'arrange': 'row', 'children': [{'kind': 'card', 'label': 'A'}, {'kind': 'note', 'lines': ['B']}]}
        children = Node.of(spec).children()
        self.assertEqual([type(child).kind for child in children], ['card', 'note'])
        self.assertIs(children[0].spec, spec['children'][0])

    def test_place_stretches_a_column_child_and_refits_it(self):
        from papers.figures.layout import Canvas
        measure = FixedMeasurer()
        spec = {'kind': 'group', 'arrange': 'column', 'children': [
            {'kind': 'card', 'id': 'wide', 'label': 'A card with a long label that wraps', 'detail': 'and a detail line that also wraps at the shared width'},
            {'kind': 'card', 'id': 'short', 'label': 'B'}]}
        node = Node.of(spec)
        node.size(400, measure)
        node.place(0, 0, Canvas(1000), measure)
        short = spec['children'][1]
        self.assertEqual(short['w'], spec['children'][0]['w'])
        self.assertEqual(short['h'], len(short['label_lines']) * LINE[BODY] + 2 * CARD_PAD_Y)
        self.assertEqual(spec['h'], spec['children'][0]['h'] + spec['gap'] + short['h'])
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m unittest tests.test_nodes.GroupTests -v`
Expected: `KeyError: 'group'`.

- [ ] **Step 3: Write `Group` and `Node.place`**

Add to `Node` in `papers/figures/nodes.py`:

```python
    def place(self, x, y, canvas, measure, stretch=None):
        """Set the absolute position; a stretchable leaf grows to the column width and re-wraps."""
        self.x, self.y = x, y
        if stretch is not None and self.stretches:
            wanted = max(self.w, min(stretch, canvas.stretch_max))
            if wanted != self.w:
                self.w = wanted
                self.refit(measure)
```

Add the class:

```python
class Group(Node):
    kind = 'group'
    fields = frozenset({'kind', 'heading', 'repeat', 'arrange', 'tone', 'children'})
    summary = 'a container; with a heading it draws a frame, for a component that holds its parts'
    field_docs = (('heading', '≤{group_heading}', True), ('repeat', '≤{repeat} such as "(N = 6)"', True),
                  ('arrange', '"row" | "column"', False), ('tone', '{tone}', True), ('children', '[1-8 nodes]', False))
    stretches = True

    def children(self):
        return [Node.of(child) for child in self.spec['children']]

    @property
    def pad(self):
        return GAP if self.spec.get('heading') is not None else 0

    @property
    def head(self):
        return LINE[BODY] + 4 if self.spec.get('heading') is not None else 0
```

Then move, by the move rules:

- the `group` branch of `prime`'s `walk` into `prime_texts` (the heading only; `prime` itself recurses through `children()`),
- the `group` branch of `size` into `size`, calling `child.size(...)` on each `Node` in `self.children()`,
- `reflow_narrow` into `reflow_narrow(self, inner, measure)`, where the recursion calls `child.reflow_narrow(...)` on children that are `Group` with `arrange == 'column'`,
- `justify` into `justify(self, inner, measure, canvas)` and `_grow_group` into `grow(self, width, canvas)`, with `_stretch_limit` staying a module function in `layout.py` that takes a `Node`,
- the group part of `place` into `Group.place`, which calls `super().place(...)` first and then places children and recomputes `h`,
- the `group` branch of `_draw` into `draw`, including the `data-node` wrapper and the heading obstacle, and then `child.draw(...)` for each child,
- the `group` branch of `schema.text` into `texts` (heading and repeat only; `schema.text` still walks the tree).

In `papers/figures/render.py`, `compose` now does:

```python
        body = Node.of(panel['body'])
        ...
        for panel in panels:
            Node.of(panel['body']).size(panel_w - 2 * PANEL_PAD, measure)
        ...
        body.reflow_narrow(inner, measure)
        body.justify(inner, measure, canvas)
        ...
        body.place(x + PANEL_PAD, body_y, canvas, measure)
        ...
        body.draw(out, boxes, measure, palette)
```

with `body['h']` and `body['w']` read as `body.h` and `body.w`. `reflow_narrow` and `justify` on a non-group body must do nothing; add both as no-op methods on `Node`.

- [ ] **Step 4: Run every figure test and the baseline compare**

```bash
python3 -m unittest tests.test_nodes tests.test_scene_layout tests.test_layout_defects tests.test_figure_hooks tests.test_layout_canvas tests.test_scene_schema tests.test_chart_node -v
python3 tests/baseline_scenes.py --compare
```

Expected: everything passes and every Scene prints `same`. Remove the `@unittest.expectedFailure` decorator from `test_every_kind_in_the_schema_has_a_class` in `tests/test_nodes.py` first; it now passes.

- [ ] **Step 5: Commit**

```bash
git add papers/figures/nodes.py papers/figures/layout.py papers/figures/render.py tests/test_nodes.py
git commit -m "Move the group kind and its layout passes into its class"
```

---

### Task 10: The schema derives fields, docs, and validation from the classes

**Files:**
- Modify: `papers/figures/schema.py` (`NODE_FIELDS`, `NODE_DOCS`, `_scene_node`), `papers/figures/nodes.py` (`validate` on each class)
- Test: `tests/test_scene_card.py`, `tests/test_scene_schema.py`

**Interfaces:**
- Produces: `Node.validate(path, errors, ids, count, recurse)` on every class, holding that kind's rules from `_scene_node`. `recurse(child, path, depth, ids, count, errors)` is `_scene_node`, passed in so `Group.validate` can descend without importing the schema module. `schema.NODE_FIELDS = {cls.kind: cls.fields for cls in REGISTRY.values()}` and `schema.NODE_DOCS` built from `summary` and `field_docs`.

- [ ] **Step 1: Confirm the existing tests are the safety net**

Run: `python3 -m unittest tests.test_scene_card tests.test_scene_schema -v`
Expected: pass. `test_docs_cover_every_node_field` and `test_card_names_every_kind_and_limit` are the tests that must keep passing after the move. Save the current card text for a byte comparison:

```bash
python3 -c "from papers.figures.schema import card; open('.scratch/card-before.txt','w').write(card())"
```

- [ ] **Step 2: Move each kind's validation rules**

Add to `Node`:

```python
    def validate(self, path, depth, errors, ids, count, recurse):
        """This kind's own rules. The common rules (kind, unsupported fields, tone, counts) stay in the schema."""
```

For each class, move the matching `elif kind == ...` block from `_scene_node` into `validate`, replacing `node` with `self.spec`. `recurse` has the signature `recurse(child, path, depth, ids, count, errors)`; only `Group.validate` calls it, once per child with `depth + 1`. The helpers `_text`, `_scene_id`, `_scene_lines`, `_panel_error`, `LIMITS`, `MAX_DEPTH`, and `TONES` are imported from `schema.py` inside `nodes.py`. If that makes an import cycle at module load, move those helpers and constants into `papers/figures/limits.py` and import them from both modules.

In `_scene_node`, after the common rules, replace the kind branches with:

```python
    Node.of(node).validate(path, depth, errors, ids, count, _scene_node)
```

Replace the `NODE_FIELDS` and `NODE_DOCS` literals with:

```python
NODE_FIELDS = {cls.kind: cls.fields for cls in REGISTRY.values()}
NODE_DOCS = {cls.kind: {'summary': cls.summary,
                        'fields': [_field(name, doc.replace('{tone}', _TONE), optional) for name, doc, optional in cls.field_docs]}
             for cls in REGISTRY.values()}
```

Keep the kind order of `KINDS` when the card is rendered, so the card text does not change: iterate `KINDS`, not `REGISTRY`, wherever the order reaches the model.

- [ ] **Step 3: Compare the card and run the tests**

```bash
python3 -c "from papers.figures.schema import card; open('.scratch/card-after.txt','w').write(card())"
diff .scratch/card-before.txt .scratch/card-after.txt && echo same card
python3 -m unittest tests.test_scene_card tests.test_scene_schema tests.test_nodes -v
```

Expected: `same card` and all tests pass. A diff means a `field_docs` entry differs from its old `NODE_DOCS` line; fix the class.

- [ ] **Step 4: Commit**

```bash
git add papers/figures/schema.py papers/figures/nodes.py
git commit -m "Derive node fields, docs, and validation from the node classes"
```

---

### Task 11: Delete the chains and record the cleanup

**Files:**
- Modify: `papers/figures/layout.py`, `papers/figures/render.py`, `papers/figures/schema.py`
- Modify: `docs/cleanup.md`
- Modify: `docs/superpowers/specs/2026-09-18-overview-scene-layout-design.md`

- [ ] **Step 1: Write the cleanup section first**

Append to `docs/cleanup.md`:

```markdown
## Node classes (planned 2026-09-24)

Status: planned. Runs with the [Figure library node classes plan](superpowers/plans/2026-09-24-figure-library-node-classes.md), Task 11. Each item names the file it changes and the check that proves it is gone.

- [ ] `papers/figures/layout.py` loses `size`, `refit`, `reflow_narrow`, `justify`, `_grow_group`, `place`, and the per-kind `walk` in `prime`; `prime` walks `Node.children()`. Check: `grep -n "^def \(size\|refit\|reflow_narrow\|justify\|_grow_group\|place\)" papers/figures/layout.py` prints nothing.
- [ ] `papers/figures/render.py` loses `_draw` and the `kind` branches; `compose` calls `Node` methods. Check: `grep -n "_draw\|kind == '" papers/figures/render.py` prints nothing.
- [ ] `papers/figures/schema.py` loses the `elif kind ==` branches in `_scene_node` and the `text` loop's kind branches; `NODE_FIELDS` and `NODE_DOCS` are derived. Check: `grep -c "elif kind ==" papers/figures/schema.py` prints `0`.
- [ ] The migration-time imports inside functions move to module level. Check: `grep -n "^    from papers.figures.nodes" papers/figures/*.py` prints nothing.
```

- [ ] **Step 2: Delete and lift**

Remove every function and branch named in the cleanup section. Lift `from papers.figures.nodes import Node` to module level in `layout.py`, `render.py`, and `schema.py`. If the module-level import creates a cycle, `nodes.py` must import only from `layout.py` constants, `text.py`, `palette.py`, and `limits.py`, and `layout.py` must not import `nodes.py` at module level; in that case `prime` moves into `nodes.py` as `prime(measure, scene, frame)` and `compose` imports it from there.

Run every check from the cleanup section and tick the boxes.

- [ ] **Step 3: Run the whole suite and the baseline compare**

```bash
python3 -m unittest discover -s tests 2>&1 | tail -3
python3 tests/baseline_scenes.py --compare
```

Expected: `OK` and `same` for every Scene.

- [ ] **Step 4: Record the structure in the design**

Add to the Open section of `docs/superpowers/specs/2026-09-18-overview-scene-layout-design.md`:

```markdown
- 2026-09-24: the Figure library's node kinds are classes in `papers/figures/nodes.py`, one per kind, each holding its fields, card entry, validation, sizing, and drawing. The Scene dict stays the state; a class is a view over it. Output was byte-identical across the move (`tests/baseline_scenes.py --compare`).
```

Set the cleanup section's status to `completed on <date>`.

- [ ] **Step 5: Commit and merge**

```bash
git add -A papers/figures docs/cleanup.md docs/superpowers/specs/2026-09-18-overview-scene-layout-design.md
git commit -m "Delete the kind chains now that every node kind is a class"
git checkout main
git merge --no-ff figure-library-node-classes
```

## Self-review

- Coverage: every kind in `schema.KINDS` has a task (Tasks 1 to 9), the schema's three per-kind tables have Task 10, and the deletion has Task 11 with its `docs/cleanup.md` entry as AGENTS.md requires.
- Placeholders: Tasks 3 to 8 name the exact branches to move and the move rules to apply instead of repeating 200 lines of existing code. The code is on the branch; the baseline compare is the check that the move was exact.
- Type consistency: `Node.place(x, y, canvas, measure, stretch=None)` in Task 9 matches the `place` signature the layout defects plan produced. `validate(path, depth, errors, ids, count, recurse)` in Task 10 step 2 is the one signature; the docstring stub in the same step's first block must use it too.
