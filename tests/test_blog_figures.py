"""Blog figure lifecycle, cleanup edits, and retained regression fixtures.

The provider is scripted and the native measurements are patched here, so these tests cover the
state machine and the edit arithmetic. Real at-article-width rendering is covered by
``tests.test_figure_readability`` and by the fixture replay at the bottom of this file.
"""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from papers.ai import ProviderError
from papers.blog_figures import (MAX_FIGURE_ATTEMPTS, apply_text_edits, attempt_figure,
                                 check_blog_figure, new_figure_state, remove_omitted_markers)
from papers.explanation import blog_figure_assignment, candidate_digest
from papers.panel_authoring import missing_value_details

NATIVE = os.environ.get('LOCALXIV_HTML_RENDERER')
FIXTURES = Path(__file__).parent / 'fixtures' / 'blog-figures'
REVIEW_ISSUE = {'code': 'review', 'category': 'readability', 'path': 'fig1',
                'message': 'The output label overlaps a connector.'}


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
        'layout_intent': 'Input at left; frozen and trainable paths stacked; addition at right.',
        'content': [{'text': 'Input reaches both paths, whose outputs are added.',
                     'kind': 'connection', 'passages': ['p00001']}],
        'exact_text': ['W₀x'],
        'illustrative_values': [],
    }
    value.update(overrides)
    return value


def drawn_svg(text='W₀x'):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 240" '
            'font-family="Arial, sans-serif" font-size="18" fill="#243b32">'
            '<text x="40" y="80" font-size="18">' + text + '</text></svg>')


def drawing(text='W₀x'):
    return {'panel_id': 'fig1', 'svg': drawn_svg(text)}


def checked(source, *, defects=(), labels=('W₀x',)):
    return {'source': source,
            'assets': {key: 'figure.' + key
                       for key in ('html', 'svg', 'png', 'pdf', 'svg_source')},
            'checks': {'issue_details': list(defects), 'issues': [],
                       'canvas': {'width': 640, 'height': 240}},
            'labels': list(labels)}


