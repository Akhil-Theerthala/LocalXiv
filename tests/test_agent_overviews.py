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
from papers.agent_overviews import (candidate_digest, remove_omitted_markers,
                                    validate_candidate, reusable_overview_figures)
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

TEXT_TWO_FIGURES=('The paper compares two methods [p00001].\n\n'
                  'Follow the blue branch in the diagram below [p00001].\n\n{{figure:fig1}}\n\n'
                  'The second drawing shows the same input [p00001].\n\n{{figure:fig2}}\n\n'
                  'Only these tasks were evaluated [p00001].')

TEXT_ONE_FIGURE=('The paper compares methods [p00001].\n\n'
                 'Follow the blue branch in the diagram below [p00001].\n\n{{figure:fig1}}\n\n'
                 'Only these tasks were evaluated [p00001].')

PLAN_FOR_ORIGINAL='Compare the operations before explaining the task-specific ranking.'

PANEL_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 360 200" '
             'font-family="Arial, sans-serif" font-size="24" fill="#243b32">'
             '<rect id="box" x="20" y="20" width="320" height="60" rx="8" fill="#dce8cf"/>'
             '<text id="label" x="36" y="58" font-size="24">Step label</text></svg>')


def blog_brief(identifier='fig1', *, passages=('p00001',), illustration='Same input',
               title='Compare the same input'):
    """One focused Blog drawing brief matching BLOG_BRIEF_SCHEMA."""
    return {
        'id': identifier,
        'title': title,
        'paper_connection': 'This paper compares two approaches.',
        'caption': 'Only these tasks were evaluated.',
        'illustrative': True,
        'passages': list(passages),
        'purpose': 'What do the two approaches do with the same input?',
        'entry_context': ['The prose has introduced both approaches.'],
        'exit_state': 'The reader can follow the shared input through both paths.',
        'construction': 'comparison',
        'layout_intent': 'Input at left; the two approaches stacked in the middle; their outputs at right.',
        'content': [{'text': illustration, 'kind': 'label', 'passages': list(passages)}],
        'exact_text': [illustration],
        'illustrative_values': [],
    }


def blog_svg(text='Same input'):
    """A panel-profile SVG carrying one brief's declared exact label."""
    return blog_svg_labels([text])


def blog_svg_labels(labels):
    """A panel-profile SVG carrying every declared exact label, in reading order."""
    rows=''.join('<text id="label%d" x="40" y="%d" font-size="18">%s</text>'
                 % (index,60+30*index,text) for index,text in enumerate(labels))
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 200" '
            'font-family="Arial, sans-serif" font-size="18" fill="#243b32">'
            '<rect id="box" x="20" y="20" width="600" height="' + str(40+30*len(labels)) + '" '
            'rx="8" fill="#dce8cf"/>' + rows + '</svg>')


def plan_for(candidate=CANDIDATE):
    return {'paper_type':candidate['paper_type'],
            **{key:{'text':candidate[key],'passages':candidate['passages']} for key in ('question','contribution','finding','limitation')},
            'visual_focus':'Follow the shared input through the compared operations.',
            'relationships':[{'source':'Input','target':'Methods','relationship':'Same input for comparison','passages':candidate['passages']}]}


def draft_for(candidate=CANDIDATE, *, figures=None, text=None):
    """A valid Blog draft: the accepted plan, cited prose, and focused briefs."""
    if figures is None:
        figures = [blog_brief(passages=candidate['passages'])]
    if text is None:
        text = candidate['text']
        if not figures:
            text = re.sub(r'\n*\{\{figure:[^}]+\}\}\n*', '\n\n', text)
    return {'plan': plan_for(candidate), 'text': text, 'figures': copy.deepcopy(figures)}


def visual_candidate(candidate=CANDIDATE):
    value=copy.deepcopy(candidate)
    value['text']=''
    return value


def plan_digest(candidate=CANDIDATE):
    return hashlib.sha256(json.dumps(plan_for(candidate),sort_keys=True,separators=(',',':')).encode()).hexdigest()


def selection_for(section='s0002'):
    return {'paper_type':'evaluation','focus':'Compare the methods and retain the scope.',
            'section_ids':[section],'passage_ids':[],'figure_ids':[]}


def action(name,**arguments):
    return {'text':'','tool_calls':[{'id':'call_'+name,'type':'function',
            'function':{'name':name,'arguments':json.dumps(arguments)}}],'usage':{'total_tokens':10}}


def panel_reply(identifier='fig1', text='Same input', *, wrong_id=False, labels=None):
    """One structured drawing response, in the request_panel shape."""
    svg=blog_svg_labels(list(labels)) if labels is not None else blog_svg(text)
    body=json.dumps({'panel_id':'fig1' if wrong_id else identifier,'svg':svg})
    return {'text':body,'usage':{'total_tokens':10}}


def invalid_reply():
    return {'text':'not json at all','usage':{'total_tokens':1}}


def open_findings(messages):
    """The unresolved findings the application supplies to this review request."""
    match=re.search(r'<open_findings>\n(.*?)\n</open_findings>',prompt_text(messages),re.S)
    return json.loads(match.group(1)) if match else []


def resolve(*needles, quote='explained directly'):
    """Explicit resolutions for supplied findings whose message mentions a needle, or for all."""
    def build(messages):
        return [{'id':item['id'],'quote':quote,
                 'explanation':'The current candidate addresses this finding.'}
                for item in open_findings(messages)
                if not needles or any(needle in item['message'] for needle in needles)]
    return build


def verdict(*issues, resolutions=(), approved=None):
    """One scripted verdict, bound to its own prompt's digest and open findings."""
    def respond(messages):
        digest=re.search(r'CURRENT CANDIDATE DIGEST: ([0-9a-f]{64})',prompt_text(messages)).group(1)
        supplied=resolutions(messages) if callable(resolutions) else list(resolutions)
        resolved={item['id'] for item in supplied}
        remaining=[item for item in open_findings(messages) if item['id'] not in resolved]
        body={'action':'verdict','candidate_digest':digest,'issues':list(issues),
              'resolutions':supplied,
              'approved':(not issues and not remaining) if approved is None else approved}
        return {'text':json.dumps(body),'usage':{}}
    return respond


def review_issue(category='readability', path='fig1', message='The label overlaps its border.',
                 passages=('p00001',), anchor=''):
    return {'category':category,'path':path,'message':message,'passages':list(passages),
            'anchor':anchor}


def prompt_text(messages):
    content=messages[-1]['content']
    return content[0].get('text','') if isinstance(content,list) else content


