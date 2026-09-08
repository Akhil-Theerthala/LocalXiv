#!/usr/bin/env python3
"""Render a refreshable markdown summary from robustness run artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def audit_result(root: Path, run_dir: Path, paper_id: str, result: dict) -> tuple[str, str]:
    candidates = [run_dir / paper_id]
    if result.get("directory"):
        candidates.insert(0, Path(str(result["directory"])))
    paper_dir = next((path for path in candidates if (path / "fidelity-audit.json").exists()), candidates[0])
    path = paper_dir / "fidelity-audit.json"
    if not path.exists():
        return "missing", "audit artifact absent"
    data = load(path)
    audit_status = str(data.get("status", "unknown"))
    if audit_status in {"failed", "error"}:
        return "failed", audit_status
    flags = data.get("flags", [])
    if not flags:
        if audit_status not in {"clean", "passed", "no_flags", "no_flags_in_checks"}:
            return "unknown", f"audit status: {audit_status}"
        return "clean", "none"
    return "needs_review", ", ".join(str(flag) for flag in flags)


def rows(root: Path, specs: list[tuple[str, str, str]]) -> list[str]:
    output = []
    for label, relative, split in specs:
        run_dir = root / relative
        result_path = run_dir / "results.json"
        if not result_path.exists():
            continue
        results = load(result_path)
        for paper_id in sorted(results):
            result = results[paper_id]
            status = result.get("status", "unknown")
            converter = result.get("converter", "-")
            seconds = result.get("seconds", result.get("conversion_seconds", "-"))
            if isinstance(seconds, float):
                seconds = f"{seconds:.2f}"
            if status == "converted":
                audit_status, flags = audit_result(root, run_dir, paper_id, result)
            else:
                audit_status, flags = "not-applicable", "not-converted"
            source_outcome = "retained" if result.get("source_hash") else "unknown"
            paper_dir = Path(str(result.get("directory", run_dir / paper_id)))
            pdf_outcome = "retained" if (paper_dir / "original.pdf").exists() else "unknown"
            output.append(
                f"| {paper_id} | {split} | {label} | {status} | {converter} | {seconds} | {audit_status} | {flags} | {source_outcome} | {pdf_outcome} |"
            )
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(".verification/robustness"))
    parser.add_argument(
        "--stage-suffix",
        default="02",
        help="candidate/holdout/historical stage suffix to report, for example 03",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root
    suffix = args.stage_suffix
    specs = [
        ("baseline", "runs/baseline", "development"),
        ("candidate-01", "runs/candidate-01", "development"),
        ("holdout-01", "runs/holdout-01", "held-out"),
        (f"final-{suffix}", "runs/final", "frozen sample"),
        (f"historical-{suffix}", f"historical/runs/candidate-{suffix}", "historical"),
    ]
    text = "\n".join(
        [
            "# Robustness run table",
            "",
            "Generated from `.verification/robustness`; audit flags are review candidates, not proof of content loss.",
            "",
            "| Paper | Split | Run | Status | Converter | Seconds | Audit status | Content-audit flags | Source | Original PDF |",
            "| --- | --- | --- | --- | --- | ---: | --- | --- | --- | --- |",
            *rows(root, specs),
            "",
        ]
    )
    if args.output:
        args.output.write_text(text)
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
