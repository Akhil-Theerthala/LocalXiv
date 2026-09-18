"""Overview coordinator: evidence, digest, scene, layout, and completion.

The generation result contract below is what ``Application.execute`` saves and what the
reader, exports, and Blog reference admission consume. It is deliberately small and flat.
"""
from __future__ import annotations

import copy
import datetime
import hashlib
import json
import os
import re
import tempfile
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit

from papers import html_figures
from papers.ai import ProviderError, _evidence
from papers.convert import Cancelled
from papers.explanation import (PanelPlanError, digest_passages,
                                scene_coverage_issues, validate_digest, validate_scene,
                                validate_selection)
from papers.overview import parse_json
from papers.reading import (REVISION as READING_REVISION, build_orientation, evidence_document,
                            orientation_page, retrieve_evidence)
from papers.scene_layout import SceneLayoutError, compose_scene, scene_headings, scene_text

# Serialized keys of the generation dictionary. Later stages must satisfy these exactly;
# tests/test_exports.py and tests/test_app.py assert this list so a rebuild cannot silently
# drop a key an older saved artifact or a caller still reads.
GENERATION_KEYS = ('text', 'explanation', 'plan', 'cited_text', 'figures', 'evidence', 'provenance')
PROVENANCE_KEYS = ('model', 'document_digest', 'passages', 'prompt_revision', 'svg_profile_revision',
                   'reading', 'usage', 'reviews', 'created_at')
FIGURE_ASSET_KEYS = ('html', 'svg', 'png', 'pdf', 'svg_source')

PROMPT_REVISION = 'overview-scene-v1'
# Provenance marker for artifacts produced by this workflow. Blog reference admission accepts
# these as drawing references only, and never as a scientific review.
PANEL_WORKFLOW = 'panel-workflow-v1'
# Text runs per million square units below which a composed figure is rejected as sparse. The
# user's reference figures measure about 42 to 64; the abandoned model-drawn output measured 13.
MIN_TEXT_DENSITY = 30
# A panel whose body spans less than this share of its width is sent back once for a wider
# arrangement; the reference figures fill 85% or more.
MIN_PANEL_FILL = 0.4
RUN_STATES = ('running', 'completed', 'failed', 'cancelled')
TERMINAL_RUN_STATES = ('completed', 'failed', 'cancelled')
# Response files never retain image payloads. The planner never needs them, but a provider may
# echo one in an error or answer.
_BASE64_PAYLOAD = re.compile(r'data:[^;\s]+;base64,[A-Za-z0-9+/=]+')
_UNWRITTEN = object()
# One retry for a transient transport failure, never for an authentication failure.
TRANSIENT_MARKERS = ('HTTP status 429', 'HTTP status 500', 'HTTP status 502', 'HTTP status 503',
                     'HTTP status 504', 'returned an invalid response')
RETRY_BACKOFF_SECONDS = 1.5

