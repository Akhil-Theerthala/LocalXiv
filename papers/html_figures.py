"""Restricted HTML/SVG authoring and native static exports; no model code execution."""
import base64
import html
import json
import os
from pathlib import Path
import re
import subprocess
import uuid
import xml.etree.ElementTree as ET

SVG_NAMESPACE = 'http://www.w3.org/2000/svg'
SVG_PROFILE_REVISION = 'overview-svg-v1'
PANEL_SVG_PROFILE_REVISION = 'panel-svg-v1'
SVG_MAX_VISIBLE_WORDS = 600
SVG_MAX_CHARACTERS = 60000
SVG_MAX_ELEMENTS = 500
SVG_MAX_ATTRIBUTE_CHARACTERS = 12000
# One panel is bounded like a whole legacy figure; a composed overview holds up to seven of them,
# so its aggregate budget is the panel budget times the panel count. These are resource bounds,
# not an editorial page budget: canvas size follows content.
SVG_PROFILES = {
    'legacy': {'revision': SVG_PROFILE_REVISION, 'max_characters': SVG_MAX_CHARACTERS,
               'max_elements': SVG_MAX_ELEMENTS, 'max_attribute_characters': SVG_MAX_ATTRIBUTE_CHARACTERS,
               'viewbox': (100, 2000, 80, 2000), 'font_size': (16, 80), 'local_definitions': True},
    'panel': {'revision': PANEL_SVG_PROFILE_REVISION, 'max_characters': SVG_MAX_CHARACTERS,
              'max_elements': SVG_MAX_ELEMENTS, 'max_attribute_characters': SVG_MAX_ATTRIBUTE_CHARACTERS,
              'viewbox': (40, 20000, 40, 20000), 'font_size': (6, 600), 'local_definitions': False},
    'overview': {'revision': PANEL_SVG_PROFILE_REVISION, 'max_characters': SVG_MAX_CHARACTERS * 7,
                 'max_elements': SVG_MAX_ELEMENTS * 7, 'max_attribute_characters': SVG_MAX_ATTRIBUTE_CHARACTERS,
                 'viewbox': (40, 20000, 40, 20000), 'font_size': (6, 600), 'local_definitions': True},
}
PANEL_BODY_FONT_SIZE = 18
PANEL_MINIMUM_FONT_SIZE = 14
SVG_DEFAULT_FONT_FAMILY = 'Arial, sans-serif'
SVG_LOCAL_FONT_FAMILIES = frozenset({'arial', 'helvetica', 'helvetica neue', 'sans-serif',
                                     'system-ui', 'liberation sans', 'nimbus sans'})
SVG_DEFAULT_FONT_SIZE = 24
SVG_DEFAULT_FILL = '#243b32'

SVG_TAGS = frozenset('svg g rect circle ellipse line polyline polygon path text tspan title desc defs marker'.split())
SVG_COMMON_ATTRIBUTES = frozenset('id fill fill-rule fill-opacity stroke stroke-width stroke-opacity stroke-linecap stroke-linejoin stroke-miterlimit stroke-dasharray stroke-dashoffset opacity transform'.split())
SVG_TEXT_ATTRIBUTES = frozenset('font-family font-size font-weight text-anchor dominant-baseline'.split())
SVG_ATTRIBUTES = {
    'svg': frozenset('viewBox width height preserveAspectRatio role aria-label aria-labelledby'.split()) | SVG_TEXT_ATTRIBUTES,
    'g': SVG_TEXT_ATTRIBUTES,
    'rect': frozenset('x y width height rx ry'.split()),
    'circle': frozenset('cx cy r'.split()),
    'ellipse': frozenset('cx cy rx ry'.split()),
    'line': frozenset('x1 y1 x2 y2 marker-start marker-mid marker-end'.split()),
    'polyline': frozenset('points marker-start marker-mid marker-end'.split()),
    'polygon': frozenset('points'.split()),
    'path': frozenset('d marker-start marker-mid marker-end'.split()),
    'text': SVG_TEXT_ATTRIBUTES | frozenset('x y dx dy'.split()),
    'tspan': SVG_TEXT_ATTRIBUTES | frozenset('x y dx dy'.split()),
    'title': frozenset(),
    'desc': frozenset(),
    'defs': frozenset(),
    'marker': frozenset('viewBox markerWidth markerHeight markerUnits refX refY orient'.split()),
}

_NUMBER = r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?'
_NUMBER_RE = re.compile(r'^(?:' + _NUMBER + r')$')
_NUMBER_TOKEN_RE = re.compile(_NUMBER)
_PATH_TOKEN_RE = re.compile(r'[AaCcHhLlMmQqSsTtVvZz]|' + _NUMBER)
_TRANSFORM_RE = re.compile(r'([A-Za-z]+)\s*\(([^()]*)\)')


