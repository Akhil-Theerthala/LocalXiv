"""Run with LOCALXIV_HTML_RENDERER pointing to a compiled HTMLSnapshot.swift."""
import os
from pathlib import Path
import struct
import tempfile
import unittest
import xml.etree.ElementTree as ET

from papers.arrangement import arrange, panel_record
from papers.html_figures import compose_figure, normalize_panel_svg, render

GUIDES = Path(__file__).resolve().parent.parent / 'papers' / 'panel-guides'


@unittest.skipUnless(os.environ.get('LOCALXIV_HTML_RENDERER'), 'Set LOCALXIV_HTML_RENDERER for native rendering checks')
class ReadabilityTests(unittest.TestCase):
    def figure(self, source):
        return {
            'id':'fig1',
            'title':'A compact explanation',
            'paper_connection':'A synthetic fixture that checks the native SVG path.',
            'caption':'Synthetic geometry, not a paper finding.',
            'illustrative':True,
            'source_svg':source,
        }

    def svg(self, body, height=240):
        return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 880 {height}">{body}</svg>'

    def test_distinct_architecture_method_and_comparison_compositions_render(self):
        fixture_dir=Path(__file__).parent/'fixtures'/'svg-overviews'
        sources={name:(fixture_dir/f'{name}.source.svg').read_text()
                 for name in ('architecture','method','comparison')}
        with tempfile.TemporaryDirectory() as directory:
            for name, source in sources.items():
                with self.subTest(name=name):
                    result=render(directory,self.figure(source),'Layout fixture',compact=True)
                    self.assertLessEqual(result['checks']['height'],960)
                    self.assertEqual([],result['checks']['issues'])
                    editable=ET.parse(os.path.join(directory,result['svg_source'])).getroot()
                    tags=[item.tag.rsplit('}',1)[-1] for item in editable.iter()]
                    self.assertIn('text',tags)
                    self.assertNotIn('image',tags)

    def test_portrait_figure_is_fitted_into_the_page(self):
        source=self.svg('<text x="20" y="60" font-size="44">Readable portrait label</text>',1100)
        with tempfile.TemporaryDirectory() as directory:
            checks=render(directory,self.figure(source),'Test',compact=True)['checks']
        self.assertLessEqual(checks['height'],960)
        self.assertEqual([],checks['issues'])
        self.assertGreaterEqual(min(run['displayed_size_px'] for run in checks['text_runs']),14)
        self.assertGreater(checks['diagram']['available_height'],0)

    def test_overview_bounds_include_header_footer_and_diagram(self):
        with tempfile.TemporaryDirectory() as directory:
            compact=render(directory,self.figure(self.svg(
                '<text x="20" y="60" font-size="28">Readable example</text>',600)),
                'Test',compact=True)['checks']
            self.assertLessEqual(compact['height'],960)
            self.assertEqual([],compact['issues'])

            tall=render(directory,self.figure(self.svg(
                '<text x="20" y="60" font-size="28">Readable example</text>',1200)),
                'Test',compact=True)['checks']
            self.assertLessEqual(tall['height'],960)
            self.assertGreater(tall['page']['height'],tall['diagram']['height'])
            self.assertGreater(tall['diagram']['available_height'],0)

    def test_native_issues_report_locations_and_measurements(self):
        cases = [
            ('small', self.svg('<text id="small" x="20" y="60" font-size="20">Too small after scaling</text>'), 'text_too_small'),
            ('overlap', self.svg('<text id="one" x="20" y="60" font-size="28">First label</text><text id="two" x="20" y="60" font-size="28">Second label</text>'), 'text_overlap'),
            ('outside', self.svg('<circle id="outside" cx="900" cy="50" r="40" fill="#dce8cf"/>'), 'out_of_bounds'),
            ('scaled', self.svg('<g transform="scale(.5)"><text id="scaled" x="20" y="60" font-size="28">Scaled too small</text></g>'), 'text_too_small'),
        ]
        with tempfile.TemporaryDirectory() as directory:
            for name, source, code in cases:
                with self.subTest(name=name):
                    checks=render(directory,self.figure(source),'Test',compact=True)['checks']
                    issue=next(item for item in checks['issue_details'] if item['code']==code)
                    self.assertIn('path',issue)
                    self.assertIn('actual',issue)
                    self.assertIn('limit',issue)

    def test_tightly_stacked_lines_are_not_reported_as_overlap(self):
        source=self.svg(
            '<text id="heading" x="20" y="40" font-size="26" font-weight="700">A heading</text>'
            '<text id="support" x="20" y="62" font-size="24">A supporting line beneath it</text>')
        with tempfile.TemporaryDirectory() as directory:
            checks=render(directory,self.figure(source),'Test',compact=True)['checks']
        self.assertNotIn('text_overlap',{item['code'] for item in checks['issue_details']})

    def test_label_that_escapes_its_container_is_reported(self):
        source=self.svg(
            '<rect id="tight-box" x="20" y="20" width="130" height="64" rx="8" fill="#dce8cf"/>'
            '<text id="overlong" x="30" y="60" font-size="26" font-weight="700">Overlong label</text>'
            '<rect id="wide-box" x="240" y="20" width="420" height="64" rx="8" fill="#e1ebf1"/>'
            '<text id="contained" x="260" y="60" font-size="26">Short</text>')
        with tempfile.TemporaryDirectory() as directory:
            checks=render(directory,self.figure(source),'Test',compact=True)['checks']
        overflow=[item for item in checks['issue_details']
                  if item.get('constraint')=='maximum_text_container_overflow_px']
        self.assertEqual(['#overlong'],[item['path'] for item in overflow])
        self.assertGreater(overflow[0]['actual'],overflow[0]['limit'])
        self.assertNotIn('#contained',[item['path'] for item in checks['issue_details']])

    def test_clipped_arrowhead_is_reported(self):
        source=self.svg(
            '<defs><marker id="wide-arrow" viewBox="0 0 20 10" markerWidth="20" markerHeight="10" '
            'refX="2" refY="5" orient="auto"><path d="M 0 0 L 20 5 L 0 10 Z" fill="#243b32"/></marker></defs>'
            '<path id="edge-arrow" d="M 700 80 L 875 80" fill="none" stroke="#243b32" stroke-width="4" '
            'marker-end="url(#wide-arrow)"/>')
        with tempfile.TemporaryDirectory() as directory:
            checks=render(directory,self.figure(source),'Test',compact=True)['checks']
        issue=next(item for item in checks['issue_details']
                   if item['code']=='out_of_bounds' and 'edge-arrow' in item['path'])
        self.assertGreater(issue['actual'],issue['limit'])


