"""Bounded outer-edge alignment for composed Overview panels."""
from __future__ import annotations

import copy
import math

from papers.arrangement import (
    FIT_OUTPUT_TOLERANCE,
    FIT_PAD,
    FIT_TOLERANCE,
    NUMBER_BAND,
    OUTER_MARGIN,
    PANEL_PADDING,
    SHRINK_MIN_TEXT_SIZE,
    _swept_gap_discrepancy,
)


EDGE_ALGORITHM = 'edge-align-v1'
OUTER_ALIGNMENT_ALGORITHM = 'outer-edge-translate-v1'
EDGE_MAX_STRETCH = 1.05
EDGE_GAP_THRESHOLD = 32.0


def _finite(value, fallback=None):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return fallback
    return value if math.isfinite(value) else fallback


def _gap_threshold(pad_length):
    return max(EDGE_GAP_THRESHOLD, 2.0 * pad_length)


def _canvas(layout):
    value = layout.get('canvas') if isinstance(layout, dict) else None
    if not isinstance(value, dict):
        return None
    width, height = _finite(value.get('width')), _finite(value.get('height'))
    if width is None or height is None or width <= 0 or height <= 0:
        return None
    return {'width': width, 'height': height}


def _frames(layout):
    placements = layout.get('placements') if isinstance(layout, dict) else None
    if not isinstance(placements, list):
        return None
    result = []
    identifiers = set()
    for index, placement in enumerate(placements):
        frame = placement.get('frame') if isinstance(placement, dict) else None
        if not isinstance(frame, dict) or placement.get('id') is None:
            return None
        if placement['id'] in identifiers:
            return None
        identifiers.add(placement['id'])
        values = [_finite(frame.get(key)) for key in ('x', 'y', 'width', 'height')]
        if any(value is None for value in values) or values[2] <= 0 or values[3] <= 0:
            return None
        result.append({'index': index, 'id': placement['id'], 'x': values[0], 'y': values[1],
                       'width': values[2], 'height': values[3]})
    return result


def _panel_map(panels):
    result = {}
    for panel in panels:
        if not isinstance(panel, dict) or panel.get('id') is None:
            return None
        identifier = panel['id']
        if identifier in result:
            return None
        result[identifier] = panel
    return result


def _source_bounds(panel):
    width = _finite(panel.get('width'))
    height = _finite(panel.get('height'))
    if width is None or height is None or width <= 0 or height <= 0:
        return None
    bounds = panel.get('content_bounds') or (0.0, 0.0, width, height)
    if not isinstance(bounds, (list, tuple)) or len(bounds) != 4:
        bounds = (0.0, 0.0, width, height)
    values = [_finite(value) for value in bounds]
    if any(value is None for value in values):
        values = [0.0, 0.0, width, height]
    left, top, right, bottom = values
    left, top = max(0.0, left), max(0.0, top)
    right, bottom = min(width, right), min(height, bottom)
    if right <= left or bottom <= top:
        left, top, right, bottom = 0.0, 0.0, width, height
    return {'width': width, 'height': height,
            'bounds': (left, top, right, bottom),
            'content_width': right - left, 'content_height': bottom - top}


def _interval_gap(first_start, first_end, second_start, second_end):
    if first_end < second_start:
        return second_start - first_end
    if second_end < first_start:
        return first_start - second_end
    return 0.0


def _vertical_neighbour(first, second, pad_length):
    return _interval_gap(first['y'], first['y'] + first['height'],
                         second['y'], second['y'] + second['height']) < pad_length - FIT_TOLERANCE


def _pair_gaps(frames, pad_length):
    report = []
    violations = []
    for first_index, first in enumerate(frames):
        for second in frames[first_index + 1:]:
            horizontal = _interval_gap(first['x'], first['x'] + first['width'],
                                       second['x'], second['x'] + second['width'])
            vertical = _interval_gap(first['y'], first['y'] + first['height'],
                                     second['y'], second['y'] + second['height'])
            item = {'first': first['id'], 'second': second['id'],
                    'horizontal': round(horizontal, 6), 'vertical': round(vertical, 6),
                    'required': round(pad_length, 6)}
            report.append(item)
            # A diagonal corner still needs one complete pad-sized clearance.  This catches the
            # near-diagonal case where intervals do not overlap but are too close on both axes.
            if horizontal < pad_length - FIT_OUTPUT_TOLERANCE \
                    and vertical < pad_length - FIT_OUTPUT_TOLERANCE:
                violations.append(item)
    return report, violations


