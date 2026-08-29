# alphaXiv and Library Anthologies Design

## Goal

Fix compiled bibliography parsing, accept trusted alphaXiv paper pages, and turn the papers visible in an alphaXiv library folder into one Kindle-ready EPUB whose table of contents contains paper titles only. Improve the popup so a saved Kindle address is not exposed as a primary field on every use.

The existing guarantees remain mandatory: preserve each paper's source order, text, figures, tables, equations, citations, bibliography, and valid internal links; fail on detected omissions; add no hosted service or third-party runtime dependency; and never send mail during automated tests.

## Chosen approach

Three implementation routes were considered:

1. Use alphaXiv's authenticated library API. This could retrieve a complete folder directly, but it would require account integration, token handling, and a new privacy/security boundary.
2. Scrape alphaXiv's private application data structures. This could expose unloaded papers, but it would couple the extension to undocumented framework internals.
3. Collect trusted `/abs/{arxiv-id}` links from the active library page and reuse the existing arXiv source converter. This needs no account access and survives alphaXiv query parameters and most layout changes.

The third option is selected. It is the smallest private implementation that matches the supplied folder view. The popup will report the exact number of collected papers before starting. A folder with no paper links is rejected rather than silently producing an empty anthology. Collection size is capped at 50 papers to bound download, conversion, attachment, and native-message work.

## URL and trust model

The shared native parser accepts only HTTPS abstract URLs on:

- `arxiv.org` and `www.arxiv.org`;
- `alphaxiv.org` and `www.alphaxiv.org`.

The path must be exactly `/abs/{id}` with an optional trailing slash. Query strings and fragments are ignored. Modern, versioned, and legacy arXiv identifiers keep their existing validation. alphaXiv never becomes a source-download origin: after extracting the identifier, the native host continues to download TeX from arXiv's export endpoint.

On an alphaXiv folder page, an active-tab script reads anchors under the page's main content, extracts the same trusted `/abs/{id}` paths, preserves their visual DOM order, and removes duplicates. It does not read cookies, local storage, account identifiers, comments, chat data, or arbitrary page text.

## Compiled bibliography repair

The current parser assumes the bibliography key's opening brace immediately follows an optional label except for whitespace. Generated `.bbl` files commonly place a TeX continuation comment between them:

```latex
\bibitem[Author(2024)]%
  {paper-key}
```

That valid form currently raises `A compiled bibliography key is malformed.` The parser will use one shared trivia skipper for whitespace and TeX comments before the optional label and before the required key. It will also ignore commented-out `\bibitem` text. Duplicate keys, empty keys, unclosed labels, and genuinely missing key braces remain hard failures.

Pandoc also drops an entire valid compiled bibliography when BibTeX places a line break between `\href` and its first braced argument. The host will join only that command-to-argument whitespace inside the selected `.bbl`; link text and URLs remain unchanged.

## Single-paper flow

On either arXiv or alphaXiv `/abs/{id}` pages, the popup shows the detected paper state and one primary `Send paper` action. It sends the current trusted URL to the unchanged local conversion pipeline. The resulting file, metadata, cover, citations, reading order, validation, Downloads copy, and Mail behavior are identical across the two sites.

## Library anthology flow

The extension sends an ordered list of alphaXiv paper URLs plus the visible folder title to the native host. The host validates and deduplicates the identifiers, then converts each paper sequentially with the existing strict `convert_source` function. A failure names the affected paper and stops the anthology; a partial or unvalidated paper is never included.

The anthology builder packages the already-validated EPUB contents without reparsing the papers:

- each paper's EPUB content tree is copied into its own namespace, so relative media and cross-document links remain valid;
- cover and navigation documents from the individual book are omitted;
- a visible paper-title heading and stable anchor are inserted before each paper's first body document;
- the anthology package spine keeps the requested paper order and each paper's internal reading order;
- one new text cover uses the folder title and paper count;
- the EPUB 3 navigation document contains exactly one top-level entry per paper and no section entries;
- the anthology metadata identifies the folder as an alphaXiv library compilation.

The complete anthology is validated as an EPUB container, including every local file and fragment target. A separate validator check requires the navigation labels to equal the ordered paper-title list exactly.

## Long-running job behavior

Multi-paper conversion can outlive a popup window. The popup therefore hands work to a minimal Manifest V3 background worker. The worker holds one native-messaging port, stores the latest job state in session storage, and relays native progress messages. The user may close and reopen the popup without cancelling the job. Only one conversion runs at a time; a second start receives a clear busy state.

The native host reports `Downloading paper i of n`, `Converting paper i of n`, `Building anthology`, and `Sending to Kindle`. The final response includes the saved EPUB path. Mail failure still preserves and exposes the validated EPUB for manual upload.

## Popup UX

This is a compact utility redesign, not a marketing surface. Design dials are variance 3, motion 2, density 5.

- The main hierarchy is context, title, short description, primary action, then status.
- The saved Kindle address lives inside a `Delivery settings` disclosure. The disclosure opens automatically only when no valid address is stored or when address validation fails.
- The summary says `Kindle address saved` without exposing the address.
- Paper and folder states get distinct action copy; invalid pages get an actionable empty state.
- Buttons and disclosure controls meet a 44px target; focus is visible; body text passes 4.5:1 contrast; error and success states are not conveyed by color alone.
- Motion is limited to short state transitions and is disabled under reduced-motion preferences.
- One sans-serif system stack, one blue accent, one 10px component radius, and no decorative imagery keep the popup native and quiet.

## Error behavior

- Malformed bibliography syntax still names the bibliography problem, but valid TeX comments no longer trigger it.
- Unsupported or lookalike domains fail before network access.
- alphaXiv folder pages with zero paper links explain that the folder must finish loading.
- Duplicate folder links are deduplicated without changing first-seen order.
- More than 50 papers is rejected with a clear limit.
- A failed paper identifies its position and arXiv ID; no anthology is saved or mailed.
- An anthology packaging or link-validation failure stops delivery.
- Mail failures preserve the final validated file for manual Send to Kindle upload.

## Verification

Automated tests must prove:

- compiled `.bbl` keys parse across TeX continuation comments and commented-out entries are ignored;
- malformed, empty, and duplicate keys still fail;
- native URL parsing accepts alphaXiv with or without query parameters and rejects lookalikes;
- single alphaXiv requests use the same arXiv ID conversion path;
- ordered duplicate folder URLs become one ordered identifier list and the 50-paper bound is enforced;
- the anthology contains each paper's content and media, preserves every local link, and has a paper-title-only table of contents in source order;
- a failed member conversion prevents anthology output;
- popup helpers classify arXiv, alphaXiv, and folder states and validate/mask saved delivery settings;
- the full Python suite and JavaScript syntax/tests pass.

Visual verification covers the popup's paper, folder, first-use settings, working, success, error, and unsupported-page states at its real Chrome dimensions with keyboard focus and both system color schemes.
