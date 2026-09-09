import copy
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from papers.overview import clean_citations, validate_outline, validate_article, validate_figure, render_figure
from papers.ai import _sources, ProviderError
from tests.overview_fixture import PLAN, SPEC, ARTICLE

class OverviewTests(unittest.TestCase):
    def test_grouped_citations_disappear_but_evidence_is_retained(self):
        value = 'Result [p00001, p00007; p00053]. Keep [2025], x[0], and 91.3% [p00001].'
        self.assertEqual('Result. Keep [2025], x[0], and 91.3%.', clean_citations(value))
        self.assertEqual('    keep  spacing\n', clean_citations('    keep  spacing [p00001]\n'))
        refs = _sources(value, [{'id': p} for p in ('p00001','p00007','p00053')])
        self.assertEqual(['p00001','p00007','p00053'], [r['id'] for r in refs])
        with self.assertRaises(ProviderError):
            _sources('[p00001, p99999]', [{'id':'p00001'}])

    def test_article_and_figure_contracts(self):
        plan = validate_outline(copy.deepcopy(PLAN), [{'id':'p00001'}])
        validate_article(ARTICLE, plan)
        for text in (ARTICLE.replace('# What', '# Different'), ARTICLE.replace('{Insert figure|','{Lost|')):
            with self.assertRaises(ValueError): validate_article(text, plan)
        for change in ({'focus': True}, {'arrows': ['invented causation']}, {'nodes': []}, {'title': 'x'*100}):
            with self.assertRaises(ValueError): validate_figure(dict(SPEC, **change))

    def test_actual_sequence_render_and_assets_are_immutable(self):
        spec = dict(SPEC, layout='sequence', arrows=['Check against outcomes'])
        with tempfile.TemporaryDirectory() as directory:
            first = render_figure(directory, 'fig1', spec)
            second = render_figure(directory, 'fig1', spec)
            self.assertNotEqual(first['svg'], second['svg'])
            scene = ET.parse(Path(directory)/first['svg']).getroot()
            self.assertEqual('{http://www.w3.org/2000/svg}svg', scene.tag)
            self.assertIn('Check against outcomes', ' '.join(' '.join(e.itertext()) for e in scene.findall('.//{*}text')).replace('\n', ' '))
            self.assertGreater(float(scene.get('width')), float(scene.get('height')))
            self.assertEqual({'fig1.svg', 'fig1.png', 'fig1.excalidraw'}, {p.name for p in (Path(directory)/first['svg']).parent.iterdir()})
            self.assertEqual([], first['checks']['warnings'])

    def test_four_step_diagram_fits_a_square_instead_of_a_vertical_stack(self):
        spec = dict(SPEC, layout='sequence', nodes=SPEC['nodes']*2, arrows=['Compare','Check','Conclude'])
        with tempfile.TemporaryDirectory() as directory:
            result = render_figure(directory, 'four', spec)
            svg = ET.parse(Path(directory)/result['svg']).getroot()
            width, height = float(svg.get('width')), float(svg.get('height'))
            self.assertLessEqual(height / width, 1.25)
            self.assertEqual([],result['checks']['warnings'])


    def test_narrative_requires_pain_point_and_prior_work_before_method(self):
        for changes in ({'opening': []}, {'opening': ['A.']*4}, {'sections': list(reversed(PLAN['sections']))}):
            with self.assertRaises(ValueError):
                validate_outline(dict(copy.deepcopy(PLAN), **changes), [{'id':'p00001'}])
        with self.assertRaises(ValueError):
            validate_article(ARTICLE.split('\n\n', 1)[1], PLAN)
