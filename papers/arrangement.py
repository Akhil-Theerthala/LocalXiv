"""Deterministic panel fitting and ordered arrangement for panel-authored Overviews.

Panels keep their authored geometry and uniform scale. The arranger uses native visual bounds when
they are available so unused outer canvas space does not become part of a phase card.
"""
from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET

# Composed geometry, in canvas units.
BODY_SIZE = 18.0        # body text target, the initial implementation default
ROW_GAP = 26.0
COLUMN_GAP = 24.0
NUMBER_BAND = 36.0      # reserved above each panel for its reading-order number
PANEL_PADDING = 16.0
OUTER_MARGIN = 20.0
MAX_COLUMNS = 3
MIN_CONTENT_SIZE = 40.0
FIT_PAD = 16.0
FIT_TOLERANCE = 1e-6
FIT_OUTPUT_TOLERANCE = 0.02
FIT_BINARY_STEPS = 36
FIT_MAX_ITERATIONS = 24
SHRINK_STEP = 0.02
SHRINK_MAX_REDUCTION = 0.20
SHRINK_MIN_TEXT_SIZE = 14.0
SHRINK_ROUNDING_MARGIN = 0.02
SHRINK_RESIZE_PENALTY = 0.02
SHRINK_MAX_ITERATIONS = 12


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


def _native_text_size(checks):
    """Return the smallest rendered source-unit text size measured by the native checker."""
    runs = checks.get('text_runs') if isinstance(checks, dict) else None
    if not isinstance(runs, list):
        return 0.0
    sizes = []
    for run in runs:
        if not isinstance(run, dict):
            continue
        size = _finite(run.get('displayed_size_px'))
        if size is not None and size > 0:
            sizes.append(size)
    return min(sizes) if sizes else 0.0


def _content_bounds(checks, width, height):
    """Return native visual bounds in source units, or the whole source canvas.

    The native panel check already accounts for text, transforms, strokes, and arrow markers. A
    missing or malformed check is treated as unknown and keeps the full authored canvas safe.
    """
    elements = checks.get('elements') if isinstance(checks, dict) else None
    if not isinstance(elements, list):
        return 0.0, 0.0, width, height
    bounds = []
    for element in elements:
        if not isinstance(element, dict):
            continue
        try:
            left, top = float(element['left']), float(element['top'])
            right, bottom = float(element['right']), float(element['bottom'])
        except (KeyError, TypeError, ValueError):
            continue
        # WebKit reports a horizontal or vertical line as a zero-height/zero-width box. Keep
        # those finite points in the union: they still mark visible geometry, and the padding
        # around a frame supplies the stroke envelope. Only reversed boxes are unusable.
        if all(math.isfinite(value) for value in (left, top, right, bottom)) and right >= left and bottom >= top:
            bounds.append((left, top, right, bottom))
    if not bounds:
        return 0.0, 0.0, width, height
    left = max(0.0, min(item[0] for item in bounds))
    top = max(0.0, min(item[1] for item in bounds))
    right = min(width, max(item[2] for item in bounds))
    bottom = min(height, max(item[3] for item in bounds))
    if right - left < MIN_CONTENT_SIZE or bottom - top < MIN_CONTENT_SIZE:
        return 0.0, 0.0, width, height
    return left, top, right, bottom


def panel_record(identifier, source, *, title=None, checks=None):
    """The measured record the arranger needs: canvas, text size, and visual bounds."""
    if isinstance(checks, dict) and isinstance(checks.get('checks'), dict):
        checks = checks['checks']
    width, height = viewbox(source)
    bounds = _content_bounds(checks, width, height)
    native_text = _native_text_size(checks)
    return {'id': identifier, 'title': title or identifier, 'width': width, 'height': height,
            'body_size': body_size(source), 'native_min_text_size': native_text,
            'native_text_measured': bool(
                isinstance(checks, dict) and isinstance(checks.get('text_runs'), list)
                and native_text > 0),
            'content_bounds': bounds}


def _scaled(panels):
    """Normalise every panel's body text to BODY_SIZE with one uniform scale per panel."""
    records = []
    for panel in panels:
        width, height = float(panel['width']), float(panel['height'])
        if width <= 0 or height <= 0:
            raise ValueError('Panel ' + str(panel.get('id')) + ' has no usable canvas size.')
        measured = float(panel.get('body_size') or BODY_SIZE)
        scale = BODY_SIZE / measured if measured > 0 else 1.0
        left, top, right, bottom = panel.get('content_bounds') or (0.0, 0.0, width, height)
        left, top = max(0.0, float(left)), max(0.0, float(top))
        right, bottom = min(width, float(right)), min(height, float(bottom))
        if right <= left or bottom <= top:
            left, top, right, bottom = 0.0, 0.0, width, height
        records.append({'id': panel['id'], 'width': (right - left) * scale,
                        'height': (bottom - top) * scale, 'scale': scale,
                        'content_offset': (left * scale, top * scale),
                        'source_width': width, 'source_height': height,
                        'native_min_text_size': float(panel.get('native_min_text_size') or 0.0),
                        'native_text_measured': bool(panel.get('native_text_measured'))})
    return records


def _rows(records):
    """All ordered row breaks with at most three panels per row (at most seven panels)."""
    if not records:
        yield []
        return
    for count in range(1, min(MAX_COLUMNS, len(records)) + 1):
        for remaining in _rows(records[count:]):
            yield [records[:count], *remaining]


def _canvas(rows):
    """The composed canvas a row layout needs, including bands, gaps, and margins."""
    width = max(sum(panel['width'] + 2 * PANEL_PADDING for panel in row)
                + COLUMN_GAP * (len(row) - 1) for row in rows)
    height = sum(max(panel['height'] for panel in row) + NUMBER_BAND + 2 * PANEL_PADDING for row in rows)
    height += ROW_GAP * (len(rows) - 1)
    return {'width': round(width + 2 * OUTER_MARGIN, 3),
            'height': round(height + 2 * OUTER_MARGIN, 3)}


def _layout_cost(canvas):
    """Prefer the smallest canvas; its dimensions follow fitted content."""
    return canvas['width'] * canvas['height']


