"""Evidence-linked contracts shared by selection, authoring and review."""
import copy
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


# --- Overview panel plan -------------------------------------------------------------------
# One flat plan: shared canonical facts, then ordered panel briefs. There are no groups, bridge
# routes, shape quotas, or passage-union coverage rules; ownership of a narrative claim is
# explicit in `covers`, so a copied citation cannot stand in for it.
PANEL_CONSTRUCTION_FAMILIES = ('flow', 'mapping', 'comparison', 'calculation', 'chart')
PANEL_CONTENT_KINDS = ('statement', 'value', 'equation', 'connection', 'qualification', 'label')
PANEL_IDENTIFIER = {'type':'string','minLength':1,'maxLength':16}
FACT_KEY = {'type':'string','minLength':1,'maxLength':40}
SHARED_FACT_SCHEMA = object_schema({
    'text':PLAN_TEXT,
    'passages':{'type':'array','items':TEXT,'uniqueItems':True},
    'kind':{'type':'string','enum':['source','illustrative']},
})
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
})
PANEL_PLAN_SCHEMA = object_schema({
    'title':{'type':'string','minLength':1,'maxLength':80},
    'paper_connection':PLAN_TEXT,
    'caption':PLAN_TEXT,
    'shared_facts':{'type':'object','additionalProperties':SHARED_FACT_SCHEMA},
    'panels':{'type':'array','items':PANEL_BRIEF_SCHEMA,'minItems':1,'maxItems':7},
})
PANEL_ID_RE = re.compile(r'[A-Za-z][A-Za-z0-9_-]{0,15}')
FACT_KEY_RE = re.compile(r'[A-Za-z][A-Za-z0-9_.-]{0,39}')
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
    'candidate': CANDIDATE_SCHEMA,
})
REVIEW_ISSUE_SCHEMA = object_schema({
    'category':{'type':'string','enum':['unsupported_claim','incorrect_mechanism',
        'missing_explanation','misleading_connection','missing_transition',
        'unexplained_term','scope','readability']},
    'path':TEXT, 'message':PLAN_TEXT,
    'passages':{'type':'array','items':TEXT,'uniqueItems':True},
})
REVIEW_RESPONSE_SCHEMA = {'anyOf':[
    object_schema({'action':{'type':'string','enum':['verdict']},
                   'approved':{'type':'boolean'},
                   'issues':{'type':'array','items':REVIEW_ISSUE_SCHEMA}}),
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
        if set(fact) != {'text', 'passages', 'kind'}:
            _panel_error(errors, path, 'must contain only text, passages, and kind')
        _text(fact, 'text', path, errors, maximum=200)
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
        for name in sorted(set(PANEL_BRIEF_SCHEMA['properties']) - set(brief)):
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


def panel_assignments(plan):
    """Project a validated panel plan into the author-facing drawing assignments.

    Evidence IDs and source text are removed; the plan stays in provenance. Inherited context is
    resolved from the exact exit states of the referenced earlier panels, and shared facts are
    resolved to their canonical display text.
    """
    exits = {brief['id']: brief['exit_state'] for brief in plan['panels']}
    facts = {key: fact['text'] for key, fact in (plan.get('shared_facts') or {}).items()}
    illustrative = {key for key, fact in (plan.get('shared_facts') or {}).items()
                    if fact.get('kind') == 'illustrative'}
    assignments = []
    for brief in plan['panels']:
        assignments.append({
            'id': brief['id'],
            'title': brief['title'],
            'purpose': brief['purpose'],
            'entry_context': [exits[parent] for parent in brief['entry_from']],
            'content': [{'text': item['text'], 'kind': item['kind']} for item in brief['content']],
            'exit_state': brief['exit_state'],
            'shared_facts': {key: facts[key] for key in brief['shared_fact_ids']},
            'illustrative_values': [facts[key] for key in brief['shared_fact_ids'] if key in illustrative],
            'construction': brief['construction'],
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
