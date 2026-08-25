# EPUB Cover and Abstract Design

## Goal

Replace the current SVG-only cover with a Kindle-compatible cover that matches the approved Essential C2 mockup, and preserve the paper abstract in the EPUB reading order using the verified `~/Developer/XivEpub` behavior as a reference.

The existing source-order, structure, figures, tables, citations, and internal-link validation remain mandatory and unchanged.

## Approved cover

The cover is a deterministic 1200 x 1600 portrait template containing exactly:

1. The paper's full arXiv identifier in a black masthead.
2. The paper's complete title in the main field.

It contains no authors, subject/category label, footer, issue marker, generic "ARXIV READER" text, generated illustration, or paper-derived image.

The visual system is:

- warm off-white paper field;
- narrow brick-red left spine;
- black top masthead with the arXiv identifier in white monospace type;
- large dark serif title, vertically centered in the remaining field;
- a restrained black and brick-red rule below the title.

The full title must never be truncated or overlap another element. The renderer wraps on word boundaries and selects the largest font size from a bounded set that fits all title lines inside the title field. If even the smallest supported size cannot fit, cover generation fails rather than omitting text.

## Kindle-compatible image path

`write_cover` creates the SVG layout as the deterministic source artifact. A separate rasterization step converts it to a 1200 x 1600 PNG using macOS-native tooling already present on the machine. Pandoc receives the PNG through `--epub-cover-image`; the SVG is not packaged as the EPUB cover.

The rasterizer uses a bounded subprocess timeout. It verifies that the result is a real PNG with the required dimensions before conversion continues. If rasterization fails, conversion reports an explicit error and does not send an EPUB with a missing or placeholder cover. No image library or hosted service is added.

## Abstract placement

`~/Developer/XivEpub` is a source reference, not a runtime dependency. Its verified output keeps the abstract visible at the start of the EPUB. This extension will retain its existing footnote-safe abstract normalization and make the reading order explicit:

1. title page;
2. clearly labeled, unnumbered Abstract content;
3. the first numbered paper section;
4. all remaining content in source order.

The abstract text and any abstract footnotes must remain intact. The implementation will borrow only the narrow presentation behavior and abstract styling needed from `XivEpub`; it will not replace the extension's secure extraction, legacy-LaTeX handling, link repair, EPUB validation, or native-messaging pipeline.

## Conversion flow

1. Download and securely extract the arXiv source into a temporary directory.
2. Find the root TeX file and perform the existing bounded compatibility rewrites.
3. Extract title and arXiv identifier for the cover.
4. Generate the approved SVG template and rasterize it to a verified PNG.
5. Convert the source to EPUB3 with Pandoc, using the PNG cover and preserving the explicit abstract-before-section ordering.
6. Repair only uniquely resolvable Pandoc link defects.
7. Validate the EPUB package, spine, local media, local links, fragments, abstract ordering, and PNG cover declaration.
8. Save the validated EPUB and hand it to the existing delivery path.

Temporary SVG, PNG, downloaded source, and extracted files are deleted with the conversion workspace. Only the final validated EPUB remains in Downloads.

## Failure behavior

- Missing title falls back to `arXiv <id>`, as today.
- Cover rasterization failure stops conversion with a clear message.
- Abstract omission or placement after the first numbered section is a validation failure.
- Existing missing-media, broken-link, unsafe-archive, and Pandoc failures remain hard failures.
- A validated EPUB is never mailed when its cover or required paper content failed validation.

## Verification

Automated checks must prove:

- cover metadata is XML-escaped;
- cover markup contains the complete title and arXiv identifier but none of the removed metadata blocks;
- short, long, and unusually long titles fit without truncation or collision;
- the rasterized file is a 1200 x 1600 PNG;
- the EPUB manifest declares a PNG cover and packages the corresponding image;
- abstract content precedes the first numbered section;
- abstract footnotes survive;
- existing structure, media, table, equation, citation, and local-link tests continue to pass.

Final visual verification uses at least two real papers: one with a long title and one from the existing `XivEpub` verified sample. Their extracted cover PNGs are inspected at full size and as small grayscale thumbnails before the extension is considered complete.
