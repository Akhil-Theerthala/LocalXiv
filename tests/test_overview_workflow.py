"""Overview planning: panel-plan validation, author-facing projection, and planner sequence."""
import copy
import json
import re
import tempfile
import threading
import time
import unittest
from pathlib import Path

from papers.ai import ProviderError
from papers.explanation import PanelPlanError, panel_assignments, validate_panel_plan
from papers.overview_workflow import build_panels, plan_overview

EVIDENCE = {'passages': [{'id': f'p{index:05d}', 'section': 'Body', 'text': 'Retained text ' + str(index)}
                         for index in range(1, 5)]}

NARRATIVE = {
    'paper_type': 'method', 'visual_focus': 'Follow one token through attention mixing.',
    'question': {'text': 'How does a token combine other tokens?', 'passages': ['p00001']},
    'contribution': {'text': 'It mixes values by attention weights.', 'passages': ['p00002']},
    'finding': {'text': 'It reaches 2.5 on the benchmark.', 'passages': ['p00003']},
    'limitation': {'text': 'Only two datasets were tested.', 'passages': ['p00004']},
    'relationships': [{'source': 'Scores', 'target': 'Values', 'relationship': 'Scores weight the values.',
                       'passages': ['p00002']}],
}


def brief(identifier, *, covers, content, parents=(), facts=(), exit_state=None, construction='flow'):
    return {'id': identifier, 'title': identifier.upper(), 'purpose': 'Explain ' + identifier,
            'covers': list(covers), 'entry_from': list(parents),
            'exit_state': exit_state or ('State of ' + identifier), 'shared_fact_ids': list(facts),
            'content': list(content), 'construction': construction}


def item(text, passages, kind='statement'):
    return {'text': text, 'passages': list(passages), 'kind': kind}


def plan(panels=None, facts=None):
    facts = {'candidate_probabilities': {'text': '0.73 and 0.27', 'passages': ['p00002'],
                                         'kind': 'source'}} if facts is None else facts
    panels = [
        brief('p1', covers=['question'], content=[item('One token needs one number per candidate.', ['p00001'])]),
        brief('p2', covers=['contribution', 'relationships[0]'], parents=['p1'],
              facts=['candidate_probabilities'], construction='calculation',
              content=[item('output = 0.73 v1 + 0.27 v2', ['p00002'], 'equation')],
              exit_state='The weights sum to one.'),
        brief('p3', covers=['finding', 'limitation'], parents=['p2'], facts=['candidate_probabilities'],
              construction='chart', content=[item('The score is 2.5.', ['p00003'], 'value'),
                                             item('Only two datasets were tested.', ['p00004'], 'qualification')]),
    ] if panels is None else panels
    return {'title': 'Attention mixing', 'paper_connection': 'One token, mixed by attention.',
            'caption': 'Illustrative numbers for the mixing step.',
            'shared_facts': facts, 'panels': panels}


