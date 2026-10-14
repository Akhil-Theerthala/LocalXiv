"""Evidence-linked contracts shared by selection, authoring and review."""
import copy
import json
import re

from papers.errors import ProviderError
from papers.figures.nodes import PANEL_ID_RE, _check_text, _identifier, _panel_error, _subtree
from papers.figures.schema import SceneError, _flatten_text
from papers.passages import cited_in, uncited

CLAIMS = ('question', 'contribution', 'finding', 'limitation')
PAPER_TYPES = ('architecture', 'method', 'survey', 'evaluation', 'theory', 'other')
TEXT = {'type':'string'}
PLAN_TEXT = {'type':'string','minLength':1,'maxLength':1200}
REFS = {'type':'array','items':TEXT,'minItems':1}


def object_schema(fields, required=None):
    return {'type':'object','properties':fields,
            'required':list(fields) if required is None else list(required),
            'additionalProperties':False}


def shape(schema):
    """A contract as the filled shape a model reads: each field name with the form of its value.

    A model shown the raw JSON schema copies its "type" and "properties" keys into the answer:
    deepseek-flash did so in three of six Blog narrative requests on 2026-09-25.
    """
    if 'anyOf' in schema:
        return '\nor '.join(shape(option) for option in schema['anyOf'])
    if 'enum' in schema:
        text = ' or '.join(json.dumps(value, ensure_ascii=False) for value in schema['enum'])
    elif schema.get('type') == 'object':
        required = set(schema.get('required', ()))
        text = '{' + ', '.join(json.dumps(name) + ('' if name in required else ' (optional)') + ': ' + shape(field)
                               for name, field in schema.get('properties', {}).items()) + '}'
    elif schema.get('type') == 'array':
        low, high = schema.get('minItems', 0), schema.get('maxItems')
        count = f'{low}-{high}' if high is not None else f'{low} or more' if low else 'any number of'
        item = shape(schema.get('items', {}))
        item = 'strings' + item[len('one string'):] if item.startswith('one string') else item
        text = '[' + count + ' ' + item + (', all different' if schema.get('uniqueItems') else '') + ']'
    elif schema.get('type') == 'string':
        low, high = schema.get('minLength', 0), schema.get('maxLength')
        text = 'one string' + (f' of {low}-{high} characters' if high else ', not empty' if low else '')
    elif schema.get('type') == 'boolean':
        text = 'true or false'
    else:
        text = 'a number' if schema.get('type') in ('integer', 'number') else 'a value'
    return text + (' (' + schema['description'] + ')' if schema.get('description') else '')


CLAIM_SCHEMA = object_schema({'text':PLAN_TEXT,'passages':REFS})
PLAN_SCHEMA = object_schema({
    'paper_type':{'type':'string','enum':list(PAPER_TYPES)},
    **{name:CLAIM_SCHEMA for name in CLAIMS},
    'visual_focus':PLAN_TEXT,
    'relationships':{'type':'array','minItems':1,'maxItems':12,'items':object_schema({'source':PLAN_TEXT,'target':PLAN_TEXT,'relationship':PLAN_TEXT,'passages':REFS})},
})

ID_ARRAY = {'type':'array','items':TEXT,'uniqueItems':True}


# --- Overview plan --------------------------------------------------------------------------
# One flat plan whose type is the content budget: at most four stacked panels, each with a short
# list of labels that are the exact display text, optional relations between labels, and one
# optional note. The validator rejects excess. Nothing in it asks for more content.
PANEL_CONTENT_KINDS = ('statement', 'value', 'equation', 'connection', 'qualification', 'label')
PANEL_IDENTIFIER = {'type':'string','minLength':1,'maxLength':32}
EXACT_TEXT_ITEM = {'type':'string','minLength':1,'maxLength':120}


# --- Blog draft and drawing briefs ----------------------------------------------------------
# A Blog figure is a validated brief, never SVG or HTML. The article text is cited Markdown and
# the application owns the surrounding article, caption, placement, and markup. Figure word
# limits do not apply; the article word limit does.
# The figures a Blog of each length plans: one for each section where a picture explains an
# operation, a relationship, a comparison, or a change. Before 2026-10-08 the cap was three, and
# most Blogs carried one.
BLOG_FIGURE_COUNTS = {'short': (1, 2), 'medium': (2, 4), 'large': (3, 6)}
BLOG_MARKUP_TOKENS = ('<svg', '<html', '<div', '<script')
BLOG_ENTRY_CONTEXT_ITEM = {'type':'string','minLength':1,'maxLength':1200}
BLOG_ILLUSTRATIVE_VALUE = {'type':'string','minLength':1,'maxLength':1200}
BLOG_CONTENT_SCHEMA = object_schema({
    'text':PLAN_TEXT,
    'kind':{'type':'string','enum':list(PANEL_CONTENT_KINDS)},
    'passages':{'type':'array','items':TEXT,'uniqueItems':True},
}, required=('text','kind'))
BLOG_BRIEF_SCHEMA = object_schema({
    'id':PANEL_IDENTIFIER,
    'title':{'type':'string','minLength':1,'maxLength':80},
    'paper_connection':PLAN_TEXT,
    'caption':PLAN_TEXT,
    'illustrative':{'type':'boolean'},
    'passages':{'type':'array','items':TEXT,'minItems':1,'uniqueItems':True},
    'purpose':PLAN_TEXT,
    'entry_context':{'type':'array','items':BLOG_ENTRY_CONTEXT_ITEM,'minItems':1,'maxItems':12},
    'exit_state':PLAN_TEXT,
    'content':{'type':'array','items':BLOG_CONTENT_SCHEMA,'minItems':1,'maxItems':8},
    'exact_text':{'type':'array','items':EXACT_TEXT_ITEM,'maxItems':8,'uniqueItems':True},
    'illustrative_values':{'type':'array','items':BLOG_ILLUSTRATIVE_VALUE,'uniqueItems':True},
})