def arrange(panels):
    """Place measured panels in planned order and return the composed canvas.

    ``panels`` is an ordered list of measured records with ``id``, ``width``, ``height`` and
    ``body_size`` and optional ``content_bounds``. Compare ordered row breaks by compactness. Each
    frame encloses only the fitted panel; drawings retain their uniform type-normalising scale and
    align at the top of their row.
    """
    panels = list(panels)
    if not panels:
        raise ValueError('An overview needs at least one panel.')
    if len(panels) > 7:
        raise ValueError('An overview supports at most seven panels.')
    records = _scaled(panels)
    candidates = []
    for rows in _rows(records):
        canvas = _canvas(rows)
        candidates.append((_layout_cost(canvas), len(rows), rows, canvas))
    _, _, rows, canvas = min(candidates, key=lambda item: (item[0], item[1]))
    placements = []
    y = OUTER_MARGIN
    for row in rows:
        row_height = max(panel['height'] + NUMBER_BAND + 2 * PANEL_PADDING for panel in row)
        row_width = (sum(panel['width'] + 2 * PANEL_PADDING for panel in row)
                     + COLUMN_GAP * (len(row) - 1))
        # Center a compact row inside the widest row's canvas. The card bounds remain the
        # measured content bounds; this only removes the arbitrary left bias from shorter rows.
        x = OUTER_MARGIN + (canvas['width'] - 2 * OUTER_MARGIN - row_width) / 2
        for panel in row:
            frame_width = panel['width'] + 2 * PANEL_PADDING
            frame_height = panel['height'] + NUMBER_BAND + 2 * PANEL_PADDING
            offset_x, offset_y = panel.get('content_offset', (0.0, 0.0))
            placements.append({
                'id': panel['id'],
                # The group origin compensates for the cropped source margin. The visible content
                # starts at frame + padding while preserving every authored coordinate.
                'x': round(x + PANEL_PADDING - offset_x, 3),
                'y': round(y + PANEL_PADDING + NUMBER_BAND - offset_y, 3),
                'width': round(panel['width'], 3), 'height': round(panel['height'], 3),
                'scale': round(panel['scale'], 6), 'number': len(placements) + 1,
                'frame': {'x': round(x, 3), 'y': round(y, 3),
                          'width': round(frame_width, 3), 'height': round(frame_height, 3)}})
            x += frame_width + COLUMN_GAP
        y += row_height + ROW_GAP
    return {'canvas': canvas, 'placements': placements, 'columns': max(map(len, rows)),
            'scales': {panel['id']: round(panel['scale'], 6) for panel in records}}


def _finite(value, fallback=None):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return fallback
    return value if math.isfinite(value) else fallback


def _topological_order(count, edges, coordinates):
    """Return a deterministic DAG order, or ``None`` when an axis has a cycle."""
    outgoing = [[] for _ in range(count)]
    indegree = [0] * count
    for source, target in edges:
        if source == target:
            return None
        outgoing[source].append(target)
        indegree[target] += 1
    ready = [index for index, value in enumerate(indegree) if value == 0]
    ready.sort(key=lambda index: (coordinates[index], index))
    order = []
    while ready:
        source = ready.pop(0)
        order.append(source)
        for target in sorted(outgoing[source], key=lambda index: (coordinates[index], index)):
            indegree[target] -= 1
            if indegree[target] == 0:
                ready.append(target)
                ready.sort(key=lambda index: (coordinates[index], index))
    return order if len(order) == count else None


def _separation_graph(frames, pad_length):
    """Choose stable separating axes for every pair of seed frames.

    A pair whose perpendicular projections overlap is a facing neighbour. All such neighbours
    become constraints. A diagonal pair gets one axis according to its larger centre offset, which
    keeps the seed's directional order without inventing a second constraint.
    """
    horizontal, vertical, relations = [], [], []
    for left_index, first in enumerate(frames):
        for right_index in range(left_index + 1, len(frames)):
            second = frames[right_index]
            first_cx = first['x'] + first['width'] / 2
            second_cx = second['x'] + second['width'] / 2
            first_cy = first['y'] + first['height'] / 2
            second_cy = second['y'] + second['height'] / 2
            vertical_overlap = (min(first['y'] + first['height'], second['y'] + second['height'])
                                - max(first['y'], second['y']) > FIT_TOLERANCE)
            horizontal_overlap = (min(first['x'] + first['width'], second['x'] + second['width'])
                                  - max(first['x'], second['x']) > FIT_TOLERANCE)
            axes = []
            edge_by_axis = {}
            if vertical_overlap:
                edge = ((left_index, right_index) if first_cx <= second_cx
                        else (right_index, left_index))
                horizontal.append(edge)
                axes.append('x')
                edge_by_axis['x'] = edge
            if horizontal_overlap:
                edge = ((left_index, right_index) if first_cy <= second_cy
                        else (right_index, left_index))
                vertical.append(edge)
                axes.append('y')
                edge_by_axis['y'] = edge
            if not axes:
                if abs(second_cx - first_cx) >= abs(second_cy - first_cy):
                    edge = ((left_index, right_index) if first_cx <= second_cx
                            else (right_index, left_index))
                    horizontal.append(edge)
                    axes.append('x')
                    edge_by_axis['x'] = edge
                else:
                    edge = ((left_index, right_index) if first_cy <= second_cy
                            else (right_index, left_index))
                    vertical.append(edge)
                    axes.append('y')
                    edge_by_axis['y'] = edge
            relations.append({'first': left_index, 'second': right_index, 'axes': axes,
                              'edges': edge_by_axis, 'required': pad_length})
    return horizontal, vertical, relations


def _axis_positions(frames, edges, sizes, envelope, outer_margin, pad_length, axis):
    """Place one coordinate by longest paths, then retain seed centres when possible."""
    count = len(frames)
    seed_coordinates = [frame[axis] for frame in frames]
    dimensions = [size[axis] for size in sizes]
    order = _topological_order(count, edges, seed_coordinates)
    if order is None:
        return None, {'axis': axis, 'reason': 'separation graph contains a cycle'}

    predecessors = [[] for _ in range(count)]
    successors = [[] for _ in range(count)]
    for source, target in edges:
        predecessors[target].append(source)
        successors[source].append(target)
    earliest = [outer_margin] * count
    for target in order:
        if predecessors[target]:
            earliest[target] = max(
                [outer_margin]
                + [earliest[source] + dimensions[source] + pad_length
                   for source in predecessors[target]])
    latest = [envelope - outer_margin - dimensions[index] for index in range(count)]
    for source in reversed(order):
        if successors[source]:
            latest[source] = min(
                [latest[source]]
                + [latest[target] - dimensions[source] - pad_length
                   for target in successors[source]])
    impossible = [index for index in range(count)
                  if earliest[index] > latest[index] + FIT_TOLERANCE]
    if impossible:
        return None, {'axis': axis, 'reason': 'required gaps exceed the fitting envelope',
                      'panels': impossible}

    positions = [0.0] * count
    centres = [frame[axis] + frame['width' if axis == 'x' else 'height'] / 2
               for frame in frames]
    for target in order:
        lower = earliest[target]
        if predecessors[target]:
            lower = max(lower, *[positions[source] + dimensions[source] + pad_length
                                  for source in predecessors[target]])
        positions[target] = max(lower, min(centres[target] - dimensions[target] / 2,
                                            latest[target]))
    return positions, None


