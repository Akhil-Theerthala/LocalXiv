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
from papers.bento import validate_bento, plan_bento
from papers.exports import artifact, export_pdf
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

COMPOSITION = {'composition': [{'columns': row['columns']} for row in plan_bento(copy.deepcopy(SPEC))['packing']['rows']]}



class BentoTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('mpost') and shutil.which('rsvg-convert'), 'Optional local render tools unavailable')
    def test_fiziko_is_embedded_and_reused_across_formats(self):
        from papers.illustrations import TEMPLATE, DESCRIPTION, render_illustration
        visual = {'kind':'illustration', 'template':TEMPLATE,
                  'caption':'Illustrative weights for one query, not measured attention.', 'passages':['p00001']}
        spec = copy.deepcopy(SPEC)
        spec['nodes'][2]['visual'] = visual
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = render_figure(temporary, 'bento', spec)
            portrait = render_figure(temporary, 'portrait', plan_bento(spec, True))
            blog = render_figure(temporary, 'blog', {'layout':'illustration', 'template':TEMPLATE,
                'title':'One query combines value vectors', 'takeaway':'The output is a weighted sum.',
                'scope':'Example weights, not observations. Score calculation is omitted.'})
            source = first['checks']['illustrations'][0]['source']
            for result in (first, portrait, blog):
                self.assertEqual(result['checks']['illustrations'][0]['source'], source)
                scene = json.loads((root / result['excalidraw']).read_text())
                images = [e for e in scene['elements'] if e['type'] == 'image']
                self.assertEqual(len(images), 1)
                self.assertTrue(scene['files'][images[0]['fileId']]['dataURL'].startswith('data:image/png;base64,'))
                self.assertIn('data:image/svg+xml;base64,', (root / result['svg']).read_text())
                self.assertTrue((root / result['png']).read_bytes().startswith(b'\x89PNG'))
            self.assertNotIn('_asset', visual)
            asset = root / source
            before = asset.stat().st_mtime_ns
            self.assertEqual(render_illustration(temporary, visual)['alt'], DESCRIPTION)
            self.assertEqual(before, asset.stat().st_mtime_ns)
            with self.assertRaises(ValueError):
                render_illustration(temporary, dict(visual, template='../../arbitrary.mp'))
            with patch('papers.illustrations.fiziko_path', return_value=None):
                with self.assertRaisesRegex(ValueError, 'requires mpost'):
                    render_illustration(temporary, visual)

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
                        order = [i for row in plan['packing']['rows'] for i in row['cards']]
                        self.assertEqual(list(range(count)), sorted(order))
                        self.assertEqual(spec['focus'], order[0])
                        self.assertTrue(all(len(row['columns']) <= (1 if portrait else 3) for row in plan['packing']['rows']))
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

    def test_visuals_validate_and_fit_cards(self):
        spec = copy.deepcopy(SPEC)
        spec['nodes'][2]['visual'] = {'kind':'flow', 'steps':['Collect predictions','Group by confidence','Compare outcomes'],
            'caption':'Predictions feed groups, then observed outcomes are compared.', 'passages':['p00001']}
        spec['nodes'][3]['visual'] = {'kind':'metrics', 'items':[
            {'label':'Example group A','value':'0.739'}, {'label':'Example group B','value':'0.715'}],
            'caption':'Synthetic values for renderer testing only.', 'passages':['p00001']}
        validate_bento(spec, [{'id':'p00001'}])
        with tempfile.TemporaryDirectory() as temporary:
            for portrait in (False, True):
                assets=render_figure(temporary, 'visuals', plan_bento(spec, portrait))
                elements=json.loads((Path(temporary)/assets['excalidraw']).read_text())['elements']
                self.assertEqual(2, len([e for e in elements if e['type']=='arrow']))
                self.assertEqual(len(elements), len({e['id'] for e in elements}))
                for e in elements:
                    if not e['id'].startswith('visual'):
                        continue
                    index=e['id'].split('-')[0].removeprefix('visual')
                    card=next(c for c in elements if c['id']=='panel'+index)
                    self.assertGreaterEqual(e['x'], card['x'])
                    self.assertGreaterEqual(e['y'], card['y'])
                    self.assertLessEqual(e['x']+e['width'], card['x']+card['width'])
                    self.assertLessEqual(e['y']+e['height'], card['y']+card['height'])
        for changes in ({'passages':['missing']}, {'kind':'image'}, {'steps':['one']}, {'steps':['x'*41]}, {'caption':''}):
            bad=copy.deepcopy(spec)
            bad['nodes'][2]['visual'].update(changes)
            with self.assertRaises(ValueError):
                validate_bento(bad, [{'id':'p00001'}])
        bad=copy.deepcopy(spec)
        bad['nodes'][0]['visual']=copy.deepcopy(bad['nodes'][2]['visual'])
        with self.assertRaises(ValueError):
            validate_bento(bad)

    def test_composition_supports_spans_stacks_and_rejects_duplicates(self):
        spec=copy.deepcopy(SPEC)
        spec['composition']=[{'columns':[{'span':7,'cards':[2]},{'span':5,'cards':[0,1]}]},
                             {'columns':[{'span':4,'cards':[3]},{'span':4,'cards':[4]},{'span':4,'cards':[5]}]}]
        validate_bento(spec)
        with tempfile.TemporaryDirectory() as temporary:
            assets=render_figure(temporary,'composition',plan_bento(spec))
            elements=json.loads((Path(temporary)/assets['excalidraw']).read_text())['elements']
            panels={e['id']:e for e in elements if e['id'].startswith('panel')}
            self.assertGreater(panels['panel2']['width'],panels['panel0']['width'])
            self.assertGreater(panels['panel2']['height'],panels['panel0']['height'])
            self.assertEqual(panels['panel0']['x'],panels['panel1']['x'])
            self.assertGreater(panels['panel1']['y'],panels['panel0']['y'])
            for i,a in enumerate(panels.values()):
                for b in list(panels.values())[i+1:]:
                    self.assertTrue(a['x']+a['width']<=b['x'] or b['x']+b['width']<=a['x'] or
                                    a['y']+a['height']<=b['y'] or b['y']+b['height']<=a['y'])
        spec['composition'][1]['columns'][0]['cards']=[2]
        with self.assertRaises(ValueError):
            validate_bento(spec)

    def test_rejects_awkward_headers_and_unsupported_card_claims(self):
        for change in ({'title':'The pain point'}, {'body':'The pain point is confidence.'}, {'passages':['missing']}, {'title':'x' * 46}):
            spec = copy.deepcopy(SPEC)
            spec['nodes'][0].update(change)
            with self.assertRaises(ValueError):
                validate_bento(spec, [{'id':'p00001'}])


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
