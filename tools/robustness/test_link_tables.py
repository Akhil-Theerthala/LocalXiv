"""Metamorphic table fixtures for failures reported as missing anchors."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from native import host


def render(text):
    result = subprocess.run(['pandoc', '-f', 'latex', '-t', 'html'], input=text,
                            text=True, capture_output=True, check=True)
    return ET.fromstring('<body>' + result.stdout + '</body>')

class LinkTableTests(unittest.TestCase):
    def normalize(self, source):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); path = root / 'main.tex'; path.write_text(source)
            for _ in range(2):
                host.prepare_table_rules_and_checks(root)
                host.prepare_column_types(root)
                host.prepare_table_labels(root)
                current = path.read_text()
                if _: self.assertEqual(previous, current)
                previous = current
            return current

    def test_spacing_forms_and_brace_group_preserve_cells_caption_target(self):
        grid = r'\begin{tabular}{lc}Alpha&1.25\\Beta&2.50\end{tabular}'
        for spacing in ['', r'\setlength{\tabcolsep}{1mm}', r'\setlength\tabcolsep{1mm}']:
            with self.subTest(spacing=spacing):
                source = r'\begin{table}' + spacing + '{' + grid + r'}\caption{Scores}\label{table: scores}\end{table}'
                tree = render(self.normalize(source))
                table = tree.find('.//table')
                self.assertIsNotNone(table)
                self.assertEqual(table.get('id'), 'table: scores')
                self.assertEqual(''.join(table.find('caption').itertext()), 'Scores')
                self.assertEqual([''.join(c.itertext()) for c in table.findall('.//td')], ['Alpha', '1.25', 'Beta', '2.50'])

    def test_nested_column_declarations_and_tabularx_match_plain_grid(self):
        definition = r'\newcolumntype{Y}[2]{>{\collectcell{\colorfromval{#1}{#2}}}c<{\endcollectcell}}'
        for env, width in [('tabular',''), ('tabularx',r'{\linewidth}')]:
            source = definition + r'\begin{table}\caption{Results}\label{tab:results}\begin{' + env + '}' + width + '\n% alternative spec {lll}\n' + r'{lY{nested={option}}{}}A&12\\B&34\end{' + env + r'}\end{table}'
            table = render(self.normalize(source)).find('.//table')
            self.assertIsNotNone(table)
            self.assertEqual(table.get('id'), 'tab:results')
            self.assertEqual([''.join(c.itertext()) for c in table.findall('.//td')], ['A','12','B','34'])

    def test_siunitx_numeric_columns_preserve_values(self):
        source = r'\usepackage{siunitx}\begin{table}\caption{Scores}\label{tab:s}\begin{tabular}{lS}A&0.00125\\B&-2.50\end{tabular}\end{table}'
        table = render(self.normalize(source)).find('.//table')
        self.assertIsNotNone(table)
        self.assertEqual([''.join(c.itertext()) for c in table.findall('.//td')], ['A','0.00125','B','-2.50'])

    def test_literals_are_unchanged_and_malformed_definitions_reject(self):
        source = '% \\newcolumntype{Z}{c}\n' + r'\verb|\setlength{\tabcolsep}{1mm}|' + '\n'
        self.assertEqual(self.normalize(source), source)
        with self.assertRaises(host.ConversionError): self.normalize(r'\newcolumntype{Y}[2]{broken')

if __name__ == '__main__': unittest.main()
