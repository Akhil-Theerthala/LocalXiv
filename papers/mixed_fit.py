"""Bounded coordinated resize for completed Overview panels."""
from __future__ import annotations

import copy
import itertools
import math
import time

from papers.arrangement import (
    FIT_OUTPUT_TOLERANCE,
    FIT_PAD,
    FIT_TOLERANCE,
    OUTER_MARGIN,
    _fixed_fit_graph,
    _frame_placements,
    _layout_occupancy,
    _minimum_axis_extent,
    _place_fit,
    _placement_frames,
    _seed_fit_records,
    _shrink_scale_limits,
    _swept_gap_discrepancy,
    _validate_fitted_layout,
)


# Keep these values fixed across the corpus and held-out synthetic audit.
MIXED_STEP = 0.04
MIXED_MIN_FACTOR = 0.80
MIXED_MAX_FACTOR = 1.50
MIXED_RESIZE_PENALTY = 0.02
MIXED_SEARCH_BUDGET = 1024
MIXED_MAX_DIRECTION_SUPPORT = 2


def _finite(value, fallback=None):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return fallback
    return value if math.isfinite(value) else fallback


def _scale_map(layout):
    scales = layout.get('scales') if isinstance(layout, dict) else None
    if not isinstance(scales, dict):
        return None
    result = {}
    for identifier, value in scales.items():
        number = _finite(value)
        if number is None or number <= 0:
            return None
        result[identifier] = number
    return result


def _direction_vectors(count):
    """Return deterministic single and pair moves, including mixed-sign pair moves."""
    directions = []
    for support in range(1, min(MIXED_MAX_DIRECTION_SUPPORT, count) + 1):
        for indexes in itertools.combinations(range(count), support):
            for signs in itertools.product((-1, 1), repeat=support):
                direction = [0] * count
                for index, sign in zip(indexes, signs):
                    direction[index] = sign
                directions.append(tuple(direction))
    return directions


def _area_tolerance(canvas):
    """Convert the existing dimensional rounding tolerance into an area allowance."""
    width = max(_finite((canvas or {}).get('width'), 0.0), 0.0)
    height = max(_finite((canvas or {}).get('height'), 0.0), 0.0)
    return FIT_OUTPUT_TOLERANCE * (width + height + FIT_OUTPUT_TOLERANCE)


def _metrics(layout, scales, reference_scales, envelope, pad_length=FIT_PAD,
             outer_margin=OUTER_MARGIN):
    gap = _swept_gap_discrepancy(layout, pad_length, outer_margin)
    occupancy = _layout_occupancy(layout, envelope)
    resize_cost = sum(
        math.log(scales[identifier] / reference_scales[identifier]) ** 2
        for identifier in reference_scales
    ) / len(reference_scales)
    growth_mass = sum(
        max(0.0, math.log(scales[identifier] / reference_scales[identifier]))
        for identifier in reference_scales
    )
    return {
        'gap': gap,
        'occupancy': occupancy,
        'resize_cost': resize_cost,
        'growth_mass': growth_mass,
        'score': gap['total'] + MIXED_RESIZE_PENALTY * resize_cost,
    }


def _tie_key(metrics, scales, reference_scales, panel_order):
    """Prefer less enlargement, then less movement, only for near-equal geometric scores."""
    return (
        metrics['growth_mass'],
        metrics['resize_cost'],
        tuple(round(scales[identifier] / reference_scales[identifier], 9)
              for identifier in panel_order),
    )


def _better(metrics, scales, best_metrics, best_scales, reference_scales, panel_order):
    if metrics['score'] < best_metrics['score'] - FIT_TOLERANCE:
        return True
    if abs(metrics['score'] - best_metrics['score']) > FIT_TOLERANCE:
        return False
    return _tie_key(metrics, scales, reference_scales, panel_order) < _tie_key(
        best_metrics, best_scales, reference_scales, panel_order)


