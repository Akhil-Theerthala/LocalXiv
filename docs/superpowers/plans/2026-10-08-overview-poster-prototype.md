# Overview poster prototype plan (2026-10-08)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Decide, by looking at renders, which poster-style changes the Overview adopts: a hero number beside the title, a weighted sequence, a band node, and chips moved out of the panels.

**Architecture:** A throwaway branch, `overview-poster-prototype`, with a build script that draws four variants of the two story scenes through the real Figure library and a comparison page to switch between them, as [the 2026-10-08 Overview story plan](2026-10-08-overview-story.md) did with the branch `overview-prototype`. No model call. Library code on the branch may change freely; the user's pick is then built on a clean branch from a second plan, and nothing is ported from this branch unchanged.

**Tech stack:** Python 3 in `.venv`, the Figure library in `papers/figures/`, the native renderer `papers/html-snapshot`, one static HTML page.

**Spec:** this file. The "Design" section states what each variant shows. The decisions the renders must settle are listed under "Decisions after the renders".

## Design

The Overview keeps its narrative strip: Why, Setup or How, Model, Result. The poster discipline adds three reading distances. From far: the title and one number. From the middle: the panel headings and one drawn object per panel. Up close: the card details. Today the far distance has no number, and the middle distance has only boxes with words.

The variants, from the current page to the full change. Each later variant includes the earlier ones.

- **P0, current.** The two story scenes on `main` at `627a131`, as the workflow laid them out. The baseline.
- **P1, hero number.** The Scene gains `hero`: one stat drawn at the top right, beside the title and subtitle, in the stat size. The Result panel keeps its stats. On AI Control the hero is "92% safety" or "85%" with "runs end with no backdoor"; on Attention it is "28.4 BLEU". This is a spec change: the Overview entry in `CONTEXT.md` says the headline numbers open the Result panel.
- **P2, drawn objects.** Two node changes.
  - A sequence item takes `weight`, a number from 0 to 1. When any item has a weight, the row grows by one line and each weighted item draws a track with a filled bar under its caption, in the accent colour. On Attention the How panel's token row shows the weights of "making" over its keys, with the values as captions. The 2026-10-08 scratch prototype rendered this with no issue and no warning at density 56.3.
  - A new `band` node: a horizontal number line with `low`, `high`, an optional `unit`, two to five `ticks`, and one to three `bands` of `{from, to, label, tone?}` drawn as shaded spans above the line. On AI Control the Setup panel shows the suspicion score line from 0 to 100 with the top 2 percent audit band and the 2 to 10 percent and 2 to 20 percent deferral bands.
- **P3, chips out.** Chips leave the panels. The components that the arrows do not touch go into one footer line, "Also in the paper: …", in the muted colour. The AI Control Result panel's chart takes the full panel width, and the Attention Result panel loses its leftover pipeline, which moves to one footer line. This is a spec change: coverage today requires every component to appear as a node.

Every variant reports its density, height, and text-run count on the comparison page, so the user sees whether a drawn page falls under the floor of 40 text runs per million square units.

Out of scope: a before-and-after pair node, a present mode in the reader, the arrow between side-by-side panels, new prompts. Prompts come after the pick, and the Scene vocabulary the model reads is generated from the node classes, so a new node kind reaches the prompt on its own.

## Decisions after the renders

The user settles these by looking at the page. Each is a yes or no, and the second plan builds only the yeses.

1. Hero number beside the title. If yes, the Overview entry in `CONTEXT.md` and the story design change: the Result panel keeps its stats, and one of them is also drawn in the header.
2. Weighted sequence. If yes, the item field `weight` is added to the Sequence class with validation, and the Scene prompt says when a weight may be illustrative.
3. Band node. If yes, the Band class is added with validation and a draw test.
4. Chips out. If yes, the workflow's chip pass moves the chips into the footer line, coverage counts the footer, and the panel chart widens. If no, the chips stay and the chart rule changes alone.
5. Density floor. If a drawn variant the user likes falls under 40, the floor counts drawn marks, bars, bands, and chart points as text runs, or the floor drops. This is the user's number.

## Global constraints

- Work in the worktree `/Users/silver/Developer/LocalXiv/.worktrees/overview-poster-prototype` on the branch `overview-poster-prototype`. Never run git in `/Users/silver/Developer/LocalXiv`.
- Link the untracked tools into the worktree before anything else: `ln -s /Users/silver/Developer/LocalXiv/tests tests`, `ln -s /Users/silver/Developer/LocalXiv/.venv .venv`, `ln -s /Users/silver/Developer/LocalXiv/papers/html-snapshot papers/html-snapshot`. Never `git add tests`. Never `git add -A` or `git add .`.
- Run `.venv/bin/python`, not `python3`.
- Every commit message on this branch starts with `PROTOTYPE:`. No attribution line.
- Library changes on this branch need no tests. They are throwaway. The branch is never merged.
- The PNGs in `tools/overview-prototype/png/` are committed, so the user can open them without a build.

