import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from papers.document import _math_images


class MathRenderCacheTests(unittest.TestCase):
    def test_repeated_formulas_reuse_pixels_without_changing_text_or_display(self):
        xml = '<p xmlns="http://www.w3.org/1999/xhtml">Before <math xmlns="http://www.w3.org/1998/Math/MathML"><mi>x</mi></math> between <math xmlns="http://www.w3.org/1998/Math/MathML"><mi>x</mi></math> after.</p>'
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cache = {}
            outputs = []
            with patch('papers.document.subprocess.run', wraps=subprocess.run) as run:
                for index in range(2):
                    directory = root / str(index)
                    directory.mkdir()
                    tree = ET.fromstring(xml)
                    self.assertEqual(_math_images(tree, directory, cache), 2)
                    outputs.append((ET.tostring(tree), {p.name:p.read_bytes() for p in directory.iterdir()}))
                renderer = [c for c in run.call_args_list if c.args[0][1].endswith('math.js')]
                self.assertEqual(len(renderer), 1)
                self.assertEqual(len(json.loads(renderer[0].kwargs['input'])), 1)
                self.assertEqual(len(run.call_args_list), 2)  # One SVG and one PNG render.
            self.assertEqual(outputs[0], outputs[1])
            self.assertEqual(''.join(ET.fromstring(outputs[0][0]).itertext()), 'Before  between  after.')
            self.assertEqual(len(cache), 1)