# The Blog outline: the story's through-line, the terms and the section that explains each, the
# sections in order, and the figure briefs. Sections are then written in parallel from it.
BLOG_OUTLINE_SECTION_SCHEMA = object_schema({
    'id': {'type': 'string', 'description': 's1, s2, and on, in article order'},
    'heading': {'type': 'string', 'maxLength': 120, 'description': 'the question the section answers'},
    'answer': PLAN_TEXT,
    'points': {'type': 'array', 'minItems': 1, 'maxItems': 8,
               'items': object_schema({'text': PLAN_TEXT, 'passages': REFS})},
    'leaves_with': PLAN_TEXT,
    'figure': {'type': 'string', 'description': 'the id of the figure this section shows, or an empty string'},
    'words': {'type': 'integer', 'minimum': 40},
})
BLOG_OUTLINE_SCHEMA = object_schema({
    'title': TEXT,
    'rationale': PLAN_TEXT,
    'example': PLAN_TEXT,
    'terms': {'type': 'array', 'maxItems': 24,
              'items': object_schema({'term': TEXT, 'plain': PLAN_TEXT, 'section': TEXT})},
    'sections': {'type': 'array', 'minItems': 3, 'maxItems': 8, 'items': BLOG_OUTLINE_SECTION_SCHEMA},
    'figures': {'type': 'array', 'items': BLOG_BRIEF_SCHEMA, 'maxItems': 6},
})
BLOG_REVISION_REQUEST_SCHEMA = object_schema({
    'action': {'type': 'string', 'enum': ['revise_narrative']},
    'reason': PLAN_TEXT,
    'passage_ids': ID_ARRAY,
})
SELECTION_FIELDS = ('paper_type', 'focus', 'section_ids', 'passage_ids', 'figure_ids')


def validate_selection(selection, orientation):
    """Validate lookup handles before any retained file is opened."""
    errors=[]
    fields=set(SELECTION_FIELDS)
    if not isinstance(selection,dict):
        raise ValueError('Selection must be an object.')
    for name in sorted(set(selection)-fields):
        errors.append('selection.'+name+' is unsupported')
    for name in sorted(fields-set(selection)):
        errors.append('selection.'+name+' is required')
    paper_type=selection.get('paper_type')
    if paper_type not in PAPER_TYPES:
        errors.append('selection.paper_type must be one of '+', '.join(PAPER_TYPES))
    focus=selection.get('focus')
    if not isinstance(focus,str) or not focus.strip() or len(focus)>1200:
        errors.append('selection.focus needs 1-1200 characters')
    known={
        'section_ids':{item.get('id') for item in orientation.get('sections',[]) if isinstance(item,dict)},
        'passage_ids':{pid for item in orientation.get('sections',[]) if isinstance(item,dict)
                       for pid in item.get('passages',[])},
        'figure_ids':{item.get('id') for item in orientation.get('figures',[]) if isinstance(item,dict)},
    }
    selected_passages=set()
    for field in ('section_ids','passage_ids','figure_ids'):
        values=selection.get(field)
        if not isinstance(values,list) or any(not isinstance(value,str) for value in values):
            errors.append('selection.'+field+' must be an array of IDs')
            continue
        if len(values)!=len(set(values)):
            errors.append('selection.'+field+' must contain unique IDs')
        invalid=sorted(set(values)-known[field])
        if invalid:
            errors.append('selection.'+field+' has unknown IDs: '+', '.join(invalid[:12]))
        if field=='section_ids':
            selected_passages.update(pid for item in orientation.get('sections',[])
                                     if item.get('id') in values for pid in item.get('passages',[]))
        elif field=='passage_ids':
            selected_passages.update(set(values)&known[field])
        else:
            selected_passages.update(item.get('passage') for item in orientation.get('figures',[])
                                     if item.get('id') in values)
    if not selected_passages:
        errors.append('selection must resolve at least one substantive passage')
    if errors:
        raise ValueError('; '.join(errors[:20])+('.' if errors else ''))
    return copy.deepcopy(selection)


def _passage_refs(ids, known, path, errors, *, required, unique=False):
    """The known passage IDs in ``ids``, each one time, in order."""
    if not isinstance(ids, list) or any(not isinstance(value, str) for value in ids):
        _panel_error(errors, path, 'must be an array of passage IDs')
        return []
    if unique and len(set(ids)) != len(ids):
        _panel_error(errors, path, 'must contain unique passage IDs')
    unknown = sorted(set(ids) - known)
    if unknown:
        _panel_error(errors, path, 'has unknown passage IDs: ' + ', '.join(unknown[:12]))
    retained = list(dict.fromkeys(value for value in ids if value in known))
    if required and not retained:
        _panel_error(errors, path, 'needs at least one retained passage ID')
    return retained


# --- Overview digest ---------------------------------------------------------------------------
# The first pass over a paper: what a reader must know to understand its core in one image. The
# required fields are how "the core is present" becomes checkable. Components nest through
# ``contains`` and flow through ``feeds``; an operation belongs to the component that computes it.
DIGEST_LIMITS = {'claim': 400, 'why': 160, 'example': 320, 'hyperparameter': 48, 'name': 48, 'role': 160,
                 'computes': 100, 'values': 80, 'repeat': 16}
DIGEST_MIN_COMPONENTS, DIGEST_MAX_COMPONENTS = 4, 24
DIGEST_COMPONENT_FIELDS = {'id', 'name', 'role', 'computes', 'values', 'contains', 'feeds', 'repeat', 'passages'}
DIGEST_EXAMPLE_TYPES = ('architecture', 'method')