class ComposedOverviewTests(unittest.TestCase):
    """A composed overview keeps each panel's own measurement, content, and export size."""

    NAMES = ('flow', 'mapping', 'comparison', 'calculation', 'chart', 'flow', 'chart')

    def panel_source(self, name):
        return normalize_panel_svg((GUIDES / (name + '.svg')).read_text())

    def overview(self, directory, names=None):
        names = names or self.NAMES
        sources, records = {}, []
        for index, name in enumerate(names, 1):
            identifier = f'p{index}'
            sources[identifier] = self.panel_source(name)
            records.append(panel_record(identifier, sources[identifier], title=name))
        layout = arrange(records)
        document = compose_figure(sources, layout)
        figure = {'id': 'fig1', 'title': 'Composed overview', 'paper_connection': 'Fixture.',
                  'caption': 'Fixture.', 'illustrative': False, 'source_svg': document}
        result = render(directory, figure, 'Fixture', mode='overview')
        return layout, document, result

    def test_text_size_and_position_survive_a_large_composition(self):
        alone = self.panel_source('chart')
        layout, document, result = self.overview(tempfile.mkdtemp())
        alone_result = render(tempfile.mkdtemp(),
                              {'id': 'p5', 'title': 'Chart', 'paper_connection': '', 'caption': '',
                               'illustrative': False, 'source_svg': alone}, 'Fixture', mode='panel')
        self.assertEqual([], alone_result['checks']['issue_details'])
        self.assertEqual([], result['checks']['issue_details'])
        self.assertGreater(layout['canvas']['width'], 0)
        placement = next(item for item in layout['placements'] if item['id'] == 'p5')
        label = next(run for run in alone_result['checks']['text_runs'] if run['text'] == '2.5')
        composed_label = next(run for run in result['checks']['text_runs'] if run['text'] == '2.5')
        self.assertAlmostEqual(label['displayed_size_px'] * placement['scale'],
                               composed_label['displayed_size_px'], delta=0.35)
        alone_box = next(item for item in alone_result['checks']['elements'] if item['path'] == label['path'])
        composed_box = next(item for item in result['checks']['elements']
                            if item['path'] == composed_label['path'])
        self.assertAlmostEqual(placement['x'] + alone_box['left'] * placement['scale'],
                               composed_box['left'], delta=0.75)
        self.assertAlmostEqual(placement['y'] + alone_box['top'] * placement['scale'],
                               composed_box['top'], delta=0.75)

    def test_a_mixed_width_plan_produces_a_composition_over_960px_in_both_axes(self):
        sources, records = {}, []
        for index in range(1, 5):
            identifier = f'p{index}'
            source = normalize_panel_svg(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 520" font-size="18">'
                f'<rect x="20" y="30" width="460" height="180" rx="10" fill="#dce8cf"/>'
                f'<text x="40" y="130">Narrow panel {index}</text>'
                '<path d="M 20 300 L 480 300" fill="none" stroke="#243b32" marker-end="url(#arrow)"/>'
                '<path d="M 20 460 C 160 380 340 520 480 440" fill="none" stroke="#2f6f5e" stroke-width="2"/></svg>')
            sources[identifier] = source
            records.append(panel_record(identifier, source))
        layout = arrange(records)
        document = compose_figure(sources, layout)
        figure = {'id': 'fig1', 'title': 'Composed', 'paper_connection': '', 'caption': '',
                  'illustrative': False, 'source_svg': document}
        with tempfile.TemporaryDirectory() as directory:
            checks = render(directory, figure, 'Fixture', mode='overview')['checks']
        self.assertEqual([], checks['issue_details'])
        self.assertGreaterEqual(layout['columns'], 2)
        self.assertGreater(checks['canvas']['width'], 960)
        self.assertGreater(checks['canvas']['height'], 960)
        self.assertGreaterEqual(min(run['displayed_size_px'] for run in checks['text_runs']), 14)

    def test_png_pdf_source_and_compatibility_svg_agree_on_the_composed_size(self):
        with tempfile.TemporaryDirectory() as directory:
            layout, document, result = self.overview(directory)
            directory = Path(directory)
            checks = result['checks']
            canvas = (checks['canvas']['width'], checks['canvas']['height'])
            png = (directory / result['png']).read_bytes()
            width, height = struct.unpack('>II', png[16:24])
            self.assertEqual(0, width % int(canvas[0]))
            scale = width // int(canvas[0])
            self.assertLessEqual(abs(width - canvas[0] * scale), 1)
            self.assertLessEqual(abs(height - canvas[1] * scale), 1)
            source = ET.parse(directory / result['svg_source']).getroot()
            self.assertEqual([0, 0, canvas[0], canvas[1]],
                             [float(value) for value in source.get('viewBox').split()])
            compatibility = ET.parse(directory / result['svg']).getroot()
            self.assertEqual(canvas[0], float(compatibility.get('width')))
            self.assertEqual(canvas[1], float(compatibility.get('height')))
            self.assertEqual([0, 0, canvas[0], canvas[1]],
                             [float(value) for value in compatibility.get('viewBox').split()])
            pdf = (directory / result['pdf']).read_bytes()
            self.assertTrue(pdf.startswith(b'%PDF-'))
            self.assertGreater(len(pdf), 1000)
            self.assertIn('</svg>', document)

    def test_no_panel_is_drawn_between_the_panels_or_reordered(self):
        with tempfile.TemporaryDirectory() as directory:
            layout, document, result = self.overview(directory)
        self.assertEqual([f'p{index}' for index in range(1, 8)],
                         [placement['id'] for placement in layout['placements']])
        for placement in layout['placements']:
            self.assertIn(f'<g id="panel-{placement["id"]}"', document)


if __name__ == '__main__':
    unittest.main()
