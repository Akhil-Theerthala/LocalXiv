# Inline Overview figure implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show the Overview's Figure render as inline SVG in the reader, so text is selectable, a hover or focus on a card shows that component's Digest fields, and a click opens the Paper at the component's first passage. The drawn figure and every export stay the same.

**Architecture:** The Figure library keeps knowing nothing about papers. Its renderer adds one hook per card and per headed group, a `<g data-node="…">` wrapper, and reports the hooks with the panel placements. The Overview workflow matches Digest component names to hook texts and stores the matches on the figure record as `components`. The reader fetches the Scene's SVG file for the current Figure palette, parses it, adds an SVG `<title>` and a click handler to each hooked element that has a component, and puts the SVG in the page in place of the image. The app's WKWebView is the same WebKit and font the Measurer measured with, so the inline SVG wraps exactly as the exported PNG does.

**Tech Stack:** Python 3 standard library and `unittest`; browser JavaScript modules in `app/static/` tested with `node` and `tests/dom_stub.mjs`.

**Spec:** none. The decisions are in this plan's Decisions section. The terms come from `CONTEXT.md`: Digest, Scene, Figure library, Figure render, Figure palette, Overview.

## Global constraints

- The model authors nothing new. No provider request changes. No model markup reaches the page.
- The SVG files that `Figure.build` writes change only by the `<g data-node>` wrappers. PNG, PDF, EPUB, and Kindle exports are unchanged, and the native checks must stay clean.
- Keep `svg_dark`. The reader inlines the light or the dark file to match the theme. Collapsing both palettes into CSS variables would need `rsvg-convert` to honour `var()` in the export path, which nobody has verified. Defer it.
- Scope is the Overview figure. Blog figures keep the `<img>` path, because their `portrait` variant is chosen by a media query on a `<picture>` element. Name Blog figures as the follow-up in the design note.
- Tests go under `tests/`. Python tests run with `python3 -m unittest tests.<module> -v`; front-end tests run with `node tests/<file>.mjs`.
- Commit messages carry no `Co-Authored-By` trailer. Work on a branch named `inline-overview-figure` and merge with `git merge --no-ff`.
- Run this plan after [the Figure library layout defects plan](2026-09-24-figure-library-layout-defects.md), so `place` already takes a `measure` argument.

## Decisions

- **Hover shows Digest fields only.** The component's name, `computes`, `role`, and `values`, in that order. The figure's drawn text does not change, so the on-screen figure and the exported figure are the same figure. This is the user's decision of 2026-09-24.
- **Hooks are stable across the light and dark passes.** `_draw` runs on the same tree in the same order for both palettes, so a card's hook is its Scene `id` when it has one, otherwise `n` plus the count of boxes drawn so far. A headed group's hook is `g` plus that count.
- **The workflow does the matching, in Python.** The reader receives a finished list and adds no logic of its own beyond attaching titles and handlers. Matching uses the same whitespace-and-case normalisation as `Figure.missing`.
- **The enlarge dialog stays as it is.** It zooms an `<img>` of the same SVG file. The inline SVG sits outside the dialog button, so a click on a card does not open the dialog.
- **Old generations still display.** A figure record without `svg_source` or without `components` renders through the existing `<img>` path with no hover.

## File structure

- Modify `papers/figures/render.py`: `<g data-node>` wrappers in `_draw`, a `nodes` list on each placement in `compose`.
- Modify `papers/overview_workflow.py`: `component_hooks(digest, placements)` and `figure['components']`.
- Modify `app/static/render.js`: the figure block for an inlinable figure, `annotateFigure`, `componentSummary`.
- Modify `app/static/app.js`: `inlineFigure`, `openPassage`, the theme swap for inline figures.
- Modify `app/static/reader-layout.css`: inline SVG and hover styles.
- Create `tests/test_figure_hooks.py`; modify `tests/test_overview_workflow.py` and `tests/test_render.mjs`.
- Modify `CONTEXT.md` and `docs/superpowers/specs/2026-09-18-overview-scene-layout-design.md`.

---

### Task 1: The renderer marks every card and headed group

**Files:**
- Modify: `papers/figures/render.py:52-84` (`_draw` card and group branches), `papers/figures/render.py:300-318` (`compose`, after `_draw`)
- Create: `tests/test_figure_hooks.py`

