import tempfile
import unittest
from pathlib import Path
from native.host import ConversionError, prepare_graphics


class CorpusGraphicsTests(unittest.TestCase):
    def test_graphicspath_with_quoted_filename_preserves_the_image(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root/'images').mkdir()
            (root/'images/plot.pdf').write_bytes(b'figure')
            tex = root/'main.tex'
            tex.write_text(r'\graphicspath{{./images/}}\includegraphics{"plot.pdf"}')
            def draw(source, target): target.write_bytes(b'png')
            self.assertEqual(prepare_graphics(root, converter=draw, compilation_dir=root), 1)
            self.assertIn(r'\includegraphics{images/plot.arxiv-kindle.png}', tex.read_text())

    def test_nested_filename_braces_and_duplicate_archive_assets(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            duplicate = root / 'duplicate'
            duplicate.mkdir()
            (root / 'plot.pdf').write_bytes(b'same figure')
            (duplicate / 'plot.pdf').write_bytes(b'same figure')
            source = duplicate / 'main.tex'
            source.write_text(r'\includegraphics{{"plot"}}')
            prepare_graphics(root, compilation_dir=root,
                             converter=lambda src, dst: dst.write_bytes(src.read_bytes()))
            self.assertEqual(source.read_text(),
                             r'\includegraphics{duplicate/plot.arxiv-kindle.png}')
            source.write_text(r'\includegraphics{{plot.pdf}}')
            (root / 'plot.pdf').write_bytes(b'different figure')
            with self.assertRaisesRegex(ConversionError, 'ambiguous'):
                prepare_graphics(root, compilation_dir=root)

    def test_math_and_captioned_panels_survive_pandoc(self):
        import shutil
        import subprocess
        from native.host import prepare_math_compatibility, prepare_captioned_minipages
        if not shutil.which('pandoc'):
            self.skipTest('Pandoc unavailable')
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'main.tex'
            source.write_text(r'''\documentclass{article}
\begin{document}
$\text{\boldmath$\omega$} + \mathbbm{1} + \smash{\binom{M}{2}\vphantom{M}^{-1}}$
\begin{align} x &= 1 \notag \\ &\hspace{-12mm}= 1 \end{align}
\begin{figure}
\begin{minipage}{0.4\linewidth}\includegraphics{one.png}\caption{First}\label{fig:first}\end{minipage}
\hfill
\begin{minipage}{0.4\linewidth}\includegraphics{two.png}\caption{Second}\label{fig:second}\end{minipage}
\end{figure}
\end{document}''')
            prepare_math_compatibility(root)
            prepare_captioned_minipages(root)
            result = subprocess.run(['pandoc', str(source), '-f', 'latex', '-t', 'html5', '--mathml'], capture_output=True, text=True, check=True)
            self.assertNotIn('Could not convert TeX math', result.stderr)
            self.assertIn('<math', result.stdout)
            for label in ('first', 'second'):
                self.assertIn(f'<figure id="fig:{label}">', result.stdout)
            for image in ('one.png', 'two.png'):
                self.assertIn(f'src="{image}"', result.stdout)
            self.assertIn('First', result.stdout)
            self.assertIn('Second', result.stdout)
