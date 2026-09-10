"""Run with LOCALXIV_HTML_RENDERER pointing to a compiled HTMLSnapshot.swift."""
import os
import tempfile
import unittest
from papers.html_figures import render


@unittest.skipUnless(os.environ.get('LOCALXIV_HTML_RENDERER'), 'Set LOCALXIV_HTML_RENDERER for native rendering checks')
class ReadabilityTests(unittest.TestCase):
    def test_parallel_architecture_scene_fits_without_label_collisions(self):
        import copy
        from tests.test_explanation import SCENE
        from papers.prototypes.parallel_scene import render_parallel_scene
        with tempfile.TemporaryDirectory() as directory:
            for count in (2,3):
                scene=copy.deepcopy(SCENE)
                if count==3:
                    scene['branches'].append({'operation':'Subtract one','result':'4 - 1 = 3'})
                    scene['output']='5 + 8 + 3 = 16'
                figure={'id':'fig1','title':'Combine parallel results','paper_connection':'A synthetic architecture fixture for checking layout.',
                        'caption':'Illustrative arithmetic, not a paper finding.','illustrative':True,
                        'html':render_parallel_scene(scene)}
                checks=render(directory,figure,'Layout fixture',compact=True)['checks']
                self.assertLessEqual(checks['height'],960)
                self.assertEqual([],checks['issues'])

    def test_overview_bounds_include_header_footer_and_all_panels(self):
        with tempfile.TemporaryDirectory() as directory:
            figure={'id':'fig1','title':'A compact explanation','paper_connection':'What the paper contributes.',
                    'caption':'Scope remains visible.','illustrative':True,
                    'html':'<svg viewBox="0 0 880 600"><text x="20" y="60" font-size="28">Readable example</text></svg>'}
            compact=render(directory,figure,'Test',compact=True)['checks']
            self.assertLessEqual(compact['height'],960)
            self.assertEqual([],compact['issues'])
            # Individually short SVGs must not bypass the complete page budget.
            figure['html']*=2
            tall=render(directory,figure,'Test',compact=True)['checks']
            self.assertGreater(tall['height'],960)
            self.assertTrue(any('maximum 960px' in issue for issue in tall['issues']))
            self.assertTrue(any('Small text' in issue for issue in tall['issues']))
            blog=render(directory,figure,'Test')['checks']
            self.assertFalse(any('maximum 960px' in issue for issue in blog['issues']))

    def test_labels_are_measured_at_reading_width_including_tspans(self):
        cases = [
            ('<text x="20" y="60" font-size="20">Too small after scaling</text>', True),
            ('<text x="20" y="60" font-size="28">Readable label</text>', False),
            ('<text x="20" y="60" font-size="28">Weight <tspan font-size="16">small detail</tspan></text>', True),
        ]
        with tempfile.TemporaryDirectory() as directory:
            for markup, small in cases:
                with self.subTest(markup=markup):
                    figure={'id':'fig1','title':'Compare tokens','paper_connection':'An illustrative comparison.',
                            'caption':'Teaching example.','illustrative':True,
                            'html':'<svg viewBox="0 0 880 200">'+markup+'</svg>'}
                    checks=render(directory,figure,'Test')['checks']
                    self.assertEqual(640,checks['reading_width'])
                    self.assertEqual(small,any('Small text at 640px' in i for i in checks['issues']))
                    if not small: self.assertEqual([],checks['issues'])