def _seed_fit_records(panels, initial_layout, outer_margin):
    """Combine source measurements with saved group coordinates for a fitting pass."""
    scaled = _scaled(panels)
    records = {panel['id']: panel for panel in scaled}
    placements = initial_layout.get('placements') if isinstance(initial_layout, dict) else None
    if not isinstance(placements, list):
        raise ValueError('The initial layout has no placements to fit.')
    saved = {placement.get('id'): placement for placement in placements
             if isinstance(placement, dict) and placement.get('id') is not None}
    missing = [panel['id'] for panel in panels if panel['id'] not in saved]
    if missing:
        raise ValueError('The initial layout is missing panels: ' + ', '.join(map(str, missing)))

    frames = []
    for panel in panels:
        identifier = panel['id']
        measured = records[identifier]
        placement = saved[identifier]
        start_scale = _finite(placement.get('scale'), measured['scale'])
        if start_scale is None or start_scale <= 0:
            start_scale = measured['scale']
        left, top, right, bottom = panel.get('content_bounds') or (
            0.0, 0.0, panel['width'], panel['height'])
        left, top = max(0.0, float(left)), max(0.0, float(top))
        right, bottom = min(float(panel['width']), float(right)), min(float(panel['height']), float(bottom))
        if right <= left or bottom <= top:
            left, top, right, bottom = 0.0, 0.0, float(panel['width']), float(panel['height'])
        content_width = (right - left) * start_scale
        content_height = (bottom - top) * start_scale
        frame_width = content_width + 2 * PANEL_PADDING
        frame_height = content_height + NUMBER_BAND + 2 * PANEL_PADDING
        source_frame = placement.get('frame')
        if isinstance(source_frame, dict):
            frame_x = _finite(source_frame.get('x'))
            frame_y = _finite(source_frame.get('y'))
        else:
            placement_x = _finite(placement.get('x'))
            placement_y = _finite(placement.get('y'))
            if placement_x is None or placement_y is None:
                raise ValueError('The initial placement for ' + str(identifier) + ' has no coordinates.')
            frame_x = placement_x + left * start_scale - PANEL_PADDING
            frame_y = placement_y + top * start_scale - NUMBER_BAND - PANEL_PADDING
        if frame_x is None or frame_y is None:
            raise ValueError('The initial frame for ' + str(identifier) + ' has no coordinates.')
        frames.append({'id': identifier, 'x': frame_x, 'y': frame_y,
                       'width': frame_width, 'height': frame_height,
                       'content_width': content_width, 'content_height': content_height,
                       'content_offset': (left * start_scale, top * start_scale),
                       'source_width': float(panel['width']), 'source_height': float(panel['height']),
                       'source_bounds': (left, top, right, bottom), 'scale': start_scale,
                       'native_min_text_size': float(measured.get('native_min_text_size') or 0.0),
                       'native_text_measured': bool(measured.get('native_text_measured')),
                       'title': panel.get('title') or identifier})

    min_x = min(frame['x'] for frame in frames)
    min_y = min(frame['y'] for frame in frames)
    max_x = max(frame['x'] + frame['width'] for frame in frames)
    max_y = max(frame['y'] + frame['height'] for frame in frames)
    shift_x = max(0.0, outer_margin - min_x)
    shift_y = max(0.0, outer_margin - min_y)
    shifted_max_x = max_x + shift_x
    shifted_max_y = max_y + shift_y
    seed_canvas = initial_layout.get('canvas') or {}
    canvas_width = _finite(seed_canvas.get('width'))
    canvas_height = _finite(seed_canvas.get('height'))
    if canvas_width is None or canvas_height is None or canvas_width <= 0 or canvas_height <= 0:
        raise ValueError('The initial layout has no usable canvas.')
    extra_right = max(0.0, shifted_max_x + outer_margin - canvas_width - shift_x)
    extra_bottom = max(0.0, shifted_max_y + outer_margin - canvas_height - shift_y)
    for frame in frames:
        frame['x'] += shift_x
        frame['y'] += shift_y
    envelope = {'width': canvas_width + shift_x + extra_right,
                'height': canvas_height + shift_y + extra_bottom}
    allowance = {'left': round(shift_x, 3), 'top': round(shift_y, 3),
                 'right': round(extra_right, 3), 'bottom': round(extra_bottom, 3)}
    return frames, envelope, allowance


def _placed_frames(seed_frames, positions_x, positions_y, growth):
    frames = []
    for index, seed in enumerate(seed_frames):
        factor = growth[seed['id']]
        frames.append({
            'id': seed['id'], 'x': positions_x[index], 'y': positions_y[index],
            'width': seed['content_width'] * factor + 2 * PANEL_PADDING,
            'height': seed['content_height'] * factor + NUMBER_BAND + 2 * PANEL_PADDING,
            'content_width': seed['content_width'] * factor,
            'content_height': seed['content_height'] * factor,
            'content_offset': (seed['content_offset'][0] * factor,
                               seed['content_offset'][1] * factor),
            'source_bounds': seed['source_bounds'], 'source_width': seed['source_width'],
            'source_height': seed['source_height'], 'scale': seed['scale'] * factor,
            'native_min_text_size': seed.get('native_min_text_size', 0.0),
            'native_text_measured': seed.get('native_text_measured', False),
            'title': seed['title'], 'growth': factor})
    return frames


def _place_fit(seed_frames, horizontal_edges, vertical_edges, growth, envelope,
               outer_margin, pad_length):
    sizes = [{'x': seed['content_width'] * growth[seed['id']] + 2 * PANEL_PADDING,
              'y': seed['content_height'] * growth[seed['id']] + NUMBER_BAND + 2 * PANEL_PADDING}
             for seed in seed_frames]
    positions_x, problem = _axis_positions(seed_frames, horizontal_edges,
                                           sizes, envelope['width'], outer_margin, pad_length, 'x')
    if problem:
        return None, problem
    positions_y, problem = _axis_positions(seed_frames, vertical_edges,
                                           sizes, envelope['height'], outer_margin, pad_length, 'y')
    if problem:
        return None, problem
    return _placed_frames(seed_frames, positions_x, positions_y, growth), None


def _fit_fits(seed_frames, horizontal_edges, vertical_edges, growth, envelope,
              outer_margin, pad_length):
    placed, problem = _place_fit(seed_frames, horizontal_edges, vertical_edges, growth,
                                 envelope, outer_margin, pad_length)
    return placed if problem is None else None


def _common_growth(seed_frames, horizontal_edges, vertical_edges, growth, active, envelope,
                   outer_margin, pad_length):
    """Find the largest monotone factor shared by all currently active panels."""
    if not active:
        return 1.0

    def candidate(factor):
        value = dict(growth)
        for identifier in active:
            value[identifier] *= factor
        return value

    if _fit_fits(seed_frames, horizontal_edges, vertical_edges, candidate(2.0), envelope,
                 outer_margin, pad_length):
        lower, upper = 2.0, 2.0
        for _ in range(24):
            upper *= 2.0
            if not _fit_fits(seed_frames, horizontal_edges, vertical_edges, candidate(upper),
                             envelope, outer_margin, pad_length):
                break
            lower = upper
        else:
            return lower
    else:
        lower, upper = 1.0, 2.0
    for _ in range(FIT_BINARY_STEPS):
        middle = (lower + upper) / 2
        if _fit_fits(seed_frames, horizontal_edges, vertical_edges, candidate(middle), envelope,
                     outer_margin, pad_length):
            lower = middle
        else:
            upper = middle
    return lower


