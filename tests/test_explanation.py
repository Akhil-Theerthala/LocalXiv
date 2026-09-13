import copy
import unittest
from papers.explanation import (OVERVIEW_CANDIDATE_MAX_BYTES, PlanValidationError,
                                REPAIR_DECISION_SCHEMA, recover_overview_narrative,
                                validate_overview_narrative, validate_panel_plan, validate_plan,
                                expand_candidate, panel_assignments, validate_selection)
from tests.test_agent_overviews import CANDIDATE, plan_for, draft_for
from tests.test_overview_workflow import EVIDENCE, NARRATIVE


class ExplanationTests(unittest.TestCase):
    def test_selection_is_closed_unique_known_and_substantive(self):
        orientation = {
            'sections': [{'id': 's0001', 'passages': ['p00001']}],
            'figures': [{'id': 'f0001', 'passage': 'p00001'}]}
        selection = {'paper_type': 'method', 'focus': 'Follow the example.',
                     'section_ids': ['s0001'], 'passage_ids': [], 'figure_ids': []}
        self.assertEqual(selection, validate_selection(selection, orientation))
        for bad in (
            dict(selection, extra=True),
            dict(selection, section_ids=['s0001', 's0001']),
            dict(selection, section_ids=[{'id': 's0001'}]),
            dict(selection, passage_ids=['p99999']),
            dict(selection, section_ids=[], passage_ids=[], figure_ids=[]),
            dict(selection, focus=' '),
        ):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate_selection(bad, orientation)

    def test_repair_contract_names_the_exact_identifier_namespaces(self):
        properties = REPAIR_DECISION_SCHEMA['properties']
        self.assertIn('issue IDs', properties['addresses']['description'])
        self.assertIn('plan.', properties['preserves']['description'])
        self.assertIn('passage IDs', properties['evidence']['description'])

    def test_each_claim_and_relationship_requires_its_own_evidence(self):
        doc={'passages':[{'id':'p00001'}]}
        self.assertEqual(plan_for(),validate_plan(plan_for(),doc))
        for name in ('question','contribution','finding','limitation'):
            bad=plan_for();bad[name]['passages']=['p99999']
            with self.assertRaises(ValueError):validate_plan(bad,doc)
        bad=plan_for();bad['relationships'][0]['passages']=[]
        with self.assertRaises(ValueError):validate_plan(bad,doc)

    def test_plan_validation_reports_independent_errors_together(self):
        bad={'paper_type':'unsupported','question':{},'extra':'value','relationships':[]}
        with self.assertRaises(ValueError) as caught:validate_plan(bad,{'passages':[{'id':'p00001'}]})
        message=str(caught.exception)
        for expected in ('plan.extra','paper_type','question.text','contribution','visual_focus','relationships'):
            self.assertIn(expected,message)

    def test_metadata_is_derived_from_plan_and_input_is_not_mutated(self):
        draft=draft_for(CANDIDATE,visual=False);before=copy.deepcopy(draft)
        draft['contribution']='Untrusted duplicate field'
        expanded=expand_candidate(draft,{'passages':[{'id':'p00001'}]})
        self.assertEqual(CANDIDATE['contribution'],expanded['contribution'])
        self.assertEqual(before['plan'],draft['plan'])
        expanded['plan']['finding']['text']='Changed'
        self.assertEqual(before['plan'],draft['plan'])

    def test_panel_plan_projection_keeps_claim_ownership_and_drops_evidence_ids(self):
        from tests.test_overview_workflow import plan as panel_plan
        plan = validate_panel_plan(panel_plan(), NARRATIVE, EVIDENCE)
        assignments = panel_assignments(plan)
        self.assertEqual(['question'], assignments[0]['covers'] if 'covers' in assignments[0] else ['question'])
        self.assertNotIn('passages', assignments[1]['content'][0])
        self.assertEqual([plan['panels'][0]['exit_state']], assignments[1]['entry_context'])


