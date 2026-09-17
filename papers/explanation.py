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
# Overview narrative fields do not inherit Blog's 1,200-character PLAN_TEXT limit. The resource
# protection is the bounded UTF-8 candidate size below; it is an implementation guard, not an
# editorial word or length target.
OVERVIEW_CANDIDATE_MAX_BYTES = 256 * 1024


# --- Overview panel plan -------------------------------------------------------------------
# One flat plan: shared canonical facts, then ordered panel briefs. There are no groups, bridge
# routes, shape quotas, or passage-union coverage rules; ownership of a narrative claim is
# explicit in `covers`, so a copied citation cannot stand in for it.
PANEL_CONSTRUCTION_FAMILIES = ('flow', 'mapping', 'comparison', 'calculation', 'chart')
PANEL_CONTENT_KINDS = ('statement', 'value', 'equation', 'connection', 'qualification', 'label')
PANEL_IDENTIFIER = {'type':'string','minLength':1,'maxLength':32}
FACT_KEY = {'type':'string','minLength':1,'maxLength':40}
# A shared fact's text is the semantic fact a panel may explain visually. exact_text holds the
# short planner-selected strings (names, values with units, notation) that must appear unchanged.
EXACT_TEXT_ITEM = {'type':'string','minLength':1,'maxLength':120}
SHARED_FACT_SCHEMA = object_schema({
    'text':{'type':'string','minLength':1,'maxLength':200},
    'passages':{'type':'array','items':TEXT,'uniqueItems':True},
    'kind':{'type':'string','enum':['source','illustrative']},
    'exact_text':{'type':'array','items':EXACT_TEXT_ITEM,'maxItems':8,'uniqueItems':True},
}, required=('text','passages','kind'))
PANEL_CONTENT_SCHEMA = object_schema({
    'text':PLAN_TEXT,
    'passages':{'type':'array','items':TEXT,'uniqueItems':True},
    'kind':{'type':'string','enum':list(PANEL_CONTENT_KINDS)},
})
PANEL_BRIEF_SCHEMA = object_schema({
    'id':PANEL_IDENTIFIER,
    'title':{'type':'string','minLength':1,'maxLength':80},
    'purpose':PLAN_TEXT,
    'covers':{'type':'array','items':TEXT,'uniqueItems':True},
    'entry_from':{'type':'array','items':PANEL_IDENTIFIER,'uniqueItems':True},
    'exit_state':PLAN_TEXT,
    'shared_fact_ids':{'type':'array','items':FACT_KEY,'uniqueItems':True},
    'content':{'type':'array','items':PANEL_CONTENT_SCHEMA,'minItems':1,'maxItems':8},
    'construction':{'type':'string','enum':list(PANEL_CONSTRUCTION_FAMILIES)},
    'layout_intent':{'type':'string','minLength':1},
}, required=('id','title','purpose','covers','entry_from','exit_state','shared_fact_ids',
             'content','construction'))
PANEL_PLAN_SCHEMA = object_schema({
    'title':{'type':'string','minLength':1,'maxLength':80},
    'paper_connection':PLAN_TEXT,
    'caption':PLAN_TEXT,
    'shared_facts':{'type':'object','additionalProperties':SHARED_FACT_SCHEMA},
    'panels':{'type':'array','items':PANEL_BRIEF_SCHEMA,'minItems':1,'maxItems':7},
})
PANEL_ID_RE = re.compile(r'[A-Za-z][A-Za-z0-9_-]{0,31}')
FACT_KEY_RE = re.compile(r'[A-Za-z][A-Za-z0-9_.-]{0,39}')


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


def narrative_claim_keys(narrative):
    """The narrative keys a panel may own: the four claims and each stated relationship."""
    if not isinstance(narrative, dict):
        return []
    keys = [name for name in CLAIMS]
    keys += [f'relationships[{index}]' for index, _ in enumerate(narrative.get('relationships') or [])]
    return keys


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

    Text is nonempty without Blog's per-field length cap; the whole JSON candidate is bounded by
    ``OVERVIEW_CANDIDATE_MAX_BYTES``. A list of string steps for ``visual_focus`` is normalised to
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


