#!/usr/bin/env python3
"""Derive a fail-closed scalar-production frontier for FUN_007afdd0.

The Phase 680 report freezes instruction/p-code identity but deliberately does
not assign source-level scalar roles. This analyzer joins that freeze back to
the raw v2 instruction export and exposes only machine facts that are safe to
consume next: exact direct trig-helper call sites, f32 store candidates and
structured p-code backward dependency slices.

It never chooses which f32 store is squared magnitude, sqrt magnitude, sine or
cosine. It also never substitutes host libm semantics for retail calls.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.Fun007afdd0ScalarProvenance/1"
STATIC_FORMAT = "SHIFT.Fun007afdd0BasisRotationStatic/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"
TARGET_ADDRESS = "0x007afdd0"
TARGET_NAME = "FUN_007afdd0"
SINE_TARGET = "0x00900c40"
COSINE_TARGET = "0x00900b10"
SCALAR_BOUNDARY_ROLES = (
    "squared_magnitude_test",
    "sqrt_magnitude",
    "sine",
    "cosine",
)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _load_single_jsonl(path: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            text = line.strip()
            if not text:
                continue
            try:
                value = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_no}: expected object")
            rows.append(value)
    if len(rows) != 1:
        raise ValueError(f"{path}: expected exactly one function row, found {len(rows)}")
    return rows[0]


def _normalize_address(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
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


def _varnode_key(value: Any) -> tuple[str, str, int] | None:
    if not isinstance(value, dict):
        return None
    space = value.get("space")
    offset = value.get("offset")
    size = value.get("size")
    if not isinstance(space, str) or not isinstance(offset, str) or not isinstance(size, int):
        return None
    return (space, offset.lower(), size)


def _structured_pcode(operation: Any) -> bool:
    return (
        isinstance(operation, dict)
        and isinstance(operation.get("opcode"), str)
        and isinstance(operation.get("text"), str)
        and isinstance(operation.get("inputs"), list)
        and (operation.get("output") is None or isinstance(operation.get("output"), dict))
    )


def _machine_sha(instructions: list[dict[str, Any]]) -> tuple[int, str]:
    machine = bytearray()
    previous = -1
    for ordinal, instruction in enumerate(instructions):
        if not isinstance(instruction, dict):
            raise ValueError(f"instruction {ordinal}: expected object")
        address = _normalize_address(instruction.get("address"))
        numeric = int(address, 16)
        if numeric <= previous:
            raise ValueError("instruction addresses are not strictly increasing")
        previous = numeric
        payload = instruction.get("bytes")
        if not isinstance(payload, str) or not payload or len(payload) % 2:
            raise ValueError(f"{address}: invalid instruction bytes")
        try:
            machine.extend(bytes.fromhex(payload))
        except ValueError as exc:
            raise ValueError(f"{address}: invalid instruction bytes") from exc
    return len(machine), hashlib.sha256(machine).hexdigest()


def _direct_calls(instructions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for ordinal, instruction in enumerate(instructions):
        if str(instruction.get("mnemonic", "")).upper() != "CALL":
            continue
        flows = instruction.get("flows")
        if not isinstance(flows, list):
            raise ValueError(f"instruction {ordinal}: CALL flows must be a list")
        normalized: list[str] = []
        for value in flows:
            normalized.append(_normalize_address(value))
        target = normalized[0] if len(normalized) == 1 else None
        result.append(
            {
                "ordinal": ordinal,
                "instruction": _normalize_address(instruction.get("address")),
                "text": instruction.get("text"),
                "direct_target": target,
                "flows": normalized,
            }
        )
    return result


def _memory_width_from_operand(operand: str) -> str | None:
    lowered = operand.strip().lower()
    for width in ("byte", "word", "dword", "qword", "tword", "xmmword"):
        if lowered.startswith(width + " ptr ["):
            return width
    return None


def _build_pcode_graph(
    instructions: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, list[str]], dict[str, dict[str, Any]]]:
    nodes: list[dict[str, Any]] = []
    last_def: dict[tuple[str, str, int], str] = {}
    edges: dict[str, list[str]] = {}
    node_by_id: dict[str, dict[str, Any]] = {}

    for instruction in instructions:
        address = _normalize_address(instruction.get("address"))
        pcode = instruction.get("pcode")
        if not isinstance(pcode, list):
            raise ValueError(f"{address}: pcode must be a list")
        for op_index, operation in enumerate(pcode):
            if not _structured_pcode(operation):
                raise ValueError(f"{address}: structured p-code varnodes required")
            node_id = f"{address}:{op_index}"
            dependencies: list[str] = []
            for input_value in operation["inputs"]:
                key = _varnode_key(input_value)
                if key is not None and key in last_def:
                    dep = last_def[key]
                    if dep not in dependencies:
                        dependencies.append(dep)
            node = {
                "id": node_id,
                "instruction": address,
                "opcode": str(operation["opcode"]).upper(),
                "text": operation["text"],
                "dependencies": dependencies,
                "output": operation.get("output"),
                "inputs": operation["inputs"],
            }
            nodes.append(node)
            edges[node_id] = dependencies
            node_by_id[node_id] = node
            output_key = _varnode_key(operation.get("output"))
            if output_key is not None:
                last_def[output_key] = node_id
    return nodes, edges, node_by_id


def _dependency_slice(
    root: str,
    edges: dict[str, list[str]],
    node_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    visited: set[str] = set()
    ordered: list[str] = []

    def visit(node_id: str) -> None:
        if node_id in visited:
            return
        visited.add(node_id)
        for dep in edges.get(node_id, []):
            visit(dep)
        ordered.append(node_id)

    visit(root)
    return [
        {
            "id": node_id,
            "instruction": node_by_id[node_id]["instruction"],
            "opcode": node_by_id[node_id]["opcode"],
            "text": node_by_id[node_id]["text"],
        }
        for node_id in ordered
        if node_id in node_by_id
    ]


def _f32_store_candidates(
    instructions: list[dict[str, Any]],
    edges: dict[str, list[str]],
    node_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    store_mnemonics = {"FST", "FSTP", "MOVSS"}
    for ordinal, instruction in enumerate(instructions):
        mnemonic = str(instruction.get("mnemonic", "")).upper()
        if mnemonic not in store_mnemonics:
            continue
        operands = instruction.get("operands")
        pcode = instruction.get("pcode")
        if not isinstance(operands, list) or not isinstance(pcode, list):
            raise ValueError(f"instruction {ordinal}: operands/pcode malformed")
        dword_operands = [
            {"operand_index": index, "operand": operand}
            for index, operand in enumerate(operands)
            if isinstance(operand, str) and _memory_width_from_operand(operand) == "dword"
        ]
        if not dword_operands:
            continue
        store_nodes = []
        address = _normalize_address(instruction.get("address"))
        for op_index, operation in enumerate(pcode):
            if str(operation.get("opcode", "")).upper() == "STORE":
                node_id = f"{address}:{op_index}"
                store_nodes.append(node_id)
        if not store_nodes:
            continue
        for operand in dword_operands:
            candidates.append(
                {
                    "ordinal": ordinal,
                    "instruction": address,
                    "mnemonic": mnemonic,
                    **operand,
                    "store_pcode_nodes": store_nodes,
                    "dependency_slices": [
                        _dependency_slice(node_id, edges, node_by_id)
                        for node_id in store_nodes
                    ],
                    "source_role": None,
                }
            )
    return candidates


def analyze_scalar_provenance(
    instruction_export: Path,
    phase680_report: Path,
) -> dict[str, Any]:
    row = _load_single_jsonl(instruction_export)
    static = _load_json(phase680_report)

    if row.get("format") != INSTRUCTION_FORMAT:
        raise ValueError(f"{instruction_export}: requires {INSTRUCTION_FORMAT}")
    if row.get("found") is not True:
        raise ValueError(f"{instruction_export}: target was not resolved")
    function = row.get("function")
    if not isinstance(function, dict):
        raise ValueError(f"{instruction_export}: function metadata missing")
    if _normalize_address(function.get("address")) != TARGET_ADDRESS:
        raise ValueError(f"{instruction_export}: expected {TARGET_NAME} at {TARGET_ADDRESS}")

    if static.get("format") != STATIC_FORMAT:
        raise ValueError(f"{phase680_report}: requires {STATIC_FORMAT}")
    if static.get("target") != TARGET_NAME or static.get("target_address") != TARGET_ADDRESS:
        raise ValueError(f"{phase680_report}: Phase 680 target identity mismatch")
    if static.get("instruction_freeze_ready") is not True:
        raise ValueError(f"{phase680_report}: Phase 680 instruction freeze is not ready")
    pcode_summary = static.get("pcode_summary")
    if not isinstance(pcode_summary, dict) or pcode_summary.get("structured_varnodes_complete") is not True:
        raise ValueError(f"{phase680_report}: structured p-code varnodes are incomplete")

    instructions = row.get("instructions")
    if not isinstance(instructions, list) or not instructions:
        raise ValueError(f"{instruction_export}: instruction list is empty")
    if row.get("instruction_count") != len(instructions):
        raise ValueError(f"{instruction_export}: instruction_count mismatch")

    byte_count, machine_sha256 = _machine_sha(instructions)
    if static.get("machine_byte_count") != byte_count:
        raise ValueError("Phase 680 machine byte count does not match instruction export")
    if static.get("machine_sha256") != machine_sha256:
        raise ValueError("Phase 680 machine SHA-256 does not match instruction export")

    calls = _direct_calls(instructions)
    sine_calls = [item for item in calls if item["direct_target"] == SINE_TARGET]
    cosine_calls = [item for item in calls if item["direct_target"] == COSINE_TARGET]
    other_calls = [
        item
        for item in calls
        if item["direct_target"] not in {SINE_TARGET, COSINE_TARGET}
    ]

    _nodes, edges, node_by_id = _build_pcode_graph(instructions)
    stores = _f32_store_candidates(instructions, edges, node_by_id)

    blockers: list[dict[str, Any]] = []
    if len(sine_calls) != 1:
        blockers.append(
            {
                "id": "sine-helper-callsite-not-unique",
                "expected_target": SINE_TARGET,
                "call_count": len(sine_calls),
            }
        )
    if len(cosine_calls) != 1:
        blockers.append(
            {
                "id": "cosine-helper-callsite-not-unique",
                "expected_target": COSINE_TARGET,
                "call_count": len(cosine_calls),
            }
        )
    if not stores:
        blockers.append(
            {
                "id": "f32-store-candidates-missing",
                "reason": "no structured dword STORE candidate was recovered",
            }
        )
    blockers.extend(
        [
            {
                "id": "scalar-store-role-mapping-unproven",
                "reason": "machine stores are frozen but none is assigned to one of the four Phase 691 scalar roles without a separate source/machine join",
            },
            {
                "id": "sqrt-helper-identity-unresolved",
                "reason": "the exact machine CALL implementing the recovered sqrt boundary has not yet been joined to a unique callee identity",
                "other_direct_calls": [item["direct_target"] for item in other_calls],
            },
            {
                "id": "call-return-floating-register-provenance-unresolved",
                "reason": "Ghidra CALL p-code does not itself prove the x87/SSE return-register definition consumed after the helper call",
            },
            {
                "id": "ambient-x87-mxcsr-state-unresolved",
                "reason": "precision/rounding state inherited at the FUN_007afdd0 callsite remains outside this instruction-local provenance report",
            },
        ]
    )

    frontier_ready = (
        len(sine_calls) == 1
        and len(cosine_calls) == 1
        and bool(stores)
    )

    return {
        "format": FORMAT,
        "target": TARGET_NAME,
        "target_address": TARGET_ADDRESS,
        "instruction_export": str(instruction_export),
        "phase680_report": str(phase680_report),
        "machine_byte_count": byte_count,
        "machine_sha256": machine_sha256,
        "direct_calls": calls,
        "helper_calls": {
            "sine": {"target": SINE_TARGET, "calls": sine_calls},
            "cosine": {"target": COSINE_TARGET, "calls": cosine_calls},
            "other": other_calls,
        },
        "f32_store_candidates": stores,
        "source_scalar_boundaries": [
            {"role": role, "assigned_store_candidate": None}
            for role in SCALAR_BOUNDARY_ROLES
        ],
        "scalar_provenance_frontier_ready": frontier_ready,
        "machine_scalar_production_ready": False,
        "host_libm_substitution_allowed": False,
        "blockers": blockers,
        "scope": {
            "source_role_assignment_by_address_assumed": False,
            "sqrt_callee_identity_assumed": False,
            "trig_helper_semantics_reimplemented": False,
            "original_game_executed": False,
            "runtime_capture_required": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("phase680_report", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = analyze_scalar_provenance(args.instruction_export, args.phase680_report)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
