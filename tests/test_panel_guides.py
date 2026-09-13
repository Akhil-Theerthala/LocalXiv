"""Panel SVG construction contract: guide examples, the panel profile, and native measurement.

The native cases need LOCALXIV_HTML_RENDERER. Set it with:

    xcrun swiftc -O papers/HTMLSnapshot.swift -o .scratch/overview-rebuild/html-snapshot
    LOCALXIV_HTML_RENDERER="$PWD/.scratch/overview-rebuild/html-snapshot" \
        .scratch/overview-agent-env/bin/python -m unittest tests.test_panel_guides
"""
import os
import struct
import tempfile
import unittest
import zlib
from pathlib import Path

from papers import html_figures
from papers.panel_authoring import (CONSTRUCTION_FAMILIES, authoring_guide, construction_notes,
                                    guide_examples, reference_examples)

GUIDES = Path(__file__).resolve().parent.parent / 'papers' / 'panel-guides'
NATIVE = os.environ.get('LOCALXIV_HTML_RENDERER')


def read_png(path):
    """Decode an 8-bit non-interlaced PNG to rows of RGB triples (stdlib only)."""
    data = Path(path).read_bytes()
    assert data[:8] == b'\x89PNG\r\n\x1a\n', 'not a PNG'
    position, compressed, header = 8, b'', None
    while position < len(data):
        length, kind = struct.unpack('>I4s', data[position:position + 8])
        chunk = data[position + 8:position + 8 + length]
        if kind == b'IHDR':
            width, height, depth, colour, _, _, interlace = struct.unpack('>IIBBBBB', chunk)
            header = (width, height, depth, colour, interlace)
        elif kind == b'IDAT':
            compressed += chunk
        position += 12 + length
    width, height, depth, colour, interlace = header
    assert depth == 8 and interlace == 0, 'unsupported PNG encoding'
    channels = {0: 1, 2: 3, 4: 2, 6: 4}[colour]
    raw = zlib.decompress(compressed)
    stride = width * channels
    rows, previous = [], bytearray(stride)
    for index in range(height):
        filter_type = raw[index * (stride + 1)]
        line = bytearray(raw[index * (stride + 1) + 1:(index + 1) * (stride + 1)])
        for offset in range(stride):
            left = line[offset - channels] if offset >= channels else 0
            up = previous[offset]
            corner = previous[offset - channels] if offset >= channels else 0
            if filter_type == 1:
                line[offset] = (line[offset] + left) & 255
            elif filter_type == 2:
                line[offset] = (line[offset] + up) & 255
            elif filter_type == 3:
                line[offset] = (line[offset] + (left + up) // 2) & 255
            elif filter_type == 4:
                estimate = left + up - corner
                distances = (abs(estimate - left), abs(estimate - up), abs(estimate - corner))
                predictor = (left, up, corner)[distances.index(min(distances))]
                line[offset] = (line[offset] + predictor) & 255
        rows.append(bytes(line))
        previous = line
    return width, height, channels, rows


def figure(source, identifier='fig1'):
    return {'id': identifier, 'title': 'Panel fixture', 'paper_connection': 'Fixture only.',
            'caption': 'Fixture only.', 'illustrative': True, 'source_svg': source}


class GuideTests(unittest.TestCase):
    def test_the_five_reference_examples_exist_and_validate_in_the_panel_profile(self):
        self.assertEqual(['calculation', 'chart', 'comparison', 'flow', 'mapping'],
                         sorted(path.stem for path in GUIDES.glob('*.svg')))
        for name in sorted(path.stem for path in GUIDES.glob('*.svg')):
            with self.subTest(name=name):
                source = html_figures.normalize_panel_svg((GUIDES / f'{name}.svg').read_text())
                self.assertIn('viewBox="0 0 ', source)

    def test_examples_carry_no_css_variables_classes_or_styles(self):
        for path in GUIDES.glob('*.svg'):
            with self.subTest(name=path.name):
                text = path.read_text()
                for token in ('var(--', 'class=', 'style=', '<defs', '<marker', '<use'):
                    self.assertNotIn(token, text)

    def test_the_authoring_guide_states_the_contract_the_profile_enforces(self):
        guide = authoring_guide()
        for phrase in ('font-size="18"', 'font-size="14"', 'tspan', 'arrowhead', 'viewBox',
                       'self-contained', '#2f6f5e'):
            self.assertIn(phrase, guide)
        self.assertIn('w3schools.com/graphics/svg_reference.asp', construction_notes())
        self.assertEqual(['calculation', 'chart', 'comparison', 'flow', 'mapping'],
                         sorted(entry['family'] for entry in guide_examples()))
        for entry in guide_examples():
            self.assertTrue(entry['svg'].startswith('<svg'))
            self.assertTrue(entry['path'].endswith('.svg'))

    def test_a_panel_receives_at_most_two_relevant_complete_examples(self):
        for family in CONSTRUCTION_FAMILIES:
            with self.subTest(family=family):
                examples = reference_examples(family)
                self.assertEqual(family, examples[0]['family'])
                self.assertLessEqual(len(examples), 2)
                self.assertTrue(all(example['svg'].startswith('<svg') for example in examples))
        with self.assertRaises(ValueError):
            reference_examples('network')


class PanelProfileTests(unittest.TestCase):
    def test_panel_profile_accepts_content_sized_canvases_and_guide_typography(self):
        source = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 2400 1500" font-size="14">'
                  '<text x="20" y="40">Small but allowed here</text></svg>')
        self.assertIn('viewBox="0 0 2400 1500"', html_figures.normalize_svg(source, profile='panel'))
        for legacy_profile in ('legacy',):
            with self.assertRaises(html_figures.SVGValidationError):
                html_figures.normalize_svg(source, profile=legacy_profile)

    def test_panel_profile_still_rejects_local_definitions_and_active_content(self):
        for body in ('<defs><marker id="m"><path d="M 0 0 L 1 1"/></marker></defs>',
                     '<script>alert(1)</script>',
                     '<rect x="0" y="0" width="10" height="10" onclick="x()"/>'):
            with self.subTest(body=body), self.assertRaises(html_figures.SVGValidationError):
                html_figures.normalize_panel_svg(
                    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200">' + body + '</svg>')

    def test_composed_overview_profile_allows_seven_panel_budgets(self):
        body = '<rect x="10" y="10" width="40" height="40" fill="#dce8cf"/>' * 60
        panel = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 700" font-size="18">'
                 + '<rect x="0" y="0" width="900" height="700" fill="#ffffff"/>' + body * 9 + '</svg>')
        with self.assertRaises(html_figures.SVGValidationError):
            html_figures.normalize_svg(panel, profile='panel')
        self.assertIn('<rect', html_figures.normalize_svg(panel, profile='overview'))


