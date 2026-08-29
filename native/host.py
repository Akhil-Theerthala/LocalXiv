#!/usr/bin/env python3
"""Native Chrome host and local arXiv-to-EPUB converter."""

from __future__ import annotations

import gzip
import html
import json
import os
import posixpath
import re
import shutil
import struct
import subprocess
import sys
import tarfile
import tempfile
import textwrap
import unicodedata
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import quote, unquote, urlsplit
from urllib.request import Request, urlopen
from xml.etree import ElementTree


MAX_ARCHIVE_MEMBERS = 10_000
MAX_EXTRACTED_BYTES = 1_000_000_000
MAX_DOWNLOAD_BYTES = 200_000_000
MAX_NATIVE_REQUEST_BYTES = 4_194_304
MAX_NATIVE_RESPONSE_BYTES = 1_048_576
_TEX_SLASH_PAIRS = r"(?:\\\\)*"
_TEX_COMMAND_PREFIX = rf"(?<!\\){_TEX_SLASH_PAIRS}\\"


class ConversionError(RuntimeError):
    """A user-actionable conversion failure."""


@dataclass(frozen=True)
class PaperMetadata:
    title: str
    authors: str
    arxiv_id: str


@dataclass(frozen=True)
class BibliographyEntry:
    key: str
    label: str


def parse_arxiv_url(url: str) -> str:
    parts = urlsplit(url)
    if parts.scheme != "https" or (parts.hostname or "").lower() not in {
        "arxiv.org",
        "www.arxiv.org",
        "alphaxiv.org",
        "www.alphaxiv.org",
    }:
        raise ConversionError("Open an arXiv or alphaXiv abstract page first.")
    path = unquote(parts.path)
    if not path.startswith("/abs/"):
        raise ConversionError("Open an arXiv or alphaXiv /abs/... page first.")
    arxiv_id = path.removeprefix("/abs/").rstrip("/")
    modern = r"\d{4}\.\d{4,5}(?:v\d+)?"
    legacy = r"[A-Za-z][A-Za-z.-]*/\d{7}(?:v\d+)?"
    if not re.fullmatch(rf"(?:{modern}|{legacy})", arxiv_id):
        raise ConversionError("The page does not contain a valid arXiv identifier.")
    return arxiv_id


def safe_extract(
    archive: Path,
    destination: Path,
    *,
    max_bytes: int = MAX_EXTRACTED_BYTES,
    max_members: int = MAX_ARCHIVE_MEMBERS,
) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    try:
        bundle = tarfile.open(archive, "r:*")
    except tarfile.TarError as error:
        raise ConversionError("The arXiv source is not a readable tar archive.") from error

    total = 0
    seen: set[Path] = set()
    with bundle:
        members = bundle.getmembers()
        if len(members) > max_members:
            raise ConversionError("The source archive contains too many files.")
        for member in members:
            if member.isdir() and member.name.rstrip("/") == ".":
                continue
            name = PurePosixPath(member.name)
            if name.is_absolute() or not name.parts or ".." in name.parts:
                raise ConversionError("The source archive contains an unsafe path.")
            if member.issym() or member.islnk() or member.isdev():
                raise ConversionError("The source archive contains an unsafe link or device.")
            target = (destination / Path(*name.parts)).resolve()
            if target != root and root not in target.parents:
                raise ConversionError("The source archive escapes its temporary directory.")
            if target in seen:
                raise ConversionError("The source archive contains duplicate paths.")
            seen.add(target)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            if not member.isfile():
                raise ConversionError("The source archive contains an unsupported entry.")
            total += member.size
            if total > max_bytes:
                raise ConversionError("The expanded source archive is too large.")
            target.parent.mkdir(parents=True, exist_ok=True)
            source = bundle.extractfile(member)
            if source is None:
                raise ConversionError(f"Could not read {member.name} from the source archive.")
            with source, target.open("wb") as output:
                shutil.copyfileobj(source, output)


def extract_source(payload: Path, destination: Path) -> None:
    if tarfile.is_tarfile(payload):
        safe_extract(payload, destination)
        return
    try:
        with gzip.open(payload, "rb") as compressed:
            source = compressed.read(MAX_EXTRACTED_BYTES + 1)
    except (gzip.BadGzipFile, OSError):
        source = payload.read_bytes()
    if len(source) > MAX_EXTRACTED_BYTES:
        raise ConversionError("The expanded arXiv source is too large.")
    if not re.search(rb"\\document(?:class|style)", source) or b"\\begin{document}" not in source:
        raise ConversionError("arXiv did not return TeX source for this paper.")
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "main.tex").write_bytes(source)


def find_root_tex(source_dir: Path) -> Path:
    candidates: list[tuple[Path, str]] = []
    for path in sorted(source_dir.rglob("*.tex")):
        text = path.read_text(encoding="utf-8", errors="replace")
        if re.search(r"\\document(?:class|style)(?:\[[^]]*\])?\s*\{", text) and re.search(
            r"\\begin\s*\{document\}", text
        ):
            candidates.append((path, text))
    if not candidates:
        raise ConversionError("No root TeX document was found in the arXiv source.")

    candidate_paths = {path.resolve() for path, _ in candidates}
    scored: list[tuple[tuple[int, int, int], Path]] = []
    include_pattern = re.compile(r"\\(?:input|include)\s*\{([^}]+)\}")
    for path, text in candidates:
        included_roots = 0
        for raw_target in include_pattern.findall(text):
            target = raw_target.strip()
            if not Path(target).suffix:
                target += ".tex"
            if (path.parent / target).resolve() in candidate_paths:
                included_roots += 1
        depth = len(path.relative_to(source_dir).parts)
        scored.append(((included_roots, -depth, len(text)), path))

    scored.sort(key=lambda item: item[0], reverse=True)
    if len(scored) > 1 and scored[0][0] == scored[1][0]:
        raise ConversionError("Multiple equally likely root TeX documents were found.")
    return scored[0][1]


def _command_values(tex: str, command: str) -> list[str]:
    pattern = re.compile(
        rf"{_TEX_COMMAND_PREFIX}{re.escape(command)}(?:\[[^]]*\])?\s*\{{"
    )
    values: list[str] = []
    position = 0
    while match := pattern.search(tex, position):
        start = match.end() - 1
        depth = 0
        escaped = False
        for index in range(start, len(tex)):
            char = tex[index]
            if escaped:
                escaped = False
                continue
            if char == "\\":
                escaped = True
                continue
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    values.append(tex[start + 1 : index])
                    position = index + 1
                    break
        else:
            break
    return values


def _command_value(tex: str, command: str) -> str | None:
    values = _command_values(tex, command)
    return values[0] if values else None


def _environment_values(tex: str, environment: str) -> list[str]:
    opening = re.compile(
        rf"{_TEX_COMMAND_PREFIX}begin\s*\{{\s*{re.escape(environment)}\s*\}}"
    )
    closing = re.compile(
        rf"{_TEX_COMMAND_PREFIX}end\s*\{{\s*{re.escape(environment)}\s*\}}"
    )
    values: list[str] = []
    position = 0
    while match := opening.search(tex, position):
        end = closing.search(tex, match.end())
        if end is None:
            break
        values.append(tex[match.end() : end.start()])
        position = end.end()
    return values


_TEX_ACCENT_MARKS = {
    '"': "\N{COMBINING DIAERESIS}",
    "'": "\N{COMBINING ACUTE ACCENT}",
    ".": "\N{COMBINING DOT ABOVE}",
    "=": "\N{COMBINING MACRON}",
    "H": "\N{COMBINING DOUBLE ACUTE ACCENT}",
    "`": "\N{COMBINING GRAVE ACCENT}",
    "^": "\N{COMBINING CIRCUMFLEX ACCENT}",
    "b": "\N{COMBINING MACRON BELOW}",
    "c": "\N{COMBINING CEDILLA}",
    "d": "\N{COMBINING DOT BELOW}",
    "k": "\N{COMBINING OGONEK}",
    "r": "\N{COMBINING RING ABOVE}",
    "u": "\N{COMBINING BREVE}",
    "v": "\N{COMBINING CARON}",
    "~": "\N{COMBINING TILDE}",
}
_TEX_ACCENT = re.compile(
    r"\\(?:"
    r"(?P<symbol_accent>[\"'.=`^~])\s*"
    r"(?:\{\s*(?P<symbol_braced>[A-Za-z])\s*\}|(?P<symbol_plain>[A-Za-z]))"
    r"|"
    r"(?P<word_accent>[bcdHkruv])"
    r"(?:\s*\{\s*(?P<word_braced>[A-Za-z])\s*\}|\s+(?P<word_plain>[A-Za-z]))"
    r")"
)


def _replace_tex_accent(match: re.Match[str]) -> str:
    accent = match.group("symbol_accent") or match.group("word_accent")
    letter = next(
        group
        for name in ("symbol_braced", "symbol_plain", "word_braced", "word_plain")
        if (group := match.group(name))
    )
    return unicodedata.normalize("NFC", letter + _TEX_ACCENT_MARKS[accent])


def _strip_tex(value: str, *, authors: bool = False) -> str:
    value = re.sub(r"(?m)(?<!\\)%.*$", "", value)
    value = re.sub(r"\\thanks\s*\{(?:[^{}]|\{[^{}]*\})*\}", "", value)
    value = _TEX_ACCENT.sub(_replace_tex_accent, value)
    if authors:
        value = re.sub(r"\\and\b|\\\\+", ", ", value)
    else:
        value = re.sub(r"\\\\+", " ", value)
    replacements = {r"\&": "&", r"\%": "%", r"\_": "_", "~": " "}
    for old, new in replacements.items():
        value = value.replace(old, new)
    command = re.compile(r"\\[A-Za-z@]+\*?(?:\[[^]]*\])?\{([^{}]*)\}")
    previous = None
    while value != previous:
        previous = value
        value = command.sub(r"\1", value)
    value = re.sub(r"\\[A-Za-z@]+\*?", " ", value)
    value = value.replace("{", "").replace("}", "").replace("$", "")
    value = re.sub(r"\s*,\s*", ", ", value)
    value = re.sub(r"(?:,\s*){2,}", ", ", value)
    return re.sub(r"\s+", " ", value).strip(" ,")


def _first_cleaned_command_value(
    tex: str, command: str, *, authors: bool = False
) -> str:
    return next(
        (
            cleaned
            for value in _command_values(tex, command)
            if (cleaned := _strip_tex(value, authors=authors))
        ),
        "",
    )


def extract_metadata(tex: str, arxiv_id: str) -> PaperMetadata:
    tex = _searchable_tex_source(tex)
    title = _first_cleaned_command_value(tex, "title")
    if not title:
        title = _first_cleaned_command_value(tex, "icmltitle")
    if not title:
        title = f"arXiv {arxiv_id}"

    authors = _first_cleaned_command_value(tex, "author", authors=True)
    if not authors:
        icml_authors = [
            cleaned
            for body in _environment_values(tex, "icmlauthorlist")
            for value in _command_values(body, "icmlauthor")
            if (cleaned := _strip_tex(value))
        ]
        authors = ", ".join(icml_authors)
    if not authors:
        authors = "Unknown authors"
    return PaperMetadata(title=title, authors=authors, arxiv_id=arxiv_id)


