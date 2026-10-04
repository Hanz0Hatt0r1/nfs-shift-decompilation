from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_bmw_body0_bind_pose_writer_target_role.py"


def _module():
    spec = importlib.util.spec_from_file_location("body0_bind_pose_writer_target_role", TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")
    return path


def _write_jsonl(path: Path, rows: list[dict]) -> Path:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return path


def _varnode(text: str, size: int, *, register: bool = False) -> dict:
    return {
        "text": text,
        "space": "register" if register else "unique",
        "offset": "0x0",
        "size": size,
        "constant": False,
        "register": register,
        "unique": not register,
    }


def _pcode_store(size: int = 4) -> list[dict]:
    return [
        {
            "opcode": "STORE",
            "text": "STORE ram, ptr, value",
            "output": None,
            "inputs": [
                _varnode("ram", 4),
                _varnode("ptr", 4),
                _varnode("value", size),
            ],
        }
    ]


def _pcode_copy(register: str) -> list[dict]:
    return [
        {
            "opcode": "COPY",
            "text": f"{register} = COPY source",
            "output": _varnode(register, 4, register=True),
            "inputs": [_varnode("source", 4)],
        }
    ]


def _ins(
    address: int,
    mnemonic: str,
    operands: list[str],
    *,
    fallthrough: int | None,
    pcode: list[dict] | None = None,
    flows: list[str] | None = None,
    flow_type: str | None = None,
) -> dict:
    if flow_type is None:
        flow_type = "TERMINATOR" if mnemonic == "RET" else "FALL_THROUGH"
    return {
        "address": f"0x{address:08x}",
        "bytes": "90",
        "mnemonic": mnemonic,
        "text": mnemonic + (" " + ", ".join(operands) if operands else ""),
        "operands": operands,
        "fallthrough": None if fallthrough is None else f"0x{fallthrough:08x}",
        "flows": [] if flows is None else flows,
        "flow_type": flow_type,
        "references": [],
        "pcode": [] if pcode is None else pcode,
    }


def _abi(m) -> dict:
    return {
        "format": m.ABI_FORMAT,
        "pose_writer": {
            "address": m.POSE_WRITER,
            "name": "FUN_007b7840",
            "calling_convention": "__thiscall",
            "parameter_count": 3,
            "register_parameter_count": 2,
            "stack_parameter_count": 1,
            "parameters": [
                {
                    "ordinal": 0,
                    "reported_name": "param_0",
                    "reported_type": "void *",
                    "kind": "register",
                    "storage": "ECX:4 (auto)",
                    "register": "ECX",
                    "tracked_parent_register": "ECX",
                    "size": 4,
                    "auto": True,
                    "reported_name_used_as_semantic_role": False,
                    "reported_type_used_as_semantic_role": False,
                },
                {
                    "ordinal": 1,
                    "reported_name": "param_1",
                    "reported_type": "void *",
                    "kind": "register",
                    "storage": "EDX:4",
                    "register": "EDX",
                    "tracked_parent_register": "EDX",
                    "size": 4,
                    "auto": False,
                    "reported_name_used_as_semantic_role": False,
                    "reported_type_used_as_semantic_role": False,
                },
                {
                    "ordinal": 2,
                    "reported_name": "param_2",
                    "reported_type": "float *",
                    "kind": "stack",
                    "storage": "Stack[0x4]:4",
                    "stack_offset": 4,
                    "stack_offset_hex": "0x4",
                    "size": 4,
                    "auto": False,
                    "reported_name_used_as_semantic_role": False,
                    "reported_type_used_as_semantic_role": False,
                },
            ],
            "reported_parameter_names_used_as_semantic_roles": False,
            "reported_parameter_types_used_as_semantic_roles": False,
        },
        "analysis": {
            "callsite_count": 1,
            "callsites": [],
            "all_callsites_parameter_storage_bound": True,
            "all_register_parameter_values_ready": True,
            "stack_value_worklist": [
                {
                    "stack_offset": 4,
                    "stack_offset_hex": "0x4",
                    "size": 4,
                    "storage": "Stack[0x4]:4",
                    "value_provenance_required_at_every_relevant_callsite": True,
                }
            ],
        },
        "handoff": {
            "pose_writer_parameter_storage_binding_ready": True,
            "pose_writer_register_argument_provenance_ready": True,
            "pose_writer_stack_argument_locations_ready": True,
            "pose_writer_stack_argument_values_ready": False,
            "pose_writer_ABI_semantic_roles_ready": False,
            "BODY0_pointer_at_bind_callsite_ready": False,
            "BODY0_bind_origin_basis_values_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "next_required_join": "path-aware stack-value provenance + FUN_007b7840 parameter role proof",
        },
        "blockers": [],
        "scope": {
            "parameter_ordinal_used_as_semantic_role": False,
            "BODY0_pointer_identity_proven": False,
            "BODY0_bind_matrix_proven": False,
        },
    }


def _pose_write_offsets() -> list[int]:
    # Split f64 origin lanes into 4-byte STORE witnesses and retain native f32
    # widths for every basis lane.  Byte coverage, not one instruction per field,
    # is the proof criterion.
    return [0x00, 0x04, 0x08, 0x0C, 0x10, 0x14] + [
        0xD4, 0xD8, 0xDC,
        0xE0, 0xE4, 0xE8,
        0xEC, 0xF0, 0xF4,
    ]


def _instruction_row(
    m,
    *,
    omit_offset: int | None = None,
    competing_offset: int | None = None,
    derived_base: bool = False,
    frame_write_offset: int | None = None,
) -> dict:
    instructions: list[dict] = []
    address = int(m.POSE_WRITER, 16)

    # Track the object base through a non-ABI temporary so the proof must use the
    # existing all-path register engine rather than lexical register identity.
    next_address = address + 1
    if derived_base:
        instructions.append(
            _ins(
                address,
                "LEA",
                ["EAX", "[ECX + 0x4]"],
                fallthrough=next_address,
                pcode=_pcode_copy("EAX"),
            )
        )
    else:
        instructions.append(
            _ins(
                address,
                "MOV",
                ["EAX", "ECX"],
                fallthrough=next_address,
                pcode=_pcode_copy("EAX"),
            )
        )
    address = next_address

    offsets = [value for value in _pose_write_offsets() if value != omit_offset]
    for offset in offsets:
        next_address = address + 1
        instructions.append(
            _ins(
                address,
                "MOV",
                [f"[EAX + 0x{offset:x}]", "EBX"],
                fallthrough=next_address,
                pcode=_pcode_store(4),
            )
        )
        address = next_address

    if competing_offset is not None:
        next_address = address + 1
        instructions.append(
            _ins(
                address,
                "MOV",
                [f"[EDX + 0x{competing_offset:x}]", "EBX"],
                fallthrough=next_address,
                pcode=_pcode_store(4),
            )
        )
        address = next_address

    if frame_write_offset is not None:
        next_address = address + 1
        instructions.append(
            _ins(
                address,
                "MOV",
                [f"[EBP + 0x{frame_write_offset:x}]", "EBX"],
                fallthrough=next_address,
                pcode=_pcode_store(4),
            )
        )
        address = next_address

    instructions.append(
        _ins(
            address,
            "RET",
            [],
            fallthrough=None,
            pcode=[],
            flow_type="TERMINATOR",
        )
    )

    return {
        "format": m.INSTRUCTION_FORMAT,
        "program": "SHIFT.exe",
        "requested": m.POSE_WRITER,
        "found": True,
        "function": {
            "address": m.POSE_WRITER,
            "name": "FUN_007b7840",
            "size": len(instructions),
            "calling_convention": "__thiscall",
        },
        "instruction_count": len(instructions),
        "instructions": instructions,
    }


def _analyze(tmp_path: Path, **row_kwargs):
    m = _module()
    abi_path = _write_json(tmp_path / "abi.json", _abi(m))
    instructions_path = _write_jsonl(
        tmp_path / "instructions.jsonl",
        [_instruction_row(m, **row_kwargs)],
    )
    return m, m.analyze_bmw_body0_bind_pose_writer_target_role(
        abi_path, instructions_path
    )


def test_proves_one_register_backed_target_from_complete_pose_write_coverage(tmp_path: Path) -> None:
    m, report = _analyze(tmp_path, frame_write_offset=0xD4)

    assert report["format"] == m.FORMAT
    handoff = report["handoff"]
    assert handoff["pose_writer_BODY_target_parameter_ready"] is True
    target = handoff["pose_writer_BODY_target_parameter"]
    assert target == {
        "ordinal": 0,
        "storage": "ECX:4 (auto)",
        "storage_kind": "register",
        "tracked_parent_register": "ECX",
        "semantic_role": "persistent_BODY_pose_record_target",
        "semantic_role_proven": True,
        "proof_basis": "complete-origin-basis-STORE-coverage-with-all-path-entry-register-provenance",
    }
    assert report["analysis"]["full_coverage_parameter_ordinals"] == [0]
    assert report["analysis"]["entry_parameter_pose_write_ordinals"] == [0]
    assert report["analysis"]["unresolved_pose_writes"] == []
    assert len(report["analysis"]["ignored_frame_writes"]) == 1

    # This phase proves one target-role only; it must not skip the caller/value
    # or source-value joins needed for a real BODY0 bind matrix.
    assert handoff["pose_writer_ABI_semantic_roles_ready"] is False
    assert handoff["BODY0_pointer_at_bind_callsite_ready"] is False
    assert handoff["BODY0_bind_origin_basis_values_ready"] is False
    assert handoff["BODY0_bind_frame_proof_ready"] is False
    blocker_ids = {row["id"] for row in report["blockers"]}
    assert "BODY0-target-parameter-callsite-value-join-unproven" in blocker_ids
    assert "bind-origin-basis-source-parameter-semantics-unproven" in blocker_ids


def test_missing_one_required_pose_lane_keeps_target_role_blocked(tmp_path: Path) -> None:
    _, report = _analyze(tmp_path, omit_offset=0xF4)

    assert report["handoff"]["pose_writer_BODY_target_parameter_ready"] is False
    assert report["analysis"]["full_coverage_parameter_ordinals"] == []
    blocker_ids = {row["id"] for row in report["blockers"]}
    assert "pose-writer-complete-origin-basis-target-coverage-missing" in blocker_ids


def test_competing_entry_parameter_pose_write_is_ambiguous(tmp_path: Path) -> None:
    _, report = _analyze(tmp_path, competing_offset=0xD4)

    assert report["handoff"]["pose_writer_BODY_target_parameter_ready"] is False
    assert report["analysis"]["full_coverage_parameter_ordinals"] == [0]
    assert report["analysis"]["entry_parameter_pose_write_ordinals"] == [0, 1]
    blocker_ids = {row["id"] for row in report["blockers"]}
    assert "pose-writer-competing-entry-parameter-pose-writes" in blocker_ids


def test_derived_object_base_is_not_promoted_to_entry_parameter(tmp_path: Path) -> None:
    _, report = _analyze(tmp_path, derived_base=True)

    assert report["handoff"]["pose_writer_BODY_target_parameter_ready"] is False
    assert report["analysis"]["full_coverage_parameter_ordinals"] == []
    assert report["analysis"]["unresolved_pose_writes"]
    blocker_ids = {row["id"] for row in report["blockers"]}
    assert "pose-writer-unresolved-object-base-pose-writes" in blocker_ids


def test_rejects_upstream_semantic_preclaim(tmp_path: Path) -> None:
    m = _module()
    abi = _abi(m)
    abi["handoff"]["BODY0_pointer_at_bind_callsite_ready"] = True
    abi_path = _write_json(tmp_path / "abi.json", abi)
    instructions_path = _write_jsonl(
        tmp_path / "instructions.jsonl",
        [_instruction_row(m)],
    )

    with pytest.raises(ValueError, match="unexpectedly preclaims BODY0_pointer_at_bind_callsite_ready"):
        m.analyze_bmw_body0_bind_pose_writer_target_role(abi_path, instructions_path)


def test_rejects_wrong_target_instruction_row(tmp_path: Path) -> None:
    m = _module()
    abi_path = _write_json(tmp_path / "abi.json", _abi(m))
    row = _instruction_row(m)
    row["requested"] = "0x007b7000"
    row["function"]["address"] = "0x007b7000"
    row["function"]["name"] = "FUN_007b7000"
    row["instructions"][0]["address"] = "0x007b7000"
    instructions_path = _write_jsonl(tmp_path / "instructions.jsonl", [row])

    with pytest.raises(ValueError, match="expected targeted 0x007b7840 row"):
        m.analyze_bmw_body0_bind_pose_writer_target_role(abi_path, instructions_path)
