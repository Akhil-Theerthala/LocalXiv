"""Evidence-linked contracts shared by selection, authoring and review."""
import copy
import hashlib
import json
import re

CLAIMS = ('question', 'contribution', 'finding', 'limitation')
PAPER_TYPES = ('architecture', 'method', 'survey', 'evaluation', 'theory', 'other')
TEXT = {'type':'string'}
PLAN_TEXT = {'type':'string','minLength':1,'maxLength':1200}
REFS = {'type':'array','items':TEXT,'minItems':1}


def object_schema(fields, required=None):
    return {'type':'object','properties':fields,
            'required':list(fields) if required is None else list(required),
            'additionalProperties':False}


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
PANEL_CONSTRUCTION_FAMILIES = ('flow', 'mapping', 'comparison', 'calculation', 'chart')
PANEL_CONTENT_KINDS = ('statement', 'value', 'equation', 'connection', 'qualification', 'label')
PANEL_IDENTIFIER = {'type':'string','minLength':1,'maxLength':32}
EXACT_TEXT_ITEM = {'type':'string','minLength':1,'maxLength':120}
OVERVIEW_MAX_PANELS = 4
OVERVIEW_MIN_LABELS = 2
OVERVIEW_MAX_LABELS = 12
OVERVIEW_MAX_RELATIONS = 8
OVERVIEW_TEXT_LIMITS = {'title': 80, 'subtitle': 160, 'footer': 240, 'heading': 60,
                        'purpose': 200, 'label': 48, 'relation_label': 24, 'note': 120}
OVERVIEW_PANEL_FIELDS = ('id', 'heading', 'construction', 'purpose', 'labels', 'relations', 'note',
                         'passages')
OVERVIEW_PANEL_REQUIRED = ('id', 'heading', 'construction', 'purpose', 'labels', 'passages')
OVERVIEW_PLAN_FIELDS = ('title', 'subtitle', 'footer', 'illustrative', 'panels')
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
    'construction':{'type':'string','enum':list(PANEL_CONSTRUCTION_FAMILIES)},
    'layout_intent':PLAN_TEXT,
    'content':{'type':'array','items':BLOG_CONTENT_SCHEMA,'minItems':1,'maxItems':8},
    'exact_text':{'type':'array','items':EXACT_TEXT_ITEM,'maxItems':8,'uniqueItems':True},
    'illustrative_values':{'type':'array','items':BLOG_ILLUSTRATIVE_VALUE,'uniqueItems':True},
})
BLOG_DRAFT_SCHEMA = object_schema({
    'plan':PLAN_SCHEMA,
    'text':TEXT,
    'figures':{'type':'array','items':BLOG_BRIEF_SCHEMA,'maxItems':3},
})
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


class PanelPlanError(ValueError):
    """A structural panel-plan failure with an exact location for the next refinement."""
    def __init__(self, issues):
        self.issues = issues
        super().__init__('; '.join(issue['message'] for issue in issues[:20]) + '.')


def _panel_error(errors, path, message, **details):
    errors.append({'code': 'panel_plan_validation', 'path': path, 'message': path + ' ' + message, **details})


def _text(item, key, path, errors, *, maximum=1200):
    value = item.get(key) if isinstance(item, dict) else None
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        _panel_error(errors, path + '.' + key, f'needs 1-{maximum} characters')


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


