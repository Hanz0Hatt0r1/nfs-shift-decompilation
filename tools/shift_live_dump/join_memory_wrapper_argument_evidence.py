#!/usr/bin/env python3
"""Join source memory-wrapper call expressions to instruction forwarding evidence.

The join is intentionally mechanical.  A source argument is associated with a
wrapper entry-storage slot only when the recovered source arity matches the
independently observed wrapper input-storage count.  Forwarding expressions from
SHIFT-MEMORY-WRAPPER-FORWARDING/1 are then traced back to those slots.

This proves value provenance across the wrapper boundary.  It does not assign
semantic roles such as allocation size, pool selector, alignment or release
flags.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

CALLSITE_FORMAT = "SHIFT-MEMORY-WRAPPER-CALLSITES/1"
FORWARDING_FORMAT = "SHIFT-MEMORY-WRAPPER-FORWARDING/1"
FORMAT = "SHIFT-MEMORY-WRAPPER-ARGUMENT-JOIN/1"


def _load_json(path: Path, expected_format: str) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("format") != expected_format:
        raise ValueError(f"{path}: expected {expected_format}")
    return report


def _forwarding_by_name(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for wrapper in report.get("wrappers") or []:
        if not isinstance(wrapper, dict):
            continue
        name = wrapper.get("name")
        if isinstance(name, str):
            rows[name] = wrapper
    return rows


def _argument_expressions(callsite: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for argument in callsite.get("arguments") or []:
        if isinstance(argument, dict):
            out.append(str(argument.get("expression") or ""))
    return out


def _input_storages_in_source(source: str, input_storage: list[str]) -> list[str]:
    return [storage for storage in input_storage if f"input:{storage}" in source]


def _backend_argument_join(
    argument: dict[str, Any],
    input_storage: list[str],
    source_arguments: list[str],
    join_ready: bool,
) -> dict[str, Any]:
    forwarding_source = str(argument.get("source") or "unresolved")
    storages = _input_storages_in_source(forwarding_source, input_storage)
    source_indices = [input_storage.index(storage) for storage in storages]
    mapped = bool(
        join_ready
        and argument.get("resolved") is True
        and len(source_indices) == 1
        and source_indices[0] < len(source_arguments)
    )
    source_index = source_indices[0] if mapped else None
    source_expression = source_arguments[source_index] if source_index is not None else None
    wrapper_internal = bool(
        argument.get("resolved") is True
        and len(storages) == 0
        and forwarding_source != "unresolved"
    )
    return {
        "backend_storage": argument.get("storage"),
        "forwarding_source": forwarding_source,
        "forwarding_source_kind": argument.get("source_kind"),
        "forwarding_resolved": argument.get("resolved") is True,
        "wrapper_input_storages": storages,
        "source_argument_indices": source_indices,
        "source_argument_index": source_index,
        "source_argument_expression": source_expression,
        "source_argument_mapped": mapped,
        "wrapper_internal_source": wrapper_internal,
    }


def _join_callsite(
    callsite: dict[str, Any],
    forwarding: dict[str, Any] | None,
) -> dict[str, Any]:
    source_arguments = _argument_expressions(callsite)
    if forwarding is None:
        return {
            **callsite,
            "forwarding_record_present": False,
            "forwarding_confirmed": False,
            "forwarding_join_ready": False,
            "ghidra_crosschecked_join": False,
            "backend_calls": [],
            "mapped_source_argument_indices": [],
            "unmapped_source_argument_indices": list(range(len(source_arguments))),
            "backend_argument_count": 0,
            "source_mapped_backend_argument_count": 0,
            "wrapper_internal_backend_argument_count": 0,
            "unresolved_backend_argument_count": 0,
            "missing": ["forwarding_record"],
        }

    input_storage = [str(value) for value in (forwarding.get("input_storage") or [])]
    source_arity_matches_storage = len(source_arguments) == len(input_storage)
    forwarding_confirmed = forwarding.get("forwarding_confirmed") is True
    join_ready = bool(
        callsite.get("arity_matches_physical_parameter_count") is True
        and source_arity_matches_storage
        and forwarding_confirmed
    )

    backend_calls: list[dict[str, Any]] = []
    mapped_indices: set[int] = set()
    backend_argument_count = 0
    source_mapped_count = 0
    wrapper_internal_count = 0
    unresolved_count = 0

    for site in forwarding.get("call_sites") or []:
        if not isinstance(site, dict):
            continue
        argument_rows: list[dict[str, Any]] = []
        for argument in site.get("arguments") or []:
            if not isinstance(argument, dict):
                continue
            joined = _backend_argument_join(
                argument,
                input_storage,
                source_arguments,
                join_ready,
            )
            argument_rows.append(joined)
            backend_argument_count += 1
            if joined["source_argument_mapped"]:
                source_mapped_count += 1
                assert joined["source_argument_index"] is not None
                mapped_indices.add(int(joined["source_argument_index"]))
            elif joined["wrapper_internal_source"]:
                wrapper_internal_count += 1
            else:
                unresolved_count += 1
        backend_calls.append(
            {
                "instruction": site.get("instruction"),
                "target": site.get("target"),
                "target_name": site.get("target_name"),
                "target_calling_convention": site.get("target_calling_convention"),
                "forwarding_arguments_resolved": site.get("arguments_resolved") is True,
                "incoming_state_uncertain": site.get("incoming_state_uncertain") is True,
                "arguments": argument_rows,
            }
        )

    all_source_indices = set(range(len(source_arguments)))
    missing: list[str] = []
    if not source_arity_matches_storage:
        missing.append("source_arity_vs_forwarding_input_storage")
    if callsite.get("arity_matches_physical_parameter_count") is not True:
        missing.append("source_arity_vs_physical_parameter_count")
    if not forwarding_confirmed:
        missing.append("forwarding_not_confirmed")

    return {
        **callsite,
        "forwarding_record_present": True,
        "forwarding_input_storage": input_storage,
        "source_arity_matches_forwarding_input_storage": source_arity_matches_storage,
        "forwarding_confirmed": forwarding_confirmed,
        "forwarding_join_ready": join_ready,
        "ghidra_crosschecked_join": bool(
            join_ready and callsite.get("ghidra_direct_edge") is True
        ),
        "backend_calls": backend_calls,
        "mapped_source_argument_indices": sorted(mapped_indices),
        "unmapped_source_argument_indices": sorted(all_source_indices - mapped_indices),
        "backend_argument_count": backend_argument_count,
        "source_mapped_backend_argument_count": source_mapped_count,
        "wrapper_internal_backend_argument_count": wrapper_internal_count,
        "unresolved_backend_argument_count": unresolved_count,
        "missing": missing,
    }


def join_memory_wrapper_argument_evidence(
    callsites_path: Path,
    forwarding_path: Path,
) -> dict[str, Any]:
    callsites = _load_json(callsites_path, CALLSITE_FORMAT)
    forwarding = _load_json(forwarding_path, FORWARDING_FORMAT)
    forwarding_rows = _forwarding_by_name(forwarding)

    rows = [
        _join_callsite(callsite, forwarding_rows.get(str(callsite.get("wrapper"))))
        for callsite in (callsites.get("callsites") or [])
        if isinstance(callsite, dict)
    ]
    rows.sort(
        key=lambda row: (
            row.get("wrapper") or "",
            row.get("caller") or "",
            int(row.get("occurrence") or 0),
        )
    )

    return {
        "format": FORMAT,
        "callsites": str(callsites_path),
        "callsites_source": callsites.get("source"),
        "callsites_source_sha256": callsites.get("source_sha256"),
        "forwarding": str(forwarding_path),
        "callsite_count": len(rows),
        "forwarding_record_callsite_count": sum(
            row["forwarding_record_present"] is True for row in rows
        ),
        "forwarding_join_ready_callsite_count": sum(
            row["forwarding_join_ready"] is True for row in rows
        ),
        "ghidra_crosschecked_join_callsite_count": sum(
            row["ghidra_crosschecked_join"] is True for row in rows
        ),
        "backend_argument_count": sum(
            int(row["backend_argument_count"]) for row in rows
        ),
        "source_mapped_backend_argument_count": sum(
            int(row["source_mapped_backend_argument_count"]) for row in rows
        ),
        "wrapper_internal_backend_argument_count": sum(
            int(row["wrapper_internal_backend_argument_count"]) for row in rows
        ),
        "unresolved_backend_argument_count": sum(
            int(row["unresolved_backend_argument_count"]) for row in rows
        ),
        "rows": rows,
        "scope": {
            "source_expression_to_entry_storage_joined": True,
            "entry_storage_to_backend_storage_joined": True,
            "argument_semantic_roles_proven": False,
            "allocation_size_role_proven": False,
            "pool_selector_role_proven": False,
            "alignment_role_proven": False,
            "release_flag_role_proven": False,
            "allocator_abi_proven": False,
            "ownership_semantics_proven": False,
            "note": (
                "A ready row proves mechanical provenance from a recovered source "
                "argument position through wrapper entry storage to modeled backend "
                "argument storage. Source arity must agree with both the callsite ABI "
                "inventory and forwarding input-storage count. No semantic parameter "
                "names are inferred from position or value appearance."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("callsites", type=Path, help="SHIFT-MEMORY-WRAPPER-CALLSITES/1 JSON")
    parser.add_argument("--forwarding", type=Path, required=True)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = join_memory_wrapper_argument_evidence(args.callsites, args.forwarding)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"callsites: {report['callsite_count']}")
    print(f"join-ready callsites: {report['forwarding_join_ready_callsite_count']}")
    print(f"Ghidra-crosschecked joins: {report['ghidra_crosschecked_join_callsite_count']}")
    print(f"mapped backend arguments: {report['source_mapped_backend_argument_count']}")
    print(f"wrapper-internal backend arguments: {report['wrapper_internal_backend_argument_count']}")
    print(f"unresolved backend arguments: {report['unresolved_backend_argument_count']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
