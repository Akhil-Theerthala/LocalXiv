"""Native handoff never needs an email and leaves conversion to the local app."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from native import host


class LocalHandoffTests(unittest.TestCase):
    def test_validated_handoff_uses_argument_list_and_no_email(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Library/Application Support/LocalXiv"
            launcher = root / "app/launch.command"
            launcher.parent.mkdir(parents=True)
            launcher.touch()
            with patch.object(Path, 'home', return_value=Path(tmp)), patch.object(Path, 'is_file', lambda path: path == launcher), patch.object(host.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)) as run:
                result = host.process_request({'action': 'import_local', 'url': 'https://www.alphaxiv.org/overview/2401.01234v2?chat=private'})
                self.assertTrue(result['ok'])
                self.assertEqual(run.call_args.args[0], [str(launcher), '--data-dir', str(root / 'library'), '--import-url', 'https://arxiv.org/abs/2401.01234v2'])
                self.assertNotIn('shell', run.call_args.kwargs)
                self.assertIn('Follow progress', result['message'])

    def test_missing_install_and_untrusted_url_do_not_launch(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(Path, 'home', return_value=Path(tmp)), patch.object(Path, 'is_file', return_value=False), patch.object(host.subprocess, 'run') as run:
            for url in ('https://evil.test/abs/2401.01234', 'https://arxiv.org/abs/2401.01234'):
                with self.assertRaises(host.ConversionError):
                    host.process_request({'action': 'import_local', 'url': url})
            run.assert_not_called()

    def test_launch_failure_is_not_reported_as_queued(self):
        with patch.object(Path, 'is_file', return_value=True), patch.object(host.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1)):
            with self.assertRaisesRegex(host.ConversionError, 'could not accept'):
                host.process_request({'action': 'import_local', 'url': 'https://arxiv.org/abs/2401.01234'})


if __name__ == '__main__':
    unittest.main()
