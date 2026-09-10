"""Check note and bibliography wording in real Pandoc EPUB output."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

from native.host import (prepare_source_notes, prepare_abstracts, prepare_front_notices, prepare_compiled_bibliography,
                         _finalize_epub, _repair_cross_file_fragments, validate_epub)


@unittest.skipUnless(shutil.which('pandoc'), 'Pandoc is required')
class SourceNotesTests(unittest.TestCase):
    def test_inline_bibliography_and_front_notice_preserve_content_and_order(self):
        source = r"""\documentclass{article}\begin{document}
\begin{center}Permission notice retained verbatim.\end{center}
\maketitle
\begin{abstract}Complete abstract.\end{abstract}
\section{Introduction}Claim \cite{first,second}.
\begin{thebibliography}{2}
\bibitem{first}A. Author.\newblock First title.
\bibitem{second}B. Author.\newblock Second title.
\end{thebibliography}
\section*{Appendix}Final evidence.
\end{document}"""
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary); root = directory / 'main.tex'; root.write_text(source)
            prepare_abstracts(directory)
            self.assertEqual(prepare_front_notices(root),1)
            self.assertEqual(prepare_front_notices(root),0)
            entries = prepare_compiled_bibliography(root)
            self.assertEqual([e.key for e in entries],['first','second'])
            text = root.read_text()
            self.assertEqual(text.count('Permission notice retained verbatim.'),1)
            self.assertLess(text.index('{Abstract}'),text.index('Permission notice'))
            self.assertLess(text.index('Second title.'),text.index('{Appendix}'))
            output = directory / 'paper.epub'
            subprocess.run(['pandoc',str(root),'-f','latex','-t','epub3','--epub-title-page=false','-o',str(output)],cwd=directory,capture_output=True,check=True)
            _finalize_epub(output,entries,numeric_citations=True)
            _repair_cross_file_fragments(output)
            validate_epub(output,require_abstract=True)
            with zipfile.ZipFile(output) as book:
                docs = [ET.fromstring(book.read(n)) for n in book.namelist() if n.endswith('.xhtml')]
            citations = [e for d in docs for e in d.iter() if 'citation' in e.get('class','').split()]
            self.assertEqual(''.join(citations[0].itertext()),'[1, 2]')

    def render(self, directory, source, bbl=None):
        root = directory / 'main.tex'
        root.write_text(source)
        prepare_abstracts(directory)
        self.assertEqual(prepare_abstracts(directory), 0)
        prepare_source_notes(directory, root)
        self.assertEqual(prepare_source_notes(directory, root), 0)
        entries = []
        if bbl:
            root.with_suffix('.bbl').write_text(bbl)
            entries = prepare_compiled_bibliography(root)
        output = directory / 'paper.epub'
        subprocess.run(['pandoc', str(root), '-f', 'latex', '-t', 'epub3', '--mathml', '--epub-title-page=false', '-o', str(output)], cwd=directory, capture_output=True, check=True)
        _finalize_epub(output, entries, numeric_citations=True)
        _repair_cross_file_fragments(output)
        validate_epub(output)
        with zipfile.ZipFile(output) as book:
            documents = [ET.fromstring(book.read(name)) for name in book.namelist() if name.endswith('.xhtml')]
        return documents

    def test_table_and_paired_notes_keep_cell_marker_text_and_backlinks(self):
        source = r'''\documentclass{article}\begin{document}
\begin{table}\begin{tabular}{lc}
GSM8K\tablefootnote{The Brier score is dominated by incorrect questions with low P(IK); the threshold is 0.5.} & 0.624 / 0.200 \\
Other\footnotemark & 0.752 / 0.121 \\
\end{tabular}\caption{Results}\label{tab:results}\end{table}
\footnotetext{The paired table note preserves its qualification.}
\end{document}'''
        with tempfile.TemporaryDirectory() as temporary:
            documents = self.render(Path(temporary), source)
            elements = [e for d in documents for e in d.iter()]
            cells = [e for e in elements if e.tag.endswith('}td')]
            self.assertTrue(any('GSM8K' in ''.join(c.itertext()) and c.find('.//{*}a') is not None for c in cells))
            refs = [e for e in elements if e.get('role') == 'doc-noteref']
            self.assertEqual(len(refs), 2)
            self.assertEqual(sum(e.get('role') == 'doc-backlink' for e in elements), 2)
            text = ' '.join(' '.join(''.join(d.itertext()).split()) for d in documents)
            for value in ('incorrect questions with low P(IK)', 'threshold is 0.5', 'paired table note preserves its qualification', '0.624 / 0.200'):
                self.assertIn(value, text)

    def test_standalone_note_and_author_thanks_are_visible_without_orphan_refs(self):
        source = r'''\documentclass{article}
\title{A paper}\author{Ada\thanks{Supported by RIE2025, Award I2301E0020. \textit{Corresponding author: Ada.}}\thanks{Department of Computing, Example University.}}
\begin{document}\maketitle
\begin{abstract}An abstract.\end{abstract}
\begin{table}\begin{tabular}{lc}Combined & -- \\\end{tabular}\caption{Probabilities}\end{table}
\footnotetext{Since we cannot get the combined probabilities of two uncertainties, we cannot get the AUROC score.}
% \tablefootnote{Do not transform comments.}
Literal: \verb|\footnotetext{Literal code}|.
\end{document}'''
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            documents = self.render(directory, source)
            text = ' '.join(' '.join(''.join(d.itertext()).split()) for d in documents)
            for value in ('RIE2025', 'I2301E0020', 'Corresponding author: Ada.', 'Department of Computing', 'we cannot get the AUROC score.'):
                self.assertIn(value, text)
            self.assertFalse(any(e.get('role') == 'doc-noteref' for d in documents for e in d.iter()))
            normalized = (directory / 'main.tex').read_text()
            self.assertIn(r'% \tablefootnote{Do not transform comments.}', normalized)
            self.assertIn(r'\verb|\footnotetext{Literal code}|', normalized)

    def test_preamble_braced_abstract_keeps_prose_and_footnote(self):
        source = r"""\documentclass{article}\title{A paper}
