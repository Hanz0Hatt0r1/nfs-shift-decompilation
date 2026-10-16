#!/usr/bin/env python3
"""Strict semantic parity gate for Shift compatibility vs revenginstr P-code tooling.

The historical Shift wrappers and the shared revenginstr core intentionally use
different format ids and reason strings.  This audit compares the behavior that
matters for P1.3 triage: corpus contract diagnostics, per-row foreign-guard
decisions/floors/pass bits, and transfer/OOD summary metrics.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.RevenginstrPcodeParity/1"
OLD_AUDIT_FORMAT = "SHIFT.CrossProjectPcodeAudit/2"
GENERIC_AUDIT_FORMAT = "REVENGINSTR.PcodeAudit/1"


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, 1):
            if not raw.strip():
                continue
            row = json.loads(raw)
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_no}: expected object")
            rows.append(row)
    return rows


def compare_number(left: Any, right: Any, *, tolerance: float) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return left is right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        a = float(left)
        b = float(right)
        if math.isnan(a) or math.isnan(b):
            return math.isnan(a) and math.isnan(b)
        return abs(a - b) <= tolerance
    return left == right


def add_mismatch(mismatches: list[dict[str, Any]], path: str, old: Any, new: Any) -> None:
    mismatches.append({"path": path, "shift": old, "revenginstr": new})


def compare_value(
    old: Any,
    new: Any,
    path: str,
    mismatches: list[dict[str, Any]],
    *,
    tolerance: float,
) -> None:
    if isinstance(old, dict) and isinstance(new, dict):
        if set(old) != set(new):
            mismatches.append(
                {
                    "path": path,
                    "reason": "key_set_mismatch",
                    "shift_only": sorted(set(old) - set(new)),
                    "revenginstr_only": sorted(set(new) - set(old)),
                }
            )
        for key in sorted(set(old) & set(new)):
            compare_value(old[key], new[key], f"{path}.{key}", mismatches, tolerance=tolerance)
        return
    if isinstance(old, list) and isinstance(new, list):
        if len(old) != len(new):
            mismatches.append(
                {"path": path, "reason": "length_mismatch", "shift": len(old), "revenginstr": len(new)}
            )
            return
        for index, (left, right) in enumerate(zip(old, new)):
            compare_value(left, right, f"{path}[{index}]", mismatches, tolerance=tolerance)
        return
    if not compare_number(old, new, tolerance=tolerance):
        add_mismatch(mismatches, path, old, new)


def normalized_corpus(report: dict[str, Any]) -> dict[str, Any]:
    corpus = dict(report["corpus"])
    # The outer retained format ids intentionally differ during migration.
    corpus.pop("formats", None)
    return corpus


def normalized_transfer_old(report: dict[str, Any]) -> dict[str, Any]:
    transfer = report.get("transfer")
    if not isinstance(transfer, dict):
        raise ValueError("historical audit lacks transfer block")
    guard = transfer.get("foreign_guard")
    if not isinstance(guard, dict):
        raise ValueError("historical audit lacks foreign_guard block")
    return {
        "rows": transfer["rows"],
        "predictions": transfer["predictions"],
        "base_actions": transfer["base_actions"],
        "actions": transfer["actions"],
        "base_accept_fraction": transfer["base_accept_fraction"],
        "accept_fraction": transfer["accept_fraction"],
        "accept_retention": guard["accept_retention"],
        "changed_actions": guard["changed_accepts"],
        "promotions": guard["promotions"],
        "confidence": transfer["confidence"],
        "raw_confidence": transfer["raw_confidence"],
        "family_similarity": transfer["family_similarity"],
        "contrast_margin": transfer["contrast_margin"],
        "semantic_labels_available": transfer["semantic_labels_available"],
    }


def normalized_transfer_generic(report: dict[str, Any]) -> dict[str, Any]:
    transfer = report.get("transfer")
    if not isinstance(transfer, dict):
        raise ValueError("revenginstr audit lacks transfer block")
    return {
        "rows": transfer["rows"],
        "predictions": transfer["predictions"],
        "base_actions": transfer["base_actions"],
        "actions": transfer["actions"],
        "base_accept_fraction": transfer["base_accept_fraction"],
        "accept_fraction": transfer["accept_fraction"],
        "accept_retention": transfer["accept_retention"],
        "changed_actions": transfer["changed_actions"],
        "promotions": transfer["promotions"],
        "confidence": transfer["confidence"],
        "raw_confidence": transfer["raw_confidence"],
        "family_similarity": transfer["family_similarity"],
        "contrast_margin": transfer["contrast_margin"],
        "semantic_labels_available": transfer["semantic_labels_available"],
    }


def compare_guard_rows(
    old_rows: list[dict[str, Any]],
    new_rows: list[dict[str, Any]],
    mismatches: list[dict[str, Any]],
    *,
    tolerance: float,
) -> None:
    if len(old_rows) != len(new_rows):
        mismatches.append(
            {
                "path": "$.guard_rows",
                "reason": "row_count_mismatch",
                "shift": len(old_rows),
                "revenginstr": len(new_rows),
            }
        )
        return

    fields = (
        "id",
        "prediction",
        "base_action",
        "action",
        "foreign_guard_changed",
        "foreign_similarity_floor",
        "foreign_contrast_floor",
        "foreign_similarity_pass",
        "foreign_contrast_pass",
        "foreign_guard_pass",
        "family_similarity",
        "contrast_margin",
        "ood_accept_threshold",
        "contrast_accept_threshold",
    )
    for index, (old, new) in enumerate(zip(old_rows, new_rows)):
        for field in fields:
            left = old.get(field)
            right = new.get(field)
            if not compare_number(left, right, tolerance=tolerance):
                add_mismatch(mismatches, f"$.guard_rows[{index}].{field}", left, right)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("shift_guarded", type=Path)
    parser.add_argument("revenginstr_guarded", type=Path)
    parser.add_argument("shift_audit", type=Path)
    parser.add_argument("revenginstr_audit", type=Path)
    parser.add_argument("--tolerance", type=float, default=1e-12)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    old_audit = read_json(args.shift_audit)
    new_audit = read_json(args.revenginstr_audit)
    if old_audit.get("format") != OLD_AUDIT_FORMAT:
        raise ValueError(f"Shift audit must be {OLD_AUDIT_FORMAT}")
    if new_audit.get("format") != GENERIC_AUDIT_FORMAT:
        raise ValueError(f"revenginstr audit must be {GENERIC_AUDIT_FORMAT}")

    mismatches: list[dict[str, Any]] = []
    compare_guard_rows(
        read_jsonl(args.shift_guarded),
        read_jsonl(args.revenginstr_guarded),
        mismatches,
        tolerance=args.tolerance,
    )
    compare_value(
        normalized_corpus(old_audit),
        normalized_corpus(new_audit),
        "$.corpus",
        mismatches,
        tolerance=args.tolerance,
    )
    compare_value(
        normalized_transfer_old(old_audit),
        normalized_transfer_generic(new_audit),
        "$.transfer",
        mismatches,
        tolerance=args.tolerance,
    )

    report = {
        "format": FORMAT,
        "shift_audit_format": OLD_AUDIT_FORMAT,
        "revenginstr_audit_format": GENERIC_AUDIT_FORMAT,
        "tolerance": args.tolerance,
        "mismatch_count": len(mismatches),
        "parity_pass": not mismatches,
        "mismatches": mismatches[:50],
        "note": "Reason-string/outer-format names are intentionally excluded; routing/OOD decisions and numeric diagnostics are strict.",
    }
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("format:", FORMAT)
    print("guard rows:", len(read_jsonl(args.shift_guarded)))
    print("tolerance:", args.tolerance)
    print("mismatches:", len(mismatches))
    print("pcode/guard parity pass:", not mismatches)
    if mismatches:
        print("first mismatch:", mismatches[0])
    if args.output is not None:
        print("output:", args.output)
    if args.strict and mismatches:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
