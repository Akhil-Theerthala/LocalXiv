"""Orthogonal arrow routing around boxes, and the label placement tests. Pure geometry."""
import heapq
import itertools

from papers.figures.layout import ARROW_GAP

ARROW_CLEARANCE = 4
# Two boxes closer than ARROW_GAP along an arrow leave no room for a turn and a straight run for
# the arrowhead, so the arrow runs straight through the middle of their overlap when the overlap
# is at least this wide.
OVERLAP_MIN = 20
# The lane search's prices, in units of path length: a turn costs BEND, crossing the edge of a
# group frame that holds neither end costs UNRELATED, crossing an earlier arrow CROSSING, crossing
# a group heading HEADING, and a last run too short for the arrowhead SHORT_RUN.
BEND = 30
UNRELATED = 400
CROSSING = 60
HEADING = 300
SHORT_RUN = 150
# The arrowhead is about 10 units long and the arrow stops 3 short of its target.
ARROWHEAD_RUN = 13
# The middle of a 14-unit gap, where a lane between two boxes runs.
GAP_MIDDLE = 7


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
            if clear(points, hard, frames) and leaves_and_enters(points, source, target):
                return points
    raise LayoutError('an arrow cannot reach its target without crossing another card')


def leaves_and_enters(points, source, target):
    """The path leaves its source outward and enters its target from outside, and touches neither
    in between: obstacles exclude the two ends, so a lane could otherwise run through the target
    and reach its far side from within."""
    pieces = segments(points)
    if any(crosses(piece, target) for piece in pieces[:-1]) or any(crosses(piece, source) for piece in pieces[1:]):
        return False
    return _outward(pieces[0], source) and _outward(pieces[-1][::-1], target)


def _outward(piece, box):
    """A segment that starts on a side of the box and moves away from it."""
    (x1, y1), (x2, y2) = piece
    left, top, width, height = box
    if y1 == y2:
        return (x1 == left and x2 < x1) or (x1 == left + width and x2 > x1)
    return (y1 == top and y2 < y1) or (y1 == top + height and y2 > y1)


def _overlap_middle(start, length, other_start, other_length):
    """The middle of two spans' overlap, or None when the overlap is too narrow for an arrow."""
    low, high = max(start, other_start), min(start + length, other_start + other_length)
    return (low + high) / 2 if high - low >= OVERLAP_MIN else None


def defects(points, others, unrelated):
    """What makes a path hard to read, worst first, so that fewer compares as better.

    The number of its segments that share a line with an arrow in ``others``, the number of
    times it crosses the edge of a frame in ``unrelated``, the number of arrows in ``others`` it
    crosses, and whether its last run is too short for the arrowhead.
    """
    pieces = segments(points)
    theirs = [piece for path in others for piece in segments(path)]
    shared = sum(_shared(piece, other) > 1 for piece in pieces for other in theirs)
    entered = sum(_edges_crossed(piece, frame) for piece in pieces for frame in unrelated)
    crossed = sum(_crossing(piece, other) for piece in pieces for other in theirs)
    (ax, ay), (bx, by) = pieces[-1]
    return shared, entered, crossed, abs(bx - ax) + abs(by - ay) < ARROWHEAD_RUN


