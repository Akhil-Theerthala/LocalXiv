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


def plan_for(candidate=CANDIDATE):
    return {'paper_type':candidate['paper_type'],
            **{key:{'text':candidate[key],'passages':candidate['passages']} for key in ('question','contribution','finding','limitation')},
            'visual_focus':'Follow the shared input through the compared operations.',
            'relationships':[{'source':'Input','target':'Methods','relationship':'Same input for comparison','passages':candidate['passages']}]}


def draft_for(candidate=CANDIDATE):
    return {'plan':plan_for(candidate),'text':candidate['text'],'figures':copy.deepcopy(candidate['figures'])}


def action(name,**arguments):
    return {'text':'','tool_calls':[{'id':'call_'+name,'type':'function',
            'function':{'name':name,'arguments':json.dumps(arguments)}}],'usage':{'total_tokens':10}}


def scripted_provider(candidate):
    """Shared fixture for HTTP/export integration tests of the new tool protocol."""
    from tests.overview_fixture import response
    actions=iter([action('submit_plan',candidate=plan_for(candidate)),action('submit_candidate',candidate=draft_for(candidate))])
    def complete(messages,**kwargs):
        if kwargs.get('json_object') is False:return next(actions)
        content=messages[-1]['content']
        if isinstance(content,list) and content[0]['text'].startswith('Review this paper-specific'):
            return {'text':'{"approved":true,"issues":[]}','usage':{}}
        return response(messages)
    return complete


def render_fixture(directory,figure,title,*,compact=False):
    import base64
    import uuid
    relative=Path('reader/overview-figures')/uuid.uuid4().hex/figure['id']
    target=Path(directory)/relative;target.parent.mkdir(parents=True)
    target.with_suffix('.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200"><text x="20" y="40">Confidence needs context</text></svg>')
    target.with_suffix('.png').write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aWQAAAABJRU5ErkJggg=='))
    return {'svg':str(relative)+'.svg','png':str(relative)+'.png','checks':{'issues':[]}}