def _candidate_from_scales(seed_frames, horizontal, vertical, scales, reference_scales,
                           checkpoint, outer_margin, pad_length):
    growth = {identifier: scales[identifier] / reference_scales[identifier]
              for identifier in reference_scales}
    minimum_width = _minimum_axis_extent(seed_frames, horizontal, growth,
                                         outer_margin, pad_length, 'x')
    minimum_height = _minimum_axis_extent(seed_frames, vertical, growth,
                                          outer_margin, pad_length, 'y')
    if minimum_width is None or minimum_height is None:
        return None, 'checkpoint separation graph contains a cycle'
    placement_envelope = {
        'width': max(2 * outer_margin, minimum_width),
        'height': max(2 * outer_margin, minimum_height),
    }
    frames, problem = _place_fit(seed_frames, horizontal, vertical, growth,
                                 placement_envelope, outer_margin, pad_length)
    if problem is not None:
        return None, problem.get('reason', 'candidate cannot satisfy the checkpoint graph')
    placements, canvas = _frame_placements(frames, outer_margin)
    return {
        'canvas': canvas,
        'placements': placements,
        'columns': checkpoint.get('columns', 1),
        'scales': {identifier: round(value, 6) for identifier, value in scales.items()},
    }, None


def _validate_candidate(layout, scales, lower_scales, relations, area_limit, outer_margin,
                        pad_length):
    if layout is None:
        return 'candidate has no layout'
    validation = _validate_fitted_layout(layout, lower_scales, relations,
                                          layout.get('canvas') or {}, outer_margin, pad_length)
    if validation:
        return validation
    canvas = layout.get('canvas') or {}
    width, height = _finite(canvas.get('width')), _finite(canvas.get('height'))
    if width is None or height is None or width <= 0 or height <= 0:
        return 'candidate has no usable canvas'
    if width * height > area_limit + _area_tolerance(canvas):
        return 'candidate canvas area exceeded the growth-checkpoint area budget'
    gap = _swept_gap_discrepancy(layout, pad_length, outer_margin)
    if any(item['residual'] < -FIT_OUTPUT_TOLERANCE for item in gap['gaps']):
        return 'candidate exposed a gap below its required pad or margin'
    return None


def _baseline(layout, label, reference_scales, lower_scales, relations, envelope, area_limit,
              outer_margin, pad_length):
    scales = _scale_map(layout)
    if scales is None or set(scales) != set(reference_scales):
        return None, label + ' checkpoint has no complete scale map'
    problem = _validate_candidate(layout, scales, lower_scales, relations, area_limit,
                                  outer_margin, pad_length)
    if problem:
        return None, label + ' checkpoint is unusable: ' + problem
    return {
        'label': label,
        'layout': copy.deepcopy(layout),
        'scales': scales,
        'metrics': _metrics(layout, scales, reference_scales, envelope, pad_length, outer_margin),
    }, None


def _failed_result(growth_checkpoint, reason, *, fallback_checkpoint=None,
                   reference_scales=None, envelope=None):
    fallback = growth_checkpoint if isinstance(growth_checkpoint, dict) else {}
    if (isinstance(fallback_checkpoint, dict)
            and isinstance(fallback_checkpoint.get('fit'), dict)
            and fallback_checkpoint['fit'].get('algorithm') == 'gap-driven-v1'
            and fallback_checkpoint['fit'].get('feasible') is True):
        fallback = fallback_checkpoint
    result = copy.deepcopy(fallback)
    result['mixed'] = {
        'algorithm': 'coordinated-mixed-v1',
        'validated': False,
        'diagnostic': {'kind': 'skipped-experiment', 'reason': reason},
        'step': MIXED_STEP,
        'minimum_factor': MIXED_MIN_FACTOR,
        'maximum_factor': MIXED_MAX_FACTOR,
        'resize_penalty': MIXED_RESIZE_PENALTY,
        'search_budget': MIXED_SEARCH_BUDGET,
        'reference_scales': reference_scales or {},
        'envelope': envelope or {},
        'candidate_count': 0,
    }
    return result


