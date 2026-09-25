"""Evidence-linked contracts shared by selection, authoring and review."""
import copy
import hashlib
import json
import re

from papers.errors import ProviderError
from papers.passages import Passages

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
FIGURE_SCHEMA = object_schema({**{name:TEXT for name in ('id','title','paper_connection','caption','html')},
                              'illustrative':{'type':'boolean'},'passages':REFS})
CANDIDATE_SCHEMA = object_schema({'plan':PLAN_SCHEMA,'text':TEXT,'figures':{'type':'array','items':FIGURE_SCHEMA}})

ID_ARRAY = {'type':'array','items':TEXT,'uniqueItems':True}


# --- Overview narrative ---------------------------------------------------------------------
# Every narrative text field is limited to the 1,200 characters the prompt states. The bounded
# UTF-8 candidate size below is a resource guard against a runaway response.
OVERVIEW_TEXT_MAX_CHARACTERS = 1200
OVERVIEW_CANDIDATE_MAX_BYTES = 256 * 1024


# --- Overview plan --------------------------------------------------------------------------
# One flat plan whose type is the content budget: at most four stacked panels, each with a short
# list of labels that are the exact display text, optional relations between labels, and one
# optional note. The validator rejects excess. Nothing in it asks for more content.
PANEL_CONTENT_KINDS = ('statement', 'value', 'equation', 'connection', 'qualification', 'label')
PANEL_IDENTIFIER = {'type':'string','minLength':1,'maxLength':32}
EXACT_TEXT_ITEM = {'type':'string','minLength':1,'maxLength':120}
PANEL_ID_RE = re.compile(r'[A-Za-z][A-Za-z0-9_-]{0,31}')


# --- Blog draft and drawing briefs ----------------------------------------------------------
# A Blog figure is a validated brief, never SVG or HTML. The article text is cited Markdown and
# the application owns the surrounding article, caption, placement, and markup. Figure word
# limits do not apply; the article word limit does.
BLOG_WORD_LIMITS = {'short':1000, 'medium':1400, 'large':2600}
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
BLOG_DRAFT_SCHEMA = object_schema({
    'plan':PLAN_SCHEMA,
    'text':TEXT,
    'figures':{'type':'array','items':BLOG_BRIEF_SCHEMA,'maxItems':3},
})
BLOG_REVISION_REQUEST_SCHEMA = object_schema({
    'action': {'type': 'string', 'enum': ['revise_narrative']},
    'reason': PLAN_TEXT,
    'passage_ids': ID_ARRAY,
})
BLOG_AUTHOR_RESPONSE_SCHEMA = {'anyOf': [BLOG_DRAFT_SCHEMA, BLOG_REVISION_REQUEST_SCHEMA]}
SELECTION_SCHEMA = object_schema({
    'paper_type':{'type':'string','enum':list(PAPER_TYPES)},
    'focus':PLAN_TEXT,
    'section_ids':ID_ARRAY,
    'passage_ids':ID_ARRAY,
    'figure_ids':ID_ARRAY,
})
REPAIR_DECISION_SCHEMA = object_schema({
    'action':{'type':'string','enum':['repair_figure','read_evidence','revise_narrative']},
    'addresses':{'type':'array','items':TEXT,'minItems':1,'uniqueItems':True,
                 'description':'Copy the exact current issue IDs from the issues list, such as issue-0282f3926e69.'},
    'change':{'type':'string','minLength':1,'maxLength':400},
    'reason':{'type':'string','minLength':1,'maxLength':400},
    'preserves':{'type':'array','items':TEXT,'uniqueItems':True,
                 'description':'Exact accepted-plan paths that remain true, such as plan.visual_focus or plan.relationships[0].'},
    'evidence':{'type':'array','items':TEXT,'uniqueItems':True,
                'description':'Exact retrieved passage IDs supporting the repair, such as p00014.'},
})
BLOG_REVISION_SCHEMA = object_schema({
    'base_digest': TEXT,
    'decision': REPAIR_DECISION_SCHEMA,
    'candidate': BLOG_DRAFT_SCHEMA,
})
REVIEW_ISSUE_SCHEMA = object_schema({
    'category':{'type':'string','enum':['unsupported_claim','incorrect_mechanism',
        'missing_explanation','misleading_connection','missing_transition',
        'unexplained_term','scope','readability']},
    'path':TEXT, 'message':PLAN_TEXT,
    'passages':{'type':'array','items':TEXT,'uniqueItems':True},
    'anchor':{'type':'string','maxLength':200,
              'description':'A label, or the two endpoint labels of the relation, copied verbatim '
                            'from the named drawing\'s visible content. Empty for an article finding.'},
})
REVIEW_RESOLUTION_SCHEMA = object_schema({
    'id':{'type':'string','description':'An exact open finding ID copied from <open_findings>.'},
    'quote':{'type':'string','description':'Text copied verbatim from the current article or from '
                                           "the repaired drawing's visible labels."},
    'explanation':PLAN_TEXT,
})
REVIEW_RESPONSE_SCHEMA = {'anyOf':[
    object_schema({'action':{'type':'string','enum':['verdict']},
                   'approved':{'type':'boolean'},
                   'candidate_digest':{'type':'string',
                       'description':'Copy CURRENT CANDIDATE DIGEST exactly; a mismatch is stale.'},
                   'issues':{'type':'array','items':REVIEW_ISSUE_SCHEMA},
                   'resolutions':{'type':'array','items':REVIEW_RESOLUTION_SCHEMA}}),
    object_schema({'action':{'type':'string','enum':['read_evidence']},
                   'section_ids':ID_ARRAY,'passage_ids':ID_ARRAY,'figure_ids':ID_ARRAY}),
]}


