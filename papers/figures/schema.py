"""The Scene contract: node kinds, limits, the validator, and the strings a reader sees."""
import copy
import json

from papers.figures.limits import (LIMITS, MAX_DEPTH, PANEL_ID_RE, TONES, _identifier, _panel_error,  # noqa: F401
                                   _scene_id, _scene_lines, _text)
from papers.figures.nodes import REGISTRY, Node


class SceneError(ValueError):
    """A structural panel-plan failure with an exact location for the next refinement."""
    def __init__(self, issues):
        self.issues = issues
        super().__init__('; '.join(issue['message'] for issue in issues[:20]) + '.')



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
MAX_PANELS = 4
MAX_NODES = 24
MAX_EDGES = 12
MAX_ACCENTS = 6


def _field(name, doc, optional=False):
    return {'name': name, 'doc': doc, 'optional': optional}


_TONE = 'blue|green|peach|muted'
# Each node class documents its own fields. The card the model reads and the JSON schema are
# generated from these tables, and a test checks they name every field the validator accepts.
NODE_FIELDS = {cls.kind: cls.fields for cls in REGISTRY.values()}
NODE_DOCS = {cls.kind: {'summary': cls.summary,
                        'fields': [_field(name, doc.replace('{tone}', _TONE), optional) for name, doc, optional in cls.field_docs]}
             for cls in REGISTRY.values()}


# One notation rule for every string a figure shows. The NTK Overview of 2026-09-25 wrote
# "Theta_inf^(L)" and "lambda_1" under the older rule, which allowed ASCII subscripts.
NOTATION = ('plain notation the figure shows as typed: Unicode letters and symbols (Θ λ Σ ∇ ∞ ≥ ≤ √ · × → α) and '
            'Unicode sub- and superscripts (λ₁, x², n₀, Θ⁽ᴸ⁾); an underscore only for a word subscript such as '
            'd_model; never LaTeX, braces, dollar signs, or a Greek letter spelled out such as Theta or lambda')


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
    lines.append('Write math in ' + NOTATION + '.')
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
        # A LoRA Blog panel put its edges inside the body twice under a bare "is unsupported".
        _panel_error(errors, path + '.' + name, 'is unsupported' + ('; edges belong on the panel, beside its body'
                                                                    if name == 'edges' else ''))
    if kind != 'group':
        count[0] += 1
    if 'tone' in node and node['tone'] not in TONES:
        _panel_error(errors, path + '.tone', 'must be one of ' + ', '.join(TONES))
    elif node.get('tone') in ('blue', 'green', 'peach') and kind != 'group':
        count[1] += 1
    Node.of(node).validate(path, depth, errors, ids, count, _scene_node)


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
            strings += Node.of(node).texts()
    return [str(value) for value in strings if str(value).strip()]
