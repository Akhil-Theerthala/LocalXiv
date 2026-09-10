from pathlib import Path
import tempfile
import subprocess
import shutil
import unittest
import xml.etree.ElementTree as E
from native.host import prepare_boxed_text, prepare_typed_references_and_algorithms, ConversionError


@unittest.skipUnless(shutil.which('pandoc'), 'Pandoc required')
class AlgorithmAndPromptTests(unittest.TestCase):
    def render(self, source, helper):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            path = directory / 'main.tex'
            path.write_text(source)
            helper(directory)
            self.assertEqual(helper(directory), 0)
            result = subprocess.run(['pandoc', '-f', 'latex', '-t', 'html5', '--mathml', str(path)], capture_output=True, text=True, check=True)
            return E.fromstring('<body>'+result.stdout+'</body>')

    def test_text_box_preserves_answer_and_existing_math(self):
        root = self.render(r'Write \boxed{answer}, or \boxed{A}. Preserve $\boxed{x+1}$. Literal \verb|\boxed{code}|.', prepare_boxed_text)
        boxes = root.findall('.//{http://www.w3.org/1998/Math/MathML}menclose')
        self.assertEqual(len(boxes), 3)
        self.assertEqual([''.join(b.itertext()) for b in boxes], ['answer','A','x+1'])
        self.assertIn(r'\boxed{code}', ''.join(root.itertext()))

    def test_algorithm_keeps_caption_conditions_comments_and_typed_links(self):
        source = r'''See \cref{alg:cluster}; results in \cref{table-results} and \cref{figure-results}.
\begin{algorithm}\caption{Bidirectional Entailment Clustering}
\begin{algorithmic}
\Require context $x$, set of meanings $C$.
\For{$2 \leq m \leq M$}
\For{$c \in C$}\Comment{Compare to already-processed meanings.}
\State $a \gets c_0$\Comment{Use first sequence.}
\If{\texttt{left} is \texttt{entailment} \textbf{and} \texttt{right} is \texttt{entailment}}
\State $c \gets c\cup a$\Comment{Put into existing class.}
\EndIf\EndFor
\State $C \gets C\cup a$\Comment{Gets own class.}
\EndFor
\Return $C$
\end{algorithmic}\label{alg:cluster}\end{algorithm}
\begin{table}\caption{Results}\label{table-results}\begin{tabular}{lr}A&2\\\end{tabular}\end{table}
\begin{figure}\includegraphics{a.png}\caption{Plot}\label{figure-results}\end{figure}'''
        root = self.render(source, prepare_typed_references_and_algorithms)
        text = ' '.join(''.join(root.itertext()).split())
        for phrase in ('Bidirectional Entailment Clustering','Compare to already-processed meanings.','Use first sequence.','left is entailment and right is entailment','Put into existing class.','Gets own class.','Return:', 'Table', 'Figure'):
            self.assertIn(phrase,text)
        self.assertGreaterEqual(len(root.findall('.//blockquote')),4)
        self.assertTrue(any(a.get('href') == '#alg:cluster' and 'Algorithm:' in ''.join(a.itertext()) for a in root.iter('a')))
        self.assertEqual(sum(e.get('id') == 'alg:cluster' for e in root.iter()),1)
        self.assertNotIn('[alg:cluster]',text)
        self.assertIn('2≤m≤M',text)
        self.assertIn('c∈C',text)

    def test_unsupported_or_unbalanced_algorithm_fails_explicitly(self):
        for content in (r'\Repeat X\Until',r'\For{$x$} X\EndIf'):
            with self.subTest(content=content), tempfile.TemporaryDirectory() as temp:
                path=Path(temp)/'main.tex'
                path.write_text(r'\begin{algorithm}\caption{Example}\begin{algorithmic}'+content+r'\end{algorithmic}\end{algorithm}')
                with self.assertRaises(ConversionError):
                    prepare_typed_references_and_algorithms(Path(temp))
