"""The Overview: select, digest, scene, layout, render.

The generation result contract below is what ``Application.execute`` saves and what the
reader, exports, and Blog reference admission consume. It is deliberately small and flat.
"""
from __future__ import annotations

import json
from pathlib import Path

from papers.coordinator import (Coordinator, RETRY_SUFFIX, RunStore, create_run_directory, evidence_text,
                                finalize_run, iso, panel_digest, request_validated, run_stage, select_evidence,
                                write_json)
from papers.explanation import (digest_passages, digest_requirements, example_coverage_issues,
                                example_structure_issues, normalize_digest_candidate, scene_coverage_issues,
                                series_text_issues, story_issues, validate_digest)
from papers.errors import ProviderError
from papers.figures import Figure, LayoutError, SceneError
from papers.figures.checks import MIN_TEXT_DENSITY
from papers.figures.schema import NOTATION, card as scene_card, collapse_repetitions
from papers.library import document_digest
from papers.reading import REVISION as READING_REVISION, build_orientation

__all__ = ['OverviewWorkflow', 'generate', 'GENERATION_KEYS', 'PROVENANCE_KEYS', 'FIGURE_ASSET_KEYS',
           'PANEL_WORKFLOW', 'panel_digest', 'component_hooks']

# Serialized keys of the generation dictionary. Later stages must satisfy these exactly;
# tests/test_exports.py and tests/test_app.py assert this list so a rebuild cannot silently
# drop a key an older saved artifact or a caller still reads.
GENERATION_KEYS = ('text', 'explanation', 'plan', 'cited_text', 'figures', 'evidence', 'provenance')
PROVENANCE_KEYS = ('model', 'document_digest', 'passages', 'prompt_revision', 'reading', 'usage', 'reviews',
                   'created_at')
FIGURE_ASSET_KEYS = ('html', 'svg', 'png', 'pdf', 'svg_source', 'svg_dark')

PROMPT_REVISION = 'overview-scene-v9'
# Provenance marker for artifacts produced by this workflow. Blog reference admission accepts
# these as drawing references only, and never as a scientific review.
PANEL_WORKFLOW = 'panel-workflow-v1'
# A panel whose body spans less than this share of its width is sent back once for a wider
# arrangement; the reference figures fill 85% or more.
MIN_PANEL_FILL = 0.4