## Review focus

1. A `weight` of 0 or 1 draws an empty or a full bar, not an error. The weighted sequence in Task 3 renders both.
2. A band whose `from` equals `low` or whose `to` equals `high` sits flush with the line's end. Task 3's AI Control band starts at 98 and ends at 100.
3. A hero stat whose label wraps to two lines must not push the panels down more than one line. Task 2 renders the longer AI Control label.
4. The comparison page must show each variant's density next to its name, or decision 5 cannot be made. Task 1 prints it.
5. The footer line in P3 must stay under the footer limit of 320 characters, or the Scene validator rejects the page. Task 4 counts it and splits into two notes if needed.

---

### Task 1: Harness and baseline

**Files:**
- Create: `tools/overview-prototype/build.py`
- Create: `tools/overview-prototype/page.html`
- Create: `tools/overview-prototype/scenes/control.json`, `tools/overview-prototype/scenes/attention.json`

**Interfaces:**
- Produces: `VARIANTS`, an ordered dict of variant key to description; `build(key, paper) -> scene dict`; the script writes `png/{paper}-{key}.png`, `svg/{paper}-{key}.svg`, and `stats.json` with `{paper: {key: {height, density, text_runs, issues, warnings}}}`, then renders `index.html` from `page.html`.

- [ ] **Step 1: Save the two story scenes**

The scenes are the workflow's output on the fixtures, which the composition tests already build. Write `tools/overview-prototype/save_scenes.py`:

```python
"""Save the two story scenes the workflow lays out from the fixtures, so the variants start from them."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))
from tests.story_fixtures import control_story, load, luna_story  # noqa: E402
from tests.test_overview_composition import _run  # noqa: E402
from tests.test_overview_workflow import _document  # noqa: E402

HERE = Path(__file__).resolve().parent
RUNS = {
    'attention': ([load('attention-selection.json'), load('attention-luna-digest.json'),
                   load('attention-luna-scene.json'), luna_story()], _document('')),
    'control': ([load('control-sonnet-selection.json'), load('control-sonnet-digest.json'),
                 load('control-sonnet-scene.json'), control_story()], load('control-sonnet-document.json')),
}
(HERE / 'scenes').mkdir(exist_ok=True)
for paper, (answers, document) in RUNS.items():
    scene = _run(answers, document)[2]
    (HERE / 'scenes' / (paper + '.json')).write_text(json.dumps(scene, indent=1, ensure_ascii=False))
    print(paper, scene['title'])
```

Run: `.venv/bin/python tools/overview-prototype/save_scenes.py`
Expected: two lines with the titles, and two JSON files. The saved scenes carry the workflow's layout annotations (`x`, `y`, `w`, `h`, `inline`, `hook`, `minor`, and the rest). `Figure.build` validates a scene before layout and the validator rejects unknown fields, so `build.py` strips them: keep only the fields the node's class lists in `fields`, plus `minor`, which the workflow sets and the schema accepts.

- [ ] **Step 2: Write the harness**

Start from the earlier harness: `git show overview-prototype:tools/overview-prototype/build.py > tools/overview-prototype/build.py` and `git show overview-prototype:tools/overview-prototype/page.html > tools/overview-prototype/page.html`. Keep the switcher, the hover tip, and the render loop. Replace the hand-written scenes with the saved ones, and replace `VARIANTS` with:

```python
VARIANTS = {'P0': 'Current: the story scene as the workflow laid it out',
            'P1': 'Hero number beside the title',
            'P2': 'Hero number, weighted token row, suspicion band',
            'P3': 'Hero number, drawn objects, chips moved to the footer'}
```

Add the strip of layout annotations:

```python
from papers.figures.nodes import REGISTRY

def clean(node):
    """The node as the model wrote it: the class's fields and ``minor``, no layout annotation."""
    keep = REGISTRY[node['kind']].fields | {'minor'}
    out = {key: value for key, value in node.items() if key in keep}
    if 'children' in out:
        out['children'] = [clean(child) for child in out['children']]
    if 'items' in out and node['kind'] == 'sequence':
        out['items'] = [{k: v for k, v in item.items() if k in {'id', 'text', 'sub', 'tone', 'hot', 'weight'}}
                        for item in out['items']]
    return out

def load_scene(paper):
    scene = json.loads((HERE / 'scenes' / (paper + '.json')).read_text())
    for panel in scene['panels']:
        panel['body'] = clean(panel['body'])
        for key in list(panel):
            if key not in {'id', 'heading', 'tone', 'body', 'notes', 'edges'}:
                del panel[key]
    return {key: scene[key] for key in ('title', 'subtitle', 'footer', 'illustrative', 'layout', 'panels')}
```

