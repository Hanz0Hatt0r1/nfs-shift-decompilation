#!/usr/bin/env python3
"""Join proven release-wrapper pointer storage back to source call arguments.

This tool consumes the mechanical source->wrapper-entry provenance report and
SHIFT-MEMORY-RELEASE-POINTER-CHAIN/1. It assigns the semantic role
`released-pointer` only when one proven release-chain path identifies exactly
one wrapper input storage and the source callsite has a complete positional
entry-storage join.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ARGUMENT_JOIN_FORMAT = "SHIFT-MEMORY-WRAPPER-ARGUMENT-JOIN/1"
RELEASE_CHAIN_FORMAT = "SHIFT-MEMORY-RELEASE-POINTER-CHAIN/1"
FORMAT = "SHIFT-MEMORY-RELEASED-POINTER-ROLE-JOIN/1"


def _load_json(path: Path, expected: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("format") != expected:
        raise ValueError(f"{path}: expected {expected}")
    return value


def _source_arguments(row: dict[str, Any]) -> list[str]:
    return [
        str(argument.get("expression") or "")
        for argument in (row.get("arguments") or [])
        if isinstance(argument, dict)
    ]


def _proven_storage_by_wrapper(chain: dict[str, Any]) -> dict[str, list[str]]:
    result: dict[str, set[str]] = {}
    if chain.get("release_pointer_to_wrapper_storage_proven") is not True:
        return {}
    for path in chain.get("wrapper_paths") or []:
        if not isinstance(path, dict) or path.get("released_pointer_path_proven") is not True:
            continue
        wrapper = path.get("wrapper")
        storage = path.get("wrapper_input_storage")
        if isinstance(wrapper, str) and isinstance(storage, str) and storage:
            result.setdefault(wrapper, set()).add(storage)
    return {wrapper: sorted(storages) for wrapper, storages in result.items()}


def _join_row(row: dict[str, Any], wrapper_storages: list[str]) -> dict[str, Any]:
    row_ready = row.get("forwarding_join_ready") is True
    input_storage = [str(value) for value in (row.get("forwarding_input_storage") or [])]
    source_arguments = _source_arguments(row)
    storage_unique = len(wrapper_storages) == 1
    storage = wrapper_storages[0] if storage_unique else None

    source_index: int | None = None
    source_expression: str | None = None
    storage_present = isinstance(storage, str) and storage in input_storage
    if row_ready and storage_present:
        candidate = input_storage.index(storage)
        if candidate < len(source_arguments):
            source_index = candidate
            source_expression = source_arguments[candidate]

    role_proven = bool(
        row_ready
        and storage_unique
        and storage_present
        and source_index is not None
        and source_expression is not None
    )

    missing: list[str] = []
    if not wrapper_storages:
        missing.append("released_pointer_wrapper_storage_not_proven")
    elif not storage_unique:
        missing.append("conflicting_released_pointer_wrapper_storages")
    if not row_ready:
        missing.append("source_to_wrapper_join_not_ready")
    if storage_unique and not storage_present:
        missing.append("released_pointer_storage_not_in_wrapper_input_storage")
    if row_ready and storage_present and source_index is None:
        missing.append("released_pointer_source_argument_not_mappable")

    return {
        "caller": row.get("caller"),
        "wrapper": row.get("wrapper"),
        "occurrence": row.get("occurrence"),
        "ghidra_direct_edge": row.get("ghidra_direct_edge") is True,
        "forwarding_join_ready": row_ready,
        "released_pointer_wrapper_storages": list(wrapper_storages),
        "released_pointer_wrapper_storage": storage if storage_unique else None,
        "released_pointer_source_argument_index": source_index if role_proven else None,
        "released_pointer_source_argument_expression": source_expression if role_proven else None,
        "released_pointer_role_proven": role_proven,
        "missing": missing,
    }


def join_released_pointer_role(argument_join_path: Path, release_chain_path: Path) -> dict[str, Any]:
    argument_join = _load_json(argument_join_path, ARGUMENT_JOIN_FORMAT)
    release_chain = _load_json(release_chain_path, RELEASE_CHAIN_FORMAT)
    storages_by_wrapper = _proven_storage_by_wrapper(release_chain)
    backend_chain_proven = release_chain.get("release_pointer_to_wrapper_storage_proven") is True

    rows = [
        _join_row(row, storages_by_wrapper.get(str(row.get("wrapper")), []))
        for row in (argument_join.get("rows") or [])
        if isinstance(row, dict)
    ]
    rows.sort(
        key=lambda row: (
            str(row.get("wrapper") or ""),
            str(row.get("caller") or ""),
            int(row.get("occurrence") or 0),
        )
    )
    proven_rows = [row for row in rows if row["released_pointer_role_proven"] is True]

    return {
        "format": FORMAT,
        "argument_join": str(argument_join_path),
        "release_pointer_chain": str(release_chain_path),
        "backend_release_pointer_role_proven": backend_chain_proven,
        "proven_wrapper_input_storage": storages_by_wrapper,
        "callsite_count": len(rows),
        "released_pointer_role_callsite_count": len(proven_rows),
        "released_pointer_source_argument_indices": sorted(
            {
                int(row["released_pointer_source_argument_index"])
                for row in proven_rows
                if row.get("released_pointer_source_argument_index") is not None
            }
        ),
        "rows": rows,
        "scope": {
            "release_diagnostic_chain_role_used": backend_chain_proven,
            "source_to_wrapper_entry_provenance_used": True,
            "released_pointer_role_proven": bool(backend_chain_proven and proven_rows),
            "release_flag_role_proven": False,
            "delete_kind_role_proven": False,
            "pool_selector_role_proven": False,
            "operator_delete_identity_proven": False,
            "ownership_semantics_proven": False,
            "note": (
                "A positive row proves that one parsed source argument occupies the exact "
                "wrapper entry storage instruction-traced to the retail pool-free `%p` "
                "diagnostic. No semantics are assigned to other release arguments."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("argument_join", type=Path)
    parser.add_argument("--release-chain", type=Path, required=True)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = join_released_pointer_role(args.argument_join, args.release_chain)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"backend release-pointer role proven: {report['backend_release_pointer_role_proven']}")
    print(f"released-pointer callsites: {report['released_pointer_role_callsite_count']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