class SVGValidationError(ValueError):
    def __init__(self, issues):
        self.issues = issues
        super().__init__('; '.join(issue['message'] for issue in issues[:20]))


def svg_profile_guidance(profile='legacy'):
    """Describe the enforced profile from the same constants the validator uses."""
    limits = svg_limits(profile)
    attributes = sorted(SVG_COMMON_ATTRIBUTES | set().union(*SVG_ATTRIBUTES.values()))
    minimum_width, maximum_width, minimum_height, maximum_height = limits['viewbox']
    minimum_font, maximum_font = limits['font_size']
    return (
        f'Profile {limits["revision"]}. Submit one complete SVG document. '
        f'Allowed elements: {", ".join(sorted(SVG_TAGS))}. '
        f'Allowed attributes, only on their documented elements: {", ".join(attributes)}. '
        f'Limits: {limits["max_characters"]} Unicode characters, {limits["max_elements"]} elements, '
        f'{limits["max_attribute_characters"]} characters per attribute, viewBox width '
        f'{minimum_width}-{maximum_width} and height {minimum_height}-{maximum_height}, numeric source '
        f'font sizes {minimum_font}-{maximum_font}. font-family accepts only local sans-serif '
        f'families ({SVG_DEFAULT_FONT_FAMILY} is used for every accepted local stack); other families '
        'are rejected. Paths support M/L/H/V/C/S/Q/T/A/Z '
        'and lowercase forms. Transforms support matrix, translate, scale, rotate, skewX, and skewY. '
        'Only local url(#marker-id) marker references are allowed. Scripts, events, animation, '
        'images, external resources, links, use, arbitrary CSS, filters, masks, and clipping paths '
        'are not supported.'
    )


def svg_limits(profile='legacy'):
    if profile not in SVG_PROFILES:
        raise ValueError('Unknown SVG profile: ' + str(profile))
    return SVG_PROFILES[profile]

TAGS = set('div section p span strong em br h2 h3 ul ol li svg g rect circle ellipse line polyline polygon path text tspan defs marker title desc'.split())
ATTRS = set('class id role aria-label aria-labelledby viewBox width height x y x1 y1 x2 y2 cx cy r rx ry d points fill stroke stroke-width stroke-linecap stroke-linejoin stroke-dasharray font-size font-weight text-anchor dx dy opacity marker-end marker-start markerWidth markerHeight refX refY orient'.split())
CLASSES = set('columns stack note emphasis muted sage blue peach label'.split())
STYLE = '''*{box-sizing:border-box}body{margin:0;background:#fafbf7;color:#243b32;font:22px/1.45 Arial,sans-serif}main{width:960px;padding:40px}header{margin-bottom:28px}h1{font-size:38px;line-height:1.15;margin:12px 0}h2{font-size:26px}h3{font-size:23px}p{margin:12px 0}svg{display:block;width:100%;height:auto}main:not(.svg-overview) svg{font-family:Arial,sans-serif;font-size:20px;fill:#243b32}.columns{display:flex;gap:28px;align-items:flex-start}.columns>*{flex:1;min-width:0}.stack>*{margin-bottom:20px}.note{padding:20px;border:1px solid #dce1d8;border-radius:8px}.emphasis{font-weight:bold}.muted,.label{color:#627168}.label{font-size:16px}.sage{background:#dce8cf}.blue{background:#e1ebf1}.peach{background:#f1e3d8}footer{font-size:17px;border-top:1px solid #dce1d8;margin-top:28px;padding-top:16px}'''


def _svg_name(tag):
    return tag.rsplit('}', 1)[-1]


def _svg_issue(code, path, message, **details):
    return {'code': code, 'path': path, 'message': message, **details}


def _raise_svg(code, path, message, **details):
    raise SVGValidationError([_svg_issue(code, path, message, **details)])


def _finite_number(value):
    if not isinstance(value, str) or not _NUMBER_RE.fullmatch(value.strip()):
        raise ValueError('expected a finite number')
    number = float(value)
    if not number == number or number in (float('inf'), float('-inf')):
        raise ValueError('expected a finite number')
    return number


def _number_list(value):
    numbers = []
    position = 0
    for match in _NUMBER_TOKEN_RE.finditer(value):
        if value[position:match.start()].strip(' ,\t\r\n'):
            raise ValueError('expected finite numbers separated by whitespace or commas')
        numbers.append(_finite_number(match.group()))
        position = match.end()
    if value[position:].strip(' ,\t\r\n') or not numbers:
        raise ValueError('expected finite numbers separated by whitespace or commas')
    return numbers


