"""A proven multi-grid float keeps one source caption and one shared target."""
import shutil
import subprocess
import tempfile
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET
import zipfile

from papers.document import XHTML, _normalize_structure, build_document


class GroupedTableTests(unittest.TestCase):
    @unittest.skipUnless(all(shutil.which(tool) for tool in ('pandoc', 'rsvg-convert', 'epubcheck')), 'EPUB toolchain is required')
    def test_real_pandoc_duplicate_group_retains_both_grids_and_shared_caption(self):
        source = r'''\documentclass{article}\begin{document}
See \ref{tab:scenarios}.
\begin{table}
\caption{Answers under two different scenarios.}
\begin{tabular}{lc}Answer & Probability \\ Paris & 0.5 \\\end{tabular}
\par\emph{Scenario one: distinct meanings.}
\begin{tabular}{lc}Answer & Probability \\ Paris & 0.9 \\\end{tabular}
\par\emph{Scenario two: shared meanings.}\label{tab:scenarios}
\end{table}
\end{document}'''
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / 'source').mkdir()
            (directory / 'reader').mkdir()
            root = directory / 'source' / 'paper.tex'
            root.write_text(source)
            result = subprocess.run(['pandoc', '-f', 'latex', '-t', 'html5', str(root)], capture_output=True, text=True, check=True)
            raw = f'<html xmlns="{XHTML}"><head><title>Scenarios</title></head><body>{result.stdout}</body></html>'
            self.assertGreater(raw.count('id="tab:scenarios"'), 1)
            (directory / 'reader' / 'main.xhtml').write_text(raw)
            document = build_document(directory, {'arxiv_id': '2501.00001v1', 'title': 'Scenarios', 'authors': 'Author'}, 'pandoc')
            tree = ET.parse(directory / 'reader' / 'main.xhtml').getroot()
            targets = [e for e in tree.iter() if e.get('id') == 'tab:scenarios']
            self.assertEqual(len(targets), 1)
            group = targets[0]
            self.assertEqual(group.get('class'), 'table-group')
            self.assertEqual(len(group.findall(f'{{{XHTML}}}table')), 2)
            self.assertEqual(len(group.findall(f'{{{XHTML}}}figcaption')), 1)
            text = ' '.join(''.join(group.itertext()).split())
            for value in ('0.5', '0.9', 'Scenario one: distinct meanings.', 'Scenario two: shared meanings.'):
                self.assertIn(value, text)
            self.assertEqual(text.count('Answers under two different scenarios.'), 1)
            self.assertTrue(any('shared caption' in w for w in document['report']['warnings']))
            with zipfile.ZipFile(directory / 'paper.epub') as book:
                chapter = ET.fromstring(book.read('EPUB/main.xhtml'))
                self.assertEqual(len(chapter.findall('.//{*}table')), 2)
                self.assertTrue(any(e.get('href') == '#tab:scenarios' for e in chapter.iter()))

    def test_unproven_or_different_caption_duplicates_still_fail(self):
        def tree(second='Same caption'):
            return ET.fromstring(f'<html xmlns="{XHTML}"><body><table id="t"><caption>Same caption</caption><tr><td>A</td></tr></table><table id="t"><caption>{second}</caption><tr><td>B</td></tr></table></body></html>')
        with self.assertRaisesRegex(ValueError, 'ambiguous duplicate'):
            _normalize_structure(tree())
        with self.assertRaisesRegex(ValueError, 'ambiguous duplicate'):
            _normalize_structure(tree('A different caption'), table_groups={'t': 2})
        with self.assertRaisesRegex(ValueError, 'ambiguous duplicate'):
            _normalize_structure(tree(), table_groups={'t': 3})


if __name__ == '__main__':
    unittest.main()
