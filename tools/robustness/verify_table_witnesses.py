#!/usr/bin/env python3
"""Verify the retained table-repair witnesses without touching conversions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[2]
STAGE = "candidate-02"
NS = {"x": "http://www.w3.org/1999/xhtml"}
UNIAD = ["100101", "001001", "101010", "000001", "110100", "110100", "000011", "001011", "001011", "101101", "111111"]


def table(path: Path, ident: str):
    root = ElementTree.parse(path).getroot()
    for node in root.findall(".//x:table", NS):
        if node.get("id") == ident:
            return node
    raise AssertionError(f"missing table {ident} in {path}")


def rows(node):
    return node.findall("./x:tbody/x:tr", NS)


def cells(row):
    return [c for c in list(row) if c.tag.rsplit("}", 1)[-1] in {"td", "th"}]


def text(cell):
    return " ".join("".join(cell.itertext()).split())


def bits(row):
    return "".join("1" if text(c) == "✓" else "0" for c in cells(row)[2:])


def expanded_rows(node):
    """Expand HTML row/col spans into a stable rectangular cell grid."""
    active = {}
    result = []
    for tr in rows(node):
        out = []
        col = 0
        created = set()
        for cell in cells(tr):
            while col in active:
                out.append(active[col][0])
                col += 1
            value = text(cell)
            width = int(cell.get("colspan", "1"))
            height = int(cell.get("rowspan", "1"))
            for offset in range(width):
                out.append(value)
                if height > 1:
                    active[col + offset] = (value, height - 1)
                    created.add(col + offset)
            col += width
        while col in active:
            out.append(active[col][0])
            col += 1
        result.append(out)
        active = {
            key: (value, height if key in created else height - 1)
            for key, (value, height) in active.items()
            if key in created or height > 1
        }
    return result


def verify_uniaD() -> dict:
    base = ROOT / ".verification/robustness/historical/runs/candidate-02/2212.10156v2"
    reader = table(base / "reader/text/ch002.xhtml", "tab:motivation")
    observed = ["".join("1" if value == "✓" else "0" for value in row[2:8]) for row in expanded_rows(reader)[2:]]
    assert observed == UNIAD, observed
    assert sum(row.count("1") for row in observed) == 33

    source = (base / "pandoc/source/arXiv_camera_ready.tex").read_text()
    block = source.split("\\begin{tabular}", 1)[1].split("\\end{tabular}", 1)[0]
    source_rows = []
    for line in block.splitlines():
        if "&" not in line or line.lstrip().startswith("%") or "\\multicolumn" in line:
            continue
        fields = [part.strip() for part in line.split("&")]
        if len(fields) >= 8 and any("\\cmark" in field for field in fields[-6:]):
            source_rows.append("".join("1" if "\\cmark" in field else "0" for field in fields[-6:]))
    assert source_rows == UNIAD, source_rows
    return {"status": "pass", "rows": 11, "columns": 6, "checkmarks": 33, "source_matches": True}


def verify_spans() -> dict:
    base = ROOT / ".verification/robustness/runs" / STAGE
    math = table(base / "2406.09403v3/reader/text/ch005.xhtml", "tab:math")
    vision = table(base / "2406.09403v3/reader/text/ch006.xhtml", "tab:vision_main")
    assert [text(c) for c in cells(rows(math)[0])] == ["", "Geometry", "Graph", "Math", "Game"]
    assert [text(c) for c in cells(rows(vision)[0])] == ["Prior multimodal LLMs"]
    assert [c.get("colspan", "1") for c in cells(rows(math)[0])] == ["1", "1", "3", "2", "1"]
    assert [c.get("colspan", "1") for c in cells(rows(math)[2])] == ["8"]
    assert [c.get("colspan", "1") for c in cells(rows(math)[7])] == ["8"]
    assert [c.get("colspan", "1") for c in cells(rows(vision)[0])] == ["8"]
    assert [c.get("colspan", "1") for c in cells(rows(vision)[8])] == ["8"]
    return {"status": "pass", "tables": {"tab:math": "header-and-section-spans", "tab:vision_main": "section-spans"}}


def verify_cline_witness() -> dict:
    base = ROOT / ".verification/robustness/runs" / STAGE / "2405.04940v3"
    source = (base / "pandoc/source/sec/4_experiment.tex").read_text()
    reader = (base / "reader/text/ch005.xhtml").read_text()
    node = table(base / "reader/text/ch005.xhtml", "tab:ablation")
    assert all(text(cell) != "7-15" for row in rows(node) for cell in cells(row))
    assert len(cells(rows(node)[0])) == 9
    assert [c.get("colspan", "1") for c in cells(rows(node)[0])[-3:]] == ["3", "3", "3"]
    return {"status": "pass", "table": "tab:ablation", "forbidden_markers_absent": True}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", default="candidate-02")
    parser.add_argument("--output", type=Path, default=ROOT / ".verification/robustness/table-witnesses.json")
    args = parser.parse_args()
    global STAGE
    STAGE = args.stage
    result = {"status": "pass", "witnesses": {"uniaD": verify_uniaD(), "sketchpad_spans": verify_spans(), "tablecell_cline": verify_cline_witness()}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