def _validate_path(value):
    tokens = []
    position = 0
    for match in _PATH_TOKEN_RE.finditer(value):
        if value[position:match.start()].strip(' ,\t\r\n'):
            raise ValueError('contains unsupported path syntax')
        token = match.group()
        tokens.append(token if len(token) == 1 and token.isalpha() else _finite_number(token))
        position = match.end()
    if value[position:].strip(' ,\t\r\n') or not tokens:
        raise ValueError('contains unsupported path syntax')
    if tokens[0] not in ('M', 'm'):
        raise ValueError('must begin with M or m')
    arity = {'M': 2, 'L': 2, 'H': 1, 'V': 1, 'C': 6, 'S': 4,
             'Q': 4, 'T': 2, 'A': 7, 'Z': 0}
    index = 0
    while index < len(tokens):
        if not isinstance(tokens[index], str):
            raise ValueError('needs a command before coordinates')
        command = tokens[index]
        expected = arity[command.upper()]
        index += 1
        start = index
        while index < len(tokens) and not isinstance(tokens[index], str):
            index += 1
        arguments = tokens[start:index]
        if expected == 0:
            if arguments:
                raise ValueError(command + ' does not accept coordinates')
            continue
        if len(arguments) < expected or len(arguments) % expected:
            raise ValueError(command + ' has incomplete coordinates')
        if command.upper() == 'A':
            for offset in range(0, len(arguments), 7):
                if arguments[offset] < 0 or arguments[offset + 1] < 0:
                    raise ValueError('arc radii cannot be negative')
                if arguments[offset + 3] not in (0, 1) or arguments[offset + 4] not in (0, 1):
                    raise ValueError('arc flags must be 0 or 1')


def _validate_transform(value):
    arities = {'matrix': (6,), 'translate': (1, 2), 'scale': (1, 2),
               'rotate': (1, 3), 'skewX': (1,), 'skewY': (1,)}
    position = 0
    found = False
    for match in _TRANSFORM_RE.finditer(value):
        if value[position:match.start()].strip(' ,\t\r\n'):
            raise ValueError('contains unsupported transform syntax')
        found = True
        name = match.group(1)
        if name not in arities:
            raise ValueError('uses unsupported transform ' + name)
        numbers = _number_list(match.group(2))
        if len(numbers) not in arities[name]:
            raise ValueError(name + ' has the wrong number of arguments')
        position = match.end()
    if not found or value[position:].strip(' ,\t\r\n'):
        raise ValueError('contains unsupported transform syntax')


def _validate_paint(value):
    if value in {'none', 'currentColor', 'transparent', 'black', 'white'}:
        return
    if re.fullmatch(r'#[0-9A-Fa-f]{3,4}(?:[0-9A-Fa-f]{3,4})?', value):
        return
    match = re.fullmatch(r'rgb\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)', value)
    if match and all(int(part) <= 255 for part in match.groups()):
        return
    raise ValueError('uses an unsupported color')


def _element_locations(root):
    result = {}

    def walk(element, path):
        result[id(element)] = '#' + element.get('id') if element.get('id') else path
        counts = {}
        for child in element:
            name = _svg_name(child.tag)
            counts[name] = counts.get(name, 0) + 1
            walk(child, path + '/' + name + '[' + str(counts[name]) + ']')

    walk(root, '/svg')
    return result


SHARED_MARKER_IDS = frozenset({'arrow', 'arrow-muted', 'arrow-accent'})
SHARED_MARKERS = (
    '<defs>'
    '<marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" '
    'orient="auto-start-reverse"><path d="M 1 2 L 8 5 L 1 8 Z" fill="#243b32"/></marker>'
    '<marker id="arrow-muted" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" '
    'orient="auto-start-reverse"><path d="M 1 2 L 8 5 L 1 8 Z" fill="#627168"/></marker>'
    '<marker id="arrow-accent" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" '
    'orient="auto-start-reverse"><path d="M 1 2 L 8 5 L 1 8 Z" fill="#2f6f5e"/></marker>'
    '</defs>'
)
CHROME_FILL = {'group': '#f3f6f0', 'panel': '#ffffff'}
CHROME_BORDER = '#dce1d8'

# Composition geometry, all in label units.
CARD_RADIUS_UNITS = 1.2
CARD_PAD_UNITS = 1.5                  # matches arrangement.CARD_PAD, the frame padding
NUMBER_LABEL_UNITS = 1.4              # the reading-order number
MAX_CHROME_FONT = 64.0                # the profile accepts source font sizes 16-80


def _xml(value):
    return html.escape(str(value))


def _chrome_font(units, scale):
    """Clamp a composed text size into the profile's accepted source font range."""
    return round(min(units * scale, MAX_CHROME_FONT), 2)


def _panel_body(source, identifier):
    """Return a panel's drawable children with its local ids namespaced to the panel."""
    root = ET.fromstring(source)
    local = {element.get('id'): identifier + '-' + element.get('id')
             for element in root.iter() if element.get('id')}
    for element in root.iter():
        if element.get('id'):
            element.set('id', local[element.get('id')])
        for key, value in element.attrib.items():
            match = re.fullmatch(r'url\(#([A-Za-z][\w.-]*)\)', value or '')
            if match and match.group(1) in local:
                element.set(key, 'url(#' + local[match.group(1)] + ')')
    return ''.join(ET.tostring(child, encoding='unicode') for child in root
                   if _svg_name(child.tag) != 'defs')


