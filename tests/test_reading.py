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
            self.assertIn('Stage 1: select grounded content', provider.complete.call_args.args[0][1]['content'])

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
                document = {'source_digest':'fixture', 'passages':[{'id':'p00001', 'text':'Evidence'}]}
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

    def test_bento_then_blog_does_not_read_again(self):
        with tempfile.TemporaryDirectory() as temporary:
            doc={'directory':temporary,'passages':[{'id':'p00001','text':'Evidence'}]}
            provider=Mock(settings={'model':'fixture','max_context_chars':480000})
            provider.complete.side_effect=[{'text':'Reading [p00001].','usage':{}},{'text':'Synthesis [p00001].','usage':{}},
                {'text':json.dumps(SPEC),'usage':{}},{'text':json.dumps(SPEC),'usage':{}},{'text':json.dumps(COMPOSITION),'usage':{}}]
            generate_overview(provider,doc,lambda _:None,visual=True)
            provider.complete.reset_mock()
            # Stop at the blog planner. Its first call must already have reused the evidence.
            provider.complete.side_effect=RuntimeError('stop at blog plan')
            with self.assertRaisesRegex(RuntimeError,'stop at blog plan'):
                generate_overview(provider,doc,lambda _:None)
            messages=provider.complete.call_args.args[0]
            self.assertIn('ARTICLE PLAN',messages[1]['content'])
            self.assertIn('Synthesis',messages[1]['content'])

    def test_rendered_bento_is_reviewed_when_vision_enabled(self):
        with tempfile.TemporaryDirectory() as temporary:
            doc={'directory':temporary,'passages':[{'id':'p00001','text':'Evidence'}]}
            provider=Mock(settings={'model':'fixture','overview_vision':True,'max_context_chars':480000})
            provider.complete.side_effect=[{'text':'Reading [p00001].','usage':{}},{'text':'Synthesis [p00001].','usage':{}},
                {'text':json.dumps(SPEC),'usage':{}},{'text':json.dumps(SPEC),'usage':{}},{'text':json.dumps(COMPOSITION),'usage':{}},
                {'text':'{"approved":true,"issues":[]}','usage':{}}]
            result=generate_overview(provider,doc,lambda _:None,visual=True)
            content=provider.complete.call_args.args[0][1]['content']
            self.assertEqual(2,sum(part['type']=='image_url' for part in content))
            self.assertEqual('passed',result['figures'][0]['checks']['visual_review'])
            provider.complete.side_effect=[{'text':json.dumps(SPEC),'usage':{}},{'text':json.dumps(SPEC),'usage':{}},{'text':json.dumps(COMPOSITION),'usage':{}},
                {'text':'{"approved":false,"issues":[{"description":"Unreadable label"}]}','usage':{}}]
            with self.assertRaisesRegex(RuntimeError,'Unreadable label'):
                generate_overview(provider,doc,lambda _:None,visual=True)

    def test_size_based_batches_do_not_spend_calls_on_tiny_sections(self):
        passages=[{'id':f'p{i:05d}','section':f'Section {i}','text':'x'*300} for i in range(1,31)]
        batches=reading_batches(passages,20000,_evidence)
        self.assertEqual(1,len(batches))
        self.assertEqual(passages,[p for b in batches for p in b])
        batches=reading_batches(passages,1500,_evidence)
        self.assertTrue(all(len(_evidence(b))<=1500 for b in batches))
        with self.assertRaises(ValueError):
            reading_batches([dict(passages[0],text='x'*2000)],1500,_evidence)

    def test_gemini_flash_planning_has_bounded_thinking(self):
        with tempfile.TemporaryDirectory() as temporary:
            doc={'directory':temporary,'passages':[{'id':'p00001','text':'Evidence'}]}
            provider=Mock(settings={'model':'gemini-3.8-flash','endpoint':'https://generativelanguage.googleapis.com/v1beta/openai/','max_context_chars':480000})
            provider.complete.side_effect=[{'text':'Reading [p00001].','usage':{}},{'text':'Synthesis [p00001].','usage':{}},
                {'text':json.dumps(SPEC),'usage':{}},{'text':json.dumps(SPEC),'usage':{}},{'text':json.dumps(COMPOSITION),'usage':{}}]
            generate_overview(provider,doc,lambda _:None,visual=True)
            calls=provider.complete.call_args_list
            self.assertNotIn('gemini_thinking_level',calls[0].kwargs)
            self.assertEqual('low',calls[2].kwargs['gemini_thinking_level'])
            self.assertEqual('medium',calls[3].kwargs['gemini_thinking_level'])

    def test_validation_retry_repairs_the_latest_candidate(self):
        with tempfile.TemporaryDirectory() as temporary:
            doc={'directory':temporary,'passages':[{'id':'p00001','text':'Evidence'}]}
            provider=Mock(settings={'model':'fixture','max_context_chars':480000})
            reviewed=copy.deepcopy(SPEC)
            reviewed['nodes'][2]['body']='A corrected scientific qualification.'
            reviewed['nodes'][2]['visual']={'kind':'flow','steps':['x'*41,'Output'],
                'caption':'Input feeds output.','passages':['p00001']}
            repaired=copy.deepcopy(reviewed)
            repaired['nodes'][2]['visual']['steps'][0]='Input'
            provider.complete.side_effect=[{'text':'Notes [p00001].','usage':{}},{'text':'Synthesis [p00001].','usage':{}},
                {'text':json.dumps(SPEC),'usage':{}},{'text':json.dumps(reviewed),'usage':{}},
                {'text':json.dumps(repaired),'usage':{}},{'text':json.dumps(COMPOSITION),'usage':{}}]
            result=generate_overview(provider,doc,lambda _:None,visual=True)
            retry=provider.complete.call_args_list[4].args[0][1]['content']
            self.assertIn('CURRENT CANDIDATE',retry)
            self.assertIn('flow step 1',retry)
            self.assertIn('A corrected scientific qualification.',retry)
            self.assertEqual(repaired['nodes'][2]['body'],result['figures'][0]['design']['nodes'][2]['body'])
