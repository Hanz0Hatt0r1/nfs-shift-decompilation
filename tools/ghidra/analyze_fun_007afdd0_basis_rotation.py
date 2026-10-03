#!/usr/bin/env python3
"""Freeze the exact machine/p-code surface of FUN_007afdd0 without guessing math.

The BODY integration path proves that FUN_007afdd0 mutates the 3x3 f32 basis
from a three-component rotation increment.  This analyzer intentionally stops
short of calling that operation Rodrigues/quaternion/exponential-map math.  It
records the complete targeted instruction slice, floating-point instruction
order, memory widths, p-code memory effects, calls and branches, then reports
which precision/data-flow questions still block an exact native port.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.Fun007afdd0BasisRotationStatic/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"
TARGET_ADDRESS = "0x007afdd0"
TARGET_NAME = "FUN_007afdd0"

_MEMORY_OPERAND = re.compile(
    r"^\s*(?:(byte|word|dword|qword|tword|xmmword)\s+ptr\s+)?\[(.+)\]\s*$",
    re.IGNORECASE,
)
_SSE_SCALAR = {
    "MOVSS", "ADDSS", "SUBSS", "MULSS", "DIVSS", "SQRTSS", "MINSS", "MAXSS",
    "CVTSS2SD", "CVTSD2SS", "CVTSI2SS", "CVTTSS2SI", "CVTSS2SI", "COMISS", "UCOMISS",
}
_X87 = {
    "F2XM1", "FABS", "FADD", "FADDP", "FBLD", "FBSTP", "FCHS", "FCLEX", "FCMOVB",
    "FCMOVBE", "FCMOVE", "FCMOVNB", "FCMOVNBE", "FCMOVNE", "FCMOVNU", "FCMOVU",
    "FCOM", "FCOMI", "FCOMIP", "FCOMP", "FCOMPP", "FCOS", "FDECSTP", "FDIV",
    "FDIVP", "FDIVR", "FDIVRP", "FFREE", "FIADD", "FICOM", "FICOMP", "FIDIV",
    "FIDIVR", "FILD", "FIMUL", "FINCSTP", "FINIT", "FIST", "FISTP", "FISTTP",
    "FISUB", "FISUBR", "FLD", "FLD1", "FLDCW", "FLDENV", "FLDL2E", "FLDL2T",
    "FLDLG2", "FLDLN2", "FLDPI", "FLDZ", "FMUL", "FMULP", "FNCLEX", "FNINIT",
    "FNOP", "FNSAVE", "FNSTCW", "FNSTENV", "FNSTSW", "FPATAN", "FPREM", "FPREM1",
    "FPTAN", "FRNDINT", "FRSTOR", "FSAVE", "FSCALE", "FSIN", "FSINCOS", "FSQRT",
    "FST", "FSTCW", "FSTENV", "FSTP", "FSTSW", "FSUB", "FSUBP", "FSUBR", "FSUBRP",
    "FTST", "FUCOM", "FUCOMI", "FUCOMIP", "FUCOMP", "FUCOMPP", "FWAIT", "FXAM",
    "FXCH", "FXTRACT", "FYL2X", "FYL2XP1",
}
_X87_CONTROL = {"FLDCW", "FNSTCW", "FSTCW"}


def _read_single_row(path: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
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
            rows.append(row)
    if len(rows) != 1:
        raise ValueError(f"{path}: expected exactly one targeted function row, found {len(rows)}")
    return rows[0]


def _normalize_address(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("function address missing")
    token = value.strip().lower()
    if token.startswith("fun_"):
        token = token[4:]
    if token.startswith("0x"):
        token = token[2:]
    try:
        return f"0x{int(token, 16):08x}"
    except ValueError as exc:
        raise ValueError(f"invalid function address: {value!r}") from exc


def _validate_pcode(value: Any, address: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError(f"{address}: pcode must be a list")
    result: list[dict[str, Any]] = []
    for operation in value:
        if not isinstance(operation, dict):
            raise ValueError(f"{address}: pcode operation must be an object")
        opcode = operation.get("opcode")
        text = operation.get("text")
        if not isinstance(opcode, str) or not opcode:
            raise ValueError(f"{address}: pcode opcode missing")
        if not isinstance(text, str) or not text:
            raise ValueError(f"{address}: pcode text missing")
        inputs = operation.get("inputs")
        output = operation.get("output")
        structured = isinstance(inputs, list) and (output is None or isinstance(output, dict))
        result.append(
            {
                "opcode": opcode.upper(),
                "text": text,
                "structured_varnodes": structured,
                "output": output if structured else None,
                "inputs": inputs if structured else None,
            }
        )
    return result


def _memory_operands(operands: list[str], pcode: list[dict[str, Any]]) -> list[dict[str, Any]]:
    memory_ops = {op["opcode"] for op in pcode if op["opcode"] in {"LOAD", "STORE"}}
    if memory_ops == {"LOAD"}:
        access = "read"
    elif memory_ops == {"STORE"}:
        access = "write"
    elif memory_ops == {"LOAD", "STORE"}:
        access = "read-write"
    else:
        access = "unclassified"

    result: list[dict[str, Any]] = []
    for index, operand in enumerate(operands):
        match = _MEMORY_OPERAND.fullmatch(operand)
        if match is None:
            if "[" in operand or "]" in operand:
                result.append(
                    {
                        "operand_index": index,
                        "operand": operand,
                        "width": None,
                        "expression": None,
                        "access": access,
                        "parsed": False,
                    }
                )
            continue
        result.append(
            {
                "operand_index": index,
                "operand": operand,
                "width": match.group(1).lower() if match.group(1) else None,
                "expression": match.group(2).strip(),
                "access": access,
                "parsed": True,
            }
        )
    return result


def analyze_fun_007afdd0(export: Path) -> dict[str, Any]:
    row = _read_single_row(export)
    if row.get("format") != INSTRUCTION_FORMAT:
        raise ValueError(
            f"{export}: exact basis analysis requires {INSTRUCTION_FORMAT}; found {row.get('format')!r}"
        )
    if row.get("found") is not True:
        raise ValueError(f"{export}: target was not resolved")

    function = row.get("function")
    if not isinstance(function, dict):
        raise ValueError(f"{export}: function metadata missing")
    function_address = _normalize_address(function.get("address"))
    if function_address != TARGET_ADDRESS:
        raise ValueError(
            f"{export}: expected {TARGET_NAME} at {TARGET_ADDRESS}, found {function_address}"
        )

    instructions = row.get("instructions")
    if not isinstance(instructions, list) or not instructions:
        raise ValueError(f"{export}: instruction list is empty")
    if row.get("instruction_count") != len(instructions):
        raise ValueError(f"{export}: instruction_count mismatch")
    if _normalize_address(instructions[0].get("address")) != TARGET_ADDRESS:
        raise ValueError(f"{export}: first instruction is not {TARGET_ADDRESS}")

    machine = bytearray()
    trace: list[dict[str, Any]] = []
    float_trace: list[dict[str, Any]] = []
    memory_trace: list[dict[str, Any]] = []
    calls: list[dict[str, Any]] = []
    conditional_branches: list[dict[str, Any]] = []
    x87_count = 0
    sse_scalar_count = 0
    x87_control_count = 0
    structured_pcode_count = 0
    previous = -1

    for ordinal, instruction in enumerate(instructions):
        if not isinstance(instruction, dict):
            raise ValueError(f"{export}: instruction {ordinal} is not an object")
        address = _normalize_address(instruction.get("address"))
        numeric_address = int(address, 16)
        if numeric_address <= previous:
            raise ValueError(f"{export}: instruction addresses are not strictly increasing")
        previous = numeric_address

        payload = instruction.get("bytes")
        if not isinstance(payload, str) or not payload or len(payload) % 2:
            raise ValueError(f"{address}: invalid instruction bytes")
        try:
            raw = bytes.fromhex(payload)
        except ValueError as exc:
            raise ValueError(f"{address}: invalid instruction bytes") from exc
        machine.extend(raw)

        mnemonic = instruction.get("mnemonic")
        text = instruction.get("text")
        operands = instruction.get("operands")
        flows = instruction.get("flows")
        references = instruction.get("references")
        flow_type = instruction.get("flow_type")
        fallthrough = instruction.get("fallthrough")
        if not isinstance(mnemonic, str) or not mnemonic:
            raise ValueError(f"{address}: mnemonic missing")
        if not isinstance(text, str) or not text:
            raise ValueError(f"{address}: instruction text missing")
        if not isinstance(operands, list) or any(not isinstance(value, str) for value in operands):
            raise ValueError(f"{address}: operands must be strings")
        if not isinstance(flows, list) or any(not isinstance(value, str) for value in flows):
            raise ValueError(f"{address}: flows must be strings")
        if not isinstance(references, list):
            raise ValueError(f"{address}: references must be a list")

        pcode = _validate_pcode(instruction.get("pcode"), address)
        if pcode and all(operation["structured_varnodes"] for operation in pcode):
            structured_pcode_count += 1
        mem = _memory_operands(operands, pcode)
        upper = mnemonic.upper()
        floating_class: str | None = None
        if upper in _X87:
            floating_class = "x87"
            x87_count += 1
            if upper in _X87_CONTROL:
                x87_control_count += 1
        elif upper in _SSE_SCALAR:
            floating_class = "sse-scalar"
            sse_scalar_count += 1
        elif upper.startswith("F"):
            floating_class = "x87-unclassified"

        item = {
            "ordinal": ordinal,
            "address": address,
            "bytes": payload.lower(),
            "mnemonic": upper,
            "text": text,
            "operands": operands,
            "flow_type": flow_type,
            "fallthrough": fallthrough,
            "flows": flows,
            "references": references,
            "pcode": pcode,
            "memory_operands": mem,
            "floating_class": floating_class,
        }
        trace.append(item)
        if floating_class is not None:
            float_trace.append(item)
        for memory in mem:
            memory_trace.append({"instruction": address, "mnemonic": upper, **memory})
        if upper == "CALL":
            calls.append(
                {
                    "instruction": address,
                    "text": text,
                    "flows": flows,
                    "references": references,
                }
            )
        if upper.startswith("J") and upper != "JMP":
            conditional_branches.append(
                {
                    "instruction": address,
                    "mnemonic": upper,
                    "text": text,
                    "flows": flows,
                }
            )

    blockers: list[dict[str, Any]] = []
    if x87_count:
        blockers.append(
            {
                "id": "x87-stack-dataflow-unreconstructed",
                "reason": "instruction order is frozen but x87 stack-temporary equivalence has not been promoted into a source-level arithmetic DAG",
            }
        )
        if x87_control_count:
            blockers.append(
                {
                    "id": "x87-control-word-provenance-unresolved",
                    "reason": "FUN_007afdd0 touches x87 control state; the exact loaded/saved control-word value and scope must be proved",
                }
            )
        else:
            blockers.append(
                {
                    "id": "ambient-x87-control-word-unfrozen",
                    "reason": "x87 arithmetic is present but the function does not locally freeze its precision/rounding control word",
                }
            )
    if sse_scalar_count:
        blockers.append(
            {
                "id": "mxcsr-rounding-state-unfrozen",
                "reason": "scalar SSE arithmetic is present; the inherited MXCSR rounding/exception state is not part of the current contract",
            }
        )
    if calls:
        blockers.append(
            {
                "id": "callee-semantics-unfrozen",
                "reason": "the target contains direct/indirect calls whose exact arithmetic/side effects must be joined before a standalone native replacement is claimed",
                "count": len(calls),
            }
        )
    if conditional_branches:
        blockers.append(
            {
                "id": "floating-control-flow-paths-unproven",
                "reason": "conditional machine-code paths exist and must be mapped to exact input predicates and write sets",
                "count": len(conditional_branches),
            }
        )
    if memory_trace:
        blockers.append(
            {
                "id": "memory-aliasing-and-field-identity-unresolved",
                "reason": "instruction memory operands are frozen syntactically, but basis/increment pointer provenance and aliasing are not reconstructed by this artifact",
                "count": len(memory_trace),
            }
        )
    unsized = [item for item in memory_trace if item["width"] is None]
    if unsized:
        blockers.append(
            {
                "id": "unsized-memory-operands",
                "reason": "one or more memory operands lack an explicit width in the disassembly text",
                "count": len(unsized),
            }
        )
    unclassified_float = [
        item for item in float_trace if item["floating_class"] == "x87-unclassified"
    ]
    if unclassified_float:
        blockers.append(
            {
                "id": "unclassified-floating-mnemonics",
                "reason": "one or more F-prefixed instructions are not in the audited x87 mnemonic set",
                "mnemonics": sorted({item["mnemonic"] for item in unclassified_float}),
            }
        )
    if structured_pcode_count != len(trace):
        blockers.append(
            {
                "id": "structured-pcode-varnodes-missing",
                "reason": "the instruction exporter did not provide structured p-code input/output varnodes for every instruction; regenerate with the Phase 680 exporter",
                "instruction_count": len(trace),
                "structured_instruction_count": structured_pcode_count,
            }
        )

    return {
        "format": FORMAT,
        "target": TARGET_NAME,
        "target_address": TARGET_ADDRESS,
        "instruction_export": str(export),
        "instruction_export_format": INSTRUCTION_FORMAT,
        "function": function,
        "instruction_count": len(trace),
        "machine_byte_count": len(machine),
        "machine_sha256": hashlib.sha256(machine).hexdigest(),
        "instruction_freeze_ready": True,
        "native_port_ready": len(blockers) == 0,
        "floating_summary": {
            "x87_instruction_count": x87_count,
            "x87_control_instruction_count": x87_control_count,
            "sse_scalar_instruction_count": sse_scalar_count,
            "floating_instruction_count": len(float_trace),
        },
        "control_flow_summary": {
            "call_count": len(calls),
            "conditional_branch_count": len(conditional_branches),
        },
        "pcode_summary": {
            "instruction_count": len(trace),
            "structured_varnode_instruction_count": structured_pcode_count,
            "structured_varnodes_complete": structured_pcode_count == len(trace),
        },
        "memory_operand_count": len(memory_trace),
        "calls": calls,
        "conditional_branches": conditional_branches,
        "memory_trace": memory_trace,
        "floating_trace": float_trace,
        "instruction_trace": trace,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "scope": {
            "basis_rotation_callsite_proven_elsewhere": True,
            "basis_pointer_identity_proven_here": False,
            "rotation_increment_pointer_identity_proven_here": False,
            "rodrigues_semantics_assumed": False,
            "quaternion_semantics_assumed": False,
            "normalization_assumed": False,
            "x87_stack_semantics_promoted": False,
            "native_arithmetic_promoted": len(blockers) == 0,
            "note": (
                "This artifact freezes exact machine order and Ghidra p-code evidence only. "
                "A native FUN_007afdd0 implementation must remain disabled until every blocker "
                "is closed by static evidence; no standard rotation formula is substituted."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument(
        "--require-native-ready",
        action="store_true",
        help="return non-zero while any precision/data-flow blocker remains",
    )
    args = parser.parse_args()

    report = analyze_fun_007afdd0(args.instruction_export)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")

    print(f"format: {report['format']}")
    print(f"instructions: {report['instruction_count']}")
    print(f"machine sha256: {report['machine_sha256']}")
    print(f"x87 instructions: {report['floating_summary']['x87_instruction_count']}")
    print(f"SSE scalar instructions: {report['floating_summary']['sse_scalar_instruction_count']}")
    print(f"blockers: {report['blocker_count']}")
    print(f"native port ready: {str(report['native_port_ready']).lower()}")
    if args.json_out:
        print(f"output: {args.json_out}")
    if args.require_native_ready and not report["native_port_ready"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
