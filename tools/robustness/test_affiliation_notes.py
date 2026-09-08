"""Regression tests for template-specific author affiliation commands."""
import tempfile
import unittest
from pathlib import Path

from native.host import prepare_source_notes


class AffiliationNoteTests(unittest.TestCase):
    def test_included_acm_title_block_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            root = directory / "main.tex"
            root.write_text(r"""\documentclass{acmart}
\input{authors}
\begin{document}\maketitle
\begin{abstract}Abstract text.\end{abstract}
\end{document}""")
            (directory / "authors.tex").write_text(r"""\author{Ada Example}
\affiliation{\institution{Example University}\country{India}}
\email{ada@example.org}
""")
            (directory / "obsolete.tex").write_text(r"\affiliation{Wrong Institution}")
            self.assertGreaterEqual(prepare_source_notes(directory, root), 2)
            normalized = root.read_text()
            self.assertIn("Example University", normalized)
            self.assertIn("ada@example.org", normalized)
            self.assertNotIn("Wrong Institution", normalized)

    def test_aastex_affil_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            root = directory / "main.tex"
            root.write_text(r"""\documentclass{aastex631}
\author{Ada Example}
\affil{Example Observatory, India}
\email{ada@example.org}
\begin{document}\maketitle
\begin{abstract}Abstract text.\end{abstract}
\end{document}""")
            self.assertGreaterEqual(prepare_source_notes(directory, root), 2)
            normalized = root.read_text()
            self.assertIn("Example Observatory, India", normalized)
            self.assertIn("ada@example.org", normalized)


if __name__ == "__main__":
    unittest.main()
