"""Panel authoring: prompt contract, one-shot requests, local checks, and simple recovery."""
import json
import os
import tempfile
import unittest

from papers.ai import ProviderError
from papers import html_figures, panel_authoring
from papers.arrangement import arrange, fit_layout, panel_record, shrink_fit_layout
from papers.explanation import blog_figure_assignment, panel_assignments, validate_panel_plan
from papers.panel_authoring import (assignment_block, check_panel, missing_values, panel_messages,
                                    request_panel, required_values, simple_panel,
                                    simple_panel_source)

NATIVE = os.environ.get('LOCALXIV_HTML_RENDERER')


def assignment(**overrides):
    value = {
        'id': 'p2',
        'title': 'Mixing two values',
        'purpose': 'Show how attention weights combine two value vectors.',
        'entry_context': ['The reader knows one token scores every candidate.'],
        'content': [
            {'text': 'The client counter starts at 8,532,412 and increases by one.', 'kind': 'value'},
            {'text': 'reply = 0.73 v1 + 0.27 v2', 'kind': 'equation'},
            {'text': 'Neither side knows the other starting value.', 'kind': 'statement'},
        ],
        'exit_state': 'The output is a weighted blend of the two value vectors.',
        'shared_facts': {'candidate_probabilities': '0.73 and 0.27', 'client_counter': '8,532,412'},
        'illustrative_values': ['0.73 and 0.27'],
        'exact_text': ['0.73 and 0.27', 'reply = 0.73 v1 + 0.27 v2'],
        'construction': 'calculation',
    }
    value.update(overrides)
    return value


def blog_brief(**overrides):
    value = {
        'id': 'fig1',
        'title': 'Two paths, one output',
        'paper_connection': 'Show how the two paths combine.',
        'caption': 'The frozen path and the learned update add to one output.',
        'illustrative': False,
        'passages': ['p00001'],
        'purpose': 'What happens when an input enters the adapted layer?',
        'entry_context': ['The prose has introduced the frozen weights.'],
        'exit_state': 'The reader can trace the base output and the update.',
        'construction': 'flow',
        'layout_intent': ('Input at left; frozen and trainable paths stacked in the middle; '
                          'addition and output at right.'),
        'content': [{'text': 'Input reaches both paths, whose outputs are added.',
                     'kind': 'connection', 'passages': ['p00001']}],
        'exact_text': ['W₀x', 'BAx'],
        'illustrative_values': [],
    }
    value.update(overrides)
    return value


def drawn_svg(body=None, width=640, height=320):
    body = body if body is not None else (
        '<text x="40" y="60" font-size="22" font-weight="bold">Mixing two values</text>'
        '<text x="40" y="110" font-size="18">The client counter starts at 8,532,412 and increases by one.</text>'
        '<text x="40" y="150" font-size="18" font-weight="bold">reply = 0.73 v1 + 0.27 v2</text>'
        '<text x="40" y="190" font-size="18">Neither side knows the other starting value.</text>'
        '<text x="40" y="240" font-size="14">0.73 and 0.27</text>')
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + str(width) + ' ' + str(height)
            + '" font-family="Arial, sans-serif" font-size="18" fill="#243b32">' + body + '</svg>')