class PanelPlanValidationTests(unittest.TestCase):
    def validate(self, value, narrative=NARRATIVE, evidence=EVIDENCE):
        return validate_panel_plan(value, narrative, evidence)

    def test_a_complete_plan_validates_and_covers_every_claim(self):
        self.assertEqual(3, len(self.validate(plan())['panels']))

    def test_panel_count_outside_one_to_seven_is_rejected(self):
        for panels in ([], [brief(f'p{index}', covers=['question'],
                                  content=[item('text', ['p00001'])]) for index in range(8)]):
            with self.subTest(count=len(panels)), self.assertRaises(PanelPlanError) as caught:
                self.validate(plan(panels=panels or []))
            self.assertTrue(any('1 through 7' in issue['message'] for issue in caught.exception.issues))

    def test_duplicate_and_path_like_ids_are_rejected(self):
        duplicate = plan(panels=[brief('p1', covers=['question'], content=[item('a', ['p00001'])]),
                                 brief('p1', covers=['contribution'], content=[item('b', ['p00002'])]),
                                 brief('p2', covers=['finding', 'limitation'], content=[item('c', ['p00003'])])])
        with self.assertRaises(PanelPlanError) as caught:
            self.validate(duplicate)
        self.assertTrue(any('duplicates' in issue['message'] for issue in caught.exception.issues))
        for identifier in ('../p1', '/etc/passwd', 'p 1', 'p1.svg'):
            with self.subTest(identifier=identifier):
                unsafe = plan(panels=[brief(identifier, covers=['question', 'contribution', 'finding', 'limitation'],
                                            content=[item('a', ['p00001'])])])
                with self.assertRaises(PanelPlanError):
                    self.validate(unsafe)

    def test_unknown_passages_and_fact_keys_are_rejected(self):
        unknown = plan(panels=[brief('p1', covers=['question', 'contribution', 'finding', 'limitation'],
                                     content=[item('a', ['p99999'])])])
        with self.assertRaises(PanelPlanError) as caught:
            self.validate(unknown)
        self.assertTrue(any('unknown passage' in issue['message'] for issue in caught.exception.issues))
        unknown_fact = plan(panels=[brief('p1', covers=['question', 'contribution', 'finding', 'limitation'],
                                          facts=['missing_fact'], content=[item('a', ['p00001'])])])
        with self.assertRaises(PanelPlanError) as caught:
            self.validate(unknown_fact)
        self.assertTrue(any('unknown shared fact' in issue['message'] for issue in caught.exception.issues))

    def test_a_later_panel_cannot_be_an_entry_dependency(self):
        panels = [brief('p1', covers=['question'], content=[item('a', ['p00001'])]),
                  brief('p2', covers=['contribution'], parents=['p3'], content=[item('b', ['p00002'])]),
                  brief('p3', covers=['finding', 'limitation'], content=[item('c', ['p00003'])])]
        with self.assertRaises(PanelPlanError) as caught:
            self.validate(plan(panels=panels))
        self.assertTrue(any('earlier panel' in issue['message'] for issue in caught.exception.issues))

    def test_an_orphaned_narrative_claim_is_reported_with_its_name(self):
        panels = [brief('p1', covers=['question', 'contribution'],
                        content=[item('a', ['p00001']), item('b', ['p00002'])]),
                  brief('p2', covers=['finding'], content=[item('c', ['p00003'])])]
        with self.assertRaises(PanelPlanError) as caught:
            self.validate(plan(panels=panels))
        orphan = next(issue for issue in caught.exception.issues
                      if issue.get('constraint') == 'unowned_claims')
        self.assertIn('limitation', orphan['message'])
        self.assertEqual(0, orphan['limit'])

    def test_copying_every_citation_into_a_panel_does_not_own_a_claim(self):
        panels = [brief('p1', covers=['question', 'contribution', 'finding'],
                        content=[item('Everything at once.', ['p00001', 'p00002', 'p00003', 'p00004'])]),
                  brief('p2', covers=[], content=[item('A note.', ['p00004'])])]
        with self.assertRaises(PanelPlanError) as caught:
            self.validate(plan(panels=panels))
        orphan = next(issue for issue in caught.exception.issues
                      if issue.get('constraint') == 'unowned_claims')
        self.assertIn('limitation', orphan['message'])

    def test_illustrative_shared_facts_are_allowed_and_source_facts_need_evidence(self):
        illustrative = plan(facts={'candidate_probabilities': {'text': '0.73 and 0.27', 'passages': [],
                                                               'kind': 'illustrative'}})
        self.assertEqual('0.73 and 0.27',
                         self.validate(illustrative)['shared_facts']['candidate_probabilities']['text'])
        ungrounded = plan(facts={'candidate_probabilities': {'text': '0.73 and 0.27', 'passages': [],
                                                             'kind': 'source'}})
        with self.assertRaises(PanelPlanError) as caught:
            self.validate(ungrounded)
        self.assertTrue(any('at least one retained passage' in issue['message']
                            for issue in caught.exception.issues))

    def test_a_panel_without_any_known_support_is_rejected(self):
        panels = [brief('p1', covers=['question', 'contribution', 'finding', 'limitation'],
                        content=[item('Everything at once.', ['p00001'])]),
                  brief('p2', covers=[], content=[item('Asserted without evidence.', [])])]
        with self.assertRaises(PanelPlanError) as caught:
            self.validate(plan(panels=panels))
        self.assertTrue(any('cite at least one retained passage' in issue['message']
                            for issue in caught.exception.issues))

    def test_unknown_narrative_claim_keys_and_unknown_construction_are_rejected(self):
        panels = [brief('p1', covers=['question', 'contribution', 'finding', 'limitation', 'conclusion'],
                        content=[item('a', ['p00001'])], construction='network')]
        with self.assertRaises(PanelPlanError) as caught:
            self.validate(plan(panels=panels))
        messages = ' '.join(issue['message'] for issue in caught.exception.issues)
        self.assertIn('unknown narrative claim', messages)
        self.assertIn('construction', messages)


