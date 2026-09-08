import subprocess, tempfile, unittest
from pathlib import Path
from native import host

class BibtexRepairTests(unittest.TestCase):
    def test_normalizes_parentheses_without_touching_values(self):
        source = r'''@String(PAMI = {IEEE (Pattern) Anal. Mach. Intell.})
@string ( X = "quoted \\"value\\"" )
@article{paper, author = {A. Author}, title = {Title}, journal = PAMI, year = 2024}'''
        expected = r'''@String{PAMI = {IEEE (Pattern) Anal. Mach. Intell.}}
@string { X = "quoted \\"value\\"" }
@article{paper, author = {A. Author}, title = {Title}, journal = PAMI, year = 2024}'''
        self.assertEqual(host._normalize_bibtex_string_delimiters(source), expected)

    def test_equivalent_forms_have_same_pandoc_citation(self):
        prefix = "---\ntitle: Test\nbibliography: refs.bib\n---\nSee [@paper]."
        forms = ['@String(PAMI = {IEEE Pattern Anal. Mach. Intell.})', '@String{PAMI = {IEEE Pattern Anal. Mach. Intell.}}']
        outputs = []
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index, declaration in enumerate(forms):
                (root / "input.md").write_text(prefix)
                (root / "refs.bib").write_text(declaration + "\n@article{paper, author={Author, Ada}, title={Paper}, journal=PAMI, year=2024}\n")
                changed = host.prepare_bibtex_string_delimiters(root)
                result = subprocess.run(["pandoc", "input.md", "-t", "html", "--citeproc", "-M", "link-citations=true", "--bibliography", "refs.bib"], cwd=root, text=True, capture_output=True, check=True)
                outputs.append(result.stdout)
                self.assertEqual(changed, [root / "refs.bib"] if index == 0 else [])
        self.assertEqual(outputs[0], outputs[1]); self.assertIn("Author", outputs[0])
        self.assertIn('data-cites="paper"', outputs[0])
        self.assertIn('id="ref-paper"', outputs[0])
        self.assertIn('href="#ref-paper"', outputs[0])

    def test_comments_nested_and_escaped_values_are_preserved(self):
        source = r'''% @String(ignored = {x})
@String(foo = {a (b) {c} \\} % comment
still value)'''
        expected = r'''% @String(ignored = {x})
@String{foo = {a (b) {c} \\} % comment
still value}'''
        self.assertEqual(host._normalize_bibtex_string_delimiters(source), expected)

    def test_malformed_declaration_is_unchanged(self):
        source = "@String(foo = {unterminated (value}\n"
        self.assertEqual(host._normalize_bibtex_string_delimiters(source), source)

    def test_does_not_rewrite_string_looking_text_inside_entries_or_comments(self):
        source = r'''@comment(@String(ignored = {x}))
@article{paper,
  title = {@String(inside = {literal})},
  journal = PAMI
}
@String(PAMI = {IEEE Pattern Anal. Mach. Intell.})'''
        expected = source.replace('@String(PAMI = {IEEE Pattern Anal. Mach. Intell.})',
                                  '@String{PAMI = {IEEE Pattern Anal. Mach. Intell.}}')
        self.assertEqual(host._normalize_bibtex_string_delimiters(source), expected)

    def test_braces_protect_parentheses_and_quotes(self):
        source = r'''@String(foo = {a ) b "quote ) {nested}})
@article{paper, title = {literal @String(inner = {unchanged})}}'''
        expected = '@String{foo = {a ) b "quote ) {nested}}}\n@article{paper, title = {literal @String(inner = {unchanged})}}'
        self.assertEqual(host._normalize_bibtex_string_delimiters(source), expected)

    def test_malformed_outer_entry_does_not_rewrite_inner_string(self):
        source = '@article{paper, title = {broken @String(inner = {literal})}\n'
        self.assertEqual(host._normalize_bibtex_string_delimiters(source), source)

    def test_prepare_recurses_into_bibtex_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            nested = Path(directory) / "refs"; nested.mkdir()
            path = nested / "journal.bibtex"
            path.write_text("@String(foo = {bar})\n")
            self.assertEqual(host.prepare_bibtex_string_delimiters(Path(directory)), [path])
            self.assertEqual(path.read_text(), "@String{foo = {bar}}\n")

if __name__ == "__main__": unittest.main()
