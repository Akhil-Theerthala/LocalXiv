"""Panel authoring: prompt contract, one-shot requests, local checks, and simple recovery."""
import json
import os
import tempfile
import unittest

from papers.ai import ProviderError
from papers import html_figures, panel_authoring
from papers.arrangement import arrange, panel_record
from papers.explanation import panel_assignments, validate_panel_plan
from papers.panel_authoring import (check_panel, missing_values, panel_messages, request_panel,
                                    required_values, simple_panel, simple_panel_source)

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
        'construction': 'calculation',
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

    def test_required_values_keep_shared_facts_whole_and_every_stated_number(self):
        values = required_values(assignment())
        self.assertEqual(['0.73 and 0.27', '8,532,412', '0.73', '1', '0.27', '2'], values)
        labels = ['Mixing two values', 'The client counter starts at 8,532,412 and increases by one.',
                  'reply = 0.73 v1 + 0.27 v2']
        self.assertEqual(['0.73 and 0.27'], missing_values(assignment(), labels))
        self.assertEqual([], missing_values(assignment(), labels + ['0.73 and 0.27']))


class RequestTests(unittest.TestCase):
    class Provider:
        def __init__(self, answer):
            self.settings = {'endpoint': 'https://example.test/v1', 'model': 'scripted'}
            self.answer = answer
            self.calls = 0

        def complete(self, messages, **kwargs):
            self.calls += 1
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

    def test_an_unsafe_document_is_rejected_before_any_render(self):
        with self.assertRaises(ValueError):
            check_panel('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200">'
                        '<script>alert(1)</script></svg>', '/tmp', 'p2')

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
                          'shared_facts', 'illustrative_values', 'construction'}, set(projected[0]))


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

    def test_the_arrangement_never_shrinks_a_panel_below_its_measured_size(self):
        panels = self.measured(3, width=400, height=260, body=14)
        layout = arrange(panels)
        self.assertGreater(layout['scales']['p1'], 1.0)
        for placement, panel in zip(layout['placements'], panels):
            self.assertGreaterEqual(placement['width'], panel['width'])


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