def normalize_panel_svg(source):
    """Validate one panel: the panel profile, shared markers only, no local definitions."""
    return normalize_svg(source, external_markers=SHARED_MARKER_IDS, profile='panel')


def with_shared_markers(source):
    """Insert the shared arrow markers into a validated panel so it renders standalone."""
    return re.sub(r'(<svg\b[^>]*>)', lambda match: match.group(1) + SHARED_MARKERS, source, count=1)


CHROME_LABEL_UNITS = 1.5


# Presentation attributes a panel root may set that must keep their meaning after composition.
INHERITED_ROOT_ATTRIBUTES = ('font-family', 'font-size', 'font-weight', 'font-style', 'text-anchor',
                             'dominant-baseline', 'fill', 'fill-rule', 'fill-opacity', 'stroke',
                             'stroke-width', 'stroke-linecap', 'stroke-linejoin', 'stroke-dasharray',
                             'stroke-opacity', 'opacity')


def _panel_group(source, placement):
    """One panel as a placed group: ids namespaced, references rewritten, root style inherited."""
    identifier = placement['id']
    root = ET.fromstring(source)
    inherited = {key: root.get(key) for key in INHERITED_ROOT_ATTRIBUTES if root.get(key) is not None}
    attributes = ''.join(f' {key}="{html.escape(str(value), quote=True)}"'
                         for key, value in inherited.items())
    body = _panel_body(source, identifier)
    return (f'<g id="panel-{identifier}" transform="translate({placement["x"]} {placement["y"]}) '
            f'scale({placement["scale"]})"{attributes}>{body}</g>')


def _number_label(placement):
    """The reading-order number in the band reserved above the panel."""
    centre = placement['x'] + placement['width'] / 2
    return (f'<text x="{round(centre, 3)}" y="{round(placement["y"] - 9, 3)}" '
            f'font-size="20" font-weight="bold" text-anchor="middle">{placement["number"]}</text>')


def compose_figure(panels, arrangement):
    """Compose validated panels into one free-sized SVG document in planned order.

    ``panels`` maps panel id to its normalized standalone SVG source. ``arrangement`` is the
    result of :func:`papers.arrangement.arrange`; every placement rectangle is already in
    composed-image coordinates, and the canvas is exactly the composed size.
    """
    canvas = arrangement['canvas']
    body = [SHARED_MARKERS]
    for placement in arrangement['placements']:
        source = panels.get(placement['id'])
        if not source:
            continue
        body.append(_number_label(placement))
        body.append(_panel_group(source, placement))
    document = (f'<svg xmlns="{SVG_NAMESPACE}" viewBox="0 0 {canvas["width"]} {canvas["height"]}" '
                f'font-family="{SVG_DEFAULT_FONT_FAMILY}" font-size="{int(PANEL_BODY_FONT_SIZE)}" '
                f'fill="{SVG_DEFAULT_FILL}">{"".join(body)}</svg>')
    return normalize_svg(document, profile='overview')