def article_and_digest(messages):
    """The article text and digest a structured correction request was bound to."""
    text=prompt_text(messages)
    digest=re.search(r'CURRENT TEXT DIGEST: ([0-9a-f]{64})',text).group(1)
    article=text.split('<article>\n',1)[1].split('\n</article>',1)[0]
    return article,digest


def cleanup_reply(article,digest,edits):
    return {'text':json.dumps({'base_digest':digest,'edits':edits}),'usage':{'total_tokens':10}}


def scripted_provider(candidate=CANDIDATE, *, drawing='Same input', review_issues=(),
                      cleanup=None, text=None, figures=None):
    """Shared fixture for the HTTP/export integration tests of the Blog protocol."""
    def complete(messages,**kwargs):
        if kwargs.get('json_object') is False:
            names={item['function']['name'] for item in kwargs.get('tools',[])}
            if 'submit_selection' in names:
                return action('submit_selection',candidate={'paper_type':candidate['paper_type'],
                    'focus':'Explain the contribution and qualified finding.','section_ids':[],
                    'passage_ids':candidate['passages'],'figure_ids':[]})
            if 'submit_plan' in names:
                return action('submit_plan',candidate=plan_for(candidate))
            if 'submit_draft' in names:
                return action('submit_draft',candidate=draft_for(candidate,figures=figures,text=text))
            raise AssertionError('Unscripted authoring request')
        text_payload=prompt_text(messages)
        if 'DRAWING ASSIGNMENT' in text_payload:
            identifier=re.search(r'panel id: (fig\d+)',text_payload).group(1)
            return panel_reply(identifier,drawing)
        if 'STAGE: REVIEW' in text_payload:
            return verdict(*review_issues)(messages)
        if cleanup is not None:
            article,digest=article_and_digest(messages)
            return cleanup_reply(article,digest,cleanup(article))
        return {'text':'Supported result [p00001].','usage':{'total_tokens':42}}
    return complete


def render_fixture(directory,figure,title,*,compact=False,mode='legacy'):
    import base64
    import uuid
    relative=Path('reader/overview-figures')/uuid.uuid4().hex/figure['id']
    target=Path(directory)/relative;target.parent.mkdir(parents=True)
    target.with_suffix('.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200"><text x="20" y="40">Confidence needs context</text></svg>')
    target.with_suffix('.png').write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aWQAAAABJRU5ErkJggg=='))
    assets={'svg':str(relative)+'.svg','png':str(relative)+'.png',
            'checks':{'issues':[],'issue_details':[],'canvas':{'width':640,'height':200},
                      'text_runs':[{'path':'#label','displayed_size_px':18,'text':'Same input'}]}}
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


