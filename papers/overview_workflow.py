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
import tempfile
import time
import uuid
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path
from urllib.parse import urlsplit

from papers import html_figures
from papers.ai import Provider, ProviderError, _evidence
from papers.arrangement import arrange, panel_record
from papers.explanation import (CLAIMS, PanelPlanError, panel_assignments, validate_panel_plan,
                                validate_plan, validate_selection)
from papers.overview import parse_json
from papers.panel_authoring import check_panel, missing_values, request_panel, simple_panel
from papers.reading import (REVISION as READING_REVISION, build_orientation, evidence_document,
                            orientation_page, retrieve_evidence)

# Serialized keys of the generation dictionary. Later stages must satisfy these exactly;
# tests/test_exports.py and tests/test_app.py assert this list so a rebuild cannot silently
# drop a key an older saved artifact or a caller still reads.
GENERATION_KEYS = ('text', 'explanation', 'plan', 'cited_text', 'figures', 'evidence', 'provenance')
PROVENANCE_KEYS = ('model', 'document_digest', 'passages', 'prompt_revision', 'svg_profile_revision',
                   'reading', 'usage', 'reviews', 'created_at')
FIGURE_ASSET_KEYS = ('html', 'svg', 'png', 'pdf', 'svg_source')

PROMPT_REVISION = 'overview-panel-workflow-v1'
# Provenance marker for artifacts produced by this workflow. Blog reference admission accepts
# these as drawing references only, and never as a scientific review.
PANEL_WORKFLOW = 'panel-workflow-v1'
MAX_PANELS = 7
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

NARRATIVE_INSTRUCTION = '''Plan what the reader will learn before any panel is drawn. Identify the
central contribution, the mechanism or comparison that makes it work, the supported finding, and the
qualification needed to interpret it. Write visual_focus as the ordered teaching steps a reader
follows, including the shared concrete example and its exact values when the paper is a mechanism
or method. Ground every claim and each stated relationship in retrieved passages. State necessary
qualifications explicitly; leave out secondary material that does not help explain the contribution.
Keep every text field at or under 1200 characters.

Fit the story to the paper:
- architecture: name the proposed architecture and its purpose, give each selected module a local
  story with a concrete input, what changes, and the resulting output, then connect them.
- method: carry one example through the actual computation and explain each quantity before its arithmetic.
- survey: state the organising question, illustrate representative approaches through their
  principles, compare their priorities or tradeoffs, and close with the survey's synthesis.
- evaluation: keep the compared methods, conditions, and actual findings.
- theory: make the assumptions, reasoning, and established result understandable.

Return one JSON object with paper_type, visual_focus, question, contribution, finding, limitation,
and relationships. Each claim is {"text": ..., "passages": [exact IDs]}. Each relationship is
{"source": ..., "target": ..., "relationship": ..., "passages": [exact IDs]}. If you need more
retained evidence, add "request_evidence": {"section_ids": [], "passage_ids": [], "figure_ids": []}
and nothing else changes.'''

PANEL_PLAN_INSTRUCTION = '''Assign the accepted narrative to between one and seven ordered panels.
A panel is the smallest unit a reader can follow on its own. Return one JSON object:

{"title": short figure title, "paper_connection": one sentence on what the figure shows,
 "caption": one sentence beneath the figure,
 "shared_facts": {"<fact key>": {"text": exact display text, "passages": [IDs], "kind": "source" or "illustrative"}},
 "panels": [{"id": short safe id, "title": visible panel title, "purpose": the one idea this panel
   explains, "covers": ["question" | "contribution" | "finding" | "limitation" | "relationships[0]" ...],
   "entry_from": [earlier panel ids this panel builds on],
   "exit_state": what this panel establishes for the reader,
   "shared_fact_ids": [fact keys used here],
   "content": [{"text": one exact statement, value, equation, or connection, "passages": [IDs], "kind":
     "statement" | "value" | "equation" | "connection" | "qualification" | "label"}],
   "construction": "flow" | "mapping" | "comparison" | "calculation" | "chart"}]}

Every narrative claim must have exactly one owning panel in covers. Keep each exact name, equation,
and number in shared_facts when more than one panel needs it, and use its display text unchanged
everywhere. entry_from may name only earlier panels, and the exit_state of those panels is the
context the later panel receives. Write content items an illustrator can draw literally: exact
values, endpoints, and labels. Choose the construction that fits the idea. A panel may cover no
claim when it only explains, but every panel needs at least one retained passage. Ids are short
safe words, never paths.'''

