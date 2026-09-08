"""Verify exact author-affiliation witnesses in generated reader XHTML.

This is deliberately a witness check, rather than a general metadata parser:
it derives nonempty institution/email values from the source archive and
checks that the same strings occur in the reader output.
"""
from __future__ import annotations

import argparse
import json
import re
import tarfile
from pathlib import Path
from xml.etree import ElementTree as ET


IDS = ("2407.13251v1", "2502.17561v1")


def source_text(source: Path) -> str:
    chunks = []
    with tarfile.open(source, "r:gz") as archive:
        for member in archive.getmembers():
            if member.isfile() and member.name.endswith(".tex"):
                handle = archive.extractfile(member)
                if handle is not None:
                    chunks.append(handle.read().decode("utf-8", "replace"))
    return "\n".join(chunks)


def argument(text: str, start: int) -> str | None:
    position = text.find("{", start)
    if position < 0:
        return None
    depth = 0
    for index in range(position, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[position + 1:index]
    return None


def witnesses(source: str) -> list[str]:
    # Ignore commented template examples and retain only active metadata.
    source = re.sub(r"(?m)(?<!\\)%[^\r\n]*", "", source)
    values = []
    # Structured ACM fields: only institution and email are stable semantic
    # witnesses across the source and rendered output.
    for match in re.finditer(r"\\institution\s*\{|\\(?:affil|affiliation)\s*\{", source):
        if match.group().startswith(r"\institution"):
            value = argument(source, match.start())
            if value:
                values.append(" ".join(value.replace(r"\\", " ").split()))
    for match in re.finditer(r"\\email\s*\{", source):
        value = argument(source, match.start())
        if value:
            values.append(" ".join(value.replace(r"\\", " ").split()))
    # AASTeX uses plain-text \affil arguments.
    for match in re.finditer(r"\\(?:affil|affiliation)\s*\{", source):
        value = argument(source, match.start())
        if value and not value.lstrip().startswith("\\") and "#" not in value:
            values.append(" ".join(value.replace(r"\\", " ").split()))
    return list(dict.fromkeys(value for value in values if "#" not in value))


def reader_text(work: Path) -> str:
    pieces = []
    for path in sorted((work / "reader").rglob("*.xhtml")):
        root = ET.parse(path).getroot()
        pieces.append(" ".join(part.strip() for part in root.itertext() if part.strip()))
    return " ".join(pieces)


def verify(work: Path) -> dict:
    source = source_text(work / "source")
    text = reader_text(work)
    expected = witnesses(source)
    def normalized(value):
        value = value.replace(r'\&', '&').replace(r'\\', ' ')
        return ''.join(c.lower() for c in value if c.isalnum())
    missing = [value for value in expected if normalized(value) not in normalized(text)]
    return {
        "status": "pass" if expected and not missing else "fail",
        "comparison": "letters and digits in order, ignoring punctuation and whitespace",
        "expected": expected,
        "missing": missing,
        "source": str(work / "source"),
        "reader": str(work / "reader"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", type=Path, help="robustness run directory, e.g. .verification/.../final-03")
    parser.add_argument("ids", nargs="*", default=IDS)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = {}
    for identifier in args.ids:
        work = args.stage / identifier
        result[identifier] = {"status": "pending"} if not (work / "source").exists() or not (work / "reader").exists() else verify(work)
    rendered = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(rendered)
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
