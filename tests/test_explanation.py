import copy
import unittest
from papers.explanation import (REPAIR_DECISION_SCHEMA, validate_panel_plan, validate_plan,
                                expand_candidate, panel_assignments, validate_selection)
from tests.test_agent_overviews import CANDIDATE, plan_for, draft_for


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
        from tests.test_overview_workflow import EVIDENCE, NARRATIVE, plan as panel_plan
        plan = validate_panel_plan(panel_plan(), NARRATIVE, EVIDENCE)
        assignments = panel_assignments(plan)
        self.assertEqual(['question'], assignments[0]['covers'] if 'covers' in assignments[0] else ['question'])
        self.assertNotIn('passages', assignments[1]['content'][0])
        self.assertEqual([plan['panels'][0]['exit_state']], assignments[1]['entry_context'])