def normalize_svg(source, *, external_markers=frozenset(), profile='legacy'):
    """Return validated, canonical standalone SVG or raise ValueError."""
    limits = svg_limits(profile)
    if not isinstance(source, str) or not source.strip():
        _raise_svg('svg_parse', 'svg', 'SVG source must be a nonempty string.')
    if len(source) > limits['max_characters']:
        _raise_svg('unsupported_svg', 'svg',
                   f'SVG source exceeds {limits["max_characters"]} characters.',
                   constraint='maximum_characters', actual=len(source), limit=limits['max_characters'])
    source = re.sub(r'<!--.*?-->', '', source, flags=re.S)
    if '<!' in source or '<?' in source:
        _raise_svg('svg_parse', 'svg', 'SVG cannot contain declarations, entities, or processing instructions.')
    try:
        root = ET.fromstring(source)
    except ET.ParseError as exc:
        _raise_svg('svg_parse', 'svg', 'SVG must be well-formed XML: ' + str(exc))
    if _svg_name(root.tag) != 'svg':
        _raise_svg('svg_parse', 'svg', 'SVG source needs one svg root.')
    if len(list(root.iter())) > limits['max_elements']:
        _raise_svg('unsupported_svg', 'svg',
                   f'SVG exceeds {limits["max_elements"]} elements.',
                   constraint='maximum_elements', actual=len(list(root.iter())), limit=limits['max_elements'])
    for element in root.iter():
        namespace = element.tag[1:].split('}', 1)[0] if element.tag.startswith('{') else ''
        if namespace not in ('', SVG_NAMESPACE):
            _raise_svg('unsupported_svg', 'svg', 'Unsupported SVG namespace: ' + namespace)
        element.tag = '{' + SVG_NAMESPACE + '}' + _svg_name(element.tag)
    locations = _element_locations(root)
    issues = []
    ids = {}
    marker_references = []
    numeric = {
        'x', 'y', 'x1', 'y1', 'x2', 'y2', 'cx', 'cy', 'r', 'rx', 'ry', 'width', 'height',
        'dx', 'dy', 'stroke-width', 'stroke-miterlimit', 'stroke-dashoffset', 'markerWidth',
        'markerHeight', 'refX', 'refY',
    }
    nonnegative = {'r', 'rx', 'ry', 'width', 'height', 'stroke-width', 'markerWidth', 'markerHeight'}
    unit_interval = {'opacity', 'fill-opacity', 'stroke-opacity'}
    for element in root.iter():
        name = _svg_name(element.tag)
        path = locations[id(element)]
        if name not in SVG_TAGS or (name == 'svg' and element is not root):
            issues.append(_svg_issue('unsupported_svg', path, 'Unsupported SVG element: ' + name + '.'))
            continue
        if name in ('defs', 'marker') and not limits['local_definitions']:
            issues.append(_svg_issue('unsupported_svg', path,
                'Panels use the shared arrow markers; local defs and markers are not allowed.'))
            continue
        allowed = SVG_COMMON_ATTRIBUTES | SVG_ATTRIBUTES[name]
        for raw_key, value in element.attrib.items():
            key = _svg_name(raw_key)
            if raw_key.startswith('{') or key.lower().startswith('on') or key in ('href', 'style') or key not in allowed:
                issues.append(_svg_issue('unsupported_svg', path, 'Unsupported attribute on ' + name + ': ' + key + '.'))
                continue
            if len(value) > limits['max_attribute_characters']:
                issues.append(_svg_issue('unsupported_svg', path,
                                         f'{key} exceeds {limits["max_attribute_characters"]} characters.',
                                         constraint='maximum_attribute_characters',
                                         actual=len(value), limit=limits['max_attribute_characters']))
                continue
            if re.search(r'javascript:|data:|https?:|file:|\\|[<>]', value, re.I):
                issues.append(_svg_issue('unsupported_svg', path, key + ' cannot load resources or code.'))
                continue
            try:
                if key == 'id':
                    if not re.fullmatch(r'[A-Za-z][\w.-]*', value):
                        raise ValueError('must begin with a letter and contain only name characters')
                    if value in ids:
                        issues.append(_svg_issue('svg_reference', path, 'Duplicate SVG id: ' + value + '.'))
                    else:
                        ids[value] = name
                elif key in numeric:
                    number = _finite_number(value)
                    if key in nonnegative and number < 0:
                        raise ValueError('cannot be negative')
                    if key == 'stroke-miterlimit' and number < 1:
                        raise ValueError('must be at least 1')
                elif key in unit_interval:
                    number = _finite_number(value)
                    if not 0 <= number <= 1:
                        raise ValueError('must be between 0 and 1')
                elif key in ('fill', 'stroke'):
                    _validate_paint(value)
                elif key == 'fill-rule' and value not in ('nonzero', 'evenodd'):
                    raise ValueError('must be nonzero or evenodd')
                elif key == 'stroke-linecap' and value not in ('butt', 'round', 'square'):
                    raise ValueError('must be butt, round, or square')
                elif key == 'stroke-linejoin' and value not in ('miter', 'round', 'bevel'):
                    raise ValueError('must be miter, round, or bevel')
                elif key == 'stroke-dasharray' and value != 'none':
                    if any(number < 0 for number in _number_list(value)):
                        raise ValueError('cannot contain negative lengths')
                elif key == 'font-size':
                    size = _finite_number(value)
                    minimum, maximum = limits['font_size']
                    if not minimum <= size <= maximum:
                        raise ValueError(f'must be from {minimum} through {maximum}')
                elif key == 'font-family':
                    families=[token.strip().strip("'").lower() for token in value.split(',')]
                    if not families or any(family not in SVG_LOCAL_FONT_FAMILIES for family in families):
                        raise ValueError('must use local text families only, such as Arial, Helvetica, '
                                         'or sans-serif; found ' + value)
                    element.set(key, SVG_DEFAULT_FONT_FAMILY)
                elif key == 'font-weight' and value not in ('normal', 'bold', *[str(n) for n in range(100, 1000, 100)]):
                    raise ValueError('must be normal, bold, or a CSS hundred weight')
                elif key == 'text-anchor' and value not in ('start', 'middle', 'end'):
                    raise ValueError('must be start, middle, or end')
                elif key == 'dominant-baseline' and value not in ('auto', 'middle', 'central', 'hanging', 'text-before-edge', 'text-after-edge', 'alphabetic'):
                    raise ValueError('uses an unsupported baseline')
                elif key == 'transform':
                    _validate_transform(value)
                elif key == 'points':
                    points = _number_list(value)
                    minimum = 6 if name == 'polygon' else 4
                    if len(points) < minimum or len(points) % 2:
                        raise ValueError('needs complete coordinate pairs')
                elif key == 'd':
                    _validate_path(value)
                elif key.startswith('marker-'):
                    match = re.fullmatch(r'url\(#([A-Za-z][\w.-]*)\)', value)
                    if not match:
                        raise ValueError('must be a local url(#marker-id) reference')
                    marker_references.append((path, match.group(1)))
                elif key == 'markerUnits' and value not in ('strokeWidth', 'userSpaceOnUse'):
                    raise ValueError('must be strokeWidth or userSpaceOnUse')
                elif key == 'orient' and value not in ('auto', 'auto-start-reverse'):
                    _finite_number(value)
                elif key == 'preserveAspectRatio' and not re.fullmatch(
                        r'(?:none|x(?:Min|Mid|Max)Y(?:Min|Mid|Max)(?: (?:meet|slice))?)', value):
                    raise ValueError('uses an unsupported preserveAspectRatio value')
            except ValueError as exc:
                issues.append(_svg_issue('unsupported_svg', path, key + ' ' + str(exc) + '.'))
        if name == 'path' and 'd' not in element.attrib:
            issues.append(_svg_issue('unsupported_svg', path, 'Path requires d.'))
        if name in ('polyline', 'polygon') and 'points' not in element.attrib:
            issues.append(_svg_issue('unsupported_svg', path, name + ' requires points.'))
        if name == 'marker' and element.get('id') is None:
            issues.append(_svg_issue('svg_reference', path, 'Marker requires a unique id.'))
    try:
        view_box = _number_list(root.get('viewBox', ''))
        minimum_width, maximum_width, minimum_height, maximum_height = limits['viewbox']
        if (len(view_box) != 4 or view_box[0:2] != [0, 0]
                or not (minimum_width <= view_box[2] <= maximum_width
                        and minimum_height <= view_box[3] <= maximum_height)):
            raise ValueError()
    except ValueError:
        issues.append(_svg_issue('unsupported_svg', '/svg',
                                 f'SVG needs viewBox="0 0 width height", dimensions '
                                 f'{minimum_width}-{maximum_width} by {minimum_height}-{maximum_height}.'))
    for path, reference in marker_references:
        if ids.get(reference) != 'marker' and reference not in external_markers:
            issues.append(_svg_issue('svg_reference', path, 'Marker reference does not resolve to a marker: ' + reference + '.'))
    labelled = root.get('aria-labelledby')
    if labelled:
        for reference in labelled.split():
            if reference not in ids:
                issues.append(_svg_issue('svg_reference', '/svg', 'aria-labelledby does not resolve: ' + reference + '.'))
    if issues:
        raise SVGValidationError(issues)
    root.set('font-family', root.get('font-family', SVG_DEFAULT_FONT_FAMILY))
    root.set('font-size', root.get('font-size', str(SVG_DEFAULT_FONT_SIZE)))
    root.set('fill', root.get('fill', SVG_DEFAULT_FILL))
    ET.register_namespace('', SVG_NAMESPACE)
    return ET.tostring(root, encoding='unicode', short_empty_elements=True)