# Two complete scenes the model reads for their form: a why panel, claim headings, statements, flow
# arrows, a worked example drawn as values, and stats that open the result panel.
ATTENTION_EXAMPLE = json.dumps({
    'title': 'Attention alone is enough to translate',
    'subtitle': 'Every word attends to every other word in one step, so a translation model needs no recurrent '
                'layer.',
    'footer': 'Values in panel 2 are illustrative. Real d_model = 512, h = 8, d_k = 64.',
    'illustrative': True, 'layout': 'auto',
    'panels': [
        {'id': 'why', 'heading': 'Why: recurrent networks read a sentence one word at a time', 'tone': 'peach',
         'body': {'kind': 'group', 'arrange': 'row', 'children': [
             {'kind': 'card', 'id': 'problem', 'label': 'Recurrent networks train slowly',
              'detail': 'each word waits for the word before it', 'tone': 'peach'},
             {'kind': 'card', 'id': 'obstacle', 'label': 'Distant words are hard to link',
              'detail': 'a signal passes through every word between them'},
             {'kind': 'card', 'id': 'idea', 'label': 'Self-attention',
              'detail': 'every word looks at every other word in one step', 'tone': 'green'}]},
         'edges': [{'from': 'problem', 'to': 'obstacle'}, {'from': 'obstacle', 'to': 'idea'}]},
        {'id': 'how', 'heading': 'How: “its” scores every word and takes a weighted mix of their values',
         'tone': 'blue',
         'body': {'kind': 'group', 'arrange': 'row', 'children': [
             {'kind': 'sequence', 'items': [{'text': 'The', 'sub': 'key'}, {'text': 'Law', 'sub': 'key'},
                                            {'id': 'its', 'text': 'its', 'sub': 'query', 'hot': True}]},
             {'kind': 'card', 'id': 'attend', 'label': 'Scaled dot-product attention',
              'detail': '`softmax(QK^T/√d_k)V`', 'tone': 'blue'},
             {'kind': 'sequence', 'items': [{'id': 'law', 'text': '0.62', 'sub': 'to Law', 'hot': True},
                                            {'text': '0.23', 'sub': 'to The'}, {'text': '0.15', 'sub': 'to its'}]}]},
         'notes': ['“its” takes most of its value from “Law”, three words back'],
         'edges': [{'from': 'its', 'to': 'attend'}, {'from': 'attend', 'to': 'law'}]},
        {'id': 'model', 'heading': 'Model: 6 encoder and 6 decoder layers built from the same parts',
         'tone': 'green',
         'body': {'kind': 'group', 'arrange': 'row', 'children': [
             {'kind': 'group', 'heading': 'Encoder', 'repeat': '(N = 6)', 'detail': '`LayerNorm(x + Sublayer(x))`',
              'arrange': 'column', 'children': [
                  {'kind': 'card', 'id': 'self', 'label': 'Self-attention'},
                  {'kind': 'card', 'id': 'ffn', 'label': 'Feed-forward', 'detail': '`max(0, xW_1 + b_1)W_2 + b_2`'}]},
             {'kind': 'group', 'heading': 'Decoder', 'repeat': '(N = 6)', 'detail': '`LayerNorm(x + Sublayer(x))`',
              'arrange': 'column', 'children': [
                  {'kind': 'card', 'id': 'masked', 'label': 'Masked self-attention',
                   'detail': 'future positions set to −∞'},
                  {'kind': 'card', 'id': 'cross', 'label': 'Encoder–decoder attention', 'tone': 'blue'},
                  {'kind': 'card', 'id': 'dffn', 'label': 'Feed-forward'},
                  {'kind': 'card', 'label': 'Positional encoding'}]}]},
         'edges': [{'from': 'self', 'to': 'ffn'}, {'from': 'ffn', 'to': 'cross', 'label': 'keys, values'},
                   {'from': 'masked', 'to': 'cross'}, {'from': 'cross', 'to': 'dffn'}]},
        {'id': 'result', 'heading': 'Result: the best English→German score at a fraction of the training cost',
         'tone': 'green',
         'body': {'kind': 'group', 'arrange': 'column', 'children': [
             {'kind': 'group', 'arrange': 'row', 'children': [
                 {'kind': 'stat', 'value': '28.4', 'label': 'BLEU English→German, 2 above earlier models'},
                 {'kind': 'stat', 'value': '3.5 days', 'label': 'of training on 8 GPUs', 'tone': 'blue'}]},
             {'kind': 'bars', 'items': [['ConvS2S', 25.2], ['ByteNet', 23.8], ['Transformer base', 27.3]],
              'caption': 'BLEU English→German, earlier models and the base model'}]}}]}, ensure_ascii=False)