class AssignmentProjectionTests(unittest.TestCase):
    def test_later_panels_inherit_the_exact_endpoint_and_shared_values(self):
        valid = validate_panel_plan(plan(), NARRATIVE, EVIDENCE)
        assignments = panel_assignments(valid)
        self.assertEqual([valid['panels'][0]['exit_state']], assignments[1]['entry_context'])
        self.assertEqual(valid['shared_facts']['candidate_probabilities']['text'],
                         assignments[1]['shared_facts']['candidate_probabilities'])
        self.assertEqual(assignments[0]['exit_state'], assignments[1]['entry_context'][0])

    def test_evidence_ids_and_unrelated_briefs_never_reach_an_author(self):
        valid = validate_panel_plan(plan(), NARRATIVE, EVIDENCE)
        assignments = panel_assignments(valid)
        self.assertNotIn('passages', assignments[1]['content'][0])
        serialized = json.dumps(assignments[1])
        self.assertNotIn('p0000', serialized)
        self.assertNotIn('retained evidence', serialized)
        self.assertNotIn('question', serialized)
        self.assertIn('0.73 and 0.27', serialized)

    def test_every_assignment_carries_the_fields_a_panel_author_needs(self):
        valid = validate_panel_plan(plan(), NARRATIVE, EVIDENCE)
        for assignment in panel_assignments(valid):
            self.assertEqual({'id', 'title', 'purpose', 'entry_context', 'content', 'exit_state',
                              'shared_facts', 'illustrative_values', 'construction'}, set(assignment))
            self.assertTrue(assignment['content'])
            self.assertTrue(assignment['purpose'])


class ScriptedProvider:
    """Answers by matching a marker in the last user message; records every request."""

    def __init__(self, responses):
        self.settings = {'endpoint': 'https://example.test/v1', 'model': 'scripted'}
        self.responses = list(responses)
        self.calls = []

    def complete(self, messages, **kwargs):
        self.calls.append(messages)
        text = '\n'.join(message['content'] for message in messages
                         if isinstance(message.get('content'), str))
        for index, (marker, value) in enumerate(self.responses):
            if marker in text:
                self.responses.pop(index)
                if isinstance(value, Exception):
                    raise value
                return {'text': value if isinstance(value, str) else json.dumps(value),
                        'usage': {'total_tokens': 7}}
        raise AssertionError('No scripted response for: ' + text[-200:])


def selection_response(ids=('p00001', 'p00002', 'p00003', 'p00004')):
    return {'paper_type': 'method', 'focus': 'Attention mixing', 'section_ids': [],
            'passage_ids': list(ids), 'figure_ids': []}


def labels(provider, events):
    return [event['label'] for event in events if event['kind'] == 'model_request']


