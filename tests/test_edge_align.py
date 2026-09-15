"""Focused geometry checks for the promoted mixed and edge layout stages."""
import copy
import unittest

from papers.edge_align import align_outer_edges, edge_align_layout
from papers.html_figures import _panel_group, normalize_panel_svg
from papers.overview_workflow import _mixed_layout_choice


def panel(identifier='p1'):
    return {
        'id': identifier,
        'width': 100.0,
        'height': 100.0,
        'body_size': 18.0,
        'native_min_text_size': 18.0,
        'native_text_measured': True,
        'content_bounds': (10.0, 20.0, 90.0, 80.0),
    }


def layout(*frames, width=500.0, height=240.0):
    placements = []
    for number, (identifier, x, y, frame_width, frame_height) in enumerate(frames, 1):
        placements.append({
            'id': identifier,
            'x': x + 6.0,
            'y': y + 32.0,
            'width': 80.0,
            'height': 60.0,
            'scale': 1.0,
            'number': number,
            'frame': {'x': x, 'y': y, 'width': frame_width, 'height': frame_height},
        })
    return {
        'canvas': {'width': width, 'height': height},
        'placements': placements,
        'mixed': {'validated': True},
    }


class EdgeAlignTests(unittest.TestCase):
    def test_large_outer_gap_stretches_x_and_recomputes_source_origin(self):
        source = layout(('p1', 20.0, 30.0, 112.0, 128.0))
        before = copy.deepcopy(source)
        result = edge_align_layout([panel()], source)
        placement = result['placements'][0]

        self.assertTrue(result['edge_align']['validated'])
        self.assertTrue(result['edge_align']['changed'])
        self.assertEqual(1.0, placement['scale_y'])
        self.assertAlmostEqual(1.05, placement['scale_x'])
        self.assertEqual(before['canvas'], result['canvas'])
        self.assertEqual(before['placements'][0]['frame']['y'], placement['frame']['y'])
        self.assertEqual(before['placements'][0]['frame']['height'], placement['frame']['height'])
        self.assertEqual(116.0, placement['frame']['width'])
        self.assertEqual(25.5, placement['x'])
        self.assertEqual(before['placements'][0]['y'], placement['y'])

    def test_near_diagonal_neighbour_limits_whole_box_extension(self):
        panels = [panel('left'), panel('right')]
        source = layout(
            ('left', 20.0, 30.0, 112.0, 128.0),
            ('right', 148.0, 170.0, 112.0, 128.0),
            width=320.0,
            height=318.0,
        )
        result = edge_align_layout(panels, source)

        self.assertTrue(result['edge_align']['validated'])
        left = next(item for item in result['placements'] if item['id'] == 'left')
        self.assertLessEqual(left.get('scale_x', left['scale']), 1.05)
        self.assertAlmostEqual(16.0, next(item for item in result['edge_align']['pair_gaps']
                                          if item['first'] == 'left')['horizontal'])
        self.assertEqual(1.0, left.get('scale_x', left['scale']))
        for pair in result['edge_align']['pair_gaps']:
            self.assertTrue(pair['horizontal'] >= pair['required'] - 0.02
                            or pair['vertical'] >= pair['required'] - 0.02)

    def test_outer_translation_is_scale_free_and_idempotent(self):
        source = layout(('p1', 80.0, 30.0, 112.0, 128.0))
        aligned = align_outer_edges([panel()], source)

        self.assertTrue(aligned['outer_alignment']['validated'])
        self.assertTrue(aligned['outer_alignment']['changed'])
        self.assertEqual(source['placements'][0]['scale'], aligned['placements'][0]['scale'])
        self.assertEqual(source['placements'][0]['frame']['width'],
                         aligned['placements'][0]['frame']['width'])
        self.assertEqual(aligned['placements'],
                         align_outer_edges([panel()], aligned)['placements'])

    def test_edge_result_is_idempotent_and_compositor_accepts_two_scales(self):
        source = layout(('p1', 20.0, 30.0, 112.0, 128.0))
        result = edge_align_layout([panel()], source)

        self.assertEqual(result['placements'],
                         edge_align_layout([panel()], result)['placements'])
        svg = normalize_panel_svg(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
            '<text x="10" y="30">label</text></svg>')
        group = _panel_group(svg, result['placements'][0])
        self.assertIn('scale(1.05 1.0)', group)


class MixedChoiceTests(unittest.TestCase):
    def test_mixed_choice_keeps_aligned_geometry_within_tolerance(self):
        aligned = {'mixed': {'validated': True, 'final_metrics': {
            'gap': {'total': 1.0}, 'occupancy': {'canvas': 0.8}}}}
        original = {'mixed': {'validated': True, 'final_metrics': {
            'gap': {'total': 1.0}, 'occupancy': {'canvas': 0.8}}}}

        chosen, variant = _mixed_layout_choice(aligned, original)

        self.assertIs(aligned, chosen)
        self.assertEqual('aligned-working-centres', variant)

    def test_mixed_choice_falls_back_when_alignment_regresses_gap(self):
        aligned = {'mixed': {'validated': True, 'final_metrics': {
            'gap': {'total': 1.1}, 'occupancy': {'canvas': 0.9}}}}
        original = {'mixed': {'validated': True, 'final_metrics': {
            'gap': {'total': 1.0}, 'occupancy': {'canvas': 0.8}}}}

        chosen, variant = _mixed_layout_choice(aligned, original)

        self.assertIs(original, chosen)
        self.assertEqual('original-fallback', variant)


class MixedSeedTests(unittest.TestCase):
    def test_working_scale_cannot_change_growth_reference_or_limits(self):
        from papers.arrangement import arrange, fit_layout
        from papers.mixed_fit import mixed_fit_layout

        records = [panel('p1')]
        growth = fit_layout(records, arrange(records))
        working = copy.deepcopy(growth)
        working['outer_alignment'] = {'validated': True}
        working['placements'][0]['scale'] = growth['placements'][0]['scale'] * 1.2
        result = mixed_fit_layout(records, growth, growth, working_layout=working)

        self.assertFalse(result['mixed']['validated'])
        self.assertIn('immutable growth', result['mixed']['diagnostic']['reason'])


if __name__ == '__main__':
    unittest.main()
