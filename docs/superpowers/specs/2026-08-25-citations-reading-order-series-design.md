# Citation, Reading Order, and Series Metadata Design

**Status:** Approved for implementation on 2026-08-25.

## Goal

Produce Kindle-ready EPUBs whose citations and bibliography remain visible and linked, whose front matter reads `Cover -> Table of Contents -> Abstract`, and whose package includes experimental `Arxiv Series` metadata without changing the paper title or authors.

## Observed failures

The delivered EPUB for arXiv `2606.19868` contains 193 citation spans and all 193 are empty. Its source archive contains `main.bbl` but no `.bib` or `.bibtex`, while the converter only enables Citeproc for the latter. The same EPUB spine begins with `cover.xhtml`, `title_page.xhtml`, `nav.xhtml`, and `ch001.xhtml`, producing the redundant title page before the table of contents.

These defects exist in the generated EPUB before Amazon receives it; Kindle ingestion is not their cause.

## Citation and bibliography behavior

When the source includes a compiled `.bbl`, the converter will treat it as the authoritative bibliography. It will preserve each `\bibitem` key, compiled label when present, entry order, and rendered entry content. Numeric bibliographies will use their sequential numbers when no optional compiled label is present.

Before Pandoc runs, the root bibliography command will be replaced with an unnumbered `References` section that inputs the matching `.bbl`. After Pandoc runs, the converter will assign stable anchors to the rendered bibliography entries and replace every empty citation span with visible links using the `.bbl` labels. Multiple-key citations will remain one bracketed citation with independently clickable labels.

If `.bib` or `.bibtex` is available without a usable `.bbl`, the existing Citeproc route remains the fallback. If source citation commands exist, validation must reject an EPUB containing an empty citation, a missing References section, an unresolved citation key, or a broken citation link. It must never silently send a partial paper.

## Reading order

Pandoc will run with its generated EPUB title page disabled and with the navigation title set to `Table of Contents`. The required front-matter spine order is:

1. cover document;
2. navigation/table-of-contents document;
3. Abstract document when the source contains an abstract;
4. numbered paper sections;
5. References when citations are present.

The paper title remains in EPUB package metadata and on the cover but does not appear as a standalone reading-order page or as the table-of-contents heading.

## Series metadata

Every generated EPUB will include the experimental series name `Arxiv Series`. The metadata is best-effort because Send to Kindle personal documents do not have Amazon's store-side/KDP series entity. It must not alter the paper title, author list, identifier, cover, or reading order, and conversion must not fail merely because a downstream Kindle service ignores it.

Use EPUB 3 collection metadata:

```xml
<meta property="belongs-to-collection" id="arxiv-series">Arxiv Series</meta>
<meta refines="#arxiv-series" property="collection-type">series</meta>
```

## Validation and testing

Tests must reproduce the exact reported failures before implementation and prove the repair afterward:

- a minimal `.bbl` paper produces visible linked citations and a complete References section;
- every bibliography anchor and citation link resolves;
- a missing citation key fails instead of disappearing;
- the spine begins `cover -> nav -> abstract`, contains no generated title page, and the nav heading is `Table of Contents`;
- package metadata contains `Arxiv Series` without changing title or author metadata;
- the affected real paper has 193 nonempty citation occurrences, a References section, the approved front-matter order, a valid PNG cover, a nonempty Abstract before Section 1, and no broken local targets.

Run the full unit/integration suite, static syntax checks, strict validation on the existing real-paper corpus, reinstall the native host, compare the installed implementation with the workspace file except for the installer-managed shebang, and regenerate the affected EPUB without sending mail.

## Constraints

- Preserve source ordering, wording, figures, tables, equations, labels, and valid links.
- Use the existing standard-library Python architecture and installed Pandoc; add no package or hosted service.
- Keep external renderer timeouts at 30 seconds.
- Do not automate Kindle Collections or publish through KDP.
- Do not send email while testing.
- Do not initialize Git in this directory.
