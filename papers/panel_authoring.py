"""Panel authoring: one drawing assignment, at most two references, one SVG response, local checks.

A panel author receives one complete assignment, at most two relevant complete reference
examples, the construction notes, and the output contract. It never sees the paper, the
planning history, or another panel's brief, and it cannot ask for a narrative change.

``request_panel`` performs one network request and never renders: the coordinator owns native
rendering, persistence, and repair scheduling.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from papers.ai import ProviderError
from papers.explanation import PANEL_CONSTRUCTION_FAMILIES
from papers.html_figures import (PANEL_BODY_FONT_SIZE, PANEL_MINIMUM_FONT_SIZE, SHARED_MARKER_IDS,
                                 SVGValidationError, measure_text_widths, normalize_panel_svg,
                                 render, svg_visible_text)
from papers.overview import parse_json

GUIDE_DIRECTORY = Path(__file__).with_name('panel-guides')
CONSTRUCTION_FAMILIES = PANEL_CONSTRUCTION_FAMILIES
# A panel learns best from its own pattern plus one neighbouring pattern, never from a wall
# of examples. One to two complete examples per request is the budget.
MAX_EXAMPLES_PER_PANEL = 2
RELATED_FAMILIES = {'flow': ('comparison',), 'mapping': ('flow',), 'comparison': ('flow',),
                    'calculation': ('chart',), 'chart': ('calculation',)}

PANEL_SYSTEM = '''You draw one panel of a paper overview as a complete SVG document. The
assignment, the reference examples, and the construction notes are the whole specification: draw
what the assignment asks for, keep every exact name, equation, and number it gives you, and choose
the geometry yourself. You cannot change the story, ask for the paper text, or revise another
panel. Return one JSON object: {"panel_id": "<the assignment id>", "svg": "<one complete svg
document>"}. The svg value is a JSON string, so its quotes are escaped exactly once; the parsed
value must be a well-formed, self-contained SVG document. Never return prose or commentary.'''

OUTPUT_CONTRACT = '''Return one JSON object with exactly two fields:

{"panel_id": "%(id)s", "svg": "<svg xmlns=\\"http://www.w3.org/2000/svg\\" viewBox=\\"0 0 W H\\" font-family=\\"Arial, sans-serif\\" font-size=\\"18\\" fill=\\"#243b32\\">...</svg>"}

The svg string contains this panel only: no page border, no card, no reading-order number, no
header or caption, and no reference to another panel. Build it from the shapes in the construction
notes, or use the shared arrow markers url(#arrow), url(#arrow-muted), and url(#arrow-accent)
without defining any defs or markers of your own.'''


def _read(name):
    path = GUIDE_DIRECTORY / name
    if not path.is_file():
        raise ValueError('Missing panel guide file: ' + str(path))
    return path.read_text()


def authoring_guide():
    """The short common drawing guide."""
    return _read('authoring.md')


def construction_notes():
    """Concise SVG construction notes for the supported profile."""
    return _read('svg-reference.md')


def guide_examples():
    """Every complete reference example, in family order."""
    return [{'family': family, 'path': str(Path('papers/panel-guides') / (family + '.svg')),
             'svg': _read(family + '.svg')} for family in CONSTRUCTION_FAMILIES]


def reference_examples(family, *, limit=MAX_EXAMPLES_PER_PANEL):
    """The example for this construction family plus at most one related pattern."""
    if family not in CONSTRUCTION_FAMILIES:
        raise ValueError('Unknown construction family: ' + str(family))
    order = [family, *RELATED_FAMILIES.get(family, ())]
    examples = {example['family']: example for example in guide_examples()}
    return [examples[name] for name in order[:limit]]


def assignment_block(assignment):
    """The drawing assignment: exactly what this panel must contain."""
    lines = ['DRAWING ASSIGNMENT', 'panel id: ' + str(assignment['id']),
             'panel title: ' + str(assignment['title']),
             'construction: ' + str(assignment['construction']),
             'purpose: ' + str(assignment['purpose'])]
    if assignment.get('entry_context'):
        lines.append('the reader already has: ' + ' '.join(assignment['entry_context']))
    if assignment.get('shared_facts'):
        lines.append('exact values and notation to use unchanged:')
        lines += ['  - ' + value for value in assignment['shared_facts'].values()]
    if assignment.get('illustrative_values'):
        lines.append('illustrative teaching values, never reported as paper results:')
        lines += ['  - ' + value for value in assignment['illustrative_values']]
    lines.append('content to draw, in this order:')
    for item in assignment['content']:
        lines.append('  - [' + str(item['kind']) + '] ' + str(item['text']))
    lines.append('this panel must leave the reader with: ' + str(assignment['exit_state']))
    return '\n'.join(lines)


def panel_messages(assignment, *, previous=None, issues=(), image=None):
    """The complete panel request, in prompt order: assignment, example, notes, contract."""
    parts = [assignment_block(assignment)]
    for example in reference_examples(assignment['construction']):
        parts.append('COMPLETE REFERENCE EXAMPLE · ' + example['family'].upper() + '\n' + example['svg'])
    parts.append('APPLICABLE CONSTRUCTION NOTES\n' + construction_notes())
    parts.append('COMMON DRAWING GUIDE\n' + authoring_guide())
    parts.append(OUTPUT_CONTRACT % {'id': assignment['id']})
    if previous is not None or issues:
        parts.append('PREVIOUS DRAWING TO REPAIR\n' + (str(previous) if previous else '(no usable drawing was returned)'))
        parts.append('DEFECTS TO FIX IN THIS DRAWING ONLY\n'
                     + '\n'.join('- ' + str(issue) for issue in (issues or ['the drawing was rejected']))
                     + '\nChange only what these defects require. Keep everything the assignment '
                       'already satisfied, and keep the same construction and values.')
    content = '\n\n'.join(parts)
    if image:
        content = [{'type': 'text', 'text': content},
                   {'type': 'image_url', 'image_url': {'url': image}}]
    return [{'role': 'system', 'content': PANEL_SYSTEM}, {'role': 'user', 'content': content}]


def error_kind(message):
    """Separate an unusable drawing from an infrastructure failure."""
    text = str(message)
    if 'authentication' in text.lower() or 'HTTP status 401' in text or 'HTTP status 403' in text:
        return 'authentication'
    return 'transport'


def request_panel(provider, assignment, *, previous=None, issues=(), image=None):
    """One network request for one panel. Returns source, error, usage, and diagnostics.

    No rendering, no persistence, and no shared writes happen here, so the coordinator can run
    this inside a request worker.
    """
    diagnostics = {'panel_id': assignment['id'], 'repair': previous is not None,
                   'issues': [str(issue) for issue in issues]}
    try:
        response = provider.complete(panel_messages(assignment, previous=previous, issues=issues,
                                                    image=image), json_object=True)
    except ProviderError as error:
        diagnostics['error_kind'] = error_kind(error)
        return {'source': None, 'error': str(error)[:500], 'error_kind': diagnostics['error_kind'],
                'usage': {}, 'diagnostics': diagnostics}
    usage = response.get('usage', {}) if isinstance(response, dict) else {}
    try:
        value = parse_json(response.get('text', ''))
    except (ValueError, TypeError) as error:
        diagnostics['error_kind'] = 'invalid_output'
        diagnostics['reason'] = str(error)
        return {'source': None, 'error': str(error)[:500], 'error_kind': 'invalid_output',
                'usage': usage, 'diagnostics': diagnostics}
    if not isinstance(value, dict) or value.get('panel_id') != assignment['id']:
        reason = ('The response did not draw panel ' + str(assignment['id'])
                  + '; its panel_id was ' + json.dumps(value.get('panel_id') if isinstance(value, dict) else None))
        diagnostics.update(error_kind='invalid_output', reason=reason)
        return {'source': None, 'error': reason, 'error_kind': 'invalid_output',
                'usage': usage, 'diagnostics': diagnostics}
    try:
        source = normalize_panel_svg(value.get('svg'))
    except (SVGValidationError, ValueError, TypeError) as error:
        issues_detail = [issue['message'] for issue in getattr(error, 'issues', [])] or [str(error)]
        diagnostics.update(error_kind='invalid_output', issues=issues_detail)
        return {'source': None, 'error': '; '.join(issues_detail)[:500], 'error_kind': 'invalid_output',
                'usage': usage, 'diagnostics': diagnostics}
    diagnostics['error_kind'] = None
    return {'source': source, 'error': None, 'error_kind': None, 'usage': usage,
            'diagnostics': diagnostics}


NUMBER_TOKEN = re.compile(r'\d[\d,]*(?:\.\d+)?')


def required_values(assignment):
    """Exact display values that must survive into the drawing.

    Shared facts keep their canonical display text, and a value or equation item keeps every
    number it states, so an author may choose their own wording and geometry around them.
    """
    values = [value for value in (assignment.get('shared_facts') or {}).values()
              if isinstance(value, str) and value.strip()]
    for item in assignment['content']:
        if item['kind'] in ('value', 'equation'):
            values.extend(NUMBER_TOKEN.findall(item['text']))
    return list(dict.fromkeys(value for value in values if value.strip()))


def _flatten(text):
    return ' '.join(str(text).split())


def missing_values(assignment, labels):
    """Which exact display values are absent from the drawing's visible text."""
    recorded = _flatten(' '.join(labels))
    missing = []
    for value in required_values(assignment):
        if re.fullmatch(r'\d[\d,]*(?:\.\d+)?', value):
            if not re.search(r'(?<![\d.,])' + re.escape(value) + r'(?![\d])', recorded):
                missing.append(value)
        elif _flatten(value) not in recorded:
            missing.append(value)
    return missing