def validate_panel_plan(plan, narrative, evidence):
    """Validate one Overview panel plan against its narrative and retained evidence.

    Structural validation covers count, safe identifiers, earlier-only handoffs, known claim
    keys, known passage and fact IDs, and required content. Whether the science is supported
    and the explanation complete is the planner's review job, not this function's claim.
    """
    errors = []
    known_passages = {item['id'] for item in evidence.get('passages', []) if isinstance(item, dict)}
    claim_keys = set(narrative_claim_keys(narrative))
    if not isinstance(plan, dict):
        raise PanelPlanError([{'code': 'panel_plan_validation', 'path': 'panel_plan',
                               'message': 'panel_plan must be an object.'}])
    allowed = set(PANEL_PLAN_SCHEMA['properties'])
    for name in sorted(set(plan) - allowed):
        _panel_error(errors, 'panel_plan.' + name, 'is unsupported')
    for name in sorted(allowed - set(plan)):
        _panel_error(errors, 'panel_plan.' + name, 'is required')
    _text(plan, 'title', 'panel_plan', errors, maximum=80)
    _text(plan, 'paper_connection', 'panel_plan', errors)
    _text(plan, 'caption', 'panel_plan', errors)
    facts = plan.get('shared_facts')
    fact_keys = set()
    if not isinstance(facts, dict):
        _panel_error(errors, 'panel_plan.shared_facts', 'must be an object keyed by fact name')
        facts = {}
    for key in sorted(facts):
        path = 'panel_plan.shared_facts.' + str(key)
        if not _identifier(key, path, errors, pattern=FACT_KEY_RE, label='fact key'):
            continue
        fact_keys.add(key)
        fact = facts[key]
        if not isinstance(fact, dict):
            _panel_error(errors, path, 'must be an object')
            continue
        unsupported = sorted(set(fact) - {'text', 'passages', 'kind', 'exact_text'})
        for name in unsupported:
            _panel_error(errors, path, 'contains unsupported field ' + name)
        for name in ('text', 'passages', 'kind'):
            if name not in fact:
                _panel_error(errors, path, 'is missing ' + name)
        _text(fact, 'text', path, errors, maximum=200)
        exact = fact.get('exact_text', [])
        if not isinstance(exact, list) or any(not isinstance(item, str) for item in exact):
            _panel_error(errors, path + '.exact_text', 'must be an array of short strings')
        else:
            fact_text = _flatten_text(fact.get('text'))
            for position, item in enumerate(exact):
                if not item.strip() or len(item) > 120:
                    _panel_error(errors, path + '.exact_text[' + str(position) + ']',
                                 'needs 1 through 120 characters')
                elif _flatten_text(item) not in fact_text:
                    _panel_error(errors, path + '.exact_text[' + str(position) + ']',
                                 'must be copied from the approved fact text in the same notation')
        kind = fact.get('kind')
        if kind not in ('source', 'illustrative'):
            _panel_error(errors, path + '.kind', 'must be source or illustrative')
        _passage_refs(fact.get('passages'), known_passages, path + '.passages', errors,
                      required=kind == 'source')
    panels = plan.get('panels')
    if not isinstance(panels, list) or not 1 <= len(panels) <= 7:
        _panel_error(errors, 'panel_plan.panels', 'needs 1 through 7 panels')
        panels = panels if isinstance(panels, list) else []
    positions, order = set(), []
    for index, brief in enumerate(panels):
        path = f'panel_plan.panels[{index}]'
        if not isinstance(brief, dict):
            _panel_error(errors, path, 'must be an object')
            continue
        if set(brief) - set(PANEL_BRIEF_SCHEMA['properties']):
            _panel_error(errors, path, 'contains unsupported fields')
        for name in sorted(set(PANEL_BRIEF_SCHEMA['required']) - set(brief)):
            _panel_error(errors, path, 'is missing ' + name)
        identifier = _identifier(brief.get('id'), path + '.id', errors,
                                pattern=PANEL_ID_RE, label='panel id')
        if identifier is not None:
            if identifier in positions:
                _panel_error(errors, path + '.id', 'duplicates an earlier panel id: ' + identifier)
            else:
                positions.add(identifier)
                order.append(identifier)
        _text(brief, 'title', path, errors, maximum=80)
        _text(brief, 'purpose', path, errors)
        _text(brief, 'exit_state', path, errors)
        if 'layout_intent' in brief:
            intent = brief['layout_intent']
            if not isinstance(intent, str) or not intent.strip():
                _panel_error(errors, path + '.layout_intent', 'needs nonempty text')
        if brief.get('construction') not in PANEL_CONSTRUCTION_FAMILIES:
            _panel_error(errors, path + '.construction',
                         'must be one of ' + ', '.join(PANEL_CONSTRUCTION_FAMILIES))
        covers = brief.get('covers')
        if not isinstance(covers, list) or any(not isinstance(value, str) for value in covers):
            _panel_error(errors, path + '.covers', 'must be an array of narrative claim keys')
            covers = []
        for key in covers:
            if key not in claim_keys:
                _panel_error(errors, path + '.covers', 'names an unknown narrative claim: ' + str(key))
        parents = brief.get('entry_from')
        if not isinstance(parents, list) or any(not isinstance(value, str) for value in parents):
            _panel_error(errors, path + '.entry_from', 'must be an array of earlier panel ids')
            parents = []
        earlier = set(order[:-1]) if identifier in order else set(order)
        for parent in parents:
            if parent not in earlier:
                _panel_error(errors, path + '.entry_from',
                             'must name an earlier panel, not ' + str(parent))
        fact_ids = brief.get('shared_fact_ids')
        if not isinstance(fact_ids, list) or any(not isinstance(value, str) for value in fact_ids):
            _panel_error(errors, path + '.shared_fact_ids', 'must be an array of shared fact keys')
            fact_ids = []
        for key in fact_ids:
            if key not in fact_keys:
                _panel_error(errors, path + '.shared_fact_ids', 'names an unknown shared fact: ' + str(key))
        content = brief.get('content')
        if not isinstance(content, list) or not 1 <= len(content) <= 8:
            _panel_error(errors, path + '.content', 'needs 1 through 8 ordered items')
            content = content if isinstance(content, list) else []
        cited = set()
        for item_index, item in enumerate(content):
            item_path = f'{path}.content[{item_index}]'
            if not isinstance(item, dict):
                _panel_error(errors, item_path, 'must be an object')
                continue
            if set(item) != {'text', 'passages', 'kind'}:
                _panel_error(errors, item_path, 'must contain only text, passages, and kind')
            _text(item, 'text', item_path, errors)
            if item.get('kind') not in PANEL_CONTENT_KINDS:
                _panel_error(errors, item_path + '.kind', 'must be one of ' + ', '.join(PANEL_CONTENT_KINDS))
            cited.update(_passage_refs(item.get('passages'), known_passages,
                                       item_path + '.passages', errors, required=False))
        fact_passages = {passage for key in fact_ids if key in facts and isinstance(facts.get(key), dict)
                         for passage in (facts[key].get('passages') or [])}
        claim_passages = {passage for name in covers if name in CLAIMS and isinstance(narrative.get(name), dict)
                          for passage in (narrative[name].get('passages') or [])}
        if identifier is not None and not (cited or fact_passages or claim_passages):
            _panel_error(errors, path, 'must cite at least one retained passage through content, '
                                       'a shared fact, or a covered claim')
    owners = {key for brief in panels if isinstance(brief, dict)
              for key in (brief.get('covers') or []) if isinstance(key, str)}
    orphaned = [name for name in CLAIMS if name not in owners]
    if orphaned:
        _panel_error(errors, 'panel_plan.panels',
                     'leaves narrative claims without a panel owner: ' + ', '.join(orphaned),
                     constraint='unowned_claims', actual=len(orphaned), limit=0)
    if errors:
        raise PanelPlanError(errors[:20])
    return copy.deepcopy(plan)


