"""One class per Scene node kind: its fields, its card entry, its sizing, and its drawing.

A node object is a view over its Scene dict. Fields come from the dict, and measurements go back
into it, so ``compose`` still annotates the Scene in place and a node can be rebuilt from its
dict at any time with ``Node.of``.
"""
from papers.figures.layout import (ARROW_GAP, BAR_ROW, BODY, CARD_MAX_DETAIL, CARD_PAD_X, CARD_PAD_Y, CHART_HEIGHT, CHART_WIDTH, CHIP,
                                   GAP, GRID_CELL, LINE, REFLOW_FILL, REFLOW_MIN_NODES, ROW_GAP, SEQUENCE_GAP, SUBTITLE, TITLE,
                                   _stretch_limit, chart_ticks, step_text)
from papers.figures.limits import LIMITS, MAX_DEPTH, TONES, _panel_error, _scene_id, _scene_lines
from papers.figures.limits import _text as _check_text
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

    def reflow_narrow(self, inner, measure):
        """Only a group reflows."""

    def justify(self, inner, measure, canvas):
        """Only a row group shares spare width."""

    def endpoints(self):
        """The ids in this subtree that an arrow can join."""
        return set()

    def mark_arrow_gaps(self, edges):
        """Only a group has gaps for arrows to cross."""

    def place(self, x, y, canvas, measure, stretch=None):
        """Set the absolute position; a stretchable leaf grows to the column width and re-wraps."""
        self.x, self.y = x, y
        if stretch is not None and self.stretches:
            wanted = max(self.w, min(stretch, canvas.stretch_max))
            if wanted != self.w:
                self.w = wanted
                self.refit(measure)

    def draw(self, out, boxes, measure, palette):
        """Append this node's SVG to ``out`` and its boxes to ``boxes``.

        Every leaf is an obstacle for arrows and labels; cards and sequence items register under
        their own id, or a synthetic one when they have none.
        """
        raise NotImplementedError

    def hook_text(self):
        """The text a reader sees on this node when it takes a Component hover hook, or None."""
        return None

    def texts(self):
        """Every string a reader can see on this node, for coverage and density checks."""
        return []

    def validate(self, path, depth, errors, ids, count, recurse):
        """This kind's own rules. The common rules (kind, unsupported fields, tone, counts) stay in the schema."""


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
        if self.spec.get('hook'):
            out.append(f'<g data-node="{esc(self.spec["hook"])}">')
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
        if self.spec.get('hook'):
            out.append('</g>')

    def validate(self, path, depth, errors, ids, count, recurse):
        _check_text(self.spec, 'label', path, errors, maximum=LIMITS['label'])
        if 'detail' in self.spec:
            _check_text(self.spec, 'detail', path, errors, maximum=LIMITS['detail'])
        _scene_id(self.spec, path, ids, errors)

    hook_prefix = 'n'

    def hook_text(self):
        return ' '.join(part for part in (str(self.spec['label']), str(self.spec.get('detail', ''))) if part)

    def endpoints(self):
        return {self.spec['id']} if self.spec.get('id') else set()

    def texts(self):
        return [self.spec['label'], self.spec.get('detail', '')]


