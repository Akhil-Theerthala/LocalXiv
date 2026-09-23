"""The Scene contract: node kinds, limits, the validator, and the strings a reader sees."""
import copy
import json
import re

PANEL_ID_RE = re.compile(r'[A-Za-z][A-Za-z0-9_-]{0,31}')


class SceneError(ValueError):
    """A structural panel-plan failure with an exact location for the next refinement."""
    def __init__(self, issues):
        self.issues = issues
        super().__init__('; '.join(issue['message'] for issue in issues[:20]) + '.')



def _panel_error(errors, path, message, **details):
    errors.append({'code': 'panel_plan_validation', 'path': path, 'message': path + ' ' + message, **details})


def _text(item, key, path, errors, *, maximum=1200):
    value = item.get(key) if isinstance(item, dict) else None
    if not isinstance(value, str) or not value.strip():
        _panel_error(errors, path + '.' + key, f'needs 1-{maximum} characters of text')
    elif len(value) > maximum:
        _panel_error(errors, path + '.' + key,
                     f'has {len(value)} characters; the limit is {maximum}, so shorten it by at least '
                     f'{len(value) - maximum} characters',
                     constraint='maximum_characters', actual=len(value), limit=maximum)


def _identifier(value, path, errors, *, pattern, label):
    if not isinstance(value, str) or not pattern.fullmatch(value):
        _panel_error(errors, path, f'must be a safe {label}: a letter, then letters, digits, dashes or underscores')
        return None
    return value


def _flatten_text(value):
    return ' '.join(str(value or '').split())


def collapse_repetitions(scene):
    """A card whose label and detail both recur in a later panel keeps only its name there.

    The first panel draws the component in full; a later copy becomes a reference card. Returns
    the labels that were collapsed, for the run record.
    """
    seen = {}
    collapsed = []
    for panel in scene['panels']:
        for node in _walk_nodes(panel['body']):
            if node.get('kind') != 'card' or not node.get('detail'):
                continue
            key = (_flatten_text(node['label']).lower(), _flatten_text(node['detail']).lower())
            owner = seen.setdefault(key, panel['id'])
            if owner != panel['id']:
                del node['detail']
                collapsed.append(node['label'])
    return collapsed


def _walk_nodes(node):
    yield node
    if isinstance(node, dict) and node.get('kind') == 'group':
        for child in node.get('children') or []:
            yield from _walk_nodes(child)



# --- Overview scene ---------------------------------------------------------------------------
# The scene is what the reader sees, as a tree the application lays out. Its limits are the
# content budget; nothing in it names a coordinate, a size, or a gap.
KINDS = ('card', 'group', 'note', 'sequence', 'grid', 'steps', 'bars', 'divider', 'chart')
TONES = ('blue', 'green', 'peach', 'muted')
MAX_PANELS = 4
MAX_DEPTH = 4
MAX_NODES = 24
MAX_EDGES = 12
MAX_ACCENTS = 6
LIMITS = {'title': 100, 'subtitle': 240, 'footer': 320, 'heading': 80, 'note_line': 90,
                'panel_note': 160, 'label': 48, 'detail': 100, 'group_heading': 48, 'repeat': 16,
                'item': 16, 'sub': 20, 'cell': 12, 'grid_label': 16, 'caption': 90, 'step': 72, 'bar_label': 28,
                'divider': 48, 'edge_label': 28, 'series_label': 28, 'axis_label': 24}
NODE_FIELDS = {
    'card': {'kind', 'id', 'label', 'detail', 'tone', 'dashed', 'plain'},
    'group': {'kind', 'heading', 'repeat', 'arrange', 'tone', 'children'},
    'note': {'kind', 'lines'},
    'sequence': {'kind', 'items'},
    'grid': {'kind', 'rows', 'col_labels', 'row_labels', 'caption'},
    'steps': {'kind', 'lines'},
    'bars': {'kind', 'items', 'caption'},
    'divider': {'kind', 'label'},
    'chart': {'kind', 'series', 'x_label', 'y_label', 'caption', 'marks'},
}


def _field(name, doc, optional=False):
    return {'name': name, 'doc': doc, 'optional': optional}


