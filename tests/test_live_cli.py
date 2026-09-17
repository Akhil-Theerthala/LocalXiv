"""Offline tests for the explicitly invoked, potentially billable live CLI."""
import contextlib
import importlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


class LiveCLITests(unittest.TestCase):
    def setUp(self):
        self.cli = importlib.import_module('tests.test_live')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_dotenv_is_literal_and_case_insensitive(self):
        env = self.root / '.env'
        env.write_text('''# ignored\n\nexport OPENROUTER_API_KEY="fake # key"\nopenrouter_MODEL='example/model'\nLITERAL=$(touch nope)\nEXPANSION=${HOME}\nPLAIN=value # comment\n''')
        values = self.cli.read_env(env)
        self.assertEqual(values['openrouter_api_key'], 'fake # key')
        self.assertEqual(values['openrouter_model'], 'example/model')
        self.assertEqual(values['literal'], '$(touch nope)')
        self.assertEqual(values['expansion'], '${HOME}')
        self.assertEqual(values['plain'], 'value')

    def test_credentials_choose_only_provider_with_os_precedence(self):
        values = {'openrouter_api_key': 'file-key', 'openrouter_model': 'file-model',
                  'openai_api_key': 'other-key'}
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'os-key', 'OpenRouter_Model': 'os-model'}, clear=True):
            self.assertEqual(self.cli.credentials('openrouter', None, values), ('os-key', 'os-model'))
            self.assertEqual(self.cli.credentials('openrouter', 'chosen', values), ('os-key', 'chosen'))
        with patch.dict(os.environ, {}, clear=True):
            for values in ({'openai_api_key': 'wrong'}, {'openrouter_api_key': 'key'}):
                with self.assertRaisesRegex(ValueError, 'key|model'):
                    self.cli.credentials('openrouter', None, values)

    def test_paper_identifiers_and_path_rejection(self):
        self.assertEqual(self.cli.paper_identifier('hep-th/9901001'), 'hep-th/9901001')
        self.assertEqual(self.cli.paper_identifier('https://arxiv.org/abs/1706.03762v2'), '1706.03762v2')
        for bad in ('../../secret', '/tmp/paper', 'https://evil.example/abs/1706.03762', '1706.03762/../../x'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.cli.paper_identifier(bad)

    def fixture(self):
        directory = self.root / 'retained'
        figures = directory / 'reader' / 'overview-figures'
        figures.mkdir(parents=True)
        for ext, data in (('png', b'fake png'), ('svg', b'<svg/>'), ('source.svg', b'<svg>editable</svg>')):
            (figures / ('fig1.' + ext)).write_bytes(data)
        document = directory / 'document.json'
        document.write_text(json.dumps({'arxiv_id': 'hep-th/9901001', 'directory': '/stale/path', 'passages': []}))
        figure = {'id': 'fig1', 'caption': 'A caption [p00001]',
                  **{ext: 'reader/overview-figures/fig1.' + ext for ext in ('png', 'svg')},
                  'svg_source': 'reader/overview-figures/fig1.source.svg'}
        overview = {'figures': [figure], 'text': ''}
        blog = {'text': 'Uncited', 'cited_text': 'Claim [p00001]\n\n{{figure:fig1}}', 'figures': [figure]}
        return document, overview, blog

    def test_main_document_both_exports_relative_assets_and_unique_runs(self):
        from papers import ai, acquire
        document, overview, blog = self.fixture()
        seen = []
        def generate(provider, doc, progress, **kwargs):
            seen.append((provider.settings, doc, kwargs))
            progress('working fake-key')
            return overview if kwargs['visual'] else dict(blog, debug='fake-key')
        args = ['openrouter', 'hep-th/9901001', '--document', str(document), '--section', 'both',
                '--model', 'example/model', '--length', 'short', '--vision',
                '--env-file', str(self.root / 'absent.env'), '--output', str(self.root / 'out')]
        output = io.StringIO()
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'fake-key'}, clear=True), \
             patch.object(self.cli, 'preflight'), patch.object(ai, 'generate_overview', side_effect=generate), \
             patch.object(acquire, 'acquire', side_effect=AssertionError('must not download')), \
             contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            self.assertEqual(self.cli.main(args), 0)
            self.assertEqual(self.cli.main(args), 0)
        self.assertNotIn('fake-key', output.getvalue())
        runs = list((self.root / 'out').iterdir())
        self.assertEqual(len(runs), 2)
        for run in runs:
            self.assertEqual((run / 'hep-th_9901001_overview.png').read_bytes(), b'fake png')
            self.assertIn('editable', (run / 'hep-th_9901001_overview.svg').read_text())
            text = (run / 'hep-th_9901001.md').read_text()
            self.assertIn('Claim [p00001]', text)
            self.assertIn('![](hep-th_9901001_assets/fig1.png)', text)
            self.assertIn('A caption [p00001]', text)
            self.assertTrue((run / 'hep-th_9901001_assets/fig1.svg').is_file())
            self.assertNotIn('fake-key', (run / 'blog.json').read_text())
        self.assertEqual(seen[0][1]['directory'], str(document.parent.resolve()))
        self.assertEqual(seen[0][0]['overview_length'], 'short')
        self.assertEqual(seen[0][0]['overview_language'], 'casual')
        self.assertTrue(seen[0][0]['overview_vision'])
        self.assertEqual(seen[1][2]['image_overview'], overview)
        self.assertEqual(json.loads(document.read_text())['directory'], '/stale/path')

    def test_export_rejects_unsafe_missing_and_unresolved_figures(self):
        document, overview, blog = self.fixture()
        for change in ({'png': '../../outside.png'}, {'png': 'reader/overview-figures/missing.png'},
                       {'id': '../../escape'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.cli.export_generation(document.parent, self.root / 'export', 'paper',
                                           dict(blog, figures=[dict(blog['figures'][0], **change)]), visual=False)
        with self.assertRaisesRegex(ValueError, 'marker'):
            self.cli.export_generation(document.parent, self.root / 'export', 'paper',
                                       dict(blog, cited_text='{{figure:unknown}}'), visual=False)

    def test_clean_error_redacts_key(self):
        output = io.StringIO()
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'fake-key'}, clear=True), \
             patch.object(self.cli, 'preflight', side_effect=RuntimeError('failure fake-key')), \
             contextlib.redirect_stderr(output):
            status = self.cli.main(['openrouter', '1706.03762', '--model', 'test', '--env-file', str(self.root / 'none')])
        self.assertEqual(status, 1)
        self.assertNotIn('fake-key', output.getvalue())
        self.assertNotIn('Traceback', output.getvalue())

    def test_diagnostic_write_failure_still_exits_cleanly(self):
        from papers import ai
        document, _, _ = self.fixture()
        errors = io.StringIO()
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'fake-key'}, clear=True), \
             patch.object(self.cli, 'preflight'), \
             patch.object(ai, 'generate_overview', side_effect=RuntimeError('failed fake-key')), \
             patch.object(Path, 'write_text', side_effect=OSError('disk full fake-key')), \
             contextlib.redirect_stderr(errors), contextlib.redirect_stdout(io.StringIO()):
            status = self.cli.main(['openai', 'hep-th/9901001', '--model', 'test', '--document', str(document),
                                    '--output', str(self.root / 'out'), '--env-file', str(self.root / 'none')])
        self.assertEqual(status, 1)
        self.assertNotIn('fake-key', errors.getvalue())

    def test_document_identity_mismatch_stops_before_generation_or_output(self):
        from papers import ai
        document, _, _ = self.fixture()
        for requested, retained in (('1706.03762', 'hep-th/9901001'),
                                    ('1706.03762v2', '1706.03762v1'),
                                    ('1706.03762v2', '1706.03762'),
                                    ('1706.03762', None),
                                    ('1706.03762', 'invalid fake-key')):
            with self.subTest(requested=requested, retained=retained):
                document.write_text(json.dumps({'arxiv_id': retained, 'passages': []}))
                errors = io.StringIO()
                with patch.dict(os.environ, {'OPENAI_API_KEY': 'fake-key'}, clear=True), \
                     patch.object(self.cli, 'preflight'), patch.object(ai, 'generate_overview') as generate, \
                     contextlib.redirect_stderr(errors), contextlib.redirect_stdout(io.StringIO()):
                    status = self.cli.main(['openai', requested, '--model', 'test', '--document', str(document),
                                            '--output', str(self.root / 'out'), '--env-file', str(self.root / 'none')])
                self.assertEqual(status, 1)
                generate.assert_not_called()
                self.assertFalse((self.root / 'out').exists())
                self.assertIn('arXiv', errors.getvalue())
                self.assertNotIn('fake-key', errors.getvalue())

    def test_document_identity_accepts_versionless_request_and_exact_version(self):
        from papers import ai
        document, _, _ = self.fixture()
        for requested, retained in (('1706.03762', '1706.03762v2'),
                                    ('1706.03762v2', '1706.03762v2'),
                                    ('hep-th/9901001', 'hep-th/9901001v3')):
            with self.subTest(requested=requested, retained=retained):
                document.write_text(json.dumps({'arxiv_id': retained, 'passages': []}))
                with patch.dict(os.environ, {'OPENAI_API_KEY': 'fake-key'}, clear=True), \
                     patch.object(self.cli, 'preflight'), \
                     patch.object(ai, 'generate_overview', return_value={'text': 'Evidence', 'figures': []}), \
                     contextlib.redirect_stdout(io.StringIO()):
                    status = self.cli.main(['openai', requested, '--model', 'test', '--document', str(document),
                                            '--section', 'blog', '--output', str(self.root / requested.replace('/', '_')),
                                            '--env-file', str(self.root / 'none')])
                self.assertEqual(status, 0)
                run, = (self.root / requested.replace('/', '_')).iterdir()
                self.assertEqual((run / (requested.replace('/', '_') + '.md')).read_text(), 'Evidence\n')

    def test_preflight_requires_native_renderer_and_blog_dependency(self):
        with patch.dict(os.environ, {'LOCALXIV_HTML_RENDERER': str(self.root / 'missing')}):
            with self.assertRaisesRegex(ValueError, 'renderer'):
                self.cli.preflight('overview')
        with patch.dict(os.environ, {'LOCALXIV_HTML_RENDERER': sys.executable}), \
             patch('importlib.util.find_spec', return_value=None):
            self.cli.preflight('overview')
            with self.assertRaisesRegex(ValueError, 'smolagents'):
                self.cli.preflight('blog')

    def test_acquire_partial_metadata_uses_production_conversion_fallback(self):
        from papers import acquire, ai, convert
        source_failure = RuntimeError('source unavailable')
        def download(url, directory):
            self.assertEqual(url, 'https://arxiv.org/abs/1706.03762')
            (directory / 'metadata.json').write_text(json.dumps({'arxiv_id': '1706.03762'}))
            raise source_failure
        def conversion(directory, metadata, progress, *, source_error):
            self.assertIs(source_error, source_failure)
            self.assertEqual(metadata['arxiv_id'], '1706.03762')
            return {'arxiv_id': '1706.03762', 'passages': []}
        def generate(provider, document, progress, **kwargs):
            self.assertTrue(Path(document['directory']).is_absolute())
            self.assertEqual(Path(document['directory']).name, 'paper')
            return {'cited_text': 'Evidence [p00001]', 'figures': []}
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'fake-key', 'OPENAI_MODEL': 'model'}, clear=True), \
             patch.object(self.cli, 'preflight'), patch.object(acquire, 'acquire', side_effect=download), \
             patch.object(convert, 'convert_import', side_effect=conversion), \
             patch.object(ai, 'generate_overview', side_effect=generate), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.cli.main(['openai', '1706.03762', '--section', 'blog',
                                           '--output', str(self.root / 'out'),
                                           '--env-file', str(self.root / 'none')]), 0)
        run, = (self.root / 'out').iterdir()
        self.assertEqual((run / '1706.03762.md').read_text(), 'Evidence [p00001]\n')

    def test_missing_credentials_fail_before_preflight_or_output(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(self.cli, 'preflight') as preflight, \
             contextlib.redirect_stderr(io.StringIO()):
            result = self.cli.main(['openai', '1706.03762', '--output', str(self.root / 'out'),
                                    '--env-file', str(self.root / 'none')])
        self.assertEqual(result, 1)
        self.assertFalse((self.root / 'out').exists())
        preflight.assert_not_called()

    def test_symlink_export_cannot_escape_retained_figures(self):
        document, overview, blog = self.fixture()
        target = document.parent / 'reader/overview-figures/fig1.png'
        target.unlink()
        outside = self.root / 'outside.png'
        outside.write_bytes(b'private')
        target.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'Invalid figure export path'):
            self.cli.export_generation(document.parent, self.root / 'export', 'paper', overview, visual=True)
        self.assertFalse((self.root / 'export').exists())

    def test_import_discovery_and_help_are_offline(self):
        script = """
import builtins, runpy, socket, sys, unittest
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if name.startswith(('papers', 'smolagents')):
        raise AssertionError('eager dependency: ' + name)
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
socket.socket = lambda *a, **k: (_ for _ in ()).throw(AssertionError('network'))
import tests.test_live
suite = unittest.defaultTestLoader.discover('tests', pattern='test_live.py')
assert suite.countTestCases() == 0
sys.argv = ['tests/test_live.py', '--help']
runpy.run_path('tests/test_live.py', run_name='__main__')
"""
        result = subprocess.run([sys.executable, '-c', script], capture_output=True, text=True,
                                cwd=Path(__file__).resolve().parents[1], timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--document', result.stdout)


if __name__ == '__main__':
    unittest.main()