def _frame_placements(frames, outer_margin):
    """Convert fitted frame rectangles into source-preserving panel placements."""
    if not frames:
        return [], {'width': round(2 * outer_margin, 3), 'height': round(2 * outer_margin, 3)}
    min_x = min(frame['x'] for frame in frames)
    min_y = min(frame['y'] for frame in frames)
    shift_x = outer_margin - min_x
    shift_y = outer_margin - min_y
    if shift_x or shift_y:
        frames = [{**frame, 'x': frame['x'] + shift_x, 'y': frame['y'] + shift_y}
                  for frame in frames]
    max_x = max(frame['x'] + frame['width'] for frame in frames)
    max_y = max(frame['y'] + frame['height'] for frame in frames)
    placements = []
    for frame in frames:
        left, top, _, _ = frame['source_bounds']
        scale = frame['scale']
        placements.append({
            'id': frame['id'], 'x': round(frame['x'] + PANEL_PADDING - left * scale, 3),
            'y': round(frame['y'] + PANEL_PADDING + NUMBER_BAND - top * scale, 3),
            'width': round(frame['content_width'], 3), 'height': round(frame['content_height'], 3),
            'scale': round(scale, 6), 'number': len(placements) + 1,
            'frame': {'x': round(frame['x'], 3), 'y': round(frame['y'], 3),
                      'width': round(frame['width'], 3), 'height': round(frame['height'], 3)}})
    return placements, {'width': round(max_x + outer_margin, 3),
                        'height': round(max_y + outer_margin, 3)}


def _gap_report(frames, relations, pad_length):
    by_axis = {'x': 'width', 'y': 'height'}
    report = []
    for relation in relations:
        first, second = relation['first'], relation['second']
        for axis in relation['axes']:
            dimension = by_axis[axis]
            source, destination = relation['edges'][axis]
            source_end = frames[source]['x' if axis == 'x' else 'y'] + frames[source][dimension]
            actual = frames[destination]['x' if axis == 'x' else 'y'] - source_end
            report.append({'first': frames[first]['id'], 'second': frames[second]['id'],
                           'source': frames[source]['id'], 'destination': frames[destination]['id'],
                           'axis': axis, 'required': round(pad_length, 3),
                           'actual': round(actual, 3),
                           'residual': round(actual - pad_length, 3)})
    return report


def _facing_gap_report(frames, pad_length):
    """Measure final left/right and top/bottom gaps for every facing pair."""
    report = []
    for first_index, first in enumerate(frames):
        for second in frames[first_index + 1:]:
            vertical_overlap = (min(first['y'] + first['height'], second['y'] + second['height'])
                                - max(first['y'], second['y']) > FIT_TOLERANCE)
            horizontal_overlap = (min(first['x'] + first['width'], second['x'] + second['width'])
                                  - max(first['x'], second['x']) > FIT_TOLERANCE)
            if vertical_overlap:
                if first['x'] + first['width'] / 2 <= second['x'] + second['width'] / 2:
                    source, destination, direction = first, second, 'right'
                else:
                    source, destination, direction = second, first, 'left'
                actual = destination['x'] - (source['x'] + source['width'])
                report.append({'first': first['id'], 'second': second['id'], 'axis': 'x',
                               'direction': direction, 'required': round(pad_length, 3),
                               'actual': round(actual, 3),
                               'residual': round(actual - pad_length, 3)})
            if horizontal_overlap:
                if first['y'] + first['height'] / 2 <= second['y'] + second['height'] / 2:
                    source, destination, direction = first, second, 'down'
                else:
                    source, destination, direction = second, first, 'up'
                actual = destination['y'] - (source['y'] + source['height'])
                report.append({'first': first['id'], 'second': second['id'], 'axis': 'y',
                               'direction': direction, 'required': round(pad_length, 3),
                               'actual': round(actual, 3),
                               'residual': round(actual - pad_length, 3)})
    return report


def _boundary_report(frames, envelope, outer_margin):
    """Report the four finite-envelope gaps for every fitted frame."""
    report = []
    for frame in frames:
        for axis, dimension, limit in (('x', 'width', envelope['width']),
                                       ('y', 'height', envelope['height'])):
            coordinate = frame[axis]
            report.append({'kind': 'canvas-boundary', 'panel': frame['id'], 'axis': axis, 'side': 'start',
                           'actual': round(coordinate - outer_margin, 3), 'required': 0.0,
                           'residual': round(coordinate - outer_margin, 3)})
            end_gap = limit - outer_margin - coordinate - frame[dimension]
            report.append({'kind': 'canvas-boundary', 'panel': frame['id'], 'axis': axis, 'side': 'end',
                           'actual': round(end_gap, 3), 'required': 0.0,
                           'residual': round(end_gap, 3)})
    return report


def _placement_frames(layout):
    """Read frame rectangles back from a public layout for post-rounding validation."""
    return [dict(placement['frame'], id=placement['id'])
            for placement in layout.get('placements', [])
            if isinstance(placement, dict) and isinstance(placement.get('frame'), dict)]


def _validate_fitted_layout(layout, start_scales, relations, envelope, outer_margin, pad_length):
    """Check public rounded geometry before exposing a fitted result."""
    frames = _placement_frames(layout)
    if len(frames) != len(start_scales):
        return 'fitted layout did not publish one frame per panel'
    canvas = layout.get('canvas') or {}
    for frame in frames:
        if (frame['x'] < outer_margin - FIT_OUTPUT_TOLERANCE
                or frame['y'] < outer_margin - FIT_OUTPUT_TOLERANCE
                or frame['x'] + frame['width'] > canvas['width'] - outer_margin + FIT_OUTPUT_TOLERANCE
                or frame['y'] + frame['height'] > canvas['height'] - outer_margin + FIT_OUTPUT_TOLERANCE):
            return 'fitted frame fell outside its cropped canvas'
    by_id = {frame['id']: frame for frame in frames}
    for relation in relations:
        for axis in relation['axes']:
            source, destination = relation['edges'][axis]
            first, second = by_id[frames[source]['id']], by_id[frames[destination]['id']]
            dimension = 'width' if axis == 'x' else 'height'
            coordinate = 'x' if axis == 'x' else 'y'
            if second[coordinate] - (first[coordinate] + first[dimension]) < pad_length - FIT_OUTPUT_TOLERANCE:
                return 'fitted frame gap fell below the requested pad length'
    for identifier, scale in layout.get('scales', {}).items():
        if scale < start_scales[identifier] - FIT_TOLERANCE:
            return 'fitted panel was shrunk below its seed scale'
    return None