def svg_visible_text(source, *, external_markers=frozenset(), profile='legacy'):
    """Return element locations and visible label text from a normalized document.

    Panels reference the shared markers without defining them, so a panel needs the same
    external_markers allowance its own validation used.
    """
    root = ET.fromstring(normalize_svg(source, external_markers=external_markers, profile=profile))
    labels = []
    locations = _element_locations(root)

    def opacity(value, default):
        return float(value) if value is not None else default

    def walk(element, hidden=False, fill=SVG_DEFAULT_FILL, fill_opacity=1,
             stroke='none', stroke_opacity=1, stroke_width=1):
        name = _svg_name(element.tag)
        fill=element.get('fill',fill)
        stroke=element.get('stroke',stroke)
        fill_opacity=opacity(element.get('fill-opacity'),fill_opacity)
        stroke_opacity=opacity(element.get('stroke-opacity'),stroke_opacity)
        stroke_width=opacity(element.get('stroke-width'),stroke_width)
        hidden = hidden or name in ('defs', 'marker') or opacity(element.get('opacity'),1)==0
        painted=((fill not in ('none','transparent') and fill_opacity>0) or
                 (stroke not in ('none','transparent') and stroke_opacity>0 and stroke_width>0))
        if name == 'text' and not hidden and painted:
            value = re.sub(r'\s+', ' ', ''.join(element.itertext())).strip()
            if value:
                labels.append((locations[id(element)], value))
        for child in element:
            walk(child,hidden,fill,fill_opacity,stroke,stroke_opacity,stroke_width)

    walk(root)
    return labels


