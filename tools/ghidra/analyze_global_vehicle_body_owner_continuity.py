#!/usr/bin/env python3
"""Prove global vehicle -> persistent BODY-array owner receiver continuity.

The current static frontier already proves that the normal outer-update receiver
is the global vehicle component base at 0x00c13700.  The remaining BODY-pose
identity edge is narrower:

    DAT_00c13700 / FUN_00770e80
      -> FUN_00765470 receiver
      -> FUN_007b2270 BODY-array owner

This analyzer keeps that proof fail-closed.  It requires the pinned retail
SHIFT.exe.c source, the existing global-vehicle/chassis/BODY contracts, the raw
Ghidra callgraph, and a targeted SHIFT.GhidraFunctionInstructions/2 export for
FUN_00765470.  Source must forward ``this`` across both calls.  At the exact
0x0076582a machine CALL, ECX must trace back to FUN_00765470 entry ECX using
only register copies/zero-displacement LEA plus standard x86 callee-saved
preservation across direct calls with supported calling conventions.

No class identity, update-child equality, renderer transform convention, or
runtime cadence is inferred here.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
from pathlib import Path
from typing import Any, Iterable

FORMAT = "SHIFT.GlobalVehicleBodyOwnerContinuity/1"
GLOBAL_FORMAT = "SHIFT.GlobalVehicleComponentBaseIdentity/1"
CHASSIS_FORMAT = "SHIFT.BMWChassisBodyIdentityFrontier/1"
BODY_FORMAT = "SHIFT.BodyFrameIntegrationStatic/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"

SOURCE_SHA256 = "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"
GLOBAL_VEHICLE_ADDRESS = 0x00C13700
OUTER_UPDATE = "0x00770e80"
HALF_STEP = "0x00765470"
BODY_ARRAY_LOOP = "0x007b2270"
HALF_STEP_BODY_CALL = "0x0076582a"
OUTER_HALF_STEP_CALLS = ("0x00770fac", "0x00770fdc")
SUPPORTED_ABI = {"__thiscall", "__cdecl", "__stdcall", "__fastcall"}
CALLEE_SAVED = {"EBX", "ESI", "EDI", "EBP"}
CALLER_SAVED = {"EAX", "ECX", "EDX"}
NONWRITING_FIRST_OPERAND = {"CMP", "TEST", "PUSH", "BT"}
CONTROL_PCODE = {"BRANCH", "CBRANCH", "BRANCHIND", "RETURN"}


def _pointer_helper():
    path = Path(__file__).with_name("analyze_vehicle_pointer_origin_frontier.py")
    spec = importlib.util.spec_from_file_location("body_owner_pointer_helper", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load helper: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load(path: Path, expected: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("format") != expected:
        raise ValueError(f"{path}: expected {expected}")
    return value


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _int(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError(f"invalid integer: {value!r}")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value, 0)
    raise ValueError(f"invalid integer: {value!r}")


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


def _extract_function(source: str, name: str) -> str:
    pattern = re.compile(
        rf"(?m)^(?:{re.escape(name)}|[^\s\n][^\n]*\b{re.escape(name)})\s*\("
    )
    matches = list(pattern.finditer(source))
    if len(matches) != 1:
        raise ValueError(f"{name}: expected exactly one definition; found {len(matches)}")
    brace = source.find("{", matches[0].end())
    if brace < 0:
        raise ValueError(f"{name}: opening brace not found")
    depth = 0
    for index in range(brace, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[brace + 1 : index]
    raise ValueError(f"{name}: closing brace not found")


def _split_args(text: str) -> list[str]:
    result: list[str] = []
    start = 0
    depth = 0
    for index, char in enumerate(text):
        if char in "([{" :
            depth += 1
        elif char in ")]}" :
            depth -= 1
            if depth < 0:
                raise ValueError("call argument nesting underflow")
        elif char == "," and depth == 0:
            result.append(text[start:index].strip())
            start = index + 1
    result.append(text[start:].strip())
    return result


def _calls(body: str, name: str) -> list[list[str]]:
    pattern = re.compile(rf"\b{re.escape(name)}\s*\(")
    result: list[list[str]] = []
    for match in pattern.finditer(body):
        open_index = body.find("(", match.start())
        depth = 0
        end = None
        for index in range(open_index, len(body)):
            char = body[index]
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    end = index
                    break
        if end is None:
            raise ValueError(f"{name}: unterminated call expression")
        result.append(_split_args(body[open_index + 1 : end]))
    return result


def _instruction_at(row: dict[str, Any], address: str) -> tuple[int, dict[str, Any]]:
    instructions = row.get("instructions")
    if not isinstance(instructions, list):
        raise ValueError("instruction row has no instructions")
    matches = [
        (index, instruction)
        for index, instruction in enumerate(instructions)
        if isinstance(instruction, dict) and instruction.get("address") == address
    ]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one instruction at {address}; found {len(matches)}")
    return matches[0]


def _load_ghidra(ghidra_root: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]], list[dict[str, Any]]]:
    binary_path = ghidra_root / "binary.json"
    functions_path = ghidra_root / "functions.jsonl"
    callgraph_path = ghidra_root / "callgraph.jsonl"
    for path in (binary_path, functions_path, callgraph_path):
        if not path.is_file():
            raise FileNotFoundError(f"missing Ghidra export file: {path}")
    binary = json.loads(binary_path.read_text(encoding="utf-8"))
    functions = {
        row["address"]: row
        for row in _read_jsonl(functions_path)
        if isinstance(row.get("address"), str)
    }
    callgraph = [row for row in _read_jsonl(callgraph_path)]
    return binary, functions, callgraph


def _direct_edges(callgraph: list[dict[str, Any]], parent: str, child: str) -> list[dict[str, Any]]:
    return [
        row
        for row in callgraph
        if row.get("from_function") == parent
        and row.get("to") == child
        and row.get("indirect") is False
    ]


def _trace_entry_receiver(
    helper,
    row: dict[str, Any],
    call_index: int,
    functions: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    function = row.get("function") or {}
    function_address = function.get("address")
    calling_convention = function.get("calling_convention")
    if calling_convention != "__thiscall":
        return {
            "evidence_state": "ambiguous",
            "status": "half-step-not-thiscall",
            "calling_convention": calling_convention,
            "chain": [],
        }

    instructions = row.get("instructions")
    if not isinstance(instructions, list):
        raise ValueError(f"{function_address}: instructions missing")

    tracked = "ECX"
    chain: list[dict[str, Any]] = []
    for index in range(call_index - 1, -1, -1):
        instruction = instructions[index]
        mnemonic, operands, pcode, opcodes = helper.instruction_parts(
            instruction, str(function_address)
        )
        address = instruction["address"]

        if opcodes & CONTROL_PCODE or mnemonic.startswith("J") or mnemonic in {"RET", "RETF", "IRET", "LOOP", "LOOPE", "LOOPNE"}:
            return {
                "evidence_state": "ambiguous",
                "status": "control-flow-barrier-before-entry-origin",
                "tracked_register": tracked,
                "barrier_instruction": address,
                "chain": chain,
            }

        if "CALLIND" in opcodes:
            return {
                "evidence_state": "ambiguous",
                "status": "indirect-call-before-entry-origin",
                "tracked_register": tracked,
                "barrier_instruction": address,
                "chain": chain,
            }
        if "CALL" in opcodes:
            if tracked not in CALLEE_SAVED:
                return {
                    "evidence_state": "ambiguous",
                    "status": "caller-saved-register-crosses-call",
                    "tracked_register": tracked,
                    "barrier_instruction": address,
                    "chain": chain,
                }
            flows = instruction.get("flows")
            if not isinstance(flows, list) or len(flows) != 1 or not isinstance(flows[0], str):
                return {
                    "evidence_state": "ambiguous",
                    "status": "callee-saved-cross-call-target-not-unique",
                    "tracked_register": tracked,
                    "barrier_instruction": address,
                    "chain": chain,
                }
            target = flows[0]
            target_cc = (functions.get(target) or {}).get("calling_convention")
            if target_cc not in SUPPORTED_ABI:
                return {
                    "evidence_state": "ambiguous",
                    "status": "callee-saved-cross-call-abi-unsupported",
                    "tracked_register": tracked,
                    "barrier_instruction": address,
                    "call_target": target,
                    "call_target_convention": target_cc,
                    "chain": chain,
                }
            chain.append(
                {
                    "instruction": address,
                    "kind": "callee-saved-register-preserved-across-direct-call",
                    "register": tracked,
                    "call_target": target,
                    "call_target_convention": target_cc,
                }
            )
            continue

        destination = helper.parse_register(operands[0]) if operands else None
        if destination != tracked:
            continue
        if mnemonic in NONWRITING_FIRST_OPERAND:
            continue
        if mnemonic == "MOV" and len(operands) >= 2:
            source_register = helper.parse_register(operands[1])
            if source_register is not None:
                chain.append(
                    {
                        "instruction": address,
                        "kind": "register-copy",
                        "from": source_register,
                        "to": tracked,
                    }
                )
                tracked = source_register
                continue
        if mnemonic == "LEA" and len(operands) >= 2:
            memory = helper.parse_memory(operands[1])
            if memory is not None and memory[1] == 0:
                source_register = memory[0]
                chain.append(
                    {
                        "instruction": address,
                        "kind": "zero-displacement-address-copy",
                        "from": source_register,
                        "to": tracked,
                    }
                )
                tracked = source_register
                continue
        return {
            "evidence_state": "ambiguous",
            "status": "receiver-register-redefined",
            "tracked_register": tracked,
            "clobber_instruction": address,
            "clobber_text": instruction.get("text"),
            "clobber_pcode": pcode,
            "chain": chain,
        }

    if tracked == "ECX":
        return {
            "evidence_state": "verified",
            "status": "exact-entry-ECX-value-preserved",
            "entry_register": "ECX",
            "chain": chain,
            "abi_rule": "x86 standard ABI preserves EBX/ESI/EDI/EBP across direct calls",
        }
    return {
        "evidence_state": "ambiguous",
        "status": "trace-ended-in-non-entry-receiver-register",
        "tracked_register": tracked,
        "chain": chain,
    }


def analyze_global_vehicle_body_owner_continuity(
    source_path: Path,
    ghidra_root: Path,
    instruction_export: Path,
    global_vehicle_identity_path: Path,
    chassis_identity_path: Path,
    body_frame_contract_path: Path,
    *,
    expected_source_sha256: str = SOURCE_SHA256,
) -> dict[str, Any]:
    source_bytes = source_path.read_bytes()
    source_sha = hashlib.sha256(source_bytes).hexdigest()
    if source_sha != expected_source_sha256:
        raise ValueError(
            f"unexpected SHIFT.exe.c SHA-256: expected {expected_source_sha256}, got {source_sha}"
        )
    source = source_bytes.decode("utf-8", errors="strict")

    global_identity = _load(global_vehicle_identity_path, GLOBAL_FORMAT)
    chassis = _load(chassis_identity_path, CHASSIS_FORMAT)
    body = _load(body_frame_contract_path, BODY_FORMAT)

    identity_join = global_identity.get("identity_join") or {}
    global_handoff = global_identity.get("handoff") or {}
    _require(identity_join.get("global_outer_receiver_is_vehicle_component_base") is True,
             "global vehicle component base is not proven")
    _require(identity_join.get("same_numeric_address") is True,
             "global vehicle/outer receiver address equality is not proven")
    _require(_int(identity_join.get("outer_update_receiver_address")) == GLOBAL_VEHICLE_ADDRESS,
             "global vehicle address drift")
    _require(global_handoff.get("global_vehicle_component_base_identity_ready") is True,
             "global vehicle component handoff is not ready")
    _require(global_handoff.get("outer_receiver_to_BODY_owner_continuity_proven") is False,
             "global identity input preclaims BODY owner continuity")

    selection = chassis.get("selection") or {}
    chassis_handoff = chassis.get("handoff") or {}
    _require(selection.get("main_chassis_BODY_selected") is True,
             "BMW chassis BODY is not selected")
    _require(_int(selection.get("selected_BODY_index")) == 0,
             "BMW chassis BODY index drift")
    _require(chassis_handoff.get("vehicle_BODY_selection_ready") is False,
             "chassis input preclaims vehicle BODY readiness")

    body_source = body.get("source") or {}
    body_functions = body.get("functions") or {}
    _require(body_source.get("executable_md5") == PE_MD5,
             "BODY contract executable identity drift")
    _require(body_source.get("decompile_sha256") == SOURCE_SHA256,
             "BODY contract source identity drift")
    _require((body_functions.get("FUN_00765470") or {}).get("address") == HALF_STEP,
             "half-step anchor drift")
    loop = body_functions.get("FUN_007b2270") or {}
    _require(loop.get("address") == BODY_ARRAY_LOOP, "BODY-array loop anchor drift")
    _require(_int(loop.get("body_count_offset")) == 0x10,
             "BODY owner count offset drift")
    _require(_int(loop.get("body_array_offset")) == 0x14,
             "BODY owner array offset drift")
    _require(_int(loop.get("body_stride")) == 0x170,
             "BODY stride drift")

    outer_body = _extract_function(source, "FUN_00770e80")
    half_body = _extract_function(source, "FUN_00765470")
    outer_half_calls = _calls(outer_body, "FUN_00765470")
    half_body_calls = _calls(half_body, "FUN_007b2270")
    if len(outer_half_calls) != 2:
        raise ValueError(
            f"FUN_00770e80: expected exactly two FUN_00765470 calls; found {len(outer_half_calls)}"
        )
    if len(half_body_calls) != 1:
        raise ValueError(
            f"FUN_00765470: expected exactly one FUN_007b2270 call; found {len(half_body_calls)}"
        )
    source_outer_to_half = all(call and call[0] == "this" for call in outer_half_calls)
    source_half_to_body_owner = bool(half_body_calls[0]) and half_body_calls[0][0] == "this"

    binary, functions, callgraph = _load_ghidra(ghidra_root)
    _require(binary.get("executable_md5") == PE_MD5,
             "Ghidra executable identity drift")
    for required in (OUTER_UPDATE, HALF_STEP, BODY_ARRAY_LOOP):
        _require(required in functions, f"Ghidra function missing: {required}")
    _require((functions[HALF_STEP].get("calling_convention") == "__thiscall"),
             "FUN_00765470 calling convention drift")
    _require((functions[BODY_ARRAY_LOOP].get("calling_convention") == "__thiscall"),
             "FUN_007b2270 calling convention drift")

    outer_edges = _direct_edges(callgraph, OUTER_UPDATE, HALF_STEP)
    _require(sorted(row.get("instruction") for row in outer_edges) == sorted(OUTER_HALF_STEP_CALLS),
             "outer -> half-step direct callsite set drift")
    body_edges = _direct_edges(callgraph, HALF_STEP, BODY_ARRAY_LOOP)
    _require(len(body_edges) == 1 and body_edges[0].get("instruction") == HALF_STEP_BODY_CALL,
             "half-step -> BODY-array direct callsite drift")

    helper = _pointer_helper()
    instruction_rows = helper.load_instructions(instruction_export)
    _require(HALF_STEP in instruction_rows,
             "targeted instruction export is missing FUN_00765470")
    half_row = instruction_rows[HALF_STEP]
    call_index, call = _instruction_at(half_row, HALF_STEP_BODY_CALL)
    mnemonic, operands, pcode, opcodes = helper.instruction_parts(call, HALF_STEP)
    flows = call.get("flows")
    _require("CALL" in opcodes and "CALLIND" not in opcodes,
             "0x0076582a is not a direct CALL in p-code")
    _require(isinstance(flows, list) and BODY_ARRAY_LOOP in flows,
             "0x0076582a no longer flows to FUN_007b2270")

    receiver_trace = _trace_entry_receiver(helper, half_row, call_index, functions)
    machine_half_to_body_owner = receiver_trace.get("evidence_state") == "verified"

    continuity_proven = (
        source_outer_to_half
        and source_half_to_body_owner
        and machine_half_to_body_owner
    )

    selected_index = 0 if continuity_proven else None
    blockers: list[dict[str, Any]] = []
    if not source_outer_to_half:
        blockers.append({
            "id": "outer-to-half-step-source-receiver",
            "evidence_state": "disproved-or-ambiguous",
            "required_evidence": "FUN_00770e80 must pass its own this pointer to both FUN_00765470 calls",
        })
    if not source_half_to_body_owner:
        blockers.append({
            "id": "half-step-to-BODY-owner-source-receiver",
            "evidence_state": "disproved-or-ambiguous",
            "required_evidence": "FUN_00765470 must pass its own this pointer to FUN_007b2270",
        })
    if not machine_half_to_body_owner:
        blockers.append({
            "id": "half-step-to-BODY-owner-machine-receiver",
            "evidence_state": receiver_trace.get("evidence_state", "unknown"),
            "status": receiver_trace.get("status"),
            "required_evidence": "trace ECX at 0x0076582a back to FUN_00765470 entry ECX without pointer transformation",
        })

    return {
        "format": FORMAT,
        "inputs": {
            "source": str(source_path),
            "ghidra_export": str(ghidra_root),
            "instruction_export": str(instruction_export),
            "global_vehicle_identity": str(global_vehicle_identity_path),
            "chassis_identity": str(chassis_identity_path),
            "body_frame_contract": str(body_frame_contract_path),
        },
        "source_identity": {
            "sha256": source_sha,
            "executable_md5": PE_MD5,
        },
        "source_receiver_join": {
            "outer_to_half_step_call_count": len(outer_half_calls),
            "outer_to_half_step_first_argument": [call[0] if call else None for call in outer_half_calls],
            "outer_receiver_forwarded_to_half_step": source_outer_to_half,
            "half_step_to_BODY_loop_call_count": len(half_body_calls),
            "half_step_to_BODY_loop_first_argument": half_body_calls[0][0] if half_body_calls[0] else None,
            "half_step_receiver_forwarded_to_BODY_owner": source_half_to_body_owner,
        },
        "machine_receiver_join": {
            "call_instruction": HALF_STEP_BODY_CALL,
            "call_mnemonic": mnemonic,
            "call_operands": operands,
            "call_pcode": pcode,
            "call_flows": flows,
            "receiver_trace": receiver_trace,
            "half_step_entry_ECX_preserved_to_BODY_owner_call": machine_half_to_body_owner,
        },
        "identity_join": {
            "global_vehicle_address": f"0x{GLOBAL_VEHICLE_ADDRESS:08x}",
            "global_vehicle_component_base_identity_ready": True,
            "main_chassis_BODY_index": 0,
            "BODY_array_owner_is_global_vehicle_base": continuity_proven,
            "evidence_state": "proven-source-machine-composed" if continuity_proven else "blocked",
        },
        "handoff": {
            "outer_receiver_to_BODY_owner_continuity_proven": continuity_proven,
            "vehicle_BODY_selection_ready": continuity_proven,
            "selected_BODY_index": selected_index,
            "phase698_positive_selection_admissible": continuity_proven,
            "phase703_old_update_child_equality_required": False,
            "vehicle_world_transform_ready": False,
            "critical_next_join": (
                "BODY origin/basis -> renderer SVWT/world-transform convention"
                if continuity_proven
                else "FUN_00765470 entry ECX -> 0x0076582a FUN_007b2270 receiver"
            ),
        },
        "blockers": blockers,
        "scope": {
            "update_child_pointer_equals_global_vehicle_base_proven": False,
            "update_child_pointer_equality_required": False,
            "BODY_owner_identity_from_callgraph_adjacency_alone": False,
            "callee_saved_registers_crossed_only_under_supported_ABI": True,
            "class_identity_inferred": False,
            "BODY_pose_to_renderer_transform_proven": False,
            "original_game_executed": False,
            "new_runtime_capture_required": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("global_vehicle_identity", type=Path)
    parser.add_argument("chassis_identity", type=Path)
    parser.add_argument("body_frame_contract", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = analyze_global_vehicle_body_owner_continuity(
        args.source,
        args.ghidra_export,
        args.instruction_export,
        args.global_vehicle_identity,
        args.chassis_identity,
        args.body_frame_contract,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    print(
        "vehicle BODY selection ready: "
        f"{report['handoff']['vehicle_BODY_selection_ready']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
