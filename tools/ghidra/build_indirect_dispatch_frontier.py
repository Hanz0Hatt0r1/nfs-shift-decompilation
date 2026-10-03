#!/usr/bin/env python3
"""Build a fail-closed static dispatch frontier for ownerless SHIFT functions.

The direct callgraph cannot identify callers reached through vtables, callbacks,
or other function-pointer tables.  This tool inventories those possibilities
without promoting any heuristic table to a class/owner identity.

Evidence layers are kept separate:

* functions/callgraph/switches/static-table bytes are direct Ghidra observations;
* vtables.json and constructors.jsonl are exporter heuristic candidate sets;
* a raw pointer occurrence is only a byte occurrence, never an ownership edge.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

FORMAT = "SHIFT.GhidraIndirectDispatchFrontier/1"
VTABLE_FORMAT = "SHIFT.GhidraVtableCandidates/1"
EVIDENCE_STATES = {"proven", "verified", "inferred", "ambiguous", "unknown"}


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


def _address(value: str) -> int:
    try:
        return int(value, 0)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid address: {value!r}") from exc


def _normalize_address(value: str) -> str:
    return f"0x{_address(value):08x}"


def _address_key(value: Any) -> tuple[int, str]:
    if isinstance(value, str):
        try:
            return _address(value), value
        except ValueError:
            pass
    return (1 << 63), str(value or "")


def _edge(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "from_function": row.get("from_function"),
        "from_name": row.get("from_name"),
        "instruction": row.get("instruction"),
        "to": row.get("to"),
        "to_name": row.get("to_name"),
        "indirect": row.get("indirect"),
    }


def _pointer_hex(address: str, pointer_size: int) -> str:
    value = _address(address)
    max_value = (1 << (8 * pointer_size)) - 1
    if value > max_value:
        raise ValueError(f"{address}: does not fit {pointer_size}-byte pointer")
    return value.to_bytes(pointer_size, "little").hex()


def _raw_pointer_occurrences(
    rows: list[dict[str, Any]], target: str, pointer_size: int
) -> list[dict[str, Any]]:
    needle = _pointer_hex(target, pointer_size)
    result: list[dict[str, Any]] = []
    for row in rows:
        raw_hex = row.get("raw_hex")
        base = row.get("address")
        if not isinstance(raw_hex, str) or not isinstance(base, str):
            continue
        if len(raw_hex) % 2:
            raise ValueError(f"static table {base}: raw_hex has odd length")
        lowered = raw_hex.lower()
        cursor = 0
        while True:
            position = lowered.find(needle, cursor)
            if position < 0:
                break
            if position % 2:
                raise ValueError(f"static table {base}: pointer match not byte aligned")
            byte_offset = position // 2
            result.append(
                {
                    "table_address": base,
                    "data_type": row.get("data_type"),
                    "length": row.get("length"),
                    "raw_truncated": row.get("raw_truncated"),
                    "byte_offset": byte_offset,
                    "cell_address": f"0x{_address(base) + byte_offset:08x}",
                    "pointer_aligned": byte_offset % pointer_size == 0,
                    "evidence_state": "verified",
                    "semantic_role_proven": False,
                }
            )
            cursor = position + 2
    result.sort(key=lambda item: (_address_key(item["table_address"]), item["byte_offset"]))
    return result


def _vtable_memberships(vtables: dict[str, Any], target: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for table in vtables.get("vtables") or []:
        if not isinstance(table, dict):
            raise ValueError("vtables.json: expected vtable object")
        slots = table.get("slots") or []
        matching = [slot for slot in slots if isinstance(slot, dict) and slot.get("target") == target]
        if not matching:
            continue
        result.append(
            {
                "vtable_address": table.get("address"),
                "block": table.get("block"),
                "slot_count": table.get("slot_count"),
                "matching_slots": [
                    {
                        "slot": slot.get("slot"),
                        "target": slot.get("target"),
                        "name": slot.get("name"),
                    }
                    for slot in matching
                ],
                "function_xrefs": sorted(
                    {value for value in table.get("function_xrefs") or [] if isinstance(value, str)},
                    key=lambda value: _address_key(value),
                ),
                "evidence_state": "ambiguous",
                "heuristic_vtable_candidate": True,
                "class_identity_proven": False,
            }
        )
    result.sort(key=lambda item: _address_key(item.get("vtable_address")))
    return result


def _constructor_candidates(
    rows: list[dict[str, Any]], vtable_addresses: set[str]
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in rows:
        addresses = {
            value for value in row.get("vtables") or [] if isinstance(value, str)
        }
        matching = sorted(addresses & vtable_addresses, key=_address_key)
        if not matching:
            continue
        result.append(
            {
                "function": row.get("function"),
                "name": row.get("name"),
                "matching_vtables": matching,
                "status": row.get("status"),
                "instruction_preview": row.get("instruction_preview") or [],
                "evidence_state": "ambiguous",
                "constructor_role_proven": False,
            }
        )
    result.sort(key=lambda item: _address_key(item.get("function")))
    return result


def build_indirect_dispatch_frontier(root: Path, targets: Iterable[str]) -> dict[str, Any]:
    required = (
        "binary.json",
        "functions.jsonl",
        "callgraph.jsonl",
        "vtables.json",
        "constructors.jsonl",
        "static_tables.jsonl",
        "switches.jsonl",
        "strings_xrefs.jsonl",
    )
    missing = [name for name in required if not (root / name).is_file()]
    if missing:
        raise FileNotFoundError("missing required Ghidra files: " + ", ".join(missing))

    normalized_targets = []
    seen_targets: set[str] = set()
    for value in targets:
        address = _normalize_address(value)
        if address not in seen_targets:
            seen_targets.add(address)
            normalized_targets.append(address)
    if not normalized_targets:
        raise ValueError("at least one target address is required")

    binary = json.loads((root / "binary.json").read_text(encoding="utf-8"))
    if not isinstance(binary, dict):
        raise ValueError("binary.json must contain an object")
    pointer_size = binary.get("pointer_size")
    if not isinstance(pointer_size, int) or pointer_size not in {4, 8}:
        raise ValueError(f"unsupported pointer_size: {pointer_size!r}")

    functions = {
        row["address"]: row
        for row in _read_jsonl(root / "functions.jsonl")
        if isinstance(row.get("address"), str)
    }
    absent = [target for target in normalized_targets if target not in functions]
    if absent:
        raise ValueError("target function(s) absent from functions.jsonl: " + ", ".join(absent))

    incoming: dict[str, list[dict[str, Any]]] = defaultdict(list)
    outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
    unresolved_indirect: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in _read_jsonl(root / "callgraph.jsonl"):
        source = row.get("from_function")
        target = row.get("to")
        if row.get("indirect") is True:
            if isinstance(source, str):
                unresolved_indirect[source].append(row)
            continue
        if row.get("indirect") is not False:
            continue
        if isinstance(source, str):
            outgoing[source].append(row)
        if isinstance(target, str):
            incoming[target].append(row)

    vtables = json.loads((root / "vtables.json").read_text(encoding="utf-8"))
    if not isinstance(vtables, dict) or vtables.get("format") != VTABLE_FORMAT:
        raise ValueError(f"vtables.json: expected {VTABLE_FORMAT}")
    if vtables.get("status") != "heuristic-candidates":
        raise ValueError("vtables.json: expected heuristic-candidates status")

    constructors = list(_read_jsonl(root / "constructors.jsonl"))
    static_tables = list(_read_jsonl(root / "static_tables.jsonl"))
    switches = list(_read_jsonl(root / "switches.jsonl"))

    strings_by_function: dict[str, set[str]] = defaultdict(set)
    for row in _read_jsonl(root / "strings_xrefs.jsonl"):
        value = row.get("value")
        if not isinstance(value, str):
            continue
        for function in row.get("functions") or []:
            if isinstance(function, str):
                strings_by_function[function].add(value)

    target_rows: list[dict[str, Any]] = []
    instruction_targets: set[str] = set()
    for target in normalized_targets:
        metadata = functions[target]
        direct_incoming = sorted(incoming.get(target, []), key=lambda row: _address_key(row.get("instruction")))
        direct_outgoing = sorted(outgoing.get(target, []), key=lambda row: _address_key(row.get("instruction")))
        memberships = _vtable_memberships(vtables, target)
        vtable_addresses = {
            row["vtable_address"] for row in memberships if isinstance(row.get("vtable_address"), str)
        }
        ctor_candidates = _constructor_candidates(constructors, vtable_addresses)
        raw_occurrences = _raw_pointer_occurrences(static_tables, target, pointer_size)
        local_switches = [row for row in switches if row.get("function") == target]

        candidate_functions: set[str] = set()
        for membership in memberships:
            candidate_functions.update(membership["function_xrefs"])
        for constructor in ctor_candidates:
            function = constructor.get("function")
            if isinstance(function, str):
                candidate_functions.add(function)
        candidate_functions.discard(target)
        instruction_targets.update(candidate_functions)
        instruction_targets.add(target)

        if memberships:
            state = "ambiguous"
            blocker = "target appears in heuristic vtable candidate(s); class/dispatch ownership still requires exact reference/dataflow proof"
        elif raw_occurrences:
            state = "ambiguous"
            blocker = "raw static-data pointer occurrence(s) exist without a proven dispatch/table semantic role"
        else:
            state = "unknown"
            blocker = "no vtable-candidate membership or raw static-table pointer occurrence in the current export"

        target_rows.append(
            {
                "address": target,
                "name": metadata.get("name"),
                "size": metadata.get("size"),
                "calling_convention": metadata.get("calling_convention"),
                "signature": metadata.get("signature"),
                "mnemonic_sha256": metadata.get("mnemonic_sha256"),
                "direct_incoming_calls": [_edge(row) for row in direct_incoming],
                "direct_incoming_count": len(direct_incoming),
                "direct_incoming_absent_verified": len(direct_incoming) == 0,
                "direct_outgoing_calls": [_edge(row) for row in direct_outgoing],
                "outgoing_unresolved_indirect_calls": [
                    _edge(row) for row in sorted(
                        unresolved_indirect.get(target, []),
                        key=lambda row: _address_key(row.get("instruction")),
                    )
                ],
                "computed_jump_candidates": local_switches,
                "vtable_memberships": memberships,
                "constructor_candidates": ctor_candidates,
                "raw_static_pointer_occurrences": raw_occurrences,
                "candidate_owner_functions": sorted(candidate_functions, key=_address_key),
                "target_strings": sorted(strings_by_function.get(target, set())),
                "evidence_state": state,
                "unresolved_blocker": blocker,
                "dispatch_owner_proven": False,
                "class_identity_proven": False,
            }
        )

    target_addresses = sorted(instruction_targets, key=_address_key)
    target_reason: list[dict[str, Any]] = []
    for address in target_addresses:
        reasons: set[str] = set()
        if address in normalized_targets:
            reasons.add("ownerless/indirect-dispatch target function")
        for row in target_rows:
            for membership in row["vtable_memberships"]:
                if address in membership["function_xrefs"]:
                    reasons.add(f"function xref to heuristic vtable candidate containing {row['address']}")
            for constructor in row["constructor_candidates"]:
                if address == constructor.get("function"):
                    reasons.add(f"constructor-candidate xref to heuristic vtable containing {row['address']}")
        target_reason.append(
            {
                "address": address,
                "name": (functions.get(address) or {}).get("name"),
                "reasons": sorted(reasons),
                "promoted": False,
            }
        )

    return {
        "format": FORMAT,
        "ghidra_export": str(root),
        "source": {
            "program": binary.get("program_name"),
            "executable_md5": binary.get("executable_md5"),
            "language_id": binary.get("language_id"),
            "image_base": binary.get("image_base"),
            "pointer_size": pointer_size,
        },
        "target_count": len(target_rows),
        "targets": target_rows,
        "instruction_export_target_count": len(target_reason),
        "instruction_export_targets": target_reason,
        "instruction_export_addresses": target_addresses,
        "scope": {
            "evidence_states": sorted(EVIDENCE_STATES),
            "direct_callgraph_is_observation": True,
            "static_table_bytes_are_observation": True,
            "vtable_candidates_are_heuristic": True,
            "constructor_candidates_are_heuristic": True,
            "raw_pointer_occurrence_is_dispatch_proof": False,
            "vtable_membership_is_class_identity_proof": False,
            "vtable_xref_is_constructor_proof": False,
            "missing_direct_call_is_root_proof": False,
            "ownership_or_virtual_dispatch_promoted": False,
            "note": (
                "Use the emitted candidate owner functions only as targeted instruction/reference "
                "work. Promotion requires exact code/data-reference and pointer-flow evidence."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument("target", nargs="+", help="function address(es), e.g. 0x0079b2d0")
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--targets-out", type=Path)
    args = parser.parse_args()

    report = build_indirect_dispatch_frontier(args.ghidra_export, args.target)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    if args.targets_out:
        args.targets_out.parent.mkdir(parents=True, exist_ok=True)
        args.targets_out.write_text(
            "".join(address + "\n" for address in report["instruction_export_addresses"]),
            encoding="utf-8",
        )

    print(f"format: {report['format']}")
    print(f"targets: {report['target_count']}")
    for row in report["targets"]:
        print(
            f"{row['address']}: direct-in={row['direct_incoming_count']} "
            f"vtables={len(row['vtable_memberships'])} "
            f"raw-pointers={len(row['raw_static_pointer_occurrences'])} "
            f"state={row['evidence_state']}"
        )
    if args.json_out:
        print(f"output: {args.json_out}")
    if args.targets_out:
        print(f"instruction targets: {args.targets_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