class Provider:
    """One scripted response per call, cycled at the last response."""

    def __init__(self, *responses):
        self.settings = {'endpoint': 'https://example.test/v1', 'model': 'scripted'}
        self.responses = list(responses)
        self.calls = 0
        self.messages = []

    def complete(self, messages, **kwargs):
        self.calls += 1
        self.messages.append(messages)
        response = self.responses[min(self.calls - 1, len(self.responses) - 1)]
        if callable(response):
            return response(messages)
        if isinstance(response, Exception):
            raise response
        return {'text': response if isinstance(response, str) else json.dumps(response),
                'usage': {'total_tokens': 5}}


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = temporary.name
        self.brief = blog_brief()

    def test_success_on_each_of_attempts_one_through_four(self):
        for target in range(1, MAX_FIGURE_ATTEMPTS + 1):
            with self.subTest(attempt=target):
                responses = ['not json'] * (target - 1) + [drawing()]
                provider = Provider(*responses)
                state = new_figure_state(self.brief)
                with patch('papers.blog_figures.check_blog_figure',
                           side_effect=[checked(drawn_svg())]):
                    for _ in range(target):
                        state = attempt_figure(provider, state, self.directory)
                self.assertEqual(target, state['attempts'])
                self.assertEqual('accepted', state['status'])
                self.assertIsNotNone(state['checked'])
                self.assertEqual([], state['issues'])
                self.assertEqual(target, provider.calls)

    def test_four_failures_end_omitted_and_a_fifth_call_makes_no_request(self):
        provider = Provider(*['not json'] * 4)
        state = new_figure_state(self.brief)
        for _ in range(4):
            state = attempt_figure(provider, state, self.directory)
        self.assertEqual(4, state['attempts'])
        self.assertEqual('omitted', state['status'])
        self.assertEqual(4, provider.calls)
        state = attempt_figure(provider, state, self.directory)
        self.assertEqual('omitted', state['status'])
        self.assertEqual(4, provider.calls)
        self.assertEqual(4, len(state['history']))

    def test_a_failed_second_attempt_stays_pending(self):
        provider = Provider('not json', 'not json')
        state = new_figure_state(self.brief)
        state = attempt_figure(provider, state, self.directory)
        self.assertEqual('pending', state['status'])
        state = attempt_figure(provider, state, self.directory)
        self.assertEqual(2, state['attempts'])
        self.assertEqual('pending', state['status'])

    def test_a_fourth_attempt_success_is_retained(self):
        provider = Provider(*['not json'] * 3, drawing())
        state = new_figure_state(self.brief)
        with patch('papers.blog_figures.check_blog_figure', return_value=checked(drawn_svg())):
            for _ in range(4):
                state = attempt_figure(provider, state, self.directory)
        self.assertEqual(4, state['attempts'])
        self.assertEqual('accepted', state['status'])
        self.assertEqual(4, provider.calls)

    def test_a_locally_accepted_drawing_rejected_by_review_consumes_an_attempt(self):
        provider = Provider(drawing(), drawing())
        state = new_figure_state(self.brief)
        with patch('papers.blog_figures.check_blog_figure',
                   side_effect=[checked(drawn_svg()), checked(drawn_svg())]):
            state = attempt_figure(provider, state, self.directory)
            self.assertEqual('accepted', state['status'])
            self.assertEqual(1, provider.calls)
            state = attempt_figure(provider, state, self.directory, issues=[REVIEW_ISSUE])
        self.assertEqual(2, provider.calls)
        self.assertEqual(2, state['attempts'])
        self.assertEqual('accepted', state['status'])
        self.assertIn('overlaps a connector', json.dumps(provider.messages[1]))

    def test_malformed_and_transport_failures_stay_inside_the_ceiling(self):
        transport = ProviderError('Provider request failed with HTTP status 503.')
        provider = Provider('not json', transport, 'not json', transport)
        state = new_figure_state(self.brief)
        for _ in range(4):
            state = attempt_figure(provider, state, self.directory)
        self.assertEqual(4, state['attempts'])
        self.assertEqual(4, provider.calls)
        self.assertEqual('omitted', state['status'])
        self.assertEqual(['invalid_output', 'transport', 'invalid_output', 'transport'],
                         [entry['error_kind'] for entry in state['history']])

    def test_checkpoint_runs_before_dispatch_and_after_checking(self):
        events = []
        provider = Provider(drawing())
        original = provider.complete

        def complete(messages, **kwargs):
            events.append('dispatch')
            return original(messages, **kwargs)

        provider.complete = complete

        def checkpoint(state):
            events.append('checkpoint:' + str(state['attempts']) + ':'
                          + str(state['checked'] is not None))

        state = new_figure_state(self.brief)
        with patch('papers.blog_figures.check_blog_figure', return_value=checked(drawn_svg())):
            state = attempt_figure(provider, state, self.directory, checkpoint=checkpoint)
        self.assertEqual(['checkpoint:1:False', 'dispatch', 'checkpoint:1:True'], events)

    def test_usage_is_recorded_once_per_provider_call(self):
        provider = Provider('not json', drawing())
        state = new_figure_state(self.brief)
        with patch('papers.blog_figures.check_blog_figure', return_value=checked(drawn_svg())):
            state = attempt_figure(provider, state, self.directory)
            state = attempt_figure(provider, state, self.directory)
        self.assertEqual(2, provider.calls)
        self.assertEqual([{'total_tokens': 5}, {'total_tokens': 5}],
                         [entry['usage'] for entry in state['history']])
        self.assertEqual([1, 2], [entry['attempt'] for entry in state['history']])

    def test_authentication_failure_raises_provider_error(self):
        provider = Provider(ProviderError('Provider rejected authentication. Check the saved key.'))
        state = new_figure_state(self.brief)
        with self.assertRaises(ProviderError):
            attempt_figure(provider, state, self.directory)

    def test_a_native_renderer_value_error_propagates(self):
        provider = Provider(drawing())
        state = new_figure_state(self.brief)
        with patch('papers.blog_figures.check_blog_figure', side_effect=ValueError('bad render')):
            with self.assertRaises(ValueError):
                attempt_figure(provider, state, self.directory)

    def test_defects_combine_native_findings_and_missing_values(self):
        native = {'code': 'text_too_small', 'path': '/svg/text[1]', 'message': 'Small text.',
                  'constraint': 'minimum_displayed_font_px', 'actual': 9, 'limit': 14}
        provider = Provider(drawing('different'), drawing())
        state = new_figure_state(self.brief)
        with patch('papers.blog_figures.check_blog_figure',
                   side_effect=[checked(drawn_svg('different'), defects=[native],
                                        labels=('different',)),
                                checked(drawn_svg())]):
            state = attempt_figure(provider, state, self.directory)
            self.assertEqual('pending', state['status'])
            self.assertIn(native, state['issues'])
            self.assertEqual(['W₀x'], [item['value'] for item in state['issues']
                                       if item.get('kind') == 'exact'])
            state = attempt_figure(provider, state, self.directory)
        self.assertEqual('accepted', state['status'])
        repair = json.dumps(provider.messages[1], ensure_ascii=False)
        self.assertIn('/svg/text[1]', repair)
        self.assertIn('measured 9; limit 14', repair)
        self.assertIn('W₀x', repair)
        self.assertIn('layout intent:', repair)


