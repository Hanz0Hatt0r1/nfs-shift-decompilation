#!/usr/bin/env python3
"""Apply a monotone safety guard to foreign-project classifier output.

This tool is intentionally not a semantic classifier for SHIFT.  It consumes
predictions produced by a model trained on another project and may only demote
base ``accept`` actions to ``review`` when cross-project family evidence is not
strong enough.  Existing review/escalate actions are never promoted.

The fixed floors are diagnostic deployment-safety defaults, not thresholds
calibrated on SHIFT labels.  Per-class OOD/contrast thresholds emitted by the
source classifier remain active through max(base_threshold, foreign_floor).
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.ForeignProjectGuard/1"


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


def numeric(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def guard_row(
    row: dict[str, Any],
    *,
    min_similarity: float,
    min_contrast: float,
) -> dict[str, Any]:
    output = dict(row)
    base_action = str(row.get("action"))
    output["base_action"] = base_action
    output["foreign_guard_format"] = FORMAT
    output["foreign_guard_changed"] = False
    output["foreign_guard_reasons"] = []

    base_ood = numeric(row.get("ood_accept_threshold"))
    base_contrast = numeric(row.get("contrast_accept_threshold"))
    similarity_floor = max(min_similarity, base_ood) if base_ood is not None else min_similarity
    contrast_floor = max(min_contrast, base_contrast) if base_contrast is not None else min_contrast
    output["foreign_similarity_floor"] = similarity_floor
    output["foreign_contrast_floor"] = contrast_floor

    similarity = numeric(row.get("family_similarity"))
    contrast = numeric(row.get("contrast_margin"))
    similarity_pass = similarity is not None and similarity >= similarity_floor
    contrast_pass = contrast is not None and contrast >= contrast_floor
    output["foreign_similarity_pass"] = similarity_pass
    output["foreign_contrast_pass"] = contrast_pass
    output["foreign_guard_pass"] = similarity_pass and contrast_pass

    if base_action != "accept":
        return output

    reasons: list[str] = []
    if not similarity_pass:
        reasons.append("family_similarity_below_foreign_floor")
    if not contrast_pass:
        reasons.append("contrast_margin_below_foreign_floor")
    output["foreign_guard_reasons"] = reasons
    if reasons:
        output["action"] = "review"
        output["foreign_guard_changed"] = True
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("classified", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--min-similarity", type=float, default=0.70)
    parser.add_argument("--min-contrast", type=float, default=0.05)
    args = parser.parse_args()

    rows = read_jsonl(args.classified)
    if not rows:
        raise SystemExit("classified input is empty")
    if not 0.0 <= args.min_similarity <= 1.0:
        raise SystemExit("--min-similarity must be in [0, 1]")
    if args.min_contrast < 0.0:
        raise SystemExit("--min-contrast must be >= 0")

    guarded = [
        guard_row(
            row,
            min_similarity=args.min_similarity,
            min_contrast=args.min_contrast,
        )
        for row in rows
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for row in guarded:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    before = collections.Counter(str(row.get("action")) for row in rows)
    after = collections.Counter(str(row.get("action")) for row in guarded)
    changed = sum(bool(row.get("foreign_guard_changed")) for row in guarded)
    promotions = sum(
        1
        for base, row in zip(rows, guarded)
        if str(base.get("action")) != "accept" and str(row.get("action")) == "accept"
    )
    reason_counts = collections.Counter(
        reason
        for row in guarded
        for reason in row.get("foreign_guard_reasons", [])
    )

    print("format:", FORMAT)
    print("rows:", len(rows))
    print("foreign similarity floor:", args.min_similarity)
    print("foreign contrast floor:", args.min_contrast)
    print("base actions:", dict(sorted(before.items())))
    print("guarded actions:", dict(sorted(after.items())))
    print("changed accepts:", changed)
    print("promotions:", promotions)
    print("reasons:", dict(sorted(reason_counts.items())))
    print("output:", args.output)
    if promotions:
        raise SystemExit("foreign guard invariant violated: action promotion detected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
