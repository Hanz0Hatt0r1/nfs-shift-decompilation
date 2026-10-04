#!/usr/bin/env python3
"""Classify the finite outer-Vehicle owner candidates from targeted instructions.

This pass consumes the four retail instruction rows selected by
``SHIFT.OuterVehicleTransformSinkReceiverProvenance/1``.  It does not infer a
class or frame from callgraph adjacency.  Instead it freezes only concrete
machine-level roles needed to choose the next static exports:

* ``FUN_007876e0`` is a call-free scalar/vector leaf and has no owner-forward edge;
* ``FUN_007afb60`` forwards its entry receiver to ``FUN_007aef50``;
* proven HDVehicle control ``FUN_007633b0`` reaches ``FUN_007ac2f0`` through the
  concrete ``+0x3fe8 -> dereference -> +0x340`` receiver chain;
* ``FUN_007ac2f0`` exposes one pointer field at ``+0x34`` (two adjacent virtual
  calls) and one embedded subobject at ``+0x534`` forwarded to ``FUN_007a4360``.

The output remains fail-closed for VHF owner identity and BODY0 bind-frame
semantics.  Its only positive handoff is a smaller static worklist.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.OuterVehicleOwnerCandidateRoles/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"

LEAF = "0x007876e0"
FORWARDER = "0x007afb60"
POST_TRANSFORM = "0x007ac2f0"
HDVEHICLE_CONTROL = "0x007633b0"
FORWARDED_HELPER = "0x007aef50"
HDVEHICLE_INIT = "0x0076df50"
CHASSIS_INIT = "0x007ac4d0"
SOLVER_SETUP = "0x007615c0"

REQUIRED = (LEAF, FORWARDER, POST_TRANSFORM, HDVEHICLE_CONTROL)
EXPECTED_NAMES = {
    LEAF: "FUN_007876e0",
    FORWARDER: "FUN_007afb60",
    POST_TRANSFORM: "FUN_007ac2f0",
    HDVEHICLE_CONTROL: "FUN_007633b0",
}
EXPECTED_COUNTS = {
    LEAF: 21,
    FORWARDER: 21,
    POST_TRANSFORM: 90,
    HDVEHICLE_CONTROL: 89,
}


def _address(value: Any) -> str:
    if isinstance(value, int):
        return f"0x{value:08x}"
    text = str(value or "").strip().lower()
    match = re.search(r"0x[0-9a-f]+", text)
    if match:
        return f"0x{int(match.group(0), 16):08x}"
    if re.fullmatch(r"[0-9a-f]+", text):
        return f"0x{int(text, 16):08x}"
    raise ValueError(f"not an address: {value!r}")


def _compact(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "")).lower()


def _load_rows(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_no}: expected JSON object")
        if value.get("format") != INSTRUCTION_FORMAT:
            raise ValueError(f"{path}:{line_no}: expected {INSTRUCTION_FORMAT}")
        if value.get("found") is not True:
            raise ValueError(f"{path}:{line_no}: target function was not found")
        requested = _address(value.get("requested"))
        function = value.get("function")
        if not isinstance(function, Mapping):
            raise ValueError(f"{path}:{line_no}: function metadata missing")
        if _address(function.get("address")) != requested:
            raise ValueError(f"{path}:{line_no}: requested/function address mismatch")
        instructions = value.get("instructions")
        if not isinstance(instructions, list):
            raise ValueError(f"{path}:{line_no}: instructions missing")
        if value.get("instruction_count") != len(instructions):
            raise ValueError(f"{path}:{line_no}: instruction_count mismatch")
        if requested in rows:
            raise ValueError(f"{path}:{line_no}: duplicate row {requested}")
        rows[requested] = value

    if set(rows) != set(REQUIRED):
        raise ValueError(
            f"instruction target drift: expected {list(REQUIRED)}, got {sorted(rows)}"
        )
    for address in REQUIRED:
        row = rows[address]
        function = row["function"]
        if function.get("name") != EXPECTED_NAMES[address]:
            raise ValueError(f"{address}: function name drift")
        if str(function.get("calling_convention") or "") != "__thiscall":
            raise ValueError(f"{address}: calling convention drift")
        if len(row["instructions"]) != EXPECTED_COUNTS[address]:
            raise ValueError(f"{address}: instruction count drift")
    return rows


def _instructions(row: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [x for x in row["instructions"] if isinstance(x, Mapping)]


def _by_address(row: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {_address(ins.get("address")): ins for ins in _instructions(row)}


def _direct_target(ins: Mapping[str, Any]) -> str | None:
    if str(ins.get("mnemonic") or "").upper() != "CALL":
        return None
    candidates = list(ins.get("flows") or []) + list(ins.get("operands") or [])
    for candidate in candidates:
        try:
            return _address(candidate)
        except ValueError:
            continue
    return None


def _call_inventory(row: Mapping[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for ins in _instructions(row):
        if str(ins.get("mnemonic") or "").upper() != "CALL":
            continue
        result.append(
            {
                "instruction": _address(ins.get("address")),
                "target": _direct_target(ins),
                "indirect": _direct_target(ins) is None,
            }
        )
    return result


def _require_text(ins: Mapping[str, Any], *parts: str) -> None:
    text = _compact(ins.get("text"))
    for part in parts:
        if _compact(part) not in text:
            raise ValueError(
                f"{_address(ins.get('address'))}: expected {part!r} in {ins.get('text')!r}"
            )


def _require_call(row: Mapping[str, Any], site: str, target: str) -> None:
    ins = _by_address(row).get(site)
    if ins is None:
        raise ValueError(f"missing required instruction {site}")
    if _direct_target(ins) != target:
        raise ValueError(f"{site}: expected direct call {target}")


def _analyze_leaf(row: Mapping[str, Any]) -> dict[str, Any]:
    calls = _call_inventory(row)
    if calls:
        raise ValueError(f"{LEAF}: expected call-free leaf")
    texts = [_compact(ins.get("text")) for ins in _instructions(row)]
    required_reads = ("[ecx+0x1b0]", "[ecx+0xb14]", "[ecx+0xb20]", "[ecx+0x8a4]", "[ecx+0x8b0]")
    for token in required_reads:
        if not any(token in text for text in texts):
            raise ValueError(f"{LEAF}: missing expected receiver scalar read {token}")
    return {
        "function": LEAF,
        "role": "call-free-physics-vector-leaf",
        "owner_forward_edge_present": False,
        "excluded_from_next_owner_join": True,
        "receiver_scalar_reads": list(required_reads),
    }


def _analyze_forwarder(row: Mapping[str, Any]) -> dict[str, Any]:
    calls = _call_inventory(row)
    if calls != [{"instruction": "0x007afb6c", "target": FORWARDED_HELPER, "indirect": False}]:
        raise ValueError(f"{FORWARDER}: direct-call inventory drift")
    before = [
        ins for ins in _instructions(row)
        if int(_address(ins.get("address")), 16) < int("0x007afb6c", 16)
    ]
    ecx_writes = [
        _address(ins.get("address")) for ins in before
        if str(ins.get("mnemonic") or "").upper() in {"MOV", "LEA", "ADD", "SUB", "XOR", "POP"}
        and (ins.get("operands") or [])
        and _compact((ins.get("operands") or [""])[0]) == "ecx"
    ]
    if ecx_writes:
        raise ValueError(f"{FORWARDER}: ECX modified before forwarded call: {ecx_writes}")
    return {
        "function": FORWARDER,
        "role": "entry-receiver-forwarder-plus-vector-accumulation",
        "entry_receiver_forwarded_unchanged": True,
        "forward_target": FORWARDED_HELPER,
        "forward_callsite": "0x007afb6c",
        "next_owner_join_target": FORWARDED_HELPER,
    }


def _analyze_control(row: Mapping[str, Any]) -> dict[str, Any]:
    _require_call(row, "0x007634df", POST_TRANSFORM)
    by = _by_address(row)
    _require_text(by["0x007633d1"], "mov", "esi", "ecx")
    _require_text(by["0x007634d1"], "mov", "edx", "[esi+0x3fe8]")
    _require_text(by["0x007634d7"], "mov", "ecx", "[edx]")
    _require_text(by["0x007634d9"], "add", "ecx", "0x340")
    return {
        "function": HDVEHICLE_CONTROL,
        "role": "proven-HDVehicle-control-bridge",
        "nested_callsite": "0x007634df",
        "nested_callee": POST_TRANSFORM,
        "nested_receiver_machine_chain": [
            "ESI = entry ECX",
            "EDX = [ESI+0x3fe8]",
            "ECX = [EDX]",
            "ECX += 0x340",
        ],
        "nested_receiver_expression": "*(*(HDVehicle_control+0x3fe8))+0x340",
        "nested_receiver_is_VHF_owner_proven": False,
        "nested_receiver_is_same_as_outer_setter_receiver_proven": False,
    }


def _analyze_post_transform(row: Mapping[str, Any]) -> dict[str, Any]:
    by = _by_address(row)
    _require_text(by["0x007ac2fc"], "mov", "esi", "ecx")
    _require_text(by["0x007ac302"], "mov", "edi", "[esi+0x34]")
    _require_call(row, "0x007ac35b", "0x007abbc0")
    _require_call(row, "0x007ac39f", "0x007aa440")
    _require_call(row, "0x007ac3cf", "0x007ab4e0")
    _require_text(by["0x007ac3d4"], "mov", "edx", "[edi]")
    _require_text(by["0x007ac3d6"], "mov", "edx", "[edx+0xe0]")
    _require_text(by["0x007ac3e4"], "mov", "eax", "[edi]")
    _require_text(by["0x007ac3e6"], "mov", "edx", "[eax+0xe4]")
    _require_text(by["0x007ac3f4"], "lea", "ecx", "[esi+0x534]")
    _require_call(row, "0x007ac3fa", "0x007a4360")
    indirect_sites = [x["instruction"] for x in _call_inventory(row) if x["indirect"]]
    if indirect_sites != ["0x007ac3e2", "0x007ac3f2"]:
        raise ValueError(f"{POST_TRANSFORM}: indirect-call inventory drift: {indirect_sites}")
    return {
        "function": POST_TRANSFORM,
        "role": "car-body-subsystem-owner-frontier",
        "entry_receiver_saved_in": "ESI",
        "interface_pointer_field": "+0x34",
        "interface_virtual_slots_called": ["+0xe0", "+0xe4"],
        "interface_virtual_callsites": ["0x007ac3e2", "0x007ac3f2"],
        "embedded_subobject_offset": "+0x534",
        "embedded_subobject_forward_target": "0x007a4360",
        "embedded_subobject_forward_callsite": "0x007ac3fa",
        "VHF_owner_identity_proven": False,
    }


def analyze(path: Path) -> dict[str, Any]:
    rows = _load_rows(path)
    leaf = _analyze_leaf(rows[LEAF])
    forwarder = _analyze_forwarder(rows[FORWARDER])
    control = _analyze_control(rows[HDVEHICLE_CONTROL])
    post = _analyze_post_transform(rows[POST_TRANSFORM])
    return {
        "format": FORMAT,
        "version": 1,
        "status": "owner-candidate-role-frontier-ready",
        "ready": True,
        "input": str(path),
        "roles": [leaf, forwarder, control, post],
        "static_context": {
            "HighDetailVehicle_Init": HDVEHICLE_INIT,
            "vehicle_solver_setup": SOLVER_SETUP,
            "car_body_CHASSIS_init": CHASSIS_INIT,
            "car_body_init_is_known_direct_callee_of_HighDetailVehicle_Init": True,
            "solver_setup_is_known_direct_callee_of_HighDetailVehicle_Init": True,
            "callgraph_adjacency_is_frame_identity": False,
        },
        "handoff": {
            "outer_vehicle_owner_candidates_narrowed": True,
            "leaf_007876e0_eliminated_from_owner_forward_search": True,
            "forwarder_007afb60_reduced_to_007aef50": True,
            "HDVehicle_nested_0x340_receiver_chain_observed": True,
            "post_transform_subowner_edges_observed": True,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "next_static_export": {
            "functions": [HDVEHICLE_INIT, CHASSIS_INIT, FORWARDED_HELPER],
            "purpose": [
                "prove ECX/owner relationship at HighDetailVehicle::Init calls to FUN_007615c0 and FUN_007ac4d0",
                "trace concrete car-body/CHASSIS initialization writes and owner fields",
                "close or retain the only surviving FUN_007afb60 forwarded receiver branch",
            ],
            "command_tail": f"{HDVEHICLE_INIT} {CHASSIS_INIT} {FORWARDED_HELPER}",
        },
        "blocker": {
            "id": "outer-vehicle-car-body-owner-to-VHF-vehicle-root-join-unproven",
            "required_evidence": (
                "join the concrete car-body/CHASSIS owner created or initialized from HighDetailVehicle::Init "
                "to the VHF vehicle-root/assembly frame, or prove that branch unrelated and continue only the surviving forwarder"
            ),
        },
        "scope": {
            "original_game_executed": False,
            "new_runtime_capture_required": False,
            "callgraph_adjacency_promoted_to_pointer_identity": False,
            "callgraph_adjacency_promoted_to_frame_identity": False,
            "plus_0x340_pattern_promoted_to_object_identity": False,
            "resource_VHF_matrix_promoted_to_physics_pose": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)
    report = analyze(args.instruction_export)
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.json_out is None:
        print(text, end="")
    else:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
