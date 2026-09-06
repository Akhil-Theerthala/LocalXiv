# LocalXiv

A local macOS paper library for importing arXiv and alphaXiv links, reading retained papers, generating illustrated technical overviews, finding related papers, and exporting or sending EPUBs to Kindle. The local app is the recommended workflow. A Chrome extension remains available for single-paper imports and the existing direct-send and anthology workflows.

LocalXiv was previously named Papers to Kindle. The installer moves the previous library to `~/Library/Application Support/LocalXiv/library` when that destination does not exist. Stop the old background service before reinstalling. Existing credentials retain their internal identifiers. If both library folders exist, the installer leaves them separate and uses the LocalXiv library.

## Install the local app

Install Apple Command Line Tools with `xcode-select --install` if needed. The installer compiles a small native macOS window using AppKit and WebKit; it does not require Electron. Install the conversion tools and JavaScript dependencies, then create the app bundle:

```sh
brew install python pandoc latexml librsvg ghostscript epubcheck node
cd /path/to/arxiv-paper-to-kindle
npm ci --ignore-scripts --omit=dev
./install-app.sh
open "$HOME/Applications/LocalXiv.app"
```

Python runs the service, Pandoc and LaTeXML convert source, librsvg and Node draw equations and covers, Ghostscript handles EPS/PDF figures, and EPUBCheck checks both EPUB profiles. This build requires macOS `sandbox-exec` for source conversion. For papers that need a TeX engine or additional packages, install MacTeX with `brew install --cask mactex-no-gui`, or use an existing TeX Live installation. TeX is optional for papers that do not need it. No custom graphics binding or experimental upstream LaTeXML build is installed by these commands.

Opening the installed app uses its own window, Dock item, and menu bar. External links can still open your default browser. EPUB downloads use a native Save dialog. Closing the window keeps the app available in the Dock; Quit closes the app, while the local service continues so pending jobs can finish. Process updates appear as dismissible bottom-right toasts. Successful updates disappear automatically; failures stay until dismissed. The translucent header includes native window dragging in its blank areas.

To run from the checkout instead of installing the app, use `./launch.command`. When the app is installed, this opens its native window for the default library; a custom test library uses the browser. `./launch.command --serve` starts the service without opening a window. Both launch methods use `~/Library/Application Support/LocalXiv/library` by default. The app bundle is under `~/Applications`; its replaceable runtime is under `~/Library/Application Support/LocalXiv/app`. Re-running `install-app.sh` updates the runtime without replacing the library. Close the running service before relaunching an updated runtime.

For a separate test library, use `./launch.command --data-dir /path/to/test-library --port 8877`. `PAPERS_INSTALL_ROOT` and `PAPERS_APPLICATIONS_DIR` let a test installation use temporary directories. The extension handoff expects the normal installation location.

## Read, explain, and export

1. Paste an arXiv or alphaXiv paper URL. Abstract, PDF, HTML, alphaXiv overview, versioned, and legacy arXiv identifiers are accepted by the local app. An unversioned link resolves to a pinned version before conversion.
2. Open the **Paper** tab to read the original converted content, or use **Overview** after configuring an AI provider. The reader defaults to 16px. The header has a light/dark toggle and a Settings gear. A reading-only bottom bar controls font size, margin width, and typeface, with a highlighted **Send to Kindle** button. Georgia, Charter, Palatino, and system sans use local fonts and work offline. Figures fit within the viewport and open in a larger viewer when clicked. Markdown tables render as tables.
3. Click **Send to Kindle** in the bottom bar and choose the paper, generated overview, or both. Save an EPUB locally, or send it through macOS Mail after configuring your Kindle address.

The Kindle profile draws equations as images with inline baseline offsets. The semantic EPUB keeps MathML. The browser reader uses semantic math. These are reflowable documents, not copies of the PDF page layout; a rendered check on your Kindle is still needed before judging device-specific equation behavior.

The source archive, available original PDF, converter attempts, reader documents, and exported artifacts remain in the library. If EPUB conversion fails or source files are unavailable, the app opens the downloaded PDF and shows a notice that sending the paper will send a PDF. The import remains usable, and macOS PDFKit extracts page-linked text inside the conversion sandbox for overview generation. PDFs without selectable text remain readable and sendable, with an explanation that an overview needs extractable text. The paper PDF and overview EPUB can be downloaded or sent separately; the combined EPUB option is unavailable for PDF imports. A failed retry does not replace an existing ready EPUB. Jobs interrupted by a service restart are not silently resumed. An ambiguous Mail result is not automatically retried.

