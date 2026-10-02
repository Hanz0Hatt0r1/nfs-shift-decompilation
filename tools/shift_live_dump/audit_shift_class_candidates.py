#!/usr/bin/env python3
"""Audit SHIFT classes for source/PE evidence sufficient for structural decompilation."""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

from build_shift_class_manifest import build_manifest

FORMAT = "SHIFT-CLASS-DECOMPILATION-CANDIDATES/1"
INITIALIZER_FORMAT = "SHIFT-FACTORY-INITIALIZER-LINKS/1"


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


def _load_initializer_links(path: Path | None) -> tuple[dict[int, list[dict]], str | None]:
    if path is None:
        return {}, None
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("format") != INITIALIZER_FORMAT:
        raise ValueError(f"{path}: expected {INITIALIZER_FORMAT}")
    by_descriptor: dict[int, list[dict]] = defaultdict(list)
    for row in report.get("links") or []:
        descriptor = row.get("descriptor")
        if isinstance(descriptor, int):
            by_descriptor[descriptor].append(row)
    return dict(by_descriptor), str(path)


def _ghidra_confirmation(rows: list[dict]) -> bool | None:
    if not rows:
        return None
    states = [row.get("ghidra_direct_call") for row in rows]
    if any(state is False for state in states):
        return False
    if all(state is True for state in states):
        return True
    return None


def audit_candidates(
    source: Path,
    exe: Path,
    initializer_links: Path | None = None,
) -> dict:
    manifest = build_manifest(source, exe)
    initializer_by_descriptor, initializer_source = _load_initializer_links(initializer_links)
    candidates: list[dict] = []

    for row in manifest["classes"]:
        blockers = _blockers(row)
        field_count = int(row.get("field_count", 0))
        descriptor = int(row["descriptor"])
        linked_rows = initializer_by_descriptor.get(descriptor, [])
        initializers = sorted({
            linked["initializer_candidate"]
            for linked in linked_rows
            if isinstance(linked.get("initializer_candidate"), str)
        })
        factories = sorted({
            linked["factory_function"]
            for linked in linked_rows
            if isinstance(linked.get("factory_function"), str)
        })
        ghidra_confirmation = _ghidra_confirmation(linked_rows)
        candidates.append({
            "class_name": row.get("name"),
            "descriptor": descriptor,
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
            "initializer_link_count": len(linked_rows),
            "initializer_linked": bool(linked_rows),
            "factory_functions": factories,
            "initializer_candidates": initializers,
            "unambiguous_initializer": (
                initializers[0] if len(initializers) == 1 else None
            ),
            "initializer_ghidra_confirmed": ghidra_confirmation,
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
        "initializer_links_source": initializer_source,
        "class_count": len(candidates),
        "structural_ready_count": sum(
            bool(row["structural_ready"]) for row in candidates
        ),
        "blocked_count": sum(
            not bool(row["structural_ready"]) for row in candidates
        ),
        "initializer_linked_count": sum(
            bool(row["initializer_linked"]) for row in candidates
        ),
        "initializer_ghidra_confirmed_count": sum(
            row["initializer_ghidra_confirmed"] is True for row in candidates
        ),
        "initializer_ghidra_mismatch_count": sum(
            row["initializer_ghidra_confirmed"] is False for row in candidates
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
    initializer_linked_only: bool,
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
    if initializer_linked_only:
        rows = [row for row in rows if row["initializer_linked"]]
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
        "initializer_link_count",
        "initializer_linked",
        "factory_functions",
        "initializer_candidates",
        "unambiguous_initializer",
        "initializer_ghidra_confirmed",
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
                "factory_functions",
                "initializer_candidates",
            ):
                rendered[key] = ";".join(str(value) for value in (row.get(key) or []))
            writer.writerow(rendered)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="recovered SHIFT.exe.c")
    parser.add_argument("--exe", required=True, type=Path, help="retail SHIFT.exe")
    parser.add_argument(
        "--initializer-links",
        type=Path,
        help="optional SHIFT-FACTORY-INITIALIZER-LINKS/1 report to annotate rows",
    )
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
    parser.add_argument(
        "--initializer-linked-only",
        action="store_true",
        help="keep only classes with one or more factory initializer links",
    )
    parser.add_argument("--top", type=int, help="keep at most this many selected rows")
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--csv-out", type=Path)
    args = parser.parse_args()

    if args.top is not None and args.top < 1:
        parser.error("--top must be >= 1")

    report = audit_candidates(args.source, args.exe, args.initializer_links)
    selected = _select(
        report,
        args.prefix,
        args.class_name,
        args.ready_only,
        args.blocked_only,
        args.initializer_linked_only,
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
