import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from native import host


class SampledStructureTests(unittest.TestCase):
    def test_template_abbreviations_and_numbered_author_information_survive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'main.tex'
            (root/'cvpr.sty').write_text(r'\def\eg{\emph{e.g}\onedot} \def\etc{\emph{etc}\onedot}')
            p.write_text(r'''\documentclass{article}\author{Author$^1$\\[2mm]$^1$~Institute\\\normalsize{Equal contribution}\\\url{https://example.org/code}}
\begin{document}\maketitle\section*{Abstract}An abstract.
% arxiv-kindle-abstract-end
\section{Method}Examples, \eg, one, \etc.
% \eg unchanged
\verb|\eg|
\end{document}''')
            host.prepare_source_notes(root,p)
            host.prepare_package_abbreviations(root)
            content=p.read_text()
            self.assertIn(r'\emph{e.g}., one, \emph{etc}.',content)
            self.assertIn('% \\eg unchanged',content)
            self.assertIn(r'\verb|\eg|',content)
            output=subprocess.run(['pandoc',str(p),'-f','latex','-t','html'],capture_output=True,text=True,check=True).stdout
            self.assertIn('Institute',output)
            self.assertIn('Equal contribution',output)
            self.assertIn('href="https://example.org/code"',output)
            p.write_text(r'\newcommand{\eg}{custom}\eg')
            host.prepare_package_abbreviations(root)
            self.assertEqual(p.read_text(),r'\newcommand{\eg}{custom}\eg')

    def test_unbraced_multirow_width_keeps_cells_and_caption(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'main.tex'
            literal=r'% \multirow{3}*{literal}'+'\n'+r'\verb|\multirow{3}*{literal}|'+'\n'
            p.write_text(literal+r'''\begin{table}\caption{Scores}\label{tab:scores}
\begin{tabular}{lc}\multirow{2}*{Method A} & 0.25\\ & 0.50\\\end{tabular}\end{table}''')
            host.prepare_table_labels(root)
            self.assertIn(literal,p.read_text())
            r=subprocess.run(['pandoc',str(p),'-f','latex','-t','html'],capture_output=True,text=True,check=True)
            t=ET.fromstring('<body>'+r.stdout+'</body>').find('.//table')
            self.assertIsNotNone(t)
            self.assertEqual(t.get('id'),'tab:scores')
            self.assertEqual(t.find('.//*[@rowspan="2"]').text,'Method A')
            self.assertEqual([c.text for c in t.findall('.//td')],['Method A','0.25','0.50'])

    def test_pre_title_note_does_not_create_a_redundant_title_chapter(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source';source.mkdir()
            (source/'main.tex').write_text(r'''\documentclass{article}\title{A paper}\author{Author}
\begin{document}\footnotetext{Both authors contributed equally.}\maketitle
\begin{abstract}An abstract with useful content.\end{abstract}\section{Method}Method text.\end{document}''')
            def cover(svg,png):subprocess.run(['rsvg-convert','-o',str(png),str(svg)],check=True,capture_output=True)
            with patch.object(host,'rasterize_cover',cover):host.convert_source(source,'2401.00001v1',root/'paper.epub')
            import zipfile
            with zipfile.ZipFile(root/'paper.epub') as z:
                all_text=' '.join(''.join(ET.fromstring(z.read(n)).itertext()) for n in z.namelist() if n.endswith('.xhtml'))
            self.assertIn('Both authors contributed equally.',all_text)



class AlgorithmDialectTests(unittest.TestCase):
    def test_uppercase_algorithmic_matches_mixed_case(self):
        body=r'''\begin{algorithm}\caption{Training}\label{alg:training}
\begin{algorithmic}[1]\For{$i=1,2$}\If{$i>1$}\State Keep $i$.\Else\State Skip.\EndIf\EndFor\end{algorithmic}\end{algorithm}'''
        commands=['For','If','State','Else','EndIf','EndFor']
        upper=body
        for command in commands:
            upper=upper.replace('\\'+command,'\\'+command.upper())
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'main.tex'
            p.write_text(body);host.prepare_typed_references_and_algorithms(root);expected=p.read_text()
            p.write_text(upper);host.prepare_typed_references_and_algorithms(root)
            self.assertEqual(p.read_text(),expected)


class SubtableTests(unittest.TestCase):
    def test_shared_and_individual_captions_survive(self):
        text=r"""\begin{table}[ht]\caption{Shared result.}\label{tab:shared}
\begin{subtable}{.5\linewidth}\caption{First comparison.}\begin{tabular}{lc}A & 12\\\end{tabular}\end{subtable}
\begin{subtable}{.5\linewidth}\caption{Second comparison.}\begin{tabular}{lc}B & 34\\\end{tabular}\end{subtable}\end{table}"""
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'main.tex';p.write_text(text)
            host.prepare_table_labels(root)
            result=subprocess.run(['pandoc',str(p),'-f','latex','-t','html'],capture_output=True,text=True,check=True)
            tree=ET.fromstring('<body>'+result.stdout+'</body>')
            self.assertEqual(len(tree.findall('.//table')),2)
            content=' '.join(tree.itertext())
            self.assertNotIn('[ht]',content)
            self.assertIn('(a) First comparison.',content)
            self.assertIn('(b) Second comparison.',content)
            for caption in ['Shared result.','First comparison.','Second comparison.']:
                self.assertEqual(content.count(caption),1)
            self.assertEqual(len(tree.findall('.//*[@id="tab:shared"]')),1)
            self.assertEqual([''.join(c.itertext()) for c in tree.findall('.//td')],['A','12','B','34'])

class FrameBoxTests(unittest.TestCase):
    def test_framed_block_content_is_not_silently_discarded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'main.tex'
            for command in ['framebox','fbox']:
                p.write_text('\\'+command+r"""{% a print border
\begin{minipage}{\linewidth}SYSTEM PROMPT. Keep this paragraph.\end{minipage}}""")
                host.prepare_reflowable_boxes(root)
                result=subprocess.run(['pandoc',str(p),'-f','latex','-t','html'],capture_output=True,text=True,check=True)
                self.assertIn('SYSTEM PROMPT. Keep this paragraph.',result.stdout)

class InlineHighlightTests(unittest.TestCase):
    def test_named_color_box_keeps_its_argument(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'main.tex'
            p.write_text(r"""\newtcbox{\highlight}{on line,colback=red!20,before upper=\strut,top=-3pt}
Before. \highlight{You can generate matplotlib code.} After.""")
            host.prepare_inline_box_commands(root)
            result=subprocess.run(['pandoc',str(p),'-f','latex','-t','html'],capture_output=True,text=True,check=True)
            self.assertIn('You can generate matplotlib code.',result.stdout)

    def test_content_bearing_box_options_are_not_discarded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'main.tex').write_text(r"\newtcbox{\note}{title=Important result} \note{Body}")
            with self.assertRaises(host.ConversionError):host.prepare_inline_box_commands(root)

if __name__=='__main__':unittest.main()
