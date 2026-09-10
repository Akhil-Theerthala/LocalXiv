"""Update feed monotonicity and authenticated, idle-only service shutdown."""
import http.client
import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import unittest
import sys
from types import SimpleNamespace
from unittest.mock import patch

from app.macos.publish_update_feed import stage, SPARKLE
from app.server import make_server, RUNTIME_ID


class LocalReleaseTests(unittest.TestCase):
    def test_draft_is_signed_locally_without_publication(self):
        module_path = Path(__file__).resolve().parents[1] / 'app/macos/release-local.py'
        spec = importlib.util.spec_from_file_location('release_local', module_path)
        release = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'sparkle': __import__('app.macos.sparkle', fromlist=['']),
                                    'publish_update_feed': __import__('app.macos.publish_update_feed', fromlist=[''])}):
            spec.loader.exec_module(release)
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / 'signed'
            calls = []
            def command(*args, **kwargs):
                calls.append(args)
                if args[:3] == ('gh', 'release', 'view'):
                    return SimpleNamespace(stdout='{"isDraft":true}')
                if args[:3] == ('gh', 'release', 'download'):
                    directory.joinpath('release.json').write_text('{"version":"0.0.5"}')
                    directory.joinpath('LocalXiv.dmg').write_bytes(b'archive')
                    directory.joinpath('SHA256SUMS').write_text('original')
            def sign(path):
                self.assertTrue((path / 'LocalXiv.app').is_symlink())
                (path / 'appcast.xml').write_text('signed feed')
            with patch.object(release, 'run', side_effect=command), patch.object(release, 'appcast', side_effect=sign):
                release.prepare('v0.0.5', directory)
            self.assertFalse((directory / 'LocalXiv.app').is_symlink())
            self.assertIn('appcast.xml', (directory / 'SHA256SUMS').read_text())
            self.assertTrue(any(c[:2] == ('hdiutil', 'detach') for c in calls))
            self.assertFalse(any(c[:3] in [('gh', 'release', 'upload'), ('gh', 'release', 'edit')] for c in calls))
            with patch.object(release, 'run', return_value=SimpleNamespace(stdout='{"isDraft":false}')):
                with self.assertRaisesRegex(ValueError, 'unpublished drafts'):
                    release.prepare('v0.0.5', Path(temporary) / 'rejected')
            self.assertFalse((Path(temporary) / 'rejected').exists())


class UpdateTests(unittest.TestCase):
    def test_feed_cannot_roll_back_or_publish_unsigned_archive(self):
        with tempfile.TemporaryDirectory() as temporary:
            source, destination = (Path(temporary) / n for n in ('new.xml', 'appcast.xml'))
            def feed(number, signature='signature'):
                return (f'<rss xmlns:sparkle="{SPARKLE[1:-1]}"><channel><item>'
                        f'<sparkle:version>{number}</sparkle:version><enclosure sparkle:edSignature="{signature}"/>'
                        '</item></channel></rss>')
            source.write_text(feed(20))
            self.assertTrue(stage(source, destination))
            source.write_text(feed(19))
            self.assertFalse(stage(source, destination))
            self.assertEqual(feed(20), destination.read_text())
            source.write_text(feed(21, ''))
            with self.assertRaises(ValueError):
                stage(source, destination)
            self.assertEqual(feed(20), destination.read_text())

    def test_shutdown_requires_auth_correct_runtime_and_no_jobs(self):
        with tempfile.TemporaryDirectory() as temporary:
            server = make_server(temporary, token='test-token')
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            def request(token='test-token', runtime=RUNTIME_ID):
                connection = http.client.HTTPConnection('127.0.0.1', server.server_port)
                connection.request('POST', '/api/update/shutdown', json.dumps({'runtime_id':runtime}),
                    {'Content-Type':'application/json', 'Authorization':'Bearer ' + token})
                response = connection.getresponse()
                result = response.status, json.loads(response.read())
                connection.close()
                return result
            try:
                self.assertEqual(401, request(token='wrong')[0])
                self.assertEqual(409, request(runtime='old-version')[0])
                job = server.app.library.create_job('reading', {'paper_id':'fixture'})
                self.assertEqual((409, {'busy':True}), request())
                server.app.library.update_job(job['id'], state='cancelled')
                server.app.active_job = job
                self.assertEqual(409, request()[0])  # Cancellation does not mean the worker has exited.
                server.app.active_job = None
                with patch.object(server, 'shutdown') as shutdown:
                    self.assertEqual((200, {'ready':True}), request())
                    with self.assertRaisesRegex(ValueError, 'restarting'):
                        server.app.submit('import', {'url':'anything'})
            finally:
                server.shutdown(); server.server_close(); server.app.close()
                thread.join(3); server.app.worker.join(3)