def search(source, target, obstacles, frames=(), soft=(), others=(), unrelated=(), bounds=None, siblings=()):
    """The cheapest orthogonal path along lanes between the boxes, or None when no path is clear.

    Lanes run through the middle of every gap between two box edges, through both boxes' centres
    and along their sides, and along the edges of ``bounds``, the area an arrow may use. The path
    leaves the middle of a source side, crosses no box in ``obstacles``, never runs along a frame
    edge or along an arrow in ``others``, and enters the middle of a target side. It may share a
    line with an arrow in ``siblings``, which leave the same source or enter the same target. Its
    price is its length plus the prices above for its turns, the edges it crosses of frames in
    ``unrelated``, the arrows in ``others`` or ``siblings`` it crosses, the headings in ``soft`` it
    crosses, and a short last run.
    """
    sx, sy, sw, sh = source
    tx, ty, tw, th = target
    s_cx, s_cy, t_cx, t_cy = sx + sw / 2, sy + sh / 2, tx + tw / 2, ty + th / 2
    walls = list(obstacles) + list(frames) + [source, target]
    xs = _lanes([(x, x + w) for x, _, w, _ in walls]) | {s_cx, t_cx, sx, sx + sw, tx, tx + tw}
    ys = _lanes([(y, y + h) for _, y, _, h in walls]) | {s_cy, t_cy, sy, sy + sh, ty, ty + th}
    # Half a gap outside every frame, for a frame with open space beside it: a path that leaves
    # the frame there and comes back in still ends with room for the arrowhead.
    xs |= {edge for x, _, w, _ in frames for edge in (x - GAP_MIDDLE, x + w + GAP_MIDDLE)}
    ys |= {edge for _, y, _, h in frames for edge in (y - GAP_MIDDLE, y + h + GAP_MIDDLE)}
    if bounds is None:
        xs |= {min(xs) - 12, max(xs) + 12}
        ys |= {min(ys) - 12, max(ys) + 12}
    else:
        left, top, width, height = bounds
        xs = {x for x in xs | {left, left + width} if left <= x <= left + width}
        ys = {y for y in ys | {top, top + height} if top <= y <= top + height}
    xs, ys = sorted(xs), sorted(ys)
    column, row = {x: index for index, x in enumerate(xs)}, {y: index for index, y in enumerate(ys)}
    theirs = [piece for path in others for piece in segments(path)]
    kin = [piece for path in siblings for piece in segments(path)]
    prices = {}

    def price(piece, first, last):
        """The price of one step between neighbouring lane points, or None when it is blocked."""
        key = (piece, first, last)
        if key in prices:
            return prices[key]
        blocked = (any(crosses(piece, box) for box in obstacles)
                   or (not first and crosses(piece, source)) or (not last and crosses(piece, target))
                   or any(_along(piece, frame) for frame in frames)
                   or any(_shared(piece, other) > 1 for other in theirs))
        prices[key] = None if blocked else (
            CROSSING * sum(_crossing_from(piece, other) for other in theirs + kin)
            + UNRELATED * sum(_edges_crossed(piece, frame) for frame in unrelated)
            + HEADING * sum(crosses(piece, box) for box in soft))
        return prices[key]

    def step(point, direction):
        (x, y), (dx, dy) = point, direction
        if dx:
            index = column[x] + dx
            return (xs[index], y) if 0 <= index < len(xs) else None
        index = row[y] + dy
        return (x, ys[index]) if 0 <= index < len(ys) else None

    starts = (((sx + sw, s_cy), (1, 0)), ((sx, s_cy), (-1, 0)), ((s_cx, sy + sh), (0, 1)), ((s_cx, sy), (0, -1)))
    goals = {((tx, t_cy), (1, 0)), ((tx + tw, t_cy), (-1, 0)), ((t_cx, ty), (0, 1)), ((t_cx, ty + th), (0, -1))}
    order = itertools.count()
    heap = [(0.0, next(order), (point, direction, 0.0)) for point, direction in starts]
    best = {state: 0.0 for _, _, state in heap}
    came = {}
    while heap:
        cost, _, state = heapq.heappop(heap)
        if state[0] == 'end':
            points, state = [state[1]], came[state]
            while state is not None:
                points.append(state[0])
                state = came.get(state)
            return _corners(points[::-1])
        if cost > best.get(state, float('inf')):
            continue
        point, direction, run = state
        first = (point, direction) in starts and run == 0
        (dx, dy) = direction
        for turn in ((direction,) if first else (direction, (dy, dx), (-dy, -dx))):
            after = step(point, turn)
            if after is None:
                continue
            last = (after, turn) in goals
            extra = price((point, after), first, last)
            if extra is None:
                continue
            length = abs(after[0] - point[0]) + abs(after[1] - point[1])
            straight = run + length if turn == direction else length
            total = cost + length + extra + (0 if turn == direction else BEND)
            if last:
                following = ('end', after, turn)
                total += SHORT_RUN if straight < ARROWHEAD_RUN else 0
            else:
                following = (after, turn, min(straight, ARROWHEAD_RUN))
            if total < best.get(following, float('inf')):
                best[following] = total
                came[following] = state
                heapq.heappush(heap, (total, next(order), following))
    return None


