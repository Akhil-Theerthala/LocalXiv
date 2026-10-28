"""The Overview: select, digest, plan, diagram, render.

``Application.execute`` saves the result of ``run_workflow``. The reader, the exports, and the
Blog read it. It is deliberately small and flat.
"""
from __future__ import annotations

import json

from papers.coordinator import (Coordinator, create_run_directory, evidence_text, iso, provenance, request_validated,
                                run_recorded, run_stage, select_evidence, write_json)
from papers.diagrams import check, write_assets
from papers.explanation import (NOTATION, ValidationError, _check_text, _flatten_text, digest_passages,
                                normalize_digest_candidate, validate_digest)
from papers.reading import REVISION as READING_REVISION, build_orientation

PROMPT_REVISION = 'overview-mermaid-v1'
WIDTH = 1000
MAX_ITEMS, MAX_NODES = 7, 12
PLAN_CHARTS = ('bar', 'line', 'pie', 'quadrant', 'radar')
# The title, subtitle, and footer keep the Scene's limits.
TEXT_LIMITS = {'title': 100, 'subtitle': 240, 'footer': 320}

DIGEST_INSTRUCTION = (r"""Extract the core of this paper from the retrieved evidence: the first pass a reader takes.
A reader who knows the field rebuilds the paper's main idea from this object alone. The methodology
story, related work, and secondary experiments belong to the Blog.

Work in this order:
1. why: the problem and who has it, what blocks the usual approach, and the paper's idea.
2. contribution, result (the headline finding with its numbers), and qualification (the one
   condition a reader needs to read the result).
3. components, by paper type:
   - architecture: every component of the proposed model, nested by containment (a layer contains
     its sub-layers; the model contains its stacks), data flow in feeds, the operation each
     computes, tensor dimensions in values, and the training and inference difference when it
     matters. A reader redraws the architecture from this list.
   - method: the setup (inputs and outputs), each step of the mechanism in order, the equation each
     step computes, the running example's values at that step, and what changes against the baseline.
   - survey: each family of methods as a component that contains its representative methods, with
     the distinguishing principle as its role and the survey's key numbers as its values; the
     comparison axes go in hyperparameters.
   - evaluation: each compared method and each condition as a component, with the findings as its
     values; a finding along an ordered factor (position, size, steps) gives its points, such as
     "steps 1k: 2.31; 10k: 1.87; 100k: 1.52".
   - theory: the assumptions, each step of the argument, and the result, in feeds order.
4. example: one concrete input followed through the core operation: named tokens, a small matrix,
   or numbers, and what each step makes of them. Take the example the paper shows when it has one,
   such as the sentence of an attention visualization or a worked appendix example. A dataset or a
   benchmark score is a result.
5. hyperparameters: the settings a reader needs to reproduce the core.
Done when every component has a role and passages, every container lists its parts in contains,
and the example carries real values.

Write every text as a complete statement in plain words that names who acts, on what, and what any
comparison is against: "GPT-3.5 is trusted but codes worse than GPT-4".

Return one JSON object:
{"paper_type": "architecture" | "method" | "survey" | "evaluation" | "theory" | "other",
 "why": {"problem": at most 160 characters, "obstacle": at most 160 characters, "idea": at most 160
   characters, "passages": [exact IDs]},
 "contribution": {"text": one or two sentences, at most 400 characters, "passages": [exact IDs]},
 "result": {"text": at most 400 characters, "passages": [exact IDs]},
 "qualification": {"text": at most 400 characters, "passages": [exact IDs]},
 "example": one sentence, at most 320 characters (required for architecture and method papers),
 "hyperparameters": [up to 12 strings of at most 48 characters such as "d_model = 512", "h = 8", "N = 6"],
 "components": [{"id": short safe id, "name": 1-48 characters, "role": what it does, 1-160 characters,
   "computes": optional plain-notation operation this component computes, 1-100 characters,
   "values": optional concrete numbers or dimensions, 1-80 characters,
   "contains": [ids of components nested inside this one], "feeds": [ids this component sends output to],
   "repeat": optional such as "×6", at most 16 characters, "passages": [exact IDs]}]}
Use 4 through 24 components. Write every equation in """ + NOTATION + """. Copy passage IDs exactly.""")