Each variant is a function `p0(scene)`, `p1(scene)`, and so on that takes `load_scene(paper)` and returns the scene to draw. `p0` returns it unchanged. The render loop calls `Figure().build(scene, tmp, 'fig')`, copies the PNG and the source SVG, and records `result.checks['canvas']['height']`, `result.density`, `len(result.checks['text_runs'])`, `result.issues`, and `result.warnings` into `stats.json`. The page shows the four numbers under each variant's name.

- [ ] **Step 3: Build P0 and open the page**

Run: `.venv/bin/python tools/overview-prototype/build.py`
Expected: `png/control-P0.png` and `png/attention-P0.png` match the renders of the current main, and `index.html` opens with the switcher. Look at both PNGs with the Read tool.

- [ ] **Step 4: Commit**

```sh
git add tools/overview-prototype/build.py tools/overview-prototype/page.html tools/overview-prototype/save_scenes.py tools/overview-prototype/scenes tools/overview-prototype/png tools/overview-prototype/svg tools/overview-prototype/stats.json tools/overview-prototype/index.html
git commit -m "PROTOTYPE: harness and the current story scenes as variant P0"
```

### Task 2: P1, the hero number

**Files:**
- Modify: `papers/figures/render.py` (`compose`, the `if frame == 'page':` header block)
- Modify: `papers/figures/schema.py` (the scene field check, `required - {'edges'}`: allow `hero`)
- Modify: `tools/overview-prototype/build.py` (`p1`)

- [ ] **Step 1: Draw the hero**

In `compose`, after the subtitle lines and before `y += 12`, when `scene.get('hero')` is set, size a `Stat` node from it at 260 units and place it at `canvas.margin + canvas.column - stat.w`, with its top at the title's top. The title and subtitle wrap at `canvas.column - stat.w - 24` instead of `canvas.column` when a hero is present, so the two never overlap. The panels start under whichever is lower, the subtitle or the hero.

```python
    hero = Node.of(dict(scene['hero'], kind='stat')) if frame == 'page' and scene.get('hero') else None
    if hero is not None:
        hero.size(260, measure)
        hero.place(canvas.margin + canvas.column - hero.w, canvas.margin + 12 + 30 - LINE[TITLE] + 8, canvas, measure)
    text_width = canvas.column - (hero.w + 24 if hero is not None else 0)
```

Use `text_width` in the two `measure.wrap` calls for the title and subtitle, draw the hero with `hero.draw(out, {}, measure, palette)` after the subtitle, and set `y = max(y, hero.y + hero.h + 8)` before `y += 12`. `prime` must measure the hero's label at BODY and its value at STAT; add that where `prime` measures the title.

In `schema.py`, allow `hero` on the scene: a dict with `value` and `label` checked like a stat. The prototype may validate it loosely.

- [ ] **Step 2: Author the heroes**

```python
HEROES = {'control': {'value': '92%', 'label': 'safety with trusted editing, at 94% usefulness', 'tone': 'green'},
          'attention': {'value': '28.4', 'label': 'BLEU English→German, 2 above the best before', 'tone': 'green'}}

def p1(scene, paper):
    return {**scene, 'hero': HEROES[paper]}
```

The AI Control label is the long one, for review focus 3.

- [ ] **Step 3: Build and look**

Run the build. Read `png/control-P1.png` and `png/attention-P1.png`. The hero sits at the top right, the title wraps short of it, and the first panel starts one line lower at most.

- [ ] **Step 4: Commit**

`git commit -m "PROTOTYPE: variant P1, a hero number beside the title"` with the changed files named.

### Task 3: P2, the weighted sequence and the band

**Files:**
- Modify: `papers/figures/nodes.py` (`Sequence`; new `Band` class after `Bars`)
- Modify: `tools/overview-prototype/build.py` (`p2`)

- [ ] **Step 1: The weighted sequence**

In `Sequence`: add `weight` to the item fields in `validate` and to `field_docs` as `"weight"? 0 to 1`. In `size`, after `row_h` is set, when any item has `weight`, add `BAR_H + 6` to `row_h` and recompute `self.h`, with `BAR_H = 6` beside `SEQUENCE_GAP` in `layout.py`. In `draw`, after the caption, when the sequence has weights and the item has one:

```python
                top = y + self.spec['row_h'] - BAR_H
                track = cell - 8
                out.append(f'<rect x="{cx + 4:g}" y="{top:g}" width="{track:g}" height="{BAR_H}" rx="3" '
                           f'fill="{palette.bar}" fill-opacity="0.5"/>')
                out.append(f'<rect x="{cx + 4:g}" y="{top:g}" width="{track * float(item["weight"]):g}" '
                           f'height="{BAR_H}" rx="3" fill="{palette.accent}"/>')
```

A weight of 0 draws the track alone and a weight of 1 fills it.

