#!/usr/bin/env python3
"""Narrow the car-body +0x534 visual-object frontier toward the retail VHF frame.

This pass consumes the already-proven outer Vehicle -> car-body/CHASSIS owner
join, the saved Ghidra evidence database, and a targeted
SHIFT.GhidraFunctionInstructions/2 export for FUN_007a3d60 and FUN_00d5bf10.

It proves only a finite physical/data-flow frontier:

* FUN_007ac4d0 dispatches the car-body +0x534 child into FUN_007a3d60;
* FUN_007a3d60 is the vehicle visual/LOD lane anchored by the four retail
  _WHEEL_*_LODA strings;
* the exact resolver callsite 0x007a402a targets thunk_FUN_00d5bf10;
* all-path register provenance immediately before that call is recorded;
* direct fallthrough uses/stores of the call result register EAX are inventoried;
* FUN_00d5bf10's register-relative memory accesses are inventoried with p-code.

The analyzer intentionally does not name the resolver result as a VHF node,
does not infer a vehicle-root frame, and does not promote lexical stack pushes
or EAX consumers to semantic ABI without an independent join.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import deque
from pathlib import Path
from typing import Any, Iterable, Mapping

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import analyze_fun_00765470_body_owner_receiver as _register_engine
import analyze_register_relative_accesses as _accesses

FORMAT = "SHIFT.OuterVehicleVisualHierarchyFrontier/1"
UPSTREAM_FORMAT = "SHIFT.OuterVehicleChassisOwnerJoin/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"
DB_FORMAT = "SHIFT.GhidraEvidenceDatabase/1"
PROGRAM = "SHIFT.exe"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"

CHASSIS_INIT = "0x007ac4d0"
VISUAL_SETUP = "0x007a3d60"
RESOLVER_THUNK = "0x0047bdf0"
RESOLVER = "0x00d5bf10"
RESOLVER_CALLSITE = "0x007a402a"

FINGERPRINTS = {
    VISUAL_SETUP: "689d88dc93c57813b682d5b8b7147f99032457307d3b2dab1d21adb1c61e8f45",
    RESOLVER_THUNK: "68de32f85d6daf246c1b8163a07400b82021cdc7a881415976e223547625a126",
    RESOLVER: "742effa774156dda6f6b2d27b46a9e37ca4208c5625722c8cda3ee87dad4199c",
}

WHEEL_STRING_WITNESSES = {
    "0x00b0c3e4": ("_WHEEL_RR_LODA", "0x007a3ef4"),
    "0x00b0c3f4": ("_WHEEL_RL_LODA", "0x007a3eea"),
    "0x00b0c404": ("_WHEEL_FR_LODA", "0x007a3ee0"),
    "0x00b0c414": ("_WHEEL_FL_LODA", "0x007a3ed6"),
}

_TRACKED = tuple(_register_engine._TRACKED)
_GENERAL_REGISTERS = {"EAX", "EBX", "ECX", "EDX", "ESI", "EDI", "EBP", "ESP"}
_MEMORY_TOKEN = re.compile(r"\[[^\]]+\]", re.IGNORECASE)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, 1):
            text = raw.strip()
            if not text:
                continue
            try:
                value = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_no}: expected object")
            rows.append(value)
    return rows


def _address(value: Any, *, field: str = "address") -> str:
    try:
        return _register_engine._normalize_address(value)
    except ValueError as exc:
        raise ValueError(f"{field}: {exc}") from exc


def _call_target(instruction: Mapping[str, Any]) -> str | None:
    if str(instruction.get("mnemonic") or "").upper() != "CALL":
        return None
    for value in list(instruction.get("flows") or []) + list(instruction.get("operands") or []):
        if not isinstance(value, str):
            continue
        try:
            return _address(value, field="call target")
        except ValueError:
            continue
    return None


def _load_upstream(path: Path) -> dict[str, Any]:
    upstream = _read_json(path)
    if upstream.get("format") != UPSTREAM_FORMAT or upstream.get("ready") is not True:
        raise ValueError(f"{path}: expected ready {UPSTREAM_FORMAT}")
    chassis = upstream.get("chassis_init")
    if not isinstance(chassis, dict) or _address(chassis.get("function")) != CHASSIS_INIT:
        raise ValueError("upstream chassis initializer anchor drift")
    edges = chassis.get("embedded_owner_edges")
    if not isinstance(edges, list):
        raise ValueError("upstream embedded_owner_edges missing")
    matching = [
        row for row in edges
        if isinstance(row, dict)
        and str(row.get("offset")) == "+0x534"
        and VISUAL_SETUP in [str(x).lower() for x in row.get("callees") or []]
    ]
    if len(matching) != 1:
        raise ValueError("upstream +0x534 -> FUN_007a3d60 edge missing or ambiguous")
    handoff = upstream.get("handoff")
    if not isinstance(handoff, dict) or handoff.get(
        "HDVehicle_car_body_CHASSIS_child_domain_joined_to_runtime_post_transform_domain"
    ) is not True:
        raise ValueError("upstream car-body/CHASSIS domain join is not ready")
    if handoff.get("outer_vehicle_root_to_VHF_vehicle_root_ready") is not False:
        raise ValueError("upstream unexpectedly preclaims outer Vehicle -> VHF frame")
    return upstream


def _load_db(root: Path) -> dict[str, Any]:
    binary = _read_json(root / "binary.json")
    if (
        binary.get("format") != DB_FORMAT
        or binary.get("program_name") != PROGRAM
        or binary.get("executable_md5") != PE_MD5
    ):
        raise ValueError("retail Ghidra database identity drift")

    wanted = set(FINGERPRINTS)
    functions: dict[str, dict[str, Any]] = {}
    for row in _read_jsonl(root / "functions.jsonl"):
        raw = row.get("address")
        if not isinstance(raw, str):
            continue
        address = raw.lower()
        if address in wanted:
            functions[address] = row
    missing = wanted - set(functions)
    if missing:
        raise ValueError(f"missing function rows: {sorted(missing)}")
    for address, fingerprint in FINGERPRINTS.items():
        if functions[address].get("mnemonic_sha256") != fingerprint:
            raise ValueError(f"{address}: mnemonic fingerprint drift")
    if functions[VISUAL_SETUP].get("thunk") is True or functions[RESOLVER].get("thunk") is True:
        raise ValueError("visual setup/resolver must be concrete functions")
    if functions[RESOLVER_THUNK].get("thunk") is not True:
        raise ValueError("resolver thunk identity drift")

    strings: dict[str, dict[str, Any]] = {}
    for row in _read_jsonl(root / "strings_xrefs.jsonl"):
        raw = row.get("address")
        if isinstance(raw, str) and raw.lower() in WHEEL_STRING_WITNESSES:
            strings[raw.lower()] = row
    for address, (value, xref) in WHEEL_STRING_WITNESSES.items():
        row = strings.get(address)
        if (
            row is None
            or row.get("value") != value
            or xref not in (row.get("xrefs") or [])
            or VISUAL_SETUP not in [str(x).lower() for x in row.get("functions") or []]
        ):
            raise ValueError(f"{address}: wheel LODA witness drift")

    visual_call_edges = []
    chassis_edges = []
    for row in _read_jsonl(root / "callgraph.jsonl"):
        source = str(row.get("from_function") or "").lower()
        target = str(row.get("to") or "").lower()
        instruction = str(row.get("instruction") or "").lower()
        if source == VISUAL_SETUP and instruction == RESOLVER_CALLSITE:
            visual_call_edges.append(row)
        if source == CHASSIS_INIT and target == VISUAL_SETUP:
            chassis_edges.append(row)
    if len(visual_call_edges) != 1 or str(visual_call_edges[0].get("to") or "").lower() != RESOLVER_THUNK:
        raise ValueError("exact FUN_007a3d60 resolver call edge drift")
    if len(chassis_edges) != 1:
        raise ValueError("expected exactly one direct chassis-init -> visual-setup edge")

    return {
        "functions": functions,
        "strings": strings,
        "visual_call_edge": visual_call_edges[0],
        "chassis_edge": chassis_edges[0],
    }


def _load_instruction_export(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in _read_jsonl(path):
        if row.get("format") != INSTRUCTION_FORMAT or row.get("program") != PROGRAM:
            raise ValueError(f"{path}: expected {INSTRUCTION_FORMAT} for {PROGRAM}")
        if row.get("found") is not True:
            raise ValueError(f"{path}: unresolved target {row.get('requested')}")
        function = row.get("function")
        instructions = row.get("instructions")
        if not isinstance(function, dict) or not isinstance(instructions, list) or not instructions:
            raise ValueError(f"{path}: malformed instruction row")
        address = _address(function.get("address"), field="function.address")
        if address in rows:
            raise ValueError(f"{path}: duplicate instruction row {address}")
        if row.get("instruction_count") != len(instructions):
            raise ValueError(f"{address}: instruction count mismatch")
        rows[address] = row
    required = {VISUAL_SETUP, RESOLVER}
    if set(rows) != required:
        raise ValueError(f"{path}: target set must be exactly {sorted(required)}")
    return rows


def _incoming_states(instructions: list[dict[str, Any]]) -> dict[str, Any]:
    by_address = {
        _address(row.get("address"), field="instruction.address"): row for row in instructions
    }
    entry = _address(instructions[0].get("address"), field="entry")
    incoming: dict[str, Any] = {entry: _register_engine._initial_state()}
    queue: deque[str] = deque((entry,))
    iterations = 0
    max_iterations = max(64, len(instructions) * 64)
    while queue:
        current = queue.popleft()
        iterations += 1
        if iterations > max_iterations:
            raise ValueError(f"{entry}: register provenance did not converge")
        after = _register_engine._transfer(by_address[current], incoming[current])
        for successor in _register_engine._successors(by_address[current], set(by_address)):
            merged, changed = _register_engine._merge(incoming.get(successor), after)
            if changed:
                incoming[successor] = merged
                queue.append(successor)
    return incoming


def _pre_call_registers(row: dict[str, Any]) -> dict[str, Any]:
    instructions = row["instructions"]
    by_address = {_address(item.get("address")): item for item in instructions}
    call = by_address.get(RESOLVER_CALLSITE)
    if call is None or _call_target(call) != RESOLVER_THUNK:
        raise ValueError("targeted export missing exact resolver CALL 0x007a402a -> 0x0047bdf0")
    incoming = _incoming_states(instructions)
    state = incoming.get(RESOLVER_CALLSITE)
    if state is None:
        raise ValueError("resolver callsite is unreachable")
    result: dict[str, Any] = {}
    for register in _TRACKED:
        origins = _register_engine._sorted_origins(state[register])
        result[register] = {
            "origins": origins,
            "exact_single_origin": len(origins) == 1,
            "contains_entry_origin": any(value.startswith("entry:") for value in origins),
            "contains_memory_origin": any(value.startswith("memory:") for value in origins),
            "contains_unknown_or_derived": any(
                value.startswith(("unknown:", "ambiguous:", "derived:", "value:"))
                for value in origins
            ),
        }
    return result


def _fallthrough_window(row: dict[str, Any], limit: int = 16) -> list[dict[str, Any]]:
    instructions = row["instructions"]
    by_address = {_address(item.get("address")): item for item in instructions}
    call = by_address[RESOLVER_CALLSITE]
    current = call.get("fallthrough")
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    while current and len(result) < limit:
        address = _address(current, field="fallthrough")
        if address in seen or address not in by_address:
            break
        seen.add(address)
        instruction = by_address[address]
        mnemonic = str(instruction.get("mnemonic") or "").upper()
        operands = [str(value) for value in instruction.get("operands") or []]
        eax_read = any("EAX" in operand.upper() for operand in operands[1:])
        eax_destination = bool(operands) and operands[0].strip().upper() == "EAX"
        memory_store_from_eax = (
            mnemonic in {"MOV", "MOVSS", "MOVSD"}
            and len(operands) >= 2
            and _MEMORY_TOKEN.search(operands[0]) is not None
            and "EAX" in operands[1].upper()
        )
        result.append(
            {
                "address": address,
                "mnemonic": mnemonic,
                "text": instruction.get("text"),
                "operands": operands,
                "pcode": instruction.get("pcode") or [],
                "reads_EAX_lexically": eax_read,
                "overwrites_EAX_lexically": eax_destination,
                "direct_memory_store_from_EAX_lexically": memory_store_from_eax,
            }
        )
        flow_type = str(instruction.get("flow_type") or "").upper()
        if mnemonic in {"RET", "JMP", "CALL"} or "BRANCH" in flow_type or eax_destination:
            break
        current = instruction.get("fallthrough")
    return result


def _resolver_access_summary(export_path: Path) -> dict[str, Any]:
    report = _accesses.analyze_register_relative_accesses(export_path)
    accesses = [row for row in report.get("accesses") or [] if str(row.get("function")).lower() == RESOLVER]
    by_register: dict[str, list[dict[str, Any]]] = {}
    for row in accesses:
        base = str(row.get("base_register") or "").upper()
        if base not in _GENERAL_REGISTERS:
            continue
        by_register.setdefault(base, []).append(
            {
                "instruction": row.get("instruction"),
                "displacement_hex": row.get("displacement_hex"),
                "access": row.get("access"),
                "operand": row.get("operand"),
            }
        )
    return {
        "syntactic_register_relative_access_count": len(accesses),
        "by_base_register": by_register,
        "semantic_receiver_identity_proven": False,
        "semantic_argument_identity_proven": False,
    }


def analyze(ghidra_export: Path, upstream_path: Path, instruction_export: Path) -> dict[str, Any]:
    _load_upstream(upstream_path)
    db = _load_db(ghidra_export)
    rows = _load_instruction_export(instruction_export)
    registers = _pre_call_registers(rows[VISUAL_SETUP])
    fallthrough = _fallthrough_window(rows[VISUAL_SETUP])
    resolver_summary = _resolver_access_summary(instruction_export)

    eax_consumers = [row for row in fallthrough if row["reads_EAX_lexically"]]
    direct_eax_stores = [row for row in fallthrough if row["direct_memory_store_from_EAX_lexically"]]

    blockers = [
        {
            "id": "resolver-stack-argument-provenance-unmodeled",
            "required_evidence": "recover exact stack value at 0x007a402a if the resolver consumes a stack argument",
        },
        {
            "id": "resolver-result-semantic-identity-unproven",
            "required_evidence": "join the physical FUN_00d5bf10 result/consumer to a source-backed RenderHierarchy/VHF runtime object class",
        },
        {
            "id": "outer-vehicle-root-to-VHF-vehicle-root-frame-relation-unproven",
            "required_evidence": "prove the affine/pointer relation from the car-body visual owner to the canonical BMW VHF assembly/root frame",
        },
    ]

    return {
        "format": FORMAT,
        "version": 1,
        "status": "visual-hierarchy-frontier-ready",
        "ready": True,
        "retail": {"program": PROGRAM, "md5": PE_MD5},
        "anchors": {
            "chassis_initializer": CHASSIS_INIT,
            "visual_setup": VISUAL_SETUP,
            "visual_setup_receiver_from_upstream": "car-body/CHASSIS +0x534",
            "wheel_LODA_strings": [
                {"address": address, "value": value, "xref": xref}
                for address, (value, xref) in WHEEL_STRING_WITNESSES.items()
            ],
            "chassis_to_visual_setup_callsite": db["chassis_edge"].get("instruction"),
        },
        "resolver_frontier": {
            "callsite": RESOLVER_CALLSITE,
            "thunk": RESOLVER_THUNK,
            "concrete_function": RESOLVER,
            "registers_before_call": registers,
            "fallthrough_window": fallthrough,
            "lexical_EAX_consumer_count": len(eax_consumers),
            "lexical_direct_memory_store_from_EAX_count": len(direct_eax_stores),
            "lexical_EAX_consumers_are_semantic_proof": False,
            "resolver_register_relative_accesses": resolver_summary,
        },
        "handoff": {
            "outer_vehicle_car_body_plus_0x534_to_visual_setup_ready": True,
            "vehicle_visual_LOD_domain_ready": True,
            "resolver_exact_machine_callsite_ready": True,
            "resolver_pre_call_register_provenance_ready": True,
            "resolver_fallthrough_result_consumer_frontier_ready": True,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "blockers": blockers,
        "scope": {
            "original_game_executed": False,
            "new_runtime_capture_required": False,
            "Ghidra_decompiler_parameter_names_used_as_semantic_ABI": False,
            "wheel_LODA_strings_promoted_to_body_root_identity": False,
            "resolver_result_promoted_to_VHF_node_identity": False,
            "lexical_stack_window_promoted_to_stack_value_proof": False,
            "lexical_EAX_consumer_promoted_to_persistent_owner_store": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument("upstream_chassis_join", type=Path)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)
    report = analyze(args.ghidra_export, args.upstream_chassis_join, args.instruction_export)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
