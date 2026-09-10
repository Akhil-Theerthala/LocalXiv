"""Pandoc must retain independent captions, links, and cells from plain NiceTabular."""
import shutil
import subprocess
import tempfile
from pathlib import Path
import unittest
import zipfile
import xml.etree.ElementTree as ET

from native.host import ConversionError, prepare_table_labels, prepare_compiled_bibliography, _finalize_epub


class NiceTableTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('pandoc'), 'Pandoc is required')
    def test_side_by_side_tables_keep_labels_captions_and_cells(self):
        source = r'''\documentclass{article}
\begin{document}
See Table~\ref{tab:results} and Table~\ref{tab:ablation}.
\begin{table}
\begin{minipage}{0.48\linewidth}
\begin{NiceTabular}{lcc}
Dataset & \textbf{\begin{tabular}[c]{@{}c@{}}Semantic \\ feature\end{tabular}} & Combined \\
Trivia & 79.21 & 79.71 \\
Natural & 65.29 & 66.02 \\
\end{NiceTabular}
\caption{Results for three models}\label{tab:results}
\end{minipage}
\hfill
\begin{minipage}{0.48\linewidth}
\begin{tabular}{lc}
Method & Score \\
Probe & 73.53 \\
\end{tabular}
\caption{Ablation results}\label{tab:ablation}
\end{minipage}
\end{table}
\end{document}'''
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'paper.tex'
            path.write_text(source)
            self.assertEqual(prepare_table_labels(Path(temporary)), 4)
            rendered = subprocess.run(['pandoc', '--from=latex', '--to=html5', str(path)], capture_output=True, text=True, check=True).stdout
            root = ET.fromstring('<body>' + rendered + '</body>')
            tables = root.findall('.//table')
            self.assertEqual([t.get('id') for t in tables], ['tab:results', 'tab:ablation'])
            self.assertEqual([''.join(t.find('caption').itertext()) for t in tables], ['Results for three models', 'Ablation results'])
            self.assertEqual([' '.join(''.join(cell.itertext()).split()) for cell in tables[0].findall('.//td')], ['Dataset', 'Semantic feature', 'Combined', 'Trivia', '79.21', '79.71', 'Natural', '65.29', '66.02'])
            self.assertEqual({a.get('href') for a in root.findall('.//a')}, {'#tab:results', '#tab:ablation'})
            self.assertEqual(prepare_table_labels(Path(temporary)), 0)

    def test_package_specific_blocks_fail_instead_of_disappearing(self):
        for body in (r'{cc}[hvlines] A & B \\', r'{cc} \Block{2-2}{Group} \\', r'[first-row]{cc} A & B \\'):
            with self.subTest(body=body), tempfile.TemporaryDirectory() as temporary:
                path = Path(temporary) / 'paper.tex'
                source = r'\begin{NiceTabular}' + body + r'\end{NiceTabular}'
                path.write_text(source)
                with self.assertRaisesRegex(ConversionError, 'package-specific'):
                    prepare_table_labels(Path(temporary))
                self.assertEqual(path.read_text(), source)


class CompiledBibliographyTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('pandoc'), 'Pandoc is required')
    def test_setup_preamble_is_removed_but_year_suffix_and_entries_remain(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'paper.tex'
            root.write_text(r'\documentclass{article}\begin{document}Claim \cite{alpha,beta}.\bibliography{paper}\end{document}')
            root.with_suffix('.bbl').write_text(r"""\begin{thebibliography}{45}
\expandafter\ifx\csname natexlab\endcsname\relax\def\natexlab#1{#1}\fi

\bibitem[Alpha(2020)]{alpha} Alpha. 2020\natexlab{a}. First title.

\bibitem[Beta(2021)]{beta} Beta. 2021. Second title.
\end{thebibliography}
""")
            entries = prepare_compiled_bibliography(root)
            output = Path(temporary) / 'paper.epub'
            subprocess.run(['pandoc', '-f', 'latex', '-t', 'epub3', '-o', str(output), str(root)], cwd=temporary, capture_output=True, check=True)
            _finalize_epub(output, entries, numeric_citations=True)
            with zipfile.ZipFile(output) as book:
                documents = [ET.fromstring(book.read(name)) for name in book.namelist() if name.endswith('.xhtml')]
            references = [element for document in documents for element in document.iter() if 'thebibliography' in element.get('class', '').split()][0]
            text = ' '.join(references.itertext())
            self.assertNotIn('45', text)
            self.assertNotIn('natexlab', text)
            self.assertIn('2020a', text)
            self.assertEqual([p.get('id') for p in references], ['ref-alpha', 'ref-beta'])
            self.assertIn('First title.', text)
            self.assertIn('Second title.', text)


if __name__ == '__main__':
    unittest.main()
