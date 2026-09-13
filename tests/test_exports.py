"""Paper representation selection with real local records and files."""
import os
import tempfile
import unittest
from pathlib import Path

from papers.library import Library
from papers.overview_workflow import FIGURE_ASSET_KEYS, GENERATION_KEYS


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

    def test_generation_and_figure_asset_keys_stay_exportable(self):
        """Record the saved-generation contract the rebuilt Overview must keep producing."""
        from papers.exports import artifact, figure_source
        self.assertEqual(('text', 'explanation', 'plan', 'cited_text', 'figures', 'evidence', 'provenance'),
                         GENERATION_KEYS)
        self.assertEqual(('html', 'svg', 'png', 'pdf', 'svg_source'), FIGURE_ASSET_KEYS)
        assets = self.directory / 'reader' / 'overview-figures' / 'run'
        assets.mkdir(parents=True)
        (assets / 'fig1.png').write_bytes(b'\x89PNG\r\n\x1a\nfixture')
        (assets / 'fig1.source.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
        generation = {'text': '{{figure:fig1}}', 'explanation': {}, 'plan': {}, 'cited_text': '',
                      'figures': [{'id': 'fig1', 'caption': 'A caption',
                                   'png': 'reader/overview-figures/run/fig1.png',
                                   'svg_source': 'reader/overview-figures/run/fig1.source.svg'}],
                      'evidence': [], 'provenance': {'reviews': [{'approved': True}]}}
        self.assertEqual(set(GENERATION_KEYS), set(generation))
        self.library.save_generation('one', 'bento', generation)
        self.assertEqual((assets / 'fig1.png').resolve(), artifact(self.library, self.paper, 'bento', 'png'))
        self.assertEqual((assets / 'fig1.source.svg').resolve(),
                         figure_source(self.directory, generation['figures'][0], 'svg', field='svg_source'))

    def test_svg_source_uses_the_explicit_owned_source_field(self):
        from papers.exports import figure_source
        assets=self.directory/'reader'/'overview-figures'
        assets.mkdir(parents=True)
        source=assets/'figure.source.svg'
        source.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
        outside=self.directory/'outside.source.svg'
        outside.write_text('private')
        (assets/'linked.source.svg').symlink_to(outside)
        for relative,valid in (
                ('reader/overview-figures/figure.source.svg',True),
                ('reader/overview-figures/figure.svg',False),
                ('../../outside.source.svg',False),
                ('reader/overview-figures/linked.source.svg',False)):
            with self.subTest(relative=relative):
                figure={'svg_source':relative}
                if valid:
                    self.assertEqual(source.resolve(),figure_source(self.directory,figure,'svg',field='svg_source'))
                else:
                    with self.assertRaises(ValueError):
                        figure_source(self.directory,figure,'svg',field='svg_source')


def native_renderer_available():
    from papers import html_figures
    return bool(os.environ.get('LOCALXIV_HTML_RENDERER')
                or (Path(html_figures.__file__).with_name('html-snapshot')).is_file())


@unittest.skipUnless(native_renderer_available(), 'Build papers/html-snapshot for native Overview exports')
class FreeSizedOverviewExportTests(unittest.TestCase):
    """A free-sized overview keeps every existing export route, at its own dimensions."""

    def setUp(self):
        from papers import html_figures
        from papers.arrangement import arrange, panel_record
        from papers.html_figures import compose_figure, normalize_panel_svg, render
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.library = Library(Path(self.temporary.name))
        self.directory = self.library.root / 'papers' / 'one'
        self.directory.mkdir(parents=True)
        document = {'arxiv_id': 'one', 'title': 'Paper', 'authors': 'A', 'format': 'epub',
                    'source_digest': 'digest', 'passages': [{'id': 'p00001', 'section': 'Body',
                                                             'text': 'Retained text.'}]}
        self.paper = self.library.save_paper('one', document, self.directory)
        sources, records = {}, []
        for index in range(1, 4):
            identifier = 'p%d' % index
            source = normalize_panel_svg(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 420" font-size="18">'
                '<rect x="20" y="20" width="860" height="200" rx="10" fill="#dce8cf"/>'
                f'<text x="40" y="130">Panel {index} of a free-sized overview</text>'
                '<path d="M 20 300 C 240 240 660 360 880 280" fill="none" stroke="#2f6f5e" stroke-width="2"/>'
                '</svg>')
            sources[identifier] = source
            records.append(panel_record(identifier, source))
        layout = arrange(records)
        composed = compose_figure(sources, layout)
        figure = {'id': 'fig1', 'title': 'Overview', 'paper_connection': 'Fixture.',
                  'caption': 'Fixture caption.', 'illustrative': False, 'passages': ['p00001'],
                  'source_svg': composed}
        assets = render(self.directory, figure, 'Paper', mode='overview')
        self.checks = assets.pop('checks')
        figure.update(assets, checks=self.checks, dimensions=self.checks['canvas'],
                      panels=[{'id': placement['id'], 'title': placement['id'],
                               'x': placement['x'], 'y': placement['y'],
                               'width': placement['width'], 'height': placement['height']}
                              for placement in layout['placements']])
        self.generation = {'text': '{{figure:fig1}}', 'figures': [figure],
                           'provenance': {'model': 'fixture', 'created_at': 'now'}}
        self.library.save_generation('one', 'bento', self.generation)

    def test_png_and_pdf_exports_carry_the_free_sized_dimensions(self):
        import struct
        from papers.exports import artifact
        png = artifact(self.library, self.paper, 'bento', 'png')
        width, height = struct.unpack('>II', png.read_bytes()[16:24])
        self.assertGreater(width, 960)
        self.assertGreater(self.checks['canvas']['height'], 0)
        pdf = artifact(self.library, self.paper, 'bento', 'pdf')
        self.assertTrue(pdf.read_bytes().startswith(b'%PDF-'))
        self.assertEqual(pdf, self.directory / 'overview.pdf')

    def test_editable_and_compatibility_svg_agree_with_the_measured_canvas(self):
        import xml.etree.ElementTree as ET
        from papers.exports import figure_source
        figure = self.generation['figures'][0]
        editable = figure_source(self.directory, figure, 'svg', field='svg_source')
        root = ET.parse(editable).getroot()
        values = [float(value) for value in root.get('viewBox').split()]
        self.assertEqual(self.checks['canvas']['width'], values[2])
        self.assertEqual(self.checks['canvas']['height'], values[3])
        self.assertIn('<text', editable.read_text())
        compatibility = figure_source(self.directory, figure, 'svg')
        self.assertEqual(self.checks['canvas']['width'], float(ET.parse(compatibility).getroot().get('width')))

    def test_the_overview_epub_packages_the_free_sized_image(self):
        import zipfile
        from papers.document import export_overview
        document = self.library.get_paper('one')
        epub = export_overview(self.directory, document, self.generation, visual=True)
        self.assertTrue(epub.is_file())
        with zipfile.ZipFile(epub) as archive:
            names = archive.namelist()
            self.assertTrue(any(name.endswith('fig1.svg') for name in names), names)
            image = next(archive.read(name) for name in names if name.endswith('fig1.svg'))
            self.assertIn(b'<svg', image)
            self.assertGreater(len(image), 1000)