PANEL_CLARIFY_INSTRUCTION = '''Check this draft panel plan against the narrative and the retrieved
evidence, then return a clarified complete plan plus the issues that remain. Check, in this order:
1. Ownership: every narrative claim (question, contribution, finding, limitation) and each stated
   relationship has exactly one owning panel, and the panel explains it.
2. Handoffs: each entry_from names an earlier panel whose exit_state is exactly what the later
   panel starts from, and no panel needs a fact it does not receive.
3. Support: every content item is supported by its cited passages, and nothing the evidence does
   not establish is asserted.
4. Shared values: every repeated name, equation, or number has one canonical shared_facts entry
   with the exact display text that the using panels reference.
5. Completeness: a reader who reads only these panels in order can follow the central contribution.
Return one JSON object:
{"panel_plan": <the complete corrected plan>, "issues": [one short sentence per problem that remains]}. Report an issue only when it is still unresolved in the plan you return. If you need
more retained evidence, add "request_evidence": {"section_ids": [], "passage_ids": [], "figure_ids": []}.'''

PANEL_SIMPLIFY_INSTRUCTION = '''Simplify the unresolved dependencies in this panel plan before the
panels are drawn. For each remaining issue, remove the dependency rather than describing it: give
the affected panel the source-supported content it needs to stand alone, using the exact display
values from shared_facts, and drop any connection the evidence does not support. Do not add new
findings, new examples, or new numbers. Keep the same order, ids, and narrative claims. Return one JSON
object: {"panel_plan": <the complete simplified plan>, "issues": [one short sentence per problem
that remains]}. An empty issues list is the expected result.'''

# Every prompt above asks for the same object twice; this is the protocol correction the next
# request carries when the first response cannot be used.
RETRY_SUFFIX = ('Return the same JSON object again with every field the instruction asks for. '
                'Copy the exact field names; do not add prose around the object.')


def _iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def panel_digest(value):
    """A stable digest of a plan, a narrative, or a source document."""
    text = value if isinstance(value, str) else json.dumps(value, sort_keys=True,
                                                           separators=(',', ':'), ensure_ascii=False)
    return hashlib.sha256(text.encode()).hexdigest()


def panel_transcript(assignment):
    """The accepted assignment text a reader can read beside the image."""
    parts = [assignment.get('purpose')]
    parts += [item['text'] for item in assignment['content']]
    parts += list((assignment.get('shared_facts') or {}).values())
    return ' '.join(dict.fromkeys(part for part in parts if isinstance(part, str) and part.strip()))


def provider_options(settings, stage):
    """Endpoint options the existing provider path already used for this vendor and stage."""
    host = urlsplit(settings.get('endpoint') or '').hostname
    options = {}
    if host == 'generativelanguage.googleapis.com' and 'flash' in (settings.get('model') or ''):
        options['gemini_thinking_level'] = 'low'
    if host == 'api.deepseek.com' and stage in ('panel', 'panel_repair'):
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
    """Owns the request trace, usage accounting, and cancellation checkpoints for one run."""

    def __init__(self, provider, progress):
        self.provider = provider
        self.progress = progress
        self.events = []
        self.requests = 0

    def call(self, label, messages, *, stage=None, json_object=True, retries=1):
        """One structured request. Usage is recorded even when the response is later rejected."""
        options = provider_options(self.provider.settings, stage or label)
        for attempt in range(retries + 1):
            self.requests += 1
            event = {'kind': 'model_request', 'label': label, 'request': self.requests, 'attempt': attempt + 1,
                     'stage': stage or label, 'model': self.provider.settings.get('model'),
                     'message_count': len(messages), 'input_chars': len(json.dumps(messages)),
                     'options': options, 'started_at': _iso()}
            self.progress(label + ' · request ' + str(self.requests))
            started = time.monotonic()
            try:
                response = self.provider.complete(messages, json_object=json_object, **options)
            except ProviderError as error:
                event.update(status='failed', error=str(error)[:500], transient=is_transient(error),
                             elapsed_seconds=round(time.monotonic() - started, 3))
                self.events.append(event)
                if attempt < retries and is_transient(error):
                    time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
                    continue
                raise
            event.update(status='completed', usage=response.get('usage', {}) if isinstance(response, dict) else {},
                         output_chars=len(response.get('text', '')) if isinstance(response, dict) else 0,
                         elapsed_seconds=round(time.monotonic() - started, 3))
            self.events.append(event)
            return response
        raise ProviderError('Provider request failed after one retry.')

    def note(self, name, **details):
        self.events.append({'kind': 'local_operation', 'label': name, 'at': _iso(), **details})


