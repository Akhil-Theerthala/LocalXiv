import copy
import unittest
from papers.explanation import validate_plan, expand_candidate
from papers.prototypes.parallel_scene import render_parallel_scene
from papers.html_figures import sanitize
from tests.test_agent_overviews import CANDIDATE, plan_for, draft_for

SCENE={'kind':'parallel-composition','input':'Illustrative: 4',
       'branches':[{'operation':'Add one','result':'4 + 1 = 5'},
                   {'operation':'Multiply by two','result':'4 x 2 = 8'}],
       'combine':'Add both results','output':'5 + 8 = 13',
       'context':'Example parallel block. The same input reaches each branch before the results are combined.'}


class ExplanationTests(unittest.TestCase):
    def test_each_claim_and_relationship_requires_its_own_evidence(self):
        doc={'passages':[{'id':'p00001'}]}
        self.assertEqual(plan_for(),validate_plan(plan_for(),doc))
        for name in ('question','contribution','finding','limitation'):
            bad=plan_for();bad[name]['passages']=['p99999']
            with self.assertRaises(ValueError):validate_plan(bad,doc)
        bad=plan_for();bad['relationships'][0]['passages']=[]
        with self.assertRaises(ValueError):validate_plan(bad,doc)

    def test_metadata_is_derived_from_plan_and_input_is_not_mutated(self):
        draft=draft_for();before=copy.deepcopy(draft)
        draft['contribution']='Untrusted duplicate field'
        expanded=expand_candidate(draft,{'passages':[{'id':'p00001'}]})
        self.assertEqual(CANDIDATE['contribution'],expanded['contribution'])
        self.assertEqual(before['plan'],draft['plan'])
        expanded['plan']['finding']['text']='Changed'
        self.assertEqual(before['plan'],draft['plan'])

    def test_parallel_scene_is_optional_escaped_and_rejects_wrong_relationships(self):
        scene=copy.deepcopy(SCENE);scene['input']='<script>&'
        html=render_parallel_scene(scene)
        self.assertIn('&lt;script&gt;&amp;',html)
        self.assertIn('polyline',sanitize(html))
        for change in ({'branches':[]},{'input':'x'*43},{'kind':'arbitrary-code'}):
            with self.assertRaises(ValueError):render_parallel_scene(dict(SCENE,**change))
