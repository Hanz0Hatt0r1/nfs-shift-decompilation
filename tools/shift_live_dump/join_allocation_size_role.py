#!/usr/bin/env python3
"""Join a proven backend `%d` storage back to wrapper source arguments.

This tool consumes mechanical source->backend provenance and the independent
allocation-diagnostic slice. It assigns the semantic role `allocation-size`
only when the diagnostic slice proves one physical FUN_00638020 entry storage
for `%d` and that exact backend storage maps to one parsed source argument.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ARGUMENT_JOIN_FORMAT = "SHIFT-MEMORY-WRAPPER-ARGUMENT-JOIN/1"
DIAGNOSTIC_SLICE_FORMAT = "SHIFT-MEMORY-ALLOCATION-DIAGNOSTIC-SLICE/1"
FORMAT = "SHIFT-MEMORY-ALLOCATION-SIZE-ROLE-JOIN/1"
ALLOCATION_BACKEND = "0x00638020"


def _load_json(path: Path, expected: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("format") != expected:
        raise ValueError(f"{path}: expected {expected}")
    return value


def _norm_address(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    token = value.strip().lower()
    if token.startswith("fun_"):
        token = token[4:]
    if token.startswith("0x"):
        token = token[2:]
    try:
        return f"0x{int(token, 16):08x}"
    except ValueError:
        return None


def _allocation_observations(row: dict[str, Any], size_storage: str | None) -> list[dict[str, Any]]:
    if size_storage is None:
        return []
    observations: list[dict[str, Any]] = []
    for call in row.get("backend_calls") or []:
        if not isinstance(call, dict) or _norm_address(call.get("target")) != ALLOCATION_BACKEND:
            continue
        for argument in call.get("arguments") or []:
            if not isinstance(argument, dict):
                continue
            if str(argument.get("backend_storage") or "") != size_storage:
                continue
            observations.append(
                {
                    "backend_call_instruction": call.get("instruction"),
                    "backend_target": ALLOCATION_BACKEND,
                    "backend_storage": size_storage,
                    "forwarding_source": argument.get("forwarding_source"),
                    "source_argument_index": argument.get("source_argument_index"),
                    "source_argument_expression": argument.get("source_argument_expression"),
                    "source_argument_mapped": argument.get("source_argument_mapped") is True,
                }
            )
    return observations


def _join_row(
    row: dict[str, Any],
    diagnostic_proven: bool,
    size_storage: str | None,
) -> dict[str, Any]:
    observations = _allocation_observations(row, size_storage)
    mapped = [
        item for item in observations
        if item["source_argument_mapped"] is True
        and isinstance(item.get("source_argument_index"), int)
    ]
    indices = sorted({int(item["source_argument_index"]) for item in mapped})
    expressions = sorted(
        {
            str(item["source_argument_expression"])
            for item in mapped
            if item.get("source_argument_expression") is not None
        }
    )
    row_ready = row.get("forwarding_join_ready") is True
    role_proven = bool(diagnostic_proven and row_ready and len(indices) == 1 and observations)
    source_index = indices[0] if role_proven else None
    source_expression = None
    if role_proven:
        matching = [item for item in mapped if item["source_argument_index"] == source_index]
        values = {
            str(item["source_argument_expression"])
            for item in matching
            if item.get("source_argument_expression") is not None
        }
        if len(values) == 1:
            source_expression = next(iter(values))
        else:
            role_proven = False
            source_index = None

    missing: list[str] = []
    if not diagnostic_proven:
        missing.append("allocation_size_backend_storage_not_proven")
    if not row_ready:
        missing.append("source_to_backend_join_not_ready")
    if diagnostic_proven and row_ready and not observations:
        missing.append("allocation_backend_size_storage_not_observed")
    if len(indices) > 1:
        missing.append("conflicting_source_argument_indices")
    if role_proven is False and len(indices) == 1 and expressions and source_expression is None:
        missing.append("conflicting_source_argument_expressions")

    return {
        "caller": row.get("caller"),
        "wrapper": row.get("wrapper"),
        "occurrence": row.get("occurrence"),
        "ghidra_direct_edge": row.get("ghidra_direct_edge") is True,
        "forwarding_join_ready": row_ready,
        "allocation_backend_storage": size_storage,
        "allocation_size_observations": observations,
        "allocation_size_source_argument_indices": indices,
        "allocation_size_source_argument_index": source_index,
        "allocation_size_source_argument_expression": source_expression,
        "allocation_size_role_proven": role_proven,
        "missing": missing,
    }


def join_allocation_size_role(argument_join_path: Path, diagnostic_slice_path: Path) -> dict[str, Any]:
    argument_join = _load_json(argument_join_path, ARGUMENT_JOIN_FORMAT)
    diagnostic_slice = _load_json(diagnostic_slice_path, DIAGNOSTIC_SLICE_FORMAT)
    diagnostic_proven = diagnostic_slice.get("allocation_size_role_proven") is True
    size_storage = (
        str(diagnostic_slice.get("allocation_size_entry_storage"))
        if diagnostic_proven and diagnostic_slice.get("allocation_size_entry_storage")
        else None
    )

    rows = [
        _join_row(row, diagnostic_proven, size_storage)
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
    proven_rows = [row for row in rows if row["allocation_size_role_proven"] is True]

    return {
        "format": FORMAT,
        "argument_join": str(argument_join_path),
        "diagnostic_slice": str(diagnostic_slice_path),
        "allocation_backend": ALLOCATION_BACKEND,
        "allocation_size_backend_storage": size_storage,
        "backend_allocation_size_role_proven": diagnostic_proven,
        "callsite_count": len(rows),
        "allocation_size_role_callsite_count": len(proven_rows),
        "allocation_size_source_argument_indices": sorted(
            {
                int(row["allocation_size_source_argument_index"])
                for row in proven_rows
                if row.get("allocation_size_source_argument_index") is not None
            }
        ),
        "rows": rows,
        "scope": {
            "backend_diagnostic_role_used": diagnostic_proven,
            "source_to_backend_provenance_used": True,
            "allocation_size_role_proven": bool(diagnostic_proven and proven_rows),
            "pool_selector_role_proven": False,
            "alignment_role_proven": False,
            "allocator_abi_proven": False,
            "ownership_semantics_proven": False,
            "note": (
                "A positive row proves that one parsed wrapper source argument reaches the "
                "physical FUN_00638020 storage independently proven to supply the allocation "
                "diagnostic `%d` value. No other allocator argument roles are inferred."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("argument_join", type=Path)
    parser.add_argument("--diagnostic-slice", type=Path, required=True)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = join_allocation_size_role(args.argument_join, args.diagnostic_slice)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"backend allocation-size role proven: {report['backend_allocation_size_role_proven']}")
    print(f"allocation-size callsites: {report['allocation_size_role_callsite_count']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
