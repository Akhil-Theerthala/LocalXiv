#!/usr/bin/env python3
"""Read-only witness checks for the RevTeX bibliography holdout."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from xml.etree import ElementTree


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", default="holdout-03")
    parser.add_argument("--output", type=Path, default=Path(".verification/robustness/revtex-witness.json"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2] / ".verification/robustness/runs" / args.stage / "2207.00575v2"
    bbls = sorted(root.glob("pandoc/source/*.bbl"))
    readers = sorted(root.glob("reader/text/*.xhtml"))
    if not bbls or not readers:
        result = {"status": "pending", "stage": args.stage, "paper": "2207.00575v2"}
    else:
        bbl = bbls[0].read_text(encoding="utf-8", errors="replace")
        trees = [ElementTree.parse(path).getroot() for path in readers]
        prose = ' '.join(' '.join(''.join(tree.itertext()).split()) for tree in trees)
        hrefs = {e.get('href') for tree in trees for e in tree.iter() if e.get('href')}
        ids = {e.get('id') for tree in trees for e in tree.iter() if e.get('id')}
        entries = re.findall(r"\\bibitem\b(?:\s*\[[^]]*\])?\s*\{([^{}]+)\}", bbl)
        dois = re.findall(r"\\href\s*\{(https://doi\.org/[^{}]+)\}", bbl)
        missing_dois = [doi for doi in dois if doi not in hrefs]
        result = {"status": "pass", "stage": args.stage, "entries": len(entries), "expected_entries": 36,
                  "doi_hrefs": len(dois), "missing_doi_hrefs": missing_dois,
                  "known_garbage_absent": not any(x in prose for x in ("bibitemNoStop", "catcode", "12‘$12", "12‘&12")),
                  "first_key": entries[0] if entries else None, "last_key": entries[-1] if entries else None}
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
        from native.host import _reference_id
        result['missing_reference_targets'] = [key for key in entries if _reference_id(key) not in ids]
        result['first_and_last_titles'] = all(title in prose for title in ['Relaxing with relaxors: a review of relaxor ferroelectrics', 'Manifestation of structural Higgs and Goldstone modes in the hexagonal manganites'])
        assert not result['missing_reference_targets']
        assert result['first_and_last_titles']
        assert result["entries"] == 36
        assert not missing_dois
        assert result["known_garbage_absent"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