def validate_digest(digest, evidence):
    """Validate one Overview digest against the retained evidence. Returns a normalized copy."""
    errors = []
    known = {item['id'] for item in evidence.get('passages', []) if isinstance(item, dict)}
    if not isinstance(digest, dict):
        raise SceneError([{'code': 'digest_validation', 'path': 'digest', 'message': 'digest must be an object.'}])
    allowed = {'paper_type', 'why', 'contribution', 'result', 'qualification', 'example', 'hyperparameters',
               'components'}
    for name in sorted(set(digest) - allowed):
        _panel_error(errors, 'digest.' + name, 'is unsupported')
    for name in ('paper_type', 'why', 'contribution', 'result', 'qualification', 'components'):
        if name not in digest:
            _panel_error(errors, 'digest.' + name, 'is required')
    paper_type = digest.get('paper_type')
    if paper_type not in PAPER_TYPES:
        _panel_error(errors, 'digest.paper_type', 'must be one of ' + ', '.join(PAPER_TYPES))
    for name in ('contribution', 'result', 'qualification'):
        claim = digest.get(name)
        if not isinstance(claim, dict) or set(claim) - {'text', 'passages'}:
            _panel_error(errors, 'digest.' + name, 'must be an object with text and passages')
            continue
        _check_text(claim, 'text', 'digest.' + name, errors, maximum=DIGEST_LIMITS['claim'])
        _passage_refs(claim.get('passages'), known, 'digest.' + name + '.passages', errors, required=True)
    why = digest.get('why')
    if 'why' in digest and (not isinstance(why, dict) or set(why) != {'problem', 'obstacle', 'idea', 'passages'}):
        _panel_error(errors, 'digest.why', 'must be an object with problem, obstacle, idea, and passages')
    elif isinstance(why, dict):
        for name in ('problem', 'obstacle', 'idea'):
            _check_text(why, name, 'digest.why', errors, maximum=DIGEST_LIMITS['why'])
        _passage_refs(why.get('passages'), known, 'digest.why.passages', errors, required=True)
    if paper_type in DIGEST_EXAMPLE_TYPES or 'example' in digest:
        _check_text(digest, 'example', 'digest', errors, maximum=DIGEST_LIMITS['example'])
    hyperparameters = digest.get('hyperparameters', [])
    if not isinstance(hyperparameters, list) or len(hyperparameters) > 12:
        _panel_error(errors, 'digest.hyperparameters', 'needs at most 12 strings')
        hyperparameters = hyperparameters if isinstance(hyperparameters, list) else []
    for index, item in enumerate(hyperparameters):
        if not isinstance(item, str) or not item.strip():
            _panel_error(errors, f'digest.hyperparameters[{index}]', 'must be one nonempty string')
        elif len(item) > DIGEST_LIMITS['hyperparameter']:
            _panel_error(errors, f'digest.hyperparameters[{index}]',
                         f'has {len(item)} characters; the limit is {DIGEST_LIMITS["hyperparameter"]}, so '
                         f'shorten it by at least {len(item) - DIGEST_LIMITS["hyperparameter"]} characters')
    components = digest.get('components')
    if not isinstance(components, list) or not DIGEST_MIN_COMPONENTS <= len(components) <= DIGEST_MAX_COMPONENTS:
        _panel_error(errors, 'digest.components',
                     f'needs {DIGEST_MIN_COMPONENTS} through {DIGEST_MAX_COMPONENTS} components')
        components = components if isinstance(components, list) else []
    ids = {}
    for index, component in enumerate(components):
        path = f'digest.components[{index}]'
        if not isinstance(component, dict):
            _panel_error(errors, path, 'must be an object')
            continue
        identifier = _identifier(component.get('id'), path + '.id', errors, pattern=PANEL_ID_RE, label='component id')
        if identifier in ids:
            _panel_error(errors, path + '.id', 'duplicates an earlier component id')
        ids[identifier] = path
    for index, component in enumerate(components):
        path = f'digest.components[{index}]'
        if not isinstance(component, dict):
            continue
        for name in sorted(set(component) - DIGEST_COMPONENT_FIELDS):
            _panel_error(errors, path + '.' + name, 'is unsupported')
        for name in ('name', 'role', 'passages'):
            if name not in component:
                _panel_error(errors, path, 'is missing ' + name)
        _check_text(component, 'name', path, errors, maximum=DIGEST_LIMITS['name'])
        _check_text(component, 'role', path, errors, maximum=DIGEST_LIMITS['role'])
        for name in ('computes', 'values', 'repeat'):
            if name in component and component[name] is not None:
                _check_text(component, name, path, errors, maximum=DIGEST_LIMITS[name])
        for name in ('contains', 'feeds'):
            refs = component.get(name, [])
            if not isinstance(refs, list) or any(not isinstance(ref, str) for ref in refs):
                _panel_error(errors, path + '.' + name, 'must be an array of component ids')
                continue
            for ref in refs:
                if ref not in ids:
                    _panel_error(errors, path + '.' + name, 'names an unknown component: ' + ref)
                elif ref == component.get('id'):
                    _panel_error(errors, path + '.' + name, 'names the component itself')
        _passage_refs(component.get('passages'), known, path + '.passages', errors, required=True)
    if paper_type == 'architecture' and components and not any(
            isinstance(item, dict) and item.get('contains') for item in components):
        _panel_error(errors, 'digest.components', 'must nest at least one component inside another '
                                                  '(a layer contains its sub-layers)')
    if paper_type in DIGEST_EXAMPLE_TYPES and components and not any(
            isinstance(item, dict) and item.get('computes') for item in components):
        _panel_error(errors, 'digest.components', 'must give the operation at least one component computes')
    if errors:
        raise SceneError(errors[:20])
    why = digest['why']
    normalized = {'paper_type': paper_type,
                  'why': {**{name: why[name] for name in ('problem', 'obstacle', 'idea')},
                          'passages': list(dict.fromkeys(why['passages']))},
                  **{name: {'text': digest[name]['text'], 'passages': list(dict.fromkeys(digest[name]['passages']))}
                     for name in ('contribution', 'result', 'qualification')},
                  'hyperparameters': list(hyperparameters), 'components': []}
    if digest.get('example'):
        normalized['example'] = digest['example']
    for component in components:
        entry = {'id': component['id'], 'name': component['name'], 'role': component['role'],
                 'contains': list(component.get('contains') or []), 'feeds': list(component.get('feeds') or []),
                 'passages': list(dict.fromkeys(component['passages']))}
        for name in ('computes', 'values', 'repeat'):
            if component.get(name):
                entry[name] = component[name]
        normalized['components'].append(entry)
    return normalized


