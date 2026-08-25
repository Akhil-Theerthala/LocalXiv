# Kindle-Compatible Cover and Abstract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate the approved Essential C2 cover as a verified 1200 x 1600 PNG, package it as the EPUB cover, and prove the abstract appears before the first numbered paper section without regressing document fidelity.

**Architecture:** Keep the existing single-file Python native host and standard-library test suite. Generate a temporary padded SVG render canvas, rasterize it with macOS Quick Look, crop it with `sips` to the exact portrait dimensions, validate its PNG header, and pass it to Pandoc. Extend EPUB validation with optional cover and abstract-order invariants while retaining all existing package/link checks.

**Tech Stack:** Python 3 standard library, Pandoc EPUB3, `/usr/bin/qlmanage`, `/usr/bin/sips`, `unittest`, SVG, PNG, EPUB/ZIP/XML.

## Global Constraints

- The cover contains exactly the full arXiv identifier and complete title as metadata text.
- Do not add authors, categories, footers, issue markers, generic masthead text, generated illustrations, or paper-derived images.
- Final cover size is exactly 1200 x 1600 pixels and its EPUB media type is `image/png`.
- Preserve the abstract and abstract footnotes before the first numbered section.
- Preserve source order, structure, figures, tables, citations, equations, and every valid local link.
- Use no new Python package, image library, hosted service, daemon, or credential.
- Bound every external renderer invocation with a 30-second timeout.
- Do not initialize Git or add commit steps: this directory is not a Git repository.

---

### Task 1: Approved cover layout and native PNG renderer

**Files:**
- Modify: `native/host.py` (`write_cover` and adjacent cover helpers)
- Modify: `tests/test_host.py` (cover unit and renderer tests)

**Interfaces:**
- Consumes: `PaperMetadata(title: str, authors: str, arxiv_id: str)`
- Produces: `_cover_title_layout(title: str) -> tuple[int, list[str], int]`
- Produces: `write_cover(metadata: PaperMetadata, path: Path) -> None`
- Produces: `rasterize_cover(svg: Path, png: Path, *, qlmanage: str = "/usr/bin/qlmanage", sips: str = "/usr/bin/sips") -> None`
- Produces: `_png_dimensions(path: Path) -> tuple[int, int]`

- [ ] **Step 1: Replace the old cover assertion with failing Essential C2 layout tests**

Add tests that parse the SVG as XML, concatenate every `<text>` node, and require the approved content contract:

```python
def test_cover_contains_only_identifier_and_complete_title(self):
    cover = self.root / "cover.svg"
    metadata = PaperMetadata("A & B", "X < Y", "2401.01234")
    write_cover(metadata, cover)
    root = ElementTree.fromstring(cover.read_bytes())
    text = " ".join("".join(node.itertext()) for node in root.iter() if node.tag.endswith("text"))
    self.assertIn("A & B", text)
    self.assertIn("arXiv 2401.01234", text)
    self.assertNotIn("X < Y", text)
    self.assertNotIn("ARXIV READER", text)
    self.assertNotIn("Authors", text)
    self.assertNotIn("Machine learning", text)
```

Add a long-title test that joins the returned lines and proves no text was dropped:

```python
def test_cover_layout_preserves_long_title_without_overflow(self):
    title = " ".join(f"word{index}" for index in range(80))
    size, lines, top = _cover_title_layout(title)
    self.assertEqual(" ".join(lines), title)
    self.assertGreaterEqual(size, 42)
    self.assertGreaterEqual(top, 190)
    self.assertLessEqual(top + len(lines) * round(size * 1.18) + 40, 1510)
```

- [ ] **Step 2: Run the focused tests and verify the old implementation fails**

Run:

```bash
python3 -m unittest -v \
  tests.test_host.HostTests.test_cover_contains_only_identifier_and_complete_title \
  tests.test_host.HostTests.test_cover_layout_preserves_long_title_without_overflow
```

Expected: FAIL because `_cover_title_layout` does not exist and `write_cover` still includes authors and bottom metadata.

- [ ] **Step 3: Implement the bounded title fitter and Essential C2 SVG**

Implement a pure layout helper that tries font sizes `(84, 78, 72, 66, 60, 54, 48, 42)`. For each size, compute a conservative line width from the 1000-pixel title field, wrap without truncation, and accept only a layout whose estimated width and total line height fit. Raise `ConversionError("Paper title is too long to fit on the cover.")` if none fit.

Generate a 1600 x 1600 temporary render canvas containing a centered 1200 x 1600 portrait at `x=200`. Inside the portrait, emit only:

