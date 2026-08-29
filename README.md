# Papers to Kindle

A small macOS Chrome extension that turns arXiv or alphaXiv papers into validated, reflowable EPUBs and sends them through the configured Mail app to your Kindle. On an alphaXiv library folder, it can combine up to 50 papers into one anthology.

The final EPUB is also kept under `~/Downloads/Arxiv to Kindle/`. Downloaded TeX and intermediate files live only in a temporary directory and are deleted after conversion.

## Requirements

- macOS with Google Chrome and Mail configured to send email
- Python 3
- [Pandoc](https://pandoc.org/installing.html): `brew install pandoc`
- [Ghostscript](https://ghostscript.com/) for legacy EPS figures: `brew install ghostscript`
- An Amazon Send-to-Kindle address ending in `@kindle.com`

Before the first send, add the email address used by macOS Mail to Amazon's **Approved Personal Document Email List** under **Manage Your Content and Devices → Preferences → Personal Document Settings**. Amazon accepts EPUB personal documents; its [Send to Kindle](https://www.amazon.com/sendtokindle) page is the fallback when email delivery is unavailable.

## Install

1. Open `chrome://extensions` in Chrome.
2. Enable **Developer mode**.
3. Click **Load unpacked** and choose the `extension` directory in this project.
4. Copy the 32-character extension ID shown by Chrome.
5. In Terminal, run:

   ```sh
   cd /path/to/arxiv-paper-to-kindle
   ./install.sh YOUR_EXTENSION_ID
   ```

6. Restart Chrome.

The installer copies one Python file and one native-host manifest into your user Library. It installs no daemon and stores no mail password.

## Use

1. Open a paper at `https://arxiv.org/abs/XXXX.YYYYY` or `https://www.alphaxiv.org/abs/XXXX.YYYYY`. alphaXiv query parameters such as `?chatId=...` are supported and ignored during identifier extraction.
2. Open the extension.
3. Enter your Send-to-Kindle address on first use. Chrome stores it locally and collapses it under **Delivery settings** on later uses.
4. Click **Send paper**.

For an alphaXiv library folder, wait for its paper list to load and open the extension. It reads the paper links visible in the folder page, reports the exact count, and offers **Compile and send N papers**. Duplicate links are removed in first-seen order. The conversion continues in the background if you close the popup, and reopening it shows the latest paper-level progress.

The combined EPUB keeps every paper's internal reading order but its table of contents contains only the paper titles, in folder order. It does not contain the individual section headings. A folder with no loaded paper links or more than 50 papers is rejected instead of producing a partial anthology.

macOS may ask once whether the Python host may control Mail. Allow it for one-click delivery. Mail sends from its default account, so that account's address must be on Amazon's approved-sender list.

To convert one paper without sending:

```sh
python3 native/host.py --convert-only https://arxiv.org/abs/XXXX.YYYYY
```

## What is preserved

The converter uses the root TeX document and follows its `\input`/`\include` order. Pandoc produces the EPUB table of contents, MathML, figures, tables, and internal labels. When an arXiv archive supplies a compiled `.bbl` instead of its `.bib`, the host restores every in-text citation as visible linked text and includes the compiled References entries in their original order. Valid BibTeX continuation comments between a `\bibitem` label and key are accepted, and multiline compiled `\href` commands are normalized so Pandoc retains the References block. Empty, malformed, duplicate, or unresolved keys remain hard failures. It rejects empty citations, missing citation keys, missing References content, and broken bibliography links instead of sending a partial paper.

alphaXiv is used only as a trusted source of arXiv identifiers. TeX archives still come directly from arXiv, and the extension does not read alphaXiv cookies, account tokens, chats, or private API data.

The host also normalizes common arXiv source patterns that Pandoc otherwise loses: wide/centered tables, custom column types, resized tables, math-array tables, scaled inline and display equations, `alltt`/verbatim/listings/minted code blocks, abstract footnotes, EPS figures, and LaTeX 2.09 front matter. Print-only `\scalebox` and `\resizebox` wrappers are removed while their reflowable content is retained, so equations remain MathML instead of disappearing or leaking raw TeX. If Pandoc still reports that it rendered an equation as TeX, conversion stops rather than sending a damaged EPUB. Its front matter reads **Cover → Table of Contents → Abstract** without a duplicate title page; the complete title remains on the cover and in EPUB metadata. It keeps a nonempty Abstract before the first numbered paper section, including abstract footnotes. After conversion, it verifies the EPUB spine, packaged files, and every local `href`, `src`, and fragment target, repairing cross-chapter and equation anchors when the target is unambiguous.

The cover uses a warm journal-style template containing only the complete title and arXiv ID. It is rendered locally with macOS tools and packaged as a verified 1200 x 1600 PNG so Amazon receives a real cover image rather than an unsupported SVG placeholder. If the cover cannot be rendered exactly, conversion stops instead of sending a coverless EPUB.

Each EPUB also declares the EPUB 3 series metadata `Arxiv Series`. This is experimental: Amazon documents true Kindle series grouping for store/KDP books, not Send-to-Kindle personal documents, so Kindle may ignore the field. The metadata does not change the paper title, authors, identifier, or reading order.

## Honest fidelity boundary

EPUB is reflowable, so it cannot retain the paper's page layout. Pandoc also does not implement every custom LaTeX macro or package. The converter fails on detected missing files, media, or links instead of claiming success, but no generic converter can prove that arbitrary TeX preserved every semantic detail. For unusually macro-heavy papers, use the retained PDF or manually inspect the saved EPUB before relying on it.

## Verify locally

```sh
python3 -m unittest -v
python3 -m py_compile native/host.py tests/test_host.py
bash -n install.sh
python3 -m json.tool extension/manifest.json
node --test tests/test_extension.js
node --check extension/shared.js
node --check extension/background.js
node --check extension/popup.js
```

The integration test builds a multi-file paper with ordered sections, a figure, a table, and internal references, runs the installed Pandoc, and inspects the resulting EPUB archive.
