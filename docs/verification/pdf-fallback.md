# PDF fallback verification

Verified on macOS, 2026-09-06.

When EPUB conversion fails, the application runs PDFKit extraction in a separate invocation of its existing macOS conversion sandbox. It keeps the original PDF and converter report, saves page-linked evidence, and completes the import as `pdf_fallback`. Unavailable source archives use the same path. An unreadable or unavailable PDF remains a failed import. A readable PDF without extracted text remains available for reading and sending, with an overview explanation.

The reader displays the original PDF. A persistent notice identifies the format and explains that paper delivery will use the PDF. PDF response headers and the PDF iframe permit the browser's native viewer; converted HTML retains its sandbox. The download button, send button, notification link, and Mail-error text name the actual format. Overview export remains EPUB. Combined export is rejected for PDF papers.

Checks performed:

- Application, AI, PDF, overview, library, handoff, and converter suite: 60 tests, 59 passed and one skipped. The final additional PDF Mail-error test also passed in the five-test PDF suite.
- `node tests/test_app_ui.js` passed, including PDF/EPUB switching, notice visibility, overview availability, delivery labels, and preservation of reading position on refresh.
- A real two-page PDF passed PDFKit extraction inside the macOS sandbox, retaining text and page references. Invalid PDFs were rejected. An empty-text result retained reading and delivery with an actionable overview error.
- The overview pipeline accepted extracted PDF evidence and recorded PDF provenance with deterministic provider responses. No live AI or Mail delivery was performed.
- The installed runtime was tested with deliberately unconvertible source data and the retained PDF for arXiv 2511.07694v1. Both source attempts failed, then the PDF imported all 11 pages. Delivery selected the byte-identical `original.pdf`.
- The PDF, fallback notice, and delivery dialog were inspected in the browser at desktop and narrow widths. Selecting the overview restored EPUB export controls.
- Nine runtime files were installed with backups under `.verification/runtime-before-pdf-fallback`. The idle local service was restarted; its health check and the reopened native library passed. Existing library papers were retained.

PDFKit text extraction does not establish the accuracy of mathematical notation or table reading order. No OCR or live-provider overview quality claim is made. No native Kindle device check was performed.
