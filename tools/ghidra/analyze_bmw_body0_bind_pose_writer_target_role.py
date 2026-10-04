#!/usr/bin/env python3
"""Prove which physical FUN_007b7840 ABI parameter targets the persistent BODY pose record.

This is a deliberately narrow semantic-role pass.  It consumes the physical ABI
join plus one targeted ``SHIFT.GhidraFunctionInstructions/2`` row for
``FUN_007b7840`` and reuses the existing all-path IA-32 register provenance
engine.  A parameter is promoted to the BODY-record target role only when one
exact entry register parameter accounts for complete writes to every persistent
BODY origin and basis byte and no competing/unresolved object-base write touches
those lanes.

The pass does not infer BODY0 identity at any caller, does not name stack/source
parameters from ordinal or Ghidra types, and does not construct a bind matrix.
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

import analyze_bmw_body0_bind_callsite_register_provenance as _callsite
import analyze_register_relative_accesses as _access

FORMAT = "SHIFT.BMWBody0BindPoseWriterTargetRole/1"
ABI_FORMAT = "SHIFT.BMWBody0BindPoseWriterABI/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"
POSE_WRITER = "0x007b7840"

ORIGIN_FIELDS = ((0x00, 8), (0x08, 8), (0x10, 8))
BASIS_FIELDS = (
    (0xD4, 4), (0xD8, 4), (0xDC, 4),
    (0xE0, 4), (0xE4, 4), (0xE8, 4),
    (0xEC, 4), (0xF0, 4), (0xF4, 4),
)
POSE_FIELDS = ORIGIN_FIELDS + BASIS_FIELDS
_REQUIRED_BYTES = frozenset(
    byte
    for offset, size in POSE_FIELDS
    for byte in range(offset, offset + size)
)
_TRACKED = tuple(_callsite._TRACKED)
_FRAME_BASES = {"EBP", "ESP"}


def _load_json(path: Path, expected_format: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(value, dict) or value.get("format") != expected_format:
        raise ValueError(f"{path}: expected {expected_format}")
    return value


def _read_single_instruction_row(path: Path) -> dict[str, Any]:
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
    if len(rows) != 1:
        raise ValueError(f"{path}: expected exactly one targeted instruction row; found {len(rows)}")
    return rows[0]


def _validate_abi(report: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    if report.get("format") != ABI_FORMAT:
        raise ValueError(f"expected {ABI_FORMAT}")
    pose_writer = report.get("pose_writer")
    if not isinstance(pose_writer, dict):
        raise ValueError("pose_writer metadata missing")
    if _callsite._address(pose_writer.get("address"), field="pose_writer.address") != POSE_WRITER:
        raise ValueError("pose-writer target drift")
    parameters = pose_writer.get("parameters")
    if not isinstance(parameters, list) or not parameters:
        raise ValueError("pose_writer.parameters missing")

    handoff = report.get("handoff")
    if not isinstance(handoff, dict):
        raise ValueError("ABI handoff missing")
    if handoff.get("pose_writer_parameter_storage_binding_ready") is not True:
        raise ValueError("pose-writer parameter storage is not ready")
    for key in (
        "pose_writer_ABI_semantic_roles_ready",
        "BODY0_pointer_at_bind_callsite_ready",
        "BODY0_bind_origin_basis_values_ready",
        "BODY0_bind_frame_proof_ready",
    ):
        if handoff.get(key) is not False:
            raise ValueError(f"upstream ABI unexpectedly preclaims {key}")

    normalized: list[dict[str, Any]] = []
    register_parameters: dict[str, dict[str, Any]] = {}
    seen_ordinals: set[int] = set()
    for index, parameter in enumerate(parameters):
        if not isinstance(parameter, dict):
            raise ValueError(f"pose_writer.parameters[{index}] must be an object")
        ordinal = parameter.get("ordinal")
        if not isinstance(ordinal, int) or ordinal < 0:
            raise ValueError(f"pose_writer.parameters[{index}].ordinal invalid")
        if ordinal in seen_ordinals:
            raise ValueError(f"duplicate parameter ordinal {ordinal}")
        seen_ordinals.add(ordinal)
        kind = parameter.get("kind")
        if kind not in {"register", "stack"}:
            raise ValueError(f"parameter {ordinal}: unsupported storage kind {kind!r}")
        row = dict(parameter)
        row["ordinal"] = ordinal
        normalized.append(row)
        if kind == "register":
            parent = parameter.get("tracked_parent_register")
            if not isinstance(parent, str):
                raise ValueError(f"parameter {ordinal}: tracked_parent_register missing")
            parent = parent.upper()
            if parent not in _TRACKED:
                raise ValueError(f"parameter {ordinal}: unsupported tracked register {parent}")
            if parent in register_parameters:
                raise ValueError(f"duplicate register-backed parameter storage {parent}")
            register_parameters[parent] = row

    if not register_parameters:
        raise ValueError("pose writer has no register-backed parameter to analyze")
    normalized.sort(key=lambda row: row["ordinal"])
    return normalized, register_parameters


def _store_width(pcode: Any) -> int | None:
    if not isinstance(pcode, list):
        raise ValueError("instruction pcode must be a list")
    sizes: list[int] = []
    for operation in pcode:
        if not isinstance(operation, dict):
            raise ValueError("pcode operation must be an object")
        if str(operation.get("opcode") or "").upper() != "STORE":
            continue
        inputs = operation.get("inputs")
        if not isinstance(inputs, list) or len(inputs) < 3:
            return None
        value = inputs[2]
        if not isinstance(value, dict):
            return None
        size = value.get("size")
        if not isinstance(size, int) or size <= 0:
            return None
        sizes.append(size)
    if not sizes:
        return None
    unique = set(sizes)
    return unique.pop() if len(unique) == 1 else None


def _required_intersection(offset: int, size: int) -> list[int]:
    return sorted(set(range(offset, offset + size)) & set(_REQUIRED_BYTES))


def _field_coverage(bytes_written: set[int], fields: tuple[tuple[int, int], ...]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for offset, size in fields:
        required = set(range(offset, offset + size))
        covered = sorted(required & bytes_written)
        result.append(
            {
                "offset": offset,
                "offset_hex": f"0x{offset:x}",
                "size": size,
                "covered_byte_count": len(covered),
                "complete": required <= bytes_written,
            }
        )
    return result


def analyze_bmw_body0_bind_pose_writer_target_role(
    abi_path: Path,
    instruction_export: Path,
) -> dict[str, Any]:
    abi = _load_json(abi_path, ABI_FORMAT)
    parameters, register_parameters = _validate_abi(abi)

    row = _read_single_instruction_row(instruction_export)
    function_address, instructions = _callsite._validate_instruction_row(row, instruction_export)
    if function_address != POSE_WRITER:
        raise ValueError(f"{instruction_export}: expected targeted {POSE_WRITER} row")
    if row.get("format") != INSTRUCTION_FORMAT:
        raise ValueError(f"{instruction_export}: expected {INSTRUCTION_FORMAT}")

    incoming, fixed_point_iterations = _callsite._analyze_incoming_states(instructions)

    parameter_bytes: dict[int, set[int]] = {
        parameter["ordinal"]: set() for parameter in parameters if parameter.get("kind") == "register"
    }
    witnesses: list[dict[str, Any]] = []
    unresolved_pose_writes: list[dict[str, Any]] = []
    ignored_frame_writes: list[dict[str, Any]] = []

    for instruction in instructions:
        address = _callsite._address(instruction.get("address"), field="instruction.address")
        state = incoming.get(address)
        if state is None:
            continue
        pcode = instruction.get("pcode")
        width = _store_width(pcode)
        if width is None:
            continue
        operands = instruction.get("operands")
        if not isinstance(operands, list):
            raise ValueError(f"{address}: operands missing")
        memory_operands: list[tuple[int, str, tuple[str, int]]] = []
        for operand_index, operand in enumerate(operands):
            if not isinstance(operand, str):
                raise ValueError(f"{address}: operand must be a string")
            parsed = _access._parse_memory_operand(operand)
            if parsed is not None:
                memory_operands.append((operand_index, operand, parsed))
        # IA-32 instructions relevant to this proof should expose one memory
        # destination. Multiple parseable memory operands make STORE ownership
        # ambiguous, so fail closed for the affected pose bytes.
        if len(memory_operands) != 1:
            continue

        operand_index, operand, (base_register, displacement) = memory_operands[0]
        touched = _required_intersection(displacement, width)
        if not touched:
            continue
        if base_register in _FRAME_BASES:
            ignored_frame_writes.append(
                {
                    "instruction": address,
                    "instruction_text": instruction.get("text"),
                    "operand_index": operand_index,
                    "operand": operand,
                    "base_register": base_register,
                    "displacement": displacement,
                    "store_width": width,
                    "required_bytes_touched": touched,
                    "reason": "frame-base-memory-is-not-object-parameter-evidence",
                }
            )
            continue
        if base_register not in state:
            unresolved_pose_writes.append(
                {
                    "instruction": address,
                    "operand": operand,
                    "base_register": base_register,
                    "required_bytes_touched": touched,
                    "origins": [],
                    "reason": "base-register-not-tracked",
                }
            )
            continue

        origins = _callsite._register_engine._sorted_origins(state[base_register])
        parameter = None
        if len(origins) == 1 and origins[0].startswith("entry:"):
            entry_register = origins[0].split(":", 1)[1].upper()
            parameter = register_parameters.get(entry_register)
        if parameter is None:
            unresolved_pose_writes.append(
                {
                    "instruction": address,
                    "instruction_text": instruction.get("text"),
                    "operand_index": operand_index,
                    "operand": operand,
                    "base_register": base_register,
                    "displacement": displacement,
                    "store_width": width,
                    "required_bytes_touched": touched,
                    "origins": origins,
                    "reason": "object-base-origin-is-not-one-exact-entry-parameter",
                }
            )
            continue

        ordinal = int(parameter["ordinal"])
        parameter_bytes[ordinal].update(touched)
        witnesses.append(
            {
                "instruction": address,
                "instruction_text": instruction.get("text"),
                "operand_index": operand_index,
                "operand": operand,
                "base_register": base_register,
                "base_origins": origins,
                "parameter_ordinal": ordinal,
                "parameter_storage": parameter.get("storage"),
                "displacement": displacement,
                "displacement_hex": f"0x{displacement:x}" if displacement >= 0 else f"-0x{-displacement:x}",
                "store_width": width,
                "required_bytes_touched": touched,
                "pcode_store_proven": True,
            }
        )

    coverage_rows: list[dict[str, Any]] = []
    full_candidates: list[dict[str, Any]] = []
    touching_ordinals: list[int] = []
    for parameter in parameters:
        if parameter.get("kind") != "register":
            continue
        ordinal = int(parameter["ordinal"])
        written = parameter_bytes[ordinal]
        if written:
            touching_ordinals.append(ordinal)
        origin_coverage = _field_coverage(written, ORIGIN_FIELDS)
        basis_coverage = _field_coverage(written, BASIS_FIELDS)
        complete = _REQUIRED_BYTES <= written
        row_coverage = {
            "parameter_ordinal": ordinal,
            "parameter_storage": parameter.get("storage"),
            "tracked_parent_register": parameter.get("tracked_parent_register"),
            "required_byte_count": len(_REQUIRED_BYTES),
            "covered_required_byte_count": len(written & set(_REQUIRED_BYTES)),
            "origin_fields": origin_coverage,
            "basis_fields": basis_coverage,
            "complete_origin_basis_write_coverage": complete,
        }
        coverage_rows.append(row_coverage)
        if complete:
            full_candidates.append(row_coverage)

    candidate = full_candidates[0] if len(full_candidates) == 1 else None
    candidate_ordinal = None if candidate is None else int(candidate["parameter_ordinal"])
    competing = [ordinal for ordinal in touching_ordinals if ordinal != candidate_ordinal]
    ready = bool(
        candidate is not None
        and not competing
        and not unresolved_pose_writes
    )

    blockers: list[dict[str, Any]] = []
    if not ready:
        if len(full_candidates) == 0:
            blockers.append(
                {
                    "id": "pose-writer-complete-origin-basis-target-coverage-missing",
                    "evidence_state": "blocked",
                    "required_evidence": (
                        "one exact register-backed ABI parameter must account for STORE coverage of every "
                        "persistent BODY origin and basis byte in FUN_007b7840"
                    ),
                }
            )
        elif len(full_candidates) > 1:
            blockers.append(
                {
                    "id": "pose-writer-multiple-complete-target-parameter-candidates",
                    "evidence_state": "ambiguous",
                    "parameter_ordinals": [row["parameter_ordinal"] for row in full_candidates],
                }
            )
        if competing:
            blockers.append(
                {
                    "id": "pose-writer-competing-entry-parameter-pose-writes",
                    "evidence_state": "ambiguous",
                    "parameter_ordinals": competing,
                }
            )
        if unresolved_pose_writes:
            blockers.append(
                {
                    "id": "pose-writer-unresolved-object-base-pose-writes",
                    "evidence_state": "blocked",
                    "write_count": len(unresolved_pose_writes),
                    "required_evidence": (
                        "resolve every non-frame base touching persistent origin/basis lanes to one exact entry parameter or prove it is unrelated"
                    ),
                }
            )

    blockers.extend(
        [
            {
                "id": "BODY0-target-parameter-callsite-value-join-unproven",
                "evidence_state": "unknown",
                "required_evidence": (
                    "join the proven FUN_007b7840 target parameter value at the selected initialization callsite to exact BMW chassis BODY 0"
                ),
            },
            {
                "id": "bind-origin-basis-source-parameter-semantics-unproven",
                "evidence_state": "unknown",
                "required_evidence": (
                    "trace the values written into the target origin/basis lanes, including stack/x87 producers, without inferring roles from parameter names or ordinals"
                ),
            },
        ]
    )

    target_parameter = None
    if ready and candidate is not None:
        parameter = next(
            row for row in parameters if int(row["ordinal"]) == int(candidate["parameter_ordinal"])
        )
        target_parameter = {
            "ordinal": parameter["ordinal"],
            "storage": parameter.get("storage"),
            "storage_kind": parameter.get("kind"),
            "tracked_parent_register": parameter.get("tracked_parent_register"),
            "semantic_role": "persistent_BODY_pose_record_target",
            "semantic_role_proven": True,
            "proof_basis": "complete-origin-basis-STORE-coverage-with-all-path-entry-register-provenance",
        }

    return {
        "format": FORMAT,
        "inputs": {
            "pose_writer_ABI": str(abi_path),
            "pose_writer_instruction_export": str(instruction_export),
        },
        "target": {
            "pose_writer": POSE_WRITER,
            "persistent_BODY_record_size": 0x170,
            "origin_offsets": [f"0x{offset:x}" for offset, _ in ORIGIN_FIELDS],
            "basis_offsets": [f"0x{offset:x}" for offset, _ in BASIS_FIELDS],
        },
        "analysis": {
            "fixed_point_iterations": fixed_point_iterations,
            "reachable_instruction_count": len(incoming),
            "function_instruction_count": len(instructions),
            "required_pose_byte_count": len(_REQUIRED_BYTES),
            "parameter_pose_write_coverage": coverage_rows,
            "full_coverage_parameter_ordinals": [row["parameter_ordinal"] for row in full_candidates],
            "entry_parameter_pose_write_ordinals": touching_ordinals,
            "pose_write_witnesses": witnesses,
            "unresolved_pose_writes": unresolved_pose_writes,
            "ignored_frame_writes": ignored_frame_writes,
        },
        "handoff": {
            "pose_writer_BODY_target_parameter_ready": ready,
            "pose_writer_BODY_target_parameter": target_parameter,
            "pose_writer_ABI_semantic_roles_ready": False,
            "BODY0_pointer_at_bind_callsite_ready": False,
            "BODY0_bind_origin_basis_values_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "next_required_join": (
                "target-parameter callsite value -> BMW chassis BODY0, then origin/basis source-value semantics"
                if ready
                else "complete FUN_007b7840 target-parameter role proof from exact machine/p-code writes"
            ),
        },
        "blockers": blockers,
        "scope": {
            "all_path_register_provenance_reused": True,
            "structured_pcode_STORE_required": True,
            "persistent_BODY_origin_basis_layout_reused": True,
            "frame_base_memory_used_as_object_evidence": False,
            "parameter_name_used_as_semantic_role": False,
            "parameter_type_used_as_semantic_role": False,
            "parameter_ordinal_used_as_semantic_role": False,
            "stack_parameter_target_role_inferred": False,
            "source_origin_basis_parameter_roles_proven": False,
            "pose_writer_candidate_promoted_to_bind_initializer": False,
            "BODY0_pointer_identity_proven": False,
            "BODY0_bind_matrix_proven": False,
            "original_game_executed": False,
            "new_runtime_capture_required": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pose_writer_abi", type=Path)
    parser.add_argument("pose_writer_instruction_export", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = analyze_bmw_body0_bind_pose_writer_target_role(
        args.pose_writer_abi,
        args.pose_writer_instruction_export,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
