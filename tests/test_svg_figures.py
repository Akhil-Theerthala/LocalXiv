import unittest

from papers import html_figures


class SVGProfileTests(unittest.TestCase):
    def valid_svg(self, body='', attributes=''):
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 912 600" '
            + attributes + '>' + body + '</svg>'
        )

    def test_namespaced_svg_normalizes_without_changing_visible_text(self):
        source = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 912 200">'
            '<text id="dimension" x="20" y="50" font-size="24">512</text>'
            '</svg>'
        )

        normalized = html_figures.normalize_svg(source)

        self.assertEqual([('#dimension', '512')], html_figures.svg_visible_text(normalized))
        self.assertEqual(normalized, html_figures.normalize_svg(normalized))
        self.assertIn('xmlns="http://www.w3.org/2000/svg"', normalized)

    def test_profile_accepts_paths_tspans_transforms_and_local_markers(self):
        body = (
            '<defs><marker id="arrow" viewBox="0 0 10 10" markerWidth="8" '
            'markerHeight="8" refX="9" refY="5" orient="auto">'
            '<path d="M 0 0 L 10 5 L 0 10 Z" fill="#243b32"/></marker></defs>'
            '<g transform="translate(20 10) scale(1.2)">'
            '<path id="curve" d="M 20 100 C 160 20 260 180 400 100" fill="none" '
            'stroke="#243b32" stroke-width="3" marker-end="url(#arrow)"/>'
            '<text id="label" x="20" y="70" font-size="28">Value '
            '<tspan font-weight="700">mixing</tspan> <tspan x="20" dy="32">keeps 0.82 probability.</tspan>'
            '</text></g>'
        )

        normalized = html_figures.normalize_svg(self.valid_svg(body))

        self.assertIn('marker-end="url(#arrow)"', normalized)
        self.assertEqual(
            [('#label', 'Value mixing keeps 0.82 probability.')],
            html_figures.svg_visible_text(normalized),
        )

    def test_namespace_free_and_namespaced_sources_have_one_canonical_form(self):
        namespaced = self.valid_svg('<circle cx="20" cy="20" r="10" fill="#dce8cf"/>')
        namespace_free = namespaced.replace(' xmlns="http://www.w3.org/2000/svg"', '')
        self.assertEqual(
            html_figures.normalize_svg(namespaced),
            html_figures.normalize_svg(namespace_free),
        )

    def test_local_sans_serif_families_are_accepted_and_canonicalised(self):
        source = self.valid_svg(
            '<text id="label" x="20" y="50" font-size="24" '
            'font-family="helvetica, arial, sans-serif">Readable</text>')
        normalized = html_figures.normalize_svg(source)
        self.assertIn('font-family="Arial, sans-serif"', normalized)
        self.assertEqual([('#label', 'Readable')], html_figures.svg_visible_text(normalized))
        self.assertEqual(normalized, html_figures.normalize_svg(normalized))

    def test_non_local_font_families_are_rejected(self):
        for family in ('Roboto', 'Times New Roman', 'Arial Black', '"Some Web Font"'):
            with self.subTest(family=family):
                source = self.valid_svg(
                    '<text x="20" y="50" font-size="24" font-family=' + repr(family) + '>Label</text>')
                with self.assertRaises(html_figures.SVGValidationError):
                    html_figures.normalize_svg(source)

    def test_comments_titles_descriptions_and_marker_text_are_not_visible_labels(self):
        source = self.valid_svg(
            '<!-- ignore these words -->'
            '<title>Hidden document title</title><desc>Long hidden description</desc>'
            '<defs><marker id="arrow"><text x="0" y="20">Marker words</text></marker></defs>'
            '<g opacity="0.0"><text x="20" y="30">Transparent group</text></g>'
            '<text x="20" y="35" fill-opacity="0">Transparent fill</text>'
            '<text x="20" y="50">Shown <tspan>once</tspan></text>'
        )
        self.assertEqual(
            [('/svg/text[2]', 'Shown once')],
            html_figures.svg_visible_text(source),
        )

    def test_adjacent_tspans_do_not_invent_whitespace(self):
        source = self.valid_svg(
            '<text id="inline" x="20" y="40">uncertain<tspan>ty</tspan></text>'
            '<text id="wrapped" x="20" y="80">first <tspan x="20" dy="28">second</tspan></text>'
        )
        self.assertEqual(
            [('#inline', 'uncertainty'), ('#wrapped', 'first second')],
            html_figures.svg_visible_text(source),
        )

    def test_rejects_unsafe_or_unsupported_markup_with_structured_issues(self):
        cases = {
            'active content': self.valid_svg('<script>alert(1)</script>'),
            'event': self.valid_svg('<rect x="0" y="0" width="10" height="10" onclick="x()"/>'),
            'external resource': self.valid_svg('<path d="M 0 0 L 10 10" marker-end="url(https://example.com/a)"/>'),
            'unknown namespace': '<svg xmlns="urn:not-svg" viewBox="0 0 912 600"/>',
            'mixed namespace': self.valid_svg('<x:rect xmlns:x="urn:not-svg" x="0" y="0" width="10" height="10"/>'),
            'wrong attribute': self.valid_svg('<circle x="10" cy="20" r="4"/>'),
            'style': self.valid_svg('<text x="10" y="20" style="font-size:24px">No</text>'),
        }
        for name, source in cases.items():
            with self.subTest(name=name), self.assertRaises(html_figures.SVGValidationError) as caught:
                html_figures.normalize_svg(source)
            self.assertTrue(caught.exception.issues)
            self.assertIn(caught.exception.issues[0]['code'], {'svg_parse', 'unsupported_svg'})

    def test_rejects_bad_ids_and_marker_references(self):
        cases = {
            'duplicate': '<rect id="same"/><circle id="same"/>',
            'missing': '<path d="M 0 0 L 10 10" marker-end="url(#missing)"/>',
            'wrong type': '<defs><path id="arrow" d="M 0 0 L 1 1"/></defs><path d="M 0 0 L 10 10" marker-end="url(#arrow)"/>',
        }
        for name, body in cases.items():
            with self.subTest(name=name), self.assertRaises(html_figures.SVGValidationError) as caught:
                html_figures.normalize_svg(self.valid_svg(body))
            self.assertIn('svg_reference', {issue['code'] for issue in caught.exception.issues})

    def test_rejects_malformed_numeric_geometry_paths_and_transforms(self):
        cases = {
            'nan': '<circle cx="NaN" cy="20" r="4"/>',
            'points': '<polygon points="0,0 10"/>',
            'path arity': '<path d="M 0 0 C 1 2 3"/>',
            'path suffix': '<path d="M 0 0 L 10 10 garbage"/>',
            'path initial': '<path d="L 0 0"/>',
            'arc flag': '<path d="M 0 0 A 10 10 0 2 0 20 20"/>',
            'transform name': '<g transform="perspective(1)"><circle cx="2" cy="2" r="1"/></g>',
            'transform arity': '<g transform="matrix(1 0 0 1 3)"><circle cx="2" cy="2" r="1"/></g>',
        }
        for name, body in cases.items():
            with self.subTest(name=name), self.assertRaises(html_figures.SVGValidationError):
                html_figures.normalize_svg(self.valid_svg(body))

    def test_rejects_malformed_xml_and_declared_entities(self):
        for source in (
            '<svg viewBox="0 0 912 600"><text></svg>',
            '<!DOCTYPE svg><svg viewBox="0 0 912 600"/>',
            '<?xml version="1.0"?><svg viewBox="0 0 912 600"/>',
        ):
            with self.subTest(source=source), self.assertRaises(html_figures.SVGValidationError) as caught:
                html_figures.normalize_svg(source)
            self.assertEqual('svg_parse', caught.exception.issues[0]['code'])

    def test_enforces_source_attribute_and_element_limits(self):
        oversized_source = self.valid_svg('<desc>' + ('x' * 60000) + '</desc>')
        oversized_attribute = self.valid_svg('<text aria-label="' + ('x' * 12001) + '">x</text>')
        too_many_elements = self.valid_svg('<g/>' * 500)
        for source in (oversized_source, oversized_attribute, too_many_elements):
            with self.subTest(size=len(source)), self.assertRaises(html_figures.SVGValidationError):
                html_figures.normalize_svg(source)


if __name__ == '__main__':
    unittest.main()
