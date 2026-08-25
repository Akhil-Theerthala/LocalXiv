# arXiv Paper to Kindle — Design

## Goal

From an `arxiv.org/abs/<id>` page, one popup button creates a reflowable EPUB from the paper's source and sends it to the Kindle address saved during first use. The paper's source order, section hierarchy, text, citations, figures, tables, and internal cross-reference links must survive conversion. A generated text-only cover identifies the paper.

## Chosen architecture

Use a Manifest V3 Chrome extension as a thin UI and a macOS native-messaging host as the local worker.

1. The popup reads the active tab and accepts only current and legacy arXiv abstract URLs.
2. The first valid Kindle address is stored with `chrome.storage.local`.
3. Clicking **Send to Kindle** sends `{arxiv_id, kindle_email}` to the registered native host.
4. The Python host downloads `https://export.arxiv.org/e-print/<id>` into a temporary directory, safely extracts the source, locates the root TeX document, and invokes Pandoc.
5. Pandoc expands `\\input`/`\\include`, preserves document order and labels, embeds supported media, emits MathML, builds a table of contents, and processes a bibliography when source bibliography files are present.
6. The host generates a simple SVG cover containing the title, authors, and arXiv ID, packages it with the EPUB, then validates the EPUB container and every local hyperlink.
7. A durable copy is written to `~/Downloads/Arxiv to Kindle/`; all downloaded/extracted source remains inside an automatically deleted temporary directory.
8. The host uses the already-configured macOS Mail app to send the EPUB attachment. The extension never receives or stores email credentials.

This is deliberately macOS-only for the first version. Native messaging gives one-click behavior without a daemon, open local port, cloud service, or credential store.

## Alternatives rejected

- A pure browser converter would require a custom TeX pipeline and ZIP/media stack, weakening fidelity while adding substantially more code.
- A hosted conversion/email service would simplify installation but adds source-data exposure, deployment, authentication, cost, and maintenance.
- Opening Amazon's Send to Kindle website or app is a useful fallback but cannot complete upload unattended through a documented public API.

## Conversion rules

- Accept `YYMM.NNNNN`, `YYMM.NNNNNvN`, and legacy category IDs from `/abs/` URLs; remove a version suffix only from output filenames, not from the requested source URL.
- Reject archives with absolute paths, parent traversal, unsafe links, excessive expanded size, or excessive file count.
- Select the root TeX file by explicit `\\documentclass` plus `\\begin{document}`; if more than one candidate exists, prefer the one that includes other candidates, then the shallowest/largest candidate. Ambiguity is an error if no unique score winner exists.
- Use the source root as Pandoc's working directory and construct the resource path from all source directories in deterministic order.
- Include all `.bib` files with citeproc only when doing so succeeds; otherwise retry without citeproc so an existing rendered `.bbl`/the paper's own reference section remains usable.
- Preserve source section ordering. Do not summarize, rewrite, or reorder paper content.
- Treat missing referenced TeX inputs, missing image files, an empty EPUB spine, or broken local hyperlinks as conversion failures.
- Unsupported TeX packages/macros remain an explicit failure boundary. No claim of byte- or layout-identical conversion is made.

## Cover

Generate one restrained, text-only SVG at conversion time: off-white background, dark text, title, authors, and arXiv ID. SVG avoids an image library and remains crisp. If the installed Pandoc/Kindle path rejects SVG covers, render the same SVG to PNG with the system `qlmanage` command; no decorative assets are introduced.

## Delivery and first use

The popup shows a Kindle-address field until a syntactically valid address is saved. The address may be edited later. On send, macOS may ask once for permission to control Mail. The user's Mail sender address must be added to Amazon's Approved Personal Document Email List; the README will make this prerequisite explicit.

The helper saves the EPUB before attempting email. If Mail delivery fails or Amazon later rejects the document, the file remains available for manual upload at Amazon Send to Kindle.

## Error handling

The native host returns one bounded JSON response with `ok`, a human-readable message, and the saved EPUB path when available. The popup disables duplicate sends, shows the current stage, and surfaces actionable errors. Network, archive, conversion, validation, and Mail failures are distinguished. Logs go only to stderr so the native-messaging protocol is not corrupted.

## Verification

One standard-library Python test module covers URL/ID validation, safe extraction, root-document selection, title/author parsing, cover escaping, and EPUB local-link validation. Tests are written before each corresponding implementation behavior.

An integration check converts a small multi-file fixture containing ordered sections, a figure, a table, citations, and `\\ref` links. It opens the EPUB ZIP and verifies content order, media inclusion, navigation, and that every local target resolves. A bounded live arXiv smoke test is run when network access is available. Email is tested in draft mode first; an actual external send is not performed unless the configured destination belongs to the user and the extension button initiates it.

## Installation

`install.sh <extension-id>` verifies Python 3 and Pandoc, installs the executable host and native-host manifest under the user's Application Support directories, and prints the Chrome unpacked-extension steps. It does not install a daemon or alter system-wide files.
