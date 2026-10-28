"""Evidence-linked contracts shared by selection, authoring and review."""
import copy
import json
import re

from papers.errors import ProviderError
from papers.passages import cited_in, uncited


class ValidationError(ValueError):
    """A structural validation failure with an exact location for the next correction."""
    def __init__(self, issues):
        self.issues = issues
        super().__init__('; '.join(issue['message'] for issue in issues[:20]) + '.')


# The validation helpers every contract below shares.
PANEL_ID_RE = re.compile(r'[A-Za-z][A-Za-z0-9_-]{0,31}')


def _flatten_text(value):
    return ' '.join(str(value or '').split())


def _panel_error(errors, path, message):
    errors.append({'code': 'panel_plan_validation', 'path': path, 'message': path + ' ' + message})


def _check_text(item, key, path, errors, *, maximum=1200):
    value = item.get(key) if isinstance(item, dict) else None
    if not isinstance(value, str) or not value.strip():
        _panel_error(errors, path + '.' + key, f'needs 1-{maximum} characters of text')
    elif len(value) > maximum:
        _panel_error(errors, path + '.' + key,
                     f'has {len(value)} characters; the limit is {maximum}, so shorten it by at least '
                     f'{len(value) - maximum} characters')


def _identifier(value, path, errors, *, pattern, label):
    if not isinstance(value, str) or not pattern.fullmatch(value):
        _panel_error(errors, path, f'must be a safe {label}: a letter, then letters, digits, dashes or underscores')
        return None
    return value


def _subtree(spec):
    yield spec
    for child in spec.get('children') or []:
        yield from _subtree(child)


# One notation rule for every string a figure shows. The NTK Overview of 2026-09-25 wrote
# "Theta_inf^(L)" and "lambda_1" under the older rule, which allowed ASCII subscripts.
NOTATION = ('plain text that the figure typesets: an underscore starts a subscript and a caret a superscript, '
            'for one word (d_k, d_model, W^Q, K^T, x_1) or a braced group (x_{t+1}, 10000^{2i/d_model}); '
            'Unicode for symbols and Greek letters (Σ √ · × → ≤ ∞ α λ θ); function names as words (softmax, log, max); '
            'never LaTeX commands, dollar signs, or a Greek letter spelled out such as theta or lambda; '
            'wrap each equation or formula in backticks, such as `Attention(Q,K,V) = softmax(QK^T/√d_k)V`, '
            'which the figure draws in a math font in a box on one line, so keep it short enough for one line of '
            'its card')

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
# A result is a (dataset, metric, score, method) row read against the other methods' rows: the
# 2026-10-28 Attention narrative kept "more than 2.0 BLEU" and dropped Table 2's comparators.
MEASURE_FIELDS = ('dataset', 'metric', 'better', 'scores', 'passages')
SCORE_FIELDS = ('method', 'value', 'ours')
MAX_MEASURES, MAX_SCORES = 3, 8
MEASURE_SCHEMA = object_schema({
    'dataset':PLAN_TEXT, 'metric':PLAN_TEXT, 'better':{'type':'string','enum':['higher','lower']},
    'scores':{'type':'array','minItems':1,'maxItems':MAX_SCORES,'items':object_schema({
        'method':PLAN_TEXT, 'value':{'type':'number'},
        'ours':{'type':'boolean','description':"true only for the paper's best variant"}})},
    'passages':REFS})
PLAN_SCHEMA = object_schema({
    'paper_type':{'type':'string','enum':list(PAPER_TYPES)},
    **{name:CLAIM_SCHEMA for name in CLAIMS},
    'measures':{'type':'array','maxItems':MAX_MEASURES,'items':MEASURE_SCHEMA},
    'visual_focus':PLAN_TEXT,
    'relationships':{'type':'array','minItems':1,'maxItems':12,'items':object_schema({'source':PLAN_TEXT,'target':PLAN_TEXT,'relationship':PLAN_TEXT,'passages':REFS})},
})

ID_ARRAY = {'type':'array','items':TEXT,'uniqueItems':True}


PANEL_CONTENT_KINDS = ('statement', 'value', 'equation', 'connection', 'qualification', 'label')
PANEL_IDENTIFIER = {'type':'string','minLength':1,'maxLength':32}


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
        raise ValidationError([{'code': 'digest_validation', 'path': 'digest', 'message': 'digest must be an object.'}])
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
        raise ValidationError(errors[:20])
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




