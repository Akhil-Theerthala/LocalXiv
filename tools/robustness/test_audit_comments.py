import io
import json
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.robustness.audit import source_inventory


def make_source(path, main, extra=None):
    with tarfile.open(path, 'w') as archive:
        files = {'main.tex': main, 'main.bbl': r'\bibitem{paper} Author.\newblock Title.'}
        if extra:
            files.update(extra)
        for name, text in files.items():
            data = text.encode()
            member = tarfile.TarInfo(name)
            member.size = len(data)
            archive.addfile(member, io.BytesIO(data))


class AuditCommentTests(unittest.TestCase):
    def test_commented_graphics_and_includes_do_not_change_inventory(self):
        base = r'''\documentclass{article}
\begin{document}
100\% retained prose.
\input{chapter}
\end{document}'''
        chapter = r'''\begin{figure}\includegraphics{active.png}\caption{Active plot}\end{figure}'''
        augmented = base.replace(
            r'100\% retained prose.',
            r'''100\% retained prose.
% \includegraphics{commented.png}
% \input{ignored}
\begin{comment}
\includegraphics{rates.png}
\input{commented-chapter}
\end{comment}
\begin{verbatim}
\begin{figure}\includegraphics{literal.png}\end{figure}
\end{verbatim}''')
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / 'first.tar'
            second = Path(tmp) / 'second.tar'
            make_source(first, base, {'chapter.tex': chapter})
            make_source(second, augmented, {'chapter.tex': chapter,
                                            'ignored.tex': r'\includegraphics{also-ignored.png}',
                                            'commented-chapter.tex': r'\includegraphics{also-ignored.png}'})
            before, before_text = source_inventory(first)
            after, after_text = source_inventory(second)
        for key in ('root', 'reachable_tex_files', 'graphics_commands', 'distinct_literal_graphics_targets',
                    'figures', 'captions', 'caption_texts', 'heading_texts'):
            self.assertEqual(before[key], after[key], key)
        self.assertEqual(before_text, after_text)
        self.assertEqual(before['graphics_commands'], 1)
        self.assertEqual(before['distinct_literal_graphics_targets'], 1)


if __name__ == '__main__':
    unittest.main()
