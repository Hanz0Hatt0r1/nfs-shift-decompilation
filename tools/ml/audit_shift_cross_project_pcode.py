#!/usr/bin/env python3
"""SHIFT-format compatibility adapter for the shared portable P-code audit."""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys
from pathlib import Path
from typing import Any

_repo = Path(
    os.environ.get(
        "REVENGINSTR_REPO",
        str(Path(__file__).resolve().parents[2].parent / "revenginstr"),
    )
)
_source = _repo / "src"
if _source.is_dir() and str(_source) not in sys.path:
    sys.path.insert(0, str(_source))

from revenginstr.pcode.audit import (  # noqa: E402
    build_report as _build_report,
    corpus_audit,
    header_value,
    quantiles,
    read_jsonl,
    transfer_audit as _transfer_audit,
)

FORMAT = "SHIFT.CrossProjectPcodeAudit/2"


def transfer_audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    transfer = _transfer_audit(rows)
    base_actions = collections.Counter(
        str(row.get("base_action", row.get("action"))) for row in rows
    )
    actions = collections.Counter(str(row.get("action")) for row in rows)
    accept = actions.get("accept", 0)
    base_accept = base_actions.get("accept", 0)
    transfer["base_actions"] = dict(sorted(base_actions.items()))
    transfer["base_accept_fraction"] = base_accept / len(rows) if rows else 0.0
    transfer["actions"] = dict(sorted(actions.items()))

    if any("foreign_guard_format" in row for row in rows):
        reasons = collections.Counter(
            reason
            for row in rows
            for reason in row.get("foreign_guard_reasons", [])
            if isinstance(reason, str)
        )
        changed = sum(bool(row.get("foreign_guard_changed")) for row in rows)
        promotions = sum(
            row.get("base_action", row.get("action")) != "accept"
            and row.get("action") == "accept"
            for row in rows
        )
        transfer["foreign_guard"] = {
            "format": next(
                (str(row["foreign_guard_format"]) for row in rows if row.get("foreign_guard_format")),
                None,
            ),
            "changed_accepts": changed,
            "changed_fraction": changed / len(rows) if rows else 0.0,
            "accept_retention": accept / base_accept if base_accept else 0.0,
            "promotions": promotions,
            "reasons": dict(sorted(reasons.items())),
        }
    else:
        transfer["foreign_guard"] = None
    transfer["interpretation"] = "OOD/representation probe only; accept is not correctness on SHIFT."
    return transfer


def build_report(
    corpus_rows: list[dict[str, Any]],
    classified_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Keep the historical SHIFT report envelope around shared audit metrics."""
    report = _build_report(corpus_rows, classified_rows)
    report["format"] = FORMAT
    transfer = report["transfer"]
    if transfer is None or classified_rows is None:
        return report
    report["transfer"] = transfer_audit(classified_rows)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus", type=Path)
    parser.add_argument("--classified", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    corpus = read_jsonl(args.corpus)
    if not corpus:
        raise SystemExit("corpus is empty")
    classified = read_jsonl(args.classified) if args.classified is not None else None
    report = build_report(corpus, classified)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    corpus_report = report["corpus"]
    print("format:", FORMAT)
    print("rows:", corpus_report["rows"])
    print("statuses:", corpus_report["statuses"])
    print("architecture:", corpus_report["architecture"])
    print("pointer size:", corpus_report["pointer_size"])
    print("portable contract pass:", corpus_report["portable_contract_pass"])
    print("leakage findings:", len(corpus_report["leakage_findings"]))
    if report["transfer"] is not None:
        transfer = report["transfer"]
        print("predictions:", transfer["predictions"])
        print("base actions:", transfer["base_actions"])
        print("actions:", transfer["actions"])
        print("base accept fraction:", round(transfer["base_accept_fraction"], 6))
        print("accept fraction:", round(transfer["accept_fraction"], 6))
        print("family similarity:", transfer["family_similarity"])
        print("contrast margin:", transfer["contrast_margin"])
        if transfer["foreign_guard"] is not None:
            print("foreign guard:", transfer["foreign_guard"])
        print("semantic labels available:", transfer["semantic_labels_available"])
    if args.output is not None:
        print("output:", args.output)
    return 0 if corpus_report["portable_contract_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
