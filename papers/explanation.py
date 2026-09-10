"""Evidence-linked meaning shared by authoring, rendering and review."""
import copy

CLAIMS = ('question', 'contribution', 'finding', 'limitation')
PAPER_TYPES = ('architecture', 'method', 'survey', 'evaluation', 'theory', 'other')
TEXT = {'type':'string'}
REFS = {'type':'array','items':TEXT,'minItems':1}


def object_schema(fields):
    return {'type':'object','properties':fields,'required':list(fields)}


CLAIM_SCHEMA = object_schema({'text':TEXT,'passages':REFS})
PLAN_SCHEMA = object_schema({
    'paper_type':{'type':'string','enum':list(PAPER_TYPES)},
    **{name:CLAIM_SCHEMA for name in CLAIMS},
    'visual_focus':TEXT,
    'relationships':{'type':'array','items':object_schema({'source':TEXT,'target':TEXT,'relationship':TEXT,'passages':REFS})},
})
FIGURE_SCHEMA = object_schema({**{name:TEXT for name in ('id','title','paper_connection','caption','html')},
                              'illustrative':{'type':'boolean'},'passages':REFS})
CANDIDATE_SCHEMA = object_schema({'plan':PLAN_SCHEMA,'text':TEXT,'figures':{'type':'array','items':FIGURE_SCHEMA}})


def validate_plan(plan, document):
    if not isinstance(plan,dict) or plan.get('paper_type') not in PAPER_TYPES:
        raise ValueError('Plan needs a supported paper_type.')
    known={p['id'] for p in document['passages']}
    def text(item,key):
        value=item.get(key)
        if not isinstance(value,str) or not value.strip() or len(value)>1200:
            raise ValueError('Plan needs concise '+key+'.')
    def refs(item):
        ids=item.get('passages')
        if not isinstance(ids,list) or not ids or any(not isinstance(i,str) or i not in known for i in ids):
            raise ValueError('Each plan claim and relationship needs exact supporting passage IDs.')
    text(plan,'visual_focus')
    for name in CLAIMS:
        claim=plan.get(name)
        if not isinstance(claim,dict): raise ValueError('Plan needs an evidence-linked '+name+'.')
        text(claim,'text'); refs(claim)
    relationships=plan.get('relationships')
    if not isinstance(relationships,list) or not 1<=len(relationships)<=12:
        raise ValueError('Plan needs 1–12 relationships the explanation must preserve.')
    for relation in relationships:
        if not isinstance(relation,dict): raise ValueError('Each relationship must be an object.')
        for key in ('source','target','relationship'): text(relation,key)
        refs(relation)
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
