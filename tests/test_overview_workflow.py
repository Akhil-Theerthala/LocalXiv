"""Overview planning: panel-plan validation, author-facing projection, and planner sequence."""
import copy
import json
import os
import re
import tempfile
import threading
import time
import unittest
from pathlib import Path

from papers import html_figures
from papers.ai import ProviderError
from papers.explanation import (PanelPlanError, PlanValidationError, panel_assignments,
                                validate_overview_narrative, validate_panel_plan, validate_plan)
from papers.overview_workflow import RunStore, build_panels, plan_overview, run_report

FIXTURES = Path(__file__).parent / 'fixtures' / 'overview-p2'

EVIDENCE = {'passages': [{'id': f'p{index:05d}', 'section': 'Body', 'text': 'Retained text ' + str(index)}
                         for index in range(1, 5)]}


def planning_document(directory):
    """A minimal saved document the coordinator can read offline."""
    return {'directory': str(directory), 'arxiv_id': '2501.00001', 'title': 'Example',
            'format': 'epub', 'source_digest': 'digest',
            'passages': copy.deepcopy(EVIDENCE['passages'])}


def latest_run(directory):
    """The single run directory this offline test created."""
    root = Path(directory) / 'reader' / 'overview-figures'
    runs = [path for path in root.iterdir() if path.is_dir()]
    if len(runs) != 1:
        raise AssertionError('expected exactly one run directory, found ' + str(runs))
    return runs[0]

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
        descriptive = plan(panels=[brief('panel_taxonomy_and_metrics', covers=[
            'question', 'contribution', 'finding', 'limitation'], content=[item('a', ['p00001'])])])
        self.assertEqual('panel_taxonomy_and_metrics',
                         self.validate(descriptive)['panels'][0]['id'])
        for identifier in ('../p1', '/etc/passwd', 'p 1', 'p1.svg', 'p' * 33):
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

    def test_the_assignment_projects_declared_exact_text_without_semantic_prose(self):
        facts = {'candidate_probabilities': {
            'text': 'The weights are 0.73 and 0.27 for the two candidates.',
            'exact_text': ['0.73', '0.27'], 'passages': ['p00002'], 'kind': 'source'}}
        valid = validate_panel_plan(plan(facts=facts), NARRATIVE, EVIDENCE)
        second = panel_assignments(valid)[1]
        self.assertEqual(['0.73', '0.27', 'output = 0.73 v1 + 0.27 v2'], second['exact_text'])
        self.assertIn('The weights are 0.73 and 0.27 for the two candidates.',
                      second['shared_facts']['candidate_probabilities'])

    def test_exact_text_must_be_copied_from_the_approved_fact_text(self):
        facts = {'candidate_probabilities': {
            'text': 'The weights are 0.73 and 0.27 for the two candidates.',
            'exact_text': ['0.75'], 'passages': ['p00002'], 'kind': 'source'}}
        with self.assertRaises(PanelPlanError) as caught:
            validate_panel_plan(plan(facts=facts), NARRATIVE, EVIDENCE)
        self.assertTrue(any('same notation' in issue['message'] for issue in caught.exception.issues))

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
                              'shared_facts', 'illustrative_values', 'exact_text',
                              'construction'}, set(assignment))
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
        return planning_document(directory)

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

    def test_contract_defects_are_corrected_without_reducing_the_plan(self):
        approved = plan()
        approved['shared_facts']['candidate_probabilities']['exact_text'] = ['0.73', '0.27']
        for defect in ('exact_text', 'title', 'fact_key', 'passage'):
            for correction_pass in ('clarify', 'simplify'):
                with self.subTest(defect=defect, correction_pass=correction_pass):
                    draft = copy.deepcopy(approved)
                    if defect == 'exact_text':
                        draft['shared_facts']['candidate_probabilities']['exact_text'][0] = '0.75'
                    elif defect == 'title':
                        draft['panels'][0]['title'] = 'x' * 81
                    elif defect == 'fact_key':
                        draft['panels'][1]['shared_fact_ids'] = ['unknown_fact']
                    else:
                        draft['panels'][1]['content'][0]['passages'] = ['p99999']
                    with self.assertRaises(PanelPlanError) as caught:
                        validate_panel_plan(draft, NARRATIVE, EVIDENCE)
                    diagnostics = [issue['message'] for issue in caught.exception.issues]
                    responses = [
                        ('Choose the retained source material', selection_response()),
                        ('Plan what the reader will learn', NARRATIVE),
                        ('Assign the accepted narrative', draft),
                        ('Check this draft panel plan', {'panel_plan': approved if correction_pass == 'clarify'
                                                       else draft, 'issues': []}),
                    ]
                    if correction_pass == 'simplify':
                        responses.append(('<remaining_issues>', {'panel_plan': approved, 'issues': []}))
                    provider = ScriptedProvider(responses)
                    result = self.run_plan(provider)
                    correction = provider.calls[-1][-1]['content']
                    for message in diagnostics:
                        self.assertIn(message, correction)
                    self.assertIn('Preserve all valid panels', correction)
                    self.assertNotIn('remove the dependency rather than describing it', correction)
                    self.assertEqual(approved, result['panel_plan'])
                    self.assertEqual('planner', result['assignment_source'])
                    self.assertFalse(result['planning_reduced'])
                    self.assertEqual(4 if correction_pass == 'clarify' else 5, len(provider.calls))

    def test_latest_invalid_candidate_and_diagnostics_reach_the_last_correction(self):
        draft = plan()
        draft['title'] = 'x' * 81
        latest = plan()
        latest['panels'][0]['purpose'] = 'Keep this improved explanation.'
        latest['shared_facts']['candidate_probabilities']['exact_text'] = ['0.75']
        corrected = copy.deepcopy(latest)
        corrected['shared_facts']['candidate_probabilities']['exact_text'] = ['0.73']
        provider = ScriptedProvider([
            ('Choose the retained source material', selection_response()),
            ('Plan what the reader will learn', NARRATIVE),
            ('Assign the accepted narrative', draft),
            ('Check this draft panel plan', {'panel_plan': latest, 'issues': []}),
            ('<remaining_issues>', {'panel_plan': corrected, 'issues': []}),
        ])
        result = self.run_plan(provider)
        prompt = provider.calls[-1][-1]['content']
        candidate = json.loads(prompt.split('<panel_plan>')[1].split('</panel_plan>')[0])
        diagnostics = json.loads(prompt.split('<remaining_issues>')[1].split('</remaining_issues>')[0])
        self.assertEqual(latest, candidate)
        self.assertEqual(['panel_plan.shared_facts.candidate_probabilities.exact_text[0] '
                          'must be copied from the approved fact text in the same notation'], diagnostics)
        self.assertEqual(corrected, result['panel_plan'])
        self.assertFalse(result['planning_reduced'])

    def test_unchanged_semantic_issues_cannot_be_cleared_by_an_empty_report(self):
        from papers.overview_workflow import _carry_forward_issues
        self.assertEqual(['conflicting science', 'missing handoff'], _carry_forward_issues(
            ['conflicting science'], plan(), plan(), ['missing handoff']))
        provider = ScriptedProvider([
            ('Choose the retained source material', selection_response()),
            ('Plan what the reader will learn', NARRATIVE),
            ('Assign the accepted narrative', {'panel_plan': plan(), 'issues': ['conflicting science']}),
            ('Check this draft panel plan', {'panel_plan': plan(), 'issues': []}),
            ('Simplify the unresolved dependencies', {'panel_plan': plan(), 'issues': []}),
        ])
        result = self.run_plan(provider)
        self.assertEqual('narrative_fallback', result['assignment_source'])
        self.assertTrue(result['planning_reduced'])
        self.assertIn('conflicting science', provider.calls[-1][-1]['content'])
        self.assertEqual(5, len(provider.calls))

    def test_planner_field_limits_match_validation(self):
        from papers.explanation import SHARED_FACT_SCHEMA
        from papers.overview_workflow import PANEL_PLAN_INSTRUCTION
        self.assertEqual(200, SHARED_FACT_SCHEMA['properties']['text']['maxLength'])
        self.assertIn('Shared fact text: 1-200 characters', PANEL_PLAN_INSTRUCTION)
        self.assertIn('Titles: 1-80 characters', PANEL_PLAN_INSTRUCTION)

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

    def test_a_step_list_for_visual_focus_is_joined_and_recorded(self):
        """DeepSeek with thinking off returned the teaching steps as an array.

        Phase 2 joins the ordered steps with newlines without changing their words.
        """
        narrative = copy.deepcopy(NARRATIVE)
        del narrative['visual_focus']
        stepped = {**narrative, 'visual_focus': ['Step 1: mix values.', 'Step 2: sum weights.']}
        provider = ScriptedProvider([
            ('Choose the retained source material', selection_response()),
            ('Plan what the reader will learn', stepped),
            ('Assign the accepted narrative', plan()),
            ('Check this draft panel plan', {'panel_plan': plan(), 'issues': []}),
        ])
        result = self.run_plan(provider)
        self.assertEqual('Step 1: mix values.\nStep 2: sum weights.', result['narrative']['visual_focus'])
        self.assertTrue(any(event.get('label') == 'visual_focus_joined' for event in result['events']))

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

    def test_a_narrative_that_never_validates_is_recovered_with_reduced_planning(self):
        broken = copy.deepcopy(NARRATIVE)
        broken['relationships'] = [{'source': 'a', 'target': 'b', 'relationship': 'r',
                                    'passages': ['p99999']}]
        independent = plan(panels=[
            brief('p1', covers=['question'], content=[item('One token needs one number per candidate.', ['p00001'])]),
            brief('p2', covers=['contribution'], parents=['p1'], facts=['candidate_probabilities'],
                  construction='calculation',
                  content=[item('output = 0.73 v1 + 0.27 v2', ['p00002'], 'equation')],
                  exit_state='The weights sum to one.'),
            brief('p3', covers=['finding', 'limitation'], parents=['p2'], facts=['candidate_probabilities'],
                  construction='chart', content=[item('The score is 2.5.', ['p00003'], 'value'),
                                                 item('Only two datasets were tested.', ['p00004'], 'qualification')])])
        provider = ScriptedProvider([
            ('Choose the retained source material', selection_response()),
            ('Plan what the reader will learn', broken),
            ('Plan what the reader will learn', broken),
            ('Assign the accepted narrative', independent),
            ('Check this draft panel plan', {'panel_plan': independent, 'issues': []}),
        ])
        result = self.run_plan(provider)
        self.assertEqual([], result['narrative']['relationships'])
        self.assertEqual(NARRATIVE['visual_focus'], result['narrative']['visual_focus'])
        recovered = next(event for event in result['events']
                         if event.get('label') == 'narrative_recovered')
        self.assertEqual('visual_focus', recovered['focus_source'])
        self.assertIn('preserved', recovered['reason'])
        self.assertTrue(result['planning_reduced'])
        self.assertTrue(any('recovered' in reason for reason in result['planning_reduction_reasons']))
        self.assertTrue(any(event.get('label') == 'narrative_recovered' for event in result['events']))

    def test_supplemental_evidence_that_cannot_be_incorporated_is_disclosed(self):
        first = copy.deepcopy(NARRATIVE)
        first['request_evidence'] = {'section_ids': [], 'passage_ids': ['p00004'], 'figure_ids': []}
        independent = plan(panels=[
            brief('p1', covers=['question'], content=[item('One token needs one number per candidate.', ['p00001'])]),
            brief('p2', covers=['contribution', 'relationships[0]'], parents=['p1'],
                  facts=['candidate_probabilities'], construction='calculation',
                  content=[item('output = 0.73 v1 + 0.27 v2', ['p00002'], 'equation')],
                  exit_state='The weights sum to one.'),
            brief('p3', covers=['finding', 'limitation'], parents=['p2'], facts=['candidate_probabilities'],
                  construction='chart', content=[item('The score is 2.5.', ['p00003'], 'value'),
                                                 item('Only two datasets were tested.', ['p00004'], 'qualification')])])
        provider = ScriptedProvider([
            ('Choose the retained source material', selection_response(ids=('p00001', 'p00002', 'p00003'))),
            ('Plan what the reader will learn', first),
            ('New retained evidence has been added', ProviderError('The supplemental request failed.')),
            ('Assign the accepted narrative', independent),
            ('Check this draft panel plan', {'panel_plan': independent, 'issues': []}),
        ])
        result = self.run_plan(provider)
        self.assertEqual(NARRATIVE['contribution']['text'], result['narrative']['contribution']['text'])
        self.assertTrue(result['planning_reduced'])
        self.assertTrue(any('could not be incorporated' in reason
                            for reason in result['planning_reduction_reasons']))
        self.assertTrue(any(event.get('label') == 'narrative_supplement_failed'
                            for event in result['events']))

    def test_unresolved_handoffs_reach_the_independent_narrative_fallback(self):
        conflicted = plan()
        issue = ['p2 depends on p1 for its endpoint, which p1 does not establish']
        provider = ScriptedProvider([
            ('Choose the retained source material', selection_response()),
            ('Plan what the reader will learn', NARRATIVE),
            ('Assign the accepted narrative', {'panel_plan': conflicted, 'issues': issue}),
            ('Check this draft panel plan', {'panel_plan': conflicted, 'issues': issue}),
            ('Simplify the unresolved dependencies', {'panel_plan': conflicted, 'issues': issue}),
        ])
        result = self.run_plan(provider)
        self.assertEqual([], result['remaining_issues'])
        self.assertTrue(result['planning_reduced'])
        self.assertEqual('narrative_fallback', result['assignment_source'])
        self.assertTrue(result['planning_reduction_reasons'])
        self.assertTrue(all(not panel['entry_from']
                            for panel in result['panel_plan']['panels']))
        validate_panel_plan(result['panel_plan'], NARRATIVE, result['evidence'])
        passes = [event for event in result['events'] if event.get('label') == 'planner_pass']
        self.assertTrue(passes, 'each structurally valid pass is retained in the events')
        self.assertEqual(issue, passes[0]['issues'])
        fallback = next(event for event in result['events'] if event.get('label') == 'planning_fallback')
        self.assertIn('p2 depends on p1', ' '.join(fallback['reasons']))

    def test_a_valid_draft_survives_a_malformed_clarification(self):
        provider = ScriptedProvider([
            ('Choose the retained source material', selection_response()),
            ('Plan what the reader will learn', NARRATIVE),
            ('Assign the accepted narrative', plan()),
            ('Check this draft panel plan', 'not json'),
        ])
        result = self.run_plan(provider)
        self.assertEqual('planner', result['assignment_source'])
        self.assertEqual([], result['remaining_issues'])
        self.assertEqual(['p1', 'p2', 'p3'],
                         [panel['id'] for panel in result['panel_plan']['panels']])
        self.assertTrue(any(event.get('label') == 'planner_protocol_error'
                            for event in result['events']))

    def test_a_first_pass_evidence_request_is_visible_to_the_clarification(self):
        draft = plan()
        with_request = {**draft, 'request_evidence': {'section_ids': [], 'passage_ids': ['p00004'],
                                                      'figure_ids': []}}
        provider = ScriptedProvider([
            ('Choose the retained source material',
             selection_response(ids=('p00001', 'p00002', 'p00003'))),
            ('Plan what the reader will learn', NARRATIVE),
            ('Assign the accepted narrative', with_request),
            ('Check this draft panel plan', {'panel_plan': draft, 'issues': []}),
        ])
        result = self.run_plan(provider)
        self.assertIn('p00004', [passage['id'] for passage in result['evidence']['passages']])

        def evidence_block(call):
            text = call[-1]['content']
            return text.split('<retrieved_evidence>')[1].split('</retrieved_evidence>')[0]

        self.assertNotIn('[p00004]', evidence_block(provider.calls[2]),
                         'the draft request had no such passage yet')
        self.assertIn('[p00004]', evidence_block(provider.calls[3]),
                      'the clarification is built from the latest retrieved evidence')

    def test_an_invalid_supplemental_narrative_request_is_disclosed_not_fatal(self):
        first = copy.deepcopy(NARRATIVE)
        first['request_evidence'] = {'section_ids': ['Appendix 7.2', 'Section 5.3'],
                                     'passage_ids': [], 'figure_ids': []}
        provider = ScriptedProvider([
            ('Choose the retained source material', selection_response()),
            ('Plan what the reader will learn', first),
            ('Assign the accepted narrative', plan()),
            ('Check this draft panel plan', {'panel_plan': plan(), 'issues': []}),
        ])
        result = self.run_plan(provider)
        self.assertEqual(['selection', 'narrative', 'panel_plan', 'panel_plan_clarify'],
                         labels(provider, result['events']),
                         'an unusable request does not earn a second narrative call')
        self.assertTrue(result['planning_reduced'])
        self.assertTrue(any('could not be incorporated' in reason
                            for reason in result['planning_reduction_reasons']))
        self.assertTrue(any(event.get('label') == 'evidence_supplement_unresolved'
                            for event in result['events']))
        self.assertEqual(NARRATIVE['contribution']['text'],
                         result['narrative']['contribution']['text'])

    def test_an_invalid_planner_supplement_is_disclosed_not_fatal(self):
        draft = plan()
        with_request = {**draft, 'request_evidence': {'section_ids': ['Section 9.9'],
                                                      'passage_ids': [], 'figure_ids': []}}
        provider = ScriptedProvider([
            ('Choose the retained source material', selection_response()),
            ('Plan what the reader will learn', NARRATIVE),
            ('Assign the accepted narrative', with_request),
            ('Check this draft panel plan', {'panel_plan': draft, 'issues': []}),
        ])
        result = self.run_plan(provider)
        self.assertEqual('planner', result['assignment_source'])
        self.assertTrue(any(event.get('label') == 'evidence_supplement_unresolved'
                            for event in result['events']))
        self.assertEqual(['p1', 'p2', 'p3'],
                         [panel['id'] for panel in result['panel_plan']['panels']])

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


