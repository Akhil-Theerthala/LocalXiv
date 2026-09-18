"""Orthogonal arrow routing around boxes, and the label placement tests. Pure geometry."""
ARROW_CLEARANCE = 4


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


def clear(points, obstacles):
    return not any(crosses(segment, box) for segment in segments(points) for box in obstacles)



def route(source, target, obstacles):
    """An orthogonal path from the source box to the target box that crosses no other box.

    Candidates in order: straight, a Z through the gap between the boxes, an L, and a detour
    down the side of the source. The first clear candidate wins. ``obstacles`` excludes the two
    endpoints. Raises ``LayoutError`` when nothing is clear.
    """
    sx, sy, sw, sh = source
    tx, ty, tw, th = target
    s_cx, s_cy, t_cx, t_cy = sx + sw / 2, sy + sh / 2, tx + tw / 2, ty + th / 2
    candidates = []
    if sx + sw <= tx:  # target on the right
        x1, x2 = sx + sw, tx
        for fraction in (0.5, 0.3, 0.7, 0.15, 0.85):
            mid = x1 + (x2 - x1) * fraction
            candidates.append([(x1, s_cy), (mid, s_cy), (mid, t_cy), (x2, t_cy)] if abs(s_cy - t_cy) > 1
                              else [(x1, s_cy), (x2, s_cy)])
        for offset in (14, 28, 42, -14, -28, -42):
            side_y = (sy + sh if offset > 0 else sy) + offset
            exit_y = sy + sh if offset > 0 else sy
            # Down (or up) out of the source, along a lane, then in through the target's top or
            # bottom; or along the lane to the gutter before the target and in through its side.
            candidates.append([(s_cx, exit_y), (s_cx, side_y), (t_cx, side_y),
                               (t_cx, ty if side_y < ty else ty + th)])
            candidates.append([(s_cx, exit_y), (s_cx, side_y), (tx - 12, side_y), (tx - 12, t_cy), (tx, t_cy)])
    elif tx + tw <= sx:  # target on the left
        x1, x2 = sx, tx + tw
        for fraction in (0.5, 0.3, 0.7):
            mid = x1 + (x2 - x1) * fraction
            candidates.append([(x1, s_cy), (mid, s_cy), (mid, t_cy), (x2, t_cy)] if abs(s_cy - t_cy) > 1
                              else [(x1, s_cy), (x2, s_cy)])
    if ty + th <= sy:  # target above
        y1, y2 = sy, ty + th
        candidates.append([(s_cx, y1), (s_cx, y2)] if abs(s_cx - t_cx) < 1
                          else [(s_cx, y1), (s_cx, (y1 + y2) / 2), (t_cx, (y1 + y2) / 2), (t_cx, y2)])
        for side in (-14, 14):
            edge_x = (sx if side < 0 else sx + sw) + side
            candidates.append([(sx if side < 0 else sx + sw, s_cy), (edge_x, s_cy), (edge_x, t_cy),
                               (tx if side < 0 else tx + tw, t_cy)])
            candidates.append([(sx if side < 0 else sx + sw, s_cy), (edge_x, s_cy), (edge_x, y2 - 8),
                               (t_cx, y2 - 8), (t_cx, y2)])
    elif sy + sh <= ty:  # target below
        y1, y2 = sy + sh, ty
        candidates.append([(s_cx, y1), (s_cx, y2)] if abs(s_cx - t_cx) < 1
                          else [(s_cx, y1), (s_cx, (y1 + y2) / 2), (t_cx, (y1 + y2) / 2), (t_cx, y2)])
        for side in (-14, 14):
            edge_x = (sx if side < 0 else sx + sw) + side
            candidates.append([(sx if side < 0 else sx + sw, s_cy), (edge_x, s_cy), (edge_x, t_cy),
                               (tx if side < 0 else tx + tw, t_cy)])
    if obstacles:
        # Around everything: a lane just above the topmost box or just below the bottommost.
        above = min(box[1] for box in obstacles + [source, target]) - 12
        below = max(box[1] + box[3] for box in obstacles + [source, target]) + 12
        candidates.append([(s_cx, sy), (s_cx, above), (t_cx, above), (t_cx, ty)])
        candidates.append([(s_cx, sy + sh), (s_cx, below), (t_cx, below), (t_cx, ty + th)])
    for points in candidates:
        if clear(points, obstacles):
            return points
    raise LayoutError('an arrow cannot reach its target without crossing another card')


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
