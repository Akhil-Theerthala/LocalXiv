"""Paper representation selection with real local records and files."""
import tempfile
import unittest
from pathlib import Path

from papers.library import Library


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.library = Library(Path(self.temporary.name))
        self.directory = self.library.root / 'papers' / 'one'
        self.directory.mkdir(parents=True)
        self.paper = self.library.save_paper('one', {'arxiv_id': 'one', 'title': 'Paper', 'authors': 'A'}, self.directory)

    def test_paper_profiles_choose_retained_files_without_generations(self):
        from papers.exports import artifact
        for filename, content in [('paper.epub', b'Kindle EPUB'), ('semantic.epub', b'Semantic EPUB'), ('original.pdf', b'%PDF-1.4 original')]:
            (self.directory / filename).write_bytes(content)
        for profile, expected in [('kindle', 'paper.epub'), ('semantic', 'semantic.epub'), ('pdf', 'original.pdf')]:
            self.assertEqual(self.directory / expected, artifact(self.library, self.paper, 'paper', profile))
        for profile in ('kindle', 'semantic', 'pdf'):
            self.assertEqual(self.directory / 'original.pdf', artifact(self.library, dict(self.paper, format='pdf'), 'paper', profile))

    def test_missing_files_and_invalid_combinations_fail_before_export(self):
        from papers.exports import artifact
        for kind, profile in [('paper', 'kindle'), ('paper', 'semantic'), ('paper', 'pdf'), ('paper', 'png'),
                              ('overview', 'png'), ('both', 'pdf'), ('unknown', 'kindle'), ('paper', 'unknown')]:
            with self.subTest(kind=kind, profile=profile), self.assertRaises(ValueError):
                artifact(self.library, self.paper, kind, profile)
        (self.directory / 'original.pdf').write_bytes(b'not a PDF')
        for profile in ('kindle', 'semantic', 'pdf'):
            with self.subTest(profile=profile), self.assertRaises(ValueError):
                artifact(self.library, dict(self.paper, format='pdf'), 'paper', profile)
        with self.assertRaisesRegex(ValueError, 'separately'):
            artifact(self.library, dict(self.paper, format='pdf'), 'both', 'kindle')

    def test_generated_exports_require_the_matching_generation(self):
        from papers.exports import artifact
        self.library.save_generation('one', 'overview', {'text': 'A blog'})
        for profile in ('kindle', 'semantic', 'pdf', 'png'):
            with self.subTest(profile=profile), self.assertRaises(ValueError):
                artifact(self.library, self.paper, 'bento', profile)
        self.library.save_generation('one', 'bento', {'text': 'No figures', 'figures': []})
        for profile in ('pdf', 'png'):
            with self.subTest(profile=profile), self.assertRaises(ValueError):
                artifact(self.library, self.paper, 'bento', profile)

    def test_png_uses_only_an_existing_owned_figure(self):
        from papers.exports import artifact
        assets = self.directory / 'reader' / 'overview-figures'
        assets.mkdir(parents=True)
        image = assets / 'figure.png'
        image.write_bytes(b'PNG fixture')
        outside = self.library.root / 'private.png'
        outside.write_bytes(b'private fixture')
        (assets / 'link.png').symlink_to(outside)
        for source, valid in [('reader/overview-figures/figure.png', True),
                              ('reader/overview-figures/missing.png', False),
                              ('../../private.png', False),
                              ('reader/overview-figures/link.png', False)]:
            self.library.save_generation('one', 'bento', {'figures': [{'png': source}]})
            with self.subTest(source=source):
                if valid:
                    self.assertEqual(image.resolve(), artifact(self.library, self.paper, 'bento', 'png'))
                else:
                    with self.assertRaises(ValueError):
                        artifact(self.library, self.paper, 'bento', 'png')
        self.assertEqual(b'private fixture', outside.read_bytes())