class PromptTests(unittest.TestCase):
    def test_the_prompt_carries_the_assignment_values_and_no_planning_context(self):
        serialized = json.dumps(panel_messages(assignment()))
        self.assertIn('8,532,412', serialized)
        self.assertIn('0.73 and 0.27', serialized)
        self.assertIn('illustrative teaching values', serialized)
        self.assertIn('exact display text that must appear in the drawing unchanged', serialized)
        self.assertIn('semantic facts and values for this panel', serialized)
        self.assertNotIn('retrieved_evidence', serialized)
        self.assertNotIn('request_narrative_revision', serialized)
        self.assertNotIn('0.75 and 1.33', serialized)
        self.assertNotIn('entire narrative', serialized)
        for tool in ('submit_candidate', 'read_evidence', 'submit_figure_repair'):
            self.assertNotIn(tool, serialized)

    def test_the_prompt_follows_the_agreed_order_and_attaches_relevant_examples(self):
        text = panel_messages(assignment())[-1]['content']
        positions = [text.index('DRAWING ASSIGNMENT'), text.index('COMPLETE REFERENCE EXAMPLE'),
                     text.index('APPLICABLE CONSTRUCTION NOTES'), text.index('COMMON DRAWING GUIDE'),
                     text.index('Return one JSON object')]
        self.assertEqual(sorted(positions), positions)
        self.assertIn('<svg', text.split('COMPLETE REFERENCE EXAMPLE')[1])
        calculation = panel_authoring.reference_examples('calculation')
        self.assertEqual(['calculation', 'chart'], [example['family'] for example in calculation])
        self.assertLessEqual(len(calculation), 2)

    def test_a_repair_prompt_carries_only_this_panel_and_its_concrete_defects(self):
        messages = panel_messages(assignment(), previous=drawn_svg(),
                                  issues=['Label is 210 units wide but its container is 180 units wide.'])
        text = messages[-1]['content']
        self.assertIn('PREVIOUS DRAWING TO REPAIR', text)
        self.assertIn('its container is 180 units wide', text)
        self.assertIn('Change only what these defects require', text)
        self.assertNotIn('p1', text.split('DRAWING ASSIGNMENT')[0])
        self.assertIn('panel id: p2', text)

    def test_exact_display_text_is_required_verbatim_but_semantic_prose_is_not(self):
        value = assignment(
            shared_facts={}, exact_text=['reply = 0.73 v1 + 0.27 v2'],
            content=[{'kind': 'equation', 'text': 'reply = 0.73 v1 + 0.27 v2'},
                     {'kind': 'statement',
                      'text': 'The encoder turns the input into two vectors, one per candidate.'}])
        drawn = ['reply = 0.73 v1 + 0.27 v2', 'two labelled layers feed two vectors']
        self.assertEqual([], missing_values(value, drawn),
                         'an encoder paragraph expressed visually need not appear as a sentence')
        self.assertTrue(missing_values(value, ['reply = 0.73 v1 - 0.27 v2']),
                        'a changed operator is not the declared equation')

    def test_changed_values_units_and_missing_labels_are_reported(self):
        value = assignment(shared_facts={}, exact_text=['0.73', '11.7 ms'],
                           content=[{'kind': 'label', 'text': '11.7 ms'}])
        self.assertEqual(['11.7 ms'], missing_values(value, ['0.73', '11.7ms']))
        self.assertIn('11.7 ms', missing_values(value, ['0.73', '11.7 seconds']))
        self.assertEqual([], missing_values(value, ['0.73', '11.7 ms']))

    def test_every_declared_exact_string_and_value_number_is_required(self):
        self.assertEqual(['0.73 and 0.27', 'reply = 0.73 v1 + 0.27 v2', '8,532,412'],
                         required_values(assignment()))
        self.assertEqual([], missing_values(assignment(), ['reply = 0.73 v1 + 0.27 v2',
                                                           'the counter reaches 8,532,412',
                                                           '0.73 and 0.27']))
        self.assertIn('8,532,412', missing_values(assignment(), ['reply = 0.73 v1 + 0.27 v2',
                                                                 '0.73 and 0.27']),
                      'a dropped number from a value item is still reported')

    def test_a_numeric_omission_is_named_as_a_limited_check(self):
        from papers.panel_authoring import missing_value_details
        details = missing_value_details(assignment(), ['reply = 0.73 v1 + 0.27 v2', '0.73 and 0.27'])
        number = next(item for item in details if item['kind'] == 'number')
        self.assertIn('limited numeric omission check', number['message'])
        self.assertIn('does not verify', number['message'])

    def test_blog_prompts_carry_layout_intent_and_article_width_guidance(self):
        projected = blog_figure_assignment(blog_brief())
        text = panel_messages(projected, purpose='blog')[-1]['content']
        self.assertIn('layout intent: ' + projected['layout_intent'], text)
        self.assertIn('640px wide', text)
        self.assertIn('640-unit-wide viewBox', text)
        self.assertIn('18px body labels', text)
        self.assertIn('below 14px', text)
        self.assertIn('labels, values, and necessary equations', text)
        self.assertIn('The application owns the', text)

    def test_blog_prompts_keep_the_request_order_contract_and_no_planning_context(self):
        projected = blog_figure_assignment(blog_brief())
        text = panel_messages(projected, purpose='blog')[-1]['content']
        positions = [text.index('DRAWING ASSIGNMENT'), text.index('COMPLETE REFERENCE EXAMPLE'),
                     text.index('APPLICABLE CONSTRUCTION NOTES'), text.index('COMMON DRAWING GUIDE'),
                     text.index('Return one JSON object')]
        self.assertEqual(sorted(positions), positions)
        self.assertIn('Return one JSON object with exactly two fields', text)
        self.assertIn('"panel_id": "fig1"', text)
        self.assertIn('"svg"', text)
        self.assertNotIn('retrieved_evidence', text)
        self.assertNotIn('p00001', text)
        self.assertNotIn('sibling', text)
        self.assertNotIn('entire narrative', text)
        self.assertNotIn('submit_candidate', text)
        self.assertNotIn('passages', json.dumps(projected))
        self.assertNotIn('p00001', json.dumps(projected))
        self.assertNotIn('SHARED STORY CONTEXT', text)

    def test_overview_prompts_are_unchanged_without_layout_intent(self):
        value = assignment()
        baseline = assignment_block(value)
        self.assertEqual(baseline, assignment_block(value, purpose='overview'))
        self.assertNotIn('layout intent:', baseline)
        self.assertNotIn('BLOG FIGURE GUIDANCE', baseline)
        self.assertEqual(panel_messages(value), panel_messages(value, purpose='overview'))

    def test_an_invalid_purpose_is_rejected(self):
        value = assignment()
        for purpose in ('overview', 'blog'):
            self.assertIn('DRAWING ASSIGNMENT', assignment_block(value, purpose=purpose))
        for purpose in ('', 'panels', 'BLOG', None, 1):
            with self.subTest(purpose=repr(purpose)):
                with self.assertRaises(ValueError):
                    assignment_block(value, purpose=purpose)
                with self.assertRaises(ValueError):
                    panel_messages(value, purpose=purpose)

    def test_overview_prompts_carry_the_shared_story_once_and_blog_never_does(self):
        story = ('Follow one token through attention mixing. '
                 'It mixes values by attention weights.')
        overview = dict(assignment(), story_context=story)
        text = panel_messages(overview)[-1]['content']
        self.assertIn('SHARED STORY CONTEXT', text)
        self.assertIn(story, text)
        self.assertEqual(1, text.count(story))
        self.assertNotIn('retrieved_evidence', text)
        blog = dict(blog_figure_assignment(blog_brief()), story_context=story)
        blog_text = panel_messages(blog, purpose='blog')[-1]['content']
        self.assertNotIn('SHARED STORY CONTEXT', blog_text)
        self.assertIn('BLOG FIGURE GUIDANCE', blog_text)
        self.assertNotIn(story, blog_text)
        self.assertNotIn('SHARED STORY CONTEXT',
                         panel_messages(dict(assignment(), story_context=''))[-1]['content'])

    def test_the_repair_prompt_keeps_the_same_assignment_and_story(self):
        story = 'Follow one token through attention mixing. It mixes values by attention weights.'
        value = dict(assignment(), story_context=story)
        messages = panel_messages(value, previous=drawn_svg(), issues=['Label exceeds its box.'])
        text = messages[-1]['content']
        self.assertIn('SHARED STORY CONTEXT', text)
        self.assertIn(story, text)
        self.assertIn('assignment', text.lower())
        self.assertEqual(text.index('DRAWING ASSIGNMENT'), 0)
        self.assertGreater(text.index('SHARED STORY CONTEXT'), text.index('DRAWING ASSIGNMENT'))
        self.assertLess(text.index('SHARED STORY CONTEXT'), text.index('COMPLETE REFERENCE EXAMPLE'))


