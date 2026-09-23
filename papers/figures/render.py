"""Draw a laid-out Scene as one SVG document, with the page frame or as a bare panel."""
import base64
import html
import json
import os
import subprocess
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

from papers.figures.palette import ACCENT_TONES, LIGHT
from papers.figures.layout import (BODY, CARD_PAD_X, CARD_PAD_Y, CHART_HEIGHT, CHIP, GAP, GRID_CELL, BAR_ROW,
                                   LINE, NOTES_GAP, PANEL_GAP, PANEL_PAD, SEQUENCE_GAP, SUBTITLE, TITLE,
                                   chart_ticks, justify, place, prime, reflow_narrow, size, step_text)
from papers.figures.route import LayoutError, label_fits, route, segments

__all__ = ['compose', 'rasterize', 'LayoutError', 'markers', 'SVG_NAMESPACE']

SVG_NAMESPACE = 'http://www.w3.org/2000/svg'
def markers(palette):
    marker = ('<marker id="{id}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" '
              'orient="auto-start-reverse"><path d="M 1 2 L 8 5 L 1 8 Z" fill="{fill}"/></marker>')
    return ('<defs>' + marker.format(id='arrow', fill=palette.text) + marker.format(id='arrow-muted', fill=palette.muted)
            + marker.format(id='arrow-accent', fill=palette.accent) + '</defs>')


def page_style(palette):
    return ('*{box-sizing:border-box}html,body{margin:0;padding:0;background:' + palette.page + '}'
            'main{margin:0;padding:0}svg{display:block}')


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


