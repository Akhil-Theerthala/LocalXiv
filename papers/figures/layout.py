"""The layout units, the canvas a Scene lays out at, and the helpers the node classes in nodes.py share."""
import math
import re
from dataclasses import dataclass, field

PANEL_GAP = 16
PANEL_PAD = 14
CHIP_HEIGHT = 26
BODY, CHIP, TITLE, SUBTITLE = 14, 15, 26, 15
LINE = {14: 18, 15: 20, 26: 31}
CARD_PAD_X, CARD_PAD_Y = 10, 7
CARD_MAX_DETAIL = 300
GAP = 14
ROW_GAP = 14
STRETCH_RATIO_MAX = 1.8
SEQUENCE_GAP = 6
GRID_CELL = 34
BAR_ROW = 22
CHART_WIDTH = 300
CHART_HEIGHT = 140
ARROW_CLEARANCE = 4
NOTES_GAP = 24

# The renderer numbers steps itself. A model that numbers them too gets its number removed
# here, not in the schema, so coverage still matches the raw line. "3.5 days" keeps its 3.
STEP_NUMBER = re.compile(r'^\s*\d{1,2}[.)]\s+')


def step_text(line):
    return STEP_NUMBER.sub('', str(line)) or str(line)


@dataclass(frozen=True)
class Canvas:
    """The width a figure lays out at. Text is never scaled, so this is the reader's width."""
    width: int
    margin: int = 24
    column: int = field(init=False)
    # A card in a column stretches to its siblings' width, but never past this, so a wide row
    # elsewhere in the container does not turn its neighbours into empty bars. 460 of 952 on the
    # 1000-unit page; the same share of a narrower canvas.
    stretch_max: int = field(init=False)

    def __post_init__(self):
        object.__setattr__(self, 'column', self.width - 2 * self.margin)
        object.__setattr__(self, 'stretch_max', round(self.column * 460 / 952))


def chart_ticks(node):
    """The y tick values at a round step that covers every point, and the x range labels."""
    ys = [point[1] for item in node['series'] for point in item['points']]
    xs = [point[0] for item in node['series'] for point in item['points']]
    low, high = min(ys), max(ys)
    span = (high - low) or abs(high) or 1.0
    raw = span / 3
    magnitude = 10 ** math.floor(math.log10(raw))
    step = next(candidate * magnitude for candidate in (1, 2, 2.5, 5, 10) if candidate * magnitude >= raw)
    first = math.floor(low / step) * step
    count = int(math.ceil((high - first) / step - 1e-9)) + 1
    ticks = [first + index * step for index in range(max(count, 2))]
    return ([f'{round(tick, 10):g}' for tick in ticks], [f'{min(xs):g}', f'{max(xs):g}'])


# A column body that spans less than this share of its panel, with at least this many nodes,
# is reflowed into two side-by-side columns. The scene keeps its order: first half left.
REFLOW_FILL = 0.55
REFLOW_MIN_NODES = 4


def _stretch_limit(node, canvas):
    """How wide a node may stretch: a cap on the absolute width and on growth from its natural width."""
    return min(canvas.stretch_max, node.w * STRETCH_RATIO_MAX)