_TONE = 'blue|green|peach|muted'
# One table documents every node kind. The card the model reads and the JSON schema are generated
# from it, and a test checks it names every field the validator accepts, so the three cannot drift.
NODE_DOCS = {
    'card': {'summary': 'one labelled box',
             'fields': [_field('id', 'needed when an edge joins it', True), _field('label', '≤{label}'),
                        _field('detail', '≤{detail} muted second line', True), _field('tone', _TONE, True),
                        _field('dashed', 'true for a discarded or optional state', True),
                        _field('plain', 'true for a non-bold label', True)]},
    'group': {'summary': 'a container; with a heading it draws a frame, for a component that holds its parts',
              'fields': [_field('heading', '≤{group_heading}', True), _field('repeat', '≤{repeat} such as "(N = 6)"', True),
                         _field('arrange', '"row" | "column"'), _field('tone', _TONE, True),
                         _field('children', '[1-8 nodes]')]},
    'note': {'summary': 'a small text block; the first line is bold',
             'fields': [_field('lines', '[1-4 strings ≤{note_line}]')]},
    'sequence': {'summary': 'tokens, values, or steps in a row, each with an optional caption under it',
                 'fields': [_field('items', '[2-8 of {{"id"?, "text" ≤{item}, "sub"? ≤{sub}, "tone"?, "hot"? true}}]')]},
    'grid': {'summary': 'a small matrix, at most 6×6; a cell is a number, a string ≤{cell}, "*value" to highlight it, or null when masked',
             'fields': [_field('rows', '[[cell]]'), _field('col_labels', '[≤{grid_label} each]', True),
                        _field('row_labels', '[≤{grid_label} each]', True), _field('caption', '≤{caption}', True)]},
    'steps': {'summary': 'a calculation the renderer numbers 1., 2., …; write the lines without numbers; the last line is the result',
              'fields': [_field('lines', '[1-6 strings ≤{step}]')]},
    'bars': {'summary': 'a comparison of values',
             'fields': [_field('items', '[2-8 of ["label" ≤{bar_label}, number]]'), _field('caption', '≤{caption}', True)]},
    'divider': {'summary': 'a dashed line, for a threshold or a boundary',
                'fields': [_field('label', '≤{divider}', True)]},
    'chart': {'summary': 'a line or scatter plot of 1 to 4 series; the application draws axes and ticks',
              'fields': [_field('series', '[1-4 of {{"label" ≤{series_label}, "points": [2-12 of [x, y]]}}]'),
                         _field('x_label', '≤{axis_label}', True), _field('y_label', '≤{axis_label}', True),
                         _field('caption', '≤{caption}', True), _field('marks', '"line" | "dots"', True)]},
}


def card():
    """The vocabulary a model reads before it authors a Scene. Generated, so it cannot drift."""
    lines = ['You decide content and structure; the application decides every size, gap, and coordinate. '
             'A scene names no size, gap, or coordinate; the validator rejects them.',
             'Node kinds, all with "kind":']
    for kind in KINDS:
        docs = NODE_DOCS[kind]
        fields = ', '.join('"' + field['name'] + '"' + ('?' if field['optional'] else '') + ': '
                           + field['doc'].format(**LIMITS) for field in docs['fields'])
        lines.append('- ' + kind + ': {' + fields + '} ' + docs['summary'].format(**LIMITS) + '.')
    lines.append('Groups nest at most %d deep. At most %d nodes and %d toned nodes per panel; a tone marks a '
                 'thing to notice, not a category.' % (MAX_DEPTH, MAX_NODES, MAX_ACCENTS))
    lines.append('Edges: {"from": card id, "to": card id, "label"? ≤%d, "accent"? true}. Arrows join cards of '
                 'the same panel, for data flow, not reading order. At most %d per panel.' % (LIMITS['edge_label'], MAX_EDGES))
    lines.append('A panel: {"id", "heading" ≤%d, "tone"?: blue|green|peach, "body": one node, "notes"?: [≤2 lines ≤%d], '
                 '"edges"?}.' % (LIMITS['heading'], LIMITS['panel_note']))
    lines.append('A page may add "edges": [{"from": panel id, "to": the next panel id}] for an arrow between '
                 'side-by-side panels.')
    return '\n'.join(lines)


