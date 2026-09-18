"""Compatibility aliases until the workflows import papers.figures directly."""
import copy

from papers.figures.layout import Canvas
from papers.figures.measure import Measurer
from papers.figures.render import LayoutError as SceneLayoutError, compose  # noqa: F401
from papers.figures.schema import headings as scene_headings, text as scene_text  # noqa: F401


def compose_scene(directory, paper_title, scene, *, with_tree=False):
    scene = copy.deepcopy(scene)
    measure = Measurer(directory)
    try:
        svg, placements = compose(measure, scene, Canvas(1000), frame='page', page_title=paper_title)
    finally:
        measure.close()
    return (svg, placements, scene) if with_tree else (svg, placements)