\abstract{We study verbal uncertainty.\footnote{Verbal means expressed in words, rather than spoken.} The full abstract conclusion remains.}
\begin{document}\maketitle\section{Introduction}The introduction.\end{document}"""
        with tempfile.TemporaryDirectory() as temporary:
            documents = self.render(Path(temporary), source)
            text = ' '.join(' '.join(''.join(d.itertext()).split()) for d in documents)
            for phrase in ('We study verbal uncertainty.', 'rather than spoken.', 'The full abstract conclusion remains.'):
                self.assertEqual(text.count(phrase), 1)
            elements = [e for d in documents for e in d.iter()]
            self.assertEqual(sum(e.get('role') == 'doc-noteref' for e in elements), 1)
            self.assertEqual(sum(e.get('role') == 'doc-backlink' for e in elements), 1)

    def test_author_metadata_follows_abstract_before_research_sections(self):
        source = r"""\documentclass{article}
\author{Ada\thanks{Equal contribution.}}
\affiliation[1]{Meta FAIR}
\affiliation[2]{University of Toronto}
\contribution[*]{Work done during Internship at Meta FAIR}
\correspondence{\href{mailto:ada@example.org}{ada@example.org}}
\abstract{The complete abstract ends here.}
\begin{document}\maketitle\section{Introduction}Research starts here.\end{document}"""
        with tempfile.TemporaryDirectory() as temporary:
            documents = self.render(Path(temporary), source)
            chapters = [d for d in documents if any(e.tag.endswith('}h1') and ''.join(e.itertext()) == 'Abstract' for e in d.iter())]
            self.assertEqual(len(chapters), 1)
            abstract = chapters[0]
            text = ' '.join(''.join(abstract.itertext()).split())
            self.assertLess(text.index('The complete abstract ends here.'), text.index('Equal contribution.'))
            for phrase in ('Affiliation 1: Meta FAIR', 'Affiliation 2: University of Toronto', 'Work done during Internship', 'ada@example.org'):
                self.assertIn(phrase, text)
            self.assertTrue(any(e.get('href') == 'mailto:ada@example.org' for e in abstract.iter()))
            self.assertNotIn('Research starts here.', text)

    def test_author_thanks_declared_inside_document_before_maketitle(self):
        source = r"""\documentclass{article}\begin{document}