def _working_centres(seed_frames, panels, working_layout, outer_margin):
    """Copy only validated working positions onto immutable growth measurements."""
    if working_layout is None:
        return seed_frames, None
    alignment = working_layout.get('outer_alignment')
    if not isinstance(alignment, dict) or alignment.get('validated') is not True:
        return None, 'working layout has no validated outer alignment'
    try:
        working_frames, _, _ = _seed_fit_records(panels, working_layout, outer_margin)
    except (KeyError, TypeError, ValueError) as error:
        return None, 'working layout geometry is unusable: ' + str(error)
    by_id = {frame['id']: frame for frame in working_frames}
    working_placements = {
        placement.get('id'): placement
        for placement in (working_layout.get('placements') or [])
        if isinstance(placement, dict) and placement.get('id') is not None
    }
    for seed in seed_frames:
        working = by_id.get(seed['id'])
        placement = working_placements.get(seed['id'])
        if working is None or placement is None:
            return None, 'working layout does not cover every growth panel'
        for key in ('scale', 'width', 'height', 'content_width', 'content_height',
                    'source_width', 'source_height'):
            if abs(working[key] - seed[key]) > FIT_OUTPUT_TOLERANCE:
                return None, 'working layout changed immutable growth ' + key
        if any(abs(left - right) > FIT_OUTPUT_TOLERANCE
               for left, right in zip(working['source_bounds'], seed['source_bounds'])):
            return None, 'working layout changed immutable growth source bounds'
        for key in ('scale_x', 'scale_y'):
            value = _finite(placement.get(key))
            if value is not None and abs(value - seed['scale']) > FIT_OUTPUT_TOLERANCE:
                return None, 'working layout changed immutable growth ' + key
        seed['x'] += (working['x'] + working['width'] / 2
                      - seed['x'] - seed['width'] / 2)
        seed['y'] += (working['y'] + working['height'] / 2
                      - seed['y'] - seed['height'] / 2)
    return seed_frames, None


