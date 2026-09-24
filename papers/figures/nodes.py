"""One class per Scene node kind: its fields, its card entry, its sizing, and its drawing.

A node object is a view over its Scene dict. Fields come from the dict, and measurements go back
into it, so ``compose`` still annotates the Scene in place and a node can be rebuilt from its
dict at any time with ``Node.of``.
"""
from papers.figures.layout import (BAR_ROW, BODY, CARD_MAX_DETAIL, CARD_PAD_X, CARD_PAD_Y, GRID_CELL, LINE, SEQUENCE_GAP,
                                   step_text)
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

    def texts(self):
        return [str(label) for label, _ in self.spec['items']] + [self.spec.get('caption', '')]
