"""Draw a laid-out Scene as one SVG document, with the page frame or as a bare panel."""
import html

from papers.figures.layout import (ACCENT, ACCENT_TONES, BODY, CARD_PAD_X, CARD_PAD_Y, CHIP, GAP, GRID_CELL,
                                   BAR_ROW, HAIRLINE, LINE, MUTED, NOTES_GAP, PANEL_GAP, PANEL_PAD,
                                   SEQUENCE_GAP, SUBTITLE, TEXT, TITLE, TONES, justify, place, prime,
                                   reflow_narrow, size)
from papers.figures.route import LayoutError, label_fits, route, segments
from papers.html_figures import SHARED_MARKERS, SVG_NAMESPACE, normalize_svg

__all__ = ['compose', 'LayoutError', 'SHARED_MARKERS', 'SVG_NAMESPACE']


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
        longest = max(segments(points), key=lambda seg: abs(seg[1][0] - seg[0][0]) + abs(seg[1][1] - seg[0][1]))
        (ax, ay), (bx, by) = longest
        # A label needs room on its segment: above a long horizontal run, beside a tall vertical
        # one. A short arrow carries no label rather than a label on top of a card.
        label_w = needed - 12
        if ay == by and abs(bx - ax) >= needed:
            box = ((ax + bx) / 2 - label_w / 2, ay - 5 - LINE[BODY] + 4, label_w, LINE[BODY])
            if label_fits(box, obstacles + [source, target], frames):
                out.append(_text((ax + bx) / 2, ay - 5, label, anchor='middle', fill=MUTED))
        elif ax == bx and abs(by - ay) >= LINE[BODY] + 8:
            box = (ax + 6, (ay + by) / 2 + 5 - LINE[BODY] + 4, label_w, LINE[BODY])
            if label_fits(box, obstacles + [source, target], frames):
                out.append(_text(ax + 6, (ay + by) / 2 + 5, label, fill=MUTED))
    return points


def compose(measure, scene, canvas, *, frame='page', page_title=''):
    """Lay out and draw one Scene at the canvas width. Returns the SVG and the panel frames.

    Panels are stacked when ``scene['layout']`` is ``stack`` and side by side for ``columns``.
    Every arrow is routed around the other cards; a scene whose arrows cannot be routed raises
    ``LayoutError`` so the caller can ask for a simpler arrangement. The scene tree is annotated in
    place with its measurements; pass a copy to keep the original. ``frame='page'`` draws the
    header line, title, subtitle, and footer; ``frame='panel'`` draws the panels alone.
    """
    prime(measure, scene, frame)
    out = [SHARED_MARKERS]
    y = canvas.margin + 12
    if frame == 'page':
        out.append(_text(canvas.margin, y, 'LOCALXIV · ' + str(page_title), fill=MUTED))
        y += 30
        for line in measure.wrap(scene['title'], canvas.column, TITLE, 700):
            out.append(_text(canvas.margin, y, line, size=TITLE, weight=700))
            y += LINE[TITLE]
        y += 4
        for line in measure.wrap(scene['subtitle'], canvas.column, SUBTITLE):
            out.append(_text(canvas.margin, y, line, size=SUBTITLE))
            y += LINE[SUBTITLE]
        y += 12
    panels = scene['panels']
    per_row = len(panels) if scene.get('layout') == 'columns' else 1
    while True:
        panel_w = (canvas.column - PANEL_GAP * (per_row - 1)) / per_row
        for panel in panels:
            size(panel['body'], panel_w - 2 * PANEL_PAD, measure)
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
        x = canvas.margin + column * (panel_w + PANEL_GAP)
        top = bottoms[column]
        tone = panel.get('tone') or ACCENT_TONES[(number - 1) % 3]
        chip_fill, _, chip_colour = TONES[tone]
        body = panel['body']
        inner = panel_w - 2 * PANEL_PAD
        reflow_narrow(body, inner, measure)
        justify(body, inner, measure, canvas)
        heading_lines = measure.wrap(panel['heading'], inner - 24, CHIP, 700)
        chip_h = len(heading_lines) * LINE[CHIP] + 6
        panel_y = top
        body_y = panel_y + PANEL_PAD + chip_h + 10
        place(body, x + PANEL_PAD, body_y, canvas)
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
    if frame == 'panel':
        # The last panel's frame ends a margin above the bottom edge.
        y = max(bottoms) - 18
    else:
        y = max(bottoms) - 10
        out.append(f'<line x1="{canvas.margin}" y1="{y:g}" x2="{canvas.margin + canvas.column}" y2="{y:g}" stroke="{HAIRLINE}"/>')
        y += 24
        lead = 'Illustrative example.' if scene.get('illustrative') else 'Paper-grounded diagram.'
        lead_w = measure.width(lead + ' ', BODY, 700)
        first = measure.wrap(scene['footer'], canvas.column - lead_w)
        rest = measure.wrap(' '.join(first[1:]), canvas.column) if len(first) > 1 else []
        out.append(f'<text x="{canvas.margin}" y="{y:g}" font-size="{BODY}"><tspan font-weight="700">{esc(lead)}</tspan> {esc(first[0])}</text>')
        y += LINE[BODY] + 2
        for line in rest:
            out.append(_text(canvas.margin, y, line))
            y += LINE[BODY] + 2
    height = int(y + canvas.margin - 8)
    document = (f'<svg xmlns="{SVG_NAMESPACE}" viewBox="0 0 {canvas.width} {height}" font-family="Arial, sans-serif" '
                f'font-size="{BODY}" fill="{TEXT}">' + ''.join(out) + '</svg>')
    return normalize_svg(document, profile='overview'), placements
