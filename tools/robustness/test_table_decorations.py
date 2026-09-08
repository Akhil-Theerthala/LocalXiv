import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from native import host
from papers.worker import run

class TableDecorations(unittest.TestCase):
    def test_cells_keep_headings_and_glyphs_without_print_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); p=root/'main.tex'
            source=r'''\newcommand{\cmark}{\ding{51}}
\begin{tabular}{ll}\rowcolor[gray]{0.9}[0pt][0pt]\multicolumn{2}{l}{Latest models}\\
A & \cmark\\\cline{1-2}B & \ding{55}\\\end{tabular}
% \ding{99} is a comment
\verb|\rowcolor{red}|'''
            p.write_text(source);host.prepare_table_rules_and_checks(root)
            output=subprocess.run(['pandoc',str(p),'-f','latex','-t','html'],text=True,capture_output=True,check=True).stdout
            tree=ET.fromstring('<body>'+output+'</body>')
            cells=tree.findall('.//td')
            self.assertEqual([''.join(c.itertext()) for c in cells],['Latest models','A','✓','B','✗'])
            self.assertEqual(cells[0].get('colspan'),'2')
            self.assertIn('% \\ding{99} is a comment',p.read_text())
            p.write_text(r'\ding{99}')
            with self.assertRaises(host.ConversionError):host.prepare_table_rules_and_checks(root)
            p.write_text(r'\newcommand{\rowcolor}[1]{Meaning}\rowcolor{red}')
            with self.assertRaises(host.ConversionError):host.prepare_table_rules_and_checks(root)

    def test_latexml_stops_after_error_and_retains_successful_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);log=root/'log'
            start=time.monotonic()
            with self.assertRaisesRegex(ValueError,'Error:broken'):
                run([sys.executable,'-u','-c','import time; print("Error:broken"); time.sleep(20)'],root,log,30)
            self.assertLess(time.monotonic()-start,5)
            self.assertIn('Error:broken',log.read_text())
            self.assertEqual(run([sys.executable,'-c','print("valid")'],root,log),'valid\n')
