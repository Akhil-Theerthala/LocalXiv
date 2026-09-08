import tempfile
import unittest
from pathlib import Path
from native import host
from tools.robustness.test_link_tables import render

class CaptionedCenterTests(unittest.TestCase):
    def test_grouping_preserves_images_captions_and_targets(self):
        groups = [r'\includegraphics{'+name+r'.png}\caption{Caption '+name+r'}\label{fig:'+name+'}' for name in ['one','two','three']]
        expected = ''.join(r'\begin{figure}'+g+r'\end{figure}' for g in groups)
        grouped = r'\begin{figure}[t]'+''.join(r'\begin{center}'+g+r'\end{center}' for g in groups)+r'\end{figure}'
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); path = root/'main.tex'; path.write_text(grouped)
            self.assertEqual(host.prepare_captioned_centers(root), 3)
            self.assertEqual(host.prepare_captioned_centers(root), 0)
            actual = render(path.read_text()); baseline = render(expected)
            self.assertEqual([(e.tag,e.attrib,e.text) for e in actual.iter()], [(e.tag,e.attrib,e.text) for e in baseline.iter()])
            self.assertEqual([e.get('id') for e in actual.findall('figure')], ['fig:one','fig:two','fig:three'])

    def test_shared_caption_is_not_split(self):
        source = r'\begin{figure}\begin{center}A\end{center}\begin{center}B\end{center}\caption{Shared}\label{fig:shared}\end{figure}'
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); p=root/'main.tex';p.write_text(source)
            self.assertEqual(host.prepare_captioned_centers(root),0)
            self.assertEqual(p.read_text(),source)

    def test_captionof_retains_caption_text_and_declared_float_type(self):
        source = r'\begin{figure}\begin{center}\captionof{table}{Measured scores}\label{tab:s}\begin{tabular}{lc}A&1.25\end{tabular}\end{center}\begin{center}\includegraphics{plot.png}\captionof{figure}{A plot}\label{fig:p}\end{center}\end{figure}'
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'main.tex';p.write_text(source)
            self.assertEqual(host.prepare_captioned_centers(root),2)
            result=render(p.read_text())
            self.assertEqual(result.find('table').get('id'),'tab:s')
            self.assertEqual(result.find('table/caption').text,'Measured scores')
            self.assertEqual(result.find('figure').get('id'),'fig:p')
            self.assertEqual(result.find('figure/figcaption').text,'A plot')

    def test_literal_macro_preserves_prose_and_math_text(self):
        import subprocess
        from xml.etree import ElementTree as ET
        source = r'\newcommand{\model}{\text{Export3D}}Training overview of \model. $\model$'
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'main.tex';p.write_text(source)
            self.assertEqual(host.prepare_literal_text_macros(root),1)
            self.assertEqual(host.prepare_literal_text_macros(root),0)
            result=subprocess.run(['pandoc','-f','latex','-t','html','--mathml'],input=p.read_text(),text=True,capture_output=True,check=True)
            tree=ET.fromstring('<body>'+result.stdout+'</body>')
            self.assertEqual(tree.find('.//span').text,'Export3D')
            self.assertEqual(tree.find('.//{*}mtext').text,'Export3D')