class RequestTests(unittest.TestCase):
    class Provider:
        def __init__(self, answer):
            self.settings = {'endpoint': 'https://example.test/v1', 'model': 'scripted'}
            self.answer = answer
            self.calls = 0
            self.messages = []

        def complete(self, messages, **kwargs):
            self.calls += 1
            self.messages.append(messages)
            if isinstance(self.answer, Exception):
                raise self.answer
            return {'text': self.answer if isinstance(self.answer, str) else json.dumps(self.answer),
                    'usage': {'total_tokens': 11}}

    def test_a_complete_first_attempt_returns_a_safe_normalized_document(self):
        provider = self.Provider({'panel_id': 'p2', 'svg': drawn_svg()})
        result = request_panel(provider, assignment())
        self.assertIsNone(result['error'])
        self.assertEqual({'total_tokens': 11}, result['usage'])
        self.assertIn('xmlns="http://www.w3.org/2000/svg"', result['source'])
        self.assertEqual('p2', result['diagnostics']['panel_id'])
        self.assertEqual(1, provider.calls)

    def test_malformed_json_wrong_panel_id_and_unsafe_svg_are_invalid_output(self):
        unsafe = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
                  '<script>x()</script></svg>')
        answers = {'malformed json': 'not json at all',
                   'wrong panel id': {'panel_id': 'p1', 'svg': drawn_svg()},
                   'unsafe svg': {'panel_id': 'p2', 'svg': unsafe}}
        for name, answer in answers.items():
            with self.subTest(name=name):
                result = request_panel(self.Provider(answer), assignment())
                self.assertIsNone(result['source'])
                self.assertEqual('invalid_output', result['error_kind'])
                self.assertTrue(result['error'])
                self.assertEqual('p2', result['diagnostics']['panel_id'])

    def test_transport_and_authentication_failures_are_reported_differently(self):
        for message, kind in [('Provider request failed or returned an invalid response.', 'transport'),
                              ('Provider rejected authentication. Check the saved key and model access.',
                               'authentication')]:
            with self.subTest(kind=kind):
                result = request_panel(self.Provider(ProviderError(message)), assignment())
                self.assertIsNone(result['source'])
                self.assertEqual(kind, result['error_kind'])
                self.assertIn(message.split('.')[0], result['error'])

    def test_blog_purpose_forwards_guidance_and_keeps_the_return_shape(self):
        provider = self.Provider({'panel_id': 'fig1', 'svg': drawn_svg()})
        value = blog_figure_assignment(blog_brief())
        result = request_panel(provider, value, purpose='blog')
        self.assertEqual({'source', 'error', 'error_kind', 'usage', 'diagnostics'}, set(result))
        self.assertIsNone(result['error'])
        self.assertEqual('fig1', result['diagnostics']['panel_id'])
        self.assertEqual(1, provider.calls)
        sent = json.dumps(provider.messages[0])
        self.assertIn('BLOG FIGURE GUIDANCE', sent)
        self.assertIn('layout intent: ' + value['layout_intent'], sent)
        self.assertNotIn('p00001', sent)
        self.assertNotIn('story_context', value)
        self.assertNotIn('SHARED STORY CONTEXT', sent)
        self.assertEqual(['system', 'user'], [message['role'] for message in provider.messages[0]])

    def test_an_invalid_purpose_makes_no_provider_request(self):
        provider = self.Provider({'panel_id': 'p2', 'svg': drawn_svg()})
        with self.assertRaises(ValueError):
            request_panel(provider, assignment(), purpose='blog-ish')
        self.assertEqual(0, provider.calls)