class OverviewNarrativeContractTests(unittest.TestCase):
    """The Overview narrative contract is separate from Blog's shared validation."""

    def value(self, **overrides):
        value = copy.deepcopy(NARRATIVE)
        value.update(overrides)
        return value

    def test_a_long_overview_focus_is_accepted_while_blog_keeps_its_limit(self):
        value = self.value(visual_focus='x' * 1324)
        accepted = validate_overview_narrative(value, EVIDENCE)
        self.assertEqual(value['visual_focus'], accepted['visual_focus'])
        with self.assertRaises(PlanValidationError) as caught:
            validate_plan(value, EVIDENCE)
        self.assertTrue(any(issue['path'] == 'plan.visual_focus' for issue in caught.exception.issues))

    def test_a_step_list_is_joined_by_newlines_without_changing_words_or_order(self):
        accepted = validate_overview_narrative(
            self.value(visual_focus=['Step 1: mix values.', 'Step 2: sum weights.']), EVIDENCE)
        self.assertEqual('Step 1: mix values.\nStep 2: sum weights.', accepted['visual_focus'])

    def test_a_mixed_type_step_array_is_rejected_with_its_issue_path(self):
        with self.assertRaises(PlanValidationError) as caught:
            validate_overview_narrative(self.value(visual_focus=['Step 1', 2]), EVIDENCE)
        self.assertIn('plan.visual_focus', [issue['path'] for issue in caught.exception.issues])

    def test_unknown_passages_empty_claims_and_unsupported_types_are_rejected(self):
        cases = {
            'unknown passage': self.value(question={'text': 'Q', 'passages': ['p99999']}),
            'empty claim': self.value(finding={'text': '   ', 'passages': ['p00003']}),
            'unsupported type': self.value(paper_type='essay'),
        }
        for name, value in cases.items():
            with self.subTest(name=name), self.assertRaises(PlanValidationError) as caught:
                validate_overview_narrative(value, EVIDENCE)
            self.assertTrue(caught.exception.issues)

    def test_zero_relationships_are_allowed_and_every_supplied_one_is_validated(self):
        independent = validate_overview_narrative(self.value(relationships=[]), EVIDENCE)
        self.assertEqual([], independent['relationships'])
        with self.assertRaises(PlanValidationError):
            validate_overview_narrative(
                self.value(relationships=[{'source': 'a', 'target': 'b', 'relationship': 'r',
                                           'passages': ['p99999']}]), EVIDENCE)

    def test_the_candidate_size_limit_is_reported_as_a_resource_limit(self):
        oversized = self.value(visual_focus='x' * (OVERVIEW_CANDIDATE_MAX_BYTES + 1))
        with self.assertRaises(PlanValidationError) as caught:
            validate_overview_narrative(oversized, EVIDENCE)
        issue = caught.exception.issues[0]
        self.assertEqual('resource_limit', issue['code'])
        self.assertTrue(issue['resource_limit'])
        self.assertGreater(issue['actual'], issue['limit'])


class OverviewNarrativeRecoveryTests(unittest.TestCase):
    """Recovery is narrow: complete valid claims in one candidate, nothing borrowed."""

    def broken(self):
        value = copy.deepcopy(NARRATIVE)
        value['relationships'] = [{'source': 'a', 'target': 'b', 'relationship': 'r',
                                   'passages': ['p99999']}]
        del value['visual_focus']
        return value

    def test_recovery_derives_the_focus_and_drops_only_invalid_relationships(self):
        recovered = recover_overview_narrative([self.broken()], EVIDENCE)
        self.assertIsNotNone(recovered)
        self.assertEqual(NARRATIVE['contribution']['text'], recovered['visual_focus'])
        self.assertEqual([], recovered['relationships'])
        self.assertEqual(1, len(recovered['_recovery']['discarded_relationships']))
        self.assertEqual('contribution', recovered['_recovery']['focus_source'])
        for name in ('question', 'contribution', 'finding', 'limitation'):
            self.assertEqual(NARRATIVE[name], recovered[name])

    def test_a_candidate_without_all_four_valid_claims_is_not_recoverable(self):
        incomplete = self.broken()
        del incomplete['limitation']
        self.assertIsNone(recover_overview_narrative([incomplete], EVIDENCE))
        unlinked = self.broken()
        unlinked['finding'] = {'text': 'Finding without evidence.', 'passages': ['p99999']}
        self.assertIsNone(recover_overview_narrative([unlinked], EVIDENCE))

    def test_recovery_never_borrows_a_claim_from_another_candidate(self):
        first = self.broken()
        del first['limitation']
        second = copy.deepcopy(NARRATIVE)
        second = {'paper_type': 'method', 'visual_focus': 'ok',
                  'question': copy.deepcopy(NARRATIVE['question']),
                  'contribution': copy.deepcopy(NARRATIVE['contribution']),
                  'finding': copy.deepcopy(NARRATIVE['finding']),
                  'limitation': {'text': 'Only here.', 'passages': ['p99999']},
                  'relationships': []}
        self.assertIsNone(recover_overview_narrative([first, second], EVIDENCE))

    def test_a_fully_valid_candidate_needs_no_recovery(self):
        self.assertEqual(copy.deepcopy(NARRATIVE),
                         validate_overview_narrative(copy.deepcopy(NARRATIVE), EVIDENCE))
