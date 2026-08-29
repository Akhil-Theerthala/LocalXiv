# Pandoc Caption and Extension Cache Cleanup Design

## Goal

Convert arXiv `2510.13290` without losing its figure-caption text or front-matter metadata, and clear transient extension cache whenever a final EPUB has been saved.

## Converter design

Pandoc expands the paper's `\stepone` command through `\rawstepcolor` and `\kw`. The last macro wraps its textual argument in `\begin{kwColorBox} ... \end{kwColorBox}`, which Pandoc rejects inside `\caption`.

Before conversion, the host detects `\newcommand`, `\renewcommand`, and `\providecommand` definitions that are pure inline environment wrappers around exactly one macro argument. It replaces only the definition body with that textual argument. The paper's `\kw` therefore becomes `#1`, so the existing step commands render as `1.`, `2.`, and `3.` without the print-only coloured boxes. The same narrow rule unwraps the paper's pure `\usefont` helper so `MERA` remains visible, while caption-local, single-line `\begin{sc}...\end{sc}` becomes Pandoc-safe `\textsc{...}`.

All three scanners operate on a length-preserving searchable view. TeX comments and literal `verbatim`, `verbatim*`, `Verbatim`, `lstlisting`, `minted`, and `alltt` environments are masked, while source reconstruction still uses the original bytes. Protected terminators must occupy their line; slash-run parity distinguishes real environment starts from escaped lookalikes. Definitions containing additional literal content or multiple body arguments remain untouched.

The paper uses ICML front matter rather than ordinary `\title` and `\author`. Metadata extraction therefore retains ordinary non-empty fields as first priority, then falls back to the full `\icmltitle` and the first balanced name argument of each `\icmlauthor` inside `icmlauthorlist`. It ignores the running title, affiliations, comments, empty names, and author commands outside the environment, and renders standard one-letter TeX accents as Unicode.

The regression will exercise the real `convert_source` path with the paper's macro chain and assert the generated EPUB figure caption, not merely the rewritten TeX.

## Cache design

`chrome.storage.local.kindleEmail` is a durable user setting and is not cache. `chrome.storage.session.jobState` is transient conversion state. Downloaded TeX and native intermediates already live in automatically deleted temporary directories.

When the native host returns a terminal response with a non-empty `epub_path`, the background worker will clear the whole session storage area, then publish the fresh terminal `jobState`. This removes stale extension cache while keeping the current completion state visible. The predicate is `epub_path`, not `ok`, because Mail can fail after the EPUB has been saved; that error state must retain the path for manual upload. Responses without an EPUB path will not trigger cache clearing.

## Validation

- Red/green integration regressions for the caption macro chain, font wrapper, and small-caps captions.
- Negative byte-preservation regressions for comments, literal-code environments, fake terminators, and slash parity.
- Red/green metadata regressions for the exact ICML source shape and ordinary-field precedence.
- Red/green Node regressions for successful generation, saved-EPUB Mail failure, and conversion failure without an EPUB.
- Reconvert untouched arXiv `2510.13290`, validate the EPUB, and inspect its generated figure caption.
- Run the full Python and extension suites plus syntax and diff checks.