def validate_selection(selection, orientation):
    """Validate lookup handles before any retained file is opened."""
    errors=[]
    fields=set(SELECTION_SCHEMA['properties'])
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


class PlanValidationError(ValueError):
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


def _passage_refs(ids, known, path, errors, *, required):
    if not isinstance(ids, list) or any(not isinstance(value, str) for value in ids):
        _panel_error(errors, path, 'must be an array of passage IDs')
        return []
    unknown = sorted(set(ids) - known)
    if unknown:
        _panel_error(errors, path, 'has unknown passage IDs: ' + ', '.join(unknown[:12]))
    if required and not [value for value in ids if value in known]:
        _panel_error(errors, path, 'needs at least one retained passage ID')
    return [value for value in ids if value in known]


def _overview_error(errors, path, message, **details):
    errors.append({'code': 'plan_validation', 'path': path, 'message': path + ' ' + message, **details})


def _candidate_size_bytes(value):
    try:
        return len(json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))
    except (TypeError, ValueError):
        return None


def _overview_passage_ids(document):
    return {item.get('id') for item in document.get('passages', []) if isinstance(item, dict)}


def _overview_claim(claim, path, known, errors):
    if not isinstance(claim, dict):
        _overview_error(errors, path, 'must be an evidence-linked object')
        return None
    unsupported = sorted(set(claim) - {'text', 'passages'})
    for name in unsupported:
        _overview_error(errors, path + '.' + name, 'is unsupported')
    for name in ('text', 'passages'):
        if name not in claim:
            _overview_error(errors, path, 'is missing ' + name)
    text = claim.get('text')
    if not isinstance(text, str) or not text.strip():
        _overview_error(errors, path + '.text', 'needs nonempty text')
        text = None
    elif len(text) > OVERVIEW_TEXT_MAX_CHARACTERS:
        _overview_error(errors, path + '.text',
                        f'has {len(text)} characters; the limit is {OVERVIEW_TEXT_MAX_CHARACTERS}')
        text = None
    refs = claim.get('passages')
    if not isinstance(refs, list) or not refs or any(not isinstance(item, str) or not item for item in refs):
        _overview_error(errors, path + '.passages', 'needs a nonempty array of passage IDs')
        refs = []
    unknown = sorted(set(refs) - known)
    if unknown:
        _overview_error(errors, path + '.passages', 'has unknown passage IDs: ' + ', '.join(unknown[:12]))
    refs = [item for item in refs if item in known]
    if text is None or not refs:
        return None
    return {'text': text, 'passages': list(dict.fromkeys(refs))}


