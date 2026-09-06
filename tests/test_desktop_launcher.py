import unittest
from pathlib import Path
from unittest.mock import patch
from app.server import open_library

class DesktopLauncherTests(unittest.TestCase):
    def test_installed_library_uses_native_app_and_custom_library_uses_browser(self):
        session = {'port': 8765, 'token': 'test'}
        with patch('app.server.Path.is_file', return_value=True), patch('app.server.subprocess.run') as run, patch('app.server.webbrowser.open') as browser:
            open_library(session, Path.home()/'Library/Application Support/LocalXiv/library')
            run.assert_called_once_with(['/usr/bin/open', '/Applications/LocalXiv.app'], check=True)
            browser.assert_not_called()
            run.reset_mock()
            open_library(session, Path('/private/tmp/separate-library'))
            run.assert_not_called()
            browser.assert_called_once_with('http://127.0.0.1:8765/#token=test')

class LibraryMigrationTests(unittest.TestCase):
    def test_migration_preserves_data_and_refuses_a_running_library(self):
        import fcntl
        import subprocess
        import sys
        import tempfile
        script = (Path(__file__).resolve().parents[1] / 'install-app.sh').read_text().split("<<'MIGRATE'\n", 1)[1].split('\nMIGRATE', 1)[0]
        with tempfile.TemporaryDirectory() as tmp:
            old, new = Path(tmp)/'old/library', Path(tmp)/'new/library'
            old.mkdir(parents=True)
            (old/'papers.db').write_bytes(b'saved papers')
            (old/'session.json').write_text('{}')
            with (old/'server.lock').open('a') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                result = subprocess.run([sys.executable, '-c', script, str(old), str(new)], capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertTrue(old.is_dir())
                self.assertFalse(new.exists())
            subprocess.run([sys.executable, '-c', script, str(old), str(new)], check=True, capture_output=True)
            self.assertEqual((new/'papers.db').read_bytes(), b'saved papers')
            self.assertFalse((new/'session.json').exists())
            self.assertFalse(old.exists())
            old.mkdir(parents=True)
            (old/'papers.db').write_bytes(b'separate library')
            subprocess.run([sys.executable, '-c', script, str(old), str(new)], check=True, capture_output=True)
            self.assertEqual((new/'papers.db').read_bytes(), b'saved papers')
            self.assertEqual((old/'papers.db').read_bytes(), b'separate library')
