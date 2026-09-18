"""Lay out an Overview scene tree into one SVG column; the model never authors geometry.

A scene is a title, subtitle, footer, and one to four panels shown stacked or side by side. A
panel holds one node tree of eight kinds: ``card``, ``group``, ``note``, ``sequence``, ``grid``,
``steps``, ``bars``, and ``divider``. Arrows (``edges``) join cards inside one panel and are routed
around the other cards. Text is measured in the renderer's own font, so a card is exactly as wide
as its words, and every size is at or above the 14-unit reading floor.
"""
from __future__ import annotations

import copy
import html
import shutil
import tempfile

from papers.html_figures import SHARED_MARKERS, SVG_NAMESPACE, measure_text_widths, normalize_svg

SCENE_KINDS = ('card', 'group', 'note', 'sequence', 'grid', 'steps', 'bars', 'divider')
WIDTH = 1000
MARGIN = 24
COLUMN = WIDTH - 2 * MARGIN
PANEL_GAP = 16
PANEL_PAD = 14
CHIP_HEIGHT = 26
BODY, CHIP, TITLE, SUBTITLE = 14, 15, 26, 15
LINE = {14: 18, 15: 20, 26: 31}
CARD_PAD_X, CARD_PAD_Y = 10, 7
CARD_MAX_DETAIL = 300
GAP = 14
ROW_GAP = 14
# A card in a column stretches to its siblings' width, but never past this, so a wide row
# elsewhere in the container does not turn its neighbours into empty bars.
COLUMN_STRETCH_MAX = 460
SEQUENCE_GAP = 6
GRID_CELL = 34
BAR_ROW = 22
ARROW_CLEARANCE = 4
NOTES_GAP = 24
TEXT, MUTED, ACCENT, HAIRLINE = '#243b32', '#627168', '#2f6f5e', '#dce1d8'
# fill, stroke, text for each tone. The plain card is white; ``muted`` is the sunk surface.
TONES = {'blue': ('#e1ebf1', '#7f9fb5', '#2b5876'), 'green': ('#dce8cf', '#8aa87a', '#2f5d3a'),
         'peach': ('#f1e3d8', '#c9a08a', '#7a4a2e'), 'muted': ('#f3f6f0', '#dce1d8', TEXT),
         'plain': ('#ffffff', '#c3ccbd', TEXT)}
ACCENT_TONES = ('blue', 'green', 'peach')


class SceneLayoutError(ValueError):
    """A scene that cannot be laid out: an arrow that cannot avoid the cards, or text that cannot fit."""


def esc(value):
    return html.escape(str(value), quote=True)


class Measurer:
    """Measure every string once per size and weight in the renderer's font.

    Measurement pages go to a private temporary directory that ``close`` removes.
    """

    def __init__(self, directory):
        self.directory = tempfile.mkdtemp(prefix='measure-', dir=str(directory))
        self.cache = {}

    def close(self):
        shutil.rmtree(self.directory, ignore_errors=True)

    def width(self, text, size=BODY, weight=None):
        key = (text, size, weight)
        if key not in self.cache:
            self.cache[key] = measure_text_widths(self.directory, [text], font_size=size,
                                                  font_weight=weight)[0]
        return self.cache[key]

    def prime(self, strings, size=BODY, weight=None):
        missing = [text for text in dict.fromkeys(strings) if (text, size, weight) not in self.cache]
        if missing:
            for text, value in zip(missing, measure_text_widths(self.directory, missing, font_size=size,
                                                                font_weight=weight)):
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


def _prime_scene(measure, scene):
    bold, plain = [], []

    def walk(node):
        kind = node.get('kind')
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
            plain.extend(str(line) for line in node['lines'])
            bold.append(str(node['lines'][-1]))
        elif kind == 'bars':
            plain.extend(str(label) for label, _ in node['items'])
            plain.append(str(node.get('caption', '')))
        elif kind == 'divider':
            plain.append(str(node.get('label', '')))

    for panel in scene['panels']:
        walk(panel['body'])
        bold.extend(str(line) for line in panel.get('notes', []))
        plain.extend(str(edge.get('label', '')) for edge in panel.get('edges', []))
    measure.prime([text for text in bold if text] + ['Illustrative example. ', 'Paper-grounded diagram. '], BODY, 700)
    measure.prime([text for text in plain if text] + str(scene['footer']).split() + [' ', 'LOCALXIV · '], BODY)
    measure.prime([word for panel in scene['panels'] for word in str(panel['heading']).split()] + [' '], CHIP, 700)
    measure.prime(str(scene['title']).split() + [' '], TITLE, 700)
    measure.prime(str(scene['subtitle']).split() + [' '], SUBTITLE)
    for panel in scene['panels']:
        measure.prime(' '.join(str(line) for line in panel.get('notes', [])).split() + [' '], BODY, 700)


