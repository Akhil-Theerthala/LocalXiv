"""Exercise the real smolagents loop with scripted compatible-provider responses."""
import copy
import hashlib
import importlib.util
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from papers.ai import generate_overview, ProviderError
from papers.agent_overviews import validate_candidate, reusable_overview_figures
from papers import html_figures
from papers.html_figures import sanitize

CANDIDATE={'paper_type':'evaluation','question':'How do the methods compare?',
 'contribution':'The paper compares two methods.','finding':'Their ranking depends on the setting.',
 'limitation':'Only these tasks were evaluated.','passages':['p00001'],
 'text':'The paper compares methods [p00001].\n\n{{figure:fig1}}\n\nThe figure shows their shared input [p00001].',
 'figures':[{'id':'fig1','title':'Compare the same input','paper_connection':'This paper compares two approaches.',
 'caption':'Only these tasks were evaluated.','illustrative':True,'passages':['p00001'],
 'svg':'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 200"><text x="20" y="60" font-size="24">Same input</text></svg>',
 'html':'<svg viewBox="0 0 800 200"><text x="20" y="60" font-size="24">Same input</text></svg>'}]}


PANEL_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 360 200" '
             'font-family="Arial, sans-serif" font-size="24" fill="#243b32">'
             '<rect id="box" x="20" y="20" width="320" height="60" rx="8" fill="#dce8cf"/>'
             '<text id="label" x="36" y="58" font-size="24">Step label</text></svg>')


def draft_submission(candidate=CANDIDATE, *, panels=2):
    leaves=[{'id':f'p{index+1}','title':f'Panel {index+1}',
             'brief':f'Explain part {index+1} of the compared methods for the reader.',
             'shape':'wide','group':'','steps':[f'Step {index+1}'],'passages':list(candidate['passages'])}
            for index in range(panels)]
    return {'plan_digest':plan_digest(candidate),'title':'Compare the same input',
            'paper_connection':'This paper compares two approaches.',
            'caption':'Only these tasks were evaluated.','groups':[],'panels':leaves,
            }


def panel_reply(identifier='p1', text='Step label'):
    return action('submit_panel', candidate={'panel_id':identifier,'svg':PANEL_SVG.replace('Step label', text)})


def plan_for(candidate=CANDIDATE):
    return {'paper_type':candidate['paper_type'],
            **{key:{'text':candidate[key],'passages':candidate['passages']} for key in ('question','contribution','finding','limitation')},
            'visual_focus':'Follow the shared input through the compared operations.',
            'relationships':[{'source':'Input','target':'Methods','relationship':'Same input for comparison','passages':candidate['passages']}]}


def draft_for(candidate=CANDIDATE, *, visual=True):
    candidate=copy.deepcopy(candidate)
    for figure in candidate['figures']:figure.pop('html' if visual else 'svg',None)
    if visual:
        candidate['text']=''
    return {'plan':plan_for(candidate),'text':candidate['text'],'figures':copy.deepcopy(candidate['figures'])}


def visual_candidate(candidate=CANDIDATE):
    value=copy.deepcopy(candidate)
    value['text']=''
    return value


def plan_digest(candidate=CANDIDATE):
    return hashlib.sha256(json.dumps(plan_for(candidate),sort_keys=True,separators=(',',':')).encode()).hexdigest()


def selection_for(section='s0002'):
    return {'paper_type':'evaluation','focus':'Compare the methods and retain the scope.',
            'section_ids':[section],'passage_ids':[],'figure_ids':[]}


def author_for(candidate=CANDIDATE):
    value=draft_for(candidate)
    return {'plan_digest':plan_digest(candidate),'text':value['text'],'figures':value['figures']}


def action(name,**arguments):
    return {'text':'','tool_calls':[{'id':'call_'+name,'type':'function',
            'function':{'name':name,'arguments':json.dumps(arguments)}}],'usage':{'total_tokens':10}}


