import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from native import host


class UnresolvedReferenceTests(unittest.TestCase):
    def test_only_source_proven_undefined_reference_loses_dead_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'paper.epub'
            with zipfile.ZipFile(path,'w') as z:
                z.writestr('main.xhtml','''<html xmlns="http://www.w3.org/1999/xhtml"><body><p><a href="#undefined" data-reference="undefined">[undefined]</a> and <a href="#dropped" data-reference="dropped">[dropped]</a></p></body></html>''')
            host._repair_cross_file_fragments(path,undefined_references={'undefined'})
            with zipfile.ZipFile(path) as z:root=ET.fromstring(z.read('main.xhtml'))
            self.assertIsNone(root.find('.//{*}a[@href="#undefined"]'))
            self.assertIsNotNone(root.find('.//{*}a[@href="#dropped"]'))
            self.assertIn('[undefined]', ''.join(root.itertext()))
            self.assertIn('undefined',path.with_suffix('.source-warnings.json').read_text())
