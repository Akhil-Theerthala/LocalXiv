# Citation, Reading Order, and Series Metadata Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore visible linked citations and the complete bibliography, enforce `Cover -> Table of Contents -> Abstract` front matter, and add experimental `Arxiv Series` EPUB metadata.

**Architecture:** Keep the single-file native host and standard-library test suite. Parse a compiled `.bbl` before Pandoc, insert it unconditionally as the References section, then finalize the EPUB by anchoring bibliography entries, filling Pandoc's empty citation spans, and adding EPUB 3 series metadata. Extend the existing validator so missing citations, bibliography targets, series metadata, or front-matter order stop delivery.

**Tech Stack:** Python 3 standard library, Pandoc EPUB3, ZIP/XML, LaTeX/BBL, `unittest`, macOS Quick Look and SIPS.

## Global Constraints

- Preserve source ordering, wording, figures, tables, equations, labels, and valid links.
- Use the existing standard-library Python architecture and installed Pandoc; add no package or hosted service.
- Keep external renderer timeouts at 30 seconds.
- Do not automate Kindle Collections or publish through KDP.
- Do not send email while testing.
- Do not initialize Git or add commit steps because this directory is not a Git repository.
- Treat `Arxiv Series` as experimental metadata; conversion succeeds even if Send to Kindle ignores it.

---

### Task 1: Compiled bibliography model and source preparation

**Files:**
- Modify: `native/host.py` adjacent to other source preprocessors
- Modify: `tests/test_host.py` adjacent to conversion integration tests

**Interfaces:**
- Produces: `BibliographyEntry(key: str, label: str)`
- Produces: `prepare_compiled_bibliography(root: Path) -> list[BibliographyEntry]`
- Consumes: `_braced_argument`, `_strip_tex`, `ConversionError`

- [x] **Step 1: Write the failing compiled-BBL integration test**

Create a minimal paper with `Claim~\cite{alpha,beta}.`, `\bibliographystyle{unsrt}`, and `\bibliography{references}`. Add only `main.bbl`, containing two `\bibitem` entries, and no `.bib`. Convert it and assert:

```python
citations = [
    element
    for root in roots
    for element in root.iter()
    if "citation" in element.attrib.get("class", "").split()
]
self.assertEqual(["".join(citation.itertext()) for citation in citations], ["[1, 2]"])
self.assertIn("Alpha Author. Alpha reference.", content)
self.assertIn("Beta Author. Beta reference.", content)
self.assertRegex(content, r'href="[^"]*#ref-alpha"')
self.assertRegex(content, r'id="ref-alpha"')
```

- [x] **Step 2: Run the focused test and verify the current converter fails**

Run:

```bash
python3 -m unittest -v tests.test_host.HostTests.test_convert_source_preserves_compiled_bbl_citations
```

Expected: FAIL because the citation span is empty and the bibliography is absent.

- [x] **Step 3: Implement strict `.bbl` discovery and parsing**

Add the immutable entry type and parser:

```python
@dataclass(frozen=True)
class BibliographyEntry:
    key: str
    label: str
```

`prepare_compiled_bibliography` must prefer `root.with_suffix(".bbl")`; otherwise accept exactly one `.bbl` below the source directory. Parse `\bibitem{key}` and `\bibitem[compiled label]{key}` in file order, reject duplicate/empty keys, normalize optional labels with `_strip_tex`, and use the one-based position when no optional label exists.

Remove root-level `\bibliographystyle{...}` and `\bibliography{...}` commands. Insert exactly this block immediately before `\end{document}` so class conditionals cannot hide it from Pandoc:

```latex
\section*{References}
\input{main.bbl}
```

Use the actual `.bbl` path relative to the root directory and do not insert a second copy when the root already includes that file.

- [x] **Step 4: Add parser tests for optional labels, duplicates, and no-BBL sources**

Require optional labels to survive as visible text, duplicate keys to raise `ConversionError`, and a paper without `.bbl` to return an empty list without changing its root.

- [x] **Step 5: Run the focused parser and integration tests**

Run:

```bash
python3 -m unittest -v \
  tests.test_host.HostTests.test_prepare_compiled_bibliography \
  tests.test_host.HostTests.test_convert_source_preserves_compiled_bbl_citations
```

Expected at this task boundary: parser PASS; integration may still fail until Task 2 fills EPUB citation spans.

---