def _request_object(coordinator, label, messages, *, stage=None):
    """One request whose JSON body may be unusable; the caller decides how to recover."""
    response = coordinator.call(label, messages, stage=stage)
    try:
        return parse_json(response['text']), None
    except (KeyError, ValueError, TypeError) as error:
        return None, 'the response was not the required JSON object: ' + (str(error)[:300] or 'invalid JSON')


def _request_validated(coordinator, label, messages, validate, *, stage=None, attempts=2,
                       describe='JSON object'):
    """Request a JSON object and validate it, carrying the rejection into the next request."""
    correction = None
    for _ in range(attempts):
        payload = messages if correction is None else messages + [{'role': 'user', 'content': correction}]
        value, problem = _request_object(coordinator, label if correction is None else label + '_correction',
                                         payload, stage=stage)
        if problem is not None:
            correction = 'The previous ' + label + ' response was rejected: ' + problem + ' ' + RETRY_SUFFIX
            continue
        try:
            return value, validate(value)
        except ValueError as error:
            correction = ('The previous ' + label + ' response was rejected: ' + str(error)[:400]
                          + ' Return the corrected complete ' + describe + '.')
    raise ProviderError('The provider did not return a valid ' + describe + ' for ' + label + '.')


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
    """Load one validated supplemental selection requested by a planner response."""
    if not isinstance(request, dict):
        return evidence
    chosen = {'paper_type': selection['paper_type'], 'focus': selection['focus'],
              'section_ids': request.get('section_ids') or [],
              'passage_ids': request.get('passage_ids') or [],
              'figure_ids': request.get('figure_ids') or []}
    if not any(chosen[field] for field in ('section_ids', 'passage_ids', 'figure_ids')):
        return evidence
    chosen = validate_selection(chosen, orientation)
    merged = _merge_evidence(evidence, retrieve_evidence(document, orientation, chosen, vision=vision),
                             document)
    coordinator.note('evidence_supplement', requested_passage_ids=chosen['passage_ids'],
                     retrieved_passage_ids=[item['id'] for item in merged['passages']])
    return merged


def _narrative(coordinator, document, evidence):
    """One validated narrative plus any requested supplemental retrieval."""
    messages = [{'role': 'user', 'content': NARRATIVE_INSTRUCTION + '\n\n<retrieved_evidence>\n'
                 + _evidence_text(evidence) + '\n</retrieved_evidence>'}]

    def validate(value):
        candidate = copy.deepcopy(value)
        candidate.pop('request_evidence', None)
        return validate_plan(candidate, {'passages': evidence['passages']})

    raw, plan = _request_validated(coordinator, 'narrative', messages, validate, stage='narrative',
                                   describe='narrative plan')
    return plan, (raw.get('request_evidence') if isinstance(raw, dict) else None)


def _fallback_panel_plan(narrative):
    """Independent briefs from the accepted narrative when no validated plan survives."""
    construction = {'architecture': 'flow', 'method': 'flow', 'evaluation': 'chart',
                    'survey': 'comparison', 'theory': 'calculation'}.get(narrative.get('paper_type'), 'flow')
    panels = []
    for index, name in enumerate(CLAIMS, 1):
        claim = narrative.get(name)
        if not isinstance(claim, dict) or not claim.get('text'):
            continue
        panels.append({'id': 'p' + str(index), 'title': name.capitalize(), 'purpose': claim['text'],
                       'covers': [name], 'entry_from': [], 'exit_state': claim['text'],
                       'shared_fact_ids': [],
                       'content': [{'text': claim['text'], 'passages': list(claim.get('passages') or []),
                                    'kind': 'statement'}],
                       'construction': construction})
    if not panels:
        raise ProviderError('The narrative did not contain a claim that could become a panel.')
    return {'title': (narrative.get('visual_focus') or 'Overview')[:80],
            'paper_connection': narrative['contribution']['text'],
            'caption': narrative['finding']['text'],
            'shared_facts': {}, 'panels': panels}


