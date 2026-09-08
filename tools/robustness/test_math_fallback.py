import subprocess
from unittest.mock import patch
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from papers.math_fallback import repair_math


class MathFallbackTests(unittest.TestCase):
    def make_book(self,path,formula):
        with zipfile.ZipFile(path,'w') as z:
            z.writestr('mimetype','application/epub+zip')
            z.writestr('body.xhtml','<html xmlns="http://www.w3.org/1999/xhtml"><body><p>Before</p><span class="math display" id="eq">'+formula+'</span><p>After</p></body></html>')

    def test_legacy_display_font_is_recovered_with_tex_anchor_and_prose(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'paper.epub';formula=r'\begin{equation}{\rm log}p(x)=1\label{eq:log}\end{equation}'
            self.make_book(p,formula);records=repair_math(p)
            with zipfile.ZipFile(p) as z:root=ET.fromstring(z.read('body.xhtml'))
            self.assertEqual([e.text for e in root.findall('.//{*}p')],['Before','After'])
            math=root.find('.//{*}math');self.assertEqual(math.get('id'),'eq')
            self.assertEqual(math.get('display'),'block')
            self.assertEqual(math.find('.//{*}annotation').text,formula)
            self.assertEqual(len(records),1)
            self.assertNotIn('merror',ET.tostring(math,encoding='unicode'))

    def test_conversion_recovers_only_failed_equations(self):
        from native import host
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source';source.mkdir()
            (source/'main.tex').write_text(r'''\documentclass{article}
\title{Fallback test}\author{An Author}\begin{document}\maketitle
\begin{abstract}The full abstract survives equation recovery.\end{abstract}
\section{Method}Known equation $x^2$.
\begin{equation}{\rm log}p(x)=1\label{eq:log}\end{equation}
See Equation~\ref{eq:log}.\end{document}''')
            def cover(svg,png):
                subprocess.run(['rsvg-convert','-o',str(png),str(svg)],check=True,capture_output=True)
            with patch.object(host,'rasterize_cover',cover):
                host.convert_source(source,'2401.00001v1',root/'paper.epub')
            with zipfile.ZipFile(root/'paper.epub') as z:
                trees=[ET.fromstring(z.read(n)) for n in z.namelist() if n.endswith('.xhtml')]
            self.assertEqual(sum(len(t.findall('.//{*}math')) for t in trees),2)
            self.assertTrue(any(t.find('.//*[@id="eq:log"]') is not None for t in trees))
            self.assertTrue((root/'paper.math-fallback.json').exists())

    def test_pandoc_delimiters_are_not_rendered_as_dollar_glyphs(self):
        with tempfile.TemporaryDirectory() as tmp:
            for formula in [r'${\rm log}x$',r'$${\rm log}x$$',r'\({\rm log}x\)',r'\[{\rm log}x\]']:
                p=Path(tmp)/'paper.epub';self.make_book(p,formula);repair_math(p)
                with zipfile.ZipFile(p) as z:root=ET.fromstring(z.read('body.xhtml'))
                self.assertNotIn('$',[e.text for e in root.findall('.//{*}mo')])
                self.assertEqual(root.find('.//{*}annotation').text,formula)

    def test_unknown_command_rejects_without_modifying_epub(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'paper.epub';self.make_book(p,r'\unknownsymbol{x}')
            before=p.read_bytes()
            with self.assertRaisesRegex(ValueError,'rejected'):repair_math(p)
            self.assertEqual(before,p.read_bytes())


if __name__=='__main__':unittest.main()
