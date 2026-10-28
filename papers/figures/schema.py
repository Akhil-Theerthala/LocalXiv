"""The Scene contract: node kinds, limits, the validator, and the strings a reader sees."""
import copy

from papers.explanation import NOTATION, ValidationError as SceneError, _flatten_text  # noqa: F401
from papers.figures.nodes import (LIMITS, MAX_DEPTH, PANEL_ID_RE, REGISTRY, TONES, Node, _check_text, _identifier,
                                  _panel_error, _subtree)





def collapse_repetitions(scene):
    """Remove the copies a reader would see twice. Returns the collapsed labels, for the run record.

    A card that repeats the heading of the group it stands in becomes that group's detail line: the
    Attention Overview of 2026-09-27 drew "Encoder layer" as a group heading and again as a card
    inside it, only to show its operation. An arrow to or from the removed card moves to the
    group's first or last card. A card whose label and detail both recur in a later panel keeps
    only its name there: the first panel draws the component in full.
    """
    collapsed = []
    for panel in scene['panels']:
        collapsed += _fold_heading_cards(panel)
    seen = {}
    for panel in scene['panels']:
        for node in _subtree(panel['body']):
            if node.get('kind') != 'card' or not node.get('detail'):
                continue
            key = (_flatten_text(node['label']).lower(), _flatten_text(node['detail']).lower())
            owner = seen.setdefault(key, panel['id'])
            if owner != panel['id']:
                del node['detail']
                collapsed.append(node['label'])
    return collapsed


def _fold_heading_cards(panel):
    folded, moved = [], {}

    def same(card, group):
        return card.get('kind') == 'card' and \
            _flatten_text(card.get('label')).lower() == _flatten_text(group['heading']).lower()

    def fold(node):
        if node.get('kind') != 'group':
            return node
        inside = {item['id'] for item in _subtree(node) if item.get('id')}
        node['children'] = [fold(child) for child in node.get('children') or []]
        if not node.get('heading'):
            return node
        twins = [child for child in node['children'] if same(child, node)]
        if len(node['children']) == 1 and twins and not node.get('detail'):
            # A frame around one card of its own name is that card.
            return twins[0]
        if not twins or (twins[0].get('detail') and node.get('detail')):
            return node
        twin = twins[0]
        node['children'].remove(twin)
        if twin.get('detail'):
            node['detail'] = twin['detail']
        folded.append(twin['label'])
        if twin.get('id'):
            moved[twin['id']] = (node, inside)
        return node

    panel['body'] = fold(panel['body'])
    if moved:
        edges, kept = [], set()
        for edge in panel.get('edges', []):
            edge = dict(edge)
            for name, other, pick in (('to', 'from', 0), ('from', 'to', -1)):
                if edge[name] not in moved:
                    continue
                group, inside = moved[edge[name]]
                # An arrow from a component to its own part drew containment; the frame shows it now.
                # An arrow from outside enters at the group's first card and leaves from its last.
                ends = [node['id'] for node in _subtree(group) if node.get('kind') == 'card' and node.get('id')]
                edge[name] = ends[pick] if ends and edge[other] not in inside else None
            key = (edge['from'], edge['to'])
            if None not in key and key[0] != key[1] and key not in kept:
                kept.add(key)
                edges.append(edge)
        panel['edges'] = edges
    return folded


# --- Overview scene ---------------------------------------------------------------------------
# The scene is what the reader sees, as a tree the application lays out. Its limits are the
# content budget; nothing in it names a coordinate, a size, or a gap.
KINDS = ('card', 'group', 'note', 'sequence', 'grid', 'steps', 'bars', 'divider', 'chart', 'stat')
MAX_PANELS = 4
MAX_NODES = 24
MAX_EDGES = 12
MAX_ACCENTS = 6