class Note(Node):
    kind = 'note'
    fields = frozenset({'kind', 'lines'})
    summary = 'a small text block; the first line is bold'
    field_docs = (('lines', '[1-4 strings ≤{note_line}]', False),)
    stretches = True

    def prime_texts(self):
        return [str(self.spec['lines'][0])], [str(line) for line in self.spec['lines']]

    def size(self, avail, measure):
        lines = [str(line) for line in self.spec['lines']]
        wanted = max(measure.width(line, BODY, 700 if index == 0 else None) for index, line in enumerate(lines))
        self.w = min(wanted + 2 * CARD_PAD_X + 4, avail)
        self.refit(measure)

    def refit(self, measure):
        lines = [str(line) for line in self.spec['lines']]
        self.spec['wrapped'] = [wrapped for index, line in enumerate(lines)
                                for wrapped in measure.wrap(line, self.w - 2 * CARD_PAD_X - 4, BODY,
                                                            700 if index == 0 else None)]
        self.h = len(self.spec['wrapped']) * LINE[BODY] + 2 * CARD_PAD_Y + 4

    def draw(self, out, boxes, measure, palette):
        x, y, w, h = self.x, self.y, self.w, self.h
        boxes['#' + str(len(boxes))] = (x, y, w, h)
        out.append(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="8" fill="{palette.card}" stroke="{palette.hairline}"/>')
        self.spec['wrapped'] = [wrapped for index, line in enumerate(self.spec['lines'])
                                for wrapped in measure.wrap(str(line), w - 2 * CARD_PAD_X - 4, BODY, 700 if index == 0 else None)]
        for index, line in enumerate(self.spec['wrapped']):
            out.append(_text(x + CARD_PAD_X + 2, y + CARD_PAD_Y + 15 + index * LINE[BODY], line,
                             weight=700 if index == 0 else None, fill=palette.text if index == 0 else palette.muted))

    def validate(self, path, depth, errors, ids, count, recurse):
        _scene_lines(self.spec.get('lines'), path + '.lines', errors, maximum=4, length=LIMITS['note_line'])

    def texts(self):
        return list(self.spec['lines'])


class Steps(Node):
    kind = 'steps'
    fields = frozenset({'kind', 'lines'})
    summary = 'a calculation the renderer numbers 1., 2., …; write the lines without numbers; the last line is the result'
    field_docs = (('lines', '[1-6 strings ≤{step}]', False),)
    stretches = True

    def prime_texts(self):
        return [step_text(self.spec['lines'][-1])], [step_text(line) for line in self.spec['lines']]

    def size(self, avail, measure):
        lines = [step_text(line) for line in self.spec['lines']]
        wanted = max(measure.width(line, BODY, 700 if index == len(lines) - 1 else None)
                     for index, line in enumerate(lines))
        # Calculation lines never wrap, so the block keeps its width even when a row cannot hold it.
        self.w = wanted + 40
        self.h = len(lines) * LINE[BODY] + 2 * CARD_PAD_Y

    def draw(self, out, boxes, measure, palette):
        x, y, w, h = self.x, self.y, self.w, self.h
        boxes['#' + str(len(boxes))] = (x, y, w, h)
        out.append(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="6" fill="{palette.sunk}" stroke="{palette.hairline}"/>')
        for index, line in enumerate(self.spec['lines']):
            last = index == len(self.spec['lines']) - 1
            baseline = y + CARD_PAD_Y + 13 + index * LINE[BODY]
            out.append(_text(x + CARD_PAD_X, baseline, f'{index + 1}.', fill=palette.muted))
            out.append(_text(x + CARD_PAD_X + 20, baseline, step_text(line), weight=700 if last else None,
                             fill=palette.accent if last else palette.text))

    def validate(self, path, depth, errors, ids, count, recurse):
        _scene_lines(self.spec.get('lines'), path + '.lines', errors, maximum=6, length=LIMITS['step'])

    def texts(self):
        return list(self.spec['lines'])


class Sequence(Node):
    kind = 'sequence'
    fields = frozenset({'kind', 'items'})
    summary = 'tokens, values, or steps in a row, each with an optional caption under it'
    field_docs = (('items', '[2-8 of {{"id"?, "text" ≤{item}, "sub"? ≤{sub}, "tone"?, "hot"? true}}]', False),)

    def prime_texts(self):
        return ([str(item['text']) for item in self.spec['items']],
                [str(item.get('sub', '')) for item in self.spec['items']])

    def size(self, avail, measure):
        items = self.spec['items']
        cell = max(measure.width(str(item['text']), BODY, 700) for item in items) + 16
        for item in items:
            if item.get('sub'):
                cell = max(cell, measure.width(str(item['sub']), BODY) + 8)
        per_row = max(1, min(len(items), int((avail + SEQUENCE_GAP) // (cell + SEQUENCE_GAP))))
        rows = (len(items) + per_row - 1) // per_row
        row_h = LINE[BODY] + 8 + (LINE[BODY] if any(item.get('sub') for item in items) else 0)
        self.spec['cell'], self.spec['per_row'], self.spec['row_h'] = cell, per_row, row_h
        self.w = min(len(items), per_row) * cell + SEQUENCE_GAP * (min(len(items), per_row) - 1)
        self.h = rows * row_h + (rows - 1) * 8

    def draw(self, out, boxes, measure, palette):
        x, y, w, h = self.x, self.y, self.w, self.h
        cell, cx = self.spec['cell'], x
        row_top = y
        for index, item in enumerate(self.spec['items']):
            if index and index % self.spec['per_row'] == 0:
                cx = x
                row_top += self.spec['row_h'] + 8
            y = row_top
            tone = item.get('tone') or 'plain'
            fill, stroke, colour = palette.tones[tone]
            out.append(f'<rect x="{cx:g}" y="{y:g}" width="{cell:g}" height="{LINE[BODY] + 8}" rx="6" fill="{fill}" stroke="{stroke}"/>')
            out.append(_text(cx + cell / 2, y + 17, item['text'], weight=700, anchor='middle',
                             fill=colour if tone in ACCENT_TONES else palette.text))
            if item.get('sub'):
                out.append(_text(cx + cell / 2, y + LINE[BODY] + 8 + 14, item['sub'], anchor='middle',
                                 fill=palette.accent if item.get('hot') else palette.muted))
            boxes[item.get('id') or '#' + str(len(boxes))] = (cx, y, cell, self.spec['row_h'])
            cx += cell + SEQUENCE_GAP
        y = self.y

    def validate(self, path, depth, errors, ids, count, recurse):
        # Each toned item is a thing to notice, so it counts toward the panel's accents.
        count[1] += sum(1 for item in self.spec.get('items') or [] if isinstance(item, dict)
                        and item.get('tone') in ('blue', 'green', 'peach'))
        items = self.spec.get('items')
        if not isinstance(items, list) or not 2 <= len(items) <= 8:
            _panel_error(errors, path + '.items', 'needs 2 through 8 items')
            return
        for index, item in enumerate(items):
            item_path = f'{path}.items[{index}]'
            if not isinstance(item, dict):
                _panel_error(errors, item_path, 'must be an object')
                continue
            for name in sorted(set(item) - {'id', 'text', 'sub', 'tone', 'hot'}):
                _panel_error(errors, item_path + '.' + name, 'is unsupported')
            _check_text(item, 'text', item_path, errors, maximum=LIMITS['item'])
            if 'sub' in item:
                _check_text(item, 'sub', item_path, errors, maximum=LIMITS['sub'])
            if 'tone' in item and item['tone'] not in TONES:
                _panel_error(errors, item_path + '.tone', 'must be one of ' + ', '.join(TONES))
            _scene_id(item, item_path, ids, errors)

    def endpoints(self):
        return {item['id'] for item in self.spec['items'] if item.get('id')}

    def texts(self):
        return [item['text'] for item in self.spec['items']] + [item.get('sub', '') for item in self.spec['items']]


class Grid(Node):
    kind = 'grid'
    fields = frozenset({'kind', 'rows', 'col_labels', 'row_labels', 'caption'})
    summary = 'a small matrix, at most 6×6; a cell is a number, a string ≤{cell}, "*value" to highlight it, or null when masked'
    field_docs = (('rows', '[[cell]]', False), ('col_labels', '[≤{grid_label} each]', True),
                  ('row_labels', '[≤{grid_label} each]', True), ('caption', '≤{caption}', True))

    def prime_texts(self):
        plain = [str(cell).lstrip('*') for row in self.spec['rows'] for cell in row if cell is not None]
        plain.extend(str(label) for label in self.spec.get('col_labels', []) + self.spec.get('row_labels', []))
        plain.append(str(self.spec.get('caption', '')))
        return [], plain

    def size(self, avail, measure):
        rows = self.spec['rows']
        columns = max(len(row) for row in rows)
        head = LINE[BODY] if self.spec.get('col_labels') else 0
        lead = (max(measure.width(str(label), BODY) for label in self.spec['row_labels']) + 8
                if self.spec.get('row_labels') else 0)
        texts = [str(cell).lstrip('*') for row in rows for cell in row if cell is not None]
        texts += [str(label) for label in self.spec.get('col_labels', [])]
        widest = max((measure.width(text, BODY, 700) for text in texts), default=0.0)
        self.spec['cell'] = max(GRID_CELL, widest + 12)
        self.spec['lead'], self.spec['head'] = lead, head
        self.w = lead + columns * self.spec['cell']
        self.spec['caption_lines'] = measure.wrap(self.spec['caption'], self.w) if self.spec.get('caption') else []
        self.h = head + len(rows) * GRID_CELL + len(self.spec['caption_lines']) * LINE[BODY]

    def draw(self, out, boxes, measure, palette):
        x, y, w, h = self.x, self.y, self.w, self.h
        boxes['#' + str(len(boxes))] = (x, y, w, h)
        lead, head, cell = self.spec['lead'], self.spec['head'], self.spec['cell']
        for column, label in enumerate(self.spec.get('col_labels', [])):
            out.append(_text(x + lead + column * cell + cell / 2, y + 12, label, anchor='middle', fill=palette.muted))
        for row_index, row in enumerate(self.spec['rows']):
            top = y + head + row_index * GRID_CELL
            if self.spec.get('row_labels'):
                out.append(_text(x + lead - 6, top + GRID_CELL / 2 + 5, self.spec['row_labels'][row_index], anchor='end', fill=palette.muted))
            for column, value in enumerate(row):
                masked = value is None
                hot = isinstance(value, str) and value.startswith('*')
                left = x + lead + column * cell
                fill = palette.cell_masked if masked else (palette.cell_hot if hot else palette.page)
                dash = ' stroke-dasharray="3 2"' if masked else ''
                out.append(f'<rect x="{left:g}" y="{top:g}" width="{cell:g}" height="{GRID_CELL}" fill="{fill}" stroke="{palette.hairline}"{dash}/>')
                if not masked:
                    out.append(_text(left + cell / 2, top + GRID_CELL / 2 + 5, str(value).lstrip('*'),
                                     anchor='middle', weight=700 if hot else None))
        for index, line in enumerate(self.spec['caption_lines']):
            out.append(_text(x, y + head + len(self.spec['rows']) * GRID_CELL + 14 + index * LINE[BODY], line, fill=palette.muted))

    def validate(self, path, depth, errors, ids, count, recurse):
        rows = self.spec.get('rows')
        if not isinstance(rows, list) or not 1 <= len(rows) <= 6 or any(
                not isinstance(row, list) or not 1 <= len(row) <= 6 for row in rows):
            _panel_error(errors, path + '.rows', 'needs 1 through 6 rows of 1 through 6 cells')
        else:
            for r, row in enumerate(rows):
                for c, cell in enumerate(row):
                    if cell is not None and not isinstance(cell, (int, float)) and (
                            not isinstance(cell, str) or len(cell.lstrip('*')) > LIMITS['cell']):
                        _panel_error(errors, f'{path}.rows[{r}][{c}]',
                                     f'must be a number, a string of at most {LIMITS["cell"]} characters, or null')
        for name in ('col_labels', 'row_labels'):
            if name in self.spec:
                _scene_lines(self.spec.get(name), path + '.' + name, errors, maximum=6, length=LIMITS['grid_label'])
        if 'caption' in self.spec:
            _check_text(self.spec, 'caption', path, errors, maximum=LIMITS['caption'])

    def texts(self):
        strings = [str(cell).lstrip('*') for row in self.spec['rows'] for cell in row if cell is not None]
        return strings + self.spec.get('col_labels', []) + self.spec.get('row_labels', []) + [self.spec.get('caption', '')]


class Bars(Node):
    kind = 'bars'
    fields = frozenset({'kind', 'items', 'caption'})
    summary = 'a comparison of values'
    field_docs = (('items', '[2-8 of ["label" ≤{bar_label}, number]]', False), ('caption', '≤{caption}', True))

    def prime_texts(self):
        return [], [str(label) for label, _ in self.spec['items']] + [str(self.spec.get('caption', ''))]

    def size(self, avail, measure):
        label_w = max(measure.width(str(label), BODY) for label, _ in self.spec['items'])
        value_w = max(measure.width(f'{float(value):g}', BODY, 700) for _, value in self.spec['items'])
        self.spec['label_w'], self.spec['value_w'] = label_w, value_w
        self.w = max(min(avail, 320), label_w + 8 + 60 + 6 + value_w)
        self.spec['caption_lines'] = measure.wrap(self.spec['caption'], self.w) if self.spec.get('caption') else []
        self.h = len(self.spec['items']) * BAR_ROW + len(self.spec['caption_lines']) * LINE[BODY]

    def draw(self, out, boxes, measure, palette):
        x, y, w, h = self.x, self.y, self.w, self.h
        boxes['#' + str(len(boxes))] = (x, y, w, h)
        items = [(str(label), float(value)) for label, value in self.spec['items']]
        top_value = max(value for _, value in items)
        label_w = self.spec['label_w']
        bar_w = max(60.0, w - label_w - 14 - self.spec['value_w'])
        for index, (label, value) in enumerate(items):
            row_y = y + index * BAR_ROW
            length = bar_w * value / top_value if top_value else 0
            best = value == top_value
            out.append(_text(x, row_y + 15, label, fill=palette.muted))
            out.append(f'<rect x="{x + label_w + 8:g}" y="{row_y + 4:g}" width="{length:g}" height="14" rx="3" '
                       f'fill="{palette.accent if best else palette.bar}"/>')
            out.append(_text(x + label_w + 14 + length, row_y + 15, f'{value:g}', weight=700 if best else None))
        for index, line in enumerate(self.spec['caption_lines']):
            out.append(_text(x, y + len(items) * BAR_ROW + 14 + index * LINE[BODY], line, fill=palette.muted))

    def validate(self, path, depth, errors, ids, count, recurse):
        items = self.spec.get('items')
        if not isinstance(items, list) or not 2 <= len(items) <= 8 or any(
                not isinstance(item, list) or len(item) != 2 or not isinstance(item[0], str)
                or not item[0].strip() or len(item[0]) > LIMITS['bar_label']
                or not isinstance(item[1], (int, float)) or item[1] < 0 for item in items):
            _panel_error(errors, path + '.items', 'needs 2 through 8 [label, number] pairs')
        if 'caption' in self.spec:
            _check_text(self.spec, 'caption', path, errors, maximum=LIMITS['caption'])

    def texts(self):
        return [str(label) for label, _ in self.spec['items']] + [self.spec.get('caption', '')]


class Divider(Node):
    kind = 'divider'
    fields = frozenset({'kind', 'label'})
    summary = 'a dashed line, for a threshold or a boundary'
    field_docs = (('label', '≤{divider}', True),)
    stretches = True

    def prime_texts(self):
        return [], [str(self.spec.get('label', ''))]

    def size(self, avail, measure):
        self.w = avail
        self.h = LINE[BODY] if self.spec.get('label') else 8

    def draw(self, out, boxes, measure, palette):
        x, y, w, h = self.x, self.y, self.w, self.h
        boxes['#' + str(len(boxes))] = (x, y, w, h)
        mid = y + h / 2
        out.append(f'<line x1="{x:g}" y1="{mid:g}" x2="{x + w:g}" y2="{mid:g}" stroke="{palette.text}" stroke-width="1" stroke-dasharray="6 4"/>')
        if self.spec.get('label'):
            out.append(_text(x + 8, mid + 5 + LINE[BODY] / 2, self.spec['label'], weight=700))

    def validate(self, path, depth, errors, ids, count, recurse):
        if 'label' in self.spec:
            _check_text(self.spec, 'label', path, errors, maximum=LIMITS['divider'])

    def texts(self):
        return [self.spec.get('label', '')]


class Chart(Node):
    kind = 'chart'
    fields = frozenset({'kind', 'series', 'x_label', 'y_label', 'caption', 'marks'})
    summary = 'a line or scatter plot of 1 to 4 series; the application draws axes and ticks'
    field_docs = (('series', '[1-4 of {{"label" ≤{series_label}, "points": [2-12 of [x, y]]}}]', False),
                  ('x_label', '≤{axis_label}', True), ('y_label', '≤{axis_label}', True),
                  ('caption', '≤{caption}', True), ('marks', '"line" | "dots"', True))

    def prime_texts(self):
        plain = [str(item['label']) for item in self.spec['series']]
        plain.extend(str(self.spec.get(name, '')) for name in ('x_label', 'y_label', 'caption'))
        plain.extend(chart_ticks(self.spec)[0] + chart_ticks(self.spec)[1])
        return [], plain

    def size(self, avail, measure):
        self.w = min(CHART_WIDTH, avail)
        self.spec['lead'] = max(measure.width(label, BODY) for label in chart_ticks(self.spec)[0]) + 10
        rows = (len(self.spec['series']) + (1 if self.spec.get('caption') else 0) + (1 if self.spec.get('x_label') else 0)
                + (1 if self.spec.get('y_label') else 0))
        self.h = CHART_HEIGHT + LINE[BODY] * rows + 8

    def draw(self, out, boxes, measure, palette):
        x, y, w, h = self.x, self.y, self.w, self.h
        boxes['#' + str(len(boxes))] = (x, y, w, h)
        y_ticks, x_ticks = chart_ticks(self.spec)
        head = LINE[BODY] if self.spec.get('y_label') else 0
        left, bottom = x + self.spec['lead'], y + head + CHART_HEIGHT - 18
        plot_w, plot_h = w - self.spec['lead'], CHART_HEIGHT - 26
        top = bottom - plot_h
        low, high = float(y_ticks[0]), float(y_ticks[-1])
        last = len(y_ticks) - 1
        xs = [point[0] for item in self.spec['series'] for point in item['points']]
        x_low, x_high = min(xs), max(xs)
        x_span = (x_high - x_low) or 1.0
        for index, label in enumerate(y_ticks):
            tick_y = bottom - plot_h * index / last
            out.append(f'<line x1="{left:g}" y1="{tick_y:g}" x2="{left + plot_w:g}" y2="{tick_y:g}" stroke="{palette.hairline}"/>')
            out.append(_text(left - 6, tick_y + 5, label, anchor='end', fill=palette.muted))
        out.append(f'<line x1="{left:g}" y1="{top:g}" x2="{left:g}" y2="{bottom:g}" stroke="{palette.text}"/>')
        out.append(f'<line x1="{left:g}" y1="{bottom:g}" x2="{left + plot_w:g}" y2="{bottom:g}" stroke="{palette.text}"/>')
        out.append(_text(left, bottom + 14, x_ticks[0], fill=palette.muted))
        out.append(_text(left + plot_w, bottom + 14, x_ticks[1], anchor='end', fill=palette.muted))
        colours = [palette.tones['blue'][2], palette.tones['green'][2], palette.tones['peach'][2], palette.muted]
        for index, item in enumerate(self.spec['series']):
            colour = colours[index % len(colours)]
            points = [(left + plot_w * (px - x_low) / x_span, bottom - plot_h * (py - low) / (high - low))
                      for px, py in item['points']]
            if self.spec.get('marks') == 'dots':
                out.extend(f'<circle cx="{cx:g}" cy="{cy:g}" r="3" fill="{colour}"/>' for cx, cy in points)
            else:
                out.append('<polyline class="series" points="' + ' '.join(f'{cx:g},{cy:g}' for cx, cy in points)
                           + f'" fill="none" stroke="{colour}" stroke-width="1.6"/>')
        if self.spec.get('y_label'):
            out.append(_text(x, y + 13, self.spec['y_label'], fill=palette.muted))
        row_y = y + head + CHART_HEIGHT
        if self.spec.get('x_label'):
            out.append(_text(left + plot_w / 2, row_y + 10, self.spec['x_label'], anchor='middle', fill=palette.muted))
            row_y += LINE[BODY]
        for index, item in enumerate(self.spec['series']):
            colour = colours[index % len(colours)]
            out.append(f'<line x1="{x:g}" y1="{row_y + 9:g}" x2="{x + 14:g}" y2="{row_y + 9:g}" stroke="{colour}" stroke-width="2"/>')
            out.append(_text(x + 20, row_y + 13, item['label']))
            row_y += LINE[BODY]
        if self.spec.get('caption'):
            out.append(_text(x, row_y + 13, self.spec['caption'], fill=palette.muted))

    def validate(self, path, depth, errors, ids, count, recurse):
        series = self.spec.get('series')
        if not isinstance(series, list) or not 1 <= len(series) <= 4:
            _panel_error(errors, path + '.series', 'needs 1 through 4 series')
            return
        for index, item in enumerate(series):
            item_path = f'{path}.series[{index}]'
            if not isinstance(item, dict) or set(item) - {'label', 'points'}:
                _panel_error(errors, item_path, 'must be {"label", "points"}')
                continue
            _check_text(item, 'label', item_path, errors, maximum=LIMITS['series_label'])
            points = item.get('points')
            if (not isinstance(points, list) or not 2 <= len(points) <= 12
                    or any(not isinstance(point, list) or len(point) != 2
                           or any(not isinstance(value, (int, float)) or isinstance(value, bool) for value in point)
                           for point in points)):
                _panel_error(errors, item_path + '.points', 'needs 2 through 12 [x, y] number pairs')
        for name in ('x_label', 'y_label'):
            if name in self.spec:
                _check_text(self.spec, name, path, errors, maximum=LIMITS['axis_label'])
        if 'caption' in self.spec:
            _check_text(self.spec, 'caption', path, errors, maximum=LIMITS['caption'])
        if 'marks' in self.spec and self.spec['marks'] not in ('line', 'dots'):
            _panel_error(errors, path + '.marks', 'must be line or dots')

    def texts(self):
        return ([item['label'] for item in self.spec['series']]
                + [self.spec.get('x_label', ''), self.spec.get('y_label', ''), self.spec.get('caption', '')])


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

    def prime_texts(self):
        return ([str(self.spec['heading'])] if self.spec.get('heading') else []), []

    def size(self, avail, measure):
        pad, head = self.pad, self.head
        # Sizing starts from even gaps; justify widens the ones arrows cross.
        self.spec.pop('gaps', None)
        gap = self.spec.get('gap', ROW_GAP if self.spec.get('arrange') == 'row' else GAP)
        inner = avail - 2 * pad
        children = self.children()
        for child in children:
            child.size(inner, measure)
        if self.spec.get('arrange') == 'row':
            total = sum(child.w for child in children) + gap * (len(children) - 1)
            if total > inner:
                # First give each child an equal share so details wrap; only a row that still
                # does not fit becomes a column.
                share = (inner - gap * (len(children) - 1)) / len(children)
                for child in children:
                    child.size(share, measure)
                total = sum(child.w for child in children) + gap * (len(children) - 1)
            if total > inner:
                self.spec['arrange'] = 'column'
                gap = GAP
                for child in children:
                    child.size(inner, measure)
        if self.spec.get('arrange') == 'row':
            self.w = sum(child.w for child in children) + gap * (len(children) - 1) + 2 * pad
            self.h = max(child.h for child in children) + 2 * pad + head
        else:
            self.w = max(child.w for child in children) + 2 * pad
            if self.spec.get('heading'):
                self.w = max(self.w, measure.width(str(self.spec['heading']), BODY, 700) + 2 * pad)
            self.h = sum(child.h for child in children) + gap * (len(children) - 1) + 2 * pad + head
        self.spec['gap'] = gap

    def reflow_narrow(self, inner, measure):
        pad = self.pad

        def unheaded_column(child):
            return child['kind'] == 'group' and child['arrange'] == 'column' and child.get('heading') is None

        if self.spec['arrange'] == 'column' and len(self.spec['children']) > 1 \
                and any(unheaded_column(child) for child in self.spec['children']):
            # An unheaded column group inside a column draws no frame, so its children are this
            # column's children. Flatten each one so the node count and the split see them all.
            self.spec['children'] = [grandchild for child in self.spec['children']
                                     for grandchild in (child['children'] if unheaded_column(child) else [child])]
            self.size(inner, measure)
        if self.spec['arrange'] == 'column' and len(self.spec['children']) >= REFLOW_MIN_NODES \
                and self.w < REFLOW_FILL * inner:
            children = self.spec['children']
            # Split where the two columns end closest to the same height.
            heights = [child['h'] for child in children]
            total = sum(heights)
            best, running = 1, 0.0
            for index in range(1, len(children)):
                running += heights[index - 1]
                if abs(running - (total - running)) < abs(sum(heights[:best]) - (total - sum(heights[:best]))):
                    best = index
            half = best
            self.spec['children'] = [{'kind': 'group', 'arrange': 'column', 'children': children[:half]},
                                     {'kind': 'group', 'arrange': 'column', 'children': children[half:]}]
            self.spec['arrange'] = 'row'
            self.spec['gap'] = ROW_GAP
            self.size(inner, measure)
            if self.spec['arrange'] == 'row':
                return
            # The two columns did not fit side by side; keep the single column.
            self.spec['children'] = children
            self.spec['gap'] = GAP
            self.size(inner, measure)
            return
        changed = False
        for child in self.children():
            # A headed group is a component whose parts the model drew in order, such as a stack
            # its arrows run up through; only the body or an unheaded column splits in two.
            if isinstance(child, Group) and child.spec['arrange'] == 'column' and child.spec.get('heading') is None:
                before = child.spec['arrange'], child.w
                child.reflow_narrow(inner - 2 * pad, measure)
                changed = changed or (child.spec['arrange'], child.w) != before
        if changed:
            self.size(inner, measure)

    def justify(self, inner, measure, canvas):
        """Give a top-level row the panel width: spare width is shared among its children.

        A gap an arrow crosses widens first, to at most ARROW_GAP and with at most half the spare
        width, so a turning arrow keeps a straight run for its arrowhead. Each grown child is
        sized again at its new width, so labels and details re-wrap.
        """
        if self.spec['arrange'] != 'row':
            return
        children = self.children()
        spare = inner - self.w
        if spare <= 0:
            return
        gap = self.spec['gap']
        arrows = self.spec.get('arrow_gaps', [])
        widen = min(ARROW_GAP - gap, spare / 2 / len(arrows)) if arrows else 0
        if widen > 0:
            self.spec['gaps'] = [gap + (widen if index in arrows else 0) for index in range(len(children) - 1)]
            spare -= widen * len(arrows)
        growable = [child for child in children
                    if child.kind in ('card', 'group', 'note', 'steps') and child.w < _stretch_limit(child, canvas)]
        if not growable and widen <= 0:
            return
        # Spare width goes to children in proportion to their natural width, so a two-word card
        # does not balloon while a sentence card wraps.
        natural = sum(child.w for child in growable)
        for child in growable:
            child.spec['justified'] = min(child.w + spare * child.w / natural, _stretch_limit(child, canvas))
            child.size(child.spec['justified'], measure)
            if isinstance(child, Group):
                child.grow(child.spec['justified'], canvas, measure)
        pad, head = self.pad, self.head
        gaps = self.spec.get('gaps', [gap] * (len(children) - 1))
        self.w = sum(child.spec.get('justified', child.w) for child in children) + sum(gaps) + 2 * pad
        self.h = max(child.h for child in children) + 2 * pad + head

    def grow(self, width, canvas, measure):
        """Widen a group into its justified width.

        A column's children stretch into it when they are placed. A row shares the spare width
        among its children the way a top-level row does, so its frame holds no empty band.
        """
        pad = self.pad
        if self.spec['arrange'] == 'row':
            self.justify(width, measure, canvas)
        self.w = max(self.w, width)
        if self.spec['arrange'] == 'column':
            for child in self.children():
                if isinstance(child, Group):
                    child.grow(min(width - 2 * pad, canvas.stretch_max), canvas, measure)

    def place(self, x, y, canvas, measure, stretch=None):
        """Place the group, then its children; a column's children stretch to the column width.

        Every group takes the height of its placed children, so no box is taller than its text.
        """
        super().place(x, y, canvas, measure, stretch)
        pad, head = self.pad, self.head
        gap = self.spec['gap']
        cx, cy = x + pad, y + pad + head
        children = self.children()
        if self.spec['arrange'] == 'row':
            gaps = self.spec.get('gaps', [gap] * (len(children) - 1)) + [gap]
            for child, after in zip(children, gaps):
                child.place(cx, cy, canvas, measure, stretch=child.spec.get('justified'))
                cx += child.w + after
            self.h = max(child.h for child in children) + 2 * pad + head
        else:
            inner = self.w - 2 * pad
            widest = max(child.w for child in children)
            for child in children:
                child.place(cx, cy, canvas, measure, stretch=min(inner, max(widest, canvas.stretch_max)))
                cy += child.h + gap
            self.h = sum(child.h for child in children) + gap * (len(children) - 1) + 2 * pad + head

    def draw(self, out, boxes, measure, palette):
        x, y, w, h = self.x, self.y, self.w, self.h
        if self.spec.get('heading') is not None:
            if self.spec.get('hook'):
                out.append(f'<g data-node="{esc(self.spec["hook"])}">')
            tone = self.spec.get('tone')
            fill, stroke, colour = palette.tones[tone] if tone in ACCENT_TONES else (palette.card, palette.hairline, palette.text)
            out.append(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="10" fill="{fill}" '
                       f'fill-opacity="0.35" stroke="{stroke}" stroke-width="1.2"/>')
            # A container's frame: an arrow label may sit inside or outside it, never across its edge.
            boxes['@' + str(len(boxes))] = (x, y, w, h)
            heading = str(self.spec['heading']) + (' ' + str(self.spec['repeat']) if self.spec.get('repeat') else '')
            out.append(_text(x + GAP, y + 16, heading, weight=700, fill=colour))
            # The heading text: a label never covers it, and an arrow crosses it only when no
            # other path is clear.
            boxes['!' + str(len(boxes))] = (x + GAP, y + 4, measure.width(heading, BODY, 700), LINE[BODY])
            if self.spec.get('hook'):
                out.append('</g>')
        for child in self.children():
            child.draw(out, boxes, measure, palette)

    def validate(self, path, depth, errors, ids, count, recurse):
        if depth > MAX_DEPTH:
            _panel_error(errors, path, f'nests deeper than {MAX_DEPTH} groups')
            return
        if 'heading' in self.spec:
            _check_text(self.spec, 'heading', path, errors, maximum=LIMITS['group_heading'])
        if 'repeat' in self.spec:
            _check_text(self.spec, 'repeat', path, errors, maximum=LIMITS['repeat'])
        if self.spec.get('arrange') not in ('row', 'column'):
            _panel_error(errors, path + '.arrange', 'must be row or column')
        children = self.spec.get('children')
        if not isinstance(children, list) or not 1 <= len(children) <= 8:
            _panel_error(errors, path + '.children', 'needs 1 through 8 nodes')
            return
        for index, child in enumerate(children):
            recurse(child, f'{path}.children[{index}]', depth + 1, ids, count, errors)

    hook_prefix = 'g'

    def hook_text(self):
        return str(self.spec['heading']) if self.spec.get('heading') is not None else None

    def endpoints(self):
        return set().union(*(child.endpoints() for child in self.children()))

    def mark_arrow_gaps(self, edges):
        """Record, for every row in this subtree, which gaps an arrow between two neighbours crosses."""
        children = self.children()
        if self.spec['arrange'] == 'row':
            owners = [child.endpoints() for child in children]
            crossed = set()
            for edge in edges:
                ends = [next((index for index, ids in enumerate(owners) if edge[name] in ids), None) for name in ('from', 'to')]
                if None not in ends and abs(ends[0] - ends[1]) == 1:
                    crossed.add(min(ends))
            self.spec['arrow_gaps'] = sorted(crossed)
        for child in children:
            child.mark_arrow_gaps(edges)

    def texts(self):
        return [self.spec.get('heading', ''), self.spec.get('repeat', '')]


def prime(measure, scene, frame):
    """Measure every string the Scene draws, in batches by size and weight, before layout."""
    bold, plain = [], []

    def walk(node):
        more_bold, more_plain = node.prime_texts()
        bold.extend(more_bold)
        plain.extend(more_plain)
        for child in node.children():
            walk(child)

    for panel in scene['panels']:
        walk(Node.of(panel['body']))
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
