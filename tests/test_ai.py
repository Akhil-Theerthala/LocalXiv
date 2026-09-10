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
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = temporary.name


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


    def test_json_format_is_requested_only_for_plans(self):
        provider = Provider({'endpoint': 'https://example.test/v1', 'model': 'test'}, 'secret')
        for structured in (False, True):
            raw = json.dumps({'choices': [{'finish_reason': 'stop', 'message': {'content': '{}'}}]}).encode()
            with patch('urllib.request.OpenerDirector.open', return_value=io.BytesIO(raw)) as opened:
                provider.complete([{'role': 'user', 'content': 'Return JSON.'}], json_object=structured)
            body = json.loads(opened.call_args.args[0].data)
            self.assertEqual({'type': 'json_object'} if structured else None, body.get('response_format'))

    def test_gemini_text_requests_disable_native_function_calls(self):
        provider = Provider({'endpoint': 'https://generativelanguage.googleapis.com/v1beta/openai', 'model': 'test'}, 'secret')
        raw = json.dumps({'choices': [{'finish_reason': 'stop', 'message': {'content': 'text'}}]}).encode()
        with patch('urllib.request.OpenerDirector.open', return_value=io.BytesIO(raw)) as opened:
            provider.complete([{'role': 'user', 'content': 'Write Python text.'}])
        self.assertEqual('none', json.loads(opened.call_args.args[0].data)['tool_choice'])

    def test_native_tool_response_allows_null_content_and_redacts_arguments(self):
        provider = Provider({'endpoint': 'https://example.test/v1', 'model': 'test'}, 'secret')
        calls = [{'id':'call1','type':'function','function':{'name':'submit_candidate','arguments':'{"text":"secret"}'}}]
        raw = json.dumps({'choices':[{'finish_reason':'tool_calls','message':{'content':None,'tool_calls':calls}}]}).encode()
        schema = [{'type':'function','function':{'name':'submit_candidate','parameters':{'type':'object'}}}]
        with patch('urllib.request.OpenerDirector.open', return_value=io.BytesIO(raw)) as opened:
            result=provider.complete([{'role':'user','content':'Draw'}],tools=schema)
        self.assertEqual('required',json.loads(opened.call_args.args[0].data)['tool_choice'])
        self.assertEqual('',result['text'])
        self.assertNotIn('secret',json.dumps(result))
        self.assertEqual('submit_candidate',result['tool_calls'][0]['function']['name'])




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
