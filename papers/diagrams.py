"""Mermaid figures: Pele's render of one source, and the Diagram checks that accept it.

Makes no provider call. ``papers/mermaid.js`` runs Pele in Node; the checks below read its report.
"""
import json
import shutil
import subprocess
from pathlib import Path

from papers.explanation import ValidationError

# The smallest text a reader can read at the figure's width, in units.
MIN_FONT = 11
# Width divided by height of the whole figure. The reference figures in docs/reference_images/ measure 0.60 to 1.06.
SHAPE = (0.6, 1.4)
MAX_WORDS = 8
# The result chart: Mermaid chart types only, drawn below the main diagram at a size the application sets.
CHART_TYPES = ('xychart', 'pie', 'quadrantChart', 'radar')
CHART_HEIGHT = 280
CHART_GAP = 24


def draw(source, width, config=None):
    """Pele's render of ``source`` at ``width``, or ``{'ok': False, 'error': ...}`` when it does not parse."""
    node = shutil.which('node')
    if not node:
        raise ValueError('Install Node.js to draw figures.')
    result = subprocess.run([node, str(Path(__file__).with_name('mermaid.js'))],
                            input=json.dumps({'source': source, 'width': width, 'config': config}),
                            capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise ValueError('A figure could not be drawn: ' + result.stderr[-500:])
    return json.loads(result.stdout)


def chart_config(width):
    """The size the application gives a result chart: as wide as the main diagram, CHART_HEIGHT high."""
    width = round(width)
    return {'xyChart': {'width': width, 'height': CHART_HEIGHT},
            'quadrantChart': {'chartWidth': min(width, CHART_HEIGHT), 'chartHeight': CHART_HEIGHT}}


def _flat(text):
    return ' '.join(str(text).replace('`', '').replace('$$', '').split()).lower()


def check(answer, *, width, required, chart_wanted=False, max_nodes=None):
    """Draw ``answer['mermaid']`` and its result chart, and raise ValidationError with every failed check."""
    issues = []

    def fail(path, message):
        issues.append({'code': 'diagram', 'path': path, 'message': message})

    if not isinstance(answer, dict) or not isinstance(answer.get('mermaid'), str):
        raise ValidationError([{'code': 'diagram', 'path': 'mermaid', 'message': 'mermaid must be a Mermaid source.'}])
    diagram = draw(answer['mermaid'], width)
    if not diagram['ok']:
        raise ValidationError([{'code': 'diagram', 'path': 'mermaid',
                                'message': 'Mermaid does not parse: ' + diagram['error'][:600]}])
    shown = _flat(' '.join(diagram['labels']))
    for item in required:
        if _flat(item) not in shown:
            fail('mermaid', 'The diagram does not show the plan item ' + json.dumps(item, ensure_ascii=False)
                 + '; write it exactly in a node label')
    starred = [node['text'] for node in diagram['nodes'] if '*' in node['text']]
    if starred:
        fail('mermaid', 'These labels show literal asterisks; for bold or italic use a markdown string such as '
             'A["`**bold** text`"]: ' + '; '.join(json.dumps(text, ensure_ascii=False) for text in starred[:5]))
    if max_nodes is not None and len(diagram['nodes']) > max_nodes:
        fail('mermaid', f'The diagram has {len(diagram["nodes"])} nodes; the limit is {max_nodes}.')
    long = [node['text'] for node in diagram['nodes'] if len(node['text'].split()) > MAX_WORDS]
    if long:
        fail('mermaid', f'These node labels have more than {MAX_WORDS} words: '
             + '; '.join(json.dumps(text, ensure_ascii=False) for text in long[:5]))
    scale = min(1, width / diagram['width'])
    if diagram['min_font'] * scale < MIN_FONT:
        fail('mermaid', f'At {width} px wide the smallest text draws at {diagram["min_font"] * scale:.1f} px; '
             f'the floor is {MIN_FONT}. Make the diagram narrower or the small text larger.')
    figure_width, figure_height = diagram['width'] * scale, diagram['height'] * scale

    chart = answer.get('chart')
    drawn_chart = config = None
    if chart_wanted and not chart:
        fail('chart', 'The plan has a result chart; write it as a Mermaid source in "chart".')
    if chart:
        config = chart_config(figure_width)
        drawn_chart = draw(chart, width, config)
        if not drawn_chart['ok']:
            fail('chart', 'The chart does not parse: ' + drawn_chart['error'][:400])
        elif drawn_chart['type'] not in CHART_TYPES:
            fail('chart', f'The chart is a {drawn_chart["type"]} diagram; '
                 'use xychart, pie, quadrantChart, or radar-beta.')
        else:
            chart_scale = min(1, width / drawn_chart['width'])
            if drawn_chart['min_font'] * chart_scale < MIN_FONT:
                fail('chart', f'The chart text draws at {drawn_chart["min_font"] * chart_scale:.1f} px; '
                     f'the floor is {MIN_FONT}.')
            figure_width = max(figure_width, drawn_chart['width'] * chart_scale)
            figure_height += CHART_GAP + drawn_chart['height'] * chart_scale

    shape = figure_width / figure_height
    what = 'figure (diagram and chart)' if chart else 'diagram'
    size = f'{round(figure_width)} × {round(figure_height)} px'
    if shape < SHAPE[0]:
        fail('mermaid', f'The {what} is {size}: too tall for its width (width ÷ height {shape:.2f}; keep it '
             f'between {SHAPE[0]} and {SHAPE[1]}). Put nodes side by side, use a left-to-right direction for a part '
             'of it, or place subgraphs next to each other.')
    elif shape > SHAPE[1]:
        fail('mermaid', f'The {what} is {size}: too wide for its height (width ÷ height {shape:.2f}; keep it '
             f'between {SHAPE[0]} and {SHAPE[1]}). Stack parts of it, use a top-to-bottom direction for a part of '
             'it, or place subgraphs above each other.')
    if issues:
        raise ValidationError(issues)
    return {'diagram': diagram, 'chart': drawn_chart, 'chart_config': config,
            'figure': {'width': round(figure_width), 'height': round(figure_height)}}
