"""Grounded visual-overview content and layout."""
from papers.overview import label

BENTO_PROMPT = """Stage 1: select grounded content for a research-paper bento overview.
Use the Excalidraw Visual Explainer lesson contract: a reader question, a misconception,
a central takeaway, scope, and one focal insight. These are metadata, not visible headings.
Explain the problem, relevant previous approach, what changed, how it works, supported
findings and their limits. Choose 4–9 distinct cards according to the evidence; never pad
or split a sentence simply to fill cards. Keep detailed teaching for the companion blog.
Use the saved original-figure readings to identify the paper's central framework and architecture.
Preserve the components and relationships they explain when selecting and simplifying content.
Choose the explanatory relationship before the renderer. A library template is not a reason
to add a visual. If supported visual types cannot preserve the idea, use clear prose instead.
Return JSON: {"layout":"bento", "title":"reader question, <=90 characters",
"misconception":"<=200 characters", "takeaway":"<=200 characters",
"scope":"<=200 characters", "focus":0, "arrows":[], "passages":["p00001"],
"nodes":[{"title":"natural short question or heading, <=45 characters",
"body":"direct paper-specific answer, <=180 characters",
"passages":["p00001"]}]}.
focus is the zero-based index of the central insight. Every card cites exact supporting
passage IDs. Use single-line plain text without Markdown. Give every card a concise, natural heading.
Prefer paper-specific questions: what changed, why it matters, how it works, what the
evidence shows, or where it falls short. Short What? or Why? headings are fine when
the answer makes their meaning clear. Do not mechanically repeat the same questions
or put a long sentence above another long sentence. Headings and answers must work together.
Never write 'The pain point', 'What the paper did', or 'What it achieved'. Start with the
actual substance. Explain unfamiliar terms. Preserve baselines and qualifications for
numbers; do not invent results or make unsupported comparisons. A heading must frame its answer without introducing an unsupported claim.
Write for scanning: target headings <=32 characters and answers <=140 characters.
Start each answer with its takeaway; add only one necessary qualification. Short questions
are welcome, but do not repeat a question template. Never remove a baseline, unit, dataset,
or limitation to meet the target; the hard limits above still apply. Use readable Unicode
notation such as √d and n², not raw LaTeX or code syntax. Explain complexity's operation.
Select one central contribution as focus. Order the remaining cards as evidence, mechanism,
context, and limitations where supported. Do not repeat claims across cards.
Optionally add a visual to at most TWO nodes, only when it explains a supported relationship
or makes reported results easier to compare. Omit visual for cards that work better as prose.
The only visual schemas are:
{"kind":"flow", "steps":["label target <=24, maximum 40 characters", "label target <=24, maximum 40 characters"],
 "caption":"<=100 characters explaining what arrows mean and any simplification", "passages":["p00001"]}
or {"kind":"metrics", "items":[{"label":"method or setting <=32 characters", "value":"exact reported value and unit <=16 characters"},
 {"label":"comparison <=32 characters", "value":"<=16 characters"}],
 "caption":"<=100 characters giving shared metric, dataset and comparison conditions", "passages":["p00001"]}.
A flow has 2–3 ordered steps. Each arrow means the preceding output feeds the next step,
not correlation, superiority, or an invented causal claim. Do not flatten branching networks,
parallel attention heads, residual connections or feedback into a sequential chain.
Metrics have 2–3 items. Preserve precision, units, baselines and shared evaluation settings;
do not compare unlike experiments or invent values. No decorative network icons or arbitrary
library assets. Keep the body useful on its own; the visual adds detail rather than repeats it.
Every visual label, value and relationship must be supported by its cited passages.
Add role to each node: contribution, mechanism, evidence, context, or limitation.
Preserve mathematical operators, transposes and variable meanings in diagrams. Distinguish
conditional steps from required steps and sequential depth from total computational cost.
Do not turn an author's hypothesis into a proven explanation. Omit composition here;
a separate stage will arrange the approved content.
Card area communicates editorial emphasis only. Do not describe geometry in the content."""