def _draw(node, out, boxes, measure, palette):
    kind = node['kind']
    x, y, w, h = node['x'], node['y'], node['w'], node['h']
    if kind not in ('group', 'card', 'sequence'):
        # Every leaf is an obstacle for arrows and labels; cards and sequence items register
        # under their own id below, or a synthetic one when they have none.
        boxes['#' + str(len(boxes))] = (x, y, w, h)
    if kind == 'card':
        tone = node.get('tone') or 'plain'
        fill, stroke, colour = palette.tones[tone]
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
                             fill=colour if tone in ACCENT_TONES else palette.text))
        offset = len(node['label_lines'])
        for index, line in enumerate(node['detail_lines']):
            out.append(_text(x + CARD_PAD_X, y + CARD_PAD_Y + 13 + (offset + index) * LINE[BODY], line, fill=palette.muted))
        boxes[node.get('id') or '#' + str(len(boxes))] = (x, y, w, h)
    elif kind == 'group':
        if node.get('heading') is not None:
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
        for child in node['children']:
            _draw(child, out, boxes, measure, palette)
    elif kind == 'note':
        out.append(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="8" fill="{palette.card}" stroke="{palette.hairline}"/>')
        node['wrapped'] = [wrapped for index, line in enumerate(node['lines'])
                           for wrapped in measure.wrap(str(line), w - 2 * CARD_PAD_X - 4, BODY, 700 if index == 0 else None)]
        for index, line in enumerate(node['wrapped']):
            out.append(_text(x + CARD_PAD_X + 2, y + CARD_PAD_Y + 15 + index * LINE[BODY], line,
                             weight=700 if index == 0 else None, fill=palette.text if index == 0 else palette.muted))
    elif kind == 'sequence':
        cell, cx = node['cell'], x
        row_top = y
        for index, item in enumerate(node['items']):
            if index and index % node['per_row'] == 0:
                cx = x
                row_top += node['row_h'] + 8
            y = row_top
            tone = item.get('tone') or 'plain'
            fill, stroke, colour = palette.tones[tone]
            out.append(f'<rect x="{cx:g}" y="{y:g}" width="{cell:g}" height="{LINE[BODY] + 8}" rx="6" fill="{fill}" stroke="{stroke}"/>')
            out.append(_text(cx + cell / 2, y + 17, item['text'], weight=700, anchor='middle',
                             fill=colour if tone in ACCENT_TONES else palette.text))
            if item.get('sub'):
                out.append(_text(cx + cell / 2, y + LINE[BODY] + 8 + 14, item['sub'], anchor='middle',
                                 fill=palette.accent if item.get('hot') else palette.muted))
            boxes[item.get('id') or '#' + str(len(boxes))] = (cx, y, cell, node['row_h'])
            cx += cell + SEQUENCE_GAP
        y = node['y']
    elif kind == 'grid':
        lead, head, cell = node['lead'], node['head'], node['cell']
        for column, label in enumerate(node.get('col_labels', [])):
            out.append(_text(x + lead + column * cell + cell / 2, y + 12, label, anchor='middle', fill=palette.muted))
        for row_index, row in enumerate(node['rows']):
            top = y + head + row_index * GRID_CELL
            if node.get('row_labels'):
                out.append(_text(x + lead - 6, top + GRID_CELL / 2 + 5, node['row_labels'][row_index], anchor='end', fill=palette.muted))
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
        for index, line in enumerate(node['caption_lines']):
            out.append(_text(x, y + head + len(node['rows']) * GRID_CELL + 14 + index * LINE[BODY], line, fill=palette.muted))
    elif kind == 'steps':
        out.append(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="6" fill="{palette.sunk}" stroke="{palette.hairline}"/>')
        for index, line in enumerate(node['lines']):
            last = index == len(node['lines']) - 1
            baseline = y + CARD_PAD_Y + 13 + index * LINE[BODY]
            out.append(_text(x + CARD_PAD_X, baseline, f'{index + 1}.', fill=palette.muted))
            out.append(_text(x + CARD_PAD_X + 20, baseline, step_text(line), weight=700 if last else None,
                             fill=palette.accent if last else palette.text))
    elif kind == 'bars':
        items = [(str(label), float(value)) for label, value in node['items']]
        top_value = max(value for _, value in items)
        label_w = node['label_w']
        bar_w = max(60.0, w - label_w - 14 - node['value_w'])
        for index, (label, value) in enumerate(items):
            row_y = y + index * BAR_ROW
            length = bar_w * value / top_value if top_value else 0
            best = value == top_value
            out.append(_text(x, row_y + 15, label, fill=palette.muted))
            out.append(f'<rect x="{x + label_w + 8:g}" y="{row_y + 4:g}" width="{length:g}" height="14" rx="3" '
                       f'fill="{palette.accent if best else palette.bar}"/>')
            out.append(_text(x + label_w + 14 + length, row_y + 15, f'{value:g}', weight=700 if best else None))
        for index, line in enumerate(node['caption_lines']):
            out.append(_text(x, y + len(items) * BAR_ROW + 14 + index * LINE[BODY], line, fill=palette.muted))
    elif kind == 'divider':
        mid = y + h / 2
        out.append(f'<line x1="{x:g}" y1="{mid:g}" x2="{x + w:g}" y2="{mid:g}" stroke="{palette.text}" stroke-width="1" stroke-dasharray="6 4"/>')
        if node.get('label'):
            out.append(_text(x + 8, mid + 5 + LINE[BODY] / 2, node['label'], weight=700))
    elif kind == 'chart':
        y_ticks, x_ticks = chart_ticks(node)
        head = LINE[BODY] if node.get('y_label') else 0
        left, bottom = x + node['lead'], y + head + CHART_HEIGHT - 18
        plot_w, plot_h = w - node['lead'], CHART_HEIGHT - 26
        top = bottom - plot_h
        low, high = float(y_ticks[0]), float(y_ticks[-1])
        last = len(y_ticks) - 1
        xs = [point[0] for item in node['series'] for point in item['points']]
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
        for index, item in enumerate(node['series']):
            colour = colours[index % len(colours)]
            points = [(left + plot_w * (px - x_low) / x_span, bottom - plot_h * (py - low) / (high - low))
                      for px, py in item['points']]
            if node.get('marks') == 'dots':
                out.extend(f'<circle cx="{cx:g}" cy="{cy:g}" r="3" fill="{colour}"/>' for cx, cy in points)
            else:
                out.append('<polyline class="series" points="' + ' '.join(f'{cx:g},{cy:g}' for cx, cy in points)
                           + f'" fill="none" stroke="{colour}" stroke-width="1.6"/>')
        if node.get('y_label'):
            out.append(_text(x, y + 13, node['y_label'], fill=palette.muted))
        row_y = y + head + CHART_HEIGHT
        if node.get('x_label'):
            out.append(_text(left + plot_w / 2, row_y + 10, node['x_label'], anchor='middle', fill=palette.muted))
            row_y += LINE[BODY]
        for index, item in enumerate(node['series']):
            colour = colours[index % len(colours)]
            out.append(f'<line x1="{x:g}" y1="{row_y + 9:g}" x2="{x + 14:g}" y2="{row_y + 9:g}" stroke="{colour}" stroke-width="2"/>')
            out.append(_text(x + 20, row_y + 13, item['label']))
            row_y += LINE[BODY]
        if node.get('caption'):
            out.append(_text(x, row_y + 13, node['caption'], fill=palette.muted))


def _draw_edge(edge, boxes, out, measure, palette):
    source, target = boxes[edge['from']], boxes[edge['to']]
    frames = [box for key, box in boxes.items() if key.startswith('@')]
    obstacles = [box for key, box in boxes.items() if key not in (edge['from'], edge['to']) and not key.startswith('@')]
    points = route(source, target, obstacles, frames)
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
    out.append(f'<path d="{path}" fill="none" stroke="{palette.accent if accent else palette.text}" stroke-width="1.6" '
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
                out.append(_text((ax + bx) / 2, ay - 5, label, anchor='middle', fill=palette.muted))
        elif ax == bx and abs(by - ay) >= LINE[BODY] + 8:
            box = (ax + 6, (ay + by) / 2 + 5 - LINE[BODY] + 4, label_w, LINE[BODY])
            if label_fits(box, obstacles + [source, target], frames):
                out.append(_text(ax + 6, (ay + by) / 2 + 5, label, fill=palette.muted))
    return points


def compose(measure, scene, canvas, *, frame='page', page_title='', palette=LIGHT):
    """Lay out and draw one Scene at the canvas width. Returns the SVG and the panel frames.

    Panels are stacked when ``scene['layout']`` is ``stack`` and side by side for ``columns``.
    Every arrow is routed around the other cards; a scene whose arrows cannot be routed raises
    ``LayoutError`` so the caller can ask for a simpler arrangement. The scene tree is annotated in
    place with its measurements; pass a copy to keep the original. ``frame='page'`` draws the
    header line, title, subtitle, and footer; ``frame='panel'`` draws the panels alone.
    """
    prime(measure, scene, frame)
    out = [markers(palette)]
    y = canvas.margin + 12
    if frame == 'page':
        out.append(_text(canvas.margin, y, 'LOCALXIV · ' + str(page_title), fill=palette.muted))
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
        chip_fill, _, chip_colour = palette.tones[tone]
        body = panel['body']
        inner = panel_w - 2 * PANEL_PAD
        reflow_narrow(body, inner, measure)
        justify(body, inner, measure, canvas)
        heading_lines = measure.wrap(panel['heading'], inner - 24, CHIP, 700)
        chip_h = len(heading_lines) * LINE[CHIP] + 6
        panel_y = top
        body_y = panel_y + PANEL_PAD + chip_h + 10
        place(body, x + PANEL_PAD, body_y, canvas, measure)
        notes = [str(line) for line in panel.get('notes', [])]
        note_lines = [wrapped for line in notes for wrapped in measure.wrap(line, inner, BODY, 700)]
        notes_h = len(note_lines) * LINE[BODY] + (NOTES_GAP if note_lines else 0)
        panel_h = PANEL_PAD + chip_h + 10 + body['h'] + notes_h + PANEL_PAD
        out.append(f'<rect id="frame-{number}" x="{x:g}" y="{panel_y:g}" width="{panel_w:g}" height="{panel_h:g}" rx="12" '
                   f'fill="{palette.page}" stroke="{palette.hairline}" stroke-width="1.5"/>')
        chip_w = min(max(measure.width(line, CHIP, 700) for line in heading_lines) + 24, inner)
        out.append(f'<rect x="{x + PANEL_PAD:g}" y="{panel_y + PANEL_PAD:g}" width="{chip_w:g}" height="{chip_h}" rx="6" fill="{chip_fill}"/>')
        for index, line in enumerate(heading_lines):
            out.append(_text(x + PANEL_PAD + 12, panel_y + PANEL_PAD + 18 + index * LINE[CHIP], line, size=CHIP, weight=700, fill=chip_colour))
        boxes = {}
        _draw(body, out, boxes, measure, palette)
        for edge in panel.get('edges', []):
            _draw_edge(edge, boxes, out, measure, palette)
        for index, line in enumerate(note_lines):
            out.append(_text(x + PANEL_PAD, body_y + body['h'] + NOTES_GAP + (index + 1) * LINE[BODY] - 4, line,
                             weight=700, fill=palette.muted))
        placements.append({'id': panel.get('id', 'panel' + str(number)), 'number': number,
                           'fill': round(body['w'] / inner, 3),
                           'frame': {'x': x, 'y': panel_y, 'width': panel_w, 'height': panel_h}})
        bottoms[column] = panel_y + panel_h + 18
    frames = {item['id']: item['frame'] for item in placements}
    for edge in scene.get('edges', []):
        a, b = frames[edge['from']], frames[edge['to']]
        if b['x'] <= a['x']:
            continue  # the panels wrapped onto separate rows; no room for a horizontal arrow
        mid = (max(a['y'], b['y']) + min(a['y'] + a['height'], b['y'] + b['height'])) / 2
        x1, x2 = a['x'] + a['width'], b['x'] - 3
        colour = palette.accent if edge.get('accent') else palette.text
        out.append(f'<path class="panel-edge" d="M {x1:g} {mid:g} L {x2:g} {mid:g}" fill="none" stroke="{colour}" '
                   f'stroke-width="1.6" marker-end="url(#{"arrow-accent" if edge.get("accent") else "arrow"})"/>')
    if frame == 'panel':
        # The last panel's frame ends a margin above the bottom edge.
        y = max(bottoms) - 18
    else:
        y = max(bottoms) - 10
        out.append(f'<line x1="{canvas.margin}" y1="{y:g}" x2="{canvas.margin + canvas.column}" y2="{y:g}" stroke="{palette.hairline}"/>')
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
                f'font-size="{BODY}" fill="{palette.text}">' + ''.join(out) + '</svg>')
    try:
        ET.fromstring(document)
    except ET.ParseError as error:
        raise LayoutError('the composed SVG is not well formed: ' + str(error)) from None
    return document, placements


def rasterize(directory, svg, figure_id, title, dark_svg=None):
    """Write the SVG page, run the native renderer, and return asset paths plus checks."""
    relative = Path('reader/overview-figures') / uuid.uuid4().hex / figure_id
    target = Path(directory) / relative
    target.parent.mkdir(parents=True)
    target.with_suffix('.source.svg').write_text(svg)
    if dark_svg is not None:
        target.with_suffix('.dark.svg').write_text(dark_svg)
    page = ('<!doctype html><html><head><meta charset="utf-8">'
            '<meta name="localxiv-render-mode" content="overview">'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'">'
            '<style>' + page_style(LIGHT) + '</style></head><body><main class="overview-image">' + svg + '</main></body></html>')
    target.with_suffix('.html').write_text(page)
    executable = os.environ.get('LOCALXIV_HTML_RENDERER') or str(Path(__file__).resolve().parent.parent / 'html-snapshot')
    if not Path(executable).is_file():
        raise ValueError('HTML renderer is missing. Build papers/HTMLSnapshot.swift as papers/html-snapshot '
                         '(see development instructions).')
    result = subprocess.run([executable, str(target.with_suffix('.html')), str(target)],
                            capture_output=True, text=True, timeout=300)
    if result.returncode:
        raise ValueError('HTML rendering failed: ' + result.stderr[-1000:])
    checks = json.loads(target.with_suffix('.checks.json').read_text())
    checks.setdefault('issue_details', [])
    png = target.with_suffix('.png').read_bytes()
    if not png.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError('Renderer did not produce a PNG.')
    # Compatibility with existing full-page SVG consumers. The editable source is the .source.svg asset.
    width, height = checks.get('width', 960), checks['height']
    target.with_suffix('.svg').write_text(
        '<svg xmlns="' + SVG_NAMESPACE + '" width="' + str(width) + '" height="' + str(height) + '" viewBox="0 0 '
        + str(width) + ' ' + str(height) + '"><title>' + esc(title) + '</title><image width="' + str(width)
        + '" height="' + str(height) + '" href="data:image/png;base64,' + base64.b64encode(png).decode() + '"/></svg>')
    assets = {extension: str(relative) + '.' + extension for extension in ('html', 'svg', 'png', 'pdf')}
    assets['svg_source'] = str(relative) + '.source.svg'
    if dark_svg is not None:
        assets['svg_dark'] = str(relative) + '.dark.svg'
    return {**assets, 'checks': checks}