```xml
<rect x="200" width="1200" height="1600" fill="#f2eee4"/>
<rect x="200" width="36" height="1600" fill="#ae4333"/>
<rect x="236" width="1164" height="190" fill="#111111"/>
<text x="300" y="116" fill="#ffffff" font-family="monospace">arXiv ...</text>
<!-- dynamically fitted title tspans in the centered main field -->
<rect x="300" ... fill="#171717"/>
<rect ... fill="#ae4333"/>
```

Escape all metadata with `html.escape`. Keep the padded canvas temporary; only the cropped PNG is passed to Pandoc.

- [ ] **Step 4: Run the layout tests and verify they pass**

Run the focused command from Step 2.

Expected: PASS.

- [ ] **Step 5: Add a failing real-render PNG test**

Add a macOS-only test guarded by the presence of `/usr/bin/qlmanage` and `/usr/bin/sips`:

```python
def test_rasterize_cover_produces_exact_png(self):
    svg = self.root / "cover.svg"
    png = self.root / "cover.png"
    write_cover(PaperMetadata("A Long but Complete Paper Title", "Ignored", "2401.01234"), svg)
    rasterize_cover(svg, png)
    self.assertEqual(_png_dimensions(png), (1200, 1600))
    self.assertEqual(png.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
```

- [ ] **Step 6: Run the renderer test and verify it fails**

Run:

```bash
python3 -m unittest -v tests.test_host.HostTests.test_rasterize_cover_produces_exact_png
```

Expected: FAIL because `rasterize_cover` and `_png_dimensions` do not exist.

- [ ] **Step 7: Implement PNG rasterization and header validation**

Implement `_png_dimensions` with the standard PNG signature and IHDR bytes:

```python
def _png_dimensions(path: Path) -> tuple[int, int]:
    header = path.read_bytes()[:24]
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise ConversionError("Cover renderer did not produce a valid PNG.")
    return struct.unpack(">II", header[16:24])
```

`rasterize_cover` must:

1. run `[qlmanage, "-t", "-s", "1600", "-o", str(svg.parent), str(svg)]` with `timeout=30`;
2. copy `<svg-name>.png` to the requested PNG path;
3. run `[sips, "--cropToHeightWidth", "1600", "1200", str(png)]` with `timeout=30`;
4. require `_png_dimensions(png) == (1200, 1600)`;
5. translate timeout, nonzero exit, and missing output into concise `ConversionError` messages.

- [ ] **Step 8: Run the renderer test and the full suite**

Run:

```bash
python3 -m unittest -v tests.test_host.HostTests.test_rasterize_cover_produces_exact_png
python3 -m unittest -v
```

Expected: renderer PASS; full suite PASS.

---

### Task 2: Package the PNG cover and validate abstract ordering

**Files:**
- Modify: `native/host.py` (`convert_source`, `validate_epub`)
- Modify: `tests/test_host.py` (EPUB fixture, conversion, and abstract tests)

**Interfaces:**
- Consumes: `write_cover`, `rasterize_cover`, and the existing `prepare_abstracts`
- Changes: `validate_epub(path: Path, *, require_png_cover: bool = False, require_abstract: bool = False) -> None`
- Produces: `_spine_documents(book: zipfile.ZipFile, package: ElementTree.Element) -> list[str]`
- Produces: `_validate_abstract_order(book: zipfile.ZipFile, spine_documents: list[str]) -> None`

- [ ] **Step 1: Add failing PNG-cover package tests**

Extend the EPUB fixture helper so it can include:

```xml
<item id="cover" href="media/cover.png" media-type="image/png" properties="cover-image"/>
```

and `EPUB/media/cover.png`. Add tests requiring `validate_epub(..., require_png_cover=True)` to accept this fixture and reject SVG, JPEG, missing cover content, or a cover item without `cover-image`.

- [ ] **Step 2: Add failing abstract-order tests**

Create two-spine fixtures with a title page, Abstract heading/content, and `1 Introduction`. Require the good order to pass and these cases to fail:

- no Abstract heading;
- Abstract after `1 Introduction`;
- an empty Abstract section.

Use `validate_epub(..., require_abstract=True)` so papers without source abstracts remain valid under the default call.

- [ ] **Step 3: Run the new validation tests and verify they fail**

Run:

```bash
python3 -m unittest -v \
  tests.test_host.HostTests.test_validate_epub_requires_png_cover \
  tests.test_host.HostTests.test_validate_epub_requires_abstract_before_first_section
```

Expected: FAIL because the keyword arguments and validations do not exist.