def _layout_problem(layout, frames, panel_map, pad_length, outer_margin):
    canvas = _canvas(layout)
    if canvas is None or frames is None or panel_map is None:
        return 'layout has no finite canvas, frames, or panel records'
    if len(frames) != len(panel_map) or {frame['id'] for frame in frames} != set(panel_map):
        return 'layout and panel records do not cover the same panels'
    for frame in frames:
        if frame['id'] not in panel_map:
            return 'layout contains an unknown panel'
        if (frame['x'] < outer_margin - FIT_OUTPUT_TOLERANCE
                or frame['y'] < outer_margin - FIT_OUTPUT_TOLERANCE
                or frame['x'] + frame['width'] > canvas['width'] - outer_margin + FIT_OUTPUT_TOLERANCE
                or frame['y'] + frame['height'] > canvas['height'] - outer_margin + FIT_OUTPUT_TOLERANCE):
            return 'frame fell outside the fixed canvas'
    _, violations = _pair_gaps(frames, pad_length)
    if violations:
        return 'layout contains a pair below the required clearance'
    return None


def _native_scale_problem(layout, panels, minimum_scale=SHRINK_MIN_TEXT_SIZE):
    by_id = _panel_map(panels)
    if by_id is None:
        return 'panel records are malformed'
    placements = layout.get('placements') if isinstance(layout, dict) else None
    if not isinstance(placements, list):
        return 'layout has no placements'
    for placement in placements:
        panel = by_id.get(placement.get('id'))
        if panel is None:
            return 'layout contains an unknown panel'
        scale_x = _finite(placement.get('scale_x'), _finite(placement.get('scale')))
        scale_y = _finite(placement.get('scale_y'), _finite(placement.get('scale')))
        if scale_x is None or scale_y is None or scale_x <= 0 or scale_y <= 0:
            return 'panel has no positive scale'
        source = _source_bounds(panel)
        if source is None:
            return 'panel has no usable source bounds'
        native = _finite(panel.get('native_min_text_size'))
        measured = bool(panel.get('native_text_measured'))
        if native is not None and native > 0 and 'native_min_text_size' in panel:
            measured = True
        if measured and native > 0 and native * min(scale_x, scale_y) \
                < minimum_scale - FIT_OUTPUT_TOLERANCE:
            return 'panel fell below the recorded native text floor'
    return None


def _y_bands(frames, height):
    coordinates = {0.0, height}
    for frame in frames:
        coordinates.add(frame['y'])
        coordinates.add(frame['y'] + frame['height'])
    values = sorted(coordinates)
    return [(lower, upper) for lower, upper in zip(values, values[1:])
            if upper - lower > FIT_TOLERANCE]


def _band_edge_gaps(frames, canvas, outer_margin):
    """Measure the actual side gap in each horizontal frame interval."""
    report = {frame['id']: {'left': [], 'right': []} for frame in frames}
    for lower, upper in _y_bands(frames, canvas['height']):
        active = [frame for frame in frames
                  if frame['y'] < upper - FIT_TOLERANCE
                  and frame['y'] + frame['height'] > lower + FIT_TOLERANCE]
        active.sort(key=lambda item: (item['x'], item['id']))
        for index, frame in enumerate(active):
            left = active[index - 1] if index else None
            right = active[index + 1] if index + 1 < len(active) else None
            report[frame['id']]['left'].append({
                'y0': round(lower, 6), 'y1': round(upper, 6),
                'actual': round(frame['x'] - (left['x'] + left['width']
                                               if left else outer_margin), 6),
                'source': left['id'] if left else None,
            })
            report[frame['id']]['right'].append({
                'y0': round(lower, 6), 'y1': round(upper, 6),
                'actual': round((right['x'] if right else canvas['width'] - outer_margin)
                                - (frame['x'] + frame['width']), 6),
                'source': right['id'] if right else None,
            })
    return report