def mixed_fit_layout(panels, growth_checkpoint, shrink_checkpoint=None, *,
                     pad_length=FIT_PAD, outer_margin=OUTER_MARGIN, working_layout=None):
    """Search bounded mixed shrink/grow moves from an original growth checkpoint.

    ``growth_checkpoint`` is the immutable reference.  ``shrink_checkpoint`` is retained as an
    unchanged comparison candidate and as the default incumbent.  ``working_layout`` optionally
    supplies translated frame positions for candidate placement; its scales, graph, and canvas
    are never used as provenance or as a budget.  The returned layout has a ``mixed`` report;
    panel sources and authored geometry are never changed here.
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

    def fail(reason, **kwargs):
        return _failed_result(growth_checkpoint, reason,
                              fallback_checkpoint=shrink_checkpoint, **kwargs)

    fit_info = growth_checkpoint.get('fit') if isinstance(growth_checkpoint, dict) else None
    if not isinstance(fit_info, dict) or fit_info.get('algorithm') != 'gap-driven-v1':
        return fail('growth checkpoint was not produced by the gap fitter')
    if fit_info.get('feasible') is not True:
        return fail('growth checkpoint is not feasible')
    try:
        seed_frames, derived_envelope, _ = _seed_fit_records(panels, growth_checkpoint, outer_margin)
    except (KeyError, TypeError, ValueError) as error:
        return fail('growth checkpoint geometry is unusable: ' + str(error))
    seed_frames, working_problem = _working_centres(
        seed_frames, panels, working_layout if isinstance(working_layout, dict) else None,
        outer_margin)
    if working_problem:
        return fail(working_problem)
    envelope = {
        'width': _finite((fit_info.get('envelope') or {}).get('width')),
        'height': _finite((fit_info.get('envelope') or {}).get('height')),
    }
    if (envelope['width'] is None or envelope['height'] is None
            or envelope['width'] <= 0 or envelope['height'] <= 0):
        envelope = derived_envelope
    horizontal, vertical, relations, problems = _fixed_fit_graph(seed_frames, fit_info, pad_length)
    if problems:
        return fail('; '.join(problems), envelope=envelope)

    reference_scales = {frame['id']: frame['scale'] for frame in seed_frames}
    lower_scales, native_text, unreadable = _shrink_scale_limits(panels, seed_frames)
    upper_scales = {identifier: scale * MIXED_MAX_FACTOR
                    for identifier, scale in reference_scales.items()}
    growth_canvas = growth_checkpoint.get('canvas') or {}
    growth_width = _finite(growth_canvas.get('width'))
    growth_height = _finite(growth_canvas.get('height'))
    if growth_width is None or growth_height is None or growth_width <= 0 or growth_height <= 0:
        return fail('growth checkpoint has no usable canvas',
                    reference_scales=reference_scales, envelope=envelope)
    area_limit = growth_width * growth_height

    # Treat a below-floor growth checkpoint as an invalid precondition for this prototype. A later
    # experiment could use enlargement to repair it, but this replay does not silently mix repair
    # with fitting.
    if unreadable:
        details = ', '.join(identifier + '=' + str(round(size, 3))
                            for identifier, size in unreadable)
        return fail('growth checkpoint text is below the 14-unit floor: ' + details,
                    reference_scales=reference_scales, envelope=envelope)

    panel_order = [frame['id'] for frame in seed_frames]
    growth_base, growth_problem = _baseline(
        growth_checkpoint, 'growth', reference_scales, lower_scales, relations, envelope,
        area_limit, outer_margin, pad_length)
    shrink_base, shrink_problem = (None, 'shrink checkpoint was not supplied')
    if isinstance(shrink_checkpoint, dict):
        shrink_base, shrink_problem = _baseline(
            shrink_checkpoint, 'shrink', reference_scales, lower_scales, relations, envelope,
            area_limit, outer_margin, pad_length)
    if shrink_base is None and growth_base is None:
        return fail('; '.join(item for item in (growth_problem, shrink_problem) if item),
                    reference_scales=reference_scales, envelope=envelope)

    # Keep the shrink checkpoint as the no-regression floor whenever it is available.
    incumbent = shrink_base or growth_base
    target_metrics = incumbent['metrics']
    if shrink_base is not None:
        target_metrics = shrink_base['metrics']
    if (growth_base is not None and growth_base is not incumbent
            and growth_base['metrics']['gap']['total'] <= target_metrics['gap']['total'] + FIT_TOLERANCE
            and growth_base['metrics']['occupancy']['canvas'] + FIT_TOLERANCE
            >= target_metrics['occupancy']['canvas']
            and _better(growth_base['metrics'], growth_base['scales'], incumbent['metrics'],
                        incumbent['scales'], reference_scales, panel_order)):
        incumbent = growth_base

    best = incumbent
    search_started = time.perf_counter()
    directions = _direction_vectors(len(panel_order))
    candidate_count = 0
    valid_count = 0
    mixed_count = 0
    accepted_mixed = 0
    iterations = 0
    stopping_reason = 'no improving mixed candidate'
    frontier = [incumbent]
    if shrink_base is not None and growth_base is not None and incumbent is shrink_base:
        # Probe both immutable checkpoints in the first bounded sweep. Subsequent sweeps follow
        # the winning state, keeping the search local and deterministic.
        frontier = [shrink_base, growth_base]

    # ponytail: single/pair local search, with a fixed 1024-evaluation ceiling; a larger joint
    # optimizer belongs in a separately justified experiment after this comparison.
    while frontier and candidate_count < MIXED_SEARCH_BUDGET:
        winner = None
        winner_direction = None
        remaining = MIXED_SEARCH_BUDGET - candidate_count
        for state in frontier:
            for direction in directions[:remaining]:
                if candidate_count >= MIXED_SEARCH_BUDGET:
                    break
                candidate_count += 1
                if sum(sign < 0 for sign in direction) and sum(sign > 0 for sign in direction):
                    mixed_count += 1
                proposed = dict(state['scales'])
                for index, sign in enumerate(direction):
                    if sign:
                        identifier = panel_order[index]
                        proposed[identifier] = max(
                            lower_scales[identifier],
                            min(upper_scales[identifier],
                                proposed[identifier] + sign * MIXED_STEP * reference_scales[identifier]),
                        )
                if proposed == state['scales']:
                    continue
                candidate, problem = _candidate_from_scales(
                    seed_frames, horizontal, vertical, proposed, reference_scales,
                    growth_checkpoint, outer_margin, pad_length)
                if candidate is None:
                    continue
                problem = _validate_candidate(candidate, proposed, lower_scales, relations,
                                              area_limit, outer_margin, pad_length)
                if problem:
                    continue
                metrics = _metrics(candidate, proposed, reference_scales, envelope,
                                   pad_length, outer_margin)
                valid_count += 1
                if (metrics['gap']['total'] > target_metrics['gap']['total'] + FIT_TOLERANCE
                        or metrics['occupancy']['canvas'] + FIT_TOLERANCE
                        < target_metrics['occupancy']['canvas']):
                    continue
                candidate_state = {'label': 'mixed', 'layout': candidate,
                                   'scales': proposed, 'metrics': metrics}
                if (winner is None or _better(metrics, proposed, winner['metrics'],
                                              winner['scales'], reference_scales, panel_order)):
                    winner = candidate_state
                    winner_direction = direction
        if winner is None or not _better(winner['metrics'], winner['scales'], best['metrics'],
                                         best['scales'], reference_scales, panel_order):
            if candidate_count >= MIXED_SEARCH_BUDGET:
                stopping_reason = 'candidate budget exhausted'
            break
        best = winner
        if winner_direction and sum(sign < 0 for sign in winner_direction) \
                and sum(sign > 0 for sign in winner_direction):
            accepted_mixed += 1
        iterations += 1
        frontier = [best]

    if candidate_count >= MIXED_SEARCH_BUDGET:
        stopping_reason = 'candidate budget exhausted'
    search_seconds = time.perf_counter() - search_started

    final_validation = _validate_candidate(best['layout'], best['scales'], lower_scales, relations,
                                           area_limit, outer_margin, pad_length)
    if final_validation:
        return fail('final mixed validation failed: ' + final_validation,
                    reference_scales=reference_scales, envelope=envelope)
    result = copy.deepcopy(best['layout'])
    # Keep the growth fit block as provenance; consumers use mixed.final_scales for the result.
    result['fit'] = copy.deepcopy(growth_checkpoint.get('fit'))
    result['mixed'] = {
        'algorithm': 'coordinated-mixed-v1',
        'validated': True,
        'diagnostic': None,
        'step': MIXED_STEP,
        'minimum_factor': MIXED_MIN_FACTOR,
        'maximum_factor': MIXED_MAX_FACTOR,
        'resize_penalty': MIXED_RESIZE_PENALTY,
        'search_budget': MIXED_SEARCH_BUDGET,
        'candidate_count': candidate_count,
        'search_seconds': round(search_seconds, 6),
        'valid_candidate_count': valid_count,
        'attempted_mixed_sign_directions': mixed_count,
        'accepted_mixed_sign_directions': accepted_mixed,
        'iterations': iterations,
        'stopping_reason': stopping_reason,
        'reference_scales': {key: round(value, 6) for key, value in reference_scales.items()},
        'minimum_scales': {key: round(value, 6) for key, value in lower_scales.items()},
        'maximum_scales': {key: round(value, 6) for key, value in upper_scales.items()},
        'native_min_text_sizes': native_text,
        'area_limit': round(area_limit, 6),
        'area_tolerance': round(_area_tolerance(growth_canvas), 6),
        'envelope': {key: round(value, 6) for key, value in envelope.items()},
        'selected_baseline': incumbent['label'],
        'baseline_growth': {
            'available': growth_base is not None,
            'diagnostic': growth_problem,
            'scales': growth_base['scales'] if growth_base else None,
            'metrics': growth_base['metrics'] if growth_base else None,
        },
        'baseline_shrink': {
            'available': shrink_base is not None,
            'diagnostic': shrink_problem,
            'scales': shrink_base['scales'] if shrink_base else None,
            'metrics': shrink_base['metrics'] if shrink_base else None,
        },
        'final_scales': dict(result['scales']),
        'final_metrics': _metrics(result, result['scales'], reference_scales, envelope,
                                  pad_length, outer_margin),
        'target_gap_total': target_metrics['gap']['total'],
        'target_canvas_occupancy': target_metrics['occupancy']['canvas'],
    }
    return result


__all__ = [
    'MIXED_MAX_FACTOR',
    'MIXED_MIN_FACTOR',
    'MIXED_RESIZE_PENALTY',
    'MIXED_SEARCH_BUDGET',
    'MIXED_STEP',
    'mixed_fit_layout',
]