First launch offers one optional setup screen for the API base URL, model, key, and Kindle email. A four-step walkthrough uses animated arrows and highlights to move from Home through the library and the complete **Attention Is All You Need** paper, then returns Home. The tour imports the pinned arXiv version 1706.03762v7 when needed, puts it first in Library during the tour, and reuses it on later visits. This import skips automatic overview generation and Kindle delivery. Library is a full page. On mobile, contents and reading preferences open on demand; desktop keeps the direct controls. On both sizes, the reader dock expands from an Aa circle at the bottom-right. Toasts fade after five seconds. Theme colors ease between modes. Replay setup or the tour from the Settings gear. Overview sections and figures animate once as they enter view; Reduce Motion disables the animations. Configure AI under **Settings**, or skip setup. Supply an OpenAI-compatible chat-completions endpoint, model name, and key. Test connection checks the current form values with a small model request before saving; it can also use the saved key. Keys are stored in macOS Keychain and sent to the configured provider only by the backend. Provider-reported input, output, and total token counts are recorded per response in the local library database for recommendations and overviews, including reported usage from truncated responses. These records contain no keys or request content. Paper text goes to that provider when generating an overview. Recommendations send saved titles and public candidate abstracts. Compatibility with one provider does not establish support for every endpoint or model. Context/output limits, provider errors, or unavailable Keychain access can prevent generation without preventing local reading. No live-provider quality result is implied by the mocked API tests.

Overview generation has six stages: read all retained paper sections into evidence notes; plan 3–7 article sections and 1–3 figure briefs; draft the sectioned article; check and edit it against those notes; design each figure from its brief and original supporting passages; review each figure's meaning and render it locally. This uses N + 3 + 2F model calls for N reading batches and F figures. Figure rendering makes no API call. Writing prompts ask for clear paragraph openings, definitions before abbreviations, intuition before equations, comparisons beside numbers, and explicit limitations.