class RunLifecycleTests(unittest.TestCase):
    """Failure and cancellation leave a terminal run record with the evidence already collected."""

    def run_planner(self, provider, progress=None):
        with tempfile.TemporaryDirectory() as directory:
            document = planning_document(Path(directory))
            with self.assertRaises(BaseException) as caught:
                plan_overview(provider, document, progress or (lambda _message: None))
            run = latest_run(directory)
            record = json.loads((run / 'run.json').read_text())
            events = [json.loads(line) for line in (run / 'events.jsonl').read_text().splitlines()
                      if line.strip()]
            requests = run / 'requests'
            files = sorted(path.name for path in requests.iterdir()) if requests.is_dir() else []
            return caught.exception, record, events, files

    def test_a_first_narrative_failure_leaves_a_terminal_run_record(self):
        provider = ScriptedProvider([
            ('Choose the retained source material', selection_response()),
            ('Plan what the reader will learn', ProviderError('The narrative request failed.')),
        ])
        error, record, events, files = self.run_planner(provider)
        self.assertIn('narrative request failed', str(error))
        self.assertEqual('failed', record['status'])
        self.assertEqual('narrative', record['failed_stage'])
        self.assertEqual('ProviderError', record['exception_type'])
        selection = next(event for event in events if event.get('label') == 'selection')
        self.assertTrue(selection['has_response'])
        self.assertIn(Path(selection['response_file']).name, files)
        narrative = next(event for event in events if event.get('label') == 'narrative')
        self.assertFalse(narrative['has_response'])
        self.assertIsNone(narrative['usage'])
        self.assertIsNone(narrative['response_file'])

    def test_a_correction_failure_records_both_candidates_and_the_rejected_answer(self):
        provider = ScriptedProvider([
            ('Choose the retained source material', selection_response()),
            ('Plan what the reader will learn', 'not json at all'),
            ('Plan what the reader will learn', ProviderError('The correction request failed.')),
        ])
        error, record, events, files = self.run_planner(provider)
        self.assertIn('correction request failed', str(error))
        self.assertEqual('failed', record['status'])
        self.assertEqual('narrative', record['failed_stage'])
        first = next(event for event in events if event.get('label') == 'narrative')
        result = next(event for event in events
                      if event.get('kind') == 'model_request_result'
                      and event.get('label') == 'narrative')
        correction = next(event for event in events if event.get('label') == 'narrative_correction')
        self.assertTrue(first['has_response'])
        self.assertEqual('unparseable', result['status'])
        self.assertEqual(['response.text'], result['validator_issue_paths'])
        self.assertFalse(correction['has_response'])
        self.assertIn('0002-response.txt', files)
        correction_messages = provider.calls[-1]
        assistant = [message['content'] for message in correction_messages
                     if message['role'] == 'assistant']
        self.assertEqual(['not json at all'], assistant,
                         'the correction carries the rejected answer as an assistant message')

    def test_a_provider_failure_before_any_response_invents_nothing(self):
        provider = ScriptedProvider([
            ('Choose the retained source material',
             ProviderError('Provider rejected authentication. Check the saved key and model access.'))])
        error, record, events, files = self.run_planner(provider)
        self.assertEqual('failed', record['status'])
        self.assertEqual('selection', record['failed_stage'])
        request = next(event for event in events if event['kind'] == 'model_request')
        self.assertFalse(request['has_response'])
        self.assertIsNone(request['usage'])
        self.assertIsNone(request['response_file'])
        self.assertEqual([], files, 'no response file is written before a response exists')

    def test_cancellation_leaves_a_cancelled_run_record(self):
        class Cancelled(Exception):
            pass

        provider = ScriptedProvider([('Choose the retained source material', selection_response())])
        state = {'count': 0}

        def progress(message):
            state['count'] += 1
            if state['count'] > 1:
                raise Cancelled()

        error, record, events, files = self.run_planner(provider, progress)
        self.assertIsInstance(error, Cancelled)
        self.assertEqual('cancelled', record['status'])
        self.assertEqual('Cancelled', record['exception_type'])
        self.assertEqual(1, len([event for event in events if event['kind'] == 'model_request']))


