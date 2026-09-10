"""Shared reading cache and actual multimodal payload checks; no external calls."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from papers.ai import _request, _evidence, generate_overview, prepare_reading
from papers.reading import shared_reading, paper_images, reading_batches
from tests.test_bento import SPEC, COMPOSITION


class ReadingTests(unittest.TestCase):
    def test_import_reading_is_reused_by_overview(self):
        with tempfile.TemporaryDirectory() as temporary:
            doc = {'directory':temporary, 'passages':[{'id':'p00001', 'text':'Evidence'}]}
            provider = Mock(settings={'model':'fixture', 'max_context_chars':480000})
            provider.complete.side_effect = [{'text':'Notes [p00001].', 'usage':{}},
                                             {'text':'Synthesis [p00001].', 'usage':{}}]
            prepare_reading(provider, doc, lambda _:None)
            provider.complete.reset_mock()
            provider.complete.side_effect = RuntimeError('stop at content selection')
            with self.assertRaisesRegex(RuntimeError, 'stop at content selection'):
                generate_overview(provider, doc, lambda _:None, visual=True)
            self.assertEqual(1, provider.complete.call_count)
            self.assertFalse(provider.complete.call_args.kwargs['json_object'])

    def test_import_queues_reading_only_with_ai_and_keeps_paper_on_read_failure(self):
        import queue
        import threading
        from app.server import Application, DEFAULTS
        from papers.library import Library
        for key, model, auto, expected in [(None, 'fixture', True, []), ('secret', '', True, []),
                                           ('secret', 'fixture', False, ['reading']),
                                           ('secret', 'fixture', True, ['reading', 'bento'])]:
            with self.subTest(key=bool(key), model=model, auto=auto), tempfile.TemporaryDirectory() as temporary:
                app = Application.__new__(Application)
                app.library = Library(Path(temporary))
                app.lock, app.queue, app.active_job = threading.RLock(), queue.Queue(), None
                app.settings = Mock(return_value=dict(DEFAULTS, model=model, auto_summary=auto))
                app.public_settings = Mock(return_value={})
                app.recommendations = Mock()
                job = app.library.create_job('import', {'url':'https://arxiv.org/abs/1706.03762'})
                document = {'arxiv_id':'1706.03762', 'source_digest':'fixture', 'passages':[{'id':'p00001', 'text':'Evidence'}]}
                with patch('papers.acquire.acquire', return_value={'arxiv_id':'1706.03762'}), \
                     patch('papers.convert.convert_paper', return_value=document), \
                     patch('app.server.get_key', return_value=key):
                    app.execute(job)
                    queued = [app.library.get_job(app.queue.get_nowait()) for _ in range(app.queue.qsize())]
                    self.assertEqual(expected, [j['kind'] for j in queued])
                    self.assertEqual('ready', app.library.get_job(job['id'])['state'])
                    if not queued:
                        # Authentication later does not backfill papers; the first requested overview reads.
                        provider = Mock(settings={'model':'configured-later', 'max_context_chars':480000})
                        provider.complete.side_effect = [{'text':'Notes [p00001].', 'usage':{}},
                            {'text':'Synthesis [p00001].', 'usage':{}}, RuntimeError('stop at overview')]
                        with self.assertRaisesRegex(RuntimeError, 'stop at overview'):
                            generate_overview(provider, app.library.get_paper('1706.03762'), lambda _:None, visual=True)
                        self.assertEqual(3, provider.complete.call_count)
                    if queued:
                        with patch('app.server.prepare_reading', side_effect=RuntimeError('Provider unavailable')):
                            with self.assertRaisesRegex(RuntimeError, 'Provider unavailable'):
                                app.execute(queued[0])
                        self.assertIsNotNone(app.library.get_paper('1706.03762'))
                        self.assertEqual('ready', app.library.get_job(job['id'])['state'])
                        with patch('app.server.get_key', return_value=None), patch('app.server.prepare_reading') as read:
                            self.assertIn('skipped', app.execute(queued[0]))
                            read.assert_not_called()

    def test_all_figures_feed_shared_notes_in_bounded_requests(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'reader'
            root.mkdir()
            for i in range(8):
                (root / f'figure{i}.png').write_bytes(b'\x89PNG\r\n\x1a\n' + bytes([i]))
            (root / 'paper.xhtml').write_text('<html><figure id="architecture">' +
                ''.join(f'<img src="figure{i}.png"/>' for i in range(8)) + '</figure></html>')
            doc = {'directory':temporary, 'passages':[{'id':'p00001',
                   'text':'Architecture with parallel branches and residual connections.',
                   'href':'reader/paper.xhtml#architecture'}]}
            provider = Mock(settings={'overview_vision':True, 'model':'fixture'})
            request = Mock(return_value={'text':'Parallel branches and residual connections [p00001].', 'usage':{}})
            notes, _, coverage = shared_reading(provider, doc, [doc['passages']], lambda _:None, request, _evidence)
            self.assertEqual([6, 2, 0], [len(c.kwargs.get('images', [])) for c in request.call_args_list])
            self.assertEqual(8, coverage['inspected_image_count'])
            self.assertEqual([], coverage['omitted_figure_passages'])
            self.assertIn('For EACH attached image', request.call_args_list[0].args[1])
            self.assertIn('residual/skip connections', request.call_args_list[1].args[1])
            self.assertIn('Parallel branches', request.call_args_list[-1].args[2])
            provider.settings['overview_length'] = 'large'
            reused, usage, coverage = shared_reading(provider, doc, [doc['passages']], lambda _:None, request, _evidence)
            self.assertEqual(notes, reused)
            self.assertEqual([], usage)
            self.assertTrue(coverage['reused'])
            self.assertEqual(3, request.call_count)

    def test_shared_notes_reused_across_output_styles_and_invalidated(self):
        with tempfile.TemporaryDirectory() as temporary:
            doc={'directory':temporary,'passages':[{'id':'p00001','text':'Original evidence'}]}
            provider=Mock(settings={'model':'test','endpoint':'https://example.test'})
            request=Mock(return_value={'text':'Evidence [p00001].','usage':{'total_tokens':10}})
            def read():
                return shared_reading(provider,doc,[doc['passages']],lambda _:None,request,_evidence)
            first=read()
            self.assertEqual(2,request.call_count)
            provider.settings['overview_length']='large'
            provider.settings['overview_language']='formal'
            second=read()
            self.assertEqual(first[0],second[0])
            self.assertEqual([],second[1])
            self.assertTrue(second[2]['reused'])
            self.assertEqual(2,request.call_count)
            for key,value in [('model','different'),('overview_vision',True)]:
                provider.settings[key]=value
                self.assertFalse(read()[2]['reused'])
            doc['passages'][0]['text']='Changed source'
            self.assertFalse(read()[2]['reused'])
            cache=Path(temporary)/'reader/paper-reading.json'
            cache.write_text('{broken')
            self.assertFalse(read()[2]['reused'])

    def test_figure_selection_and_payload(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'reader').mkdir()
            (root/'reader/chart.png').write_bytes(b'\x89PNG\r\n\x1a\nfixture')
            (root/'reader/p.xhtml').write_text('<html><figure id="f"><img src="chart.png"/><img src="https://bad.test/x.png"/><img src="../../outside.png"/></figure></html>')
            doc={'directory':temporary,'passages':[{'id':'p00001','text':'Chart caption','href':'reader/p.xhtml#f'}]}
            images,omitted=paper_images(doc)
            self.assertEqual(1,len(images))
            provider=Mock()
            provider.complete.return_value={'text':'Chart observation [p00001].','usage':{}}
            _request(provider,'Read figure','caption',doc['passages'],images=images)
            content=provider.complete.call_args.args[0][1]['content']
            self.assertEqual('image_url',content[-1]['type'])
            self.assertTrue(content[-1]['image_url']['url'].startswith('data:image/png;base64,'))



    def test_size_based_batches_do_not_spend_calls_on_tiny_sections(self):
        passages=[{'id':f'p{i:05d}','section':f'Section {i}','text':'x'*300} for i in range(1,31)]
        batches=reading_batches(passages,_evidence)
        self.assertEqual(1,len(batches))
        self.assertEqual(passages,[p for b in batches for p in b])
        large = [dict(passages[0], text='x' * 1_000_001)]
        self.assertEqual([large], reading_batches(large, _evidence))
