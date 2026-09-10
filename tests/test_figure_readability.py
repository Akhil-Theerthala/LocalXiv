"""Run with LOCALXIV_HTML_RENDERER pointing to a compiled HTMLSnapshot.swift."""
import os
import tempfile
import unittest
from papers.html_figures import render


@unittest.skipUnless(os.environ.get('LOCALXIV_HTML_RENDERER'), 'Set LOCALXIV_HTML_RENDERER for native rendering checks')
class ReadabilityTests(unittest.TestCase):
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
