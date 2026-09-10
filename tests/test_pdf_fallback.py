"""PDF fallback keeps real page evidence and sends the retained original."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch


def write_pdf(path):
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>',
               b'<< /Type /Pages /Kids [3 0 R 5 0 R] /Count 2 >>']
    for index, text in enumerate(('The measured accuracy is 91 percent.', 'The study used 120 examples.')):
        stream = f'BT /F1 12 Tf 40 740 Td ({text}) Tj ET'.encode()
        objects.extend([
            f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 7 0 R >> >> /Contents {4 + index * 2} 0 R >>'.encode(),
            f'<< /Length {len(stream)} >>\nstream\n'.encode() + stream + b'\nendstream'])
    objects.append(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>')
    output = b'%PDF-1.4\n'
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(output))
        output += f'{number} 0 obj\n'.encode() + obj + b'\nendobj\n'
    xref = len(output)
    output += f'xref\n0 {len(offsets)}\n0000000000 65535 f \n'.encode()
    output += b''.join(f'{offset:010} 00000 n \n'.encode() for offset in offsets[1:])
    output += f'trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode()
    path.write_bytes(output)


@unittest.skipUnless(sys.platform == 'darwin', 'PDFKit requires macOS')
class PDFFallbackTests(unittest.TestCase):
    def test_real_pdf_retains_page_evidence_and_original_bytes(self):
        from papers.pdf import build_pdf_document
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            pdf = directory / 'original.pdf'
            write_pdf(pdf)
            before = pdf.read_bytes()
            document = build_pdf_document(directory, {'arxiv_id': '2501.00001v1', 'title': 'PDF fixture'})
            self.assertEqual(document['format'], 'pdf')
            self.assertEqual(len(document['chapters']), 2)
            self.assertEqual([p['href'] for p in document['passages']], ['original.pdf#page=1', 'original.pdf#page=2'])
            self.assertIn('91 percent', document['passages'][0]['text'])
            self.assertIn('120 examples', document['passages'][1]['text'])
            self.assertEqual(pdf.read_bytes(), before)
            self.assertTrue(document['pdf_digest'])
            self.assertFalse((directory / 'paper.epub').exists())

    def test_overview_pipeline_uses_pdf_pages_and_records_format(self):
        from papers.pdf import build_pdf_document
        from papers.ai import Provider, generate_overview
        from tests.test_agent_overviews import CANDIDATE, scripted_provider, render_fixture
        import copy
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            write_pdf(directory / 'original.pdf')
            document = build_pdf_document(directory, {'arxiv_id': '2501.00001v1', 'title': 'PDF fixture'})
            document['directory'] = str(directory)
            provider = Provider({'endpoint': 'https://example.org/v1', 'model': 'test'}, '')
            candidate=copy.deepcopy(CANDIDATE)
            with patch.object(provider, 'complete', side_effect=scripted_provider(candidate)) as complete, patch('papers.html_figures.render', side_effect=render_fixture):
                overview = generate_overview(provider, document, lambda _: None)
            requests = [call.args[0][-1]['content'] for call in complete.call_args_list]
            self.assertIn('91 percent', requests[0])
            self.assertIn('120 examples', requests[0])
            self.assertEqual(overview['provenance']['evidence_format'], 'pdf')
            self.assertEqual(overview['provenance']['pdf_digest'], document['pdf_digest'])
            self.assertEqual(overview['provenance']['passages'], ['p00001', 'p00002'])
            self.assertTrue(overview['text'])

    def test_pdf_without_text_remains_readable_with_an_overview_explanation(self):
        from papers.pdf import build_pdf_document
        from papers.ai import ProviderError, generate_overview
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            write_pdf(directory / 'original.pdf')
            with patch('papers.pdf.subprocess.run') as run:
                run.return_value.returncode = 0
                run.return_value.stdout = json.dumps(['', ''])
                document = build_pdf_document(directory, {})
            self.assertEqual(len(document['chapters']), 2)
            self.assertEqual(document['passages'], [])
            with self.assertRaisesRegex(ProviderError, 'no extractable text'):
                generate_overview(Mock(settings={}), document, lambda _: None)

    def test_invalid_pdf_is_not_a_successful_import(self):
        from papers.pdf import build_pdf_document
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / 'original.pdf').write_bytes(b'%PDF-1.4 not a document')
            with self.assertRaises(ValueError):
                build_pdf_document(directory, {})

    def test_mail_failure_names_the_pdf_without_sending(self):
        from native.host import ConversionError, send_with_mail
        with patch('native.host.subprocess.run') as run:
            run.return_value.returncode = 1
            run.return_value.stderr = 'Mail unavailable'
            with self.assertRaisesRegex(ConversionError, 'The PDF was saved'):
                send_with_mail(Path('original.pdf'), 'reader@kindle.com', 'Fixture')
