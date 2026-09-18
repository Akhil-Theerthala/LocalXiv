"""The Overview: select, digest, scene, layout, render.

The generation result contract below is what ``Application.execute`` saves and what the
reader, exports, and Blog reference admission consume. It is deliberately small and flat.
"""
from __future__ import annotations

import json
from pathlib import Path

from papers.ai import ProviderError
from papers.coordinator import (Coordinator, RETRY_SUFFIX, RunStore, create_run_directory, evidence_text,
                                finalize_run, iso, panel_digest, request_validated, select_evidence, write_json)
from papers.explanation import (digest_passages, example_coverage_issues, normalize_digest_candidate,
                                scene_coverage_issues, validate_digest)
from papers.figures import Figure, LayoutError, SceneError
from papers.figures.schema import collapse_repetitions
from papers.reading import REVISION as READING_REVISION, build_orientation

__all__ = ['OverviewWorkflow', 'generate', 'GENERATION_KEYS', 'PROVENANCE_KEYS', 'FIGURE_ASSET_KEYS',
           'PANEL_WORKFLOW', 'panel_digest']

# Serialized keys of the generation dictionary. Later stages must satisfy these exactly;
# tests/test_exports.py and tests/test_app.py assert this list so a rebuild cannot silently
# drop a key an older saved artifact or a caller still reads.
GENERATION_KEYS = ('text', 'explanation', 'plan', 'cited_text', 'figures', 'evidence', 'provenance')
PROVENANCE_KEYS = ('model', 'document_digest', 'passages', 'prompt_revision', 'reading', 'usage', 'reviews',
                   'created_at')
FIGURE_ASSET_KEYS = ('html', 'svg', 'png', 'pdf', 'svg_source')

PROMPT_REVISION = 'overview-scene-v1'
# Provenance marker for artifacts produced by this workflow. Blog reference admission accepts
# these as drawing references only, and never as a scientific review.
PANEL_WORKFLOW = 'panel-workflow-v1'
# A panel whose body spans less than this share of its width is sent back once for a wider
# arrangement; the reference figures fill 85% or more.
MIN_PANEL_FILL = 0.4