ATTENTION_EXAMPLE = '{"title":"Multi-Level Architecture and Attention Mechanism","subtitle":"Connects token-level scaled dot-product attention, multi-head parallel projections, and the complete encoder-decoder architecture.","footer":"Level 1 resolves anaphora for \'its\' via scaled dot products. Level 2 projects 8 parallel heads. Level 3 connects N=6 encoder-decoder stacks with cross-attention. Residuals and LayerNorm within sub-layers are simplified.","illustrative":true,"layout":"stack","panels":[{"id":"sdpa","heading":"Level 1: Scaled Dot-Product Attention on Concrete Tokens","tone":"blue","body":{"kind":"group","arrange":"row","children":[{"kind":"group","arrange":"row","children":[{"kind":"group","arrange":"column","children":[{"kind":"card","id":"law","label":"\\"The Law\\"","tone":"peach"},{"kind":"card","id":"kv1","label":"K1, V1","tone":"muted"}]},{"kind":"group","arrange":"column","children":[{"kind":"card","id":"app","label":"\\"application\\"","tone":"peach"},{"kind":"card","id":"kv2","label":"K2, V2","tone":"muted"}]},{"kind":"group","arrange":"column","children":[{"kind":"card","id":"its","label":"\\"its\\"","tone":"green"},{"kind":"card","id":"q","label":"Query Q","tone":"green"}]}]},{"kind":"group","heading":"Scaled Dot-Product Pipeline","arrange":"row","children":[{"kind":"group","arrange":"column","children":[{"kind":"card","id":"matmul","label":"MatMul: Q · Kᵀ","tone":"blue"},{"kind":"card","id":"scale","label":"Scale (÷ √dₖ)"},{"kind":"card","id":"softmax","label":"Softmax (Weights)"},{"kind":"card","id":"out","label":"MatMul · V → Output","tone":"green"}]},{"kind":"note","lines":["Specialized Heads:","• Head 5: \\"its\\" → \\"Law\\"","• Head 6: \\"its\\" → \\"appl.\\"","O(1) direct lookup"]}]}]},"edges":[{"from":"kv1","to":"matmul"},{"from":"kv2","to":"matmul"},{"from":"q","to":"matmul"},{"from":"matmul","to":"scale"},{"from":"scale","to":"softmax"},{"from":"softmax","to":"out"}]},{"id":"heads","heading":"Level 2: Multi-Head Parallelism (h = 8 Subspaces)","tone":"green","body":{"kind":"group","arrange":"row","children":[{"kind":"card","id":"inputs","label":"Layer Inputs","detail":"Q, K, V (d = 512)"},{"kind":"group","arrange":"column","children":[{"kind":"card","id":"h1","label":"Head 1 (Syntax / local)","tone":"blue"},{"kind":"card","id":"h5","label":"Head 5 (Coreference)","tone":"peach"},{"kind":"card","id":"hrest","label":"Heads 2..8 (Parallel)","tone":"muted"}]},{"kind":"card","id":"concat","label":"Concat (h × dᵥ)","detail":"8 × 64 = 512 dim","tone":"green"},{"kind":"card","id":"linear","label":"Linear (Wᴼ)","detail":"Output: d = 512"}]},"edges":[{"from":"inputs","to":"h1"},{"from":"inputs","to":"h5"},{"from":"inputs","to":"hrest"},{"from":"h1","to":"concat"},{"from":"h5","to":"concat"},{"from":"hrest","to":"concat"},{"from":"concat","to":"linear"}]},{"id":"stack","heading":"Level 3: Full Transformer Architecture (Encoder-Decoder)","tone":"peach","body":{"kind":"group","arrange":"row","children":[{"kind":"group","arrange":"column","children":[{"kind":"card","id":"kv","label":"Encoder Keys & Values"},{"kind":"group","heading":"ENCODER","repeat":"(N = 6)","arrange":"column","tone":"blue","children":[{"kind":"card","id":"effn","label":"Feed Forward Network"},{"kind":"card","id":"mhsa","label":"Multi-Head Self-Attention","detail":"All tokens attend mutually","tone":"blue"},{"kind":"card","id":"ein","label":"Input + Positional Encoding"},{"kind":"card","id":"src","label":"Source: \\"The Law will never...\\"","tone":"muted","plain":true}]}]},{"kind":"group","arrange":"column","children":[{"kind":"card","id":"lsm","label":"Linear + Softmax"},{"kind":"group","heading":"DECODER","repeat":"(N = 6)","arrange":"column","tone":"peach","children":[{"kind":"card","id":"dffn","label":"Feed Forward Network"},{"kind":"card","id":"cross","label":"Cross-Attention (Enc-Dec)","detail":"Q from Dec, K & V from Enc","tone":"green"},{"kind":"card","id":"masked","label":"Masked Self-Attention","detail":"Prevents looking ahead","tone":"peach"},{"kind":"card","id":"tgt","label":"Target Tokens (Shifted Right)"}]}]}]},"notes":["Constant O(1) sequential operations across tokens; recurrence and convolutions are entirely absent."],"edges":[{"from":"ein","to":"mhsa"},{"from":"mhsa","to":"effn"},{"from":"mhsa","to":"kv"},{"from":"tgt","to":"masked"},{"from":"masked","to":"cross"},{"from":"cross","to":"dffn"},{"from":"dffn","to":"lsm"},{"from":"kv","to":"cross"}]}]}'
VARIETY_EXAMPLE = '{"title":"Attention as a worked example","subtitle":"One query scores three keys, the scores become weights, and the weights mix the values.","footer":"Values are illustrative. Real d_k = 64 and h = 8; the masked grid shows decoder self-attention.","illustrative":true,"layout":"columns","panels":[{"id":"score","heading":"1. Score and weight","tone":"blue","body":{"kind":"group","arrange":"column","children":[{"kind":"sequence","items":[{"text":"The","sub":"k1"},{"text":"Law","sub":"k2"},{"text":"its","sub":"q","tone":"green","hot":true}]},{"kind":"steps","lines":["scores q·k = [3.0, 1.0, 0.4]","scale ÷ √d_k = ÷ 2 → [1.5, 0.5, 0.2]","softmax → [0.62, 0.23, 0.15]"]},{"kind":"sequence","items":[{"text":"0.62","sub":"→ Law","tone":"green","hot":true},{"text":"0.23","sub":"→ The"},{"text":"0.15","sub":"→ its"}]},{"kind":"note","lines":["Weights sum to 1","The output stays inside the value vectors"]}]}},{"id":"mask","heading":"2. Masked decoder grid","tone":"peach","body":{"kind":"group","arrange":"column","children":[{"kind":"grid","col_labels":["y1","y2","y3"],"row_labels":["y1","y2","y3"],"rows":[["*1.0",null,null],["0.4","*0.6",null],["0.2","0.3","*0.5"]],"caption":"future positions set to −∞ before softmax"},{"kind":"card","id":"masked","label":"Masked Self-Attention","detail":"Prevents looking ahead","tone":"peach"},{"kind":"divider","label":"Threshold cutoff α = 0.10"},{"kind":"card","id":"disc","label":"Discarded: y4..y10 (< α)","detail":"Cuts noise from rare tails","tone":"peach","dashed":true,"plain":true}]}},{"id":"result","heading":"3. Result","tone":"green","body":{"kind":"group","arrange":"column","children":[{"kind":"bars","items":[["ConvS2S",25.2],["ByteNet",23.8],["Transformer (base)",27.3],["Transformer (big)",28.4]],"caption":"BLEU, WMT 2014 EN-DE"},{"kind":"card","id":"cost","label":"Training cost","detail":"3.5 days on 8 P100 GPUs, a fraction of the prior best models"},{"kind":"note","lines":["Sequential ops O(1)","Path length O(1)","Per-layer O(n²·d)"]}]}}]}'