class TextEditTests(unittest.TestCase):
    def test_the_documented_exact_edit_example(self):
        text = 'Opening stays.\n\nFollow the blue branch below.\n\nEnding stays.'
        edits = [{'old': 'Follow the blue branch below.',
                  'new': 'The input follows two paths whose outputs are added.'}]
        result = apply_text_edits(text, edits, base_digest=candidate_digest(text))
        self.assertEqual('Opening stays.\n\nThe input follows two paths whose outputs are added.'
                         '\n\nEnding stays.', result)

    def test_a_stale_digest_is_rejected(self):
        text = 'Opening stays.'
        with self.assertRaises(ValueError):
            apply_text_edits(text, [{'old': 'Opening', 'new': 'Start'}], base_digest='0' * 64)

    def test_repeated_old_text_is_rejected(self):
        repeated = 'A figure. Another figure.'
        with self.assertRaises(ValueError):
            apply_text_edits(repeated, [{'old': 'figure.', 'new': 'drawing.'}],
                             base_digest=candidate_digest(repeated))
        text = 'Opening stays.'
        with self.assertRaises(ValueError):
            apply_text_edits(text, [{'old': 'Opening', 'new': 'A'},
                                    {'old': 'Opening', 'new': 'B'}],
                             base_digest=candidate_digest(text))

    def test_overlapping_edits_are_rejected(self):
        text = 'abcdef'
        with self.assertRaises(ValueError):
            apply_text_edits(text, [{'old': 'abcd', 'new': 'x'}, {'old': 'cdef', 'new': 'y'}],
                             base_digest=candidate_digest(text))

    def test_text_outside_changed_spans_is_preserved_and_empty_replacements_are_allowed(self):
        text = 'one two three four'
        edits = [{'old': 'two', 'new': '2'}, {'old': ' four', 'new': ''}]
        self.assertEqual('one 2 three',
                         apply_text_edits(text, edits, base_digest=candidate_digest(text)))

    def test_remove_omitted_markers_keeps_text_outside_the_marker(self):
        text = 'Opening stays.\n\n{{figure:fig2}}\n\nEnding stays.'
        self.assertEqual('Opening stays.\n\nEnding stays.',
                         remove_omitted_markers(text, ['fig2']))
        inline = 'A sentence {{figure:fig2}} continues.'
        self.assertEqual('A sentence  continues.', remove_omitted_markers(inline, ['fig2']))

    def test_remove_omitted_markers_only_removes_named_ids(self):
        text = 'Keep {{figure:fig1}}.\n\n{{figure:fig2}}\n\n{{figure:fig3}}'
        self.assertEqual('Keep {{figure:fig1}}.\n\n{{figure:fig3}}',
                         remove_omitted_markers(text, ['fig2']))


@unittest.skipUnless(NATIVE, 'Set LOCALXIV_HTML_RENDERER for native rendering checks')
class BlogFigureFixtureTests(unittest.TestCase):
    """Retained failures replay through the real checker with a hand-corrected counterpart."""

    CASES = (
        ('undersized-text', ['text_too_small'], []),
        ('out-of-bounds-label', ['out_of_bounds'], []),
        ('contract-mismatch', [], ['W₀x']),
    )

    def assignment(self):
        return blog_figure_assignment(blog_brief())

    def test_each_fixture_reports_its_defect_and_the_correction_is_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            for name, expected_codes, expected_missing in self.CASES:
                with self.subTest(name=name):
                    broken = (FIXTURES / (name + '.source.svg')).read_text()
                    fixed = (FIXTURES / (name + '.fixed.svg')).read_text()
                    result = check_blog_figure(broken, directory, 'fig1')
                    codes = [item['code'] for item in result['checks']['issue_details']]
                    missing = missing_value_details(self.assignment(), result['labels'])
                    for code in expected_codes:
                        self.assertIn(code, codes)
                    self.assertEqual(expected_missing, [item['value'] for item in missing])
                    corrected = check_blog_figure(fixed, directory, 'fig1')
                    self.assertEqual([], corrected['checks']['issue_details'])
                    self.assertEqual([], missing_value_details(self.assignment(), corrected['labels']))


if __name__ == '__main__':
    unittest.main()
