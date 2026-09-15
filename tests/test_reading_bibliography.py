"""Bibliography exclusion at the actual AI request boundary; original paper retained."""
import copy
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from papers.ai import generate_overview
from papers.library import document_digest
from papers.reading import build_orientation, evidence_document, retrieve_evidence
from tests.test_agent_overviews import (action, blog_brief, draft_for, panel_reply,
                                          plan_for, prompt_text, resolve, verdict)


class BibliographyTests(unittest.TestCase):
    def test_xhtml_structure_and_heading_fallback_preserve_discussion_and_appendix(self):
        with tempfile.TemporaryDirectory() as directory:
            reader = Path(directory) / 'reader'
            reader.mkdir()
            (reader / 'paper.xhtml').write_text('''<html xmlns="http://www.w3.org/1999/xhtml">
              <p id="body">Related work cites Smith [1].</p>
              <section role="doc-bibliography"><div><p id="bib">Secret bibliography entry</p></div></section>
              <div class="ltx_bibitem" id="bib2">Another reference</div>
              <div class="csl-entry" id="bib3">Pandoc reference</div>
              <p id="appendix">Appendix proof.</p></html>''')
            passages = [dict(id=f'p{i:05d}', text=text, section=section, href='reader/paper.xhtml#'+anchor)
                        for i, (anchor, section, text) in enumerate([
                            ('body', 'Related work', 'Related work cites Smith [1].'),
                            ('bib', 'Paper title', 'Secret bibliography entry'),
                            ('bib2', 'Paper title', 'Another reference'),
                            ('bib3', 'Paper title', 'Pandoc reference'),
                            ('missing', '12. References', 'Heading-only reference'),
                            ('appendix', 'Appendix A', 'Appendix proof.')], 1)]
            doc = dict(directory=directory, passages=passages)
            before = copy.deepcopy(doc)
            filtered = evidence_document(doc)
            self.assertEqual(['p00001', 'p00006'], [p['id'] for p in filtered['passages']])
            self.assertIn('Smith [1]', filtered['passages'][0]['text'])
            self.assertEqual(before, doc)
            self.assertEqual(filtered, evidence_document(filtered))

    def test_pdf_mixed_pages_multpage_references_and_appendix(self):
        for heading in ('Appendix A. Proof', 'A Proof of the bound', 'Supplementary material'):
            with self.subTest(heading=heading):
                doc = {'format':'pdf', 'passages':[
                    {'id':'p00001', 'text':'Conclusion\nOur result [3].\nReferences\nFirst reference'},
                    {'id':'p00002', 'text':'A. Smith and B. Jones. A title.\nMore references'},
                    {'id':'p00003', 'text':'Last reference\n'+heading+'\nProof retained.'}]}
                before = copy.deepcopy(doc)
                filtered = evidence_document(doc)['passages']
                self.assertEqual(['p00001', 'p00003'], [p['id'] for p in filtered])
                self.assertEqual('Conclusion\nOur result [3].', filtered[0]['text'])
                self.assertEqual(heading+'\nProof retained.', filtered[1]['text'])
                self.assertEqual(before, doc)
        doc = {'format':'pdf', 'passages':[{'id':'p00001', 'text':'The bibliography discusses related work.\nReferences to our method appear throughout.'}]}
        self.assertEqual(doc, evidence_document(doc))

    def test_outside_reader_files_are_not_parsed(self):
        with tempfile.TemporaryDirectory() as directory:
            doc = {'directory':directory, 'passages':[{'id':'p00001', 'text':'Body', 'href':'../outside.xhtml#ref'}]}
            with patch('papers.reading.ET.parse') as parse:
                self.assertEqual(doc, evidence_document(doc))
                parse.assert_not_called()

    def test_pdf_unnumbered_figure_supplement_survives_reversed_extraction_order(self):
        doc = {'format':'pdf', 'passages':[
            {'id':'p00010', 'text':'Conclusion.\nReferences\n[1] First reference'},
            {'id':'p00011', 'text':'[2] Another reference\nContinuation of the title'},
            {'id':'p00012', 'text':'12\nCaption continuation.\nFigure 3: A dependency example.\nTokens\nAttention Visualizations'},
            {'id':'p00013', 'text':'Figure 4: Another example.'}]}
        filtered = evidence_document(doc)['passages']
        self.assertEqual(['p00010','p00012','p00013'], [p['id'] for p in filtered])
        self.assertEqual(doc['passages'][2:], filtered[1:])

    def test_selective_reading_ignores_old_cache_and_never_calls_a_provider(self):
        with tempfile.TemporaryDirectory() as directory:
            reader=Path(directory)/'reader';reader.mkdir()
            cache=reader/'paper-reading.json'
            cache.write_text(json.dumps({'revision':'reading-v3','notes':['BIBLIOGRAPHY_SENTINEL']}))
            doc = {'directory':directory, 'passages':[
                {'id':'p00001', 'section':'Results', 'text':'Our result cites [1].'},
                {'id':'p00002', 'section':'Bibliography', 'text':'BIBLIOGRAPHY_SENTINEL'},
                {'id':'p00003', 'section':'Appendix', 'text':'The full proof.'}]}
            orientation=build_orientation(doc)
            selected=[section['id'] for section in orientation['sections']]
            evidence=retrieve_evidence(doc,orientation,{'paper_type':'evaluation','focus':'Explain the result and proof.',
                'section_ids':selected,'passage_ids':[],'figure_ids':[]},vision=False)
            self.assertEqual(['p00001','p00003'],[item['id'] for item in evidence['passages']])
            self.assertNotIn('BIBLIOGRAPHY_SENTINEL',json.dumps(evidence))
            self.assertEqual({'revision':'reading-v3','notes':['BIBLIOGRAPHY_SENTINEL']},json.loads(cache.read_text()))

    def test_planning_and_authoring_use_filtered_evidence_in_both_modes(self):
        """Neither Blog nor the panel workflow ever receives bibliography-only text."""
        from tests.test_agent_overviews import (CANDIDATE, action, draft_for, panel_reply, plan_for,
                                                render_fixture, verdict)
        claims = {name: {'text': name.capitalize() + ' claim.', 'passages': ['p00001']}
                  for name in ('question', 'contribution', 'finding', 'limitation')}
        narrative = {'paper_type': 'evaluation', 'visual_focus': 'One panel only.', **claims,
                     'relationships': [{'source': 'a', 'target': 'b', 'relationship': 'r',
                                        'passages': ['p00001']}]}
        panel_plan = {'title': 'Overview', 'paper_connection': 'One panel.', 'caption': 'One panel.',
                      'shared_facts': {},
                      'panels': [{'id': 'p1', 'title': 'Only panel', 'purpose': 'Explain the result.',
                                  'covers': ['question', 'contribution', 'finding', 'limitation'],
                                  'entry_from': [], 'exit_state': 'The reader knows the result.',
                                  'shared_fact_ids': [],
                                  'content': [{'text': 'One retained result.', 'passages': ['p00001'],
                                               'kind': 'statement'}],
                                  'construction': 'flow'}]}
        panel_svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 520 300" font-size="18">'
                     '<text x="40" y="60" font-weight="bold">Only panel</text>'
                     '<text x="40" y="140">One retained result.</text></svg>')

        def visual_script(messages, **kwargs):
            text = json.dumps(messages)
            if 'SOURCE MAP' in text:
                answer = {'paper_type': 'evaluation', 'focus': 'Explain the result.', 'section_ids': [],
                          'passage_ids': ['p00001'], 'figure_ids': []}
            elif 'Plan what the reader will learn' in text:
                answer = narrative
            elif 'Assign the accepted narrative' in text:
                answer = panel_plan
            elif 'Check this draft panel plan' in text:
                answer = {'panel_plan': panel_plan, 'issues': []}
            elif 'DRAWING ASSIGNMENT' in text:
                answer = {'panel_id': 'p1', 'svg': panel_svg}
            else:
                raise AssertionError('Unscripted request: ' + text[-200:])
            return {'text': json.dumps(answer), 'usage': {}}

        for visual in (True, False):
            with self.subTest(visual=visual), tempfile.TemporaryDirectory() as directory:
                doc = {'directory': directory, 'passages': [
                    {'id': 'p00001', 'text': 'Results.\nReferences\nBIBLIOGRAPHY_SENTINEL',
                     'href': 'original.pdf#page=1'},
                    {'id': 'p00002', 'text': 'ONLY_BIBLIOGRAPHY', 'href': 'original.pdf#page=2'}]}
                provider = Mock(settings={'model': 'fixture'})
                if visual:
                    provider.complete.side_effect = visual_script
                    result = generate_overview(provider, doc, lambda _: None, visual=True)
                else:
                    from papers.agent_overviews import candidate_digest
                    approved={'action':'verdict','approved':True,'issues':[],'resolutions':[],
                              'candidate_digest':candidate_digest(draft_for(CANDIDATE)['text'])}
                    provider.complete.side_effect = [
                        action('submit_selection', candidate={'paper_type': 'evaluation',
                            'focus': 'Explain the result.', 'section_ids': [], 'passage_ids': ['p00001'],
                            'figure_ids': []}),
                        action('submit_plan', candidate=plan_for(CANDIDATE)),
                        action('submit_draft', candidate=draft_for(CANDIDATE)),
                        panel_reply('fig1'),
                        {'text': json.dumps(approved), 'usage': {}}]
                    with patch('papers.html_figures.render', side_effect=render_fixture):
                        result = generate_overview(provider, doc, lambda _: None, visual=False)
                payload = json.dumps([call.args for call in provider.complete.call_args_list])
                self.assertNotIn('BIBLIOGRAPHY_SENTINEL', payload)
                self.assertNotIn('ONLY_BIBLIOGRAPHY', payload)
                self.assertEqual(document_digest(doc), result['provenance']['document_digest'])
                self.assertEqual(['p00001'], result['provenance']['passages'])


