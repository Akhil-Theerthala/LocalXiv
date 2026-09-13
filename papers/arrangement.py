"""Deterministic panel measurement and ordered row arrangement for panel-authored Overviews.

Panels are drawn freely at their own canvas size. The arranger normalises their body text to one
shared size and places them in planned order, left to right and then top to bottom. Nothing is
reordered or shrunk to satisfy a page shape: the canvas grows to hold the drawing.
"""
from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET

# Composed geometry, in canvas units.
BODY_SIZE = 18.0        # body text target, the initial implementation default
ROW_GAP = 26.0
COLUMN_GAP = 24.0
NUMBER_BAND = 30.0      # reserved above each panel for its reading-order number
OUTER_MARGIN = 20.0
MAX_COLUMNS = 3


def _tag(element):
    return element.tag.rsplit('}', 1)[-1]


def _number(value, fallback):
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _transform_scale(value):
    """Return the scale magnitude a validated transform applies to child geometry."""
    scale = 1.0
    for name, arguments in re.findall(r'([A-Za-z]+)\s*\(([^)]*)\)', value or ''):
        numbers = [float(item) for item in re.findall(r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?', arguments)]
        if name == 'matrix' and len(numbers) == 6:
            a, b, c, d = numbers[:4]
            scale *= max(math.hypot(a, b), math.hypot(c, d), 1e-6)
        elif name == 'scale' and numbers:
            scale *= max(abs(numbers[0]), abs(numbers[1]) if len(numbers) > 1 else abs(numbers[0]))
    return scale


def viewbox(source):
    """The panel's declared canvas size."""
    root = ET.fromstring(source)
    numbers = re.findall(r'[-+]?(?:\d+\.?\d*|\.\d+)', root.get('viewBox') or '')
    if len(numbers) == 4:
        return float(numbers[2]), float(numbers[3])
    return _number(root.get('width'), 0.0), _number(root.get('height'), 0.0)


def body_size(source):
    """The smallest effective text size in a panel, in its own canvas units."""
    root = ET.fromstring(source)
    smallest = None
    stack = [(root, _number(root.get('font-size'), 24.0), 1.0)]
    while stack:
        element, inherited, scale = stack.pop()
        tag = _tag(element)
        if tag in ('defs', 'marker', 'title', 'desc'):
            continue
        font = _number(element.get('font-size'), inherited) * scale
        if tag in ('text', 'tspan') and ''.join(element.itertext()).strip():
            smallest = font if smallest is None else min(smallest, font)
        stack.extend((child, _number(element.get('font-size'), inherited),
                      scale * _transform_scale(element.get('transform'))) for child in element)
    return smallest or 0.0


def panel_record(identifier, source, *, title=None):
    """The measured record the arranger needs: canvas size and the panel's body text size."""
    width, height = viewbox(source)
    return {'id': identifier, 'title': title or identifier, 'width': width, 'height': height,
            'body_size': body_size(source)}


def _scaled(panels):
    """Normalise every panel's body text to BODY_SIZE with one uniform scale per panel."""
    records = []
    for panel in panels:
        width, height = float(panel['width']), float(panel['height'])
        if width <= 0 or height <= 0:
            raise ValueError('Panel ' + str(panel.get('id')) + ' has no usable canvas size.')
        measured = float(panel.get('body_size') or BODY_SIZE)
        scale = BODY_SIZE / measured if measured > 0 else 1.0
        records.append({'id': panel['id'], 'width': width * scale, 'height': height * scale,
                        'scale': scale})
    return records


def _rows(records, columns):
    return [records[index:index + columns] for index in range(0, len(records), columns)]


def _canvas(rows):
    """The composed canvas a row layout needs, including bands, gaps, and margins."""
    width = max(sum(panel['width'] for panel in row) + COLUMN_GAP * (len(row) - 1) for row in rows)
    height = sum(max(panel['height'] for panel in row) + NUMBER_BAND for row in rows)
    height += ROW_GAP * (len(rows) - 1)
    return {'width': round(width + 2 * OUTER_MARGIN, 3),
            'height': round(height + 2 * OUTER_MARGIN, 3)}


def _unused_area(rows, canvas, panels):
    """Composed area no panel occupies.

    The panel area is fixed for a plan, so ranking candidates by this cost is ranking them by the
    composed canvas they need. A single-panel row wastes nothing sideways, which is why two wide
    panels stack instead of forming a very wide image, while two narrow panels sit side by side.
    """
    used = sum(panel['width'] * panel['height'] for panel in panels)
    return round(canvas['width'] * canvas['height'] - used, 3)


def arrange(panels):
    """Place measured panels in planned order and return the composed canvas.

    ``panels`` is an ordered list of measured records with ``id``, ``width``, ``height`` and
    ``body_size``. One to three columns are compared by unused composed area, then by row count,
    so the least wasteful canvas in the fewest rows wins. Reading order is always the array order.
    """
    panels = list(panels)
    if not panels:
        raise ValueError('An overview needs at least one panel.')
    records = _scaled(panels)
    candidates = []
    for columns in range(1, min(MAX_COLUMNS, len(records)) + 1):
        rows = _rows(records, columns)
        canvas = _canvas(rows)
        candidates.append((_unused_area(rows, canvas, records), len(rows), columns, rows, canvas))
    _, _, columns, rows, canvas = min(candidates, key=lambda item: (item[0], item[1]))
    placements = []
    y = OUTER_MARGIN
    for row in rows:
        row_height = max(panel['height'] for panel in row)
        x = OUTER_MARGIN
        for panel in row:
            placements.append({
                'id': panel['id'], 'x': round(x, 3),
                'y': round(y + NUMBER_BAND + (row_height - panel['height']) / 2, 3),
                'width': round(panel['width'], 3), 'height': round(panel['height'], 3),
                'scale': round(panel['scale'], 6), 'number': len(placements) + 1})
            x += panel['width'] + COLUMN_GAP
        y += row_height + NUMBER_BAND + ROW_GAP
    return {'canvas': canvas, 'placements': placements, 'columns': columns,
            'scales': {panel['id']: round(panel['scale'], 6) for panel in records}}
