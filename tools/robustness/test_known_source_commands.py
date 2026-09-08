"""Known corpus constructs: equivalent forms, idempotency, and invalid mutations."""
import sys
import tempfile
import unittest
import subprocess
from pathlib import Path
from xml.etree import ElementTree as ET
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from native import host
from papers.document import _safe_xhtml, _normalize_structure


class KnownSourceCommands(unittest.TestCase):
    def normalize(self, text, function):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / 'main.tex'
            path.write_text(text)
            function(root)
            result = path.read_text()
            function(root)
            self.assertEqual(result, path.read_text(), 'normalization must be idempotent')
            return result

    def test_repeat_dialects_preserve_condition_and_nested_body(self):
        body = r'''\begin{algorithm}\caption{Convergence}\begin{algorithmic}
\Repeat\State Update $x$.\If{$x>0$}\State Keep.\EndIf\Until{$\epsilon<\epsilon_{tol}$}
\end{algorithmic}\end{algorithm}'''
        expected = self.normalize(body, host.prepare_typed_references_and_algorithms)
        upper = body
        for name in ['Repeat', 'State', 'If', 'EndIf', 'Until']:
            upper = upper.replace('\\' + name, '\\' + name.upper())
        self.assertEqual(expected, self.normalize(upper, host.prepare_typed_references_and_algorithms))
        rendered = subprocess.run(['pandoc', '-f', 'latex', '-t', 'html'], input=expected, text=True, capture_output=True, check=True).stdout
        self.assertIn('Repeat', rendered)
        self.assertIn('Until', rendered)
        self.assertIn('Update', rendered)
        self.assertIn('Keep.', rendered)
        self.assertIn('epsilon', rendered)
        for damaged in [body.replace(r'\Repeat', ''), body.replace(r'\Until{$\epsilon<\epsilon_{tol}$}', ''), body.replace(r'\EndIf', ''), body.replace(r'\Until{$\epsilon<\epsilon_{tol}$}', r'\Until')]:
            with self.assertRaises(host.ConversionError):
                self.normalize(damaged, host.prepare_typed_references_and_algorithms)

    def test_circled_digits_match_literal_unicode_and_preserve_literals(self):
        literal = '% \\ding{172}\n' + r'\verb|\ding{173}|' + '\n'
        for i in range(10):
            text = literal + r'\ding ' + '{' + str(172+i) + '}'
            self.assertEqual(self.normalize(text, host.prepare_table_rules_and_checks), literal + chr(0x2460+i))
        with self.assertRaises(host.ConversionError):
            self.normalize(r'\ding{999}', host.prepare_table_rules_and_checks)

    def test_explicit_affiliations_preserve_first_and_last_institution(self):
        text = r"""\documentclass{article}
\author{Author$^1$\and Other$^2$\\
\affiliations
$^1$First Institution\\
$^2$Second Institution\\
\emails first@example.org, second@example.org}
\begin{document}\maketitle
\section*{Abstract}Abstract text.
% arxiv-kindle-abstract-end
\section{Method}Body.\end{document}"""
        def prepare(root): host.prepare_source_notes(root, root / 'main.tex')
        result = self.normalize(text, prepare)
        note = result.split('% arxiv-kindle-author-notes')[1]
        for value in ['First Institution', 'Second Institution', 'first@example.org', 'second@example.org']:
            self.assertEqual(note.count(value), 1)
        # An intervening comment or blank line cannot drop the first affiliation.
        altered = text.replace(r'\affiliations', '\\affiliations % marker\n')
        other = self.normalize(altered, prepare).split('% arxiv-kindle-author-notes')[1]
        self.assertEqual(' '.join(host._searchable_tex_source(note).split()),
                         ' '.join(host._searchable_tex_source(other).split()))

    def test_template_prose_macros_match_explicit_text(self):
        source = r"\documentclass{article}\begin{document}Before \say{quoted \emph{definition}} after.\acks{Support from Fund.}\end{document}"
        def prepare(root): host.prepare_package_text(root, root / 'main.tex')
        normalized = self.normalize(source, prepare)
        def render(text):
            return subprocess.run(['pandoc', '-f', 'latex', '-t', 'html'], input=text, text=True, capture_output=True, check=True).stdout
        explicit = source.replace(r"\say{quoted \emph{definition}}", "``quoted \\emph{definition}''").replace(r"\acks{Support from Fund.}", r"\section*{Acknowledgments}Support from Fund.")
        self.assertEqual(render(normalized), render(explicit))
        self.assertIn('Support from Fund.', render(normalized))
        self.assertIn('definition', render(normalized))
        custom = r"\newcommand{\say}[1]{Custom #1}" + source.replace(r"\acks{Support from Fund.}", '')
        self.assertEqual(self.normalize(custom, prepare), custom)
        commented = "% \\say{ignored}\n" + r"\documentclass{article}\begin{document}Text.\end{document}"
        self.assertEqual(self.normalize(commented, prepare), commented)

    def test_nonblind_acknowledgment_retains_grants_without_exposing_blind_block(self):
        source = r"\documentclass[nonblindrev]{informs3}\begin{document}Body.\ACKNOWLEDGMENT{Award \#2143176 and grant 866274.}\end{document}"
        def prepare(root): host.prepare_package_text(root, root / 'main.tex')
        converted = self.normalize(source, prepare)
        rendered = subprocess.run(['pandoc', '-f', 'latex', '-t', 'html'], input=converted, text=True, capture_output=True, check=True).stdout
        self.assertIn('Award #2143176 and grant 866274.', rendered)
        blind = source.replace('nonblindrev', 'blindrev')
        self.assertEqual(self.normalize(blind, prepare), blind)

    def test_image_table_keeps_caption_image_and_anchor(self):
        body = r"\caption{Measured scores}\label{tab:scores}\includegraphics{scores.png}"
        source = r"\begin{table}" + body + r"\end{table}"
        converted = self.normalize(source, host.prepare_table_labels)
        equivalent = r"\begin{figure}" + body + r"\end{figure}"
        def render(text):
            return subprocess.run(['pandoc', '-f', 'latex', '-t', 'html'], input=text, text=True, capture_output=True, check=True).stdout
        self.assertEqual(render(converted), render(equivalent))
        tree = ET.fromstring('<body>' + render(converted) + '</body>')
        self.assertIsNotNone(tree.find('.//*[@id="tab:scores"]'))
        self.assertEqual(tree.find('.//img').get('src'), 'scores.png')
        self.assertIn('Measured scores', ''.join(tree.itertext()))

    def test_empty_math_spacing_matches_omitted_spacing(self):
        def normalize(attribute):
            root = ET.fromstring('<math xmlns="http://www.w3.org/1998/Math/MathML"><mtable ' + attribute + '><mtr><mtd><mi>x</mi></mtd></mtr></mtable></math>')
            _normalize_structure(root)
            return ET.tostring(root)
        self.assertEqual(normalize('columnspacing=""'), normalize(''))
        self.assertNotEqual(normalize('columnspacing="2em"'), normalize(''))

    def test_url_escape_equivalence_preserves_text_and_safety(self):
        def clean(url):
            root = ET.fromstring('<html xmlns="http://www.w3.org/1999/xhtml"><a>Reference_label</a></html>')
            root[0].set('href', url)
            _safe_xhtml(root)
            once = ET.tostring(root)
            self.assertEqual(once, ET.tostring(_safe_xhtml(root)))
            self.assertEqual(root[0].text, 'Reference_label')
            return root[0].get('href')
        for url in ['https://openreview.net/pdf?id=xkev3_np08z', 'https://doi.org/10.1007/978-3-031-19433-7_2']:
            self.assertEqual(clean(url.replace('_', r'\_')), clean(url))
        self.assertEqual(clean('https://example.org/a%5Fb'), 'https://example.org/a%5Fb')
        with self.assertRaises(ValueError): clean('javascript:alert(1)')

if __name__ == '__main__': unittest.main()