\title{Paper\thanks{Title support note.}}
\author{Ada\thanks{Supported by RIE2025, Award I2301E0020.}\thanks{Correspondence: ada@example.org.}}
\maketitle\begin{abstract}Abstract conclusion.\end{abstract}
\section{Introduction}Research text.
% \author{Comment\thanks{Excluded comment note.}}
\end{document}"""
        with tempfile.TemporaryDirectory() as temporary:
            documents = self.render(Path(temporary), source)
            abstract = next(d for d in documents if any(e.tag.endswith('}h1') and ''.join(e.itertext()) == 'Abstract' for e in d.iter()))
            text = ' '.join(''.join(abstract.itertext()).split())
            for phrase in ('Title support note.', 'RIE2025', 'I2301E0020', 'ada@example.org'):
                self.assertEqual(text.count(phrase), 1)
            self.assertLess(text.index('Abstract conclusion.'), text.index('Title support note.'))
            self.assertNotIn('Excluded comment note.', text)
            self.assertNotIn('Research text.', text)

    def test_separator_on_its_own_line_does_not_split_a_reference(self):
        source = r'\documentclass{article}\begin{document}Claim \cite{one,two}.\bibliography{main}\end{document}'
        bbl = r"""\begin{thebibliography}{2}
\bibitem{one} An Author. 2020.
\newblock {A title}.
\newblock
  \url{https://example.org/reference}.
\newblock [Accessed 26-01-2025].

\bibitem{two} Another Author. 2021.\newblock {Another title}.
\end{thebibliography}"""
        with tempfile.TemporaryDirectory() as temporary:
            documents = self.render(Path(temporary), source, bbl)
            entries = [e for d in documents for e in d.iter() if e.get('id', '').startswith('ref-')]
            self.assertEqual(len(entries), 2)
            first = next(e for e in entries if e.get('id') == 'ref-one')
            text = ' '.join(''.join(first.itertext()).split())
            for phrase in ('A title', 'https://example.org/reference', '[Accessed 26-01-2025]'):
                self.assertIn(phrase, text)

    def test_newblock_preserves_braced_titles_venues_and_identifiers(self):
        source = r'\documentclass{article}\begin{document}Claim \cite{rho,r,whole}.\bibliography{main}\end{document}'
        bbl = r'''\begin{thebibliography}{3}
\bibitem{rho} Authors.\newblock {RHO}: Reducing hallucination.\newblock {ACL 2023}.\newblock {arXiv:1234.5678}.
\bibitem{r} Authors.\newblock {R}-tuning: A title.
\bibitem{whole} Authors.\newblock {TriviaQA: A Large Scale Dataset for Reading Comprehension and Question Answering}.
\end{thebibliography}'''
        with tempfile.TemporaryDirectory() as temporary:
            documents = self.render(Path(temporary), source, bbl)
            text = ' '.join(' '.join(''.join(d.itertext()).split()) for d in documents)
            for value in ('RHO', 'R-tuning', 'ACL 2023', 'arXiv:1234.5678', 'TriviaQA: A Large Scale Dataset for Reading Comprehension and Question Answering'):
                self.assertIn(value, text)


if __name__ == '__main__':
    unittest.main()
