"""Exercise import recovery without network requests or external converters."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from papers import convert


class ConversionRecoveryTests(unittest.TestCase):
    def test_stops_at_first_success_and_retains_ordered_attempts(self):
        for winner, expected in [
            ('pandoc', ['pandoc']),
            ('arxiv-html', ['pandoc', 'arxiv-html']),
            ('latexml', ['pandoc', 'arxiv-html', 'latexml']),
            ('pdf', ['pandoc', 'arxiv-html', 'latexml', 'pdf']),
        ]:
            with self.subTest(winner=winner), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                routes = []

                def attempt(directory, metadata, progress, *, source_engine=None, html_only=False, pdf_only=False):
                    route = 'pdf' if pdf_only else 'arxiv-html' if html_only else source_engine
                    routes.append(route)
                    report_path = directory / 'conversion-report.json'
                    report = json.loads(report_path.read_text()) if report_path.exists() else {}
                    report.setdefault('attempts', []).append({'engine': route, 'status': 'converted' if route == winner else 'failed'})
                    report_path.write_text(json.dumps(report))
                    progress('Attempting ' + route)
                    if route != winner:
                        raise ValueError(route + ' failed')
                    document = dict(metadata, converter=route, format='pdf' if pdf_only else 'epub', report=report)
                    (directory / 'document.json').write_text(json.dumps(document))
                    return document

                with patch.object(convert, 'convert_paper', side_effect=attempt), patch('papers.arxiv_html.retrieve'):
                    result = convert.convert_import(root, {'arxiv_id': 'one'}, lambda _: None)
                self.assertEqual(expected, routes)
                self.assertEqual(winner, result['converter'])
                self.assertEqual(expected, [a['engine'] for a in result['report']['attempts']])
                self.assertEqual(result, json.loads((root / 'document.json').read_text()))
                if winner == 'pdf':
                    self.assertEqual('latexml failed', result['report']['epub_error'])

    def test_unavailable_source_skips_source_engines_and_records_html_retrieval_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            routes = []

            def attempt(directory, metadata, progress, *, pdf_only=False, **kwargs):
                self.assertTrue(pdf_only)
                routes.append('pdf')
                report = json.loads((directory / 'conversion-report.json').read_text())
                return dict(metadata, format='pdf', report=report)

            with patch.object(convert, 'convert_paper', side_effect=attempt), patch('papers.arxiv_html.retrieve', side_effect=ValueError('HTML unavailable')):
                result = convert.convert_import(root, {'arxiv_id': 'one'}, lambda _: None,
                                                source_error=ValueError('Source unavailable'))
            self.assertEqual(['pdf'], routes)
            self.assertEqual('Source unavailable', result['report']['epub_error'])
            self.assertIn('source files were unavailable', result['report']['warning'])
            self.assertEqual([{'engine': 'arxiv-html', 'status': 'failed', 'error': 'HTML unavailable'}], result['report']['attempts'])

    def test_epub_only_evaluation_stops_before_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            routes = []
            def attempt(directory, metadata, progress, *, source_engine=None, html_only=False, pdf_only=False):
                routes.append('pdf' if pdf_only else 'arxiv-html' if html_only else source_engine)
                raise ValueError('Conversion failed')
            with patch.object(convert, 'convert_paper', side_effect=attempt), patch('papers.arxiv_html.retrieve'):
                with self.assertRaisesRegex(ValueError, 'EPUB unavailable'):
                    convert.convert_import(Path(tmp), {}, lambda _: None, epub_only=True)
            self.assertEqual(['pandoc', 'arxiv-html', 'latexml'], routes)

    def test_cancellation_never_starts_the_next_route(self):
        for cancelled_at in ('pandoc', 'retrieve', 'arxiv-html', 'latexml', 'pdf'):
            with self.subTest(cancelled_at=cancelled_at), tempfile.TemporaryDirectory() as tmp:
                visited = []

                def visit(route):
                    visited.append(route)
                    if route == cancelled_at:
                        raise convert.Cancelled()
                    if route != 'retrieve':
                        raise ValueError(route + ' failed')

                def attempt(directory, metadata, progress, *, source_engine=None, html_only=False, pdf_only=False):
                    visit('pdf' if pdf_only else 'arxiv-html' if html_only else source_engine)

                with patch.object(convert, 'convert_paper', side_effect=attempt), patch('papers.arxiv_html.retrieve', side_effect=lambda *args: visit('retrieve')):
                    with self.assertRaises(convert.Cancelled):
                        convert.convert_import(Path(tmp), {'arxiv_id': 'one'}, lambda _: None)
                self.assertEqual(cancelled_at, visited[-1])
                self.assertEqual(['pandoc', 'retrieve', 'arxiv-html', 'latexml', 'pdf'][:len(visited)], visited)

    def test_final_failure_retains_original_files_and_recovery_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'source').write_bytes(b'original source')
            (root / 'original.pdf').write_bytes(b'%PDF-1.4 retained')
            with patch.object(convert, 'convert_paper', side_effect=ValueError('Converter failed')), patch('papers.arxiv_html.retrieve', side_effect=ValueError('HTML unavailable')):
                with self.assertRaisesRegex(ValueError, 'PDF fallback is also unavailable'):
                    convert.convert_import(root, {'arxiv_id': 'one'}, lambda _: None)
            self.assertEqual(b'original source', (root / 'source').read_bytes())
            self.assertEqual(b'%PDF-1.4 retained', (root / 'original.pdf').read_bytes())
            report = json.loads((root / 'conversion-report.json').read_text())
            self.assertEqual('HTML unavailable', report['html_recovery_error'])
            self.assertEqual('Converter failed', report['epub_error'])
