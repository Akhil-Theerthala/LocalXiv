import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from native import host

class ScientificNotation(unittest.TestCase):
    def test_uppercase_exponent_keeps_number_and_denominator(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'main.tex'
            original=r'''\SI{5E5}{\gram/\cm^3} and $\sim\SI{4E9}{\K}$.
% \SI{5E5}{\gram}
\verb|\num{5E5}|'''
            p.write_text(original);host.prepare_package_math(root)
            self.assertEqual(p.read_text(),original.replace(r'\SI{5E5}{\gram/\cm^3}',r'\SI{5e5}{\gram/\cm^3}').replace('4E9','4e9'))
            result=subprocess.run(['pandoc',str(p),'-f','latex','-t','html','--mathml'],capture_output=True,text=True,check=True)
            self.assertNotIn('Could not convert',result.stderr)
            tree=ET.fromstring('<body>'+result.stdout+'</body>')
            self.assertIn('g/cm3',''.join(tree.itertext()).replace(' ',''))
            self.assertIn('5',result.stdout);self.assertIn('9',result.stdout)
            (root/'custom.sty').write_text(r'\newcommand{\SI}[2]{#1 #2}')
            p.write_text(original);host.prepare_package_math(root);self.assertEqual(p.read_text(),original)

    def test_html_cannot_silently_accept_source_unit_denominator_loss(self):
        from papers.arxiv_html import prepare
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'pandoc/source';source.mkdir(parents=True)
            (source/'main.tex').write_text(r'\SI{5e5}{\gram/\cm^3}')
            with self.assertRaisesRegex(ValueError,'denominators'):
                prepare(root,root/'attempt',{})

    def test_implicit_scientific_coefficient_is_retained(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'main.tex';p.write_text(r'\SI{e8}{\cm}')
            host.prepare_package_math(root)
            self.assertEqual(p.read_text(),r'\SI{1e8}{\cm}')