def _invalid_fit_result(initial_layout, base_fit, start_growth, seed_frames, envelope, problem):
    """Attach a diagnostic while retaining an infeasible input byte-for-byte geometrically."""
    seed_area = sum(frame['width'] * frame['height'] for frame in seed_frames)
    base_fit.update({
        'feasible': False, 'diagnostic': {'kind': 'invalid-fit', **problem},
        'growth': dict(start_growth), 'frozen': [frame['id'] for frame in seed_frames],
        'iterations': 0, 'gaps': [], 'gap_violations': [], 'remaining_gap_space': [],
        'boundary_gaps': [], 'binding_constraints': [],
        'remaining_whitespace': {
            'seed_frame_area': round(seed_area, 3), 'final_frame_area': None,
            'envelope_area': round(envelope['width'] * envelope['height'], 3),
        },
    })
    result = dict(initial_layout)
    result['fit'] = base_fit
    return result


def fit_layout(panels, initial_layout, *, pad_length=FIT_PAD, outer_margin=OUTER_MARGIN):
    """Grow uniformly scaled panels into the gaps of a finite seed layout.

    The seed positions choose every separating axis. Longest-path lower and upper bounds keep all
    chosen gaps feasible while target centres retain the seed's visual relationships. Only the
    panel source transform changes; content is never reflowed or rewritten. The returned ``fit``
    block records the envelope, growth decisions, constraints, and any residual diagnostic.
    """
    panels = list(panels)
    if not panels:
        raise ValueError('An overview needs at least one panel.')
    if len(panels) > 7:
        raise ValueError('An overview supports at most seven panels.')
    pad_length = _finite(pad_length)
    outer_margin = _finite(outer_margin)
    if pad_length is None or pad_length < 0 or outer_margin is None or outer_margin < 0:
        raise ValueError('Fitting gaps and margins must be finite and nonnegative.')
    seed_frames, envelope, allowance = _seed_fit_records(panels, initial_layout, outer_margin)
    horizontal_edges, vertical_edges, relations = _separation_graph(seed_frames, pad_length)
    start_growth = {frame['id']: 1.0 for frame in seed_frames}
    initial_frames, initial_problem = _place_fit(seed_frames, horizontal_edges, vertical_edges,
                                                 start_growth, envelope, outer_margin, pad_length)
    start_scales = {frame['id']: frame['scale'] for frame in seed_frames}
    base_fit = {
        'algorithm': 'gap-driven-v1', 'feasible': initial_problem is None,
        'pad_length': round(pad_length, 3), 'outer_margin': round(outer_margin, 3),
        'seed_canvas': dict(initial_layout['canvas']), 'envelope': {
            key: round(value, 3) for key, value in envelope.items()},
        'decoration_allowance': allowance,
        'start_scales': {key: round(value, 9) for key, value in start_scales.items()},
        'horizontal_edges': [[seed_frames[a]['id'], seed_frames[b]['id']]
                             for a, b in horizontal_edges],
        'vertical_edges': [[seed_frames[a]['id'], seed_frames[b]['id']]
                           for a, b in vertical_edges],
        'neighbours': [{'first': seed_frames[item['first']]['id'],
                        'second': seed_frames[item['second']]['id'],
                        'axes': list(item['axes']), 'required': round(pad_length, 3)}
                       for item in relations],
    }

    if initial_problem is not None:
        # Keep an infeasible input untouched. A reconstructed decorated fallback could overlap,
        # so callers must see the original coordinates and the explicit reason for no fit.
        return _invalid_fit_result(initial_layout, base_fit, start_growth, seed_frames,
                                   envelope, initial_problem)

    growth = dict(start_growth)
    active = [frame['id'] for frame in seed_frames]
    iterations = 0
    frozen = []
    while active and iterations < FIT_MAX_ITERATIONS:
        factor = _common_growth(seed_frames, horizontal_edges, vertical_edges, growth, active,
                                envelope, outer_margin, pad_length)
        progressed = factor > 1.0 + FIT_TOLERANCE
        if progressed:
            for identifier in active:
                growth[identifier] *= factor
        next_active = []
        for identifier in active:
            test_growth = dict(growth)
            test_growth[identifier] *= 1.0001
            if _fit_fits(seed_frames, horizontal_edges, vertical_edges, test_growth, envelope,
                         outer_margin, pad_length):
                next_active.append(identifier)
            else:
                frozen.append(identifier)
        iterations += 1
        if not progressed and len(next_active) == len(active):
            break
        if not progressed and not next_active:
            break
        active = next_active

    fitted_frames, final_problem = _place_fit(seed_frames, horizontal_edges, vertical_edges, growth,
                                              envelope, outer_margin, pad_length)
    if final_problem is not None:
        # This is defensive: a monotone placement should remain feasible after each accepted step.
        return _invalid_fit_result(initial_layout, base_fit, start_growth, seed_frames,
                                   envelope, final_problem)
    placements, canvas = _frame_placements(fitted_frames, outer_margin)
    candidate = {'canvas': canvas, 'placements': placements,
                 'columns': initial_layout.get('columns', 1),
                 'scales': {key: round(value, 6) for key, value in
                            ((frame['id'], frame['scale']) for frame in fitted_frames)}}
    validation_problem = _validate_fitted_layout(candidate, start_scales, relations, envelope,
                                                  outer_margin, pad_length)
    if validation_problem:
        return _invalid_fit_result(initial_layout, base_fit, start_growth, seed_frames,
                                   envelope, {'reason': validation_problem})
    gaps = _gap_report(fitted_frames, relations, pad_length)
    facing_gaps = _facing_gap_report(fitted_frames, pad_length)
    boundaries = _boundary_report(fitted_frames, envelope, outer_margin)
    seed_area = sum(frame['width'] * frame['height'] for frame in seed_frames)
    final_area = sum(frame['width'] * frame['height'] for frame in fitted_frames)
    envelope_area = envelope['width'] * envelope['height']
    violations = ([gap for gap in gaps + facing_gaps if gap['residual'] < -FIT_TOLERANCE])
    remaining_gap_space = [gap for gap in gaps + facing_gaps if gap['residual'] > FIT_TOLERANCE]
    binding = ([gap for gap in gaps + facing_gaps if abs(gap['residual']) <= 0.01]
               + [gap for gap in boundaries if abs(gap['residual']) <= 0.01])
    base_fit.update({
        'diagnostic': None,
        'growth': {key: round(value, 9) for key, value in growth.items()},
        'frozen': list(dict.fromkeys(frozen)), 'iterations': iterations, 'gaps': gaps,
        'facing_gaps': facing_gaps,
        'gap_violations': violations, 'remaining_gap_space': remaining_gap_space,
        'boundary_gaps': boundaries, 'binding_constraints': binding,
        'remaining_whitespace': {
            'seed_frame_area': round(seed_area, 3), 'final_frame_area': round(final_area, 3),
            'envelope_area': round(envelope_area, 3),
            'seed_occupancy_same_envelope': round(seed_area / envelope_area, 6),
            'final_occupancy_same_envelope': round(final_area / envelope_area, 6),
            'seed_unused_same_envelope': round(envelope_area - seed_area, 3),
            'final_unused_same_envelope': round(envelope_area - final_area, 3),
            'final_canvas_area': round(canvas['width'] * canvas['height'], 3),
            'final_canvas_occupancy': round(final_area / (canvas['width'] * canvas['height']), 6),
        },
    })
    candidate['fit'] = base_fit
    return candidate