def _overview_relationship(relation, index, known, errors):
    path = 'plan.relationships[' + str(index) + ']'
    if not isinstance(relation, dict):
        _overview_error(errors, path, 'must be an object')
        return None
    unsupported = sorted(set(relation) - {'source', 'target', 'relationship', 'passages'})
    for name in unsupported:
        _overview_error(errors, path + '.' + name, 'is unsupported')
    for name in ('source', 'target', 'relationship', 'passages'):
        if name not in relation:
            _overview_error(errors, path, 'is missing ' + name)
    for name in ('source', 'target', 'relationship'):
        value = relation.get(name)
        if not isinstance(value, str) or not value.strip():
            _overview_error(errors, path + '.' + name, 'needs nonempty text')
        elif len(value) > OVERVIEW_TEXT_MAX_CHARACTERS:
            _overview_error(errors, path + '.' + name,
                            f'has {len(value)} characters; the limit is {OVERVIEW_TEXT_MAX_CHARACTERS}')
    refs = relation.get('passages')
    if not isinstance(refs, list) or not refs or any(not isinstance(item, str) or not item for item in refs):
        _overview_error(errors, path + '.passages', 'needs a nonempty array of passage IDs')
        refs = []
    unknown = sorted(set(refs) - known)
    if unknown:
        _overview_error(errors, path + '.passages', 'has unknown passage IDs: ' + ', '.join(unknown[:12]))
    refs = [item for item in refs if item in known]
    if refs and all(isinstance(relation.get(name), str) and relation.get(name).strip()
                    for name in ('source', 'target', 'relationship')):
        return {'source': relation['source'], 'target': relation['target'],
                'relationship': relation['relationship'], 'passages': list(dict.fromkeys(refs))}
    return None


def validate_overview_narrative(value, document):
    """Validate one Overview narrative independently of Blog's shared contract.

    Every text field is nonempty and within ``OVERVIEW_TEXT_MAX_CHARACTERS``; the whole JSON
    candidate is bounded by ``OVERVIEW_CANDIDATE_MAX_BYTES``. A list of string steps for ``visual_focus`` is normalised to
    newline-separated text without changing words or order. Relationships are optional, and every
    supplied relationship and passage reference is validated. Blog keeps ``validate_plan``.
    """
    issues = []
    if not isinstance(value, dict):
        raise PlanValidationError([{'code': 'plan_validation', 'path': 'plan',
                                    'message': 'plan must be an object'}])
    size = _candidate_size_bytes(value)
    if size is not None and size > OVERVIEW_CANDIDATE_MAX_BYTES:
        raise PlanValidationError([{
            'code': 'resource_limit', 'path': 'candidate',
            'message': ('Narrative candidate is ' + str(size) + ' UTF-8 bytes; the resource limit is '
                        + str(OVERVIEW_CANDIDATE_MAX_BYTES) + ' bytes.'),
            'constraint': 'maximum_candidate_bytes', 'actual': size,
            'limit': OVERVIEW_CANDIDATE_MAX_BYTES, 'resource_limit': True}])
    allowed = set(PLAN_SCHEMA['properties']) | {'request_evidence'}
    for name in sorted(set(value) - allowed):
        _overview_error(issues, 'plan.' + name, 'is unsupported')
    for name in sorted(set(PLAN_SCHEMA['properties']) - {'relationships'} - set(value)):
        _overview_error(issues, 'plan.' + name, 'is required')
    paper_type = value.get('paper_type')
    if paper_type not in PAPER_TYPES:
        _overview_error(issues, 'plan.paper_type', 'must be one of ' + ', '.join(PAPER_TYPES))
    # Normalise visual_focus: one string, or a list of string steps joined by newlines.
    visual_focus = value.get('visual_focus')
    if isinstance(visual_focus, list):
        invalid = [index for index, item in enumerate(visual_focus) if not isinstance(item, str)]
        if invalid:
            _overview_error(issues, 'plan.visual_focus',
                            'must be one string or an array of strings; entries '
                            + ', '.join(str(index) for index in invalid[:8]) + ' are not strings')
            visual_focus = None
        else:
            visual_focus = '\n'.join(step.strip() for step in visual_focus)
    visual_focus_ok = isinstance(visual_focus, str) and bool(visual_focus.strip())
    if not visual_focus_ok:
        _overview_error(issues, 'plan.visual_focus', 'needs nonempty text')
    elif len(visual_focus) > OVERVIEW_TEXT_MAX_CHARACTERS:
        _overview_error(issues, 'plan.visual_focus',
                        f'has {len(visual_focus)} characters; the limit is {OVERVIEW_TEXT_MAX_CHARACTERS}')
    known = _overview_passage_ids(document)
    claims = {}
    for name in CLAIMS:
        claims[name] = _overview_claim(value.get(name), 'plan.' + name, known, issues)
    request = value.get('request_evidence')
    if request is not None:
        if not isinstance(request, dict):
            _overview_error(issues, 'plan.request_evidence', 'must be an object')
        else:
            unsupported = sorted(set(request) - {'section_ids', 'passage_ids', 'figure_ids'})
            for name in unsupported:
                _overview_error(issues, 'plan.request_evidence.' + name, 'is unsupported')
            for name in ('section_ids', 'passage_ids', 'figure_ids'):
                ids = request.get(name)
                if not isinstance(ids, list) or any(not isinstance(item, str) or not item for item in ids):
                    _overview_error(issues, 'plan.request_evidence.' + name, 'must be an array of IDs')
    relationships = value.get('relationships', [])
    if relationships is None:
        relationships = []
    if not isinstance(relationships, list):
        _overview_error(issues, 'plan.relationships', 'must be an array')
        relationships = []
    elif len(relationships) > 12:
        _overview_error(issues, 'plan.relationships', 'needs no more than 12 items')
    normalized_relationships = []
    for index, relation in enumerate(relationships):
        normalized = _overview_relationship(relation, index, known, issues)
        if normalized is not None:
            normalized_relationships.append(normalized)
    if issues:
        raise PlanValidationError(issues[:20])
    result = {'paper_type': paper_type,
              'visual_focus': visual_focus,
              **{name: claims[name] for name in CLAIMS},
              'relationships': normalized_relationships}
    if request is not None:
        result['request_evidence'] = copy.deepcopy(request)
    return copy.deepcopy(result)


