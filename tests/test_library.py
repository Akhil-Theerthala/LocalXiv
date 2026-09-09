import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from papers.library import Library


class LibraryTests(unittest.TestCase):
    def test_remove_paper_deletes_only_its_files_and_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            lib = Library(Path(tmp))
            for key in ('one', 'two'):
                directory = Path(tmp) / 'papers' / key
                directory.mkdir(parents=True)
                (directory / 'paper.epub').write_text(key)
                lib.save_paper(key, {'passages': [{'text': 'Searchable'}]}, directory)
                lib.save_generation(key, 'overview', {'text': 'Overview'})
                lib.add_message(key, 'user', 'Question', [])
            lib.remove_paper('one')
            self.assertIsNone(lib.get_paper('one'))
            self.assertIsNone(lib.get_generation('one', 'overview'))
            self.assertEqual([], lib.messages('one'))
            self.assertEqual([], lib.passages('one'))
            self.assertFalse((Path(tmp) / 'papers/one').exists())
            self.assertEqual('two', (Path(tmp) / 'papers/two/paper.epub').read_text())
            self.assertIsNotNone(lib.get_paper('two'))
            with self.assertRaises(KeyError):
                lib.remove_paper('one')

    def test_remove_rejects_outside_directory_and_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lib = Library(root / 'library')
            outside = root / 'outside'
            outside.mkdir()
            (outside / 'keep').write_text('safe')
            for directory in (outside, lib.root, lib.root / 'papers/link'):
                if directory.name == 'link':
                    directory.parent.mkdir()
                    directory.symlink_to(outside, target_is_directory=True)
                lib.save_paper('one', {}, directory)
                with self.assertRaises(ValueError):
                    lib.remove_paper('one')
                self.assertIsNotNone(lib.get_paper('one'))
                self.assertEqual('safe', (outside / 'keep').read_text())

    def test_remove_waits_for_cancelled_worker_and_queued_jobs(self):
        from app.server import Application
        import threading
        import queue
        with tempfile.TemporaryDirectory() as tmp:
            app = Application.__new__(Application)
            app.library = Library(Path(tmp))
            app.lock = threading.RLock()
            app.queue = queue.Queue()
            app.active_job = None
            directory = Path(tmp) / 'papers/one'
            directory.mkdir(parents=True)
            app.library.save_paper('one', {}, directory)
            job = app.library.create_job('summary', {'paper_id': 'one'})
            with self.assertRaises(ValueError):
                app.remove_paper('one')
            app.library.update_job(job['id'], state='cancelled')
            app.active_job = job
            with self.assertRaises(ValueError):
                app.remove_paper('one')
            app.active_job = None
            app.remove_paper('one')

    def test_remove_restores_files_if_database_update_fails(self):
        import sqlite3
        with tempfile.TemporaryDirectory() as tmp:
            lib = Library(Path(tmp))
            directory = Path(tmp) / 'papers/one'
            directory.mkdir(parents=True)
            (directory / 'paper.epub').write_text('keep')
            lib.save_paper('one', {}, directory)
            with lib._connect() as db:
                db.execute("CREATE TRIGGER fail_delete BEFORE DELETE ON papers BEGIN SELECT RAISE(ABORT, 'failure'); END")
            with self.assertRaises(sqlite3.IntegrityError):
                lib.remove_paper('one')
            self.assertEqual('keep', (directory / 'paper.epub').read_text())
            self.assertIsNotNone(lib.get_paper('one'))

    def test_remove_http_requires_auth_and_handles_legacy_ids(self):
        from app.server import make_server
        import http.client
        import threading
        with tempfile.TemporaryDirectory() as tmp:
            server = make_server(Path(tmp), token='test-token')
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                directory = Path(tmp) / 'papers/one'
                directory.mkdir(parents=True)
                server.app.library.save_paper('hep-th/9901001v1', {}, directory)
                path = '/api/papers/hep-th%2F9901001v1/remove'
                for token, expected in [('wrong', 401), ('test-token', 200), ('test-token', 404)]:
                    conn = http.client.HTTPConnection('127.0.0.1', server.server_port)
                    conn.request('POST', path, '{}', {'Authorization': 'Bearer '+token, 'Content-Type': 'application/json'})
                    response = conn.getresponse()
                    self.assertEqual(expected, response.status)
                    response.read()
                    conn.close()
                self.assertEqual([], server.app.library.list_papers())
                self.assertFalse(directory.exists())
                directory.mkdir()
                server.app.library.save_paper('hep-th/9901001v1', {}, directory)
                self.assertEqual(1, len(server.app.library.list_papers()))
            finally:
                server.shutdown()
                server.server_close()
                server.app.close()
                server.app.worker.join(3)
                thread.join(3)

    def test_polling_lists_omit_paper_content_and_keep_all_active_jobs(self):
        with tempfile.TemporaryDirectory() as tmp:
            lib = Library(Path(tmp))
            saved = lib.save_paper('1v1', {'title': 'Paper', 'authors': ['A'],
                'passages': [{'id': 'p1', 'text': 'Long content ' * 1000}], 'chapters': []}, tmp)
            summary = lib.list_papers(summaries=True)[0]
            self.assertNotIn('passages', summary)
            self.assertNotIn('directory', summary)
            self.assertEqual(saved['document_digest'], summary['document_digest'])
            self.assertEqual(['A'], summary['authors'])
            self.assertEqual(saved, lib.get_paper('1v1'))
            active = lib.create_job('import', {'url': 'active'})
            completed = []
            for i in range(4):
                job = lib.create_job('import', {'url': str(i)})
                lib.update_job(job['id'], state='ready')
                completed.append(job['id'])
            self.assertEqual([*reversed(completed[-2:]), active['id']], [j['id'] for j in lib.list_jobs(recent=2)])
            self.assertEqual([active['id']], [j['id'] for j in lib.list_jobs(recent=0)])
            self.assertEqual(5, len(lib.list_jobs()))
            lib.update_job(active['id'], state='ready', result={'download_url': '/files/1v1/paper.epub'})
            self.assertEqual([active['id']], [j['id'] for j in lib.list_jobs(recent=1)],
                             'A long-running job must still appear when it finishes after newer jobs')

    def test_restart_duplicate_search_and_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            lib = Library(Path(tmp))
            job = lib.create_job('import', {'url': 'https://arxiv.org/abs/2505.07309v1'})
            self.assertEqual(job['id'], lib.create_job('import', job['payload'])['id'])
            doc = {'title': 'Test', 'arxiv_id': '2505.07309v1', 'passages': [
                {'id': 'p00001', 'section': 'Intro', 'text': 'Bayesian inference', 'href': 'reader/a#p00001'},
                {'id': 'p00002', 'section': 'Intro', 'text': 'Neighbor', 'href': 'reader/a#p00002'}]}
            lib.save_paper(doc['arxiv_id'], doc, tmp)
            self.assertEqual(2, len(lib.passages(doc['arxiv_id'], 'Bayesian?')))
            lib.save_generation(doc['arxiv_id'], 'overview', {'text': 'saved'})
            lib.add_message(doc['arxiv_id'], 'user', 'Question', [])
            lib.save_settings({'model': 'test', 'api_key': 'secret', 'auto_summary': True, 'kindle_address': 'test@kindle.com'})
            self.assertNotIn('secret', str(lib.get_settings()))
            self.assertTrue(lib.get_settings()['auto_summary'])
            self.assertEqual('test@kindle.com', lib.get_settings()['kindle_address'])
            other = Library(Path(tmp))
            self.assertEqual('interrupted', other.get_job(job['id'])['state'])
            self.assertNotEqual(job['id'], other.create_job('import', job['payload'])['id'])
            self.assertEqual('saved', other.get_generation(doc['arxiv_id'], 'overview')['text'])
            self.assertEqual(1, len(other.messages(doc['arxiv_id'])))
            self.assertEqual(tmp, other.get_paper(doc['arxiv_id'])['directory'])

    def test_atomic_reservation_and_terminal_separation(self):
        with tempfile.TemporaryDirectory() as tmp:
            lib = Library(Path(tmp))
            with ThreadPoolExecutor(max_workers=8) as pool:
                jobs = list(pool.map(lambda _: lib.create_job('import', {'url': 'same'}), range(24)))
            self.assertEqual(1, len({j['id'] for j in jobs}))
            lib.update_job(jobs[0]['id'], state='ready', result={'paper_id': 'v1'})
            summary = lib.create_job('overview', {'paper_id': 'v1'})
            lib.update_job(summary['id'], state='failed', error='Provider unavailable')
            self.assertEqual('ready', lib.get_job(jobs[0]['id'])['state'])
            with self.assertRaises(ValueError):
                lib.update_job(summary['id'], state='queued')
            with self.assertRaises(ValueError):
                lib.save_settings({'endpoint': 'https://secret@example.org/v1'})

    def test_reconversion_invalidates_only_changed_evidence(self):
        import copy
        with tempfile.TemporaryDirectory() as tmp:
            lib = Library(Path(tmp))
            doc = {'arxiv_id': '1v1', 'source_digest': 'original', 'chapters': [],
                   'passages': [{'id': 'p00001', 'text': 'Original', 'href': 'a#p00001'}]}
            first = lib.save_paper('1v1', doc, tmp)
            for changed in ('source', 'passage', 'anchor'):
                lib.save_generation('1v1', 'overview', {'text': 'Old evidence'})
                lib.add_message('1v1', 'assistant', 'Old evidence', doc['passages'])
                same = lib.save_paper('1v1', dict(doc, report={'attempts': ['fresh run']}), tmp)
                self.assertEqual(first['document_digest'], same['document_digest'])
                self.assertIsNotNone(lib.get_generation('1v1', 'overview'))
                self.assertEqual(1, len(lib.messages('1v1')))
                doc = copy.deepcopy(doc)
                if changed == 'source':
                    doc['source_digest'] = 'new source'
                elif changed == 'passage':
                    doc['passages'][0]['text'] = 'New findings'
                else:
                    doc['passages'][0]['href'] = 'b#p00001'
                updated = lib.save_paper('1v1', doc, tmp)
                self.assertNotEqual(first['document_digest'], updated['document_digest'])
                self.assertIsNone(lib.get_generation('1v1', 'overview'))
                self.assertEqual([], lib.messages('1v1'))
                self.assertEqual(doc['passages'], lib.passages('1v1'))
                first = updated

    def test_chat_provenance_persists_with_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            lib = Library(Path(tmp))
            metadata = {'model': 'test', 'prompt_revision': '1', 'source_digest': 'archive',
                        'document_digest': 'document', 'usage': {'total_tokens': 4},
                        'evidence_passages': ['p00001'], 'evidence_scope': 'search_with_neighbors'}
            lib.add_message('1v1', 'assistant', 'Answer [p00001]', [], metadata=metadata)
            self.assertEqual(metadata, Library(Path(tmp)).messages('1v1')[0]['metadata'])