def validate_overview_plan(plan, evidence):
    """Validate one Overview plan against the retained evidence.

    The limits are the content budget: panel count, label count and length, relation count, and
    the length of every prose field. Every relation endpoint must be one of the panel's labels,
    and every panel must cite at least one retrieved passage.
    """
    errors = []
    known_passages = {item['id'] for item in evidence.get('passages', []) if isinstance(item, dict)}
    if not isinstance(plan, dict):
        raise PanelPlanError([{'code': 'panel_plan_validation', 'path': 'plan',
                               'message': 'plan must be an object.'}])
    for name in sorted(set(plan) - set(OVERVIEW_PLAN_FIELDS)):
        _panel_error(errors, 'plan.' + name, 'is unsupported')
    for name in sorted(set(OVERVIEW_PLAN_FIELDS) - set(plan)):
        _panel_error(errors, 'plan.' + name, 'is required')
    for name in ('title', 'subtitle', 'footer'):
        _text(plan, name, 'plan', errors, maximum=OVERVIEW_TEXT_LIMITS[name])
    if not isinstance(plan.get('illustrative'), bool):
        _panel_error(errors, 'plan.illustrative', 'must be true or false')
    panels = plan.get('panels')
    if not isinstance(panels, list) or not 1 <= len(panels) <= OVERVIEW_MAX_PANELS:
        _panel_error(errors, 'plan.panels', f'needs 1 through {OVERVIEW_MAX_PANELS} panels',
                     constraint='maximum_panels',
                     actual=len(panels) if isinstance(panels, list) else None, limit=OVERVIEW_MAX_PANELS)
        panels = panels if isinstance(panels, list) else []
    seen = set()
    for index, panel in enumerate(panels):
        path = f'plan.panels[{index}]'
        if not isinstance(panel, dict):
            _panel_error(errors, path, 'must be an object')
            continue
        for name in sorted(set(panel) - set(OVERVIEW_PANEL_FIELDS)):
            _panel_error(errors, path + '.' + name, 'is unsupported')
        for name in sorted(set(OVERVIEW_PANEL_REQUIRED) - set(panel)):
            _panel_error(errors, path, 'is missing ' + name)
        identifier = _identifier(panel.get('id'), path + '.id', errors, pattern=PANEL_ID_RE, label='panel id')
        if identifier is not None:
            if identifier in seen:
                _panel_error(errors, path + '.id', 'duplicates an earlier panel id: ' + identifier)
            seen.add(identifier)
        _text(panel, 'heading', path, errors, maximum=OVERVIEW_TEXT_LIMITS['heading'])
        _text(panel, 'purpose', path, errors, maximum=OVERVIEW_TEXT_LIMITS['purpose'])
        if panel.get('construction') not in PANEL_CONSTRUCTION_FAMILIES:
            _panel_error(errors, path + '.construction',
                         'must be one of ' + ', '.join(PANEL_CONSTRUCTION_FAMILIES))
        labels = _label_list(panel.get('labels'), path + '.labels', errors)
        relations = panel.get('relations', [])
        if relations is None:
            relations = []
        if not isinstance(relations, list):
            _panel_error(errors, path + '.relations', 'must be an array')
            relations = []
        elif len(relations) > OVERVIEW_MAX_RELATIONS:
            _panel_error(errors, path + '.relations', f'needs no more than {OVERVIEW_MAX_RELATIONS} items',
                         constraint='maximum_relations', actual=len(relations), limit=OVERVIEW_MAX_RELATIONS)
        for position, relation in enumerate(relations):
            _relation(relation, f'{path}.relations[{position}]', labels, errors)
        if 'note' in panel and panel['note'] is not None:
            _text(panel, 'note', path, errors, maximum=OVERVIEW_TEXT_LIMITS['note'])
        _passage_refs(panel.get('passages'), known_passages, path + '.passages', errors, required=True)
    if errors:
        raise PanelPlanError(errors[:20])
    normalized = {'title': plan['title'], 'subtitle': plan['subtitle'], 'footer': plan['footer'],
                  'illustrative': plan['illustrative'], 'panels': []}
    for panel in panels:
        entry = {'id': panel['id'], 'heading': panel['heading'], 'construction': panel['construction'],
                 'purpose': panel['purpose'], 'labels': list(panel['labels']),
                 'relations': [{key: value for key, value in relation.items() if value}
                               for relation in (panel.get('relations') or [])],
                 'passages': list(dict.fromkeys(panel['passages']))}
        if panel.get('note'):
            entry['note'] = panel['note']
        normalized['panels'].append(entry)
    return normalized