class ReviewProtocolTests(unittest.TestCase):
    """Findings persist across verdicts, and a figure finding is bound to its own drawing."""

    EVIDENCE={'passages':[{'id':'p00001'}]}
    ARTICLE='The paper compares two methods in one setting [p00001].'

    def finding(self,identifier='issue-111111111111',path='article',
                message='The comparison setting is missing.'):
        return {'id':identifier,'category':'scope','path':path,'message':message,
                'passages':['p00001'],'anchor':''}

    def identified(self,**overrides):
        """A finding with the application-owned ID a review response would produce."""
        from papers.agent_overviews import _with_issue_ids
        value={'code':'review',**dict(self.finding(),**overrides)}
        value.pop('id')
        return _with_issue_ids([value])[0]

    def verdict(self,**overrides):
        value={'action':'verdict','approved':False,'candidate_digest':'digest',
               'issues':[],'resolutions':[]}
        value.update(overrides)
        return value

    def check(self,value,*,findings=(),figure_ids=(),figure_labels=None,article=None,digest='digest'):
        from papers.agent_overviews import _review_response
        return _review_response(value,self.EVIDENCE,candidate_digest_expected=digest,
                                findings=list(findings),figure_ids=list(figure_ids),
                                figure_labels=figure_labels or {},
                                article_text=self.ARTICLE if article is None else article)

    def test_an_explicit_valid_resolution_closes_only_its_own_finding(self):
        resolved=self.finding('issue-aaaa','article','The setting is missing.')
        other=self.finding('issue-bbbb','article','The ranking is unqualified.')
        accepted=self.check(self.verdict(approved=False,resolutions=[
            {'id':'issue-aaaa','quote':'in one setting','explanation':'The setting is now named.'}]),
            findings=[resolved,other])
        self.assertEqual(['issue-bbbb'],[item['id'] for item in accepted['open_findings']])
        self.assertEqual([resolved['id']],[item['id'] for item in accepted['resolutions']])
        closed=self.check(self.verdict(approved=True,resolutions=[
            {'id':'issue-bbbb','quote':'one setting','explanation':'The ranking now names its setting.'}]),
            findings=accepted['open_findings'])
        self.assertEqual([],closed['open_findings'])
        retained=self.check(self.verdict(),findings=[resolved,other])
        self.assertEqual([resolved,other],retained['open_findings'])

    def test_unknown_stale_and_unverifiable_resolutions_are_rejected(self):
        finding=self.identified()
        same=finding['message']
        cases={
            'unknown id':self.verdict(resolutions=[{'id':'issue-9999','quote':'in one setting',
                                                    'explanation':'No such finding.'}]),
            'stale candidate':self.verdict(candidate_digest='stale',resolutions=[
                {'id':finding['id'],'quote':'in one setting','explanation':'Fixed.'}]),
            'absent quote':self.verdict(resolutions=[{'id':finding['id'],'quote':'nothing like this',
                                                      'explanation':'Fixed.'}]),
            'empty quote':self.verdict(resolutions=[{'id':finding['id'],'quote':' ',
                                                     'explanation':'Fixed.'}]),
            'reported twice':self.verdict(issues=[{'category':'scope','path':'article',
                                                   'message':same,'passages':['p00001'],'anchor':''}],
                                          resolutions=[{'id':finding['id'],'quote':'in one setting',
                                                        'explanation':'Fixed.'}]),
            'contradictory approval':self.verdict(approved=True),
        }
        for name,value in cases.items():
            with self.subTest(name=name),self.assertRaises(ValueError):
                self.check(value,findings=[finding])
        with self.assertRaisesRegex(ValueError,'names no supplied open finding'):
            self.check(cases['unknown id'],findings=[finding])
        with self.assertRaisesRegex(ValueError,'different candidate'):
            self.check(cases['stale candidate'],findings=[finding])
        with self.assertRaisesRegex(ValueError,'quotes no text visible'):
            self.check(cases['absent quote'],findings=[finding])
        with self.assertRaisesRegex(ValueError,'cannot be both reported and resolved'):
            self.check(cases['reported twice'],findings=[finding])
        with self.assertRaisesRegex(ValueError,'Approval is rejected'):
            self.check(cases['contradictory approval'],findings=[finding])

    def test_a_figure_finding_needs_an_anchor_visible_only_in_the_named_drawing(self):
        labels={'fig1':'tokens fixed rule','fig2':'tokens HBM SRAM'}
        issue=lambda anchor,path='fig2':{'category':'readability','path':path,
                                         'message':'The label collides.','passages':['p00001'],
                                         'anchor':anchor}
        accepted=self.check(self.verdict(issues=[issue('HBM')]),
                            figure_ids=['fig1','fig2'],figure_labels=labels)
        self.assertEqual(['fig2'],[item['path'] for item in accepted['open_findings']])
        endpoints=self.check(self.verdict(issues=[issue('HBM and SRAM')]),
                             figure_ids=['fig1','fig2'],figure_labels=labels)
        self.assertEqual(1,len(endpoints['open_findings']),'relation endpoints are one anchor')
        for bad,message in ((issue('HBM and SRAM','fig1'),'not visible in fig1'),
                            (issue(''),'needs an anchor'),
                            (issue('nothing'),'not visible in fig2'),
                            (issue('tokens','fig1'),'visible in fig1, fig2')):
            with self.subTest(anchor=bad['anchor'],path=bad['path']),\
                    self.assertRaisesRegex(ValueError,message):
                self.check(self.verdict(issues=[bad]),figure_ids=['fig1','fig2'],figure_labels=labels)
        article=dict(issue(''),path='article',anchor='HBM')
        with self.assertRaisesRegex(ValueError,'leave anchor empty'):
            self.check(self.verdict(issues=[article]),figure_ids=['fig1','fig2'],figure_labels=labels)
        omitted=dict(issue('HBM'),path='fig3')
        accepted=self.check(self.verdict(issues=[omitted]),figure_ids=['fig1','fig2','fig3'],
                            figure_labels=labels)
        self.assertEqual(['fig3'],[item['path'] for item in accepted['open_findings']],
                         'a finding on an omitted drawing is still accepted as a prose problem')

    def test_omission_continuity_findings_are_stable_and_per_figure(self):
        from papers.agent_overviews import omission_continuity_finding
        state=lambda identifier,title:{'id':identifier,'attempts':4,'brief':{'title':title}}
        first=omission_continuity_finding(state('fig1','Why a fixed rule fails'))
        repeat=omission_continuity_finding(state('fig1','Why a fixed rule fails'))
        other=omission_continuity_finding(state('fig3','Selective scan keeps HBM off SRAM'))
        self.assertEqual(first['id'],repeat['id'])
        self.assertNotEqual(first['id'],other['id'])
        self.assertEqual('article',first['path'])
        self.assertIn('was omitted after 4 drawing attempts',first['message'])


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
        def render(directory,figure,title,*,compact=False,mode='legacy'):
            root=Path(directory);path=root/'figure.png';path.write_bytes(b'\x89PNG\r\n\x1a\nfixture')
            assets={'png':'figure.png','html':'figure.html','svg':'figure.svg','pdf':'figure.pdf',
                    'checks':{'issues':[],'issue_details':[],'canvas':{'width':640,'height':200},
                              'text_runs':[{'path':'#label','displayed_size_px':18,'text':'Same input'}]}}
            if figure.get('source_svg'):
                (root/'figure.source.svg').write_text(figure['source_svg'])
                assets['svg_source']='figure.source.svg'
            return assets
        self.render=patch('papers.html_figures.render',side_effect=render).start()

    def run_steps(self,steps,**kwargs):
        """Run one Blog generation with exactly one scripted response per provider request."""
        pending=list(steps)
        def complete(messages,**call):
            if not pending:
                raise AssertionError('Unscripted provider request: '+json.dumps(messages)[-300:])
            step=pending.pop(0)
            return step(messages) if callable(step) else step
        self.provider.reset_mock()
        self.provider.complete.side_effect=complete
        return generate_overview(self.provider,self.doc,lambda _:None,**kwargs)

    def authoring(self,candidate=CANDIDATE,*,figures=None,text=None):
        """Selection, narrative, and authoring, in the stage order the coordinator uses."""
        return [action('submit_selection',candidate=selection_for()),
                action('submit_plan',candidate=plan_for(candidate)),
                action('submit_draft',candidate=draft_for(candidate,figures=figures,text=text))]

    def drawing(self,text='Same input'):
        """One structured drawing response answering the requested stable ID."""
        def respond(messages):
            identifier=re.search(r'panel id: (fig\d+)',prompt_text(messages)).group(1)
            return panel_reply(identifier,text)
        return respond

    def drawing_labels(self,labels_by_id):
        """One structured drawing response per requested stable ID, with that figure's labels."""
        def respond(messages):
            identifier=re.search(r'panel id: (fig\d+)',prompt_text(messages)).group(1)
            return panel_reply(identifier,labels=labels_by_id[identifier])
        return respond

    def invalid(self):
        return lambda messages: invalid_reply()

    def cleanup_step(self,edits):
        """One structured cleanup response built against the bound article and digest."""
        def respond(messages):
            article,digest=article_and_digest(messages)
            return cleanup_reply(article,digest,edits if not callable(edits) else edits(article))
        return respond

    def prose_edit(self,old,new):
        return self.cleanup_step([{'old':old,'new':new}])

    def omission_steps(self,count,positions,*,text=None,figures=None):
        """A full scripted run in which the named planned figures exhaust their budget."""
        if figures is None:
            figures=[blog_brief(f'fig{index}') for index in range(1,count+1)]
        if text is None:
            text=('\n\n'.join(f'Follow the blue branch for figure {index} [p00001].\n\n'
                              f'{{{{figure:fig{index}}}}}' for index in range(1,count+1))
                  +'\n\nOnly these tasks were evaluated [p00001].')
        steps=self.authoring(figures=figures,text=text)
        for index in range(1,count+1):
            steps.extend([self.invalid()]*4 if index in positions else [self.drawing()])
        if positions:
            steps.append(self.cleanup_step(
                [{'old':f'Follow the blue branch for figure {index} [p00001].',
                  'new':f'The operation for figure {index} is explained directly [p00001].'}
                 for index in positions]))
        return steps,text

    def failure(self):
        return json.loads(next(Path(self.doc['directory']).rglob('failure.json')).read_text())

    def drawing_calls(self):
        return [call for call in self.provider.complete.call_args_list
                if 'DRAWING ASSIGNMENT' in json.dumps(call.args[0])]

    def test_context_checkpoint_round_trip_rejects_stale_identity(self):
        from papers.agent_overviews import write_generation_context, load_generation_context
        path=Path(self.doc['directory'])/'generation_context.json'
        context={'context_revision':'generation-context-v1','document_digest':'doc',
                 'source_digest':'source','provider':{'model':'fixture','endpoint':'https://example.test','vision':False},
                 'prompt_revision':'prompt','schema_revision':'schema','stage':'figures',
                 'selection':selection_for(),'evidence':{'passages':[{'id':'p00001','text':'Evidence'}],'images':[]},
                 'accepted_plan':plan_for(),'plan_digest':plan_digest(),'article_digest':'article',
                 'briefs':[blog_brief()],'figure_states':[],'omitted_figures':[],'cleanup_edits':[]}
        write_generation_context(path,context)
        self.assertEqual(context,load_generation_context(path,document_digest='doc',source_digest='source',
            provider=context['provider'],prompt_revision='prompt',schema_revision='schema'))
        with self.assertRaises(ValueError):
            load_generation_context(path,document_digest='changed',source_digest='source',
                provider=context['provider'],prompt_revision='prompt',schema_revision='schema')

    def test_blog_authors_briefs_draws_once_and_completes_after_review(self):
        result=self.run_steps([*self.authoring(),self.drawing(),verdict()])
        self.assertEqual(5,self.provider.complete.call_count)
        self.assertEqual('blog-focused-svg-v1',result['provenance']['prompt_revision'])
        self.assertEqual(html_figures.PANEL_SVG_PROFILE_REVISION,result['provenance']['svg_profile_revision'])
        self.assertEqual('formal',result['provenance']['overview_language'])
        self.assertTrue(result['provenance']['reviews'][-1]['approved'])
        self.assertEqual(64,len(result['provenance']['reviews'][-1]['article_digest']))
        figure=result['figures'][0]
        self.assertEqual({'html','svg','png','pdf','svg_source'},set(figure)&{'html','svg','png','pdf','svg_source'})
        self.assertEqual([],figure['checks']['issue_details'])
        outcome=result['provenance']['figure_outcomes'][0]
        self.assertEqual({'id':'fig1','status':'accepted','attempts':1,'accepted_attempt':1},
                         {key:value for key,value in outcome.items() if key!='issues'})
        review_prompt=prompt_text(self.provider.complete.call_args_list[4].args[0])
        self.assertIn('<accepted_narrative>',review_prompt)
        self.assertIn('<surviving_figures>',review_prompt)
        author_prompt=json.dumps(self.provider.complete.call_args_list[2].args[0])
        self.assertIn('request_narrative_revision',author_prompt)
        self.assertNotIn('<svg',author_prompt)

    def test_blog_preferences_reach_every_prose_request(self):
        from papers.overview import LANGUAGES,LENGTHS
        steps=[*self.authoring(text=TEXT_ONE_FIGURE),self.drawing(),
               verdict(review_issue(category='readability',path='article',
                                    message='Clarify how the two paths combine.')),
               self.prose_edit('Follow the blue branch in the diagram below [p00001].',
                               'The input follows two paths whose outputs are added [p00001].'),
               verdict(resolutions=resolve(quote='two paths whose outputs are added'))]
        for language,length in (('casual','short'),('semi-formal','medium'),('formal','large')):
            with self.subTest(language=language,length=length):
                self.provider.settings.update(overview_language=language,overview_length=length)
                result=self.run_steps(steps)
                for call in self.provider.complete.call_args_list:
                    payload=json.dumps(call.args[0],ensure_ascii=False)
                    if 'DRAWING ASSIGNMENT' in payload:
                        continue
                    self.assertIn(LANGUAGES[language],payload)
                    self.assertIn('Requested Blog length: '+LENGTHS[length],payload)
                self.assertEqual(language,result['provenance']['overview_language'])
                self.assertEqual(length,result['provenance']['overview_length'])

    def test_blog_author_cannot_silently_replace_accepted_plan(self):
        changed=draft_for();changed['plan']['visual_focus']='An unapproved change of story.'
        result=self.run_steps([action('submit_selection',candidate=selection_for()),
                               action('submit_plan',candidate=plan_for()),
                               action('submit_draft',candidate=changed),
                               action('submit_draft',candidate=draft_for()),
                               self.drawing(),verdict()])
        self.assertEqual(plan_for(),result['plan'])
        self.assertEqual(6,self.provider.complete.call_count)

    def test_blog_can_revise_the_narrative_before_authoring(self):
        revised=draft_for()
        revised['plan']['visual_focus']=PLAN_FOR_ORIGINAL
        result=self.run_steps([action('submit_selection',candidate=selection_for()),
                               action('submit_plan',candidate=plan_for()),
                               action('request_narrative_revision',reason='Explain the comparison first.',
                                      passage_ids=['p00001']),
                               action('submit_plan',candidate=revised['plan']),
                               action('submit_draft',candidate=revised),
                               self.drawing(),verdict()])
        self.assertEqual(revised['plan'],result['plan'])
        self.assertEqual(7,self.provider.complete.call_count)

    def test_an_invalid_draft_is_corrected_once_before_drawing(self):
        broken=draft_for();broken['figures'][0]['layout_intent']=''
        result=self.run_steps([action('submit_selection',candidate=selection_for()),
                               action('submit_plan',candidate=plan_for()),
                               action('submit_draft',candidate=broken),
                               action('submit_draft',candidate=draft_for()),
                               self.drawing(),verdict()])
        self.assertEqual(6,self.provider.complete.call_count)
        correction=json.dumps(self.provider.complete.call_args_list[3].args[0])
        self.assertIn('draft_issues',correction)
        self.assertIn('layout_intent',correction)
        self.assertEqual(1,len(result['figures']))

    def test_first_middle_and_last_figure_omission(self):
        for count,position in ((2,1),(3,2),(3,3)):
            with self.subTest(count=count,position=position):
                steps,_=self.omission_steps(count,(position,))
                result=self.run_steps([*steps,verdict(resolutions=resolve(quote='explained directly'))])
                expected=[f'fig{index}' for index in range(1,count+1) if index!=position]
                self.assertEqual(expected,[figure['id'] for figure in result['figures']])
                self.assertNotIn(f'{{{{figure:fig{position}}}}}',result['cited_text'])
                self.assertNotIn(f'Follow the blue branch for figure {position}',result['cited_text'])
                self.assertIn(f'The operation for figure {position} is explained directly',
                              result['cited_text'])
                self.assertEqual([f'fig{position}'],
                                 [item['id'] for item in result['provenance']['omitted_figures']])
                self.assertEqual(4,result['provenance']['omitted_figures'][0]['attempts'])

    def test_multiple_omissions_share_one_cleanup_request(self):
        steps,_=self.omission_steps(3,(1,3))
        result=self.run_steps([*steps,verdict(resolutions=resolve(quote='explained directly'))])
        self.assertEqual(['fig2'],[figure['id'] for figure in result['figures']])
        cleanups=[call for call in self.provider.complete.call_args_list
                  if 'REMOVE OMITTED FIGURES' in json.dumps(call.args[0])]
        self.assertEqual(1,len(cleanups))
        self.assertEqual(['fig1','fig3'],
                         [item['id'] for item in result['provenance']['omitted_figures']])
        self.assertEqual(2,len(result['provenance']['cleanup_edits'][0]['edits']))

    def test_all_figures_omitted_delivers_a_coherent_article(self):
        steps,_=self.omission_steps(1,(1,))
        result=self.run_steps([*steps,verdict(resolutions=resolve(quote='explained directly'))])
        self.assertEqual([],result['figures'])
        self.assertNotIn('{{figure:',result['cited_text'])
        self.assertNotIn('blue branch',result['cited_text'])
        self.assertIn('explained directly',result['cited_text'])
        self.assertIn('Only these tasks were evaluated',result['cited_text'])
        self.assertTrue(result['provenance']['reviews'][-1]['approved'])

    def test_source_paper_figure_references_survive_cleanup(self):
        text=('The paper compares two methods [p00001].\n\n'
              'Follow the blue branch below [p00001].\n\n{{figure:fig1}}\n\n'
              'Figure 2 of the paper reports the ranking [p00001].')
        steps=self.authoring(figures=[blog_brief('fig1')],text=text)
        steps.extend([self.invalid()]*4)
        steps.append(self.prose_edit('Follow the blue branch below [p00001].',
                                     'The two approaches are explained in prose [p00001].'))
        result=self.run_steps([*steps,verdict(resolutions=resolve(quote='explained in prose'))])
        self.assertIn('Figure 2 of the paper reports the ranking',result['cited_text'])
        self.assertNotIn('blue branch',result['cited_text'])
        self.assertEqual([],result['figures'])

    def test_omission_opens_a_continuity_finding_that_a_later_verdict_must_resolve(self):
        """A reviewer cannot approve an omission cleanup without resolving its continuity finding."""
        steps,_=self.omission_steps(1,(1,))
        approval=verdict(approved=True)
        with self.assertRaises(ProviderError) as caught:
            self.run_steps([*steps,approval,approval])
        self.assertIn('Approval is rejected',str(caught.exception))
        self.assertTrue(list(Path(self.doc['directory']).rglob('failure.json')))
        review_prompts=[prompt_text(call.args[0]) for call in self.provider.complete.call_args_list
                        if 'STAGE: REVIEW' in json.dumps(call.args[0])]
        self.assertEqual(2,len(review_prompts),'one request plus one protocol correction')
        self.assertIn('was omitted after 4 drawing attempts',review_prompts[-1])

    def test_figure_omission_resolves_its_visual_finding_and_keeps_continuity_open(self):
        """Omission closes the drawing defect; the prose-continuity finding outlives it."""
        steps=self.authoring()
        steps.extend([self.drawing(),
                      verdict(review_issue(category='readability',path='fig1',anchor='Same input',
                                           message='The output label overlaps a connector.')),
                      self.invalid(),self.invalid(),self.invalid(),
                      self.prose_edit('The figure shows their shared input [p00001].',
                                      'Both paths receive the same input [p00001].'),
                      verdict(approved=False),
                      self.prose_edit('Both paths receive the same input [p00001].',
                                      'Both paths receive the same input before combining [p00001].'),
                      verdict(resolutions=resolve(quote='before combining'))])
        result=self.run_steps(steps)
        self.assertEqual([],result['figures'])
        self.assertTrue(result['provenance']['reviews'][-1]['approved'])
        opened=result['provenance']['reviews'][1]['issue_details']
        self.assertEqual(['article'],[item['path'] for item in opened])
        self.assertIn('was omitted after 4 drawing attempts',opened[0]['message'])
        self.assertNotIn('overlaps a connector',json.dumps(opened))

    def test_a_late_omission_after_semantic_review_is_cleaned_once(self):
        steps=self.authoring()
        steps.extend([self.drawing(),
                      verdict(review_issue(category='readability',path='fig1',anchor='Same input',
                                           message='The output label overlaps a connector.')),
                      self.invalid(),self.invalid(),self.invalid(),
                      self.prose_edit('The figure shows their shared input [p00001].',
                                      'Both paths receive the same input [p00001].'),
                      verdict(resolutions=resolve(quote='Both paths receive the same input'))])
        result=self.run_steps(steps)
        self.assertEqual([],result['figures'])
        outcome=result['provenance']['figure_outcomes'][0]
        self.assertEqual({'status':'omitted','attempts':4},
                         {key:outcome[key] for key in ('status','attempts')})
        drawings=self.drawing_calls()
        self.assertEqual(4,len(drawings))
        self.assertIn('overlaps a connector',json.dumps(drawings[1].args[0]))
        self.assertIn('data:image/png;base64',json.dumps(drawings[1].args[0]))
        self.assertEqual(1,len(result['provenance']['cleanup_edits']))

    def test_article_findings_use_bounded_exact_edits(self):
        steps=[*self.authoring(),self.drawing(),
               verdict(review_issue(category='scope',path='article',
                                    message='The comparison setting is missing.')),
               self.prose_edit('The paper compares methods [p00001].',
                               'The paper compares two methods in one setting [p00001].'),
               verdict(resolutions=resolve(quote='in one setting'))]
        result=self.run_steps(steps)
        self.assertIn('in one setting',result['cited_text'])
        self.assertEqual(1,result['provenance']['prose_corrections'])
        self.assertEqual(2,len(result['provenance']['reviews']))

    def test_a_reworded_finding_does_not_reset_its_correction_history(self):
        issue=review_issue(category='scope',path='article',message='The setting is missing.')
        reworded=review_issue(category='scope',path='article',
                              message='Readers still cannot see which dataset and model size were used.')
        steps=[*self.authoring(),self.drawing(),verdict(issue),
               self.prose_edit('The paper compares methods [p00001].',
                               'The paper compares methods carefully [p00001].'),
               verdict(reworded)]
        with self.assertRaises(ProviderError) as caught:
            self.run_steps(steps)
        self.assertIn('did not improve',str(caught.exception))
        self.assertEqual('article_or_review',self.failure()['failure_kind'])

    def test_the_two_prose_correction_ceiling_still_stops_the_loop(self):
        """Each correction makes progress; a third unrelated finding still ends the run."""
        steps=[*self.authoring(),self.drawing(),
               verdict(review_issue(category='scope',path='article',message='The setting is missing.')),
               self.prose_edit('The paper compares methods [p00001].',
                               'The paper compares two methods in one setting [p00001].'),
               verdict(review_issue(category='missing_transition',path='article',
                                    message='The ranking arrives without a transition.'),
                       resolutions=resolve('setting',quote='in one setting')),
               self.prose_edit('The paper compares two methods in one setting [p00001].',
                               'The paper compares two methods in one setting [p00001],\n\n'
                               'The ranking follows from that comparison.'),
               verdict(review_issue(category='unexplained_term',path='article',
                                    message='The limitation term is unexplained.'),
                       resolutions=resolve('transition',quote='follows from that comparison'))]
        with self.assertRaises(ProviderError) as caught:
            self.run_steps(steps)
        self.assertIn('after two corrections',str(caught.exception))
        self.assertEqual(2,len(self.failure()['cleanup_edits']))
        self.assertEqual(3,len(self.failure()['reviews']))

    def test_rejected_cleanup_is_retried_once_then_fails_without_publishing(self):
        stale={'text':json.dumps({'base_digest':'0'*64,'edits':[{'old':'x','new':'y'}]}),'usage':{}}
        steps=[*self.authoring(),self.drawing(),
               verdict(review_issue(category='scope',path='article',message='The setting is missing.')),
               stale,stale]
        with self.assertRaises(ProviderError) as caught:
            self.run_steps(steps)
        self.assertIn('text correction was rejected',str(caught.exception))
        self.assertEqual('article_or_review',self.failure()['failure_kind'])

    def test_cleanup_provider_failure_preserves_the_draft(self):
        def explode(messages):
            raise ProviderError('Provider request failed with HTTP status 503.')
        steps=[*self.authoring(),self.drawing(),
               verdict(review_issue(category='scope',path='article',message='The setting is missing.')),
               explode]
        with self.assertRaises(ProviderError):
            self.run_steps(steps)
        self.assertIn('503',self.failure()['error'])
        self.assertTrue(list(Path(self.doc['directory']).rglob('draft.json')))

    def test_reviewer_may_request_one_batched_evidence_supplement_per_verdict(self):
        supplement={'text':json.dumps({'action':'read_evidence','section_ids':['s0001'],
                                       'passage_ids':[],'figure_ids':[]}),'usage':{}}
        result=self.run_steps([*self.authoring(),self.drawing(),supplement,verdict()])
        self.assertTrue(result['provenance']['reviews'][-1]['approved'])
        self.assertIn('p00000',result['provenance']['passages'])

    def test_a_second_evidence_supplement_request_in_one_verdict_is_refused(self):
        supplement={'text':json.dumps({'action':'read_evidence','section_ids':['s0001'],
                                       'passage_ids':[],'figure_ids':[]}),'usage':{}}
        steps=[*self.authoring(),self.drawing(),supplement,supplement]
        with self.assertRaises(ProviderError) as caught:
            self.run_steps(steps)
        self.assertIn('second evidence supplement',str(caught.exception))

    def test_review_can_route_a_scientific_error_to_a_supported_brief_correction(self):
        corrected=blog_brief()
        corrected['purpose']='What do the two compared paths compute?'
        corrected['layout_intent']='Input at left; frozen and trainable paths stacked; outputs added at right.'
        def correct_brief(messages):
            digest=re.search(r'CURRENT BRIEF DIGEST: ([0-9a-f]{64})',prompt_text(messages)).group(1)
            return {'text':json.dumps({'base_digest':digest,'brief':corrected}),'usage':{}}
        steps=[*self.authoring(),self.drawing(),
               verdict(review_issue(category='incorrect_mechanism',path='fig1',anchor='Same input',
                                    message='The brief implies the update replaces the base output.')),
               correct_brief,self.drawing(),verdict(resolutions=resolve(quote='Same input'))]
        result=self.run_steps(steps)
        self.assertTrue(result['provenance']['reviews'][-1]['approved'])
        self.assertIn('frozen and trainable paths',result['figures'][0]['brief']['layout_intent'])
        drawings=self.drawing_calls()
        self.assertEqual(2,len(drawings))
        self.assertIn('frozen and trainable paths',json.dumps(drawings[1].args[0]))

    def test_a_second_scientific_finding_reuses_the_remaining_drawing_budget(self):
        corrected=blog_brief();corrected['purpose']='Corrected purpose.'
        def correct_brief(messages):
            digest=re.search(r'CURRENT BRIEF DIGEST: ([0-9a-f]{64})',prompt_text(messages)).group(1)
            return {'text':json.dumps({'base_digest':digest,'brief':corrected}),'usage':{}}
        issue=review_issue(category='incorrect_mechanism',path='fig1',anchor='Same input',
                           message='The mechanism is wrong.')
        steps=[*self.authoring(),self.drawing(),verdict(issue),correct_brief,self.invalid(),
               self.invalid(),self.invalid(),
               self.prose_edit('The figure shows their shared input [p00001].',
                               'The mechanism is explained in prose [p00001].'),
               verdict(resolutions=resolve(quote='The mechanism is explained in prose'))]
        result=self.run_steps(steps)
        self.assertEqual([],result['figures'])
        self.assertEqual(4,result['provenance']['figure_outcomes'][0]['attempts'])
        corrections=[call for call in self.provider.complete.call_args_list
                     if 'STAGE: BRIEF CORRECTION' in json.dumps(call.args[0])]
        self.assertEqual(1,len(corrections))

    def test_a_review_finding_on_an_exhausted_figure_omits_without_a_fifth_draw(self):
        steps=[*self.authoring(text=TEXT_ONE_FIGURE),
               self.invalid(),self.invalid(),self.invalid(),self.drawing(),
               verdict(review_issue(category='readability',path='fig1',anchor='Same input',
                                    message='The output label overlaps a connector.')),
               self.prose_edit('Follow the blue branch in the diagram below [p00001].',
                               'The two paths are explained directly in prose [p00001].'),
               verdict(resolutions=resolve(quote='explained directly in prose'))]
        result=self.run_steps(steps)
        self.assertEqual(4,len(self.drawing_calls()),'no fifth drawing request is made')
        self.assertEqual([],result['figures'])
        self.assertNotIn('{{figure:',result['cited_text'])
        self.assertNotIn('blue branch',result['cited_text'])
        self.assertIn('explained directly in prose',result['cited_text'])
        outcome=result['provenance']['figure_outcomes'][0]
        self.assertEqual({'id':'fig1','status':'omitted','attempts':4,'accepted_attempt':None},
                         {key:outcome[key] for key in ('id','status','attempts','accepted_attempt')})
        self.assertEqual([{'id':'fig1','attempts':4,'issues':['review']}],
                         result['provenance']['omitted_figures'])
        self.assertTrue(result['provenance']['reviews'][-1]['approved'])

    def two_figure_run(self):
        """A two-drawing article whose later verdict drops the open prose finding."""
        figures=[blog_brief('fig1',illustration='tokens',title='Why a fixed rule fails'),
                 blog_brief('fig2',illustration='HBM',title='Selective scan keeps HBM off SRAM')]
        text=('The paper compares two methods [p00001].\n\n'
              'Follow the blue branch in the diagram below [p00001].\n\n{{figure:fig1}}\n\n'
              'The second drawing shows the same input [p00001].\n\n{{figure:fig2}}\n\n'
              'Only these tasks were evaluated [p00001].')
        prose=review_issue(category='scope',path='article',
                           message='The comparison setting is missing.')
        drawing=self.drawing_labels({'fig1':['tokens'],'fig2':['HBM','SRAM']})
        steps=[*self.authoring(figures=figures,text=text),drawing,drawing,
               verdict(review_issue(category='readability',path='fig2',anchor='SRAM',
                                    message='The SRAM label crosses its border.'),prose),
               # The drawing is repaired and resolved, then the next verdict silences the prose one.
               drawing,
               verdict(resolutions=resolve('SRAM',quote='SRAM')),
               self.prose_edit('The paper compares two methods [p00001].',
                               'The paper compares two methods in one setting [p00001].'),
               verdict(resolutions=resolve('setting',quote='in one setting'))]
        return steps,prose

    def test_a_drawing_repair_does_not_drop_the_open_prose_finding(self):
        """A finding missing from a later verdict is still open and still reaches its repair."""
        steps,prose=self.two_figure_run()
        result=self.run_steps(steps)
        self.assertIn('in one setting',result['cited_text'])
        self.assertTrue(result['provenance']['reviews'][-1]['approved'])
        dropped=result['provenance']['reviews'][1]['issue_details']
        self.assertEqual([prose['message']],[item['message'] for item in dropped])
        repairs=[prompt_text(call.args[0]) for call in self.provider.complete.call_args_list
                 if 'REPAIR ARTICLE FINDINGS' in json.dumps(call.args[0])]
        self.assertEqual(1,len(repairs))
        self.assertIn(prose['message'],repairs[0])
        self.assertIn(dropped[0]['id'],repairs[0])

    def test_a_finding_dropped_from_every_verdict_cannot_reach_approval(self):
        """Absence is not resolution: a silent verdict cannot approve the candidate."""
        steps,prose=self.two_figure_run()
        approval=verdict(approved=True)
        with self.assertRaises(ProviderError) as caught:
            self.run_steps(steps[:7]+[approval,approval])
        self.assertIn('Approval is rejected',str(caught.exception))
        open_findings=self.failure()['open_findings']
        self.assertIn(prose['message'],[item['message'] for item in open_findings])
        self.assertIn('SRAM',json.dumps(open_findings))

    def test_a_mismatched_figure_anchor_never_repairs_the_named_figure(self):
        """A fig1 finding quoting fig2's labels draws nothing and keeps the draft."""
        figures=[blog_brief('fig1',illustration='tokens',title='Why a fixed rule fails'),
                 blog_brief('fig2',illustration='HBM',title='Selective scan keeps HBM off SRAM')]
        text=('The methods differ [p00001].\n\n{{figure:fig1}}\n\n{{figure:fig2}}\n\n'
              'Only these tasks were evaluated [p00001].')
        mismatched=verdict(review_issue(category='incorrect_mechanism',path='fig1',anchor='HBM',
                                        message='The HBM and SRAM labels are grouped as input-dependent.'))
        steps=[*self.authoring(figures=figures,text=text),
               self.drawing_labels({'fig1':['tokens'],'fig2':['HBM','SRAM']}),
               self.drawing_labels({'fig1':['tokens'],'fig2':['HBM','SRAM']}),
               mismatched,mismatched]
        with self.assertRaises(ProviderError) as caught:
            self.run_steps(steps)
        self.assertIn('not visible in fig1',str(caught.exception))
        self.assertEqual(2,len(self.drawing_calls()),'neither figure consumes a repair attempt')
        failure=self.failure()
        self.assertEqual([('fig1','accepted',1),('fig2','accepted',1)],
                         [(item['id'],item['status'],item['attempts']) for item in failure['figure_states']])
        self.assertEqual([],failure['open_findings'])
        corrections=[call for call in self.provider.complete.call_args_list
                     if 'STAGE: BRIEF CORRECTION' in json.dumps(call.args[0])]
        self.assertEqual([],corrections,'no brief is altered for a mismatched anchor')
        retry=prompt_text(self.provider.complete.call_args_list[-1].args[0])
        self.assertIn('not visible in fig1',retry)
        self.assertIn('HBM',retry)

    def test_a_corrected_anchor_repairs_only_the_named_figure(self):
        """The protocol correction re-anchors to fig3; fig1 keeps its drawing and its budget."""
        figures=[blog_brief('fig1',illustration='tokens',title='Why a fixed rule fails'),
                 blog_brief('fig3',illustration='HBM',title='Selective scan keeps HBM off SRAM')]
        text=('The methods differ [p00001].\n\n{{figure:fig1}}\n\n{{figure:fig3}}\n\n'
              'Only these tasks were evaluated [p00001].')
        steps=[*self.authoring(figures=figures,text=text),
               self.drawing_labels({'fig1':['tokens'],'fig3':['HBM','SRAM']}),
               self.drawing_labels({'fig1':['tokens'],'fig3':['HBM','SRAM']}),
               verdict(review_issue(category='readability',path='fig1',anchor='HBM',
                                    message='The HBM and SRAM labels collide.')),
               verdict(review_issue(category='readability',path='fig3',anchor='HBM and SRAM',
                                    message='The HBM and SRAM labels collide.')),
               self.drawing_labels({'fig3':['HBM','SRAM']}),
               verdict(resolutions=resolve(quote='SRAM'))]
        result=self.run_steps(steps)
        self.assertEqual(['fig1','fig3'],[figure['id'] for figure in result['figures']])
        self.assertEqual([('fig1',1),('fig3',2)],
                         [(item['id'],item['attempts']) for item in result['provenance']['figure_outcomes']])
        drawings=self.drawing_calls()
        self.assertEqual(3,len(drawings))
        self.assertIn('panel id: fig3',json.dumps(drawings[2].args[0]))
        self.assertNotIn('panel id: fig1',json.dumps(drawings[2].args[0]))
        self.assertEqual('tokens',result['figures'][0]['brief']['exact_text'][0])
        self.assertTrue(result['provenance']['reviews'][-1]['approved'])

    def test_an_ambiguous_shared_anchor_needs_more_identifying_context(self):
        """A label drawn in both figures is not an identity; the run fails rather than guess."""
        figures=[blog_brief('fig1',illustration='tokens',title='Why a fixed rule fails'),
                 blog_brief('fig2',illustration='tokens',title='Selective scan keeps tokens')]
        text=('The methods differ [p00001].\n\n{{figure:fig1}}\n\n{{figure:fig2}}\n\n'
              'Only these tasks were evaluated [p00001].')
        labels={'fig1':['tokens','fixed rule'],'fig2':['tokens','HBM']}
        ambiguous=verdict(review_issue(category='readability',path='fig1',anchor='tokens',
                                       message='The tokens label collides with a connector.'))
        steps=[*self.authoring(figures=figures,text=text),self.drawing_labels(labels),
               self.drawing_labels(labels),ambiguous,ambiguous]
        with self.assertRaises(ProviderError) as caught:
            self.run_steps(steps)
        self.assertIn('visible in fig1, fig2',str(caught.exception))
        self.assertEqual(2,len(self.drawing_calls()))

    def test_a_contextualized_anchor_repairs_the_named_figure_within_the_protocol_budget(self):
        """The correction allowance turns an ambiguous label into a distinctive anchor."""
        figures=[blog_brief('fig1',illustration='tokens',title='Why a fixed rule fails'),
                 blog_brief('fig2',illustration='tokens',title='Selective scan keeps tokens')]
        text=('The methods differ [p00001].\n\n{{figure:fig1}}\n\n{{figure:fig2}}\n\n'
              'Only these tasks were evaluated [p00001].')
        labels={'fig1':['tokens','fixed rule'],'fig2':['tokens','HBM']}
        steps=[*self.authoring(figures=figures,text=text),
               self.drawing_labels(labels),self.drawing_labels(labels),
               verdict(review_issue(category='readability',path='fig1',anchor='tokens',
                                    message='The tokens label collides with a connector.')),
               verdict(review_issue(category='readability',path='fig1',anchor='fixed rule',
                                    message='The tokens label collides with a connector.')),
               self.drawing_labels(labels),
               verdict(resolutions=resolve(quote='fixed rule'))]
        result=self.run_steps(steps)
        self.assertEqual([('fig1',2),('fig2',1)],
                         [(item['id'],item['attempts']) for item in result['provenance']['figure_outcomes']])
        drawings=self.drawing_calls()
        self.assertEqual(3,len(drawings))
        self.assertIn('panel id: fig1',json.dumps(drawings[2].args[0]))

    def test_a_finding_on_an_omitted_figure_never_reopens_it(self):
        """An omitted drawing's finding is a prose problem; it draws nothing and stays closed."""
        steps,_=self.omission_steps(1,(1,))
        steps.extend([verdict(review_issue(category='readability',path='fig1',anchor='Same input',
                                           message='The omitted drawing is still unclear.'),
                              approved=False),
                      self.prose_edit('The operation for figure 1 is explained directly [p00001].',
                                      'The operation is explained directly here [p00001].'),
                      verdict(resolutions=resolve(quote='explained directly here'))])
        result=self.run_steps(steps)
        self.assertEqual([],result['figures'])
        self.assertEqual(4,len(self.drawing_calls()),'omission is terminal')
        self.assertEqual(4,result['provenance']['figure_outcomes'][0]['attempts'])
        self.assertTrue(result['provenance']['reviews'][-1]['approved'])

    def test_figure_issue_targets_use_the_stable_id(self):
        from papers.agent_overviews import _figure_issue_target
        self.assertEqual('fig2',_figure_issue_target('fig2',['fig1','fig2','fig3']))
        self.assertEqual('fig3',_figure_issue_target('figures[2].label',['fig1','fig2','fig3']))
        self.assertIsNone(_figure_issue_target('article',['fig1']))
        self.assertIsNone(_figure_issue_target('The figure is unclear.',['fig1']))
        self.assertEqual('fig1',_figure_issue_target('figures[0]',['fig1','fig3']))

    def test_remove_omitted_markers_keeps_text_outside_the_marker(self):
        text='Opening stays.\n\n{{figure:fig2}}\n\nEnding stays.'
        self.assertEqual('Opening stays.\n\nEnding stays.',remove_omitted_markers(text,['fig2']))
        inline='A sentence {{figure:fig2}} continues.'
        self.assertEqual('A sentence  continues.',remove_omitted_markers(inline,['fig2']))

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

    def test_figure_issue_targets_use_the_stable_id(self):
        from papers.agent_overviews import _figure_issue_target
        self.assertEqual('fig2',_figure_issue_target('fig2',['fig1','fig2','fig3']))
        self.assertEqual('fig3',_figure_issue_target('figures[2].label',['fig1','fig2','fig3']))
        self.assertIsNone(_figure_issue_target('article',['fig1']))
        self.assertIsNone(_figure_issue_target('The figure is unclear.',['fig1']))
        self.assertEqual('fig1',_figure_issue_target('figures[0]',['fig1','fig3']))

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

    def test_remove_omitted_markers_keeps_text_outside_the_marker(self):
        text='Opening stays.\n\n{{figure:fig2}}\n\nEnding stays.'
        self.assertEqual('Opening stays.\n\nEnding stays.',remove_omitted_markers(text,['fig2']))
        inline='A sentence {{figure:fig2}} continues.'
        self.assertEqual('A sentence  continues.',remove_omitted_markers(inline,['fig2']))

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

    def test_blog_uses_a_reviewed_overview_as_a_drawing_reference(self):
        overview=self.saved_overview();before=copy.deepcopy(overview)
        steps=[action('submit_selection',candidate=selection_for()),
               action('submit_plan',candidate=plan_for()),
               action('read_overview_figure',reference='overview_fig1'),
               action('submit_draft',candidate=draft_for()),
               self.drawing(),verdict()]
        result=self.run_steps(steps,image_overview=overview)
        self.assertEqual(overview,before)
        self.assertEqual('saved-time',result['provenance']['overview_basis']['created_at'])
        manifest=json.dumps(self.provider.complete.call_args_list[2].args[0])
        self.assertIn('overview_fig1',manifest)
        tool_result=json.dumps(self.provider.complete.call_args_list[3].args[0])
        self.assertIn('Overview',tool_result)
        self.assertEqual('fig1',result['figures'][0]['id'])
        self.assertIn('Same input',result['figures'][0]['source_svg'])
        self.assertNotIn('source_html',result['figures'][0])

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
