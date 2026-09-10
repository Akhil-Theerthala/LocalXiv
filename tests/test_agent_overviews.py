"""Exercise the real smolagents loop with scripted compatible-provider responses."""
import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from papers.ai import generate_overview, ProviderError
from papers.agent_overviews import validate_candidate, reusable_overview_figures
from papers.html_figures import sanitize

CANDIDATE={'paper_type':'evaluation','question':'How do the methods compare?',
 'contribution':'The paper compares two methods.','finding':'Their ranking depends on the setting.',
 'limitation':'Only these tasks were evaluated.','passages':['p00001'],
 'text':'The paper compares methods [p00001].\n\n{{figure:fig1}}\n\nThe figure shows their shared input [p00001].',
 'figures':[{'id':'fig1','title':'Compare the same input','paper_connection':'This paper compares two approaches.',
 'caption':'Only these tasks were evaluated.','illustrative':True,'passages':['p00001'],
 'html':'<svg viewBox="0 0 800 200"><text x="20" y="60" font-size="24">Same input</text></svg>'}]}


def action(name,**arguments):
    return {'text':'','tool_calls':[{'id':'call_'+name,'type':'function',
            'function':{'name':name,'arguments':json.dumps(arguments)}}],'usage':{'total_tokens':10}}


def scripted_provider(candidate):
    """Shared fixture for HTTP/export integration tests of the new tool protocol."""
    from tests.overview_fixture import response
    actions=iter([action('submit_candidate',candidate=candidate),action('review_candidate'),action('final_answer',answer='Done')])
    def complete(messages,**kwargs):
        if kwargs.get('json_object') is False:return next(actions)
        content=messages[-1]['content']
        if isinstance(content,list) and content[0]['text'].startswith('Review this paper-specific'):
            return {'text':'{"approved":true,"issues":[]}','usage':{}}
        return response(messages)
    return complete


def render_fixture(directory,figure,title):
    import base64
    import uuid
    relative=Path('reader/overview-figures')/uuid.uuid4().hex/figure['id']
    target=Path(directory)/relative;target.parent.mkdir(parents=True)
    target.with_suffix('.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200"><text x="20" y="40">Confidence needs context</text></svg>')
    target.with_suffix('.png').write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aWQAAAABJRU5ErkJggg=='))
    return {'svg':str(relative)+'.svg','png':str(relative)+'.png','checks':{'issues':[]}}

class MarkupTests(unittest.TestCase):
    def test_overview_starts_with_a_visual_and_limits_prose(self):
        doc={'passages':[{'id':'p00001'}]}
        architecture=copy.deepcopy(CANDIDATE);architecture['paper_type']='architecture'
        validate_candidate(architecture,doc,True)
        for field,limit in (('title',12),('paper_connection',30),('caption',45)):
            bad=copy.deepcopy(CANDIDATE);bad['figures'][0][field]='word '*(limit+1)
            with self.assertRaises(ValueError):validate_candidate(bad,doc,True)
        bad=copy.deepcopy(CANDIDATE)
        bad['figures'][0]['html']='<p>Long introduction</p>'+bad['figures'][0]['html']
        with self.assertRaises(ValueError):validate_candidate(bad,doc,True)
        with self.assertRaises(ValueError):validate_candidate(bad,doc,False)

    def test_comments_are_removed_without_allowing_active_markup(self):
        self.assertEqual('<div><p>Text</p></div>',sanitize('<!-- layout note --><p>Text</p>'))
        with self.assertRaises(ValueError):sanitize('<!-- note --><script>bad()</script>')

    def test_rejects_resource_loads_code_and_unbounded_content(self):
        for bad in ['<script>alert(1)</script>','<img src="file:///etc/passwd"/>',
                    '<div style="background:url(https://bad.test)">x</div>',
                    '<svg viewBox="0 0 800 200"><use href="#x"/></svg>',
                    '<p onclick="x()">text</p>','<!DOCTYPE x><p>x</p>',
                    '<svg viewBox="0 0 800 200"><text font-size="12">tiny</text></svg>']:
            with self.subTest(bad=bad),self.assertRaises(ValueError):sanitize(bad)
        self.assertIn('Same input',sanitize(CANDIDATE['figures'][0]['html']))

    def test_paper_claims_citations_and_markers_are_required(self):
        doc={'passages':[{'id':'p00001'}]}
        for field in ('contribution','finding','limitation'):
            bad=copy.deepcopy(CANDIDATE);bad[field]=''
            with self.assertRaises(ValueError):validate_candidate(bad,doc,True)
        bad=copy.deepcopy(CANDIDATE);bad['figures'][0]['passages']=['p0047']
        with self.assertRaises(ValueError):validate_candidate(bad,doc,True)
        bad=copy.deepcopy(CANDIDATE);bad['text']+=' {{figure:fig2}}'
        with self.assertRaises(ValueError):validate_candidate(bad,doc,False)