class PlannerSequenceTests(unittest.TestCase):
    def document(self, directory):
        return {'directory': str(directory), 'arxiv_id': '2501.00001', 'title': 'Example',
                'format': 'epub', 'source_digest': 'digest',
                'passages': copy.deepcopy(EVIDENCE['passages'])}

    def run_plan(self, provider):
        with tempfile.TemporaryDirectory() as directory:
            document = self.document(Path(directory))
            return plan_overview(provider, document, lambda _message: None)

    def test_the_planner_drafts_clarifies_then_simplifies_before_any_panel_is_drawn(self):
        conflict = plan(panels=[brief('p1', covers=['question', 'contribution'], content=[item('a', ['p00001'])]),
                                brief('p2', covers=['finding'], content=[item('b', ['p00003'])]),
                                brief('p3', covers=[], content=[item('c', ['p00002'])])])
        clarified = copy.deepcopy(conflict)
        clarified['panels'][0]['content'].append(item('A fifth candidate remains unresolved.', ['p00002']))
        independent = plan(panels=[brief(f'p{index}', covers=[name], content=[item(name, [pid])])
                                   for index, (name, pid) in enumerate(
                                       zip(('question', 'contribution', 'finding', 'limitation'),
                                           ('p00001', 'p00002', 'p00003', 'p00004')), 1)])
        provider = ScriptedProvider([
            ('Choose the retained source material', selection_response()),
            ('Plan what the reader will learn', NARRATIVE),
            ('Assign the accepted narrative', conflict),
            ('Check this draft panel plan', {'panel_plan': clarified, 'issues': ['p3 depends on p1 for its endpoint']}),
            ('Simplify the unresolved dependencies', {'panel_plan': independent, 'issues': []}),
        ])
        result = self.run_plan(provider)
        self.assertEqual(['selection', 'narrative', 'panel_plan', 'panel_plan_clarify', 'panel_plan_simplify'],
                         labels(provider, result['events']))
        self.assertEqual(['p1', 'p2', 'p3', 'p4'], [panel['id'] for panel in result['panel_plan']['panels']])
        self.assertTrue(all(not panel['entry_from'] for panel in result['panel_plan']['panels']))
        self.assertEqual('planner', result['assignment_source'])
        self.assertEqual('0.73 and 0.27',
                         result['panel_plan']['shared_facts']['candidate_probabilities']['text'])

    def test_every_planner_instruction_states_its_json_contract(self):
        """A live run returned a bare array for selection because the contract was implicit."""
        from papers.overview_workflow import (NARRATIVE_INSTRUCTION, PANEL_CLARIFY_INSTRUCTION,
                                              PANEL_PLAN_INSTRUCTION, PANEL_SIMPLIFY_INSTRUCTION,
                                              SELECTION_INSTRUCTION)
        for instruction in (SELECTION_INSTRUCTION, NARRATIVE_INSTRUCTION, PANEL_PLAN_INSTRUCTION,
                            PANEL_CLARIFY_INSTRUCTION, PANEL_SIMPLIFY_INSTRUCTION):
            with self.subTest(instruction=instruction[:40]):
                self.assertIn('JSON object', ' '.join(instruction.split()))
                self.assertIn('{', instruction)
        for field in ('paper_type', 'focus', 'section_ids', 'passage_ids', 'figure_ids'):
            self.assertIn(field, SELECTION_INSTRUCTION)

    def test_a_malformed_narrative_gets_one_protocol_correction(self):
        provider = ScriptedProvider([
            ('Choose the retained source material', selection_response()),
            ('Plan what the reader will learn', 'not json at all'),
            ('Plan what the reader will learn', NARRATIVE),
            ('Assign the accepted narrative', plan()),
            ('Check this draft panel plan', {'panel_plan': plan(), 'issues': []}),
        ])
        result = self.run_plan(provider)
        self.assertEqual(['selection', 'narrative', 'narrative_correction', 'panel_plan', 'panel_plan_clarify'],
                         labels(provider, result['events']))
        self.assertEqual(NARRATIVE, result['narrative'])

    def test_a_plan_that_never_validates_falls_back_to_independent_narrative_briefs(self):
        provider = ScriptedProvider([
            ('Choose the retained source material', selection_response()),
            ('Plan what the reader will learn', NARRATIVE),
            ('Assign the accepted narrative', 'not json'),
            ('Check this draft panel plan', {'panel_plan': {'panels': []}, 'issues': ['no usable plan']}),
            ('Simplify the unresolved dependencies', {'panel_plan': {'panels': []}, 'issues': ['still unusable']}),
        ])
        result = self.run_plan(provider)
        self.assertEqual('narrative_fallback', result['assignment_source'])
        self.assertEqual(['question', 'contribution', 'finding', 'limitation'],
                         [panel['covers'][0] for panel in result['panel_plan']['panels']])
        self.assertTrue(all(panel['entry_from'] == [] for panel in result['panel_plan']['panels']))
        self.assertTrue(any(event['label'] == 'independent_briefs' for event in result['events']))
        validate_panel_plan(result['panel_plan'], NARRATIVE, result['evidence'])

    def test_one_supplemental_retrieval_answers_a_planner_evidence_request(self):
        narrative = copy.deepcopy(NARRATIVE)
        narrative['limitation'] = {'text': 'Only two datasets were tested.', 'passages': ['p00003']}
        narrative['request_evidence'] = {'section_ids': [], 'passage_ids': ['p00004'], 'figure_ids': []}
        independent = plan()
        provider = ScriptedProvider([
            ('Choose the retained source material', selection_response(ids=('p00001', 'p00002', 'p00003'))),
            ('Plan what the reader will learn', narrative),
            ('Plan what the reader will learn', NARRATIVE),
            ('Assign the accepted narrative', independent),
            ('Check this draft panel plan', {'panel_plan': independent, 'issues': []}),
        ])
        result = self.run_plan(provider)
        self.assertEqual(['selection', 'narrative', 'narrative', 'panel_plan', 'panel_plan_clarify'],
                         labels(provider, result['events']))
        supplements = [event for event in result['events'] if event['label'] == 'evidence_supplement']
        self.assertEqual(1, len(supplements))
        self.assertIn('p00004', [passage['id'] for passage in result['evidence']['passages']])

    def test_a_paper_without_retained_text_fails_before_any_request(self):
        provider = ScriptedProvider([])
        with tempfile.TemporaryDirectory() as directory:
            document = self.document(Path(directory))
            document['passages'] = []
            document['report'] = {'text_warning': 'No retained text for this paper.'}
            with self.assertRaises(ProviderError) as caught:
                plan_overview(provider, document, lambda _message: None)
        self.assertIn('No retained text', str(caught.exception))
        self.assertEqual([], provider.calls)

    def test_an_unavailable_provider_fails_without_inventing_a_plan(self):
        failure = ProviderError('Provider request failed or returned an invalid response.')
        provider = ScriptedProvider([('Choose the retained source material', failure),
                                     ('Choose the retained source material', failure)])
        with tempfile.TemporaryDirectory() as directory:
            document = self.document(Path(directory))
            with self.assertRaises(ProviderError):
                plan_overview(provider, document, lambda _message: None)
        self.assertEqual(2, len(provider.calls), 'a transient transport failure gets exactly one retry')

    def test_an_authentication_failure_is_never_retried(self):
        provider = ScriptedProvider([
            ('Choose the retained source material',
             ProviderError('Provider rejected authentication. Check the saved key and model access.'))])
        with tempfile.TemporaryDirectory() as directory:
            document = self.document(Path(directory))
            with self.assertRaises(ProviderError) as caught:
                plan_overview(provider, document, lambda _message: None)
        self.assertIn('authentication', str(caught.exception))
        self.assertEqual(1, len(provider.calls))

    def test_cancellation_stops_the_planner_between_requests(self):
        class Cancelled(Exception):
            pass

        provider = ScriptedProvider([('Choose the retained source material', selection_response())])
        state = {'count': 0}

        def progress(message):
            state['count'] += 1
            if state['count'] > 1:
                raise Cancelled()

        with tempfile.TemporaryDirectory() as directory:
            document = self.document(Path(directory))
            with self.assertRaises(Cancelled):
                plan_overview(provider, document, progress)
        self.assertEqual(1, len(provider.calls))


