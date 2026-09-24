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