**Interfaces:**
- Produces: in the SVG, `<g data-node="KEY">` around each card's rect and text, and around each headed group's frame rect and heading text but not its children. Each placement dict from `compose` gains `'nodes': [{'node': KEY, 'text': TEXT}, …]` in draw order, where TEXT is the card's label plus detail or the group's heading.

- [ ] **Step 1: Write the failing test**

Create `tests/test_figure_hooks.py`:

```python
"""The renderer marks cards and headed groups so the reader can attach Digest fields to them."""
import copy
import json
import re
import unittest
from pathlib import Path

from papers.figures.layout import Canvas
from papers.figures.measure import FixedMeasurer
from papers.figures.palette import DARK
from papers.figures.render import compose

FIXTURES = Path(__file__).resolve().parent / 'fixtures' / 'overview'
HOOK = re.compile(r'<g data-node="([^"]+)">')


def compose_fixture(name, palette=None):
    scene = json.loads((FIXTURES / name).read_text())
    kwargs = {'palette': palette} if palette else {}
    return compose(FixedMeasurer(), copy.deepcopy(scene), Canvas(1000), frame='page', page_title='Paper', **kwargs)


class HookTests(unittest.TestCase):
    def test_a_card_with_an_id_is_hooked_by_that_id(self):
        svg, placements = compose_fixture('attention-scene.json')
        self.assertIn('<g data-node="matmul">', svg)
        nodes = {node['node']: node['text'] for item in placements for node in item['nodes']}
        self.assertEqual(nodes['matmul'], 'MatMul: Q · Kᵀ')

    def test_a_headed_group_is_hooked_and_its_children_are_outside_the_wrapper(self):
        svg, placements = compose_fixture('attention-scene.json')
        texts = [node['text'] for item in placements for node in item['nodes']]
        self.assertIn('ENCODER', texts)
        start = svg.index('ENCODER')
        wrapper_end = svg.index('</g>', start)
        self.assertNotIn('Feed Forward Network', svg[start:wrapper_end])

    def test_every_reported_hook_appears_once_in_the_svg(self):
        svg, placements = compose_fixture('attention-scene.json')
        reported = [node['node'] for item in placements for node in item['nodes']]
        self.assertEqual(len(reported), len(set(reported)))
        self.assertEqual(sorted(HOOK.findall(svg)), sorted(reported))

    def test_light_and_dark_passes_report_the_same_hooks(self):
        _, light = compose_fixture('attention-scene.json')
        _, dark = compose_fixture('attention-scene.json', DARK)
        self.assertEqual([item['nodes'] for item in light], [item['nodes'] for item in dark])

    def test_a_card_without_an_id_still_gets_a_hook(self):
        svg, placements = compose_fixture('variety-scene.json')
        hooks = [node['node'] for item in placements for node in item['nodes']]
        self.assertTrue(any(hook.startswith('n') for hook in hooks))
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m unittest tests.test_figure_hooks -v`
Expected: every test fails, the first with `'<g data-node="matmul">' not found`.

- [ ] **Step 3: Wrap cards and headed groups and record the hooks**

In `papers/figures/render.py`, in `_draw`, change the start of the `card` branch to:

```python
    if kind == 'card':
        hook = node.get('id') or 'n' + str(len(boxes))
        node['hook'] = hook
        out.append(f'<g data-node="{esc(hook)}">')
        tone = node.get('tone') or 'plain'
```

and, at the end of the branch, after `boxes[node.get('id') or '#' + str(len(boxes))] = (x, y, w, h)`, add:

```python
        out.append('</g>')
```

In the `group` branch, change the `if node.get('heading') is not None:` block so the frame and the heading are wrapped, and the heading obstacle from the layout defects plan stays inside the block:

```python
        if node.get('heading') is not None:
            hook = 'g' + str(len(boxes))
            node['hook'] = hook
            out.append(f'<g data-node="{esc(hook)}">')
            tone = node.get('tone')
            fill, stroke, colour = palette.tones[tone] if tone in ACCENT_TONES else (palette.card, palette.hairline, palette.text)
            out.append(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="10" fill="{fill}" '
                       f'fill-opacity="0.35" stroke="{stroke}" stroke-width="1.2"/>')
            # A container's frame: an arrow label may sit inside or outside it, never across its edge.
            boxes['@' + str(len(boxes))] = (x, y, w, h)
            heading = str(node['heading']) + (' ' + str(node['repeat']) if node.get('repeat') else '')
            out.append(_text(x + GAP, y + 16, heading, weight=700, fill=colour))
            # The heading text is a leaf: an arrow does not cross it and a label does not cover it.
            boxes['#' + str(len(boxes))] = (x + GAP, y + 4, measure.width(heading, BODY, 700), LINE[BODY])
            out.append('</g>')
        for child in node['children']:
            _draw(child, out, boxes, measure, palette)
```

