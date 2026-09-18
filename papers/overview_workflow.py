"""Overview coordinator: evidence, planning, parallel panel dispatch, and completion.

The generation result contract below is what ``Application.execute`` saves and what the
reader, exports, and Blog reference admission consume. It is deliberately small and flat.
"""
from __future__ import annotations

import base64
import copy
import datetime
import hashlib
import json
import os
import re
import tempfile
import time
import uuid
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path
from urllib.parse import urlsplit

from papers import html_figures
from papers.ai import Provider, ProviderError, _evidence
from papers.arrangement import FIT_TOLERANCE, arrange, fit_layout, panel_record, shrink_fit_layout
from papers.convert import Cancelled
from papers.edge_align import align_outer_edges, edge_align_layout
from papers.explanation import (CLAIMS, OVERVIEW_CANDIDATE_MAX_BYTES, OVERVIEW_MAX_PANELS,
                                PanelPlanError, PlanValidationError, panel_assignments,
                                recover_overview_narrative, validate_overview_narrative,
                                validate_overview_plan, validate_selection)
from papers.overview import parse_json
from papers.panel_authoring import check_panel, panel_defects, request_panel
from papers.mixed_fit import mixed_fit_layout
from papers.reading import (REVISION as READING_REVISION, build_orientation, evidence_document,
                            orientation_page, retrieve_evidence)

# Serialized keys of the generation dictionary. Later stages must satisfy these exactly;
# tests/test_exports.py and tests/test_app.py assert this list so a rebuild cannot silently
# drop a key an older saved artifact or a caller still reads.
GENERATION_KEYS = ('text', 'explanation', 'plan', 'cited_text', 'figures', 'evidence', 'provenance')
PROVENANCE_KEYS = ('model', 'document_digest', 'passages', 'prompt_revision', 'svg_profile_revision',
                   'reading', 'usage', 'reviews', 'created_at')
FIGURE_ASSET_KEYS = ('html', 'svg', 'png', 'pdf', 'svg_source')

PROMPT_REVISION = 'overview-stacked-v1'
# Provenance marker for artifacts produced by this workflow. Blog reference admission accepts
# these as drawing references only, and never as a scientific review.
PANEL_WORKFLOW = 'panel-workflow-v1'
MAX_PANELS = OVERVIEW_MAX_PANELS
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

NARRATIVE_INSTRUCTION = r'''Plan what the reader will learn before any panel is drawn. Identify the
central contribution, the mechanism or comparison that makes it work, the supported finding, and the
qualification needed to interpret it. Write visual_focus as at most four ordered teaching steps,
one short line each, including the shared concrete example and its exact values when the paper is
a mechanism or method. Name the recurring objects once so every panel uses the same names. Ground
every claim and each stated relationship in retrieved passages. Keep secondary findings out of the
teaching steps; the qualification field holds what the reader needs to interpret the finding.
Keep every text field at or under 1200 characters.

Fit the story to the paper:
- architecture: name the proposed architecture and its purpose, give each selected module a local
  story with a concrete input, what changes, and the resulting output, then connect them.
- method: carry one example through the actual computation and explain each quantity before its arithmetic.
- survey: state the organising question, illustrate representative approaches through their
  principles, compare their priorities or tradeoffs, and close with the survey's synthesis.
- evaluation: keep the compared methods, conditions, and actual findings.
- theory: make the assumptions, reasoning, and established result understandable.

Write every equation in plain readable notation that SVG text can show, using Unicode symbols
(Σ ≥ ≤ √ · × → α) and ASCII subscripts, never LaTeX such as \sum, \frac, \mathbf or \log: write
"PRO(x) = -log p*_K - Σ(i=1..K) p*_i log(p*_i / p*_K)". There is no math renderer.

Return one JSON object with exactly these fields:
{"paper_type": "architecture" or "method" or "survey" or "evaluation" or "theory" or "other",
 "visual_focus": one string holding the ordered teaching steps, never a list or an object,
 "question": {"text": one string, "passages": [exact IDs]},
 "contribution": {"text": one string, "passages": [exact IDs]},
 "finding": {"text": one string, "passages": [exact IDs]},
 "limitation": {"text": one string, "passages": [exact IDs]},
 "relationships": [{"source": one string, "target": one string, "relationship": one string,
                    "passages": [exact IDs]}]}
Every field in that object is required. Write one string wherever this contract shows a string.
If you need more retained evidence, add "request_evidence": {"section_ids": [], "passage_ids": [],
"figure_ids": []} and nothing else changes.'''

