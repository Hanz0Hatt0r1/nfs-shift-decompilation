#!/usr/bin/env python3
"""Build a joined SHIFT class manifest from RTTI and reflection evidence."""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

from extract_shift_reflection_fields import extract_reflection_fields
from extract_shift_rtti_registry import extract_registry

FORMAT = "SHIFT-CLASS-MANIFEST/1"


def _ancestry(row: dict, by_descriptor: dict[int, dict]) -> list[str]:
    out: list[str] = []
    seen: set[int] = set()
    descriptor = row.get("parent_descriptor")
    while isinstance(descriptor, int) and descriptor not in seen:
        seen.add(descriptor)
        parent = by_descriptor.get(descriptor)
        if parent is None:
            break
        name = parent.get("name")
        if isinstance(name, str):
            out.append(name)
        descriptor = parent.get("parent_descriptor")
    return out


def build_manifest(source: Path, exe: Path | None = None) -> dict:
    registry = extract_registry(source, exe)
    reflection = extract_reflection_fields(source, exe)

    fields_by_descriptor: dict[int, list[dict]] = defaultdict(list)
    for field in reflection["fields"]:
        descriptor = field.get("class_descriptor")
        if isinstance(descriptor, int):
            fields_by_descriptor[descriptor].append(field)

    by_descriptor = {
        int(row["descriptor"]): row
        for row in registry["classes"]
        if isinstance(row.get("descriptor"), int)
    }
    children: dict[int, list[str]] = defaultdict(list)
    for row in registry["classes"]:
        parent = row.get("parent_descriptor")
        name = row.get("name")
        if isinstance(parent, int) and isinstance(name, str):
            children[parent].append(name)

    classes: list[dict] = []
    for source_row in registry["classes"]:
        descriptor = int(source_row["descriptor"])
        class_fields = sorted(
            fields_by_descriptor.get(descriptor, []),
            key=lambda row: (
                row.get("offset") is None,
                row.get("offset") if row.get("offset") is not None else 0,
                row.get("field_name") or "",
                row.get("field_name_token") or "",
            ),
        )
        functions = sorted({
            row["reflection_function"]
            for row in class_fields
            if row.get("reflection_function")
        })
        row = dict(source_row)
        row["ancestry"] = _ancestry(source_row, by_descriptor)
        row["children"] = sorted(children.get(descriptor, []))
        row["reflection_functions"] = functions
        row["field_count"] = len(class_fields)
        row["resolved_field_name_count"] = sum(
            field.get("field_name") is not None for field in class_fields
        )
        row["static_field_offset_count"] = sum(
            field.get("offset") is not None for field in class_fields
        )
        row["fields"] = class_fields
        classes.append(row)

    classes.sort(key=lambda row: (
        row.get("name") is None,
        row.get("name") or "",
        int(row["descriptor"]),
    ))

    return {
        "format": FORMAT,
        "source": registry["source"],
        "source_sha256": registry["source_sha256"],
        "exe": registry["exe"],
        "exe_sha256": registry["exe_sha256"],
        "class_count": len(classes),
        "named_class_count": sum(row.get("name") is not None for row in classes),
        "reflected_class_count": sum(row["field_count"] > 0 for row in classes),
        "reflection_field_count": sum(row["field_count"] for row in classes),
        "unique_vtable_count": sum(
            row.get("unique_vtable") is not None for row in classes
        ),
        "classes": classes,
    }


def _selected_classes(
    report: dict,
    prefixes: list[str],
    names: list[str],
    only_reflected: bool,
) -> list[dict]:
    selected = report["classes"]
    if prefixes:
        selected = [
            row for row in selected
            if any((row.get("name") or "").startswith(prefix) for prefix in prefixes)
        ]
    if names:
        wanted = set(names)
        selected = [row for row in selected if row.get("name") in wanted]
    if only_reflected:
        selected = [row for row in selected if row.get("field_count", 0) > 0]
    return selected


def _write_csv(path: Path, classes: list[dict]) -> None:
    columns = [
        "name",
        "descriptor",
        "registration_function",
        "parent_class",
        "parent_descriptor",
        "reflection_metadata_symbol",
        "reflection_functions",
        "field_count",
        "resolved_field_name_count",
        "static_field_offset_count",
        "rtti_getter_addresses",
        "vtable_candidates",
        "unique_vtable",
        "ancestry",
        "children",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in classes:
            rendered = {key: row.get(key) for key in columns}
            for key in (
                "reflection_functions",
                "rtti_getter_addresses",
                "vtable_candidates",
                "ancestry",
                "children",
            ):
                rendered[key] = ";".join(str(value) for value in (row.get(key) or []))
            writer.writerow(rendered)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="recovered SHIFT.exe.c")
    parser.add_argument("--exe", type=Path, help="retail SHIFT.exe")
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
    parser.add_argument(
        "--only-reflected",
        action="store_true",
        help="keep only classes with recovered reflection fields",
    )
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--csv-out", type=Path)
    args = parser.parse_args()

    report = build_manifest(args.source, args.exe)
    selected = _selected_classes(
        report,
        args.prefix,
        args.class_name,
        args.only_reflected,
    )
    rendered = dict(report)
    rendered["selected_class_count"] = len(selected)
    rendered["classes"] = selected

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