if __name__ == '__main__':
    unittest.main()


class BarrierProvider:
    """Panel requests must overlap; each reports usage to the instance's own callback."""

    def __init__(self, barrier, answers, delays=None):
        self.settings = {'endpoint': 'https://example.test/v1', 'model': 'scripted'}
        self.key = 'test-key'
        self.barrier = barrier
        self.answers = answers
        self.delays = delays or {}
        self.calls = []
        self.usage = []
        self.finished = []
        self.threads = []

    def with_usage(self, callback):
        clone = BarrierProvider(self.barrier, self.answers, self.delays)
        clone.calls = self.calls
        clone.usage = self.usage
        clone.finished = self.finished
        clone.threads = self.threads
        return _ClonedProvider(clone, callback)

    def complete(self, messages, **kwargs):
        return self._answer(messages)

    def _answer(self, messages):
        self.calls.append(messages)
        self.threads.append(threading.current_thread().name)
        matched = re.search(r'panel id: (p\d+)', json.dumps(messages))
        panel_id = matched.group(1) if matched else 'p1'
        if self.barrier is not None:
            self.barrier.wait(5)
        delay = self.delays.get(panel_id, 0.0)
        if delay:
            time.sleep(delay)
        answer = self.answers.get(panel_id)
        if isinstance(answer, list):
            answer = answer.pop(0) if answer else 'not json'
        if isinstance(answer, Exception):
            raise answer
        self.finished.append(panel_id)
        return {'text': answer if isinstance(answer, str) else json.dumps(answer),
                'usage': {'total_tokens': 3}}


