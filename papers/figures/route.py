"""Orthogonal arrow routing around boxes, and the label placement tests. Pure geometry."""
from papers.figures.layout import ARROW_GAP

ARROW_CLEARANCE = 4
# Two boxes closer than ARROW_GAP along an arrow leave no room for a turn and a straight run for
# the arrowhead, so the arrow runs straight through the middle of their overlap when the overlap
# is at least this wide.
OVERLAP_MIN = 20


class LayoutError(ValueError):
    """A scene that cannot be laid out: an arrow that cannot avoid the cards, or text that cannot fit."""


def segments(points):
    return list(zip(points, points[1:]))


def crosses(segment, box):
    (x1, y1), (x2, y2) = segment
    left, top, w, h = box
    right, bottom = left + w, top + h
    left -= ARROW_CLEARANCE
    top -= ARROW_CLEARANCE
    right += ARROW_CLEARANCE
    bottom += ARROW_CLEARANCE
    if x1 == x2:
        return left < x1 < right and min(y1, y2) < bottom and max(y1, y2) > top
    if y1 == y2:
        return top < y1 < bottom and min(x1, x2) < right and max(x1, x2) > left
    return True


def runs_along(segment, frame):
    """A segment that lies on a frame edge, within the arrow clearance, for more than a corner."""
    (x1, y1), (x2, y2) = segment
    left, top, w, h = frame
    right, bottom = left + w, top + h
    if y1 == y2:
        near_edge = abs(y1 - top) <= ARROW_CLEARANCE or abs(y1 - bottom) <= ARROW_CLEARANCE
        overlap = min(max(x1, x2), right) - max(min(x1, x2), left)
        return near_edge and overlap > 2 * ARROW_CLEARANCE
    if x1 == x2:
        near_edge = abs(x1 - left) <= ARROW_CLEARANCE or abs(x1 - right) <= ARROW_CLEARANCE
        overlap = min(max(y1, y2), bottom) - max(min(y1, y2), top)
        return near_edge and overlap > 2 * ARROW_CLEARANCE
    return False


def clear(points, obstacles, frames=()):
    return (not any(crosses(segment, box) for segment in segments(points) for box in obstacles)
            and not any(runs_along(segment, frame) for segment in segments(points) for frame in frames))