def _side_clearance(frames, index, canvas, pad_length, outer_margin, bands=None):
    """Return raw side gaps and the safe whole-box extension for one panel.

    A neighbour is a blocker whenever its vertical interval overlaps or comes within the required
    pad.  Taking the minimum across all such neighbours handles partial exposure without trusting
    a panel centre or a single row assignment.
    """
    frame = frames[index]
    side_report = (bands or {}).get(frame['id'], {})
    result = {}
    for side in ('left', 'right'):
        raw = canvas['width'] - outer_margin - (frame['x'] + frame['width']) \
            if side == 'right' else frame['x'] - outer_margin
        safe = raw
        blockers = []
        for other_index, other in enumerate(frames):
            if other_index == index or not _vertical_neighbour(frame, other, pad_length):
                continue
            if side == 'right':
                if other['x'] >= frame['x'] + frame['width'] - FIT_TOLERANCE:
                    actual = other['x'] - (frame['x'] + frame['width'])
                    safe_gap = actual - pad_length
                elif other['x'] + other['width'] > frame['x'] + FIT_TOLERANCE:
                    actual, safe_gap = 0.0, -pad_length
                else:
                    continue
            else:
                if other['x'] + other['width'] <= frame['x'] + FIT_TOLERANCE:
                    actual = frame['x'] - (other['x'] + other['width'])
                    safe_gap = actual - pad_length
                elif other['x'] < frame['x'] + frame['width'] - FIT_TOLERANCE:
                    actual, safe_gap = 0.0, -pad_length
                else:
                    continue
            raw = min(raw, actual)
            safe = min(safe, safe_gap)
            blockers.append({'panel': other['id'], 'actual': round(actual, 6),
                             'safe': round(safe_gap, 6)})
        band_values = side_report.get(side, [])
        outer = [item['actual'] for item in band_values if item.get('source') is None]
        result[side] = {
            'actual': round(raw, 6), 'safe': round(safe, 6),
            'outer_actual': round(min(outer), 6) if outer else None,
            'blockers': blockers, 'bands': band_values,
        }
    return result


def _translation_limits(frame, frames, index, canvas, pad_length, outer_margin):
    lower = outer_margin
    upper = canvas['width'] - outer_margin - frame['width']
    for other_index, other in enumerate(frames):
        if other_index == index or not _vertical_neighbour(frame, other, pad_length):
            continue
        if other['x'] + other['width'] <= frame['x'] + FIT_TOLERANCE:
            lower = max(lower, other['x'] + other['width'] + pad_length)
        elif other['x'] >= frame['x'] + frame['width'] - FIT_TOLERANCE:
            upper = min(upper, other['x'] - pad_length)
        else:
            return None
    return lower, upper


def _set_frame_x(layout, index, x):
    placements = layout['placements']
    placement = placements[index]
    frame = placement['frame']
    delta = x - float(frame['x'])
    frame['x'] = round(x, 3)
    placement['x'] = round(float(placement['x']) + delta, 3)


def _alignment_count(frames, canvas, outer_margin, threshold):
    bands = _band_edge_gaps(frames, canvas, outer_margin)
    count = 0
    residual = 0.0
    for frame in frames:
        for side in ('left', 'right'):
            values = [item['actual'] for item in bands[frame['id']][side]
                      if item.get('source') is None]
            if values:
                residual += max(0.0, min(values) - threshold)
                if min(values) <= FIT_OUTPUT_TOLERANCE:
                    count += 1
    return count, residual