PLAN_PROMPT = """Plan the Overview of this paper: the reader's first pass, one image they understand in about
30 seconds. It tells why the work was needed, how it works, and what it achieved. The Blog carries
everything else, so leave out what the first pass does not need.

From the digest, choose:
- through_line: one sentence from the problem to the result.
- items: at most 7 things on the path of the core mechanism, in reading order. Use a digest
  component name exactly when the item is a component; otherwise a short phrase of at most 6 words.
- headline_numbers: one or two numbers from the result, each with what it measures.
- chart: a result chart, or null. Add one only when the digest has at least 3 numbers on one
  measure that a reader should compare: methods, model sizes, steps, or conditions. Choose bar for
  a comparison of methods or conditions, line for a trend along an ordered factor, pie for shares
  of one whole, quadrant for methods placed on two axes, radar for methods across 3 or more
  metrics. Copy the values from the digest.

Return one JSON object and nothing else:
{"through_line": "...", "items": [{"name": "...", "why": "why the first pass needs it"}],
 "headline_numbers": [{"value": "...", "measures": "..."}],
 "chart": null or {"type": "bar|line|pie|quadrant|radar", "shows": "what it compares",
           "values": [["label", number], ...]}}"""

DIAGRAM_PROMPT = """Draw the Overview of this paper as one Mermaid diagram. The Overview is the reader's first pass:
one image that tells why the work was needed, how it works, and what it achieved. The reader follows
it along its arrows.

Choose the Mermaid diagram type and the layout that explain this paper best. A flowchart with
subgraphs suits most architectures and methods; a mindmap or a block diagram can suit a survey;
a sequence, state, timeline, or xychart diagram can suit a paper whose idea has that shape.
Use standard Mermaid 12.1 syntax.

Content:
- Draw the plan below: its through-line, its items in order, and its headline numbers. Write each
  item name exactly as the plan writes it, in a node label. Draw nothing the plan leaves out.
- At most 12 nodes. At most 8 words in a node label. A reader takes in the whole figure in about
  30 seconds; the Blog and the hover on each node carry the detail.
- Every arrow means the output of one node goes into the next.
- Write math in plain Unicode text (d_k, W^Q, √, ∑), with no backticks outside a markdown string.
  For an equation, you can use $$TeX$$.

Style: use Mermaid's styling freely to show what matters most: bold and italic in labels, and
classDef or style with font-size, font-weight, fill, stroke, and color. For example, draw the
headline numbers large and bold, the paper's idea in a strong colour, and secondary text small.
Text smaller than 11px is not readable. Bold and italic need a Mermaid markdown string, with
backticks inside the quotes: A["`**28.4 BLEU** on WMT 2014`"]. In a plain label such as
A["**28.4 BLEU**"], the asterisks show as asterisks.

Chart: when the plan has a chart, write it as a second Mermaid source in "chart": xychart (bar or
line), pie, quadrantChart, or radar-beta, with the plan's values and a short title. Leave its size
unset: the application draws it below the main diagram, 280 pixels high and as wide as the main
diagram. When the plan's chart is null, "chart" is null. The main diagram still shows the headline
numbers.

Shape: the figure displays in a 1000-pixel column. Keep the whole figure, the main diagram and the
chart below it, about as wide as it is high: width ÷ height between 0.6 and 1.4. Neither a tall
strip nor a wide band.

Return one JSON object and nothing else:
{"title": "the paper's main claim, at most 80 characters", "subtitle": "one sentence of at most 160 characters",
 "footer": "what is illustrative and the real values, at most 240 characters",
 "illustrative": true or false, "mermaid": "the complete Mermaid source of the main diagram",
 "chart": "the complete Mermaid source of the result chart, or null"}"""