def route(source, target, obstacles, frames=(), soft=()):
    """An orthogonal path from the source box to the target box that crosses no other box.

    Candidates in order: straight, a Z through the gap between the boxes, an L, and a detour
    down the side of the source. Two boxes too close for a Z join straight through their overlap. The first clear candidate wins. ``obstacles`` excludes the two
    endpoints. ``frames`` are group frames an arrow may cross but never run along. ``soft`` boxes
    are group headings: the first card under a heading has its top center below the heading
    text, so a path avoids them when another path is clear and crosses them only otherwise.
    Raises ``LayoutError`` when nothing is clear.
    """
    sx, sy, sw, sh = source
    tx, ty, tw, th = target
    s_cx, s_cy, t_cx, t_cy = sx + sw / 2, sy + sh / 2, tx + tw / 2, ty + th / 2
    candidates = []
    across = _overlap_middle(sy, sh, ty, th)
    along = _overlap_middle(sx, sw, tx, tw)
    if sx + sw <= tx:  # target on the right
        x1, x2 = sx + sw, tx
        if abs(s_cy - t_cy) > 1 and x2 - x1 < ARROW_GAP and across is not None:
            candidates.append([(x1, across), (x2, across)])
        for fraction in (0.5, 0.3, 0.7, 0.15, 0.85):
            mid = x1 + (x2 - x1) * fraction
            candidates.append([(x1, s_cy), (mid, s_cy), (mid, t_cy), (x2, t_cy)] if abs(s_cy - t_cy) > 1
                              else [(x1, s_cy), (x2, s_cy)])
        # The gutter turn sits 12 before the target. Inside a headed frame that is 2 from the
        # frame's edge, so a second gutter turns 7 before the frame: the middle of the 14-unit
        # gap to a sibling frame on its left.
        gutters = [tx - 12] + [left - 7 for left, _, _, _ in frames if abs(tx - 12 - left) <= ARROW_CLEARANCE]
        for offset in (14, 28, 42, -14, -28, -42, 21, 35, -21, -35):
            side_y = (sy + sh if offset > 0 else sy) + offset
            exit_y = sy + sh if offset > 0 else sy
            # Down (or up) out of the source, along a lane, then in through the target's top or
            # bottom; or along the lane to the gutter before the target and in through its side.
            candidates.append([(s_cx, exit_y), (s_cx, side_y), (t_cx, side_y),
                               (t_cx, ty if side_y < ty else ty + th)])
            for gutter in gutters:
                candidates.append([(s_cx, exit_y), (s_cx, side_y), (gutter, side_y), (gutter, t_cy), (tx, t_cy)])
    elif tx + tw <= sx:  # target on the left
        x1, x2 = sx, tx + tw
        if abs(s_cy - t_cy) > 1 and x1 - x2 < ARROW_GAP and across is not None:
            candidates.append([(x1, across), (x2, across)])
        for fraction in (0.5, 0.3, 0.7):
            mid = x1 + (x2 - x1) * fraction
            candidates.append([(x1, s_cy), (mid, s_cy), (mid, t_cy), (x2, t_cy)] if abs(s_cy - t_cy) > 1
                              else [(x1, s_cy), (x2, s_cy)])
    if ty + th <= sy:  # target above
        y1, y2 = sy, ty + th
        if abs(s_cx - t_cx) >= 1 and y1 - y2 < ARROW_GAP and along is not None:
            candidates.append([(along, y1), (along, y2)])
        candidates.append([(s_cx, y1), (s_cx, y2)] if abs(s_cx - t_cx) < 1
                          else [(s_cx, y1), (s_cx, (y1 + y2) / 2), (t_cx, (y1 + y2) / 2), (t_cx, y2)])
        for side in (-14, 14, -21, 21, -35, 35):
            edge_x = (sx if side < 0 else sx + sw) + side
            candidates.append([(sx if side < 0 else sx + sw, s_cy), (edge_x, s_cy), (edge_x, t_cy),
                               (tx if side < 0 else tx + tw, t_cy)])
            candidates.append([(sx if side < 0 else sx + sw, s_cy), (edge_x, s_cy), (edge_x, y2 - 8),
                               (t_cx, y2 - 8), (t_cx, y2)])
    elif sy + sh <= ty:  # target below
        y1, y2 = sy + sh, ty
        if abs(s_cx - t_cx) >= 1 and y2 - y1 < ARROW_GAP and along is not None:
            candidates.append([(along, y1), (along, y2)])
        candidates.append([(s_cx, y1), (s_cx, y2)] if abs(s_cx - t_cx) < 1
                          else [(s_cx, y1), (s_cx, (y1 + y2) / 2), (t_cx, (y1 + y2) / 2), (t_cx, y2)])
        for side in (-14, 14, -21, 21, -35, 35):
            edge_x = (sx if side < 0 else sx + sw) + side
            candidates.append([(sx if side < 0 else sx + sw, s_cy), (edge_x, s_cy), (edge_x, t_cy),
                               (tx if side < 0 else tx + tw, t_cy)])
    if obstacles:
        # Around everything: a lane just above the topmost box or just below the bottommost.
        above = min(box[1] for box in obstacles + [source, target]) - 12
        below = max(box[1] + box[3] for box in obstacles + [source, target]) + 12
        candidates.append([(s_cx, sy), (s_cx, above), (t_cx, above), (t_cx, ty)])
        candidates.append([(s_cx, sy + sh), (s_cx, below), (t_cx, below), (t_cx, ty + th)])
    for hard in (obstacles + list(soft), obstacles):
        for points in candidates:
            if clear(points, hard, frames):
                return points
    raise LayoutError('an arrow cannot reach its target without crossing another card')


def _overlap_middle(start, length, other_start, other_length):
    """The middle of two spans' overlap, or None when the overlap is too narrow for an arrow."""
    low, high = max(start, other_start), min(start + length, other_start + other_length)
    return (low + high) / 2 if high - low >= OVERLAP_MIN else None


def label_fits(box, obstacles, frames):
    """A label overlaps no leaf and crosses no container edge."""
    if any(overlaps(box, other) for other in obstacles):
        return False
    return all(inside(box, frame) or not overlaps(box, frame) for frame in frames)


def inside(box, frame):
    x, y, w, h = box
    fx, fy, fw, fh = frame
    return x >= fx and y >= fy and x + w <= fx + fw and y + h <= fy + fh


def overlaps(box, other):
    x, y, w, h = box
    ox, oy, ow, oh = other
    return x < ox + ow and x + w > ox and y < oy + oh and y + h > oy
