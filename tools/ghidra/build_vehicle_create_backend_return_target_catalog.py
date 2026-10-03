#!/usr/bin/env python3
"""Catalog exact create-backend return targets in the saved static Ghidra corpus.

The input frontier already identifies a finite set of exact inner targets whose
machine values/control feed the two vehicle create backends.  This builder joins
those addresses to the saved full Ghidra export (`functions.jsonl`,
`callgraph.jsonl`, `strings_xrefs.jsonl`) and emits a deterministic instruction
export worklist.

Function metadata, direct-call context and exact string references are discovery
facts only.  Even an allocation diagnostic referenced by one target does not
prove that the target returns an allocated pointer or establish allocator ABI,
operator-new, object-size, ownership, constructor, or whole-lifetime identity.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

FORMAT = "SHIFT.VehicleCreateBackendReturnTargetCatalog/1"
FRONTIER_FORMAT = "SHIFT.VehicleCreateBackendReturnOriginFrontier/1"

ALLOC_DIAGNOSTIC = re.compile(
    r"Unable to allocate .*bytes of memory from the pool", re.IGNORECASE
)
FREE_DIAGNOSTIC = re.compile(r"Error freeing .* from pool", re.IGNORECASE)


def _read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_no}: expected object")
            yield value


def _norm(value: Any) -> str | None:
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


def _load_frontier(path: Path) -> tuple[dict[str, Any], list[str]]:
    report = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(report, dict) or report.get("format") != FRONTIER_FORMAT:
        raise ValueError(f"{path}: expected {FRONTIER_FORMAT}")
    if report.get("all_backend_machine_return_origins_resolved") is not True:
        raise ValueError("backend return-origin frontier is not fully resolved")

    raw = report.get("next_backend_return_targets")
    if not isinstance(raw, list) or not raw:
        raise ValueError("backend return-origin frontier has no next targets")
    targets: list[str] = []
    for value in raw:
        address = _norm(value)
        if address is None:
            raise ValueError(f"invalid backend return target: {value!r}")
        targets.append(address)
    if len(set(targets)) != len(targets):
        raise ValueError("backend return-origin frontier contains duplicate targets")
    if targets != sorted(targets):
        raise ValueError("backend return-origin frontier targets must be sorted")
    declared_count = report.get("next_backend_return_target_count")
    if declared_count is not None and declared_count != len(targets):
        raise ValueError("backend return-origin frontier target count drift")
    return report, targets


def _load_functions(root: Path) -> dict[str, dict[str, Any]]:
    path = root / "functions.jsonl"
    if not path.is_file():
        raise FileNotFoundError(f"missing required Ghidra file: {path}")
    result: dict[str, dict[str, Any]] = {}
    for row in _read_jsonl(path):
        address = _norm(row.get("address"))
        if address is None:
            continue
        if address in result:
            raise ValueError(f"{path}: duplicate function {address}")
        result[address] = row
    return result


def _load_callgraph(
    root: Path,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
    path = root / "callgraph.jsonl"
    if not path.is_file():
        raise FileNotFoundError(f"missing required Ghidra file: {path}")
    outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
    incoming: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: set[tuple[str, str | None, str]] = set()
    for row in _read_jsonl(path):
        if row.get("indirect") is not False:
            continue
        source = _norm(row.get("from_function"))
        target = _norm(row.get("to"))
        instruction = _norm(row.get("instruction"))
        if source is None or target is None:
            continue
        key = source, instruction, target
        if key in seen:
            continue
        seen.add(key)
        edge = {
            "from": source,
            "instruction": instruction,
            "to": target,
            "to_name": row.get("to_name"),
        }
        outgoing[source].append(edge)
        incoming[target].append(edge)
    for rows in outgoing.values():
        rows.sort(key=lambda row: (row.get("instruction") or "", row["to"]))
    for rows in incoming.values():
        rows.sort(key=lambda row: (row["from"], row.get("instruction") or ""))
    return dict(outgoing), dict(incoming)


def _load_strings(root: Path) -> dict[str, list[dict[str, Any]]]:
    path = root / "strings_xrefs.jsonl"
    if not path.is_file():
        raise FileNotFoundError(f"missing required Ghidra file: {path}")
    by_function: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in _read_jsonl(path):
        value = row.get("value")
        if not isinstance(value, str):
            continue
        functions = []
        for item in row.get("functions") or []:
            address = _norm(item)
            if address is not None:
                functions.append(address)
        if not functions:
            continue
        xrefs = sorted(
            {
                address
                for item in row.get("xrefs") or []
                if (address := _norm(item)) is not None
            }
        )
        string_address = _norm(row.get("address"))
        record = {
            "string_address": string_address,
            "value": value,
            "xrefs": xrefs,
            "allocation_diagnostic_text_match": bool(ALLOC_DIAGNOSTIC.search(value)),
            "free_diagnostic_text_match": bool(FREE_DIAGNOSTIC.search(value)),
        }
        for function in sorted(set(functions)):
            by_function[function].append(record)
    for rows in by_function.values():
        rows.sort(key=lambda row: (row.get("string_address") or "", row["value"]))
    return dict(by_function)


def _function_record(
    address: str,
    metadata: dict[str, Any] | None,
    outgoing: dict[str, list[dict[str, Any]]],
    incoming: dict[str, list[dict[str, Any]]],
    strings: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    refs = list(strings.get(address, ()))
    present = metadata is not None
    external = metadata.get("external") is True if present else None
    export_eligible = bool(present and external is not True)
    blockers: list[str] = []
    if not present:
        blockers.append("target_absent_from_functions_jsonl")
    elif external is True:
        blockers.append("target_is_external_function")

    return {
        "address": address,
        "present": present,
        "name": metadata.get("name") if present else None,
        "signature": metadata.get("signature") if present else None,
        "calling_convention": metadata.get("calling_convention") if present else None,
        "parameters": metadata.get("parameters") if present else None,
        "external": external,
        "size": metadata.get("size") if present else None,
        "mnemonic_sha256": metadata.get("mnemonic_sha256") if present else None,
        "incoming_direct_calls": list(incoming.get(address, ())),
        "outgoing_direct_calls": list(outgoing.get(address, ())),
        "exact_string_references": refs,
        "allocation_diagnostic_text_reference_present": any(
            row["allocation_diagnostic_text_match"] is True for row in refs
        ),
        "free_diagnostic_text_reference_present": any(
            row["free_diagnostic_text_match"] is True for row in refs
        ),
        "instruction_export_eligible": export_eligible,
        "blockers": blockers,
        "returned_allocation_pointer_role_proven": False,
    }


def build_vehicle_create_backend_return_target_catalog(
    frontier_path: Path,
    ghidra_export: Path,
) -> dict[str, Any]:
    frontier, targets = _load_frontier(frontier_path)
    functions = _load_functions(ghidra_export)
    outgoing, incoming = _load_callgraph(ghidra_export)
    strings = _load_strings(ghidra_export)

    rows = [
        _function_record(address, functions.get(address), outgoing, incoming, strings)
        for address in targets
    ]
    export_addresses = [
        row["address"] for row in rows if row["instruction_export_eligible"] is True
    ]
    blockers = [
        {"target": row["address"], "id": blocker}
        for row in rows
        for blocker in row["blockers"]
    ]
    all_present = all(row["present"] is True for row in rows)
    all_internal = all(row["instruction_export_eligible"] is True for row in rows)

    create_contexts = frontier.get("vehicle_create_bridges")
    if not isinstance(create_contexts, list):
        raise ValueError("backend return-origin frontier vehicle_create_bridges must be a list")

    return {
        "format": FORMAT,
        "inputs": {
            "backend_return_origin_frontier": str(frontier_path),
            "ghidra_export": str(ghidra_export),
        },
        "target_count": len(targets),
        "targets": rows,
        "all_targets_present_in_functions": all_present,
        "all_targets_instruction_export_eligible": all_internal,
        "instruction_export_address_count": len(export_addresses),
        "instruction_export_addresses": export_addresses,
        "vehicle_create_bridges": create_contexts,
        "blockers": blockers,
        "scope": {
            "full_static_ghidra_function_inventory_used": True,
            "direct_callgraph_context_used": True,
            "exact_string_xrefs_used": True,
            "target_selection_ranked": False,
            "instruction_export_worklist_exact": True,
            "allocation_diagnostic_text_is_return_role_proof": False,
            "returned_allocation_pointer_role_proven": False,
            "allocator_abi_proven": False,
            "operator_new_identity_proven": False,
            "object_size_proven": False,
            "constructor_semantics_proven": False,
            "ownership_semantics_proven": False,
            "same_runtime_object_as_vehicle_update_proven": False,
            "note": (
                "This catalog only attaches exact saved Ghidra metadata, direct-call context "
                "and string xrefs to the finite return-origin target set. A diagnostic string "
                "reference is discovery evidence and cannot establish the semantic role of the "
                "function's return value."
            ),
        },
    }


def _write_targets(path: Path, report: dict[str, Any]) -> None:
    values = report.get("instruction_export_addresses")
    if not isinstance(values, list):
        raise ValueError("catalog instruction_export_addresses must be a list")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(str(address) + "\n" for address in values), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backend_return_origin_frontier", type=Path)
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--targets-out", type=Path)
    args = parser.parse_args()

    report = build_vehicle_create_backend_return_target_catalog(
        args.backend_return_origin_frontier,
        args.ghidra_export,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    if args.targets_out:
        _write_targets(args.targets_out, report)

    print(f"format: {report['format']}")
    print(f"targets: {report['target_count']}")
    print(f"targets present: {report['all_targets_present_in_functions']}")
    print(f"instruction-export eligible: {report['instruction_export_address_count']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    if args.targets_out:
        print(f"target list: {args.targets_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