def validate_overview_plan(plan):
    """The Overview plan, or ValidationError with the exact fix."""
    errors = []

    def fail(path, message):
        errors.append({'code': 'overview_plan', 'path': path, 'message': path + ' ' + message})

    if not isinstance(plan, dict):
        raise ValidationError([{'code': 'overview_plan', 'path': 'plan', 'message': 'plan must be an object.'}])
    _check_text(plan, 'through_line', 'plan', errors, maximum=400)
    items = plan.get('items')
    if not isinstance(items, list) or not items:
        fail('plan.items', f'needs 1 to {MAX_ITEMS} items')
    else:
        if len(items) > MAX_ITEMS:
            fail('plan.items', f'has {len(items)} items; the limit is {MAX_ITEMS}')
        for index, item in enumerate(items):
            _check_text(item, 'name', f'plan.items[{index}]', errors, maximum=80)
    numbers = plan.get('headline_numbers')
    if not isinstance(numbers, list) or not 1 <= len(numbers) <= 2:
        fail('plan.headline_numbers', 'needs 1 or 2 numbers, each with value and measures')
    chart = plan.get('chart')
    if chart is not None and (not isinstance(chart, dict) or chart.get('type') not in PLAN_CHARTS):
        fail('plan.chart', 'is null or an object whose type is one of ' + ', '.join(PLAN_CHARTS))
    if errors:
        raise ValidationError(errors[:20])
    return plan