def check_panel(source, directory, panel_id):
    """Render one panel through the native helper and report its measured geometry."""
    normalized = normalize_panel_svg(source)
    figure = {'id': panel_id, 'title': 'Panel ' + str(panel_id), 'paper_connection': '',
              'caption': '', 'illustrative': False, 'source_svg': normalized}
    result = render(directory, figure, '', mode='panel')
    labels = [text for _, text in svg_visible_text(normalized, external_markers=SHARED_MARKER_IDS,
                                                   profile='panel')]
    return {'source': normalized, 'assets': {key: value for key, value in result.items() if key != 'checks'},
            'checks': result['checks'], 'labels': labels}


def _wrap(directory, text, width, font_size):
    """Wrap text to a measured pixel width using the renderer's own font."""
    words = str(text).split()
    if not words:
        return []
    measured = measure_text_widths(directory, words, font_size=font_size)
    space = measure_text_widths(directory, [' '], font_size=font_size)[0]
    lines, current, used = [], [], 0.0
    for word, size in zip(words, measured):
        if current and used + space + size > width:
            lines.append(' '.join(current))
            current, used = [], 0.0
        current.append(word)
        used += (space if used else 0.0) + size
    if current:
        lines.append(' '.join(current))
    return lines


SIMPLE_CANVAS_WIDTH = 900
SIMPLE_MARGIN = 40
SIMPLE_LINE_HEIGHT = 26