Add a helper after `_draw_edge`:

```python
def hooks(node):
    """Every hooked node in draw order, with the text a reader sees on it."""
    found = []
    if node.get('hook'):
        text = (str(node['heading']) if node['kind'] == 'group'
                else ' '.join(part for part in (str(node['label']), str(node.get('detail', ''))) if part))
        found.append({'node': node['hook'], 'text': text})
    for child in node.get('children', []):
        found.extend(hooks(child))
    return found
```

In `compose`, change the `placements.append(...)` call to include the hooks:

```python
        placements.append({'id': panel.get('id', 'panel' + str(number)), 'number': number,
                           'fill': round(body['w'] / inner, 3),
                           'frame': {'x': x, 'y': panel_y, 'width': panel_w, 'height': panel_h},
                           'nodes': hooks(body)})
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m unittest tests.test_figure_hooks tests.test_scene_layout tests.test_figure tests.test_layout_defects -v`
Expected: all pass, including `test_build_writes_a_dark_svg_from_the_same_layout`, and the native checks in `test_figure` report no issue.

- [ ] **Step 5: Commit**

```bash
git add papers/figures/render.py tests/test_figure_hooks.py
git commit -m "Mark cards and headed groups with a data-node hook"
```

---

### Task 2: The workflow stores the Digest fields for each hooked component

**Files:**
- Modify: `papers/overview_workflow.py:216-240` (`run_workflow`) and a new function beside `document_digest_of`
- Test: `tests/test_overview_workflow.py`

**Interfaces:**
- Consumes: `placements[i]['nodes']` from Task 1.
- Produces: `component_hooks(digest, placements) -> list[dict]`, each dict `{'node', 'name', 'role', 'computes', 'values', 'passages'}`. The figure record gains `'components': component_hooks(...)`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_overview_workflow.py`:

```python
import re

from papers.overview_workflow import component_hooks


class ComponentHookTests(unittest.TestCase):
    def test_the_longest_component_name_in_a_node_text_wins(self):
        digest = {'components': [
            {'id': 'a', 'name': 'Attention', 'role': 'mixes values', 'passages': ['p1']},
            {'id': 'b', 'name': 'Multi-head attention', 'role': 'runs h heads', 'computes': 'Concat(head_i)W^O',
             'passages': ['p2', 'p3']}]}
        placements = [{'nodes': [{'node': 'mha', 'text': 'Multi-Head Attention (h = 8)'},
                                 {'node': 'n7', 'text': 'Feed-forward network'}]}]
        self.assertEqual(component_hooks(digest, placements), [
            {'node': 'mha', 'name': 'Multi-head attention', 'role': 'runs h heads',
             'computes': 'Concat(head_i)W^O', 'values': None, 'passages': ['p2', 'p3']}])

    def test_the_run_stores_components_that_match_the_svg_hooks(self):
        scene = json.loads((FIXTURES / 'attention-run.json').read_text())
        digest = json.loads((FIXTURES / 'attention-digest.json').read_text())
        selection = json.loads((FIXTURES / 'attention-selection.json').read_text())
        document = json.loads((FIXTURES / 'attention-document.json').read_text())
        with tempfile.TemporaryDirectory() as directory:
            document['directory'] = directory
            result = generate(FakeProvider([selection, digest, scene]), document, lambda label: None)
            figure = result['figures'][0]
            self.assertTrue(figure['components'])
            names = {component['name'] for component in digest['components']}
            for item in figure['components']:
                self.assertIn('<g data-node="' + item['node'] + '">', figure['source_svg'])
                self.assertIn(item['name'], names)
                self.assertTrue(item['passages'])
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m unittest tests.test_overview_workflow -v`
Expected: `ImportError: cannot import name 'component_hooks'`.

- [ ] **Step 3: Add `component_hooks` and store it on the figure**

In `papers/overview_workflow.py`, add after `document_digest_of`:

```python
def component_hooks(digest, placements):
    """The Digest fields for every drawn node whose text names a component.

    The reader shows these on hover. Names are compared after whitespace and case normalisation,
    the same rule Digest coverage uses, and the longest matching name wins so "Multi-head
    attention" beats "Attention" on the same card.
    """
    def flat(value):
        return ' '.join(str(value).split()).lower()

    components = sorted(digest['components'], key=lambda component: -len(component['name']))
    found = []
    for placement in placements:
        for node in placement.get('nodes', []):
            text = flat(node['text'])
            match = next((component for component in components if flat(component['name']) in text), None)
            if match:
                found.append({'node': node['node'], 'name': match['name'], 'role': match['role'],
                              'computes': match.get('computes'), 'values': match.get('values'),
                              'passages': list(match.get('passages', []))})
    return found