@unittest.skipUnless(__import__('importlib').util.find_spec('smolagents'),'AI environment required')
class BlogRequestBoundaryTests(unittest.TestCase):
    """Every new Blog provider boundary sees filtered evidence and the source map it needs."""

    def build(self,directory,*,abstract='identified'):
        reader=Path(directory)/'reader';reader.mkdir()
        sections=[]
        passages=[]
        if abstract=='identified':
            sections.append('<section id="abstract"><h1>Abstract</h1>'
                            '<p id="abs">ABSTRACT_SENTINEL and a comparison.</p></section>')
            passages.append({'id':'p00001','section':'Abstract',
                             'text':'ABSTRACT_SENTINEL and a comparison.','href':'reader/paper.xhtml#abs'})
        elif abstract=='ambiguous':
            passages.append({'id':'p00001','section':'Abstract',
                             'text':'AMBIGUOUS_SENTINEL.','href':''})
        sections.append('<section><h1>1 Method</h1><p id="method">METHOD_SENTINEL with a comparison [1].</p></section>')
        sections.append('<section><h1>2 Unrelated</h1><p id="unrelated">UNRELATED_SENTINEL.</p></section>')
        sections.append('<section><h1>3 Related work</h1><p id="related">RELATED_SENTINEL discusses prior work [1].</p></section>')
        sections.append('<section role="doc-bibliography"><h1>References</h1>'
                        '<div class="csl-entry"><p id="bib">BIBLIOGRAPHY_SENTINEL.</p></div></section>')
        sections.append('<section><h1>A. Additional proof</h1><p id="appendix">APPENDIX_SENTINEL.</p></section>')
        (reader/'paper.xhtml').write_text('<html><body>'+''.join(sections)+'</body></html>')
        passages.extend([
            {'id':'p00002','section':'1 Method','text':'METHOD_SENTINEL with a comparison [1].',
             'href':'reader/paper.xhtml#method'},
            {'id':'p00006','section':'3 Related work','text':'RELATED_SENTINEL discusses prior work [1].',
             'href':'reader/paper.xhtml#related'},
            {'id':'p00003','section':'2 Unrelated','text':'UNRELATED_SENTINEL.',
             'href':'reader/paper.xhtml#unrelated'},
            {'id':'p00004','section':'References','text':'BIBLIOGRAPHY_SENTINEL.',
             'href':'reader/paper.xhtml#bib'},
            {'id':'p00005','section':'A. Additional proof','text':'APPENDIX_SENTINEL.',
             'href':'reader/paper.xhtml#appendix'}])
        return {'directory':directory,'title':'Boundary paper','format':'epub','passages':passages}

    def run_blog(self,document,*,supplement=None):
        from papers.ai import generate_overview
        from tests.test_agent_overviews import CANDIDATE
        selected=dict(CANDIDATE,passages=['p00002'])
        payloads=[]
        def complete(messages,**kwargs):
            payloads.append(json.dumps(messages,ensure_ascii=False))
            if kwargs.get('json_object') is False:
                names={item['function']['name'] for item in kwargs.get('tools',[])}
                if 'submit_selection' in names:
                    text=prompt_text(messages)
                    source_map=json.loads(text.split('<source_map>\n',1)[1]
                                          .split('\n</source_map>',1)[0])
                    method=next(entry['id'] for entry in source_map['entries']
                                if entry.get('title')=='1 Method')
                    self.source_maps.append(source_map)
                    return action('submit_selection',candidate={'paper_type':'method',
                        'focus':'Explain the method.','section_ids':[method],
                        'passage_ids':[],'figure_ids':[]})
                if 'submit_plan' in names:
                    return action('submit_plan',candidate=plan_for(selected))
                if 'submit_draft' in names:
                    if supplement and not any('APPENDIX_SENTINEL' in payload for payload in payloads):
                        return action('read_evidence',section_ids=[],passage_ids=[supplement],
                                      figure_ids=[])
                    return action('submit_draft',candidate=draft_for(
                        selected,figures=[blog_brief(passages=['p00002'])],
                        text='The method adds a small learned update [p00002].'
                             '\n\n{{figure:fig1}}'))
                raise AssertionError('Unscripted authoring request')
            text=prompt_text(messages)
            if 'DRAWING ASSIGNMENT' in text:
                identifier=re.search(r'panel id: (fig\d+)',text).group(1)
                return panel_reply(identifier)
            if 'STAGE: REVIEW' in text:
                return verdict()(messages)
            raise AssertionError('Unscripted structured request')
        provider=Mock(settings={'model':'fixture','overview_language':'formal',
                                'overview_length':'short','overview_vision':False})
        provider.complete.side_effect=complete
        self.source_maps=[]
        result=generate_overview(provider,document,lambda _:None)
        return result,payloads,provider

    def test_selection_uses_the_abstract_then_authoring_sees_only_selected_evidence(self):
        for abstract,status in (('identified','identified'),('ambiguous','ambiguous'),
                                ('unavailable','unavailable')):
            with self.subTest(abstract=abstract),tempfile.TemporaryDirectory() as directory:
                document=self.build(directory,abstract=abstract)
                before=copy.deepcopy(document)
                result,payloads,_=self.run_blog(document,supplement='p00005')
                selection=payloads[0]
                self.assertEqual(status,self.source_maps[0]['abstract_status'])
                self.assertIn('A. Additional proof',selection)
                if abstract=='identified':
                    self.assertIn('ABSTRACT_SENTINEL',selection)
                else:
                    self.assertNotIn('ABSTRACT_SENTINEL',selection)
                if status=='unavailable':
                    self.assertIn('No explicit abstract was identified.',selection)
                author=payloads[2]
                self.assertIn('METHOD_SENTINEL',author)
                self.assertNotIn('ABSTRACT_SENTINEL',author)
                self.assertNotIn('UNRELATED_SENTINEL',author)
                self.assertNotIn('APPENDIX_SENTINEL',author)
                after_supplement=payloads[3]
                self.assertIn('APPENDIX_SENTINEL',after_supplement)
                self.assertIn('[p00005]',after_supplement)
                self.assertNotIn('UNRELATED_SENTINEL',after_supplement)
                for payload in payloads:
                    self.assertNotIn('BIBLIOGRAPHY_SENTINEL',payload)
                    self.assertNotIn('ONLY_BIBLIOGRAPHY',payload)
                self.assertEqual(before,document)
                self.assertEqual(document_digest(document),result['provenance']['document_digest'])

    def test_repair_and_cleanup_boundaries_exclude_bibliography_material(self):
        """The omission cleanup and the article repair see filtered evidence and the full article."""
        from tests.test_agent_overviews import (CANDIDATE, article_and_digest, cleanup_reply,
                                                invalid_reply, review_issue, selection_for)
        with tempfile.TemporaryDirectory() as directory:
            document=self.build(directory)
            before=copy.deepcopy(document)
            selected=dict(CANDIDATE,passages=['p00002'])
            text=('The method adds a small learned update [p00002].\n\n'
                  'Follow the blue branch below to see the addition [p00002].\n\n{{figure:fig1}}\n\n'
                  'Prior work discusses the same comparison [p00006].\n\n'
                  'Only the method was evaluated [p00002].')
            payloads=[]
            stage={'reviewed':False}
            def complete(messages,**kwargs):
                payloads.append(json.dumps(messages,ensure_ascii=False))
                if kwargs.get('json_object') is False:
                    names={item['function']['name'] for item in kwargs.get('tools',[])}
                    if 'submit_selection' in names:
                        candidate=selection_for()
                        candidate['passage_ids']=['p00002','p00006']
                        return action('submit_selection',candidate=candidate)
                    if 'submit_plan' in names:
                        return action('submit_plan',candidate=plan_for(selected))
                    if 'submit_draft' in names:
                        return action('submit_draft',candidate=draft_for(
                            selected,figures=[blog_brief(passages=['p00002'])],text=text))
                    raise AssertionError('Unscripted authoring request')
                prompt=prompt_text(messages)
                if 'DRAWING ASSIGNMENT' in prompt:
                    return invalid_reply()
                if 'STAGE: TEXT CORRECTION' in prompt:
                    article,digest=article_and_digest(messages)
                    if 'REMOVE OMITTED FIGURES' in prompt:
                        return cleanup_reply(article,digest,[
                            {'old':'Follow the blue branch below to see the addition [p00002].',
                             'new':'The two outputs are added [p00002].'}])
                    return cleanup_reply(article,digest,[
                        {'old':'Only the method was evaluated [p00002].',
                         'new':'Only the method was evaluated here [p00002].'}])
                if 'STAGE: REVIEW' in prompt:
                    if not stage['reviewed']:
                        stage['reviewed']=True
                        return verdict(review_issue(category='scope',path='article',
                                                    message='The evaluation scope is missing.',
                                                    passages=('p00002',)))(messages)
                    return verdict(resolutions=resolve(quote='evaluated here'))(messages)
                raise AssertionError('Unscripted structured request')
            provider=Mock(settings={'model':'fixture','overview_language':'formal',
                                    'overview_length':'short','overview_vision':False})
            provider.complete.side_effect=complete
            result=generate_overview(provider,document,lambda _:None)
            cleanup=next(payload for payload in payloads if 'REMOVE OMITTED FIGURES' in payload)
            repair=next(payload for payload in payloads
                        if 'STAGE: TEXT CORRECTION' in payload and 'REMOVE OMITTED FIGURES' not in payload)
            self.assertIn('The method adds a small learned update [p00002].',cleanup)
            self.assertIn('fig1',cleanup)
            self.assertIn('The two outputs are added [p00002].',repair)
            self.assertIn('Prior work discusses the same comparison [p00006].',repair)
            for payload in payloads:
                self.assertNotIn('BIBLIOGRAPHY_SENTINEL',payload)
                self.assertNotIn('ONLY_BIBLIOGRAPHY',payload)
            self.assertEqual(before,document)
            self.assertEqual(document_digest(document),result['provenance']['document_digest'])
            self.assertNotIn('blue branch',result['cited_text'])
            self.assertIn('The two outputs are added [p00002].',result['cited_text'])
            self.assertIn('The method adds a small learned update [p00002].',result['cited_text'])
            self.assertIn('Prior work discusses the same comparison [p00006].',result['cited_text'])
            self.assertIn('evaluated here [p00002]',result['cited_text'])
            self.assertEqual([],result['figures'])

    def test_the_appendix_arrives_only_after_a_supplemental_request(self):
        with tempfile.TemporaryDirectory() as directory:
            document=self.build(directory)
            result,payloads,_=self.run_blog(document)
            author=payloads[2]
            self.assertIn('METHOD_SENTINEL',author)
            self.assertNotIn('APPENDIX_SENTINEL',author)
            self.assertEqual(['p00002'],result['provenance']['passages'])

    def test_a_large_source_map_is_paged_without_dropping_entries(self):
        from papers.agent_overviews import _orientation_payload
        orientation={'revision':'reading-v5-selective','document_digest':'digest','abstract':[],
                     'abstract_status':'unavailable','abstract_candidates':[],
                     'index_kind':'sections','figures':[],'warnings':[],
                     'sections':[{'id':'s%04d' % index,'title':'Section %d' % index,'parent':None,
                                  'passages':[],'chars':0,'is_appendix':False}
                                 for index in range(1,251)]}
        page=_orientation_payload(orientation)
        self.assertTrue(page['partial'])
        self.assertEqual(250,page['total'])
        self.assertIsNotNone(page['next_offset'])
        self.assertLessEqual(len(json.dumps(page,ensure_ascii=False)),24_000)
        self.assertIn('read_index',page['diagnostic'])


if __name__ == '__main__':
    unittest.main()