@unittest.skipUnless(NATIVE, 'Set LOCALXIV_HTML_RENDERER for native rendering checks')
class NativePanelTests(unittest.TestCase):
    def test_a_drawn_panel_renders_and_reports_its_visible_labels(self):
        with tempfile.TemporaryDirectory() as directory:
            result = check_panel(drawn_svg(), directory, 'p2')
        self.assertEqual([], result['checks']['issue_details'])
        self.assertEqual(14, min(run['displayed_size_px'] for run in result['checks']['text_runs']))
        self.assertEqual([], missing_values(assignment(), result['labels']))
        self.assertEqual({'html', 'svg', 'png', 'pdf', 'svg_source'}, set(result['assets']))

    def test_a_drawing_that_renders_with_geometry_defects_is_not_a_success(self):
        small = drawn_svg('<text x="40" y="60" font-size="9">too small to read</text>')
        with tempfile.TemporaryDirectory() as directory:
            result = check_panel(small, directory, 'p2')
        codes = {issue['code'] for issue in result['checks']['issue_details']}
        self.assertIn('text_too_small', codes)

    def test_source_notation_survives_recovery_literally_and_is_identified(self):
        notation = r'\frac{a+b}{c+d}'
        value = assignment(exact_text=[notation], shared_facts={}, illustrative_values=[],
                           content=[{'text': notation, 'kind': 'equation'},
                                    {'text': 'A note on the fraction.', 'kind': 'statement'}])
        with tempfile.TemporaryDirectory() as directory:
            result = simple_panel(value, directory)
        visible = ' '.join(result['labels'])
        self.assertEqual([], result['checks']['issue_details'])
        self.assertIn(notation, visible)
        self.assertNotIn('a + b / c + d', visible, 'grouping is never silently rewritten')
        self.assertIn('source notation', visible.lower())
        self.assertEqual('source notation preserved literally, not re-rendered',
                         result['reduced_presentation'])
        self.assertIn(notation, result['source_notation'])

    def test_recovery_keeps_source_notation_and_the_illustrative_label(self):
        value = assignment(
            exact_text=['positions $<i$'], shared_facts={},
            illustrative_values=['0.73 and 0.27'],
            content=[{'text': 'Predictions depend on positions $<i$ and earlier ones.',
                      'kind': 'statement'}])
        with tempfile.TemporaryDirectory() as directory:
            result = simple_panel(value, directory)
        visible = ' '.join(result['labels'])
        self.assertEqual([], result['checks']['issue_details'])
        self.assertIn('positions $<i$', visible)
        self.assertIn('illustrative', visible.lower())
        self.assertIn('0.73 and 0.27', visible)

    def test_an_unsafe_document_is_rejected_before_any_render(self):
        with self.assertRaises(ValueError):
            check_panel('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200">'
                        '<script>alert(1)</script></svg>', '/tmp', 'p2')

    def test_a_changed_operator_in_a_drawn_panel_is_reported(self):
        value = assignment(shared_facts={}, exact_text=['reply = 0.73 v1 + 0.27 v2'],
                           content=[{'text': 'reply = 0.73 v1 + 0.27 v2', 'kind': 'equation'}])
        wrong = drawn_svg('<text x="40" y="60" font-size="18">reply = 0.73 v1 - 0.27 v2</text>')
        right = drawn_svg('<text x="40" y="60" font-size="18">reply = 0.73 v1 + 0.27 v2</text>')
        with tempfile.TemporaryDirectory() as directory:
            changed = check_panel(wrong, directory, 'p2')
            accepted = check_panel(right, directory, 'p2')
        self.assertIn('reply = 0.73 v1 + 0.27 v2', missing_values(value, changed['labels']))
        self.assertEqual([], missing_values(value, accepted['labels']))

    def test_a_missing_declared_label_is_reported_from_visible_text(self):
        value = assignment(shared_facts={}, exact_text=['encoder'],
                           content=[{'text': 'encoder', 'kind': 'label'}])
        without = drawn_svg('<text x="40" y="60" font-size="18">two layers</text>')
        with tempfile.TemporaryDirectory() as directory:
            result = check_panel(without, directory, 'p2')
        self.assertEqual(['encoder'], missing_values(value, result['labels']))

    def test_a_missing_exact_value_is_reported_against_the_drawing(self):
        without_value = drawn_svg('<text x="40" y="60" font-size="18">Mixing two values</text>')
        with tempfile.TemporaryDirectory() as directory:
            result = check_panel(without_value, directory, 'p2')
        self.assertIn('8,532,412', missing_values(assignment(), result['labels']))

    def test_simple_recovery_keeps_the_content_and_marks_illustrative_values(self):
        with tempfile.TemporaryDirectory() as directory:
            result = simple_panel(assignment(), directory)
        self.assertTrue(result['simplified'])
        self.assertEqual([], result['checks']['issue_details'])
        self.assertEqual([], missing_values(assignment(), result['labels']))
        self.assertIn('illustrative values, not paper results', result['labels'])
        self.assertIn('8,532,412', ' '.join(result['labels']))
        self.assertLess(result['checks']['canvas']['width'], 1000)

    def test_simple_recovery_escapes_xml_hostile_content(self):
        """A live run died on 'positions $<i$' because the recovery emitted a raw <."""
        hostile = assignment(content=[{'text': 'Predictions depend on positions $<i$ & earlier ones.',
                                       'kind': 'statement'},
                                      {'text': 'R&D <baseline> > ours', 'kind': 'value'}],
                             shared_facts={'notation': 'a < b & c > d'})
        with tempfile.TemporaryDirectory() as directory:
            result = simple_panel(hostile, directory)
        self.assertEqual([], result['checks']['issue_details'])
        self.assertIn('<i$ & earlier', ' '.join(result['labels']))
        self.assertIn('R&D <baseline> > ours', ' '.join(result['labels']))

    def test_simple_recovery_handles_quotes_non_ascii_and_long_labels(self):
        hostile = assignment(
            content=[{'text': 'The paper calls this "soft" mixing — naïve at first, ≥ 0.73 later.',
                      'kind': 'statement'}],
            shared_facts={'candidate_probabilities': '0.73 and 0.27'},
            exact_text=['0.73 and 0.27'], illustrative_values=['0.73 and 0.27'])
        with tempfile.TemporaryDirectory() as directory:
            result = simple_panel(hostile, directory)
        visible = ' '.join(result['labels'])
        self.assertEqual([], result['checks']['issue_details'])
        self.assertIn('"soft" mixing — naïve at first, ≥ 0.73 later', visible)
        self.assertEqual([], missing_values(hostile, result['labels']))

    def test_simple_recovery_wraps_with_measured_widths_inside_its_canvas(self):
        long_text = assignment(content=[{'text': 'word ' * 220, 'kind': 'statement'}])
        with tempfile.TemporaryDirectory() as directory:
            result = simple_panel(long_text, directory)
        self.assertEqual([], result['checks']['issue_details'])
        self.assertGreater(result['checks']['canvas']['height'], 400)
        self.assertGreater(len(result['checks']['text_runs']), 8)
        for run in result['checks']['text_runs']:
            self.assertGreaterEqual(run['displayed_size_px'], 14)

    def test_assignments_from_a_validated_plan_drive_the_same_checks(self):
        plan = {'title': 'Overview', 'paper_connection': 'A', 'caption': 'B', 'shared_facts': {},
                'panels': [{'id': 'p1', 'title': 'Question', 'purpose': 'Purpose',
                            'covers': ['question', 'contribution', 'finding', 'limitation'],
                            'entry_from': [], 'exit_state': 'State', 'shared_fact_ids': [],
                            'content': [{'text': 'A retained claim.', 'passages': ['p00001'],
                                         'kind': 'statement'}],
                            'construction': 'flow'}]}
        narrative = {name: {'text': name, 'passages': ['p00001']}
                     for name in ('question', 'contribution', 'finding', 'limitation')}
        narrative['relationships'] = [{'source': 'a', 'target': 'b', 'relationship': 'r',
                                       'passages': ['p00001']}]
        evidence = {'passages': [{'id': 'p00001', 'section': 'Body', 'text': 'Retained text'}]}
        projected = panel_assignments(validate_panel_plan(plan, narrative, evidence))
        self.assertEqual([], projected[0]['illustrative_values'])
        self.assertEqual({'id', 'title', 'purpose', 'entry_context', 'content', 'exit_state',
                          'shared_facts', 'illustrative_values', 'exact_text',
                          'construction'}, set(projected[0]))


