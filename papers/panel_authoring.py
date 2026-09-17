"""Panel authoring: one drawing assignment, at most two references, one SVG response, local checks.

A panel author receives one complete assignment, at most two relevant complete reference
examples, the construction notes, and the output contract. It never sees the paper, the
planning history, or another panel's brief, and it cannot ask for a narrative change.

``request_panel`` performs one network request and never renders: the coordinator owns native
rendering, persistence, and repair scheduling.
"""
from __future__ import annotations

import html
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

BLOG_FIGURE_GUIDANCE = '''BLOG FIGURE GUIDANCE
This figure is displayed 640px wide in a Blog article. Author toward a 640-unit-wide viewBox with
18px body labels, and never let a displayed label fall below 14px. The application owns the
article, the caption, and the figure placement, so draw the figure only. Figure text is limited to
labels, values, and necessary equations; context and explanation belong in the article.'''


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

    Optional ``layout_intent`` and Overview ``story_context`` are emitted only when supplied.
    ``purpose='blog'`` appends the Blog width and text guidance, never Overview story context;
    the shared request structure is unchanged.
    """
    _validated_purpose(purpose)
    lines = ['DRAWING ASSIGNMENT', 'panel id: ' + str(assignment['id']),
             'panel title: ' + str(assignment['title']),
             'construction: ' + str(assignment['construction']),
             'purpose: ' + str(assignment['purpose'])]
    if assignment.get('layout_intent'):
        lines.append('layout intent: ' + str(assignment['layout_intent']))
    if assignment.get('entry_context'):
        lines.append('the reader already has: ' + ' '.join(assignment['entry_context']))
    if assignment.get('shared_facts'):
        lines.append('semantic facts and values for this panel — express them in the drawing; they '
                     'do not have to appear word for word:')
        lines += ['  - ' + value for value in assignment['shared_facts'].values()]
    if assignment.get('exact_text'):
        lines.append('exact display text that must appear in the drawing unchanged:')
        lines += ['  - ' + value for value in assignment['exact_text']]
    if assignment.get('illustrative_values'):
        lines.append('illustrative teaching values, never reported as paper results:')
        lines += ['  - ' + value for value in assignment['illustrative_values']]
    lines.append('content to draw, in this order:')
    for item in assignment['content']:
        lines.append('  - [' + str(item['kind']) + '] ' + str(item['text']))
    lines.append('you may express semantic statements and connections visually; every exact '
                 'display string above must survive with the same grouping, signs, operators, '
                 'and units, not a paraphrase or a closer-looking variant')
    lines.append('if an exact display string is source notation such as \\frac or \\sum, preserve '
                 'it literally and label it as source notation; do not rewrite the mathematics')
    lines.append('this panel must leave the reader with: ' + str(assignment['exit_state']))
    if purpose == 'blog':
        lines.append(BLOG_FIGURE_GUIDANCE)
    elif assignment.get('story_context'):
        lines.append('SHARED STORY CONTEXT — orientation only, not extra content to draw:\n'
                     + str(assignment['story_context']))
        lines.append('Use the same example and assigned semantic encodings across panels. Draw '
                     'only this assignment; shared orientation does not override its exact text, '
                     'values, content, or handoff.')
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


NUMBER_TOKEN = re.compile(r'\d[\d,]*(?:\.\d+)?')


def _display_requirements(assignment):
    """Display requirements in check order, each tagged with the check it receives.

    ``exact`` strings are declared exact display text: the author-facing ``exact_text`` union
    (shared-fact exact strings, complete equations, complete labels) plus any hand-built
    equation or label item. ``number`` tokens come from ordinary ``value`` items and receive only
    a limited omission check.
    """
    exact, numbers = [], []
    for value in assignment.get('exact_text') or []:
        if isinstance(value, str) and value.strip():
            exact.append(value)
    for item in assignment.get('content') or []:
        text = item.get('text') if isinstance(item, dict) else None
        if not isinstance(text, str) or not text.strip():
            continue
        if item.get('kind') in ('equation', 'label'):
            exact.append(text)
        elif item.get('kind') == 'value':
            numbers.extend(NUMBER_TOKEN.findall(text))
    return (list(dict.fromkeys(exact)), list(dict.fromkeys(numbers)))


def required_values(assignment):
    """Every declared exact string and numeric omission token for one assignment.

    This is the display contract, not a scientific-equivalence test: an exact string must appear
    unchanged, while a numeric token from an ordinary ``value`` item only has to survive as a
    number.
    """
    exact, numbers = _display_requirements(assignment)
    return list(dict.fromkeys([*exact, *numbers]))


def _flatten(text):
    return ' '.join(str(text).split())


def _normalized_display(text):
    """The comparison form of one label: whitespace-normalized and XML-entity-decoded only."""
    return _flatten(html.unescape(str(text or '')))


def missing_value_details(assignment, labels):
    """Which display requirements are absent, with the check that produced each finding."""
    recorded = _normalized_display(' '.join(str(label) for label in labels if label))
    exact, numbers = _display_requirements(assignment)
    missing = []
    for value in exact:
        canonical = _normalized_display(value)
        if canonical and canonical in recorded:
            continue
        missing.append({
            'kind': 'exact', 'value': value,
            'message': ('The declared exact display text ' + json.dumps(value)
                        + ' is missing or changed in the drawing. Preserve its grouping, signs, '
                          'operators, and units exactly.')})
    for value in numbers:
        canonical = _normalized_display(value)
        if re.search(r'(?<![\d.,])' + re.escape(canonical) + r'(?![\d])', recorded):
            continue
        missing.append({
            'kind': 'number', 'value': value,
            'message': ('The number ' + value + ' from a value item is missing from the drawing. '
                        'This is a limited numeric omission check; it does not verify the '
                        'surrounding wording or the scientific meaning.')})
    return missing


def missing_values(assignment, labels):
    """Which display requirements are absent from the drawing's visible text.

    Every declared exact string (``exact_text``, complete equations, complete labels) must appear
    with the same grouping, signs, operators, units, and words after only whitespace
    normalization and XML entity decoding. Numbers inside ordinary ``value`` items get a limited
    omission check so a dropped number is reported; that check cannot prove the surrounding
    reformulation is scientifically equivalent, and it deliberately does not attempt to.
    """
    return [item['value'] for item in missing_value_details(assignment, labels)]


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


def _wrap(directory, text, width, font_size, weight=None):
    """Wrap text to a measured pixel width using the renderer's own font and weight."""
    words = str(text).split()
    if not words:
        return []
    measured = measure_text_widths(directory, words, font_size=font_size, font_weight=weight)
    space = measure_text_widths(directory, [' '], font_size=font_size, font_weight=weight)[0]
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