BENTO_COMPOSITION = """Arrange the supplied approved cards, without rewriting their content.
Return only {"composition":[{"columns":[{"span":5,"cards":[0,1]},{"span":7,"cards":[2]}]}]}.
Plan a real bento composition in a top-level composition array. Each band has columns:
{"columns":[{"span":7,"cards":[0]},{"span":5,"cards":[1,2]}]}.
Spans are integers summing to 12 per band, at least 4 each. A column contains one or
 two stacked cards. Every card index appears exactly once; put focus first. Choose spans
and stacking from the explanation: a detailed mechanism can sit beside two short claims;
a result comparison deserves width; compact supporting facts can share a three-column band.
Use different band arrangements when content supports them. Never manufacture variation
or repeat cards. Cards in a span-4 column must have <=110 body characters and no visual.
Use role-based color to distinguish the contribution, evidence, mechanism and limitations.
Do not reduce this to a full-width heading followed by identical equal-width rows.

Balance actual content height: put a rich visual beside two short stacked cards.
A short prose card should not occupy an entire tall column opposite a long visual.
Focus must be the first card but may share its column with another short card.
Keep the contribution prominent, then evidence and mechanism, then limits. Favor two
or three varied bands, not a wall of equally sized rectangles. No empty slots.
"""

BENTO_REVIEW = """Review the candidate against the original evidence and return the corrected full schema.
Preserve card count, order, roles and focal insight; correct their wording and visuals.
Do not choose geometry. Keep transposes, subscripts, conditional operations and hypothesis
qualifiers. State what a complexity bound counts; sequential steps are not total work.
In every field including takeaway, O(1) attention paths or sequential depth do not mean
constant total computation. Scaled dot products are between queries and keys; values
are combined using the resulting weights, not included in the score dot product.
Check title, takeaway and scope as carefully as card bodies. Evaluate each clause of comparisons separately: do not transfer a limitation of one method to another method. Check every claim, visual value, arrow and citation. Remove unsupported visuals instead of
guessing. Preserve qualifications and distinguish reported results from interpretation.
Then edit for scanning: one clear central contribution, short headings, answer-first bodies,
no repeated claims, no paragraph disguised as a heading, no raw math code. Keep only visuals
that teach a relationship or comparison. Ensure flow captions explain arrows and metrics
captions identify evaluation conditions. Do not add cards just to fill space.
"""