def card():
    """The vocabulary a model reads before it authors a Scene. Generated, so it cannot drift."""
    lines = ['You decide content and structure; the application decides every size, gap, and coordinate. '
             'A scene names no size, gap, or coordinate; the validator rejects them.',
             'Node kinds, all with "kind":']
    for kind in KINDS:
        node = REGISTRY[kind]
        fields = ', '.join('"' + name + '"' + ('?' if optional else '') + ': '
                           + doc.format(**LIMITS, tone='|'.join(TONES)) for name, doc, optional in node.field_docs)
        lines.append('- ' + kind + ': {' + fields + '} ' + node.summary.format(**LIMITS) + '.')
    lines.append('Groups nest at most %d deep. At most %d nodes and %d toned nodes per panel; a tone marks a '
                 'thing to notice, not a category.' % (MAX_DEPTH, MAX_NODES, MAX_ACCENTS))
    lines.append('Edges: {"from": card id, "to": card id, "label"? ≤%d, "accent"? true}. Arrows join cards of '
                 'the same panel, for data flow, not reading order. '
                 'At most %d per panel.' % (LIMITS['edge_label'], MAX_EDGES))
    lines.append('A panel: {"id", "heading" ≤%d, "tone"?: blue|green|peach, "body": one node, '
                 '"notes"?: [≤2 lines ≤%d], "edges"?}.' % (LIMITS['heading'], LIMITS['panel_note']))
    lines.append('A page may add "edges": [{"from": panel id, "to": the next panel id}] for an arrow between '
                 'side-by-side panels.')
    lines.append('Write math in ' + NOTATION + '.')
    return '\n'.join(lines)


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
        _check_text(scene, name, 'scene', errors, maximum=LIMITS[name])
    if not isinstance(scene.get('illustrative'), bool):
        _panel_error(errors, 'scene.illustrative', 'must be true or false')
    if scene.get('layout') not in ('stack', 'columns', 'auto'):
        _panel_error(errors, 'scene.layout', 'must be stack, columns, or auto')
    panels = scene.get('panels')
    if not isinstance(panels, list) or not 1 <= len(panels) <= MAX_PANELS:
        _panel_error(errors, 'scene.panels', f'needs 1 through {MAX_PANELS} panels')
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
        if scene.get('layout') not in ('columns', 'auto'):
            _panel_error(errors, path, 'joins panels only when layout is columns or auto')
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
    _check_text(panel, 'heading', path, errors, maximum=LIMITS['heading'])
    if 'tone' in panel and panel['tone'] not in ('blue', 'green', 'peach'):
        _panel_error(errors, path + '.tone', 'must be blue, green, or peach')
    ids, count = {}, [0, 0]
    _scene_node(panel.get('body'), path + '.body', 1, ids, count, errors)
    if count[1] > MAX_ACCENTS:
        _panel_error(errors, path + '.body', f'tones {count[1]} nodes blue, green, or peach; the limit is '
                                             f'{MAX_ACCENTS} per panel, for the things to notice')
    if count[0] > MAX_NODES:
        _panel_error(errors, path + '.body', f'has {count[0]} nodes; the limit is {MAX_NODES}')
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
            _check_text(edge, 'label', edge_path, errors, maximum=LIMITS['edge_label'])
def _scene_node(node, path, depth, ids, count, errors):
    if not isinstance(node, dict):
        _panel_error(errors, path, 'must be an object')
        return
    kind = node.get('kind')
    if kind not in KINDS:
        _panel_error(errors, path + '.kind', 'must be one of ' + ', '.join(KINDS))
        return
    for name in sorted(set(node) - REGISTRY[kind].fields):
        # A LoRA Blog panel put its edges inside the body twice under a bare "is unsupported".
        _panel_error(errors, path + '.' + name, 'is unsupported' + ('; edges belong on the panel, beside its body'
                                                                    if name == 'edges' else ''))
    if kind != 'group':
        count[0] += 1
    if 'tone' in node and node['tone'] not in TONES:
        _panel_error(errors, path + '.tone', 'must be one of ' + ', '.join(TONES))
    elif node.get('tone') in ('blue', 'green', 'peach') and kind != 'group':
        count[1] += 1
    for name, limit in REGISTRY[kind].optional_text.items():
        if name in node:
            _check_text(node, name, path, errors, maximum=LIMITS[limit])
    Node.of(node).validate(path, depth, errors, ids, count, _scene_node)


def headings(scene):
    """Every panel heading and group heading in the scene, for the containment coverage check."""
    headings = [str(panel['heading']) for panel in scene['panels']]
    headings += [str(node['heading']) for panel in scene['panels'] for node in _subtree(panel['body'])
                 if node['kind'] == 'group' and node.get('heading')]
    return headings


def text(scene):
    """Every string a reader can see in the scene, for coverage and density checks."""
    strings = [scene['title'], scene['subtitle'], scene['footer']]
    for panel in scene['panels']:
        strings.append(panel['heading'])
        strings.extend(panel.get('notes', []))
        strings.extend(edge.get('label', '') for edge in panel.get('edges', []))
        for node in _subtree(panel['body']):
            strings += Node.of(node).texts()
    return [str(value) for value in strings if str(value).strip()]