class _ClonedProvider:
    def __init__(self, clone, callback):
        self.clone = clone
        self.callback = callback

    @property
    def settings(self):
        return {'endpoint': 'https://example.test/v1', 'model': 'scripted'}

    def complete(self, messages, **kwargs):
        result = self.clone._answer(messages)
        self.callback(result.get('usage') or {})
        return result


DRAWING_TEXT = {'p1': 'One retained claim.', 'p2': 'A weight of 0.73 applies.',
                'p3': 'Only two datasets were tested.'}


def panel_response(identifier, text=None):
    text = text or DRAWING_TEXT[identifier]
    body = (f'<text x="40" y="60" font-size="22" font-weight="bold">{identifier}</text>'
            f'<text x="40" y="120" font-size="18">{text}</text>')
    return {'panel_id': identifier,
            'svg': ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 520 300" font-size="18">'
                    + body + '</svg>')}


def assignment_records():
    return [
        {'id': 'p1', 'title': 'Question', 'purpose': 'Explain the question',
         'entry_context': [], 'content': [{'text': 'One retained claim.', 'kind': 'statement'}],
         'exit_state': 'The reader knows the question.', 'shared_facts': {},
         'illustrative_values': [], 'construction': 'flow'},
        {'id': 'p2', 'title': 'Mixing', 'purpose': 'Explain the mixing',
         'entry_context': ['The reader knows the question.'],
         'content': [{'text': 'A weight of 0.73 applies.', 'kind': 'value'}],
         'exit_state': 'The reader knows the mixing.', 'shared_facts': {},
         'illustrative_values': [], 'construction': 'calculation'},
        {'id': 'p3', 'title': 'Limitation', 'purpose': 'Explain the limitation',
         'entry_context': [], 'content': [{'text': 'Only two datasets were tested.', 'kind': 'statement'}],
         'exit_state': 'The reader knows the limitation.', 'shared_facts': {},
         'illustrative_values': [], 'construction': 'comparison'},
    ]