SELECTION_INSTRUCTION = '''Choose the retained source material needed to explain this paper's
contribution, how it works, the supported finding, and its qualification, for a reader who knows
the paper's field but not this paper. Use the abstract to navigate, and select the smallest
sufficient set: a parent section includes every descendant, so prefer leaf sections or direct
passage IDs for isolated details. Include an appendix or figure when the contribution needs it.
Copy IDs exactly from the source map. Do not write the story or choose panel layouts yet.

Return one JSON object and nothing else:
{"paper_type": "architecture" or "method" or "survey" or "evaluation" or "theory" or "other",
 "focus": one sentence naming what the explanation must make understandable,
 "section_ids": [section IDs copied from the source map],
 "passage_ids": [individual passage IDs copied from the source map],
 "figure_ids": [figure or table IDs copied from the source map]}
Use an empty list for a field you do not need, and select at least one section, passage, or figure.'''

DIGEST_INSTRUCTION = r"""Extract what a reader must know to understand this paper's core from the retrieved
evidence. This is the first pass over the paper: the core content, not the methodology story,
related work, or every experiment. A reader who knows the field should be able to reconstruct the
paper's main idea from this object alone.

Return one JSON object:
{"paper_type": "architecture" | "method" | "survey" | "evaluation" | "theory" | "other",
 "contribution": {"text": one or two sentences, at most 400 characters, "passages": [exact IDs]},
 "result": {"text": the headline finding with its numbers, at most 400 characters, "passages": [exact IDs]},
 "qualification": {"text": the one caveat a reader needs to interpret the result, at most 400 characters, "passages": [exact IDs]},
 "example": one concrete running example with real values, one sentence, at most 240 characters (required for architecture and method papers),
 "hyperparameters": [up to 12 strings of at most 40 characters such as "d_model = 512", "h = 8", "N = 6"],
 "components": [{"id": short safe id, "name": 1-40 characters, "role": what it does, 1-160 characters,
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
nodes of its parts. A part shared by several components is drawn once, and those components
become cards. A leaf component becomes a card whose label is its name and whose detail is the
operation it computes or its values. Never draw containment as a stack of full-width cards joined
by arrows. Two or three sibling containers (an encoder stack beside a decoder stack, or the
families of a survey) go in a row; a pipeline of steps goes in a column.

Structure: 1 to 4 panels. Use "layout": "stack" for an architecture (panels one under another,
from the core operation to the full system) and "columns" for a method, survey, or evaluation
(panels side by side, in order). Each panel has a heading, one body node, optional notes (at most
2 lines under the body), and edges (arrows between cards in that panel, at most 12).

Node kinds, all with "kind":
- card: {"id"?, "label" ≤40, "detail"? ≤80 muted second line, "tone"? blue|green|peach|muted,
  "dashed"? true for a discarded or optional state, "plain"? true for a non-bold label}
- group: {"heading"? ≤40, "repeat"? such as "(N = 6)", "arrange": "row" | "column", "tone"?,
  "children": [1-8 nodes]}. A group with a heading draws a container; use it for containment
  (a layer holding its sub-layers). Groups nest at most 3 deep.
- note: {"lines": [1-4 strings ≤60]} a small text block; the first line is bold.
- sequence: {"items": [2-8 of {"id"?, "text" ≤14, "sub"? ≤16, "tone"?, "hot"? true}]} tokens,
  values, or steps in a row with an optional caption under each.
- grid: {"rows": [[cell]], "col_labels"? ≤16 each, "row_labels"? ≤16 each, "caption"? ≤60} a small
  matrix, at most 6×6; a cell is a number, a string ≤12, "*value" to highlight it, or null for a
  masked cell.
- steps: {"lines": [1-6 strings ≤60]} a numbered calculation; the last line is the result.
- bars: {"items": [2-8 of ["label" ≤24, number]], "caption"? ≤60} a comparison of values.
- divider: {"label"? ≤40} a dashed line, for a threshold or a boundary.
Edges: {"from": card id, "to": card id, "label"? ≤24, "accent"? true}. Arrows join cards of the
same panel only; use them for data flow, not for reading order.

Density is the goal: at most 24 nodes per panel, but use them, and use the width. A panel is 952
units wide; its body must span at least 40% of that, so arrange parts in rows, put sibling groups
side by side, and keep a single column for a short pipeline only. Put numbers in details, sequences,
grids, steps, and bars rather than in prose. Use tone for the one thing to notice per panel. Put
explanation in the subtitle and footer, not in cards. Title ≤80, subtitle ≤160, footer ≤240,
"illustrative": true when a shown value is a teaching value rather than a paper result.

Two complete examples of the object:
EXAMPLE_ARCHITECTURE
EXAMPLE_METHOD

Return one JSON object with title, subtitle, footer, illustrative, layout, and panels."""
SCENE_INSTRUCTION = SCENE_INSTRUCTION.replace('EXAMPLE_ARCHITECTURE', ATTENTION_EXAMPLE).replace('EXAMPLE_METHOD', VARIETY_EXAMPLE)