def _fixed_fit_graph(seed_frames, fit_info, pad_length):
    """Read the checkpoint's directed separation graph without changing its axes."""
    identifiers = [frame['id'] for frame in seed_frames]
    indexes = {identifier: index for index, identifier in enumerate(identifiers)}
    horizontal, vertical = [], []
    relation_axes = {}
    relation_edges = {}
    problems = []
    for axis, key, target in (('x', 'horizontal_edges', horizontal),
                              ('y', 'vertical_edges', vertical)):
        edges = fit_info.get(key)
        if not isinstance(edges, list):
            problems.append('checkpoint has no ' + key)
            continue
        for edge in edges:
            if not isinstance(edge, (list, tuple)) or len(edge) != 2:
                problems.append('checkpoint has a malformed ' + axis + ' edge')
                continue
            source, destination = edge
            if source not in indexes or destination not in indexes or source == destination:
                problems.append('checkpoint has an unknown ' + axis + ' edge')
                continue
            pair = tuple(sorted((indexes[source], indexes[destination])))
            relation_axes.setdefault(pair, []).append(axis)
            relation_edges.setdefault(pair, {})[axis] = (indexes[source], indexes[destination])
            target.append((indexes[source], indexes[destination]))
    if problems:
        return None, None, None, problems
    if _topological_order(len(seed_frames), horizontal,
                          [frame['x'] for frame in seed_frames]) is None:
        problems.append('checkpoint horizontal separation graph contains a cycle')
    if _topological_order(len(seed_frames), vertical,
                          [frame['y'] for frame in seed_frames]) is None:
        problems.append('checkpoint vertical separation graph contains a cycle')
    if problems:
        return None, None, None, problems
    relations = [{'first': pair[0], 'second': pair[1],
                  'axes': list(relation_axes[pair]), 'edges': relation_edges[pair],
                  'required': pad_length}
                 for pair in sorted(relation_axes)]
    return horizontal, vertical, relations, []


def _swept_gap_discrepancy(layout, pad_length, outer_margin):
    """Measure excess gaps in horizontal and vertical bands of a public layout."""
    frames = _placement_frames(layout)
    canvas = layout.get('canvas') or {}
    width = _finite(canvas.get('width'), 0.0)
    height = _finite(canvas.get('height'), 0.0)
    if not frames or width <= 0 or height <= 0:
        return {'horizontal': 0.0, 'vertical': 0.0, 'total': 0.0, 'gaps': []}

    def sweep(axis):
        perpendicular = 'y' if axis == 'x' else 'x'
        dimension = 'width' if axis == 'x' else 'height'
        perpendicular_dimension = 'height' if axis == 'x' else 'width'
        limit = width if axis == 'x' else height
        perpendicular_limit = height if axis == 'x' else width
        coordinates = {0.0, perpendicular_limit}
        for frame in frames:
            start = frame[perpendicular]
            end = start + frame[perpendicular_dimension]
            coordinates.update((max(0.0, start), min(perpendicular_limit, end)))
        sorted_coordinates = sorted(coordinates)
        gaps = []
        weighted_excess = 0.0
        for lower, upper in zip(sorted_coordinates, sorted_coordinates[1:]):
            band = upper - lower
            if band <= FIT_TOLERANCE:
                continue
            active = [frame for frame in frames
                      if frame[perpendicular] < upper - FIT_TOLERANCE
                      and frame[perpendicular] + frame[perpendicular_dimension] > lower + FIT_TOLERANCE]
            if not active:
                continue
            active.sort(key=lambda frame: (frame[axis], frame['id']))
            previous = None
            for index, frame in enumerate(active):
                start = frame[axis]
                if previous is None:
                    actual = start
                    required = outer_margin
                    source = None
                    destination = frame['id']
                    kind = 'boundary-start'
                else:
                    previous_end = previous[axis] + previous[dimension]
                    actual = start - previous_end
                    required = pad_length
                    source = previous['id']
                    destination = frame['id']
                    kind = 'between'
                excess = max(0.0, actual - required)
                weighted_excess += band * excess * excess
                gaps.append({'axis': axis, 'kind': kind, 'source': source,
                             'destination': destination, 'actual': actual,
                             'required': required, 'residual': actual - required,
                             'weight': band})
                previous = frame
            end_gap = limit - (previous[axis] + previous[dimension])
            required = outer_margin
            excess = max(0.0, end_gap - required)
            weighted_excess += band * excess * excess
            gaps.append({'axis': axis, 'kind': 'boundary-end', 'source': previous['id'],
                         'destination': None, 'actual': end_gap, 'required': required,
                         'residual': end_gap - required, 'weight': band})
        normalizer = max(perpendicular_limit * limit * limit, 1.0)
        return weighted_excess / normalizer, gaps

    horizontal, horizontal_gaps = sweep('x')
    vertical, vertical_gaps = sweep('y')
    gaps = []
    for item in horizontal_gaps + vertical_gaps:
        gaps.append({key: (round(value, 6) if isinstance(value, float) else value)
                     for key, value in item.items()})
    return {'horizontal': round(horizontal, 9), 'vertical': round(vertical, 9),
            'total': round(horizontal + vertical, 9), 'gaps': gaps}


def _minimum_axis_extent(frames, edges, growth, outer_margin, pad_length, axis):
    """Return the smallest finite canvas extent that can host one fixed axis graph."""
    dimension = 'content_width' if axis == 'x' else 'content_height'
    sizes = [frame[dimension] * growth[frame['id']]
             + 2 * PANEL_PADDING + (NUMBER_BAND if axis == 'y' else 0.0)
             for frame in frames]
    order = _topological_order(len(frames), edges,
                               [frame[axis] for frame in frames])
    if order is None:
        return None
    predecessors = [[] for _ in frames]
    for source, destination in edges:
        predecessors[destination].append(source)
    earliest = [outer_margin] * len(frames)
    for destination in order:
        if predecessors[destination]:
            earliest[destination] = max(
                [outer_margin]
                + [earliest[source] + sizes[source] + pad_length
                   for source in predecessors[destination]])
    return max(earliest[index] + sizes[index] for index in range(len(frames))) + outer_margin