OVERVIEW_PLAN_INSTRUCTION = r"""Turn the accepted narrative into one figure of stacked panels that a
reader follows from top to bottom. Use three panels. Use a fourth only when the story cannot be
told in three, and never more. Each panel shows one idea with a few labelled objects and the
relations between them. The reader sees every panel at the same width, one under the other, with
its heading above it, the title and subtitle above the figure, and the footer below it.

Return one JSON object:
{"title": figure title, 1-80 characters,
 "subtitle": one sentence on what the figure shows, 1-160 characters,
 "footer": one sentence of qualification the reader needs, 1-240 characters,
 "illustrative": true when a label carries a teaching value that is not a paper result, else false,
 "panels": [{"id": short safe id,
   "heading": 1-60 characters,
   "construction": "flow" | "mapping" | "comparison" | "calculation" | "chart",
   "purpose": the one idea this panel shows, 1-200 characters,
   "labels": [2-12 strings, each 1-48 characters: the exact names, values with units, equations,
     and step names the drawing shows, in reading order],
   "relations": [{"from": a label, "to": a label, "label": optional, 1-24 characters}], at most 8,
   "note": optional, 1-120 characters, one line of muted context beside the drawing,
   "passages": [retained passage IDs that support this panel]}]}

Labels are the whole text of the drawing. Write each one as it should appear, for example
"Query Q", "d_model = 512", "softmax(QKᵀ/√d_k)V", "Encoder (N = 6)". A label is never a sentence.
Do not add a label the drawing does not need. Relations name what connects to what; the drawing
shows them as arrows or alignment. Put explanation in the subtitle and the footer, not in the
panels. When the paper is a mechanism or method, carry one concrete example through the panels and
keep the same name for the same object in every panel. Ground every panel in retrieved passages.

Id rules: start with a letter, then letters, digits, dashes or underscores, at most 32 characters
(for example attention, heads, p3).

Equation rules: write every equation in plain readable notation that SVG text can show, using
Unicode symbols (Σ ≥ ≤ √ · × → α) and ASCII subscripts. Write "PRO(x) = -log p*_K - Σ(i=1..K) p*_i
log(p*_i / p*_K)", never LaTeX such as \sum, \frac, \mathbf or \log. There is no math renderer."""

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


def panel_transcript(assignment):
    """The accepted assignment text a reader can read beside the image."""
    parts = [assignment.get('purpose'), *assignment.get('labels', []), assignment.get('note')]
    return ' '.join(dict.fromkeys(part for part in parts if isinstance(part, str) and part.strip()))


def provider_options(settings, stage):
    """Endpoint options the existing provider path already used for this vendor and stage.

    ``overview_reasoning`` is False when the reader wants the fastest completion: DeepSeek runs
    every stage with thinking disabled. Otherwise planning keeps thinking and drawing turns it off
    under the existing latency/cost policy. This is not evidence that reasoning cannot improve
    drawing quality. A provider without a real settings mapping receives no vendor-specific options.
    """
    if not isinstance(settings, dict):
        return {}
    host = urlsplit(settings.get('endpoint') or '').hostname
    options = {}
    reasoning = settings.get('overview_reasoning', True)
    if host == 'generativelanguage.googleapis.com' and 'flash' in (settings.get('model') or ''):
        # Gemini exposes only a level, not an on/off switch, so it stays at its fastest level.
        options['gemini_thinking_level'] = 'low'
    if host == 'api.deepseek.com':
        if not reasoning:
            options['deepseek_thinking'] = False
        elif stage in ('panel', 'panel_repair'):
            options['reasoning_effort'] = 'low'
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


def _panel_context(narrative, evidence):
    return ('\n\n<accepted_narrative>\n' + json.dumps(narrative, ensure_ascii=False)
            + '\n</accepted_narrative>\n\n<retrieved_evidence>\n' + _evidence_text(evidence)
            + '\n</retrieved_evidence>')