class MarkupTests(unittest.TestCase):
    def test_overview_word_budget_does_not_reduce_blog_budget(self):
        candidate=copy.deepcopy(CANDIDATE)
        candidate['figures'][0]['html']+='<p>'+'detail '*170+'</p>'
        doc={'passages':[{'id':'p00001'}]}
        with self.assertRaisesRegex(ValueError,'180 visible words'):
            validate_candidate(candidate,doc,True)
        validate_candidate(candidate,doc,False)

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
        patch('papers.agent_overviews.prepare_reading',return_value=([{'text':'Notes [p00001].'}],[{'total_tokens':3}],{'reused':True})).start()
        self.addCleanup(patch.stopall)
        def render(directory,figure,title,*,compact=False):
            path=Path(directory)/'figure.png';path.write_bytes(b'\x89PNG\r\n\x1a\nfixture')
            return {'png':'figure.png','html':'figure.html','svg':'figure.svg','pdf':'figure.pdf','checks':{'issues':[]}}
        self.render=patch('papers.html_figures.render',side_effect=render).start()

    def replies(self,candidate=CANDIDATE):
        return [action('submit_plan',candidate=plan_for(candidate)),
                action('submit_candidate',candidate=draft_for(candidate)),
                {'text':'{"approved":true,"issues":[]}','usage':{'total_tokens':5}}]

    def trace(self):
        path=next(Path(self.doc['directory']).rglob('agent-trace.jsonl'))
        return path,[json.loads(line) for line in path.read_text().splitlines()]

    def test_both_modes_complete_after_review_without_final_answer(self):
        for visual in (True,False):
            self.provider.reset_mock();self.provider.complete.side_effect=self.replies()
            result=generate_overview(self.provider,self.doc,lambda _:None,visual=visual)
            self.assertEqual(3,self.provider.complete.call_count)
            self.assertEqual(visual,self.render.call_args.kwargs['compact'])
            self.assertEqual('smolagents-staged-html-v7',result['provenance']['prompt_revision'])
            self.assertEqual('formal',result['provenance']['overview_language'])
            self.assertTrue(result['provenance']['reviews'][-1]['approved'])
            self.assertEqual(64,len(result['provenance']['reviews'][-1]['candidate_digest']))
            self.assertIn('relationships',result['plan'])
            review=self.provider.complete.call_args.args[0][-1]['content']
            self.assertIn('Mode: Overview image.' if visual else 'Mode: Blog.',review[0]['text'])
            self.assertEqual('image_url',review[-1]['type'])

    def test_provider_review_failure_is_terminal_and_retains_rendered_draft(self):
        self.provider.complete.side_effect=self.replies()[:2]+[ProviderError('HTTP status 400. Invalid image payload')]
        with self.assertRaisesRegex(ProviderError,'400'):
            generate_overview(self.provider,self.doc,lambda _:None,visual=True)
        self.assertEqual(3,self.provider.complete.call_count)
        path,events=self.trace()
        self.assertEqual('failed',events[-1]['status'])
        self.assertIn('400',events[-1]['error'])
        self.assertTrue(path.with_name('rendered-draft.json').is_file())
        self.assertFalse(path.with_name('candidate.json').exists())

    def test_native_reasoning_survives_tool_round_but_not_next_stage(self):
        import io
        from papers.ai import Provider
        for endpoint,reasoning in [('https://api.deepseek.com/v1',{'reasoning_content':'Exact private reasoning.\n'}),
                                   ('https://openrouter.ai/api/v1',{'reasoning_details':[{'type':'reasoning.encrypted','data':'opaque','signature':'signed'}]})]:
            with self.subTest(endpoint=endpoint):
                provider=Provider({'endpoint':endpoint,'model':'fixture','overview_length':'short'},'fake-key')
                replies=iter([action('read_passages',ids=['p00001']),*self.replies()])
                requests=[]; first_assistant=None
                def complete(request,**kwargs):
                    nonlocal first_assistant
                    body=json.loads(request.data);requests.append(body)
                    reply=next(replies)
                    message={'role':'assistant','content':reply['text'],**copy.deepcopy(reasoning)}
                    if reply.get('tool_calls'):message['tool_calls']=reply['tool_calls']
                    if first_assistant is None:first_assistant=copy.deepcopy(message)
                    return io.BytesIO(json.dumps({'choices':[{'finish_reason':'tool_calls' if message.get('tool_calls') else 'stop','message':message}]}).encode())
                with patch('urllib.request.OpenerDirector.open',side_effect=complete):
                    generate_overview(provider,self.doc,lambda _:None,visual=True)
                self.assertEqual(first_assistant,next(m for m in requests[1]['messages'] if m['role']=='assistant'))
                self.assertEqual('call_read_passages',next(m for m in requests[1]['messages'] if m['role']=='tool')['tool_call_id'])
                self.assertFalse(any(m['role']=='assistant' for m in requests[2]['messages']))
                for path in Path(self.doc['directory']).rglob('*.json*'):
                    self.assertNotIn('Exact private reasoning.',path.read_text())
                    self.assertNotIn('reasoning_details',path.read_text())

    def test_repairs_start_fresh_and_approval_matches_current_revision(self):
        revised=copy.deepcopy(CANDIDATE);revised['figures'][0]['caption']='Corrected scope.'
        self.provider.complete.side_effect=self.replies()[:2]+[
            {'text':'{"approved":false,"issues":["Clarify scope"]}','usage':{}},
            action('submit_candidate',candidate=draft_for(revised)),self.replies()[-1]]
        result=generate_overview(self.provider,self.doc,lambda _:None,visual=True)
        review=result['provenance']['reviews']
        self.assertNotEqual(review[0]['candidate_digest'],review[1]['candidate_digest'])
        repair=self.provider.complete.call_args_list[3].args[0]
        self.assertFalse(any(m['role'] in ('tool','assistant') for m in repair))
        self.assertIn('Clarify scope',json.dumps(repair))
        self.assertEqual(2,self.render.call_count)

    def test_identical_rejected_candidate_stops_before_another_render_or_review(self):
        self.provider.complete.side_effect=self.replies()[:2]+[
            {'text':'{"approved":false,"issues":["Clarify scope"]}','usage':{}},
            action('submit_candidate',candidate=draft_for())]
        with self.assertRaisesRegex(ProviderError,'unchanged rejected'):
            generate_overview(self.provider,self.doc,lambda _:None,visual=True)
        self.assertEqual(4,self.provider.complete.call_count)
        self.assertEqual(1,self.render.call_count)

    def test_progressing_repairs_have_no_fixed_request_cap(self):
        replies=[self.replies()[0]]
        for i in range(8):
            candidate=copy.deepcopy(CANDIDATE);candidate['figures'][0]['caption']='Revision '+str(i)
            replies.extend([action('submit_candidate',candidate=draft_for(candidate)),
                            {'text':json.dumps({'approved':i==7,'issues':[] if i==7 else ['Clarify scope '+str(i)]}),'usage':{}}])
        self.provider.complete.side_effect=replies
        result=generate_overview(self.provider,self.doc,lambda _:None,visual=True)
        self.assertEqual(17,self.provider.complete.call_count)
        self.assertEqual(8,len(result['provenance']['reviews']))

    def test_geometry_issues_skip_review_and_invalid_markup_errors_stay_short(self):
        bad=copy.deepcopy(CANDIDATE);bad['figures'][0]['html']='<script>unsafe()</script>'
        self.provider.complete.side_effect=[self.replies()[0],action('submit_candidate',candidate=draft_for(bad)),
                                            action('submit_candidate',candidate=draft_for()),self.replies()[-1]]
        result=generate_overview(self.provider,self.doc,lambda _:None,visual=True)
        repair=json.dumps(self.provider.complete.call_args_list[2].args[0])
        self.assertIn('Unsupported figure tag: script',repair)
        self.assertNotIn('Error executing tool',repair)
        self.assertEqual(1,self.render.call_count)
        self.assertEqual(1,len(result['provenance']['reviews']))

    def test_oversized_overview_is_repaired_before_review(self):
        assets=self.render.side_effect(self.doc['directory'],CANDIDATE['figures'][0],'Test')
        oversized=copy.deepcopy(assets);oversized['checks']['issues']=['Overview is 1800px tall; maximum 960px.']
        self.render.side_effect=[oversized,assets]
        revised=copy.deepcopy(CANDIDATE);revised['figures'][0]['html']=revised['figures'][0]['html'].replace('Same input','Short input')
        self.provider.complete.side_effect=self.replies()[:2]+[action('submit_candidate',candidate=draft_for(revised)),self.replies()[-1]]
        result=generate_overview(self.provider,self.doc,lambda _:None,visual=True)
        self.assertIn('maximum 960px',json.dumps(self.provider.complete.call_args_list[2].args[0]))
        self.assertEqual(1,len(result['provenance']['reviews']))

    def test_cancellation_after_network_response_prevents_rendering(self):
        self.provider.complete.side_effect=self.replies()
        def progress(stage):
            if self.provider.complete.call_count==2: raise RuntimeError('Cancelled at checkpoint')
        with self.assertRaisesRegex(ProviderError,'Cancelled'):
            generate_overview(self.provider,self.doc,progress,visual=True)
        self.render.assert_not_called()
        self.assertEqual(2,self.provider.complete.call_count)

    def test_no_final_answer_or_review_tool_is_exposed(self):
        self.provider.complete.side_effect=self.replies()
        generate_overview(self.provider,self.doc,lambda _:None,visual=True)
        for index,submit in [(0,'submit_plan'),(1,'submit_candidate')]:
            names={t['function']['name'] for t in self.provider.complete.call_args_list[index].kwargs['tools']}
            self.assertEqual({'read_passages','diagram_reference',submit},names)
            system=self.provider.complete.call_args_list[index].args[0][0]['content']
            self.assertNotIn('only way to complete',str(system))
            self.assertIn('application controls',str(system))
        self.assertNotIn('tools',self.provider.complete.call_args.kwargs)

    def test_unexpected_finish_and_repeated_lookup_terminate(self):
        for replies in ([action('final_answer',answer='Done')],
                        [action('read_passages',ids=['p00001'])]*2,
                        [{'text':'Done without submission','usage':{}}]):
            self.provider.reset_mock();self.provider.complete.side_effect=replies
            with self.assertRaises(ProviderError):generate_overview(self.provider,self.doc,lambda _:None,visual=True)
            self.assertEqual(len(replies),self.provider.complete.call_count)
        self.render.assert_not_called()

    def test_trace_keeps_call_diagnostics_without_replaying_request_bodies(self):
        self.provider.complete.side_effect=[action('read_passages',ids=['p00001']),*self.replies()]
        generate_overview(self.provider,self.doc,lambda _:None,visual=True)
        path,events=self.trace()
        self.assertEqual(4,len(events))
        self.assertFalse(path.with_name('messages').exists())
        for event in events:
            self.assertIn('elapsed_seconds',event)
            self.assertGreater(event['input_chars'],0)
            self.assertNotIn('messages',event)
            self.assertNotIn('message_ids',event)


    def test_effort_is_low_for_deepseek_authoring_only_and_gemini_stays_low(self):
        for endpoint,model in [('https://api.deepseek.com','deepseek-flash'),
                               ('https://generativelanguage.googleapis.com/v1beta/openai','gemini-3.8-flash')]:
            self.provider.reset_mock();self.provider.settings.update(endpoint=endpoint,model=model)
            self.provider.complete.side_effect=self.replies()
            generate_overview(self.provider,self.doc,lambda _:None,visual=True)
            calls=self.provider.complete.call_args_list
            if 'deepseek' in endpoint:
                self.assertEqual('low',calls[0].kwargs['reasoning_effort'])
                self.assertEqual('low',calls[1].kwargs['reasoning_effort'])
                self.assertNotIn('reasoning_effort',calls[2].kwargs)
            else:
                self.assertTrue(all(c.kwargs['gemini_thinking_level']=='low' for c in calls))

    def saved_overview(self):
        from papers.library import document_digest
        figure=copy.deepcopy(CANDIDATE['figures'][0]);figure['source_html']=figure['html']
        for ext in ('html','svg','png','pdf'):
            name='saved-figure.'+ext
            (Path(self.doc['directory'])/name).write_text('<header></header>'+figure['source_html']+'<footer></footer>' if ext=='html' else 'fixture')
            figure[ext]=name
        figure['checks']={'issues':[]}
        return {'figures':[figure],'explanation':{'question':'Which methods share inputs?'},
                'provenance':{'document_digest':document_digest(self.doc),'created_at':'saved-time','reviews':[{'approved':True,'issues':[]}]}}

    def test_blog_adapts_reference_and_rejects_unchanged_copy(self):
        overview=self.saved_overview();before=copy.deepcopy(overview)
        revised=copy.deepcopy(CANDIDATE);revised['figures'][0]['html']=revised['figures'][0]['html'].replace('Same input','Focused example')
        self.provider.complete.side_effect=[self.replies()[0],action('read_overview_figure',reference='overview_fig1'),
            action('submit_candidate',candidate=draft_for()),action('submit_candidate',candidate=draft_for(revised)),self.replies()[-1]]
        result=generate_overview(self.provider,self.doc,lambda _:None,image_overview=overview)
        self.assertEqual(overview,before)
        self.assertEqual(1,self.render.call_count)
        self.assertEqual('saved-time',result['provenance']['overview_basis']['created_at'])
        self.assertIn('reference only',json.dumps(self.provider.complete.call_args_list[3].args[0]))

    def test_saved_reference_compatibility_and_missing_assets(self):
        overview=self.saved_overview();del overview['figures'][0]['source_html']
        self.assertIn('overview_fig1',reusable_overview_figures(self.doc,overview))
        overview=self.saved_overview();overview['figures'][0]['source_html']+='<p>'+'detail '*170+'</p>'
        self.assertIn('overview_fig1',reusable_overview_figures(self.doc,overview))
        overview['figures'][0]['png']='missing.png'
        self.assertEqual({},reusable_overview_figures(self.doc,overview))

    def test_plain_model_receives_no_images(self):
        self.provider.settings['overview_vision']=False
        self.provider.complete.side_effect=self.replies()
        result=generate_overview(self.provider,self.doc,lambda _:None,visual=True)
        self.assertFalse(result['provenance']['vision_review'])
        self.assertTrue(all(p['type']=='text' for p in self.provider.complete.call_args.args[0][-1]['content']))