def json_schema(frame='page'):
    """A JSON schema for structured output, from the same node table.

    The node schema is loose on purpose: the validator is the contract, and providers reject
    deeply recursive schemas. The page and panel shapes are exact.
    """
    node = {'type': 'object', 'properties': {'kind': {'type': 'string', 'enum': list(KINDS)}}, 'required': ['kind']}
    panel = {'type': 'object', 'required': ['id', 'heading', 'body'], 'additionalProperties': False,
             'properties': {'id': {'type': 'string'}, 'heading': {'type': 'string', 'maxLength': LIMITS['heading']},
                            'tone': {'type': 'string', 'enum': ['blue', 'green', 'peach']}, 'body': node,
                            'notes': {'type': 'array', 'maxItems': 2, 'items': {'type': 'string', 'maxLength': LIMITS['panel_note']}},
                            'edges': {'type': 'array', 'maxItems': MAX_EDGES, 'items': {'type': 'object'}}}}
    if frame == 'panel':
        return panel
    return {'type': 'object', 'required': ['title', 'subtitle', 'footer', 'illustrative', 'layout', 'panels'],
            'additionalProperties': False,
            'properties': {'title': {'type': 'string', 'maxLength': LIMITS['title']},
                           'subtitle': {'type': 'string', 'maxLength': LIMITS['subtitle']},
                           'footer': {'type': 'string', 'maxLength': LIMITS['footer']},
                           'illustrative': {'type': 'boolean'}, 'layout': {'type': 'string', 'enum': ['stack', 'columns']},
                           'panels': {'type': 'array', 'minItems': 1, 'maxItems': MAX_PANELS, 'items': panel},
                           'edges': {'type': 'array', 'maxItems': MAX_PANELS - 1, 'items': {'type': 'object'}}}}


def validate(value, *, frame='page'):
    """Validate one Scene (frame 'page') or one panel object (frame 'panel').

    Returns a deep copy or raises ``SceneError`` with the issue records a correction needs.
    """
    if frame not in ('page', 'panel'):
        raise ValueError('frame must be page or panel')
    errors = []
    if not isinstance(value, dict):
        raise SceneError([{'code': 'scene_validation', 'path': frame, 'message': frame + ' must be an object.'}])
    if frame == 'panel':
        _validate_panel(value, 'panel', errors)
        if errors:
            raise SceneError(errors[:20])
        return copy.deepcopy(value)
    scene = value
    required = {'title', 'subtitle', 'footer', 'illustrative', 'layout', 'panels'}
    for name in sorted(set(scene) - required - {'edges'}):
        _panel_error(errors, 'scene.' + name, 'is unsupported')
    for name in sorted(required - set(scene)):
        _panel_error(errors, 'scene.' + name, 'is required')
    for name in ('title', 'subtitle', 'footer'):
        _text(scene, name, 'scene', errors, maximum=LIMITS[name])
    if not isinstance(scene.get('illustrative'), bool):
        _panel_error(errors, 'scene.illustrative', 'must be true or false')
    if scene.get('layout') not in ('stack', 'columns'):
        _panel_error(errors, 'scene.layout', 'must be stack or columns')
    panels = scene.get('panels')
    if not isinstance(panels, list) or not 1 <= len(panels) <= MAX_PANELS:
        _panel_error(errors, 'scene.panels', f'needs 1 through {MAX_PANELS} panels',
                     constraint='maximum_panels', actual=len(panels) if isinstance(panels, list) else None,
                     limit=MAX_PANELS)
        panels = panels if isinstance(panels, list) else []
    seen_panels = set()
    for index, panel in enumerate(panels):
        path = f'scene.panels[{index}]'
        if not isinstance(panel, dict):
            _panel_error(errors, path, 'must be an object')
            continue
        identifier = panel.get('id')
        if identifier in seen_panels:
            _panel_error(errors, path + '.id', 'duplicates an earlier panel id')
        seen_panels.add(identifier)
        _validate_panel(panel, path, errors)
    edges = scene.get('edges', [])
    order = [panel.get('id') for panel in panels if isinstance(panel, dict)]
    if not isinstance(edges, list) or len(edges) > MAX_PANELS - 1:
        _panel_error(errors, 'scene.edges', f'needs at most {MAX_PANELS - 1} arrows between panels')
        edges = edges if isinstance(edges, list) else []
    for position, edge in enumerate(edges):
        path = f'scene.edges[{position}]'
        if not isinstance(edge, dict) or set(edge) - {'from', 'to', 'accent'}:
            _panel_error(errors, path, 'must be {"from", "to", "accent"?}')
            continue
        if scene.get('layout') != 'columns':
            _panel_error(errors, path, 'joins panels only when layout is columns')
        if (edge.get('from') not in order or edge.get('to') not in order
                or order.index(edge['to']) != order.index(edge['from']) + 1):
            _panel_error(errors, path, 'must join a panel to the next panel in order')
    if errors:
        raise SceneError(errors[:20])
    return copy.deepcopy(scene)