def validate_bento(spec, passages=None):
    if not isinstance(spec, dict) or spec.get('layout') != 'bento' or spec.get('arrows') != []:
        raise ValueError('Use a bento object without arrows.')
    for key, maximum in [('title',90), ('misconception',200), ('takeaway',200), ('scope',200)]:
        spec[key] = label(spec.get(key), maximum)
    nodes = spec.get('nodes')
    if not isinstance(nodes, list) or not 4 <= len(nodes) <= 9:
        raise ValueError('Select 4–9 distinct supported cards, without filler.')
    if type(spec.get('focus')) is not int or not 0 <= spec['focus'] < len(nodes):
        raise ValueError('Focus must identify one card.')
    known = {p['id'] for p in passages} if passages is not None else None
    visuals = [card['visual'] for card in nodes if isinstance(card, dict) and 'visual' in card]
    if len(visuals) > 2 or any(not isinstance(v, dict) for v in visuals):
        raise ValueError('Use at most two visual objects; omit unused visuals.')
    for entry in [spec, *nodes, *visuals]:
        if not isinstance(entry, dict):
            raise ValueError('Cards and visuals must be objects.')
        refs = entry.get('passages')
        if not isinstance(refs, list) or not refs or any(not isinstance(r,str) or (known is not None and r not in known) for r in refs):
            raise ValueError('Every card must cite exact supporting passage IDs.')
    for card in nodes:
        card['title'] = label(card.get('title'), 45, field='card title')
        if card['title'].lower().rstrip('?:.') in ('the pain point', 'what the paper did', 'what it achieved'):
            raise ValueError('Use a natural, paper-specific heading instead of a generic category label.')
        card['body'] = label(card.get('body'), 180, field='card body')
        if any(term in card['body'].lower() for term in ('the pain point', 'what the paper did', 'what it achieved')):
            raise ValueError('Replace generic labels with the actual claim.')
    for visual in visuals:
        visual['caption'] = label(visual.get('caption'), 100)
        if visual.get('kind') == 'flow':
            steps = visual.get('steps')
            if not isinstance(steps, list) or not 2 <= len(steps) <= 3:
                raise ValueError('A flow needs 2–3 supported steps.')
            visual['steps'] = [label(step, 40, field=f'flow step {i + 1}') for i, step in enumerate(steps)]
        elif visual.get('kind') == 'metrics':
            items = visual.get('items')
            if not isinstance(items, list) or not 2 <= len(items) <= 3 or any(not isinstance(item, dict) for item in items):
                raise ValueError('A metrics visual needs 2–3 labeled values.')
            for item in items:
                item['label'] = label(item.get('label'), 32)
                item['value'] = label(item.get('value'), 16)
        elif visual.get('kind') == 'illustration':
            from papers.illustrations import validate_illustration
            validate_illustration(visual)
        else:
            raise ValueError('Visual kind must be flow, metrics, or illustration.')
    composition = spec.get('composition')
    if composition is not None:
        if not isinstance(composition, list) or not composition or len(composition) > len(nodes):
            raise ValueError('Composition needs nonempty bands.')
        order = []
        for band in composition:
            columns = band.get('columns') if isinstance(band, dict) else None
            if not isinstance(columns, list) or not 1 <= len(columns) <= 3:
                raise ValueError('Each band needs 1–3 columns.')
            spans = []
            for column in columns:
                if not isinstance(column, dict) or type(column.get('span')) is not int or not 4 <= column['span'] <= 12:
                    raise ValueError('Column spans must be integers from 4 to 12.')
                ids = column.get('cards')
                if not isinstance(ids, list) or not 1 <= len(ids) <= 2 or any(type(i) is not int or not 0 <= i < len(nodes) for i in ids):
                    raise ValueError('A column needs 1–2 valid card indices.')
                if column['span'] == 4 and any(len(nodes[i]['body']) > 110 or nodes[i].get('visual') for i in ids):
                    raise ValueError('Span-4 cards require short text and no visual; widen this column.')
                order.extend(ids)
                spans.append(column['span'])
            if sum(spans) != 12:
                raise ValueError('Band spans must sum to 12.')
        if sorted(order) != list(range(len(nodes))) or order[0] != spec['focus']:
            raise ValueError('Composition must include each card once with focus first.')
    for node in nodes:
        if node.get('role', 'context') not in ('contribution', 'mechanism', 'evidence', 'context', 'limitation'):
            raise ValueError('Unknown card role.')
    return spec


def plan_bento(spec, portrait=False):
    """Stage 2: pack every claim once, keeping reading order and allocating by text demand."""
    validate_bento(spec)
    order = [spec['focus']] + [i for i in range(len(spec['nodes'])) if i != spec['focus']]
    bands = spec.get('composition')
    if not bands:
        # Saved designs have no composition. Give dense focal cards space beside shorter cards.
        bands = []
        while order:
            ids, order = order[:3], order[3:]
            columns = ([{'span':7, 'cards':ids[:1]}, {'span':5, 'cards':ids[1:]}]
                       if len(ids) > 1 else [{'span':12, 'cards':ids}])
            bands.append({'columns':columns})
    order = [i for band in bands for column in band['columns'] for i in column['cards']]
    if portrait:
        bands = [{'columns':[{'span':12, 'cards':[i]}]} for i in order]
    rows = [{'cards':[i for col in band['columns'] for i in col['cards']],
             'columns':band['columns']} for band in bands]
    return dict(spec, packing={'orientation': 'portrait' if portrait else 'landscape', 'rows': rows})