### Task 2: EPUB citation linking and strict citation validation

**Files:**
- Modify: `native/host.py` near `_repair_cross_file_fragments` and `validate_epub`
- Modify: `tests/test_host.py` citation and validation fixtures

**Interfaces:**
- Consumes: `list[BibliographyEntry]`
- Produces: `_finalize_epub(path: Path, bibliography: list[BibliographyEntry], series_name: str) -> None`
- Changes: `validate_epub(..., require_citations: bool = False, require_series: str | None = None) -> None`

- [x] **Step 1: Add failing validator tests for empty and broken citations**

Extend the EPUB fixture so a chapter may include citation spans and a References document. Assert `validate_epub(..., require_citations=True)` rejects:

- an empty `<span class="citation" data-cites="alpha"></span>`;
- citation text without an `<a>` target;
- a citation link whose `#ref-alpha` target is missing;
- citation-bearing content without a `References` heading.

Require a visible linked citation and existing bibliography target to pass.

- [x] **Step 2: Run the citation validator tests and verify they fail**

Run:

```bash
python3 -m unittest -v tests.test_host.HostTests.test_validate_epub_requires_visible_linked_citations
```

Expected: FAIL because `require_citations` is not accepted.

- [x] **Step 3: Implement compiled citation finalization**

Read the EPUB members and XML documents once. Find exactly one `div` whose class contains `thebibliography`. Ignore its first label-width paragraph when it contains only the widest label, then require the remaining top-level entry paragraphs to match the `.bbl` entry count exactly. Assign each paragraph `id="ref-<sanitized-key>"`.

For every `span.citation`, split `data-cites`, require each key in the `.bbl` map, remove any empty children, and emit bracketed XHTML anchors:

```xml
<span class="citation" data-cites="alpha beta">[<a href="#ref-alpha">1</a>, <a href="#ref-beta">2</a>]</span>
```

Write the EPUB back while preserving the original member order and compression metadata. Run `_repair_cross_file_fragments` afterward so same-file citation fragments are relocated to the References chapter.

- [x] **Step 4: Implement strict citation validation**

When `require_citations=True`, require at least one citation span, nonempty normalized citation text, at least one local anchor per span, and a `References` heading in spine content. Reuse the existing all-local-link validation to prove every citation target exists.

- [x] **Step 5: Run the compiled-BBL integration and validator tests**

Run:

```bash
python3 -m unittest -v \
  tests.test_host.HostTests.test_validate_epub_requires_visible_linked_citations \
  tests.test_host.HostTests.test_convert_source_preserves_compiled_bbl_citations
```

Expected: PASS.

- [x] **Step 6: Add and verify the unresolved-key failure**

Create a source containing `\cite{missing}` but a `.bbl` containing only `\bibitem{present}`. Require `convert_source` to raise `ConversionError` naming `missing`, then run that test and confirm PASS.

---

### Task 3: Exact front matter and experimental series metadata

**Files:**
- Modify: `native/host.py` in `convert_source`, `_finalize_epub`, and `validate_epub`
- Modify: `tests/test_host.py` strict package and integration tests

**Interfaces:**
- Changes: `_finalize_epub(path, bibliography, series_name="Arxiv Series")`
- Changes: `validate_epub(..., require_front_matter: bool = False, require_series: str | None = None)`
- Produces in OPF: `belongs-to-collection` plus `collection-type=series`

- [x] **Step 1: Add a failing converted-spine test**

Convert a minimal paper with a title, author, abstract, and Section 1. Resolve manifest IDs to spine hrefs and require:

```python
self.assertEqual(spine[:3], ["text/cover.xhtml", "nav.xhtml", "text/ch001.xhtml"])
self.assertNotIn("title_page.xhtml", " ".join(spine))
self.assertEqual(nav_heading, "Table of Contents")
self.assertEqual(first_body_heading, "Abstract")
```

The test must classify the files from OPF properties/content rather than depend on Pandoc's exact chapter filename when that is avoidable.

- [x] **Step 2: Add a failing series metadata test**

Require the OPF metadata to contain exactly one `meta[property="belongs-to-collection"]` with text `Arxiv Series` and one `meta[property="collection-type"]` refining its ID with text `series`. Also assert `dc:title` and `dc:creator` retain the paper metadata.

- [x] **Step 3: Run both tests and verify current output fails**

Run:

```bash
python3 -m unittest -v \
  tests.test_host.HostTests.test_convert_source_has_direct_cover_toc_abstract_order \
  tests.test_host.HostTests.test_convert_source_adds_arxiv_series_metadata
```

Expected: FAIL because Pandoc still creates `title_page.xhtml`, uses the paper title as the nav heading, and emits no series metadata.

- [x] **Step 4: Change Pandoc front-matter options**

Add these arguments to `base`:

```python
"--epub-title-page=false",
"--metadata=toc-title:Table of Contents",
```

Do not remove title, author, or identifier package metadata.

- [x] **Step 5: Add exact EPUB 3 series metadata during finalization**

Find the OPF `<metadata>` element, remove any preexisting `belongs-to-collection` entry with the same ID, and append:

```xml
<meta property="belongs-to-collection" id="arxiv-series">Arxiv Series</meta>
<meta refines="#arxiv-series" property="collection-type">series</meta>
```

- [x] **Step 6: Extend strict front-matter and series validation**

When `require_front_matter=True`, require the first spine document to be the cover, the second to be the manifest `nav` document, no spine document to contain an EPUB titlepage section, and—when `require_abstract=True`—the next non-nav body document to begin with Abstract. Require the nav heading to equal `Table of Contents`.

When `require_series` is set, require the exact collection name and `collection-type=series` refinement.

- [x] **Step 7: Run the Task 3 tests and full regression suite**

Run:

```bash
python3 -m unittest -v \
  tests.test_host.HostTests.test_convert_source_has_direct_cover_toc_abstract_order \
  tests.test_host.HostTests.test_convert_source_adds_arxiv_series_metadata
python3 -m unittest -v
```

Expected: all tests PASS.

---

### Task 4: Real-paper regeneration, installation, and final audit

**Files:**
- Modify: `README.md`
- Modify: installed host through `install.sh`
- Create: `/tmp/arxiv-kindle-citation-review/2606.19868-fixed.epub`
- Do not modify or send: the existing EPUB under `~/Downloads/Arxiv to Kindle/`

**Interfaces:**
- Consumes: final `convert_source` and strict `validate_epub`
- Produces: one inspectable fixed EPUB and an updated installed native host

- [x] **Step 1: Update documentation**

Document visible linked `.bbl` citations, strict citation failure behavior, the direct cover/contents/abstract order, and experimental `Arxiv Series` metadata with the warning that Send to Kindle may ignore personal-document series fields.

- [x] **Step 2: Re-extract the original arXiv `2606.19868` archive and convert once from clean source**

Write the output to `/tmp/arxiv-kindle-citation-review/2606.19868-fixed.epub`. Call `convert_source` directly; do not call `process_request` or `send_with_mail`.

- [x] **Step 3: Run the original red-capable EPUB diagnostic against the fixed file**

Require all of the following in one unattended check:

- citation occurrence count is 193;
- empty citation count is zero;
- every citation has a local link whose fragment exists;
- a References heading and compiled entries are present;
- spine begins cover, nav, Abstract with no title page;
- nav heading is `Table of Contents`;
- `Arxiv Series` metadata and its `series` refinement are present;
- strict cover, abstract, front-matter, citation, series, package, media, and local-link validation passes.

- [x] **Step 4: Revalidate the other two real-paper fixtures**

Convert clean copies of arXiv `2602.03545` and `2601.10387` with the final implementation. Run strict cover, abstract, front-matter, series, and package/link validation; require citation validation whenever source citation commands exist.

- [x] **Step 5: Run all final automated checks**

Run:

```bash
python3 -m unittest -v
python3 -m py_compile native/host.py tests/test_host.py
bash -n install.sh
node --check extension/popup.js
python3 -m json.tool extension/manifest.json
rg -n "\[DEBUG-" .
```

Expected: all tests and syntax checks exit zero; debug scan has no matches.

- [x] **Step 6: Reinstall and compare the native host**

Reuse the installed native-message manifest's existing extension ID with `./install.sh`. Compile the installed host, then compare it with `native/host.py` after excluding only their first shebang lines. Require no other difference.

- [x] **Step 7: Final requirement-by-requirement audit**

Re-read the approved design, inspect the fixed EPUB's OPF, spine, nav, citations, References content, local targets, cover dimensions, and series fields, and report separately what is verified locally versus what remains downstream-dependent. Do not send email and do not claim that Kindle honors the experimental series field without a new real delivery.