class OverviewWorkflow:
    """Select, digest, plan, diagram, render. One run directory owns every request."""

    def __init__(self, provider, document, progress):
        self.provider = provider
        self.document = document
        self.progress = progress
        self.run_directory = create_run_directory(document)
        self.coordinator = Coordinator(provider, progress, run_directory=self.run_directory)

    def plan(self):
        """Selection and digest. Returns digest, evidence, selection, orientation."""
        orientation = build_orientation(self.document)
        selection, evidence = run_stage(self.coordinator, 'selection', lambda: select_evidence(
            self.coordinator, self.document, orientation))
        digest = run_stage(self.coordinator, 'digest', lambda: self._digest(evidence))
        return {'digest': digest, 'evidence': evidence, 'selection': selection, 'orientation': orientation}

    def _digest(self, evidence):
        """One validated digest request; the correction carries the rejected answer as assistant."""
        messages = [{'role': 'user', 'content': DIGEST_INSTRUCTION + '\n\n<retrieved_evidence>\n'
                     + evidence_text(evidence) + '\n</retrieved_evidence>'}]
        _, digest = request_validated(self.coordinator, 'digest', messages,
                                      lambda value: validate_digest(normalize_digest_candidate(value), evidence),
                                      stage='digest', attempts=3, describe='digest object')
        self.coordinator.note('digest_accepted', components=len(digest['components']), paper_type=digest['paper_type'])
        return digest

    def _overview_plan(self, digest):
        """What the first pass shows, chosen from the digest."""
        messages = [{'role': 'user', 'content': PLAN_PROMPT + '\n\n<digest>\n'
                     + json.dumps(digest, ensure_ascii=False) + '\n</digest>'}]
        _, plan = request_validated(self.coordinator, 'overview_plan', messages, validate_overview_plan,
                                    stage='overview_plan', attempts=3, describe='Overview plan')
        return plan

    def _diagram(self, digest, plan):
        """The plan drawn as one Mermaid diagram that passes the Diagram checks. Returns the answer and the check."""
        messages = [{'role': 'user', 'content': DIAGRAM_PROMPT + '\n\n<plan>\n' + json.dumps(plan, ensure_ascii=False)
                     + '\n</plan>\n\n<digest>\n' + json.dumps(digest, ensure_ascii=False) + '\n</digest>'}]
        checked = {}

        def validate(answer):
            errors = []
            for key, maximum in TEXT_LIMITS.items():
                _check_text(answer, key, 'diagram', errors, maximum=maximum)
            if errors:
                raise ValidationError(errors)
            checked.update(check(answer, width=WIDTH, required=[item['name'] for item in plan['items']],
                                 chart_wanted=bool(plan.get('chart')), max_nodes=MAX_NODES))
            return answer

        _, answer = request_validated(self.coordinator, 'diagram', messages, validate, stage='diagram',
                                      attempts=3, describe='diagram object')
        return answer, checked

    def run_workflow(self):
        store = self.coordinator.store
        plan = self.plan()
        digest, evidence = plan['digest'], plan['evidence']
        write_json(self.run_directory / 'digest.json', digest)
        store.update(stage='overview_plan')
        overview_plan = run_stage(self.coordinator, 'overview_plan', lambda: self._overview_plan(digest))
        write_json(self.run_directory / 'overview-plan.json', overview_plan)
        store.update(stage='diagram')
        answer, checked = run_stage(self.coordinator, 'diagram', lambda: self._diagram(digest, overview_plan))
        write_json(self.run_directory / 'diagram.json', answer)
        figure = {'id': 'fig1', 'title': answer['title'], 'paper_connection': answer['subtitle'],
                  'caption': answer['footer'], 'illustrative': bool(answer.get('illustrative')),
                  'passages': digest_passages(digest), 'mermaid': answer['mermaid'],
                  'chart': answer.get('chart') or None,
                  'chart_config': checked['chart_config'], 'layout_width': WIDTH, 'dimensions': checked['figure'],
                  'components': component_hooks(digest, checked['diagram']['nodes'])}
        figure.update(write_assets(self.document['directory'], 'fig1', checked, width=WIDTH, title=answer['title'],
                                   subtitle=answer['subtitle'], footer=answer['footer']))
        explanation = {'paper_type': digest['paper_type'],
                       'contribution': digest['contribution']['text'],
                       'finding': digest['result']['text'],
                       'qualification': digest['qualification']['text'],
                       'passages': digest_passages(digest)}
        shape = round(checked['figure']['width'] / checked['figure']['height'], 2)
        nodes = len(checked['diagram']['nodes'])
        store.update(status='completed', stage='completed', delivery='completed', finished_at=iso(), nodes=nodes)
        return {'text': '{{figure:fig1}}', 'explanation': explanation, 'plan': digest, 'overview_plan': overview_plan,
                'cited_text': '', 'figures': [figure], 'evidence': evidence['passages'],
                'provenance': {
                    **provenance(self.coordinator, self.document, evidence, PROMPT_REVISION),
                    'reading': dict(evidence.get('coverage') or {}, revision=READING_REVISION),
                    'selection': plan['selection'],
                    'checks': {'components': len(digest['components']), 'nodes': nodes, 'shape': shape},
                }}


def generate(provider, document, progress):
    """Run the complete Overview. A failed run never publishes a replacement Overview."""
    workflow = OverviewWorkflow(provider, document, progress)
    return run_recorded(workflow.coordinator, workflow.run_workflow)


def component_hooks(digest, nodes):
    """The Digest fields for every drawn node whose text names a component.

    The reader shows these on hover. Names are compared after whitespace and case normalisation,
    the same rule Digest coverage uses, and the longest matching name wins so "Multi-head
    attention" beats "Attention" on the same node.
    """
    components = sorted(digest['components'], key=lambda component: -len(component['name']))
    found = []
    for node in nodes:
        text = _flatten_text(node['text']).lower()
        match = next((component for component in components
                      if _flatten_text(component['name']).lower() in text), None)
        if match:
            found.append({'node': node['id'], 'name': match['name'], 'role': match['role'],
                          'computes': match.get('computes'), 'values': match.get('values'),
                          'passages': list(match.get('passages', []))})
    return found