def _cover_title_layout(title: str) -> tuple[int, list[str], int]:
    """Return the largest complete title layout that fits the cover field."""
    for font_size in (84, 78, 72, 66, 60, 54, 48, 42):
        max_chars = int(1000 / (font_size * 0.56))
        lines = textwrap.wrap(
            title,
            width=max_chars,
            break_long_words=False,
            break_on_hyphens=False,
        ) or [title]
        line_height = round(font_size * 1.18)
        block_height = len(lines) * line_height + 40
        if max(map(len, lines)) <= max_chars and block_height <= 1320:
            top = 190 + (1320 - block_height) // 2
            return font_size, lines, top
    raise ConversionError("Paper title is too long to fit on the cover.")


def _write_text_cover(title: str, masthead: str, path: Path) -> None:
    font_size, title_lines, top = _cover_title_layout(title)
    line_height = round(font_size * 1.18)
    lines: list[str] = []
    for index, line in enumerate(title_lines):
        lines.append(
            f'<text x="300" y="{top + index * line_height}" fill="#171717" '
            f'font-family="Georgia, serif" font-size="{font_size}" font-weight="bold">'
            f"{html.escape(line)}</text>"
        )
    rule_y = top + (len(title_lines) - 1) * line_height + round(font_size * 0.65)
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1600" viewBox="0 0 1600 1600">'
        '<rect width="1600" height="1600" fill="#ffffff"/>'
        '<rect x="200" width="1200" height="1600" fill="#f2eee4"/>'
        '<rect x="200" width="36" height="1600" fill="#ae4333"/>'
        '<rect x="236" width="1164" height="190" fill="#111111"/>'
        '<text x="300" y="116" fill="#ffffff" font-family="monospace" '
        'font-size="42" font-weight="bold">'
        f'{html.escape(masthead)}</text>'
        + "".join(lines)
        + f'<rect x="300" y="{rule_y}" width="830" height="12" fill="#171717"/>'
        + f'<rect x="1150" y="{rule_y}" width="170" height="12" fill="#ae4333"/>'
        + "</svg>"
    )
    path.write_text(svg, encoding="utf-8")


def write_cover(metadata: PaperMetadata, path: Path) -> None:
    _write_text_cover(metadata.title, f"arXiv {metadata.arxiv_id}", path)


def write_collection_cover(title: str, paper_count: int, path: Path) -> None:
    noun = "paper" if paper_count == 1 else "papers"
    _write_text_cover(title, f"alphaXiv library / {paper_count} {noun}", path)


def _png_dimensions(path: Path) -> tuple[int, int]:
    header = path.read_bytes()[:24]
    if (
        len(header) != 24
        or header[:8] != b"\x89PNG\r\n\x1a\n"
        or header[12:16] != b"IHDR"
    ):
        raise ConversionError("Cover renderer did not produce a valid PNG.")
    return struct.unpack(">II", header[16:24])