def scripted_provider(candidate):
    """Shared fixture for HTTP/export integration tests of the new tool protocol."""
    from tests.overview_fixture import response
    submitted=set()
    def complete(messages,**kwargs):
        names={item['function']['name'] for item in kwargs.get('tools',[])}
        if kwargs.get('json_object') is False:
            if 'submit_selection' in names:
                submitted.add('selection')
                return action('submit_selection',candidate={'paper_type':candidate['paper_type'],
                    'focus':'Explain the contribution and qualified finding.','section_ids':[],
                    'passage_ids':candidate['passages'],'figure_ids':[]})
            if 'submit_plan' in names:
                submitted.add('plan')
                return action('submit_plan',candidate=plan_for(candidate))
            if 'submit_draft' in names:
                return action('submit_draft',candidate=draft_submission(candidate))
            if 'submit_panel' in names:
                text=json.dumps(messages)
                match=re.search(r'\\"id\\": ?\\"(p[0-9]+)\\"',text)
                return panel_reply(match.group(1) if match else 'p1')
            return action('submit_candidate',candidate=author_for(candidate) if 'plan_digest' in json.dumps(kwargs.get('tools'))
                          else draft_for(candidate,visual=False))
        content=messages[-1]['content']
        text=content[0].get('text','') if isinstance(content,list) else content
        if isinstance(text,str) and 'accepted narrative' in text:
            return {'text':'{"action":"verdict","approved":true,"issues":[]}','usage':{}}
        return response(messages)
    return complete


def render_fixture(directory,figure,title,*,compact=False):
    import base64
    import uuid
    relative=Path('reader/overview-figures')/uuid.uuid4().hex/figure['id']
    target=Path(directory)/relative;target.parent.mkdir(parents=True)
    target.with_suffix('.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200"><text x="20" y="40">Confidence needs context</text></svg>')
    target.with_suffix('.png').write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aWQAAAABJRU5ErkJggg=='))
    assets={'svg':str(relative)+'.svg','png':str(relative)+'.png','checks':{'issues':[]}}
    if figure.get('source_svg'):
        target.with_suffix('.source.svg').write_text(figure['source_svg'])
        assets['svg_source']=str(relative)+'.source.svg'
    return assets