# Every prompt above asks for the same object twice; this is the protocol correction the next
# request carries when the first response cannot be used.
RETRY_SUFFIX = ('Return the same JSON object again with every field the instruction asks for. '
                'Copy the exact field names; do not add prose around the object.')


def _iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _read_json(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return {}


class RunStore:
    """The append-only event log and atomically updated run record for one generation run.

    ``events.jsonl`` is opened once per event and appended to, so a crash never loses completed
    requests. ``run.json`` identifies the run state. Response text is kept in separate files under
    ``requests/``, referenced by events, and never includes credentials or base64 image payloads.
    """

    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.events_path = self.directory / 'events.jsonl'
        self.requests_directory = self.directory / 'requests'
        self.requests_directory.mkdir(parents=True, exist_ok=True)
        if not self.events_path.exists():
            self.events_path.touch()
        if not (self.directory / 'run.json').exists():
            _write_json(self.directory / 'run.json',
                        {'status': 'running', 'created_at': _iso()})

    def read(self):
        return _read_json(self.directory / 'run.json')

    def update(self, **fields):
        record = self.read()
        record.update(fields)
        _write_json(self.directory / 'run.json', record)
        return record

    def append(self, event):
        line = json.dumps(event, ensure_ascii=False, separators=(',', ':'))
        with open(self.events_path, 'a', encoding='utf-8') as stream:
            stream.write(line + '\n')

    def _relative(self, path):
        return str(path.relative_to(self.directory))

    def write_response(self, ordinal, text):
        path = self.requests_directory / (f'{int(ordinal):04d}-response.txt')
        path.write_text(_BASE64_PAYLOAD.sub('[base64 image payload removed]', str(text or '')),
                        encoding='utf-8')
        return self._relative(path)

    def write_candidate(self, ordinal, suffix, value):
        path = self.requests_directory / (f'{int(ordinal):04d}-{suffix}.json')
        _write_json(path, value)
        return self._relative(path)


def create_run_directory(document):
    """Create the per-run artifact directory before the first request can fail."""
    directory = (Path(document['directory']) / 'reader' / 'overview-figures'
                 / uuid.uuid4().hex)
    RunStore(directory)
    return directory


def _is_cancelled(error):
    return isinstance(error, Cancelled) or type(error).__name__ == 'Cancelled'


def _finalize_run(store, error, *, stage):
    """Write a terminal run record without replacing the original exception.

    The inner coordinator owns the most specific failure stage. An outer lifecycle guard must not
    overwrite a terminal record after the original failure has already been diagnosed.
    """
    current = store.read()
    if current.get('status') in TERMINAL_RUN_STATES:
        return current
    status = 'cancelled' if _is_cancelled(error) else 'failed'
    fields = {'status': status, 'finished_at': _iso(),
              'failed_stage': stage or 'planning',
              'exception_type': type(error).__name__,
              'exception_message': str(error)[:2000],
              'exception': {'type': type(error).__name__, 'message': str(error)[:2000],
                            'stage': stage or 'planning'}}
    return store.update(**fields)


def panel_digest(value):
    """A stable digest of a plan, a narrative, or a source document."""
    text = value if isinstance(value, str) else json.dumps(value, sort_keys=True,
                                                           separators=(',', ':'), ensure_ascii=False)
    return hashlib.sha256(text.encode()).hexdigest()


def provider_options(settings, stage):
    """Endpoint options for one stage of this vendor.

    Every stage keeps the model's reasoning on. Gemini flash exposes only a level, so it stays at
    its fastest. DeepSeek turns thinking off for every stage only when ``overview_reasoning`` is
    False, the reader's choice of the fastest completion. ``stage`` is recorded with each request
    so a later policy can vary by stage again.
    """
    if not isinstance(settings, dict):
        return {}
    host = urlsplit(settings.get('endpoint') or '').hostname
    options = {}
    if host == 'generativelanguage.googleapis.com' and 'flash' in (settings.get('model') or ''):
        options['gemini_thinking_level'] = 'low'
    if host == 'api.deepseek.com' and not settings.get('overview_reasoning', True):
        options['deepseek_thinking'] = False
    return options


def is_transient(error):
    """A transport failure worth one retry; an authentication failure never is."""
    message = str(error)
    if 'authentication' in message.lower() or 'HTTP status 401' in message or 'HTTP status 403' in message:
        return False
    return any(marker in message for marker in TRANSIENT_MARKERS)


class Coordinator:
    """Owns the request trace, run delivery record, usage accounting, and cancellation checkpoints."""

    def __init__(self, provider, progress, *, run_directory=None):
        self.provider = provider
        self.progress = progress
        self.events = []
        self.requests = 0
        self.active_stage = 'planning'
        self.writer = None
        self.last_event = None
        self.run_directory = Path(run_directory) if run_directory else None
        self.store = RunStore(self.run_directory) if self.run_directory else None

    def _record(self, event):
        self.events.append(event)
        if self.store is not None:
            try:
                self.store.append(event)
            except OSError:
                pass

    def call_with_event(self, label, messages, *, stage=None, json_object=True, retries=1):
        """One structured request; returns the provider response and its persisted event."""
        options = provider_options(self.provider.settings, stage or label)
        self.active_stage = stage or label
        response = None
        event = None
        for attempt in range(retries + 1):
            self.requests += 1
            event = {'kind': 'model_request', 'label': label, 'request': self.requests,
                     'attempt': attempt + 1, 'stage': stage or label,
                     'model': self.provider.settings.get('model'),
                     'message_count': len(messages), 'input_chars': len(json.dumps(messages)),
                     'options': options, 'started_at': _iso(),
                     'response_file': None, 'response_chars': None, 'has_response': False,
                     'usage': None, 'normalized_candidate': None,
                     'validator_issue_paths': None, 'normalization_status': None}
            self.progress(label + ' · request ' + str(self.requests))
            started = time.monotonic()
            try:
                response = self.provider.complete(messages, json_object=json_object, **options)
            except ProviderError as error:
                event.update(status='failed', error=str(error)[:500],
                             error_type=type(error).__name__,
                             transient=is_transient(error), finished_at=_iso(),
                             elapsed_seconds=round(time.monotonic() - started, 3),
                             has_response=False, response_file=None, response_chars=None,
                             usage=None, normalized_candidate=None,
                             validator_issue_paths=None)
                self.last_event = event
                self._record(event)
                if attempt < retries and is_transient(error):
                    time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
                    continue
                raise
            raw_text = response.get('text', '') if isinstance(response, dict) else ''
            response_file = self.store.write_response(self.requests, raw_text) if self.store else None
            event.update(status='completed',
                         usage=(response.get('usage', {}) if isinstance(response, dict) else {}),
                         output_chars=len(raw_text), response_file=response_file,
                         response_chars=len(raw_text), has_response=True,
                         finished_at=_iso(),
                         elapsed_seconds=round(time.monotonic() - started, 3))
            self.last_event = event
            self._record(event)
            return response, event
        raise ProviderError('Provider request failed after one retry.')

    def call(self, label, messages, *, stage=None, json_object=True, retries=1):
        """Backwards-compatible response-only wrapper around :meth:`call_with_event`."""
        response, _event = self.call_with_event(label, messages, stage=stage,
                                                json_object=json_object, retries=retries)
        return response

    def record_normalization(self, event, *, status, candidate=None, normalized=_UNWRITTEN,
                             issue_paths=(), issues=()):
        """Persist the parsed or validated candidate apart from the raw response."""
        if not isinstance(event, dict):
            return {}
        ordinal = event.get('request')
        issue_paths = [str(path) for path in issue_paths if str(path).strip()]
        result = {'kind': 'model_request_result', 'request': ordinal,
                  'stage': event.get('stage'), 'label': event.get('label'), 'status': status,
                  'validator_issue_paths': issue_paths,
                  'issues': [str(issue)[:500] for issue in issues][:20], 'at': _iso(),
                  'candidate_file': None, 'normalized_candidate_file': None,
                  'normalized_candidate': None}
        if candidate is not None and self.store is not None:
            result['candidate_file'] = self.store.write_candidate(ordinal, 'candidate', candidate)
        if normalized is not _UNWRITTEN:
            result['normalized_candidate'] = normalized
            if self.store is not None:
                result['normalized_candidate_file'] = self.store.write_candidate(
                    ordinal, 'normalized', normalized)
        # Keep the in-memory request event inspectable by callers after normalization completes.
        event['normalization_status'] = status
        event['validator_issue_paths'] = issue_paths
        event['normalized_candidate'] = result['normalized_candidate']
        event['candidate_file'] = result['candidate_file']
        event['normalized_candidate_file'] = result['normalized_candidate_file']
        self._record(result)
        return result

    def note(self, name, **details):
        event = {'kind': 'local_operation', 'label': name, 'at': _iso(), **details}
        self._record(event)
        return event


def _validation_paths(error):
    """Exact validator issue paths from a PlanValidationError or PanelPlanError."""
    issues = getattr(error, 'issues', None)
    if not isinstance(issues, list):
        return []
    paths = []
    for issue in issues:
        if isinstance(issue, dict) and issue.get('path'):
            paths.append(str(issue['path']))
        elif isinstance(issue, str):
            paths.append(issue[:120])
    return list(dict.fromkeys(paths))


def _validation_messages(error):
    issues = getattr(error, 'issues', None)
    if not isinstance(issues, list):
        return [str(error)[:500]]
    return [str(issue.get('message') if isinstance(issue, dict) else issue)[:500]
            for issue in issues][:20]


def _request_object(coordinator, label, messages, *, stage=None):
    """One request whose JSON body may be unusable; the caller decides how to recover.

    Returns the parsed value, the parsing problem, the persisted request event, and the raw
    response text so a correction can include the rejected answer as an assistant message.
    """
    response, event = coordinator.call_with_event(label, messages, stage=stage)
    raw_text = response.get('text', '') if isinstance(response, dict) else ''
    try:
        return parse_json(raw_text), None, event, raw_text
    except (KeyError, ValueError, TypeError) as error:
        return None, 'the response was not the required JSON object: ' + (str(error)[:300] or 'invalid JSON'), event, raw_text


def _request_validated(coordinator, label, messages, validate, *, stage=None, attempts=2,
                       describe='JSON object'):
    """Request a JSON object and validate it, carrying the rejected answer into the correction."""
    correction = None
    previous_text = None
    last_reason = None
    for _ in range(attempts):
        payload = messages if correction is None else messages + [
            *([{'role': 'assistant', 'content': previous_text}] if previous_text is not None else []),
            {'role': 'user', 'content': correction},
        ]
        request_label = label if correction is None else label + '_correction'
        value, problem, event, raw_text = _request_object(coordinator, request_label, payload, stage=stage)
        if problem is not None:
            coordinator.record_normalization(event, status='unparseable',
                                             issue_paths=['response.text'], issues=[problem])
            previous_text = raw_text
            last_reason = problem
            correction = ('The previous ' + label + ' response was rejected: ' + problem + ' '
                          + RETRY_SUFFIX)
            continue
        try:
            validated = validate(value)
        except ValueError as error:
            paths = _validation_paths(error)
            coordinator.record_normalization(event, status='rejected', candidate=value,
                                             issue_paths=paths,
                                             issues=_validation_messages(error))
            previous_text = raw_text
            last_reason = str(error)
            paths_text = ', '.join(paths[:8]) if paths else 'the unstated field'
            correction = ('The previous ' + label + ' response was rejected at these exact issue '
                          'paths: ' + paths_text + '. ' + str(error)[:360]
                          + ' Return the corrected complete ' + describe
                          + ' Preserve every valid claim, citation, passage, and relationship that '
                            'already passed; change only what the issue paths require.')
            continue
        coordinator.record_normalization(event, status='validated', candidate=value,
                                         normalized=validated)
        return value, validated
    reason = ' '.join(str(last_reason or correction or '').split())[:300]
    raise ProviderError('The provider did not return a valid ' + describe + ' for ' + label
                        + (': ' + reason if reason else '.'))


def _evidence_text(evidence):
    return _evidence(evidence.get('passages', []))


def _source_map(orientation):
    """Send the complete compact map when it fits; otherwise expose explicit paging."""
    total = len(orientation['sections']) + len(orientation['figures'])
    complete = orientation_page(orientation, 0, max(1, min(total, 200)))
    if total <= 200 and len(json.dumps(complete, ensure_ascii=False)) <= 24_000:
        return complete
    limit = min(50, max(1, total))
    page = orientation_page(orientation, 0, limit)
    while limit > 1 and len(json.dumps(page, ensure_ascii=False)) > 16_000:
        limit = max(1, limit // 2)
        page = orientation_page(orientation, 0, limit)
    page['diagnostic'] = ('The complete source map exceeds the initial request budget. Select the '
                          'sections and passages you need from this page; no entries were discarded locally.')
    return page


def _merge_evidence(current, new, document):
    """Order retrieved passages by their position in the retained paper and merge coverage."""
    order = {item['id']: index for index, item in enumerate(evidence_document(document).get('passages', []))}
    passages = {item['id']: item for item in current.get('passages', [])}
    passages.update({item['id']: item for item in new.get('passages', [])})
    images = {item['digest']: item for item in current.get('images', [])}
    images.update({item['digest']: item for item in new.get('images', [])})
    coverage = copy.deepcopy(current.get('coverage', {}))
    for key, value in new.get('coverage', {}).items():
        if isinstance(value, list):
            combined = [*coverage.get(key, []), *value]
            seen, unique = set(), []
            for item in combined:
                identity = json.dumps(item, sort_keys=True, ensure_ascii=False)
                if identity not in seen:
                    seen.add(identity)
                    unique.append(item)
            coverage[key] = unique
        else:
            coverage[key] = value
    return {'document_digest': new['document_digest'],
            'passages': sorted(passages.values(), key=lambda item: order.get(item['id'], len(order))),
            'images': list(images.values()), 'coverage': coverage}


def select_evidence(coordinator, document, orientation, *, vision):
    """One validated selection request, then local retrieval. Selection is counted separately."""
    messages = [{'role': 'user', 'content': SELECTION_INSTRUCTION + '\n\nSOURCE MAP:\n'
                 + json.dumps(_source_map(orientation), ensure_ascii=False)}]
    _, selection = _request_validated(coordinator, 'selection', messages,
                                      lambda value: validate_selection(value, orientation),
                                      stage='selection', describe='selection object')
    added = retrieve_evidence(document, orientation, selection, vision=vision)
    evidence = _merge_evidence({'passages': [], 'images': [], 'coverage': {}}, added, document)
    coordinator.note('retrieval', requested_passage_ids=selection['passage_ids'],
                     retrieved_passage_ids=[item['id'] for item in evidence['passages']])
    return selection, evidence


def supplement_evidence(coordinator, document, orientation, selection, evidence, request, *, vision):
    """Load one validated supplemental selection requested by a planner response.

    A request that names handles the source map does not contain is not a provider failure: the
    run keeps its existing evidence, records the unresolved request, and continues. The original
    evidence object is returned unchanged so callers can tell that nothing was added.
    """
    if not isinstance(request, dict):
        return evidence
    chosen = {'paper_type': selection['paper_type'], 'focus': selection['focus'],
              'section_ids': request.get('section_ids') or [],
              'passage_ids': request.get('passage_ids') or [],
              'figure_ids': request.get('figure_ids') or []}
    if not any(chosen[field] for field in ('section_ids', 'passage_ids', 'figure_ids')):
        return evidence
    try:
        chosen = validate_selection(chosen, orientation)
    except ValueError as error:
        coordinator.note('evidence_supplement_unresolved', request=request,
                         reason=str(error)[:400])
        return evidence
    merged = _merge_evidence(evidence, retrieve_evidence(document, orientation, chosen, vision=vision),
                             document)
    coordinator.note('evidence_supplement', requested_passage_ids=chosen['passage_ids'],
                     retrieved_passage_ids=[item['id'] for item in merged['passages']])
    return merged


def plan_digest(coordinator, evidence):
    """One validated digest request; the correction carries the rejected answer as assistant."""
    messages = [{'role': 'user', 'content': DIGEST_INSTRUCTION + '\n\n<retrieved_evidence>\n'
                 + _evidence_text(evidence) + '\n</retrieved_evidence>'}]
    _, digest = _request_validated(coordinator, 'digest', messages,
                                   lambda value: validate_digest(value, evidence),
                                   stage='digest', attempts=3, describe='digest object')
    coordinator.note('digest_accepted', components=len(digest['components']), paper_type=digest['paper_type'])
    return digest


def plan_scene(coordinator, digest, directory, paper_title):
    """A validated, covering, laid-out scene in at most three requests.

    Validation and digest coverage are checked inside the request loop. A scene that validates
    but cannot be laid out, or that renders too sparse, gets one more correction with the reason.
    """
    messages = [{'role': 'user', 'content': SCENE_INSTRUCTION + '\n\n<digest>\n'
                 + json.dumps(digest, ensure_ascii=False) + '\n</digest>'}]

    def validate(value):
        scene = validate_scene(value)
        issues = scene_coverage_issues(digest, scene_text(scene), scene_headings(scene))
        if issues:
            raise PanelPlanError(issues[:20])
        return scene

    raw, scene = _request_validated(coordinator, 'scene', messages, validate, stage='scene',
                                    attempts=3, describe='scene object')
    for attempt in range(2):
        try:
            composed, placements = compose_scene(directory, paper_title, scene)
        except SceneLayoutError as error:
            problem = str(error)
        else:
            narrow = [placement for placement in placements if placement['fill'] < MIN_PANEL_FILL]
            if not narrow:
                return scene, composed, placements
            problem = ('; '.join('panel ' + item['id'] + ' uses ' + str(round(item['fill'] * 100))
                                 + '% of its width' for item in narrow)
                       + '. Each panel is ' + str(int(MIN_PANEL_FILL * 100)) + '% or more of its width '
                       'when its body is a row, or a column of rows, or two groups side by side; a '
                       'single narrow column wastes the panel.')
            coordinator.note('scene_narrow', panels=[item['id'] for item in narrow])
        if attempt:
            break
        correction = ('The previous scene laid out with a problem: ' + problem + ' Rearrange the '
                      'affected panels (put connected cards in one row or one column, put sibling '
                      'groups side by side, or drop an arrow that cannot pass). Return the complete '
                      'corrected scene object. ' + RETRY_SUFFIX)
        raw, scene = _request_validated(coordinator, 'scene_layout', messages + [
            {'role': 'assistant', 'content': json.dumps(raw, ensure_ascii=False)},
            {'role': 'user', 'content': correction}], validate, stage='scene', describe='scene object')
    raise ProviderError('The scene could not be laid out: ' + problem)


def plan_overview(provider, document, progress, *, vision=False, run_directory=None):
    """Select evidence and extract the digest. Returns the digest with its evidence and events."""
    if not document.get('passages'):
        raise ProviderError(document.get('report', {}).get('text_warning')
                            or 'This paper has no retained passages for an overview.')
    if not document.get('directory'):
        raise ProviderError('Save the paper before generating an overview.')
    if run_directory is None:
        run_directory = create_run_directory(document)
    else:
        run_directory = Path(run_directory)
        RunStore(run_directory)
    coordinator = Coordinator(provider, progress, run_directory=run_directory)
    try:
        orientation = build_orientation(document)
        selection, evidence = select_evidence(coordinator, document, orientation, vision=vision)
        digest = plan_digest(coordinator, evidence)
        return {'digest': digest, 'evidence': evidence, 'selection': selection,
                'orientation': orientation, 'coordinator': coordinator}
    except BaseException as error:
        try:
            _finalize_run(coordinator.store, error, stage=coordinator.active_stage)
        except Exception:
            # Diagnostic writing must never replace the original exception.
            pass
        raise


def _write_json(path, value):
    """Atomic replacement: a reader or a later run never sees a half-written common file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=str(path.parent), suffix='.json')
    try:
        with os.fdopen(handle, 'w') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def text_density(checks):
    """Visible text runs per million square units of the composed image."""
    canvas = checks.get('canvas') or {}
    area = float(canvas.get('width') or 0) * float(canvas.get('height') or 0)
    return len(checks.get('text_runs') or []) / (area / 1e6) if area else 0.0


def generate(provider, document, progress, *, vision=False):
    """Run the complete overview: select, digest, scene, layout, render.

    One run directory owns every request and the terminal delivery record. A failed run never
    publishes a replacement overview.
    """
    if not document.get('passages'):
        raise ProviderError(document.get('report', {}).get('text_warning')
                            or 'This paper has no retained passages for an overview.')
    if not document.get('directory'):
        raise ProviderError('Save the paper before generating an overview.')
    run = create_run_directory(document)
    store = RunStore(run)
    state = {'stage': 'planning'}
    try:
        plan = plan_overview(provider, document, progress, vision=vision, run_directory=run)
        digest, evidence, coordinator = plan['digest'], plan['evidence'], plan['coordinator']
        _write_json(run / 'digest.json', digest)
        state['stage'] = 'scene'
        store.update(stage='scene')
        progress('Composing the figure')
        scene, composed, placements = plan_scene(coordinator, digest, run, document.get('title', ''))
        _write_json(run / 'scene.json', scene)
        (run / 'overview.source.svg').write_text(composed)
        _write_json(run / 'placements.json', placements)
        state['stage'] = 'rendering'
        store.update(stage='rendering')
        figure = {'id': 'fig1', 'title': scene['title'], 'paper_connection': scene['subtitle'],
                  'caption': scene['footer'], 'illustrative': scene['illustrative'],
                  'passages': digest_passages(digest), 'source_svg': composed}
        settings = getattr(provider, 'settings', {}) or {}
        assets = html_figures.render(document['directory'], figure, document.get('title', ''), mode='overview')
        checks = assets.pop('checks')
        _write_json(run / 'composition-checks.json', checks)
        issues = [str(issue.get('message') or issue.get('code')) for issue in checks.get('issue_details') or []]
        density = text_density(checks)
        if density < MIN_TEXT_DENSITY:
            issues.append('The figure is too sparse: ' + str(round(density, 1)) + ' text runs per million '
                          'square units; the floor is ' + str(MIN_TEXT_DENSITY))
        if issues:
            try:
                store.append({'kind': 'local_operation', 'label': 'composition_rejected', 'at': _iso(),
                              'issues': issues[:8]})
            except OSError:
                pass
            raise ProviderError('The assembled overview image failed its local checks: ' + '; '.join(issues[:3]))
        stored_source = (Path(document['directory']) / assets['svg_source']).read_text()
        headings = {panel['id']: panel['heading'] for panel in scene['panels']}
        figure.update(assets, checks=checks, dimensions=checks['canvas'],
                      panels=[{'id': placement['id'], 'title': headings.get(placement['id'], ''),
                               **{key: placement['frame'][key] for key in ('x', 'y', 'width', 'height')},
                               'text': ''}
                              for placement in placements])
        explanation = {'paper_type': digest['paper_type'],
                       'contribution': digest['contribution']['text'],
                       'finding': digest['result']['text'],
                       'qualification': digest['qualification']['text'],
                       'passages': digest_passages(digest)}
        events = coordinator.events
        store.update(status='completed', stage='completed', delivery='completed', finished_at=_iso(),
                     panels=len(scene['panels']), density=round(density, 1))
        return {'text': '{{figure:fig1}}', 'explanation': explanation, 'plan': digest, 'cited_text': '',
                'figures': [figure], 'evidence': evidence['passages'],
                'provenance': {
                    'model': settings.get('model'), 'document_digest': document_digest_of(document),
                    'source_digest': document.get('source_digest'), 'arxiv_id': document.get('arxiv_id'),
                    'evidence_format': document.get('format', 'epub'),
                    'pdf_digest': document.get('pdf_digest'),
                    'passages': [item['id'] for item in evidence['passages']],
                    'prompt_revision': PROMPT_REVISION,
                    'svg_profile_revision': html_figures.PANEL_SVG_PROFILE_REVISION,
                    'workflow': PANEL_WORKFLOW,
                    'narrative_digest': panel_digest(digest),
                    'scene_digest': panel_digest(scene),
                    'figure_digests': {figure['id']: panel_digest(stored_source)},
                    'reading': dict(evidence.get('coverage') or {}, revision=READING_REVISION),
                    'selection': plan['selection'],
                    'usage': [event for event in events if event.get('usage')],
                    'events': events,
                    'checks': {'density': round(density, 1), 'panels': len(scene['panels']),
                               'components': len(digest['components'])},
                    'reviews': [],
                    'created_at': _iso(),
                    'run': str(run.relative_to(Path(document['directory']))),
                }}
    except BaseException as error:
        try:
            _finalize_run(store, error, stage=state['stage'])
        except Exception:
            # Diagnostic writing must never replace the original exception.
            pass
        raise


def document_digest_of(document):
    from papers.library import document_digest
    return document_digest(document)
