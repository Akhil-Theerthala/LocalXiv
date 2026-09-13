"""Bibliography exclusion at the actual AI request boundary; original paper retained."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from papers.ai import generate_overview
from papers.library import document_digest
from papers.reading import build_orientation, evidence_document, retrieve_evidence


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
        from tests.test_agent_overviews import (CANDIDATE, action, plan_for, draft_for, render_fixture)
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
                    verdict = {'text': '{"action":"verdict","approved":true,"issues":[]}', 'usage': {}}
                    provider.complete.side_effect = [
                        action('submit_selection', candidate={'paper_type': 'evaluation',
                            'focus': 'Explain the result.', 'section_ids': [], 'passage_ids': ['p00001'],
                            'figure_ids': []}),
                        action('submit_plan', candidate=plan_for(CANDIDATE)),
                        action('submit_candidate', candidate=draft_for(CANDIDATE, visual=False)),
                        verdict]
                    with patch('papers.html_figures.render', side_effect=render_fixture):
                        result = generate_overview(provider, doc, lambda _: None, visual=False)
                payload = json.dumps([call.args for call in provider.complete.call_args_list])
                self.assertNotIn('BIBLIOGRAPHY_SENTINEL', payload)
                self.assertNotIn('ONLY_BIBLIOGRAPHY', payload)
                self.assertEqual(document_digest(doc), result['provenance']['document_digest'])
                self.assertEqual(['p00001'], result['provenance']['passages'])


if __name__ == '__main__':
    unittest.main()
