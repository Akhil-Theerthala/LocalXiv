"""Panel authoring: one drawing assignment, at most two references, one SVG response, local checks.

A panel author receives one complete assignment, at most two relevant complete reference
examples, the construction notes, and the output contract. It never sees the paper, the
planning history, or another panel's brief, and it cannot ask for a narrative change. The
assignment's labels are the whole text of the drawing; the checks reject a missing label and,
for an Overview panel, text beyond the assignment.

``request_panel`` performs one network request and never renders: the coordinator owns native
rendering, persistence, and repair scheduling.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

from papers.ai import ProviderError
from papers.explanation import PANEL_CONSTRUCTION_FAMILIES
from papers.html_figures import (PANEL_DISPLAY_WIDTH, SHARED_MARKER_IDS, SVGValidationError,
                                 fit_canvas, normalize_panel_svg, render, svg_visible_text)
from papers.overview import parse_json

GUIDE_DIRECTORY = Path(__file__).with_name('panel-guides')
CONSTRUCTION_FAMILIES = PANEL_CONSTRUCTION_FAMILIES
# The two authoring purposes: an Overview panel and a standalone Blog figure. Everything else
# (system prompt, examples, notes, guide, output contract) is shared between them.
PANEL_PURPOSES = ('overview', 'blog')
# A panel learns best from its own pattern plus one neighbouring pattern, never from a wall
# of examples. One to two complete examples per request is the budget.
MAX_EXAMPLES_PER_PANEL = 2
RELATED_FAMILIES = {'flow': ('comparison',), 'mapping': ('flow',), 'comparison': ('flow',),
                    'calculation': ('chart',), 'chart': ('calculation',)}

PANEL_SYSTEM = '''You draw one panel of a paper overview as a complete SVG document. The
assignment, the reference examples, and the construction notes are the whole specification: draw
the assignment's labels exactly as written, show its relations as geometry, and choose the layout
yourself. The application scales your panel to the reader's column, so draw at whatever size
lays out cleanly. You cannot change the story, ask for the paper text, or revise another panel. Return one JSON object: {"panel_id": "<the assignment id>", "svg": "<one complete svg
document>"}. The svg value is a JSON string, so its quotes are escaped exactly once; the parsed
value must be a well-formed, self-contained SVG document. Never return prose or commentary.'''

OUTPUT_CONTRACT = '''Return one JSON object with exactly two fields:

{"panel_id": "%(id)s", "svg": "<svg xmlns=\\"http://www.w3.org/2000/svg\\" viewBox=\\"0 0 W H\\" font-family=\\"Arial, sans-serif\\" font-size=\\"18\\" fill=\\"#243b32\\">...</svg>"}

The svg string contains this panel only: no page border, no card, no heading, no reading-order
number, no caption, and no reference to another panel. Build it from the shapes in the construction
notes, or use the shared arrow markers url(#arrow), url(#arrow-muted), and url(#arrow-accent)
without defining any defs or markers of your own.'''

BLOG_FIGURE_GUIDANCE = '''BLOG FIGURE GUIDANCE
This figure is displayed 640px wide in a Blog article; the application scales it to that width
and rejects any label that then falls below 14px. The application owns the article, the caption,
and the figure placement, so draw the figure only. Figure text is limited to the labels above,
short arrow labels, values, and necessary equations; context and explanation belong in the article.'''


REPAIR_ORDER = '''Fix them in this order. First remove: delete text that is not an assignment label,
relation label, or note; drop decoration; merge boxes that carry one idea. Then shorten: wrap a
label that escapes its box into tspan lines, or give it a wider box by taking room from empty
space. Only when removal and wrapping cannot fix a defect, enlarge the canvas. Keep every
assignment label unchanged and keep the same construction.'''


def _validated_purpose(purpose):
    """Reject an authoring purpose outside the two supported workflows."""
    if purpose not in PANEL_PURPOSES:
        raise ValueError('Unknown panel authoring purpose: ' + str(purpose))
    return purpose


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


def assignment_block(assignment, *, purpose='overview'):
    """The drawing assignment: exactly what this panel must contain.

    Both purposes share the shape: heading, purpose, labels, relations, and an optional note.
    A Blog assignment adds the article context, the takeaway, the layout intent, semantic content
    lines, and illustrative values; an Overview assignment adds the one-line figure story.
    """
    _validated_purpose(purpose)
    lines = ['DRAWING ASSIGNMENT', 'panel id: ' + str(assignment['id']),
             'heading (the application draws it above the panel; do not draw it): '
             + str(assignment['heading']),
             'construction: ' + str(assignment['construction']),
             'purpose: ' + str(assignment['purpose'])]
    if assignment.get('layout_intent'):
        lines.append('layout intent: ' + str(assignment['layout_intent']))
    if assignment.get('context'):
        lines.append('the reader already has: ' + str(assignment['context']))
    lines.append('labels, each of which must appear in the drawing exactly as written, in its own '
                 'text element:')
    lines += ['  - ' + value for value in assignment['labels']]
    if assignment.get('relations'):
        lines.append('relations to show as arrows or alignment (an arrow may carry the short label):')
        lines += ['  - ' + relation['from'] + ' → ' + relation['to']
                  + (' (' + relation['label'] + ')' if relation.get('label') else '')
                  for relation in assignment['relations']]
    if assignment.get('note'):
        lines.append('note, one line of muted text inside the panel: ' + str(assignment['note']))
    if assignment.get('content'):
        lines.append('content to express visually; the sentence itself need not appear:')
        lines += ['  - ' + value for value in assignment['content']]
    if assignment.get('illustrative_values'):
        lines.append('illustrative teaching values, never reported as paper results:')
        lines += ['  - ' + value for value in assignment['illustrative_values']]
    if assignment.get('takeaway'):
        lines.append('this figure must leave the reader with: ' + str(assignment['takeaway']))
    if purpose == 'blog':
        lines.append(BLOG_FIGURE_GUIDANCE)
    else:
        lines.append('Draw no text beyond the labels, the relation labels, and the note. Explanation '
                     'lives in the figure subtitle and footer, which the application draws.')
        if assignment.get('story'):
            lines.append('FIGURE STORY, orientation only, not text to draw: ' + str(assignment['story']))
    return '\n'.join(lines)


def panel_messages(assignment, *, previous=None, issues=(), image=None, purpose='overview'):
    """The complete panel request, in prompt order: assignment, example, notes, contract."""
    _validated_purpose(purpose)
    parts = [assignment_block(assignment, purpose=purpose)]
    for example in reference_examples(assignment['construction']):
        parts.append('COMPLETE REFERENCE EXAMPLE · ' + example['family'].upper() + '\n' + example['svg'])
    parts.append('APPLICABLE CONSTRUCTION NOTES\n' + construction_notes())
    parts.append('COMMON DRAWING GUIDE\n' + authoring_guide())
    parts.append(OUTPUT_CONTRACT % {'id': assignment['id']})
    if previous is not None or issues:
        parts.append('PREVIOUS DRAWING TO REPAIR\n' + (str(previous) if previous else '(no usable drawing was returned)'))
        parts.append('DEFECTS TO FIX IN THIS DRAWING ONLY\n'
                     + '\n'.join('- ' + str(issue) for issue in (issues or ['the drawing was rejected']))
                     + '\n' + REPAIR_ORDER)
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


def request_panel(provider, assignment, *, previous=None, issues=(), image=None, options=None,
                  purpose='overview'):
    """One network request for one panel. Returns source, error, usage, and diagnostics.

    ``options`` are the provider-level request options for this stage (for example a reasoning
    policy). They are forwarded exactly and never inferred here, so the workflow module owns the
    policy and this module stays free of workflow imports.

    No rendering, no persistence, and no shared writes happen here, so the coordinator can run
    this inside a request worker.
    """
    _validated_purpose(purpose)
    diagnostics = {'panel_id': assignment['id'], 'repair': previous is not None,
                   'issues': [str(issue) for issue in issues],
                   'options': dict(options or {})}
    try:
        response = provider.complete(panel_messages(assignment, previous=previous, issues=issues,
                                                    image=image, purpose=purpose), json_object=True,
                                     **(options or {}))
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


def _flatten(text):
    return ' '.join(str(text).split())


def _normalized_display(text):
    """The comparison form of one label: whitespace-normalized and XML-entity-decoded only."""
    return _flatten(html.unescape(str(text or '')))


def missing_value_details(assignment, labels):
    """Which assignment labels are absent from the drawing's visible text.

    Every label must appear with the same words, grouping, signs, operators, and units after only
    whitespace normalization and XML entity decoding. The search runs over the space-joined text
    of every visible ``text`` element, so a label wrapped across ``tspan`` lines still passes.
    """
    recorded = _normalized_display(' '.join(str(label) for label in labels if label))
    missing = []
    for value in assignment.get('labels') or []:
        canonical = _normalized_display(value)
        if canonical and canonical in recorded:
            continue
        missing.append({
            'kind': 'exact', 'value': value,
            'message': ('The assignment label ' + json.dumps(value)
                        + ' is missing or changed in the drawing. Draw it exactly as written.')})
    return missing


# An Overview panel may show at most this many visible words beyond its assignment's own words,
# after the multiplier. The check fires on excess, the only defect whose remedy is removal.
EXCESS_WORD_MULTIPLIER = 1.5
EXCESS_WORD_ALLOWANCE = 12
# An Overview panel taller than this ratio of its width stacks into a column no reader can see at
# once. The remedy is more columns and fewer rows, not a smaller font.
MAX_PANEL_HEIGHT_RATIO = 1.25


def word_budget(assignment):
    """The visible-word budget of one Overview assignment."""
    words = sum(len(_flatten(value).split()) for value in assignment.get('labels') or [])
    words += sum(len(_flatten(relation.get('label') or '').split())
                 for relation in assignment.get('relations') or [])
    words += len(_flatten(assignment.get('note') or '').split())
    return int(words * EXCESS_WORD_MULTIPLIER) + EXCESS_WORD_ALLOWANCE


def excess_text_details(assignment, labels):
    """An Overview panel that shows more words than its assignment supports."""
    visible = sum(len(_normalized_display(label).split()) for label in labels if label)
    budget = word_budget(assignment)
    if visible <= budget:
        return []
    return [{'kind': 'excess', 'value': visible,
             'message': ('The drawing shows ' + str(visible) + ' visible words; this panel supports at '
                         'most ' + str(budget) + '. Remove text that is not an assignment label, a '
                         'relation label, or the note. Do not shrink the text.')}]


def tall_panel_details(checks):
    """An Overview panel whose displayed height exceeds the readable ratio."""
    canvas = checks.get('canvas') or {}
    width, height = float(canvas.get('width') or 0), float(canvas.get('height') or 0)
    if not width or height <= width * MAX_PANEL_HEIGHT_RATIO:
        return []
    return [{'kind': 'tall', 'value': round(height / width, 2),
             'message': ('The panel is ' + str(round(height)) + ' units tall at ' + str(round(width))
                         + ' wide; the limit is ' + str(MAX_PANEL_HEIGHT_RATIO) + ' times the width. '
                         'Arrange the content in more columns and fewer rows, and remove what the '
                         'assignment does not require.')}]


def panel_defects(assignment, checked, *, purpose='overview'):
    """Every local defect of one checked drawing: measurements first, then content rules."""
    _validated_purpose(purpose)
    issues = [issue.get('message') or issue.get('code')
              for issue in checked['checks'].get('issue_details') or []]
    issues.extend(item['message'] for item in missing_value_details(assignment, checked['labels']))
    if purpose == 'overview':
        issues.extend(item['message'] for item in excess_text_details(assignment, checked['labels']))
        issues.extend(item['message'] for item in tall_panel_details(checked['checks']))
    return [issue for issue in issues if issue]


def check_panel(source, directory, panel_id, *, display_width=PANEL_DISPLAY_WIDTH):
    """Render one panel at the width the reader sees and report its measured geometry.

    A drawing that spills past its own canvas is fitted locally first: the viewBox grows to
    enclose every element and the panel is rendered again. That is a resize, not a repair, so
    it costs no model request and cannot lose content.
    """
    normalized = normalize_panel_svg(source)
    result = _render_panel(normalized, directory, panel_id, display_width)
    fitted = fit_canvas(normalized, result['checks'])
    if fitted is not None:
        normalized = normalize_panel_svg(fitted)
        result = _render_panel(normalized, directory, panel_id, display_width)
        result['checks']['canvas_fitted'] = True
    labels = [text for _, text in svg_visible_text(normalized, external_markers=SHARED_MARKER_IDS,
                                                   profile='panel')]
    return {'source': normalized, 'assets': {key: value for key, value in result.items() if key != 'checks'},
            'checks': result['checks'], 'labels': labels}


def _render_panel(normalized, directory, panel_id, display_width):
    figure = {'id': panel_id, 'title': 'Panel ' + str(panel_id), 'paper_connection': '',
              'caption': '', 'illustrative': False, 'source_svg': normalized}
    return render(directory, figure, '', mode='panel', display_width=display_width)