def _shrink_scale_limits(panels, seed_frames):
    """Return per-panel shrink limits using native rendered text measurements when present."""
    limits = {}
    measurements = {}
    unreadable = []
    for panel, frame in zip(panels, seed_frames):
        reference = frame['scale']
        native = _finite(panel.get('native_min_text_size'))
        native_measured = bool(panel.get('native_text_measured'))
        # A positive explicitly supplied native measurement is also accepted for callers that
        # construct records outside panel_record. Static font attributes are not a safe fallback:
        # transforms can make their displayed size smaller than the attribute suggests.
        if native is not None and native > 0 and ('native_min_text_size' in panel):
            native_measured = True
        if not native_measured:
            native = 0.0
        if native <= 0 and _finite(panel.get('body_size'), 0.0) <= 0:
            readable = 0.0
        elif native <= 0:
            readable = reference
        elif native * reference < SHRINK_MIN_TEXT_SIZE:
            # A checkpoint that is already unreadable cannot be made safe by a shrink pass.
            readable = reference
            unreadable.append((frame['id'], native * reference))
        elif native * reference <= SHRINK_MIN_TEXT_SIZE + SHRINK_ROUNDING_MARGIN:
            # The checkpoint is already at the floor; preserve its scale exactly.
            readable = reference
        else:
            readable = ((SHRINK_MIN_TEXT_SIZE + SHRINK_ROUNDING_MARGIN) / native)
        limits[frame['id']] = min(reference,
                                  max(reference * (1.0 - SHRINK_MAX_REDUCTION), readable))
        measurements[frame['id']] = round(native, 6) if native else None
    return limits, measurements, unreadable


def _layout_occupancy(layout, envelope):
    frames = _placement_frames(layout)
    area = sum(frame['width'] * frame['height'] for frame in frames)
    canvas = layout.get('canvas') or {}
    canvas_area = max(_finite(canvas.get('width'), 0.0) * _finite(canvas.get('height'), 0.0), 1.0)
    envelope_area = max(envelope['width'] * envelope['height'], 1.0)
    return {'frame_area': round(area, 6),
            'same_envelope': round(area / envelope_area, 9),
            'canvas': round(area / canvas_area, 9),
            'canvas_area': round(canvas_area, 6)}


def _shrink_skip(initial_layout, reason):
    result = dict(initial_layout)
    result['shrink'] = {
        'algorithm': 'shrink-first-v1', 'validated_checkpoint': False,
        'diagnostic': {'kind': 'skipped-refinement', 'reason': reason},
        'step': SHRINK_STEP, 'maximum_reduction': SHRINK_MAX_REDUCTION,
        'minimum_text_size': SHRINK_MIN_TEXT_SIZE,
        'rounding_margin': SHRINK_ROUNDING_MARGIN, 'candidate_count': 0,
    }
    return result


