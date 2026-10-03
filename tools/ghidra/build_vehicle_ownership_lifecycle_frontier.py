#!/usr/bin/env python3
"""Join the upper vehicle-update chain with static ownership/lifecycle candidates.

This layer is intentionally fail-closed.  Direct callgraph edges are exact
execution observations.  Vtable and constructor exports remain heuristic
candidate sets, and string proximity is descriptive only.  No class, owner,
constructor, destructor, scheduler, or input role is promoted without later
instruction/reference and pointer-flow proof.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

FORMAT = "SHIFT.VehicleOwnershipLifecycleFrontier/1"
UPPER_CONTRACT_FORMAT = "SHIFT.VehicleUpperDirectContract/1"
INDIRECT_FRONTIER_FORMAT = "SHIFT.GhidraIndirectDispatchFrontier/1"
VTABLE_FORMAT = "SHIFT.GhidraVtableCandidates/1"

OUTER_UPDATE = "0x00770e80"
UPPER_CALLER = "0x007155e9"
ALTERNATE_CALLER = "0x0079b2d0"

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


def _load_json(path: Path, expected_format: str) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(report, dict):
        raise ValueError(f"{path}: expected JSON object")
    if report.get("format") != expected_format:
        raise ValueError(
            f"{path}: expected {expected_format}, found {report.get('format')}"
        )
    return report


def _addr(value: str) -> int:
    try:
        return int(value, 0)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid address: {value!r}") from exc


def _addr_key(value: Any) -> tuple[int, str]:
    if isinstance(value, str):
        try:
            return _addr(value), value
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


def _target_row(report: dict[str, Any], address: str) -> dict[str, Any]:
    matches = [row for row in report.get("targets") or [] if row.get("address") == address]
    if len(matches) != 1:
        raise ValueError(
            f"indirect dispatch frontier: expected one target row for {address}; found {len(matches)}"
        )
    return matches[0]


def _vtable_memberships(vtables: dict[str, Any], target: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for table in vtables.get("vtables") or []:
        if not isinstance(table, dict):
            raise ValueError("vtables.json: expected vtable object")
        slots = [
            slot
            for slot in table.get("slots") or []
            if isinstance(slot, dict) and slot.get("target") == target
        ]
        if not slots:
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
                    for slot in slots
                ],
                "function_xrefs": sorted(
                    {
                        value
                        for value in table.get("function_xrefs") or []
                        if isinstance(value, str)
                    },
                    key=_addr_key,
                ),
                "evidence_state": "ambiguous",
                "heuristic_vtable_candidate": True,
                "virtual_dispatch_proven": False,
                "class_identity_proven": False,
            }
        )
    result.sort(key=lambda row: _addr_key(row.get("vtable_address")))
    return result


def _constructor_candidates(
    rows: list[dict[str, Any]], vtable_addresses: set[str]
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in rows:
        addresses = {
            value for value in row.get("vtables") or [] if isinstance(value, str)
        }
        matching = sorted(addresses & vtable_addresses, key=_addr_key)
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
                "destructor_role_proven": False,
                "owner_role_proven": False,
            }
        )
    result.sort(key=lambda row: _addr_key(row.get("function")))
    return result


def build_vehicle_ownership_lifecycle_frontier(
    ghidra_root: Path,
    upper_contract_path: Path,
    indirect_frontier_path: Path,
) -> dict[str, Any]:
    upper = _load_json(upper_contract_path, UPPER_CONTRACT_FORMAT)
    indirect_report = _load_json(indirect_frontier_path, INDIRECT_FRONTIER_FORMAT)

    anchors = upper.get("anchors") or {}
    closure = upper.get("closure") or {}
    if anchors.get("outer_update") != OUTER_UPDATE:
        raise ValueError("upper contract outer-update anchor changed")
    if anchors.get("upper_caller") != UPPER_CALLER:
        raise ValueError("upper contract upper-caller anchor changed")
    if anchors.get("alternate_caller") != ALTERNATE_CALLER:
        raise ValueError("upper contract alternate-caller anchor changed")
    if closure.get("upper_direct_path") != "verified":
        raise ValueError("upper direct path is not verified")
    path = closure.get("path") or []
    if not path or path[0] != UPPER_CALLER or path[-1] != OUTER_UPDATE:
        raise ValueError("upper direct path endpoints changed")

    alternate_frontier = _target_row(indirect_report, ALTERNATE_CALLER)
    if alternate_frontier.get("direct_incoming_count") != 0:
        raise ValueError("alternate caller acquired a direct incoming edge")
    if alternate_frontier.get("direct_incoming_absent_verified") is not True:
        raise ValueError("alternate caller direct-incoming absence is not verified")

    required = (
        "binary.json",
        "functions.jsonl",
        "callgraph.jsonl",
        "vtables.json",
        "constructors.jsonl",
        "strings_xrefs.jsonl",
    )
    missing = [name for name in required if not (ghidra_root / name).is_file()]
    if missing:
        raise FileNotFoundError("missing required Ghidra files: " + ", ".join(missing))

    binary = json.loads((ghidra_root / "binary.json").read_text(encoding="utf-8"))
    if not isinstance(binary, dict):
        raise ValueError("binary.json must contain an object")

    functions = {
        row["address"]: row
        for row in _read_jsonl(ghidra_root / "functions.jsonl")
        if isinstance(row.get("address"), str)
    }
    for address in (UPPER_CALLER, ALTERNATE_CALLER, OUTER_UPDATE):
        if address not in functions:
            raise ValueError(f"required function absent from functions.jsonl: {address}")

    incoming: dict[str, list[dict[str, Any]]] = defaultdict(list)
    outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
    unresolved_indirect: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in _read_jsonl(ghidra_root / "callgraph.jsonl"):
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

    alternate_direct = incoming.get(ALTERNATE_CALLER, [])
    if alternate_direct:
        raise ValueError(
            "Ghidra callgraph disagrees with indirect frontier: alternate caller has direct incoming edge(s)"
        )

    upper_incoming = sorted(
        incoming.get(UPPER_CALLER, []),
        key=lambda row: (_addr_key(row.get("from_function")), _addr_key(row.get("instruction"))),
    )
    if not upper_incoming:
        raise ValueError(
            "no direct caller of FUN_007155e9 in current callgraph; ownership frontier cannot advance"
        )

    upper_caller_addresses = sorted(
        {
            row["from_function"]
            for row in upper_incoming
            if isinstance(row.get("from_function"), str)
        },
        key=_addr_key,
    )
    missing_callers = [address for address in upper_caller_addresses if address not in functions]
    if missing_callers:
        raise ValueError(
            "upper direct caller(s) missing from functions.jsonl: " + ", ".join(missing_callers)
        )

    vtables = json.loads((ghidra_root / "vtables.json").read_text(encoding="utf-8"))
    if not isinstance(vtables, dict) or vtables.get("format") != VTABLE_FORMAT:
        raise ValueError(f"vtables.json: expected {VTABLE_FORMAT}")
    if vtables.get("status") != "heuristic-candidates":
        raise ValueError("vtables.json: expected heuristic-candidates status")

    constructors = list(_read_jsonl(ghidra_root / "constructors.jsonl"))

    strings_by_function: dict[str, set[str]] = defaultdict(set)
    for row in _read_jsonl(ghidra_root / "strings_xrefs.jsonl"):
        value = row.get("value")
        if not isinstance(value, str):
            continue
        for function in row.get("functions") or []:
            if isinstance(function, str):
                strings_by_function[function].add(value)

    upper_memberships = _vtable_memberships(vtables, UPPER_CALLER)
    alternate_memberships = _vtable_memberships(vtables, ALTERNATE_CALLER)
    relevant_vtables = {
        row["vtable_address"]
        for row in upper_memberships + alternate_memberships
        if isinstance(row.get("vtable_address"), str)
    }
    ctor_candidates = _constructor_candidates(constructors, relevant_vtables)

    heuristic_xref_functions: set[str] = set()
    for row in upper_memberships + alternate_memberships:
        heuristic_xref_functions.update(row["function_xrefs"])
    constructor_functions = {
        row["function"]
        for row in ctor_candidates
        if isinstance(row.get("function"), str)
    }

    caller_rows: list[dict[str, Any]] = []
    for address in upper_caller_addresses:
        metadata = functions[address]
        calls_to_upper = [
            _edge(row) for row in upper_incoming if row.get("from_function") == address
        ]
        direct_in = sorted(
            incoming.get(address, []),
            key=lambda row: (_addr_key(row.get("from_function")), _addr_key(row.get("instruction"))),
        )
        direct_out = sorted(outgoing.get(address, []), key=lambda row: _addr_key(row.get("instruction")))
        overlaps = []
        if address in heuristic_xref_functions:
            overlaps.append("function-xref-to-relevant-heuristic-vtable")
        if address in constructor_functions:
            overlaps.append("constructor-candidate-for-relevant-heuristic-vtable")
        caller_rows.append(
            {
                "address": address,
                "name": metadata.get("name"),
                "size": metadata.get("size"),
                "calling_convention": metadata.get("calling_convention"),
                "signature": metadata.get("signature"),
                "mnemonic_sha256": metadata.get("mnemonic_sha256"),
                "direct_calls_to_upper": calls_to_upper,
                "direct_call_count_to_upper": len(calls_to_upper),
                "direct_incoming_calls": [_edge(row) for row in direct_in],
                "direct_incoming_count": len(direct_in),
                "direct_outgoing_calls": [_edge(row) for row in direct_out],
                "unresolved_indirect_calls": [
                    _edge(row)
                    for row in sorted(
                        unresolved_indirect.get(address, []),
                        key=lambda row: _addr_key(row.get("instruction")),
                    )
                ],
                "strings": sorted(strings_by_function.get(address, set())),
                "heuristic_lifecycle_overlap": overlaps,
                "execution_edge_to_upper_state": "verified",
                "owner_role_state": "unknown",
                "lifecycle_role_state": "ambiguous" if overlaps else "unknown",
                "owner_role_proven": False,
                "constructor_role_proven": False,
                "destructor_role_proven": False,
                "scheduler_role_proven": False,
            }
        )

    lifecycle_candidates = sorted(
        heuristic_xref_functions | constructor_functions,
        key=_addr_key,
    )

    target_reasons: dict[str, set[str]] = defaultdict(set)
    target_reasons[UPPER_CALLER].add("upper verified vehicle-update frontier function")
    target_reasons[ALTERNATE_CALLER].add("ownerless alternate outer-update caller")
    for address in upper_caller_addresses:
        target_reasons[address].add("exact direct caller of FUN_007155e9")
    for address in lifecycle_candidates:
        target_reasons[address].add("heuristic lifecycle/vtable candidate requiring exact pointer-flow audit")
    for address in alternate_frontier.get("candidate_owner_functions") or []:
        if isinstance(address, str):
            target_reasons[address].add("candidate owner from indirect-dispatch frontier")

    instruction_targets = [
        {
            "address": address,
            "name": (functions.get(address) or {}).get("name"),
            "reasons": sorted(reasons),
            "promoted": False,
        }
        for address, reasons in sorted(target_reasons.items(), key=lambda item: _addr_key(item[0]))
    ]

    return {
        "format": FORMAT,
        "source": {
            "ghidra_export": str(ghidra_root),
            "program": binary.get("program_name"),
            "executable_md5": binary.get("executable_md5"),
            "language_id": binary.get("language_id"),
            "image_base": binary.get("image_base"),
            "pointer_size": binary.get("pointer_size"),
            "upper_contract": str(upper_contract_path),
            "indirect_frontier": str(indirect_frontier_path),
        },
        "anchors": {
            "outer_update": OUTER_UPDATE,
            "upper_caller": UPPER_CALLER,
            "alternate_caller": ALTERNATE_CALLER,
        },
        "upper_direct_callers": caller_rows,
        "upper_direct_caller_count": len(caller_rows),
        "upper_exact_incoming_edges": [_edge(row) for row in upper_incoming],
        "alternate_direct_incoming_absent_verified": True,
        "upper_vtable_memberships": upper_memberships,
        "alternate_vtable_memberships": alternate_memberships,
        "lifecycle_candidates": ctor_candidates,
        "instruction_export_targets": instruction_targets,
        "instruction_export_addresses": [row["address"] for row in instruction_targets],
        "blockers": [
            {
                "id": "upper-owner-pointer-flow",
                "evidence_state": "unknown",
                "required_evidence": "instruction/p-code proof of the receiver/object flow from direct upper caller(s) into FUN_007155e9",
            },
            {
                "id": "lifecycle-role-proof",
                "evidence_state": "ambiguous" if lifecycle_candidates else "unknown",
                "required_evidence": "exact vtable-store/destructor/pointer provenance; heuristic constructor/vtable membership is insufficient",
            },
            {
                "id": "alternate-dispatch-owner",
                "evidence_state": alternate_frontier.get("evidence_state", "unknown"),
                "required_evidence": "exact code/data-reference and pointer-flow proof for the FUN_0079b2d0 dispatch owner",
            },
            {
                "id": "input-control-provenance",
                "evidence_state": "unknown",
                "required_evidence": "static dataflow from a proven input/control source into the update chain",
            },
            {
                "id": "rendered-frame-cadence",
                "evidence_state": "unknown",
                "required_evidence": "static scheduler path proving update invocation cadence",
            },
        ],
        "scope": {
            "evidence_states": sorted(EVIDENCE_STATES),
            "direct_callgraph_edges_are_execution_observations": True,
            "direct_caller_is_owner_proof": False,
            "vtable_candidates_are_heuristic": True,
            "constructor_candidates_are_heuristic": True,
            "vtable_xref_is_constructor_proof": False,
            "constructor_candidate_is_owner_proof": False,
            "string_proximity_is_semantic_proof": False,
            "automatic_function_renaming_performed": False,
            "unknown_offsets_renamed": False,
            "physical_units_inferred": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument("upper_contract", type=Path)
    parser.add_argument("indirect_frontier", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--targets-out", type=Path)
    args = parser.parse_args()

    report = build_vehicle_ownership_lifecycle_frontier(
        args.ghidra_export,
        args.upper_contract,
        args.indirect_frontier,
    )
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
    print(f"upper direct callers: {report['upper_direct_caller_count']}")
    print(f"lifecycle candidates: {len(report['lifecycle_candidates'])}")
    print(f"instruction targets: {len(report['instruction_export_addresses'])}")
    if args.json_out:
        print(f"output: {args.json_out}")
    if args.targets_out:
        print(f"targets: {args.targets_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
