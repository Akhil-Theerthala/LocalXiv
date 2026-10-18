# Chat spikes P3 and P4: results

Date: 2026-10-18. Branch `claude/modest-almeida-e32d2f`, from `main` at `b41b7cf`. This is a report of two throwaway spikes. No app or `papers/` code changed.

Scope: items P3 (Chat answers) and P4 (WebKit) of Release 1 in `docs/highlights-notes-chat-plan-2026-10-18.md`, section 7. The plan file is in the main checkout and is not committed. Criteria 4 to 6 are the plan's acceptance criteria in its section 4.

The scripts, the step files, the raw runs, and the evidence are in `spikes/chat-2026-10-18/`. Section 6 tells how to run them again.

## 1. Summary

P3_SUMMARY

| P4 check | macOS 26 WKWebView | Browser pane (Chromium 152, a control) | Fallback |
| --- | --- | --- | --- |
| 1. A CSS Custom Highlight paints over inline MathML | **Fail.** Text paints. Each `<math>` element stays unpainted. | Partial. The tokens paint, with gaps between them. | Paint text with the Highlight API, and give each covered `<math>` element a background. It paints in WKWebView. |
| 2. The page reads a selection in a PDF Paper's frame | **Fail.** ⌘A selects the PDF page, and the page reads an empty selection. | Not testable. The pane shows no PDF viewer. | Keep plan 5.8: no Highlights and no Ask on PDF-only Papers. Chat reads the page text. |
| 3. A stream survives 120 s with a 70 s silent gap | **Pass.** 50 of 50 lines, the end at 120.1 s. | **Pass.** 50 of 50 lines, the end at 120.1 s. | Not needed. Section 5.3 gives the disconnect rule. |
| 4. How ⌘F treats text in a panel beside the Paper frame | ⌘F finds panel text and frame text. No attribute or style hides panel text. | Not tested. The browser's own find applies there. | Rule: Find covers the Paper and the panel. To keep panel text out, the panel must leave the page's document. |

## 2. P3: Chat answers

P3_BODY

## 5. P4: WebKit

### How the checks ran

- **WKWebView.** `spikes/chat-2026-10-18/native_spike.py` runs `tools/native_shot.py` and adds one throwaway route, `/spike/stream`, to the scratch copy of `app/server.py` that `native_shot.py` installs. The route is in `spike_routes.py`. The step files are `p4-steps.json`, `p4-steps-fallback.json`, and `p4-steps-fallback2.json`. The app is the macOS 26 test build, user agent `AppleWebKit/605.1.15`.
- **Browser pane.** `spike_server.py` runs the app server with the same route on port 8799. The pane is Chromium 152 in Electron, not WebKit, so its results are a control only. This spike did not use Safari.
- **Library.** `make_library.py` makes a scratch library with three Papers from the reader's library: the Attention Paper (Pandoc, 138 MathML elements), 2610.02887v1 (arXiv HTML), and 2609.37725v1 (a PDF Paper). The reader's library stays read only.

### 5.1 Check 1: a Highlight over MathML

Method: on passage `p00045` of the Attention Paper, which holds three inline formulas, the page makes a `Range` over the whole passage. It registers the range with the frame's `CSS.highlights` and adds a `::highlight()` rule to `#app-reading-style` (`app/static/reader.js:333-334`).

Result in WKWebView: **fail.** The Highlight API exists (`typeof Highlight` is `function`) and paints every text run. It paints nothing inside a `<math>` element: the three formulas stay on a white ground (`evidence/p4-1-wk-highlight.png`). A range that starts inside a formula token also paints nothing inside the formula.

Result in Chromium: partial. The math tokens paint, but the spaces between tokens do not (`evidence/p4-1-highlight-mathml-chromium-zoom.png`). This is the gap that alphaXiv issue #176 reports.

Fallback, tested in WKWebView: keep the Highlight API for text, and give each `<math>` element inside the Highlight a background colour through a class in `#app-reading-style`. The formulas then paint (`evidence/p4-1-fallback-math.png`). Thin light lines stay where the band of a formula is shorter than the band of the text line. A `<span>` wrapper with a background around each `<math>` element also paints, with the same thin lines (`evidence/p4-1-fallback-span.png`). The class is the smaller change, because it adds no element. Plan 5.4 already snaps a selection edge inside a formula to the whole formula, so a whole-formula background agrees with the anchor rule. The class changes no text, and the Reference preview copy keeps no classes (`app/static/reader.js:588-600`).

### 5.2 Check 2: a selection in a PDF Paper's frame

Method: the reader opens 2609.37725v1. For a PDF Paper the frame has no `sandbox` attribute (`app/static/reader.js:267`), and the server sends the PDF with `default-src 'none'` (`app/server.py:301-304`). The step clicks inside the PDF, presses ⌘A, and reads `getSelection()` in the page and in the frame.

