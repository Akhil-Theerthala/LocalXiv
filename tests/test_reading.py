"""Shared reading cache and actual multimodal payload checks; no external calls."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from papers.reading import build_orientation, orientation_page, retrieve_evidence


class SelectiveReadingTests(unittest.TestCase):
    def test_structural_duplicate_titles_stay_distinct_and_index_pages_are_complete(self):
        with tempfile.TemporaryDirectory() as directory:
            reader=Path(directory)/'reader';reader.mkdir()
            (reader/'paper.xhtml').write_text('''<html><body>
              <section id="first"><p id="one">First result.</p></section>
              <section id="second"><p id="two">Second result.</p></section></body></html>''')
            document={'directory':directory,'passages':[
                {'id':'p00001','section':'Results','text':'First result.','href':'reader/paper.xhtml#one'},
                {'id':'p00002','section':'Results','text':'Second result.','href':'reader/paper.xhtml#two'}]}
            first=build_orientation(document);second=build_orientation(document)
            self.assertEqual(first,second)
            self.assertEqual(['Results','Results'],[section['title'] for section in first['sections']])
            pages=[];offset=0
            while offset is not None:
                page=orientation_page(first,offset,1);pages.extend(page['entries']);offset=page['next_offset']
            self.assertEqual(['s0001','s0002'],[entry['id'] for entry in pages])
            self.assertTrue(all(entry['entry_kind']=='section' for entry in pages))

    def test_ambiguous_abstract_returns_locations_without_guessing_body_text(self):
        document={'passages':[{'id':'p00001','section':'Abstract','text':'Unmapped abstract candidate.'},
                               {'id':'p00002','section':'Method','text':'Body sentinel.'}]}
        orientation=build_orientation(document)
        self.assertEqual('ambiguous',orientation['abstract_status'])
        self.assertEqual(['p00001'],orientation['abstract_candidates'])
        self.assertEqual([],orientation['abstract'])

    def test_orientation_finds_structural_abstract_sections_appendix_and_figures(self):
        with tempfile.TemporaryDirectory() as directory:
            reader = Path(directory) / 'reader'
            reader.mkdir()
            (reader / 'figure.png').write_bytes(b'not loaded during orientation')
            (reader / 'paper.xhtml').write_text('''<html><body>
              <section id="abstract"><h1>Abstract</h1>
                <div class="center"><p id="license">Permission notice.</p></div>
                <p id="abstract-body">A real abstract with permission to compare methods.</p>
                <p id="author"><em>Author note:</em> Equal contribution.</p></section>
              <section><h1>1 Method</h1><p id="method">METHOD_BODY_SENTINEL</p>
                <section><h2>1.1 Detail</h2><figure id="figure"><img src="figure.png"/><figcaption>Full method caption.</figcaption></figure>
                <table id="table"><caption>Text-only result table.</caption><tr><td>Result</td></tr></table></section></section>
              <section role="doc-bibliography"><h1>References</h1><p id="bib">BIBLIOGRAPHY_SENTINEL</p></section>
              <section><h1>A. Additional experiments</h1><p id="appendix">Appendix evidence.</p></section>
            </body></html>''')
            passages = [
                {'id': 'p00001', 'section': 'Abstract', 'text': 'Permission notice.', 'href': 'reader/paper.xhtml#license'},
                {'id': 'p00002', 'section': 'Abstract', 'text': 'A real abstract with permission to compare methods.', 'href': 'reader/paper.xhtml#abstract-body'},
                {'id': 'p00003', 'section': 'Abstract', 'text': 'Author note: Equal contribution.', 'href': 'reader/paper.xhtml#author'},
                {'id': 'p00004', 'section': '1 Method', 'text': 'METHOD_BODY_SENTINEL', 'href': 'reader/paper.xhtml#method'},
                {'id': 'p00005', 'section': '1.1 Detail', 'text': 'Full method caption.', 'href': 'reader/paper.xhtml#figure'},
                {'id': 'p00008', 'section': '1.1 Detail', 'text': 'Text-only result table.', 'href': 'reader/paper.xhtml#table'},
                {'id': 'p00006', 'section': 'References', 'text': 'BIBLIOGRAPHY_SENTINEL', 'href': 'reader/paper.xhtml#bib'},
                {'id': 'p00007', 'section': 'A. Additional experiments', 'text': 'Appendix evidence.', 'href': 'reader/paper.xhtml#appendix'}]
            document = {'directory': directory, 'format': 'epub', 'passages': passages}
            before = copy.deepcopy(document)
            with unittest.mock.patch('pathlib.Path.read_bytes', side_effect=AssertionError('orientation loaded image bytes')):
                orientation = build_orientation(document)
            self.assertEqual(before, document)
            self.assertEqual('identified', orientation['abstract_status'])
            self.assertEqual(['p00002'], [item['passage'] for item in orientation['abstract']])
            self.assertIn('A. Additional experiments', [item['title'] for item in orientation['sections']])
            self.assertNotIn('References', [item['title'] for item in orientation['sections']])
            self.assertEqual(['figure','table'],[item['kind'] for item in orientation['figures']])
            self.assertFalse(orientation['figures'][1]['image_available'])
            initial = json.dumps({k: v for k, v in orientation.items() if k != 'sections'})
            self.assertNotIn('METHOD_BODY_SENTINEL', initial)
            self.assertNotIn('BIBLIOGRAPHY_SENTINEL', json.dumps(orientation))

    def test_retrieve_evidence_expands_children_deduplicates_and_loads_selected_image_only(self):
        with tempfile.TemporaryDirectory() as directory:
            reader = Path(directory) / 'reader'
            reader.mkdir()
            png = b'\x89PNG\r\n\x1a\nselected'
            (reader / 'selected.png').write_bytes(png)
            (reader / 'unselected.png').write_bytes(b'\x89PNG\r\n\x1a\nunselected')
            (reader / 'paper.xhtml').write_text('''<html><body>
              <figure id="selected"><img src="selected.png"/></figure>
              <figure id="unselected"><img src="unselected.png"/></figure></body></html>''')
            document = {'directory': directory, 'passages': [
                {'id': 'p00001', 'section': '1 Method', 'text': 'Parent.', 'href': 'reader/paper.xhtml#parent'},
                {'id': 'p00002', 'section': '1.1 Detail', 'text': 'Child.', 'href': 'reader/paper.xhtml#child'},
                {'id': 'p00003', 'section': '1.1 Detail', 'text': 'Selected caption.', 'href': 'reader/paper.xhtml#selected'},
                {'id': 'p00004', 'section': '2 Other', 'text': 'Unselected caption.', 'href': 'reader/paper.xhtml#unselected'}]}
            orientation = build_orientation(document)
            parent = next(section['id'] for section in orientation['sections'] if section['title'] == '1 Method')
            selected = next(figure['id'] for figure in orientation['figures'] if figure['passage'] == 'p00003')
            selection = {'paper_type': 'method', 'focus': 'Explain the method.',
                         'section_ids': [parent], 'passage_ids': ['p00003'], 'figure_ids': [selected]}
            evidence = retrieve_evidence(document, orientation, selection, vision=True)
            self.assertEqual(['p00001', 'p00002', 'p00003'], [p['id'] for p in evidence['passages']])
            self.assertEqual(1, len(evidence['images']))
            self.assertEqual('p00003', evidence['images'][0]['passage'])
            self.assertNotIn('unselected', json.dumps(evidence))
            self.assertEqual([selected], evidence['coverage']['attached_image_ids'])


class ReadingTests(unittest.TestCase):
    @unittest.skipUnless(__import__('importlib').util.find_spec('smolagents'),'AI environment required')
    def test_fresh_import_to_automatic_overview_runs_the_panel_workflow_once(self):
        import queue
        import threading
        from app.server import Application, DEFAULTS
        from papers.library import Library
        from tests.test_app import scripted_overview
        with tempfile.TemporaryDirectory() as temporary:
            app=Application.__new__(Application);app.library=Library(Path(temporary))
            app.lock,app.queue,app.active_job=threading.RLock(),queue.Queue(),None
            app.settings=Mock(return_value=dict(DEFAULTS,model='fixture',auto_summary=True))
            app.public_settings=Mock(return_value={});app.recommendations=Mock()
            provider=Mock(settings=dict(DEFAULTS,model='fixture',overview_vision=False),key=None)
            provider.complete.side_effect=scripted_overview()
            def converted(directory,metadata,progress,**kwargs):
                reader=Path(directory)/'reader';reader.mkdir()
                (reader/'paper.xhtml').write_text(
                    '<html><body><section id="abstract"><h1>Abstract</h1><p id="one">The paper asks how values are mixed.</p></section>'
                    '<section><h1>1 Method</h1><p id="two">It answers with attention weights.</p></section>'
                    '<section><h1>2 Results</h1><p id="three">It reaches the reported benchmark.</p></section>'
                    '<section><h1>3 Limitations</h1><p id="four">Only two datasets were tested.</p></section></body></html>')
                return dict(metadata,directory=str(directory),passages=[
                    {'id':'p00001','section':'Abstract','text':'The paper asks how values are mixed.','href':'reader/paper.xhtml#one'},
                    {'id':'p00002','section':'1 Method','text':'It answers with attention weights.','href':'reader/paper.xhtml#two'},
                    {'id':'p00003','section':'2 Results','text':'It reaches the reported benchmark.','href':'reader/paper.xhtml#three'},
                    {'id':'p00004','section':'3 Limitations','text':'Only two datasets were tested.','href':'reader/paper.xhtml#four'}])
            imported=app.library.create_job('import',{'url':'https://arxiv.org/abs/1706.03762'})
            with patch('papers.acquire.acquire',return_value={'arxiv_id':'1706.03762v7','title':'Fixture'}), \
                 patch('app.server.convert_import',side_effect=converted),patch('app.server.get_key',return_value='secret'), \
                 patch('app.server.Provider',return_value=provider):
                app.execute(imported)
                queued=app.library.get_job(app.queue.get_nowait())
                self.assertEqual('bento',queued['kind'])
                app.execute(queued)
            paper=app.library.get_paper('1706.03762v7')
            self.assertFalse((Path(paper['directory'])/'reader/paper-reading.json').exists())
            generation=app.library.get_generation('1706.03762v7','bento')
            self.assertEqual('panel-workflow-v1',generation['provenance']['workflow'])
            self.assertEqual(['p1','p2'],[panel['id'] for panel in generation['figures'][0]['panels']])
            self.assertEqual('reading-v5-selective',
                generation['provenance']['reading']['revision'])
            requests=[event for event in generation['provenance']['events'] if event.get('kind')=='model_request']
            self.assertEqual(['selection','narrative','panel_plan','panel_plan_clarify'],
                             [event['label'] for event in requests])
            self.assertEqual(2,len(generation['provenance']['panel_calls']),
                             'each panel is requested exactly once when it draws cleanly')

    def test_import_queues_only_an_enabled_automatic_overview(self):
        import queue
        import threading
        from app.server import Application, DEFAULTS
        from papers.library import Library
        for key,model,auto,expected in [(None,'fixture',True,[]),('secret','',True,[]),
                                        ('secret','fixture',False,[]),('secret','fixture',True,['bento'])]:
            with self.subTest(key=bool(key), model=model, auto=auto), tempfile.TemporaryDirectory() as temporary:
                app = Application.__new__(Application)
                app.library = Library(Path(temporary))
                app.lock, app.queue, app.active_job = threading.RLock(), queue.Queue(), None
                app.settings = Mock(return_value=dict(DEFAULTS, model=model, auto_summary=auto))
                app.public_settings = Mock(return_value={})
                app.recommendations = Mock()
                job = app.library.create_job('import', {'url':'https://arxiv.org/abs/1706.03762'})
                document = {'arxiv_id':'1706.03762', 'source_digest':'fixture', 'passages':[{'id':'p00001', 'text':'Evidence'}]}
                with patch('papers.acquire.acquire',return_value={'arxiv_id':'1706.03762'}), \
                     patch('app.server.convert_import',return_value=document), \
                     patch('app.server.get_key',return_value=key), \
                     patch('app.server.Provider') as provider:
                    app.execute(job)
                    queued = [app.library.get_job(app.queue.get_nowait()) for _ in range(app.queue.qsize())]
                    self.assertEqual(expected, [j['kind'] for j in queued])
                    self.assertEqual('ready', app.library.get_job(job['id'])['state'])
                    self.assertEqual(bool(expected),provider.called)

    def test_legacy_reading_job_indexes_locally_without_credentials(self):
        import queue
        import threading
        from app.server import Application
        from papers.library import Library
        with tempfile.TemporaryDirectory() as temporary:
            app=Application.__new__(Application);app.library=Library(Path(temporary))
            app.lock,app.queue,app.active_job=threading.RLock(),queue.Queue(),None
            paper={'id':'paper','arxiv_id':'paper','directory':temporary,'passages':[
                {'id':'p00001','section':'1 Method','text':'Evidence'}]}
            app.library.save_paper('paper',paper,temporary)
            job=app.library.create_job('reading',{'paper_id':'paper'})
            with patch('app.server.get_key',side_effect=AssertionError('key lookup')), \
                 patch('app.server.Provider',side_effect=AssertionError('provider construction')):
                result=app.execute(job)
            self.assertEqual('reading-v5-selective',result['reading']['revision'])
            self.assertEqual('sections',result['reading']['index_kind'])