def align_outer_edges(panels, layout, *, pad_length=FIT_PAD, outer_margin=OUTER_MARGIN):
    """Translate exposed outer panels into a safe canvas edge before mixed fitting.

    Translation may redistribute the intermediate fixed-canvas gap score.  This pass never changes
    a panel scale and can therefore be used as the mixed fitter's working geometry.
    """
    panels = list(panels)
    pad_length, outer_margin = _finite(pad_length), _finite(outer_margin)
    result = copy.deepcopy(layout) if isinstance(layout, dict) else {}
    if (pad_length is None or pad_length < 0 or outer_margin is None or outer_margin < 0):
        result['outer_alignment'] = {'algorithm': OUTER_ALIGNMENT_ALGORITHM, 'validated': False,
                                     'diagnostic': {'reason': 'invalid pad or margin'}}
        return result
    if (not panels or len(panels) > 7 or _panel_map(panels) is None
            or _canvas(result) is None or _frames(result) is None):
        result['outer_alignment'] = {'algorithm': OUTER_ALIGNMENT_ALGORITHM, 'validated': False,
                                     'diagnostic': {'reason': 'layout or panel records are unusable'}}
        return result
    if isinstance(result.get('outer_alignment'), dict) \
            and result['outer_alignment'].get('validated') is True:
        return result
    frames = _frames(result)
    panel_map = _panel_map(panels)
    problem = _layout_problem(result, frames, panel_map, pad_length, outer_margin)
    if problem:
        result['outer_alignment'] = {'algorithm': OUTER_ALIGNMENT_ALGORITHM, 'validated': False,
                                     'diagnostic': {'reason': problem}}
        return result
    canvas = _canvas(result)
    threshold = _gap_threshold(pad_length)
    before = _swept_gap_discrepancy(result, pad_length, outer_margin)
    accepted = []
    for index, frame in enumerate(frames):
        current_frames = _frames(result)
        bands = _band_edge_gaps(current_frames, canvas, outer_margin)
        clearances = _side_clearance(current_frames, index, canvas, pad_length,
                                     outer_margin, bands)
        limits = _translation_limits(current_frames[index], current_frames, index, canvas,
                                     pad_length, outer_margin)
        if limits is None:
            continue
        lower, upper = limits
        candidates = []
        for side in ('left', 'right'):
            info = clearances[side]
            outer_gap = info['outer_actual']
            if outer_gap is None or outer_gap <= threshold + FIT_TOLERANCE:
                continue
            target = outer_margin if side == 'left' else canvas['width'] - outer_margin - frame['width']
            # A partial exposure cannot be aligned through a nearby neighbour.  Leave it in
            # place instead of translating to the nearest safe point and calling that aligned.
            if target < lower - FIT_TOLERANCE or target > upper + FIT_TOLERANCE:
                continue
            if abs(target - current_frames[index]['x']) <= FIT_TOLERANCE:
                continue
            candidate = copy.deepcopy(result)
            _set_frame_x(candidate, index, target)
            candidate_frames = _frames(candidate)
            if _layout_problem(candidate, candidate_frames, panel_map, pad_length, outer_margin):
                continue
            metrics = _swept_gap_discrepancy(candidate, pad_length, outer_margin)
            count, residual = _alignment_count(candidate_frames, canvas, outer_margin, threshold)
            candidates.append((metrics, count, residual, side, candidate))
        if not candidates:
            continue
        # Pick the nearest exposed canvas edge; a left edge wins an exact tie.  Intermediate gap
        # score is intentionally not an acceptance gate because this is a starting geometry pass.
        candidates.sort(key=lambda item: (abs(item[4]['placements'][index]['frame']['x']
                                             - current_frames[index]['x']), item[3]))
        metrics, count, residual, side, candidate = candidates[0]
        result = candidate
        accepted.append({'id': frame['id'], 'side': side,
                         'before_x': round(current_frames[index]['x'], 6),
                         'after_x': round(_frames(result)[index]['x'], 6),
                         'gap_total': metrics['total']})
    final_frames = _frames(result)
    after = _swept_gap_discrepancy(result, pad_length, outer_margin)
    result['outer_alignment'] = {
        'algorithm': OUTER_ALIGNMENT_ALGORITHM, 'validated': True,
        'diagnostic': None, 'gap_threshold': round(threshold, 6),
        'accepted': accepted, 'changed': bool(accepted),
        'before_gap': before, 'after_gap': after,
        'pair_gaps': _pair_gaps(final_frames, pad_length)[0],
    }
    return result


