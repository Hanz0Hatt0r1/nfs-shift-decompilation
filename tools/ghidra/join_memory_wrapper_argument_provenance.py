#!/usr/bin/env python3
"""Join source wrapper calls with instruction-level forwarding provenance.

The join substitutes concrete source argument expressions for symbolic
`input:<physical-storage>` leaves in SHIFT-MEMORY-WRAPPER-FORWARDING/1. It does
not assign semantic names to any argument or backend parameter.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

FORMAT = "SHIFT-MEMORY-WRAPPER-ARGUMENT-PROVENANCE/1"
CALLSITE_FORMAT = "SHIFT-MEMORY-WRAPPER-CALLSITE-EVIDENCE/1"
FORWARDING_FORMAT = "SHIFT-MEMORY-WRAPPER-FORWARDING/1"

_INPUT_TOKEN = re.compile(
    r"input:(?:Stack\[0x[0-9a-fA-F]+\]:\d+|[A-Za-z][A-Za-z0-9]*:\d+)"
)


def _load(path: Path, expected: str) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("format") != expected:
        raise ValueError(f"{path}: expected {expected}")
    return payload


def _input_storage(token: str) -> str:
    return token[len("input:") :]


def _storage_argument_map(
    forwarding_wrapper: dict[str, Any],
    source_callsite: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    storages = forwarding_wrapper.get("input_storage") or []
    arguments = source_callsite.get("arguments") or []
    reasons: list[str] = []
    mapping: dict[str, dict[str, Any]] = {}
    if source_callsite.get("arguments_parse_complete") is not True:
        reasons.append("source call arguments were not parsed completely")
        return mapping, reasons
    if len(arguments) != len(storages):
        reasons.append(
            f"source argument count {len(arguments)} does not match wrapper input-storage count {len(storages)}"
        )
    for index, storage in enumerate(storages):
        if not isinstance(storage, str):
            continue
        if index >= len(arguments):
            continue
        argument = arguments[index]
        if not isinstance(argument, dict):
            continue
        mapping[storage] = {
            "argument_index": index,
            "expression": argument.get("expression"),
            "integer_literals": argument.get("integer_literals") or [],
            "is_exact_integer_literal": argument.get("is_exact_integer_literal") is True,
            "exact_integer_value": argument.get("exact_integer_value"),
        }
    return mapping, reasons


def _project_symbolic_source(
    symbolic: str,
    storage_map: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if symbolic == "unresolved":
        return {
            "symbolic_source": symbolic,
            "input_storages": [],
            "source_argument_indices": [],
            "projected_expression": None,
            "projection_resolved": False,
            "projection_kind": "unresolved",
            "missing_input_storages": [],
        }

    tokens = list(dict.fromkeys(_INPUT_TOKEN.findall(symbolic)))
    if not tokens:
        return {
            "symbolic_source": symbolic,
            "input_storages": [],
            "source_argument_indices": [],
            "projected_expression": symbolic,
            "projection_resolved": True,
            "projection_kind": "wrapper-internal",
            "missing_input_storages": [],
        }

    missing: list[str] = []
    indices: list[int] = []
    projected = symbolic
    for token in tokens:
        storage = _input_storage(token)
        source = storage_map.get(storage)
        if source is None or not isinstance(source.get("expression"), str):
            missing.append(storage)
            continue
        indices.append(int(source["argument_index"]))
        projected = projected.replace(token, f"source_arg[{source['argument_index']}]({source['expression']})")

    return {
        "symbolic_source": symbolic,
        "input_storages": [_input_storage(token) for token in tokens],
        "source_argument_indices": sorted(set(indices)),
        "projected_expression": None if missing else projected,
        "projection_resolved": not missing,
        "projection_kind": "source-argument" if not missing else "unresolved-input",
        "missing_input_storages": sorted(set(missing)),
    }


def _index_forwarding_wrappers(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for wrapper in payload.get("wrappers") or []:
        if not isinstance(wrapper, dict):
            continue
        name = wrapper.get("name")
        if isinstance(name, str):
            rows[name] = wrapper
    return rows


def _join_callsite(
    source_callsite: dict[str, Any],
    forwarding_wrapper: dict[str, Any] | None,
) -> dict[str, Any]:
    wrapper_name = source_callsite.get("wrapper")
    base = {
        "caller": source_callsite.get("caller"),
        "wrapper": wrapper_name,
        "occurrence": source_callsite.get("occurrence"),
        "source_statement": source_callsite.get("source_statement"),
        "source_arguments": source_callsite.get("arguments") or [],
        "ghidra_direct_edge": source_callsite.get("ghidra_direct_edge"),
    }
    if forwarding_wrapper is None:
        return {
            **base,
            "forwarding_wrapper_present": False,
            "forwarding_confirmed": False,
            "input_storage_map": [],
            "backend_calls": [],
            "projection_complete": False,
            "projection_reasons": ["wrapper missing from forwarding report"],
        }

    storage_map, reasons = _storage_argument_map(forwarding_wrapper, source_callsite)
    storage_rows = [
        {"storage": storage, **row}
        for storage, row in storage_map.items()
    ]
    backend_calls: list[dict[str, Any]] = []
    unresolved_count = 0
    for backend in forwarding_wrapper.get("call_sites") or []:
        if not isinstance(backend, dict):
            continue
        projected_arguments: list[dict[str, Any]] = []
        for argument in backend.get("arguments") or []:
            if not isinstance(argument, dict):
                continue
            symbolic = argument.get("source")
            projection = _project_symbolic_source(
                symbolic if isinstance(symbolic, str) else "unresolved",
                storage_map,
            )
            if projection["projection_resolved"] is not True:
                unresolved_count += 1
            projected_arguments.append(
                {
                    "backend_storage": argument.get("storage"),
                    "forwarding_source_kind": argument.get("source_kind"),
                    **projection,
                }
            )
        backend_calls.append(
            {
                "instruction": backend.get("instruction"),
                "target": backend.get("target"),
                "target_name": backend.get("target_name"),
                "target_calling_convention": backend.get("target_calling_convention"),
                "forwarding_arguments_resolved": backend.get("arguments_resolved") is True,
                "forwarding_state_uncertain": backend.get("incoming_state_uncertain") is True,
                "arguments": projected_arguments,
            }
        )

    forwarding_confirmed = forwarding_wrapper.get("forwarding_confirmed") is True
    if not forwarding_confirmed:
        reasons.append("wrapper forwarding is not confirmed")
    if unresolved_count:
        reasons.append(f"{unresolved_count} backend argument projection(s) unresolved")
    complete = bool(forwarding_confirmed and not reasons and backend_calls)
    return {
        **base,
        "forwarding_wrapper_present": True,
        "forwarding_confirmed": forwarding_confirmed,
        "input_storage_map": storage_rows,
        "backend_calls": backend_calls,
        "projected_backend_call_count": len(backend_calls),
        "projected_backend_argument_count": sum(
            len(call["arguments"]) for call in backend_calls
        ),
        "unresolved_backend_argument_count": unresolved_count,
        "projection_complete": complete,
        "projection_reasons": reasons,
    }


def join_memory_wrapper_argument_provenance(
    callsites_path: Path,
    forwarding_path: Path,
) -> dict[str, Any]:
    callsites = _load(callsites_path, CALLSITE_FORMAT)
    forwarding = _load(forwarding_path, FORWARDING_FORMAT)
    forwarding_by_name = _index_forwarding_wrappers(forwarding)

    rows = [
        _join_callsite(row, forwarding_by_name.get(str(row.get("wrapper"))))
        for row in (callsites.get("callsites") or [])
        if isinstance(row, dict)
    ]
    rows.sort(
        key=lambda row: (
            str(row.get("wrapper") or ""),
            str(row.get("caller") or ""),
            int(row.get("occurrence") or 0),
        )
    )
    projected_arguments = sum(
        int(row.get("projected_backend_argument_count") or 0) for row in rows
    )
    unresolved_arguments = sum(
        int(row.get("unresolved_backend_argument_count") or 0) for row in rows
    )
    complete_rows = sum(row.get("projection_complete") is True for row in rows)

    return {
        "format": FORMAT,
        "callsites": str(callsites_path),
        "forwarding": str(forwarding_path),
        "callsite_count": len(rows),
        "projection_complete_callsite_count": complete_rows,
        "projection_incomplete_callsite_count": len(rows) - complete_rows,
        "projected_backend_argument_count": projected_arguments,
        "unresolved_backend_argument_count": unresolved_arguments,
        "all_callsites_projection_complete": bool(rows) and complete_rows == len(rows),
        "rows": rows,
        "scope": {
            "source_argument_expressions_used": True,
            "instruction_forwarding_used": True,
            "physical_backend_storage_used": True,
            "argument_provenance_projected": True,
            "argument_semantic_roles_proven": False,
            "allocator_abi_proven": False,
            "release_abi_proven": False,
            "ownership_semantics_proven": False,
            "note": (
                "A complete row maps source wrapper argument expressions into the "
                "symbolic physical backend-parameter provenance already proven by the "
                "instruction forwarding layer. It does not name any argument as size, "
                "alignment, pool selector, flags, delete kind or ownership state."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("callsites", type=Path)
    parser.add_argument("forwarding", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = join_memory_wrapper_argument_provenance(args.callsites, args.forwarding)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"callsites: {report['callsite_count']}")
    print(f"complete projections: {report['projection_complete_callsite_count']}")
    print(f"projected backend arguments: {report['projected_backend_argument_count']}")
    print(f"unresolved backend arguments: {report['unresolved_backend_argument_count']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