# --- sizing ------------------------------------------------------------------------------------

def _size(node, avail, measure):
    """Set ``w`` and ``h`` on every node for the width available to it."""
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
            _size(child, inner, measure)
        if node.get('arrange') == 'row':
            total = sum(child['w'] for child in children) + gap * (len(children) - 1)
            if total > inner:
                # First give each child an equal share so details wrap; only a row that still
                # does not fit becomes a column.
                share = (inner - gap * (len(children) - 1)) / len(children)
                for child in children:
                    _size(child, share, measure)
                total = sum(child['w'] for child in children) + gap * (len(children) - 1)
            if total > inner:
                node['arrange'] = 'column'
                gap = GAP
                for child in children:
                    _size(child, inner, measure)
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
        lines = [str(line) for line in node['lines']]
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


# A column body that spans less than this share of its panel, with at least this many nodes,
# is reflowed into two side-by-side columns. The scene keeps its order: first half left.
REFLOW_FILL = 0.55
REFLOW_MIN_NODES = 4


def _reflow_narrow(node, inner, measure):
    if node['kind'] != 'group':
        return
    pad = GAP if node.get('heading') is not None else 0
    if node['arrange'] == 'column' and len(node['children']) > 1 and all(
            child['kind'] == 'group' and child['arrange'] == 'column' and child.get('heading') is None
            for child in node['children']):
        # Unheaded column groups inside a column are one column; flatten them so it can reflow.
        node['children'] = [grandchild for child in node['children'] for grandchild in child['children']]
        _size(node, inner, measure)
    if node['arrange'] == 'column' and len(node['children']) >= REFLOW_MIN_NODES \
            and node['w'] < REFLOW_FILL * inner:
        children = node['children']
        half = (len(children) + 1) // 2
        node['children'] = [{'kind': 'group', 'arrange': 'column', 'children': children[:half]},
                            {'kind': 'group', 'arrange': 'column', 'children': children[half:]}]
        node['arrange'] = 'row'
        node['gap'] = ROW_GAP
        _size(node, inner, measure)
        if node['arrange'] == 'row':
            return
        # The two columns did not fit side by side; keep the single column.
        node['children'] = children
        node['gap'] = GAP
        _size(node, inner, measure)
        return
    changed = False
    for child in node['children']:
        if child['kind'] == 'group' and child['arrange'] == 'column':
            before = child['arrange'], child['w']
            _reflow_narrow(child, inner - 2 * pad, measure)
            changed = changed or (child['arrange'], child['w']) != before
    if changed:
        _size(node, inner, measure)


def _justify(node, inner, measure):
    """Give a top-level row the panel width: spare width is shared among its children.

    Each grown child is sized again at its new width, so labels and details re-wrap.
    """
    if node['kind'] != 'group' or node['arrange'] != 'row':
        return
    children = node['children']
    spare = inner - node['w']
    if spare <= 0:
        return
    growable = [child for child in children
                if child['kind'] in ('card', 'group', 'note', 'steps') and child['w'] < COLUMN_STRETCH_MAX]
    if not growable:
        return
    share = spare / len(growable)
    for child in growable:
        child['justified'] = min(child['w'] + share, COLUMN_STRETCH_MAX)
        _size(child, child['justified'], measure)
        if child['kind'] == 'group':
            _grow_group(child, child['justified'])
    pad = GAP if node.get('heading') is not None else 0
    head = LINE[BODY] + 4 if node.get('heading') is not None else 0
    node['w'] = sum(child.get('justified', child['w']) for child in children) + node['gap'] * (len(children) - 1) + 2 * pad
    node['h'] = max(child['h'] for child in children) + 2 * pad + head


