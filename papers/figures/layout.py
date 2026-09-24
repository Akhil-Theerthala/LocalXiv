"""Sizing, reflow, justification, and placement of a Scene tree at one canvas width."""
import math
import re
from dataclasses import dataclass, field

PANEL_GAP = 16
PANEL_PAD = 14
CHIP_HEIGHT = 26
BODY, CHIP, TITLE, SUBTITLE = 14, 15, 26, 15
LINE = {14: 18, 15: 20, 26: 31}
CARD_PAD_X, CARD_PAD_Y = 10, 7
CARD_MAX_DETAIL = 300
GAP = 14
ROW_GAP = 14
STRETCH_RATIO_MAX = 1.8
SEQUENCE_GAP = 6
GRID_CELL = 34
BAR_ROW = 22
CHART_WIDTH = 300
CHART_HEIGHT = 140
ARROW_CLEARANCE = 4
NOTES_GAP = 24

# The renderer numbers steps itself. A model that numbers them too gets its number removed
# here, not in the schema, so coverage still matches the raw line. "3.5 days" keeps its 3.
STEP_NUMBER = re.compile(r'^\s*\d{1,2}[.)]\s+')


def step_text(line):
    return STEP_NUMBER.sub('', str(line)) or str(line)


@dataclass(frozen=True)
class Canvas:
    """The width a figure lays out at. Text is never scaled, so this is the reader's width."""
    width: int
    margin: int = 24
    column: int = field(init=False)
    # A card in a column stretches to its siblings' width, but never past this, so a wide row
    # elsewhere in the container does not turn its neighbours into empty bars. 460 of 952 on the
    # 1000-unit page; the same share of a narrower canvas.
    stretch_max: int = field(init=False)

    def __post_init__(self):
        object.__setattr__(self, 'column', self.width - 2 * self.margin)
        object.__setattr__(self, 'stretch_max', round(self.column * 460 / 952))


def prime(measure, scene, frame):
    bold, plain = [], []

    def walk(node):
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
        if kind == 'card':
            bold.append(str(node['label']))
            plain.extend(str(node.get('detail', '')).split())
        elif kind == 'group':
            if node.get('heading'):
                bold.append(str(node['heading']))
            for child in node['children']:
                walk(child)
        elif kind == 'note':
            bold.append(str(node['lines'][0]))
            plain.extend(str(line) for line in node['lines'])
        elif kind == 'sequence':
            bold.extend(str(item['text']) for item in node['items'])
            plain.extend(str(item.get('sub', '')) for item in node['items'])
        elif kind == 'grid':
            plain.extend(str(cell).lstrip('*') for row in node['rows'] for cell in row if cell is not None)
            plain.extend(str(label) for label in node.get('col_labels', []) + node.get('row_labels', []))
            plain.append(str(node.get('caption', '')))
        elif kind == 'steps':
            plain.extend(step_text(line) for line in node['lines'])
            bold.append(step_text(node['lines'][-1]))
        elif kind == 'bars':
            plain.extend(str(label) for label, _ in node['items'])
            plain.append(str(node.get('caption', '')))
        elif kind == 'divider':
            plain.append(str(node.get('label', '')))
        elif kind == 'chart':
            plain.extend(str(item['label']) for item in node['series'])
            plain.extend(str(node.get(name, '')) for name in ('x_label', 'y_label', 'caption'))
            plain.extend(chart_ticks(node)[0] + chart_ticks(node)[1])

    for panel in scene['panels']:
        walk(panel['body'])
        bold.extend(str(line) for line in panel.get('notes', []))
        plain.extend(str(edge.get('label', '')) for edge in panel.get('edges', []))
    page = frame == 'page'
    measure.prime([text for text in bold if text] + (['Illustrative example. ', 'Paper-grounded diagram. '] if page else []), BODY, 700)
    measure.prime([text for text in plain if text] + (str(scene['footer']).split() + [' ', 'LOCALXIV · '] if page else [' ']), BODY)
    measure.prime([word for panel in scene['panels'] for word in str(panel['heading']).split()] + [' '], CHIP, 700)
    if page:
        measure.prime(str(scene['title']).split() + [' '], TITLE, 700)
        measure.prime(str(scene['subtitle']).split() + [' '], SUBTITLE)
    for panel in scene['panels']:
        measure.prime(' '.join(str(line) for line in panel.get('notes', [])).split() + [' '], BODY, 700)



