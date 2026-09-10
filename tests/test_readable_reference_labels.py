"""Generated reader and EPUB references use readable labels without invented numbers."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as E
import zipfile

from papers.document import XHTML, build_document


@unittest.skipUnless(all(shutil.which(t) for t in ('node','rsvg-convert','epubcheck')), 'EPUB toolchain required')
class ReadableReferenceTests(unittest.TestCase):
    def test_equation_labels_and_duplicate_algorithm_prefix_in_both_profiles(self):
        with tempfile.TemporaryDirectory() as temp:
            directory=Path(temp)
            reader=directory/'reader'
            reader.mkdir()
            (reader/'spine.json').write_text(json.dumps(['one.xhtml','two.xhtml']))
            (reader/'one.xhtml').write_text(f'''<html xmlns="{XHTML}"><head><title>References</title></head><body><h1>References</h1>
<p>Use Equation <a href="two.xhtml#eq:raw">[eq:raw]</a>. Then <em>Equation</em> <a href="two.xhtml#eq:raw">[eq:raw]</a>. See <a href="two.xhtml#eq:raw">[eq:raw]</a>.</p>
<p>Keep Equation <a href="two.xhtml#eq:raw">3</a>, <a href="two.xhtml#ordinary">[ordinary]</a>, and Algorithm <a href="two.xhtml#alg:test">Algorithm: Clustering</a>.</p>
</body></html>''')
            (reader/'two.xhtml').write_text(f'''<html xmlns="{XHTML}"><head><title>Targets</title></head><body><h1>Targets</h1>
<math xmlns="http://www.w3.org/1998/Math/MathML" id="eq:raw" display="block"><mi>x</mi></math>
<p id="ordinary">An ordinary text target.</p><div id="alg:test"><p>Algorithm: Clustering</p></div>
</body></html>''')
            document=build_document(directory,{'arxiv_id':'2501.00001v1','title':'Reference fixture','authors':'Author'},'test')
            paths=[E.parse(reader/'one.xhtml').getroot()]
            for profile in ('semantic.epub','paper.epub'):
                with zipfile.ZipFile(directory/profile) as book:
                    paths.append(E.fromstring(book.read('EPUB/one.xhtml')))
            for root in paths:
                links=list(root.findall('.//{*}a'))
                self.assertEqual([''.join(e.itertext()) for e in links],['Equation','Equation','equation','3','[ordinary]','Algorithm: Clustering'])
                self.assertTrue(all(e.get('href')=='two.xhtml#eq:raw' for e in links[:4]))
                text=' '.join(''.join(root.itertext()).split())
                self.assertNotIn('[eq:raw]',text)
                self.assertNotIn('Equation Equation',text)
                self.assertNotIn('Algorithm Algorithm',text)
            self.assertFalse(any('[eq:raw]' in p['text'] for p in document['passages']))
