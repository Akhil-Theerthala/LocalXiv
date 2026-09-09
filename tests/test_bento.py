"""Run with python3 -m unittest tests.test_bento. No provider calls."""
import copy
import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch

from papers.ai import generate_overview
from papers.bento import validate_bento, export_pdf, plan_bento
from papers.overview import render_figure

SPEC = {'title': 'Can a confident answer still be wrong?', 'misconception': 'Confidence is not correctness.',
        'layout': 'bento', 'focus': 2, 'arrows': [], 'passages': ['p00001'],
        'takeaway': 'Check confidence against observed outcomes before treating it as reliable.',
        'scope': 'Conceptual summary. Card area shows emphasis, not measured quantities.',
        'nodes': [{'title': title, 'body': body, 'passages':['p00001']} for title, body in zip([
            'Can certainty mislead?', 'Why check confidence?', 'What gets compared?',
            'How is the mismatch found?', 'What does calibration tell us?', 'What remains unknown?'], [
            'An answer can sound certain and still be incorrect.',
            'Stated confidence needs checking against observed correctness.',
            'Compare confidence with correctness across held-out examples.',
            'Group predictions by confidence to inspect the mismatch.',
            'Calibration measures how closely confidence matches outcomes.',
            'This conceptual fixture supplies no measured improvement.'])]}



class BentoTests(unittest.TestCase):
    def test_rejects_bad_evidence_and_layout(self):
        validate_bento(copy.deepcopy(SPEC), [{'id': 'p00001'}])
        for changes in ({'passages': ['p1']}, {'nodes': SPEC['nodes'][:2]}, {'arrows': ['causes']}, {'layout': 'sequence'}, {'focus': True}):
            with self.assertRaises(ValueError):
                validate_bento(dict(copy.deepcopy(SPEC), **changes), [{'id': 'p00001'}])

    def test_all_card_counts_fit_in_both_orientations(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for count in range(4, 10):
                spec = copy.deepcopy(SPEC)
                spec['nodes'] = [copy.deepcopy(SPEC['nodes'][i % 6]) for i in range(count)]
                for portrait in (False, True):
                    with self.subTest(count=count, portrait=portrait):
                        plan = plan_bento(spec, portrait)
                        self.assertEqual(list(range(count)), [i for row in plan['packing']['rows'] for i in row['cards']])
                        assets = render_figure(root, 'grid', plan)
                        scene = json.loads((root / assets['excalidraw']).read_text())['elements']
                        cards = [e for e in scene if e['type'] == 'rectangle']
                        self.assertEqual(count, len(cards))
                        for text in [e for e in scene if e['type'] == 'text']:
                            card = next(c for c in cards if c['id'] == 'panel' + text['id'].removeprefix('body').removeprefix('heading'))
                            self.assertEqual(2, text['fontFamily'])
                            self.assertEqual('left', text['textAlign'])
                            self.assertLessEqual(text['y'] + text['height'], card['y'] + card['height'])
                        svg = (root / assets['svg']).read_text()
                        self.assertNotIn('text-anchor="middle"', svg)
                        self.assertNotIn('The pain point', svg)

    def test_rejects_awkward_headers_and_unsupported_card_claims(self):
        for change in ({'title':'The pain point'}, {'body':'The pain point is confidence.'}, {'passages':['missing']}, {'title':'x' * 46}):
            spec = copy.deepcopy(SPEC)
            spec['nodes'][0].update(change)
            with self.assertRaises(ValueError):
                validate_bento(spec, [{'id':'p00001'}])

    def test_visual_generation_skips_blog_and_retains_editable_assets(self):
        provider = Mock(settings={'max_context_chars': 480000, 'model': 'fixture'})
        provider.complete.side_effect = [{'text': 'Check confidence against outcomes [p00001].', 'usage': {}},
                                         {'text': json.dumps(SPEC), 'usage': {}}, {'text': json.dumps(SPEC), 'usage': {}}]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            doc = {'directory': temporary, 'title': 'Fixture', 'passages': [{'id': 'p00001', 'text': 'Evidence'}]}
            result = generate_overview(provider, doc, lambda _: None, visual=True)
            figure = result['figures'][0]
            self.assertEqual(3, provider.complete.call_count)
            self.assertEqual([], figure['checks']['warnings'])
            self.assertTrue((root / figure['portrait']['png']).is_file())
            self.assertEqual('landscape', figure['design']['packing']['orientation'])
            self.assertTrue((root / figure['png']).read_bytes().startswith(b'\x89PNG'))
            scene = json.loads((root / figure['excalidraw']).read_text())
            ids = [e['id'] for e in scene['elements']]
            self.assertEqual(len(ids), len(set(ids)))
            if shutil.which('rsvg-convert'):
                self.assertTrue(export_pdf(root, doc, 'bento', result).read_bytes().startswith(b'%PDF-'))
            with self.assertRaises(ValueError):
                export_pdf(root, doc, 'paper', None)
            (root / 'original.pdf').write_bytes(b'%PDF-1.4 fixture')
            self.assertEqual(root / 'original.pdf', export_pdf(root, doc, 'paper', None))

    @unittest.skipUnless(shutil.which('xelatex') and shutil.which('pandoc'), 'XeLaTeX required')
    def test_blog_pdf_with_math_and_figure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            assets = render_figure(root, 'fig1', copy.deepcopy(SPEC))
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
                assets = render_figure(root, 'fig1', copy.deepcopy(SPEC))
                app.library.save_paper('2601.00001v1', {'arxiv_id':'2601.00001v1','title':'Fixture','authors':'A'}, str(root))
                generation = {'text':'{{figure:fig1}}','figures':[dict(id='fig1', **assets, alt='Pain point, approach and achievement', caption=SPEC['takeaway'])]}
                app.library.save_generation('2601.00001v1','bento',generation)
                (root/'overview.epub').write_bytes(b'Existing blog EPUB')
                paper=app.library.get_paper('2601.00001v1')
                for profile in ('kindle','semantic'):
                    exported=app.artifact(paper,'bento',profile)
                    with zipfile.ZipFile(exported) as book:
                        self.assertEqual(b'application/epub+zip',book.read('mimetype'))
                        self.assertTrue(any(name.endswith('.svg') or name.endswith('.png') for name in book.namelist()))
                self.assertEqual(b'Existing blog EPUB',(root/'overview.epub').read_bytes())
                with self.assertRaises(ValueError):
                    app.artifact(paper,'overview','png')
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
                assets = render_figure(root, 'fig1', copy.deepcopy(SPEC))
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
