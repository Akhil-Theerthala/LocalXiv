"""Retain the original PDF and extract page evidence with macOS PDFKit."""
import hashlib
import json
import subprocess
from pathlib import Path

PDF_NOTICE = ('We downloaded the PDF instead of an EPUB because the paper’s template '
              'could not be parsed for EPUB conversion. Sending this paper will send the PDF.')

_EXTRACT = '''ObjC.import("PDFKit");
function run(args) {
    var doc = $.PDFDocument.alloc.initWithURL($.NSURL.fileURLWithPath(args[0]));
    if (doc.isNil() || doc.isLocked || !doc.pageCount) throw Error("The PDF could not be opened.");
    var pages = [];
    for (var i = 0; i < doc.pageCount; i++) {
        var value = doc.pageAtIndex(i).string;
        pages.push(value.isNil() ? "" : ObjC.unwrap(value));
    }
    return JSON.stringify(pages);
}'''


def build_pdf_document(directory: Path, metadata: dict) -> dict:
    pdf = directory / 'original.pdf'
    if not pdf.is_file() or not pdf.read_bytes().startswith(b'%PDF-'):
        raise ValueError('No downloaded PDF is available for this paper.')
    result = subprocess.run(['/usr/bin/osascript', '-l', 'JavaScript', '-e', _EXTRACT, str(pdf.resolve())],
                            capture_output=True, text=True, timeout=90)
    if result.returncode:
        raise ValueError('The downloaded PDF could not be opened: ' + result.stderr[-500:])
    pages = json.loads(result.stdout)
    if not isinstance(pages, list) or not pages or any(not isinstance(p, str) for p in pages):
        raise ValueError('The PDF reader did not return valid pages.')
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    chapters, passages = [], []
    for number, text in enumerate(pages, 1):
        href, title = f'original.pdf#page={number}', f'PDF page {number}'
        chapters.append({'title': title, 'path': href})
        if text.strip():
            passages.append({'id': f'p{number:05d}', 'section': title, 'text': text.strip(), 'href': href})
    report_path = directory / 'conversion-report.json'
    report = json.loads(report_path.read_text()) if report_path.is_file() else {}
    report.update(status='pdf_fallback', warning=report.get('warning', PDF_NOTICE), pages=len(pages),
                  text_pages=len(passages), checks=['PDFKit opened original PDF', 'page-linked PDF text'])
    if not passages:
        report['text_warning'] = 'This PDF has no extractable text. You can read and send it, but an overview needs selectable text.'
    document = dict(metadata, source_digest=metadata.get('source_digest') or digest, pdf_digest=digest,
                    format='pdf', status='pdf_fallback', converter='pdfkit', chapters=chapters,
                    passages=passages, report=report, artifacts={'original_pdf': 'original.pdf'})
    (directory / 'reader').mkdir(exist_ok=True)
    (directory / 'document.json').write_text(json.dumps(document), encoding='utf-8')
    report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    return document
