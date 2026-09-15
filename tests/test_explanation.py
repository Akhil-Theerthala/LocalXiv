import copy
import json
import unittest
from papers.explanation import (BLOG_BRIEF_SCHEMA, BLOG_CONTENT_SCHEMA, BLOG_DRAFT_SCHEMA,
                                BLOG_REVISION_SCHEMA, OVERVIEW_CANDIDATE_MAX_BYTES,
                                PlanValidationError, REPAIR_DECISION_SCHEMA, REVIEW_ISSUE_SCHEMA,
                                REVIEW_RESOLUTION_SCHEMA, REVIEW_RESPONSE_SCHEMA,
                                blog_figure_assignment, candidate_digest, recover_overview_narrative,
                                validate_blog_brief, validate_blog_draft,
                                validate_overview_narrative, validate_panel_plan, validate_plan,
                                expand_candidate, panel_assignments, validate_selection)
from tests.test_agent_overviews import CANDIDATE, plan_for
from tests.test_overview_workflow import EVIDENCE, NARRATIVE


BLOG_DOCUMENT = {'passages': [{'id': 'p00001'}, {'id': 'p00002'}]}
# Frozen with the digest implementation moved verbatim from papers/agent_overviews.py. A change
# means the move stopped being verbatim or the fixture changed.
BLOG_CANDIDATE_DIGEST = '72f4f588fb8edb6d68e6c388347bd91b82130a2fa9c7651ce43554df8d309c24'


def blog_brief(**overrides):
    brief = {
        'id': 'fig1',
        'title': 'Two paths, one output',
        'paper_connection': 'Show how the two contributions combine.',
        'caption': 'The frozen path and learned update add to one output.',
        'illustrative': False,
        'passages': ['p00001'],
        'purpose': 'What happens when an input enters the adapted layer?',
        'entry_context': ['The prose has introduced the frozen weights.'],
        'exit_state': 'The reader can trace the base output and the update.',
        'construction': 'flow',
        'layout_intent': 'Input at left; frozen and trainable paths stacked in the middle.',
        'content': [{'text': 'Input reaches both paths, whose outputs are added.',
                     'kind': 'connection', 'passages': ['p00001']}],
        'exact_text': ['W₀x', 'BAx'],
        'illustrative_values': [],
    }
    brief.update(overrides)
    return brief


def blog_draft(*, figures=None, plan=None, text=None):
    figures = [blog_brief()] if figures is None else figures
    plan = plan_for() if plan is None else plan
    if text is None:
        markers = ' '.join('{{figure:' + brief['id'] + '}}' for brief in figures)
        text = ('The paper compares methods [p00001]. ' + markers).strip()
    return {'plan': plan, 'text': text, 'figures': figures}


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
        draft=blog_draft();before=copy.deepcopy(draft)
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