def digest_requirements(digest):
    """The strings a scene must show: every component name and every operation it computes."""
    required = []
    for component in digest['components']:
        required.append(component['name'])
        if component.get('computes'):
            required.append(component['computes'])
    return list(dict.fromkeys(required))


_NUMBER = re.compile(r'\d+(?:\.\d+)?')
_QUOTED = re.compile(r'["\u201c]([^"\u201d]{1,30})["\u201d]')


def example_coverage_issues(digest, scene_strings):
    """The running example must reach the scene: two of its numbers, or one of its quoted tokens."""
    example = str(digest.get('example') or '')
    if not example.strip():
        return []
    shown = _flatten_text(' '.join(scene_strings)).lower()
    numbers = [token for token in dict.fromkeys(_NUMBER.findall(example)) if len(token) > 1 or token.isdigit()]
    quoted = list(dict.fromkeys(_QUOTED.findall(example)))
    wanted = numbers if len(numbers) >= 2 else quoted
    if not wanted:
        return []
    hits = [token for token in wanted if token.lower() in shown]
    needed = 2 if wanted is numbers else 1
    if len(hits) >= needed:
        return []
    return [{'code': 'scene_coverage', 'path': 'scene', 'value': example[:80],
             'message': 'the scene does not carry the running example ' + json.dumps(example[:120])
                        + '; show at least ' + str(needed) + ' of its values '
                        + json.dumps(wanted[:6]) + ' in a sequence, steps, or grid in the first panel'}]


def example_structure_issues(digest, scene):
    """A digest example must be drawn as values, not as boxes around them, for every paper type.

    gpt-6-luna drew the Attention example as three cards, "making", the head, and "more
    difficult", and sonnet-5.5 wrote the AI Control numbers into card details; 36 of 43 saved
    scenes drew it as a sequence, steps, or a grid. haiku-5.5 typed AI Control as an evaluation,
    which the rule skipped, and drew no worked example at all.
    """
    if not str(digest.get('example') or '').strip():
        return []
    if any(node['kind'] in ('sequence', 'steps', 'grid') for panel in scene['panels']
           for node in _subtree(panel['body'])):
        return []
    return [{'code': 'scene_coverage', 'path': 'scene', 'value': 'example',
             'message': 'the scene draws the running example only as cards; show its tokens or values as a '
                        'sequence, the arithmetic as steps, or a small matrix as a grid, in the panel '
                        'that walks through the mechanism, with an edge into the card that uses them'}]


_POINT = re.compile(r'(?<![\w.])\d+(?:\.\d+)?\s*[%kKMBx×]?\s*:\s*[-−]?\d')


def series_text_issues(scene):
    """Measured points written into a card detail belong in a chart.

    sonnet-5.5 wrote the AI Control safety and usefulness trade-off as "Defer 5%: 74/95; 20%:
    92/83; 50%: 100/51" in three cards beside an unused chart kind.
    """
    issues = []
    for panel in scene['panels']:
        for card in (node for node in _subtree(panel['body']) if node['kind'] == 'card'):
            points = len(_POINT.findall(str(card.get('detail', ''))))
            if points >= 3:
                issues.append({'code': 'scene_coverage', 'path': 'scene.panels.' + str(panel['id']),
                               'value': card['label'],
                               'message': 'the card ' + json.dumps(card['label']) + ' lists ' + str(points)
                                          + ' measured points in its detail; draw them as a chart with one '
                                          'series per method, "marks": "line" along an ordered factor or '
                                          '"dots" for two measures against each other, and keep each '
                                          'method name as a series label or card label'})
    return issues


def story_issues(scene):
    """The story rules of the 2026-10-08 Overview: a why panel first, stats in the result, one fact per detail."""
    issues = []

    def issue(value, message):
        issues.append({'code': 'scene_coverage', 'path': 'scene', 'value': value, 'message': message})

    first = scene['panels'][0]
    cards = [node for node in _subtree(first['body']) if node['kind'] == 'card']
    if first.get('id') != 'why' or len(cards) != 3 or len(first.get('edges', [])) != 2:
        issue('why', 'the first panel must have the id "why" and a row of three cards joined by two edges: the '
                     "digest's why.problem, why.obstacle, and why.idea")
    if not any(node['kind'] == 'stat' for node in _subtree(scene['panels'][-1]['body'])):
        issue('stat', 'the last panel must open with one to three stat nodes for the headline numbers of the '
                      "digest's result")
    for panel in scene['panels']:
        for node in _subtree(panel['body']):
            if node['kind'] == 'card' and str(node.get('detail', '')).count('; ') > 1:
                issue(node['label'], 'the card ' + json.dumps(node['label']) + ' packs '
                      + str(node['detail'].count('; ') + 1) + ' facts into its detail; keep one fact, the '
                      'operation it computes or one value, and move the rest to the footer or a stat')
    return issues