```

Add `'component_hooks'` to `__all__`. In `run_workflow`, extend the `figure.update(...)` call with one more keyword:

```python
                      components=component_hooks(digest, result.placements),
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m unittest tests.test_overview_workflow -v`
Expected: all pass. If `test_the_run_stores_components_that_match_the_svg_hooks` finds an empty list, print `[node['text'] for item in result.placements for node in item['nodes']]` and the digest names to see which normalisation differs, then fix `flat`, not the test.

- [ ] **Step 5: Commit**

```bash
git add papers/overview_workflow.py tests/test_overview_workflow.py
git commit -m "Store the Digest fields for each hooked figure component"
```

---

### Task 3: The reader annotates a parsed SVG with component titles

**Files:**
- Modify: `app/static/render.js` (new exports `annotateFigure`, `componentSummary`)
- Test: `tests/test_render.mjs`

**Interfaces:**
- Produces: `componentSummary({name, role, computes, values}) -> string` and `annotateFigure(elements, components, {svgNode, onPassage}) -> number`, the count of elements that received a component. `svgNode(tag)` creates an SVG element; `onPassage(id)` opens a passage.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_render.mjs`, before the `renderLibrary` section:

```js
import {annotateFigure, componentSummary} from '../app/static/render.js';

assert.equal(componentSummary({name: 'Multi-head attention', role: 'runs h heads', computes: 'Concat(head_i)W^O', values: 'h = 8'}),
  'Multi-head attention computes Concat(head_i)W^O. runs h heads. Values: h = 8');
assert.equal(componentSummary({name: 'FFN', role: 'position-wise'}), 'FFN. position-wise');

const hooked = new Element('g'), unhooked = new Element('g'), unknown = new Element('g');
hooked.dataset.node = 'mha'; unhooked.dataset.node = 'n7'; unknown.dataset.node = 'zzz';
const passages = [];
const count = annotateFigure([hooked, unhooked, unknown],
  [{node: 'mha', name: 'Multi-head attention', role: 'runs h heads', computes: null, values: null, passages: ['p2', 'p3']}],
  {svgNode: tag => new Element(tag), onPassage: id => passages.push(id)});
assert.equal(count, 1);
assert.equal(hooked.children[0].tagName, 'TITLE');
assert.equal(hooked.children[0].textContent, 'Multi-head attention. runs h heads');
assert.equal(hooked.getAttribute('tabindex'), '0');
assert.ok(hooked.classList.contains('has-component'));
hooked.onclick(); assert.deepEqual(passages, ['p2']);
assert.equal(unhooked.children.length, 0, 'a hook without a component gets no title');
assert.equal(unknown.onclick, undefined);
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `node tests/test_render.mjs`
Expected: `SyntaxError: The requested module '../app/static/render.js' does not provide an export named 'annotateFigure'`.

- [ ] **Step 3: Add the two functions**

Append to `app/static/render.js`:

```js
// Component hover: the Digest fields for one drawn card or group heading, as the SVG title the
// browser shows on hover and the label a screen reader announces.
export function componentSummary({name, role, computes, values}) {
  return [name + (computes ? ' computes ' + computes : ''), role, values ? 'Values: ' + values : ''].filter(Boolean).join('. ');
}

