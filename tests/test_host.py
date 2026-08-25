import gzip
import io
import json
import subprocess
import struct
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree

import native.host as host
from native.host import (
    _convert_graphic_to_png,
    _pandoc_error_detail,
    _repair_cross_file_fragments,
    ConversionError,
    PaperMetadata,
    convert_source,
    extract_source,
    extract_metadata,
    find_root_tex,
    parse_arxiv_url,
    prepare_graphics,
    process_request,
    read_message,
    safe_extract,
    validate_epub,
    validate_kindle_email,
    write_message,
    write_cover,
)


class HostTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def make_tar(self, files: dict[str, bytes], *, link: str | None = None) -> Path:
        archive = self.root / "source.tar.gz"
        with tarfile.open(archive, "w:gz") as bundle:
            for name, content in files.items():
                info = tarfile.TarInfo(name)
                info.size = len(content)
                bundle.addfile(info, io.BytesIO(content))
            if link:
                info = tarfile.TarInfo("linked.tex")
                info.type = tarfile.SYMTYPE
                info.linkname = link
                bundle.addfile(info)
        return archive

    def make_epub(
        self,
        *,
        href: str,
        chapter_id: str,
        extra_body: str = "",
        link_class: str = "",
    ) -> Path:
        epub = self.root / "fixture.epub"
        container = b'''<?xml version="1.0"?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
  <rootfiles><rootfile full-path="EPUB/content.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>'''
        package = b'''<?xml version="1.0"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Fixture</dc:title></metadata>
  <manifest><item id="chapter" href="chapter.xhtml" media-type="application/xhtml+xml"/></manifest>
  <spine><itemref idref="chapter"/></spine>
</package>'''
        class_attribute = f' class="{link_class}"' if link_class else ""
        chapter = f'''<?xml version="1.0"?>
<html xmlns="http://www.w3.org/1999/xhtml"><body>
  <p id="{chapter_id}">Target</p><a href="{href}"{class_attribute}>link</a>{extra_body}
</body></html>'''.encode()
        with zipfile.ZipFile(epub, "w") as book:
            book.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
            book.writestr("META-INF/container.xml", container)
            book.writestr("EPUB/content.opf", package)
            book.writestr("EPUB/chapter.xhtml", chapter)
        return epub

    def make_strict_epub(
        self,
        documents: list[tuple[str, str, str]],
        *,
        cover_href: str = "media/cover.png",
        cover_media_type: str = "image/png",
        cover_properties: str = "cover-image",
        include_cover_file: bool = True,
        document_properties: dict[str, str] | None = None,
        metadata_extra: str = "",
    ) -> Path:
        epub = self.root / "strict-fixture.epub"
        container = b'''<?xml version="1.0"?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
  <rootfiles><rootfile full-path="EPUB/content.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>'''
        cover_property = (
            f' properties="{cover_properties}"' if cover_properties else ""
        )
        manifest = [
            f'<item id="cover" href="{cover_href}" media-type="{cover_media_type}"{cover_property}/>'
        ]
        spine = []
        for item_id, filename, _body in documents:
            properties = (document_properties or {}).get(item_id, "")
            properties_attribute = f' properties="{properties}"' if properties else ""
            manifest.append(
                f'<item id="{item_id}" href="{filename}" '
                f'media-type="application/xhtml+xml"{properties_attribute}/>'
            )
            spine.append(f'<itemref idref="{item_id}"/>')
        package = f'''<?xml version="1.0"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Fixture</dc:title>{metadata_extra}</metadata>
  <manifest>{"".join(manifest)}</manifest>
  <spine>{"".join(spine)}</spine>
</package>'''.encode()
        with zipfile.ZipFile(epub, "w") as book:
            book.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
            book.writestr("META-INF/container.xml", container)
            book.writestr("EPUB/content.opf", package)
            for _item_id, filename, body in documents:
                book.writestr(
                    f"EPUB/{filename}",
                    f'''<?xml version="1.0"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><body>{body}</body></html>''',
                )
            if include_cover_file:
                book.writestr(f"EPUB/{cover_href}", b"cover bytes")
        return epub

    def test_parse_arxiv_url_accepts_modern_versioned_and_legacy_ids(self):
        cases = {
            "https://arxiv.org/abs/2401.01234": "2401.01234",
            "https://www.arxiv.org/abs/2401.01234v2": "2401.01234v2",
            "https://arxiv.org/abs/hep-th/9901001": "hep-th/9901001",
            "https://arxiv.org/abs/math.GT/0501234v3?ref=reader": "math.GT/0501234v3",
        }
        for url, expected in cases.items():
            with self.subTest(url=url):
                self.assertEqual(parse_arxiv_url(url), expected)

    def test_parse_arxiv_url_rejects_non_abstract_or_untrusted_urls(self):
        urls = [
            "https://arxiv.org/pdf/2401.01234",
            "https://example.com/abs/2401.01234",
            "https://arxiv.org/abs/../../etc/passwd",
            "https://arxiv.org/abs/2401.12",
            "javascript:alert(1)",
        ]
        for url in urls:
            with self.subTest(url=url), self.assertRaises(ConversionError):
                parse_arxiv_url(url)

    def test_safe_extract_writes_regular_files(self):
        archive = self.make_tar({"paper/main.tex": b"content", "paper/fig.png": b"png"})
        destination = self.root / "out"
        safe_extract(archive, destination)
        self.assertEqual((destination / "paper/main.tex").read_bytes(), b"content")
        self.assertEqual((destination / "paper/fig.png").read_bytes(), b"png")

    def test_safe_extract_accepts_legacy_current_directory_entry(self):
        archive = self.root / "legacy-source.tar"
        with tarfile.open(archive, "w") as bundle:
            directory = tarfile.TarInfo("./")
            directory.type = tarfile.DIRTYPE
            bundle.addfile(directory)
            content = b"legacy"
            paper = tarfile.TarInfo("./main.tex")
            paper.size = len(content)
            bundle.addfile(paper, io.BytesIO(content))
        destination = self.root / "legacy-out"
        safe_extract(archive, destination)
        self.assertEqual((destination / "main.tex").read_bytes(), content)

    def test_safe_extract_rejects_traversal_absolute_paths_and_links(self):
        for name in ("../escape.tex", "/tmp/escape.tex"):
            archive = self.make_tar({name: b"bad"})
            with self.subTest(name=name), self.assertRaises(ConversionError):
                safe_extract(archive, self.root / f"out-{len(name)}")

        archive = self.make_tar({}, link="../escape.tex")
        with self.assertRaises(ConversionError):
            safe_extract(archive, self.root / "out-link")

    def test_safe_extract_enforces_expanded_size_limit(self):
        archive = self.make_tar({"large.tex": b"12345"})
        with self.assertRaises(ConversionError):
            safe_extract(archive, self.root / "out-large", max_bytes=4)

    def test_find_root_tex_prefers_document_that_includes_another_candidate(self):
        source = self.root / "source"
        source.mkdir()
        (source / "main.tex").write_text(
            "\\documentclass{article}\n\\begin{document}\n\\input{appendix}\n\\end{document}"
        )
        (source / "appendix.tex").write_text(
            "\\documentclass{article}\n\\begin{document}\nAppendix\n\\end{document}"
        )
        self.assertEqual(find_root_tex(source), source / "main.tex")

    def test_find_root_tex_accepts_latex_209_documentstyle(self):
        source = self.root / "legacy-source"
        source.mkdir()
        legacy = source / "paper.tex"
        legacy.write_text(
            "\\documentstyle[preprint]{article}\n"
            "\\begin{document}\nLegacy paper.\n\\end{document}"
        )
        self.assertEqual(find_root_tex(source), legacy)

    def test_find_root_tex_rejects_no_root_and_ambiguous_roots(self):
        empty = self.root / "empty"
        empty.mkdir()
        (empty / "fragment.tex").write_text("fragment")
        with self.assertRaises(ConversionError):
            find_root_tex(empty)

        ambiguous = self.root / "ambiguous"
        ambiguous.mkdir()
        body = "\\documentclass{article}\n\\begin{document}\nSame\n\\end{document}"
        (ambiguous / "one.tex").write_text(body)
        (ambiguous / "two.tex").write_text(body)
        with self.assertRaises(ConversionError):
            find_root_tex(ambiguous)

    def test_extract_metadata_handles_nested_braces_and_tex_separators(self):
        tex = r"""
        \title{% formatting note that must not become title text
        A {Careful} Paper\\on \textbf{Links}}
        \author{Ada Lovelace \and Alan Turing\\Grace Hopper}
        """
        self.assertEqual(
            extract_metadata(tex, "2401.01234"),
            PaperMetadata(
                title="A Careful Paper on Links",
                authors="Ada Lovelace, Alan Turing, Grace Hopper",
                arxiv_id="2401.01234",
            ),
        )

    def test_extract_metadata_has_stable_fallbacks(self):
        self.assertEqual(
            extract_metadata("\\begin{document}", "2401.01234"),
            PaperMetadata(
                title="arXiv 2401.01234",
                authors="Unknown authors",
                arxiv_id="2401.01234",
            ),
        )

    def test_extract_metadata_ignores_commented_placeholders(self):
        metadata = extract_metadata(
            "% Template says \\title{} and \\author{} here.\n"
            "\\title{The Real Paper Title}\n"
            "\\author{Ada Example}",
            "2401.01234",
        )
        self.assertEqual(metadata.title, "The Real Paper Title")
        self.assertEqual(metadata.authors, "Ada Example")

    def test_prepare_compiled_bibliography_preserves_labels_and_inserts_references(self):
        source = self.root / "compiled-bibliography-source"
        source.mkdir()
        root = source / "main.tex"
        root.write_text(
            r"""\documentclass{article}
\begin{document}
Claim~\cite{alpha,beta}.
\bibliographystyle{plainnat}
\bibliography{references}
\end{document}
"""
        )
        (source / "main.bbl").write_text(
            r"""\begin{thebibliography}{2}
\bibitem[Alpha(2024)]{alpha} Alpha entry.
\bibitem{beta} Beta entry.
\end{thebibliography}
"""
        )

        entries = host.prepare_compiled_bibliography(root)

        self.assertEqual(
            [(entry.key, entry.label) for entry in entries],
            [("alpha", "Alpha(2024)"), ("beta", "2")],
        )
        rewritten = root.read_text()
        self.assertNotIn(r"\bibliographystyle", rewritten)
        self.assertNotIn(r"\bibliography{references}", rewritten)
        self.assertIn(r"\section*{References}", rewritten)
        self.assertIn(r"\input{main.bbl}", rewritten)
        self.assertLess(rewritten.index(r"\section*{References}"), rewritten.index(r"\end{document}"))

    def test_prepare_compiled_bibliography_rejects_duplicate_keys(self):
        source = self.root / "duplicate-bibliography"
        source.mkdir()
        root = source / "main.tex"
        root.write_text(r"\begin{document}\bibliography{x}\end{document}")
        (source / "main.bbl").write_text(
            r"""\begin{thebibliography}{2}
\bibitem{same} First.
\bibitem{same} Second.
\end{thebibliography}
"""
        )
        with self.assertRaisesRegex(ConversionError, "duplicate bibliography key"):
            host.prepare_compiled_bibliography(root)

    def test_prepare_compiled_bibliography_leaves_source_without_bbl_unchanged(self):
        root = self.root / "main.tex"
        original = r"\begin{document}No citations.\end{document}"
        root.write_text(original)

        self.assertEqual(host.prepare_compiled_bibliography(root), [])
        self.assertEqual(root.read_text(), original)

    def test_cover_contains_only_identifier_and_complete_title(self):
        cover = self.root / "cover.svg"
        write_cover(PaperMetadata("A & B", "X < Y", "2401.01234"), cover)
        root = ElementTree.fromstring(cover.read_bytes())
        text = " ".join(
            "".join(node.itertext())
            for node in root.iter()
            if node.tag.endswith("text")
        )
        self.assertIn("A & B", text)
        self.assertIn("arXiv 2401.01234", text)
        self.assertNotIn("X < Y", text)
        self.assertNotIn("ARXIV READER", text)
        self.assertNotIn("Authors", text)
        self.assertNotIn("Machine learning", text)

    def test_cover_layout_preserves_long_title_without_overflow(self):
        layout = getattr(host, "_cover_title_layout", None)
        self.assertIsNotNone(layout, "cover title fitter is missing")
        title = " ".join(f"word{index}" for index in range(80))
        size, lines, top = layout(title)
        line_height = round(size * 1.18)
        self.assertEqual(" ".join(lines), title)
        self.assertGreaterEqual(size, 42)
        self.assertGreaterEqual(top, 190)
        self.assertLessEqual(top + len(lines) * line_height + 40, 1510)

    @unittest.skipUnless(
        Path("/usr/bin/qlmanage").exists() and Path("/usr/bin/sips").exists(),
        "macOS cover renderers are unavailable",
    )
    def test_rasterize_cover_produces_exact_png(self):
        rasterize = getattr(host, "rasterize_cover", None)
        dimensions = getattr(host, "_png_dimensions", None)
        self.assertIsNotNone(rasterize, "cover rasterizer is missing")
        self.assertIsNotNone(dimensions, "PNG validator is missing")
        svg = self.root / "cover.svg"
        png = self.root / "cover.png"
        write_cover(
            PaperMetadata("A Long but Complete Paper Title", "Ignored", "2401.01234"),
            svg,
        )
        rasterize(svg, png)
        self.assertEqual(dimensions(png), (1200, 1600))
        self.assertEqual(png.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")

    def test_validate_epub_accepts_resolved_local_fragment(self):
        validate_epub(self.make_epub(href="chapter.xhtml#present", chapter_id="present"))

    def test_validate_epub_rejects_missing_file_or_fragment(self):
        for href in ("missing.xhtml", "chapter.xhtml#missing"):
            with self.subTest(href=href), self.assertRaises(ConversionError):
                validate_epub(self.make_epub(href=href, chapter_id="present"))

    def test_validate_epub_requires_png_cover(self):
        documents = [("chapter", "chapter.xhtml", "<h1>1 Introduction</h1><p>Body.</p>")]
        try:
            validate_epub(self.make_strict_epub(documents), require_png_cover=True)
        except TypeError as error:
            self.fail(f"PNG cover validation is missing: {error}")

        invalid = (
            {"cover_href": "media/cover.svg", "cover_media_type": "image/svg+xml"},
            {"cover_href": "media/cover.jpg", "cover_media_type": "image/jpeg"},
            {"cover_properties": ""},
            {"include_cover_file": False},
        )
        for options in invalid:
            with self.subTest(options=options), self.assertRaises(ConversionError):
                validate_epub(
                    self.make_strict_epub(documents, **options),
                    require_png_cover=True,
                )

    def test_validate_epub_requires_abstract_before_first_section(self):
        title = ("title", "title.xhtml", '<h1 class="title">Paper Title</h1>')
        abstract = (
            "abstract",
            "abstract.xhtml",
            '<h1 class="unnumbered">Abstract</h1><p>Complete abstract text.</p>',
        )
        introduction = (
            "intro",
            "intro.xhtml",
            '<h1><span class="header-section-number">1</span> Introduction</h1><p>Body.</p>',
        )
        try:
            validate_epub(
                self.make_strict_epub([title, abstract, introduction]),
                require_abstract=True,
            )
        except TypeError as error:
            self.fail(f"abstract order validation is missing: {error}")

        invalid_documents = (
            [title, introduction],
            [title, introduction, abstract],
            [
                title,
                ("abstract", "abstract.xhtml", '<h1 class="unnumbered">Abstract</h1>'),
                introduction,
            ],
        )
        for documents in invalid_documents:
            with self.subTest(documents=documents), self.assertRaises(ConversionError):
                validate_epub(
                    self.make_strict_epub(documents),
                    require_abstract=True,
                )

    def test_validate_epub_requires_visible_linked_citations(self):
        valid_documents = [
            (
                "body",
                "body.xhtml",
                '<h1>1 Body</h1><p>Claim <span class="citation" data-cites="alpha">'
                '[<a href="references.xhtml#ref-alpha">1</a>]</span>.</p>',
            ),
            (
                "references",
                "references.xhtml",
                '<h1 class="unnumbered">References</h1>'
                '<p id="ref-alpha">Alpha reference.</p>',
            ),
        ]
        try:
            validate_epub(
                self.make_strict_epub(valid_documents),
                require_citations=True,
            )
        except ConversionError as error:
            self.fail(f"valid citation EPUB was rejected: {error}")

        invalid_documents = [
            [
                (
                    "body",
                    "body.xhtml",
                    '<h1>1 Body</h1><p><span class="citation" data-cites="alpha"></span></p>',
                ),
                valid_documents[1],
            ],
            [
                (
                    "body",
                    "body.xhtml",
                    '<h1>1 Body</h1><p><span class="citation" data-cites="alpha">[1]</span></p>',
                ),
                valid_documents[1],
            ],
            [
                (
                    "body",
                    "body.xhtml",
                    '<h1>1 Body</h1><p><span class="citation" data-cites="alpha">'
                    '[<a href="references.xhtml#ref-missing">1</a>]</span></p>',
                ),
                valid_documents[1],
            ],
            [valid_documents[0]],
        ]
        for documents in invalid_documents:
            with self.subTest(documents=documents), self.assertRaises(ConversionError):
                validate_epub(
                    self.make_strict_epub(documents),
                    require_citations=True,
                )

    def test_validate_epub_requires_direct_front_matter_and_series(self):
        cover = (
            "coverdoc",
            "cover.xhtml",
            '<section epub:type="cover"><img src="media/cover.png" alt="Cover"/></section>',
        )
        nav = (
            "nav",
            "nav.xhtml",
            '<nav epub:type="toc"><h1>Table of Contents</h1>'
            '<ol><li><a href="abstract.xhtml#abstract">Abstract</a></li></ol></nav>',
        )
        abstract = (
            "abstract",
            "abstract.xhtml",
            '<section id="abstract"><h1>Abstract</h1><p>Complete abstract.</p></section>',
        )
        metadata = (
            '<meta property="belongs-to-collection" id="arxiv-series">Arxiv Series</meta>'
            '<meta refines="#arxiv-series" property="collection-type">series</meta>'
        )
        valid = self.make_strict_epub(
            [cover, nav, abstract],
            document_properties={"nav": "nav"},
            metadata_extra=metadata,
        )
        try:
            validate_epub(
                valid,
                require_abstract=True,
                require_front_matter=True,
                require_series="Arxiv Series",
            )
        except ConversionError as error:
            self.fail(f"valid front matter and series were rejected: {error}")

        invalid_cases = [
            ([cover, abstract, nav], metadata),
            ([cover, nav, abstract], metadata.replace("Arxiv Series", "Different Series")),
            (
                [
                    cover,
                    (
                        "title",
                        "title.xhtml",
                        '<section epub:type="titlepage"><h1 class="title">Paper</h1></section>',
                    ),
                    nav,
                    abstract,
                ],
                metadata,
            ),
        ]
        for documents, invalid_metadata in invalid_cases:
            epub = self.make_strict_epub(
                documents,
                document_properties={"nav": "nav"},
                metadata_extra=invalid_metadata,
            )
            with self.subTest(documents=documents), self.assertRaises(ConversionError):
                validate_epub(
                    epub,
                    require_abstract=True,
                    require_front_matter=True,
                    require_series="Arxiv Series",
                )

    def test_repair_promotes_labels_from_fallback_math_spans(self):
        epub = self.make_epub(
            href="#levelmatch",
            chapter_id="unrelated",
            extra_body=(
                '<span class="math display">'
                r"$$K^2 \leq 2.\label{levelmatch}"
                r"Q = 0.\label{last}$$"
                '</span><a href="#last">last</a>'
            ),
        )
        with self.assertRaises(ConversionError):
            validate_epub(epub)
        _repair_cross_file_fragments(epub)
        validate_epub(epub)
        with zipfile.ZipFile(epub) as book:
            chapter = book.read("EPUB/chapter.xhtml").decode("utf-8")
        self.assertIn('id="levelmatch"', chapter)
        self.assertIn('id="last"', chapter)

    def test_repair_promotes_bare_web_domains_to_https(self):
        epub = self.make_epub(
            href="paperswithcode.com/datasets",
            chapter_id="present",
            link_class="uri",
        )
        with self.assertRaises(ConversionError):
            validate_epub(epub)
        _repair_cross_file_fragments(epub)
        try:
            validate_epub(epub)
        except ConversionError as error:
            self.fail(f"bare web domain was not repaired: {error}")
        with zipfile.ZipFile(epub) as book:
            chapter = book.read("EPUB/chapter.xhtml").decode("utf-8")
        self.assertIn('href="https://paperswithcode.com/datasets"', chapter)

    @unittest.skipUnless(Path("/opt/homebrew/bin/pandoc").exists(), "Pandoc is not installed")
    def test_convert_source_preserves_order_media_and_cross_references(self):
        source = self.root / "paper"
        source.mkdir()
        (source / "main.tex").write_text(
            r"""\documentclass{article}
\usepackage{graphicx}
\title{Linked Paper}
\author{Ada Author \and Bob Writer}
\begin{document}
\maketitle
\section{First}\label{sec:first}
See Section~\ref{sec:second}, Figure~\ref{fig:one}, and Table~\ref{tab:one}.
\input{body}
\begin{figure}
\includegraphics{figure.svg}
\caption{Figure caption}\label{fig:one}
\end{figure}
\begin{table}
\caption{Table caption}\label{tab:one}
\begin{tabular}{ll}A & B\\1 & 2\end{tabular}
\end{table}
\end{document}
"""
        )
        (source / "body.tex").write_text(
            r"""\section{Second}\label{sec:second}
Second body.
"""
        )
        (source / "figure.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="40" height="20">'
            '<rect width="40" height="20" fill="black"/></svg>'
        )
        output = self.root / "paper.epub"
        convert_source(source, "2401.01234", output, pandoc="/opt/homebrew/bin/pandoc")
        validate_epub(output)
        with zipfile.ZipFile(output) as book:
            content = "\n".join(
                book.read(name).decode("utf-8")
                for name in book.namelist()
                if name.endswith((".xhtml", ".html"))
            )
            names = book.namelist()
            svg_media = "\n".join(
                book.read(name).decode("utf-8") for name in names if name.endswith(".svg")
            )
        self.assertLess(content.index("First"), content.index("Second"))
        self.assertLess(content.index("Second"), content.index("Figure caption"))
        self.assertLess(content.index("Figure caption"), content.index("Table caption"))
        self.assertIn('fill="black"', svg_media)
        self.assertRegex(content, r'href="[^"]*#sec:second"')
        self.assertRegex(content, r'href="[^"]*#fig:one"')
        self.assertRegex(content, r'href="[^"]*#tab:one"')

    @unittest.skipUnless(Path("/opt/homebrew/bin/pandoc").exists(), "Pandoc is not installed")
    def test_convert_source_preserves_compiled_bbl_citations(self):
        source = self.root / "compiled-bibliography"
        source.mkdir()
        (source / "main.tex").write_text(
            r"""\documentclass{article}
\title{Cited Paper}
\author{Ada Author}
\begin{document}
\maketitle
\section{Body}
Claim~\cite{alpha,beta}.
\bibliographystyle{unsrt}
\bibliography{references}
\end{document}
"""
        )
        (source / "main.bbl").write_text(
            r"""\begin{thebibliography}{2}
\bibitem{alpha}
Alpha Author.
\newblock Alpha reference.
\bibitem{beta}
Beta Author.
\newblock Beta reference.
\end{thebibliography}
"""
        )
        output = self.root / "compiled-bibliography.epub"
        convert_source(source, "2401.01234", output, pandoc="/opt/homebrew/bin/pandoc")
        with zipfile.ZipFile(output) as book:
            roots = [
                ElementTree.fromstring(book.read(name))
                for name in book.namelist()
                if name.endswith((".xhtml", ".html"))
            ]
            content = "\n".join(
                book.read(name).decode("utf-8")
                for name in book.namelist()
                if name.endswith((".xhtml", ".html"))
            )
        citations = [
            element
            for root in roots
            for element in root.iter()
            if "citation" in element.attrib.get("class", "").split()
        ]
        self.assertEqual(
            ["".join(citation.itertext()) for citation in citations],
            ["[1, 2]"],
        )
        self.assertIn("Alpha Author", content)
        self.assertIn("Alpha reference", content)
        self.assertIn("Beta Author", content)
        self.assertIn("Beta reference", content)
        self.assertRegex(content, r'href="[^"]*#ref-alpha"')
        self.assertRegex(content, r'id="ref-alpha"')

    @unittest.skipUnless(Path("/opt/homebrew/bin/pandoc").exists(), "Pandoc is not installed")
    def test_convert_source_rejects_citation_missing_from_compiled_bibliography(self):
        source = self.root / "missing-compiled-citation"
        source.mkdir()
        (source / "main.tex").write_text(
            r"""\documentclass{article}
\begin{document}
Claim~\cite{missing}.
\bibliography{references}
\end{document}
"""
        )
        (source / "main.bbl").write_text(
            r"""\begin{thebibliography}{1}
\bibitem{present} Present entry.
\end{thebibliography}
"""
        )
        with self.assertRaisesRegex(ConversionError, "missing citation key: missing"):
            convert_source(
                source,
                "2401.01234",
                self.root / "missing-compiled-citation.epub",
                pandoc="/opt/homebrew/bin/pandoc",
            )

    @unittest.skipUnless(Path("/opt/homebrew/bin/pandoc").exists(), "Pandoc is not installed")
    def test_convert_source_links_citeproc_citations(self):
        source = self.root / "citeproc-bibliography"
        source.mkdir()
        (source / "main.tex").write_text(
            r"""\documentclass{article}
\title{Citeproc Paper}
\begin{document}
\section{Body}
Claim~\citep{alpha,beta}.
\bibliography{references}
\end{document}
"""
        )
        (source / "references.bib").write_text(
            r"""@article{alpha,
  author = {Alpha, Ada},
  title = {Alpha Reference},
  year = {2024}
}
@article{beta,
  author = {Beta, Bob},
  title = {Beta Reference},
  year = {2025}
}
"""
        )
        output = self.root / "citeproc-bibliography.epub"
        convert_source(source, "2401.01234", output, pandoc="/opt/homebrew/bin/pandoc")
        validate_epub(output, require_citations=True)
        with zipfile.ZipFile(output) as book:
            roots = [
                ElementTree.fromstring(book.read(name))
                for name in book.namelist()
                if name.endswith((".xhtml", ".html"))
            ]
        citation = next(
            element
            for root in roots
            for element in root.iter()
            if "citation" in element.attrib.get("class", "").split()
        )
        self.assertIn("Alpha", "".join(citation.itertext()))
        self.assertIn("Beta", "".join(citation.itertext()))
        links = [
            element.attrib["href"]
            for element in citation.iter()
            if element.tag.rsplit("}", 1)[-1] == "a"
        ]
        self.assertEqual(len(links), 1)
        self.assertRegex(links[0], r"[^\s]*#ref-alpha$")

    @unittest.skipUnless(Path("/opt/homebrew/bin/pandoc").exists(), "Pandoc is not installed")
    def test_convert_source_preserves_centered_table_star_label(self):
        source = self.root / "wide-table"
        source.mkdir()
        (source / "main.tex").write_text(
            r"""\documentclass{article}
\begin{document}
See Table~\ref{tab:wide}.
\begin{table*}
\begin{center}
\begin{tabular*}{\textwidth}{lc}
Name & Score\\
Model & 99\\
\end{tabular*}
\caption{Wide results.}
\label{tab:wide}
\end{center}
\end{table*}
\end{document}
"""
        )
        output = self.root / "wide-table.epub"
        convert_source(source, "2401.01234", output, pandoc="/opt/homebrew/bin/pandoc")
        validate_epub(output)
        with zipfile.ZipFile(output) as book:
            content = "\n".join(
                book.read(name).decode("utf-8")
                for name in book.namelist()
                if name.endswith((".xhtml", ".html"))
            )
        self.assertIn('id="tab:wide"', content)
        self.assertRegex(content, r'href="[^"]*#tab:wide"')

    @unittest.skipUnless(Path("/opt/homebrew/bin/pandoc").exists(), "Pandoc is not installed")
    def test_convert_source_preserves_tables_with_custom_column_types(self):
        source = self.root / "custom-columns"
        source.mkdir()
        (source / "main.tex").write_text(
            r"""\documentclass{article}
\usepackage{array}
\begin{document}
\newcolumntype{x}[1]{>{\centering}p{#1pt}}
\newcolumntype{y}{>{\centering}p{16pt}}
\begin{table}
\begin{tabular}{l|x{42}|yy}
Network & Plain & A & B\\
18 layers & 27.94 & 27.88 & 25.03\\
\end{tabular}
\caption{Custom columns.}\label{tab:custom}
\end{table}
See Table~\ref{tab:custom}.
\end{document}
"""
        )
        output = self.root / "custom-columns.epub"
        convert_source(source, "2401.01234", output, pandoc="/opt/homebrew/bin/pandoc")
        validate_epub(output)
        with zipfile.ZipFile(output) as book:
            roots = [
                ElementTree.fromstring(book.read(name))
                for name in book.namelist()
                if name.endswith((".xhtml", ".html"))
            ]
        tables = [
            " ".join("".join(element.itertext()).split())
            for root in roots
            for element in root.iter()
            if element.tag.rsplit("}", 1)[-1] == "table"
        ]
        self.assertEqual(len(tables), 1)
        self.assertIn("18 layers 27.94 27.88 25.03", tables[0])

    @unittest.skipUnless(Path("/opt/homebrew/bin/pandoc").exists(), "Pandoc is not installed")
    def test_convert_source_preserves_resized_tables(self):
        source = self.root / "resized-table"
        source.mkdir()
        (source / "main.tex").write_text(
            r"""\documentclass{article}
\begin{document}
See Table~\ref{tab:architecture}.
\begin{table*}
\begin{center}
\resizebox{0.7\linewidth}{!}{
\begin{tabular}{lc}
Network & Score\\
ResNet-152 & 3.57\\
\end{tabular}
}
\end{center}
\caption{Architectures.}\label{tab:architecture}
\end{table*}
\end{document}
"""
        )
        output = self.root / "resized-table.epub"
        convert_source(source, "2401.01234", output, pandoc="/opt/homebrew/bin/pandoc")
        validate_epub(output)
        with zipfile.ZipFile(output) as book:
            roots = [
                ElementTree.fromstring(book.read(name))
                for name in book.namelist()
                if name.endswith((".xhtml", ".html"))
            ]
        tables = [
            " ".join("".join(element.itertext()).split())
            for root in roots
            for element in root.iter()
            if element.tag.rsplit("}", 1)[-1] == "table"
        ]
        self.assertEqual(tables, ["Architectures. Network Score ResNet-152 3.57"])
        self.assertTrue(
            any(
                element.attrib.get("id") == "tab:architecture"
                for root in roots
                for element in root.iter()
            )
        )

    @unittest.skipUnless(Path("/opt/homebrew/bin/pandoc").exists(), "Pandoc is not installed")
    def test_convert_source_splits_tables_joined_for_print_layout(self):
        source = self.root / "joined-tables"
        source.mkdir()
        (source / "main.tex").write_text(
            r"""\documentclass{article}
\begin{document}
See Tables~\ref{tab:single} and~\ref{tab:ensemble}.
\begin{table}
\begin{tabular}{lc}
Single & 4.49\\
\end{tabular}
\caption{Single model.}\label{tab:single}
%\end{table}
%\begin{table}[t]
\begin{tabular}{lc}
Ensemble & 3.57\\
\end{tabular}
\caption{Ensemble.}\label{tab:ensemble}
\end{table}
\end{document}
"""
        )
        output = self.root / "joined-tables.epub"
        convert_source(source, "2401.01234", output, pandoc="/opt/homebrew/bin/pandoc")
        validate_epub(output)
        with zipfile.ZipFile(output) as book:
            content = "\n".join(
                book.read(name).decode("utf-8")
                for name in book.namelist()
                if name.endswith((".xhtml", ".html"))
            )
        self.assertIn('id="tab:single"', content)
        self.assertIn('id="tab:ensemble"', content)
        self.assertIn("Single", content)
        self.assertIn("Ensemble", content)

    @unittest.skipUnless(Path("/opt/homebrew/bin/pandoc").exists(), "Pandoc is not installed")
    def test_convert_source_preserves_math_array_tables(self):
        source = self.root / "math-array-table"
        source.mkdir()
        (source / "main.tex").write_text(
            r"""\documentclass{article}
\begin{document}
See Table~\ref{tab:metric}.
\begin{table}
\caption{Intersection numbers.}\label{tab:metric}
\begin{displaymath}
\begin{array}{c|cc}
 & A & B\\
A & 1 & 0\\
\end{array}
\end{displaymath}
\end{table}
\end{document}
"""
        )
        output = self.root / "math-array-table.epub"
        convert_source(source, "2401.01234", output, pandoc="/opt/homebrew/bin/pandoc")
        validate_epub(output)
        with zipfile.ZipFile(output) as book:
            roots = [
                ElementTree.fromstring(book.read(name))
                for name in book.namelist()
                if name.endswith((".xhtml", ".html"))
            ]
        tables = [
            " ".join("".join(element.itertext()).split())
            for root in roots
            for element in root.iter()
            if element.tag.rsplit("}", 1)[-1] == "table"
        ]
        self.assertEqual(tables, ["Intersection numbers. A B A 1 0"])
        self.assertTrue(
            any(
                element.attrib.get("id") == "tab:metric"
                for root in roots
                for element in root.iter()
            )
        )

    @unittest.skipUnless(Path("/opt/homebrew/bin/pandoc").exists(), "Pandoc is not installed")
    def test_convert_source_promotes_equation_labels_from_mathml_annotations(self):
        source = self.root / "equation-label"
        source.mkdir()
        (source / "main.tex").write_text(
            r"""\documentclass{article}
\begin{document}
\begin{equation}\label{eq:identity}
y = F(x) + x.
\end{equation}
See Equation~\ref{eq:identity}.
\end{document}
"""
        )
        output = self.root / "equation-label.epub"
        convert_source(source, "2401.01234", output, pandoc="/opt/homebrew/bin/pandoc")
        validate_epub(output)
        with zipfile.ZipFile(output) as book:
            content = "\n".join(
                book.read(name).decode("utf-8")
                for name in book.namelist()
                if name.endswith((".xhtml", ".html"))
            )
        self.assertIn('id="eq:identity"', content)
        self.assertRegex(content, r'href="[^"]*#eq:identity"')

    @unittest.skipUnless(Path("/opt/homebrew/bin/pandoc").exists(), "Pandoc is not installed")
    def test_convert_source_preserves_abstract_footnotes(self):
        source = self.root / "abstract-footnote"
        source.mkdir()
        (source / "main.tex").write_text(
            r"""\documentclass{article}
\title{A Paper}
\begin{document}
\maketitle
\begin{abstract}
Results and data\footnote{Dataset details at \url{https://example.com/data}.}.
\end{abstract}
\section{Body}
Main text.
\end{document}
"""
        )
        output = self.root / "abstract-footnote.epub"
        convert_source(source, "2401.01234", output, pandoc="/opt/homebrew/bin/pandoc")
        try:
            validate_epub(output, require_png_cover=True, require_abstract=True)
        except ConversionError as error:
            self.fail(f"converted EPUB failed strict validation: {error}")
        with zipfile.ZipFile(output) as book:
            content = "\n".join(
                book.read(name).decode("utf-8")
                for name in book.namelist()
                if name.endswith((".xhtml", ".html"))
            )
        self.assertIn("Abstract", content)
        self.assertIn("Dataset details", content)
        self.assertIn("https://example.com/data", content)
        self.assertRegex(content, r'href="[^"]*#fn1"')
        self.assertIn('id="fn1"', content)

    @unittest.skipUnless(Path("/opt/homebrew/bin/pandoc").exists(), "Pandoc is not installed")
    def test_convert_source_has_direct_cover_toc_abstract_order(self):
        source = self.root / "direct-front-matter"
        source.mkdir()
        (source / "main.tex").write_text(
            r"""\documentclass{article}
\title{Front Matter Paper}
\author{Ada Author}
\begin{document}
\maketitle
\begin{abstract}
Abstract body.
\end{abstract}
\section{Body}
Main text.
\end{document}
"""
        )
        output = self.root / "direct-front-matter.epub"
        convert_source(source, "2401.01234", output, pandoc="/opt/homebrew/bin/pandoc")
        with zipfile.ZipFile(output) as book:
            package = ElementTree.fromstring(book.read("EPUB/content.opf"))
            items = {
                element.attrib["id"]: element
                for element in package.iter()
                if element.tag.rsplit("}", 1)[-1] == "item"
            }
            spine = [
                items[element.attrib["idref"]].attrib["href"]
                for element in package.iter()
                if element.tag.rsplit("}", 1)[-1] == "itemref"
            ]
            nav_id = next(
                item_id
                for item_id, element in items.items()
                if "nav" in element.attrib.get("properties", "").split()
            )
            nav_href = items[nav_id].attrib["href"]
            nav = ElementTree.fromstring(book.read("EPUB/" + nav_href))
            nav_heading = next(
                " ".join("".join(element.itertext()).split())
                for element in nav.iter()
                if element.tag.rsplit("}", 1)[-1] == "h1"
            )
            abstract = ElementTree.fromstring(book.read("EPUB/" + spine[2]))
            abstract_heading = next(
                " ".join("".join(element.itertext()).split())
                for element in abstract.iter()
                if element.tag.rsplit("}", 1)[-1] == "h1"
            )
        self.assertEqual(spine[:2], ["text/cover.xhtml", nav_href])
        self.assertNotIn("title_page.xhtml", " ".join(spine))
        self.assertEqual(nav_heading, "Table of Contents")
        self.assertEqual(abstract_heading, "Abstract")

    @unittest.skipUnless(Path("/opt/homebrew/bin/pandoc").exists(), "Pandoc is not installed")
    def test_convert_source_adds_arxiv_series_metadata(self):
        source = self.root / "series-metadata"
        source.mkdir()
        (source / "main.tex").write_text(
            r"""\documentclass{article}
\title{Series Paper}
\author{Ada Author}
\begin{document}
\maketitle
\section{Body}
Main text.
\end{document}
"""
        )
        output = self.root / "series-metadata.epub"
        convert_source(source, "2401.01234", output, pandoc="/opt/homebrew/bin/pandoc")
        with zipfile.ZipFile(output) as book:
            package = ElementTree.fromstring(book.read("EPUB/content.opf"))
        metadata = [
            element
            for element in package.iter()
            if element.tag.rsplit("}", 1)[-1] == "metadata"
        ][0]
        collection = [
            element
            for element in metadata
            if element.tag.rsplit("}", 1)[-1] == "meta"
            and element.attrib.get("property") == "belongs-to-collection"
        ]
        collection_type = [
            element
            for element in metadata
            if element.tag.rsplit("}", 1)[-1] == "meta"
            and element.attrib.get("property") == "collection-type"
        ]
        titles = [
            "".join(element.itertext())
            for element in metadata
            if element.tag.rsplit("}", 1)[-1] == "title"
        ]
        creators = [
            "".join(element.itertext())
            for element in metadata
            if element.tag.rsplit("}", 1)[-1] == "creator"
        ]
        self.assertEqual(
            [(element.attrib.get("id"), "".join(element.itertext())) for element in collection],
            [("arxiv-series", "Arxiv Series")],
        )
        self.assertEqual(
            [(element.attrib.get("refines"), "".join(element.itertext())) for element in collection_type],
            [("#arxiv-series", "series")],
        )
        self.assertEqual(titles, ["Series Paper"])
        self.assertEqual(creators, ["Ada Author"])

    @unittest.skipUnless(Path("/opt/homebrew/bin/pandoc").exists(), "Pandoc is not installed")
    def test_convert_source_preserves_ieee_title_abstract(self):
        source = self.root / "ieee-abstract"
        source.mkdir()
        (source / "main.tex").write_text(
            r"""\documentclass{article}
\title{IEEE Paper}
\begin{document}
\IEEEtitleabstractindextext{\input{abstract}}
\maketitle
\section{Body}
Main text.
\end{document}
"""
        )
        (source / "abstract.tex").write_text(
            r"""\begin{abstract}
The complete IEEE abstract survives.
\end{abstract}
"""
        )
        output = self.root / "ieee-abstract.epub"
        try:
            convert_source(source, "2401.01234", output, pandoc="/opt/homebrew/bin/pandoc")
        except ConversionError as error:
            self.fail(f"IEEE abstract conversion failed: {error}")
        validate_epub(output, require_png_cover=True, require_abstract=True)
        with zipfile.ZipFile(output) as book:
            content = "\n".join(
                book.read(name).decode("utf-8")
                for name in book.namelist()
                if name.endswith((".xhtml", ".html"))
            )
        self.assertIn("The complete IEEE abstract survives.", content)
        self.assertLess(content.index("The complete IEEE abstract survives."), content.index("Main text."))

    @unittest.skipUnless(Path("/opt/homebrew/bin/pandoc").exists(), "Pandoc is not installed")
    def test_convert_source_ignores_commented_abstract_marker(self):
        source = self.root / "commented-abstract"
        source.mkdir()
        (source / "main.tex").write_text(
            r"""\documentclass{article}
\begin{document}
% \section*{Abstract}
\section{Body}
Main text.
\end{document}
"""
        )
        output = self.root / "commented-abstract.epub"
        try:
            convert_source(source, "2401.01234", output, pandoc="/opt/homebrew/bin/pandoc")
        except ConversionError as error:
            self.fail(f"commented abstract marker affected conversion: {error}")
        validate_epub(output, require_png_cover=True)

    @unittest.skipUnless(Path("/opt/homebrew/bin/pandoc").exists(), "Pandoc is not installed")
    def test_convert_source_preserves_labels_in_minipage_tables(self):
        source = self.root / "minipage-table"
        source.mkdir()
        (source / "main.tex").write_text(
            r"""\documentclass{article}
\begin{document}
See Tables~\ref{tab:realism} and~\ref{tab:human}.
\begin{table}
\begin{minipage}{0.42\textwidth}
\caption{Realism results.}
\label{tab:realism}
\begin{tabular}{lc}
Model & Score \\
A & 99 \\
\end{tabular}
\end{minipage}\hfill
\begin{minipage}{0.55\textwidth}
\caption{Human results.}
\label{tab:human}
\begin{tabular}{lc}
Method & Score \\
B & 98 \\
\end{tabular}
\end{minipage}
\end{table}
\end{document}
"""
        )
        output = self.root / "minipage-table.epub"
        try:
            convert_source(source, "2401.01234", output, pandoc="/opt/homebrew/bin/pandoc")
        except ConversionError as error:
            self.fail(f"minipage table conversion failed: {error}")
        validate_epub(output, require_png_cover=True)
        with zipfile.ZipFile(output) as book:
            content = "\n".join(
                book.read(name).decode("utf-8")
                for name in book.namelist()
                if name.endswith((".xhtml", ".html"))
            )
        self.assertIn('id="tab:realism"', content)
        self.assertIn('id="tab:human"', content)
        self.assertRegex(content, r'href="[^"]*#tab:realism"')
        self.assertRegex(content, r'href="[^"]*#tab:human"')

    @unittest.skipUnless(Path("/opt/homebrew/bin/pandoc").exists(), "Pandoc is not installed")
    def test_convert_source_preserves_custom_prompt_blocks(self):
        source = self.root / "prompt-block"
        source.mkdir()
        (source / "main.tex").write_text(
            r"""\documentclass{article}
\begin{document}
See Prompt~\ref{prompt:questionnaire}.
\begin{prompt}[ht]
\begin{mymessagebox}[frametitle=Questionnaire Example]
\begin{verbatim}
question = "Complete prompt content"
\end{verbatim}
\end{mymessagebox}
\caption{Example generated questionnaire.}
\label{prompt:questionnaire}
\end{prompt}
\end{document}
"""
        )
        output = self.root / "prompt-block.epub"
        try:
            convert_source(source, "2401.01234", output, pandoc="/opt/homebrew/bin/pandoc")
        except ConversionError as error:
            self.fail(f"custom prompt conversion failed: {error}")
        validate_epub(output, require_png_cover=True)
        with zipfile.ZipFile(output) as book:
            content = "\n".join(
                book.read(name).decode("utf-8")
                for name in book.namelist()
                if name.endswith((".xhtml", ".html"))
            )
        self.assertIn("Complete prompt content", content)
        self.assertIn("Example generated questionnaire.", content)
        self.assertIn('id="prompt:questionnaire"', content)
        self.assertRegex(content, r'href="[^"]*#prompt:questionnaire"')

    @unittest.skipUnless(Path("/opt/homebrew/bin/pandoc").exists(), "Pandoc is not installed")
    def test_convert_source_preserves_latex_209_front_matter(self):
        source = self.root / "legacy-front-matter"
        source.mkdir()
        (source / "main.tex").write_text(
            r"""\documentstyle[preprint]{article}
\title{Legacy Paper}
\author{Ada Example}
\inst{Example Institute}
\abst{The legacy abstract text.}
\begin{document}
\maketitle
\section{Body}
Main text.
\end{document}
"""
        )
        output = self.root / "legacy-front-matter.epub"
        convert_source(source, "hep-th/9901001", output, pandoc="/opt/homebrew/bin/pandoc")
        validate_epub(output)
        with zipfile.ZipFile(output) as book:
            content = "\n".join(
                book.read(name).decode("utf-8")
                for name in book.namelist()
                if name.endswith((".xhtml", ".html"))
            )
        self.assertIn("Example Institute", content)
        self.assertIn("The legacy abstract text.", content)
        self.assertLess(content.index("The legacy abstract text."), content.index("Main text."))

    def test_extract_source_accepts_tar_and_single_gzipped_tex(self):
        tar_destination = self.root / "tar-source"
        extract_source(self.make_tar({"main.tex": b"\\documentclass{article}"}), tar_destination)
        self.assertEqual(
            (tar_destination / "main.tex").read_bytes(), b"\\documentclass{article}"
        )

        single = self.root / "single.gz"
        with gzip.open(single, "wb") as compressed:
            compressed.write(b"\\documentclass{article}\n\\begin{document}Hi\\end{document}")
        single_destination = self.root / "single-source"
        extract_source(single, single_destination)
        self.assertIn("\\documentclass", (single_destination / "main.tex").read_text())

    def test_extract_source_rejects_non_tex_single_payload(self):
        payload = self.root / "paper.gz"
        with gzip.open(payload, "wb") as compressed:
            compressed.write(b"%PDF-1.7")
        with self.assertRaises(ConversionError):
            extract_source(payload, self.root / "not-source")

    def test_native_message_round_trip_preserves_unicode(self):
        stream = io.BytesIO()
        value = {"title": "λ paper", "ok": True}
        write_message(stream, value)
        stream.seek(0)
        self.assertEqual(read_message(stream), value)

    def test_native_message_rejects_truncation_and_oversize(self):
        truncated = io.BytesIO(struct.pack("=I", 5) + b"{}")
        with self.assertRaises(ConversionError):
            read_message(truncated)

        oversized = io.BytesIO(struct.pack("=I", 4_194_305))
        with self.assertRaises(ConversionError):
            read_message(oversized)

    def test_native_message_rejects_invalid_json_shape(self):
        payload = json.dumps(["not", "an", "object"]).encode()
        stream = io.BytesIO(struct.pack("=I", len(payload)) + payload)
        with self.assertRaises(ConversionError):
            read_message(stream)

    def test_validate_kindle_email_accepts_kindle_domains_only(self):
        self.assertEqual(validate_kindle_email(" Reader_1@Kindle.com "), "Reader_1@kindle.com")
        self.assertEqual(validate_kindle_email("reader@free.kindle.com"), "reader@free.kindle.com")
        for email in ("reader@example.com", "@kindle.com", "reader name@kindle.com", ""):
            with self.subTest(email=email), self.assertRaises(ConversionError):
                validate_kindle_email(email)

    def test_process_request_rejects_bad_input_before_network_access(self):
        for message in (
            {},
            {"url": "https://arxiv.org/abs/2401.01234", "kindle_email": "bad", "send": True},
            {"url": "https://example.com/abs/2401.01234", "send": False},
        ):
            with self.subTest(message=message), self.assertRaises(ConversionError):
                process_request(message)

    def test_process_request_keeps_epub_when_mail_delivery_fails(self):
        destination = self.root / "saved.epub"

        def convert(_source, arxiv_id, temporary_epub):
            temporary_epub.write_bytes(b"validated epub")
            return PaperMetadata("Saved Paper", "Ada Example", arxiv_id)

        with (
            patch("native.host._download_source"),
            patch("native.host.extract_source"),
            patch("native.host.convert_source", side_effect=convert),
            patch("native.host._output_path", return_value=destination),
            patch(
                "native.host.send_with_mail",
                side_effect=ConversionError("Mail permission denied"),
            ),
        ):
            response = process_request(
                {
                    "url": "https://arxiv.org/abs/2401.01234",
                    "kindle_email": "reader@kindle.com",
                    "send": True,
                }
            )

        self.assertFalse(response["ok"])
        self.assertEqual(response["epub_path"], str(destination))
        self.assertEqual(destination.read_bytes(), b"validated epub")
        self.assertIn("Mail permission denied", response["message"])

    def test_prepare_graphics_converts_pdf_and_rewrites_only_its_target(self):
        source = self.root / "graphics"
        source.mkdir()
        (source / "plot.pdf").write_bytes(b"pdf")
        (source / "drawing.eps").write_bytes(b"eps")
        (source / "photo.png").write_bytes(b"png")
        tex = source / "main.tex"
        tex.write_text(
            r"""Before
\includegraphics[width=\linewidth]{plot.pdf}
\epsfbox{drawing.eps}
\includegraphics{photo.png}
After
"""
        )

        def converter(source_path: Path, output_path: Path) -> None:
            self.assertIn(
                source_path,
                {(source / "plot.pdf").resolve(), (source / "drawing.eps").resolve()},
            )
            output_path.write_bytes(b"converted png")

        self.assertEqual(prepare_graphics(source, converter=converter), 2)
        rewritten = tex.read_text()
        self.assertIn(r"\includegraphics[width=\linewidth]{plot.arxiv-kindle.png}", rewritten)
        self.assertIn(r"\includegraphics{drawing.arxiv-kindle.png}", rewritten)
        self.assertIn(r"\includegraphics{photo.png}", rewritten)
        self.assertTrue((source / "plot.arxiv-kindle.png").exists())

    def test_graphic_conversion_times_out_instead_of_hanging(self):
        source = self.root / "figure.eps"
        output = self.root / "figure.png"
        source.write_bytes(b"eps")
        failed = subprocess.CompletedProcess([], 1, stdout="", stderr="unsupported")
        with (
            patch("native.host.shutil.which", return_value=None),
            patch(
                "native.host.subprocess.run",
                side_effect=[
                    failed,
                    failed,
                    subprocess.TimeoutExpired(["qlmanage"], 30),
                ],
            ),
            self.assertRaises(ConversionError),
        ):
            _convert_graphic_to_png(source, output)

    def test_pandoc_error_detail_does_not_collapse_to_a_caret(self):
        stderr = r"""[WARNING] Could not parse a style file
Error at source.tex line 294 column 26:
unexpected #1
\newcolumntype{x}[1]{>{\centering}p{#1pt}}
                         ^
"""
        detail = _pandoc_error_detail(stderr)
        self.assertIn("source.tex line 294", detail)
        self.assertIn("unexpected #1", detail)
        self.assertNotEqual(detail, "^")


if __name__ == "__main__":
    unittest.main()