def _narrative_correction(error):
    paths = _validation_paths(error)
    lines = ['The previous narrative response was rejected at these exact issue paths:',
             *(['- ' + path for path in paths[:12]] or ['- (the validator reported no path)'])]
    lines.append('Return the complete corrected narrative JSON object. Preserve every valid claim, '
                 'citation, passage ID, and relationship the previous answer already had; change '
                 'only what the issue paths require.')
    return '\n'.join(lines) + '\n' + RETRY_SUFFIX


def _narrative(coordinator, document, evidence, *, draft_text=None):
    """Up to two narrative requests; the correction carries the rejected answer as assistant.

    Both parsed candidates are saved independently. If the second answer is rejected too, a
    candidate whose four claims are valid and source-linked may be recovered by preserving its
    focus (deriving one only if invalid) and dropping only invalid optional relationships.
    """
    messages = [{'role': 'user', 'content': NARRATIVE_INSTRUCTION + '\n\n<retrieved_evidence>\n'
                 + _evidence_text(evidence) + '\n</retrieved_evidence>'}]
    if draft_text is not None:
        messages.append({'role': 'assistant', 'content': draft_text})
        messages.append({'role': 'user', 'content':
                         'New retained evidence has been added. Return the complete revised narrative '
                         'JSON object using the same contract; keep every valid claim and passage ID.'})
    correction = None
    latest_text = None
    last_reason = None
    candidates = []
    for attempt in range(2):
        payload = messages if correction is None else messages + [
            {'role': 'assistant', 'content': latest_text or ''},
            {'role': 'user', 'content': correction},
        ]
        request_label = 'narrative' if correction is None else 'narrative_correction'
        value, problem, event, raw_text = _request_object(coordinator, request_label, payload,
                                                           stage='narrative')
        if problem is not None:
            coordinator.record_normalization(event, status='unparseable',
                                             issue_paths=['response.text'], issues=[problem])
            candidates.append({'value': None, 'issue_paths': ['response.text'],
                               'issues': [problem], 'raw_text': raw_text})
            latest_text = raw_text
            last_reason = problem
            correction = ('The previous narrative response was rejected: ' + problem + ' '
                          + RETRY_SUFFIX)
            continue
        request = value.get('request_evidence') if isinstance(value, dict) else None
        focus_value = value.get('visual_focus') if isinstance(value, dict) else None
        if isinstance(focus_value, list) and all(isinstance(step, str) for step in focus_value):
            coordinator.note('visual_focus_joined', steps=len(focus_value))
        try:
            normalized = validate_overview_narrative(value, document)
        except PlanValidationError as error:
            paths = _validation_paths(error)
            issues = _validation_messages(error)
            coordinator.record_normalization(event, status='rejected', candidate=value,
                                             issue_paths=paths, issues=issues)
            candidates.append({'value': copy.deepcopy(value), 'issue_paths': paths,
                               'issues': issues, 'raw_text': raw_text})
            latest_text = raw_text
            last_reason = str(error)
            correction = _narrative_correction(error)
            continue
        coordinator.record_normalization(event, status='validated', candidate=value,
                                         normalized=normalized)
        return {'narrative': normalized, 'request_evidence': request, 'candidates': candidates,
                'raw_text': raw_text, 'recovered': False, 'discarded_relationships': [],
                'recovery_reason': None}
    # Prefer a fully valid candidate, which would already have been returned above. Recovery is
    # limited to complete, source-linked claims and never borrows a field from another candidate.
    parsed = [item['value'] for item in candidates if item.get('value') is not None]
    recovered = recover_overview_narrative(parsed, document)
    if recovered:
        meta = recovered.pop('_recovery', {}) or {}
        discarded = meta.get('discarded_relationships') or []
        focus_source = meta['focus_source']
        reason = ('the corrected narrative still failed validation; recovered the claims, '
                  + ('preserved the existing visual focus' if focus_source == 'visual_focus'
                     else 'derived the focus from the existing contribution')
                  + ' and discarded invalid optional relationships')
        coordinator.note('narrative_recovered', discarded_relationships=discarded,
                         reason=reason, candidates=len(parsed), focus_source=focus_source)
        return {'narrative': recovered, 'request_evidence': None, 'candidates': candidates,
                'raw_text': None, 'recovered': True, 'discarded_relationships': discarded,
                'recovery_reason': reason}
    reason = ' '.join(str(last_reason or correction or '').split())[:300]
    raise ProviderError('The provider did not return a valid narrative plan for narrative'
                        + (': ' + reason if reason else '.'))