@unittest.skipUnless(importlib.util.find_spec('smolagents'),'Install requirements-ai.txt for agent integration tests')
class AgentTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.doc={'directory':tmp.name,'title':'Evaluation paper','passages':[{'id':'p00001','text':'Two methods were evaluated. Ranking varies by task.'}]}
        self.provider=Mock(settings={'model':'fixture','overview_language':'formal','overview_length':'short','overview_vision':True})
        self.read=patch('papers.agent_overviews.prepare_reading',return_value=([{'text':'Notes [p00001].'}],[{'total_tokens':3}],{'reused':True})).start()
        self.addCleanup(patch.stopall)
        def render(directory,figure,title):
            path=Path(directory)/'figure.png';path.write_bytes(b'\x89PNG\r\n\x1a\nfixture')
            return {'png':'figure.png','html':'figure.html','svg':'figure.svg','pdf':'figure.pdf','checks':{'issues':[]}}
        self.render=patch('papers.html_figures.render',side_effect=render).start()

    def replies(self,candidate=CANDIDATE):
        return [action('submit_candidate',candidate=candidate),action('review_candidate'),
                {'text':'{"approved":true,"issues":[]}','usage':{'total_tokens':5}},action('final_answer',answer='Done')]

    def saved_overview(self):
        from papers.library import document_digest
        figure=copy.deepcopy(CANDIDATE['figures'][0])
        figure['source_html']=figure['html']
        for ext in ('html','svg','png','pdf'):
            name='saved-figure.'+ext
            (Path(self.doc['directory'])/name).write_text('<header></header>'+figure['source_html']+'<footer></footer>' if ext=='html' else 'fixture')
            figure[ext]=name
        figure['checks']={'issues':[]}
        return {'figures':[figure],'explanation':{'question':'Which methods share inputs?'},
                'provenance':{'document_digest':document_digest(self.doc),'created_at':'saved-time',
                              'reviews':[{'approved':True,'issues':[]}]}}

    def test_blog_reuses_reviewed_overview_without_rendering_it_again(self):
        overview=self.saved_overview();before=copy.deepcopy(overview)
        candidate=copy.deepcopy(CANDIDATE);candidate['figures']=[{'id':'fig1','reuse':'overview_fig1'}]
        self.provider.complete.side_effect=self.replies(candidate)
        result=generate_overview(self.provider,self.doc,lambda _:None,image_overview=overview)
        self.render.assert_not_called()
        self.assertEqual('saved-figure.png',result['figures'][0]['png'])
        self.assertEqual('overview_fig1',result['figures'][0]['reused_from'])
        self.assertEqual('saved-time',result['provenance']['overview_basis']['created_at'])
        self.assertEqual(overview,before)
        prompt=json.dumps(self.provider.complete.call_args_list[0].args[0])
        self.assertIn('default visual and narrative foundation',prompt)
        self.assertIn('Which methods share inputs?',prompt)
        self.assertEqual('Same input' in result['figures'][0]['source_html'],True)

    def test_blog_can_reuse_one_figure_and_render_an_additional_figure(self):
        overview=self.saved_overview();candidate=copy.deepcopy(CANDIDATE)
        extra=dict(candidate['figures'][0],id='fig2')
        candidate['figures']=[{'id':'fig1','reuse':'overview_fig1'},extra]
        candidate['text']+='\n\nAnother relationship [p00001].\n\n{{figure:fig2}}'
        self.provider.complete.side_effect=self.replies(candidate)
        result=generate_overview(self.provider,self.doc,lambda _:None,image_overview=overview)
        self.assertEqual(1,self.render.call_count)
        self.assertEqual('fig2',self.render.call_args.args[1]['id'])
        self.assertEqual(2,len(result['figures']))

    def test_unusable_overview_falls_back_to_direct_blog(self):
        for reason in ('absent','stale','unreviewed','missing_asset','external_asset'):
            overview=self.saved_overview()
            if reason=='absent':overview=None
            elif reason=='stale':overview['provenance']['document_digest']='old'
            elif reason=='unreviewed':overview['provenance']['reviews'][-1]['approved']=False
            elif reason=='missing_asset':overview['figures'][0]['png']='missing.png'
            else:overview['figures'][0]['html']='/etc/passwd'
            self.render.reset_mock();self.provider.complete.side_effect=self.replies()
            result=generate_overview(self.provider,self.doc,lambda _:None,image_overview=overview)
            self.assertEqual(1,self.render.call_count,reason)
            self.assertIsNone(result['provenance']['overview_basis'])

    def test_older_html_overview_can_recover_its_editable_fragment(self):
        overview=self.saved_overview();del overview['figures'][0]['source_html']
        reusable=reusable_overview_figures(self.doc,overview)
        self.assertIn('Same input',reusable['overview_fig1']['spec']['html'])

    def test_reuse_does_not_bypass_blog_review(self):
        candidate=copy.deepcopy(CANDIDATE);candidate['figures']=[{'id':'fig1','reuse':'overview_fig1'}]
        self.provider.complete.side_effect=[action('submit_candidate',candidate=candidate),action('review_candidate'),
            {'text':'{"approved":false,"issues":["Prose misinterprets the reused figure"]}'},RuntimeError('stop')]
        with self.assertRaises(ProviderError):
            generate_overview(self.provider,self.doc,lambda _:None,image_overview=self.saved_overview())
        self.render.assert_not_called()

    def test_both_modes_use_agent_render_review_and_preserve_preferences(self):
        for visual in (True,False):
            self.provider.complete.side_effect=self.replies()
            result=generate_overview(self.provider,self.doc,lambda _:None,visual=visual)
            self.assertEqual('smolagents-tool-html-v4',result['provenance']['prompt_revision'])
            self.assertEqual('ToolCallingAgent',result['provenance']['agent_type'])
            self.assertEqual('formal',result['provenance']['overview_language'])
            self.assertIn({'total_tokens':3},result['provenance']['usage'])
            self.assertTrue(result['provenance']['vision_review'])
            self.assertEqual('figure.html',result['figures'][0]['html'])
            self.assertIn('{{figure:fig1}}',result['text'])
            review_prompt=self.provider.complete.call_args_list[-2].args[0][-1]['content'][0]['text']
            self.assertIn('Mode: Overview image.' if visual else 'Mode: Blog.',review_prompt)
            if visual:self.assertNotIn('Requested length:',review_prompt)
            self.assertNotIn('[p00001]',result['text'])
            review=self.provider.complete.call_args_list[-2].args[0][1]['content']
            self.assertEqual('image_url',review[-1]['type'])

    def test_failed_review_can_be_repaired_but_never_silently_accepted(self):
        revised=copy.deepcopy(CANDIDATE);revised['limitation']='A revised qualification.'
        self.provider.complete.side_effect=[action('submit_candidate',candidate=CANDIDATE),action('review_candidate'),
            {'text':'{"approved":false,"issues":["Correct the limitation"]}'},*self.replies(revised)]
        result=generate_overview(self.provider,self.doc,lambda _:None,visual=True)
        self.assertEqual(2,len(result['provenance']['reviews']))
        self.assertFalse(result['provenance']['reviews'][0]['approved'])
        self.assertEqual(2,self.render.call_count)

    def test_geometry_errors_feed_back_without_spending_review_calls(self):
        self.render.side_effect=None
        self.render.return_value={'png':'x.png','checks':{'issues':['Overlapping text']}}
        self.provider.complete.side_effect=[action('submit_candidate',candidate=CANDIDATE),action('review_candidate'),RuntimeError('stop')]
        with self.assertRaises(ProviderError):generate_overview(self.provider,self.doc,lambda _:None,visual=True)
        self.assertEqual(3,self.provider.complete.call_count)
        self.assertIn('Overlapping text',json.dumps(self.provider.complete.call_args.args[0]))

    def test_cannot_finish_without_an_approved_candidate(self):
        self.provider.complete.return_value=action('final_answer',answer='Done')
        with self.assertRaises(ProviderError):generate_overview(self.provider,self.doc,lambda _:None,visual=True)
        self.render.assert_not_called()
        self.assertLessEqual(self.provider.complete.call_count,16)

    def test_invalid_candidate_does_not_render(self):
        invalid=copy.deepcopy(CANDIDATE);invalid['figures'][0]['html']='<script>evil</script>'
        self.provider.complete.side_effect=[action('submit_candidate',candidate=invalid),RuntimeError('stop')]
        with self.assertRaises(ProviderError):generate_overview(self.provider,self.doc,lambda _:None,visual=True)
        self.render.assert_not_called()

    def test_only_named_tools_are_exposed(self):
        self.provider.complete.side_effect=self.replies()
        generate_overview(self.provider,self.doc,lambda _:None,visual=True)
        tools=self.provider.complete.call_args_list[0].kwargs['tools']
        self.assertEqual({'diagram_reference','read_passages','submit_candidate','review_candidate','final_answer'},
                         {t['function']['name'] for t in tools})
        candidate=next(t for t in tools if t['function']['name']=='submit_candidate')
        self.assertIn('figures',candidate['function']['parameters']['properties']['candidate']['properties'])

    def test_plain_model_does_not_receive_images(self):
        self.provider.settings['overview_vision']=False
        self.provider.complete.side_effect=self.replies()
        result=generate_overview(self.provider,self.doc,lambda _:None,visual=True)
        self.assertFalse(result['provenance']['vision_review'])
        review=self.provider.complete.call_args_list[-2].args[0][1]['content']
        self.assertTrue(all(p['type']=='text' for p in review))

    def test_gemini_uses_json_and_low_thinking(self):
        self.provider.settings.update(model='gemini-3.8-flash',endpoint='https://generativelanguage.googleapis.com/v1beta/openai/')
        self.provider.complete.side_effect=self.replies()
        generate_overview(self.provider,self.doc,lambda _:None,visual=True)
        for call in self.provider.complete.call_args_list:
            self.assertEqual('low',call.kwargs['gemini_thinking_level'])
        self.assertFalse(self.provider.complete.call_args_list[0].kwargs['json_object'])
        self.assertTrue(self.provider.complete.call_args_list[2].kwargs['json_object'])