class GenerateLifecycleTests(unittest.TestCase):
    """``generate`` owns one run directory from before planning through the terminal record."""

    def test_generate_creates_the_run_directory_before_planning_and_finalizes_its_failure(self):
        from papers import overview_workflow as workflow
        seen = {}

        def failing_plan(provider, document, progress, *, vision=False, run_directory=None):
            seen['directory'] = Path(run_directory)
            seen['record'] = json.loads((Path(run_directory) / 'run.json').read_text())
            raise ProviderError('planning exploded')

        original = workflow.plan_overview
        workflow.plan_overview = failing_plan
        try:
            with tempfile.TemporaryDirectory() as directory:
                document = planning_document(Path(directory))
                with self.assertRaises(ProviderError) as caught:
                    workflow.generate(ScriptedProvider([]), document, lambda _message: None)
                run = latest_run(directory)
                record = json.loads((run / 'run.json').read_text())
                self.assertEqual(run, seen['directory'])
        finally:
            workflow.plan_overview = original
        self.assertIn('planning exploded', str(caught.exception))
        self.assertEqual('running', seen['record']['status'])
        self.assertEqual('failed', record['status'])
        self.assertEqual('planning', record['failed_stage'])

    def test_a_drawing_stage_failure_keeps_the_plan_and_records_its_stage(self):
        from papers import overview_workflow as workflow
        generated_plan = {'narrative': copy.deepcopy(NARRATIVE), 'panel_plan': plan(),
                          'evidence': copy.deepcopy(EVIDENCE), 'selection': selection_response(),
                          'orientation': {}, 'events': [], 'assignment_source': 'planner',
                          'remaining_issues': [], 'planning_reduced': False,
                          'planning_reduction_reasons': []}
        original_plan, original_build = workflow.plan_overview, workflow.build_panels

        def fake_plan(*args, **kwargs):
            return copy.deepcopy(generated_plan)

        def failing_build(*args, **kwargs):
            raise RuntimeError('drawing exploded')

        workflow.plan_overview, workflow.build_panels = fake_plan, failing_build
        try:
            with tempfile.TemporaryDirectory() as directory:
                document = planning_document(Path(directory))
                with self.assertRaises(RuntimeError):
                    workflow.generate(ScriptedProvider([]), document, lambda _message: None)
                run = latest_run(directory)
                record = json.loads((run / 'run.json').read_text())
                self.assertTrue((run / 'assignments.json').is_file())
                self.assertTrue((run / 'narrative.json').is_file())
        finally:
            workflow.plan_overview, workflow.build_panels = original_plan, original_build
        self.assertEqual('failed', record['status'])
        self.assertEqual('drawing', record['failed_stage'])
        self.assertEqual('RuntimeError', record['exception_type'])

    def test_generate_finalizes_a_cancelled_drawing_stage(self):
        from papers import overview_workflow as workflow
        generated_plan = {'narrative': copy.deepcopy(NARRATIVE), 'panel_plan': plan(),
                          'evidence': copy.deepcopy(EVIDENCE), 'selection': selection_response(),
                          'orientation': {}, 'events': [], 'assignment_source': 'planner',
                          'remaining_issues': [], 'planning_reduced': False,
                          'planning_reduction_reasons': []}
        original_plan, original_build = workflow.plan_overview, workflow.build_panels

        def fake_plan(*args, **kwargs):
            return copy.deepcopy(generated_plan)

        def cancelled_build(*args, **kwargs):
            raise Cancelled('user cancelled')

        workflow.plan_overview, workflow.build_panels = fake_plan, cancelled_build
        try:
            with tempfile.TemporaryDirectory() as directory:
                document = planning_document(Path(directory))
                with self.assertRaises(Cancelled):
                    workflow.generate(ScriptedProvider([]), document, lambda _message: None)
                record = json.loads((latest_run(directory) / 'run.json').read_text())
        finally:
            workflow.plan_overview, workflow.build_panels = original_plan, original_build
        self.assertEqual('cancelled', record['status'])
        self.assertEqual('drawing', record['failed_stage'])