def _plan_pass(coordinator, label, messages, narrative, evidence, *, stage):
    """One planner pass: validated plan (or None), reported issues, an evidence request, and
    the payload the next pass should see when this one did not validate."""
    value, problem = _request_object(coordinator, label, messages, stage=stage)
    if value is None:
        coordinator.note('planner_protocol_error', label=label, reason=problem)
        return None, [problem], None, {'unvalidated_response': problem}
    request = value.pop('request_evidence', None) if isinstance(value, dict) else None
    reported = value.get('issues') if isinstance(value, dict) else None
    issues = [str(item)[:400] for item in reported if str(item).strip()] if isinstance(reported, list) else []
    candidate = value.get('panel_plan', value) if isinstance(value, dict) else value
    try:
        return validate_panel_plan(candidate, narrative, evidence), issues, request, candidate
    except PanelPlanError as error:
        reasons = [issue['message'] for issue in error.issues[:8]]
        coordinator.note('planner_validation_error', label=label, issues=reasons)
        return None, issues + reasons, request, candidate


def plan_panels(coordinator, document, narrative, evidence, *, vision, orientation, selection):
    """Draft, clarify, and — only when dependencies remain — simplify one panel plan."""
    context = ('\n\n<accepted_narrative>\n' + json.dumps(narrative, ensure_ascii=False)
               + '\n</accepted_narrative>\n\n<retrieved_evidence>\n' + _evidence_text(evidence)
               + '\n</retrieved_evidence>')
    draft, issues, request, payload = _plan_pass(
        coordinator, 'panel_plan',
        [{'role': 'user', 'content': PANEL_PLAN_INSTRUCTION + context}],
        narrative, evidence, stage='panel_plan')
    evidence = supplement_evidence(coordinator, document, orientation, selection, evidence, request,
                                   vision=vision)
    clarified, clarified_issues, request, clarified_payload = _plan_pass(
        coordinator, 'panel_plan_clarify',
        [{'role': 'user', 'content': PANEL_CLARIFY_INSTRUCTION + '\n\n<draft_panel_plan>\n'
          + json.dumps(payload, ensure_ascii=False) + '\n</draft_panel_plan>\n\n<remaining_issues>\n'
          + json.dumps(issues, ensure_ascii=False) + '\n</remaining_issues>' + context}],
        narrative, evidence, stage='panel_plan_clarify')
    evidence = supplement_evidence(coordinator, document, orientation, selection, evidence, request,
                                   vision=vision)
    plan, remaining, payload = clarified, clarified_issues, clarified_payload
    if plan is None or remaining:
        simplified, simplified_issues, request, simplified_payload = _plan_pass(
            coordinator, 'panel_plan_simplify',
            [{'role': 'user', 'content': PANEL_SIMPLIFY_INSTRUCTION + '\n\n<panel_plan>\n'
              + json.dumps(payload, ensure_ascii=False) + '\n</panel_plan>\n\n<remaining_issues>\n'
              + json.dumps(remaining, ensure_ascii=False) + '\n</remaining_issues>' + context}],
            narrative, evidence, stage='panel_plan_simplify')
        evidence = supplement_evidence(coordinator, document, orientation, selection, evidence, request,
                                       vision=vision)
        if simplified is not None:
            plan, remaining, payload = simplified, simplified_issues, simplified_payload
    source = 'planner'
    if plan is None:
        coordinator.note('independent_briefs', reason='; '.join(remaining[:3]) or 'no validated panel plan')
        plan = validate_panel_plan(_fallback_panel_plan(narrative), narrative, evidence)
        source = 'narrative_fallback'
    coordinator.note('panel_plan_accepted', panels=len(plan['panels']), source=source,
                     remaining_issues=remaining)
    return plan, evidence, source, remaining


def plan_overview(provider, document, progress, *, vision=False):
    """Select evidence, plan the narrative, and produce validated drawing assignments."""
    if not document.get('passages'):
        raise ProviderError(document.get('report', {}).get('text_warning')
                            or 'This paper has no retained passages for an overview.')
    if not document.get('directory'):
        raise ProviderError('Save the paper before generating an overview.')
    coordinator = Coordinator(provider, progress)
    orientation = build_orientation(document)
    selection, evidence = select_evidence(coordinator, document, orientation, vision=vision)
    narrative, request = _narrative(coordinator, document, evidence)
    if request:
        evidence = supplement_evidence(coordinator, document, orientation, selection, evidence, request,
                                       vision=vision)
        narrative, _ = _narrative(coordinator, document, evidence)
    panel_plan, evidence, source, remaining = plan_panels(coordinator, document, narrative, evidence,
                                                          vision=vision, orientation=orientation,
                                                          selection=selection)
    return {'narrative': narrative, 'panel_plan': panel_plan, 'evidence': evidence,
            'selection': selection, 'orientation': orientation, 'events': coordinator.events,
            'assignment_source': source, 'remaining_issues': remaining}