class BlogDraftContractTests(unittest.TestCase):
    """Blog authoring separates cited prose from validated drawing briefs."""

    def test_schemas_freeze_the_brief_draft_and_revision_fields(self):
        self.assertEqual({'text', 'kind', 'passages'}, set(BLOG_CONTENT_SCHEMA['properties']))
        self.assertEqual(
            {'id', 'title', 'paper_connection', 'caption', 'illustrative', 'passages', 'purpose',
             'entry_context', 'exit_state', 'construction', 'layout_intent', 'content',
             'exact_text', 'illustrative_values'},
            set(BLOG_BRIEF_SCHEMA['properties']))
        self.assertEqual({'plan', 'text', 'figures'}, set(BLOG_DRAFT_SCHEMA['properties']))
        self.assertEqual(3, BLOG_DRAFT_SCHEMA['properties']['figures']['maxItems'])
        self.assertIs(BLOG_DRAFT_SCHEMA, BLOG_REVISION_SCHEMA['properties']['candidate'])

    def test_markup_in_a_brief_is_rejected_as_a_structured_issue(self):
        with self.assertRaises(PlanValidationError) as caught:
            validate_blog_brief(blog_brief(caption='<div>Own it</div>'), BLOG_DOCUMENT)
        issue = next(issue for issue in caught.exception.issues if issue['path'] == 'brief.caption')
        self.assertEqual('plan_validation', issue['code'])
        self.assertIn('application owns', issue['message'])

    def test_markup_in_the_article_text_is_rejected(self):
        draft = blog_draft(text='<script>alert(1)</script> The paper compares methods [p00001].')
        with self.assertRaises(PlanValidationError) as caught:
            validate_blog_draft(draft, BLOG_DOCUMENT, 'medium')
        self.assertTrue(any(issue['path'] == 'text' and 'application owns' in issue['message']
                            for issue in caught.exception.issues))

    def test_unknown_evidence_duplicate_ids_and_unknown_construction_name_their_path(self):
        cases = {
            'brief.passages': lambda: validate_blog_brief(blog_brief(passages=['p99999']),
                                                          BLOG_DOCUMENT),
            'figures[1].id': lambda: validate_blog_draft(
                blog_draft(figures=[blog_brief(id='fig1'), blog_brief(id='fig1')]),
                BLOG_DOCUMENT, 'medium'),
            'brief.construction': lambda: validate_blog_brief(
                blog_brief(construction='origami'), BLOG_DOCUMENT),
        }
        for expected, call in cases.items():
            with self.subTest(path=expected), self.assertRaises(PlanValidationError) as caught:
                call()
            self.assertIn(expected, [issue['path'] for issue in caught.exception.issues])

    def test_mismatched_and_duplicated_markers_are_rejected_at_text(self):
        mismatched = blog_draft(figures=[blog_brief(id='fig1')],
                                text='The paper compares methods [p00001]. {{figure:fig2}}')
        with self.assertRaises(PlanValidationError) as caught:
            validate_blog_draft(mismatched, BLOG_DOCUMENT, 'medium')
        messages = ' '.join(issue['message'] for issue in caught.exception.issues)
        self.assertIn('fig2', messages)
        self.assertIn('fig1', messages)
        self.assertTrue(all(issue['path'] == 'text' for issue in caught.exception.issues))
        duplicated = blog_draft(figures=[blog_brief(id='fig1')],
                                text='The paper compares methods [p00001]. '
                                     '{{figure:fig1}} {{figure:fig1}}')
        with self.assertRaises(PlanValidationError) as caught:
            validate_blog_draft(duplicated, BLOG_DOCUMENT, 'medium')
        self.assertTrue(any(issue['path'] == 'text' and 'repeats' in issue['message']
                            for issue in caught.exception.issues))

    def test_zero_figures_sparse_ids_and_ordering(self):
        zero = blog_draft(figures=[], text='The paper compares methods [p00001].')
        self.assertEqual([], validate_blog_draft(zero, BLOG_DOCUMENT, 'medium')['figures'])
        sparse = blog_draft(figures=[blog_brief(id='fig1'), blog_brief(id='fig3')])
        accepted = validate_blog_draft(sparse, BLOG_DOCUMENT, 'medium')
        self.assertEqual(['fig1', 'fig3'], [brief['id'] for brief in accepted['figures']])
        descending = blog_draft(figures=[blog_brief(id='fig3'), blog_brief(id='fig1')])
        with self.assertRaises(PlanValidationError) as caught:
            validate_blog_draft(descending, BLOG_DOCUMENT, 'medium')
        self.assertIn('figures[1].id', [issue['path'] for issue in caught.exception.issues])

    def test_a_valid_draft_returns_derived_metadata_and_unique_passages(self):
        accepted = validate_blog_draft(blog_draft(), BLOG_DOCUMENT, 'medium')
        self.assertEqual(plan_for(), accepted['plan'])
        self.assertEqual('evaluation', accepted['paper_type'])
        self.assertEqual(plan_for()['question']['text'], accepted['question'])
        self.assertEqual(plan_for()['contribution']['text'], accepted['contribution'])
        self.assertEqual(plan_for()['finding']['text'], accepted['finding'])
        self.assertEqual(plan_for()['limitation']['text'], accepted['limitation'])
        self.assertEqual(['p00001'], accepted['passages'])
        self.assertEqual(['fig1'], [brief['id'] for brief in accepted['figures']])

    def test_the_assignment_projection_drops_evidence_and_keeps_layout(self):
        brief = validate_blog_brief(blog_brief(), BLOG_DOCUMENT)
        assignment = blog_figure_assignment(brief)
        self.assertEqual('fig1', assignment['id'])
        self.assertEqual(brief['exact_text'], assignment['exact_text'])
        self.assertEqual(brief['layout_intent'], assignment['layout_intent'])
        self.assertEqual({}, assignment['shared_facts'])
        dumped = json.dumps(assignment)
        self.assertNotIn('passages', dumped)
        self.assertNotIn('p00001', dumped)

    def test_the_candidate_digest_is_frozen_and_key_order_independent(self):
        self.assertEqual(BLOG_CANDIDATE_DIGEST, candidate_digest(CANDIDATE))
        reordered = {key: CANDIDATE[key] for key in reversed(list(CANDIDATE))}
        self.assertEqual(BLOG_CANDIDATE_DIGEST, candidate_digest(reordered))
        self.assertEqual(64, len(BLOG_CANDIDATE_DIGEST))

    def test_illustrative_content_may_omit_citations_but_a_brief_needs_evidence(self):
        illustrative = blog_brief(content=[{'text': 'A concrete illustrative input.',
                                            'kind': 'statement'}])
        accepted = validate_blog_brief(illustrative, BLOG_DOCUMENT)
        self.assertNotIn('passages', accepted['content'][0])
        for passages in ([], ['p99999']):
            with self.subTest(passages=passages), self.assertRaises(PlanValidationError) as caught:
                validate_blog_brief(blog_brief(passages=passages), BLOG_DOCUMENT)
            self.assertIn('brief.passages', [issue['path'] for issue in caught.exception.issues])

    def test_a_corrected_brief_must_keep_its_stable_id(self):
        with self.assertRaises(PlanValidationError) as caught:
            validate_blog_brief(blog_brief(id='fig2'), BLOG_DOCUMENT, figure_id='fig1')
        self.assertIn('brief.id', [issue['path'] for issue in caught.exception.issues])


class BlogReviewContractTests(unittest.TestCase):
    """The Blog review separates open findings from explicit, quoted resolutions."""

    def test_the_review_response_freezes_anchors_resolutions_and_candidate_identity(self):
        verdict = REVIEW_RESPONSE_SCHEMA['anyOf'][0]['properties']
        self.assertEqual({'action', 'approved', 'candidate_digest', 'issues', 'resolutions'}, set(verdict))
        self.assertEqual({'category', 'path', 'message', 'passages', 'anchor'},
                         set(REVIEW_ISSUE_SCHEMA['properties']))
        self.assertEqual({'id', 'quote', 'explanation'}, set(REVIEW_RESOLUTION_SCHEMA['properties']))
        self.assertEqual(['verdict', 'read_evidence'],
                         [item['properties']['action']['enum'][0]
                          for item in REVIEW_RESPONSE_SCHEMA['anyOf']])
        self.assertIn('visible content', REVIEW_ISSUE_SCHEMA['properties']['anchor']['description'])