class Cancelled(Exception):
    """A named cancellation for the lifecycle tests; the workflow matches by name as well."""


class RecoveryDeliveryTests(unittest.TestCase):
    """A simplified panel is checked like a drawn one and never hides the original defects."""

    def notation_assignment(self, identifier='p1'):
        return {
            'id': identifier, 'title': 'Source notation', 'purpose': 'Show the fraction.',
            'entry_context': [],
            'content': [{'text': 'Predictions depend on positions $<i$ and earlier ones.',
                         'kind': 'statement'},
                        {'text': r'\frac{a+b}{c+d}', 'kind': 'equation'}],
            'exit_state': 'The reader sees the fraction.', 'shared_facts': {},
            'illustrative_values': ['0.73 and 0.27'],
            'exact_text': [r'\frac{a+b}{c+d}'], 'construction': 'calculation'}

    def test_a_simplified_panel_is_checked_and_keeps_its_original_defects_separate(self):
        assignments = [self.notation_assignment('p1'), self.notation_assignment('p2')]
        provider = BarrierProvider(None, {'p1': ['not json', 'still not json'],
                                          'p2': ['not json', 'still not json']})
        with tempfile.TemporaryDirectory() as directory:
            built = build_panels(provider, assignments, directory, lambda _message: None)
        panel = {item['id']: item for item in built['panels']}['p1']
        self.assertEqual('simplified', panel['outcome'])
        self.assertEqual([], panel['checks']['issue_details'])
        self.assertIn('positions $<i$', ' '.join(panel['labels']))
        self.assertIn('illustrative', ' '.join(panel['labels']).lower())
        self.assertIn(r'\frac{a+b}{c+d}', ' '.join(panel['labels']))
        self.assertEqual([], panel['issues'], 'the accepted fallback has no active issues')
        self.assertTrue(panel['drawing_defects'],
                        'the original drawing defects stay recorded separately')

    def test_a_fallback_that_cannot_show_the_exact_text_is_not_delivered(self):
        assignment = [{'id': 'p1', 'title': 'Missing number', 'purpose': 'Show a number.',
                       'entry_context': [], 'content': [{'text': 'A statement without it.',
                                                         'kind': 'statement'}],
                       'exit_state': 'State.', 'shared_facts': {}, 'illustrative_values': [],
                       'exact_text': ['0.91'], 'construction': 'chart'}]
        provider = BarrierProvider(None, {'p1': ['not json', 'still not json']})
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ProviderError) as caught:
                build_panels(provider, assignment, directory, lambda _message: None)
        self.assertIn('could not be drawn or recovered', str(caught.exception))
        self.assertIn('0.91', str(caught.exception))

    def test_a_missing_renderer_is_one_diagnosed_failure(self):
        from papers import panel_authoring
        provider = BarrierProvider(None, {'p1': panel_response('p1')})
        original = panel_authoring.render
        panel_authoring.render = lambda *args, **kwargs: (_ for _ in ()).throw(
            ValueError('HTML renderer is missing. Build papers/HTMLSnapshot.swift.'))
        try:
            with tempfile.TemporaryDirectory() as directory:
                with self.assertRaises(ValueError) as caught:
                    build_panels(provider, assignment_records()[:1], directory, lambda _m: None)
        finally:
            panel_authoring.render = original
        self.assertIn('renderer is missing', str(caught.exception))
        self.assertEqual(1, len(provider.finished),
                         'the failed renderer is diagnosed once, not invoked repeatedly')

    def test_a_fallback_renderer_exception_keeps_sibling_artifacts_and_usage(self):
        provider = BarrierProvider(None, {'p1': ['not json', 'still not json'],
                                          'p2': panel_response('p2')})
        assignments = assignment_records()[:2]
        from papers import overview_workflow as workflow
        original = workflow.simple_panel

        def failing(assignment_value, directory):
            raise RuntimeError('recovery exploded')

        workflow.simple_panel = failing
        try:
            with tempfile.TemporaryDirectory() as directory:
                trace = Path(directory) / 'panel-trace.jsonl'
                usage = []
                with self.assertRaises(ProviderError) as caught:
                    workflow.build_panels(provider, assignments, directory, lambda _m: None,
                                          trace=trace, usage_callback=usage.append)
                sibling = (Path(directory) / 'panel-p2' / 'source.svg').is_file()
                checks = (Path(directory) / 'panel-p2' / 'checks.json').is_file()
                traced = [json.loads(line) for line in trace.read_text().splitlines()
                          if line.strip()]
        finally:
            workflow.simple_panel = original
        self.assertIn('recovery exploded', str(caught.exception))
        self.assertTrue(sibling, 'the completed sibling drawing stays on disk')
        self.assertTrue(checks, 'the sibling diagnostics stay on disk')
        self.assertTrue(usage, 'billed sibling usage remains accessible')
        self.assertTrue(any(event.get('kind') == 'model_request' for event in traced))