# XML 1.0 forbids most control characters; model output may still contain them.
_XML_FORBIDDEN = re.compile('[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')


def _xml_text(value):
    """Escape text for an SVG text node. A raw < or & must never malform the panel."""
    return _xml_forbidden_free(value).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _xml_forbidden_free(value):
    return _XML_FORBIDDEN.sub('', str(value))


def _svg_text(x, y, text, size, weight=None):
    attributes = f'x="{x}" y="{y}" font-size="{size}"'
    if weight:
        attributes += f' font-weight="{weight}"'
    return f'<text {attributes}>{_xml_text(text)}</text>'


def source_notation_values(assignment):
    """Approved texts that still contain source notation such as LaTeX commands.

    Planning asks for plain display notation; anything still carrying a backslash reached the
    drawing phase unchanged. The recovery shows it literally and identifies it instead of
    rewriting the mathematics.
    """
    values = [assignment.get('title') or '']
    values += [item.get('text') or '' for item in assignment.get('content') or []
               if isinstance(item, dict)]
    values += [value for value in (assignment.get('shared_facts') or {}).values()]
    values += list(assignment.get('illustrative_values') or [])
    values += list(assignment.get('exact_text') or [])
    return [value for value in dict.fromkeys(values)
            if isinstance(value, str) and '\\' in value]


def simple_panel_source(assignment, directory):
    """An application-owned text panel: measured wrapping, the same typography, no model.

    Used only after a panel's drawing repair still fails. It keeps the title, the approved
    content, the canonical values, and the illustrative label without dropping words or altering
    mathematical text. Source notation that survived planning is preserved literally, XML-escaped,
    and visibly identified as source notation rather than silently rewritten.
    """
    width = SIMPLE_CANVAS_WIDTH - 2 * SIMPLE_MARGIN
    body = []
    y = 60
    for line in _wrap(directory, assignment['title'], width, 22, 700):
        body.append(_svg_text(SIMPLE_MARGIN, y, line, 22, 700))
        y += 30
    y += 8
    if source_notation_values(assignment):
        for line in _wrap(directory, 'source notation, shown literally, not re-rendered',
                          width, PANEL_MINIMUM_FONT_SIZE, 700):
            body.append(_svg_text(SIMPLE_MARGIN, y, line, PANEL_MINIMUM_FONT_SIZE, 700))
            y += 22
        y += 4
    for item in assignment['content']:
        weight = 700 if item['kind'] in ('value', 'equation', 'label') else None
        for line in _wrap(directory, item['text'], width, PANEL_BODY_FONT_SIZE, weight):
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
    else:
        illustrative = [value for value in assignment.get('illustrative_values') or []
                        if isinstance(value, str) and value.strip()]
        if illustrative:
            y += 4
            body.append(_svg_text(SIMPLE_MARGIN, y, 'illustrative values, not paper results:',
                                  PANEL_MINIMUM_FONT_SIZE, 700))
            y += 22
            for value in illustrative:
                for line in _wrap(directory, value, width, PANEL_MINIMUM_FONT_SIZE):
                    body.append(_svg_text(SIMPLE_MARGIN, y, line, PANEL_MINIMUM_FONT_SIZE))
                    y += 22

    height = max(160, int(y + SIMPLE_MARGIN - SIMPLE_LINE_HEIGHT))
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + str(SIMPLE_CANVAS_WIDTH) + ' '
            + str(height) + '" font-family="Arial, sans-serif" font-size="18" fill="#243b32" '
            'role="img" aria-label="' + _attribute_text(assignment['title']) + '">'
            + ''.join(body) + '</svg>')


def _attribute_text(value):
    return (_xml_forbidden_free(value).replace('&', '&amp;').replace('<', '&lt;')
            .replace('>', '&gt;').replace('"', '&quot;'))


def simple_panel(assignment, directory):
    """Render the application-owned fallback through the same local check as a drawn panel."""
    result = check_panel(simple_panel_source(assignment, directory), directory, assignment['id'])
    result['simplified'] = True
    notation = source_notation_values(assignment)
    if notation:
        result['reduced_presentation'] = 'source notation preserved literally, not re-rendered'
        result['source_notation'] = notation
    return result
