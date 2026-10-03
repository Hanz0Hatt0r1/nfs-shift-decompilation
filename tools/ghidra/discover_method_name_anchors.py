#!/usr/bin/env python3
"""Discover conservative semantic method-name anchors in a Ghidra export.

Retail SHIFT contains diagnostic/assert strings which spell fully-qualified
method names such as ``MWL::Core::cPhysicsManager::GetAssetDatabase``.  This
tool joins those exact strings to their Ghidra containing functions and keeps
unique and ambiguous cases separate.

A unique anchor is still a semantic-name *candidate*, not an automatic rename:
a debug/assert string can describe nearby logic rather than prove the complete
function boundary.  Functions containing multiple distinct method-name strings
are therefore explicitly ambiguous.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

FORMAT = "SHIFT.GhidraMethodNameAnchors/1"

# Intentionally conservative.  Accept ordinary fully-qualified C++-style names
# with at least MWL::<scope>::<member>, but reject paths, format strings, spaces,
# decorated RTTI names and prose diagnostics.
_METHOD = re.compile(
    r"^MWL::(?:[A-Za-z_][A-Za-z0-9_<>]*::)+[A-Za-z_~][A-Za-z0-9_~<>]*$"
)


def _read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
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


def _is_method_anchor(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    if not _METHOD.fullmatch(value):
        return False
    if any(token in value for token in ("%", "/", "\\", "?", ".?")):
        return False
    # MWL::Class::Method is the minimum useful shape: at least two separators.
    return value.count("::") >= 2


def discover_method_name_anchors(root: Path) -> dict[str, Any]:
    functions_path = root / "functions.jsonl"
    strings_path = root / "strings_xrefs.jsonl"
    missing = [path.name for path in (functions_path, strings_path) if not path.is_file()]
    if missing:
        raise FileNotFoundError("missing required Ghidra files: " + ", ".join(missing))

    functions: dict[str, dict[str, Any]] = {}
    for row in _read_jsonl(functions_path):
        address = row.get("address")
        if isinstance(address, str):
            functions[address] = row

    anchor_rows: list[dict[str, Any]] = []
    anchors_by_function: dict[str, set[str]] = defaultdict(set)
    rows_by_function: dict[str, list[dict[str, Any]]] = defaultdict(list)
    unresolved_function_refs: set[str] = set()

    for row in _read_jsonl(strings_path):
        value = row.get("value")
        if not _is_method_anchor(value):
            continue
        containing = sorted(
            {
                function
                for function in (row.get("functions") or [])
                if isinstance(function, str)
            }
        )
        known = [function for function in containing if function in functions]
        unknown = [function for function in containing if function not in functions]
        unresolved_function_refs.update(unknown)
        anchor = {
            "string_address": row.get("address"),
            "value": value,
            "xrefs": row.get("xrefs") or [],
            "functions": containing,
            "known_functions": known,
            "unknown_functions": unknown,
            "single_known_function": known[0] if len(known) == 1 and not unknown else None,
            "status": (
                "single-function-method-string-anchor"
                if len(known) == 1 and not unknown
                else "shared-or-unresolved-method-string-anchor"
            ),
        }
        anchor_rows.append(anchor)
        if len(known) == 1 and not unknown:
            function = known[0]
            anchors_by_function[function].add(str(value))
            rows_by_function[function].append(anchor)

    function_rows: list[dict[str, Any]] = []
    for address in sorted(anchors_by_function):
        values = sorted(anchors_by_function[address])
        unique_candidate = values[0] if len(values) == 1 else None
        metadata = functions[address]
        function_rows.append(
            {
                "address": address,
                "name": metadata.get("name"),
                "calling_convention": metadata.get("calling_convention"),
                "size": metadata.get("size"),
                "mnemonic_sha256": metadata.get("mnemonic_sha256"),
                "method_anchors": values,
                "method_anchor_count": len(values),
                "anchor_string_addresses": sorted(
                    {
                        str(row.get("string_address"))
                        for row in rows_by_function[address]
                        if row.get("string_address") is not None
                    }
                ),
                "unique_method_name_candidate": unique_candidate,
                "status": (
                    "unique-method-name-anchor-candidate"
                    if unique_candidate is not None
                    else "ambiguous-method-name-anchors"
                ),
            }
        )

    anchor_rows.sort(
        key=lambda row: (
            str(row.get("value") or ""),
            str(row.get("string_address") or ""),
        )
    )
    unique_rows = [
        row for row in function_rows if row["unique_method_name_candidate"] is not None
    ]
    ambiguous_rows = [
        row for row in function_rows if row["unique_method_name_candidate"] is None
    ]

    return {
        "format": FORMAT,
        "ghidra_export": str(root),
        "function_inventory_count": len(functions),
        "method_string_anchor_count": len(anchor_rows),
        "single_function_method_string_anchor_count": sum(
            row["status"] == "single-function-method-string-anchor" for row in anchor_rows
        ),
        "shared_or_unresolved_method_string_anchor_count": sum(
            row["status"] == "shared-or-unresolved-method-string-anchor"
            for row in anchor_rows
        ),
        "functions_with_method_anchors": len(function_rows),
        "unique_method_name_candidate_count": len(unique_rows),
        "ambiguous_method_anchor_function_count": len(ambiguous_rows),
        "unresolved_function_reference_count": len(unresolved_function_refs),
        "unresolved_function_references": sorted(unresolved_function_refs),
        "anchors": anchor_rows,
        "functions": function_rows,
        "scope": {
            "exact_string_values_used": True,
            "string_xrefs_used": True,
            "function_boundaries_used": True,
            "unique_string_anchor_is_automatic_rename": False,
            "ambiguous_functions_promoted": False,
            "method_behavior_proven": False,
            "note": (
                "A unique candidate means one Ghidra function contains exactly one "
                "distinct conservative MWL::<scope>::<member> string anchor and the "
                "string resolves only to that known function. It is a high-value "
                "semantic-name candidate, not proof that the entire function exactly "
                "implements the named method. Multiple method anchors remain ambiguous."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = discover_method_name_anchors(args.ghidra_export)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"method string anchors: {report['method_string_anchor_count']}")
    print(f"functions with method anchors: {report['functions_with_method_anchors']}")
    print(f"unique method-name candidates: {report['unique_method_name_candidate_count']}")
    print(f"ambiguous functions: {report['ambiguous_method_anchor_function_count']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
