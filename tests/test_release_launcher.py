"""Portable launcher paths, migration safety and version handoff without providers."""
import fcntl
from contextlib import closing
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch

from app import server
from native import host
from papers.convert import sandbox_profile
from papers import convert
from papers.library import Library
import sqlite3


class ReleaseLauncherTests(unittest.TestCase):
    def test_bundled_shell_ignores_developer_tools_and_python_injection(self):
        with tempfile.TemporaryDirectory(prefix='LocalXiv relocation ') as tmp:
            root = Path(tmp)
            app = root / 'Resources/app'
            tools = root / 'Resources/runtime/bin'
            app.mkdir(parents=True)
            tools.mkdir(parents=True)
            shutil.copyfile(Path(__file__).resolve().parents[1] / 'launch.command', app / 'launch.command')
            python = tools / 'python3'
            python.write_text('#!/bin/sh\n/usr/bin/env\nprintf "ARG:%s\\n" "$@"\n')
            python.chmod(0o755)
            result = subprocess.run(['/bin/bash', str(app / 'launch.command'), '--serve', '--data-dir', str(root / 'library')],
                                    env={**os.environ, 'PYTHONPATH': '/unsafe', 'PYTHONHOME': '/unsafe',
                                         'NODE_OPTIONS': '--require=/unsafe', 'PERL5LIB': '/unsafe'},
                                    text=True, capture_output=True, check=True)
            lines = result.stdout.splitlines()
            self.assertIn(f'PATH={tools}:/usr/bin:/bin:/usr/sbin:/sbin', lines)
            self.assertIn('PYTHONDONTWRITEBYTECODE=1', lines)
            self.assertIn('PYTHONNOUSERSITE=1', lines)
            self.assertFalse(any('/unsafe' in line for line in lines))
            self.assertNotIn('ARG:--open', lines)
            self.assertIn('ARG:app.server', lines)
            self.assertEqual(lines[lines.index('ARG:--port') + 1], 'ARG:0')

    def test_migration_locked_library_and_existing_destination_are_preserved(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(Path, 'home', return_value=Path(tmp)):
            root = Path(tmp) / 'Library/Application Support'
            old, new = root / 'PapersToKindle/library', root / 'LocalXiv/library'
            old.mkdir(parents=True)
            (old / 'papers.db').write_bytes(b'original library')
            (old / 'session.json').write_text('{}')
            with (old / 'server.lock').open('a') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with self.assertRaisesRegex(SystemExit, 'service is running'):
                    server.migrate_library(new)
                self.assertFalse(new.exists())
            server.migrate_library(new)
            self.assertEqual((new / 'papers.db').read_bytes(), b'original library')
            self.assertFalse((new / 'session.json').exists())
            old.mkdir()
            (old / 'papers.db').write_bytes(b'separate library')
            server.migrate_library(new)
            self.assertEqual((new / 'papers.db').read_bytes(), b'original library')
            self.assertEqual((old / 'papers.db').read_bytes(), b'separate library')

    def test_moved_library_repairs_only_its_missing_absolute_directories(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(Path, 'home', return_value=Path(tmp)):
            base = Path(tmp) / 'Library/Application Support'
            old, new = base / 'PapersToKindle/library', base / 'LocalXiv/library'
            library = Library(old)
            directory = old / 'papers/sample'
            directory.mkdir(parents=True)
            (directory / 'paper.epub').write_bytes(b'saved epub')
            library.save_paper('sample', {'title': 'Saved', 'artifacts': {'epub': 'paper.epub'}}, directory)
            external = Path(tmp) / 'external'
            external.mkdir()
            library.save_paper('external', {'title': 'Separate'}, external)
            server.migrate_library(new)
            # Add malformed data to prove that a later failure rolls the entire repair back.
            database = new / 'library.sqlite3'
            with closing(sqlite3.connect(database)) as db, db:
                db.execute('INSERT INTO papers VALUES (?,?)', ('broken', 'invalid json'))
            with self.assertRaises(json.JSONDecodeError):
                Library(new)
            with closing(sqlite3.connect(database)) as db, db:
                value = json.loads(db.execute("SELECT value FROM papers WHERE id='sample'").fetchone()[0])
                self.assertEqual(value['directory'], str(directory))
                db.execute("DELETE FROM papers WHERE id='broken'")
            repaired = Library(new)
            paper = repaired.get_paper('sample')
            self.assertEqual(Path(paper['directory']), (new / 'papers/sample').resolve())
            self.assertEqual((Path(paper['directory']) / paper['artifacts']['epub']).read_bytes(), b'saved epub')
            self.assertEqual(repaired.get_paper('external')['directory'], str(external))
            # Reopening is idempotent, including an installer that had already moved the folder.
            self.assertEqual(Library(new).get_paper('sample'), paper)

    def test_health_identity_blocks_stale_service_without_stopping_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            httpd = server.make_server(directory, token='test')
            thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            thread.start()
            session = directory / 'session.json'
            session.write_text(json.dumps({'port': httpd.server_port, 'token': 'test'}))
            try:
                with patch.object(server, 'RUNTIME_ID', 'previous-build'):
                    old = server.active_session(session)
                self.assertEqual(old['runtime_id'], 'previous-build')
                with patch.object(server, 'BUNDLED', True), patch.object(server, 'RUNTIME_ID', 'new-build'), \
                     patch.object(server, 'active_session', return_value=old), \
                     patch('sys.argv', ['server', '--data-dir', str(directory)]):
                    with self.assertRaisesRegex(SystemExit, 'older LocalXiv background service'):
                        server.main()
                self.assertTrue(thread.is_alive())
            finally:
                httpd.shutdown()
                httpd.server_close()
                httpd.app.close()
                httpd.app.worker.join(3)

    def test_handoff_and_open_support_both_application_folders(self):
        for bundle in (Path('/Applications/LocalXiv.app'), Path.home() / 'Applications/LocalXiv.app'):
            launcher = bundle / 'Contents/Resources/app/launch.command'
            executable = bundle / 'Contents/MacOS/LocalXiv'
            with self.subTest(bundle=bundle), patch.object(Path, 'is_file', lambda path: path in (launcher, executable)), \
                 patch.object(subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)) as run:
                result = host.import_local_paper('https://arxiv.org/abs/2401.01234v2')
                self.assertTrue(result['ok'])
                self.assertEqual(run.call_args.args[0][0], str(launcher))
                server.open_library({'port': 8765, 'token': 'test'}, Path.home() / 'Library/Application Support/LocalXiv/library')
                self.assertEqual(run.call_args.args[0], ['/usr/bin/open', str(bundle)])

    def test_child_servers_and_workers_use_the_relocated_python_wrapper(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = Path(tmp) / 'Resources/app'
            runtime = app.parent / 'runtime'
            runtime.mkdir(parents=True)
            work = Path(tmp) / 'library'
            work.mkdir()
            old = {'port': 8765, 'token': 'test', 'runtime_id': server.RUNTIME_ID}
            with patch.object(server, 'BUNDLED', True), patch.object(server, 'APP_ROOT', app), \
                 patch.object(server, 'active_session', side_effect=[None, old]), \
                 patch.object(server, 'queue_import'), patch.object(server.time, 'sleep'), \
                 patch.object(subprocess, 'Popen') as spawn, \
                 patch('sys.argv', ['server', '--data-dir', str(work), '--import-url', 'https://arxiv.org/abs/2401.01234']):
                server.main()
                self.assertEqual(spawn.call_args.args[0][0], str(runtime / 'bin/python3'))
            # Stop at the process boundary: inspect the real conversion command and clean environment.
            for name in ('native/host.py', 'papers/worker.py', 'papers/convert.py', 'papers/document.py',
                         'papers/citations.py', 'papers/pdf.py', 'papers/math.js', 'papers/assets/ieee.csl', 'package-lock.json'):
                path = app / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            with patch.object(convert, '__file__', str(app / 'papers/convert.py')), \
                 patch.object(convert.shutil, 'which', return_value='/usr/bin/sandbox-exec'), \
                 patch.object(subprocess, 'Popen', side_effect=RuntimeError('process boundary')) as spawn:
                with self.assertRaisesRegex(RuntimeError, 'process boundary'):
                    convert.convert_paper(work, {})
                self.assertEqual(spawn.call_args.args[0][3], str(runtime.resolve() / 'bin/python3'))
                self.assertEqual(spawn.call_args.kwargs['env']['PYTHONPATH'], str(app.resolve()))
                self.assertNotIn('OPENAI_API_KEY', spawn.call_args.kwargs['env'])

    def test_sandbox_reads_sibling_runtime_but_does_not_grant_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = Path(tmp) / 'Resources/app'
            runtime = app.parent / 'runtime'
            app.mkdir(parents=True)
            runtime.mkdir()
            profile = sandbox_profile(Path(tmp) / 'work', app)
            self.assertIn('(allow file-read* (subpath ' + json.dumps(str(runtime.resolve())) + '))', profile)
            self.assertIn('(deny default)', profile)
            self.assertNotIn('(allow network', profile)
            self.assertIn('com.apple.securityd', profile)


if __name__ == '__main__':
    unittest.main()