- [ ] **Step 2: The band node**

Add after `Bars`:

```python
class Band(Node):
    kind = 'band'
    fields = frozenset({'kind', 'id', 'low', 'high', 'unit', 'ticks', 'bands', 'caption'})
    summary = 'a number line with shaded spans above it, for a threshold, a budget, or a range'
    field_docs = (('low', 'number', False), ('high', 'number', False), ('unit', '≤8 such as "%"', True),
                  ('ticks', '[2-5 numbers between low and high]', False),
                  ('bands', '[1-3 of {{"from", "to", "label" ≤{bar_label}, "tone"?}}]', False),
                  ('caption', '≤{caption}', True))
    stretches = True
```

Size: width `min(avail, 420)`, height `len(bands) * 16 + 30` plus one line for the caption. Draw: the line at the bottom with a tick mark and its number under each tick, and the unit after the last; each band as a rect of height 12 from `from` to `high`'s fraction of the width, stacked upward in order, with its label inside when it fits and to its right when it does not, in the band's tone fill or the accent at 0.35 opacity. Register the node's box under its id. `texts` returns the labels and the caption. `validate` checks the numbers are numbers, `low < high`, every tick and band edge within the range, and 1 to 3 bands.

- [ ] **Step 3: Author P2**

```python
def p2(scene, paper):
    scene = p1(scene, paper)
    if paper == 'attention':
        seq = next(node for node in nodes(scene['panels'][1]['body']) if node['kind'] == 'sequence')
        seq['items'] = [{'id': 'making', 'text': 'making', 'sub': 'query', 'hot': True},
                        {'text': 'the', 'sub': '0.02', 'weight': 0.02}, {'text': 'process', 'sub': '0.06', 'weight': 0.06},
                        {'text': 'more', 'sub': '0.31', 'weight': 0.31}, {'text': 'difficult', 'sub': '0.47', 'weight': 0.47},
                        {'text': '.', 'sub': '0.04', 'weight': 0.04}]
        scene['panels'][1]['notes'] = ['Head 5 of layer 5: the bar under each key is its weight for the query "making"; values illustrative']
        scene['illustrative'] = True
    else:
        setup = scene['panels'][1]['body']
        setup['children'].append({'kind': 'band', 'low': 0, 'high': 100, 'unit': '% most suspicious', 'ticks': [0, 80, 90, 98, 100],
                                  'bands': [{'from': 98, 'to': 100, 'label': 'audited', 'tone': 'peach'},
                                            {'from': 90, 'to': 98, 'label': 'defer, 10% band'},
                                            {'from': 80, 'to': 98, 'label': 'edit, 20% band', 'tone': 'blue'}],
                                  'caption': 'Where a suspicion score sends the code'})
    return scene
```

`nodes()` is the tree walker the earlier harness had. Adjust the panel index if the saved scene's How panel is not the second.

- [ ] **Step 4: Build and look**

Read both P2 PNGs. The token row shows six bars; the band shows three spans flush with the right end. Check `stats.json`: the density of each P2 page, against the floor of 40.

- [ ] **Step 5: Commit**

`git commit -m "PROTOTYPE: variant P2, a weighted token row and a suspicion band"`.

### Task 4: P3, chips out

**Files:**
- Modify: `tools/overview-prototype/build.py` (`p3`)
- Modify: `papers/figures/render.py` only if the footer needs a second line: the footer wraps already.

- [ ] **Step 1: Author P3**

```python
def p3(scene, paper):
    scene = p2(scene, paper)
    chips = []
    for panel in scene['panels']:
        panel['body'] = without_chips(panel['body'], chips)
    if paper == 'attention':
        result = scene['panels'][-1]['body']
        pipeline = [child for child in result['children'] if child['kind'] != 'group' or 'stat' not in {c['kind'] for c in child['children']}]
        for child in pipeline:
            result['children'].remove(child)
            chips += [node['label'] for node in nodes(child) if node['kind'] == 'card']
    line = 'Also in the paper: ' + ', '.join(dict.fromkeys(chips)) + '.'
    scene['footer'] = scene['footer'] + ' ' + line
    return scene
```

`without_chips(node, chips)` removes every `minor` card from the tree, appends its label to `chips`, drops a group left with no children, and returns the node. If the footer passes 320 characters, put the line in the last panel's `notes` instead and say so in the commit message.

- [ ] **Step 2: Build and look**

Read both P3 PNGs. The AI Control chart takes the full Result panel width. The Attention Result panel holds the stats and the bars alone. Check the density of each P3 page.

- [ ] **Step 3: Commit, then hand over**

`git commit -m "PROTOTYPE: variant P3, chips moved to the footer"`. Then report the four variants' stats for both papers as one table, and the path of `index.html`, and stop. The user picks. The second plan builds the picks on a clean branch from `main`.