def _validate_panel(panel, path, errors):
    """The per-panel rules both frames share: fields, heading, tone, body, notes, edges."""
    for name in sorted(set(panel) - {'id', 'heading', 'tone', 'body', 'notes', 'edges'}):
        _panel_error(errors, path + '.' + name, 'is unsupported')
    for name in ('id', 'heading', 'body'):
        if name not in panel:
            _panel_error(errors, path, 'is missing ' + name)
    _identifier(panel.get('id'), path + '.id', errors, pattern=PANEL_ID_RE, label='panel id')
    _text(panel, 'heading', path, errors, maximum=LIMITS['heading'])
    if 'tone' in panel and panel['tone'] not in ('blue', 'green', 'peach'):
        _panel_error(errors, path + '.tone', 'must be blue, green, or peach')
    ids, count = {}, [0, 0]
    _scene_node(panel.get('body'), path + '.body', 1, ids, count, errors)
    if count[1] > MAX_ACCENTS:
        _panel_error(errors, path + '.body', f'tones {count[1]} nodes blue, green, or peach; the limit is '
                                             f'{MAX_ACCENTS} per panel, for the things to notice',
                     constraint='maximum_accents', actual=count[1], limit=MAX_ACCENTS)
    if count[0] > MAX_NODES:
        _panel_error(errors, path + '.body', f'has {count[0]} nodes; the limit is {MAX_NODES}',
                     constraint='maximum_nodes', actual=count[0], limit=MAX_NODES)
    notes = panel.get('notes', [])
    if not isinstance(notes, list) or len(notes) > 2 or any(
            not isinstance(line, str) or not line.strip() or len(line) > LIMITS['panel_note'] for line in notes):
        _panel_error(errors, path + '.notes', f'needs at most 2 lines of 1-{LIMITS["panel_note"]} characters')
    edges = panel.get('edges', [])
    if not isinstance(edges, list) or len(edges) > MAX_EDGES:
        _panel_error(errors, path + '.edges', f'needs at most {MAX_EDGES} arrows')
        edges = edges if isinstance(edges, list) else []
    for position, edge in enumerate(edges):
        edge_path = f'{path}.edges[{position}]'
        if not isinstance(edge, dict):
            _panel_error(errors, edge_path, 'must be an object')
            continue
        for name in sorted(set(edge) - {'from', 'to', 'label', 'accent'}):
            _panel_error(errors, edge_path + '.' + name, 'is unsupported')
        for name in ('from', 'to'):
            if edge.get(name) not in ids:
                _panel_error(errors, edge_path + '.' + name, 'must be the id of a card or sequence item in this panel')
        if edge.get('from') == edge.get('to'):
            _panel_error(errors, edge_path, 'joins a card to itself')
        if 'label' in edge:
            _text(edge, 'label', edge_path, errors, maximum=LIMITS['edge_label'])