def normalize_digest_candidate(value):
    """Accept harmless shape variants before validation.

    An ``example`` given as an object with ``text`` becomes its text, and a component's
    reference to itself is dropped; neither carries information the validator should reject.
    """
    if not isinstance(value, dict):
        return value
    example = value.get('example')
    if isinstance(example, dict) and isinstance(example.get('text'), str):
        value['example'] = example['text']
    if not isinstance(value.get('components'), list):
        return value
    for component in value['components']:
        if not isinstance(component, dict):
            continue
        for name in ('contains', 'feeds'):
            refs = component.get(name)
            if isinstance(refs, list):
                component[name] = [ref for ref in refs if ref != component.get('id')]
    return value


def scene_coverage_issues(digest, group_headings):
    """The containment rule, as validator issues for the correction request.

    A component with two or more parts of its own must appear as a group heading, or as a panel
    heading when the panel is about it, so the picture keeps the hierarchy the digest established.
    A part shared by several components is drawn once, so those components may be cards. The
    string check is ``Figure.missing`` with ``digest_requirements``.
    """
    headings = [_flatten_text(heading).lower() for heading in group_headings]
    issues = []
    owners = {}
    for component in digest['components']:
        for part in component.get('contains') or []:
            owners.setdefault(part, []).append(component['id'])
    for component in digest['components']:
        own = [part for part in component.get('contains') or [] if owners.get(part) == [component['id']]]
        if len(own) < 2:
            continue
        name = _flatten_text(component['name']).lower()
        if not any(name in heading for heading in headings):
            issues.append({'code': 'scene_coverage', 'path': 'scene', 'value': component['name'],
                           'message': 'the component ' + json.dumps(component['name']) + ' contains '
                                      + ', '.join(own[:4]) + ', so it must be a group whose heading '
                                      'is its name and whose detail is its operation, holding the nodes '
                                      'of its parts, or the panel '
                                      'about it must carry its name in the panel heading'})
    return issues


def digest_passages(digest):
    refs = []
    # A digest saved before 2026-10-08 has no why.
    refs.extend((digest.get('why') or {}).get('passages', []))
    for name in ('contribution', 'result', 'qualification'):
        refs.extend(digest[name]['passages'])
    for component in digest['components']:
        refs.extend(component['passages'])
    return list(dict.fromkeys(refs))


def blog_panel_required(brief):
    """Every string a Blog figure's Scene panel must show verbatim."""
    return list(brief.get('exact_text') or []) + list(brief.get('illustrative_values') or [])


def _blog_strings(value, path):
    """Yield ``(path, text)`` for every string value in a JSON-like structure."""
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for name, item in value.items():
            yield from _blog_strings(item, path + '.' + str(name) if path else str(name))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _blog_strings(item, path + '[' + str(index) + ']')


def _blog_reject_markup(value, path, errors):
    """Reject SVG or HTML markup anywhere in a Blog draft string field."""
    for text_path, text in _blog_strings(value, path):
        lowered = text.lower()
        for token in BLOG_MARKUP_TOKENS:
            if token in lowered:
                _panel_error(errors, text_path,
                             'must not contain ' + token + ' markup; the application owns the '
                             'surrounding article, caption, placement, and markup.')
                break


def _blog_text(item, key, path, errors, *, maximum=1200):
    value = item.get(key) if isinstance(item, dict) else None
    if isinstance(value, (list, dict)):
        # deepseek-flash wrote exit_state as a one-item list like its neighbour entry_context.
        _panel_error(errors, path + '.' + key, 'must be one string of 1-' + str(maximum) + ' characters, not '
                     + ('a list' if isinstance(value, list) else 'an object'))
    elif isinstance(value, str) and len(value) > maximum:
        # A value cut by the exact excess came back over the limit again: ask for a margin.
        _panel_error(errors, path + '.' + key, f'has {len(value)} characters; the limit is {maximum}, so shorten it '
                     f'to about {maximum * 11 // 12} characters while preserving required detail')
    elif not isinstance(value, str) or not value.strip():
        _panel_error(errors, path + '.' + key, 'needs 1-' + str(maximum) + ' characters')


def _blog_string_items(values, path, errors, *, minimum=0, maximum=None, length=1200, unique=False):
    if not isinstance(values, list):
        _panel_error(errors, path, 'must be an array of strings')
        return []
    if len(values) < minimum or (maximum is not None and len(values) > maximum):
        bounds = ('at least ' + str(minimum) if maximum is None
                  else str(minimum) + ' through ' + str(maximum))
        _panel_error(errors, path, 'needs ' + bounds + ' items')
    normalized = []
    for index, value in enumerate(values):
        item_path = path + '[' + str(index) + ']'
        if not isinstance(value, str) or not value.strip() or len(value) > length:
            _panel_error(errors, item_path, 'needs 1-' + str(length) + ' characters')
            continue
        normalized.append(value)
    if unique and len(set(normalized)) != len(normalized):
        _panel_error(errors, path, 'must contain unique strings')
    return normalized


def _blog_content_items(values, known, path, errors):
    if not isinstance(values, list) or not 1 <= len(values) <= 8:
        _panel_error(errors, path, 'needs 1 through 8 ordered items')
        values = values if isinstance(values, list) else []
    normalized = []
    for index, item in enumerate(values):
        item_path = path + '[' + str(index) + ']'
        if not isinstance(item, dict):
            _panel_error(errors, item_path, 'must be an object')
            continue
        for name in sorted(set(item) - {'text', 'kind', 'passages'}):
            _panel_error(errors, item_path + '.' + name, 'is unsupported')
        for name in ('text', 'kind'):
            if name not in item:
                _panel_error(errors, item_path, 'is missing ' + name)
        _blog_text(item, 'text', item_path, errors)
        if item.get('kind') not in PANEL_CONTENT_KINDS:
            _panel_error(errors, item_path + '.kind',
                         'must be one of ' + ', '.join(PANEL_CONTENT_KINDS))
        entry = {'text': item.get('text'), 'kind': item.get('kind')}
        if 'passages' in item:
            entry['passages'] = _passage_refs(item.get('passages'), known,
                                              item_path + '.passages', errors, required=False, unique=True)
        normalized.append(entry)
    return normalized