def shrink_fit_layout(panels, checkpoint, *, pad_length=FIT_PAD, outer_margin=OUTER_MARGIN):
    """Compact a validated gap-fit checkpoint through bounded uniform panel reductions.

    Each candidate keeps the checkpoint's source geometry and pair axes. A band sweep scores the
    newly exposed gaps after constraint-aware repositioning; only candidates with at least the
    current canvas occupancy and a lower geometric score are accepted. This stage never grows a
    panel, edits SVG text, or chooses an aspect ratio.
    """
    panels = list(panels)
    if not panels:
        raise ValueError('An overview needs at least one panel.')
    if len(panels) > 7:
        raise ValueError('An overview supports at most seven panels.')
    pad_length = _finite(pad_length)
    outer_margin = _finite(outer_margin)
    if pad_length is None or pad_length < 0 or outer_margin is None or outer_margin < 0:
        raise ValueError('Fitting gaps and margins must be finite and nonnegative.')
    existing_shrink = checkpoint.get('shrink') if isinstance(checkpoint, dict) else None
    if (isinstance(existing_shrink, dict)
            and existing_shrink.get('algorithm') == 'shrink-first-v1'):
        result = dict(checkpoint)
        result['shrink'] = dict(existing_shrink)
        result['shrink']['diagnostic'] = {
            'kind': 'already-refined', 'reason': 'checkpoint already has shrink-first refinement'}
        result['shrink']['refinement_skipped'] = True
        result['shrink']['candidate_count'] = 0
        return result
    fit_info = checkpoint.get('fit') if isinstance(checkpoint, dict) else None
    if not isinstance(fit_info, dict) or fit_info.get('algorithm') != 'gap-driven-v1':
        return _shrink_skip(checkpoint, 'checkpoint was not produced by the gap fitter')
    if fit_info.get('feasible') is not True:
        return _shrink_skip(checkpoint, 'checkpoint is not feasible')
    try:
        seed_frames, derived_envelope, _ = _seed_fit_records(panels, checkpoint, outer_margin)
    except (KeyError, TypeError, ValueError) as error:
        return _shrink_skip(checkpoint, 'checkpoint geometry is unusable: ' + str(error))
    envelope = {'width': _finite((fit_info.get('envelope') or {}).get('width')),
                'height': _finite((fit_info.get('envelope') or {}).get('height'))}
    if (envelope['width'] is None or envelope['height'] is None
            or envelope['width'] <= 0 or envelope['height'] <= 0):
        envelope = derived_envelope
    horizontal, vertical, relations, problems = _fixed_fit_graph(seed_frames, fit_info, pad_length)
    if problems:
        return _shrink_skip(checkpoint, '; '.join(problems))
    limits, native_text, unreadable = _shrink_scale_limits(panels, seed_frames)
    reference_scales = {frame['id']: frame['scale'] for frame in seed_frames}
    if set(reference_scales) != set(checkpoint.get('scales', reference_scales)):
        return _shrink_skip(checkpoint, 'checkpoint scale map does not cover every panel')
    if unreadable:
        details = ', '.join(identifier + '=' + str(round(size, 3))
                            for identifier, size in unreadable)
        return _shrink_skip(checkpoint, 'checkpoint text is below the 14-unit floor: ' + details)

    def compact(scales):
        growth = {identifier: scales[identifier] / reference_scales[identifier]
                  for identifier in reference_scales}
        if any(value > 1.0 + FIT_TOLERANCE for value in growth.values()):
            return None, 'shrink candidate grew a panel'
        minimum_width = _minimum_axis_extent(seed_frames, horizontal, growth,
                                             outer_margin, pad_length, 'x')
        minimum_height = _minimum_axis_extent(seed_frames, vertical, growth,
                                              outer_margin, pad_length, 'y')
        if minimum_width is None or minimum_height is None:
            return None, 'checkpoint separation graph contains a cycle'
        compact_envelope = {'width': min(envelope['width'], minimum_width),
                            'height': min(envelope['height'], minimum_height)}
        frames, problem = _place_fit(seed_frames, horizontal, vertical, growth,
                                     compact_envelope, outer_margin, pad_length)
        if problem is not None:
            return None, problem.get('reason', 'candidate cannot satisfy the checkpoint graph')
        placements, canvas = _frame_placements(frames, outer_margin)
        candidate = {'canvas': canvas, 'placements': placements,
                     'columns': checkpoint.get('columns', 1),
                     'scales': {key: round(value, 6) for key, value in scales.items()}}
        if canvas['width'] > envelope['width'] + FIT_OUTPUT_TOLERANCE or \
                canvas['height'] > envelope['height'] + FIT_OUTPUT_TOLERANCE:
            return None, 'candidate canvas exceeded the checkpoint envelope'
        validation = _validate_fitted_layout(candidate, limits, relations, envelope,
                                              outer_margin, pad_length)
        if validation:
            return None, validation
        gaps = _swept_gap_discrepancy(candidate, pad_length, outer_margin)
        if any(gap['residual'] < -FIT_OUTPUT_TOLERANCE for gap in gaps['gaps']):
            return None, 'candidate exposed a gap below its required pad or margin'
        return candidate, None

    def scored(candidate, scales):
        gaps = _swept_gap_discrepancy(candidate, pad_length, outer_margin)
        resize = sum(math.log(scales[key] / reference_scales[key]) ** 2
                     for key in reference_scales) / len(reference_scales)
        occupancy = _layout_occupancy(candidate, envelope)
        return {'gap': gaps, 'resize_cost': round(resize, 9),
                'score': round(gaps['total'] + SHRINK_RESIZE_PENALTY * resize, 9),
                'occupancy': occupancy}

    reference_scales = {key: float(value) for key, value in reference_scales.items()}
    checkpoint_score = scored(checkpoint, reference_scales)
    if any(gap['residual'] < -FIT_OUTPUT_TOLERANCE
           for gap in checkpoint_score['gap']['gaps']):
        return _shrink_skip(checkpoint, 'checkpoint exposed a gap below its required pad or margin')
    best = dict(checkpoint)
    best_scales = dict(reference_scales)
    best_score = checkpoint_score
    compact_reference, problem = compact(reference_scales)
    if compact_reference is not None:
        compact_score = scored(compact_reference, reference_scales)
        if (compact_score['occupancy']['canvas'] + FIT_TOLERANCE >= best_score['occupancy']['canvas']
                and compact_score['score'] < best_score['score'] - FIT_TOLERANCE):
            best, best_score = compact_reference, compact_score
    candidate_count = 0
    iterations = 0
    stopping_reason = 'no improving shrink candidate'
    panel_order = [frame['id'] for frame in seed_frames]
    for _ in range(SHRINK_MAX_ITERATIONS):
        eligible = [index for index, identifier in enumerate(panel_order)
                    if best_scales[identifier] - limits[identifier]
                    > FIT_TOLERANCE]
        if not eligible:
            stopping_reason = 'all panels reached readability or reduction limits'
            break
        winner = None
        winner_scales = None
        winner_score = None
        winner_subset = None
        for mask in range(1, 1 << len(eligible)):
            subset = tuple(eligible[index] for index in range(len(eligible)) if mask & (1 << index))
            proposed = dict(best_scales)
            for index in subset:
                identifier = panel_order[index]
                proposed[identifier] = max(limits[identifier],
                                            proposed[identifier]
                                            - SHRINK_STEP * reference_scales[identifier])
            if all(abs(proposed[key] - best_scales[key]) <= FIT_TOLERANCE
                   for key in panel_order):
                continue
            candidate, problem = compact(proposed)
            candidate_count += 1
            if candidate is None:
                continue
            candidate_score = scored(candidate, proposed)
            if candidate_score['occupancy']['canvas'] + FIT_TOLERANCE < best_score['occupancy']['canvas']:
                continue
            better = candidate_score['score'] < (winner_score['score'] - FIT_TOLERANCE
                                                  if winner_score else float('inf'))
            tied = (winner_score is not None
                    and abs(candidate_score['score'] - winner_score['score']) <= FIT_TOLERANCE)
            if tied and candidate_score['resize_cost'] < winner_score['resize_cost'] - FIT_TOLERANCE:
                better = True
            if tied and abs(candidate_score['resize_cost'] - winner_score['resize_cost']) <= FIT_TOLERANCE:
                better = winner_subset is None or subset < winner_subset
            if better:
                winner, winner_scales, winner_score, winner_subset = (
                    candidate, proposed, candidate_score, subset)
        if winner is None or winner_score['score'] >= best_score['score'] - FIT_TOLERANCE:
            stopping_reason = 'no improving shrink candidate'
            break
        best, best_scales, best_score = winner, winner_scales, winner_score
        iterations += 1
    final_validation = _validate_fitted_layout(best, limits, relations, envelope,
                                                outer_margin, pad_length)
    if final_validation:
        return _shrink_skip(checkpoint, 'final shrink validation failed: ' + final_validation)
    final_gaps = best_score['gap']
    final_occupancy = best_score['occupancy']
    checkpoint_occupancy = checkpoint_score['occupancy']
    best['fit'] = checkpoint.get('fit')
    best['shrink'] = {
        'algorithm': 'shrink-first-v1', 'validated_checkpoint': True,
        'step': SHRINK_STEP, 'maximum_reduction': SHRINK_MAX_REDUCTION,
        'minimum_text_size': SHRINK_MIN_TEXT_SIZE,
        'rounding_margin': SHRINK_ROUNDING_MARGIN,
        'pad_length': round(pad_length, 6), 'outer_margin': round(outer_margin, 6),
        'checkpoint_scales': {key: round(value, 6) for key, value in reference_scales.items()},
        'minimum_scales': {key: round(value, 6) for key, value in limits.items()},
        'native_min_text_sizes': native_text,
        'final_scales': dict(best['scales']),
        'accepted_reductions': {key: round(reference_scales[key] - best_scales[key], 6)
                                for key in panel_order if reference_scales[key] - best_scales[key] > FIT_TOLERANCE},
        'checkpoint_canvas': dict(checkpoint.get('canvas') or {}),
        'final_canvas': dict(best.get('canvas') or {}),
        'checkpoint_gap_score': checkpoint_score['gap'],
        'final_gap_score': final_gaps,
        'checkpoint_resize_cost': checkpoint_score['resize_cost'],
        'final_resize_cost': best_score['resize_cost'],
        'checkpoint_occupancy': checkpoint_occupancy,
        'final_occupancy': final_occupancy,
        'final_gaps': final_gaps.get('gaps', []),
        'remaining_gap_space': [gap for gap in final_gaps.get('gaps', [])
                                if gap['residual'] > FIT_OUTPUT_TOLERANCE],
        'gap_violations': [gap for gap in final_gaps.get('gaps', [])
                           if gap['residual'] < -FIT_OUTPUT_TOLERANCE],
        'candidate_count': candidate_count, 'iterations': iterations,
        'stopping_reason': stopping_reason, 'diagnostic': None,
    }
    return best