def recover_overview_narrative(candidates, document):
    """Recover a usable Overview from one candidate with four valid, source-linked claims.

    This is deliberately narrow: the candidate must contain all four evidence-linked claims.
    A valid ``visual_focus`` — one string or an ordered list of string steps — is preserved;
    only a missing or invalid focus is replaced by the contribution sentence. Invalid optional
    relationships are removed and recorded under ``_recovery``; a relationship with an unknown
    passage reference is discarded, never silently repaired. No field is ever borrowed from
    another candidate, and the whole candidate still respects ``OVERVIEW_CANDIDATE_MAX_BYTES``.
    Returns ``None`` when no candidate can be recovered.
    """
    known = _overview_passage_ids(document)
    for index, candidate in enumerate(candidates or []):
        if not isinstance(candidate, dict):
            continue
        size = _candidate_size_bytes(candidate)
        if size is None or size > OVERVIEW_CANDIDATE_MAX_BYTES:
            continue
        errors = []
        claims = {name: _overview_claim(candidate.get(name), 'plan.' + name, known, errors)
                  for name in CLAIMS}
        if errors:
            continue
        valid_relationships, discarded = [], []
        relationships = candidate.get('relationships')
        if relationships is None:
            relationships = []
        elif not isinstance(relationships, list):
            discarded.append(copy.deepcopy(relationships))
            relationships = []
        for position, relation in enumerate(relationships):
            errors = []
            normalized = _overview_relationship(relation, position, known, errors)
            if errors:
                discarded.append(copy.deepcopy(relation))
            else:
                valid_relationships.append(normalized)
        if len(valid_relationships) > 12:
            continue
        paper_type = candidate.get('paper_type')
        defaulted = paper_type not in PAPER_TYPES
        focus = candidate.get('visual_focus')
        if isinstance(focus, list) and all(isinstance(step, str) for step in focus):
            focus = '\n'.join(step.strip() for step in focus)
        focus_source = 'visual_focus'
        if not isinstance(focus, str) or not focus.strip():
            focus = claims['contribution']['text']
            focus_source = 'contribution'
        recovered = {'paper_type': paper_type if not defaulted else 'other',
                     'visual_focus': focus}
        recovered.update(claims)
        recovered['relationships'] = valid_relationships
        recovered['_recovery'] = {
            'reduced': True,
            'source_candidate': index,
            'discarded_relationships': discarded,
            'paper_type_defaulted': defaulted,
            'focus_source': focus_source,
        }
        return copy.deepcopy(recovered)
    return None


# --- Overview digest ---------------------------------------------------------------------------
# The first pass over a paper: what a reader must know to understand its core in one image. The
# required fields are how "the core is present" becomes checkable. Components nest through
# ``contains`` and flow through ``feeds``; an operation belongs to the component that computes it.
DIGEST_LIMITS = {'claim': 400, 'example': 320, 'hyperparameter': 48, 'name': 48, 'role': 160,
                 'computes': 100, 'values': 80, 'repeat': 16}