def _label_list(values, path, errors):
    if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
        _panel_error(errors, path, 'must be an array of short strings')
        return []
    if not OVERVIEW_MIN_LABELS <= len(values) <= OVERVIEW_MAX_LABELS:
        _panel_error(errors, path, f'needs {OVERVIEW_MIN_LABELS} through {OVERVIEW_MAX_LABELS} labels',
                     constraint='maximum_labels', actual=len(values), limit=OVERVIEW_MAX_LABELS)
    limit = OVERVIEW_TEXT_LIMITS['label']
    for index, value in enumerate(values):
        if not value.strip() or len(value) > limit:
            _panel_error(errors, f'{path}[{index}]', f'needs 1-{limit} characters')
    flattened = [_flatten_text(value) for value in values]
    if len(set(flattened)) != len(flattened):
        _panel_error(errors, path, 'must contain unique labels')
    return values


def _relation(relation, path, labels, errors):
    if not isinstance(relation, dict):
        _panel_error(errors, path, 'must be an object')
        return
    for name in sorted(set(relation) - {'from', 'to', 'label'}):
        _panel_error(errors, path + '.' + name, 'is unsupported')
    for name in ('from', 'to'):
        value = relation.get(name)
        if not isinstance(value, str) or value not in labels:
            _panel_error(errors, path + '.' + name, 'must be one of this panel\'s labels')
    if 'label' in relation and relation['label'] is not None:
        _text(relation, 'label', path, errors, maximum=OVERVIEW_TEXT_LIMITS['relation_label'])


def panel_assignments(plan):
    """Project a validated Overview plan into the author-facing drawing assignments.

    Evidence IDs stay in the plan. Every assignment carries the same one-line story so the
    panels use one vocabulary, and nothing else from the other panels.
    """
    story = plan['title'].rstrip('.') + '. ' + plan['subtitle']
    assignments = []
    for panel in plan['panels']:
        assignment = {'id': panel['id'], 'heading': panel['heading'],
                      'construction': panel['construction'], 'purpose': panel['purpose'],
                      'labels': list(panel['labels']),
                      'relations': [dict(relation) for relation in panel.get('relations') or []],
                      'story': story}
        if panel.get('note'):
            assignment['note'] = panel['note']
        assignments.append(assignment)
    return assignments


def blog_figure_assignment(brief):
    """Project a validated Blog brief into the drawing assignment shape Overview panels use.

    ``labels`` holds every string the check requires verbatim: the brief's ``exact_text`` plus
    each ``label`` and ``equation`` content item. The other content items are semantic lines the
    author expresses in the drawing; ``values`` repeats the ``value`` items whose numbers must
    survive.
    """
    labels = list(brief['exact_text'])
    labels += [item['text'] for item in brief['content'] if item['kind'] in ('equation', 'label')]
    return {
        'id': brief['id'],
        'heading': brief['title'],
        'construction': brief['construction'],
        'purpose': brief['purpose'],
        'takeaway': brief['exit_state'],
        'context': ' '.join(brief['entry_context']),
        'layout_intent': brief['layout_intent'],
        'labels': list(dict.fromkeys(value for value in labels if value.strip())),
        'relations': [],
        'content': [item['text'] for item in brief['content'] if item['kind'] not in ('equation', 'label')],
        'values': [item['text'] for item in brief['content'] if item['kind'] == 'value'],
        'illustrative_values': list(brief['illustrative_values']),
    }


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
    if brief.get('construction') not in PANEL_CONSTRUCTION_FAMILIES:
        _blog_error(errors, path + '.construction',
                    'must be one of ' + ', '.join(PANEL_CONSTRUCTION_FAMILIES))
    _blog_text(brief, 'layout_intent', path, errors)
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
        'construction': brief['construction'],
        'layout_intent': brief['layout_intent'],
        'content': content,
        'exact_text': exact_text,
        'illustrative_values': illustrative_values,
    }