ATTENTION_EXAMPLE = '{"title":"Multi-Level Architecture and Attention Mechanism","subtitle":"Connects token-level scaled dot-product attention, multi-head parallel projections, and the complete encoder-decoder architecture.","footer":"Level 1 resolves anaphora for \'its\' via scaled dot products. Level 2 projects 8 parallel heads. Level 3 connects N=6 encoder-decoder stacks with cross-attention. Residuals and LayerNorm within sub-layers are simplified.","illustrative":true,"layout":"stack","panels":[{"id":"sdpa","heading":"Level 1: Scaled Dot-Product Attention on Concrete Tokens","tone":"blue","body":{"kind":"group","arrange":"row","children":[{"kind":"group","arrange":"row","children":[{"kind":"group","arrange":"column","children":[{"kind":"card","id":"law","label":"\\"The Law\\"","tone":"peach"},{"kind":"card","id":"kv1","label":"K1, V1","tone":"muted"}]},{"kind":"group","arrange":"column","children":[{"kind":"card","id":"app","label":"\\"application\\"","tone":"peach"},{"kind":"card","id":"kv2","label":"K2, V2","tone":"muted"}]},{"kind":"group","arrange":"column","children":[{"kind":"card","id":"its","label":"\\"its\\"","tone":"green"},{"kind":"card","id":"q","label":"Query Q","tone":"green"}]}]},{"kind":"group","heading":"Scaled Dot-Product Pipeline","arrange":"row","children":[{"kind":"group","arrange":"column","children":[{"kind":"card","id":"matmul","label":"MatMul: Q · Kᵀ","tone":"blue"},{"kind":"card","id":"scale","label":"Scale (÷ √dₖ)"},{"kind":"card","id":"softmax","label":"Softmax (Weights)"},{"kind":"card","id":"out","label":"MatMul · V → Output","tone":"green"}]},{"kind":"note","lines":["Specialized Heads:","• Head 5: \\"its\\" → \\"Law\\"","• Head 6: \\"its\\" → \\"appl.\\"","O(1) direct lookup"]}]}]},"edges":[{"from":"kv1","to":"matmul"},{"from":"kv2","to":"matmul"},{"from":"q","to":"matmul"},{"from":"matmul","to":"scale"},{"from":"scale","to":"softmax"},{"from":"softmax","to":"out"}]},{"id":"heads","heading":"Level 2: Multi-Head Parallelism (h = 8 Subspaces)","tone":"green","body":{"kind":"group","arrange":"row","children":[{"kind":"card","id":"inputs","label":"Layer Inputs","detail":"Q, K, V (d = 512)"},{"kind":"group","arrange":"column","children":[{"kind":"card","id":"h1","label":"Head 1 (Syntax / local)","tone":"blue"},{"kind":"card","id":"h5","label":"Head 5 (Coreference)","tone":"peach"},{"kind":"card","id":"hrest","label":"Heads 2..8 (Parallel)","tone":"muted"}]},{"kind":"card","id":"concat","label":"Concat (h × dᵥ)","detail":"8 × 64 = 512 dim","tone":"green"},{"kind":"card","id":"linear","label":"Linear (Wᴼ)","detail":"Output: d = 512"}]},"edges":[{"from":"inputs","to":"h1"},{"from":"inputs","to":"h5"},{"from":"inputs","to":"hrest"},{"from":"h1","to":"concat"},{"from":"h5","to":"concat"},{"from":"hrest","to":"concat"},{"from":"concat","to":"linear"}]},{"id":"stack","heading":"Level 3: Full Transformer Architecture (Encoder-Decoder)","tone":"peach","body":{"kind":"group","arrange":"row","children":[{"kind":"group","arrange":"column","children":[{"kind":"card","id":"kv","label":"Encoder Keys & Values"},{"kind":"group","heading":"ENCODER","repeat":"(N = 6)","arrange":"column","tone":"blue","children":[{"kind":"card","id":"effn","label":"Feed Forward Network"},{"kind":"card","id":"mhsa","label":"Multi-Head Self-Attention","detail":"All tokens attend mutually","tone":"blue"},{"kind":"card","id":"ein","label":"Input + Positional Encoding"},{"kind":"card","id":"src","label":"Source: \\"The Law will never...\\"","tone":"muted","plain":true}]}]},{"kind":"group","arrange":"column","children":[{"kind":"card","id":"lsm","label":"Linear + Softmax"},{"kind":"group","heading":"DECODER","repeat":"(N = 6)","arrange":"column","tone":"peach","children":[{"kind":"card","id":"dffn","label":"Feed Forward Network"},{"kind":"card","id":"cross","label":"Cross-Attention (Enc-Dec)","detail":"Q from Dec, K & V from Enc","tone":"green"},{"kind":"card","id":"masked","label":"Masked Self-Attention","detail":"Prevents looking ahead","tone":"peach"},{"kind":"card","id":"tgt","label":"Target Tokens (Shifted Right)"}]}]}]},"notes":["Constant O(1) sequential operations across tokens; recurrence and convolutions are entirely absent."],"edges":[{"from":"ein","to":"mhsa"},{"from":"mhsa","to":"effn"},{"from":"mhsa","to":"kv"},{"from":"tgt","to":"masked"},{"from":"masked","to":"cross"},{"from":"cross","to":"dffn"},{"from":"dffn","to":"lsm"},{"from":"kv","to":"cross"}]}]}'
VARIETY_EXAMPLE = '{"title":"Attention as a worked example","subtitle":"One query scores three keys, the scores become weights, and the weights mix the values.","footer":"Values are illustrative. Real d_k = 64 and h = 8; the masked grid shows decoder self-attention.","illustrative":true,"layout":"columns","panels":[{"id":"score","heading":"1. Score and weight","tone":"blue","body":{"kind":"group","arrange":"column","children":[{"kind":"sequence","items":[{"text":"The","sub":"k1"},{"text":"Law","sub":"k2"},{"text":"its","sub":"q","tone":"green","hot":true}]},{"kind":"steps","lines":["scores q·k = [3.0, 1.0, 0.4]","scale ÷ √d_k = ÷ 2 → [1.5, 0.5, 0.2]","softmax → [0.62, 0.23, 0.15]"]},{"kind":"sequence","items":[{"text":"0.62","sub":"→ Law","tone":"green","hot":true},{"text":"0.23","sub":"→ The"},{"text":"0.15","sub":"→ its"}]},{"kind":"note","lines":["Weights sum to 1","The output stays inside the value vectors"]}]}},{"id":"mask","heading":"2. Masked decoder grid","tone":"peach","body":{"kind":"group","arrange":"column","children":[{"kind":"grid","col_labels":["y1","y2","y3"],"row_labels":["y1","y2","y3"],"rows":[["*1.0",null,null],["0.4","*0.6",null],["0.2","0.3","*0.5"]],"caption":"future positions set to −∞ before softmax"},{"kind":"card","id":"masked","label":"Masked Self-Attention","detail":"Prevents looking ahead","tone":"peach"},{"kind":"divider","label":"Threshold cutoff α = 0.10"},{"kind":"card","id":"disc","label":"Discarded: y4..y10 (< α)","detail":"Cuts noise from rare tails","tone":"peach","dashed":true,"plain":true}]}},{"id":"result","heading":"3. Result","tone":"green","body":{"kind":"group","arrange":"column","children":[{"kind":"bars","items":[["ConvS2S",25.2],["ByteNet",23.8],["Transformer (base)",27.3],["Transformer (big)",28.4]],"caption":"BLEU, WMT 2014 EN-DE"},{"kind":"card","id":"cost","label":"Training cost","detail":"3.5 days on 8 P100 GPUs, a fraction of the prior best models"},{"kind":"note","lines":["Sequential ops O(1)","Path length O(1)","Per-layer O(n²·d)"]}]}}]}'

