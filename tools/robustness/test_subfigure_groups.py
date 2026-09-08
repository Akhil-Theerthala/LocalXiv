import subprocess
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET
from native import host

class SubfigureGroups(unittest.TestCase):
    def test_group_caption_and_each_panel_survive_once_in_source_order(self):
        source=r'''\begin{figure}\caption[Short]{Shared comparison {with braces}.}
\begin{subfigure}{.5\textwidth}\includegraphics{a.png}\caption{Panel A}\end{subfigure}
\begin{subfigure}{.5\textwidth}\includegraphics{b.png}\caption{Panel B}\end{subfigure}
\label{fig:shared}\end{figure}'''
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'main.tex';p.write_text(source)
            self.assertEqual(host.prepare_subfloats(root),1)
            self.assertEqual(host.prepare_subfloats(root),0)
            output=subprocess.run(['pandoc',str(p),'-f','latex','-t','html'],capture_output=True,text=True,check=True).stdout
            tree=ET.fromstring('<body>'+output+'</body>')
            text=' '.join(tree.itertext())
            for phrase in ['Shared comparison','Panel A','Panel B']:self.assertEqual(text.count(phrase),1)
            self.assertLess(text.index('Shared comparison'),text.index('Panel A'))
            self.assertLess(text.index('Panel A'),text.index('Panel B'))
            self.assertIsNotNone(tree.find('.//*[@id="fig:shared"]'))
            self.assertEqual([x.get('src') for x in tree.findall('.//img')],['a.png','b.png'])
