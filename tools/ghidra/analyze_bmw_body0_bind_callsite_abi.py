#!/usr/bin/env python3
"""Prove physical __thiscall/stack argument mapping at FUN_007b7840 callers.

This stage is deliberately narrower than BODY0 bind semantics. It consumes the
source-backed initialization frontier plus targeted Ghidra instruction rows,
reuses the merged all-path register-provenance analyzer, and proves only the
physical-to-formal ABI mapping at the two retail direct callsites.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import analyze_bmw_body0_bind_callsite_register_provenance as _register_provenance

FORMAT = "SHIFT.BMWBody0BindCallsiteABI/1"
FRONTIER_FORMAT = "SHIFT.BMWBody0BindInitializationFrontier/1"
REGISTER_FORMAT = "SHIFT.BMWBody0BindCallsiteRegisterProvenance/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"
POSE_WRITER = "0x007b7840"
SELF_CALL = "0x007b7d75"
EXTERNAL_CALLER = "0x007b8260"
EXTERNAL_CALL = "0x007b82f4"
EXTERNAL_ENTRY_THIS_COPY = "0x007b8282"
EXPECTED_CC = "__thiscall"
EXPECTED_SIGNATURE = (
    "undefined FUN_007b7840(void * this, float * param_1, double * param_2, "
    "undefined1 param_3, undefined1 param_4)"
)
FORMAL_TYPES = {
    "this": "void *",
    "param_1": "float *",
    "param_2": "double *",
    "param_3": "undefined1",
    "param_4": "undefined1",
}


def _load_json(path: Path, expected: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("format") != expected:
        raise ValueError(f"{path}: expected {expected}")
    return value


def _read_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{line_no}: expected object")
        rows.append(row)
    return rows


def _addr(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError(f"invalid address: {value!r}")
    token = value.strip().lower()
    if token.startswith("fun_"):
        token = token[4:]
    if token.startswith("0x"):
        token = token[2:]
    try:
        return f"0x{int(token, 16):08x}"
    except ValueError as exc:
        raise ValueError(f"invalid address: {value!r}") from exc


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _ops(instruction: dict[str, Any]) -> list[str]:
    operands = instruction.get("operands")
    if not isinstance(operands, list) or any(not isinstance(item, str) for item in operands):
        raise ValueError(f"{instruction.get('address')}: operands must be string list")
    return [" ".join(item.upper().split()) for item in operands]


def _index_rows(path: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in _read_rows(path):
        _require(row.get("format") == INSTRUCTION_FORMAT, f"{path}: instruction format drift")
        _require(row.get("found") is True, f"{path}: targeted function unresolved")
        function = row.get("function") or {}
        address = _addr(function.get("address"))
        _require(address not in result, f"duplicate instruction row {address}")
        instructions = row.get("instructions")
        _require(isinstance(instructions, list) and instructions, f"{address}: empty instructions")
        _require(row.get("instruction_count") == len(instructions), f"{address}: instruction_count mismatch")
        result[address] = row
    return result


def _instruction_map(row: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    previous = -1
    instructions = row.get("instructions")
    _require(isinstance(instructions, list), "instruction list missing")
    for instruction in instructions:
        _require(isinstance(instruction, dict), "instruction is not object")
        address = _addr(instruction.get("address"))
        numeric = int(address, 16)
        _require(numeric > previous, "instruction addresses are not strictly increasing")
        _require(address not in result, f"duplicate instruction {address}")
        previous = numeric
        result[address] = instruction
    return result


def _expect(
    by_address: dict[str, dict[str, Any]],
    address: str,
    mnemonic: str,
    operands: list[str],
    fallthrough: str,
) -> None:
    instruction = by_address.get(address)
    _require(instruction is not None, f"missing instruction {address}")
    _require(
        str(instruction.get("mnemonic") or "").upper() == mnemonic,
        f"{address}: mnemonic drift",
    )
    actual_operands = _ops(instruction)
    _require(actual_operands == operands, f"{address}: operands drift: {actual_operands}")
    _require(
        _addr(instruction.get("fallthrough")) == fallthrough,
        f"{address}: fallthrough drift",
    )


def _expect_call(by_address: dict[str, dict[str, Any]], address: str) -> None:
    instruction = by_address.get(address)
    _require(instruction is not None, f"missing call {address}")
    _require(str(instruction.get("mnemonic") or "").upper() == "CALL", f"{address}: not CALL")
    targets: list[str] = []
    for value in list(instruction.get("flows") or []) + list(instruction.get("operands") or []):
        if not isinstance(value, str):
            continue
        try:
            targets.append(_addr(value))
        except ValueError:
            pass
    _require(POSE_WRITER in targets, f"{address}: direct target drift")


def _validate_frontier(frontier: dict[str, Any]) -> None:
    anchor = (frontier.get("anchors") or {}).get("pose_writer_candidate") or {}
    _require(_addr(anchor.get("address")) == POSE_WRITER, "pose-writer address drift")
    _require(anchor.get("calling_convention") == EXPECTED_CC, "pose-writer calling convention drift")
    _require(anchor.get("signature") == EXPECTED_SIGNATURE, "pose-writer signature drift")

    writer = frontier.get("pose_writer_candidate") or {}
    _require(writer.get("direct_caller_count") == 2, "expected two retail direct callers")
    _require(writer.get("bind_initializer_semantics_proven") is False, "frontier preclaims bind semantics")
    callers = writer.get("direct_callers")
    _require(isinstance(callers, list) and len(callers) == 2, "expected two retail direct caller rows")
    pairs = {
        (_addr(row.get("caller")), _addr(row.get("callsite")))
        for row in callers
        if isinstance(row, dict)
    }
    _require(
        pairs == {(POSE_WRITER, SELF_CALL), (EXTERNAL_CALLER, EXTERNAL_CALL)},
        "retail caller set drift",
    )
    for row in callers:
        _require(row.get("BODY0_pointer_proven") is False, "frontier preclaims BODY0 pointer")
        _require(row.get("bind_initializer_semantics_proven") is False, "frontier preclaims initializer")


def _build_and_validate_register_report(
    frontier_path: Path,
    instruction_export_path: Path,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    report = _register_provenance.analyze_bmw_body0_bind_callsite_register_provenance(
        frontier_path,
        instruction_export_path,
    )
    _require(report.get("format") == REGISTER_FORMAT, "register provenance format drift")
    analysis = report.get("analysis") or {}
    _require(analysis.get("all_frontier_callsites_analyzed") is True, "register provenance incomplete")
    rows = analysis.get("callsites")
    _require(isinstance(rows, list) and len(rows) == 2, "register provenance callsite count drift")
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        _require(isinstance(row, dict), "register provenance callsite row invalid")
        callsite = _addr(row.get("callsite"))
        indexed[callsite] = row
        _require(row.get("physical_register_provenance_ready") is True, "physical register provenance not ready")
        _require(row.get("BODY0_pointer_proven") is False, "register provenance preclaims BODY0")
        _require(row.get("bind_initializer_semantics_proven") is False, "register provenance preclaims bind semantics")
    _require(set(indexed) == {SELF_CALL, EXTERNAL_CALL}, "register provenance caller set drift")

    external_registers = indexed[EXTERNAL_CALL].get("registers_before_call") or {}
    _require(
        (external_registers.get("ECX") or {}).get("origins") == ["entry:ECX"],
        "external call receiver does not resolve to entry ECX",
    )
    _require(
        (external_registers.get("ESI") or {}).get("origins") == ["entry:ECX"],
        "external call preserved ESI does not resolve to entry ECX",
    )
    return report, indexed


def _validate_pose_writer_row(row: dict[str, Any]) -> None:
    function = row.get("function") or {}
    _require(
        function.get("calling_convention") == EXPECTED_CC,
        "pose-writer instruction metadata calling convention drift",
    )
    by = _instruction_map(row)
    # Self-call stack setup is one exact fallthrough chain: p4, p3, p2, p1, ECX=this.
    chain = [
        ("0x007b7d5d", "MOV", ["EDI", "DWORD PTR [EBP + -0X24]"], "0x007b7d60"),
        ("0x007b7d60", "MOV", ["EAX", "DWORD PTR [EBP + -0X28]"], "0x007b7d63"),
        ("0x007b7d63", "MOV", ["ECX", "DWORD PTR [EBX + 0XC]"], "0x007b7d66"),
        ("0x007b7d66", "PUSH", ["EAX"], "0x007b7d67"),
        ("0x007b7d67", "MOV", ["EAX", "DWORD PTR [EBP + -0X20]"], "0x007b7d6a"),
        ("0x007b7d6a", "PUSH", ["EDI"], "0x007b7d6b"),
        ("0x007b7d6b", "PUSH", ["ECX"], "0x007b7d6c"),
        ("0x007b7d6c", "MOV", ["ECX", "DWORD PTR [EAX]"], "0x007b7d6e"),
        ("0x007b7d6e", "LEA", ["EDX", "[EBP + 0XFFFFFD50]"], "0x007b7d74"),
        ("0x007b7d74", "PUSH", ["EDX"], SELF_CALL),
    ]
    for expected in chain:
        _expect(by, *expected)
    _expect_call(by, SELF_CALL)


def _validate_external_row(row: dict[str, Any]) -> None:
    by = _instruction_map(row)
    _expect(by, EXTERNAL_ENTRY_THIS_COPY, "MOV", ["ESI", "ECX"], "0x007b8284")
    # The x87 instructions between pushes touch EBP-relative locals only. Exact
    # fallthrough validation proves there is no CALL/branch/ESP writer in this
    # retail stack-argument construction chain.
    chain = [
        ("0x007b82d3", "MOV", ["ECX", "DWORD PTR [EBX + 0XC]"], "0x007b82d6"),
        ("0x007b82d6", "FSTP", ["FLOAT PTR [EBP + -0X50]"], "0x007b82d9"),
        ("0x007b82d9", "FLD", ["FLOAT PTR [EAX + 0X4]"], "0x007b82dc"),
        ("0x007b82dc", "MOV", ["EDX", "DWORD PTR [EBX + 0X8]"], "0x007b82df"),
        ("0x007b82df", "PUSH", ["ECX"], "0x007b82e0"),
        ("0x007b82e0", "FSTP", ["FLOAT PTR [EBP + -0X4C]"], "0x007b82e3"),
        ("0x007b82e3", "FLD", ["FLOAT PTR [EAX + 0X8]"], "0x007b82e6"),
        ("0x007b82e6", "MOV", ["EAX", "DWORD PTR [ESI + 0X18]"], "0x007b82e9"),
        ("0x007b82e9", "PUSH", ["EDX"], "0x007b82ea"),
        ("0x007b82ea", "FSTP", ["FLOAT PTR [EBP + -0X48]"], "0x007b82ed"),
        ("0x007b82ed", "PUSH", ["EAX"], "0x007b82ee"),
        ("0x007b82ee", "LEA", ["ECX", "[EBP + -0X80]"], "0x007b82f1"),
        ("0x007b82f1", "PUSH", ["ECX"], "0x007b82f2"),
        ("0x007b82f2", "MOV", ["ECX", "ESI"], EXTERNAL_CALL),
    ]
    for expected in chain:
        _expect(by, *expected)
    _expect_call(by, EXTERNAL_CALL)


def _argument_rows(callsite: str) -> list[dict[str, Any]]:
    if callsite == SELF_CALL:
        return [
            {"formal": "this", "type": FORMAL_TYPES["this"], "physical": "ECX", "producer": "0x007b7d6c", "source_expression": "dword ptr [dword ptr [EBP - 0x20]]"},
            {"formal": "param_1", "type": FORMAL_TYPES["param_1"], "physical": "stack+0x04", "producer": "0x007b7d74", "source_expression": "address [EBP - 0x2b0]"},
            {"formal": "param_2", "type": FORMAL_TYPES["param_2"], "physical": "stack+0x08", "producer": "0x007b7d6b", "source_expression": "dword ptr [EBX + 0x0c]"},
            {"formal": "param_3", "type": FORMAL_TYPES["param_3"], "physical": "stack+0x0c", "producer": "0x007b7d6a", "source_expression": "dword ptr [EBP - 0x24]"},
            {"formal": "param_4", "type": FORMAL_TYPES["param_4"], "physical": "stack+0x10", "producer": "0x007b7d66", "source_expression": "dword ptr [EBP - 0x28]"},
        ]
    return [
        {"formal": "this", "type": FORMAL_TYPES["this"], "physical": "ECX", "producer": "0x007b82f2", "source_expression": "entry:ECX (all-path preserved as ESI)"},
        {"formal": "param_1", "type": FORMAL_TYPES["param_1"], "physical": "stack+0x04", "producer": "0x007b82f1", "source_expression": "address [EBP - 0x80]"},
        {"formal": "param_2", "type": FORMAL_TYPES["param_2"], "physical": "stack+0x08", "producer": "0x007b82ed", "source_expression": "dword ptr [entry:ECX + 0x18]"},
        {"formal": "param_3", "type": FORMAL_TYPES["param_3"], "physical": "stack+0x0c", "producer": "0x007b82e9", "source_expression": "dword ptr [EBX + 0x08]"},
        {"formal": "param_4", "type": FORMAL_TYPES["param_4"], "physical": "stack+0x10", "producer": "0x007b82df", "source_expression": "dword ptr [EBX + 0x0c]"},
    ]


def analyze_bmw_body0_bind_callsite_abi(
    frontier_path: Path,
    instruction_export_path: Path,
) -> dict[str, Any]:
    frontier = _load_json(frontier_path, FRONTIER_FORMAT)
    _validate_frontier(frontier)
    register_report, register_calls = _build_and_validate_register_report(
        frontier_path,
        instruction_export_path,
    )
    rows = _index_rows(instruction_export_path)
    _require(POSE_WRITER in rows, "instruction export missing pose writer row")
    _require(EXTERNAL_CALLER in rows, "instruction export missing external caller row")
    _validate_pose_writer_row(rows[POSE_WRITER])
    _validate_external_row(rows[EXTERNAL_CALLER])

    callsites = []
    for caller, callsite in ((POSE_WRITER, SELF_CALL), (EXTERNAL_CALLER, EXTERNAL_CALL)):
        register_row = register_calls[callsite]
        callsites.append(
            {
                "caller": caller,
                "callsite": callsite,
                "target": POSE_WRITER,
                "receiver_origins_before_call": (register_row.get("registers_before_call") or {}).get("ECX", {}).get("origins"),
                "formal_argument_sources": _argument_rows(callsite),
                "stack_push_order": ["param_4", "param_3", "param_2", "param_1"],
                "stack_slot_width_bytes": 4,
                "linear_fallthrough_stack_setup_proven": True,
                "BODY0_pointer_proven": False,
                "bind_initializer_semantics_proven": False,
            }
        )

    return {
        "format": FORMAT,
        "inputs": {
            "initialization_frontier": str(frontier_path),
            "instruction_export": str(instruction_export_path),
            "register_provenance_format": register_report.get("format"),
            "register_provenance_computed_in_process": True,
        },
        "target": {
            "function": POSE_WRITER,
            "calling_convention": EXPECTED_CC,
            "signature": EXPECTED_SIGNATURE,
            "physical_receiver_register": "ECX",
            "stack_slot_width_bytes": 4,
            "formal_parameters": ["this", "param_1", "param_2", "param_3", "param_4"],
            "formal_types": FORMAL_TYPES,
        },
        "analysis": {
            "direct_callsite_count": 2,
            "callsites": callsites,
            "source_signature_to_physical_ABI_binding_proven": True,
            "stack_argument_value_provenance_modeled": True,
            "right_to_left_stack_order_proven": True,
            "stack_setup_linear_fallthrough_proven": True,
            "external_receiver_entry_ECX_continuity_proven": True,
            "BODY0_pointer_at_bind_callsite_proven": False,
            "bind_origin_basis_value_semantics_proven": False,
            "bind_initializer_semantics_proven": False,
        },
        "handoff": {
            "pose_writer_physical_ABI_ready": True,
            "pose_writer_stack_argument_provenance_ready": True,
            "BODY0_bind_frame_proof_ready": False,
            "next_required_join": (
                "join one exact receiver to BMW BODY index 0 and trace the mapped param_1/param_2 "
                "values to source-backed bind origin+basis initialization"
            ),
        },
        "blockers": [
            {"id": "BODY0-pointer-at-bind-callsite-unproven", "evidence_state": "unknown"},
            {"id": "bind-origin-basis-value-provenance-unproven", "evidence_state": "unknown"},
            {"id": "pose-writer-candidate-bind-role-unproven", "evidence_state": "candidate"},
        ],
        "scope": {
            "source_parameter_names_reinterpreted_as_physical_semantics": False,
            "param_1_promoted_to_bind_origin": False,
            "param_2_promoted_to_bind_basis": False,
            "BODY0_pointer_identity_proven": False,
            "pose_writer_candidate_promoted_to_initializer": False,
            "BODY0_bind_matrix_proven": False,
            "original_game_executed": False,
            "new_runtime_capture_required": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("frontier", type=Path)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    report = analyze_bmw_body0_bind_callsite_abi(args.frontier, args.instruction_export)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