def plan_figure(coordinator, narrative, evidence):
    """One validated plan request; the correction carries the rejected answer as assistant."""
    messages = [{'role': 'user', 'content': OVERVIEW_PLAN_INSTRUCTION + _panel_context(narrative, evidence)}]
    _, plan = _request_validated(coordinator, 'overview_plan', messages,
                                 lambda value: validate_overview_plan(value, evidence),
                                 stage='overview_plan', describe='overview plan object')
    coordinator.note('plan_accepted', panels=len(plan['panels']),
                     labels=sum(len(panel['labels']) for panel in plan['panels']))
    return plan


def plan_overview(provider, document, progress, *, vision=False, run_directory=None):
    """Select evidence, plan the narrative, and plan the figure.

    ``generate`` creates the run directory before planning and passes it here; direct callers may
    omit it. A failure still leaves a terminal run record and every completed request diagnostic.
    """
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
    reductions = []
    try:
        orientation = build_orientation(document)
        selection, evidence = select_evidence(coordinator, document, orientation, vision=vision)
        first = _narrative(coordinator, document, evidence)
        narrative = first['narrative']
        if first['recovered']:
            reductions.append(first['recovery_reason'])
        if first['request_evidence']:
            before = evidence
            evidence = supplement_evidence(coordinator, document, orientation, selection, evidence,
                                           first['request_evidence'], vision=vision)
            coordinator.note('narrative_supplement', request=first['request_evidence'])
            if evidence is before:
                # The requested handles do not exist in this source map; the accepted narrative
                # stands and the unresolved request is disclosed instead of failing the run.
                reductions.append('supplemental narrative evidence could not be incorporated: the '
                                  'requested handles are not in the source map')
                coordinator.note('narrative_supplement_failed',
                                 error='request_evidence named handles the source map does not contain')
            else:
                try:
                    second = _narrative(coordinator, document, evidence, draft_text=first['raw_text'])
                except ProviderError as error:
                    # A complete, validated first answer exists; preserve it and disclose that the
                    # supplemental evidence could not be incorporated rather than inventing claims.
                    reductions.append('supplemental narrative evidence could not be incorporated: '
                                      + str(error)[:240])
                    coordinator.note('narrative_supplement_failed', error=str(error)[:500])
                else:
                    narrative = second['narrative']
                    if second['recovered']:
                        reductions.append(second['recovery_reason'])
                    if second['request_evidence']:
                        coordinator.note('narrative_evidence_request_unresolved',
                                         request=second['request_evidence'])
        panel_plan = plan_figure(coordinator, narrative, evidence)
        reductions = list(dict.fromkeys(reason for reason in reductions if reason))
        return {'narrative': narrative, 'panel_plan': panel_plan, 'evidence': evidence,
                'selection': selection, 'orientation': orientation, 'events': coordinator.events,
                'assignment_source': 'planner', 'remaining_issues': [],
                'planning_reduced': bool(reductions), 'planning_reduction_reasons': reductions}
    except BaseException as error:
        try:
            _finalize_run(coordinator.store, error, stage=coordinator.active_stage)
        except Exception:
            # Diagnostic writing must never replace the original exception.
            pass
        raise


# --- Panel authoring: parallel requests, local checks, one repair each --------------------------
PANEL_WORKERS = 3
CREATED, REPAIRED = 'created', 'repaired'
# One creation request and at most this many repairs per panel. A panel that still has defects
# fails the run with them; there is no application-drawn substitute.
MAX_REPAIRS = 2
REPAIR_IMAGE_LIMIT = 2_000_000


def default_panel_provider(provider, usage):
    """A provider instance for one worker: copied settings, usage callback bound to its own list."""
    factory = getattr(provider, 'with_usage', None)
    if callable(factory):
        return factory(usage.append)
    return Provider(provider.settings, getattr(provider, 'key', None), on_usage=usage.append)