# --- Panel authoring: parallel requests, local checks, one repair each --------------------------
PANEL_WORKERS = 3
CREATED, REPAIRED, SIMPLIFIED = 'created', 'repaired', 'simplified'
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
    usage, and its diagnostics for the coordinator to act on.
    """
    usage, requests = [], []
    worker = provider_factory(provider, usage)
    for attempt in (1, 2):
        try:
            result = request_panel(worker, assignment, previous=previous, issues=issues, image=image)
        except Exception as error:   # a worker must never fail the coordinator thread
            result = {'source': None, 'error': str(error)[:500], 'error_kind': 'transport',
                      'usage': {}, 'diagnostics': {'panel_id': assignment['id'], 'repair': previous is not None,
                                                   'issues': [str(issue) for issue in issues]}}
        requests.append({'ordinal': attempt, 'repair': previous is not None, 'status': 'completed' if result['source'] else 'rejected',
                         'error': result['error'], 'error_kind': result['error_kind'], 'usage': result.get('usage') or {},
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


def _panel_issues(assignment, checked):
    """The concrete defects a repair request receives: measurements, never sibling drawings."""
    issues = [issue.get('message') or issue.get('code')
              for issue in checked['checks'].get('issue_details') or []]
    issues.extend('The exact value ' + value + ' is missing from the drawing.'
                  for value in missing_values(assignment, checked['labels']))
    return [issue for issue in issues if issue]


class PanelRun:
    """The coordinator-side bookkeeping for one panel: requests, checks, repair, outcome."""

    def __init__(self, assignment, directory, *, usage_callback=None, trace=None, image_enabled=False):
        self.assignment = assignment
        self.id = assignment['id']
        self.directory = Path(directory)
        self.artifacts = _panel_paths(self.directory, self.id)
        self.usage_callback = usage_callback
        self.trace = trace
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

    def record_usage(self, result, label):
        """Count each billed response exactly once, on the coordinator thread."""
        entries = [entry for entry in (result.get('usage') or [])]
        if not entries and result.get('requests'):
            entries = [item.get('usage') or {} for item in result['requests']]
        self.note({'kind': 'model_request', 'label': label, 'panel': self.id,
                   'attempts': len(result.get('requests') or []),
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

    def accept(self, checked, outcome, issues=()):
        self.record = checked
        self.outcome = outcome
        self.issues = list(issues)
        source_path = self.artifacts / 'source.svg'
        source_path.write_text(checked['source'])
        _write_json(self.artifacts / 'checks.json', {'checks': checked['checks'],
                                                     'outcome': outcome, 'issues': self.issues,
                                                     'labels': checked['labels']})
        self.note({'kind': 'local_operation', 'label': 'panel_' + outcome, 'panel': self.id,
                   'issues': self.issues[:6], 'at': _iso()})
        return self.record


def build_panels(provider, assignments, directory, progress, *, provider_factory=default_panel_provider,
                 trace=None, usage_callback=None, image_enabled=False):
    """Author every panel concurrently, checking and repairing on the coordinator thread.

    Returns the panels in plan order plus the request/usage trace. No worker renders, writes a
    common file, or invokes a persistence callback: workers only request, and the coordinator
    renders, checks, records usage, and decides on one repair per panel.
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    runs = {assignment['id']: PanelRun(assignment, directory, usage_callback=usage_callback,
                                       trace=trace, image_enabled=image_enabled)
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
                        if run.repairs == 0:
                            # A malformed drawing is a repairable first attempt.
                            run.repairs += 1
                            submit(run, issues=[result.get('error') or 'the drawing was rejected'])
                        continue
                    checked, issues = _check(run, result['source'])
                    if not issues:
                        run.accept(checked, REPAIRED if run.repairs else CREATED)
                    elif run.repairs == 0:
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
            run.accept(simple_panel(run.assignment, directory), SIMPLIFIED, issues=run.issues)
        run.note({'kind': 'local_operation', 'label': 'panel_result', 'panel': run.id,
                  'outcome': run.outcome, 'issues': run.issues[:6], 'at': _iso()})
        panels.append({'id': identifier, 'source': run.record['source'], 'assets': run.record['assets'],
                       'checks': run.record['checks'], 'labels': run.record['labels'],
                       'outcome': run.outcome, 'issues': run.issues, 'usage': run.usage})
        events.append({'panel': identifier, 'outcome': run.outcome, 'issues': run.issues,
                       'usage': run.usage, 'attempts': run.attempts})
    return {'panels': panels, 'events': events, 'runs': runs}


def _check(run, source):
    """Render and check one returned drawing locally; never a model call."""
    checked = check_panel(source, run.directory, run.id)
    issues = _panel_issues(run.assignment, checked)
    return checked, issues


def generate(provider, document, progress, *, vision=False):
    """Run the complete overview: plan, author panels concurrently, compose, and render."""
    if not document.get('passages'):
        raise ProviderError(document.get('report', {}).get('text_warning')
                            or 'This paper has no retained passages for an overview.')
    if not document.get('directory'):
        raise ProviderError('Save the paper before generating an overview.')
    plan = plan_overview(provider, document, progress, vision=vision)
    narrative, panel_plan, evidence = plan['narrative'], plan['panel_plan'], plan['evidence']
    assignments = panel_assignments(panel_plan)
    run = Path(document['directory']) / 'reader' / 'overview-figures' / uuid.uuid4().hex
    run.mkdir(parents=True, exist_ok=True)
    _write_json(run / 'narrative.json', narrative)
    _write_json(run / 'panel-plan.json', panel_plan)
    _write_json(run / 'assignments.json', assignments)
    _write_json(run / 'plan-events.json', plan['events'])
    trace = run / 'panel-trace.jsonl'
    settings = getattr(provider, 'settings', {}) or {}
    built = build_panels(provider, assignments, run, progress, trace=trace,
                         image_enabled=bool(settings.get('overview_vision')))
    titles = {assignment['id']: assignment['title'] for assignment in assignments}
    records = [panel_record(panel['id'], panel['source'], title=titles[panel['id']])
               for panel in built['panels']]
    layout = arrange(records)
    sources = {panel['id']: panel['source'] for panel in built['panels']}
    composed = html_figures.compose_figure(sources, layout)
    (run / 'overview.source.svg').write_text(composed)
    _write_json(run / 'arrangement.json', layout)
    outcomes = {'created': [panel['id'] for panel in built['panels'] if panel['outcome'] == CREATED],
                'repaired': [panel['id'] for panel in built['panels'] if panel['outcome'] == REPAIRED],
                'simplified': [panel['id'] for panel in built['panels'] if panel['outcome'] == SIMPLIFIED]}
    figure = {'id': 'fig1', 'title': panel_plan['title'],
              'paper_connection': panel_plan['paper_connection'], 'caption': panel_plan['caption'],
              'illustrative': any(fact.get('kind') == 'illustrative'
                                  for fact in (panel_plan.get('shared_facts') or {}).values()),
              'passages': narrative_passages(narrative), 'source_svg': composed}
    assets = html_figures.render(document['directory'], figure, document.get('title', ''), mode='overview')
    checks = assets.pop('checks')
    stored_source = (Path(document['directory']) / assets['svg_source']).read_text()
    texts = {assignment['id']: panel_transcript(assignment) for assignment in assignments}
    claims = {name: narrative[name]['text'] for name in CLAIMS}
    figure.update(assets, checks=checks, dimensions=checks['canvas'],
                  panels=[{'id': placement['id'], 'title': titles[placement['id']],
                           'x': placement['x'], 'y': placement['y'],
                           'width': placement['width'], 'height': placement['height'],
                           'text': texts.get(placement['id'], '')}
                          for placement in layout['placements']],
                  panel_outcomes=outcomes)
    _write_json(run / 'panel-calls.json', built['events'])
    explanation = {'paper_type': narrative['paper_type'], **claims,
                   'passages': narrative_passages(narrative)}
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
                'usage': [event for event in plan['events'] if event.get('usage')]
                         + [item for panel in built['panels'] for item in panel['usage']],
                'events': plan['events'],
                'panel_calls': built['events'],
                'panel_outcomes': outcomes,
                'checks': {'planner': {'panels': len(panel_plan['panels']),
                                       'remaining_issues': plan.get('remaining_issues', [])},
                           'drawing': {'issues': [issue for panel in built['panels'] for issue in panel['issues']],
                                       'panels': len(built['panels'])}},
                'reviews': [],
                'vision_review': bool(settings.get('overview_vision')),
                'created_at': _iso(),
                'run': str(run.relative_to(Path(document['directory']))),
            }}


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
