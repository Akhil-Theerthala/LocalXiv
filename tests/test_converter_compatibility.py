"""Real parser checks for source constructs that previously lost math or anchors."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from unittest.mock import patch
import xml.etree.ElementTree as ET

from native.host import (ConversionError, convert_source, prepare_compiled_bibliography,
                         prepare_grouped_figure_labels, prepare_math_compatibility,
                         prepare_measured_inline_boxes, prepare_wrapfigures, prepare_table_labels,
                         _repair_cross_file_fragments, validate_epub, prepare_multiple_references)


class ConverterCompatibilityTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('pandoc'), 'Pandoc is required')
    def test_aligned_equation_retains_all_label_targets(self):
        source = r'''\documentclass{article}\begin{document}
\section{Derivation}
\begin{align}
x &= a \label{eq:first} \\
  &\ge b \label{eq:middle} \\
  &= c \label{eq:last}
\end{align}
\section{Discussion}
Use \eqref{eq:first}, \eqref{eq:middle}, and \eqref{eq:last}.
\end{document}'''
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'paper.epub'
            subprocess.run(['pandoc', '-f', 'latex', '-t', 'epub3', '--mathml', '-o', str(output)],
                           input=source, capture_output=True, text=True, check=True)
            # Also exercise an existing first anchor, as on a repeated repair.
            for _ in range(2):
                _repair_cross_file_fragments(output)
                validate_epub(output)
                with zipfile.ZipFile(output) as book:
                    roots = [ET.fromstring(book.read(n)) for n in book.namelist() if n.endswith('.xhtml')]
                elements = [e for root in roots for e in root.iter()]
                for label in ('eq:first', 'eq:middle', 'eq:last'):
                    targets = [e for e in elements if e.get('id') == label]
                    self.assertEqual(len(targets), 1)
                    self.assertTrue(any(e.tag.endswith('}math') for e in targets[0].iter()))
                    self.assertTrue(any(e.get('href', '').endswith('#' + label) for e in elements))
                math = next(e for e in elements if e.tag.endswith('}math'))
                self.assertEqual(len(math.findall('.//{*}mtr')), 3)
                self.assertFalse(any(e.tag == '{http://www.w3.org/1999/xhtml}span' for e in math.iter()))

    @unittest.skipUnless(shutil.which('pandoc'), 'Pandoc is required')
    def test_upright_labels_and_alignment_style_retain_mathml(self):
        source = r'''The score is $H_{\textup{SE}}(x)$.
\begin{align*}
\textstyle &\text{SE}_\textup{low}=\{j: H_{\textup{SE}}(x_j) < \gamma\},
&\text{SE}_\textup{high}=\{j: H_{\textup{SE}}(x_j) \ge \gamma\}, \\
\textstyle &\hat{H}_{\textup{low}}= \frac{1}{\lvert\text{SE}_\textup{low}\rvert} \sum\nolimits_{j\in \text{SE}_\textup{low}}H_{\textup{SE}}(x_j).
\end{align*}'''
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'paper.tex'
            path.write_text(source)
            prepare_math_compatibility(Path(temporary))
            result = subprocess.run(['pandoc', '-f', 'latex', '-t', 'html5', '--mathml', str(path)], text=True, capture_output=True, check=True)
            self.assertNotIn('Could not convert TeX math', result.stderr)
            document = ET.fromstring('<body>' + result.stdout + '</body>')
            self.assertEqual(len(document.findall('.//{http://www.w3.org/1998/Math/MathML}math')), 2)
            text = ''.join(document.itertext())
            for word in ('SE', 'low', 'high'):
                self.assertIn(word, text)

    @unittest.skipUnless(shutil.which('pandoc'), 'Pandoc is required')
    def test_unlabelled_group_does_not_steal_child_figure_label(self):
        source = r'''See \ref{panel-b}.
\begin{figure}
\begin{subfigure}{0.4\textwidth}\includegraphics{a.png}\caption{First panel}\label{panel-a}\end{subfigure}
\begin{subfigure}{0.4\textwidth}\includegraphics{b.png}\caption{}\label{panel-b}\end{subfigure}
\caption{Combined explanation.}
\end{figure}'''
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'paper.tex'
            path.write_text(source)
            self.assertEqual(prepare_grouped_figure_labels(Path(temporary)), 1)
            self.assertEqual(prepare_grouped_figure_labels(Path(temporary)), 0)
            result = subprocess.run(['pandoc', '-f', 'latex', '-t', 'html5', str(path)], text=True, capture_output=True, check=True)
            root = ET.fromstring('<body>' + result.stdout + '</body>')
            ids = [e.get('id') for e in root.iter() if e.get('id')]
            self.assertEqual(len(ids), len(set(ids)))
            panel = next(e for e in root.iter() if e.get('id') == 'panel-b')
            self.assertEqual(panel.find('img').get('src'), 'b.png')
            self.assertIn('Combined explanation.', ''.join(root.itertext()))
            self.assertIn('#panel-b', [e.get('href') for e in root.iter('a')])

    @unittest.skipUnless(shutil.which('pandoc'), 'Pandoc is required')
    def test_wrapped_table_keeps_caption_anchor_and_values(self):
        source = r"""See Table~\ref{tab:comparison}.