DIGEST_INSTRUCTION = r"""Extract what a reader must know to understand this paper's core from the retrieved
evidence. This is the first pass over the paper: the core content, not the methodology story,
related work, or every experiment. A reader who knows the field should be able to reconstruct the
paper's main idea from this object alone.

Return one JSON object:
{"paper_type": "architecture" | "method" | "survey" | "evaluation" | "theory" | "other",
 "contribution": {"text": one or two sentences, at most 400 characters, "passages": [exact IDs]},
 "result": {"text": the headline finding with its numbers, at most 400 characters, "passages": [exact IDs]},
 "qualification": {"text": the one caveat a reader needs to interpret the result, at most 400 characters, "passages": [exact IDs]},
 "example": one concrete running example with real values, one sentence, at most 320 characters (required for architecture and method papers),
 "hyperparameters": [up to 12 strings of at most 48 characters such as "d_model = 512", "h = 8", "N = 6"],
 "components": [{"id": short safe id, "name": 1-48 characters, "role": what it does, 1-160 characters,
   "computes": optional plain-notation operation this component computes, 1-100 characters,
   "values": optional concrete numbers or dimensions, 1-80 characters,
   "contains": [ids of components nested inside this one], "feeds": [ids this component sends output to],
   "repeat": optional such as "×6", at most 16 characters, "passages": [exact IDs]}]}

By paper type:
- architecture: every component of the proposed model, nested by containment (a layer contains its
  sub-layers; the model contains its stacks), data flow in feeds, the operation each computes, tensor
  dimensions in values, and the training versus inference distinction when it matters. A reader must be
  able to redraw the architecture from this list.
- method: the setup (inputs and outputs), each step of the mechanism in order, the equation each step
  computes, the running example's values at that step, and what changes against the baseline.
- survey: each family of methods as a component that contains its representative methods, role = the
  distinguishing principle, values = the key numbers the survey reports for it, and the comparison
  axes as hyperparameters.
- evaluation: each compared method and each condition as a component, values = the findings.
- theory: the assumptions, each step of the argument, and the result, in feeds order.
Use 4 through 24 components. Write every equation in plain notation that text can show (Unicode
symbols Σ ≥ ≤ √ · × → α and ASCII subscripts, never LaTeX). Copy passage IDs exactly."""

