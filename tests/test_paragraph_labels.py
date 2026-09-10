"""Verify no-output TeX commands cannot swallow visible paragraph labels."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from xml.etree import ElementTree as ET

from native.host import prepare_noindent
from tests import test_source_notes as source_notes


class ParagraphLabelTests(unittest.TestCase):
    def test_grouped_labels_and_macro_bodies_survive_real_pandoc(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'main.tex'
            source.write_text(r'''\newcommand{\lead}[1]{\noindent{\bf #1}}
\noindent{\bf Closed-box access.} This text remains.

\lead{Generative adaptability.} Another paragraph.
% \noindent{A commented label.}
\verb|\noindent{Literal example.}|
''')
            self.assertEqual(prepare_noindent(root), 2)
            self.assertEqual(prepare_noindent(root), 0)
            normalized = source.read_text()
            self.assertIn(r'% \noindent{A commented label.}', normalized)
            self.assertIn(r'\verb|\noindent{Literal example.}|', normalized)
            result = subprocess.run(['pandoc', str(source), '-f', 'latex', '-t', 'html', '--mathml'], capture_output=True, text=True, check=True)
            tree = ET.fromstring('<div>' + result.stdout + '</div>')
            labels = [''.join(node.itertext()) for node in tree.iter('strong')]
            self.assertEqual(labels, ['Closed-box access.', 'Generative adaptability.'])
            source.write_text(r'\renewcommand{\noindent}[1]{Visible #1}\noindent{argument}')
            self.assertEqual(prepare_noindent(root), 0)

    def test_grouped_author_organization_is_retained_in_frontmatter(self):
        source = r'''\documentclass{article}\title{A paper}
\author{Ada and Grace\\{\Large Example Research Lab}}
\begin{document}\maketitle\begin{abstract}Abstract prose.\end{abstract}
\section{Method}Research prose.\end{document}'''
        with tempfile.TemporaryDirectory() as temporary:
            documents = source_notes.SourceNotesTests().render(Path(temporary), source)
            text = ' '.join(' '.join(''.join(document.itertext()).split()) for document in documents)
            self.assertEqual(text.count('Example Research Lab'), 1)
            self.assertLess(text.index('Abstract prose.'), text.index('Example Research Lab'))
            self.assertLess(text.index('Example Research Lab'), text.index('Research prose.'))