class CompositionDeliveryTests(unittest.TestCase):
    """The composed image must pass its own checks before a completed run is returned."""

    def generated_plan(self):
        return {'narrative': copy.deepcopy(NARRATIVE), 'panel_plan': plan(),
                'evidence': copy.deepcopy(EVIDENCE), 'selection': selection_response(),
                'orientation': {}, 'events': [], 'assignment_source': 'planner',
                'remaining_issues': [], 'planning_reduced': False,
                'planning_reduction_reasons': []}

    def fake_render(self, document, *, issue_details=None):
        def render(directory, figure, title, mode='overview'):
            source = Path(directory) / 'reader' / 'overview-figures' / 'composed.source.svg'
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"/>')
            relative = source.relative_to(Path(document['directory']))
            return {'html': 'fake.html', 'svg': 'fake.svg', 'png': 'fake.png', 'pdf': 'fake.pdf',
                    'svg_source': str(relative),
                    'checks': {'issue_details': list(issue_details or []),
                               'canvas': {'width': 100, 'height': 100}}}
        return render

    def run_generate(self, provider, document, render):
        from papers import overview_workflow as workflow
        original_plan, original_assign, original_render = (
            workflow.plan_overview, workflow.panel_assignments, html_figures.render)
        workflow.plan_overview = lambda *args, **kwargs: copy.deepcopy(self.generated_plan())
        workflow.panel_assignments = lambda _plan: assignment_records()
        html_figures.render = render
        try:
            return workflow.generate(provider, document, lambda _message: None)
        finally:
            workflow.plan_overview = original_plan
            workflow.panel_assignments = original_assign
            html_figures.render = original_render

    def test_active_composition_geometry_issues_cannot_publish(self):
        provider = BarrierProvider(None, {'p1': panel_response('p1'), 'p2': panel_response('p2'),
                                          'p3': panel_response('p3')})
        with tempfile.TemporaryDirectory() as directory:
            document = planning_document(Path(directory))
            issue = {'code': 'layout_fit', 'message': 'Overview page is too tall.'}
            with self.assertRaises(ProviderError) as caught:
                self.run_generate(provider, document, self.fake_render(document,
                                                                      issue_details=[issue]))
            run = latest_run(directory)
            record = json.loads((run / 'run.json').read_text())
            files = sorted(path.name for path in run.iterdir() if path.is_file())
            panels = sorted(path.name for path in run.glob('panel-*') if path.is_dir())
        self.assertIn('geometry checks', str(caught.exception))
        self.assertEqual('failed', record['status'])
        self.assertEqual('composition', record['failed_stage'])
        self.assertIn('overview.source.svg', files, 'the assembled source is preserved')
        self.assertIn('panel-calls.json', files)
        self.assertIn('composition-checks.json', files)
        self.assertEqual(['panel-p1', 'panel-p2', 'panel-p3'], panels,
                         'the accepted panel records are preserved')

    def test_a_renderer_failure_at_composition_records_its_stage(self):
        provider = BarrierProvider(None, {'p1': panel_response('p1'), 'p2': panel_response('p2'),
                                          'p3': panel_response('p3')})

        def missing(directory, figure, title, mode='overview'):
            raise ValueError('HTML renderer is missing. Build papers/HTMLSnapshot.swift.')

        with tempfile.TemporaryDirectory() as directory:
            document = planning_document(Path(directory))
            with self.assertRaises(ValueError):
                self.run_generate(provider, document, missing)
            record = json.loads((latest_run(directory) / 'run.json').read_text())
        self.assertEqual('failed', record['status'])
        self.assertEqual('rendering', record['failed_stage'])
        self.assertEqual('ValueError', record['exception_type'])

    def test_a_clean_composition_marks_the_run_completed(self):
        provider = BarrierProvider(None, {'p1': panel_response('p1'), 'p2': panel_response('p2'),
                                          'p3': panel_response('p3')})
        with tempfile.TemporaryDirectory() as directory:
            document = planning_document(Path(directory))
            result = self.run_generate(provider, document, self.fake_render(document))
            record = json.loads((latest_run(directory) / 'run.json').read_text())
        self.assertEqual('completed', record['status'])
        self.assertEqual('completed', record['delivery'])
        self.assertEqual({'created': ['p1', 'p2', 'p3'], 'repaired': [], 'simplified': []},
                         record['panel_outcomes'])
        self.assertEqual('planner', record['assignment_source'])
        self.assertFalse(record['planning_reduced'])
        self.assertEqual([], record['local_issues'])
        self.assertEqual('{{figure:fig1}}', result['text'])
        self.assertEqual('planner', result['provenance']['assignment_source'])
        self.assertFalse(result['provenance']['planning_reduced'])