# --- sizing ------------------------------------------------------------------------------------

def size(node, avail, measure):
    """Set ``w`` and ``h`` on every node for the width available to it."""
    from papers.figures.nodes import REGISTRY, Node
    if node['kind'] in REGISTRY:
        return Node.of(node).size(avail, measure)
    kind = node['kind']
    if kind == 'card':
        weight = None if node.get('plain') else 700
        label_w = measure.width(str(node['label']), BODY, weight)
        detail_w = measure.width(str(node['detail']), BODY) if node.get('detail') else 0.0
        width = min(max(label_w, min(detail_w, CARD_MAX_DETAIL)) + 2 * CARD_PAD_X, avail)
        words = str(node['label']).split() + str(node.get('detail', '')).split()
        measure.prime(words, BODY, 700)
        longest = max((measure.width(word, BODY, 700) for word in words), default=0.0)
        width = max(width, longest + 2 * CARD_PAD_X)
        node['w'] = width
        node['label_lines'] = measure.wrap(node['label'], width - 2 * CARD_PAD_X, BODY, weight)
        node['detail_lines'] = (measure.wrap(node['detail'], width - 2 * CARD_PAD_X)
                                if node.get('detail') else [])
        node['h'] = (len(node['label_lines']) + len(node['detail_lines'])) * LINE[BODY] + 2 * CARD_PAD_Y
    elif kind == 'group':
        pad = GAP if node.get('heading') is not None else 0
        head = LINE[BODY] + 4 if node.get('heading') is not None else 0
        gap = node.get('gap', ROW_GAP if node.get('arrange') == 'row' else GAP)
        inner = avail - 2 * pad
        children = node['children']
        for child in children:
            size(child, inner, measure)
        if node.get('arrange') == 'row':
            total = sum(child['w'] for child in children) + gap * (len(children) - 1)
            if total > inner:
                # First give each child an equal share so details wrap; only a row that still
                # does not fit becomes a column.
                share = (inner - gap * (len(children) - 1)) / len(children)
                for child in children:
                    size(child, share, measure)
                total = sum(child['w'] for child in children) + gap * (len(children) - 1)
            if total > inner:
                node['arrange'] = 'column'
                gap = GAP
                for child in children:
                    size(child, inner, measure)
        if node.get('arrange') == 'row':
            node['w'] = sum(child['w'] for child in children) + gap * (len(children) - 1) + 2 * pad
            node['h'] = max(child['h'] for child in children) + 2 * pad + head
        else:
            node['w'] = max(child['w'] for child in children) + 2 * pad
            if node.get('heading'):
                node['w'] = max(node['w'], measure.width(str(node['heading']), BODY, 700) + 2 * pad)
            node['h'] = sum(child['h'] for child in children) + gap * (len(children) - 1) + 2 * pad + head
        node['gap'] = gap
    elif kind == 'note':
        lines = [str(line) for line in node['lines']]
        wanted = max(measure.width(line, BODY, 700 if index == 0 else None) for index, line in enumerate(lines))
        node['w'] = min(wanted + 2 * CARD_PAD_X + 4, avail)
        node['wrapped'] = [wrapped for index, line in enumerate(lines)
                           for wrapped in measure.wrap(line, node['w'] - 2 * CARD_PAD_X - 4, BODY,
                                                       700 if index == 0 else None)]
        node['h'] = len(node['wrapped']) * LINE[BODY] + 2 * CARD_PAD_Y + 4
    elif kind == 'sequence':
        items = node['items']
        cell = max(measure.width(str(item['text']), BODY, 700) for item in items) + 16
        for item in items:
            if item.get('sub'):
                cell = max(cell, measure.width(str(item['sub']), BODY) + 8)
        per_row = max(1, min(len(items), int((avail + SEQUENCE_GAP) // (cell + SEQUENCE_GAP))))
        rows = (len(items) + per_row - 1) // per_row
        row_h = LINE[BODY] + 8 + (LINE[BODY] if any(item.get('sub') for item in items) else 0)
        node['cell'], node['per_row'], node['row_h'] = cell, per_row, row_h
        node['w'] = min(len(items), per_row) * cell + SEQUENCE_GAP * (min(len(items), per_row) - 1)
        node['h'] = rows * row_h + (rows - 1) * 8
    elif kind == 'grid':
        rows = node['rows']
        columns = max(len(row) for row in rows)
        head = LINE[BODY] if node.get('col_labels') else 0
        lead = (max(measure.width(str(label), BODY) for label in node['row_labels']) + 8
                if node.get('row_labels') else 0)
        texts = [str(cell).lstrip('*') for row in rows for cell in row if cell is not None]
        texts += [str(label) for label in node.get('col_labels', [])]
        widest = max((measure.width(text, BODY, 700) for text in texts), default=0.0)
        node['cell'] = max(GRID_CELL, widest + 12)
        node['lead'], node['head'] = lead, head
        node['w'] = lead + columns * node['cell']
        node['caption_lines'] = measure.wrap(node['caption'], node['w']) if node.get('caption') else []
        node['h'] = head + len(rows) * GRID_CELL + len(node['caption_lines']) * LINE[BODY]
    elif kind == 'steps':
        lines = [step_text(line) for line in node['lines']]
        wanted = max(measure.width(line, BODY, 700 if index == len(lines) - 1 else None)
                     for index, line in enumerate(lines))
        # Calculation lines never wrap, so the block keeps its width even when a row cannot hold it.
        node['w'] = wanted + 40
        node['h'] = len(lines) * LINE[BODY] + 2 * CARD_PAD_Y
    elif kind == 'bars':
        label_w = max(measure.width(str(label), BODY) for label, _ in node['items'])
        value_w = max(measure.width(f'{float(value):g}', BODY, 700) for _, value in node['items'])
        node['label_w'], node['value_w'] = label_w, value_w
        node['w'] = max(min(avail, 320), label_w + 8 + 60 + 6 + value_w)
        node['caption_lines'] = measure.wrap(node['caption'], node['w']) if node.get('caption') else []
        node['h'] = len(node['items']) * BAR_ROW + len(node['caption_lines']) * LINE[BODY]
    elif kind == 'divider':
        node['w'] = avail
        node['h'] = LINE[BODY] if node.get('label') else 8
    elif kind == 'chart':
        node['w'] = min(CHART_WIDTH, avail)
        node['lead'] = max(measure.width(label, BODY) for label in chart_ticks(node)[0]) + 10
        rows = (len(node['series']) + (1 if node.get('caption') else 0) + (1 if node.get('x_label') else 0)
                + (1 if node.get('y_label') else 0))
        node['h'] = CHART_HEIGHT + LINE[BODY] * rows + 8


def chart_ticks(node):
    """The y tick values at a round step that covers every point, and the x range labels."""
    ys = [point[1] for item in node['series'] for point in item['points']]
    xs = [point[0] for item in node['series'] for point in item['points']]
    low, high = min(ys), max(ys)
    span = (high - low) or abs(high) or 1.0
    raw = span / 3
    magnitude = 10 ** math.floor(math.log10(raw))
    step = next(candidate * magnitude for candidate in (1, 2, 2.5, 5, 10) if candidate * magnitude >= raw)
    first = math.floor(low / step) * step
    count = int(math.ceil((high - first) / step - 1e-9)) + 1
    ticks = [first + index * step for index in range(max(count, 2))]
    return ([f'{round(tick, 10):g}' for tick in ticks], [f'{min(xs):g}', f'{max(xs):g}'])


# A column body that spans less than this share of its panel, with at least this many nodes,
# is reflowed into two side-by-side columns. The scene keeps its order: first half left.
REFLOW_FILL = 0.55
REFLOW_MIN_NODES = 4


def reflow_narrow(node, inner, measure):
    from papers.figures.nodes import Node
    Node.of(node).reflow_narrow(inner, measure)


def justify(node, inner, measure, canvas):
    from papers.figures.nodes import Node
    Node.of(node).justify(inner, measure, canvas)


def _stretch_limit(node, canvas):
    """How wide a node may stretch: a cap on the absolute width and on growth from its natural width."""
    return min(canvas.stretch_max, node.w * STRETCH_RATIO_MAX)


def _grow_group(node, width, canvas):
    from papers.figures.nodes import Node
    Node.of(node).grow(width, canvas)


def refit(node, measure):
    """Wrap a card or note again at its current width and set ``h`` from the result."""
    from papers.figures.nodes import REGISTRY, Node
    if node['kind'] in REGISTRY:
        return Node.of(node).refit(measure)
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


def place(node, x, y, canvas, measure, stretch=None):
    from papers.figures.nodes import Node
    Node.of(node).place(x, y, canvas, measure, stretch)