def _lanes(spans):
    """The middle of every gap wider than the clearance on both sides between consecutive edges."""
    edges = sorted({edge for span in spans for edge in span})
    return {(low + high) / 2 for low, high in zip(edges, edges[1:]) if high - low > 2 * ARROW_CLEARANCE}


def _corners(points):
    """The path without the points where it goes on straight."""
    kept = [points[0]]
    for before, point, after in zip(points, points[1:], points[2:]):
        if not (before[0] == point[0] == after[0] or before[1] == point[1] == after[1]):
            kept.append(point)
    return kept + [points[-1]]


def _shared(piece, other):
    """The length two axis-parallel segments share on one line."""
    (ax1, ay1), (ax2, ay2) = piece
    (bx1, by1), (bx2, by2) = other
    if ax1 == ax2 == bx1 == bx2:
        return min(max(ay1, ay2), max(by1, by2)) - max(min(ay1, ay2), min(by1, by2))
    if ay1 == ay2 == by1 == by2:
        return min(max(ax1, ax2), max(bx1, bx2)) - max(min(ax1, ax2), min(bx1, bx2))
    return 0


def _crossing(piece, other):
    """Whether a horizontal and a vertical segment cross inside both."""
    (ax1, ay1), (ax2, ay2) = piece
    (bx1, by1), (bx2, by2) = other
    if ay1 == ay2 and bx1 == bx2:
        return min(ax1, ax2) < bx1 < max(ax1, ax2) and min(by1, by2) < ay1 < max(by1, by2)
    if ax1 == ax2 and by1 == by2:
        return _crossing(other, piece)
    return False


def _crossing_from(step, other):
    """Whether a step crosses a segment inside it or at its first point, never at its last.

    Consecutive steps of a path meet at lane points, and another arrow can cross the path at one;
    this counts that crossing once, on the step that leaves the point.
    """
    (x1, y1), (x2, y2) = step
    (ox1, oy1), (ox2, oy2) = other
    if x1 == x2 and oy1 == oy2 and min(ox1, ox2) < x1 < max(ox1, ox2):
        return y1 <= oy1 < y2 if y2 > y1 else y2 < oy1 <= y1
    if y1 == y2 and ox1 == ox2 and min(oy1, oy2) < y1 < max(oy1, oy2):
        return x1 <= ox1 < x2 if x2 > x1 else x2 < ox1 <= x1
    return False


def _edges_crossed(piece, frame):
    """How many of the frame's edges a segment crosses."""
    (x1, y1), (x2, y2) = piece
    left, top, width, height = frame
    if y1 == y2 and top < y1 < top + height:
        return sum(min(x1, x2) < edge < max(x1, x2) for edge in (left, left + width))
    if x1 == x2 and left < x1 < left + width:
        return sum(min(y1, y2) < edge < max(y1, y2) for edge in (top, top + height))
    return 0


def _along(piece, frame):
    """A segment within the clearance of a frame edge, beside it for any length."""
    (x1, y1), (x2, y2) = piece
    left, top, width, height = frame
    if y1 == y2:
        near = abs(y1 - top) <= ARROW_CLEARANCE or abs(y1 - top - height) <= ARROW_CLEARANCE
        return near and min(max(x1, x2), left + width) - max(min(x1, x2), left) > 0
    near = abs(x1 - left) <= ARROW_CLEARANCE or abs(x1 - left - width) <= ARROW_CLEARANCE
    return near and min(max(y1, y2), top + height) - max(min(y1, y2), top) > 0


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