@unittest.skipUnless(NATIVE, 'Set LOCALXIV_HTML_RENDERER for native rendering checks')
class NativePanelTests(unittest.TestCase):
    def render(self, source, mode='panel'):
        with tempfile.TemporaryDirectory() as directory:
            return html_figures.render(directory, figure(source), 'Fixture', mode=mode)

    def test_every_reference_example_renders_without_a_geometry_issue(self):
        for path in sorted(GUIDES.glob('*.svg')):
            with self.subTest(name=path.name):
                checks = self.render(path.read_text())['checks']
                self.assertEqual([], checks['issue_details'])
                self.assertEqual('panel', checks['mode'])
                self.assertGreater(checks['canvas']['width'], 0)
                self.assertGreaterEqual(min(run['displayed_size_px'] for run in checks['text_runs']), 14)

    def test_wide_tall_and_large_shapes_measure_their_own_canvas(self):
        cases = {
            'wide': ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1800 200" font-size="18">'
                     '<rect x="10" y="10" width="1780" height="180" fill="#f3f6f0"/>'
                     '<text x="40" y="100">A wide panel with one long row</text></svg>', (1800, 200)),
            'tall': ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 1600" font-size="18">'
                     '<circle cx="150" cy="800" r="140" fill="#e1ebf1"/>'
                     '<text x="150" y="806" text-anchor="middle">A tall panel with a large circle</text></svg>', (300, 1600)),
            'transformed': ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300" font-size="18">'
                            '<g transform="translate(40 40) scale(1.1)">'
                            '<rect x="0" y="0" width="280" height="80" rx="8" fill="#dce8cf"/>'
                            '<text x="20" y="48">A transformed group</text></g></svg>', (400, 300)),
        }
        for name, (source, canvas) in cases.items():
            with self.subTest(name=name):
                checks = self.render(source)['checks']
                self.assertEqual([], checks['issue_details'])
                self.assertEqual(canvas, (checks['canvas']['width'], checks['canvas']['height']))
                self.assertTrue(checks['elements'])

    def test_escaped_path_beyond_a_small_canvas_is_reported_with_measurements(self):
        source = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200" font-size="18">'
                  '<path d="M 0 0 L 900 900" stroke="black"/><text x="20" y="40">Example</text></svg>')
        checks = self.render(source)['checks']
        issue = next(item for item in checks['issue_details'] if item['code'] == 'out_of_bounds')
        self.assertGreater(issue['actual'], issue['limit'])
        self.assertEqual(0, issue['limit'])

    def test_strokes_arrowheads_tspans_and_long_labels_stay_inside_the_canvas(self):
        source = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 320" font-size="18">'
                  '<text x="20" y="40">Value '
                  '<tspan font-weight="bold">mixing</tspan></text>'
                  '<text x="20" y="80">a label that is wrapped<tspan x="20" dy="24">onto a second line</tspan></text>'
                  '<rect x="20" y="140" width="600" height="60" rx="8" fill="#f3f6f0" stroke="#dce1d8"/>'
                  '<text x="40" y="178" font-size="16">Generous room for a secondary explanation</text>'
                  '<line x1="40" y1="250" x2="520" y2="250" stroke="#2f6f5e" stroke-width="3"/>'
                  '<path d="M 520 242 L 534 250 L 520 258 Z" fill="#2f6f5e"/>'
                  '<path d="M 60 290 C 180 260 300 320 420 290" fill="none" stroke="#243b32" stroke-width="2"/></svg>')
        checks = self.render(source)['checks']
        self.assertEqual([], checks['issue_details'])
        self.assertEqual(5, len(checks['text_runs']))
        self.assertEqual(640, checks['canvas']['width'])

    def test_an_overview_sized_canvas_renders_readable_text_above_960px(self):
        rows = ''.join(
            f'<rect x="20" y="{40 + index * 150}" width="1360" height="120" rx="10" fill="#f3f6f0" '
            f'stroke="#dce1d8"/><text x="60" y="{110 + index * 150}" font-size="20">Panel row {index + 1}</text>'
            for index in range(7))
        source = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1400 1120" font-size="18">'
                  f'{rows}</svg>')
        with tempfile.TemporaryDirectory() as directory:
            result = html_figures.render(directory, figure(source), 'Fixture', mode='overview')
            checks = result['checks']
            width, height, _, _ = read_png(Path(directory) / result['png'])
        self.assertEqual([], checks['issue_details'])
        self.assertEqual((1400, 1120), (checks['canvas']['width'], checks['canvas']['height']))
        self.assertEqual('overview', checks['mode'])
        self.assertGreater(width, 960)
        self.assertGreater(height, 960)
        self.assertEqual(width / checks['canvas']['width'], height / checks['canvas']['height'],
                         'the raster must keep one uniform scale')
        self.assertEqual(0, width % checks['canvas']['width'])

    def test_a_tall_canvas_is_rasterized_as_tiles_and_reassembled_in_order(self):
        source = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 8300 160" font-size="18">'
                  '<rect x="0" y="0" width="200" height="160" fill="#ff0000"/>'
                  '<rect x="8100" y="0" width="200" height="160" fill="#0000ff"/>'
                  '<text x="4000" y="90" text-anchor="middle">Connector across the seam</text></svg>')
        with tempfile.TemporaryDirectory() as directory:
            result = html_figures.render(directory, figure(source), 'Fixture', mode='panel')
            checks = result['checks']
            self.assertEqual([], checks['issue_details'])
            width, height, channels, rows = read_png(Path(directory) / result['png'])
        self.assertEqual(8300, checks['canvas']['width'])
        self.assertEqual(160, checks['canvas']['height'])
        self.assertEqual(0, width % 8300)
        scale = width // 8300

        def colour(row, x):
            return tuple(rows[row][x * scale * channels:x * scale * channels + 3])

        self.assertEqual((255, 0, 0), colour(80, 20), 'left band moved')
        self.assertEqual((0, 0, 255), colour(80, 8200), 'right band moved or the seam duplicated')
        # The centred label sits on a tile seam (page x=4096 for 2048-unit tiles).
        inked = [(row, x) for row in range(70 * scale, 100 * scale)
                 for x in range(3900 * scale, 4100 * scale)
                 if tuple(rows[row][x * channels:x * channels + 3]) != (255, 255, 255)]
        self.assertTrue(inked, 'text lost at a tile seam')
        for x in (2047, 2048, 2049, 4095, 4096, 4097, 6144, 6145):
            self.assertEqual((255, 255, 255), colour(4, x), f'empty row changed at tile seam x={x}')

    def test_tile_assembly_keeps_the_panel_scale_when_the_canvas_exceeds_the_safe_raster(self):
        source = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1900 9000" font-size="18">'
                  '<rect x="0" y="0" width="1900" height="200" fill="#ff0000"/>'
                  '<rect x="0" y="8800" width="1900" height="200" fill="#0000ff"/>'
                  '<text x="100" y="4500">Middle of the canvas</text></svg>')
        with tempfile.TemporaryDirectory() as directory:
            result = html_figures.render(directory, figure(source), 'Fixture', mode='panel')
            width, height, channels, rows = read_png(Path(directory) / result['png'])
        self.assertEqual((1900, 9000), (width, height))
        self.assertEqual(b'\xff\x00\x00', rows[10][20 * channels:20 * channels + 3])
        self.assertEqual(b'\x00\x00\xff', rows[8990][20 * channels:20 * channels + 3])
        runs = [run for run in result['checks']['text_runs'] if 'Middle' in run['text']]
        self.assertEqual(18, runs[0]['displayed_size_px'])


if __name__ == '__main__':
    unittest.main()