if __name__ == '__main__':
    unittest.main()


class BarrierProvider:
    """Panel requests must overlap; each reports usage to the instance's own callback."""

    def __init__(self, barrier, answers, delays=None, settings=None):
        self.settings = settings or {'endpoint': 'https://example.test/v1', 'model': 'scripted'}
        self.key = 'test-key'
        self.barrier = barrier
        self.answers = answers
        self.delays = delays or {}
        self.calls = []
        self.options = []
        self.usage = []
        self.finished = []
        self.threads = []

    def with_usage(self, callback):
        clone = BarrierProvider(self.barrier, self.answers, self.delays, settings=self.settings)
        clone.calls = self.calls
        clone.options = self.options
        clone.usage = self.usage
        clone.finished = self.finished
        clone.threads = self.threads
        return _ClonedProvider(clone, callback)

    def complete(self, messages, **kwargs):
        return self._answer(messages, **kwargs)

    def _answer(self, messages, **kwargs):
        self.calls.append(messages)
        self.options.append({key: value for key, value in kwargs.items() if key != 'json_object'})
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
        return self.clone.settings

    def complete(self, messages, **kwargs):
        result = self.clone._answer(messages, **kwargs)
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


class ProviderOptionTests(unittest.TestCase):
    def test_reasoning_off_disables_deepseek_thinking_for_every_stage(self):
        from papers.overview_workflow import provider_options
        settings = {'endpoint': 'https://api.deepseek.com', 'model': 'deepseek-flash',
                    'overview_reasoning': False}
        for stage in ('selection', 'narrative', 'panel_plan', 'panel_plan_simplify', 'panel',
                      'panel_repair'):
            with self.subTest(stage=stage):
                self.assertEqual({'deepseek_thinking': False}, provider_options(settings, stage))

    def test_reasoning_on_keeps_planning_thinking_and_turns_drawing_thinking_off(self):
        from papers.overview_workflow import provider_options
        settings = {'endpoint': 'https://api.deepseek.com', 'model': 'deepseek-flash'}
        self.assertEqual({}, provider_options(settings, 'panel_plan'))
        self.assertEqual({'reasoning_effort': 'low', 'deepseek_thinking': False},
                         provider_options(settings, 'panel'))


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

    def test_a_recovery_failure_is_diagnosed_without_discarding_sibling_artifacts(self):
        provider = BarrierProvider(None, {'p1': ['not json', 'still not json'],
                                          'p2': panel_response('p2')})
        assignments = assignment_records()[:2]
        from papers import overview_workflow as workflow
        original = workflow.simple_panel

        def failing(assignment_value, directory):
            raise RuntimeError('recovery exploded')

        workflow.simple_panel = failing
        try:
            with tempfile.TemporaryDirectory() as directory:
                with self.assertRaises(ProviderError) as caught:
                    workflow.build_panels(provider, assignments, directory, lambda _message: None)
                written = sorted(path.name for path in Path(directory).glob('panel-*'))
                sibling_source = (Path(directory) / 'panel-p2' / 'source.svg').is_file()
        finally:
            workflow.simple_panel = original
        self.assertIn('p1', str(caught.exception))
        self.assertIn('recovery exploded', str(caught.exception))
        self.assertEqual(['panel-p1', 'panel-p2'], written)
        self.assertTrue(sibling_source, 'the completed sibling drawing stays on disk')

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


