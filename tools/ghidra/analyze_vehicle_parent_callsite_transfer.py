#!/usr/bin/env python3
"""Prove parent-callsite register transfer for pointer-origin entry boundaries.

For a child pointer-origin chain that terminates at a function-entry general
register, this analyzer finds the exact direct parent->child call instruction in
the raw Ghidra callgraph, requires matching CALL flow+p-code in a targeted
instruction export, and traces that same register immediately before the call.

On x86 CALL preserves general-purpose registers except ESP at callee entry. The
register-transfer boundary is therefore an architectural observation, but the
value's object/class/owner semantics remain unknown until independently proven.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.VehicleParentCallsiteTransfer/1"
POINTER_FORMAT = "SHIFT.VehiclePointerOriginFrontier/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"


def _load_pointer_helper():
    path = Path(__file__).with_name("analyze_vehicle_pointer_origin_frontier.py")
    spec = importlib.util.spec_from_file_location("vehicle_pointer_origin_helper", path)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise RuntimeError(f"cannot load helper: {path}")
    spec.loader.exec_module(module)
    return module


def _load_pointer_report(path: Path) -> dict[str, Any]:
    row = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(row, dict):
        raise ValueError(f"{path}: expected JSON object")
    if row.get("format") != POINTER_FORMAT:
        raise ValueError(f"{path}: expected {POINTER_FORMAT}, found {row.get('format')}")
    return row


def _edge(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "from_function": row.get("from_function"),
        "from_name": row.get("from_name"),
        "instruction": row.get("instruction"),
        "to": row.get("to"),
        "to_name": row.get("to_name"),
        "indirect": row.get("indirect"),
    }


def _load_callgraph(root: Path, helper):
    path = root / "callgraph.jsonl"
    functions_path = root / "functions.jsonl"
    if not path.is_file() or not functions_path.is_file():
        raise FileNotFoundError("Ghidra export requires callgraph.jsonl and functions.jsonl")
    functions = {
        row["address"]: row
        for row in helper.read_jsonl(functions_path)
        if isinstance(row.get("address"), str)
    }
    incoming: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in helper.read_jsonl(path):
        if row.get("indirect") is not False:
            continue
        src, dst = row.get("from_function"), row.get("to")
        if isinstance(src, str) and isinstance(dst, str):
            incoming[dst].append(row)
    return functions, incoming


def _eligible_entry_boundaries(pointer: dict[str, Any]) -> list[dict[str, Any]]:
    origins = pointer.get("origins")
    if not isinstance(origins, list):
        raise ValueError("pointer-origin report origins must be a list")
    result = []
    for row in origins:
        if not isinstance(row, dict):
            raise ValueError("pointer-origin report contains invalid origin row")
        child = row.get("caller")
        trace = row.get("base_origin_trace")
        if not isinstance(child, str) or not isinstance(trace, dict):
            continue
        source = trace.get("source")
        if not isinstance(source, dict) or source.get("kind") != "function-entry-register":
            continue
        register = source.get("register")
        parents = row.get("direct_incoming_callers")
        if not isinstance(register, str) or not isinstance(parents, list):
            raise ValueError(f"{child}: malformed entry-boundary provenance")
        if any(not isinstance(parent, str) for parent in parents):
            raise ValueError(f"{child}: invalid direct incoming caller list")
        result.append(
            {
                "child": child,
                "entry_register": register.upper(),
                "child_entry_state": trace.get("evidence_state", "unknown"),
                "expected_parents": sorted(set(parents)),
            }
        )
    return result


def _instruction_at(row: dict[str, Any], address: str) -> tuple[int, dict[str, Any]]:
    instructions = row.get("instructions")
    if not isinstance(instructions, list):
        raise ValueError(f"{row.get('function')}: instructions missing")
    matches = [
        (index, instruction)
        for index, instruction in enumerate(instructions)
        if isinstance(instruction, dict) and instruction.get("address") == address
    ]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one instruction at {address}; found {len(matches)}")
    return matches[0]


def analyze_vehicle_parent_callsite_transfer(
    ghidra_root: Path,
    instruction_export: Path,
    pointer_origin_frontier: Path,
) -> dict[str, Any]:
    helper = _load_pointer_helper()
    pointer = _load_pointer_report(pointer_origin_frontier)
    instruction_rows = helper.load_instructions(instruction_export)
    functions, incoming = _load_callgraph(ghidra_root, helper)
    boundaries = _eligible_entry_boundaries(pointer)
    if not boundaries:
        raise ValueError("pointer-origin report has no function-entry register boundary")

    transfers: list[dict[str, Any]] = []
    next_targets: dict[str, set[str]] = defaultdict(set)
    for boundary in boundaries:
        child = boundary["child"]
        register = boundary["entry_register"]
        expected_parents = boundary["expected_parents"]
        raw_edges = incoming.get(child, [])
        raw_parents = sorted(
            {edge.get("from_function") for edge in raw_edges if isinstance(edge.get("from_function"), str)}
        )
        if raw_parents != expected_parents:
            raise ValueError(
                f"{child}: raw callgraph parent set changed: expected {expected_parents}, got {raw_parents}"
            )
        if not raw_edges:
            raise ValueError(f"{child}: no direct incoming call edge in raw Ghidra export")

        for edge in sorted(raw_edges, key=lambda item: int(item.get("instruction"), 16)):
            parent = edge["from_function"]
            call_address = edge.get("instruction")
            if not isinstance(call_address, str):
                raise ValueError(f"{parent}->{child}: call instruction missing")
            if parent not in instruction_rows:
                raise ValueError(f"instruction export missing parent target {parent}")
            parent_row = instruction_rows[parent]
            call_index, call = _instruction_at(parent_row, call_address)
            mnemonic, operands, pcode, opcodes = helper.instruction_parts(call, parent)
            flows = call.get("flows")
            if not isinstance(flows, list) or child not in flows:
                raise ValueError(f"{parent}: {call_address} no longer flows to {child}")
            if "CALL" not in opcodes:
                raise ValueError(f"{parent}: {call_address} direct edge lacks CALL p-code")

            if register == "ESP":
                source_trace = {
                    "register": register,
                    "evidence_state": "ambiguous",
                    "status": "esp-mutated-by-call",
                    "chain": [],
                    "source": None,
                }
                transfer_state = "ambiguous"
                transfer_note = "x86 CALL pushes the return address and changes ESP before callee entry"
            elif register not in helper.REGISTERS:
                raise ValueError(f"{child}: unsupported entry register {register}")
            else:
                source_trace = helper.trace_origin(
                    parent_row["instructions"],
                    call_index,
                    register,
                    parent_row["function"].get("calling_convention"),
                )
                transfer_state = "verified"
                transfer_note = "x86 near CALL preserves this general-purpose register value into callee entry"

            terminal = source_trace.get("source") if isinstance(source_trace, dict) else None
            reached_parent_entry = (
                isinstance(terminal, dict)
                and terminal.get("kind") == "function-entry-register"
            )
            parent_incoming = incoming.get(parent, [])
            grandparent_sources = sorted(
                {
                    item.get("from_function")
                    for item in parent_incoming
                    if isinstance(item.get("from_function"), str)
                }
            )
            if reached_parent_entry:
                for grandparent in grandparent_sources:
                    next_targets[grandparent].add(
                        f"direct caller of {parent}; transferred {register} provenance reached parent entry"
                    )

            transfers.append(
                {
                    "parent": parent,
                    "parent_name": (functions.get(parent) or {}).get("name"),
                    "child": child,
                    "child_name": (functions.get(child) or {}).get("name"),
                    "raw_callgraph_edge": _edge(edge),
                    "call_instruction": call_address,
                    "call_instruction_text": call.get("text"),
                    "call_operands": operands,
                    "call_pcode": pcode,
                    "entry_register": register,
                    "register_transfer_state": transfer_state,
                    "register_transfer_note": transfer_note,
                    "parent_register_source_trace": source_trace,
                    "grandparent_callers": grandparent_sources,
                    "object_identity_proven": False,
                    "owner_identity_proven": False,
                }
            )

    counts = {
        state: sum(row["register_transfer_state"] == state for row in transfers)
        for state in ("verified", "ambiguous")
    }
    source_states = defaultdict(int)
    for row in transfers:
        source_states[(row.get("parent_register_source_trace") or {}).get("evidence_state", "unknown")] += 1

    target_rows = [
        {"address": address, "reasons": sorted(reasons), "promoted": False}
        for address, reasons in sorted(next_targets.items())
    ]
    return {
        "format": FORMAT,
        "ghidra_export": str(ghidra_root),
        "instruction_export": str(instruction_export),
        "pointer_origin_frontier": str(pointer_origin_frontier),
        "entry_boundary_count": len(boundaries),
        "transfer_count": len(transfers),
        "verified_register_transfer_count": counts["verified"],
        "ambiguous_register_transfer_count": counts["ambiguous"],
        "source_trace_state_counts": dict(sorted(source_states.items())),
        "transfers": transfers,
        "next_instruction_export_targets": target_rows,
        "next_instruction_export_addresses": [row["address"] for row in target_rows],
        "blockers": [
            {
                "id": "parent-register-source",
                "evidence_state": "unknown" if source_states.get("unknown") else ("ambiguous" if source_states.get("ambiguous") else "verified"),
                "required_evidence": "continue targeted register provenance where parent-side source trace is not closed",
            },
            {
                "id": "recursive-entry-boundary",
                "evidence_state": "unknown" if target_rows else "verified",
                "required_evidence": "inspect next parent callsites emitted by this report" if target_rows else "none",
            },
            {
                "id": "object-owner-semantics",
                "evidence_state": "unknown",
                "required_evidence": "join the completed value chain to allocation/vtable/lifecycle evidence for the same pointer identity",
            },
        ],
        "scope": {
            "raw_callgraph_parent_set_cross_checked": True,
            "exact_call_instruction_flow_required": True,
            "call_pcode_required": True,
            "same_gp_register_value_crosses_near_call": True,
            "esp_transfer_treated_as_unchanged": False,
            "register_transfer_is_object_identity_proof": False,
            "direct_parent_is_owner_proof": False,
            "thiscall_entry_hint_is_object_identity_proof": False,
            "owner_identity_proven": False,
            "class_identity_proven": False,
            "field_semantics_proven": False,
            "automatic_function_renaming_performed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("pointer_origin_frontier", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--targets-out", type=Path)
    parser.add_argument("--fail-on-ambiguous-transfer", action="store_true")
    args = parser.parse_args()
    report = analyze_vehicle_parent_callsite_transfer(
        args.ghidra_export,
        args.instruction_export,
        args.pointer_origin_frontier,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    if args.targets_out:
        args.targets_out.parent.mkdir(parents=True, exist_ok=True)
        args.targets_out.write_text(
            "".join(address + "\n" for address in report["next_instruction_export_addresses"]),
            encoding="utf-8",
        )
    print(f"format: {report['format']}")
    print(f"transfers: {report['transfer_count']}")
    print(f"verified register transfers: {report['verified_register_transfer_count']}")
    print(f"ambiguous register transfers: {report['ambiguous_register_transfer_count']}")
    print(f"next instruction targets: {len(report['next_instruction_export_addresses'])}")
    if args.json_out:
        print(f"output: {args.json_out}")
    if args.targets_out:
        print(f"targets: {args.targets_out}")
    if args.fail_on_ambiguous_transfer and report["ambiguous_register_transfer_count"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