def _stretch_candidate(layout, index, panel, side_clearance, pad_length):
    placements = layout.get('placements') or []
    placement = placements[index]
    frame = placement.get('frame') or {}
    source = _source_bounds(panel)
    if source is None:
        return None
    base_x = _finite(placement.get('scale_x'), _finite(placement.get('scale')))
    base_y = _finite(placement.get('scale_y'), _finite(placement.get('scale')))
    if base_x is None or base_y is None or base_x <= 0 or base_y <= 0:
        return None
    left, top, right, bottom = source['bounds']
    max_delta = source['content_width'] * (EDGE_MAX_STRETCH - 1.0) * base_x
    if max_delta <= FIT_TOLERANCE:
        return None
    eligible = {}
    for side in ('left', 'right'):
        info = side_clearance[side]
        if info['outer_actual'] is not None \
                and info['actual'] > _gap_threshold(pad_length) + FIT_TOLERANCE \
                and info['safe'] > FIT_TOLERANCE:
            eligible[side] = min(info['safe'], max_delta)
    if not eligible:
        return None
    total = min(max_delta, sum(eligible.values()))
    if total <= FIT_TOLERANCE:
        return None
    if len(eligible) == 1:
        left_delta = total if 'left' in eligible else 0.0
        right_delta = total if 'right' in eligible else 0.0
    else:
        available = sum(eligible.values())
        left_delta = total * eligible['left'] / available
        right_delta = total - left_delta
    candidate = copy.deepcopy(layout)
    updated = candidate['placements'][index]
    updated_frame = updated['frame']
    old_width = _finite(updated_frame.get('width'))
    if old_width is None or old_width <= 0:
        return None
    new_frame_x = _finite(updated_frame.get('x')) - left_delta
    new_frame_width = old_width + left_delta + right_delta
    new_x_scale = base_x + (left_delta + right_delta) / source['content_width']
    updated_frame['x'] = round(new_frame_x, 3)
    updated_frame['width'] = round(new_frame_width, 3)
    updated['scale_x'] = round(new_x_scale, 6)
    updated['scale_y'] = round(base_y, 6)
    updated['x'] = round(new_frame_x + PANEL_PADDING - left * new_x_scale, 3)
    updated['y'] = round(_finite(updated_frame.get('y')) + PANEL_PADDING
                         + NUMBER_BAND - top * base_y, 3)
    updated['width'] = round(source['content_width'] * new_x_scale, 3)
    updated['height'] = round(source['content_height'] * base_y, 3)
    return candidate