VARIETY_EXAMPLE = json.dumps({
    'title': 'A small model drafts, a large model checks',
    'subtitle': 'Speculative decoding generates several tokens per large-model pass and keeps the large '
                'model\'s output distribution.',
    'footer': 'Values are illustrative. The speed-up depends on how often the large model accepts a drafted '
              'token.',
    'illustrative': True, 'layout': 'auto',
    'panels': [
        {'id': 'why', 'heading': 'Why: a large model generates one token per forward pass', 'tone': 'peach',
         'body': {'kind': 'group', 'arrange': 'row', 'children': [
             {'kind': 'card', 'id': 'problem', 'label': 'Generation is slow',
              'detail': 'each token waits for one full pass of the large model', 'tone': 'peach'},
             {'kind': 'card', 'id': 'obstacle', 'label': 'The GPU is mostly idle',
              'detail': 'one token uses a small part of its compute'},
             {'kind': 'card', 'id': 'idea', 'label': 'Draft, then verify',
              'detail': 'a small model drafts tokens; the large model checks them in one pass', 'tone': 'green'}]},
         'edges': [{'from': 'problem', 'to': 'obstacle'}, {'from': 'obstacle', 'to': 'idea'}]},
        {'id': 'how', 'heading': 'How: the large model accepts 3 of 4 drafted tokens in one pass', 'tone': 'blue',
         'body': {'kind': 'group', 'arrange': 'row', 'children': [
             {'kind': 'sequence', 'items': [{'text': 'the', 'sub': 'kept'}, {'text': 'cat', 'sub': 'kept'},
                                            {'text': 'sat', 'sub': 'kept'},
                                            {'id': 'down', 'text': 'down', 'sub': 'checked', 'hot': True}]},
             {'kind': 'card', 'id': 'verify', 'label': 'Large model verifies',
              'detail': '`accept if u < p_large(x) / p_small(x)`', 'tone': 'blue'},
             {'kind': 'steps', 'lines': ['the small model drafts 4 tokens', 'one large-model pass scores all 4',
                                         'keep the first 3, resample the 4th from the large model']}]},
         'edges': [{'from': 'down', 'to': 'verify'}]},
        {'id': 'result', 'heading': 'Result: 2.5× faster generation with the same output distribution',
         'tone': 'green',
         'body': {'kind': 'group', 'arrange': 'row', 'children': [
             {'kind': 'group', 'arrange': 'column', 'children': [
                 {'kind': 'stat', 'value': '2.5×', 'label': 'faster than the large model alone'},
                 {'kind': 'stat', 'value': '0', 'label': 'change in the output distribution', 'tone': 'blue'}]},
             {'kind': 'chart', 'marks': 'line', 'x_label': 'tokens drafted', 'y_label': 'speed-up ×',
              'series': [{'label': 'speed-up', 'points': [[1, 1.6], [2, 2.1], [4, 2.5], [8, 2.3]]}]}]}}]},
    ensure_ascii=False)

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

SCENE_WRAPPER = (r"""Turn this digest into one figure that tells the paper's story: why the work was needed, how
it works, and what it achieved. A reader follows it panel by panel along its arrows, and the panel
headings alone tell the story.

Work in this order:
1. Why panel: the first panel, with the id "why" and a heading that starts with "Why: ". Its body
   is a row of three cards joined by two edges: the digest's why.problem (tone peach), why.obstacle,
   and why.idea (tone green), each as a short label and a one-line detail.
2. Middle panels, by paper type. Architecture: How (the core operation on the running example),
   then Model (how the parts compose). Method: How (the mechanism as a worked example), with Setup
   before it when the inputs need it. Survey: the families of methods. Evaluation: Setup (the task,
   the models, and the factor varied). Theory: the main result as its equation.
3. Result panel: the last panel. It opens with a row of one to three stat nodes, the headline
   numbers of the digest's result, each with a label that says what it measures and for what. A
   chart or bars beside or under them show the comparison behind them, with each stat's number
   shown once.
Done when the headings alone tell the story, every digest component name and computes string
appears in the scene exactly as written, and every edge carries data flow.

Headings and words
- Each panel heading is a claim a reader can check, after "Why: ", "How: ", "Model: ", "Setup: ", or
  "Result: ", such as "How: “its” scores every word and takes a weighted mix of their values". The
  title is the paper's main claim or the question it answers.
- Write every label and detail in plain words a reader understands without the paper. Name who acts
  and on what, and name what each comparison is against: "GPT-3.5 is trusted but codes worse than
  GPT-4", "experts can audit only 2% of solutions".
- A label is a name. A detail is one fact: the operation the card computes, or one value. Each
  equation appears once, on the card that computes it.
- Numbers go in details, sequences, grids, steps, stats, and bars; explanation goes in the subtitle
  and the footer. Each panel has at most one note line, for the one fact the reader must not miss.
- A digest name or computes string goes in a card label or detail, a group heading or detail, a
  step, or a note.

Structure
- An edge means the output of one card goes into the next. Draw edges along the mechanism's path in
  one direction: left to right along a row, or down a column; a stack drawn with its input at the
  bottom points up. A card that no edge touches is drawn as a small label chip, and the reader sees
  its digest fields on hover.
- A digest component with two or more parts of its own becomes a group: its name (with its repeat,
  such as "(N = 6)") is the heading, the operation it computes or its values is the detail, and the
  nodes of its parts are its children; the name appears once, as the heading. When a whole panel is
  about that component, its name in the panel heading counts instead.
- A part shared by several components is drawn once, and those components become cards. A leaf
  component becomes a card: its name is the label, and its operation or values is the detail.
- Two or three sibling containers (an encoder stack beside a decoder stack, or the families of a
  survey) go in a row; a pipeline of steps goes in a column; a single column is for a short path.
- The How panel carries the digest's running example as a sequence, steps, or a grid with its real
  values, and an edge joins its tokens or numbers to the operation that uses them.
- Each component is drawn once in full; a later panel refers to it by a card with its name only.
- Tone at most six nodes per panel, for the things to notice.
- A value along an ordered factor (position, size, steps) is a chart with "marks": "line"; two
  measures plotted against each other are a chart with "marks": "dots"; separate items are bars.
  Draw the values the digest gives; without values, state the trend in a card.
- Set "layout": "auto"; the application places the panels. Title ≤80, subtitle ≤160, footer ≤240,
  and "illustrative": true when a shown value is a teaching value rather than a paper result.

One complete example of the object. It shows the form; every string in your scene comes from the
digest.
EXAMPLE

Return one JSON object with title, subtitle, footer, illustrative, layout, and panels.""")