def _author_once(provider, assignment, provider_factory, *, previous=None, issues=(), image=None):
    """One worker task: request a panel, retrying one explicitly transient transport failure.

    The worker never renders, writes shared artifacts, or raises: it returns the response, its
    usage, and its diagnostics for the coordinator to act on. The stage options are computed here
    from the worker's own settings, so the request that reaches the provider carries the
    configured drawing policy for initial creation or repair.
    """
    usage, requests = [], []
    worker = provider_factory(provider, usage)
    stage = 'panel_repair' if previous is not None or issues else 'panel'
    options = provider_options(worker.settings, stage)
    for attempt in (1, 2):
        started_at = time.monotonic()
        try:
            result = request_panel(worker, assignment, previous=previous, issues=issues, image=image,
                                   options=options)
        except Exception as error:   # a worker must never fail the coordinator thread
            result = {'source': None, 'error': str(error)[:500], 'error_kind': 'transport',
                      'usage': {}, 'diagnostics': {'panel_id': assignment['id'], 'repair': previous is not None,
                                                   'issues': [str(issue) for issue in issues]}}
        requests.append({'ordinal': attempt, 'stage': stage,
                         'repair': previous is not None, 'status': 'completed' if result['source'] else 'rejected',
                         'error': result['error'], 'error_kind': result['error_kind'], 'usage': result.get('usage') or {},
                         'options': options, 'requested_reasoning': stage == 'panel' and bool(options),
                         'started_at': round(started_at, 3), 'finished_at': round(time.monotonic(), 3),
                         'transport_retry': attempt > 1})
        if result['source'] is not None or result['error_kind'] != 'transport' or attempt == 2:
            break
        time.sleep(RETRY_BACKOFF_SECONDS)
    if not usage and requests[-1]['usage']:
        usage.append(requests[-1]['usage'])
    return {'source': result['source'], 'error': result['error'], 'error_kind': result['error_kind'],
            'diagnostics': result['diagnostics'], 'usage': usage, 'requests': requests}


def _repair_image(record, enabled):
    """A rendered PNG data URL for a repair request, when image input is configured."""
    if not enabled or not record.get('assets'):
        return None
    png = Path(record['assets'].get('png') or '')
    try:
        data = png.read_bytes() if png.is_file() else b''
    except OSError:
        return None
    if not data or len(data) > REPAIR_IMAGE_LIMIT:
        return None
    return 'data:image/png;base64,' + base64.b64encode(data).decode()


def _panel_paths(directory, identifier):
    target = Path(directory) / ('panel-' + identifier)
    target.mkdir(parents=True, exist_ok=True)
    return target


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


class PanelRun:
    """The coordinator-side bookkeeping for one panel: requests, checks, repair, outcome."""

    def __init__(self, assignment, directory, *, usage_callback=None, trace=None, store=None,
                 image_enabled=False):
        self.assignment = assignment
        self.id = assignment['id']
        self.directory = Path(directory)
        self.artifacts = _panel_paths(self.directory, self.id)
        self.usage_callback = usage_callback
        self.trace = trace
        self.store = store
        self.image_enabled = image_enabled
        self.usage = []
        self.attempts = 0
        self.repairs = 0
        self.record = None
        self.outcome = None
        self.issues = []

    def note(self, event):
        if self.trace is not None:
            with open(self.trace, 'a') as stream:
                stream.write(json.dumps(event, ensure_ascii=False) + '\n')
        if self.store is not None:
            try:
                self.store.append(event)
            except OSError:
                pass

    def record_usage(self, result, label):
        """Count each billed response exactly once, on the coordinator thread."""
        entries = [entry for entry in (result.get('usage') or [])]
        if not entries and result.get('requests'):
            entries = [item.get('usage') or {} for item in result['requests']]
        self.note({'kind': 'model_request', 'label': label, 'panel': self.id,
                   'attempt_count': len(result.get('requests') or []),
                   'attempts': [{'ordinal': item.get('ordinal'), 'stage': item.get('stage'),
                                 'repair': item.get('repair'), 'status': item.get('status'),
                                 'error_kind': item.get('error_kind'),
                                 'options': item.get('options') or {},
                                 'usage': item.get('usage') or {},
                                 'started_at': item.get('started_at'),
                                 'finished_at': item.get('finished_at'),
                                 'transport_retry': item.get('transport_retry')}
                                for item in result.get('requests') or []],
                   'usage': entries, 'at': _iso()})
        for item in result.get('requests') or []:
            self.attempts += 1
            if item.get('transport_retry'):
                self.note({'kind': 'local_operation', 'label': 'transport_retry', 'panel': self.id,
                           'at': _iso()})
        for entry in entries:
            self.usage.append(entry)
            if self.usage_callback:
                self.usage_callback(entry)

    def accept(self, checked, outcome):
        self.record = checked
        self.outcome = outcome
        self.issues = []
        source_path = self.artifacts / 'source.svg'
        source_path.write_text(checked['source'])
        _write_json(self.artifacts / 'checks.json', {'checks': checked['checks'],
                                                     'outcome': outcome, 'labels': checked['labels']})
        self.note({'kind': 'local_operation', 'label': 'panel_' + outcome, 'panel': self.id,
                   'at': _iso()})
        return self.record