def validate_blog_brief(brief, document, *, figure_id=None):
    """Validate one Blog drawing brief and return its normalized copy.

    ``figure_id`` is the stable identifier the caller requires; when supplied, the brief's own
    ``id`` must match it, so a correction cannot silently rename a figure. Issues carry the exact
    path, such as ``brief.layout_intent`` or ``figures[0].layout_intent``.
    """
    errors = []
    normalized = _validate_blog_brief(brief, document, errors, '', figure_id=figure_id)
    if errors or normalized is None:
        raise PlanValidationError(errors[:20])
    return copy.deepcopy(normalized)


def _blog_validate_text(text, document, length, errors):
    try:
        from papers.ai import ProviderError, _sources
        _sources(text, document['passages'])
    except ProviderError as exc:
        _blog_error(errors, 'text', str(exc))
    if length in BLOG_WORD_LIMITS:
        from papers.overview import clean_citations
        words = len(clean_citations(text).split())
        maximum = BLOG_WORD_LIMITS[length]
        if words > maximum:
            _blog_error(errors, 'text',
                        'has ' + str(words) + ' words; the limit is ' + str(maximum)
                        + ', so shorten it by at least ' + str(words - maximum)
                        + ' words while preserving citations and figure markers.',
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


def validate_blog_draft(draft, document, length):
    """Validate one Blog draft and return its normalized copy with derived metadata.

    The draft retains ``plan`` and cited ``text``; its ``figures`` are validated drawing briefs,
    not SVG or HTML. Evidence is checked against ``document['passages']``, markers must match the
    figure IDs exactly once each, and the article word limit follows ``length``. Figure word limits
    do not apply.
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
        _blog_validate_text(text, document, length, errors)
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
    for name in sorted(set(plan)-allowed):error('plan.'+name, 'is unsupported')
    for name in sorted(allowed-set(plan)):error('plan.'+name, 'is required')
    if plan.get('paper_type') not in PAPER_TYPES:error('plan.paper_type', 'must be supported')
    known={p['id'] for p in document['passages']}
    def text(item,key,path):
        value=item.get(key)
        if not isinstance(value,str) or not value.strip() or len(value)>1200:
            over=len(value)-1200 if isinstance(value,str) and len(value)>1200 else None
            message='needs 1-1200 characters'
            if over:
                message=(f'has {len(value)} characters; the limit is 1200, so shorten it by at '
                         f'least {over} characters while preserving required detail')
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
            error('plan.'+name, 'must be an evidence-linked object');continue
        if set(claim)!={'text','passages'}:error('plan.'+name, 'must contain only text and passages')
        text(claim,'text','plan.'+name);refs(claim,'plan.'+name)
    relationships=plan.get('relationships')
    if not isinstance(relationships,list) or not 1<=len(relationships)<=12:
        violation = max(1 - len(relationships), len(relationships) - 12, 0) if isinstance(relationships, list) else None
        error('plan.relationships', 'needs 1-12 items', violation)
        relationships=[]
    for index,relation in enumerate(relationships):
        path=f'plan.relationships[{index}]'
        if not isinstance(relation,dict):error(path, 'must be an object');continue
        if set(relation)!={'source','target','relationship','passages'}:
            error(path, 'must contain only source, target, relationship, and passages')
        for key in ('source','target','relationship'):text(relation,key,path)
        refs(relation,path)
    if errors:raise PlanValidationError(errors)
    return copy.deepcopy(plan)


def expand_candidate(draft, document):
    if not isinstance(draft,dict): raise ValueError('Submit an object with plan, text and figures.')
    value=copy.deepcopy(draft)
    plan=validate_plan(value.get('plan'),document)
    value.update(paper_type=plan['paper_type'],**{name:plan[name]['text'] for name in CLAIMS})
    value['passages']=list(dict.fromkeys(i for item in [*(plan[n] for n in CLAIMS),*plan['relationships']] for i in item['passages']))
    figures=value.get('figures')
    if not isinstance(figures,list): raise ValueError('Figures must be an array.')
    return value