def _validate_blog_brief(brief, document, errors, prefix, figure_id=None):
    """Validate one Blog drawing brief, appending issues under ``prefix``.

    Returns the normalized brief when it introduces no new issues, otherwise ``None``.
    """
    path = prefix or 'brief'
    start = len(errors)
    if not isinstance(brief, dict):
        _panel_error(errors, path, 'must be an object')
        return None
    allowed = set(BLOG_BRIEF_SCHEMA['properties'])
    for name in sorted(set(brief) - allowed):
        _panel_error(errors, path + '.' + name, 'is unsupported')
    for name in sorted(allowed - set(brief)):
        _panel_error(errors, path, 'is missing ' + name)
    _blog_reject_markup(brief, path, errors)
    known = {item.get('id') for item in document.get('passages', []) if isinstance(item, dict)}
    identifier = brief.get('id')
    if not isinstance(identifier, str) or not PANEL_ID_RE.fullmatch(identifier):
        _panel_error(errors, path + '.id', 'must be a safe figure id: a letter, then letters, '
                                           'digits, dashes, or underscores')
        identifier = None
    else:
        if not re.fullmatch(r'fig[1-6]', identifier):
            _panel_error(errors, path + '.id', 'must be fig1 through fig6')
        if figure_id is not None and identifier != figure_id:
            _panel_error(errors, path + '.id',
                         'must stay ' + figure_id + ' when the brief is corrected')
    _blog_text(brief, 'title', path, errors, maximum=80)
    _blog_text(brief, 'paper_connection', path, errors)
    _blog_text(brief, 'caption', path, errors)
    if type(brief.get('illustrative')) is not bool:
        _panel_error(errors, path + '.illustrative', 'must be true or false')
    passages = _passage_refs(brief.get('passages'), known, path + '.passages',
                             errors, required=True, unique=True)
    _blog_text(brief, 'purpose', path, errors)
    entry_context = _blog_string_items(brief.get('entry_context'), path + '.entry_context',
                                       errors, minimum=1, maximum=12)
    _blog_text(brief, 'exit_state', path, errors)
    content = _blog_content_items(brief.get('content'), known, path + '.content', errors)
    exact_text = _blog_string_items(brief.get('exact_text'), path + '.exact_text',
                                    errors, maximum=8, length=120, unique=True)
    illustrative_values = _blog_string_items(brief.get('illustrative_values'),
                                             path + '.illustrative_values', errors, unique=True)
    if len(errors) != start:
        return None
    return {
        'id': identifier,
        'title': brief['title'],
        'paper_connection': brief['paper_connection'],
        'caption': brief['caption'],
        'illustrative': brief['illustrative'],
        'passages': passages,
        'purpose': brief['purpose'],
        'entry_context': entry_context,
        'exit_state': brief['exit_state'],
        'content': content,
        'exact_text': exact_text,
        'illustrative_values': illustrative_values,
    }


