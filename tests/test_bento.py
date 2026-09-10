"""Saved overview exports and import preferences; no provider calls."""
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from papers.exports import artifact, export_pdf
from tests.test_agent_overviews import render_fixture


class BentoExportTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('xelatex') and shutil.which('pandoc'), 'XeLaTeX required')
    def test_blog_pdf_with_math_and_figure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            assets = render_fixture(root, {'id':'fig1'}, 'Saved overview')
            assets.pop('png')  # Exercise legacy SVG-to-PDF export with a real rasterization.
            blog = {'text': '# Confidence and correctness\n\nAn equation: $x=1$.\n\n{{figure:fig1}}\n\n![untrusted](/private/etc/passwd)',
                    'figures': [dict(id='fig1', **assets, caption='Conceptual overview.')]}
            pdf = export_pdf(root, {'title': 'Fixture'}, 'overview', blog)
            self.assertTrue(pdf.read_bytes().startswith(b'%PDF-'))


    @unittest.skipUnless(all(shutil.which(tool) for tool in ('pandoc','rsvg-convert','epubcheck')), 'EPUB tools required')
    def test_bento_epub_preserves_blog_export(self):
        from app.server import Application
        with tempfile.TemporaryDirectory() as temporary:
            app = Application(temporary)
            root = Path(temporary)/'paper'
            try:
                assets = render_fixture(root, {'id':'fig1'}, 'Saved overview')
                app.library.save_paper('2601.00001v1', {'arxiv_id':'2601.00001v1','title':'Fixture','authors':'A'}, str(root))
                generation = {'text':'{{figure:fig1}}','figures':[dict(id='fig1', **assets, alt='Pain point, approach and achievement', caption='Conceptual overview.')]}
                app.library.save_generation('2601.00001v1','bento',generation)
                (root/'overview.epub').write_bytes(b'Existing blog EPUB')
                paper=app.library.get_paper('2601.00001v1')
                for profile in ('kindle','semantic'):
                    exported=artifact(app.library, paper,'bento',profile)
                    with zipfile.ZipFile(exported) as book:
                        self.assertEqual(b'application/epub+zip',book.read('mimetype'))
                        self.assertTrue(any(name.endswith('.svg') or name.endswith('.png') for name in book.namelist()))
                self.assertEqual(b'Existing blog EPUB',(root/'overview.epub').read_bytes())
                with self.assertRaises(ValueError):
                    artifact(app.library, paper,'overview','png')
            finally:
                app.close()
                app.worker.join(3)


class ImportPreferenceTests(unittest.TestCase):
    def test_import_generates_only_visual_overview_when_enabled(self):
        from app.server import Application
        metadata = {'arxiv_id':'2601.00002v1', 'title':'Example', 'source_digest':'fixture'}
        document = dict(metadata, passages=[{'id':'p00001', 'text':'Evidence'}])
        for enabled in (False, True):
            with self.subTest(enabled=enabled), tempfile.TemporaryDirectory() as temporary:
                app = Application(temporary)
                try:
                    self.assertFalse(app.settings()['auto_summary'])
                    app.library.save_settings({'auto_summary':enabled, 'model':'fixture'})
                    with patch('papers.acquire.acquire', return_value=metadata), patch('papers.convert.convert_paper', return_value=document), patch('app.server.get_key', return_value='fixture'), patch('app.server.generate_overview', return_value={'text':'visual'}) as generate, patch.object(app, 'recommendations', return_value={}):
                        app.submit('import', {'url':'https://arxiv.org/abs/2601.00002'})
                        app.queue.join()
                        self.assertIsNone(app.library.get_generation(metadata['arxiv_id'], 'overview'))
                        self.assertEqual(enabled, bool(app.library.get_generation(metadata['arxiv_id'], 'bento')))
                        if enabled:
                            self.assertTrue(generate.call_args.kwargs['visual'])
                        else:
                            generate.assert_not_called()
                finally:
                    app.close()
                    app.worker.join(3)

    def test_bento_png_job_keeps_nested_download_path(self):
        from app.server import Application
        with tempfile.TemporaryDirectory() as temporary:
            app = Application(temporary)
            root = Path(temporary) / 'paper'
            try:
                assets = render_fixture(root, {'id':'fig1'}, 'Saved overview')
                app.library.save_paper('2601.00003v1', {'title':'Fixture'}, str(root))
                app.library.save_generation('2601.00003v1', 'bento', {'text':'{{figure:fig1}}', 'figures':[dict(id='fig1', **assets)]})
                job = app.submit('export', {'paper_id':'2601.00003v1','kind':'bento','profile':'png'})
                app.queue.join()
                finished = app.library.get_job(job['id'])
                self.assertEqual('ready', finished['state'], finished.get('error'))
                self.assertIn('/reader/overview-figures/', finished['result']['download_url'])
                self.assertTrue(finished['result']['download_url'].endswith('/fig1.png'))
            finally:
                app.close()
                app.worker.join(3)