class DrawingOptionTests(unittest.TestCase):
    """The configured reasoning policy reaches the actual drawing request, not just a helper."""

    def test_every_drawing_attempt_carries_the_stage_options_and_timings(self):
        from papers.overview_workflow import RunStore

        def too_small(identifier):
            return {'panel_id': identifier,
                    'svg': ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 520 300" font-size="18">'
                            '<text x="40" y="60" font-size="9">too small</text></svg>')}

        provider = BarrierProvider(
            None, {'p1': ['not json', panel_response('p1')],
                   'p2': [too_small('p2'), panel_response('p2')]},
            settings={'endpoint': 'https://api.deepseek.com', 'model': 'deepseek-chat'})
        assignments = assignment_records()[:2]
        with tempfile.TemporaryDirectory() as directory:
            store = RunStore(Path(directory))
            built = build_panels(provider, assignments, directory, lambda _message: None,
                                 store=store)
            events = [json.loads(line) for line in (Path(directory) / 'events.jsonl').read_text().splitlines()
                      if line.strip()]
        self.assertEqual(['repaired', 'repaired'],
                         [panel['outcome'] for panel in built['panels']])
        self.assertEqual(4, len(provider.options), 'two panels, each with one repair')
        self.assertTrue(all(options == {'reasoning_effort': 'low', 'deepseek_thinking': False}
                            for options in provider.options),
                        'drawing creation and repair use the drawing policy')
        repair_prompts = [messages for messages in provider.calls
                          if 'DEFECTS TO FIX IN THIS DRAWING ONLY' in json.dumps(messages)]
        self.assertEqual(2, len(repair_prompts), 'one repair for malformed output and one for geometry')
        serialized = [json.dumps(prompt) for prompt in repair_prompts]
        self.assertTrue(any('minimum 14' in text for text in serialized),
                        'the geometry repair carries the measured defect')
        self.assertTrue(any('invalid article or figure plan' in text for text in serialized),
                        'a malformed first drawing is repaired through the repair stage')
        recorded = [event for event in events if event.get('kind') == 'model_request']
        self.assertEqual(4, len(recorded))
        for event in recorded:
            self.assertTrue(event['attempts'])
            for attempt in event['attempts']:
                self.assertIn(attempt['stage'], ('panel', 'panel_repair'))
                self.assertEqual({'reasoning_effort': 'low', 'deepseek_thinking': False},
                                 attempt['options'])
                self.assertIsNotNone(attempt['started_at'])
                self.assertIsNotNone(attempt['finished_at'])
        self.assertEqual(['panel', 'panel', 'panel_repair', 'panel_repair'],
                         sorted(attempt['stage'] for event in recorded
                                for attempt in event['attempts']))

    def test_gemini_flash_drawing_requests_carry_the_low_thinking_level(self):
        provider = BarrierProvider(
            None, {'p1': panel_response('p1'), 'p2': panel_response('p2')},
            settings={'endpoint': 'https://generativelanguage.googleapis.com/v1beta/openai',
                      'model': 'gemini-2.5-flash'})
        assignments = assignment_records()[:2]
        with tempfile.TemporaryDirectory() as directory:
            build_panels(provider, assignments, directory, lambda _message: None)
        self.assertTrue(all(options == {'gemini_thinking_level': 'low'} for options in provider.options))


NATIVE_RENDERER = os.environ.get('LOCALXIV_HTML_RENDERER')


def fixture(name):
    return json.loads((FIXTURES / name).read_text())


class P2ReplayTests(unittest.TestCase):
    """Offline replays of the recorded phase 2 failures, from labelled synthetic fixtures."""

    def test_every_fixture_labels_its_synthetic_origin(self):
        names = sorted(path.name for path in FIXTURES.glob('*.json'))
        self.assertTrue(names, 'the phase 2 replay fixtures exist')
        for name in names:
            data = fixture(name)
            with self.subTest(fixture=name):
                self.assertIn('replay', data['origin'].lower())
                self.assertTrue(data['defect'])

    def test_the_long_focus_replay_is_accepted_without_the_blog_cap(self):
        data = fixture('narrative-long-focus.json')
        value = copy.deepcopy(NARRATIVE)
        value['visual_focus'] = 'x' * 1324 if data['visual_focus'] == 'x1324' else data['visual_focus']
        accepted = validate_overview_narrative(value, EVIDENCE)
        self.assertEqual(value['visual_focus'], accepted['visual_focus'])
        with self.assertRaises(PlanValidationError):
            validate_plan(value, EVIDENCE)

    def test_the_array_focus_replay_is_normalized_by_newlines(self):
        data = fixture('narrative-array-focus.json')
        value = copy.deepcopy(NARRATIVE)
        value['visual_focus'] = data['visual_focus']
        accepted = validate_overview_narrative(value, EVIDENCE)
        self.assertEqual(data['expected'], accepted['visual_focus'])

    def test_the_verbatim_paragraph_replay_no_longer_requires_the_sentence(self):
        from papers.panel_authoring import missing_values
        data = fixture('encoder-paragraph.json')
        self.assertEqual([], missing_values(data['assignment'], data['accepted_drawing']))
        self.assertEqual(['0.73 and 0.27'],
                         missing_values(data['assignment'], data['rejected_drawing']))

    def test_the_changed_equation_replay_is_still_rejected(self):
        from papers.panel_authoring import missing_values
        data = fixture('changed-equation.json')
        self.assertEqual([], missing_values(data['assignment'], data['accepted_drawing']))
        self.assertIn('reply = 0.73 v1 + 0.27 v2',
                      missing_values(data['assignment'], data['rejected_drawing']))

    def test_the_unresolved_handoff_replay_falls_back_to_independent_briefs(self):
        data = fixture('unresolved-handoff.json')
        conflicted = plan()
        issue = [data['issue']]
        provider = ScriptedProvider([
            ('Choose the retained source material', selection_response()),
            ('Plan what the reader will learn', NARRATIVE),
            ('Assign the accepted narrative', {'panel_plan': conflicted, 'issues': issue}),
            ('Check this draft panel plan', {'panel_plan': conflicted, 'issues': issue}),
            ('Simplify the unresolved dependencies', {'panel_plan': conflicted, 'issues': issue}),
        ])
        with tempfile.TemporaryDirectory() as directory:
            document = planning_document(Path(directory))
            result = plan_overview(provider, document, lambda _message: None)
        self.assertEqual(data['expected']['remaining_issues'], result['remaining_issues'])
        self.assertTrue(result['planning_reduced'])
        self.assertEqual(data['expected']['assignment_source'], result['assignment_source'])
        self.assertTrue(all(not panel['entry_from'] for panel in result['panel_plan']['panels']))

    def test_the_request_option_replay_reaches_the_provider(self):
        from papers.overview_workflow import provider_options
        data = fixture('request-options.json')
        provider = BarrierProvider(None, {'p1': ['not json', panel_response('p1')],
                                          'p2': panel_response('p2')},
                                   settings=data['settings'])
        with tempfile.TemporaryDirectory() as directory:
            build_panels(provider, assignment_records()[:2], directory, lambda _message: None)
        self.assertEqual([data['expected']['panel']] * 3, provider.options)
        self.assertEqual(data['gemini_expected'],
                         provider_options(data['gemini_settings'], 'panel'))


