"""Related forms of the original table-note failure, through the real reader."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from native.host import prepare_package_math


class NoteMarkerTests(unittest.TestCase):
    def test_equivalent_math_delimiters_and_comments_preserve_the_marker(self):
        wrappers=[('$','$'),(r'\(',r'\)'),(r'\[',r'\]'),
                  (r'\begin{equation*}',r'\end{equation*}'),
                  (r'\begin{math}',r'\end{math}'),
                  (r'\begin{displaymath}',r'\end{displaymath}')]
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path=root/'main.tex'
            for left,right in wrappers:
                for symbol,glyph in [(r'\textdagger','†'),(r'\textdaggerdbl','‡')]:
                    with self.subTest(left=left,symbol=symbol):
                        literal='% '+left+symbol+right+'\n'+r'\verb|'+symbol+'|\n'
                        path.write_text(literal+left+r'^{\text{'+symbol+'}}'+right)
                        prepare_package_math(root)
                        self.assertIn(literal,path.read_text())
                        self.assertEqual(prepare_package_math(root),0)
                        r=subprocess.run(['pandoc',str(path),'-f','latex','-t','html','--mathml'],capture_output=True,text=True,check=True)
                        self.assertNotIn('Could not convert TeX math',r.stderr)
                        tree=ET.fromstring('<body>'+r.stdout+'</body>')
                        self.assertEqual(tree.find('.//{*}msup/{*}mtext').text,glyph)

    def test_author_redefinition_is_not_replaced_with_a_standard_glyph(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'main.tex'
            source=r'\renewcommand{\textdagger}{X}$\text{\textdagger}$'
            p.write_text(source);prepare_package_math(root)
            self.assertEqual(p.read_text(),source)

    def test_definition_in_a_local_style_is_respected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'main.tex'
            (root/'custom.sty').write_text(r"\renewcommand{\textdagger}{X}")
            p.write_text(r"$\text{\textdagger}$");before=p.read_text()
            prepare_package_math(root)
            self.assertEqual(p.read_text(),before)


class PackageMathTests(unittest.TestCase):
    def test_fraction_and_print_spacing_keep_the_equation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'main.tex'
            p.write_text(r"\begin{equation}\nicefrac{T^2}{n}+1\vspace{-.1cm}\end{equation}")
            prepare_package_math(root)
            result=subprocess.run(['pandoc',str(p),'-f','latex','-t','html','--mathml'],capture_output=True,text=True,check=True)
            self.assertNotIn('Could not convert TeX math',result.stderr)
            tree=ET.fromstring('<body>'+result.stdout+'</body>')
            self.assertIsNotNone(tree.find('.//{*}mfrac'))
            self.assertIn('n', ''.join(tree.find('.//{*}mfrac').itertext()))
            self.assertEqual(prepare_package_math(root),0)

if __name__=='__main__':unittest.main()