Result in WKWebView: **fail.** The frame document is same-origin and readable. Its `contentType` is `application/pdf`, and its body holds one `<embed>`. ⌘A selects the whole PDF page in WebKit's PDF view (`evidence/p4-2-pdf-select-all.png`), but the page and the frame both return an empty string. The selection lives in the PDF plug-in, outside the DOM.

Result in Chromium: not testable. The browser pane shows an empty frame for the PDF, because it has no PDF viewer.

Fallback: keep plan 5.8 as written. PDF-only Papers get Chat on their page text (`papers/pdf.py:36-40`), and no Highlights or Ask. Two later options exist, and this spike did not test them: show PDF Papers in a native `PDFView`, which gives `currentSelection` to the shell, or render them with PDF.js, which puts the text in the DOM.

### 5.3 Check 3: a long silent stream, and a disconnect

Method: from the page, `fetch('/spike/stream?...')` reads the body with a `ReadableStream` reader. The route writes one line a second for 120 s, with no write from 25 s to 95 s. A second stream has a 50 s gap. A third stream aborts with `AbortController` at 10 s. The route is on the app's own `Handler`, so the HTTP/1.0 response, the body that ends on close, and the 15 s socket timeout (`app/server.py:278`) are the real ones.

| Stream | WKWebView | Chromium |
| --- | --- | --- |
| 120 s, 70 s silent gap | 50 of 50 lines. The first line after the gap arrives at 95.0 s. The body ends at 120.14 s. | 50 of 50 lines. After the gap at 95.0 s. Ends at 120.12 s. |
| 90 s, 50 s silent gap | 40 of 40 lines. Ends at 90.11 s. | Not run. |
| Abort at 10 s | `AbortError` at 10.01 s. The server's write at 10.05 s succeeds. The write at 11.06 s raises `BrokenPipeError`. | `AbortError` at 10.0 s. The write at 10.04 s succeeds. The write at 11.05 s raises `BrokenPipeError`. |

Result: **pass** in both. A 70 s silence did not stop the stream in WKWebView. The 15 s socket timeout does not apply, because the handler does not read or block on a send during the gap.

What a disconnect does: the first write after the client leaves succeeds, and the second write raises `BrokenPipeError`. `handle_request` already catches it (`app/server.py:506`). So the server learns of a disconnect only when it writes twice. During a long silent reasoning phase it writes nothing, so it cannot see that the reader pressed Stop or closed the Paper.

Rule for C3: while the provider is silent, the Chat route writes a heartbeat byte about every 5 s. Then a Stop or a closed page ends the provider request within about 10 s, which criterion 9 needs. A whitespace byte before the answer text is enough, and the page ignores it. If a later WebKit version drops a silent stream, the same heartbeat keeps the stream alive.

### 5.4 Check 4: ⌘F and a panel beside the Paper frame

Method: the Native shell's Find bar calls `WKWebView.find` on the whole web view (`app/macos/Shell.swift:365-367`), and its field says "Find in this view" (`:314`). The step adds a panel to the page, beside the Paper frame, with a unique word. Then it types words in the Find bar and reads the status and the selection.

| Word | Where | Found |
| --- | --- | --- |
| `zqxpanelword` | panel in the page | yes. The page selection is the word. |
| `desiderata` | Paper frame only | yes. The frame selection is the word. |
| `self-attention` | both | yes. The first two matches are in the frame. |
| `zqxinert` | panel with `inert` | yes |
| `zqxnoselect` | panel with `user-select: none` | yes |
| `zqxshadow` | panel in an open shadow root | yes |
| `zqxariahidden` | panel with `aria-hidden="true"` | yes |
| `zqxmissing` | nowhere | no ("Not found") |

A loaded same-origin `<iframe>` panel is searched too: Find selected `journalistic` inside it (`p4-steps-fallback2.json`, `evidence/p4-4-find-iframe-panel.png`). A `srcdoc` panel rendered empty under the page's policy, so its "Not found" proves nothing.

Result: `WKWebView.find` searches the page document and every frame in it. No attribute or style that a Chat panel can keep hides its text from Find.

Rule for criterion 15: **Find covers the Paper and the Chat panel.** The Find bar already says "Find in this view". Search inside Chat answers is also a request in alphaXiv's tracker (#293). The test for the rule: a word that is only in an answer is found, and a word that is only in the Paper is found.

Fallback, if the rule must be "Find covers the Paper only": move the panel out of the page's document. An `<iframe>` panel does not do it. Two ways: a second `WKWebView` or a native AppKit panel in the Native shell, or a Find of our own that searches the Paper frame's text and paints the matches with the Highlight API. Browser mode then keeps the browser's own Find, which also searches every frame.

## 6. How to run the spikes again

LATER

## 7. Limits

LATER