@unittest.skipUnless(NATIVE_RENDERER, 'Set LOCALXIV_HTML_RENDERER for the native replay')
class P2NativeReplayTests(unittest.TestCase):
    def test_the_raw_less_than_replay_delivers_a_checked_fallback(self):
        data = fixture('raw-less-than.json')
        provider = BarrierProvider(None, {'p1': ['not json', 'still not json']})
        with tempfile.TemporaryDirectory() as directory:
            built = build_panels(provider, [data['assignment']], directory, lambda _m: None)
        panel = built['panels'][0]
        visible = ' '.join(panel['labels'])
        self.assertEqual('simplified', panel['outcome'])
        self.assertEqual([], panel['checks']['issue_details'])
        for expected in data['expected_labels']:
            self.assertIn(expected, visible)
        self.assertTrue(panel['drawing_defects'])

    def test_the_bold_equation_replay_fits_the_fallback_canvas(self):
        from papers.panel_authoring import simple_panel
        data = fixture('bold-wrap-overflow.json')
        with tempfile.TemporaryDirectory() as directory:
            checked = simple_panel(data['assignment'], directory)
        self.assertEqual([], checked['checks']['issue_details'])
        self.assertIn(data['expected_label'], ' '.join(checked['labels']))

    def test_regular_and_bold_wrapping_agree_with_the_drawn_weight(self):
        from papers.html_figures import measure_text_widths
        text = 'Brier = (1/N) * sum_i (C(x_i, y_i) - 1{y_i = yhat_i})^2'
        with tempfile.TemporaryDirectory() as directory:
            regular = measure_text_widths(directory, [text], font_size=18)[0]
            bold = measure_text_widths(directory, [text], font_size=18, font_weight=700)[0]
        self.assertGreater(bold, regular)


class DeliveryReportTests(unittest.TestCase):
    """The report distinguishes a checked image, a reduced explanation, and a failed run."""

    def completed_record(self, **overrides):
        record = {'status': 'completed', 'delivery': 'completed',
                  'created_at': '2026-09-13T00:00:00+00:00',
                  'finished_at': '2026-09-13T00:00:05+00:00',
                  'assignment_source': 'narrative_fallback', 'planning_reduced': True,
                  'planning_reduction_reasons': ['panel planning fell back to independent briefs'],
                  'panel_outcomes': {'created': ['p1', 'p2', 'p4'], 'repaired': ['p3'],
                                     'simplified': []},
                  'local_issues': [], 'drawing_defects': {}}
        record.update(overrides)
        return record

    def test_a_reduced_plan_with_clean_drawings_is_reported_as_reduced(self):
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)
            (run / 'run.json').write_text(json.dumps(self.completed_record()))
            (run / 'events.jsonl').write_text('')
            report = run_report(run)
        self.assertEqual('completed', report['delivery'])
        self.assertEqual('narrative_fallback', report['assignment_source'])
        self.assertTrue(report['planning_reduced'])
        self.assertEqual({'created': ['p1', 'p2', 'p4'], 'repaired': ['p3'], 'simplified': []},
                         report['panel_outcomes'])
        self.assertEqual('pass', report['local_checks'])
        self.assertEqual('not_reviewed', report['independent_inspection']['status'],
                         'empty geometry issues never imply an independent inspection')
        self.assertEqual(5.0, report['elapsed_seconds'])

    def test_a_planning_failure_report_reads_the_persisted_record(self):
        provider = ScriptedProvider([
            ('Choose the retained source material', selection_response()),
            ('Plan what the reader will learn', ProviderError('The narrative request failed.'))])
        with tempfile.TemporaryDirectory() as directory:
            document = planning_document(Path(directory))
            with self.assertRaises(ProviderError):
                plan_overview(provider, document, lambda _message: None)
            report = run_report(latest_run(directory))
        self.assertEqual('failed', report['delivery'])
        self.assertEqual('narrative', report['failed_stage'])
        self.assertEqual('not_run', report['local_checks'])
        self.assertIsNone(report['assignment_source'])
        self.assertFalse(report['planning_reduced'])
        self.assertEqual([], report['panel_outcomes']['created'])
        self.assertTrue(report['request_options'])
        self.assertEqual('selection', report['request_options'][0]['stage'])
        self.assertEqual('not_reviewed', report['independent_inspection']['status'])

    def test_independent_inspection_is_recorded_only_when_supplied(self):
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)
            (run / 'run.json').write_text(json.dumps(self.completed_record()))
            (run / 'events.jsonl').write_text('')
            review = {'status': 'pass', 'artifact': 'reader/p1.png', 'digest': 'abc123',
                      'findings': ['the central contribution is clear']}
            report = run_report(run, independent_inspection=review)
            ignored = run_report(run, independent_inspection={'status': 'guessed'})
        self.assertEqual(review, report['independent_inspection'])
        self.assertEqual('not_reviewed', ignored['independent_inspection']['status'])

    def test_a_failed_run_reports_its_drawing_options_and_usage(self):
        from papers import overview_workflow as workflow
        provider = BarrierProvider(
            None, {'p1': ['not json', 'still not json']},
            settings={'endpoint': 'https://api.deepseek.com', 'model': 'deepseek-chat'})
        original = workflow.simple_panel
        workflow.simple_panel = lambda assignment_value, directory: (_ for _ in ()).throw(
            RuntimeError('no renderer available'))
        try:
            with tempfile.TemporaryDirectory() as directory:
                run = Path(directory)
                store = RunStore(run)
                with self.assertRaises(ProviderError):
                    build_panels(provider, assignment_records()[:1], run, lambda _m: None,
                                 store=store)
                store.update(status='failed', failed_stage='drawing',
                             finished_at='2026-09-13T00:00:02+00:00')
                report = run_report(run)
        finally:
            workflow.simple_panel = original
        self.assertEqual('failed', report['delivery'])
        self.assertEqual('drawing', report['failed_stage'])
        self.assertEqual('fail', report['local_checks'])
        self.assertEqual({'reasoning_effort': 'low', 'deepseek_thinking': False},
                         report['drawing_attempts'][0]['options'])
        self.assertTrue(report['usage']['drawing'])
        self.assertTrue(report['usage']['totals']['total_tokens'] > 0)
