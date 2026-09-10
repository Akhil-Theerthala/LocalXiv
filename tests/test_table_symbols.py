"""Booktabs trim rules must not become cells or erase comparison symbols."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

from native.host import prepare_table_rules_and_checks, ConversionError


class TableSymbolTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('pandoc'), 'Pandoc is required')
    def test_generated_equivalence_table_keeps_all_five_checks_in_their_cells(self):
        table = r'''\documentclass{article}\begin{document}
\begin{table}\caption{Types of equivalence}
\begin{tabular}{@{}llccc@{}}
\toprule
 & & \multicolumn{3}{c}{Equivalence} \\\cmidrule(l){3-5}
Sentence A & Sentence B & Lexical & Syntactic & Semantic \\ \midrule
Paris is the capital of France. & Paris is the capital of France. & \Checkmark & \Checkmark & \Checkmark\\
 & Berlin is the capital of France. & & \Checkmark & \\
 & France's capital is Paris. & & & \Checkmark \\ \bottomrule
\end{tabular}\end{table}\end{document}'''
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'paper.tex'
            for rule in (r'\cmidrule(l){3-5}', r'\cmidrule[0.4pt](l{.5em}r{.5em}){3-5}', r'\cmidrule{3-5}'):
                with self.subTest(rule=rule):
                    path.write_text(table.replace(r'\cmidrule(l){3-5}', rule))
                    self.assertEqual(prepare_table_rules_and_checks(Path(tmp)),6)
                    self.assertEqual(prepare_table_rules_and_checks(Path(tmp)),0)
                    rendered=subprocess.run(['pandoc','--from=latex','--to=html5',str(path)],check=True,capture_output=True,text=True).stdout
                    root=ET.fromstring('<body>'+rendered+'</body>')
                    rows=[[' '.join(''.join(c.itertext()).split()) for c in row if c.tag in ('td','th')] for row in root.findall('.//tr')]
                    self.assertEqual(rows[-3][2:],['✓','✓','✓'])
                    self.assertEqual(rows[-2][2:],['','✓',''])
                    self.assertEqual(rows[-1][2:],['','','✓'])
                    self.assertEqual(sum(cell.count('✓') for row in rows for cell in row),5)
                    self.assertEqual(root.find('.//*[@colspan="3"]').text,'Equivalence')
                    for leaked in ('3-5','cmidrule','0.4pt','.5em'):
                        self.assertNotIn(leaked,rendered)

    def test_comments_literal_commands_and_custom_definitions_are_not_reinterpreted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'paper.tex'
            literal=r'''% \Checkmark \cmidrule(l){3-5}
\verb|\Checkmark \cmidrule(l){3-5}|
\begin{verbatim}
\Checkmark \cmidrule(l){3-5}
\end{verbatim}
'''
            path.write_text(literal)
            self.assertEqual(prepare_table_rules_and_checks(Path(tmp)),0)
            self.assertEqual(path.read_text(),literal)
            path.write_text(r'\renewcommand{\Checkmark}{No}\Checkmark')
            with self.assertRaises(ConversionError):
                prepare_table_rules_and_checks(Path(tmp))


if __name__=='__main__':
    unittest.main()