def _grow_group(node, width):
    """Widen a group so its column children can stretch into the justified width."""
    pad = GAP if node.get('heading') is not None else 0
    node['w'] = max(node['w'], width)
    if node['arrange'] == 'column':
        for child in node['children']:
            if child['kind'] == 'group':
                _grow_group(child, min(width - 2 * pad, COLUMN_STRETCH_MAX))


def _place(node, x, y, stretch=None):
    """Set absolute ``x`` and ``y``; column children stretch to the column width."""
    node['x'], node['y'] = x, y
    if stretch is not None and node['kind'] in ('card', 'group', 'note', 'steps', 'divider'):
        node['w'] = max(node['w'], min(stretch, COLUMN_STRETCH_MAX))
    if node['kind'] != 'group':
        return
    pad = GAP if node.get('heading') is not None else 0
    head = LINE[BODY] + 4 if node.get('heading') is not None else 0
    gap = node['gap']
    cx, cy = x + pad, y + pad + head
    if node['arrange'] == 'row':
        for child in node['children']:
            _place(child, cx, cy, stretch=child.get('justified'))
            cx += child['w'] + gap
    else:
        inner = node['w'] - 2 * pad
        widest = max(child['w'] for child in node['children'])
        for child in node['children']:
            _place(child, cx, cy, stretch=min(inner, max(widest, COLUMN_STRETCH_MAX)))
            cy += child['h'] + gap


# --- drawing -----------------------------------------------------------------------------------

def _text(x, y, text, *, size=BODY, weight=None, fill=None, anchor=None):
    attributes = f'x="{x:g}" y="{y:g}" font-size="{size}"'
    if weight:
        attributes += f' font-weight="{weight}"'
    if fill:
        attributes += f' fill="{fill}"'
    if anchor:
        attributes += f' text-anchor="{anchor}"'
    return f'<text {attributes}>{esc(text)}</text>'