DIGEST_MIN_COMPONENTS, DIGEST_MAX_COMPONENTS = 4, 24
DIGEST_COMPONENT_FIELDS = {'id', 'name', 'role', 'computes', 'values', 'contains', 'feeds', 'repeat', 'passages'}
DIGEST_EXAMPLE_TYPES = ('architecture', 'method')


def validate_digest(digest, evidence):
    """Validate one Overview digest against the retained evidence. Returns a normalized copy."""
    errors = []
    known = {item['id'] for item in evidence.get('passages', []) if isinstance(item, dict)}
    if not isinstance(digest, dict):
        raise PlanValidationError([{'code': 'digest_validation', 'path': 'digest', 'message': 'digest must be an object.'}])
    allowed = {'paper_type', 'contribution', 'result', 'qualification', 'example', 'hyperparameters', 'components'}
    for name in sorted(set(digest) - allowed):
        _panel_error(errors, 'digest.' + name, 'is unsupported')
    for name in ('paper_type', 'contribution', 'result', 'qualification', 'components'):
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
        _text(claim, 'text', 'digest.' + name, errors, maximum=DIGEST_LIMITS['claim'])
        _passage_refs(claim.get('passages'), known, 'digest.' + name + '.passages', errors, required=True)
    if paper_type in DIGEST_EXAMPLE_TYPES or 'example' in digest:
        _text(digest, 'example', 'digest', errors, maximum=DIGEST_LIMITS['example'])
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
                     f'needs {DIGEST_MIN_COMPONENTS} through {DIGEST_MAX_COMPONENTS} components',
                     constraint='maximum_components',
                     actual=len(components) if isinstance(components, list) else None,
                     limit=DIGEST_MAX_COMPONENTS)
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
        _text(component, 'name', path, errors, maximum=DIGEST_LIMITS['name'])
        _text(component, 'role', path, errors, maximum=DIGEST_LIMITS['role'])
        for name in ('computes', 'values', 'repeat'):
            if name in component and component[name] is not None:
                _text(component, name, path, errors, maximum=DIGEST_LIMITS[name])
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
        raise PlanValidationError(errors[:20])
    normalized = {'paper_type': paper_type,
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


def scene_coverage_issues(digest, scene_strings, group_headings):
    """The containment rule, as validator issues for the correction request.

    A component with two or more parts of its own must appear as a group heading, or as a panel
    heading when the panel is about it, so the picture keeps the hierarchy the digest established.
    A part shared by several components is drawn once, so those components may be cards. The
    string check is ``Figure.missing`` with ``digest_requirements``; ``scene_strings`` is unused.
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
                                      'is its name, holding the nodes of its parts, or the panel '
                                      'about it must carry its name in the panel heading'})
    return issues


def digest_passages(digest):
    refs = []
    for name in ('contribution', 'result', 'qualification'):
        refs.extend(digest[name]['passages'])
    for component in digest['components']:
        refs.extend(component['passages'])
    return list(dict.fromkeys(refs))


def blog_panel_required(brief):
    """Every string a Blog figure's Scene panel must show verbatim."""
    return list(brief.get('exact_text') or []) + list(brief.get('illustrative_values') or [])


def _blog_error(errors, path, message, **details):
    errors.append({'code': 'plan_validation', 'path': path, 'message': path + ' ' + message, **details})


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
                _blog_error(errors, text_path,
                            'must not contain ' + token + ' markup; the application owns the '
                            'surrounding article, caption, placement, and markup.')
                break


def _blog_text(item, key, path, errors, *, maximum=1200):
    value = item.get(key) if isinstance(item, dict) else None
    if isinstance(value, (list, dict)):
        # deepseek-flash wrote exit_state as a one-item list like its neighbour entry_context.
        _blog_error(errors, path + '.' + key, 'must be one string of 1-' + str(maximum) + ' characters, not '
                    + ('a list' if isinstance(value, list) else 'an object'))
        return False
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        _blog_error(errors, path + '.' + key, 'needs 1-' + str(maximum) + ' characters')
        return False
    return True


def _blog_string_items(values, path, errors, *, minimum=0, maximum=None, length=1200, unique=False):
    if not isinstance(values, list):
        _blog_error(errors, path, 'must be an array of strings')
        return []
    if len(values) < minimum or (maximum is not None and len(values) > maximum):
        bounds = ('at least ' + str(minimum) if maximum is None
                  else str(minimum) + ' through ' + str(maximum))
        _blog_error(errors, path, 'needs ' + bounds + ' items')
    normalized = []
    for index, value in enumerate(values):
        item_path = path + '[' + str(index) + ']'
        if not isinstance(value, str) or not value.strip() or len(value) > length:
            _blog_error(errors, item_path, 'needs 1-' + str(length) + ' characters')
            continue
        normalized.append(value)
    if unique and len(set(normalized)) != len(normalized):
        _blog_error(errors, path, 'must contain unique strings')
    return normalized


def _blog_passage_refs(ids, known, path, errors, *, required):
    if not isinstance(ids, list) or any(not isinstance(value, str) for value in ids):
        _blog_error(errors, path, 'must be an array of passage IDs')
        return []
    if len(set(ids)) != len(ids):
        _blog_error(errors, path, 'must contain unique passage IDs')
    unknown = sorted(set(ids) - known)
    if unknown:
        _blog_error(errors, path, 'has unknown passage IDs: ' + ', '.join(unknown[:12]))
    retained = list(dict.fromkeys(value for value in ids if value in known))
    if required and not retained:
        _blog_error(errors, path, 'needs at least one retained passage ID')
    return retained


def _blog_content_items(values, known, path, errors):
    if not isinstance(values, list) or not 1 <= len(values) <= 8:
        _blog_error(errors, path, 'needs 1 through 8 ordered items')
        values = values if isinstance(values, list) else []
    normalized = []
    for index, item in enumerate(values):
        item_path = path + '[' + str(index) + ']'
        if not isinstance(item, dict):
            _blog_error(errors, item_path, 'must be an object')
            continue
        for name in sorted(set(item) - {'text', 'kind', 'passages'}):
            _blog_error(errors, item_path + '.' + name, 'is unsupported')
        for name in ('text', 'kind'):
            if name not in item:
                _blog_error(errors, item_path, 'is missing ' + name)
        _blog_text(item, 'text', item_path, errors)
        if item.get('kind') not in PANEL_CONTENT_KINDS:
            _blog_error(errors, item_path + '.kind',
                        'must be one of ' + ', '.join(PANEL_CONTENT_KINDS))
        entry = {'text': item.get('text'), 'kind': item.get('kind')}
        if 'passages' in item:
            entry['passages'] = _blog_passage_refs(item.get('passages'), known,
                                                   item_path + '.passages', errors, required=False)
        normalized.append(entry)
    return normalized


def _validate_blog_brief(brief, document, errors, prefix, figure_id=None):
    """Validate one Blog drawing brief, appending issues under ``prefix``.

    Returns the normalized brief when it introduces no new issues, otherwise ``None``.
    """
    path = prefix or 'brief'
    start = len(errors)
    if not isinstance(brief, dict):
        _blog_error(errors, path, 'must be an object')
        return None
    allowed = set(BLOG_BRIEF_SCHEMA['properties'])
    for name in sorted(set(brief) - allowed):
        _blog_error(errors, path + '.' + name, 'is unsupported')
    for name in sorted(allowed - set(brief)):
        _blog_error(errors, path, 'is missing ' + name)
    _blog_reject_markup(brief, path, errors)
    known = {item.get('id') for item in document.get('passages', []) if isinstance(item, dict)}
    identifier = brief.get('id')
    if not isinstance(identifier, str) or not PANEL_ID_RE.fullmatch(identifier):
        _blog_error(errors, path + '.id', 'must be a safe figure id: a letter, then letters, '
                                          'digits, dashes, or underscores')
        identifier = None
    else:
        if not re.fullmatch(r'fig[1-3]', identifier):
            _blog_error(errors, path + '.id', 'must be fig1, fig2, or fig3')
        if figure_id is not None and identifier != figure_id:
            _blog_error(errors, path + '.id',
                        'must stay ' + figure_id + ' when the brief is corrected')
    _blog_text(brief, 'title', path, errors, maximum=80)
    _blog_text(brief, 'paper_connection', path, errors)
    _blog_text(brief, 'caption', path, errors)
    if type(brief.get('illustrative')) is not bool:
        _blog_error(errors, path + '.illustrative', 'must be true or false')
    passages = _blog_passage_refs(brief.get('passages'), known, path + '.passages',
                                  errors, required=True)
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


def validate_blog_brief(brief, document, *, figure_id=None):
    """Validate one Blog drawing brief and return its normalized copy.

    ``figure_id`` is the stable identifier the caller requires; when supplied, the brief's own
    ``id`` must match it, so a correction cannot silently rename a figure. Issues carry the exact
    path, such as ``brief.purpose`` or ``figures[0].exact_text``.
    """
    errors = []
    normalized = _validate_blog_brief(brief, document, errors, '', figure_id=figure_id)
    if errors or normalized is None:
        raise PlanValidationError(errors[:20])
    return copy.deepcopy(normalized)


def _blog_validate_text(text, document, length, errors):
    try:
        Passages(document['passages']).cited_in(text)
    except ProviderError as exc:
        _blog_error(errors, 'text', str(exc))
    if length in BLOG_WORD_LIMITS:
        words = len(Passages.uncited(text).split())
        maximum = BLOG_WORD_LIMITS[length]
        if words > maximum:
            # A draft cut by the exact excess came back 7 and 24 words over in live runs: ask for
            # a margin under the limit.
            _blog_error(errors, 'text',
                        'has ' + str(words) + ' words; the limit is ' + str(maximum)
                        + ', so shorten it to about ' + str(maximum - 100) + ' words (' + str(words - maximum + 100)
                        + ' fewer) while preserving citations and figure markers.',
                        constraint='maximum_article_words', actual=words, limit=maximum)


def _blog_check_markers(text, figures, errors):
    markers = re.findall(r'\{\{figure:([^}]+)\}\}', text)
    expected = [brief['id'] for brief in figures]
    for marker in sorted(set(markers) - set(expected)):
        _blog_error(errors, 'text', 'names unknown figure marker {{figure:' + marker + '}}')
    for marker in sorted(set(markers)):
        if markers.count(marker) > 1:
            _blog_error(errors, 'text', 'repeats figure marker {{figure:' + marker + '}}')
    for identifier in expected:
        if markers.count(identifier) != 1:
            _blog_error(errors, 'text',
                        'must contain the marker {{figure:' + identifier + '}} exactly once')


def validate_blog_draft(draft, document, length, *, word_limit=True):
    """Validate one Blog draft and return its normalized copy with derived metadata.

    The draft retains ``plan`` and cited ``text``; its ``figures`` are validated drawing briefs,
    not SVG or HTML. Evidence is checked against ``document['passages']``, markers must match the
    figure IDs exactly once each, and the article word limit follows ``length`` unless
    ``word_limit`` is false, for a caller that shortens the text itself. Figure word limits do not
    apply.
    """
    errors = []
    if not isinstance(draft, dict):
        _blog_error(errors, 'draft', 'must be an object')
        raise PlanValidationError(errors)
    allowed = set(BLOG_DRAFT_SCHEMA['properties'])
    for name in sorted(set(draft) - allowed):
        _blog_error(errors, 'draft.' + name, 'is unsupported')
    for name in sorted(allowed - set(draft)):
        _blog_error(errors, 'draft', 'is missing ' + name)
    if length not in BLOG_WORD_LIMITS:
        _blog_error(errors, 'length', 'must be one of ' + ', '.join(BLOG_WORD_LIMITS))
    plan = None
    try:
        plan = validate_plan(draft.get('plan'), document)
    except PlanValidationError as exc:
        errors.extend(exc.issues)
    _blog_reject_markup(draft.get('plan'), 'plan', errors)
    text = draft.get('text')
    if not isinstance(text, str) or not text.strip():
        _blog_error(errors, 'text', 'needs cited Markdown prose')
    else:
        _blog_reject_markup(text, 'text', errors)
        _blog_validate_text(text, document, length if word_limit else None, errors)
    figures = draft.get('figures')
    normalized_figures = []
    if not isinstance(figures, list):
        _blog_error(errors, 'figures', 'must be an array of figure briefs')
        figures = []
    elif len(figures) > 3:
        _blog_error(errors, 'figures', 'needs no more than 3 items')
    previous = 0
    for index, brief in enumerate(figures):
        prefix = 'figures[' + str(index) + ']'
        figure_errors = []
        normalized = _validate_blog_brief(brief, document, figure_errors, prefix)
        if normalized is not None:
            number = int(normalized['id'][3:])
            if number <= previous:
                _blog_error(figure_errors, prefix + '.id',
                            'must be a strictly ascending unique figure id')
            else:
                previous = number
                normalized_figures.append(normalized)
        errors.extend(figure_errors)
    if isinstance(text, str) and text.strip():
        _blog_check_markers(text, normalized_figures, errors)
    if errors:
        raise PlanValidationError(errors[:20])
    return copy.deepcopy({
        'plan': plan,
        'text': text,
        'figures': normalized_figures,
        'paper_type': plan['paper_type'],
        'question': plan['question']['text'],
        'contribution': plan['contribution']['text'],
        'finding': plan['finding']['text'],
        'limitation': plan['limitation']['text'],
        'passages': list(dict.fromkeys(
            passage
            for item in [*(plan[name] for name in CLAIMS), *plan['relationships']]
            for passage in item['passages'])),
    })


def candidate_digest(value):
    """A stable digest for a JSON-serializable candidate value."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False).encode()).hexdigest()


def _flatten_text(value):
    return ' '.join(str(value or '').split())


def validate_plan(plan, document):
    errors = []

    def error(path, message, violation=None):
        issue = {'code': 'plan_validation', 'path': path, 'message': path + ' ' + message}
        if violation is not None:
            issue.update(actual=violation, limit=0)
        errors.append(issue)

    if not isinstance(plan, dict):
        error('plan', 'must be an object')
        raise PlanValidationError(errors)
    allowed=set(PLAN_SCHEMA['properties'])
    for name in sorted(set(plan)-allowed):
        error('plan.'+name, 'is unsupported')
    for name in sorted(allowed-set(plan)):
        error('plan.'+name, 'is required')
    if plan.get('paper_type') not in PAPER_TYPES:
        error('plan.paper_type', 'must be supported')
    known={p['id'] for p in document['passages']}
    def text(item,key,path):
        value=item.get(key)
        if not isinstance(value,str) or not value.strip() or len(value)>1200:
            over=len(value)-1200 if isinstance(value,str) and len(value)>1200 else None
            message='needs 1-1200 characters'
            if isinstance(value,(list,dict)):
                # A correction that does not name the type came back with the same object twice.
                kind='a list' if isinstance(value,list) else 'an object'
                message='must be one string of 1-1200 characters, not '+kind
            if over:
                # A value cut by the exact excess came back over the limit again: ask for a margin.
                message=(f'has {len(value)} characters; the limit is 1200, so shorten it to about 1100 '
                         f'characters while preserving required detail')
            violation = max(1 - len(value.strip()), over or 0, 0) if isinstance(value, str) else None
            error(path+'.'+key, message, violation)
    def refs(item,path):
        ids=item.get('passages')
        if not isinstance(ids,list) or not ids or any(not isinstance(i,str) or i not in known for i in ids):
            error(path+'.passages', 'needs exact retrieved passage IDs')
    text(plan,'visual_focus','plan')
    for name in CLAIMS:
        claim=plan.get(name)
        if not isinstance(claim,dict):
            error('plan.'+name, 'must be an evidence-linked object')
            continue
        if set(claim)!={'text','passages'}:
            error('plan.'+name, 'must contain only text and passages')
        text(claim,'text','plan.'+name)
        refs(claim,'plan.'+name)
    relationships=plan.get('relationships')
    if not isinstance(relationships,list) or not 1<=len(relationships)<=12:
        violation = max(1 - len(relationships), len(relationships) - 12, 0) if isinstance(relationships, list) else None
        error('plan.relationships', 'needs 1-12 items', violation)
        relationships=[]
    for index,relation in enumerate(relationships):
        path=f'plan.relationships[{index}]'
        if not isinstance(relation,dict):
            error(path, 'must be an object')
            continue
        if set(relation)!={'source','target','relationship','passages'}:
            error(path, 'must contain only source, target, relationship, and passages')
        for key in ('source','target','relationship'):
            text(relation,key,path)
        refs(relation,path)
    if errors:
        raise PlanValidationError(errors)
    return copy.deepcopy(plan)


def expand_candidate(draft, document):
    if not isinstance(draft,dict):
        raise ValueError('Submit an object with plan, text and figures.')
    value=copy.deepcopy(draft)
    plan=validate_plan(value.get('plan'),document)
    value.update(paper_type=plan['paper_type'],**{name:plan[name]['text'] for name in CLAIMS})
    value['passages']=list(dict.fromkeys(i for item in [*(plan[n] for n in CLAIMS),*plan['relationships']] for i in item['passages']))
    figures=value.get('figures')
    if not isinstance(figures,list):
        raise ValueError('Figures must be an array.')
    return value