def sanitize(fragment):
    if not isinstance(fragment, str) or not fragment.strip() or len(fragment) > 60000:
        raise ValueError('Figure HTML must contain 1–60000 characters.')
    fragment = re.sub(r'<!--.*?-->', '', fragment, flags=re.S)
    if '<!' in fragment or '<?' in fragment:
        raise ValueError('No declarations, entities or processing instructions.')
    try:
        tree = ET.fromstring('<div>' + fragment + '</div>')
    except ET.ParseError as exc:
        raise ValueError('Use XML-compatible HTML/SVG with closed tags and escaped ampersands: ' + str(exc)) from None
    count = 0
    for element in tree.iter():
        count += 1
        if element.tag not in TAGS:
            raise ValueError('Unsupported figure tag: ' + str(element.tag))
        unsupported = set(element.attrib) - ATTRS
        if unsupported:
            raise ValueError('Unsupported attributes on ' + element.tag + ': ' + ', '.join(sorted(unsupported)))
        if set(element.get('class', '').split()) - CLASSES:
            raise ValueError('Use only the documented layout and color classes.')
        for key, value in element.attrib.items():
            if len(value)>12000 or re.search(r'javascript:|data:|https?:|file:|\\|[<>]',value,re.I):
                raise ValueError('Figure attributes cannot load resources or code.')
            if 'url(' in value.lower() and not re.fullmatch(r'url\(#[A-Za-z][\w-]*\)',value):
                raise ValueError('Only local SVG marker references are allowed.')
        if element.tag == 'svg':
            try:
                x,y,w,h=map(float,element.get('viewBox','').split())
                if (x,y)!=(0,0) or not (100<=w<=2000 and 80<=h<=2000): raise ValueError()
            except ValueError:
                raise ValueError('SVG needs viewBox="0 0 width height", dimensions 100–2000 by 80–2000.') from None
        if 'font-size' in element.attrib:
            try: size=float(element.get('font-size'))
            except ValueError: raise ValueError('SVG font-size must be a number.') from None
            if not 16<=size<=80: raise ValueError('SVG text must be 16–80px. Use fewer labels instead of shrinking text.')
    if count>500: raise ValueError('Simplify the figure to fewer than 500 elements.')
    return ET.tostring(tree, encoding='unicode', method='html')


PANEL_PAGE_STYLE = ('*{box-sizing:border-box}html,body{margin:0;padding:0;background:#ffffff}'
                    'main{margin:0;padding:0}svg{display:block}')


