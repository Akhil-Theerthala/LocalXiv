"""Exercise the selected release dependencies, not the developer node_modules."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app/macos'))
spec = importlib.util.spec_from_file_location('build_release', ROOT / 'app/macos/build-release.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)
sys.path.pop(0)


class BundleSizeTests(unittest.TestCase):
    def test_selected_packages_render_math_and_parse_xml(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            build.copy_node_modules(ROOT / 'node_modules', work / 'node_modules')
            self.assertLess(build.file_bytes(work), 20 * 1024**2)
            self.assertFalse((work / 'node_modules/@modelcontextprotocol').exists())
            self.assertFalse((work / 'node_modules/@resvg').exists())
            self.assertFalse((work / 'node_modules/excalidrawer').exists())
            self.assertFalse((work / 'node_modules/mathjax-full/ts').exists())
            self.assertTrue((work / 'node_modules/mathjax-full/es5/tex-svg.js').is_file())
            for name in ('math.js', 'tex_math.js', 'arxiv_html.js'):
                shutil.copy2(ROOT / 'papers' / name, work / name)
            tex = subprocess.run(['node', str(work / 'tex_math.js')], input=json.dumps([
                {'tex': r'\frac{1}{2}+\alpha', 'display': True},
                {'tex': r'\ce{H2O}', 'display': False},
                {'tex': r'\nonexistentcommand{x}', 'display': False}]),
                text=True, capture_output=True, check=True)
            formulas = json.loads(tex.stdout)
            self.assertIn('mathml', formulas[0])
            self.assertIn('mathml', formulas[1])
            self.assertIn('error', formulas[2])
            math = subprocess.run(['node', str(work / 'math.js')], input=json.dumps([
                {'math': item['mathml'], 'display': True} for item in formulas[:2]]),
                text=True, capture_output=True, check=True)
            self.assertTrue(all('<svg' in item['svg'] for item in json.loads(math.stdout)))
            subprocess.run(['node', '-e', "const {DOMParser}=require('@xmldom/xmldom'); if(new DOMParser().parseFromString('<p>ok</p>','text/xml').documentElement.textContent!=='ok')process.exit(1)"],
                           cwd=work, check=True, capture_output=True)
    def test_nested_dependency_resolution_and_missing_dependency_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / 'source'
            for name, dependencies in [('mathjax-full', {'child': '1'}), ('mathjax-full/node_modules/child', {}),
                                       ('@xmldom/xmldom', {})]:
                directory = source / name
                directory.mkdir(parents=True)
                (directory / 'package.json').write_text(json.dumps({
                    'name': name.split('node_modules/')[-1], 'version': '0.5.12', 'dependencies': dependencies}))
            build.copy_node_modules(source, Path(temporary) / 'copied')
            self.assertTrue((Path(temporary) / 'copied/mathjax-full/node_modules/child/package.json').exists())
            shutil.rmtree(source / 'mathjax-full/node_modules/child')
            with self.assertRaisesRegex(RuntimeError, 'Missing runtime dependency child'):
                build.copy_node_modules(source, Path(temporary) / 'missing')

    def test_budget_rejects_reintroduced_full_jdk(self):
        with tempfile.TemporaryDirectory() as temporary:
            app = Path(temporary)
            (app / 'Contents/Resources/runtime/vendor/openjdk').mkdir(parents=True)
            with patch.object(build, 'file_bytes', return_value=380 * 1024**2):
                with self.assertRaisesRegex(RuntimeError, 'openjdk exceeds'):
                    build.size_inventory(app)


if __name__ == '__main__':
    unittest.main()
