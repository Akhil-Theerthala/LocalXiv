import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from native import host


class BibliographyKeyTests(unittest.TestCase):
    def test_anchor_encoding_is_distinct_for_punctuation_and_reserved_prefixes(self):
        keys=['RDAD','RDAD+','RDAD-','RDAD++','encoded-524441442b','author/year','author year','é','e','-','_']
        anchors=[host._reference_id(key) for key in keys]
        self.assertEqual(len(set(anchors)),len(keys))
        self.assertEqual(host._reference_id('ordinary-key'),'ref-ordinary-key')

    def test_distinct_keys_keep_distinct_citations_in_both_profiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for numeric in (False,True):
                with self.subTest(numeric=numeric):
                    source=root/str(numeric);source.mkdir()
                    (source/'main.tex').write_text(r'''\documentclass{article}\title{References}\author{Author}
\begin{document}\maketitle\begin{abstract}Two different methods must stay distinct.\end{abstract}
\section{Results}The base method\cite{RDAD} and extension\cite{RDAD+} differ.
\bibliography{refs}\end{document}''')
                    (source/'main.bbl').write_text(r'''\begin{thebibliography}{2}
\bibitem{RDAD} The original method.
\bibitem{RDAD+} A distinct extension.
\end{thebibliography}''')
                    def cover(svg,png):subprocess.run(['rsvg-convert','-o',str(png),str(svg)],check=True,capture_output=True)
                    output=root/(str(numeric)+'.epub')
                    with patch.object(host,'rasterize_cover',cover):host.convert_source(source,'2401.00001v1',output,numeric_citations=numeric)
                    with zipfile.ZipFile(output) as z:
                        trees=[ET.fromstring(z.read(n)) for n in z.namelist() if n.endswith('.xhtml')]
                    citations=[e for t in trees for e in t.iter() if 'citation' in e.get('class','').split()]
                    hrefs=[e.find('.//{*}a').get('href') for e in citations]
                    self.assertEqual(len(set(hrefs)),2)
                    targets={e.get('id'):''.join(e.itertext()) for t in trees for e in t.iter() if e.get('id')}
                    self.assertIn('original method',targets[hrefs[0].split('#')[-1]])
                    self.assertIn('distinct extension',targets[hrefs[1].split('#')[-1]])


if __name__=='__main__':unittest.main()
