"""Mermaid figures: Pele's render of one source, and the Diagram checks that accept it.

Makes no provider call. ``papers/mermaid.js`` runs Pele in Node; the checks below read its report.
"""
import html
import json
import os
import shutil
import subprocess
import uuid
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
# Pele's colour variables in the light Figure palette: the export palette for PNG, PDF, and Kindle.
# app/static/app.css holds the same values for the page.
LIGHT_VARIABLES = {'--pele-bg': '#ffffff', '--pele-fg': '#243b32', '--pele-muted': '#627168', '--pele-line': '#7f9fb5',
                   '--pele-surface': '#fbfcfa', '--pele-surface-alt': '#f3f6f0', '--pele-border': '#c3ccbd',
                   '--pele-accent': '#2f6f5e'}


def draw(source, width, config=None):
    """Pele's render of ``source`` at ``width``, or ``{'ok': False, 'error': ...}`` when it does not parse."""
    node = shutil.which('node')
    if not node:
        # Not a ValueError: the correction loop would send a missing tool to the model as its mistake.
        raise RuntimeError('Install Node.js to draw figures.')
    result = subprocess.run([node, str(Path(__file__).with_name('mermaid.js'))],
                            input=json.dumps({'source': source, 'width': width, 'config': config}),
                            capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise RuntimeError('A figure could not be drawn: ' + result.stderr[-500:])
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


# The export page around a figure: the light palette, the title and subtitle above, the footer below.
PAGE_STYLE = (
    'html, body { margin: 0; background: #ffffff; } '
    'main { box-sizing: border-box; padding: 24px; color: #243b32; '
    'font: 14px/1.45 -apple-system, system-ui, sans-serif; } '
    'h1 { font-size: 26px; line-height: 1.2; margin: 0 0 6px; } p { margin: 0; } '
    '.subtitle { color: #627168; margin-bottom: 18px; } '
    '.footer { color: #627168; font-size: 12.5px; margin-top: 18px; } '
    'svg { display: block; max-width: 100%; height: auto; margin: 0 auto; } '
    f'.chart {{ margin-top: {CHART_GAP}px; }}')


def write_assets(directory, figure_id, result, *, width=1000, title='', subtitle='', footer=''):
    """Write the checked figure as PNG and PDF, through html-snapshot, and its main diagram as an editable SVG.

    Returns the paths relative to the Paper directory, where ``papers.exports`` reads them.
    """
    relative = Path('reader/overview-figures') / uuid.uuid4().hex / figure_id
    target = Path(directory) / relative
    target.parent.mkdir(parents=True)
    variables = ''.join(f'{name}: {value}; ' for name, value in LIGHT_VARIABLES.items())
    svg = result['diagram']['svg']
    opening = svg.index('>') + 1
    target.with_suffix('.source.svg').write_text(svg[:opening] + '<style>svg { ' + variables + '}</style>'
                                                 + svg[opening:])
    parts = [f'<h1>{html.escape(title)}</h1>' if title else '',
             f'<p class="subtitle">{html.escape(subtitle)}</p>' if subtitle else '', svg,
             f'<div class="chart">{result["chart"]["svg"]}</div>' if result.get('chart') else '',
             f'<p class="footer">{html.escape(footer)}</p>' if footer else '']
    target.with_suffix('.html').write_text(
        '<!doctype html><html><head><meta charset="utf-8"><meta name="localxiv-render-mode" content="page">'
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'">'
        f'<style>:root {{ {variables}--pele-font: -apple-system, system-ui, sans-serif; }} {PAGE_STYLE} '
        f'main {{ width: {width}px; }}</style></head><body><main>' + ''.join(parts) + '</main></body></html>')
    executable = os.environ.get('LOCALXIV_HTML_RENDERER') or str(Path(__file__).with_name('html-snapshot'))
    if not Path(executable).is_file():
        raise ValueError('HTML renderer is missing. Build papers/HTMLSnapshot.swift as papers/html-snapshot '
                         '(see development instructions).')
    rendered = subprocess.run([executable, str(target.with_suffix('.html')), str(target)],
                              capture_output=True, text=True, timeout=300)
    if rendered.returncode:
        raise ValueError('HTML rendering failed: ' + rendered.stderr[-1000:])
    if not target.with_suffix('.png').read_bytes().startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError('Renderer did not produce a PNG.')
    return {'png': str(relative) + '.png', 'pdf': str(relative) + '.pdf', 'svg_source': str(relative) + '.source.svg'}