class MarkupTests(unittest.TestCase):
    def test_svg_word_budget_is_independent_of_shell_metadata_and_blog_budget(self):
        doc={'passages':[{'id':'p00001'}]}
        for count in (181, 400, 600):
            candidate=visual_candidate()
            candidate['figures'][0]['svg']=(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 200">'
                '<desc>' + ('hidden ' * 700) + '</desc>'
                '<text x="20" y="60" font-size="24">' + ('word ' * count) + '</text></svg>'
            )
            validate_candidate(candidate,doc,True)
        candidate=visual_candidate()
        candidate['figures'][0]['svg']=(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 200">'
            '<text x="20" y="60" font-size="24">' + ('word ' * 601) + '</text></svg>'
        )
        with self.assertRaisesRegex(ValueError,'601 visible SVG words; limit 600'):
            validate_candidate(candidate,doc,True)
        validate_candidate(CANDIDATE,doc,False)

    def test_overview_starts_with_a_visual_and_limits_prose(self):
        doc={'passages':[{'id':'p00001'}]}
        architecture=visual_candidate();architecture['paper_type']='architecture'
        validate_candidate(architecture,doc,True)
        for field,limit in (('title',12),('paper_connection',30),('caption',45)):
            bad=visual_candidate();bad['figures'][0][field]='word '*(limit+1)
            with self.assertRaises(ValueError):validate_candidate(bad,doc,True)
        bad=visual_candidate()
        bad['figures'][0]['svg']='<p>Long introduction</p>'+bad['figures'][0]['svg']
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
        reader=Path(tmp.name)/'reader';reader.mkdir()
        (reader/'paper.xhtml').write_text('''<html><body><section id="abstract"><h1>Abstract</h1>
          <p id="abstract-body">The paper compares two methods.</p></section>
          <section><h1>1 Evaluation</h1><p id="body">Two methods were evaluated. Ranking varies by task.</p></section></body></html>''')
        self.doc={'directory':tmp.name,'title':'Evaluation paper','passages':[
            {'id':'p00000','section':'Abstract','text':'The paper compares two methods.','href':'reader/paper.xhtml#abstract-body'},
            {'id':'p00001','section':'1 Evaluation','text':'Two methods were evaluated. Ranking varies by task.','href':'reader/paper.xhtml#body'}]}
        self.provider=Mock(settings={'model':'fixture','overview_language':'formal','overview_length':'short','overview_vision':True})
        self.addCleanup(patch.stopall)
        def render(directory,figure,title,*,compact=False):
            root=Path(directory);path=root/'figure.png';path.write_bytes(b'\x89PNG\r\n\x1a\nfixture')
            assets={'png':'figure.png','html':'figure.html','svg':'figure.svg','pdf':'figure.pdf','checks':{'issues':[]}}
            if figure.get('source_svg'):
                (root/'figure.source.svg').write_text(figure['source_svg'])
                assets['svg_source']='figure.source.svg'
            return assets
        self.render=patch('papers.html_figures.render',side_effect=render).start()

    def replies(self,candidate=CANDIDATE, *, visual=True):
        if not visual:
            return [action('submit_selection',candidate=selection_for()),
                    action('submit_plan',candidate=plan_for(candidate)),
                    action('submit_candidate',candidate=draft_for(candidate,visual=False)),
                    {'text':'{"action":"verdict","approved":true,"issues":[]}','usage':{'total_tokens':5}}]
        return [action('submit_selection',candidate=selection_for()),
                action('submit_plan',candidate=plan_for(candidate)),
                action('submit_draft',candidate=draft_submission(candidate)),
                {'text':'{"action":"verdict","approved":true,"issues":[]}','usage':{'total_tokens':5}},
                panel_reply('p1'),panel_reply('p2'),
                {'text':'{"action":"verdict","approved":true,"issues":[]}','usage':{'total_tokens':5}}]

    VISUAL_STAGES=['selection','narrative','draft','draft_review','panel','panel','review']

    def authoring(self):
        """Everything the visual path does between the accepted narrative and the figure review."""
        return self.replies()[2:6]

    def shell_reply(self, *, title=None, paper_connection=None, caption=None):
        figure=CANDIDATE['figures'][0]
        return action('submit_shell',candidate={
            'title':figure['title'] if title is None else title,
            'paper_connection':figure['paper_connection'] if paper_connection is None else paper_connection,
            'caption':figure['caption'] if caption is None else caption})

    def test_context_checkpoint_round_trip_rejects_stale_identity(self):
        from papers.agent_overviews import write_generation_context, load_generation_context
        path=Path(self.doc['directory'])/'generation_context.json'
        context={'context_revision':'generation-context-v1','document_digest':'doc',
                 'source_digest':'source','provider':{'model':'fixture','endpoint':'https://example.test','vision':False},
                 'prompt_revision':'prompt','schema_revision':'schema','stage':'repair',
                 'selection':selection_for(),'evidence':{'passages':[{'id':'p00001','text':'Evidence'}],'images':[]},
                 'accepted_plan':plan_for(),'plan_digest':plan_digest(),'current_candidate':CANDIDATE,
                 'candidate_digest':'candidate','issues':[{'id':'issue-one'}],
                 'repair_decisions':[],'rejected_content_digests':['old'],'no_progress':{'issue-one':1}}
        write_generation_context(path,context)
        self.assertEqual(context,load_generation_context(path,document_digest='doc',source_digest='source',
            provider=context['provider'],prompt_revision='prompt',schema_revision='schema'))
        with self.assertRaises(ValueError):
            load_generation_context(path,document_digest='changed',source_digest='source',
                provider=context['provider'],prompt_revision='prompt',schema_revision='schema')

    def trace(self):
        path=next(Path(self.doc['directory']).rglob('agent-trace.jsonl'))
        return path,[json.loads(line) for line in path.read_text().splitlines()]

    def test_blog_completes_after_a_structured_review(self):
        self.provider.complete.side_effect=self.replies(visual=False)
        result=generate_overview(self.provider,self.doc,lambda _:None)
        self.assertEqual(4,self.provider.complete.call_count)
        self.assertEqual('smolagents-selective-blog-v3',result['provenance']['prompt_revision'])
        self.assertEqual('formal',result['provenance']['overview_language'])
        self.assertTrue(result['provenance']['reviews'][-1]['approved'])
        self.assertEqual(64,len(result['provenance']['reviews'][-1]['candidate_digest']))
        review=self.provider.complete.call_args.args[0][-1]['content']
        self.assertIn('<accepted_narrative>',review[0]['text'])
        self.assertIn('relationships',review[0]['text'])

    def test_blog_preferences_reach_every_stage_and_survive_repair(self):
        from papers.overview import LANGUAGES, LENGTHS

        revised = copy.deepcopy(CANDIDATE)
        revised['figures'][0]['caption'] = 'Corrected scope for these tasks.'
        stages = ('selection', 'narrative', 'author', 'review', 'repair', 'review')
        for language, length in (('casual', 'short'), ('semi-formal', 'medium'), ('formal', 'large')):
            with self.subTest(language=language, length=length):
                self.provider.reset_mock()
                self.provider.settings.update(overview_language=language, overview_length=length)
                self.provider.complete.side_effect = self.replies(visual=False)[:3] + [
                    {'text': json.dumps(self.review_issue()), 'usage': {}},
                    action('submit_candidate', candidate=draft_for(revised, visual=False)),
                    self.replies(visual=False)[-1],
                ]
                result = generate_overview(self.provider, self.doc, lambda _: None, visual=False)
                self.assertEqual(len(stages), self.provider.complete.call_count)
                for stage, call in zip(stages, self.provider.complete.call_args_list):
                    payload = json.dumps(call.args[0], ensure_ascii=False)
                    self.assertIn(LANGUAGES[language], payload, stage)
                    self.assertIn('Requested Blog length: ' + LENGTHS[length], payload, stage)
                    self.assertNotIn('within the Overview scope', payload, stage)
                self.assertEqual(language, result['provenance']['overview_language'])
                self.assertEqual(length, result['provenance']['overview_length'])

    def initial_compiled(self,candidate=CANDIDATE):
        from papers.explanation import expand_candidate
        value=expand_candidate(draft_for(candidate),{'passages':[{'id':'p00001'}]})
        value['figures'][0]['source_svg']=html_figures.normalize_svg(value['figures'][0].pop('svg'))
        return value

    def review_issue(self,message='Clarify the evaluated scope.'):
        return {'action':'verdict','approved':False,'issues':[{
            'category':'scope','path':'figures[0].caption','message':message,'passages':['p00001']}]}

    def repair_submission(self,current,revised,issue):
        from papers.agent_overviews import candidate_digest, _issue_id
        return {'base_digest':candidate_digest(current),
                'decision':{'action':'repair_figure','addresses':[_issue_id(dict(issue,code='review'))],
                    'change':'Clarify the figure caption.','reason':'The qualification must be visible.',
                    'preserves':['plan.visual_focus'],'evidence':['p00001']},
                'figure':draft_for(revised)['figures'][0]}

    def test_visible_passage_id_is_located_for_the_repair(self):
        from papers.agent_overviews import validate_candidate, FigureValidationError
        base=self.initial_compiled()
        for field,expected in (('paper_connection','figures[0].paper_connection'),
                               ('caption','figures[0].caption')):
            value=copy.deepcopy(base)
            value['figures'][0][field]='A claim supported by [p00001].'
            with self.subTest(field=field):
                with self.assertRaises(FigureValidationError) as caught:
                    validate_candidate(value,{'passages':[{'id':'p00001'}]},True)
                self.assertEqual(expected,caught.exception.issue['path'])
                self.assertIn('Passage ID',caught.exception.issue['message'])
        value=copy.deepcopy(base)
        value['figures'][0]['source_svg']=value['figures'][0]['source_svg'].replace('Same input','Same input [p00001]')
        with self.assertRaises(FigureValidationError) as caught:
            validate_candidate(value,{'passages':[{'id':'p00001'}]},True)
        self.assertTrue(caught.exception.issue['path'].startswith('figures[0].svg'))

    def test_blog_author_cannot_silently_replace_accepted_plan(self):
        changed = draft_for(visual=False)
        changed['plan']['visual_focus'] = 'An unapproved change of story.'
        self.provider.complete.side_effect = self.replies(visual=False)[:2] + [
            action('submit_candidate', candidate=changed), *self.replies(visual=False)[2:]]
        result = generate_overview(self.provider, self.doc, lambda _: None)
        self.assertEqual(plan_for(), result['plan'])
        self.assertEqual(5, self.provider.complete.call_count)

    def test_blog_can_explicitly_revise_narrative_before_and_after_authoring(self):
        from papers.agent_overviews import candidate_digest
        from papers.explanation import expand_candidate
        for before_authoring in (True, False):
            with self.subTest(before_authoring=before_authoring):
                revised = draft_for(visual=False)
                revised['plan']['visual_focus'] = 'Compare the operations before explaining the task-specific ranking.'
                if before_authoring:
                    responses = self.replies(visual=False)[:2] + [
                        action('request_narrative_revision', reason='Explain the comparison first.',
                               passage_ids=['p00001']),
                        action('submit_plan', candidate=revised['plan']),
                        action('submit_candidate', candidate=revised)]
                else:
                    current = expand_candidate(draft_for(visual=False), self.doc)
                    submission = self.repair_submission(current, CANDIDATE, self.review_issue()['issues'][0])
                    submission.pop('figure')
                    submission['decision']['action'] = 'revise_narrative'
                    submission['decision']['preserves'] = ['plan.finding']
                    submission['candidate'] = revised
                    responses = self.replies(visual=False)[:3] + [
                        {'text': json.dumps(self.review_issue()), 'usage': {}},
                        action('submit_revision', candidate=submission)]
                self.provider.complete.reset_mock()
                self.provider.complete.side_effect = responses + [self.replies()[-1]]
                result = generate_overview(self.provider, self.doc, lambda _: None)
                self.assertEqual(revised['plan'], result['plan'])
                self.assertEqual(6, self.provider.complete.call_count)
                expected = candidate_digest(expand_candidate(revised, self.doc))
                self.assertEqual(expected, result['provenance']['reviews'][-1]['candidate_digest'])

    def test_no_progress_uses_measurements_for_mechanical_issues(self):
        from papers.agent_overviews import _update_no_progress, _with_issue_ids
        issue=lambda actual:{'id':'same','code':'word_budget','path':'figures[0].caption',
                             'message':'too long','actual':actual,'limit':600}
        counters=_update_no_progress([issue(820)],[issue(800)],{'same':1})
        self.assertEqual(0,counters['same'])
        counters=_update_no_progress([issue(800)],[issue(800)],counters,
            before_candidate={'figures':[{'caption':'old'}]},after_candidate={'figures':[{'caption':'new'}]})
        self.assertEqual(1,counters['same'])
        counters=_update_no_progress([issue(800)],[issue(800)],counters,evidence_changed=True)
        self.assertEqual(2,counters['same'])

        height=lambda actual=None:_with_issue_ids([{
            'code':'layout_fit','constraint':'max_height','path':'figures[0]',
            'message':'Measured height changed.',**({'actual':actual,'limit':960} if actual is not None else {})}])[0]
        old,new=height(1100),height(1150)
        counters=_update_no_progress([old],[new],{old['id']:0},
            before_candidate={'figures':[{'caption':'old'}]},after_candidate={'figures':[{'caption':'new'}]})
        self.assertEqual(1,counters[old['id']])
        improved=height(1050)
        counters=_update_no_progress([new],[improved],counters)
        self.assertEqual(0,counters[old['id']])
        unavailable=height()
        counters=_update_no_progress([improved],[unavailable],counters)
        self.assertEqual(1,counters[old['id']])

    def test_no_progress_keeps_unavailable_height_separate_from_width(self):
        from papers.agent_overviews import _update_no_progress, _with_issue_ids
        height=_with_issue_ids([{'code':'layout_fit','constraint':'max_height','path':'figures[0]',
            'message':'Tall.','actual':1100,'limit':960}])[0]
        width=_with_issue_ids([{'code':'layout_fit','constraint':'min_width','path':'figures[0].scene.rows[0]',
            'message':'Wide.','actual':939,'limit':800}])[0]

        counters=_update_no_progress([height],[width],{height['id']:1})
        self.assertEqual(1,counters[height['id']])
        self.assertEqual(0,counters[width['id']])
        counters=_update_no_progress([width],[height],counters)
        self.assertEqual(1,counters[height['id']])
        self.assertNotIn(width['id'],counters)

    def test_no_progress_keeps_semantic_content_and_evidence_handling(self):
        from papers.agent_overviews import _update_no_progress
        issue={'id':'review','code':'review','path':'figures[0].caption','message':'Clarify scope.'}
        counters=_update_no_progress([issue],[issue],{'review':1},
            before_candidate={'figures':[{'caption':'old'}]},after_candidate={'figures':[{'caption':'new'}]})
        self.assertEqual(0,counters['review'])
        counters=_update_no_progress([issue],[issue],{'review':1},evidence_changed=True)
        self.assertEqual(0,counters['review'])

    def test_layout_issues_have_distinct_stable_ids(self):
        from papers.agent_overviews import _with_issue_ids
        first=_with_issue_ids([{'code':'layout_fit','constraint':'max_height','path':'figures[0]',
            'message':'Overview is 1100px tall.','actual':1100,'limit':960}])[0]
        changed=_with_issue_ids([{'code':'layout_fit','constraint':'max_height','path':'figures[0]',
            'message':'Overview is now 1150px tall.','actual':1150,'limit':960}])[0]
        width=_with_issue_ids([{'code':'layout_fit','constraint':'min_width','path':'figures[0]',
            'message':'The row is wide.','actual':939,'limit':800}])[0]
        self.assertEqual(first['id'],changed['id'])
        self.assertNotEqual(first['id'],width['id'])

    def test_native_issue_details_keep_independent_failures_and_measurements(self):
        from papers.agent_overviews import _native_issue_messages, _native_issues
        checks={'height':1200,'issues':['Small text at 640px reading width: label',
            'Overview is 1200px tall; maximum 960px including heading and caption.'],
            'issue_details':[
                {'code':'text_too_small','path':'#label','message':'Small text at 640px reading width: label',
                 'constraint':'minimum_displayed_font_px','actual':11.8,'limit':14},
                {'code':'layout_fit','path':'figure-page','message':'Overview is 1200px tall; maximum 960px including heading and caption.',
                 'constraint':'maximum_page_height_px','actual':1200,'limit':960}]}
        self.assertEqual(checks['issues'],_native_issue_messages(checks,structured=True))
        self.assertEqual(checks['issues'],_native_issue_messages(checks,structured=False))
        details=_native_issues(checks,'figures[0]',structured=True)
        self.assertEqual(['text_too_small','layout_fit'],[item['code'] for item in details])
        self.assertEqual('figures[0].svg#label',details[0]['path'])
        self.assertEqual(11.8,details[0]['actual'])

    def test_element_renaming_does_not_reset_mechanical_no_progress(self):
        from papers.agent_overviews import _update_no_progress, _with_issue_ids
        before=_with_issue_ids([{'code':'text_too_small','path':'figures[0].svg#old',
            'message':'Small.','constraint':'minimum_displayed_font_px','actual':11.8,'limit':14}])
        after=_with_issue_ids([{'code':'text_too_small','path':'figures[0].svg#renamed',
            'message':'Still small.','constraint':'minimum_displayed_font_px','actual':11.8,'limit':14}])
        counters=_update_no_progress(before,after,{before[0]['id']:1})
        self.assertEqual(2,counters[after[0]['id']])

    def test_evidence_merge_deduplicates_structured_unavailable_images(self):
        from papers.agent_overviews import _merge_evidence
        document={'passages':[{'id':'p00001'},{'id':'p00002'}]}
        unavailable={'figure_id':'f0001','reason':'missing image asset'}
        current={'passages':[{'id':'p00001'}],'images':[],
                 'coverage':{'unavailable_images':[unavailable]}}
        added={'document_digest':'digest','passages':[{'id':'p00002'}],'images':[],
               'coverage':{'unavailable_images':[copy.deepcopy(unavailable)]}}
        merged=_merge_evidence(current,added,document)
        self.assertEqual([unavailable],merged['coverage']['unavailable_images'])

    def saved_overview(self):
        from papers.library import document_digest
        figure=copy.deepcopy(CANDIDATE['figures'][0]);figure['source_html']=figure['html']
        figure['scene']={'historical':'inert metadata'}
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
        self.provider.complete.side_effect=[self.replies()[0],self.replies()[1],
            action('read_overview_figure',reference='overview_fig1'),
            action('submit_candidate',candidate=draft_for(visual=False)),
            action('submit_candidate',candidate=draft_for(revised,visual=False)),self.replies()[-1]]
        result=generate_overview(self.provider,self.doc,lambda _:None,image_overview=overview)
        self.assertEqual(overview,before)
        self.assertEqual(1,self.render.call_count)
        self.assertEqual('saved-time',result['provenance']['overview_basis']['created_at'])
        self.assertIn('reference only',json.dumps(self.provider.complete.call_args_list[4].args[0]))

    def test_saved_reference_compatibility_and_missing_assets(self):
        overview=self.saved_overview();del overview['figures'][0]['source_html']
        self.assertIn('overview_fig1',reusable_overview_figures(self.doc,overview))
        overview=self.saved_overview();overview['figures'][0]['source_html']+='<p>'+'detail '*170+'</p>'
        self.assertIn('overview_fig1',reusable_overview_figures(self.doc,overview))
        overview['figures'][0]['png']='missing.png'
        self.assertEqual({},reusable_overview_figures(self.doc,overview))

    def test_new_svg_reference_uses_new_ceiling_and_requires_genuine_source(self):
        overview=self.saved_overview();figure=overview['figures'][0]
        figure.pop('source_html')
        source=('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 880 600">'
                '<text x="20" y="40" font-size="24">'+('word '*400)+'</text></svg>')
        source_name='saved-figure.source.svg'
        (Path(self.doc['directory'])/source_name).write_text(source)
        figure['svg_source']=source_name
        overview['provenance']['svg_profile_revision']=html_figures.SVG_PROFILE_REVISION
        reused=reusable_overview_figures(self.doc,overview)
        self.assertEqual('svg',reused['overview_fig1']['spec']['source_format'])
        self.assertEqual(400,len(html_figures.svg_visible_text(
            reused['overview_fig1']['spec']['svg'])[0][1].split()))

        figure['svg_source']='saved-figure.svg'
        self.assertEqual({},reusable_overview_figures(self.doc,overview))
        figure['svg_source']=source_name;figure['source_svg']=source.replace('word ','changed ',1)
        self.assertEqual({},reusable_overview_figures(self.doc,overview))

    def test_old_overview_with_mixed_pdf_bibliography_is_not_reused(self):
        from papers.reading import REVISION
        self.doc['format']='pdf'
        self.doc['passages'][1]['text']+='\nReferences\nBibliography entry'
        overview=self.saved_overview()
        self.assertEqual({},reusable_overview_figures(self.doc,overview))
        overview['provenance']['reading']={'revision':REVISION}
        self.assertIn('overview_fig1',reusable_overview_figures(self.doc,overview))