class PanelBuildTests(unittest.TestCase):
    def test_two_panel_requests_overlap_and_results_keep_plan_order(self):
        barrier = threading.Barrier(2)
        provider = BarrierProvider(barrier, {'p1': panel_response('p1'), 'p2': panel_response('p2')},
                                   delays={'p1': 0.4})
        assignments = assignment_records()[:2]
        with tempfile.TemporaryDirectory() as directory:
            usage, threads = [], []
            built = build_panels(provider, assignments, directory, lambda _message: None,
                                 usage_callback=lambda entry: (usage.append(entry),
                                                               threads.append(threading.current_thread())))
        # The barrier fails a sequential implementation; the slower first panel still finishes last.
        self.assertEqual(['p2', 'p1'], provider.finished)
        self.assertEqual(['p1', 'p2'], [panel['id'] for panel in built['panels']])
        self.assertEqual(2, len(usage), 'each billed response is counted exactly once')
        self.assertTrue(all(thread is threading.current_thread() for thread in threads),
                        'usage callbacks run on the coordinator thread')

    def test_a_billed_response_rejected_as_malformed_is_still_counted_once(self):
        provider = BarrierProvider(None, {'p1': ['not json', panel_response('p1')],
                                          'p2': panel_response('p2')})
        assignments = assignment_records()[:2]
        with tempfile.TemporaryDirectory() as directory:
            usage = []
            built = build_panels(provider, assignments, directory, lambda _message: None,
                                 usage_callback=usage.append)
        self.assertEqual(3, len(usage), 'two requests for the repaired panel plus one for its sibling')
        repaired = built['runs']['p1']
        self.assertEqual(2, repaired.attempts)
        self.assertEqual(2, len(repaired.usage))

    def test_a_malformed_first_drawing_is_repaired_once_and_accepted(self):
        provider = BarrierProvider(None, {'p1': ['not json', panel_response('p1')],
                                          'p2': panel_response('p2')})
        assignments = assignment_records()[:2]
        with tempfile.TemporaryDirectory() as directory:
            built = build_panels(provider, assignments, directory, lambda _message: None)
        outcomes = {panel['id']: panel['outcome'] for panel in built['panels']}
        self.assertEqual({'p1': 'repaired', 'p2': 'created'}, outcomes)

    def test_a_second_invalid_drawing_falls_back_to_the_simplified_panel(self):
        provider = BarrierProvider(None, {'p1': ['not json', 'still not json'],
                                          'p2': ['not json', 'still not json']})
        assignments = assignment_records()[:2]
        with tempfile.TemporaryDirectory() as directory:
            built = build_panels(provider, assignments, directory, lambda _message: None)
        panels = {panel['id']: panel for panel in built['panels']}
        self.assertEqual(['simplified', 'simplified'],
                         [panels['p1']['outcome'], panels['p2']['outcome']])
        self.assertEqual([], panels['p1']['checks']['issue_details'])
        self.assertIn('One retained claim.', ' '.join(panels['p1']['labels']))
        self.assertIn('0.73', ' '.join(panels['p2']['labels']))

    def test_a_geometry_defect_triggers_one_repair_with_measured_issues(self):
        bad = {'panel_id': 'p1',
               'svg': ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 520 300" font-size="18">'
                       '<text x="40" y="60" font-size="9">too small</text></svg>')}
        provider = BarrierProvider(None, {'p1': [bad, panel_response('p1')],
                                          'p2': panel_response('p2')})
        assignments = assignment_records()[:2]
        with tempfile.TemporaryDirectory() as directory:
            built = build_panels(provider, assignments, directory, lambda _message: None)
        repairs = [messages for messages in provider.calls
                   if 'DEFECTS TO FIX IN THIS DRAWING ONLY' in json.dumps(messages)]
        self.assertEqual(1, len(repairs), 'exactly one repair request per panel')
        self.assertIn('minimum 14', json.dumps(repairs[0]))
        self.assertEqual('repaired', built['panels'][0]['outcome'])

    def test_one_unavailable_panel_fails_the_run_without_losing_sibling_artifacts(self):
        provider = BarrierProvider(None, {'p1': panel_response('p1'), 'p2': panel_response('p2')})
        provider.answers['p1'] = ProviderError('Provider request failed or returned an invalid response.')
        assignments = assignment_records()[:2]
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ProviderError):
                build_panels(provider, assignments, directory, lambda _message: None)
            artifacts = Path(directory)
            written = sorted(path.name for path in artifacts.glob('panel-*'))
        self.assertIn('panel-p2', written)

    def test_cancellation_stops_submission_and_does_not_publish_late_results(self):
        class Cancelled(Exception):
            pass

        provider = BarrierProvider(None, {'p1': panel_response('p1'), 'p2': panel_response('p2')})
        assignments = assignment_records()[:2]
        state = {'calls': 0}

        def progress(message):
            state['calls'] += 1
            if state['calls'] >= 2:
                raise Cancelled()

        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(Cancelled):
                build_panels(provider, assignments, directory, progress)