def blog_figure_assignment(brief):
    """Project a validated Blog brief into the author-facing drawing assignment.

    Evidence IDs and source text stay in the saved brief. The drawing author receives the
    visual purpose, the required labels and values, and the broad layout idea.
    """
    return {
        'id': brief['id'],
        'title': brief['title'],
        'purpose': brief['purpose'],
        'entry_context': list(brief['entry_context']),
        'exit_state': brief['exit_state'],
        'construction': brief['construction'],
        'content': [{'text': item['text'], 'kind': item['kind']} for item in brief['content']],
        'exact_text': list(brief['exact_text']),
        'illustrative_values': list(brief['illustrative_values']),
        'shared_facts': {},
        'layout_intent': brief['layout_intent'],
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


# An inline source handle is an evidence passage ID, such as p00014 or s0003, standing in prose.
_INLINE_HANDLE = re.compile(r'\bp\d{5,}\b|\bs\d{4,}\b|\bf\d{4,}\b')


def _strip_inline_handles(text):
    """Drop inline passage IDs from prose, keeping every other word and value unchanged.

    This is display projection only: it never touches the saved narrative, shared facts, or
    declared exact display text, and it does not decide scientific meaning.
    """
    return _INLINE_HANDLE.sub(' ', str(text or ''))


def _story_context(narrative):
    """Compact orientation, not another evidence bundle or a display requirement.

    Prefer the accepted narrative's visual_focus and contribution, selecting only complete
    sentences when a field exceeds the budget. If neither fits, use other narrative claims or
    disclose the omission rather than cutting an expression or inventing an orientation.
    Inline source handles are removed only from this projection; the accepted narrative and
    panel content are unchanged. This prompt budget never requires another provider request.
    """
    omitted = []

    def bounded(value):
        return _flatten_text(_strip_inline_handles(value))

    def line(label, value):
        if not isinstance(value, str) or not value.strip():
            return None
        text = bounded(value)
        total = len(label) + 2 + len(text)
        if total <= 1100:
            return label + ': ' + text
        selected = []
        used = 0
        # Only consider conservative period + new prose boundaries: ! and ? can be
        # operators; decimals and single-letter/number terms are not safe split points.
        # Reject uncertain bracket splits rather than displaying an expression's tail.
        sentences = re.split(r'(?<=\.)\s+(?=[A-Z][a-z]|A [a-z])', text)
        if any(not re.search(r'(?:\b[a-z]{2,}|\b\d+\.\d+)\.$', sentence)
               for sentence in sentences[:-1]):
            sentences = []
        for sentence in sentences:
            brackets = []
            for char in sentence:
                if char in '([{':
                    brackets.append(char)
                elif char in ')]}':
                    if not brackets or brackets.pop() != {')': '(', ']': '[', '}': '{'}[char]:
                        break
            else:
                if not brackets:
                    continue
            sentences = []
            break
        for sentence in sentences:
            size = len(sentence) + (1 if selected else 0)
            if not sentence.endswith('.') or used + size > 1000:
                # Skip whole sentences, never fall back to a word or character cutoff.
                continue
            selected.append(sentence)
            used += size
        if not selected:
            omitted.append(label + ': omitted (no complete sentence fits the orientation budget).')
            return None
        omitted.append(label + ': some sentences omitted for the orientation budget.')
        return label + ': ' + ' '.join(selected) + ' …'

    lines = [line('Teaching focus', narrative.get('visual_focus')),
             line('Contribution', (narrative.get('contribution') or {}).get('text'))]
    lines = [entry for entry in lines if entry]
    if not lines:
        for field in ('question', 'finding', 'limitation'):
            entry = line(field.capitalize(), (narrative.get(field) or {}).get('text'))
            if entry:
                lines.append(entry)
                break
    if not lines:
        lines.append('No complete narrative sentence fits the shared orientation budget.')
    if omitted:
        lines.extend(omitted)
        lines.append('Use the complete content and handoffs in this assignment.')
    return '\n'.join(lines)


def panel_assignments(plan, *, narrative=None):
    """Project a validated panel plan into the author-facing drawing assignments.

    Evidence IDs and source text are removed; the plan stays in provenance. Inherited context is
    resolved from the exact exit states of the referenced earlier panels. Shared facts keep their
    canonical display text. The author-facing ``exact_text`` is the ordered union of referenced
    facts' declared exact strings, complete equation items, and complete label items: these must
    appear unchanged. Semantic fact text and other prose may be expressed visually instead.
    Optional layout intent is copied unchanged. Supplying the accepted narrative adds the same
    compact story orientation to every assignment, without exposing evidence or other briefs.
    """
    story = _story_context(narrative) if narrative is not None else ''
    exits = {brief['id']: brief['exit_state'] for brief in plan['panels']}
    source_facts = plan.get('shared_facts') or {}
    facts = {key: fact['text'] for key, fact in source_facts.items()}
    exact_by_key = {key: list(fact.get('exact_text') or []) for key, fact in source_facts.items()}
    illustrative = {key for key, fact in source_facts.items()
                    if fact.get('kind') == 'illustrative'}
    assignments = []
    for brief in plan['panels']:
        exact_text = []
        for key in brief['shared_fact_ids']:
            exact_text.extend(exact_by_key.get(key, []))
        for item in brief['content']:
            if item['kind'] in ('equation', 'label'):
                exact_text.append(item['text'])
        exact_text = list(dict.fromkeys(value for value in exact_text if value.strip()))
        assignments.append({
            'id': brief['id'],
            'title': brief['title'],
            'purpose': brief['purpose'],
            'entry_context': [exits[parent] for parent in brief['entry_from']],
            'content': [{'text': item['text'], 'kind': item['kind']} for item in brief['content']],
            'exit_state': brief['exit_state'],
            'shared_facts': {key: facts[key] for key in brief['shared_fact_ids']},
            'illustrative_values': [facts[key] for key in brief['shared_fact_ids'] if key in illustrative],
            'exact_text': exact_text,
            'construction': brief['construction'],
            **({'layout_intent': brief['layout_intent']} if 'layout_intent' in brief else {}),
            **({'story_context': story} if story else {}),
        })
    return assignments


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