Drafts contain `{Insert figure|fig1|Draw X to explain Y}` briefs. The app replaces them with captioned PNGs and links to editable `.excalidraw` files. The pinned MIT-licensed [Excalidrawer](https://github.com/guohaonan-shy/excalidrawer) renderer also produces SVGs. The current visual vocabulary supports short sequences and paired conceptual comparisons. It does not invent measured charts. Each figure records its question, takeaway, scope and evidence. Local checks reject geometry warnings; model review checks the diagram's meaning against passages. There is no independent vision-model review at runtime.

Passage IDs are retained in the internal cited draft and evidence record, but omitted from overview prose and EPUBs. Existing overviews get citation cleanup without another API call; the new article structure and figures appear after **Regenerate overview**. A failed regeneration keeps the previous saved article. Overviews retain model, prompt revision, document identity, source citations, and reported usage. Generated writing is separate from the original paper and can be reopened without another API call. Context overflow produces an error instead of silently discarding paper sections.

Home opens with an **Add your paper** bar. With saved papers and a configured API key, it shows up to three related papers with short summaries. One public DBLP search finds main-conference records from the last ten calendar years, excluding workshops and Findings/industry tracks. An [arXiv API](https://info.arxiv.org/help/api/user-manual.html) query matches those titles to available preprints and abstracts, keeping at most twelve candidates. One model request receives the current date, conference names, publication years, and abstracts. It prioritizes relevant work from the last three years, favors ICML, NeurIPS, and ICLR when equally relevant, and can retain older foundational work within the decade. Cards show the conference and year with a DBLP record link. Papers without a matching conference record and arXiv version are omitted, so the list can contain fewer than three. Conference membership is a discovery filter, not proof that a paper is a breakthrough. Requests use at most 12,000 input characters and 900 output tokens, respecting lower configured limits. Results are cached on disk and checked when the app opens or polls, refreshing after 24 hours or a changed library. Adding a paper also triggers that check. Failed attempts preserve the previous list and wait until the next day or library change. No key or an empty library means no recommendation search or model request.

Automatic overview and automatic paper delivery are separate saved preferences. Overviews run after import when AI is configured, unless you disable that preference. Automatic delivery is off by default. A completed send means the artifact was handed to Mail; it does not confirm arrival on Kindle. Add the account used by Mail to Amazon's approved-sender list before enabling delivery.

## Conversion evidence and limits

The current local pipeline tries Pandoc first and LaTeXML on a fresh source copy when needed. Source processing runs in an OS sandbox with no network and bounded runtime/resources. Both EPUB profiles must pass EPUBCheck and local resource/link checks before publication. Numeric linked citations preserve bibliography order and narrative citation text where supported. These checks detect particular failures; they cannot establish semantic equivalence for arbitrary TeX.

Some papers have no downloadable TeX or require unsupported macros, packages, or assets. The application does not promise successful conversion of every paper. Inspect figures, tables, equations, references, and appendices before relying on a converted research document.

The verification files record specific pinned versions and may be refreshed as conversion work proceeds:

- [Local application verification](docs/verification/local-paper-library.md), covering the installed workflow, tests, and remaining device/provider checks.
- [Corpus and source availability](docs/verification/corpus-discovery.md), with the [machine-readable corpus](docs/verification/corpus.json).
- [Conversion results](docs/verification/conversion-results.json), separating passed, failed, and unfinished attempts rather than extrapolating to all papers.
- [Content fidelity audit](docs/verification/content-audit.md), with [artifact hashes and detailed findings](docs/verification/content-audit.json). Its review flags and snapshot date matter even when an EPUB passed packaging checks.
- [LaTeXML compatibility investigation](docs/verification/latexml-runtime.md), including unsuccessful experiments that are not shipped dependencies.

## Optional Chrome extension

After installing the local app and the native host below, choose **Import into local library** on a single-paper abstract page to use the new library pipeline. No Kindle address is required for that handoff. It follows the app's saved automatic overview and delivery preferences and opens the app for progress. After updating the extension, rerun `install.sh` so the installed native host understands this action.

The original extension's **Send paper** and **Compile and send** actions remain available. Their final EPUB is kept under `~/Downloads/Arxiv to Kindle/`; unlike local-library imports, their downloaded TeX and intermediate files are temporary and deleted after conversion. The following sections describe that existing direct-send workflow.

### Direct-send requirements

- macOS with Google Chrome and Mail configured to send email
- Python 3
- [Pandoc](https://pandoc.org/installing.html): `brew install pandoc`
- [Ghostscript](https://ghostscript.com/) for legacy EPS figures: `brew install ghostscript`
- pdfLaTeX or XeLaTeX for papers whose diagrams are written directly with the LaTeX `forest` package. The engine and the paper's required TeX packages are optional for other papers.
- An Amazon Send-to-Kindle address ending in `@kindle.com`

Before the first send, add the email address used by macOS Mail to Amazon's **Approved Personal Document Email List** under **Manage Your Content and Devices → Preferences → Personal Document Settings**. Amazon accepts EPUB personal documents; its [Send to Kindle](https://www.amazon.com/sendtokindle) page is the fallback when email delivery is unavailable.

### Install the extension and native host

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

### Direct-send usage

1. Open a paper at `https://arxiv.org/abs/XXXX.YYYYY` or `https://www.alphaxiv.org/abs/XXXX.YYYYY`. alphaXiv query parameters such as `?chatId=...` are supported and ignored during identifier extraction.
2. Open the extension.
3. Enter your Send-to-Kindle address on first use. Chrome stores it locally and collapses it under **Delivery settings** on later uses.
4. Click **Send paper**.

For an explicit alphaXiv folder route such as `https://www.alphaxiv.org/library/folders/uncertainty`, wait for its paper list to load and open the extension. It reads the visible paper links, shows the first five paper titles for review, reports the exact count, and offers **Compile and send N papers**. Duplicate links are removed in first-seen order. Other alphaXiv list and search pages are not treated as folders. The conversion continues in the background if you close the popup, and reopening it shows the latest paper-level progress.

The combined EPUB keeps every paper's internal reading order but its table of contents contains only the paper titles, ordered by their verified initial arXiv submission dates. It does not contain the individual section headings. A folder with no loaded paper links is unavailable. A folder with more than 50 papers stays visible for review, but the extension disables submission before native conversion starts instead of producing a partial anthology.

macOS may ask once whether the Python host may control Mail. Allow it for one-click delivery. Mail sends from its default account, so that account's address must be on Amazon's approved-sender list.

To convert one paper without sending:

```sh
python3 native/host.py --convert-only https://arxiv.org/abs/XXXX.YYYYY
```

### Direct-send conversion details

The converter uses the root TeX document and follows its `\input`/`\include` order. Pandoc produces the EPUB table of contents, MathML, figures, tables, and internal labels. When an arXiv archive supplies a compiled `.bbl` instead of its `.bib`, the host restores every in-text citation as visible linked text and includes the compiled References entries in their original order. Valid BibTeX continuation comments between a `\bibitem` label and key are accepted, and multiline compiled `\href` commands are normalized so Pandoc retains the References block. Empty, malformed, duplicate, or unresolved keys remain hard failures. It rejects empty citations, missing citation keys, missing References content, and broken bibliography links instead of sending a partial paper.

alphaXiv is used only as a trusted source of arXiv identifiers. TeX archives still come directly from arXiv, and the extension does not read alphaXiv cookies, account tokens, chats, or private API data.

The host also normalizes common arXiv source patterns that Pandoc otherwise loses: wide/centered tables, custom column types, resized tables, math-array tables, scaled inline and display equations, `alltt`/verbatim/listings/minted code blocks, abstract footnotes, EPS figures, and LaTeX 2.09 front matter. Print-only `\scalebox` and `\resizebox` wrappers are removed while their reflowable content is retained, so equations remain MathML instead of disappearing or leaking raw TeX. If Pandoc still reports that it rendered an equation as TeX, conversion stops rather than sending a damaged EPUB. Its front matter reads **Cover → Table of Contents → Abstract** without a duplicate title page; the complete title remains on the cover and in EPUB metadata. It keeps a nonempty Abstract before the first numbered paper section, including abstract footnotes. After conversion, it verifies the EPUB spine, packaged files, and every local `href`, `src`, and fragment target, repairing cross-chapter and equation anchors when the target is unambiguous.

Diagrams written directly in a live `forest` environment are rendered with the paper's own preamble using pdfLaTeX or XeLaTeX, then embedded as full-width PNGs. LuaLaTeX is refused for downloaded sources because embedded Lua can bypass TeX's file-I/O restrictions. Citations and cross-references used inside the diagram remain below it as live EPUB links, so diagram-only sources still appear in References. The renderer disables shell escape and applies restrictive TeX file-I/O settings, but these controls are not an OS-level sandbox. It also stops on unresolved references instead of rasterizing `??` or `[?]`.

The cover uses a warm journal-style template containing only the complete title and arXiv ID. It is rendered locally with macOS tools and packaged as a verified 1200 x 1600 PNG so Amazon receives a real cover image rather than an unsupported SVG placeholder. If the cover cannot be rendered exactly, conversion stops instead of sending a coverless EPUB.

Each EPUB also declares the EPUB 3 series metadata `Arxiv Series`. This is experimental: Amazon documents true Kindle series grouping for store/KDP books, not Send-to-Kindle personal documents, so Kindle may ignore the field. The metadata does not change the paper title, authors, identifier, or reading order.

### Direct-send fidelity boundary

EPUB is reflowable, so it cannot retain the paper's page layout. Pandoc also does not implement every custom LaTeX macro or package. The converter fails on detected missing files, media, or links instead of claiming success, but no generic converter can prove that arbitrary TeX preserved every semantic detail. For unusually macro-heavy papers, use the original PDF or manually inspect the saved EPUB before relying on it.

## Verify locally

```sh
python3 -m unittest -v
python3 -m py_compile native/host.py tests/test_host.py
bash -n install.sh install-app.sh launch.command
python3 -m json.tool extension/manifest.json
node --test tests/test_extension.js
node tests/test_app_ui.js
node --check extension/shared.js
node --check extension/chronology.js
node --check extension/background.js
node --check extension/popup.js
```

The integration test builds a multi-file paper with ordered sections, a figure, a table, and internal references, runs the installed Pandoc, and inspects the resulting EPUB archive.
