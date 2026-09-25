"""The request, run record, correction, and evidence machinery both workflows share.

A ``Coordinator`` owns one run directory: its append-only event log, the per-request response
files, and the terminal run record. ``request_validated`` is the one correction pattern: the
rejected answer goes back as an assistant message with the exact issue paths.
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

from papers.ai import REASONING_EFFORTS, ProviderError, _evidence
from papers.convert import Cancelled
from papers.explanation import validate_selection
from papers.overview import parse_json
from papers.reading import evidence_document, orientation_page, retrieve_evidence

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
PROGRESS_STAGES = {
    'selection': 'Reading the paper',
    'digest': 'Understanding the paper',
    'scene': 'Preparing the Overview',
    'narrative': 'Planning the Blog',
    'author': 'Writing the Blog',
    'figures': 'Preparing the Blog figures',
    'review': 'Checking the Blog',
    'brief_correction': 'Refining the Blog',
    'omission_cleanup': 'Refining the Blog',
    'article_cleanup': 'Refining the Blog',
}

SELECTION_INSTRUCTION = '''Choose the retained source material needed to explain this paper's
contribution, how it works, the supported finding, and its qualification, for a reader who knows
the paper's field but not this paper. Use the abstract to navigate, and select the smallest
sufficient set: a parent section includes every descendant, so prefer leaf sections or direct
passage IDs for isolated details. Include an appendix or figure when the contribution needs it,
and the passage where the paper shows its mechanism on a concrete input (a worked example or a
visualization) when it has one. When the headline result is measured across a factor (position,
size, steps), include the table that lists its values, often in an appendix.
Copy IDs exactly from the source map. Do not write the story or choose panel layouts yet.

Return one JSON object and nothing else:
{"paper_type": "architecture" or "method" or "survey" or "evaluation" or "theory" or "other",
 "focus": one sentence naming what the explanation must make understandable,
 "section_ids": [section IDs copied from the source map],
 "passage_ids": [individual passage IDs copied from the source map],
 "figure_ids": [figure or table IDs copied from the source map]}
Use an empty list for a field you do not need, and select at least one section, passage, or figure.'''

# Every prompt above asks for the same object twice; this is the protocol correction the next
# request carries when the first response cannot be used.
RETRY_SUFFIX = ('Return the same JSON object again with every field the instruction asks for. '
                'Copy the exact field names; do not add prose around the object.')


def iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def read_json(path):
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
            write_json(self.directory / 'run.json',
                        {'status': 'running', 'created_at': iso()})

    def read(self):
        return read_json(self.directory / 'run.json')

    def update(self, **fields):
        record = self.read()
        record.update(fields)
        write_json(self.directory / 'run.json', record)
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
        write_json(path, value)
        return self._relative(path)


def create_run_directory(document):
    """Create the per-run artifact directory before the first request can fail."""
    directory = (Path(document['directory']) / 'reader' / 'overview-figures'
                 / uuid.uuid4().hex)
    RunStore(directory)
    return directory


def is_cancelled(error):
    return isinstance(error, Cancelled) or type(error).__name__ == 'Cancelled'


def finalize_run(store, error, *, stage):
    """Write a terminal run record without replacing the original exception.

    The inner coordinator owns the most specific failure stage. An outer lifecycle guard must not
    overwrite a terminal record after the original failure has already been diagnosed.
    """
    current = store.read()
    if current.get('status') in TERMINAL_RUN_STATES:
        return current
    status = 'cancelled' if is_cancelled(error) else 'failed'
    fields = {'status': status, 'finished_at': iso(),
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


# The effort of each workflow when the reader keeps Auto. Blind reviews of deepseek-flash runs on
# five papers, 2026-09-25: Blogs at medium or high ranked well above Blogs at low, and Overviews
# gained nothing above low while taking 1.6 times as long. DeepSeek runs medium as high; other
# providers make medium the cheaper of the two.
AUTO_EFFORTS = {'overview': 'low', 'blog': 'medium'}


def reasoning_effort(value, workflow='overview'):
    """The reasoning effort for one workflow: the level the reader chose, or the workflow's own.

    Any stored value but a level is Auto: unset, true or false from before the choice had levels,
    and off, which the settings no longer offer. Without reasoning, deepseek-flash made 0 of 10
    Overviews and 3 of 10 Blogs: it sent the same fault back after each correction.
    """
    return value if value in REASONING_EFFORTS else AUTO_EFFORTS[workflow]


def provider_options(settings, stage, workflow='overview'):
    """Endpoint options for one stage of an Overview or a Blog: its reasoning effort.

    ``stage`` is recorded with each request so a later policy can vary by stage.
    """
    if not isinstance(settings, dict):
        return {}
    return {'reasoning': reasoning_effort(settings.get('overview_reasoning'), workflow)}


def is_transient(error):
    """A transport failure worth one retry; an authentication failure never is."""
    message = str(error)
    if 'authentication' in message.lower() or 'HTTP status 401' in message or 'HTTP status 403' in message:
        return False
    return any(marker in message for marker in TRANSIENT_MARKERS)


class Coordinator:
    """Owns the request trace, run delivery record, usage accounting, and cancellation checkpoints."""

    def __init__(self, provider, progress, *, run_directory=None, workflow='overview'):
        self.provider = provider
        self.workflow = workflow
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
        options = provider_options(self.provider.settings, stage or label, self.workflow)
        self.active_stage = stage or label
        response = None
        event = None
        for attempt in range(retries + 1):
            self.requests += 1
            event = {'kind': 'model_request', 'label': label, 'request': self.requests,
                     'attempt': attempt + 1, 'stage': stage or label,
                     'model': self.provider.settings.get('model'),
                     'message_count': len(messages), 'input_chars': len(json.dumps(messages)),
                     'options': options, 'started_at': iso(),
                     'response_file': None, 'response_chars': None, 'has_response': False,
                     'usage': None, 'normalized_candidate': None,
                     'validator_issue_paths': None, 'normalization_status': None}
            self.progress(PROGRESS_STAGES.get(self.active_stage, 'Preparing the explanation'))
            started = time.monotonic()
            try:
                response = self.provider.complete(messages, json_object=json_object, **options)
            except ProviderError as error:
                event.update(status='failed', error=str(error)[:500],
                             error_type=type(error).__name__,
                             transient=is_transient(error), finished_at=iso(),
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
                         finished_at=iso(),
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
                  'issues': [str(issue)[:500] for issue in issues][:20], 'at': iso(),
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
        event = {'kind': 'local_operation', 'label': name, 'at': iso(), **details}
        self._record(event)
        return event


def validation_paths(error):
    """Exact validator issue paths from a PlanValidationError or SceneError."""
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


def validation_messages(error):
    issues = getattr(error, 'issues', None)
    if not isinstance(issues, list):
        return [str(error)[:500]]
    return [str(issue.get('message') if isinstance(issue, dict) else issue)[:500]
            for issue in issues][:20]


def request_object(coordinator, label, messages, *, stage=None):
    """One request whose JSON body may be unusable; the caller decides how to recover.

    Returns the parsed value, the parsing problem, the persisted request event, and the raw
    response text so a correction can include the rejected answer as an assistant message.
    """
    response, event = coordinator.call_with_event(label, messages, stage=stage)
    raw_text = response.get('text', '') if isinstance(response, dict) else ''
    try:
        value = parse_json(raw_text)
        if isinstance(value, dict) and value.get('type') == 'json_object':
            # DeepSeek echoes the response_format into the answer; it is not content.
            value.pop('type')
        return value, None, event, raw_text
    except (KeyError, ValueError, TypeError) as error:
        return None, 'the response was not the required JSON object: ' + (str(error)[:300] or 'invalid JSON'), event, raw_text


def request_validated(coordinator, label, messages, validate, *, stage=None, attempts=2,
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
        value, problem, event, raw_text = request_object(coordinator, request_label, payload, stage=stage)
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
            paths = validation_paths(error)
            coordinator.record_normalization(event, status='rejected', candidate=value,
                                             issue_paths=paths,
                                             issues=validation_messages(error))
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



def evidence_text(evidence):
    return _evidence(evidence.get('passages', []))


def source_map(orientation):
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


def merge_evidence(current, new, document):
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


def select_evidence(coordinator, document, orientation, *, vision, instruction=SELECTION_INSTRUCTION):
    """One validated selection request, then local retrieval. Selection is counted separately."""
    messages = [{'role': 'user', 'content': instruction + '\n\nSOURCE MAP:\n'
                 + json.dumps(source_map(orientation), ensure_ascii=False)}]
    _, selection = request_validated(coordinator, 'selection', messages,
                                      lambda value: validate_selection(value, orientation),
                                      stage='selection', describe='selection object')
    added = retrieve_evidence(document, orientation, selection, vision=vision)
    evidence = merge_evidence({'passages': [], 'images': [], 'coverage': {}}, added, document)
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
    merged = merge_evidence(evidence, retrieve_evidence(document, orientation, chosen, vision=vision),
                             document)
    coordinator.note('evidence_supplement', requested_passage_ids=chosen['passage_ids'],
                     retrieved_passage_ids=[item['id'] for item in merged['passages']])
    return merged


def write_json(path, value):
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