def rasterize_cover(
    svg: Path,
    png: Path,
    *,
    qlmanage: str = "/usr/bin/qlmanage",
    sips: str = "/usr/bin/sips",
) -> None:
    rendered = svg.parent / f"{svg.name}.png"
    rendered.unlink(missing_ok=True)
    try:
        preview = subprocess.run(
            [qlmanage, "-t", "-s", "1600", "-o", str(svg.parent), str(svg)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if preview.returncode or not rendered.is_file():
            raise ConversionError("macOS could not render the EPUB cover.")
        shutil.copy2(rendered, png)
        crop = subprocess.run(
            [sips, "--cropToHeightWidth", "1600", "1200", str(png)],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired as error:
        raise ConversionError("EPUB cover rendering timed out.") from error
    except OSError as error:
        raise ConversionError("macOS cover rendering tools are unavailable.") from error
    finally:
        rendered.unlink(missing_ok=True)
    if crop.returncode or _png_dimensions(png) != (1200, 1600):
        raise ConversionError("EPUB cover is not a 1200 x 1600 PNG.")


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _xml_ids(data: bytes, name: str) -> set[str]:
    try:
        root = ElementTree.fromstring(data)
    except ElementTree.ParseError as error:
        raise ConversionError(f"EPUB document {name} is not valid XML.") from error
    return {
        value
        for element in root.iter()
        for key, value in element.attrib.items()
        if _local_name(key) == "id"
    }


def _validate_abstract_order(
    book: zipfile.ZipFile, spine_documents: list[str]
) -> None:
    abstract_found = False
    abstract_has_content = False
    collecting_abstract = False
    numbered_heading_seen = False
    headings = {"h1", "h2", "h3", "h4", "h5", "h6"}
    content_elements = {"p", "li", "blockquote", "table", "math", "figure"}

    for name in spine_documents:
        try:
            document = ElementTree.fromstring(book.read(name))
        except (KeyError, ElementTree.ParseError) as error:
            raise ConversionError(f"EPUB document {name} is not valid XML.") from error
        if any(_local_name(element.tag) == "nav" for element in document.iter()):
            continue
        for element in document.iter():
            tag = _local_name(element.tag)
            text = " ".join("".join(element.itertext()).split())
            if tag in headings:
                classes = element.attrib.get("class", "").split()
                if "title" in classes:
                    continue
                if collecting_abstract:
                    collecting_abstract = False
                if text.casefold() == "abstract":
                    if numbered_heading_seen or abstract_found:
                        raise ConversionError(
                            "The EPUB abstract is not before the first paper section."
                        )
                    abstract_found = True
                    collecting_abstract = True
                elif re.match(r"^\d+(?:\.\d+)*\s", text) or any(
                    "section-number" in descendant.attrib.get("class", "")
                    for descendant in element.iter()
                ):
                    numbered_heading_seen = True
            elif collecting_abstract and tag in content_elements and text:
                abstract_has_content = True

    if not abstract_found:
        raise ConversionError("The EPUB is missing the paper abstract.")
    if not abstract_has_content:
        raise ConversionError("The EPUB abstract is empty.")


def validate_epub(
    path: Path,
    *,
    require_png_cover: bool = False,
    require_abstract: bool = False,
    require_citations: bool = False,
    require_front_matter: bool = False,
    require_series: str | None = None,
) -> None:
    try:
        book = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as error:
        raise ConversionError("Pandoc did not produce a readable EPUB.") from error
    with book:
        infos = book.infolist()
        names = set(book.namelist())
        if (
            not infos
            or infos[0].filename != "mimetype"
            or infos[0].compress_type != zipfile.ZIP_STORED
            or book.read("mimetype") != b"application/epub+zip"
        ):
            raise ConversionError("The EPUB container has an invalid mimetype entry.")
        if book.testzip() is not None:
            raise ConversionError("The EPUB contains a corrupt ZIP member.")
        try:
            container = ElementTree.fromstring(book.read("META-INF/container.xml"))
            rootfile = next(
                element.attrib["full-path"]
                for element in container.iter()
                if _local_name(element.tag) == "rootfile"
            )
            package = ElementTree.fromstring(book.read(rootfile))
        except (KeyError, StopIteration, ElementTree.ParseError) as error:
            raise ConversionError("The EPUB package metadata is incomplete.") from error

        manifest_items = [
            element
            for element in package.iter()
            if _local_name(element.tag) == "item"
        ]
        manifest = {
            element.attrib["id"]: element.attrib["href"]
            for element in manifest_items
            if "id" in element.attrib
            and "href" in element.attrib
        }
        spine = [
            element.attrib.get("idref", "")
            for element in package.iter()
            if _local_name(element.tag) == "itemref"
        ]
        if not spine:
            raise ConversionError("The EPUB has an empty reading order.")
        package_dir = posixpath.dirname(rootfile)
        if require_png_cover:
            covers = [
                element
                for element in manifest_items
                if "cover-image" in element.attrib.get("properties", "").split()
            ]
            if len(covers) != 1:
                raise ConversionError("The EPUB does not declare one cover image.")
            cover = covers[0]
            cover_href = unquote(cover.attrib.get("href", ""))
            cover_target = posixpath.normpath(
                posixpath.join(package_dir, cover_href)
            )
            if (
                cover.attrib.get("media-type") != "image/png"
                or not cover_href.lower().endswith(".png")
                or cover_target not in names
            ):
                raise ConversionError("The EPUB cover is not a packaged PNG.")

        if require_series is not None:
            collections = [
                element
                for element in package.iter()
                if _local_name(element.tag) == "meta"
                and element.attrib.get("property") == "belongs-to-collection"
                and "".join(element.itertext()).strip() == require_series
            ]
            if len(collections) != 1 or not collections[0].attrib.get("id"):
                raise ConversionError("The EPUB is missing its series metadata.")
            collection_id = collections[0].attrib["id"]
            collection_types = [
                element
                for element in package.iter()
                if _local_name(element.tag) == "meta"
                and element.attrib.get("property") == "collection-type"
                and element.attrib.get("refines") == "#" + collection_id
                and "".join(element.itertext()).strip() == "series"
            ]
            if len(collection_types) != 1:
                raise ConversionError("The EPUB series metadata is incomplete.")

        spine_documents: list[str] = []
        for item_id in spine:
            if item_id not in manifest:
                raise ConversionError("The EPUB reading order references missing content.")
            target = posixpath.normpath(posixpath.join(package_dir, unquote(manifest[item_id])))
            if target not in names:
                raise ConversionError("The EPUB reading order contains a missing document.")
            spine_documents.append(target)

        if require_front_matter:
            nav_items = [
                element
                for element in manifest_items
                if "nav" in element.attrib.get("properties", "").split()
            ]
            if len(nav_items) != 1:
                raise ConversionError("The EPUB does not declare one table of contents.")
            nav_target = posixpath.normpath(
                posixpath.join(package_dir, unquote(nav_items[0].attrib.get("href", "")))
            )
            if len(spine_documents) < 2 or spine_documents[1] != nav_target:
                raise ConversionError(
                    "The EPUB table of contents does not follow the cover."
                )
            cover_targets = {
                posixpath.normpath(
                    posixpath.join(package_dir, unquote(element.attrib.get("href", "")))
                )
                for element in package.iter()
                if _local_name(element.tag) == "reference"
                and element.attrib.get("type") == "cover"
            }
            try:
                cover_document = ElementTree.fromstring(book.read(spine_documents[0]))
                nav_document = ElementTree.fromstring(book.read(nav_target))
            except (IndexError, KeyError, ElementTree.ParseError) as error:
                raise ConversionError("The EPUB front matter is incomplete.") from error
            cover_signals = any(
                element.attrib.get("id") == "cover"
                or "cover" in next(
                    (
                        value.split()
                        for key, value in element.attrib.items()
                        if _local_name(key) == "type"
                    ),
                    [],
                )
                for element in cover_document.iter()
            )
            if spine_documents[0] not in cover_targets and not cover_signals:
                raise ConversionError("The EPUB cover is not first in the reading order.")
            nav_headings = [
                " ".join("".join(element.itertext()).split())
                for element in nav_document.iter()
                if _local_name(element.tag) == "h1"
            ]
            if not nav_headings or nav_headings[0] != "Table of Contents":
                raise ConversionError("The EPUB table of contents has the wrong title.")
            for name in spine_documents:
                try:
                    document = ElementTree.fromstring(book.read(name))
                except (KeyError, ElementTree.ParseError) as error:
                    raise ConversionError(f"EPUB document {name} is not valid XML.") from error
                for element in document.iter():
                    classes = element.attrib.get("class", "").split()
                    epub_types = next(
                        (
                            value.split()
                            for key, value in element.attrib.items()
                            if _local_name(key) == "type"
                        ),
                        [],
                    )
                    if "titlepage" in classes or "titlepage" in epub_types:
                        raise ConversionError(
                            "The EPUB contains a redundant title page."
                        )
            if require_abstract:
                if len(spine_documents) < 3:
                    raise ConversionError("The EPUB abstract does not follow the contents.")
                try:
                    abstract_document = ElementTree.fromstring(
                        book.read(spine_documents[2])
                    )
                except (KeyError, ElementTree.ParseError) as error:
                    raise ConversionError("The EPUB abstract document is invalid.") from error
                headings = [
                    " ".join("".join(element.itertext()).split())
                    for element in abstract_document.iter()
                    if _local_name(element.tag) in {"h1", "h2", "h3", "h4", "h5", "h6"}
                ]
                if not headings or headings[0].casefold() != "abstract":
                    raise ConversionError(
                        "The EPUB abstract does not immediately follow the contents."
                    )

        if require_abstract:
            _validate_abstract_order(book, spine_documents)

        id_cache: dict[str, set[str]] = {}
        citation_count = 0
        references_found = False
        for name in sorted(names):
            if not name.lower().endswith((".xhtml", ".html", ".svg")):
                continue
            data = book.read(name)
            try:
                document = ElementTree.fromstring(data)
            except ElementTree.ParseError as error:
                raise ConversionError(f"EPUB document {name} is not valid XML.") from error
            id_cache[name] = _xml_ids(data, name)
            for element in document.iter():
                tag = _local_name(element.tag)
                normalized_text = " ".join("".join(element.itertext()).split())
                if tag in {"h1", "h2", "h3", "h4", "h5", "h6"} and (
                    normalized_text.casefold() == "references"
                ):
                    references_found = True
                if "citation" in element.attrib.get("class", "").split():
                    citation_count += 1
                    local_anchors = [
                        descendant.attrib.get("href", "")
                        for descendant in element.iter()
                        if _local_name(descendant.tag) == "a"
                        and descendant.attrib.get("href")
                    ]
                    if require_citations and (
                        not normalized_text
                        or not any(
                            not urlsplit(href).scheme
                            and not urlsplit(href).netloc
                            and bool(urlsplit(href).fragment)
                            for href in local_anchors
                        )
                    ):
                        raise ConversionError(
                            "The EPUB contains an empty or unlinked citation."
                        )
                for key, raw_value in element.attrib.items():
                    if _local_name(key) not in {"href", "src"} or not raw_value:
                        continue
                    parsed = urlsplit(raw_value)
                    if parsed.scheme or parsed.netloc:
                        continue
                    target = name
                    if parsed.path:
                        target = posixpath.normpath(
                            posixpath.join(posixpath.dirname(name), unquote(parsed.path))
                        )
                    if target.startswith("../") or target not in names:
                        raise ConversionError(f"EPUB link target is missing: {raw_value}")
                    if parsed.fragment:
                        if target not in id_cache:
                            id_cache[target] = _xml_ids(book.read(target), target)
                        if unquote(parsed.fragment) not in id_cache[target]:
                            raise ConversionError(f"EPUB link fragment is missing: {raw_value}")
        if require_citations:
            if citation_count == 0:
                raise ConversionError("The EPUB is missing its in-text citations.")
            if not references_found:
                raise ConversionError("The EPUB is missing its References section.")


def _repair_cross_file_fragments(path: Path) -> None:
    """Repair Pandoc refs that keep a same-file href after EPUB chapter splitting."""
    with zipfile.ZipFile(path) as source:
        infos = source.infolist()
        members = {info.filename: source.read(info.filename) for info in infos}

    documents = {
        name: ElementTree.fromstring(data)
        for name, data in members.items()
        if name.lower().endswith((".xhtml", ".html", ".svg"))
    }
    changed: set[str] = set()
    existing_ids = {
        value
        for document in documents.values()
        for element in document.iter()
        for key, value in element.attrib.items()
        if _local_name(key) == "id"
    }
    for name, document in documents.items():
        for element in document.iter():
            if "id" in element.attrib:
                continue
            if _local_name(element.tag) == "math":
                fallback_span = False
                label_sources = [
                    "".join(annotation.itertext())
                    for annotation in element.iter()
                    if _local_name(annotation.tag) == "annotation"
                ]
            elif (
                _local_name(element.tag) == "span"
                and "math" in element.attrib.get("class", "").split()
            ):
                fallback_span = True
                label_sources = ["".join(element.itertext())]
            else:
                continue
            labels = list(
                dict.fromkeys(
                    match.group(1)
                    for source in label_sources
                    for match in re.finditer(r"\\label\s*\{([^{}]+)\}", source)
                )
            )
            labels = [label for label in labels if label not in existing_ids]
            if not labels:
                continue
            element.set("id", labels[0])
            if fallback_span:
                for label in labels[1:]:
                    ElementTree.SubElement(
                        element, "{http://www.w3.org/1999/xhtml}span", {"id": label}
                    )
            existing_ids.update(labels)
            changed.add(name)

    ids = {
        name: {
            value
            for element in document.iter()
            for key, value in element.attrib.items()
            if _local_name(key) == "id"
        }
        for name, document in documents.items()
    }
    locations: dict[str, list[str]] = {}
    for name, document_ids in ids.items():
        for element_id in document_ids:
            locations.setdefault(element_id, []).append(name)

    for name, document in documents.items():
        for element in document.iter():
            for key, raw_value in list(element.attrib.items()):
                if _local_name(key) != "href":
                    continue
                parsed = urlsplit(raw_value)
                if (
                    not parsed.scheme
                    and not parsed.netloc
                    and "uri" in element.attrib.get("class", "").split()
                    and re.match(
                        r"^(?:www\.)?[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+(?::\d+)?(?:/|$)",
                        parsed.path,
                    )
                ):
                    element.set(key, "https://" + raw_value)
                    changed.add(name)
                    continue
                if parsed.scheme or parsed.netloc or not parsed.fragment:
                    continue
                target = name
                if parsed.path:
                    target = posixpath.normpath(
                        posixpath.join(posixpath.dirname(name), unquote(parsed.path))
                    )
                fragment = unquote(parsed.fragment)
                if fragment in ids.get(target, set()):
                    continue
                candidates = locations.get(fragment, [])
                if len(candidates) != 1:
                    continue
                relative = posixpath.relpath(candidates[0], posixpath.dirname(name))
                element.set(key, f"{relative}#{parsed.fragment}")
                changed.add(name)

    if not changed:
        return
    ElementTree.register_namespace("", "http://www.w3.org/1999/xhtml")
    ElementTree.register_namespace("epub", "http://www.idpf.org/2007/ops")
    for name in changed:
        members[name] = ElementTree.tostring(
            documents[name], encoding="utf-8", xml_declaration=True
        )
    repaired = path.with_name(path.name + ".repairing")
    try:
        with zipfile.ZipFile(repaired, "w") as target:
            for info in infos:
                target.writestr(info, members[info.filename])
        os.replace(repaired, path)
    finally:
        repaired.unlink(missing_ok=True)


def _reference_id(key: str) -> str:
    suffix = re.sub(r"[^A-Za-z0-9_.:-]+", "-", key).strip("-")
    if not suffix:
        raise ConversionError("A compiled bibliography key cannot form an EPUB anchor.")
    return "ref-" + suffix


def _finalize_epub(
    path: Path,
    bibliography: list[BibliographyEntry],
    series_name: str = "Arxiv Series",
) -> None:
    with zipfile.ZipFile(path) as source:
        infos = source.infolist()
        members = {info.filename: source.read(info.filename) for info in infos}

    try:
        container_xml = ElementTree.fromstring(members["META-INF/container.xml"])
        rootfile = next(
            element.attrib["full-path"]
            for element in container_xml.iter()
            if _local_name(element.tag) == "rootfile"
        )
        package = ElementTree.fromstring(members[rootfile])
        metadata = next(
            element for element in package.iter() if _local_name(element.tag) == "metadata"
        )
    except (KeyError, StopIteration, ElementTree.ParseError) as error:
        raise ConversionError("The EPUB package metadata is incomplete.") from error
    for element in list(metadata):
        if _local_name(element.tag) != "meta":
            continue
        if element.attrib.get("id") == "arxiv-series" or (
            element.attrib.get("refines") == "#arxiv-series"
        ):
            metadata.remove(element)
    opf = "http://www.idpf.org/2007/opf"
    collection = ElementTree.SubElement(
        metadata,
        f"{{{opf}}}meta",
        {"property": "belongs-to-collection", "id": "arxiv-series"},
    )
    collection.text = series_name
    collection_type = ElementTree.SubElement(
        metadata,
        f"{{{opf}}}meta",
        {"refines": "#arxiv-series", "property": "collection-type"},
    )
    collection_type.text = "series"
    ElementTree.register_namespace("", opf)
    ElementTree.register_namespace("dc", "http://purl.org/dc/elements/1.1/")
    members[rootfile] = ElementTree.tostring(
        package, encoding="utf-8", xml_declaration=True
    )

    documents = {
        name: ElementTree.fromstring(data)
        for name, data in members.items()
        if name.lower().endswith((".xhtml", ".html"))
    }
    changed: set[str] = set()
    xhtml = "http://www.w3.org/1999/xhtml"
    if bibliography:
        containers = [
            (name, element)
            for name, document in documents.items()
            for element in document.iter()
            if _local_name(element.tag) == "div"
            and "thebibliography" in element.attrib.get("class", "").split()
        ]
        if len(containers) != 1:
            raise ConversionError("Pandoc did not preserve one compiled bibliography.")
        bibliography_name, bibliography_container = containers[0]
        paragraphs = [
            element
            for element in list(bibliography_container)
            if _local_name(element.tag) == "p"
        ]
        if len(paragraphs) == len(bibliography) + 1:
            paragraphs = paragraphs[1:]
        if len(paragraphs) != len(bibliography):
            raise ConversionError("Pandoc changed the compiled bibliography entry count.")

        ids: dict[str, str] = {}
        labels: dict[str, str] = {}
        for entry, paragraph in zip(bibliography, paragraphs, strict=True):
            reference_id = _reference_id(entry.key)
            if reference_id in ids.values():
                raise ConversionError(
                    "Compiled bibliography keys produce duplicate EPUB anchors."
                )
            ids[entry.key] = reference_id
            labels[entry.key] = entry.label
            paragraph.set("id", reference_id)

        changed.add(bibliography_name)
        citation_count = 0
        for name, document in documents.items():
            for element in document.iter():
                if "citation" not in element.attrib.get("class", "").split():
                    continue
                keys = element.attrib.get("data-cites", "").split()
                missing = [key for key in keys if key not in ids]
                if missing:
                    raise ConversionError(
                        "The compiled bibliography is missing citation key: " + missing[0]
                    )
                if not keys:
                    raise ConversionError("Pandoc emitted a citation without a key.")
                for child in list(element):
                    element.remove(child)
                element.text = "["
                for index, key in enumerate(keys):
                    anchor = ElementTree.SubElement(
                        element,
                        f"{{{xhtml}}}a",
                        {"href": "#" + ids[key]},
                    )
                    anchor.text = labels[key]
                    anchor.tail = "]" if index == len(keys) - 1 else ", "
                citation_count += 1
                changed.add(name)
        if citation_count == 0:
            raise ConversionError("Pandoc did not preserve the paper citations.")
    else:
        existing_ids = {
            value
            for document in documents.values()
            for element in document.iter()
            for key, value in element.attrib.items()
            if _local_name(key) == "id"
        }
        for name, document in documents.items():
            for element in document.iter():
                if "citation" not in element.attrib.get("class", "").split():
                    continue
                if any(
                    _local_name(descendant.tag) == "a"
                    and descendant.attrib.get("href")
                    for descendant in element.iter()
                ):
                    continue
                keys = element.attrib.get("data-cites", "").split()
                if not keys or not " ".join("".join(element.itertext()).split()):
                    raise ConversionError("Pandoc emitted an empty citation.")
                target = _reference_id(keys[0])
                if target not in existing_ids:
                    raise ConversionError(
                        "The bibliography is missing citation key: " + keys[0]
                    )
                children = list(element)
                original_text = element.text
                for child in children:
                    element.remove(child)
                element.text = None
                anchor = ElementTree.SubElement(
                    element,
                    f"{{{xhtml}}}a",
                    {"href": "#" + target},
                )
                anchor.text = original_text
                for child in children:
                    anchor.append(child)
                changed.add(name)

    ElementTree.register_namespace("", xhtml)
    ElementTree.register_namespace("epub", "http://www.idpf.org/2007/ops")
    for name in changed:
        members[name] = ElementTree.tostring(
            documents[name], encoding="utf-8", xml_declaration=True
        )
    repaired = path.with_name(path.name + ".finalizing")
    try:
        with zipfile.ZipFile(repaired, "w") as target:
            for info in infos:
                target.writestr(info, members[info.filename])
        os.replace(repaired, path)
    finally:
        repaired.unlink(missing_ok=True)


def validate_anthology_toc(path: Path, expected_titles: list[str]) -> None:
    """Require one flat EPUB navigation entry per paper, in folder order."""
    try:
        with zipfile.ZipFile(path) as book:
            container = ElementTree.fromstring(book.read("META-INF/container.xml"))
            rootfile = next(
                element.attrib["full-path"]
                for element in container.iter()
                if _local_name(element.tag) == "rootfile"
            )
            package = ElementTree.fromstring(book.read(rootfile))
            nav_items = [
                element
                for element in package.iter()
                if _local_name(element.tag) == "item"
                and "nav" in element.attrib.get("properties", "").split()
            ]
            if len(nav_items) != 1:
                raise ConversionError("The anthology does not declare one table of contents.")
            nav_name = posixpath.normpath(
                posixpath.join(
                    posixpath.dirname(rootfile),
                    unquote(nav_items[0].attrib.get("href", "")),
                )
            )
            navigation = ElementTree.fromstring(book.read(nav_name))
    except (OSError, KeyError, StopIteration, zipfile.BadZipFile, ElementTree.ParseError) as error:
        raise ConversionError("The anthology table of contents is unreadable.") from error

    toc = next(
        (
            element
            for element in navigation.iter()
            if _local_name(element.tag) == "nav"
            and "toc"
            in next(
                (
                    value.split()
                    for key, value in element.attrib.items()
                    if _local_name(key) == "type"
                ),
                [],
            )
        ),
        None,
    )
    if toc is None:
        raise ConversionError("The anthology table of contents is missing.")
    anchors = [element for element in toc.iter() if _local_name(element.tag) == "a"]
    titles = [" ".join("".join(element.itertext()).split()) for element in anchors]
    if titles != expected_titles:
        raise ConversionError("The anthology table of contents must contain paper titles only.")
    if any(
        unquote(urlsplit(element.attrib.get("href", "")).fragment) != f"paper-{index}"
        for index, element in enumerate(anchors, 1)
    ):
        raise ConversionError("The anthology table of contents has an invalid paper target.")


def build_anthology(
    papers: list[tuple[PaperMetadata, Path]],
    title: str,
    output: Path,
) -> None:
    """Package validated paper EPUBs as one flat-navigation anthology."""
    if not papers:
        raise ConversionError("The alphaXiv folder contains no papers.")
    collection_title = re.sub(r"\s+", " ", title).strip() or "alphaXiv Library"
    output.parent.mkdir(parents=True, exist_ok=True)
    xhtml = "http://www.w3.org/1999/xhtml"
    epub = "http://www.idpf.org/2007/ops"
    ElementTree.register_namespace("", xhtml)
    ElementTree.register_namespace("epub", epub)

    members: dict[str, bytes] = {}
    manifest_rows: list[str] = []
    spine_rows: list[str] = []
    nav_rows: list[str] = []

    for paper_index, (metadata, source_path) in enumerate(papers, 1):
        try:
            book = zipfile.ZipFile(source_path)
        except (OSError, zipfile.BadZipFile) as error:
            raise ConversionError(
                f"Paper {paper_index} ({metadata.arxiv_id}) is not a readable EPUB."
            ) from error
        with book:
            try:
                container = ElementTree.fromstring(book.read("META-INF/container.xml"))
                rootfile = next(
                    element.attrib["full-path"]
                    for element in container.iter()
                    if _local_name(element.tag) == "rootfile"
                )
                package = ElementTree.fromstring(book.read(rootfile))
            except (KeyError, StopIteration, ElementTree.ParseError) as error:
                raise ConversionError(
                    f"Paper {paper_index} ({metadata.arxiv_id}) has incomplete EPUB metadata."
                ) from error
            package_dir = posixpath.dirname(rootfile)
            items = {
                element.attrib["id"]: element
                for element in package.iter()
                if _local_name(element.tag) == "item"
                and element.attrib.get("id")
                and element.attrib.get("href")
            }
            nav_ids = {
                item_id
                for item_id, element in items.items()
                if "nav" in element.attrib.get("properties", "").split()
            }
            cover_targets = {
                posixpath.normpath(
                    posixpath.join(package_dir, unquote(element.attrib.get("href", "")))
                )
                for element in package.iter()
                if _local_name(element.tag) == "reference"
                and element.attrib.get("type") == "cover"
            }
            skipped_ids = nav_ids | {
                item_id
                for item_id, element in items.items()
                if "cover-image" in element.attrib.get("properties", "").split()
                or posixpath.normpath(
                    posixpath.join(package_dir, unquote(element.attrib.get("href", "")))
                )
                in cover_targets
            }
            member_spine = [
                element.attrib.get("idref", "")
                for element in package.iter()
                if _local_name(element.tag) == "itemref"
                and element.attrib.get("idref", "") not in skipped_ids
            ]
            if not member_spine or member_spine[0] not in items:
                raise ConversionError(
                    f"Paper {paper_index} ({metadata.arxiv_id}) has no body reading order."
                )

            id_map: dict[str, str] = {}
            href_map: dict[str, str] = {}
            for old_id, item in items.items():
                if old_id in skipped_ids:
                    continue
                raw_href = item.attrib["href"]
                relative = posixpath.normpath(unquote(raw_href))
                if relative.startswith("../") or relative.startswith("/"):
                    raise ConversionError(
                        f"Paper {paper_index} ({metadata.arxiv_id}) has an unsafe manifest path."
                    )
                source_name = posixpath.normpath(posixpath.join(package_dir, relative))
                try:
                    data = book.read(source_name)
                except KeyError as error:
                    raise ConversionError(
                        f"Paper {paper_index} ({metadata.arxiv_id}) is missing {raw_href}."
                    ) from error
                new_id = f"p{paper_index:03d}-{old_id}"
                new_href = f"papers/p{paper_index:03d}/{relative}"
                id_map[old_id] = new_id
                href_map[old_id] = new_href
                if old_id == member_spine[0]:
                    try:
                        document = ElementTree.fromstring(data)
                        body = next(
                            element
                            for element in document.iter()
                            if _local_name(element.tag) == "body"
                        )
                    except (StopIteration, ElementTree.ParseError) as error:
                        raise ConversionError(
                            f"Paper {paper_index} ({metadata.arxiv_id}) has an invalid first chapter."
                        ) from error
                    paper_id = f"paper-{paper_index}"
                    if any(
                        value == paper_id
                        for element in document.iter()
                        for key, value in element.attrib.items()
                        if _local_name(key) == "id"
                    ):
                        raise ConversionError(
                            f"Paper {paper_index} ({metadata.arxiv_id}) conflicts with its anthology anchor."
                        )
                    heading = ElementTree.Element(
                        f"{{{xhtml}}}h1", {"id": paper_id, "class": "paper-title"}
                    )
                    heading.text = metadata.title
                    body.insert(0, heading)
                    data = ElementTree.tostring(document, encoding="utf-8", xml_declaration=True)
                members["EPUB/" + new_href] = data
                properties = " ".join(
                    value
                    for value in item.attrib.get("properties", "").split()
                    if value not in {"nav", "cover-image"}
                )
                properties_attr = (
                    f' properties="{html.escape(properties, quote=True)}"' if properties else ""
                )
                manifest_rows.append(
                    f'<item id="{html.escape(new_id, quote=True)}" '
                    f'href="{html.escape(quote(new_href, safe="/"), quote=True)}" '
                    f'media-type="{html.escape(item.attrib.get("media-type", "application/octet-stream"), quote=True)}"'
                    f"{properties_attr}/>"
                )

            for old_id in member_spine:
                if old_id not in id_map:
                    raise ConversionError(
                        f"Paper {paper_index} ({metadata.arxiv_id}) has an incomplete reading order."
                    )
                spine_rows.append(f'<itemref idref="{html.escape(id_map[old_id], quote=True)}"/>')
            first_href = href_map[member_spine[0]]
            nav_rows.append(
                f'<li><a href="{html.escape(quote(first_href, safe="/") + f"#paper-{paper_index}", quote=True)}">'
                f"{html.escape(metadata.title)}</a></li>"
            )

    with tempfile.TemporaryDirectory(prefix="alphaxiv-anthology-") as temporary:
        cover_svg = Path(temporary) / "cover.svg"
        cover_png = Path(temporary) / "cover.png"
        write_collection_cover(collection_title, len(papers), cover_svg)
        rasterize_cover(cover_svg, cover_png)
        members["EPUB/media/cover.png"] = cover_png.read_bytes()

    cover_document = '''<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><head><title>Cover</title></head><body><section id="cover" epub:type="cover"><img src="media/cover.png" alt="Cover"/></section></body></html>'''
    navigation = f'''<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><head><title>Table of Contents</title></head><body><nav epub:type="toc"><h1>Table of Contents</h1><ol>{"".join(nav_rows)}</ol></nav></body></html>'''
    identifier = re.sub(r"[^a-z0-9]+", "-", collection_title.casefold()).strip("-") or "library"
    package = f'''<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="bookid">urn:alphaxiv-library:{html.escape(identifier)}</dc:identifier><dc:title>{html.escape(collection_title)}</dc:title><dc:creator>alphaXiv Library</dc:creator><dc:language>en</dc:language></metadata>
<manifest><item id="coverdoc" href="cover.xhtml" media-type="application/xhtml+xml"/><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/><item id="coverimage" href="media/cover.png" media-type="image/png" properties="cover-image"/>{"".join(manifest_rows)}</manifest>
<spine><itemref idref="coverdoc"/><itemref idref="nav"/>{"".join(spine_rows)}</spine>
<guide><reference type="cover" title="Cover" href="cover.xhtml"/></guide>
</package>'''
    container = b'''<?xml version="1.0" encoding="utf-8"?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0"><rootfiles><rootfile full-path="EPUB/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>'''
    members["META-INF/container.xml"] = container
    members["EPUB/content.opf"] = package.encode()
    members["EPUB/cover.xhtml"] = cover_document.encode()
    members["EPUB/nav.xhtml"] = navigation.encode()

    staging = output.with_name(output.name + ".building")
    try:
        with zipfile.ZipFile(staging, "w", compression=zipfile.ZIP_DEFLATED) as target:
            target.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
            for name, data in members.items():
                target.writestr(name, data)
        os.replace(staging, output)
    finally:
        staging.unlink(missing_ok=True)
    validate_epub(output, require_png_cover=True, require_front_matter=True)
    validate_anthology_toc(output, [metadata.title for metadata, _path in papers])


def _find_pandoc() -> str:
    for candidate in (
        shutil.which("pandoc"),
        "/opt/homebrew/bin/pandoc",
        "/usr/local/bin/pandoc",
    ):
        if candidate and Path(candidate).is_file():
            return candidate
    raise ConversionError("Pandoc is required. Install it with: brew install pandoc")


def _convert_graphic_to_png(source: Path, output: Path) -> None:
    try:
        result = subprocess.run(
            ["/usr/bin/sips", "-s", "format", "png", "-Z", "2000", str(source), "--out", str(output)],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        result = None
    if result is not None and not result.returncode and output.is_file() and output.stat().st_size:
        return
    output.unlink(missing_ok=True)
    if source.suffix.lower() == ".eps":
        ghostscript = next(
            (
                candidate
                for candidate in (shutil.which("gs"), "/opt/homebrew/bin/gs", "/usr/local/bin/gs")
                if candidate and Path(candidate).is_file()
            ),
            None,
        )
        if ghostscript:
            try:
                result = subprocess.run(
                    [
                        ghostscript,
                        "-dSAFER",
                        "-dBATCH",
                        "-dNOPAUSE",
                        "-sDEVICE=pngalpha",
                        "-r144",
                        "-dEPSCrop",
                        f"-sOutputFile={output}",
                        str(source),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
            except subprocess.TimeoutExpired:
                result = None
            if result is not None and not result.returncode and output.is_file() and output.stat().st_size:
                return
            output.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix="arxiv-figure-") as temporary:
        try:
            result = subprocess.run(
                ["/usr/bin/qlmanage", "-t", "-s", "2000", "-o", temporary, str(source)],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            result = None
        previews = list(Path(temporary).glob("*.png"))
        if result is None or result.returncode or len(previews) != 1:
            raise ConversionError(f"Could not convert figure {source.name} to a Kindle-safe image.")
        shutil.copy2(previews[0], output)


def prepare_graphics(source_dir: Path, *, converter=None) -> int:
    converter = converter or _convert_graphic_to_png
    root = source_dir.resolve()
    pattern = re.compile(
        r"(?P<prefix>\\includegraphics(?:\[[^]]*\])?\s*\{|\\epsfbox\s*\{)"
        r"(?P<target>[^{}]+)(?P<suffix>\})"
    )
    converted: dict[Path, Path] = {}
    count = 0
    for tex_path in sorted(source_dir.rglob("*.tex")):
        original = tex_path.read_text(encoding="utf-8", errors="replace")

        def replace(match: re.Match) -> str:
            nonlocal count
            raw_target = match.group("target").strip()
            if "\\" in raw_target:
                return match.group(0)
            target = tex_path.parent / raw_target
            candidates = [target] if target.suffix else [
                target.with_suffix(extension)
                for extension in (".pdf", ".png", ".jpg", ".jpeg", ".svg", ".eps")
            ]
            source = next((path for path in candidates if path.is_file()), None)
            if source is None or source.suffix.lower() not in {".pdf", ".eps"}:
                return match.group(0)
            source = source.resolve()
            if root not in source.parents:
                raise ConversionError("A figure path escapes the extracted source directory.")
            if source not in converted:
                output = source.with_name(source.stem + ".arxiv-kindle.png")
                converter(source, output)
                if not output.is_file() or not output.stat().st_size:
                    raise ConversionError(f"Figure conversion produced no image for {source.name}.")
                converted[source] = output
                count += 1
            replacement = Path(
                os.path.relpath(converted[source], tex_path.parent.resolve())
            ).as_posix()
            if match.group("prefix").lstrip().startswith(r"\epsfbox"):
                return rf"\includegraphics{{{replacement}}}"
            return f"{match.group('prefix')}{replacement}{match.group('suffix')}"

        rewritten = pattern.sub(replace, original)
        if rewritten != original:
            tex_path.write_text(rewritten, encoding="utf-8")
    return count


def prepare_table_labels(source_dir: Path) -> int:
    """Remove print-only table centering that separates Pandoc captions and labels."""
    joined_table_pattern = re.compile(
        r"(?m)^[ \t]*%[ \t]*(\\end\{table\*?\})[ \t]*\n"
        r"[ \t]*%[ \t]*(\\begin\{table\*?\}(?:\[[^]\n]*\])?)[ \t]*$"
    )
    table_pattern = re.compile(
        r"(\\begin\{(?P<environment>table\*?)\})(?P<body>.*?)(\\end\{(?P=environment)\})",
        re.DOTALL,
    )
    center_pattern = re.compile(
        r"(\\begin\{center\})(?P<body>.*?)(\\end\{center\})", re.DOTALL
    )
    math_array_pattern = re.compile(
        r"\\begin\{displaymath\}\s*\\begin\{array\}(?P<body>.*?)"
        r"\\end\{array\}\s*\\end\{displaymath\}",
        re.DOTALL,
    )
    minipage_pattern = re.compile(
        r"\\begin\{minipage\}(?:\[[^]]*\])?\s*\{[^{}]*\}"
        r"(?P<body>.*?)\\end\{minipage\}",
        re.DOTALL,
    )
    count = 0

    def normalize_table(table_match: re.Match) -> str:
        nonlocal count
        raw_body = table_match.group("body")
        minipages = list(minipage_pattern.finditer(raw_body))
        if len(minipages) > 1 and all(
            re.search(r"\\begin\{tabular\*?\}", match.group("body"))
            for match in minipages
        ):
            count += len(minipages)
            return "\n".join(
                r"\begin{table}" + match.group("body") + r"\end{table}"
                for match in minipages
            )

        body, arrays = math_array_pattern.subn(
            lambda match: r"\begin{tabular}"
            + match.group("body")
            + r"\end{tabular}",
            raw_body,
        )
        body, removed = center_pattern.subn(
            lambda match: match.group("body"), body
        )
        count += arrays + removed
        if table_match.group("environment") == "table*":
            count += 1
        return r"\begin{table}" + body + r"\end{table}"

    for tex_path in sorted(source_dir.rglob("*.tex")):
        original = tex_path.read_text(encoding="utf-8", errors="replace")
        separated, reopened = joined_table_pattern.subn(r"\1\n\2", original)
        count += reopened
        rewritten = table_pattern.sub(normalize_table, separated)
        if rewritten != original:
            tex_path.write_text(rewritten, encoding="utf-8")
    return count


def prepare_local_heading_styles(source_dir: Path) -> int:
    """Keep local print styles from recursively redefining Pandoc headings."""
    heading = r"(?:section|subsection|subsubsection|paragraph|subparagraph)"
    definition = re.compile(
        rf"\\(?:def|gdef|edef|xdef)\s*\\{heading}\b|"
        rf"\\(?:newcommand|renewcommand|providecommand)\s*\{{?\s*\\{heading}\b"
    )
    conflicting: set[str] = set()
    for style in source_dir.rglob("*.sty"):
        text = re.sub(
            r"(?m)(?<!\\)%.*$",
            "",
            style.read_text(encoding="utf-8", errors="replace"),
        )
        if definition.search(text):
            conflicting.add(style.stem)
            conflicting.add(style.relative_to(source_dir).with_suffix("").as_posix())
    if not conflicting:
        return 0

    package = re.compile(
        r"\\usepackage(?P<options>\s*\[[^]\n]*\])?\s*\{(?P<names>[^{}\n]+)\}"
    )
    removed = 0
    for tex_path in source_dir.rglob("*.tex"):
        original = tex_path.read_text(encoding="utf-8", errors="replace")

        def omit_conflict(match: re.Match) -> str:
            nonlocal removed
            names = [name.strip() for name in match.group("names").split(",")]
            kept = [name for name in names if name not in conflicting]
            removed += len(names) - len(kept)
            if not kept:
                return ""
            return rf"\usepackage{match.group('options') or ''}{{{','.join(kept)}}}"

        rewritten = package.sub(omit_conflict, original)
        if rewritten != original:
            tex_path.write_text(rewritten, encoding="utf-8")
    return removed


def prepare_abstracts(source_dir: Path) -> int:
    """Keep abstract footnotes out of Pandoc's lossy EPUB title page."""
    begin = re.compile(r"\\begin\s*\{abstract\}")
    end = re.compile(r"\\end\s*\{abstract\}")
    count = 0
    for tex_path in sorted(source_dir.rglob("*.tex")):
        original = tex_path.read_text(encoding="utf-8", errors="replace")
        rewritten, opened = begin.subn(lambda _: r"\section*{Abstract}", original)
        rewritten, closed = end.subn("", rewritten)
        if opened != closed:
            continue
        if opened:
            tex_path.write_text(rewritten, encoding="utf-8")
            count += opened
    return count


def prepare_latex_209_front_matter(source_dir: Path) -> int:
    """Translate common LaTeX 2.09 front-matter macros into readable content."""
    documentstyle = re.compile(r"\\documentstyle(?:\[[^]]*\])?\s*\{[^{}]+\}")
    count = 0
    for tex_path in sorted(source_dir.rglob("*.tex")):
        original = tex_path.read_text(encoding="utf-8", errors="replace")
        if not documentstyle.search(original):
            continue
        details: list[str] = []
        preprint = _command_value(original, "preprintnumber")
        affiliation = _command_value(original, "inst")
        received = _command_value(original, "recdate")
        abstract = _command_value(original, "abst")
        if preprint:
            details.append(r"\begin{flushright}" + preprint + r"\end{flushright}")
        if affiliation:
            details.append(r"\begin{center}\emph{" + affiliation + r"}\end{center}")
        if received:
            details.append(r"\begin{center}" + received + r"\end{center}")
        if abstract:
            blocks = [
                r"\section*{Abstract}"
                + "\n"
                + "\n".join(details + [abstract])
            ]
        else:
            blocks = details
        rewritten = documentstyle.sub(lambda _: r"\documentclass{article}", original, count=1)
        if blocks:
            marker = re.search(r"\\maketitle\b", rewritten)
            if marker:
                position = marker.end()
            else:
                document = re.search(r"\\begin\s*\{document\}", rewritten)
                position = document.end() if document else 0
            rewritten = rewritten[:position] + "\n" + "\n".join(blocks) + rewritten[position:]
        tex_path.write_text(rewritten, encoding="utf-8")
        count += 1
    return count


def _braced_argument(text: str, position: int) -> tuple[int, int] | None:
    while position < len(text) and text[position].isspace():
        position += 1
    if position >= len(text) or text[position] != "{":
        return None
    depth = 0
    escaped = False
    for index in range(position, len(text)):
        char = text[index]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return position + 1, index
    return None


_PROTECTED_LITERAL_ENVIRONMENT = re.compile(
    _TEX_COMMAND_PREFIX
    + r"begin\s*\{\s*"
    r"(?P<environment>verbatim\*|verbatim|Verbatim|lstlisting|minted|alltt)"
    r"\s*\}"
    r".*?^[ \t]*(?<!\\)\\end\s*\{\s*(?P=environment)\s*\}[ \t]*(?=\r?$)",
    re.DOTALL | re.MULTILINE,
)


def _searchable_tex_source(original: str) -> str:
    """Mask comments and literal environments without changing source offsets."""
    masked = list(original)
    index = 0
    while index < len(original):
        if original[index] != "%":
            index += 1
            continue
        slash_count = 0
        before = index - 1
        while before >= 0 and original[before] == "\\":
            slash_count += 1
            before -= 1
        if slash_count % 2:
            index += 1
            continue
        while index < len(original) and original[index] not in "\r\n":
            masked[index] = " "
            index += 1
    searchable = "".join(masked)
    return _PROTECTED_LITERAL_ENVIRONMENT.sub(
        lambda match: "".join(
            char if char in "\r\n" else " " for char in match.group(0)
        ),
        searchable,
    )


def _read_tex_preserving_bytes(tex_path: Path) -> str:
    with tex_path.open(
        "r", encoding="utf-8", errors="surrogateescape", newline=""
    ) as source:
        return source.read()


def _write_tex_preserving_bytes(tex_path: Path, text: str) -> None:
    with tex_path.open(
        "w", encoding="utf-8", errors="surrogateescape", newline=""
    ) as output:
        output.write(text)


_INLINE_COMMAND_DEFINITION = re.compile(
    _TEX_COMMAND_PREFIX
    + r"(?:newcommand|renewcommand|providecommand)\*?\s*"
    r"(?:\{\s*\\[A-Za-z@]+\s*\}|\\[A-Za-z@]+)\s*"
    r"\[(?P<arity>[1-9]\d*)\]\s*"
)


def _rewrite_inline_definitions(source_dir: Path, body_pattern: re.Pattern[str]) -> int:
    count = 0
    for tex_path in sorted(source_dir.rglob("*.tex")):
        original = _read_tex_preserving_bytes(tex_path)
        searchable = _searchable_tex_source(original)
        output: list[str] = []
        cursor = 0
        for match in _INLINE_COMMAND_DEFINITION.finditer(searchable):
            if match.start() < cursor:
                continue
            body = _braced_argument(searchable, match.end())
            if body is None:
                continue
            body_match = body_pattern.fullmatch(searchable[body[0] : body[1]])
            if body_match is None:
                continue
            argument = int(body_match.group("argument"))
            if not 1 <= argument <= int(match.group("arity")):
                continue
            output.append(original[cursor : body[0]])
            output.append(f"#{argument}")
            cursor = body[1]
            count += 1
        if output:
            output.append(original[cursor:])
            _write_tex_preserving_bytes(tex_path, "".join(output))
    return count


def prepare_inline_box_commands(source_dir: Path) -> int:
    """Unwrap pure environment-backed command formatting before Pandoc sees it."""
    box_body = re.compile(
        r"\s*\\begin\s*\{\s*(?P<environment>[^{}\s]+)\s*\}"
        r"(?:\s*\[(?:\\.|[^]\\])*\])?"
        r"\s*\{\s*#(?P<argument>\d+)\s*\}"
        r"\s*\\end\s*\{\s*(?P=environment)\s*\}"
        r"\s*\\xspace\b\s*",
        re.DOTALL,
    )
    return _rewrite_inline_definitions(source_dir, box_body)


def prepare_inline_font_commands(source_dir: Path) -> int:
    """Unwrap pure required-argument font-selection commands before Pandoc sees them."""
    font_body = re.compile(
        r"\s*(?P<outer>\{\s*)?\\usefont\s*\{[^{}]*\}\s*\{[^{}]*\}"
        r"\s*\{[^{}]*\}\s*\{[^{}]*\}\s*#(?P<argument>\d+)\s*"
        r"(?(outer)\})\s*",
        re.DOTALL,
    )
    return _rewrite_inline_definitions(source_dir, font_body)


def prepare_inline_small_caps(source_dir: Path) -> int:
    """Translate inline small-caps environments into Pandoc-safe text formatting."""
    caption = re.compile(_TEX_COMMAND_PREFIX + r"caption\s*")
    pattern = re.compile(
        rf"(?<!\\)(?P<begin_pairs>{_TEX_SLASH_PAIRS})\\begin\s*\{{sc\}}"
        rf"(?P<body>[^\r\n]*?)"
        rf"(?<!\\)(?P<end_pairs>{_TEX_SLASH_PAIRS})\\end\s*\{{sc\}}"
    )
    count = 0
    for tex_path in sorted(source_dir.rglob("*.tex")):
        original = _read_tex_preserving_bytes(tex_path)
        searchable = _searchable_tex_source(original)
        output: list[str] = []
        cursor = 0
        for caption_match in caption.finditer(searchable):
            if caption_match.start() < cursor:
                continue
            argument = _braced_argument(searchable, caption_match.end())
            if argument is None:
                continue
            body_start, body_end = argument
            normalized: list[str] = []
            body_cursor = body_start
            replacements = 0
            for match in pattern.finditer(searchable, body_start, body_end):
                normalized.append(original[body_cursor : match.start()])
                normalized.append(
                    original[
                        match.start("begin_pairs") : match.end("begin_pairs")
                    ]
                    + r"\textsc{"
                    + original[match.start("body") : match.end("body")]
                    + original[match.start("end_pairs") : match.end("end_pairs")]
                    + "}"
                )
                body_cursor = match.end()
                replacements += 1
            if not replacements:
                continue
            normalized.append(original[body_cursor:body_end])
            output.append(original[cursor:body_start])
            output.append("".join(normalized))
            cursor = body_end
            count += replacements
        if output:
            output.append(original[cursor:])
            _write_tex_preserving_bytes(tex_path, "".join(output))
    return count


def _skip_tex_trivia(text: str, position: int) -> int:
    """Skip TeX whitespace and unescaped comments between command arguments."""
    while position < len(text):
        if text[position].isspace():
            position += 1
        elif text[position] == "%" and (position == 0 or text[position - 1] != "\\"):
            newline = text.find("\n", position)
            position = len(text) if newline < 0 else newline + 1
        else:
            break
    return position


def prepare_compiled_bibliography(root: Path) -> list[BibliographyEntry]:
    """Expose an arXiv-compiled BBL to Pandoc and retain its citation labels."""
    preferred = root.with_suffix(".bbl")
    candidates = sorted(root.parent.rglob("*.bbl"))
    if preferred.is_file():
        bbl = preferred
    elif len(candidates) == 1:
        bbl = candidates[0]
    elif not candidates:
        return []
    else:
        raise ConversionError("Multiple compiled bibliographies were found.")

    bbl_text = bbl.read_text(encoding="utf-8", errors="replace")
    searchable_bbl = re.sub(
        r"(?m)(?<!\\)%[^\n]*",
        lambda match: " " * len(match.group(0)),
        bbl_text,
    )
    entries: list[BibliographyEntry] = []
    seen: set[str] = set()
    for match in re.finditer(r"\\bibitem\b", searchable_bbl):
        position = _skip_tex_trivia(searchable_bbl, match.end())
        raw_label = ""
        if position < len(searchable_bbl) and searchable_bbl[position] == "[":
            closing = position + 1
            escaped = False
            brace_depth = 0
            while closing < len(searchable_bbl):
                char = searchable_bbl[closing]
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == "{":
                    brace_depth += 1
                elif char == "}":
                    brace_depth = max(0, brace_depth - 1)
                elif char == "]" and brace_depth == 0:
                    break
                closing += 1
            if closing >= len(searchable_bbl):
                raise ConversionError("A compiled bibliography label is malformed.")
            raw_label = bbl_text[position + 1 : closing]
            position = _skip_tex_trivia(searchable_bbl, closing + 1)
        key_argument = _braced_argument(searchable_bbl, position)
        if key_argument is None:
            raise ConversionError("A compiled bibliography key is malformed.")
        key = bbl_text[key_argument[0] : key_argument[1]].strip()
        if not key:
            raise ConversionError("A compiled bibliography key is empty.")
        if key in seen:
            raise ConversionError(f"The compiled bibliography has duplicate bibliography key: {key}")
        seen.add(key)
        label = _strip_tex(raw_label) or str(len(entries) + 1)
        entries.append(BibliographyEntry(key=key, label=label))
    if not entries:
        raise ConversionError("The compiled bibliography contains no entries.")

    normalized_bbl = re.sub(r"\\href\s+\{", r"\\href{", bbl_text)
    normalized_bbl = re.sub(
        r"(?<!\n)\n(\\bibitem\b)", r"\n\n\1", normalized_bbl
    )
    if normalized_bbl != bbl_text:
        bbl.write_text(normalized_bbl, encoding="utf-8")

    original = root.read_text(encoding="utf-8", errors="replace")
    rewritten = re.sub(r"\\bibliographystyle\s*\{[^{}]*\}", "", original)
    rewritten = re.sub(r"\\bibliography\s*\{[^{}]*\}", "", rewritten)
    rewritten = re.sub(
        r"\\(?:input|include)\s*\{[^{}]*\.bbl\}", "", rewritten
    )
    ending = list(re.finditer(r"\\end\s*\{document\}", rewritten))
    if not ending:
        raise ConversionError("The root TeX document has no end marker.")
    relative_bbl = bbl.relative_to(root.parent).as_posix()
    block = "\n\\section*{References}\n\\input{" + relative_bbl + "}\n"
    position = ending[-1].start()
    rewritten = rewritten[:position] + block + rewritten[position:]
    root.write_text(rewritten, encoding="utf-8")
    return entries


def prepare_ieee_title_abstracts(source_dir: Path) -> int:
    """Unwrap IEEE title-area content that Pandoc otherwise discards."""
    pattern = re.compile(r"\\IEEEtitleabstractindextext\s*")
    count = 0
    for path in sorted(source_dir.rglob("*.tex")):
        original = path.read_text(encoding="utf-8", errors="replace")
        output: list[str] = []
        cursor = 0
        for match in pattern.finditer(original):
            if match.start() < cursor:
                continue
            content = _braced_argument(original, match.end())
            if content is None:
                continue
            output.append(original[cursor : match.start()])
            output.append(original[content[0] : content[1]])
            cursor = content[1] + 1
            count += 1
        if output:
            output.append(original[cursor:])
            path.write_text("".join(output), encoding="utf-8")
    return count


def prepare_prompt_blocks(source_dir: Path) -> int:
    """Turn common prompt boxes into readable nested quotations."""
    count = 0

    def message_box(match: re.Match) -> str:
        options = match.group(1) or ""
        title = re.search(r"frametitle=([^,\]]+)", options)
        prefix = f"\\textbf{{{title.group(1).strip()}}}\n" if title else ""
        return prefix + r"\begin{quote}"

    def caption_labels(text: str) -> str:
        output: list[str] = []
        cursor = 0
        for match in re.finditer(r"\\caption\s*", text):
            caption = _braced_argument(text, match.end())
            if caption is None:
                continue
            label_match = re.match(r"\s*\\label\s*", text[caption[1] + 1 :])
            if label_match is None:
                continue
            label_start = caption[1] + 1 + label_match.end()
            label = _braced_argument(text, label_start)
            if label is None:
                continue
            output.append(text[cursor : match.start()])
            output.append(
                r"\paragraph{"
                + text[caption[0] : caption[1]]
                + r"}\label{"
                + text[label[0] : label[1]]
                + "}"
            )
            cursor = label[1] + 1
        if not output:
            return text
        output.append(text[cursor:])
        return "".join(output)

    def prompt_block(match: re.Match) -> str:
        body = caption_labels(match.group("body"))
        body = re.sub(
            r"\\begin\{mymessagebox\}(\[[^]]*\])?", message_box, body
        )
        body = re.sub(
            r"\\end\{mymessagebox\}", lambda _: r"\end{quote}", body
        )
        return r"\begin{quote}" + body + r"\end{quote}"

    for path in sorted(source_dir.rglob("*.tex")):
        original = path.read_text(encoding="utf-8", errors="replace")
        rewritten, prompts = re.subn(
            r"\\begin\{prompt\}(?:\[[^]]*\])?(?P<body>.*?)\\end\{prompt\}",
            prompt_block,
            original,
            flags=re.DOTALL,
        )
        rewritten, opened_boxes = re.subn(
            r"\\begin\{mymessagebox\}(\[[^]]*\])?", message_box, rewritten
        )
        rewritten, closed_boxes = re.subn(
            r"\\end\{mymessagebox\}", lambda _: r"\end{quote}", rewritten
        )
        if opened_boxes != closed_boxes:
            continue
        changes = prompts + opened_boxes
        if changes:
            path.write_text(rewritten, encoding="utf-8")
            count += changes
    return count


def prepare_scaled_content(source_dir: Path) -> int:
    """Drop print-only scaling while retaining reflowable tables, math, and text."""
    pattern = re.compile(r"\\(?P<command>resizebox\*?|scalebox)(?![A-Za-z@])")
    count = 0
    for tex_path in sorted(source_dir.rglob("*.tex")):
        original = tex_path.read_text(encoding="utf-8", errors="replace")
        output: list[str] = []
        cursor = 0
        for match in pattern.finditer(original):
            if match.start() < cursor:
                continue
            first_position = _skip_tex_trivia(original, match.end())
            first = _braced_argument(original, first_position)
            if first is None:
                continue
            position = _skip_tex_trivia(original, first[1] + 1)
            if match.group("command").startswith("resizebox"):
                second = _braced_argument(original, position)
                if second is None:
                    continue
                position = _skip_tex_trivia(original, second[1] + 1)
            elif position < len(original) and original[position] == "[":
                closing = original.find("]", position + 1)
                if closing < 0:
                    continue
                position = _skip_tex_trivia(original, closing + 1)
            content = _braced_argument(original, position)
            if content is None:
                continue
            body = original[content[0] : content[1]]
            stripped = body.strip()
            if stripped.startswith("$$") and stripped.endswith("$$") and len(stripped) > 4:
                body = "\\[" + stripped[2:-2].strip() + "\\]"
            elif stripped.startswith("$") and stripped.endswith("$") and len(stripped) > 2:
                body = "\\ensuremath{" + stripped[1:-1] + "}"
            elif stripped.startswith(r"\(") and stripped.endswith(r"\)"):
                body = "\\ensuremath{" + stripped[2:-2] + "}"
            output.append(original[cursor : match.start()])
            output.append(body)
            cursor = content[1] + 1
            count += 1
        if not output:
            continue
        output.append(original[cursor:])
        tex_path.write_text("".join(output), encoding="utf-8")
    return count


def prepare_inline_equations(source_dir: Path) -> int:
    """Promote equations introduced by a colon out of fragile inline layout."""
    pattern = re.compile(
        r"(?P<prefix>:[ \t]*(?:\n[ \t]*)?)\$(?!\$)"
        r"(?P<body>(?:\\.|[^$\\])*)\$(?!\$)"
    )
    count = 0
    for tex_path in source_dir.rglob("*.tex"):
        original = tex_path.read_text(encoding="utf-8", errors="replace")

        def promote(match: re.Match) -> str:
            nonlocal count
            if "=" not in match.group("body"):
                return match.group(0)
            count += 1
            return match.group("prefix") + r"\[" + match.group("body") + r"\]"

        rewritten = pattern.sub(promote, original)
        if rewritten != original:
            tex_path.write_text(rewritten, encoding="utf-8")
    return count


def prepare_alltt_blocks(source_dir: Path) -> int:
    """Preserve alltt whitespace as a reflowable EPUB code block."""
    pattern = re.compile(
        r"(?m)^(?P<indent>[ \t]*)\\begin\{alltt\}[ \t]*\n"
        r"(?P<body>.*?)"
        r"^(?P=indent)\\end\{alltt\}[ \t]*$",
        re.DOTALL,
    )
    count = 0
    for tex_path in sorted(source_dir.rglob("*.tex")):
        original = tex_path.read_text(encoding="utf-8", errors="replace")
        rewritten, changes = pattern.subn(
            lambda match: match.group("indent")
            + r"\begin{verbatim}"
            + "\n"
            + match.group("body")
            + match.group("indent")
            + r"\end{verbatim}",
            original,
        )
        if changes:
            tex_path.write_text(rewritten, encoding="utf-8")
            count += changes
    return count


def _standardize_column_spec(specification: str, custom_types: dict[str, int]) -> str:
    output: list[str] = []
    index = 0
    while index < len(specification):
        char = specification[index]
        if char == "{":
            argument = _braced_argument(specification, index)
            if argument is None:
                output.append(char)
                index += 1
            else:
                output.append(specification[index : argument[1] + 1])
                index = argument[1] + 1
            continue
        if char not in custom_types:
            output.append(char)
            index += 1
            continue
        output.append("c")
        index += 1
        for _ in range(custom_types[char]):
            argument = _braced_argument(specification, index)
            if argument is None:
                break
            index = argument[1] + 1
    return "".join(output)


def prepare_column_types(source_dir: Path) -> int:
    """Replace array-package column aliases that Pandoc cannot parse."""
    definition_pattern = re.compile(
        r"\\newcolumntype\s*\{(?P<name>[^{}\s])\}\s*"
        r"(?:\[(?P<arguments>\d+)\]\s*)?"
        r"\{(?:[^{}]|\{[^{}]*\})*\}\s*"
    )
    tex_files = sorted(source_dir.rglob("*.tex"))
    contents = {
        path: path.read_text(encoding="utf-8", errors="replace") for path in tex_files
    }
    custom_types: dict[str, int] = {}
    for text in contents.values():
        for match in definition_pattern.finditer(text):
            custom_types[match.group("name")] = int(match.group("arguments") or 0)
    if not custom_types:
        return 0

    tabular = re.compile(r"\\begin\{tabular(?P<star>\*)?\}")

    def rewrite_specs(text: str) -> str:
        output: list[str] = []
        cursor = 0
        for match in tabular.finditer(text):
            position = match.end()
            if match.group("star"):
                width = _braced_argument(text, position)
                if width is None:
                    continue
                position = width[1] + 1
            while position < len(text) and text[position].isspace():
                position += 1
            if position < len(text) and text[position] == "[":
                closing = text.find("]", position + 1)
                if closing < 0:
                    continue
                position = closing + 1
            specification = _braced_argument(text, position)
            if specification is None:
                continue
            start, end = specification
            output.append(text[cursor:start])
            output.append(_standardize_column_spec(text[start:end], custom_types))
            cursor = end
        output.append(text[cursor:])
        return "".join(output)

    removed = 0
    for path, original in contents.items():
        stripped, count = definition_pattern.subn("", original)
        removed += count
        rewritten = rewrite_specs(stripped)
        if rewritten != original:
            path.write_text(rewritten, encoding="utf-8")
    return removed


def _pandoc_error_detail(output: str) -> str:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    while lines and re.fullmatch(r"\^+", lines[-1]):
        lines.pop()
    detail = "\n".join(lines[-5:]) or "unknown error"
    return detail if len(detail) <= 800 else "..." + detail[-797:]


def convert_source(
    source_dir: Path,
    arxiv_id: str,
    output: Path,
    *,
    pandoc: str | None = None,
) -> PaperMetadata:
    prepare_graphics(source_dir)
    prepare_inline_box_commands(source_dir)
    prepare_inline_font_commands(source_dir)
    prepare_inline_small_caps(source_dir)
    prepare_abstracts(source_dir)
    prepare_ieee_title_abstracts(source_dir)
    prepare_prompt_blocks(source_dir)
    prepare_latex_209_front_matter(source_dir)
    prepare_scaled_content(source_dir)
    prepare_inline_equations(source_dir)
    prepare_alltt_blocks(source_dir)
    prepare_column_types(source_dir)
    prepare_table_labels(source_dir)
    prepare_local_heading_styles(source_dir)
    root = find_root_tex(source_dir)
    compiled_bibliography = prepare_compiled_bibliography(root)
    tex = root.read_text(encoding="utf-8", errors="replace")
    metadata = extract_metadata(tex, arxiv_id)
    cover_svg = source_dir / ".arxiv-kindle-cover.svg"
    cover_png = source_dir / ".arxiv-kindle-cover.png"
    write_cover(metadata, cover_svg)
    rasterize_cover(cover_svg, cover_png)
    require_abstract = any(
        re.search(
            r"\\section\*\s*\{Abstract\}",
            re.sub(
                r"(?m)(?<!\\)%.*$",
                "",
                path.read_text(encoding="utf-8", errors="replace"),
            ),
        )
        for path in source_dir.rglob("*.tex")
    )
    require_citations = any(
        re.search(
            r"\\(?:cite|citep|citet|parencite|textcite|autocite)\*?"
            r"(?:\[[^]]*\])*\s*\{",
            re.sub(
                r"(?m)(?<!\\)%.*$",
                "",
                path.read_text(encoding="utf-8", errors="replace"),
            ),
        )
        for path in source_dir.rglob("*.tex")
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    resource_dirs = sorted(
        {str(path.parent.resolve()) for path in source_dir.rglob("*") if path.is_file()}
    )
    base = [
        pandoc or _find_pandoc(),
        str(root),
        "--from=latex",
        "--to=epub3",
        "--standalone",
        "--toc",
        "--epub-title-page=false",
        "--mathml",
        "--number-sections",
        "--split-level=1",
        f"--resource-path={os.pathsep.join(resource_dirs)}",
        f"--epub-cover-image={cover_png}",
        f"--metadata=title:{metadata.title}",
        f"--metadata=author:{metadata.authors}",
        f"--metadata=identifier:arXiv:{arxiv_id}",
        "--metadata=toc-title:Table of Contents",
        "--metadata=reference-section-title:References",
        f"--output={output}",
    ]
    bibliographies = [] if compiled_bibliography else (
        sorted(source_dir.rglob("*.bib")) + sorted(source_dir.rglob("*.bibtex"))
    )
    command = base + [argument for bib in bibliographies for argument in ("--bibliography", str(bib))]
    if bibliographies:
        command.append("--citeproc")
    result = subprocess.run(command, cwd=root.parent, capture_output=True, text=True)
    if result.returncode and bibliographies:
        result = subprocess.run(base, cwd=root.parent, capture_output=True, text=True)
    if result.returncode:
        raise ConversionError(
            "Pandoc could not convert this paper: "
            + _pandoc_error_detail(result.stderr or result.stdout)
        )
    if re.search(r"Could not convert TeX math\b", result.stderr, re.IGNORECASE):
        raise ConversionError(
            "Pandoc could not render one LaTeX equation; the EPUB was not created."
        )
    if re.search(r"could not (?:fetch|find|load)|not found", result.stderr, re.IGNORECASE):
        raise ConversionError("Pandoc reported a missing source file or figure.")
    _finalize_epub(output, compiled_bibliography)
    _repair_cross_file_fragments(output)
    validate_epub(
        output,
        require_png_cover=True,
        require_abstract=require_abstract,
        require_citations=require_citations,
        require_front_matter=True,
        require_series="Arxiv Series",
    )
    return metadata


def validate_kindle_email(value: str) -> str:
    if not isinstance(value, str):
        raise ConversionError("Enter your Send-to-Kindle email address.")
    email = value.strip()
    match = re.fullmatch(r"([^@\s]+)@((?:free\.)?kindle\.com)", email, re.IGNORECASE)
    if not match:
        raise ConversionError("Enter an address ending in @kindle.com.")
    return f"{match.group(1)}@{match.group(2).lower()}"


def read_message(stream) -> dict | None:
    header = stream.read(4)
    if not header:
        return None
    if len(header) != 4:
        raise ConversionError("The native message header is truncated.")
    length = struct.unpack("=I", header)[0]
    if length > MAX_NATIVE_REQUEST_BYTES:
        raise ConversionError("The native message is too large.")
    payload = stream.read(length)
    if len(payload) != length:
        raise ConversionError("The native message body is truncated.")
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ConversionError("The native message is not valid JSON.") from error
    if not isinstance(value, dict):
        raise ConversionError("The native message must be a JSON object.")
    return value


def write_message(stream, value: dict) -> None:
    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(payload) > MAX_NATIVE_RESPONSE_BYTES:
        raise ConversionError("The native response is too large.")
    stream.write(struct.pack("=I", len(payload)))
    stream.write(payload)
    stream.flush()


def _download_source(arxiv_id: str, destination: Path) -> None:
    url = f"https://export.arxiv.org/e-print/{quote(arxiv_id, safe='/')}"
    request = Request(url, headers={"User-Agent": "arxiv-paper-to-kindle/0.1 (personal use)"})
    try:
        response = urlopen(request, timeout=120)
        with response, destination.open("wb") as output:
            total = 0
            while chunk := response.read(1_048_576):
                total += len(chunk)
                if total > MAX_DOWNLOAD_BYTES:
                    raise ConversionError("The compressed arXiv source is too large.")
                output.write(chunk)
    except ConversionError:
        raise
    except OSError as error:
        raise ConversionError(f"Could not download arXiv source: {error}") from error


def _output_path(metadata: PaperMetadata) -> Path:
    title = re.sub(r"[^\w .()\[\]-]+", "", metadata.title, flags=re.UNICODE)
    title = re.sub(r"\s+", " ", title).strip(" .")[:100] or "arXiv paper"
    stable_id = re.sub(r"v\d+$", "", metadata.arxiv_id).replace("/", "-")
    return _available_download_path(f"{title} [{stable_id}].epub")


def _available_download_path(filename: str) -> Path:
    folder = Path.home() / "Downloads" / "Arxiv to Kindle"
    folder.mkdir(parents=True, exist_ok=True)
    candidate = folder / filename
    counter = 2
    while candidate.exists():
        stem = Path(filename).stem
        candidate = folder / f"{stem} ({counter}).epub"
        counter += 1
    return candidate


def _collection_output_path(title: str) -> Path:
    safe_title = re.sub(r"[^\w .()\[\]-]+", "", title, flags=re.UNICODE)
    safe_title = re.sub(r"\s+", " ", safe_title).strip(" .")[:100] or "alphaXiv Library"
    return _available_download_path(f"{safe_title} [alphaXiv library].epub")


MAIL_SCRIPT = r'''
on run argv
    set recipientAddress to item 1 of argv
    set subjectText to item 2 of argv
    set attachmentPath to item 3 of argv
    tell application "Mail"
        set outgoingMessage to make new outgoing message with properties {subject:subjectText, content:"Sent by arXiv Paper to Kindle." & return & return, visible:false}
        tell outgoingMessage
            make new to recipient at end of to recipients with properties {address:recipientAddress}
            make new attachment with properties {file name:(POSIX file attachmentPath)} at after last paragraph
            send
        end tell
    end tell
end run
'''


def send_with_mail(epub: Path, recipient: str, title: str) -> None:
    result = subprocess.run(
        ["/usr/bin/osascript", "-e", MAIL_SCRIPT, recipient, title, str(epub)],
        capture_output=True,
        text=True,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout).strip().splitlines()
        raise ConversionError(
            "The EPUB was saved, but Mail could not send it: "
            + (detail[-1] if detail else "unknown error")
        )


def _convert_downloaded_paper(arxiv_id: str, work: Path) -> tuple[PaperMetadata, Path]:
    work.mkdir(parents=True, exist_ok=True)
    payload = work / "source"
    source_dir = work / "paper"
    epub = work / "paper.epub"
    _download_source(arxiv_id, payload)
    extract_source(payload, source_dir)
    return convert_source(source_dir, arxiv_id, epub), epub


def _persist_epub(source: Path, destination: Path) -> None:
    staging = destination.with_name(destination.name + ".copying")
    try:
        shutil.copy2(source, staging)
        os.replace(staging, destination)
    finally:
        staging.unlink(missing_ok=True)


def process_request(
    message: dict,
    progress: Callable[[dict], None] | None = None,
) -> dict:
    if not isinstance(message, dict):
        raise ConversionError("The native request must be an object.")
    should_send = message.get("send", True)
    if not isinstance(should_send, bool):
        raise ConversionError("The send option must be true or false.")
    recipient = validate_kindle_email(message.get("kindle_email", "")) if should_send else ""

    def report(text: str, *, current: int | None = None, total: int | None = None) -> None:
        if progress is None:
            return
        value = {"type": "progress", "message": text}
        if current is not None:
            value["current"] = current
        if total is not None:
            value["total"] = total
        progress(value)

    urls = message.get("urls")
    if urls is not None:
        if not isinstance(urls, list) or not all(isinstance(url, str) for url in urls):
            raise ConversionError("The alphaXiv folder paper list is invalid.")
        if not urls:
            raise ConversionError("The alphaXiv folder contains no papers.")
        if len(urls) > 50:
            raise ConversionError("An alphaXiv anthology can contain at most 50 papers.")
        arxiv_ids: list[str] = []
        seen: set[str] = set()
        for url in urls:
            arxiv_id = parse_arxiv_url(url)
            if arxiv_id not in seen:
                seen.add(arxiv_id)
                arxiv_ids.append(arxiv_id)
        title_value = message.get("collection_title", "alphaXiv Library")
        if not isinstance(title_value, str):
            raise ConversionError("The alphaXiv folder title is invalid.")
        collection_title = re.sub(r"\s+", " ", title_value).strip()[:160] or "alphaXiv Library"

        with tempfile.TemporaryDirectory(prefix="alphaxiv-to-kindle-") as temporary:
            work = Path(temporary)
            papers: list[tuple[PaperMetadata, Path]] = []
            total = len(arxiv_ids)
            for index, arxiv_id in enumerate(arxiv_ids, 1):
                try:
                    report(f"Downloading paper {index} of {total}.", current=index, total=total)
                    paper_work = work / f"paper-{index:03d}"
                    paper_work.mkdir()
                    payload = paper_work / "source"
                    source_dir = paper_work / "paper"
                    paper_epub = paper_work / "paper.epub"
                    _download_source(arxiv_id, payload)
                    report(f"Converting paper {index} of {total}.", current=index, total=total)
                    extract_source(payload, source_dir)
                    metadata = convert_source(source_dir, arxiv_id, paper_epub)
                except ConversionError as error:
                    raise ConversionError(
                        f"Paper {index} of {total} ({arxiv_id}) failed: {error}"
                    ) from error
                papers.append((metadata, paper_epub))
            report("Building anthology.", current=total, total=total)
            temporary_epub = work / "anthology.epub"
            build_anthology(papers, collection_title, temporary_epub)
            destination = _collection_output_path(collection_title)
            _persist_epub(temporary_epub, destination)

        if should_send:
            report("Sending anthology to Kindle.")
            try:
                send_with_mail(destination, recipient, collection_title)
            except ConversionError as error:
                return {"ok": False, "message": str(error), "epub_path": str(destination)}
            return {
                "ok": True,
                "message": f"Anthology with {len(arxiv_ids)} papers sent to Kindle through Mail.",
                "epub_path": str(destination),
            }
        return {
            "ok": True,
            "message": f"Anthology with {len(arxiv_ids)} papers created.",
            "epub_path": str(destination),
        }

    url = message.get("url")
    if not isinstance(url, str):
        raise ConversionError("The active tab URL is missing.")
    arxiv_id = parse_arxiv_url(url)

    with tempfile.TemporaryDirectory(prefix="arxiv-to-kindle-") as temporary:
        work = Path(temporary)
        report("Downloading paper.")
        metadata, temporary_epub = _convert_downloaded_paper(arxiv_id, work)
        destination = _output_path(metadata)
        _persist_epub(temporary_epub, destination)

    if should_send:
        report("Sending paper to Kindle.")
        try:
            send_with_mail(destination, recipient, metadata.title)
        except ConversionError as error:
            return {"ok": False, "message": str(error), "epub_path": str(destination)}
        return {
            "ok": True,
            "message": "EPUB sent to Kindle through Mail.",
            "epub_path": str(destination),
        }
    return {"ok": True, "message": "EPUB created.", "epub_path": str(destination)}


def main() -> int:
    if len(sys.argv) >= 3 and sys.argv[1] == "--convert-only":
        try:
            response = process_request({"url": sys.argv[2], "send": False})
        except ConversionError as error:
            print(f"Error: {error}", file=sys.stderr)
            return 1
        print(response["epub_path"])
        return 0

    try:
        message = read_message(sys.stdin.buffer)
        if message is None:
            return 0
        callback = (
            lambda value: write_message(sys.stdout.buffer, value)
            if message.get("stream_progress") is True
            else None
        )
        response = process_request(message, callback)
    except ConversionError as error:
        response = {"ok": False, "message": str(error)}
    except Exception as error:  # Native boundary: never corrupt stdout or expose a traceback.
        print(f"Unexpected native host error: {error!r}", file=sys.stderr)
        response = {"ok": False, "message": "Unexpected converter failure; see Chrome's native-host log."}
    write_message(sys.stdout.buffer, response)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