def edge_align_layout(panels, mixed_layout, *, pad_length=FIT_PAD, outer_margin=OUTER_MARGIN):
    """Stretch finished mixed panels horizontally into large safe edge gaps.

    The canvas and every y coordinate remain fixed.  A panel is changed at most once, with a
    modest 5% content-width cap.  The returned layout is safe to pass through this function
    again: a validated edge result is returned byte-for-byte geometrically unchanged.
    """
    panels = list(panels)
    result = copy.deepcopy(mixed_layout) if isinstance(mixed_layout, dict) else {}
    if isinstance(result.get('edge_align'), dict) and result['edge_align'].get('validated') is True:
        return result
    pad_length, outer_margin = _finite(pad_length), _finite(outer_margin)
    mixed = result.get('mixed')
    if (pad_length is None or pad_length < 0 or outer_margin is None or outer_margin < 0
            or not panels or len(panels) > 7 or _panel_map(panels) is None
            or not isinstance(mixed, dict) or mixed.get('validated') is not True):
        result['edge_align'] = {'algorithm': EDGE_ALGORITHM, 'validated': False,
                                'diagnostic': {'reason': 'mixed result or settings are unusable'}}
        return result
    frames = _frames(result)
    panel_map = _panel_map(panels)
    problem = _layout_problem(result, frames, panel_map, pad_length, outer_margin)
    if problem:
        result['edge_align'] = {'algorithm': EDGE_ALGORITHM, 'validated': False,
                                'diagnostic': {'reason': problem}}
        return result
    problem = _native_scale_problem(result, panels)
    if problem:
        result['edge_align'] = {'algorithm': EDGE_ALGORITHM, 'validated': False,
                                'diagnostic': {'reason': problem}}
        return result
    canvas = _canvas(result)
    before = _swept_gap_discrepancy(result, pad_length, outer_margin)
    before_frames = copy.deepcopy(frames)
    changed = []
    candidate_count = 0
    for index, frame in enumerate(before_frames):
        current_frames = _frames(result)
        bands = _band_edge_gaps(current_frames, canvas, outer_margin)
        clearances = _side_clearance(current_frames, index, canvas, pad_length,
                                     outer_margin, bands)
        candidate = _stretch_candidate(result, index, panel_map[frame['id']], clearances,
                                       pad_length)
        candidate_count += 1
        if candidate is None:
            continue
        candidate_frames = _frames(candidate)
        if _layout_problem(candidate, candidate_frames, panel_map, pad_length, outer_margin):
            continue
        if _native_scale_problem(candidate, panels):
            continue
        current_gap = _swept_gap_discrepancy(result, pad_length, outer_margin)
        candidate_gap = _swept_gap_discrepancy(candidate, pad_length, outer_margin)
        if candidate_gap['total'] >= current_gap['total'] - FIT_TOLERANCE:
            continue
        placement = candidate['placements'][index]
        changed.append({
            'id': frame['id'], 'before_frame': frame,
            'after_frame': candidate_frames[index],
            'before_scale_x': round(_finite(result['placements'][index].get('scale_x'),
                                            result['placements'][index].get('scale')), 6),
            'after_scale_x': placement['scale_x'], 'scale_y': placement['scale_y'],
            'gap_before': current_gap, 'gap_after': candidate_gap,
        })
        result = candidate
    final_frames = _frames(result)
    after = _swept_gap_discrepancy(result, pad_length, outer_margin)
    pair_gaps, violations = _pair_gaps(final_frames, pad_length)
    problem = _layout_problem(result, final_frames, panel_map, pad_length, outer_margin)
    if problem or violations:
        # This should be unreachable because every candidate is checked, but retaining the mixed
        # result is safer than publishing a partially composed layout if rounding surprises us.
        result = copy.deepcopy(mixed_layout)
        final_frames = _frames(result)
        after = _swept_gap_discrepancy(result, pad_length, outer_margin)
        pair_gaps, violations = _pair_gaps(final_frames, pad_length)
        changed = []
    bands = _band_edge_gaps(final_frames, canvas, outer_margin)
    edge_gaps = []
    for frame in final_frames:
        clearances = _side_clearance(final_frames, frame['index'], canvas, pad_length,
                                     outer_margin, bands)
        for side in ('left', 'right'):
            item = dict(clearances[side])
            item.update({'panel': frame['id'], 'side': side})
            edge_gaps.append(item)
    result['edge_align'] = {
        'algorithm': EDGE_ALGORITHM, 'validated': True, 'diagnostic': None,
        'gap_threshold': round(_gap_threshold(pad_length), 6),
        'maximum_stretch': EDGE_MAX_STRETCH, 'candidate_count': candidate_count,
        'changed': bool(changed), 'changed_panels': changed,
        'before_gap': before, 'after_gap': after,
        'edge_gaps': edge_gaps, 'pair_gaps': pair_gaps,
        'pair_violations': violations,
        'canvas': dict(canvas), 'canvas_fixed': True,
        'minimum_singular_scale': {
            frame['id']: round(min(
                _finite(result['placements'][frame['index']].get('scale_x'),
                        result['placements'][frame['index']].get('scale')),
                _finite(result['placements'][frame['index']].get('scale_y'),
                        result['placements'][frame['index']].get('scale'))), 6)
            for frame in final_frames
        },
    }
    return result


__all__ = [
    'EDGE_ALGORITHM',
    'EDGE_GAP_THRESHOLD',
    'EDGE_MAX_STRETCH',
    'OUTER_ALIGNMENT_ALGORITHM',
    'align_outer_edges',
    'edge_align_layout',
]
