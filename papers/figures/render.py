"""Draw a laid-out Scene as one SVG document, with the page frame or as a bare panel."""
import base64
import json
import os
import subprocess
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

from papers.figures.palette import ACCENT_TONES, LIGHT
from papers.figures.layout import BODY, CHIP, LINE, NOTES_GAP, PANEL_GAP, PANEL_PAD, SUBTITLE, TITLE
from papers.figures.nodes import Node, prime
from papers.figures.route import LayoutError, label_fits, route, segments
from papers.figures.text import _text, esc

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


def _draw_edge(edge, boxes, out, measure, palette):
    source, target = boxes[edge['from']], boxes[edge['to']]
    frames = [box for key, box in boxes.items() if key.startswith('@')]
    headings = [box for key, box in boxes.items() if key.startswith('!')]
    obstacles = [box for key, box in boxes.items() if key not in (edge['from'], edge['to']) and key[0] not in '@!']
    points = route(source, target, obstacles, frames, headings)
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
            if label_fits(box, obstacles + headings + [source, target], frames):
                out.append(_text((ax + bx) / 2, ay - 5, label, anchor='middle', fill=palette.muted))
        elif ax == bx and abs(by - ay) >= LINE[BODY] + 8:
            box = (ax + 6, (ay + by) / 2 + 5 - LINE[BODY] + 4, label_w, LINE[BODY])
            if label_fits(box, obstacles + headings + [source, target], frames):
                out.append(_text(ax + 6, (ay + by) / 2 + 5, label, fill=palette.muted))
    return points


def name_hooks(node, used, number):
    """Name every card and headed group with a hook no other node on the page has, in draw order.

    A card's hook is its Scene id; a card without one gets "n", and a headed group "g", plus the
    count of hooks on the page so far. Scene ids are unique within a panel only, so an id an
    earlier node already holds takes "-" and the panel number. The light and dark passes name the
    same tree, so they agree. Returns each hook with the text a reader sees on its node.
    """
    found = []
    text = node.hook_text()
    if text is not None:
        hook = node.spec.get('id') or node.hook_prefix + str(len(used))
        while hook in used:
            hook += '-' + str(number)
        used.add(hook)
        node.spec['hook'] = hook
        found.append({'node': hook, 'text': text})
    for child in node.children():
        found.extend(name_hooks(child, used, number))
    return found


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
            Node.of(panel['body']).size(panel_w - 2 * PANEL_PAD, measure)
        if per_row == 1 or all(panel['body']['w'] <= panel_w - 2 * PANEL_PAD for panel in panels):
            break
        # A body that cannot fit its column (a calculation, a wide grid) halves the panels per
        # row: four side by side become two by two, then a single stack.
        per_row = max(1, per_row // 2)
    # Panels flow into the column whose bottom is highest, so a tall panel beside short ones
    # does not leave a hole; reading order is left to right, then down each column.
    bottoms = [y] * per_row
    placements = []
    hooked = set()
    for number, panel in enumerate(panels, 1):
        column = min(range(per_row), key=lambda index: (round(bottoms[index]), index))
        x = canvas.margin + column * (panel_w + PANEL_GAP)
        top = bottoms[column]
        tone = panel.get('tone') or ACCENT_TONES[(number - 1) % 3]
        chip_fill, _, chip_colour = palette.tones[tone]
        body = Node.of(panel['body'])
        inner = panel_w - 2 * PANEL_PAD
        body.reflow_narrow(inner, measure)
        body.mark_arrow_gaps(panel.get('edges', []))
        body.justify(inner, measure, canvas)
        heading_lines = measure.wrap(panel['heading'], inner - 24, CHIP, 700)
        chip_h = len(heading_lines) * LINE[CHIP] + 6
        panel_y = top
        body_y = panel_y + PANEL_PAD + chip_h + 10
        body.place(x + PANEL_PAD, body_y, canvas, measure)
        nodes = name_hooks(body, hooked, number)
        notes = [str(line) for line in panel.get('notes', [])]
        note_lines = [wrapped for line in notes for wrapped in measure.wrap(line, inner, BODY, 700)]
        notes_h = len(note_lines) * LINE[BODY] + (NOTES_GAP if note_lines else 0)
        panel_h = PANEL_PAD + chip_h + 10 + body.h + notes_h + PANEL_PAD
        out.append(f'<rect id="frame-{number}" x="{x:g}" y="{panel_y:g}" width="{panel_w:g}" height="{panel_h:g}" rx="12" '
                   f'fill="{palette.page}" stroke="{palette.hairline}" stroke-width="1.5"/>')
        chip_w = min(max(measure.width(line, CHIP, 700) for line in heading_lines) + 24, inner)
        out.append(f'<rect x="{x + PANEL_PAD:g}" y="{panel_y + PANEL_PAD:g}" width="{chip_w:g}" height="{chip_h}" rx="6" fill="{chip_fill}"/>')
        for index, line in enumerate(heading_lines):
            out.append(_text(x + PANEL_PAD + 12, panel_y + PANEL_PAD + 18 + index * LINE[CHIP], line, size=CHIP, weight=700, fill=chip_colour))
        boxes = {}
        body.draw(out, boxes, measure, palette)
        for edge in panel.get('edges', []):
            _draw_edge(edge, boxes, out, measure, palette)
        for index, line in enumerate(note_lines):
            out.append(_text(x + PANEL_PAD, body_y + body.h + NOTES_GAP + (index + 1) * LINE[BODY] - 4, line,
                             weight=700, fill=palette.muted))
        placements.append({'id': panel.get('id', 'panel' + str(number)), 'number': number,
                           'fill': round(body.w / inner, 3),
                           'frame': {'x': x, 'y': panel_y, 'width': panel_w, 'height': panel_h},
                           'nodes': nodes})
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
