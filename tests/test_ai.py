import json
import threading
import unittest
from unittest.mock import patch
import io
import tempfile
from pathlib import Path
from tests.overview_fixture import response, PLAN, ARTICLE
from http.server import BaseHTTPRequestHandler, HTTPServer
from papers.ai import Provider, ProviderError, generate_overview, answer_question


class FakeProvider:
    settings = {'model': 'fake', 'max_context_chars': 12000}
    def __init__(self):
        self.calls = []
    def complete(self, messages, **kwargs):
        self.calls.append(messages)
        return {'text': 'Supported finding [p00001].', 'usage': {}}


class AITests(unittest.TestCase):
    def test_overlong_medium_article_is_shortened_with_contract_preserved(self):
        provider = FakeProvider()
        provider.settings = dict(provider.settings, max_context_chars=480000)
        def complete(messages, **kwargs):
            provider.calls.append(messages)
            result = response(messages)
            if messages[-1]['content'].startswith('Check every numerical'):
                result['text'] = ARTICLE.replace('The result is 91 percent', 'Background ' * 600)
            return result
        provider.complete = complete
        with patch('papers.overview.render_figure', return_value={'svg': 'figure.svg'}):
            result = generate_overview(provider, {'passages': [{'id': 'p00001', 'text': 'Evidence'}],
                                                 'directory': 'unused'}, lambda _: None)
        self.assertEqual(1, sum(call[-1]['content'].startswith('Shorten this article') for call in provider.calls))
        self.assertLess(len(result['text'].split()), 1250)
        self.assertEqual(PLAN['sections'], result['outline']['sections'])

    def test_invalid_citations_are_regenerated_not_accepted(self):
        from papers.ai import _request
        provider = FakeProvider()
        replies = iter(['A claim [p0047].', 'A claim [p00047].'])
        def complete(messages):
            provider.calls.append(messages)
            return {'text': next(replies), 'usage': {'total_tokens': 5}}
        provider.complete = complete
        result = _request(provider, 'Summarize.', '[p00047] Evidence.', [{'id': 'p00047'}])
        self.assertEqual('A claim [p00047].', result['text'])
        self.assertEqual({'total_tokens': 10}, result['usage'])
        self.assertIn('including every leading zero', provider.calls[1][-1]['content'])
        replies = iter(['Invented [p99999].', 'Invented [p99999].'])
        with self.assertRaises(ProviderError):
            _request(provider, 'Summarize.', '[p00047] Evidence.', [{'id': 'p00047'}])

    def test_plan_json_mode_and_bounded_correction(self):
        for invalid in ('not JSON', json.dumps(dict(PLAN, figures=[]))):
            provider = FakeProvider()
            plan_calls = []
            def complete(messages, **kwargs):
                if messages[-1]['content'].startswith('ARTICLE PLAN.'):
                    plan_calls.append(messages)
                    self.assertTrue(kwargs['json_object'])
                    self.assertNotIn('Write plain connected prose', messages[0]['content'])
                    if len(plan_calls) == 1:
                        return {'text': invalid, 'usage': {'total_tokens': 5}}
                return response(messages)
            provider.complete = complete
            with patch('papers.overview.render_figure', return_value={'svg': 'figure.svg'}):
                result = generate_overview(provider, {'passages': [{'id': 'p00001', 'text': 'Evidence'}],
                                                     'directory': 'unused'}, lambda _: None)
            self.assertEqual(2, len(plan_calls))
            self.assertIn('failed validation', plan_calls[1][-1]['content'])
            self.assertIn({'total_tokens': 5}, result['provenance']['usage'])

        provider = FakeProvider()
        calls = []
        def invalid_plan(messages, **kwargs):
            calls.append(messages)
            return {'text': 'not JSON' if kwargs else 'Evidence [p00001].'}
        provider.complete = invalid_plan
        with self.assertRaisesRegex(ProviderError, 'after one correction'):
            generate_overview(provider, {'passages': [{'id': 'p00001', 'text': 'Evidence'}]}, lambda _: None)
        self.assertEqual(3, len(calls))  # One evidence request and two plan attempts.

    def test_json_format_is_requested_only_for_plans(self):
        provider = Provider({'endpoint': 'https://example.test/v1', 'model': 'test'}, 'secret')
        for structured in (False, True):
            raw = json.dumps({'choices': [{'finish_reason': 'stop', 'message': {'content': '{}'}}]}).encode()
            with patch('urllib.request.OpenerDirector.open', return_value=io.BytesIO(raw)) as opened:
                provider.complete([{'role': 'user', 'content': 'Return JSON.'}], json_object=structured)
            body = json.loads(opened.call_args.args[0].data)
            self.assertEqual({'type': 'json_object'} if structured else None, body.get('response_format'))

    def test_three_section_batches_cover_every_passage_and_respect_context(self):
        for passage_size in (10, 2400):
            provider = FakeProvider()
            def complete(messages, **kwargs):
                provider.calls.append(messages)
                return response(messages)
            provider.complete = complete
            passages = [{'id': f'p{i:05}', 'section': f'Section {(i-1)//2}', 'text': 'x' * passage_size}
                        for i in range(1, 15)]
            with patch('papers.overview.render_figure', return_value={'svg': 'figure.svg'}):
                result = generate_overview(provider, {'passages': passages, 'directory': 'unused'}, lambda _: None)
            self.assertEqual([p['id'] for p in passages], [ref for n in result['evidence'] for ref in n['passages']])
            if passage_size == 10:
                self.assertEqual([6, 6, 2], [len(n['passages']) for n in result['evidence']])
            else:
                self.assertGreater(len(result['evidence']), 3)
            for call in provider.calls[:len(result['evidence'])]:
                self.assertLessEqual(sum(len(m['content']) for m in call), provider.settings['max_context_chars'])

    def test_language_and_length_reach_planning_drafting_review_and_provenance(self):
        from papers.overview import LANGUAGES, LENGTHS
        for language in LANGUAGES:
            for length in LENGTHS:
                provider = FakeProvider()
                provider.settings = dict(provider.settings, overview_language=language, overview_length=length)
                def complete(messages, **kwargs):
                    provider.calls.append(messages)
                    return response(messages)
                provider.complete = complete
                with patch('papers.overview.render_figure', return_value={'svg': 'figure.svg'}):
                    result = generate_overview(provider, {'passages': [{'id': 'p00001', 'text': 'Evidence'}], 'directory': 'unused'}, lambda _: None)
                for call in provider.calls[1:4]:
                    self.assertIn(LANGUAGES[language], call[-1]['content'])
                    self.assertIn(LENGTHS[length], call[-1]['content'])
                    self.assertIn('central question', call[-1]['content'])
                self.assertEqual(language, result['provenance']['overview_language'])
                self.assertEqual(length, result['provenance']['overview_length'])

    def test_coverage_and_provenance(self):
        provider = FakeProvider()
        doc = {'arxiv_id': '1v1', 'source_digest': 'sha', 'passages': [
            {'id': 'p00001', 'section': 'Intro', 'text': 'One', 'href': 'a#p00001'},
            {'id': 'p00002', 'section': 'Appendix', 'text': 'Two', 'href': 'b#p00002'}]}
        # Each section must cite its own evidence.
        def complete(messages, **kwargs):
            provider.calls.append(messages)
            return response(messages)
        provider.complete = complete
        with tempfile.TemporaryDirectory() as directory:
            doc['directory'] = directory
            result = generate_overview(provider, doc, lambda _: None)
            self.assertTrue((Path(directory) / result['figures'][0]['svg']).is_file())
            self.assertIn('png', result['figures'][0])
            self.assertIn('excalidraw', result['figures'][0])
        self.assertNotIn('[p00001]', result['text'])
        self.assertIn('[p00001]', result['cited_text'])
        self.assertEqual(6, len(provider.calls))
        self.assertEqual(['p00001', 'p00002'], result['provenance']['passages'])
        self.assertEqual(1, len(result['evidence']))
        self.assertEqual('casual', result['provenance']['overview_language'])
        self.assertEqual('medium', result['provenance']['overview_length'])
        from papers.library import document_digest
        self.assertEqual('sha', result['provenance']['source_digest'])
        self.assertEqual(document_digest(doc), result['provenance']['document_digest'])
        self.assertGreaterEqual(len(provider.calls), 3)
        with self.assertRaises(ProviderError):
            answer_question(FakeProvider(), 'Q', [doc['passages'][1]], [])

    def test_response_bounds_timeout_and_unfinished_output(self):
        p = Provider({'endpoint': 'https://example.org/v1', 'model': 'fake'}, 'secret')
        for raw in (b'x' * 2_000_001,
                    json.dumps({'choices': [{'finish_reason': 'length', 'message': {'content': 'partial'}}]}).encode()):
            with patch('urllib.request.OpenerDirector.open', return_value=io.BytesIO(raw)):
                with self.assertRaises(ProviderError):
                    p.complete([{'role': 'user', 'content': 'Q'}])
        with patch('urllib.request.OpenerDirector.open', side_effect=TimeoutError('secret')):
            with self.assertRaises(ProviderError) as error:
                p.complete([{'role': 'user', 'content': 'Q'}])
            self.assertNotIn('secret', str(error.exception))
        provider = FakeProvider()
        doc = {'passages': [{'id': 'p00001', 'section': 'Large', 'text': 'x' * 20000}]}
        with self.assertRaises(ProviderError):
            generate_overview(provider, doc, lambda _: None)
        self.assertEqual([], provider.calls)

    def test_evidence_and_review_overflow_do_not_drop_sections(self):
        doc = {'passages': [
            {'id': 'p00001', 'section': 'Intro', 'text': 'First' + 'x' * 4200},
            {'id': 'p00002', 'section': 'Appendix', 'text': 'Last' + 'x' * 4200}]}
        for note_length, expected_calls in ((6000, 2), (2500, 4)):
            provider = FakeProvider()
            provider.settings = {'model': 'fake', 'max_context_chars': 10000}
            def complete(messages, **kwargs):
                provider.calls.append(messages)
                if len(provider.calls) <= 2:
                    return {'text': 'x' * note_length + ' [p0000' + str(len(provider.calls)) + ']', 'usage': {}}
                if len(provider.calls) == 3:
                    return response(messages)
                return {'text': ARTICLE.replace('The result is 91 percent', 'x' * 1700), 'usage': {}}
            provider.complete = complete
            with self.assertRaisesRegex(ProviderError, 'context bound'):
                generate_overview(provider, doc, lambda _: None)
            self.assertEqual(expected_calls, len(provider.calls))
            self.assertIn('First', provider.calls[0][-1]['content'])
            self.assertIn('Last', provider.calls[1][-1]['content'])

    def test_openai_completion_bound_includes_reasoning_tokens(self):
        response = json.dumps({'choices':[{'finish_reason':'stop','message':{'content':'Answer'}}]}).encode()
        provider = Provider({'endpoint':'https://api.openai.com/v1','model':'test-model'}, 'fake-test-key')
        with patch('urllib.request.OpenerDirector.open', return_value=io.BytesIO(response)) as opened:
            provider.complete([{'role':'user','content':'Question'}])
        body = json.loads(opened.call_args.args[0].data)
        self.assertEqual(body['max_completion_tokens'],24576)
        self.assertNotIn('max_tokens',body)
        self.assertEqual(provider.context_limit,480000)
        self.assertEqual(opened.call_args.kwargs['timeout'],150)

    def test_reported_usage_is_recorded_even_when_output_is_truncated(self):
        events=[]
        provider=Provider({'endpoint':'https://example.test/v1','model':'test'},'secret',on_usage=events.append)
        result={'choices':[{'finish_reason':'length','message':{'content':'partial'}}], 'usage':{'prompt_tokens':12,'completion_tokens':8,'total_tokens':20,'secret':'no','invalid':-1}}
        with patch('urllib.request.OpenerDirector.open',return_value=io.BytesIO(json.dumps(result).encode())):
            with self.assertRaises(ProviderError):provider.complete([{'role':'user','content':'Q'}])
        self.assertEqual(events,[{'prompt_tokens':12,'completion_tokens':8,'total_tokens':20}])

    def test_provider_http_contract_and_safe_error(self):
        class Handler(BaseHTTPRequestHandler):
            status = 200
            request = None
            def log_message(self, *args):
                pass
            def do_POST(self):
                Handler.request = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                self.send_response(Handler.status)
                self.end_headers()
                self.wfile.write(json.dumps({'choices': [{'finish_reason': 'stop', 'message': {'content': 'Answer'}}], 'usage': {'total_tokens': 3}}).encode())
        server = HTTPServer(('127.0.0.1', 0), Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            p = Provider({'endpoint': 'http://127.0.0.1:' + str(server.server_port) + '/v1', 'model': 'fake'}, 'secret')
            self.assertEqual('Answer', p.complete([{'role': 'user', 'content': 'Q'}])['text'])
            self.assertEqual('fake', Handler.request['model'])
            Handler.status = 401
            with self.assertRaises(ProviderError) as error:
                p.complete([{'role': 'user', 'content': 'Q'}])
            self.assertNotIn('secret', str(error.exception))
            with self.assertRaises(ProviderError):
                p.complete([{'role': 'user', 'content': 'X' * 100001}])
        finally:
            server.shutdown()
            server.server_close()


class KeychainSmokeTest(unittest.TestCase):
    @unittest.skipUnless(__import__('os').environ.get('PAPERS_KEYCHAIN_SMOKE') == '1',
                         'Opt-in test creates and removes one fake Keychain item')
    def test_ephemeral_keychain_roundtrip(self):
        import ctypes
        import uuid
        from papers.settings import _security, get_key, set_key
        endpoint = 'https://keychain-test-' + uuid.uuid4().hex + '.invalid/v1'
        lib, cf = _security()
        lib.SecKeychainSetUserInteractionAllowed.argtypes = [ctypes.c_ubyte]
        lib.SecKeychainSetUserInteractionAllowed.restype = ctypes.c_int32
        self.assertEqual(0, lib.SecKeychainSetUserInteractionAllowed(False))
        service = b'org.papers-to-kindle.provider'
        account = endpoint.encode()
        try:
            self.assertEqual('', get_key(endpoint))
            set_key(endpoint, 'fake-test-key-only')
            self.assertEqual('fake-test-key-only', get_key(endpoint))
            set_key(endpoint, 'fake-replacement-key-only')
            self.assertEqual('fake-replacement-key-only', get_key(endpoint))
        finally:
            item = ctypes.c_void_p()
            status = lib.SecKeychainFindGenericPassword(None, len(service), service,
                len(account), account, None, None, ctypes.byref(item))
            if status == 0:
                try:
                    self.assertEqual(0, lib.SecKeychainItemDelete(item))
                finally:
                    cf.CFRelease(item)
            else:
                self.assertEqual(-25300, status)
        self.assertEqual('', get_key(endpoint))