def focus(scene):
    """Draw each untoned card that no edge touches as a chip, and set the auto layout.

    A chip shows its label only; the reader sees its Digest fields in the Component hover, so the
    figure keeps every component and only the mechanism's path carries details. Returns the labels.
    """
    chips = []
    for panel in scene['panels']:
        ends = {end for edge in panel.get('edges', []) for end in (edge['from'], edge['to'])}
        stack = [panel['body']]
        while stack:
            node = stack.pop()
            stack.extend(node.get('children') or [])
            if node['kind'] == 'card' and node.get('id') not in ends and not node.get('tone'):
                node['minor'] = True
                node.pop('detail', None)
                chips.append(node['label'])
    scene['layout'] = 'auto'
    return chips


class OverviewWorkflow:
    """Select, digest, scene, layout, render. One run directory owns every request."""

    def __init__(self, provider, document, progress, *, vision=False, run_directory=None):
        if not document.get('passages'):
            raise ProviderError(document.get('report', {}).get('text_warning')
                                or 'This paper has no retained passages for an overview.')
        if not document.get('directory'):
            raise ProviderError('Save the paper before generating an overview.')
        self.provider = provider
        self.document = document
        self.progress = progress
        self.vision = vision
        self.run_directory = Path(run_directory) if run_directory else create_run_directory(document)
        RunStore(self.run_directory)
        self.coordinator = Coordinator(provider, progress, run_directory=self.run_directory)
        self.figure = Figure(width=1000)

    def plan(self):
        """Selection and digest. Returns digest, evidence, selection, orientation."""
        orientation = build_orientation(self.document)
        selection, evidence = run_stage(self.coordinator, 'selection', lambda: select_evidence(
            self.coordinator, self.document, orientation, vision=self.vision))
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

    def _build(self, scene):
        return self.figure.build(scene, self.document['directory'], 'fig1', frame='page',
                                 page_title=self.document.get('title', ''))

    def _scene(self, digest):
        """A validated, covering, laid-out scene in at most three requests plus one layout correction.

        Validation and digest coverage are checked inside the request loop. A scene that validates
        but cannot be laid out, or that renders too sparse or with native defects, gets one more
        correction with the reason. Returns the scene and its ``FigureResult``.
        """
        example = ATTENTION_EXAMPLE if digest.get('paper_type') == 'architecture' else VARIETY_EXAMPLE
        messages = [{'role': 'user', 'content': scene_card() + '\n\n' + SCENE_WRAPPER.replace('EXAMPLE', example)
                     + '\n\n<digest>\n' + json.dumps(digest, ensure_ascii=False) + '\n</digest>'}]

        def validate(value):
            scene = self.figure.validate(value)
            collapsed = collapse_repetitions(scene)
            if collapsed:
                self.coordinator.note('scene_repetitions_collapsed', labels=collapsed[:12])
            strings = self.figure.text(scene)
            issues = [{'code': 'scene_coverage', 'path': 'scene', 'value': value,
                       'message': 'scene does not show the digest string ' + json.dumps(value)
                                  + '; put it in a card label or detail, a group heading or detail, a step, '
                                    'or a note exactly as written'}
                      for value in self.figure.missing(scene, digest_requirements(digest))]
            issues += (scene_coverage_issues(digest, strings, self.figure.headings(scene))
                       + example_coverage_issues(digest, strings) + example_structure_issues(digest, scene)
                       + series_text_issues(scene) + story_issues(scene))
            if issues:
                raise SceneError(issues[:20])
            chips = focus(scene)
            if chips:
                self.coordinator.note('scene_chips', labels=chips[:24])
            return scene

        raw, scene = request_validated(self.coordinator, 'scene', messages, validate, stage='scene',
                                       attempts=3, describe='scene object')
        shippable = None
        for attempt in range(2):
            self.coordinator.active_stage = 'rendering'
            try:
                result = self._build(scene)
            except LayoutError as error:
                problem = str(error)
            else:
                narrow = [item for item in result.placements if item['fill'] < MIN_PANEL_FILL]
                if not narrow and not result.issues:
                    if not result.warnings or attempt:
                        return scene, result
                    # An arrow detour is worth one correction; the figure ships if that fails.
                    shippable = (scene, result)
                    problem = ('; '.join(result.warnings[:3]) + '. Put the two cards of each such arrow next to '
                               'each other in one row or one column, or drop the arrow if it is not data flow.')
                    self.coordinator.note('arrow_detours', warnings=result.warnings[:8])
                elif narrow:
                    problem = ('; '.join('panel ' + item['id'] + ' uses ' + str(round(item['fill'] * 100))
                                         + '% of its width' for item in narrow)
                               + '. Each panel is ' + str(int(MIN_PANEL_FILL * 100)) + '% or more of its width '
                               'when its body is a row, or a column of rows, or two groups side by side; a '
                               'single narrow column wastes the panel.')
                    self.coordinator.note('scene_narrow', panels=[item['id'] for item in narrow])
                else:
                    problem = '; '.join(result.issues[:3])
                    if result.density < MIN_TEXT_DENSITY:
                        # More prose would pass the floor and make the figure harder to follow; a
                        # wider, shorter arrangement removes the empty area instead.
                        problem += ('. Make the panels wide and short: put sibling groups side by side '
                                    'and the inputs of one card in a row beside it, and show the digest\'s '
                                    'values in stats, sequences, and charts. Add no notes or other prose.')
                    self.coordinator.note('composition_rejected', issues=result.issues[:8])
            if attempt:
                break
            correction = ('The previous scene laid out with a problem: ' + problem + ' Rearrange the '
                          'affected panels (put connected cards in one row or one column, put sibling '
                          'groups side by side, or drop an arrow that cannot pass). Return the complete '
                          'corrected scene object. ' + RETRY_SUFFIX)
            try:
                raw, scene = request_validated(self.coordinator, 'scene_layout', messages + [
                    {'role': 'assistant', 'content': json.dumps(raw, ensure_ascii=False)},
                    {'role': 'user', 'content': correction}], validate, stage='scene', describe='scene object')
            except (SceneError, ProviderError):
                if not shippable:
                    raise
                # The detour correction failed; the figure before it was fine except for one arrow.
                self.coordinator.note('arrow_detours_kept', warnings=shippable[1].warnings[:8])
                return shippable
        if shippable:
            return shippable
        raise ProviderError('The scene could not be laid out: ' + problem)

    def run_workflow(self):
        store = self.coordinator.store
        plan = self.plan()
        digest, evidence = plan['digest'], plan['evidence']
        write_json(self.run_directory / 'digest.json', digest)
        store.update(stage='scene')
        self.progress('Composing the figure')
        scene, result = run_stage(self.coordinator, 'scene', lambda: self._scene(digest))
        write_json(self.run_directory / 'scene.json', scene)
        (self.run_directory / 'overview.source.svg').write_text(result.svg)
        write_json(self.run_directory / 'placements.json', result.placements)
        write_json(self.run_directory / 'composition-checks.json', result.checks)
        figure = {'id': 'fig1', 'title': scene['title'], 'paper_connection': scene['subtitle'],
                  'caption': scene['footer'], 'illustrative': scene['illustrative'],
                  'passages': digest_passages(digest), 'source_svg': result.svg}
        settings = getattr(self.provider, 'settings', {}) or {}
        stored_source = (Path(self.document['directory']) / result.assets['svg_source']).read_text()
        headings = {panel['id']: panel['heading'] for panel in scene['panels']}
        figure.update(result.assets, checks=result.checks, dimensions=result.checks['canvas'],
                      panels=[{'id': placement['id'], 'title': headings.get(placement['id'], ''),
                               **{key: placement['frame'][key] for key in ('x', 'y', 'width', 'height')},
                               'text': ''}
                              for placement in result.placements],
                      components=component_hooks(digest, result.placements))
        explanation = {'paper_type': digest['paper_type'],
                       'contribution': digest['contribution']['text'],
                       'finding': digest['result']['text'],
                       'qualification': digest['qualification']['text'],
                       'passages': digest_passages(digest)}
        events = self.coordinator.events
        store.update(status='completed', stage='completed', delivery='completed', finished_at=iso(),
                     panels=len(scene['panels']), density=round(result.density, 1))
        document = self.document
        return {'text': '{{figure:fig1}}', 'explanation': explanation, 'plan': digest, 'cited_text': '',
                'figures': [figure], 'evidence': evidence['passages'],
                'provenance': {
                    'model': settings.get('model'), 'document_digest': document_digest(document),
                    'source_digest': document.get('source_digest'), 'arxiv_id': document.get('arxiv_id'),
                    'evidence_format': document.get('format', 'epub'),
                    'pdf_digest': document.get('pdf_digest'),
                    'passages': [item['id'] for item in evidence['passages']],
                    'prompt_revision': PROMPT_REVISION,
                    'workflow': PANEL_WORKFLOW,
                    'narrative_digest': panel_digest(digest),
                    'scene_digest': panel_digest(scene),
                    'figure_digests': {figure['id']: panel_digest(stored_source)},
                    'reading': dict(evidence.get('coverage') or {}, revision=READING_REVISION),
                    'selection': plan['selection'],
                    'usage': [event for event in events if event.get('usage')],
                    'events': events,
                    'checks': {'density': round(result.density, 1), 'panels': len(scene['panels']),
                               'components': len(digest['components'])},
                    'reviews': [],
                    'created_at': iso(),
                    'run': str(self.run_directory.relative_to(Path(document['directory']))),
                }}

    def run(self):
        """Run the complete overview. A failed run never publishes a replacement overview."""
        try:
            return self.run_workflow()
        except BaseException as error:
            try:
                finalize_run(self.coordinator.store, error, stage=self.coordinator.active_stage)
            except Exception:
                # Diagnostic writing must never replace the original exception.
                pass
            raise


def generate(provider, document, progress, *, vision=False):
    return OverviewWorkflow(provider, document, progress, vision=vision).run()


def component_hooks(digest, placements):
    """The Digest fields for every drawn node whose text names a component.

    The reader shows these on hover. Names are compared after whitespace and case normalisation,
    the same rule Digest coverage uses, and the longest matching name wins so "Multi-head
    attention" beats "Attention" on the same card.
    """
    def flat(value):
        return ' '.join(str(value).split()).lower()

    components = sorted(digest['components'], key=lambda component: -len(component['name']))
    found = []
    for placement in placements:
        for node in placement.get('nodes', []):
            text = flat(node['text'])
            match = next((component for component in components if flat(component['name']) in text), None)
            if match:
                found.append({'node': node['node'], 'name': match['name'], 'role': match['role'],
                              'computes': match.get('computes'), 'values': match.get('values'),
                              'passages': list(match.get('passages', []))})
    return found
