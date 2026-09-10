import json
import tempfile
import unittest
import zipfile
import subprocess
from unittest.mock import patch
from pathlib import Path
from xml.etree import ElementTree as ET


class PaperTests(unittest.TestCase):
    def test_math_table_note_markers_keep_symbols_and_superscripts(self):
        from native.host import prepare_package_math
        literal = r'''% $\text{\textdagger}$
\verb|$\text{\textdagger}$|
\begin{verbatim}
$\text{\textdaggerdbl}$
\end{verbatim}
'''
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'main.tex'
            path.write_text(r'''\documentclass{article}\begin{document}
\begin{tabular}{lc}
PnPNet$^\text{\textdagger}$ & 1.15 \\
Tracker$^{\text{\textdaggerdbl}}$ & 0.378
\end{tabular}
${\text{\textdagger}}$: Reimplemented. $\text{\textdaggerdbl marker}$
''' + literal + r'\end{document}')
            prepare_package_math(Path(tmp))
            self.assertIn(literal, path.read_text())
            self.assertEqual(prepare_package_math(Path(tmp)), 0)
            result = subprocess.run(['pandoc', str(path), '-f', 'latex', '-t', 'html', '--mathml'],
                                    capture_output=True, text=True, check=True)
            self.assertNotIn('Could not convert TeX math', result.stderr)
            root = ET.fromstring('<body>' + result.stdout + '</body>')
            self.assertEqual([e.text for e in root.findall('.//{*}msup/{*}mtext')], ['†', '‡'])
            self.assertEqual([e.text for e in root.findall('.//{*}math//{*}mtext')],
                             ['†', '‡', '†', '‡ marker'])
            self.assertEqual([''.join(e.itertext()) for e in root.findall('.//tr/td')][1::2],
                             ['1.15', '0.378'])

    def test_unused_filler_import_preserves_active_content_and_used_package(self):
        from papers.worker import omit_unused_filler
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            p=source/'main.tex'
            p.write_text('\\usepackage{lipsum}\nReal paper text.\n% \\lipsum[1]\n')
            self.assertEqual(omit_unused_filler(source), 1)
            self.assertIn('Real paper text.',p.read_text())
            self.assertIn('% \\lipsum[1]',p.read_text())
            p.write_text('\\usepackage{lipsum}\n\\newcommand{\\bodytext}{\\lipsum[1]}\n')
            self.assertEqual(omit_unused_filler(source), 0)
            self.assertIn('\\usepackage{lipsum}',p.read_text())

    def test_pandoc_numeric_citations_preserve_names_locators_and_links(self):
        from native import host
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source'
            source.mkdir()
            (source / 'main.tex').write_text(r'''\documentclass{article}
\usepackage{natbib}\title{Citation test}\author{An Author}
\begin{document}\maketitle\begin{abstract}A complete abstract.\end{abstract}
\section{Method}Prior work \citep[see][p.~4]{a,b}. \citet{a} argue this.
\bibliography{refs}\end{document}''')
            (source / 'main.bbl').write_text(r'''\begin{thebibliography}{2}
\bibitem[Matlin et~al.(2025)]{a} Matlin et al. First work. 2025.
\bibitem[Buho(2026)]{b} Buho. Second work. 2026.
\end{thebibliography}''')
            def cover(svg, png):
                subprocess.run(['rsvg-convert','-w','1200','-h','1600','-o',str(png),str(svg)],check=True,capture_output=True)
            with patch.object(host, 'rasterize_cover', cover):
                host.convert_source(source,'2503.14477v2',root/'paper.epub',numeric_citations=True)
            with zipfile.ZipFile(root/'paper.epub') as z:
                docs = [ET.fromstring(z.read(n)) for n in z.namelist() if n.endswith('.xhtml')]
            cites = [e for d in docs for e in d.iter() if 'citation' in e.get('class','').split()]
            self.assertEqual(len(cites),2)
            self.assertNotIn('2025',''.join(cites[0].itertext()))
            self.assertIn('p.', ''.join(cites[0].itertext()))
            self.assertIn('Matlin', ''.join(cites[1].itertext()))
            self.assertEqual(len(list(cites[0].iter('{http://www.w3.org/1999/xhtml}a'))),2)

    def test_arxiv_declared_root_precedes_larger_author_response(self):
        from native.host import find_root_tex, ConversionError
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'paper.tex').write_text(r'\documentclass{article}\begin{document}Paper\end{document}')
            (root/'response.tex').write_text(r'\documentclass{article}\begin{document}Long response to reviewers\end{document}')
            manifest = root/'00README.json'
            manifest.write_text(json.dumps({'sources':[{'usage':'toplevel','filename':'paper.tex'},{'usage':'ignore','filename':'response.tex'}]}))
            self.assertEqual(find_root_tex(root), (root/'paper.tex').resolve())
            manifest.write_text(json.dumps({'sources':[{'usage':'toplevel','filename':'../outside.tex'}]}))
            with self.assertRaises(ConversionError): find_root_tex(root)

    def test_package_notation_keeps_math_and_literal_examples(self):
        from native.host import prepare_package_math
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root/'main.tex'
            path.write_text(r'\documentclass{article}\usepackage{physics}\begin{document}$\abs{x}$ $\Large[\frac{1}{2}\Large]$ $\mathds{1}$\[\centering z=1\]\verb|\abs{example}|\end{document}')
            prepare_package_math(root)
            self.assertIn(r'\verb|\abs{example}|', path.read_text())
            result = subprocess.run(['pandoc',str(path),'-f','latex','-t','html','--mathml'],capture_output=True,text=True,check=True)
            self.assertNotIn('Could not convert', result.stderr)
            self.assertIn('<math', result.stdout)
            formula = ET.fromstring(result.stdout).find('.//{*}math')
            self.assertEqual([e.text for e in formula.findall('.//{*}mo')], ['|', '|'])

    def test_paper_routes_and_trust_boundary(self):
        from papers.acquire import paper_id
        for url, expected in [
            ('https://arxiv.org/pdf/2503.14477v2.pdf', '2503.14477v2'),
            ('https://www.alphaxiv.org/abs/2503.14477?chatId=a', '2503.14477'),
            ('https://www.alphaxiv.org/overview/2410.20199v1?chatId=a', '2410.20199v1'),
            ('https://arxiv.org/html/2503.14477v2', '2503.14477v2'),
            ('https://arxiv.org/abs/hep-th/9901001v1', 'hep-th/9901001v1'),
        ]:
            self.assertEqual(paper_id(url), expected)
        for url in ['https://arxiv.org.evil.test/abs/2503.14477',
                    'https://user@arxiv.org/abs/2503.14477',
                    'https://arxiv.org:123/abs/2503.14477',
                    'https://arxiv.org/abs/2503.14477/../../etc/passwd']:
            with self.assertRaises(ValueError):
                paper_id(url)

    def test_numeric_xml_retains_narrative_names_and_locators(self):
        from papers.document import numeric_latexml
        xml = '''<document xmlns="http://dlmf.nist.gov/LaTeXML">
          <p><cite class="ltx_citemacro_citep">(see <bibref bibrefs="a,b" show="AuthorsPhrase1Year"><bibrefphrase>, </bibrefphrase></bibref>, p. 4)</cite>
          <cite class="ltx_citemacro_citet"><bibref bibrefs="a" show="Authors Phrase1YearPhrase2"><bibrefphrase>(</bibrefphrase><bibrefphrase>)</bibrefphrase></bibref></cite></p>
          <bibliography><biblist><bibitem key="a"><tags><tag role="number">1</tag><tag role="refnum">Matlin 2025</tag><tag role="authors">Matlin</tag></tags></bibitem>
          <bibitem key="b"><tags><tag role="number">2</tag><tag role="refnum">Buho 2026</tag></tags></bibitem></biblist></bibliography></document>'''
        result = ET.fromstring(numeric_latexml(xml.encode()))
        refs = result.findall('.//{*}bibref')
        self.assertEqual(refs[0].get('show'), 'Number')
        self.assertIn('Authors', refs[1].get('show'))
        self.assertIn('Number', refs[1].get('show'))
        self.assertEqual(result.find('.//{*}cite').text, '[see ')
        self.assertEqual(refs[0].tail, ', p. 4]')
        self.assertEqual([e.text for e in result.findall('.//{*}tag[@role="refnum"]')], ['[1]', '[2]'])
        self.assertEqual(result.find('.//{*}tag[@role="authors"]').text, 'Matlin')

    def test_redundant_labels_and_resized_tables_keep_content(self):
        from papers.document import _normalize_structure, local
        tree = ET.fromstring('<div><span id="table1" data-label="table1"/><span class="ltx_transformed_inner"><table id="table1"><tr><td>Result</td></tr></table></span></div>')
        _normalize_structure(tree)
        self.assertEqual(len([e for e in tree.iter() if e.get('id') == 'table1']), 1)
        self.assertEqual(local(tree[1].tag), 'div')
        self.assertEqual(''.join(tree.itertext()), 'Result')
        duplicate = ET.fromstring('<div><figure id="same">First</figure><figure id="same">Second</figure><a href="#same">2</a></div>')
        warnings = []
        _normalize_structure(duplicate, {'same':2}, warnings)
        self.assertEqual(duplicate[1].get('id'), 'same')
        self.assertNotEqual(duplicate[0].get('id'), 'same')
        self.assertEqual(''.join(duplicate.itertext()), 'FirstSecond2')
        self.assertEqual(len(warnings),1)
        spaced = ET.fromstring('<div id="a b"><a href="#a%20b">Link</a></div>')
        _normalize_structure(spaced)
        self.assertEqual(spaced[0].get('href'), '#'+spaced.get('id'))
        with self.assertRaisesRegex(ValueError, 'ambiguous duplicate'):
            _normalize_structure(ET.fromstring('<div><figure id="same">First</figure><figure id="same">Second</figure></div>'))

    def test_document_math_and_epub_contract(self):
        from papers.document import build_document
        from native.host import validate_epub
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reader = root / 'reader'
            reader.mkdir()
            (reader / 'main.xhtml').write_text('''<html xmlns="http://www.w3.org/1999/xhtml"><head><title>Calibration</title></head><body>
              <h1>Calibration</h1><h2 id="abstract">Abstract</h2><p>A complete abstract.</p>
              <h2 id="method">Method</h2><p>Inline <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline" alttext="x_i"><msub><mi>x</mi><mi>i</mi></msub></math> remains readable. <a href="#ref1">[1]</a></p>
              <div><math xmlns="http://www.w3.org/1998/Math/MathML" display="block" alttext="y=important_result"><mi>y</mi><mo>=</mo><mi>important_result</mi></math></div>
              <h2>References</h2><p id="ref1">Matlin. Work. 2025.</p></body></html>''')
            doc = build_document(root, {'arxiv_id': '2503.14477v2', 'title': 'Calibration', 'authors': 'Author'}, 'test')
            self.assertGreaterEqual(len(doc['passages']), 3)
            self.assertTrue(all(p['href'].startswith('reader/') for p in doc['passages']))
            self.assertTrue(any('important_result' in p['text'] for p in doc['passages']))
            validate_epub(root / 'paper.epub')
            validate_epub(root / 'semantic.epub')
            with zipfile.ZipFile(root / 'paper.epub') as z:
                t = z.read('EPUB/main.xhtml').decode()
                self.assertIn('vertical-align:', t)
                self.assertIn('math-image', t)
                self.assertNotIn('<math', t)
                self.assertTrue(any(n.endswith('.png') and 'math' in n for n in z.namelist()))
            self.assertEqual(json.loads((root / 'document.json').read_text())['arxiv_id'], '2503.14477v2')


if __name__ == '__main__':
    unittest.main()