class PanelWorkflowReferenceTests(unittest.TestCase):
    """Blog accepts a panel-workflow overview as a drawing reference, never as a review."""

    def setUp(self):
        from papers.library import document_digest
        from papers.overview_workflow import PANEL_WORKFLOW, panel_digest
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.doc = {'arxiv_id': 'one', 'title': 'Paper', 'format': 'epub', 'directory': str(self.directory),
                    'source_digest': 'digest',
                    'passages': [{'id': 'p00001', 'section': 'Method', 'text': 'Retained method text.'}]}
        run = self.directory / 'reader' / 'overview-figures' / 'run'
        run.mkdir(parents=True)
        source = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1400 2200" font-size="18">'
                  '<rect x="20" y="20" width="1360" height="200" rx="10" fill="#dce8cf"/>'
                  '<text x="40" y="130">A free-sized panel</text></svg>')
        (run / 'fig1.source.svg').write_text(source)
        (run / 'fig1.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
        (run / 'fig1.png').write_bytes(b'\x89PNG\r\n\x1a\nfixture')
        (run / 'fig1.html').write_text('<html></html>')
        (run / 'fig1.pdf').write_bytes(b'%PDF-1.4 fixture')
        self.narrative = {'paper_type': 'method', 'visual_focus': 'One panel.',
                          'question': {'text': 'How?', 'passages': ['p00001']},
                          'contribution': {'text': 'Like this.', 'passages': ['p00001']},
                          'finding': {'text': 'It works.', 'passages': ['p00001']},
                          'limitation': {'text': 'One dataset.', 'passages': ['p00001']},
                          'relationships': [{'source': 'a', 'target': 'b', 'relationship': 'r',
                                             'passages': ['p00001']}]}
        self.overview = {
            'text': '{{figure:fig1}}', 'plan': self.narrative,
            'figures': [{'id': 'fig1', 'title': 'Overview', 'paper_connection': 'One figure.',
                         'caption': 'Free-sized.', 'illustrative': False, 'passages': ['p00001'],
                         'html': 'reader/overview-figures/run/fig1.html',
                         'svg': 'reader/overview-figures/run/fig1.svg',
                         'png': 'reader/overview-figures/run/fig1.png',
                         'pdf': 'reader/overview-figures/run/fig1.pdf',
                         'svg_source': 'reader/overview-figures/run/fig1.source.svg',
                         'dimensions': {'width': 1400, 'height': 2200},
                         'panels': [{'id': 'p1', 'title': 'One', 'x': 20.0, 'y': 50.0,
                                     'width': 1360.0, 'height': 200.0, 'text': 'The accepted content.'}],
                         'checks': {'issue_details': []}}],
            'provenance': {'workflow': PANEL_WORKFLOW, 'document_digest': document_digest(self.doc),
                           'narrative_digest': panel_digest(self.narrative),
                           'figure_digests': {'fig1': panel_digest((run / 'fig1.source.svg').read_text())},
                           'reviews': [], 'created_at': 'now'}}

    def test_a_clean_panel_workflow_artifact_is_reused_as_a_drawing_reference(self):
        reused = reusable_overview_figures(self.doc, self.overview)
        self.assertIn('overview_fig1', reused)
        spec = reused['overview_fig1']['spec']
        self.assertEqual('svg', spec['source_format'])
        self.assertIn('A free-sized panel', spec['svg'])
        self.assertEqual(set(['html', 'svg', 'png', 'pdf']),
                         set(reused['overview_fig1']['assets']) - {'checks'})

    def test_review_state_geometry_and_identity_must_still_match(self):
        for name, change in [
                ('changed narrative', lambda value: value['plan'].update({'finding': {'text': 'Changed.'}})),
                ('edited source', lambda value: (self.directory / 'reader' / 'overview-figures' / 'run'
                                                 / 'fig1.source.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"/>')),
                ('failed local check', lambda value: value['figures'][0]['checks'].update(
                    {'issue_details': [{'code': 'text_too_small', 'message': 'too small'}]})),
                ('missing asset', lambda value: value['figures'][0].update({'png': 'reader/missing.png'})),
                ('other document', lambda value: value['provenance'].update({'document_digest': 'other'})),
                ('no workflow marker', lambda value: value['provenance'].pop('workflow'))]:
            with self.subTest(name=name):
                value = copy.deepcopy(self.overview)
                change(value)
                self.assertEqual({}, reusable_overview_figures(self.doc, value))