def _scene_node(node, path, depth, ids, count, errors):
    if not isinstance(node, dict):
        _panel_error(errors, path, 'must be an object')
        return
    kind = node.get('kind')
    if kind not in KINDS:
        _panel_error(errors, path + '.kind', 'must be one of ' + ', '.join(KINDS))
        return
    for name in sorted(set(node) - NODE_FIELDS[kind]):
        _panel_error(errors, path + '.' + name, 'is unsupported')
    if kind != 'group':
        count[0] += 1
    if 'tone' in node and node['tone'] not in TONES:
        _panel_error(errors, path + '.tone', 'must be one of ' + ', '.join(TONES))
    elif node.get('tone') in ('blue', 'green', 'peach') and kind != 'group':
        count[1] += 1
    if kind == 'sequence':
        count[1] += sum(1 for item in node.get('items') or [] if isinstance(item, dict)
                        and item.get('tone') in ('blue', 'green', 'peach'))
    if kind == 'card':
        _text(node, 'label', path, errors, maximum=LIMITS['label'])
        if 'detail' in node:
            _text(node, 'detail', path, errors, maximum=LIMITS['detail'])
        _scene_id(node, path, ids, errors)
    elif kind == 'group':
        if depth > MAX_DEPTH:
            _panel_error(errors, path, f'nests deeper than {MAX_DEPTH} groups')
            return
        if 'heading' in node:
            _text(node, 'heading', path, errors, maximum=LIMITS['group_heading'])
        if 'repeat' in node:
            _text(node, 'repeat', path, errors, maximum=LIMITS['repeat'])
        if node.get('arrange') not in ('row', 'column'):
            _panel_error(errors, path + '.arrange', 'must be row or column')
        children = node.get('children')
        if not isinstance(children, list) or not 1 <= len(children) <= 8:
            _panel_error(errors, path + '.children', 'needs 1 through 8 nodes')
            return
        for index, child in enumerate(children):
            _scene_node(child, f'{path}.children[{index}]', depth + 1, ids, count, errors)
    elif kind == 'note':
        _scene_lines(node.get('lines'), path + '.lines', errors, maximum=4, length=LIMITS['note_line'])
    elif kind == 'sequence':
        items = node.get('items')
        if not isinstance(items, list) or not 2 <= len(items) <= 8:
            _panel_error(errors, path + '.items', 'needs 2 through 8 items')
            return
        for index, item in enumerate(items):
            item_path = f'{path}.items[{index}]'
            if not isinstance(item, dict):
                _panel_error(errors, item_path, 'must be an object')
                continue
            for name in sorted(set(item) - {'id', 'text', 'sub', 'tone', 'hot'}):
                _panel_error(errors, item_path + '.' + name, 'is unsupported')
            _text(item, 'text', item_path, errors, maximum=LIMITS['item'])
            if 'sub' in item:
                _text(item, 'sub', item_path, errors, maximum=LIMITS['sub'])
            if 'tone' in item and item['tone'] not in TONES:
                _panel_error(errors, item_path + '.tone', 'must be one of ' + ', '.join(TONES))
            _scene_id(item, item_path, ids, errors)
    elif kind == 'grid':
        rows = node.get('rows')
        if not isinstance(rows, list) or not 1 <= len(rows) <= 6 or any(
                not isinstance(row, list) or not 1 <= len(row) <= 6 for row in rows):
            _panel_error(errors, path + '.rows', 'needs 1 through 6 rows of 1 through 6 cells')
        else:
            for r, row in enumerate(rows):
                for c, cell in enumerate(row):
                    if cell is not None and not isinstance(cell, (int, float)) and (
                            not isinstance(cell, str) or len(cell.lstrip('*')) > LIMITS['cell']):
                        _panel_error(errors, f'{path}.rows[{r}][{c}]',
                                     f'must be a number, a string of at most {LIMITS["cell"]} characters, or null')
        for name in ('col_labels', 'row_labels'):
            if name in node:
                _scene_lines(node.get(name), path + '.' + name, errors, maximum=6, length=LIMITS['grid_label'])
        if 'caption' in node:
            _text(node, 'caption', path, errors, maximum=LIMITS['caption'])
    elif kind == 'steps':
        _scene_lines(node.get('lines'), path + '.lines', errors, maximum=6, length=LIMITS['step'])
    elif kind == 'bars':
        items = node.get('items')
        if not isinstance(items, list) or not 2 <= len(items) <= 8 or any(
                not isinstance(item, list) or len(item) != 2 or not isinstance(item[0], str)
                or not item[0].strip() or len(item[0]) > LIMITS['bar_label']
                or not isinstance(item[1], (int, float)) or item[1] < 0 for item in items):
            _panel_error(errors, path + '.items', 'needs 2 through 8 [label, number] pairs')
        if 'caption' in node:
            _text(node, 'caption', path, errors, maximum=LIMITS['caption'])
    elif kind == 'divider':
        if 'label' in node:
            _text(node, 'label', path, errors, maximum=LIMITS['divider'])
    elif kind == 'chart':
        series = node.get('series')
        if not isinstance(series, list) or not 1 <= len(series) <= 4:
            _panel_error(errors, path + '.series', 'needs 1 through 4 series')
            return
        for index, item in enumerate(series):
            item_path = f'{path}.series[{index}]'
            if not isinstance(item, dict) or set(item) - {'label', 'points'}:
                _panel_error(errors, item_path, 'must be {"label", "points"}')
                continue
            _text(item, 'label', item_path, errors, maximum=LIMITS['series_label'])
            points = item.get('points')
            if (not isinstance(points, list) or not 2 <= len(points) <= 12
                    or any(not isinstance(point, list) or len(point) != 2
                           or any(not isinstance(value, (int, float)) or isinstance(value, bool) for value in point)
                           for point in points)):
                _panel_error(errors, item_path + '.points', 'needs 2 through 12 [x, y] number pairs')
        for name in ('x_label', 'y_label'):
            if name in node:
                _text(node, name, path, errors, maximum=LIMITS['axis_label'])
        if 'caption' in node:
            _text(node, 'caption', path, errors, maximum=LIMITS['caption'])
        if 'marks' in node and node['marks'] not in ('line', 'dots'):
            _panel_error(errors, path + '.marks', 'must be line or dots')


