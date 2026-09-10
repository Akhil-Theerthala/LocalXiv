"""Exercise real HTTP boundaries and durable worker transitions without provider/Mail calls."""
import http.client
import hashlib
import io
import shutil
import zipfile
import xml.etree.ElementTree as ET
import json
from papers.exports import artifact
from pathlib import Path
import tempfile
import subprocess
import sys
import threading
import time
import unittest
from unittest.mock import patch

from app.server import make_server


class ApplicationHTTPTests(unittest.TestCase):
    def setUp(self):
        html_unavailable = patch('papers.arxiv_html.retrieve', side_effect=ValueError('No HTML fixture'))
        html_unavailable.start()
        self.addCleanup(html_unavailable.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.server = make_server(Path(self.temp.name), token='test-session-token')
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.app = self.server.app
        self.directory = Path(self.temp.name) / 'papers' / 'sample'
        (self.directory / 'reader').mkdir(parents=True)
        (self.directory / 'reader' / 'one.xhtml').write_text('<html><body>Paper</body></html>')
        (self.directory / 'paper.epub').write_bytes(b'EPUB fixture')
        (self.directory / 'source.tar').write_bytes(b'private source')
        self.app.library.save_paper('hep-th/9901001v1', {'title': 'Example', 'passages': []}, str(self.directory))

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.app.close()
        self.app.worker.join(3)
        self.temp.cleanup()

    def request(self, path, body=None, headers=None, raw=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
        supplied = {'Authorization': 'Bearer test-session-token'}
        if body is not None or raw is not None:
            supplied['Content-Type'] = 'application/json'
        supplied.update(headers or {})
        conn.request('POST' if body is not None or raw is not None else 'GET', path,
                     json.dumps(body) if raw is None and body is not None else raw, supplied)
        response = conn.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        conn.close()
        return result

    def test_auth_host_origin_and_static(self):
        self.assertEqual(self.request('/api/health')[0], 200)
        for headers in ({'Authorization': ''}, {'Authorization': 'Bearer wrong'}):
            self.assertEqual(self.request('/api/health', headers=headers)[0], 401)
        for headers in ({'Host': 'evil.test'}, {'Origin': 'https://evil.test'}, {'Origin': 'null'}):
            self.assertEqual(self.request('/api/health', headers=headers)[0], 403)
        self.assertEqual(self.request('/')[0], 200)
        self.assertEqual(self.request('/static/app.js')[0], 200)
        self.assertEqual(self.request('/static/app.css')[0], 200)
        self.assertEqual(self.request('/static/math-config.js')[0], 200)
        status, headers, body = self.request('/static/mathjax.js')
        self.assertEqual(status, 200)
        self.assertEqual(headers['Content-Type'], 'text/javascript')
        self.assertGreater(len(body), 100000)
        self.assertEqual(self.request('/node_modules/mathjax-full/package.json')[0], 404)

    def test_onboarding_persists_without_keys(self):
        with patch('app.server.get_key', return_value=''), patch('app.server.set_key') as save_key:
            status, _, body = self.request('/api/settings', body={'onboarding_complete':True,'kindle_email':'reader@kindle.com'})
            self.assertEqual(status,200)
            self.assertTrue(json.loads(body)['onboarding_complete'])
            self.assertEqual(self.app.library.get_settings()['kindle_address'],'reader@kindle.com')
            save_key.assert_not_called()
            self.assertEqual(self.request('/api/settings',body={'onboarding_complete':'yes'})[0],400)

    def test_overview_preferences_persist_independently_and_reject_invalid_values(self):
        from papers.library import Library
        with patch('app.server.get_key', return_value=''), patch('app.server.set_key') as save_key:
            self.assertEqual(self.app.settings()['overview_language'], 'casual')
            self.assertEqual(self.app.settings()['overview_length'], 'medium')
            self.assertEqual(self.request('/api/settings', body={'overview_language': 'formal'})[0], 200)
            status, _, body = self.request('/api/settings', body={'overview_length': 'large'})
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(body)['overview_language'], 'formal')
            saved = Library(Path(self.temp.name)).get_settings()
            self.assertEqual(saved['overview_language'], 'formal')
            self.assertEqual(saved['overview_length'], 'large')
            for field, bad in (('overview_language', 'friendly'), ('overview_length', 'casual'),
                               ('overview_language', []), ('overview_length', None)):
                self.assertEqual(self.request('/api/settings', body={field: bad, 'api_key': 'must-not-save'})[0], 400)
            save_key.assert_not_called()
            self.assertEqual(saved, self.app.library.get_settings())
    def test_legacy_request_limits_are_ignored_and_removed_on_save(self):
        old = {'model':'saved-model', 'overview_language':'formal',
               'max_context_chars':4000, 'max_output_tokens':512, 'timeout':1}
        with self.app.library._connect() as db:
            db.execute('INSERT OR REPLACE INTO settings VALUES (1,?)', (json.dumps(old),))
        self.assertEqual(self.app.library.get_settings(), {'model':'saved-model', 'overview_language':'formal'})
        with patch('app.server.get_key', return_value=''):
            status, _, body = self.request('/api/settings', body={**old, 'overview_length':'large'})
        self.assertEqual(status, 200)
        self.assertTrue({'max_context_chars', 'max_output_tokens', 'timeout'}.isdisjoint(json.loads(body)))
        with self.app.library._connect() as db:
            saved = json.loads(db.execute('SELECT value FROM settings WHERE id=1').fetchone()[0])
        self.assertEqual(saved, {'model':'saved-model', 'overview_language':'formal', 'overview_length':'large'})

    def test_connection_checks_unsaved_values_without_saving_credentials(self):
        original = self.app.library.get_settings()
        with patch('app.server.Provider') as provider, patch('app.server.get_key',return_value='saved-secret'), patch('app.server.set_key') as save:
            provider.return_value.url = 'https://example.test/v1/chat/completions'
            provider.return_value.complete.return_value = {'text':'OK','usage':{}}
            status, _, body = self.request('/api/test-connection',body={'endpoint':'https://example.test/v1','model':'draft-model','api_key':'draft-secret'})
            self.assertEqual(status,200)
            settings, key = provider.call_args.args
            self.assertEqual(settings['model'],'draft-model'); self.assertEqual(key,'draft-secret')
            self.assertTrue({'max_context_chars', 'max_output_tokens', 'timeout'}.isdisjoint(settings))
            self.assertNotIn(b'draft-secret',body)
            save.assert_not_called(); self.assertEqual(self.app.library.get_settings(),original)
            provider.call_args.kwargs['on_usage']({'prompt_tokens':9,'completion_tokens':2})
            with self.app.library._connect() as db:
                logged = json.loads(db.execute('SELECT value FROM usage').fetchone()[0])
            self.assertEqual(logged['prompt_tokens'],9); self.assertEqual(logged['completion_tokens'],2)
            self.assertNotIn('draft-secret',json.dumps(logged))
            self.request('/api/test-connection',body={'endpoint':'https://example.test/v1','model':'saved-model'})
            self.assertEqual(provider.call_args.args[1],'saved-secret')
        self.assertEqual(self.request('/api/test-connection',body={'api_key':123})[0],400)
        with patch('app.server.get_key',return_value=''):
            self.assertEqual(self.request('/api/test-connection',body={})[0],400)

    def test_tutorial_imports_real_paper_once_without_automatic_send_or_overview(self):
        self.app.library.remove_paper('1706.03762v7')
        metadata = {'arxiv_id':'1706.03762v7','title':'Attention Is All You Need','source_digest':'abc'}
        document = dict(metadata,passages=[],chapters=[{'path':'reader/main.xhtml'}])
        self.app.library.save_settings({'auto_send':True,'auto_summary':True,'model':'test-model'})
        with patch('papers.acquire.acquire',return_value=metadata) as acquire, patch('papers.convert.convert_paper',return_value=document), patch('app.server.get_key',return_value='key'), patch.object(self.app,'recommendations',return_value={}):
            status, _, body = self.request('/api/tutorial',body={})
            self.assertEqual(status,202)
            self.app.queue.join()
            self.assertEqual([j['kind'] for j in self.app.library.list_jobs()],['import'])
            acquire.assert_called_once()
            self.assertEqual(acquire.call_args.args[0],'https://arxiv.org/abs/1706.03762v7')
            status, _, body = self.request('/api/tutorial',body={})
            self.assertEqual(status,200)
            self.assertEqual(json.loads(body)['paper_id'],'1706.03762v7')
            self.assertEqual(acquire.call_count,1)

    def test_files_legacy_ids_cookie_and_traversal(self):
        base = '/files/hep-th%2F9901001v1/'
        status, headers, content = self.request(base + 'reader/one.xhtml?token=test-session-token', headers={'Authorization': ''})
        self.assertEqual(status, 200)
        self.assertIn(b'Paper', content)
        self.assertIn("sandbox allow-same-origin", headers['Content-Security-Policy'])
        self.assertNotIn('allow-scripts', headers['Content-Security-Policy'])
        cookie = headers['Set-Cookie'].split(';')[0]
        self.assertEqual(self.request(base + 'reader/one.xhtml', headers={'Authorization': '', 'Cookie': cookie})[0], 200)
        for path in ('../library.sqlite3', 'reader/%2e%2e/%2e%2e/library.sqlite3', 'source.tar', 'reader/%2fetc/passwd'):
            self.assertEqual(self.request(base + path)[0], 403)
        (self.directory / 'reader' / 'escape').symlink_to(Path(self.temp.name) / 'library.sqlite3')
        self.assertEqual(self.request(base + 'reader/escape')[0], 403)

    def test_invalid_input_and_export(self):
        self.assertEqual(self.request('/api/import', raw='{')[0], 400)
        self.assertEqual(self.request('/api/import', body=[])[0], 400)
        self.assertEqual(self.request('/api/import', body={'url': 'https://evil.test/abs/2501.00001'})[0], 400)
        base = '/api/papers/hep-th%2F9901001v1/'
        self.assertEqual(self.request(base + 'chat', body={'question': ''})[0], 400)
        self.assertEqual(self.request(base + 'export', body={'kind': '../source'})[0], 400)
        status, _, raw = self.request(base + 'export', body={})
        self.assertEqual(status, 202)
        job_id = json.loads(raw)['job']['id']
        self.app.queue.join()
        job = self.app.library.get_job(job_id)
        self.assertEqual(job['state'], 'ready')
        self.assertEqual(self.request(job['result']['download_url'])[0], 200)
        self.assertEqual(self.request('/api/papers/hep-th%2F9901001v1')[0], 200)

    def test_delivery_records_exact_artifact_and_ambiguous_outcome(self):
        self.app.library.save_settings({'kindle_address': 'reader@kindle.com'})
        semantic = self.directory / 'semantic.epub'
        semantic.write_bytes(b'Semantic EPUB fixture')
        payload = {'paper_id': 'hep-th/9901001v1', 'kind': 'paper', 'profile': 'semantic'}
        with patch('native.host.send_with_mail') as send:
            job = self.app.submit('send', payload)
            self.app.queue.join()
            completed = self.app.library.get_job(job['id'])
            self.assertEqual(completed['state'], 'ready')
            result = completed['result']
            self.assertEqual(result['artifact_sha256'], hashlib.sha256(semantic.read_bytes()).hexdigest())
            self.assertEqual(result['artifact'], 'semantic.epub')
            self.assertEqual(result['recipient'], 'reader@kindle.com')
            self.assertEqual(result['requested_at'], job['created_at'])
            self.assertEqual(result['profile'], 'semantic')
            self.assertEqual(result['delivery'], 'handed_to_mail')
            send.assert_called_once_with(semantic, 'reader@kindle.com', 'Example')
        with patch('native.host.send_with_mail', side_effect=RuntimeError('Mail timed out')) as send:
            job = self.app.submit('send', payload)
            self.app.queue.join()
            failed = self.app.library.get_job(job['id'])
            self.assertEqual(failed['state'], 'failed')
            self.assertEqual(failed['result']['delivery'], 'unknown')
            self.assertEqual(failed['result']['artifact_sha256'], result['artifact_sha256'])
            send.assert_called_once()

    def test_invalid_combined_export_does_not_replace_previous_book(self):
        paper = self.app.library.get_paper('hep-th/9901001v1')
        paper.update(authors='A. Researcher', arxiv_id=paper['id'])
        self.app.library.save_generation(paper['id'], 'overview', {'text': 'Overview'})
        overview = self.directory / 'overview.epub'
        overview.write_bytes(b'overview fixture')
        combined = self.directory / 'combined.epub'
        combined.write_bytes(b'previous valid combined book')
        def build(_papers, _title, output):
            output.write_bytes(b'invalid candidate')
        failed_check = subprocess.CompletedProcess(['epubcheck'], 1, 'EPUB error', '')
        with patch('papers.document.export_overview', return_value=overview), patch('native.host.build_anthology', side_effect=build), patch('papers.exports.shutil.which', return_value='/epubcheck'), patch('papers.exports.subprocess.run', return_value=failed_check):
            with self.assertRaisesRegex(ValueError, 'Combined EPUB validation failed'):
                artifact(self.app.library, paper, 'both', 'kindle')
        self.assertEqual(combined.read_bytes(), b'previous valid combined book')
        self.assertFalse((self.directory / '.combined.epub').exists())

    def test_duplicate_cancel_retry_and_failure(self):
        entered, resume = threading.Event(), threading.Event()
        def operation(job):
            entered.set()
            resume.wait(3)
            self.app.checkpoint(job['id'])
            raise ValueError('Specific operation error')
        with patch.object(self.app, 'execute', side_effect=operation):
            first = self.app.submit('summary', {'paper_id': 'same'})
            self.assertTrue(entered.wait(2))
            duplicate = self.app.submit('summary', {'paper_id': 'same'})
            self.assertEqual(first['id'], duplicate['id'])
            self.assertEqual(self.request('/api/jobs/' + first['id'] + '/cancel', body={})[0], 200)
            resume.set()
            self.app.queue.join()
            self.assertEqual(self.app.library.get_job(first['id'])['state'], 'cancelled')
            retry = self.app.submit('summary', {'paper_id': 'same'})
            self.app.queue.join()
            self.assertNotEqual(first['id'], retry['id'])
            self.assertEqual(self.app.library.get_job(retry['id'])['error'], 'Specific operation error')

    def test_chat_retains_history_and_all_whole_paper_evidence(self):
        passages = [
            {'id': 'p00001', 'text': 'Unrelated material. ' * 3000, 'section': 'Background'},
            {'id': 'p00002', 'text': 'Other background.', 'section': 'Background'},
            {'id': 'p00003', 'text': 'Caption: evaluation on the held-out corpus.', 'section': 'Results'},
            {'id': 'p00004', 'text': 'Zephyr achieves 91 percent.', 'section': 'Results'},
            {'id': 'p00005', 'text': 'The adjacent comparison uses the same test split.', 'section': 'Results'},
        ]
        paper_id = 'hep-th/9901001v1'
        self.app.library.save_paper(paper_id, {'title': 'Example', 'passages': passages}, str(self.directory))
        self.app.library.save_settings({'model': 'test-model', 'max_context_chars': 6000})
        self.app.library.add_message(paper_id, 'user', 'Old conversation ' * 2000, [])
        self.app.library.add_message(paper_id, 'assistant', 'Old answer ' * 2000, [])
        def answer(provider, question, evidence, history):
            expected = passages if question == 'Summarize the whole paper' else passages[2:]
            self.assertEqual(evidence, expected)
            if question in ('Explain Zephyr', 'Summarize the whole paper'):
                self.assertEqual(history[0]['content'], 'Old conversation ' * 2000)
                self.assertEqual(history[1]['content'], 'Old answer ' * 2000)
            return {'text': '91 percent [p00004]', 'sources': [next(p for p in evidence if p['id'] == 'p00004')]}
        with patch('app.server.get_key', return_value=''), patch('app.server.answer_question', side_effect=answer) as call:
            narrow = self.app.submit('chat', {'paper_id': paper_id, 'question': 'Explain Zephyr'})
            self.app.queue.join()
            self.assertEqual(self.app.library.get_job(narrow['id'])['state'], 'ready')
            metadata = self.app.library.messages(paper_id)[-1]['metadata']
            self.assertEqual(metadata['evidence_scope'], 'search_with_neighbors')
            self.assertEqual(metadata['evidence_passages'], ['p00003', 'p00004', 'p00005'])
            self.assertEqual(metadata['model'], 'test-model')
            for question in ('What does the paper report for Zephyr?', 'How does the Zephyr method perform?'):
                with patch.object(self.app.library, 'messages', return_value=[]):
                    specific = self.app.submit('chat', {'paper_id': paper_id, 'question': question})
                    self.app.queue.join()
                self.assertEqual(self.app.library.get_job(specific['id'])['state'], 'ready')
            broad = self.app.submit('chat', {'paper_id': paper_id, 'question': 'Summarize the whole paper'})
            self.app.queue.join()
            self.assertEqual(self.app.library.get_job(broad['id'])['state'], 'ready')
            self.assertEqual(call.call_count, 4)

    def test_failed_conversion_exposes_pdf_without_replacing_ready_paper(self):
        metadata = {'arxiv_id': '2501.00001v1', 'title': 'Fallback', 'authors': 'A', 'source_digest': 'abc'}
        def acquire(url, directory):
            (directory / 'original.pdf').write_bytes(b'%PDF-1.4 fixture')
            (directory / 'source').write_bytes(b'source archive')
            return metadata
        with patch('papers.acquire.acquire', side_effect=acquire), patch('papers.convert.convert_paper', side_effect=ValueError('Unsupported source')):
            job = self.app.submit('import', {'url': 'https://arxiv.org/abs/2501.00001'})
            self.app.queue.join()
            result = self.app.library.get_job(job['id'])
            self.assertEqual(result['state'], 'failed')
            self.assertEqual(result['result']['paper_id'], metadata['arxiv_id'])
            failed = self.app.library.get_paper(metadata['arxiv_id'])
            self.assertEqual(failed['status'], 'conversion_failed')
            for filename in ('original.pdf', 'source', 'report.json'):
                self.assertEqual(self.request('/files/2501.00001v1/' + filename)[0], 200)
            ready = self.app.library.save_paper(metadata['arxiv_id'], {'title': 'Previously ready', 'chapters': [{'path': 'reader/one.xhtml'}]}, str(self.directory))
            retry = self.app.submit('import', {'url': 'https://arxiv.org/abs/2501.00001'})
            self.app.queue.join()
            self.assertEqual(self.app.library.get_paper(metadata['arxiv_id']), ready)
            self.assertEqual(self.app.library.get_job(retry['id'])['state'], 'failed')

    @unittest.skipUnless(sys.platform == 'darwin', 'PDFKit requires macOS')
    def test_pdf_fallback_import_overview_export_and_delivery(self):
        from tests.test_pdf_fallback import write_pdf
        from papers.pdf import build_pdf_document
        metadata = {'arxiv_id': '2501.00006v1', 'title': 'PDF fallback', 'authors': 'A', 'source_digest': 'source-hash'}
        def acquire(url, directory):
            write_pdf(directory / 'original.pdf')
            return metadata
        def convert(directory, metadata, progress, *, pdf_only=False, html_only=False, source_engine=None):
            if not pdf_only:
                raise ValueError('Unsupported template')
            return build_pdf_document(directory, metadata)
        with patch('papers.acquire.acquire', side_effect=acquire), patch('papers.convert.convert_paper', side_effect=convert):
            job = self.app.submit('import', {'url': 'https://arxiv.org/abs/2501.00006'})
            self.app.queue.join()
        ready = self.app.library.get_job(job['id'])
        self.assertEqual(ready['state'], 'ready', ready.get('error'))
        self.assertEqual(ready['result']['format'], 'pdf')
        self.assertIn('Sending this paper will send the PDF', ready['result']['warning'])
        paper = self.app.library.get_paper(metadata['arxiv_id'])
        self.assertEqual(paper['format'], 'pdf')
        self.assertIn('91 percent', self.app.library.passages(paper['id'])[0]['text'])
        self.assertEqual(paper['report']['epub_error'], 'Unsupported template')
        pdf = Path(paper['directory']) / 'original.pdf'
        self.assertEqual(artifact(self.app.library, paper, 'paper', 'kindle'), pdf)
        self.assertEqual(artifact(self.app.library, paper, 'paper', 'semantic'), pdf)
        with self.assertRaisesRegex(ValueError, 'separately'):
            artifact(self.app.library, paper, 'both', 'kindle')
        status, headers, body = self.request('/files/' + paper['id'] + '/original.pdf')
        self.assertEqual(status, 200)
        self.assertEqual(headers['Content-Type'], 'application/pdf')
        self.assertNotIn('sandbox', headers['Content-Security-Policy'])
        self.assertEqual(body, pdf.read_bytes())
        self.app.library.save_settings({'kindle_address': 'reader@kindle.com', 'model': 'test-model'})
        with patch('native.host.send_with_mail') as send:
            job = self.app.submit('send', {'paper_id': paper['id'], 'kind': 'paper'})
            self.app.queue.join()
            send.assert_called_once_with(pdf, 'reader@kindle.com', paper['title'])
            delivered = self.app.library.get_job(job['id'])['result']
            self.assertEqual(delivered['artifact'], 'original.pdf')
            self.assertEqual(delivered['artifact_sha256'], hashlib.sha256(pdf.read_bytes()).hexdigest())
        with patch('app.server.get_key', return_value=''), patch('app.server.generate_overview', return_value={'text': 'PDF overview', 'sources': []}) as overview:
            job = self.app.submit('summary', {'paper_id': paper['id']})
            self.app.queue.join()
            evidence = overview.call_args.args[1]
            self.assertEqual(evidence['format'], 'pdf')
            self.assertIn('120 examples', evidence['passages'][1]['text'])
            self.assertEqual(self.app.library.get_job(job['id'])['state'], 'ready')
            self.assertEqual(self.app.library.get_generation(paper['id'], 'overview')['text'], 'PDF overview')
        job = self.app.submit('export', {'paper_id': paper['id'], 'kind': 'paper'})
        self.app.queue.join()
        self.assertEqual(self.app.library.get_job(job['id'])['result']['download_url'], '/files/' + paper['id'] + '/original.pdf')

    @unittest.skipUnless(sys.platform == 'darwin', 'PDFKit requires macOS')
    def test_unavailable_source_imports_valid_pdf(self):
        from tests.test_pdf_fallback import write_pdf
        from papers.pdf import build_pdf_document
        def acquire(url, directory):
            (directory / 'metadata.json').write_text(json.dumps({'arxiv_id': '2501.00007v1', 'title': 'PDF only'}))
            write_pdf(directory / 'original.pdf')
            raise ValueError('Source archive unavailable')
        with patch('papers.acquire.acquire', side_effect=acquire), patch('papers.convert.convert_paper', side_effect=lambda directory, metadata, progress, **kw: build_pdf_document(directory, metadata)):
            job = self.app.submit('import', {'url': 'https://arxiv.org/abs/2501.00007'})
            self.app.queue.join()
        ready = self.app.library.get_job(job['id'])
        self.assertEqual(ready['state'], 'ready', ready.get('error'))
        self.assertIn('source files were unavailable', ready['result']['warning'])
        self.assertTrue(self.app.library.get_paper('2501.00007v1')['source_digest'])

    def test_source_download_failure_retains_available_pdf(self):
        def acquire(url, directory):
            (directory / 'metadata.json').write_text(json.dumps({'arxiv_id': '2501.00003v1', 'title': 'PDF only'}))
            (directory / 'original.pdf').write_bytes(b'%PDF-1.4 fixture')
            raise ValueError('No downloadable source archive')
        with patch('papers.acquire.acquire', side_effect=acquire):
            job = self.app.submit('import', {'url': 'https://arxiv.org/abs/2501.00003'})
            self.app.queue.join()
            self.assertEqual(self.app.library.get_job(job['id'])['state'], 'failed')
            self.assertEqual(self.request('/files/2501.00003v1/original.pdf')[0], 200)

    def test_automatic_overview_requires_configured_ai(self):
        metadata = {'arxiv_id': '2501.00002v1', 'title': 'Example', 'authors': 'A', 'source_digest': 'abc'}
        with patch('papers.acquire.acquire', return_value=metadata), patch('papers.convert.convert_paper', return_value=dict(metadata, passages=[{'id': 'p00001', 'text': 'Evidence'}])), patch('app.server.get_key', return_value=''):
            self.assertFalse(self.app.settings()['auto_summary'])
            self.app.submit('import', {'url': 'https://arxiv.org/abs/2501.00002'})
            self.app.queue.join()
            self.assertEqual([j['kind'] for j in self.app.library.list_jobs()], ['import'])
        self.app.library.save_settings({'model': 'test-model', 'auto_summary': True})
        with patch('papers.acquire.acquire', return_value=metadata), patch('papers.convert.convert_paper', return_value=dict(metadata, passages=[{'id': 'p00001', 'text': 'Evidence'}])), patch('app.server.get_key', return_value='fake-key'), patch('app.server.generate_overview', return_value={'text': 'Overview', 'sources': []}), patch('app.server.prepare_reading', return_value=([], [], {})):
            self.app.submit('import', {'url': 'https://arxiv.org/abs/2501.00002'})
            self.app.queue.join()
            self.assertEqual(self.app.library.get_generation(metadata['arxiv_id'], 'bento')['text'], 'Overview')

    @unittest.skipUnless(shutil.which('pandoc') and shutil.which('rsvg-convert') and shutil.which('node'), 'EPUB toolchain is required')
    def test_real_overview_and_combined_exports(self):
        from papers.document import build_document
        from native.host import validate_epub
        metadata = {'arxiv_id': '2501.00004v1', 'title': 'Integration paper', 'authors': 'A. Researcher', 'source_digest': 'fixture'}
        (self.directory / 'reader' / 'one.xhtml').write_text('<html xmlns="http://www.w3.org/1999/xhtml"><head><title>Original</title></head><body><h1>Original result</h1><p>The original result is 91 percent.</p></body></html>')
        document = build_document(self.directory, metadata, 'test-fixture')
        self.app.library.save_paper(metadata['arxiv_id'], document, str(self.directory))
        self.app.library.save_settings({'model': 'fixed-provider'})
        response = {'text': 'The result is 91 percent, with $x=1$ [p00001].', 'usage': {'total_tokens': 42}}
        base = '/api/papers/' + metadata['arxiv_id']
        from tests.test_agent_overviews import CANDIDATE, scripted_provider, render_fixture
        import copy
        candidate=copy.deepcopy(CANDIDATE)
        candidate['text']='The result is 91 percent, with $x=1$ [p00001].\n\n{{figure:fig1}}\n\nConfidence needs context [p00001].'
        with patch('app.server.get_key', return_value=''), patch('papers.ai.Provider.complete', side_effect=scripted_provider(candidate)), patch('papers.html_figures.render', side_effect=render_fixture):
            status, _, raw = self.request(base + '/summary', body={})
            self.assertEqual(status, 202)
            self.app.queue.join()
            self.assertEqual(self.app.library.get_job(json.loads(raw)['job']['id'])['state'], 'ready')
        overview = self.app.library.get_generation(metadata['arxiv_id'], 'overview')
        self.assertEqual(overview['provenance']['model'], 'fixed-provider')
        original = (self.directory / 'paper.epub').read_bytes()
        for kind in ('overview', 'both'):
            for profile in ('kindle', 'semantic'):
                status, _, raw = self.request(base + '/export', body={'kind': kind, 'profile': profile})
                self.assertEqual(status, 202)
                self.app.queue.join()
                job = self.app.library.get_job(json.loads(raw)['job']['id'])
                self.assertEqual(job['state'], 'ready', job['error'])
                status, _, body = self.request(job['result']['download_url'])
                self.assertEqual(status, 200)
                output = self.directory / ('checked-' + kind + '-' + profile + '.epub')
                output.write_bytes(body)
                validate_epub(output, require_png_cover=True)
                with zipfile.ZipFile(io.BytesIO(body)) as book:
                    xhtml = b' '.join(book.read(name) for name in book.namelist() if name.endswith('.xhtml'))
                    self.assertIn(b'The result is 91 percent', xhtml)
                    source_links = [link for name in book.namelist() if name.endswith('.xhtml')
                                    for link in ET.fromstring(book.read(name)).iter()
                                    if link.get('href') == 'https://arxiv.org/abs/' + metadata['arxiv_id']]
                    self.assertTrue(any(''.join(link.itertext()) == 'original paper' for link in source_links))
                    self.assertNotIn(b'[p00001]', xhtml)
                    self.assertNotIn(b'{{figure:', xhtml)
                    self.assertTrue(any(b'Confidence needs' in book.read(name) for name in book.namelist() if name.endswith('.xhtml')))
                    self.assertTrue(any('fig1' in name and name.endswith('.svg') for name in book.namelist()))
                    if kind == 'both':
                        self.assertIn(b'The original result is 91 percent', xhtml)
                        combined_name = 'combined-semantic' if profile == 'semantic' else 'combined'
                        self.assertIn('No errors or warnings detected.', (self.directory / (combined_name + '.epubcheck.log')).read_text())
                    if profile == 'semantic':
                        self.assertTrue(any(ET.fromstring(book.read(name)).find('.//{http://www.w3.org/1998/Math/MathML}math') is not None for name in book.namelist() if name.endswith('.xhtml')))
                    else:
                        self.assertIn(b'math-image', xhtml)
                self.assertEqual((self.directory / 'paper.epub').read_bytes(), original)

    def test_cli_import_acknowledges_running_library_queue(self):
        (Path(self.temp.name) / 'session.json').write_text(json.dumps({'port': self.server.server_port, 'token': self.app.token}))
        with patch.object(self.app, 'execute', return_value={'paper_id': '2501.00005v1'}):
            result = subprocess.run([sys.executable, '-m', 'app.server', '--data-dir', self.temp.name, '--import-url', 'https://arxiv.org/abs/2501.00005'], capture_output=True, text=True, timeout=10)
            self.app.queue.join()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Import queued.', result.stdout)
        self.assertNotIn(self.app.token, result.stdout + result.stderr)
        self.assertEqual(self.app.library.list_jobs()[0]['payload']['url'], 'https://arxiv.org/abs/2501.00005')

    def test_cli_bootstrap_waits_for_authenticated_queue_acceptance(self):
        from app.server import main
        def start(*args, **kwargs):
            (Path(self.temp.name) / 'session.json').write_text(json.dumps({'port': self.server.server_port, 'token': self.app.token}))
            self.assertEqual(kwargs['stdin'], subprocess.DEVNULL)
            self.assertTrue(kwargs['start_new_session'])
            self.assertIs(kwargs['stdout'], kwargs['stderr'])
            self.assertNotIn('--import-url', args[0])
        argv = ['app.server', '--data-dir', self.temp.name, '--import-url', 'https://arxiv.org/abs/2501.00006', '--open']
        with patch('sys.argv', argv), patch('app.server.subprocess.Popen', side_effect=start) as launch, patch.object(self.app, 'execute', return_value={}), patch('app.server.webbrowser.open') as browser, patch('builtins.print') as output:
            main()
            self.app.queue.join()
        launch.assert_called_once()
        self.assertEqual(self.app.library.list_jobs()[0]['payload']['url'], 'https://arxiv.org/abs/2501.00006')
        browser.assert_called_once_with(f'http://127.0.0.1:{self.server.server_port}/#token={self.app.token}')
        output.assert_called_once_with('Import queued. Follow progress in the local library.')

    def test_blog_passes_saved_image_overview_without_queuing_one(self):
        paper_id='2501.00001v1'
        self.app.library.save_paper(paper_id, {'title':'Example','passages':[{'id':'p00001','text':'Evidence'}]}, str(self.directory))
        self.app.library.save_settings({'model':'fixed-provider'})
        saved={'text':'{{figure:fig1}}','figures':[],'provenance':{'created_at':'saved'}}
        self.app.library.save_generation(paper_id,'bento',saved)
        with patch('app.server.get_key',return_value=''), patch('app.server.generate_overview',return_value={'text':'Blog'}) as generate:
            job=self.app.submit('summary',{'paper_id':paper_id})
            self.app.queue.join()
        self.assertEqual('ready',self.app.library.get_job(job['id'])['state'])
        self.assertEqual(saved,generate.call_args.kwargs['image_overview'])
        self.assertEqual(['summary'],[j['kind'] for j in self.app.library.list_jobs()])
        self.assertEqual(saved,self.app.library.get_generation(paper_id,'bento'))

    def test_cancel_running_overview_keeps_existing_generation(self):
        paper_id = 'hep-th/9901001v1'
        self.app.library.save_paper(paper_id, {'title': 'Example', 'passages': [{'id': 'p00001', 'section': 'Result', 'text': 'A result.'}]}, str(self.directory))
        previous = {'text': 'Previously saved overview', 'sources': []}
        self.app.library.save_generation(paper_id, 'overview', previous)
        self.app.library.save_settings({'model': 'fixed-provider'})
        entered, resume = threading.Event(), threading.Event()
        def complete(*args):
            entered.set()
            resume.wait(3)
            return {'text': 'A result [p00001].', 'usage': {}}
        with patch('app.server.get_key', return_value=''), patch('papers.ai.Provider.complete', side_effect=complete):
            job = self.app.submit('summary', {'paper_id': paper_id})
            self.assertTrue(entered.wait(2))
            self.assertEqual(self.request('/api/jobs/' + job['id'] + '/cancel', body={})[0], 200)
            resume.set()
            self.app.queue.join()
        self.assertEqual(self.app.library.get_job(job['id'])['state'], 'cancelled')
        self.assertEqual(self.app.library.get_generation(paper_id, 'overview'), previous)

    def test_failed_figure_keeps_previous_overview(self):
        from tests.overview_fixture import response
        paper_id = '2501.00001v1'
        self.app.library.save_paper(paper_id, {'title': 'Example', 'passages': [{'id': 'p00001', 'section': 'Result', 'text': 'A result.'}]}, str(self.directory))
        previous = {'text': 'Previously saved overview', 'sources': []}
        self.app.library.save_generation(paper_id, 'overview', previous)
        self.app.library.save_settings({'model': 'fixed-provider'})
        with patch('app.server.get_key', return_value=''), patch('papers.ai.Provider.complete', side_effect=response), patch('papers.overview.render_figure', side_effect=ValueError('Figure labels overlap')):
            job = self.app.submit('summary', {'paper_id': paper_id})
            self.app.queue.join()
        self.assertEqual(self.app.library.get_job(job['id'])['state'], 'failed')
        self.assertEqual(self.app.library.get_generation(paper_id, 'overview'), previous)

    def test_settings_key_never_persisted(self):
        with patch('app.server.set_key') as setter, patch('app.server.get_key', return_value='secret-key'):
            status, _, raw = self.request('/api/settings', body={'endpoint': 'https://api.openai.com/v1', 'model': 'example', 'api_key': 'secret-key', 'kindle_email': 'reader@kindle.com'})
            self.assertEqual(status, 200, raw)
            self.assertNotIn(b'secret-key', raw)
            setter.assert_called_once_with('https://api.openai.com/v1', 'secret-key')
            self.assertNotIn('api_key', self.app.library.get_settings())
            self.assertEqual(json.loads(raw)['kindle_email'], 'reader@kindle.com')


if __name__ == '__main__':
    unittest.main()