class ArrangementTests(unittest.TestCase):
    def measured(self, count, *, width=520, height=300, body=18):
        return [{'id': f'p{index + 1}', 'width': width + index * 20, 'height': height + index * 15,
                 'body_size': body} for index in range(count)]

    def test_one_four_and_seven_panels_keep_planned_order_inside_the_canvas(self):
        for count in (1, 4, 7):
            with self.subTest(count=count):
                panels = self.measured(count)
                layout = arrange(panels)
                self.assertEqual([panel['id'] for panel in panels],
                                 [placement['id'] for placement in layout['placements']])
                self.assertEqual(list(range(1, count + 1)),
                                 [placement['number'] for placement in layout['placements']])
                for placement in layout['placements']:
                    self.assertGreaterEqual(placement['x'], 0)
                    self.assertGreaterEqual(placement['y'], 0)
                    self.assertLessEqual(placement['x'] + placement['width'], layout['canvas']['width'])
                    self.assertLessEqual(placement['y'] + placement['height'], layout['canvas']['height'])

    def test_panels_are_placed_row_major_and_never_intersect(self):
        for panels in (self.measured(7, width=300, height=220),
                       [{'id': 'p1', 'width': 200, 'height': 300, 'body_size': 18},
                        {'id': 'p2', 'width': 200, 'height': 300, 'body_size': 18},
                        {'id': 'p3', 'width': 200, 'height': 300, 'body_size': 18},
                        {'id': 'p4', 'width': 900, 'height': 320, 'body_size': 18}]):
            with self.subTest(count=len(panels)):
                layout = arrange(panels)
                placements = layout['placements']
                for index, first in enumerate(placements):
                    for second in placements[index + 1:]:
                        overlaps = (first['x'] < second['x'] + second['width']
                                    and second['x'] < first['x'] + first['width']
                                    and first['y'] < second['y'] + second['height']
                                    and second['y'] < first['y'] + first['height'])
                        self.assertFalse(overlaps, f"{first['id']} overlaps {second['id']}")
                for index, first in enumerate(placements):
                    for second in placements[index + 1:]:
                        self.assertTrue(second['x'] >= first['x'] + first['width']
                                        or second['y'] >= first['y'] + first['height'],
                                        f"{second['id']} is not later in reading order than {first['id']}")
                self.assertEqual(list(range(1, len(placements) + 1)),
                                 [placement['number'] for placement in placements])

    def test_a_mixed_width_plan_uses_more_than_one_column(self):
        layout = arrange([{'id': 'p1', 'width': 200, 'height': 300, 'body_size': 18},
                          {'id': 'p2', 'width': 200, 'height': 300, 'body_size': 18},
                          {'id': 'p3', 'width': 200, 'height': 300, 'body_size': 18},
                          {'id': 'p4', 'width': 900, 'height': 320, 'body_size': 18}])
        self.assertGreaterEqual(layout['columns'], 2)
        self.assertEqual(['p1', 'p2', 'p3', 'p4'], [p['id'] for p in layout['placements']])

    def test_body_text_is_normalised_to_one_shared_size_without_reordering(self):
        panels = [{'id': 'p1', 'width': 800, 'height': 400, 'body_size': 40},
                  {'id': 'p2', 'width': 300, 'height': 200, 'body_size': 9}]
        layout = arrange(panels)
        self.assertEqual([0.45, 2.0], [layout['scales']['p1'], layout['scales']['p2']])
        self.assertEqual([360.0, 600.0], [layout['placements'][0]['width'],
                                          layout['placements'][1]['width']])

    def test_zero_panels_is_invalid(self):
        with self.assertRaises(ValueError):
            arrange([])

    def test_phase_frames_follow_content_without_forcing_an_aspect_ratio(self):
        panels = [{'id': f'p{i}', 'width': width, 'height': height, 'body_size': 18}
                  for i, (width, height) in enumerate(
                      [(1800, 668), (1157, 797), (1157, 797), (900, 280)], 1)]
        layout = arrange(panels)
        ratio = layout['canvas']['width'] / layout['canvas']['height']
        self.assertGreater(ratio, 0.0)
        placements = layout['placements']
        for index, placement in enumerate(placements):
            frame = placement['frame']
            self.assertGreater(placement['x'], frame['x'])
            self.assertGreater(placement['y'], frame['y'])
            self.assertLessEqual(placement['x'] + placement['width'], frame['x'] + frame['width'])
            self.assertLessEqual(placement['y'] + placement['height'], frame['y'] + frame['height'])
            for other in placements[index + 1:]:
                second = other['frame']
                if frame['y'] == second['y']:
                    self.assertEqual(placement['y'], other['y'])
                    self.assertEqual(frame['height'], second['height'])
                    self.assertLessEqual(frame['x'] + frame['width'], second['x'])
                else:
                    self.assertLessEqual(frame['y'] + frame['height'], second['y'])

    def test_native_bounds_fit_the_frame_and_keep_degenerate_lines(self):
        source = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 500" '
                  'font-size="18"><rect x="120" y="100" width="260" height="160"/>'
                  '<line x1="60" y1="360" x2="900" y2="360" stroke="#243b32"/></svg>')
        checks = {'elements': [{'left': 120, 'top': 100, 'right': 380, 'bottom': 260},
                               # WebKit reports a horizontal line with equal top/bottom.
                               {'left': 60, 'top': 360, 'right': 900, 'bottom': 360}]}
        layout = arrange([panel_record('p1', source, checks=checks)])
        placement = layout['placements'][0]
        frame = placement['frame']
        self.assertEqual(840.0, placement['width'])
        self.assertEqual(260.0, placement['height'])
        self.assertEqual(872.0, frame['width'])
        self.assertEqual(328.0, frame['height'])
        self.assertLess(placement['x'], frame['x'])
        self.assertAlmostEqual(frame['x'] + 16.0, placement['x'] + 60.0)
        self.assertAlmostEqual(frame['y'] + 16.0 + 36.0, placement['y'] + 100.0)

    def test_panel_record_prefers_native_rendered_text_size_over_static_font_attributes(self):
        source = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 240" '
                  'font-size="20"><g transform="scale(.8)"><text x="20" y="40">Label</text></g></svg>')
        record = panel_record('p1', source, checks={
            'text_runs': [{'displayed_size_px': 16}, {'displayed_size_px': 14}],
            'elements': [{'left': 16, 'top': 0, 'right': 300, 'bottom': 160}],
        })
        self.assertEqual(14, record['native_min_text_size'])
        self.assertTrue(record['native_text_measured'])

    def test_arrangement_bounds_the_row_search_to_seven_panels(self):
        with self.assertRaises(ValueError):
            arrange(self.measured(8))

    def test_the_arrangement_never_shrinks_a_panel_below_its_measured_size(self):
        panels = self.measured(3, width=400, height=260, body=14)
        layout = arrange(panels)
        self.assertGreater(layout['scales']['p1'], 1.0)
        for placement, panel in zip(layout['placements'], panels):
            self.assertGreaterEqual(placement['width'], panel['width'])

    def seed_layout(self, panels, frames, canvas):
        """Build the public group coordinates that correspond to these decorated seed frames."""
        return {'canvas': {'width': canvas[0], 'height': canvas[1]},
                'placements': [
                    {'id': panel['id'], 'x': frame[0] + 16, 'y': frame[1] + 36 + 16,
                     'width': panel['width'], 'height': panel['height'], 'scale': 1.0,
                     'number': index + 1}
                    for index, (panel, frame) in enumerate(zip(panels, frames))],
                'columns': 3}

    def test_gap_fit_uses_shared_slack_and_preserves_every_facing_neighbour(self):
        panels = [{'id': identifier, 'width': width, 'height': height, 'body_size': 18}
                  for identifier, width, height in (('a', 150, 90), ('b', 90, 70),
                                                    ('c', 90, 70))]
        seed = self.seed_layout(panels, [(20, 20), (250, 20), (250, 140)], (520, 360))
        fitted = fit_layout(panels, seed)
        self.assertTrue(fitted['fit']['feasible'])
        self.assertGreater(fitted['fit']['remaining_whitespace']['final_occupancy_same_envelope'],
                           fitted['fit']['remaining_whitespace']['seed_occupancy_same_envelope'])
        self.assertGreater(fitted['fit']['growth']['a'], 1.0)
        neighbours = {(item['first'], item['second'], axis)
                      for item in fitted['fit']['neighbours'] for axis in item['axes']}
        self.assertIn(('a', 'b', 'x'), neighbours)
        self.assertIn(('a', 'c', 'x'), neighbours)
        self.assertIn(('b', 'c', 'y'), neighbours)
        for gap in fitted['fit']['gaps']:
            self.assertGreaterEqual(gap['actual'], gap['required'] - 0.02)

    def test_gap_fit_gives_unblocked_diagonal_panels_different_scales(self):
        panels = [{'id': 'a', 'width': 170, 'height': 55, 'body_size': 18},
                  {'id': 'b', 'width': 90, 'height': 55, 'body_size': 18}]
        seed = self.seed_layout(panels, [(20, 20), (330, 390)], (640, 640))
        fitted = fit_layout(panels, seed)
        self.assertTrue(fitted['fit']['feasible'])
        scales = fitted['scales']
        self.assertGreater(scales['a'], 1.0)
        self.assertGreater(scales['b'], 1.0)
        self.assertNotAlmostEqual(scales['a'], scales['b'], places=3)
        relation = next(item for item in fitted['fit']['neighbours']
                        if item['first'] == 'a' and item['second'] == 'b')
        self.assertEqual(1, len(relation['axes']))
        self.assertEqual(1, len(fitted['fit']['horizontal_edges'])
                         + len(fitted['fit']['vertical_edges']))

    def test_gap_fit_stops_at_a_full_envelope_without_shrinking(self):
        panels = [{'id': 'a', 'width': 100, 'height': 100, 'body_size': 18},
                  {'id': 'b', 'width': 100, 'height': 100, 'body_size': 18}]
        seed = self.seed_layout(panels, [(20, 20), (168, 20)], (320, 208))
        fitted = fit_layout(panels, seed)
        self.assertTrue(fitted['fit']['feasible'])
        self.assertEqual({'a': 1.0, 'b': 1.0}, fitted['fit']['growth'])
        self.assertEqual([], fitted['fit']['gap_violations'])
        self.assertEqual(seed['canvas'], fitted['canvas'])

    def test_gap_fit_reports_an_impossible_envelope_without_rebuilding_geometry(self):
        panels = [{'id': 'a', 'width': 100, 'height': 100, 'body_size': 18},
                  {'id': 'b', 'width': 100, 'height': 100, 'body_size': 18}]
        seed = self.seed_layout(panels, [(20, 20), (20, 20)], (100, 100))
        fitted = fit_layout(panels, seed)
        self.assertFalse(fitted['fit']['feasible'])
        self.assertEqual('invalid-fit', fitted['fit']['diagnostic']['kind'])
        self.assertEqual(seed['placements'], fitted['placements'])
        self.assertNotIn('frame', fitted['placements'][0])

    def test_shrink_fit_reduces_a_width_bottleneck_and_keeps_the_narrow_panel(self):
        panels = [{'id': identifier, 'width': width, 'height': 100, 'body_size': 18,
                   'native_min_text_size': 18}
                  for identifier, width in (('a', 400), ('b', 250), ('c', 300))]
        seed = self.seed_layout(panels, [(20, 20), (20, 188), (20, 356)], (472, 600))
        checkpoint = fit_layout(panels, seed)
        refined = shrink_fit_layout(panels, checkpoint)
        self.assertLess(refined['canvas']['width'], checkpoint['canvas']['width'])
        self.assertLess(refined['scales']['a'], checkpoint['scales']['a'])
        self.assertEqual(refined['scales']['b'], checkpoint['scales']['b'])
        self.assertGreaterEqual(refined['shrink']['final_occupancy']['canvas'],
                                refined['shrink']['checkpoint_occupancy']['canvas'])
        self.assertEqual([], refined['shrink']['gap_violations'])

    def test_shrink_fit_can_reduce_two_panels_together_in_a_staggered_layout(self):
        panels = [{'id': identifier, 'width': width, 'height': 100, 'body_size': 18,
                   'native_min_text_size': 18}
                  for identifier, width in (('a', 100), ('b', 100), ('c', 150))]
        seed = self.seed_layout(panels, [(20, 20), (176, 20), (20, 214)], (608, 322))
        checkpoint = fit_layout(panels, seed)
        refined = shrink_fit_layout(panels, checkpoint)
        reductions = refined['shrink']['accepted_reductions']
        self.assertGreater(reductions.get('a', 0), 0)
        self.assertGreater(reductions.get('b', 0), 0)
        self.assertLess(refined['canvas']['width'], checkpoint['canvas']['width'])
        axes = {gap['axis'] for gap in refined['shrink']['final_gaps']}
        self.assertEqual({'x', 'y'}, axes)

    def test_shrink_fit_honours_native_floor_and_twenty_percent_cap(self):
        panels = [{'id': identifier, 'width': width, 'height': 100, 'body_size': 18,
                   'native_min_text_size': native}
                  for identifier, width, native in (('a', 400, 18), ('b', 250, 14),
                                                    ('c', 300, 18))]
        seed = self.seed_layout(panels, [(20, 20), (20, 188), (20, 356)], (472, 600))
        checkpoint = fit_layout(panels, seed)
        refined = shrink_fit_layout(panels, checkpoint)
        for panel in panels:
            identifier = panel['id']
            reference = checkpoint['scales'][identifier]
            final = refined['scales'][identifier]
            self.assertGreaterEqual(final, reference * 0.8 - 1e-6)
            self.assertGreaterEqual(final * panel['native_min_text_size'], 14.0 - 1e-6)
        self.assertEqual(refined['scales']['b'], checkpoint['scales']['b'])

    def test_shrink_fit_keeps_a_compact_checkpoint_unchanged(self):
        panels = [{'id': identifier, 'width': 100, 'height': 100, 'body_size': 18,
                   'native_min_text_size': 18}
                  for identifier in ('a', 'b')]
        seed = self.seed_layout(panels, [(20, 20), (168, 20)], (320, 208))
        checkpoint = fit_layout(panels, seed)
        refined = shrink_fit_layout(panels, checkpoint)
        self.assertEqual(checkpoint['canvas'], refined['canvas'])
        self.assertEqual(checkpoint['placements'], refined['placements'])
        self.assertEqual(checkpoint['scales'], refined['scales'])
        self.assertEqual('no improving shrink candidate', refined['shrink']['stopping_reason'])

    def test_shrink_fit_does_not_shrink_when_native_text_measurement_is_missing(self):
        panels = [{'id': identifier, 'width': 400, 'height': 100, 'body_size': 18}
                  for identifier in ('a', 'b')]
        seed = self.seed_layout(panels, [(20, 20), (20, 188)], (500, 400))
        checkpoint = fit_layout(panels, seed)
        refined = shrink_fit_layout(panels, checkpoint)
        self.assertEqual(checkpoint['scales'], refined['scales'])

    def test_shrink_fit_skips_a_checkpoint_already_below_the_readability_floor(self):
        panels = [{'id': 'a', 'width': 200, 'height': 100, 'body_size': 18,
                   'native_min_text_size': 13.99}]
        seed = self.seed_layout(panels, [(20, 20)], (272, 208))
        checkpoint = fit_layout(panels, seed)
        refined = shrink_fit_layout(panels, checkpoint)
        self.assertEqual('skipped-refinement', refined['shrink']['diagnostic']['kind'])
        self.assertIn('below the 14-unit floor', refined['shrink']['diagnostic']['reason'])
        self.assertEqual(checkpoint['placements'], refined['placements'])

    def test_shrink_fit_does_not_compound_an_existing_refinement(self):
        panels = [{'id': identifier, 'width': width, 'height': 100, 'body_size': 18,
                   'native_min_text_size': 18}
                  for identifier, width in (('a', 400), ('b', 250), ('c', 300))]
        seed = self.seed_layout(panels, [(20, 20), (20, 188), (20, 356)], (472, 600))
        checkpoint = fit_layout(panels, seed)
        refined = shrink_fit_layout(panels, checkpoint)
        repeated = shrink_fit_layout(panels, refined)
        self.assertEqual(refined['canvas'], repeated['canvas'])
        self.assertEqual(refined['placements'], repeated['placements'])
        self.assertEqual(refined['scales'], repeated['scales'])
        self.assertEqual('already-refined', repeated['shrink']['diagnostic']['kind'])