def _scene_id(node, path, ids, errors):
    if 'id' not in node:
        return
    identifier = _identifier(node['id'], path + '.id', errors, pattern=PANEL_ID_RE, label='card id')
    if identifier in ids:
        _panel_error(errors, path + '.id', 'duplicates an earlier id in this panel')
    ids[identifier] = path


def _scene_lines(lines, path, errors, *, maximum, length):
    if not isinstance(lines, list) or not 1 <= len(lines) <= maximum or any(
            not isinstance(line, str) or not line.strip() for line in lines):
        _panel_error(errors, path, f'needs 1 through {maximum} strings of 1-{length} characters')
        return
    for index, line in enumerate(lines):
        if len(line) > length:
            _panel_error(errors, f'{path}[{index}]',
                         f'has {len(line)} characters; the limit is {length}, so shorten it by at least '
                         f'{len(line) - length} characters',
                         constraint='maximum_characters', actual=len(line), limit=length)



def _walk(node):
    yield node
    if node['kind'] == 'group':
        for child in node['children']:
            yield from _walk(child)


def headings(scene):
    """Every panel heading and group heading in the scene, for the containment coverage check."""
    headings = [str(panel['heading']) for panel in scene['panels']]
    headings += [str(node['heading']) for panel in scene['panels'] for node in _walk(panel['body'])
                 if node['kind'] == 'group' and node.get('heading')]
    return headings


def text(scene):
    """Every string a reader can see in the scene, for coverage and density checks."""
    strings = [scene['title'], scene['subtitle'], scene['footer']]
    for panel in scene['panels']:
        strings.append(panel['heading'])
        strings.extend(panel.get('notes', []))
        strings.extend(edge.get('label', '') for edge in panel.get('edges', []))
        for node in _walk(panel['body']):
            kind = node['kind']
            if kind == 'card':
                strings += [node['label'], node.get('detail', '')]
            elif kind == 'group':
                strings += [node.get('heading', ''), node.get('repeat', '')]
            elif kind == 'note':
                strings += node['lines']
            elif kind == 'sequence':
                strings += [item['text'] for item in node['items']] + [item.get('sub', '') for item in node['items']]
            elif kind == 'grid':
                strings += [str(cell).lstrip('*') for row in node['rows'] for cell in row if cell is not None]
                strings += node.get('col_labels', []) + node.get('row_labels', []) + [node.get('caption', '')]
            elif kind == 'steps':
                strings += node['lines']
            elif kind == 'bars':
                strings += [str(label) for label, _ in node['items']] + [node.get('caption', '')]
            elif kind == 'divider':
                strings.append(node.get('label', ''))
            elif kind == 'chart':
                strings += [item['label'] for item in node['series']]
                strings += [node.get('x_label', ''), node.get('y_label', ''), node.get('caption', '')]
    return [str(value) for value in strings if str(value).strip()]
