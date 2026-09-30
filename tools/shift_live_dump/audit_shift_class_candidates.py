#!/usr/bin/env python3
"""Audit SHIFT classes for source/PE evidence sufficient for structural decompilation."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from build_shift_class_manifest import build_manifest

FORMAT = "SHIFT-CLASS-DECOMPILATION-CANDIDATES/1"


def _blockers(row: dict) -> list[str]:
    blockers: list[str] = []
    if not row.get("name"):
        blockers.append("unresolved_class_name")
    if row.get("reflection_metadata_symbol") is None:
        blockers.append("no_reflection_metadata")
    if int(row.get("field_count", 0)) <= 0:
        blockers.append("no_reflected_fields")
    if row.get("unique_vtable") is None:
        blockers.append("non_unique_vtable")
    if int(row.get("resolved_field_name_count", 0)) != int(row.get("field_count", 0)):
        blockers.append("unresolved_field_names")
    if int(row.get("static_field_offset_count", 0)) != int(row.get("field_count", 0)):
        blockers.append("dynamic_field_offsets")

    fields = row.get("fields") or []
    if any(field.get("type_code") is None for field in fields):
        blockers.append("dynamic_field_types")
    if any(field.get("flags") is None for field in fields):
        blockers.append("dynamic_field_flags")
    if not row.get("reflection_functions") and fields:
        blockers.append("unresolved_reflection_function")
    return blockers


def audit_candidates(source: Path, exe: Path) -> dict:
    manifest = build_manifest(source, exe)
    candidates: list[dict] = []

    for row in manifest["classes"]:
        blockers = _blockers(row)
        field_count = int(row.get("field_count", 0))
        candidates.append({
            "class_name": row.get("name"),
            "descriptor": row.get("descriptor"),
            "parent_class": row.get("parent_class"),
            "ancestry": row.get("ancestry") or [],
            "reflection_metadata_symbol": row.get("reflection_metadata_symbol"),
            "reflection_functions": row.get("reflection_functions") or [],
            "field_count": field_count,
            "resolved_field_name_count": int(
                row.get("resolved_field_name_count", 0)
            ),
            "static_field_offset_count": int(
                row.get("static_field_offset_count", 0)
            ),
            "rtti_getter_addresses": row.get("rtti_getter_addresses") or [],
            "vtable_candidates": row.get("vtable_candidates") or [],
            "unique_vtable": row.get("unique_vtable"),
            "structural_ready": not blockers,
            "blockers": blockers,
        })

    candidates.sort(key=lambda row: (
        not row["structural_ready"],
        -row["field_count"],
        row["class_name"] is None,
        row["class_name"] or "",
        int(row["descriptor"]),
    ))

    blocker_counts: dict[str, int] = {}
    for row in candidates:
        for blocker in row["blockers"]:
            blocker_counts[blocker] = blocker_counts.get(blocker, 0) + 1

    return {
        "format": FORMAT,
        "source": manifest["source"],
        "source_sha256": manifest["source_sha256"],
        "exe": manifest["exe"],
        "exe_sha256": manifest["exe_sha256"],
        "class_count": len(candidates),
        "structural_ready_count": sum(
            bool(row["structural_ready"]) for row in candidates
        ),
        "blocked_count": sum(
            not bool(row["structural_ready"]) for row in candidates
        ),
        "blocker_counts": dict(sorted(blocker_counts.items())),
        "candidates": candidates,
    }


def _select(
    report: dict,
    prefixes: list[str],
    names: list[str],
    ready_only: bool,
    blocked_only: bool,
    top: int | None,
) -> list[dict]:
    rows = report["candidates"]
    if prefixes:
        rows = [
            row for row in rows
            if any((row.get("class_name") or "").startswith(prefix) for prefix in prefixes)
        ]
    if names:
        wanted = set(names)
        rows = [row for row in rows if row.get("class_name") in wanted]
    if ready_only:
        rows = [row for row in rows if row["structural_ready"]]
    if blocked_only:
        rows = [row for row in rows if not row["structural_ready"]]
    if top is not None:
        rows = rows[:top]
    return rows


def _write_csv(path: Path, rows: list[dict]) -> None:
    columns = [
        "class_name",
        "descriptor",
        "parent_class",
        "ancestry",
        "reflection_metadata_symbol",
        "reflection_functions",
        "field_count",
        "resolved_field_name_count",
        "static_field_offset_count",
        "rtti_getter_addresses",
        "vtable_candidates",
        "unique_vtable",
        "structural_ready",
        "blockers",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            rendered = {key: row.get(key) for key in columns}
            for key in (
                "ancestry",
                "reflection_functions",
                "rtti_getter_addresses",
                "vtable_candidates",
                "blockers",
            ):
                rendered[key] = ";".join(str(value) for value in (row.get(key) or []))
            writer.writerow(rendered)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="recovered SHIFT.exe.c")
    parser.add_argument("--exe", required=True, type=Path, help="retail SHIFT.exe")
    parser.add_argument(
        "--prefix",
        action="append",
        default=[],
        help="keep class names beginning with this prefix",
    )
    parser.add_argument(
        "--class-name",
        action="append",
        default=[],
        help="keep this exact class name",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--ready-only",
        action="store_true",
        help="keep only classes that satisfy every structural evidence gate",
    )
    group.add_argument(
        "--blocked-only",
        action="store_true",
        help="keep only classes with one or more evidence blockers",
    )
    parser.add_argument("--top", type=int, help="keep at most this many selected rows")
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--csv-out", type=Path)
    args = parser.parse_args()

    if args.top is not None and args.top < 1:
        parser.error("--top must be >= 1")

    report = audit_candidates(args.source, args.exe)
    selected = _select(
        report,
        args.prefix,
        args.class_name,
        args.ready_only,
        args.blocked_only,
        args.top,
    )
    rendered = dict(report)
    rendered["selected_count"] = len(selected)
    rendered["candidates"] = selected

    payload = json.dumps(rendered, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    if args.csv_out:
        _write_csv(args.csv_out, selected)
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