class CompositionTests(unittest.TestCase):
    def fixture(self, count=3):
        sources, records = {}, []
        for index in range(1, count + 1):
            identifier = f'p{index}'
            source = html_figures.normalize_panel_svg(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 420 260" font-size="18">'
                f'<rect id="box{index}" x="20" y="30" width="360" height="80" rx="8" fill="#dce8cf"/>'
                f'<text id="label{index}" x="40" y="80">Panel {index} label</text>'
                f'<path d="M 20 220 L 400 220" fill="none" stroke="#243b32" marker-end="url(#arrow)"/></svg>')
            sources[identifier] = source
            records.append(panel_record(identifier, source, title=f'Panel {index}'))
        return sources, records

    def test_composition_namespaces_ids_and_keeps_the_panel_content(self):
        sources, records = self.fixture(7)
        document = html_figures.compose_figure(sources, arrange(records))
        for index in range(1, 8):
            self.assertIn(f'id="p{index}-box{index}"', document)
            self.assertIn(f'id="p{index}-label{index}"', document)
            self.assertIn(f'>Panel {index} label<', document)
        self.assertNotIn('id="box1"', document)
        self.assertIn('marker id="arrow"', document)
        self.assertIn('url(#arrow)', document)
        self.assertEqual(7, document.count('marker-end="url(#arrow)"'))

    def test_each_phase_background_precedes_its_unchanged_drawing(self):
        sources, records = self.fixture(4)
        layout = arrange(records)
        document = html_figures.compose_figure(sources, layout)
        for placement in layout['placements']:
            identifier = placement['id']
            self.assertLess(document.index(f'id="phase-{identifier}"'),
                            document.index(f'id="panel-{identifier}"'))
        self.assertEqual(4, document.count('fill="#ffffff"'))

    def test_the_composed_canvas_is_the_arrangement_canvas_and_holds_every_number(self):
        sources, records = self.fixture(4)
        layout = arrange(records)
        document = html_figures.compose_figure(sources, layout)
        self.assertIn(f'viewBox="0 0 {layout["canvas"]["width"]} {layout["canvas"]["height"]}"',
                      document)
        for placement in layout['placements']:
            self.assertIn(f'>{placement["number"]}</text>', document)
            self.assertIn(f'translate({placement["x"]} {placement["y"]})', document)
            self.assertIn(f'scale({placement["scale"]})', document)

    def test_a_nested_root_font_and_transform_survive_composition(self):
        source = html_figures.normalize_panel_svg(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 240" font-size="30" fill="#2f6f5e">'
            '<g transform="translate(30 20) scale(0.5)">'
            '<text x="0" y="40">Scaled label</text></g>'
            '<text x="20" y="200">Plain label</text></svg>')
        records = [panel_record('p1', source)]
        document = html_figures.compose_figure({'p1': source}, arrange(records))
        self.assertIn('font-size="30"', document)
        self.assertIn('fill="#2f6f5e"', document)
        self.assertIn('scale(0.5)', document)
        self.assertIn('>Scaled label</text>', document)

    def test_composition_rejects_a_panel_outside_the_supported_profile(self):
        with self.assertRaises(ValueError):
            html_figures.normalize_panel_svg(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 240" font-size="18">'
                '<text x="10" y="40">Text</text><image href="https://example.test/a.png"/></svg>')


if __name__ == '__main__':
    unittest.main()
