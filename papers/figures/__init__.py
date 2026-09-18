"""The figure library: a Scene in, laid-out SVG, PNG, checks, and issues out."""
import re
from dataclasses import dataclass, field

from papers.figures import schema
from papers.figures.checks import MIN_TEXT_DENSITY, native_issues, text_density
from papers.figures.layout import Canvas
from papers.figures.measure import Measurer
from papers.figures.render import LayoutError, compose, rasterize
from papers.figures.schema import SceneError

__all__ = ['Figure', 'FigureResult', 'SceneError', 'LayoutError']
_SPACE = re.compile(r'\s+')


def _flat(value):
    return _SPACE.sub(' ', str(value)).strip().lower()


@dataclass
class FigureResult:
    svg: str
    assets: dict
    checks: dict
    placements: list
    density: float
    issues: list = field(default_factory=list)


class Figure:
    """Lay out, render, and check Scenes at one width. Makes no provider call."""

    def __init__(self, measurer_factory=None, *, width=1000):
        self.measurer_factory = measurer_factory or Measurer
        self.canvas = Canvas(width)

    @staticmethod
    def _page(value, frame):
        if frame == 'panel':
            return {'title': '', 'subtitle': '', 'footer': '', 'illustrative': False,
                    'layout': 'stack', 'panels': [value]}
        return value

    def validate(self, value, *, frame='page'):
        return schema.validate(value, frame=frame)

    def text(self, value, *, frame='page'):
        return schema.text(self._page(value, frame))

    def headings(self, value, *, frame='page'):
        return schema.headings(self._page(value, frame))

    def missing(self, value, required, *, frame='page'):
        """The required strings the scene does not show, compared after whitespace normalisation."""
        shown = _flat(' '.join(self.text(value, frame=frame)))
        return [item for item in required if _flat(item) not in shown]

    def build(self, value, directory, figure_id, *, frame='page', page_title=''):
        """Compose, rasterize, and check. Raises SceneError or LayoutError; defects are issues."""
        if frame == 'panel' and page_title:
            raise ValueError('page_title applies to frame page only')
        scene = self._page(self.validate(value, frame=frame), frame)
        measure = self.measurer_factory(directory)
        try:
            svg, placements = compose(measure, scene, self.canvas, frame=frame, page_title=page_title)
        finally:
            measure.close()
        assets = rasterize(directory, svg, figure_id, scene.get('title') or figure_id)
        checks = assets.pop('checks')
        density = text_density(checks)
        issues = native_issues(checks)
        if frame == 'page' and density < MIN_TEXT_DENSITY:
            issues.append('The figure is too sparse: ' + str(round(density, 1))
                          + ' text runs per million square units; the floor is ' + str(MIN_TEXT_DENSITY))
        return FigureResult(svg=svg, assets=assets, checks=checks, placements=placements,
                            density=density, issues=issues)