def _svg_text(x, y, text, size, weight=None):
    attributes = f'x="{x}" y="{y}" font-size="{size}"'
    if weight:
        attributes += f' font-weight="{weight}"'
    return f'<text {attributes}>{text}</text>'


def simple_panel_source(assignment, directory):
    """An application-owned text panel: measured wrapping, the same typography, no model.

    Used only after a panel's drawing repair still fails. It keeps the title, the approved
    content, and the canonical values, and marks illustrative numbers as illustrative.
    """
    width = SIMPLE_CANVAS_WIDTH - 2 * SIMPLE_MARGIN
    body = []
    y = 60
    title_lines = _wrap(directory, assignment['title'], width, 22)
    for line in title_lines:
        body.append(_svg_text(SIMPLE_MARGIN, y, line, 22, 700))
        y += 30
    y += 8
    for item in assignment['content']:
        weight = 700 if item['kind'] in ('value', 'equation') else None
        for line in _wrap(directory, item['text'], width, PANEL_BODY_FONT_SIZE):
            body.append(_svg_text(SIMPLE_MARGIN, y, line, PANEL_BODY_FONT_SIZE, weight))
            y += SIMPLE_LINE_HEIGHT
        y += 6
    facts = list((assignment.get('shared_facts') or {}).items())
    if facts:
        y += 4
        body.append(_svg_text(SIMPLE_MARGIN, y, 'values used here', PANEL_MINIMUM_FONT_SIZE, 700))
        y += SIMPLE_LINE_HEIGHT
        for _, value in facts:
            for line in _wrap(directory, value, width, PANEL_MINIMUM_FONT_SIZE):
                body.append(_svg_text(SIMPLE_MARGIN, y, line, PANEL_MINIMUM_FONT_SIZE))
                y += 22
        if any(fact in assignment.get('illustrative_values', []) for _, fact in facts):
            y += 4
            body.append(_svg_text(SIMPLE_MARGIN, y, 'illustrative values, not paper results',
                                  PANEL_MINIMUM_FONT_SIZE))
            y += 22
    height = max(160, int(y + SIMPLE_MARGIN - SIMPLE_LINE_HEIGHT))
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + str(SIMPLE_CANVAS_WIDTH) + ' '
            + str(height) + '" font-family="Arial, sans-serif" font-size="18" fill="#243b32" '
            'role="img" aria-label="' + _attribute_text(assignment['title']) + '">'
            + ''.join(body) + '</svg>')


def _attribute_text(value):
    return (str(value).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            .replace('"', '&quot;'))


def simple_panel(assignment, directory):
    """Render the application-owned fallback through the same local check as a drawn panel."""
    result = check_panel(simple_panel_source(assignment, directory), directory, assignment['id'])
    result['simplified'] = True
    return result
