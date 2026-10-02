#!/usr/bin/env python3
"""Build a joined SHIFT class manifest from RTTI and reflection evidence."""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

from extract_shift_reflection_fields import extract_reflection_fields
from extract_shift_rtti_registry import extract_registry

FORMAT = "SHIFT-CLASS-MANIFEST/1"
GHIDRA_REGISTRATION_CORE = "0x00631740"
_REGISTRATION_FUNCTION = re.compile(r"^FUN_([0-9a-fA-F]{8})$")


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


def _read_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_no}: expected object")
            yield row


def _registration_address(function_name: object) -> str | None:
    if not isinstance(function_name, str):
        return None
    match = _REGISTRATION_FUNCTION.fullmatch(function_name)
    if match is None:
        return None
    return "0x" + match.group(1).lower()


def _load_ghidra_registration_index(root: Path) -> dict:
    required = ["functions.jsonl", "callgraph.jsonl", "strings_xrefs.jsonl"]
    missing = [name for name in required if not (root / name).is_file()]
    if missing:
        raise FileNotFoundError(
            "missing required Ghidra export files: " + ", ".join(missing)
        )

    functions = {
        row["address"]: row
        for row in _read_jsonl(root / "functions.jsonl")
        if isinstance(row.get("address"), str)
    }
    calls_by_function: dict[str, set[str]] = defaultdict(set)
    for row in _read_jsonl(root / "callgraph.jsonl"):
        source = row.get("from_function")
        target = row.get("to")
        if (
            isinstance(source, str)
            and isinstance(target, str)
            and row.get("indirect") is False
        ):
            calls_by_function[source].add(target)

    strings_by_function: dict[str, set[str]] = defaultdict(set)
    for row in _read_jsonl(root / "strings_xrefs.jsonl"):
        value = row.get("value")
        if not isinstance(value, str):
            continue
        for function in row.get("functions") or []:
            if isinstance(function, str):
                strings_by_function[function].add(value)

    return {
        "functions": functions,
        "calls_by_function": calls_by_function,
        "strings_by_function": strings_by_function,
    }


def _ghidra_registration_evidence(row: dict, index: dict) -> dict:
    registration_function = row.get("registration_function")
    address = _registration_address(registration_function)
    class_name = row.get("name")
    function = index["functions"].get(address) if address is not None else None
    calls = index["calls_by_function"].get(address, set()) if address else set()
    strings = index["strings_by_function"].get(address, set()) if address else set()

    checks = {
        "registration_function_address": address is not None,
        "function_present": function is not None,
        "class_name_resolved": isinstance(class_name, str),
        "class_string_xref": isinstance(class_name, str) and class_name in strings,
        "registration_core_call": GHIDRA_REGISTRATION_CORE in calls,
    }
    return {
        "address": address,
        "ghidra_name": function.get("name") if isinstance(function, dict) else None,
        "mnemonic_sha256": (
            function.get("mnemonic_sha256") if isinstance(function, dict) else None
        ),
        "verified": all(checks.values()),
        "checks": checks,
    }


def build_manifest(
    source: Path,
    exe: Path | None = None,
    ghidra_export: Path | None = None,
) -> dict:
    registry = extract_registry(source, exe)
    reflection = extract_reflection_fields(source, exe, registry=registry)
    ghidra_index = (
        _load_ghidra_registration_index(ghidra_export)
        if ghidra_export is not None
        else None
    )

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
            field["reflection_function"]
            for field in class_fields
            if field.get("reflection_function")
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
        if ghidra_index is not None:
            row["ghidra_registration"] = _ghidra_registration_evidence(
                source_row,
                ghidra_index,
            )
        classes.append(row)

    classes.sort(key=lambda row: (
        row.get("name") is None,
        row.get("name") or "",
        int(row["descriptor"]),
    ))

    ghidra_checked = [
        row["ghidra_registration"]
        for row in classes
        if isinstance(row.get("ghidra_registration"), dict)
    ]
    return {
        "format": FORMAT,
        "source": registry["source"],
        "source_sha256": registry["source_sha256"],
        "exe": registry["exe"],
        "exe_sha256": registry["exe_sha256"],
        "ghidra_export": str(ghidra_export) if ghidra_export is not None else None,
        "class_count": len(classes),
        "named_class_count": sum(row.get("name") is not None for row in classes),
        "reflected_class_count": sum(row["field_count"] > 0 for row in classes),
        "reflection_field_count": sum(row["field_count"] for row in classes),
        "unique_vtable_count": sum(
            row.get("unique_vtable") is not None for row in classes
        ),
        "ghidra_registration_checked_count": len(ghidra_checked),
        "ghidra_registration_verified_count": sum(
            row.get("verified") is True for row in ghidra_checked
        ),
        "ghidra_registration_mismatch_count": sum(
            row.get("verified") is not True for row in ghidra_checked
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
        "ghidra_registration_address",
        "ghidra_registration_verified",
        "ghidra_registration_class_string_xref",
        "ghidra_registration_core_call",
        "ghidra_registration_fingerprint",
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
            ghidra = row.get("ghidra_registration") or {}
            checks = ghidra.get("checks") or {}
            rendered["ghidra_registration_address"] = ghidra.get("address")
            rendered["ghidra_registration_verified"] = ghidra.get("verified")
            rendered["ghidra_registration_class_string_xref"] = checks.get(
                "class_string_xref"
            )
            rendered["ghidra_registration_core_call"] = checks.get(
                "registration_core_call"
            )
            rendered["ghidra_registration_fingerprint"] = ghidra.get(
                "mnemonic_sha256"
            )
            writer.writerow(rendered)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="recovered SHIFT.exe.c")
    parser.add_argument("--exe", type=Path, help="retail SHIFT.exe")
    parser.add_argument(
        "--ghidra-export",
        type=Path,
        help="optional SHIFT.GhidraEvidenceDatabase/1 directory for registration cross-checks",
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
    parser.add_argument(
        "--only-reflected",
        action="store_true",
        help="keep only classes with recovered reflection fields",
    )
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--csv-out", type=Path)
    args = parser.parse_args()

    report = build_manifest(args.source, args.exe, args.ghidra_export)
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
