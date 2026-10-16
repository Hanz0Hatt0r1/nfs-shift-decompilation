#!/usr/bin/env python3
"""SHIFT-format adapter for the shared monotone foreign-project guard."""
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

from revenginstr.ood.foreign_guard import (  # noqa: E402
    apply_guard as _apply_guard,
    read_jsonl,
)

FORMAT = "SHIFT.ForeignProjectGuard/1"


def numeric(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _shift_row(row: dict[str, Any]) -> dict[str, Any]:
    output = dict(row)
    output["foreign_guard_format"] = FORMAT
    replacements = {
        "family_similarity_below_floor": "family_similarity_below_foreign_floor",
        "contrast_margin_below_floor": "contrast_margin_below_foreign_floor",
    }
    output["foreign_guard_reasons"] = [
        replacements.get(reason, reason) for reason in output["foreign_guard_reasons"]
    ]
    return output


def guard_row(
    row: dict[str, Any],
    *,
    min_similarity: float,
    min_contrast: float,
) -> dict[str, Any]:
    guarded, _ = _apply_guard([row], min_similarity, min_contrast)
    return _shift_row(guarded[0])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("classified", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--min-similarity", type=float, default=0.70)
    parser.add_argument("--min-contrast", type=float, default=0.05)
    args = parser.parse_args(argv)

    if not 0.0 <= args.min_similarity <= 1.0:
        raise SystemExit("--min-similarity must be in [0, 1]")
    if args.min_contrast < 0.0:
        raise SystemExit("--min-contrast must be >= 0")
    rows = read_jsonl(args.classified)
    if not rows:
        raise SystemExit("classified input is empty")
    guarded, summary = _apply_guard(rows, args.min_similarity, args.min_contrast)
    guarded = [_shift_row(row) for row in guarded]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for row in guarded:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    base_actions = collections.Counter(str(row.get("action")) for row in rows)
    actions = collections.Counter(str(row.get("action")) for row in guarded)
    reasons = collections.Counter(
        reason for row in guarded for reason in row["foreign_guard_reasons"]
    )
    print("format:", FORMAT)
    print("rows:", len(rows))
    print("foreign similarity floor:", args.min_similarity)
    print("foreign contrast floor:", args.min_contrast)
    print("base actions:", dict(sorted(base_actions.items())))
    print("guarded actions:", dict(sorted(actions.items())))
    print("changed accepts:", summary["changed_accepts"])
    print("promotions:", summary["promotions"])
    print("reasons:", dict(sorted(reasons.items())))
    print("output:", args.output)
    if summary["promotions"]:
        raise SystemExit("foreign guard invariant violated: action promotion detected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
