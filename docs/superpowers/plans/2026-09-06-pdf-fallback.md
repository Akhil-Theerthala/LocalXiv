# PDF fallback implementation plan

Goal: When source conversion cannot produce a validated EPUB, import the retained PDF for reading and sending, and use its extracted text for overviews.

The requested flow is approved in the task. Keep conversion diagnostics and original files. A persistent notice explains the PDF fallback. Paper export and delivery select the original PDF; overview export remains EPUB. Combined export is unavailable for PDF papers. Existing successful EPUB imports must survive a failed retry.

- [x] Add PDFKit extraction in the isolated conversion worker, with page-linked passages and PDF provenance. No new dependency or provider-specific PDF upload.
- [x] Recover conversion and source-download failures through the PDF worker. Keep imports failed only when no usable PDF is available. Preserve cancellation and successful prior imports.
- [x] Display the PDF in the reader, show the notice, and label download/send controls with the selected format. Keep HTML readers sandboxed.
- [x] Test fallback imports, unavailable PDFs, source failures, overview evidence, download/send selection, and ordinary EPUB behavior. Mock Mail and AI delivery.
- [x] Verify the real paper in the macOS sandbox and inspect the rendered PDF reader at wide and narrow widths. Install the tested runtime changes.
