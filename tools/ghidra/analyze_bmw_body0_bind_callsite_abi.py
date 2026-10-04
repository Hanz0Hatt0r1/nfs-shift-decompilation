#!/usr/bin/env python3
"""Prove physical __thiscall/stack argument mapping at FUN_007b7840 callers.

This is deliberately narrower than BODY0 bind semantics.  It consumes the
existing initialization frontier, register-provenance report and targeted
Ghidra instruction rows and proves only physical-to-formal parameter mapping at
the two retail direct callsites.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.BMWBody0BindCallsiteABI/1"
FRONTIER_FORMAT = "SHIFT.BMWBody0BindInitializationFrontier/1"
REGISTER_FORMAT = "SHIFT.BMWBody0BindCallsiteRegisterProvenance/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"
POSE_WRITER = "0x007b7840"
SELF_CALL = "0x007b7d75"
EXTERNAL_CALLER = "0x007b8260"
EXTERNAL_CALL = "0x007b82f4"
EXPECTED_CC = "__thiscall"
EXPECTED_SIGNATURE = (
    "undefined FUN_007b7840(void * this, float * param_1, double * param_2, "
    "undefined1 param_3, undefined1 param_4)"
)


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
    if not isinstance(operands, list) or any(not isinstance(x, str) for x in operands):
        raise ValueError(f"{instruction.get('address')}: operands must be string list")
    return [" ".join(x.upper().split()) for x in operands]


def _index_rows(path: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in _read_rows(path):
        _require(row.get("format") == INSTRUCTION_FORMAT, f"{path}: instruction format drift")
        _require(row.get("found") is True, f"{path}: targeted function unresolved")
        fn = row.get("function") or {}
        address = _addr(fn.get("address"))
        _require(address not in result, f"duplicate instruction row {address}")
        instructions = row.get("instructions")
        _require(isinstance(instructions, list) and instructions, f"{address}: empty instructions")
        _require(row.get("instruction_count") == len(instructions), f"{address}: instruction_count mismatch")
        result[address] = row
    return result


def _instruction_map(row: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    previous = -1
    for instruction in row["instructions"]:
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
    fallthrough: str | None,
) -> None:
    ins = by_address.get(address)
    _require(ins is not None, f"missing instruction {address}")
    _require(str(ins.get("mnemonic") or "").upper() == mnemonic, f"{address}: mnemonic drift")
    _require(_ops(ins) == operands, f"{address}: operands drift: {_ops(ins)}")
    if fallthrough is not None:
        _require(_addr(ins.get("fallthrough")) == fallthrough, f"{address}: fallthrough drift")


def _expect_call(by_address: dict[str, dict[str, Any]], address: str) -> None:
    ins = by_address.get(address)
    _require(ins is not None, f"missing call {address}")
    _require(str(ins.get("mnemonic") or "").upper() == "CALL", f"{address}: not CALL")
    targets: list[str] = []
    for value in list(ins.get("flows") or []) + list(ins.get("operands") or []):
        if isinstance(value, str):
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
    _require(writer.get("bind_initializer_semantics_proven") is False, "frontier preclaims bind semantics")
    callers = writer.get("direct_callers")
    _require(isinstance(callers, list) and len(callers) == 2, "expected two retail direct callers")
    pairs = {(_addr(x.get("caller")), _addr(x.get("callsite"))) for x in callers if isinstance(x, dict)}
    _require(pairs == {(POSE_WRITER, SELF_CALL), (EXTERNAL_CALLER, EXTERNAL_CALL)}, "retail caller set drift")
    for row in callers:
        _require(row.get("BODY0_pointer_proven") is False, "frontier preclaims BODY0 pointer")
        _require(row.get("bind_initializer_semantics_proven") is False, "frontier preclaims initializer")


def _validate_register_report(report: dict[str, Any]) -> None:
    analysis = report.get("analysis") or {}
    _require(analysis.get("all_frontier_callsites_analyzed") is True, "register report incomplete")
    rows = analysis.get("callsites")
    _require(isinstance(rows, list) and len(rows) == 2, "register report callsite count drift")
    pairs = {(_addr(x.get("caller")), _addr(x.get("callsite"))) for x in rows if isinstance(x, dict)}
    _require(pairs == {(POSE_WRITER, SELF_CALL), (EXTERNAL_CALLER, EXTERNAL_CALL)}, "register report caller set drift")
    for row in rows:
        _require(row.get("physical_register_provenance_ready") is True, "physical register provenance not ready")
        _require(row.get("BODY0_pointer_proven") is False, "register report preclaims BODY0")
        _require(row.get("bind_initializer_semantics_proven") is False, "register report preclaims bind semantics")


def _validate_pose_writer_row(row: dict[str, Any]) -> None:
    fn = row.get("function") or {}
    _require(fn.get("calling_convention") == EXPECTED_CC, "pose-writer instruction metadata calling convention drift")
    by = _instruction_map(row)
    # Re-entrant/self call: p4, p3, p2, p1, then ECX=this.
    _expect(by, "0x007b7d5d", "MOV", ["EDI", "DWORD PTR [EBP - 0X24]"], "0x007b7d60")
    _expect(by, "0x007b7d60", "MOV", ["EAX", "DWORD PTR [EBP - 0X28]"], "0x007b7d63")
    _expect(by, "0x007b7d63", "MOV", ["ECX", "DWORD PTR [EBX + 0XC]"], "0x007b7d66")
    _expect(by, "0x007b7d66", "PUSH", ["EAX"], "0x007b7d67")
    _expect(by, "0x007b7d67", "MOV", ["EAX", "DWORD PTR [EBP - 0X20]"], "0x007b7d6a")
    _expect(by, "0x007b7d6a", "PUSH", ["EDI"], "0x007b7d6b")
    _expect(by, "0x007b7d6b", "PUSH", ["ECX"], "0x007b7d6c")
    _expect(by, "0x007b7d6c", "MOV", ["ECX", "DWORD PTR [EAX]"], "0x007b7d6e")
    _expect(by, "0x007b7d6e", "LEA", ["EDX", "[EBP - 0X2B0]"], "0x007b7d74")
    _expect(by, "0x007b7d74", "PUSH", ["EDX"], SELF_CALL)
    _expect_call(by, SELF_CALL)


def _validate_external_row(row: dict[str, Any]) -> None:
    by = _instruction_map(row)
    _expect(by, "0x007b827d", "MOV", ["ESI", "ECX"], "0x007b827f")
    _expect(by, "0x007b82d3", "MOV", ["ECX", "DWORD PTR [EBX + 0XC]"], "0x007b82d6")
    _expect(by, "0x007b82dc", "MOV", ["EDX", "DWORD PTR [EBX + 0X8]"], "0x007b82df")
    _expect(by, "0x007b82df", "PUSH", ["ECX"], "0x007b82e0")
    _expect(by, "0x007b82e6", "MOV", ["EAX", "DWORD PTR [ESI + 0X18]"], "0x007b82e9")
    _expect(by, "0x007b82e9", "PUSH", ["EDX"], "0x007b82ea")
    _expect(by, "0x007b82ed", "PUSH", ["EAX"], "0x007b82ee")
    _expect(by, "0x007b82ee", "LEA", ["ECX", "[EBP - 0X80]"], "0x007b82f1")
    _expect(by, "0x007b82f1", "PUSH", ["ECX"], "0x007b82f2")
    _expect(by, "0x007b82f2", "MOV", ["ECX", "ESI"], EXTERNAL_CALL)
    _expect_call(by, EXTERNAL_CALL)


def analyze_bmw_body0_bind_callsite_abi(
    frontier_path: Path,
    register_report_path: Path,
    instruction_export_path: Path,
) -> dict[str, Any]:
    frontier = _load_json(frontier_path, FRONTIER_FORMAT)
    registers = _load_json(register_report_path, REGISTER_FORMAT)
    _validate_frontier(frontier)
    _validate_register_report(registers)
    rows = _index_rows(instruction_export_path)
    _require(POSE_WRITER in rows, "instruction export missing pose writer row")
    _require(EXTERNAL_CALLER in rows, "instruction export missing external caller row")
    _validate_pose_writer_row(rows[POSE_WRITER])
    _validate_external_row(rows[EXTERNAL_CALLER])

    callsites = [
        {
            "caller": POSE_WRITER,
            "callsite": SELF_CALL,
            "target": POSE_WRITER,
            "physical_to_formal": {
                "this": "dword ptr [dword ptr [EBP - 0x20]]",
                "param_1": "address [EBP - 0x2b0]",
                "param_2": "dword ptr [EBX + 0x0c]",
                "param_3": "dword ptr [EBP - 0x24]",
                "param_4": "dword ptr [EBP - 0x28]",
            },
            "stack_push_order": ["param_4", "param_3", "param_2", "param_1"],
            "BODY0_pointer_proven": False,
            "bind_initializer_semantics_proven": False,
        },
        {
            "caller": EXTERNAL_CALLER,
            "callsite": EXTERNAL_CALL,
            "target": POSE_WRITER,
            "physical_to_formal": {
                "this": "entry:ECX (preserved as ESI)",
                "param_1": "address [EBP - 0x80]",
                "param_2": "dword ptr [entry:ECX + 0x18]",
                "param_3": "dword ptr [EBX + 0x08]",
                "param_4": "dword ptr [EBX + 0x0c]",
            },
            "stack_push_order": ["param_4", "param_3", "param_2", "param_1"],
            "BODY0_pointer_proven": False,
            "bind_initializer_semantics_proven": False,
        },
    ]
    return {
        "format": FORMAT,
        "inputs": {
            "initialization_frontier": str(frontier_path),
            "register_provenance": str(register_report_path),
            "instruction_export": str(instruction_export_path),
        },
        "target": {
            "function": POSE_WRITER,
            "calling_convention": EXPECTED_CC,
            "signature": EXPECTED_SIGNATURE,
            "formal_parameters": ["this", "param_1", "param_2", "param_3", "param_4"],
        },
        "analysis": {
            "direct_callsite_count": 2,
            "callsites": callsites,
            "physical_ABI_semantic_binding_proven": True,
            "stack_argument_value_provenance_modeled": True,
            "right_to_left_stack_order_proven": True,
            "BODY0_pointer_at_bind_callsite_proven": False,
            "bind_origin_basis_value_semantics_proven": False,
            "bind_initializer_semantics_proven": False,
        },
        "handoff": {
            "pose_writer_physical_ABI_ready": True,
            "pose_writer_stack_argument_provenance_ready": True,
            "BODY0_bind_frame_proof_ready": False,
            "next_required_join": (
                "prove which callsite receiver is exact BMW BODY0 and trace the mapped param_1/param_2 "
                "values to source-backed bind origin+basis initialization"
            ),
        },
        "blockers": [
            {
                "id": "BODY0-pointer-at-bind-callsite-unproven",
                "evidence_state": "unknown",
            },
            {
                "id": "bind-origin-basis-value-provenance-unproven",
                "evidence_state": "unknown",
            },
            {
                "id": "pose-writer-candidate-bind-role-unproven",
                "evidence_state": "candidate",
            },
        ],
        "scope": {
            "physical_parameter_names_are_source_backed_ordinals_only": True,
            "param_1_semantically_named_origin_proven": False,
            "param_2_semantically_named_basis_proven": False,
            "BODY0_pointer_identity_proven": False,
            "pose_writer_candidate_promoted_to_initializer": False,
            "callgraph_reachability_used_as_semantic_proof": False,
            "original_game_executed": False,
            "new_runtime_capture_required": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("frontier", type=Path)
    parser.add_argument("register_report", type=Path)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    report = analyze_bmw_body0_bind_callsite_abi(
        args.frontier, args.register_report, args.instruction_export
    )
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