\begin{wraptable}{r}{0.27\textwidth}
\captionsetup{labelformat=empty}
\caption{Comparison of models.}\label{tab:comparison}
\begin{tabular}{lr}Model & Difference \\
Small & $2.8 \pm 1.4$ \\
Large & $-0.5 \pm 2.6$ \\
\end{tabular}
\end{wraptable}"""
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'paper.tex'
            path.write_text(source)
            self.assertEqual(prepare_wrapfigures(Path(temporary)), 1)
            prepare_table_labels(Path(temporary))
            result = subprocess.run(['pandoc', '-f', 'latex', '-t', 'html5', '--mathml', str(path)], capture_output=True, text=True, check=True)
            root = ET.fromstring('<body>' + result.stdout + '</body>')
            table = root.find('.//table')
            self.assertEqual(table.get('id'), 'tab:comparison')
            self.assertEqual(len(table.findall('.//tr')), 3)
            self.assertIn('Comparison of models.', ''.join(table.itertext()))
            self.assertIn('2.8', ''.join(table.itertext()))
            self.assertIn('2.6', ''.join(table.itertext()))

    @unittest.skipUnless(shutil.which('pandoc'), 'Pandoc is required')
    def test_measured_icon_keeps_link_image_and_caption_text(self):
        source = r"""\newcommand{\notebook}[1]{\href{#1}{\begingroup
\setbox0=\hbox{\includegraphics[height=1.5em]{icon.png}}%
\parbox{\wd0}{\box0}\endgroup}}
Read this notebook: \notebook{https://example.org/notebook}. End of paragraph.
"""
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'paper.tex'
            path.write_text(source)
            self.assertEqual(prepare_measured_inline_boxes(Path(temporary)), 1)
            self.assertEqual(prepare_measured_inline_boxes(Path(temporary)), 0)
            result = subprocess.run(['pandoc', '-f', 'latex', '-t', 'html5', str(path)], capture_output=True, text=True, check=True)
            root = ET.fromstring('<body>' + result.stdout + '</body>')
            link = root.find('.//a')
            self.assertEqual(link.get('href'), 'https://example.org/notebook')
            self.assertEqual(link.find('.//img').get('src'), 'icon.png')
            self.assertIn('End of paragraph.', ' '.join(''.join(root.itertext()).split()))

    @unittest.skipUnless(shutil.which('pandoc'), 'Pandoc is required')
    def test_mixed_math_epub_keeps_reference_emphasis_breaks_and_footnote(self):
        source = r"""\documentclass{article}\title{Mixed math fixture}
\begin{document}
A new point is $(X_{\rm test},Y^{\rm (val)})$. The score is ${\rm OOD}(x)$.
\begin{equation}\label{eq:bound}
P(Y_{\rm test} \in C(X_{\rm test})) \ge 1-\alpha.
\footnote{The second empirical risk $R_2$ uses the nonempty predictions.}
\end{equation}
The guarantee is $\eqref{eq:bound}$.
A sequence is $(X_1,Y_1),\dots,\\(X_n,Y_n)$.
\begin{align}
\text{Rejecting the null $H_{\lambda}$ } &\to \text{ the risk \emph{is} controlled at $\lambda$.} \\
\text{Accepting the null $H_{\lambda}$ } &\to \text{ the risk \emph{is not} controlled at $\lambda$.}
\end{align}
\end{document}"""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'paper.tex'
            root.write_text(source)
            prepare_math_compatibility(Path(temporary))
            self.assertEqual(prepare_math_compatibility(Path(temporary)), 0)
            output = Path(temporary) / 'paper.epub'
            result = subprocess.run(['pandoc', '-f', 'latex', '-t', 'epub3', '--mathml', '-o', str(output), str(root)], capture_output=True, text=True, check=True)
            self.assertNotIn('Could not convert TeX math', result.stderr)
            _repair_cross_file_fragments(output)
            validate_epub(output)
            with zipfile.ZipFile(output) as book:
                documents = [ET.fromstring(book.read(name)) for name in book.namelist() if name.endswith('.xhtml')]
            elements = [e for document in documents for e in document.iter()]
            text = ' '.join(' '.join(e.itertext()) for e in documents)
            self.assertIn('The second empirical risk', text)
            self.assertIn('nonempty predictions.', text)
            self.assertIn('is not', text)
            self.assertIn('Rejecting the null', text)
            self.assertTrue(any(e.get('href', '').endswith('#eq:bound') for e in elements))
            self.assertTrue(any(e.get('role') == 'doc-noteref' for e in elements))
            self.assertTrue(any(e.tag.endswith('}br') for e in elements))
            self.assertGreaterEqual(sum(e.tag == '{http://www.w3.org/1998/Math/MathML}math' for e in elements), 7)

    @unittest.skipUnless(shutil.which('pandoc'), 'Pandoc is required')
    def test_cleveref_list_has_independent_links_and_leaves_literals_unchanged(self):
        source = r"""Results appear in \cref{sec:one,sec:two}, with the same context.
% Leave \Cref{comment:a,comment:b} alone.
Literal: \verb|\cref{literal:a,literal:b}|.
\begin{verbatim}
\cref{code:a,code:b}
\end{verbatim}
\section{First}\label{sec:one}
\section{Second}\label{sec:two}
"""
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'paper.tex'
            path.write_text(source)
            self.assertEqual(prepare_multiple_references(Path(temporary)), 1)
            rewritten = path.read_text()
            self.assertIn(r'\cref{sec:one}, \cref{sec:two}', rewritten)
            self.assertIn(r'% Leave \Cref{comment:a,comment:b} alone.', rewritten)
            self.assertIn(r'\verb|\cref{literal:a,literal:b}|', rewritten)
            self.assertIn(r'\cref{code:a,code:b}', rewritten)
            self.assertEqual(prepare_multiple_references(Path(temporary)), 0)
            result = subprocess.run(['pandoc', '-f', 'latex', '-t', 'html5', str(path)], capture_output=True, text=True, check=True)
            root = ET.fromstring('<body>' + result.stdout + '</body>')
            hrefs = [a.get('href') for a in root.iter('a')]
            self.assertEqual(hrefs, ['#sec:one', '#sec:two'])
            self.assertIn('with the same context.', ' '.join(''.join(root.itertext()).split()))
            path.write_text(r'\Cref*{sec:one, sec:two}')
            prepare_multiple_references(Path(temporary))
            self.assertEqual(path.read_text(), r'\Cref*{sec:one}, \Cref*{sec:two}')

    def test_failed_pandoc_attempt_retains_diagnostics(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / 'paper.tex').write_text(r'\documentclass{article}\title{Fixture}\begin{document}Content.\end{document}')
            output = directory / 'paper.epub'
            failure = subprocess.CompletedProcess(['pandoc'], 1, '', 'Specific parser warning and failure')
            with patch('native.host.rasterize_cover'), patch('native.host.subprocess.run', return_value=failure):
                with self.assertRaisesRegex(ConversionError, 'Specific parser warning'):
                    convert_source(directory, '2501.00001v1', output, pandoc='pandoc')
            self.assertIn('Specific parser warning and failure', output.with_suffix('.pandoc.log').read_text())

    def test_biber_database_uses_source_bib_or_reports_missing_input(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'paper.tex'
            source = r'\documentclass{article}\begin{document}\cite{smith}\printbibliography\end{document}'
            root.write_text(source)
            root.with_suffix('.bbl').write_text(r'\datalist[entry]{nyt/global//global/global}\entry{smith}{article}{}\endentry\enddatalist')
            with self.assertRaisesRegex(ConversionError, 'source .bib database'):
                prepare_compiled_bibliography(root)
            root.with_suffix('.bib').write_text('@article{smith, title={A result}, author={Smith, A}, year={2020}}')
            self.assertEqual(prepare_compiled_bibliography(root), [])
            self.assertEqual(root.read_text(), source)


if __name__ == '__main__':
    unittest.main()