SCENE_INSTRUCTION = r"""Turn this digest into one information-dense figure the reader sees as a column 1000 units
wide. You decide the content and the structure; the application decides every size, gap, and
coordinate, so the object names no geometry. Every component name and every computes string in the
digest must appear somewhere in the scene exactly as written, in a card label, a card detail, a
step, or a note.

Containment is the first rule. A digest component with two or more parts of its own becomes a
group whose heading is that component's name (with its repeat, such as "(N = 6)"), holding the
nodes of its parts; when a whole panel is about that component, its name in the panel heading
counts instead (for example "Level 3: Full Transformer" holding the encoder and decoder groups). A part shared by several components is drawn once, and those components
become cards. A leaf component becomes a card whose label is its name and whose detail is the
operation it computes or its values. Never draw containment as a stack of full-width cards joined
by arrows. Two or three sibling containers (an encoder stack beside a decoder stack, or the
families of a survey) go in a row; a pipeline of steps goes in a column.

Structure: three panels is the norm. For an architecture: the core operation with its equation,
how it composes (heads, sub-layers), and the full system with its results. For a method: the
setup, the mechanism as a worked example, and the result. For a survey: the signals or inputs,
the families of methods, and the findings. Use a fourth panel only when the digest has more than
those hold, and one panel only for a small paper. Use "layout": "stack" for an architecture
(panels one under another) and "columns" for a method, survey, or evaluation (panels side by
side, in order). Each panel has a heading, one body node, optional notes (at most
2 lines under the body), and edges (arrows between cards in that panel, at most 12).

Node kinds, all with "kind":
- card: {"id"?, "label" ≤48, "detail"? ≤100 muted second line, "tone"? blue|green|peach|muted,
  "dashed"? true for a discarded or optional state, "plain"? true for a non-bold label}
- group: {"heading"? ≤48, "repeat"? such as "(N = 6)", "arrange": "row" | "column", "tone"?,
  "children": [1-8 nodes]}. A group with a heading draws a container; use it for containment
  (a layer holding its sub-layers). Groups nest at most 4 deep.
- note: {"lines": [1-4 strings ≤90]} a small text block; the first line is bold.
- sequence: {"items": [2-8 of {"id"?, "text" ≤16, "sub"? ≤20, "tone"?, "hot"? true}]} tokens,
  values, or steps in a row with an optional caption under each.
- grid: {"rows": [[cell]], "col_labels"? ≤16 each, "row_labels"? ≤16 each, "caption"? ≤90} a small
  matrix, at most 6×6; a cell is a number, a string ≤12, "*value" to highlight it, or null for a
  masked cell.
- steps: {"lines": [1-6 strings ≤72]} a numbered calculation; the last line is the result.
- bars: {"items": [2-8 of ["label" ≤28, number]], "caption"? ≤90} a comparison of values.
- divider: {"label"? ≤48} a dashed line, for a threshold or a boundary.
Edges: {"from": card id, "to": card id, "label"? ≤28, "accent"? true}. Arrows join cards of the
same panel only; use them for data flow, not for reading order.

The running example from the digest goes in the first panel as a sequence, steps, or grid with
its real values, so the reader follows concrete tokens or numbers through the mechanism. Draw
each component once in full; a later panel refers to it by a card with its name and no detail.
Tone at most six nodes per panel, and fewer is better; a tone marks a thing to notice, not a category.

Density is the goal: at most 24 nodes per panel, but use them, and use the width. A panel is 952
units wide; its body must span at least 40% of that, so arrange parts in rows, put sibling groups
side by side, and keep a single column for a short pipeline only. Put numbers in details, sequences,
grids, steps, and bars rather than in prose. Use tone for the one thing to notice per panel. Put
explanation in the subtitle and footer, not in cards. Title ≤100, subtitle ≤240, footer ≤320,
"illustrative": true when a shown value is a teaching value rather than a paper result.

Two complete examples of the object:
EXAMPLE_ARCHITECTURE
EXAMPLE_METHOD

Return one JSON object with title, subtitle, footer, illustrative, layout, and panels."""
SCENE_INSTRUCTION = SCENE_INSTRUCTION.replace('EXAMPLE_ARCHITECTURE', ATTENTION_EXAMPLE).replace('EXAMPLE_METHOD', VARIETY_EXAMPLE)



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
        selection, evidence = select_evidence(self.coordinator, self.document, orientation, vision=self.vision)
        digest = self._digest(evidence)
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
        messages = [{'role': 'user', 'content': SCENE_INSTRUCTION + '\n\n<digest>\n'
                     + json.dumps(digest, ensure_ascii=False) + '\n</digest>'}]

        def validate(value):
            scene = self.figure.validate(value)
            collapsed = collapse_repetitions(scene)
            if collapsed:
                self.coordinator.note('scene_repetitions_collapsed', labels=collapsed[:12])
            strings = self.figure.text(scene)
            issues = (scene_coverage_issues(digest, strings, self.figure.headings(scene))
                      + example_coverage_issues(digest, strings))
            if issues:
                raise SceneError(issues[:20])
            return scene

        raw, scene = request_validated(self.coordinator, 'scene', messages, validate, stage='scene',
                                       attempts=3, describe='scene object')
        for attempt in range(2):
            self.coordinator.active_stage = 'rendering'
            try:
                result = self._build(scene)
            except LayoutError as error:
                problem = str(error)
            else:
                narrow = [item for item in result.placements if item['fill'] < MIN_PANEL_FILL]
                if not narrow and not result.issues:
                    return scene, result
                if narrow:
                    problem = ('; '.join('panel ' + item['id'] + ' uses ' + str(round(item['fill'] * 100))
                                         + '% of its width' for item in narrow)
                               + '. Each panel is ' + str(int(MIN_PANEL_FILL * 100)) + '% or more of its width '
                               'when its body is a row, or a column of rows, or two groups side by side; a '
                               'single narrow column wastes the panel.')
                    self.coordinator.note('scene_narrow', panels=[item['id'] for item in narrow])
                else:
                    problem = '; '.join(result.issues[:3])
                    self.coordinator.note('composition_rejected', issues=result.issues[:8])
            if attempt:
                break
            correction = ('The previous scene laid out with a problem: ' + problem + ' Rearrange the '
                          'affected panels (put connected cards in one row or one column, put sibling '
                          'groups side by side, or drop an arrow that cannot pass). Return the complete '
                          'corrected scene object. ' + RETRY_SUFFIX)
            raw, scene = request_validated(self.coordinator, 'scene_layout', messages + [
                {'role': 'assistant', 'content': json.dumps(raw, ensure_ascii=False)},
                {'role': 'user', 'content': correction}], validate, stage='scene', describe='scene object')
        raise ProviderError('The scene could not be laid out: ' + problem)

    def run_workflow(self):
        store = self.coordinator.store
        plan = self.plan()
        digest, evidence = plan['digest'], plan['evidence']
        write_json(self.run_directory / 'digest.json', digest)
        store.update(stage='scene')
        self.progress('Composing the figure')
        scene, result = self._scene(digest)
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
                              for placement in result.placements])
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
                    'model': settings.get('model'), 'document_digest': document_digest_of(document),
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


def document_digest_of(document):
    from papers.library import document_digest
    return document_digest(document)