def _draw(node, out, boxes, measure):
    kind = node['kind']
    x, y, w, h = node['x'], node['y'], node['w'], node['h']
    if kind not in ('group', 'card', 'sequence'):
        # Every leaf is an obstacle for arrows and labels; cards and sequence items register
        # under their own id below, or a synthetic one when they have none.
        boxes['#' + str(len(boxes))] = (x, y, w, h)
    if kind == 'card':
        tone = node.get('tone') or 'plain'
        fill, stroke, colour = TONES[tone]
        dash = ' stroke-dasharray="5 3"' if node.get('dashed') else ''
        stroke_width = 1.5 if tone in ACCENT_TONES else 1
        out.append(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="7" fill="{fill}" '
                   f'stroke="{stroke}" stroke-width="{stroke_width}"{dash}/>')
        # Wrap at the final width: a stretched card has more room than it was sized for.
        node['label_lines'] = measure.wrap(node['label'], w - 2 * CARD_PAD_X, BODY, None if node.get('plain') else 700)
        if node.get('detail'):
            node['detail_lines'] = measure.wrap(node['detail'], w - 2 * CARD_PAD_X)
        for index, line in enumerate(node['label_lines']):
            out.append(_text(x + CARD_PAD_X, y + CARD_PAD_Y + 13 + index * LINE[BODY], line,
                             weight=None if node.get('plain') else 700,
                             fill=colour if tone in ACCENT_TONES else TEXT))
        offset = len(node['label_lines'])
        for index, line in enumerate(node['detail_lines']):
            out.append(_text(x + CARD_PAD_X, y + CARD_PAD_Y + 13 + (offset + index) * LINE[BODY], line, fill=MUTED))
        boxes[node.get('id') or '#' + str(len(boxes))] = (x, y, w, h)
    elif kind == 'group':
        if node.get('heading') is not None:
            tone = node.get('tone')
            fill, stroke, colour = TONES[tone] if tone in ACCENT_TONES else ('#fbfcfa', HAIRLINE, TEXT)
            out.append(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="10" fill="{fill}" '
                       f'fill-opacity="0.35" stroke="{stroke}" stroke-width="1.2"/>')
            # A container's frame: an arrow label may sit inside or outside it, never across its edge.
            boxes['@' + str(len(boxes))] = (x, y, w, h)
            heading = str(node['heading']) + (' ' + str(node['repeat']) if node.get('repeat') else '')
            out.append(_text(x + GAP, y + 16, heading, weight=700, fill=colour))
        for child in node['children']:
            _draw(child, out, boxes, measure)
    elif kind == 'note':
        out.append(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="8" fill="#fbfcfa" stroke="{HAIRLINE}"/>')
        node['wrapped'] = [wrapped for index, line in enumerate(node['lines'])
                           for wrapped in measure.wrap(str(line), w - 2 * CARD_PAD_X - 4, BODY, 700 if index == 0 else None)]
        for index, line in enumerate(node['wrapped']):
            out.append(_text(x + CARD_PAD_X + 2, y + CARD_PAD_Y + 15 + index * LINE[BODY], line,
                             weight=700 if index == 0 else None, fill=TEXT if index == 0 else MUTED))
    elif kind == 'sequence':
        cell, cx = node['cell'], x
        row_top = y
        for index, item in enumerate(node['items']):
            if index and index % node['per_row'] == 0:
                cx = x
                row_top += node['row_h'] + 8
            y = row_top
            tone = item.get('tone') or 'plain'
            fill, stroke, colour = TONES[tone]
            out.append(f'<rect x="{cx:g}" y="{y:g}" width="{cell:g}" height="{LINE[BODY] + 8}" rx="6" fill="{fill}" stroke="{stroke}"/>')
            out.append(_text(cx + cell / 2, y + 17, item['text'], weight=700, anchor='middle',
                             fill=colour if tone in ACCENT_TONES else TEXT))
            if item.get('sub'):
                out.append(_text(cx + cell / 2, y + LINE[BODY] + 8 + 14, item['sub'], anchor='middle',
                                 fill=ACCENT if item.get('hot') else MUTED))
            boxes[item.get('id') or '#' + str(len(boxes))] = (cx, y, cell, node['row_h'])
            cx += cell + SEQUENCE_GAP
        y = node['y']
    elif kind == 'grid':
        lead, head, cell = node['lead'], node['head'], node['cell']
        for column, label in enumerate(node.get('col_labels', [])):
            out.append(_text(x + lead + column * cell + cell / 2, y + 12, label, anchor='middle', fill=MUTED))
        for row_index, row in enumerate(node['rows']):
            top = y + head + row_index * GRID_CELL
            if node.get('row_labels'):
                out.append(_text(x + lead - 6, top + GRID_CELL / 2 + 5, node['row_labels'][row_index], anchor='end', fill=MUTED))
            for column, value in enumerate(row):
                masked = value is None
                hot = isinstance(value, str) and value.startswith('*')
                left = x + lead + column * cell
                fill = '#eef1ea' if masked else ('#dce8cf' if hot else '#ffffff')
                dash = ' stroke-dasharray="3 2"' if masked else ''
                out.append(f'<rect x="{left:g}" y="{top:g}" width="{cell:g}" height="{GRID_CELL}" fill="{fill}" stroke="{HAIRLINE}"{dash}/>')
                if not masked:
                    out.append(_text(left + cell / 2, top + GRID_CELL / 2 + 5, str(value).lstrip('*'),
                                     anchor='middle', weight=700 if hot else None))
        for index, line in enumerate(node['caption_lines']):
            out.append(_text(x, y + head + len(node['rows']) * GRID_CELL + 14 + index * LINE[BODY], line, fill=MUTED))
    elif kind == 'steps':
        out.append(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="6" fill="#f3f6f0" stroke="{HAIRLINE}"/>')
        for index, line in enumerate(node['lines']):
            last = index == len(node['lines']) - 1
            baseline = y + CARD_PAD_Y + 13 + index * LINE[BODY]
            out.append(_text(x + CARD_PAD_X, baseline, f'{index + 1}.', fill=MUTED))
            out.append(_text(x + CARD_PAD_X + 20, baseline, line, weight=700 if last else None,
                             fill=ACCENT if last else TEXT))
    elif kind == 'bars':
        items = [(str(label), float(value)) for label, value in node['items']]
        top_value = max(value for _, value in items)
        label_w = node['label_w']
        bar_w = max(60.0, w - label_w - 14 - node['value_w'])
        for index, (label, value) in enumerate(items):
            row_y = y + index * BAR_ROW
            length = bar_w * value / top_value if top_value else 0
            best = value == top_value
            out.append(_text(x, row_y + 15, label, fill=MUTED))
            out.append(f'<rect x="{x + label_w + 8:g}" y="{row_y + 4:g}" width="{length:g}" height="14" rx="3" '
                       f'fill="{ACCENT if best else "#c3ccbd"}"/>')
            out.append(_text(x + label_w + 14 + length, row_y + 15, f'{value:g}', weight=700 if best else None))
        for index, line in enumerate(node['caption_lines']):
            out.append(_text(x, y + len(items) * BAR_ROW + 14 + index * LINE[BODY], line, fill=MUTED))
    elif kind == 'divider':
        mid = y + h / 2
        out.append(f'<line x1="{x:g}" y1="{mid:g}" x2="{x + w:g}" y2="{mid:g}" stroke="{TEXT}" stroke-width="1" stroke-dasharray="6 4"/>')
        if node.get('label'):
            out.append(_text(x + 8, mid + 5 + LINE[BODY] / 2, node['label'], weight=700))


# --- arrows ------------------------------------------------------------------------------------

def _segments(points):
    return list(zip(points, points[1:]))


def _crosses(segment, box):
    (x1, y1), (x2, y2) = segment
    left, top, w, h = box
    right, bottom = left + w, top + h
    left -= ARROW_CLEARANCE
    top -= ARROW_CLEARANCE
    right += ARROW_CLEARANCE
    bottom += ARROW_CLEARANCE
    if x1 == x2:
        return left < x1 < right and min(y1, y2) < bottom and max(y1, y2) > top
    if y1 == y2:
        return top < y1 < bottom and min(x1, x2) < right and max(x1, x2) > left
    return True


def _clear(points, obstacles):
    return not any(_crosses(segment, box) for segment in _segments(points) for box in obstacles)


def route(source, target, obstacles):
    """An orthogonal path from the source box to the target box that crosses no other box.

    Candidates in order: straight, a Z through the gap between the boxes, an L, and a detour
    down the side of the source. The first clear candidate wins. ``obstacles`` excludes the two
    endpoints. Raises ``SceneLayoutError`` when nothing is clear.
    """
    sx, sy, sw, sh = source
    tx, ty, tw, th = target
    s_cx, s_cy, t_cx, t_cy = sx + sw / 2, sy + sh / 2, tx + tw / 2, ty + th / 2
    candidates = []
    if sx + sw <= tx:  # target on the right
        x1, x2 = sx + sw, tx
        for fraction in (0.5, 0.3, 0.7, 0.15, 0.85):
            mid = x1 + (x2 - x1) * fraction
            candidates.append([(x1, s_cy), (mid, s_cy), (mid, t_cy), (x2, t_cy)] if abs(s_cy - t_cy) > 1
                              else [(x1, s_cy), (x2, s_cy)])
        for offset in (14, 28, 42, -14, -28, -42):
            side_y = (sy + sh if offset > 0 else sy) + offset
            exit_y = sy + sh if offset > 0 else sy
            # Down (or up) out of the source, along a lane, then in through the target's top or
            # bottom; or along the lane to the gutter before the target and in through its side.
            candidates.append([(s_cx, exit_y), (s_cx, side_y), (t_cx, side_y),
                               (t_cx, ty if side_y < ty else ty + th)])
            candidates.append([(s_cx, exit_y), (s_cx, side_y), (tx - 12, side_y), (tx - 12, t_cy), (tx, t_cy)])
    elif tx + tw <= sx:  # target on the left
        x1, x2 = sx, tx + tw
        for fraction in (0.5, 0.3, 0.7):
            mid = x1 + (x2 - x1) * fraction
            candidates.append([(x1, s_cy), (mid, s_cy), (mid, t_cy), (x2, t_cy)] if abs(s_cy - t_cy) > 1
                              else [(x1, s_cy), (x2, s_cy)])
    if ty + th <= sy:  # target above
        y1, y2 = sy, ty + th
        candidates.append([(s_cx, y1), (s_cx, y2)] if abs(s_cx - t_cx) < 1
                          else [(s_cx, y1), (s_cx, (y1 + y2) / 2), (t_cx, (y1 + y2) / 2), (t_cx, y2)])
        for side in (-14, 14):
            edge_x = (sx if side < 0 else sx + sw) + side
            candidates.append([(sx if side < 0 else sx + sw, s_cy), (edge_x, s_cy), (edge_x, t_cy),
                               (tx if side < 0 else tx + tw, t_cy)])
            candidates.append([(sx if side < 0 else sx + sw, s_cy), (edge_x, s_cy), (edge_x, y2 - 8),
                               (t_cx, y2 - 8), (t_cx, y2)])
    elif sy + sh <= ty:  # target below
        y1, y2 = sy + sh, ty
        candidates.append([(s_cx, y1), (s_cx, y2)] if abs(s_cx - t_cx) < 1
                          else [(s_cx, y1), (s_cx, (y1 + y2) / 2), (t_cx, (y1 + y2) / 2), (t_cx, y2)])
        for side in (-14, 14):
            edge_x = (sx if side < 0 else sx + sw) + side
            candidates.append([(sx if side < 0 else sx + sw, s_cy), (edge_x, s_cy), (edge_x, t_cy),
                               (tx if side < 0 else tx + tw, t_cy)])
    if obstacles:
        # Around everything: a lane just above the topmost box or just below the bottommost.
        above = min(box[1] for box in obstacles + [source, target]) - 12
        below = max(box[1] + box[3] for box in obstacles + [source, target]) + 12
        candidates.append([(s_cx, sy), (s_cx, above), (t_cx, above), (t_cx, ty)])
        candidates.append([(s_cx, sy + sh), (s_cx, below), (t_cx, below), (t_cx, ty + th)])
    for points in candidates:
        if _clear(points, obstacles):
            return points
    raise SceneLayoutError('an arrow cannot reach its target without crossing another card')


def _draw_edge(edge, boxes, out, measure):
    source, target = boxes[edge['from']], boxes[edge['to']]
    frames = [box for key, box in boxes.items() if key.startswith('@')]
    obstacles = [box for key, box in boxes.items() if key not in (edge['from'], edge['to']) and not key.startswith('@')]
    points = route(source, target, obstacles)
    (x2, y2) = points[-1]
    (px, py) = points[-2]
    # Stop short of the target so the arrowhead sits on its border.
    if px == x2:
        y2 += -3 if y2 > py else 3
    else:
        x2 += -3 if x2 > px else 3
    points = points[:-1] + [(x2, y2)]
    path = 'M ' + ' L '.join(f'{x:g} {y:g}' for x, y in points)
    accent = edge.get('accent')
    out.append(f'<path d="{path}" fill="none" stroke="{ACCENT if accent else TEXT}" stroke-width="1.6" '
               f'marker-end="url(#{"arrow-accent" if accent else "arrow"})"/>')
    if edge.get('label'):
        label = str(edge['label'])
        needed = measure.width(label, BODY) + 12
        longest = max(_segments(points), key=lambda seg: abs(seg[1][0] - seg[0][0]) + abs(seg[1][1] - seg[0][1]))
        (ax, ay), (bx, by) = longest
        # A label needs room on its segment: above a long horizontal run, beside a tall vertical
        # one. A short arrow carries no label rather than a label on top of a card.
        label_w = needed - 12
        if ay == by and abs(bx - ax) >= needed:
            box = ((ax + bx) / 2 - label_w / 2, ay - 5 - LINE[BODY] + 4, label_w, LINE[BODY])
            if _label_fits(box, obstacles + [source, target], frames):
                out.append(_text((ax + bx) / 2, ay - 5, label, anchor='middle', fill=MUTED))
        elif ax == bx and abs(by - ay) >= LINE[BODY] + 8:
            box = (ax + 6, (ay + by) / 2 + 5 - LINE[BODY] + 4, label_w, LINE[BODY])
            if _label_fits(box, obstacles + [source, target], frames):
                out.append(_text(ax + 6, (ay + by) / 2 + 5, label, fill=MUTED))
    return points


def _label_fits(box, obstacles, frames):
    """A label overlaps no leaf and crosses no container edge."""
    if any(_overlaps(box, other) for other in obstacles):
        return False
    return all(_inside(box, frame) or not _overlaps(box, frame) for frame in frames)


def _inside(box, frame):
    x, y, w, h = box
    fx, fy, fw, fh = frame
    return x >= fx and y >= fy and x + w <= fx + fw and y + h <= fy + fh


def _overlaps(box, other):
    x, y, w, h = box
    ox, oy, ow, oh = other
    return x < ox + ow and x + w > ox and y < oy + oh and y + h > oy


# --- composition -------------------------------------------------------------------------------

def compose_scene(directory, paper_title, scene, *, with_tree=False):
    """Lay out and draw one scene. Returns the SVG document and the panel frames.

    Panels are stacked when ``scene['layout']`` is ``stack`` and side by side for ``columns``.
    Every arrow is routed around the other cards; a scene whose arrows cannot be routed raises
    ``SceneLayoutError`` so the caller can ask the planner for a simpler arrangement. The scene
    is never modified; ``with_tree`` also returns the laid-out copy with its measurements.
    """
    scene = copy.deepcopy(scene)
    measure = Measurer(directory)
    try:
        _prime_scene(measure, scene)
        svg, placements = _compose(measure, paper_title, scene)
    finally:
        measure.close()
    return (svg, placements, scene) if with_tree else (svg, placements)


def _compose(measure, paper_title, scene):
    out = [SHARED_MARKERS]
    y = MARGIN + 12
    out.append(_text(MARGIN, y, 'LOCALXIV · ' + str(paper_title), fill=MUTED))
    y += 30
    for line in measure.wrap(scene['title'], COLUMN, TITLE, 700):
        out.append(_text(MARGIN, y, line, size=TITLE, weight=700))
        y += LINE[TITLE]
    y += 4
    for line in measure.wrap(scene['subtitle'], COLUMN, SUBTITLE):
        out.append(_text(MARGIN, y, line, size=SUBTITLE))
        y += LINE[SUBTITLE]
    y += 12
    panels = scene['panels']
    per_row = len(panels) if scene.get('layout') == 'columns' else 1
    while True:
        panel_w = (COLUMN - PANEL_GAP * (per_row - 1)) / per_row
        for panel in panels:
            _size(panel['body'], panel_w - 2 * PANEL_PAD, measure)
        if per_row == 1 or all(panel['body']['w'] <= panel_w - 2 * PANEL_PAD for panel in panels):
            break
        # A body that cannot fit its column (a calculation, a wide grid) halves the panels per
        # row: four side by side become two by two, then a single stack.
        per_row = max(1, per_row // 2)
    # Panels flow into the column whose bottom is highest, so a tall panel beside short ones
    # does not leave a hole; reading order is left to right, then down each column.
    bottoms = [y] * per_row
    placements = []
    for number, panel in enumerate(panels, 1):
        column = min(range(per_row), key=lambda index: (round(bottoms[index]), index))
        x = MARGIN + column * (panel_w + PANEL_GAP)
        top = bottoms[column]
        tone = panel.get('tone') or ACCENT_TONES[(number - 1) % 3]
        chip_fill, _, chip_colour = TONES[tone]
        body = panel['body']
        inner = panel_w - 2 * PANEL_PAD
        _reflow_narrow(body, inner, measure)
        _justify(body, inner, measure)
        heading_lines = measure.wrap(panel['heading'], inner - 24, CHIP, 700)
        chip_h = len(heading_lines) * LINE[CHIP] + 6
        panel_y = top
        body_y = panel_y + PANEL_PAD + chip_h + 10
        _place(body, x + PANEL_PAD, body_y)
        notes = [str(line) for line in panel.get('notes', [])]
        note_lines = [wrapped for line in notes for wrapped in measure.wrap(line, inner, BODY, 700)]
        notes_h = len(note_lines) * LINE[BODY] + (NOTES_GAP if note_lines else 0)
        panel_h = PANEL_PAD + chip_h + 10 + body['h'] + notes_h + PANEL_PAD
        out.append(f'<rect id="frame-{number}" x="{x:g}" y="{panel_y:g}" width="{panel_w:g}" height="{panel_h:g}" rx="12" '
                   f'fill="#ffffff" stroke="{HAIRLINE}" stroke-width="1.5"/>')
        chip_w = min(max(measure.width(line, CHIP, 700) for line in heading_lines) + 24, inner)
        out.append(f'<rect x="{x + PANEL_PAD:g}" y="{panel_y + PANEL_PAD:g}" width="{chip_w:g}" height="{chip_h}" rx="6" fill="{chip_fill}"/>')
        for index, line in enumerate(heading_lines):
            out.append(_text(x + PANEL_PAD + 12, panel_y + PANEL_PAD + 18 + index * LINE[CHIP], line, size=CHIP, weight=700, fill=chip_colour))
        boxes = {}
        _draw(body, out, boxes, measure)
        for edge in panel.get('edges', []):
            _draw_edge(edge, boxes, out, measure)
        for index, line in enumerate(note_lines):
            out.append(_text(x + PANEL_PAD, body_y + body['h'] + NOTES_GAP + (index + 1) * LINE[BODY] - 4, line,
                             weight=700, fill=MUTED))
        placements.append({'id': panel.get('id', 'panel' + str(number)), 'number': number,
                           'fill': round(body['w'] / inner, 3),
                           'frame': {'x': x, 'y': panel_y, 'width': panel_w, 'height': panel_h}})
        bottoms[column] = panel_y + panel_h + 18
    y = max(bottoms) - 10
    out.append(f'<line x1="{MARGIN}" y1="{y:g}" x2="{MARGIN + COLUMN}" y2="{y:g}" stroke="{HAIRLINE}"/>')
    y += 24
    lead = 'Illustrative example.' if scene.get('illustrative') else 'Paper-grounded diagram.'
    lead_w = measure.width(lead + ' ', BODY, 700)
    first = measure.wrap(scene['footer'], COLUMN - lead_w)
    rest = measure.wrap(' '.join(first[1:]), COLUMN) if len(first) > 1 else []
    out.append(f'<text x="{MARGIN}" y="{y:g}" font-size="{BODY}"><tspan font-weight="700">{esc(lead)}</tspan> {esc(first[0])}</text>')
    y += LINE[BODY] + 2
    for line in rest:
        out.append(_text(MARGIN, y, line))
        y += LINE[BODY] + 2
    height = int(y + MARGIN - 8)
    document = (f'<svg xmlns="{SVG_NAMESPACE}" viewBox="0 0 {WIDTH} {height}" font-family="Arial, sans-serif" '
                f'font-size="{BODY}" fill="{TEXT}">' + ''.join(out) + '</svg>')
    return normalize_svg(document, profile='overview'), placements


def _walk(node):
    yield node
    if node['kind'] == 'group':
        for child in node['children']:
            yield from _walk(child)


def scene_headings(scene):
    """Every panel heading and group heading in the scene, for the containment coverage check."""
    headings = [str(panel['heading']) for panel in scene['panels']]
    headings += [str(node['heading']) for panel in scene['panels'] for node in _walk(panel['body'])
                 if node['kind'] == 'group' and node.get('heading')]
    return headings


def scene_text(scene):
    """Every string a reader can see in the scene, for coverage and density checks."""
    strings = [scene['title'], scene['subtitle'], scene['footer']]
    for panel in scene['panels']:
        strings.append(panel['heading'])
        strings.extend(panel.get('notes', []))
        strings.extend(edge.get('label', '') for edge in panel.get('edges', []))
        for node in _walk(panel['body']):
            kind = node['kind']
            if kind == 'card':
                strings += [node['label'], node.get('detail', '')]
            elif kind == 'group':
                strings += [node.get('heading', ''), node.get('repeat', '')]
            elif kind == 'note':
                strings += node['lines']
            elif kind == 'sequence':
                strings += [item['text'] for item in node['items']] + [item.get('sub', '') for item in node['items']]
            elif kind == 'grid':
                strings += [str(cell).lstrip('*') for row in node['rows'] for cell in row if cell is not None]
                strings += node.get('col_labels', []) + node.get('row_labels', []) + [node.get('caption', '')]
            elif kind == 'steps':
                strings += node['lines']
            elif kind == 'bars':
                strings += [str(label) for label, _ in node['items']] + [node.get('caption', '')]
            elif kind == 'divider':
                strings.append(node.get('label', ''))
    return [str(value) for value in strings if str(value).strip()]