- [ ] **Step 4: Implement optional cover and abstract invariants**

Reuse the manifest and spine maps already built by `validate_epub`; do not parse the package twice. When `require_png_cover=True`, require exactly one manifest item whose whitespace-separated `properties` contains `cover-image`, whose `media-type` is `image/png`, and whose resolved path exists in the archive.

When `require_abstract=True`, traverse headings and visible paragraph text in spine order. Ignore the title-page `<h1 class="title">`; require the first paper-level heading to normalize to `Abstract`, require nonempty text after that heading, and require it to precede the first numbered section heading.

- [ ] **Step 5: Run the validation tests and full suite**

Run the focused command from Step 3, then:

```bash
python3 -m unittest -v
```

Expected: all tests PASS.

- [ ] **Step 6: Add a failing conversion integration assertion**

Update the existing abstract-footnote conversion test to inspect spine order and call:

```python
validate_epub(output, require_png_cover=True, require_abstract=True)
```

Also inspect `content.opf` and assert its `cover-image` item uses `image/png`.

- [ ] **Step 7: Wire cover rasterization and requirements into `convert_source`**

Capture the count from `prepare_abstracts(source_dir)`. Generate `.arxiv-kindle-cover.svg`, rasterize it to `.arxiv-kindle-cover.png`, and replace the Pandoc argument with:

```python
f"--epub-cover-image={cover_png}"
```

After link repair, call:

```python
validate_epub(
    output,
    require_png_cover=True,
    require_abstract=abstract_count > 0 or legacy_abstract_count > 0,
)
```

Adjust `prepare_latex_209_front_matter` to return both its rewrite count and whether it inserted a legacy abstract, or add a narrow helper that detects the inserted `\section*{Abstract}` marker before Pandoc.

- [ ] **Step 8: Run the integration test and full regression suite**

Run:

```bash
python3 -m unittest -v tests.test_host.HostTests.test_convert_source_preserves_abstract_footnotes
python3 -m unittest -v
python3 -m py_compile native/host.py tests/test_host.py
bash -n install.sh
node --check extension/popup.js
```

Expected: every command exits zero.

---

### Task 3: Documentation and real-paper visual verification

**Files:**
- Modify: `README.md` (cover and abstract behavior)
- Create: `/tmp/arxiv-kindle-cover-review/` outputs during verification only
- Do not modify: `~/Developer/XivEpub`

**Interfaces:**
- Consumes: `convert_source`, `validate_epub`, `_png_dimensions`
- Produces: two validated EPUBs and extracted full-size/grayscale thumbnail cover images for inspection

- [ ] **Step 1: Update user-facing documentation**

Replace the old "plain SVG" sentence with the exact behavior: Essential C2 title-and-identifier template, verified PNG packaging, abstract before numbered sections, and explicit failure when the cover cannot be rendered.

- [ ] **Step 2: Convert the long-title paper used in the Kindle screenshot flow**

Run the native converter for arXiv `2606.19868` with delivery disabled or through `convert_source` directly into `/tmp/arxiv-kindle-cover-review/long-title.epub`. Validate it with both strict flags.

- [ ] **Step 3: Convert the verified XivEpub reference paper**

Use the existing local XivEpub sample/source when available, otherwise its known arXiv ID `2602.03545`, and write `/tmp/arxiv-kindle-cover-review/xivepub-sample.epub`. Validate strict cover and abstract invariants.

- [ ] **Step 4: Extract and inspect both covers**

Extract each manifest-declared cover PNG. Verify its header and dimensions with `_png_dimensions`, inspect it at original resolution, and create a grayscale thumbnail with:

```bash
sips -s format png -s formatOptions normal -z 320 240 cover.png --out cover-thumb.png
sips -s saturation 0 cover-thumb.png
```

Inspect both full-size and thumbnail images. Reject clipping, overlap, missing words, weak grayscale hierarchy, or unexpected metadata.

- [ ] **Step 5: Inspect abstract and first-section ordering in both EPUBs**

List spine documents and print normalized headings plus the first abstract paragraph. Confirm title page -> Abstract -> first numbered section and compare the reference paper's abstract text with its verified XivEpub EPUB.

- [ ] **Step 6: Run the final completion audit**

Run:

```bash
python3 -m unittest -v
python3 -m py_compile native/host.py tests/test_host.py
bash -n install.sh
node --check extension/popup.js
```

Then inspect EPUB manifests, cover media types, cover image dimensions, abstract order, package/link validation results, and generated images for both real papers. Do not claim completion from the regression suite alone.