_POINT = re.compile(r'(?<![\w.])\d+(?:\.\d+)?\s*[%kKMBx×]?\s*:\s*[-−]?\d')


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


def digest_passages(digest):
    refs = []
    # A digest saved before 2026-10-08 has no why.
    refs.extend((digest.get('why') or {}).get('passages', []))
    for name in ('contribution', 'result', 'qualification'):
        refs.extend(digest[name]['passages'])
    for component in digest['components']:
        refs.extend(component['passages'])
    return list(dict.fromkeys(refs))


def blog_figure_required(brief):
    """Every value a Blog figure must show verbatim: the values its section's prose also gives."""
    return list(brief.get('illustrative_values') or [])


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


def _validate_blog_brief(brief, document, errors, prefix):
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
        raise ValidationError(errors)
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
        raise ValidationError(errors[:20])
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


def sentences(text):
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
        raise ValidationError(errors)
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
              'next': after['id'], 'first_sentence': sentences(body)[0]}
             for before, after, body in zip(sections, sections[1:], bodies[1:])]
    repeats = []
    for term in outline['terms']:
        explains = _explains_pattern(term['term'])
        found = [{'section': section['id'], 'sentence': sentence}
                 for section, body in zip(sections, bodies)
                 for sentence in sentences(body) if explains.search(sentence)]
        if len(found) > 1:
            repeats.append({'term': term['term'], 'keep': found[0], 'cut': found[1:]})
    return {'seams': seams, 'repeats': repeats}


def validate_plan(plan, document):
    errors = []
    if not isinstance(plan, dict):
        _panel_error(errors, 'plan', 'must be an object')
        raise ValidationError(errors)
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
    _measure_issues(plan, known, errors)
    if errors:
        raise ValidationError(errors)
    return copy.deepcopy(plan)


def _measure_issues(plan, known, errors):
    """The shape of plan.measures. A proposing paper needs one measure with its own score marked ours.

    The check is strict on shape and lenient on comparators: a paper with no comparison table gives
    one score, so a missing baseline never fails the narrative stage.
    """
    measures = plan.get('measures')
    proposes = plan.get('paper_type') in ('architecture', 'method')
    if not isinstance(measures, list) or len(measures) > MAX_MEASURES:
        _panel_error(errors, 'plan.measures', f'needs 0-{MAX_MEASURES} measures')
        return
    if proposes and not measures:
        _panel_error(errors, 'plan.measures', "needs the main result: the paper's score marked ours and "
                     'the score of each method the paper compares it with')
    for index, measure in enumerate(measures):
        path = f'plan.measures[{index}]'
        if not isinstance(measure, dict) or set(measure) != set(MEASURE_FIELDS):
            _panel_error(errors, path, 'must be an object with only ' + ', '.join(MEASURE_FIELDS))
            continue
        _blog_text(measure, 'dataset', path, errors)
        _blog_text(measure, 'metric', path, errors)
        if measure['better'] not in ('higher', 'lower'):
            _panel_error(errors, path + '.better', 'must be "higher" or "lower"')
        _passage_refs(measure['passages'], known, path + '.passages', errors, required=True)
        scores = measure['scores']
        if not isinstance(scores, list) or not 1 <= len(scores) <= MAX_SCORES:
            _panel_error(errors, path + '.scores', f'needs 1-{MAX_SCORES} scores; keep the strongest comparators')
            continue
        ours = 0
        for number, score in enumerate(scores):
            spot = f'{path}.scores[{number}]'
            if not isinstance(score, dict) or set(score) != set(SCORE_FIELDS):
                _panel_error(errors, spot, 'must be an object with only ' + ', '.join(SCORE_FIELDS))
                continue
            _blog_text(score, 'method', spot, errors)
            if isinstance(score['value'], bool) or not isinstance(score['value'], (int, float)):
                _panel_error(errors, spot + '.value', 'must be a number such as 28.4, with the unit in metric')
            if not isinstance(score['ours'], bool):
                _panel_error(errors, spot + '.ours', 'must be true or false')
            ours += score['ours'] is True
        if ours > 1:
            _panel_error(errors, path + '.scores', f'has {ours} scores marked ours; mark only the paper\'s best '
                         'variant')
        elif proposes and not ours:
            _panel_error(errors, path + '.scores', "needs the paper's own score marked ours")