def validate_blog_outline(outline, document, length):
    """Validate one Blog outline and return its normalized copy.

    Every point cites retrieved passages, every term belongs to a section and appears in no earlier
    section's heading, answer, or points, every figure is named by exactly one section, the
    figure count follows ``length``, and the title and headings have no em dash or en dash between
    words.
    """
    errors = []
    if not isinstance(outline, dict):
        _panel_error(errors, 'outline', 'must be an object')
        raise SceneError(errors)
    known = {item['id'] for item in document.get('passages', [])}
    for name in sorted(set(outline) - set(BLOG_OUTLINE_SCHEMA['properties'])):
        _panel_error(errors, 'outline.' + name, 'is unsupported')
    for name in ('title', 'rationale', 'example'):
        if not isinstance(outline.get(name), str) or not outline[name].strip():
            _panel_error(errors, 'outline.' + name, 'needs text')
    if isinstance(outline.get('title'), str):
        _dash_errors(outline['title'], 'outline.title', errors)
    sections = outline.get('sections')
    if not isinstance(sections, list) or not 3 <= len(sections) <= 8:
        _panel_error(errors, 'outline.sections', 'needs 3 to 8 sections')
        sections = sections if isinstance(sections, list) else []
    section_ids, shaped, named = [], [], {}
    for index, section in enumerate(sections):
        path = f'outline.sections[{index}]'
        if not isinstance(section, dict) or set(section) != set(BLOG_OUTLINE_SECTION_SCHEMA['properties']):
            _panel_error(errors, path, 'must have exactly ' + ', '.join(BLOG_OUTLINE_SECTION_SCHEMA['properties']))
            continue
        if section['id'] != f's{index + 1}':
            _panel_error(errors, path + '.id', f'must be s{index + 1}: sections are numbered in article order')
        section_ids.append(section['id'])
        shaped.append((path, section))
        for name in ('heading', 'answer', 'leaves_with'):
            if not isinstance(section[name], str) or not section[name].strip():
                _panel_error(errors, path + '.' + name, 'needs text')
        if isinstance(section['heading'], str):
            _dash_errors(section['heading'], path + '.heading', errors)
        points = section['points']
        if not isinstance(points, list) or not points:
            _panel_error(errors, path + '.points', 'needs at least one point')
            points = []
        for number, point in enumerate(points):
            if not isinstance(point, dict) or not isinstance(point.get('text'), str) or not point['text'].strip():
                _panel_error(errors, f'{path}.points[{number}]', 'needs text and passages')
                continue
            _passage_refs(point.get('passages'), known, f'{path}.points[{number}].passages', errors, required=True)
        if not isinstance(section['words'], int) or section['words'] < 40:
            _panel_error(errors, path + '.words', 'must be a whole number of at least 40')
        if section['figure']:
            named.setdefault(section['figure'], []).append(section['id'])
    terms = outline.get('terms', [])
    for index, item in enumerate(terms if isinstance(terms, list) else []):
        if not isinstance(item, dict) or item.get('section') not in section_ids:
            _panel_error(errors, f'outline.terms[{index}].section', 'must name a section id of this outline')
            continue
        if not isinstance(item.get('term'), str) or not item['term'].strip():
            _panel_error(errors, f'outline.terms[{index}].term', 'needs text')
            continue
        # A section writer opens with the outline's answer and must not use a later section's
        # term, so the outline cannot put the term in an earlier section's text.
        pattern = blog_term_pattern(item['term'])
        for path, section in shaped[:section_ids.index(item['section'])]:
            texts = [('heading', section['heading']), ('answer', section['answer'])]
            texts += [(f'points[{number}].text', point['text']) for number, point in enumerate(section['points'])
                      if isinstance(point, dict) and isinstance(point.get('text'), str)]
            for name, value in texts:
                if isinstance(value, str) and pattern.search(value):
                    _panel_error(errors, f'{path}.{name}', f'uses the term "{item["term"]}", which {item["section"]} '
                                                           'owns; the section that explains a term is the first to '
                                                           'use it')
    figures = outline.get('figures')
    normalized_figures = []
    if not isinstance(figures, list):
        _panel_error(errors, 'outline.figures', 'must be an array of figure briefs')
        figures = []
    elif length in BLOG_FIGURE_COUNTS and not (BLOG_FIGURE_COUNTS[length][0] <= len(figures)
                                               <= BLOG_FIGURE_COUNTS[length][1]):
        low, high = BLOG_FIGURE_COUNTS[length]
        _panel_error(errors, 'outline.figures',
                     f'has {len(figures)} briefs; a {length} Blog plans {low} to {high}, one for each section where '
                     'a picture explains an operation, a relationship, a comparison, or a change')
    for index, brief in enumerate(figures):
        normalized = _validate_blog_brief(brief, document, errors, f'outline.figures[{index}]')
        if normalized is None:
            continue
        if normalized['id'] != f'fig{index + 1}':
            _panel_error(errors, f'outline.figures[{index}].id',
                         f'must be fig{index + 1}: figures are numbered in order')
        elif len(named.get(normalized['id'], [])) != 1:
            _panel_error(errors, f'outline.figures[{index}]',
                         'must be named by exactly one section in its figure field')
        normalized_figures.append(normalized)
    for figure_id in sorted(set(named) - {brief['id'] for brief in normalized_figures}):
        _panel_error(errors, 'outline.sections', f'names {figure_id}, which has no brief in figures')
    if errors:
        raise SceneError(errors[:20])
    return copy.deepcopy(dict(outline, figures=normalized_figures, terms=terms if isinstance(terms, list) else []))


# A section body may run to this many times its outline target before the application rejects it.
# The band is loose because a model counts words poorly; a tight band would spend every attempt on
# counting.
BLOG_SECTION_WORD_CEILING = 1.5
_FIGURE_MARKER = re.compile(r'\{\{figure:([^}]+)\}\}')
# A sentence ends at its punctuation or at a paragraph break, so a figure marker line stands alone.
_SENTENCE_END = re.compile(r'(?<=[.!?])\s+|\n\s*\n')
# A passage citation may sit between a term and the verb that explains it: "attention [p00017] is".
_CITATION_GAP = r'(?:\s*\[[^\]]*\])*'


def blog_term_pattern(term):
    """The term as a whole word, singular or plural, in any case."""
    return re.compile(r'(?<!\w)' + re.escape(' '.join(term.split())) + r'(?:e?s)?(?!\w)', re.IGNORECASE)


def _explains_pattern(term):
    """A sentence explains a term when it opens with the term, after an optional article, followed
    by is, are, means, or refers to, or when the term follows called, named, or known as.

    The term as a subject anywhere else is a measurement, not an explanation: on 2026-10-08
    "At a 2% budget, safety is 15%" was listed as a repeat of "Safety is the probability that".
    """
    word = blog_term_pattern(term).pattern
    return re.compile(r'\b(?:called|named|known as)\s+["\u201c]?' + word
                      + r'|\A(?:(?:a|an|the)\s+)?' + word + r'["\u201d]?' + _CITATION_GAP
                      + r'\s+(?:is|are|means|refers to)\b', re.IGNORECASE)


def _sentences(text):
    return [sentence for sentence in _SENTENCE_END.split(text) if sentence.strip()]


# An en dash between two numbers is a range, as in "pages 770–778", so only one beside a letter or
# between spaces is punctuation.
_DASHES = re.compile(r'\u2014|\s\u2013\s|(?<=[^\W\d_])\u2013|\u2013(?=[^\W\d_])')


def _dash_errors(text, path, errors):
    for match in _DASHES.finditer(text):
        near = json.dumps(text[max(0, match.start() - 30):match.end() + 30], ensure_ascii=False)
        if '\u2014' in match.group():
            _panel_error(errors, path, 'has an em dash in ' + near + '; replace the em dash with a period or a comma')
        else:
            _panel_error(errors, path, 'has an en dash in ' + near + '; replace the en dash with a hyphen, a period, '
                                       'or a comma')