def measure_text_widths(directory, strings, *, font_size=18, font_family=SVG_DEFAULT_FONT_FAMILY):
    """Measure rendered text widths in the same WebKit text stack the panel renderer uses.

    Application-owned wrapping measures each word once and adds them with the space width, so a
    simple recovery panel wraps exactly as the rasterizer will draw it.
    """
    strings = [str(value) for value in strings]
    if not strings:
        return []
    target = Path(directory) / ('measure-' + uuid.uuid4().hex)
    target.parent.mkdir(parents=True, exist_ok=True)
    spans = ''.join('<span data-key="' + str(index) + '">' + html.escape(value) + '</span>'
                    for index, value in enumerate(strings))
    page = ('<!doctype html><html><head><meta charset="utf-8">'
            '<meta name="localxiv-render-mode" content="measure">'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'">'
            '<style>*{box-sizing:border-box}html,body{margin:0;padding:0}'
            'main{font-family:' + font_family + ';font-size:' + str(font_size) + 'px;white-space:nowrap}'
            'span{display:inline-block;white-space:pre}</style></head><body><main>' + spans + '</main></body></html>')
    target.with_suffix('.html').write_text(page)
    executable = os.environ.get('LOCALXIV_HTML_RENDERER') or str(Path(__file__).with_name('html-snapshot'))
    if not Path(executable).is_file():
        raise ValueError('HTML renderer is missing. Build papers/HTMLSnapshot.swift as papers/html-snapshot '
                         '(see development instructions).')
    result = subprocess.run([executable, str(target.with_suffix('.html')), str(target)],
                            capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise ValueError('HTML text measurement failed: ' + result.stderr[-1000:])
    checks = json.loads(target.with_suffix('.checks.json').read_text())
    widths = {int(item['key']): float(item['width']) for item in checks.get('widths', [])}
    return [widths.get(index, 0.0) for index in range(len(strings))]


def render(directory, figure, paper_title, *, compact=False, mode='legacy'):
    """Render one figure through the native helper.

    ``legacy`` keeps the 960px Blog page. ``panel`` and ``overview`` render a complete SVG
    canvas at its intrinsic size and return its measured canvas, text runs, and element
    bounds under ``checks``.
    """
    if mode not in ('legacy', 'panel', 'overview'):
        raise ValueError('Unknown figure render mode: ' + str(mode))
    source_svg=figure.get('source_svg')
    standalone=source_svg is not None
    if mode == 'legacy':
        fragment=normalize_svg(source_svg) if standalone else sanitize(figure['html'])
    else:
        if not standalone:
            raise ValueError('Panel and overview rendering needs a complete SVG source.')
        fragment=normalize_svg(source_svg, external_markers=SHARED_MARKER_IDS, profile=mode)
        if mode == 'panel':
            fragment=with_shared_markers(fragment)
    relative = Path('reader/overview-figures') / uuid.uuid4().hex / figure['id']
    target = Path(directory) / relative
    target.parent.mkdir(parents=True)
    if standalone:
        target.with_suffix('.source.svg').write_text(fragment)
    esc=html.escape
    compact_style='.compact{padding:24px}.compact header{margin-bottom:16px}.compact h1{font-size:30px;line-height:1.15;margin:6px 0}.compact header p{font-size:21px;line-height:1.35;margin:8px 0 0}.compact footer{margin-top:16px;padding-top:12px}.compact .stack>*{margin-bottom:12px}'
    # The application owns the physical size of an authored figure: the SVG is fitted into the
    # remaining page height so any supported shape ratio renders without pushing the page past
    # 960px, and the native reading check still measures the resulting label sizes.
    overview_fit_style=('.compact.svg-overview{display:flex;flex-direction:column;max-height:960px}'
                        '.compact.svg-overview svg{min-height:0;max-height:100%}')
    classes=' '.join(name for name,enabled in (('compact',compact),('svg-overview',standalone)) if enabled)
    if mode == 'legacy':
        page='<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'"><style>'+STYLE+compact_style+overview_fit_style+'</style></head><body><main'+((' class="'+classes+'"') if classes else '')+'>'
        page+='<header><div class="label">LOCALXIV · '+esc(paper_title)+'</div><h1>'+esc(figure['title'])+'</h1><p>'+esc(figure['paper_connection'])+'</p></header>'
        page+=fragment+'<footer><strong>'+('Illustrative example. ' if figure['illustrative'] else 'Paper-grounded diagram. ')+'</strong>'+esc(figure['caption'])+'</footer></main></body></html>'
    else:
        page=('<!doctype html><html><head><meta charset="utf-8">'
              '<meta name="localxiv-render-mode" content="'+mode+'">'
              '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'">'
              '<style>'+PANEL_PAGE_STYLE+'</style></head><body><main class="overview-image">'+fragment+'</main></body></html>')
    target.with_suffix('.html').write_text(page)
    executable=os.environ.get('LOCALXIV_HTML_RENDERER') or str(Path(__file__).with_name('html-snapshot'))
    if not Path(executable).is_file():
        raise ValueError('HTML renderer is missing. Build papers/HTMLSnapshot.swift as papers/html-snapshot (see development instructions).')
    timeout=60 if mode == 'legacy' else 300
    result=subprocess.run([executable,str(target.with_suffix('.html')),str(target)],capture_output=True,text=True,timeout=timeout)
    if result.returncode: raise ValueError('HTML rendering failed: '+result.stderr[-1000:])
    checks=json.loads(target.with_suffix('.checks.json').read_text())
    checks.setdefault('issue_details',[])
    if compact and mode == 'legacy' and checks['height']>960:
        diagram=checks.get('diagram') or {}
        available=round(diagram.get('available_height',0))
        current=round(diagram.get('height',0))
        message=('Overview page is '+str(checks['height'])+'px tall; maximum 960px including heading and caption. '
                 'The heading and caption leave '+str(available)+'px of diagram height, and the current diagram is '
                 +str(current)+'px. Recompose to a shorter viewBox or remove repeated and secondary detail. '
                 'Do not shrink labels or crop content.')
        checks['issues'].append(message)
        checks['issue_details'].append({'code':'layout_fit','path':'figure-page','message':message,
            'constraint':'maximum_page_height_px','actual':checks['height'],'limit':960,
            'available_diagram_height':available,'diagram_height':current})
        target.with_suffix('.checks.json').write_text(json.dumps(checks))
    png=target.with_suffix('.png').read_bytes()
    if not png.startswith(b'\x89PNG\r\n\x1a\n'): raise ValueError('Renderer did not produce a PNG.')
    # Compatibility with existing full-page SVG consumers. New editable source is the separate .source.svg asset.
    image_width=checks.get('width',960)
    image_height=checks['height']
    target.with_suffix('.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="'+str(image_width)+'" height="'+str(image_height)+'" viewBox="0 0 '+str(image_width)+' '+str(image_height)+'"><title>'+esc(figure['title'])+'</title><image width="'+str(image_width)+'" height="'+str(image_height)+'" href="data:image/png;base64,'+base64.b64encode(png).decode()+'"/></svg>')
    assets={ext:str(relative)+'.'+ext for ext in ('html','svg','png','pdf')}
    if standalone:
        assets['svg_source']=str(relative)+'.source.svg'
    return {**assets,'checks':checks}