export function annotateFigure(elements, components, {svgNode, onPassage}) {
  const byNode = new Map((components || []).map(item => [item.node, item]));
  let count = 0;
  for (const element of elements) {
    const component = byNode.get(element.dataset.node);
    if (!component) continue;
    const summary = componentSummary(component);
    const title = svgNode('title'); title.textContent = summary;
    element.append(title);
    element.classList.add('has-component');
    element.setAttribute('tabindex', '0'); element.setAttribute('role', 'link'); element.setAttribute('aria-label', summary);
    const passage = component.passages?.[0];
    if (passage && onPassage) {
      element.onclick = () => onPassage(passage);
      element.onkeydown = event => { if (['Enter', ' '].includes(event.key)) { event.preventDefault(); onPassage(passage); } };
    }
    count++;
  }
  return count;
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `node tests/test_render.mjs`
Expected: exits 0 with no output.

- [ ] **Step 5: Commit**

```bash
git add app/static/render.js tests/test_render.mjs
git commit -m "Attach component titles and passage links to hooked figure nodes"
```

---

### Task 4: The figure block inlines the SVG for a figure that has a source file

**Files:**
- Modify: `app/static/render.js:191-205` (the figure branch of `renderProse`)
- Modify: `app/static/app.js:130-131` (the `prose` helper), `app/static/app.js:516-521` (`swapFigureSources`), and new functions `inlineFigure` and `openPassage` beside `sources`
- Modify: `app/static/reader-layout.css:39-44`
- Test: `tests/test_render.mjs`

**Interfaces:**
- Consumes: `annotateFigure` from Task 3, `figure.components` from Task 2, `figure.svg_source` and `figure.svg_dark` from the figure record.
- Produces: `renderProse` calls `io.inlineFigure(container, figure)` when both exist. The container is a `div.figure-inline` with `dataset.lightSrc` and `dataset.darkSrc`.

- [ ] **Step 1: Write the failing test**

In `tests/test_render.mjs`, after the existing `renderProse` figure assertions (the line `assert.equal(figures.length, 1);`), add:

```js
const inlined = [];
target = new Element('div');
renderProse(target, '{{figure:fig1}}', {...io, inlineFigure: (container, figure) => inlined.push([container, figure]),
  figures: [{id: 'fig1', svg: 'reader/f.svg', svg_source: 'reader/f.source.svg', svg_dark: 'reader/f.dark.svg',
             components: [], caption: 'Cap', alt: 'Alt'}]});
assert.equal(inlined.length, 1, 'a figure with a source file is inlined');
const [container] = inlined[0];
assert.equal(container.className, 'figure-inline');
assert.equal(container.dataset.lightSrc, '/files/x/reader/f.source.svg');
assert.equal(container.dataset.darkSrc, '/files/x/reader/f.dark.svg');
assert.equal(find(target, el => el.tagName === 'IMG'), undefined, 'no image element beside the inline figure');
assert.ok(find(target, el => String(el.className).includes('figure-open')), 'the enlarge button stays');
assert.ok(find(target, el => el.tagName === 'FIGCAPTION'));

target = new Element('div');
renderProse(target, '{{figure:fig1}}', {...io, inlineFigure: (container, figure) => inlined.push([container, figure]),
  figures: [{id: 'fig1', svg: 'reader/f.svg', caption: 'Old', alt: 'Alt'}]});
assert.equal(inlined.length, 1, 'a figure without a source file keeps the image path');
assert.ok(find(target, el => el.tagName === 'IMG'));
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `node tests/test_render.mjs`
Expected: `a figure with a source file is inlined` fails with `0 !== 1`.

- [ ] **Step 3: Branch the figure block in `renderProse`**

In `app/static/render.js`, replace the body of the `if (image) {` block in the figure branch with:

```js
      if (image) {
        const block = node('figure', undefined, 'overview-figure');
        const alt = figure.alt || figure.caption || 'Paper explanation';
        const source = fileURL(figure.svg_source);
        if (source && io.inlineFigure) {
          // The Scene's own SVG goes into the page, so its text is selectable and its cards can
          // carry the component hover. The enlarge dialog keeps zooming the image file.
          const container = node('div', undefined, 'figure-inline');
          container.dataset.lightSrc = source;
          const dark = fileURL(figure.svg_dark); if (dark) container.dataset.darkSrc = dark;
          container.setAttribute('aria-busy', 'true');
          const expand = node('button', 'Enlarge figure ↗', 'figure-open quiet'); expand.type = 'button';
          expand.onclick = () => openFigure(image, alt, figure.caption, figure.panels, figure.dimensions);
          block.append(container, expand, node('figcaption', figure.caption));
          target.append(block);
          io.inlineFigure(container, figure);
        } else {
          const img = node('img');
          img.src = image; img.dataset.lightSrc = image; const dark = fileURL(figure.svg_dark); if (dark) img.dataset.darkSrc = dark; img.alt = alt; img.loading = 'lazy';
          const expand = node('button', undefined, 'figure-open'); expand.type = 'button'; expand.setAttribute('aria-label', 'Enlarge figure: ' + alt); const picture = node('picture');
          if (figure.portrait?.svg) { const source = node('source'); source.media = '(max-width: 600px)'; source.srcset = fileURL(figure.portrait.svg); picture.append(source); }
          picture.append(img); expand.append(picture, node('span', 'Enlarge figure ↗'));
          expand.onclick = () => openFigure(img.currentSrc || image, img.alt, figure.caption, figure.panels, figure.dimensions);
          block.append(expand, node('figcaption', figure.caption));
          target.append(block);
        }
      } else target.append(node('p', 'Figure unavailable. Regenerate this view to restore it.', 'muted'));
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `node tests/test_render.mjs`
Expected: exits 0.

- [ ] **Step 5: Fetch, parse, and annotate in the app**

In `app/static/app.js`, import `annotateFigure` in the existing `render.js` import line. Add after the `sources` function:

```js
const SVG_NS = 'http://www.w3.org/2000/svg';
const inlineFigures = new WeakMap();
// The Overview's Figure render goes into the page as SVG, in the Figure palette that matches the
// theme. The file is the application's own render; the parser still refuses anything that is not
// one SVG document, and the page's CSP runs no script from it.
async function inlineFigure(container, figure) {
  inlineFigures.set(container, figure);
  const theme = document.documentElement.dataset.theme;
  const url = theme === 'dark' && container.dataset.darkSrc ? container.dataset.darkSrc : container.dataset.lightSrc;
  if (!url) return;
  try {
    const response = await fetch(url, {credentials: 'same-origin'});
    if (!response.ok) throw new Error(response.statusText);
    const parsed = new DOMParser().parseFromString(await response.text(), 'image/svg+xml');
    const svg = parsed.documentElement;
    if (svg.namespaceURI !== SVG_NS || svg.tagName !== 'svg' || parsed.querySelector('parsererror')) throw new Error('not an SVG document');
    svg.removeAttribute('width'); svg.removeAttribute('height');
    svg.setAttribute('role', 'img'); svg.setAttribute('aria-label', figure.alt || figure.caption || 'Paper explanation');
    annotateFigure(svg.querySelectorAll('[data-node]'), figure.components, {svgNode: tag => document.createElementNS(SVG_NS, tag), onPassage: openPassage});
    container.replaceChildren(svg); container.dataset.theme = theme; container.removeAttribute('aria-busy');
  } catch (error) {
    container.replaceChildren(node('p', 'Figure unavailable. Regenerate this view to restore it.', 'muted'));
    container.removeAttribute('aria-busy');
  }
}
function openPassage(id) {
  const passage = (detail?.overview?.evidence || []).find(item => item.id === id);
  const url = passage && fileURL(passage.href);
  if (!url) return;
  $('reader').src = url; switchTab('paper');
}
```

Change the `prose` helper to pass `inlineFigure` along with the other io:

```js
const prose = (target, text, references, figures) => renderProse(target, text, {node, references, figures, fileURL, renderMath, openFigure, inlineFigure,
  openSource: href => { $('reader').src = fileURL(href); switchTab('paper'); }});
```

Extend `swapFigureSources` so an inline figure follows the theme:

```js
function swapFigureSources(theme) {
  for (const img of document.querySelectorAll('img[data-dark-src]')) {
    const next = theme === 'dark' ? img.dataset.darkSrc : img.dataset.lightSrc;
    if (img.getAttribute('src') !== next) img.src = next;
  }
  for (const container of document.querySelectorAll('.figure-inline[data-dark-src]')) {
    if (container.dataset.theme !== theme && inlineFigures.has(container)) inlineFigure(container, inlineFigures.get(container));
  }
}
```

Check that `swapFigureSources` is called where the theme changes (`applyAppearance`), and that `detail` is the module variable that holds the paper detail response with `overview.evidence`. The server returns the stored generation whole from `library.get_generation`, and `GENERATION_KEYS` includes `evidence`, so the passages with their `href` are present.

- [ ] **Step 6: Style the inline figure**

In `app/static/reader-layout.css`, after the `.overview-figure img` rule, add:

```css
.figure-inline{padding:12px;background:var(--paper);border:1px solid var(--line);border-radius:14px;overflow:hidden}
.figure-inline svg{display:block;width:100%;height:auto}
.figure-inline .has-component{cursor:pointer}
.figure-inline .has-component:hover>rect:first-of-type,.figure-inline .has-component:focus-visible>rect:first-of-type{stroke:var(--accent);stroke-width:2}
.figure-inline .has-component:focus-visible{outline:none}
.overview-figure .figure-open.quiet{width:auto;display:inline-block;margin-top:10px;padding:8px 12px;font-size:var(--text-small)}
```

Run: `node tests/test_css.mjs`
Expected: exits 0.

- [ ] **Step 7: Verify in the app**

Start the reader with the isolated library from `docs/development.md` and open a paper that has an Overview generated after Task 2. Check:

1. The Overview tab shows the figure as inline SVG. Select a word in a card; the selection works.
2. Hover a card that names a Digest component; the browser shows the summary. Press Tab to reach the card; the accent outline appears.
3. Click that card; the Paper tab opens at the cited passage.
4. Switch the theme; the figure changes to the dark Figure palette without a reload.
5. Open a paper whose Overview predates Task 2; the figure still shows as an image with the enlarge button.
6. Export PNG and PDF from the share dialog; both open and match the on-screen figure.

- [ ] **Step 8: Commit**

```bash
git add app/static/render.js app/static/app.js app/static/reader-layout.css tests/test_render.mjs
git commit -m "Inline the Overview figure and show Digest fields on hover"
```

---

### Task 5: Name the term and record the decision

**Files:**
- Modify: `CONTEXT.md` (after the Figure palette entry)
- Modify: `docs/superpowers/specs/2026-09-18-overview-scene-layout-design.md` (Open list)

- [ ] **Step 1: Add the term**

In `CONTEXT.md`, after the **Figure palette** entry, add:

```markdown
**Component hover**: The Digest fields for one drawn card or group heading, shown when the reader hovers or focuses it in the inline Figure render: name, `computes`, role, and values. A click opens the Paper at the component's first passage. The figure's drawn text does not change, so the on-screen figure and every export are the same figure.
```

- [ ] **Step 2: Record the decision in the design's Open list**

Add to the Open section of `docs/superpowers/specs/2026-09-18-overview-scene-layout-design.md`:

```markdown
- 2026-09-24: the reader shows the Overview as inline SVG with the Component hover (`docs/superpowers/plans/2026-09-24-inline-overview-figure.md`). The Figure library adds only `data-node` hooks. Open: Blog figures still display as images because of their portrait variant, and the dark file stays until `rsvg-convert` is shown to honour CSS `var()` in exports.
```

- [ ] **Step 3: Run every test and commit**

Run:

```bash
python3 -m unittest discover -s tests 2>&1 | tail -3
for test in tests/test_*.mjs; do node "$test" || echo "FAILED $test"; done
```

Expected: `OK` from Python and no `FAILED` line.

```bash
git add CONTEXT.md docs/superpowers/specs/2026-09-18-overview-scene-layout-design.md
git commit -m "Name the Component hover and record the inline figure decision"
git checkout main
git merge --no-ff inline-overview-figure
```

## Self-review

- Coverage: the renderer hook (Task 1), the workflow's component list (Task 2), the reader annotation (Task 3), the inline display with theme swap and passage links (Task 4), and the language entry (Task 5) cover every decision above. Exports need no task because the SVG files change only by the wrappers, which Task 1's `test_figure` run checks against the native renderer.
- Placeholders: none.
- Type consistency: `placements[i]['nodes']` items are `{'node', 'text'}` in Task 1 and read as such in Task 2. `figure['components']` items are `{'node', 'name', 'role', 'computes', 'values', 'passages'}` in Task 2 and read by `annotateFigure` in Task 3. `io.inlineFigure(container, figure)` in Task 4's `renderProse` matches `inlineFigure(container, figure)` in `app.js`.