def build_panels(provider, assignments, directory, progress, *, provider_factory=default_panel_provider,
                 trace=None, usage_callback=None, image_enabled=False, store=None):
    """Author every panel concurrently, checking and repairing on the coordinator thread.

    Returns the panels in plan order plus the request/usage trace. No worker renders, writes a
    common file, or invokes a persistence callback: workers only request, and the coordinator
    renders, checks, records usage, and decides on at most ``MAX_REPAIRS`` repairs per panel.
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    runs = {assignment['id']: PanelRun(assignment, directory, usage_callback=usage_callback,
                                       trace=trace, store=store, image_enabled=image_enabled)
            for assignment in assignments}
    events = []
    order = [assignment['id'] for assignment in assignments]
    failure = None
    with ThreadPoolExecutor(max_workers=max(1, min(PANEL_WORKERS, len(assignments)))) as pool:
        futures = {}

        def submit(run, *, previous=None, issues=(), image=None):
            future = pool.submit(_author_once, provider, run.assignment, provider_factory,
                                 previous=previous, issues=issues, image=image)
            futures[future] = run
            return future

        try:
            for identifier in order:
                submit(runs[identifier])
            while futures:
                done, _ = wait(list(futures), return_when=FIRST_COMPLETED)
                for future in done:
                    run = futures.pop(future)
                    result = future.result()
                    label = 'panel_repair' if run.attempts else 'panel'
                    run.record_usage(result, label)
                    progress('Drawing panel ' + str(order.index(run.id) + 1) + ' of ' + str(len(order)))
                    if result.get('source') is None:
                        if result.get('error_kind') in ('transport', 'authentication'):
                            failure = (run, result)
                            continue
                        if run.repairs < MAX_REPAIRS:
                            run.repairs += 1
                            submit(run, issues=[result.get('error') or 'the drawing was rejected'])
                        else:
                            run.issues = [result.get('error') or 'the drawing was rejected']
                        continue
                    checked, issues = _check(run, result['source'])
                    if not issues:
                        run.accept(checked, REPAIRED if run.repairs else CREATED)
                    elif run.repairs < MAX_REPAIRS:
                        run.repairs += 1
                        submit(run, previous=checked['source'], issues=issues,
                               image=_repair_image(checked, run.image_enabled))
                    else:
                        run.issues = issues
                if failure:
                    break
                progress(None)
        except BaseException:
            pool.shutdown(wait=True, cancel_futures=True)
            raise
        finally:
            for future, run in list(futures.items()):
                if not future.done():
                    continue
                try:
                    leftover = future.result()
                except BaseException:
                    continue
                if leftover.get('usage') or leftover.get('requests'):
                    run.record_usage(leftover, 'panel_repair' if run.attempts else 'panel')
    if failure:
        run, result = failure
        raise ProviderError('Panel ' + run.id + ' could not be drawn: ' + str(result.get('error'))[:300])
    panels = []
    for identifier in order:
        run = runs[identifier]
        if run.record is None:
            run.note({'kind': 'local_operation', 'label': 'panel_failed', 'panel': run.id,
                      'issues': run.issues[:6], 'at': _iso()})
            raise ProviderError('Panel ' + run.id + ' still had defects after ' + str(MAX_REPAIRS)
                                + ' repairs: ' + '; '.join(run.issues[:3]))
        run.note({'kind': 'local_operation', 'label': 'panel_result', 'panel': run.id,
                  'outcome': run.outcome, 'repairs': run.repairs, 'at': _iso()})
        panels.append({'id': identifier, 'source': run.record['source'], 'assets': run.record['assets'],
                       'checks': run.record['checks'], 'labels': run.record['labels'],
                       'outcome': run.outcome, 'usage': run.usage})
        events.append({'panel': identifier, 'outcome': run.outcome, 'repairs': run.repairs,
                       'usage': run.usage, 'attempts': run.attempts})
    return {'panels': panels, 'events': events, 'runs': runs}


def _check(run, source):
    """Render and check one returned drawing locally; never a model call."""
    checked = check_panel(source, run.directory, run.id)
    return checked, panel_defects(run.assignment, checked)


def _mixed_layout_choice(aligned, original):
    """Keep aligned working centres only when the accepted mixed geometry does not regress."""
    aligned_info = aligned.get('mixed') if isinstance(aligned, dict) else None
    original_info = original.get('mixed') if isinstance(original, dict) else None
    if not isinstance(original_info, dict) or original_info.get('validated') is not True:
        return aligned, 'aligned-only'
    if not isinstance(aligned_info, dict) or aligned_info.get('validated') is not True:
        return original, 'original-fallback'
    aligned_metrics = aligned_info.get('final_metrics') or {}
    original_metrics = original_info.get('final_metrics') or {}
    aligned_gap = ((aligned_metrics.get('gap') or {}).get('total'))
    original_gap = ((original_metrics.get('gap') or {}).get('total'))
    aligned_occupancy = ((aligned_metrics.get('occupancy') or {}).get('canvas'))
    original_occupancy = ((original_metrics.get('occupancy') or {}).get('canvas'))
    if all(value is not None for value in (aligned_gap, original_gap,
                                           aligned_occupancy, original_occupancy)) \
            and aligned_gap <= original_gap + FIT_TOLERANCE \
            and aligned_occupancy + FIT_TOLERANCE >= original_occupancy:
        return aligned, 'aligned-working-centres'
    return original, 'original-fallback'


def generate(provider, document, progress, *, vision=False):
    """Run the complete overview: plan, author panels concurrently, compose, and render.

    One run directory owns planning, drawing, composition, and the terminal delivery record. The
    directory is created before the first request can fail. ``plan_overview`` finalizes its own
    planning failures; any later failure or cancellation is finalized here without replacing the
    original exception. A failed run never publishes a replacement overview.
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
        state['stage'] = 'drawing'
        store.update(stage='drawing')
        narrative, panel_plan, evidence = plan['narrative'], plan['panel_plan'], plan['evidence']
        assignments = panel_assignments(panel_plan)
        _write_json(run / 'narrative.json', narrative)
        _write_json(run / 'panel-plan.json', panel_plan)
        _write_json(run / 'assignments.json', assignments)
        _write_json(run / 'plan-events.json', plan['events'])
        trace = run / 'panel-trace.jsonl'
        settings = getattr(provider, 'settings', {}) or {}
        built = build_panels(provider, assignments, run, progress, trace=trace, store=store,
                             image_enabled=bool(settings.get('overview_vision')))
        state['stage'] = 'composition'
        store.update(stage='composition')
        titles = {assignment['id']: assignment['heading'] for assignment in assignments}
        records = [panel_record(panel['id'], panel['source'], title=titles[panel['id']],
                                checks=panel.get('checks'))
                   for panel in built['panels']]
        checkpoint = fit_layout(records, arrange(records))
        shrink = shrink_fit_layout(records, checkpoint)
        aligned = align_outer_edges(records, checkpoint)
        aligned_mixed = mixed_fit_layout(records, checkpoint, shrink, working_layout=aligned)
        original_mixed = mixed_fit_layout(records, checkpoint, shrink)
        layout, layout_variant = _mixed_layout_choice(aligned_mixed, original_mixed)
        if isinstance(layout.get('mixed'), dict) and layout['mixed'].get('validated') is True:
            edge = edge_align_layout(records, layout)
            if isinstance(edge.get('edge_align'), dict) and edge['edge_align'].get('validated') is True:
                layout = edge
            else:
                layout['edge_align'] = {'algorithm': 'edge-align-v1', 'validated': False,
                                        'diagnostic': {'reason': 'edge pass retained mixed result'}}
        else:
            layout_variant = 'shrink-fallback'
        layout['layout_pipeline'] = {
            'algorithm': 'aligned-mixed-edge-v1', 'variant': layout_variant,
            'mixed_candidates': {'aligned': aligned_mixed.get('mixed', {}).get('validated') is True,
                                 'original': original_mixed.get('mixed', {}).get('validated') is True},
        }
        sources = {panel['id']: panel['source'] for panel in built['panels']}
        composed = html_figures.compose_figure(sources, layout)
        (run / 'overview.source.svg').write_text(composed)
        _write_json(run / 'arrangement.json', layout)
        _write_json(run / 'panel-calls.json', built['events'])
        outcomes = {'created': [panel['id'] for panel in built['panels'] if panel['outcome'] == CREATED],
                    'repaired': [panel['id'] for panel in built['panels'] if panel['outcome'] == REPAIRED]}
        figure = {'id': 'fig1', 'title': panel_plan['title'],
                  'paper_connection': panel_plan['subtitle'], 'caption': panel_plan['footer'],
                  'illustrative': panel_plan['illustrative'],
                  'passages': narrative_passages(narrative), 'source_svg': composed}
        state['stage'] = 'rendering'
        assets = html_figures.render(document['directory'], figure, document.get('title', ''), mode='overview')
        checks = assets.pop('checks')
        _write_json(run / 'composition-checks.json', checks)
        composition_issues = checks.get('issue_details') or []
        if composition_issues:
            state['stage'] = 'composition'
            messages = [str(issue.get('message') or issue.get('code'))
                        for issue in composition_issues if isinstance(issue, dict)]
            try:
                store.append({'kind': 'local_operation', 'label': 'composition_rejected',
                              'at': _iso(), 'issues': messages[:8]})
            except OSError:
                pass
            raise ProviderError('The assembled overview image failed its local geometry checks: '
                                + '; '.join(messages[:3]))
        stored_source = (Path(document['directory']) / assets['svg_source']).read_text()
        texts = {assignment['id']: panel_transcript(assignment) for assignment in assignments}
        claims = {name: narrative[name]['text'] for name in CLAIMS}
        figure.update(assets, checks=checks, dimensions=checks['canvas'],
                      panels=[{'id': placement['id'], 'title': titles[placement['id']],
                               **{key: placement.get('frame', placement)[key]
                                  for key in ('x', 'y', 'width', 'height')},
                               'text': texts.get(placement['id'], '')}
                              for placement in layout['placements']],
                      panel_outcomes=outcomes)
        explanation = {'paper_type': narrative['paper_type'], **claims,
                       'passages': narrative_passages(narrative)}
        store.update(status='completed', stage='completed', delivery='completed', finished_at=_iso(),
                     assignment_source=plan['assignment_source'],
                     planning_reduced=plan['planning_reduced'],
                     planning_reduction_reasons=plan['planning_reduction_reasons'],
                     panel_outcomes=outcomes, panels=len(built['panels']))
        return {'text': '{{figure:fig1}}', 'explanation': explanation, 'plan': narrative, 'cited_text': '',
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
                    'narrative_digest': panel_digest(narrative),
                    'plan_digest': panel_digest(panel_plan),
                    'figure_digests': {figure['id']: panel_digest(stored_source)},
                    'reading': dict(evidence.get('coverage') or {}, revision=READING_REVISION),
                    'selection': plan['selection'],
                    'assignment_source': plan['assignment_source'],
                    'planning_reduced': plan['planning_reduced'],
                    'planning_reduction_reasons': plan['planning_reduction_reasons'],
                    'usage': [event for event in plan['events'] if event.get('usage')]
                             + [item for panel in built['panels'] for item in panel['usage']],
                    'events': plan['events'],
                    'panel_calls': built['events'],
                    'panel_outcomes': outcomes,
                    'checks': {'planner': {'panels': len(panel_plan['panels']),
                                           'remaining_issues': plan.get('remaining_issues', []),
                                           'planning_reduced': plan['planning_reduced'],
                                           'planning_reduction_reasons': plan['planning_reduction_reasons']},
                               'drawing': {'repairs': {panel['id']: panel['repairs'] for panel in built['events']},
                                           'panels': len(built['panels'])}},
                    'reviews': [],
                    'vision_review': bool(settings.get('overview_vision')),
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


def narrative_passages(narrative):
    """The narrative's cited passages in claim order, without duplicates."""
    refs = []
    for name in CLAIMS:
        claim = narrative.get(name) or {}
        refs.extend(claim.get('passages') or [])
    for relation in narrative.get('relationships') or []:
        refs.extend(relation.get('passages') or [])
    return list(dict.fromkeys(refs))


def document_digest_of(document):
    from papers.library import document_digest
    return document_digest(document)