def validate_blog_section(body, outline, index, document):
    """Check one section body against its outline entry and return it without a repeated heading.

    The body is rejected, with one exact message for each failed check, when its figure markers
    are not the section's, a citation names an unknown passage, a point's passages are all
    uncited, its words (without citations and markers) are above ``BLOG_SECTION_WORD_CEILING``
    times the section's target, it uses a term a later section owns, or it has an em dash or an en
    dash between words.
    """
    errors = []
    section = outline['sections'][index]
    path = 'sections[' + str(index) + ']'
    # The application writes the heading; a body that repeats it keeps the body only.
    body = re.sub(r'\A#+ [^\n]*\n+', '', body.strip())
    expected = [section['figure']] if section['figure'] else []
    markers = _FIGURE_MARKER.findall(body)
    if markers != expected:
        needed = ('{{figure:' + expected[0] + '}} once') if expected else 'no figure marker'
        _panel_error(errors, path, 'has figure markers ' + json.dumps(markers) + '; it needs ' + needed)
    # The HTML export replaces a marker only when it is a paragraph of its own; inside a paragraph
    # the marker's text would reach the reader.
    for line in body.splitlines():
        if _FIGURE_MARKER.search(line) and not _FIGURE_MARKER.fullmatch(line.strip()):
            _panel_error(errors, path, 'has ' + line.strip()[:80] + ' inside a paragraph; put the marker on a line of '
                                       'its own after the paragraph it supports')
    try:
        cited = {item['id'] for item in cited_in(document['passages'], body)}
    except ProviderError as error:
        cited = None
        _panel_error(errors, path, str(error))
    for number, point in enumerate(section['points'] if cited is not None else []):
        if not cited.intersection(point['passages']):
            _panel_error(errors, f'{path}.points[{number}]', 'cites none of its passages '
                         + json.dumps(point['passages']) + ' for the point '
                         + json.dumps(point['text'], ensure_ascii=False))
    words = len(_FIGURE_MARKER.sub('', uncited(body)).split())
    ceiling = int(section['words'] * BLOG_SECTION_WORD_CEILING)
    if words > ceiling:
        _panel_error(errors, path, f'has {words} words; the target is {section["words"]} and the ceiling is {ceiling}')
    later = {item['id'] for item in outline['sections'][index + 1:]}
    for term in outline['terms']:
        if term['section'] in later and blog_term_pattern(term['term']).search(body):
            _panel_error(errors, path, f'uses the term "{term["term"]}", which section {term["section"]} explains; '
                                       'say it in plain words here')
    _dash_errors(body, path, errors)
    if errors:
        raise SceneError(errors)
    return body


def blog_seams(outline, bodies):
    """Where a join request may edit: the seam between each pair of adjacent sections, and each term
    the article explains more than once. Makes no provider call.

    ``bodies`` are the accepted section bodies in outline order. A seam carries the first section's
    ``leaves_with`` and the sentence the next section opens with. A repeat carries the term, the
    sentence that explains it first in reading order, which stays, and each later explaining
    sentence, copied so the join can edit it exactly. A term explained once is never listed, so the
    join cannot cut an article's only explanation: on 2026-10-08 the outline's owner section had
    explained "Pareto dominance" in words the pattern does not match.
    """
    sections = outline['sections']
    seams = [{'previous': before['id'], 'leaves_with': before['leaves_with'],
              'next': after['id'], 'first_sentence': _sentences(body)[0]}
             for before, after, body in zip(sections, sections[1:], bodies[1:])]
    repeats = []
    for term in outline['terms']:
        explains = _explains_pattern(term['term'])
        found = [{'section': section['id'], 'sentence': sentence}
                 for section, body in zip(sections, bodies)
                 for sentence in _sentences(body) if explains.search(sentence)]
        if len(found) > 1:
            repeats.append({'term': term['term'], 'keep': found[0], 'cut': found[1:]})
    return {'seams': seams, 'repeats': repeats}


def validate_plan(plan, document):
    errors = []
    if not isinstance(plan, dict):
        _panel_error(errors, 'plan', 'must be an object')
        raise SceneError(errors)
    allowed=set(PLAN_SCHEMA['properties'])
    for name in sorted(set(plan)-allowed):
        _panel_error(errors, 'plan.'+name, 'is unsupported')
    for name in sorted(allowed-set(plan)):
        _panel_error(errors, 'plan.'+name, 'is required')
    if plan.get('paper_type') not in PAPER_TYPES:
        _panel_error(errors, 'plan.paper_type', 'must be supported')
    known={p['id'] for p in document['passages']}
    _blog_text(plan, 'visual_focus', 'plan', errors)
    for name in CLAIMS:
        claim=plan.get(name)
        if not isinstance(claim,dict):
            _panel_error(errors, 'plan.'+name, 'must be an evidence-linked object')
            continue
        if set(claim)!={'text','passages'}:
            _panel_error(errors, 'plan.'+name, 'must contain only text and passages')
        _blog_text(claim, 'text', 'plan.'+name, errors)
        _passage_refs(claim.get('passages'), known, 'plan.'+name+'.passages', errors, required=True)
    relationships=plan.get('relationships')
    if not isinstance(relationships,list) or not 1<=len(relationships)<=12:
        _panel_error(errors, 'plan.relationships', 'needs 1-12 items')
        relationships=[]
    for index,relation in enumerate(relationships):
        path=f'plan.relationships[{index}]'
        if not isinstance(relation,dict):
            _panel_error(errors, path, 'must be an object')
            continue
        if set(relation)!={'source','target','relationship','passages'}:
            _panel_error(errors, path, 'must contain only source, target, relationship, and passages')
        for key in ('source','target','relationship'):
            _blog_text(relation, key, path, errors)
        _passage_refs(relation.get('passages'), known, path+'.passages', errors, required=True)
    if errors:
        raise SceneError(errors)
    return copy.deepcopy(plan)
