import json
import threading
import unittest
from unittest.mock import patch
import io
import tempfile
from pathlib import Path
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
    def test_deepseek_effort_does_not_leak_to_other_provider_payloads(self):
        raw=json.dumps({'choices':[{'finish_reason':'stop','message':{'content':'Answer'}}]}).encode()
        for endpoint,expected in [('https://api.deepseek.com','low'),('https://api.deepseek.com.example.org',None),('https://openrouter.ai/api/v1',None)]:
            provider=Provider({'endpoint':endpoint,'model':'fixture'},'secret')
            with patch('urllib.request.OpenerDirector.open',return_value=io.BytesIO(raw)) as opened:
                provider.complete([{'role':'user','content':'Q'}],reasoning_effort='low')
            self.assertEqual(expected,json.loads(opened.call_args.args[0].data).get('reasoning_effort'))

    def test_provider_error_details_are_bounded_and_credentials_redacted(self):
        import urllib.error
        provider=Provider({'endpoint':'https://example.test','model':'test'},'secret-key')
        for message in ['Invalid image: secret-key Bearer another-token', 'bad '*1000]:
            error=urllib.error.HTTPError(provider.url,400,'Bad request',{},io.BytesIO(json.dumps({'error':{'message':message}}).encode()))
            with patch('urllib.request.OpenerDirector.open',side_effect=error):
                with self.assertRaises(ProviderError) as caught:
                    provider.complete([{'role':'user','content':'Q'}])
            detail=str(caught.exception)
            self.assertIn('400',detail)
            self.assertLess(len(detail),550)
            self.assertNotIn('secret-key',detail)
            self.assertNotIn('another-token',detail)
        self.assertIn('bad',detail)

    def test_cache_and_reasoning_usage_are_preserved_as_numeric_counts(self):
        reported={'prompt_tokens':100,'completion_tokens':20,'total_tokens':120,
                  'prompt_cache_hit_tokens':80,'prompt_cache_miss_tokens':20,
                  'prompt_tokens_details':{'cached_tokens':80,'secret':'discard'},
                  'completion_tokens_details':{'reasoning_tokens':12,'secret':'discard'}}
        raw=json.dumps({'choices':[{'finish_reason':'stop','message':{'content':'Answer'}}],'usage':reported}).encode()
        provider=Provider({'endpoint':'https://example.test','model':'test'},'secret')
        with patch('urllib.request.OpenerDirector.open',return_value=io.BytesIO(raw)):
            usage=provider.complete([{'role':'user','content':'Q'}])['usage']
        self.assertEqual(80,usage['cached_tokens'])
        self.assertEqual(12,usage['reasoning_tokens'])
        self.assertEqual(20,usage['prompt_cache_miss_tokens'])
        self.assertNotIn('secret',json.dumps(usage))

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

    def test_reasoning_switch_uses_exact_base_url_host(self):
        for endpoint, fields in (
            ('https://api.deepseek.com', {'reasoning_content':'exact\nreasoning'}),
            ('https://api.deepseek.com/beta/chat/completions', {'reasoning_content':''}),
            ('https://openrouter.ai/api/v1/', {'reasoning':'plain fallback'}),
            ('https://api.deepseek.com.example.org/v1', {}),
            ('https://example.org/openrouter.ai', {}),
            ('https://api.openai.com/v1', {}),
        ):
            with self.subTest(endpoint=endpoint):
                p=Provider({'endpoint':endpoint,'model':'deepseek-flash'},'fake-key')
                raw=json.dumps({'choices':[{'finish_reason':'stop','message':{'content':'Answer',**fields}}]}).encode()
                with patch('urllib.request.OpenerDirector.open',return_value=io.BytesIO(raw)) as opened:
                    result=p.complete([{'role':'user','content':'Q'}],tools=[{'type':'function','function':{'name':'test'}}])
                body=json.loads(opened.call_args.args[0].data)
                self.assertEqual('auto' if fields else 'required',body['tool_choice'])
                self.assertNotIn('thinking',body)
                if fields:
                    self.assertEqual({'role':'assistant','content':'Answer',**fields},result['assistant_message'])
                else:
                    self.assertNotIn('assistant_message',result)

    def test_credentials_are_not_replayed(self):
        p=Provider({'endpoint':'https://openrouter.ai/api/v1','model':'test','max_context_chars':4000},'fake-key')
        raw=json.dumps({'choices':[{'finish_reason':'stop','message':{'content':'ok','reasoning_details':[{'text':'fake-key','signature':'signed'}]}}]}).encode()
        with patch('urllib.request.OpenerDirector.open',return_value=io.BytesIO(raw)):
            with self.assertRaises(ProviderError) as error:
                p.complete([{'role':'user','content':'Q'}])
        self.assertNotIn('fake-key',str(error.exception))




    def test_invalid_response_timeout_and_unfinished_output(self):
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


    def test_legacy_limits_do_not_bound_requests_or_responses(self):
        response = json.dumps({'choices':[{'finish_reason':'stop','message':{'content':'x' * 2_000_001}}]}).encode()
        for endpoint in ('https://api.openai.com/v1', 'https://api.deepseek.com/v1', 'https://openrouter.ai/api/v1'):
            with self.subTest(endpoint=endpoint):
                provider = Provider({'endpoint':endpoint, 'model':'test-model', 'max_context_chars':4000,
                                     'max_output_tokens':512, 'timeout':1}, 'fake-test-key')
                messages = [{'role':'assistant','content':'x' * 1_000_001, 'reasoning_content':'y' * 4001}]
                with patch('urllib.request.OpenerDirector.open', return_value=io.BytesIO(response)) as opened:
                    result = provider.complete(messages)
                body = json.loads(opened.call_args.args[0].data)
                self.assertEqual(body['messages'], messages)
                self.assertNotIn('max_completion_tokens', body)
                self.assertNotIn('max_tokens', body)
                self.assertIsNone(opened.call_args.kwargs['timeout'])
                self.assertEqual(len(result['text']), 2_000_001)

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
