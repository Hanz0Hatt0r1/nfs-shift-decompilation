from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_bmw_body0_bind_pose_writer_value_provenance.py"


def _module():
    spec = importlib.util.spec_from_file_location("body0_bind_pose_writer_value_provenance", TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _varnode(
    text: str,
    *,
    space: str = "register",
    offset: str = "0x0",
    size: int = 4,
    constant: bool = False,
    register: bool | None = None,
    unique: bool | None = None,
) -> dict:
    if register is None:
        register = space == "register"
    if unique is None:
        unique = space == "unique"
    return {
        "text": text,
        "space": space,
        "offset": offset,
        "size": size,
        "constant": constant,
        "register": register,
        "unique": unique,
    }


def _pcode(opcode: str, text: str, *, output=None, inputs=None) -> dict:
    return {
        "opcode": opcode,
        "text": text,
        "output": output,
        "inputs": [] if inputs is None else inputs,
    }


def _instruction(
    address: int,
    mnemonic: str,
    operands: list[str],
    pcode: list[dict],
    *,
    fallthrough: int | None,
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
        "flow_type": flow_type,
        "fallthrough": None if fallthrough is None else f"0x{fallthrough:08x}",
        "flows": [] if flows is None else flows,
        "references": [],
        "pcode": pcode,
    }


def _pose_offsets() -> list[int]:
    return [0x00, 0x04, 0x08, 0x0C, 0x10, 0x14] + [
        0xD4, 0xD8, 0xDC,
        0xE0, 0xE4, 0xE8,
        0xEC, 0xF0, 0xF4,
    ]


def _target_role(m, store_addresses: dict[int, str]) -> dict:
    witnesses = []
    for offset in _pose_offsets():
        witnesses.append(
            {
                "instruction": store_addresses[offset],
                "instruction_text": f"STORE +0x{offset:x}",
                "operand_index": 0,
                "operand": f"[EAX + 0x{offset:x}]",
                "base_register": "EAX",
                "base_origins": ["entry:ECX"],
                "parameter_ordinal": 0,
                "parameter_storage": "ECX:4 (auto)",
                "displacement": offset,
                "displacement_hex": f"0x{offset:x}",
                "store_width": 4,
                "required_bytes_touched": list(range(offset, offset + 4)),
                "pcode_store_proven": True,
            }
        )
    # The origin layout is f64, so paired 4-byte witnesses jointly cover each
    # exact persistent lane. Basis fields are one 4-byte witness each.
    required = set(m._target._REQUIRED_BYTES)
    assert {value for row in witnesses for value in row["required_bytes_touched"]} == required
    return {
        "format": m.TARGET_ROLE_FORMAT,
        "target": {
            "pose_writer": m.POSE_WRITER,
            "persistent_BODY_record_size": 0x170,
            "origin_offsets": ["0x0", "0x8", "0x10"],
            "basis_offsets": ["0xd4", "0xd8", "0xdc", "0xe0", "0xe4", "0xe8", "0xec", "0xf0", "0xf4"],
        },
        "analysis": {
            "required_pose_byte_count": len(required),
            "full_coverage_parameter_ordinals": [0],
            "entry_parameter_pose_write_ordinals": [0],
            "pose_write_witnesses": witnesses,
            "unresolved_pose_writes": [],
            "ignored_frame_writes": [],
        },
        "handoff": {
            "pose_writer_BODY_target_parameter_ready": True,
            "pose_writer_BODY_target_parameter": {
                "ordinal": 0,
                "storage": "ECX:4 (auto)",
                "storage_kind": "register",
                "tracked_parent_register": "ECX",
                "semantic_role": "persistent_BODY_pose_record_target",
                "semantic_role_proven": True,
                "proof_basis": "complete-origin-basis-STORE-coverage-with-all-path-entry-register-provenance",
            },
            "pose_writer_ABI_semantic_roles_ready": False,
            "BODY0_pointer_at_bind_callsite_ready": False,
            "BODY0_bind_origin_basis_values_ready": False,
            "BODY0_bind_frame_proof_ready": False,
        },
        "blockers": [],
        "scope": {"BODY0_bind_matrix_proven": False},
    }


def _fixture(m, *, duplicate_store_at: int | None = None, memory_source: bool = False):
    ram = _varnode(
        "ram", space="const", offset="0x1", constant=True, register=False, unique=False
    )
    eax = _varnode("EAX", offset="0x10")
    edx = _varnode("EDX", offset="0x20")
    ebp = _varnode("EBP", offset="0x30")
    ebx = _varnode("EBX", offset="0x40")
    st0 = _varnode("ST0", offset="0x100", size=10)
    loaded = _varnode(
        "unique:200", space="unique", offset="0x200", register=False, unique=True
    )
    call_target = _varnode(
        "0x00909990",
        space="const",
        offset="0x909990",
        constant=True,
        register=False,
        unique=False,
    )

    instructions: list[dict] = []
    address = int(m.POSE_WRITER, 16)
    next_address = address + 1
    if memory_source:
        instructions.append(
            _instruction(
                address,
                "MOV",
                ["EBX", "[EBP + 0x8]"],
                [
                    _pcode("LOAD", "unique:200 = LOAD ram, EBP", output=loaded, inputs=[ram, ebp]),
                    _pcode("COPY", "EBX = COPY unique:200", output=ebx, inputs=[loaded]),
                ],
                fallthrough=next_address,
            )
        )
    else:
        instructions.append(
            _instruction(
                address,
                "MOV",
                ["EBX", "EDX"],
                [_pcode("COPY", "EBX = COPY EDX", output=ebx, inputs=[edx])],
                fallthrough=next_address,
            )
        )
    address = next_address

    store_addresses: dict[int, str] = {}
    for offset in _pose_offsets():
        if offset == 0xD4:
            next_address = address + 1
            instructions.append(
                _instruction(
                    address,
                    "CALL",
                    ["0x00909990"],
                    [_pcode("CALL", "CALL 0x00909990", inputs=[call_target])],
                    fallthrough=next_address,
                    flows=["0x00909990"],
                    flow_type="UNCONDITIONAL_CALL",
                )
            )
            address = next_address
            source = st0
            mnemonic = "FSTP"
        else:
            source = ebx
            mnemonic = "MOV"

        next_address = address + 1
        store_pcode = [_pcode("STORE", "STORE ram, EAX, value", inputs=[ram, eax, source])]
        if duplicate_store_at == offset:
            store_pcode.append(
                _pcode("STORE", "STORE ram, EAX, value duplicate", inputs=[ram, eax, source])
            )
        instructions.append(
            _instruction(
                address,
                mnemonic,
                [f"[EAX + 0x{offset:x}]", "ST0" if source is st0 else "EBX"],
                store_pcode,
                fallthrough=next_address,
            )
        )
        store_addresses[offset] = f"0x{address:08x}"
        address = next_address

    instructions.append(
        _instruction(
            address,
            "RET",
            [],
            [_pcode("RETURN", "RETURN", inputs=[])],
            fallthrough=None,
            flow_type="TERMINATOR",
        )
    )
    row = {
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
    return row, store_addresses


def _run(tmp_path: Path, **fixture_kwargs):
    m = _module()
    row, store_addresses = _fixture(m, **fixture_kwargs)
    target_path = tmp_path / "target.json"
    target_path.write_text(json.dumps(_target_role(m, store_addresses)) + "\n", encoding="utf-8")
    instruction_path = tmp_path / "instructions.jsonl"
    instruction_path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    return m, m.analyze_bmw_body0_bind_pose_writer_value_provenance(
        target_path, instruction_path
    )


def test_builds_value_only_dependency_frontier_without_promoting_bind_values(tmp_path: Path) -> None:
    m, report = _run(tmp_path)

    assert report["format"] == m.FORMAT
    assert report["analysis"]["analyzed_pose_store_count"] == 15
    assert report["analysis"]["all_target_role_pose_stores_analyzed"] is True
    assert report["handoff"]["pose_writer_pose_store_value_dependency_frontier_ready"] is True
    assert report["handoff"]["BODY0_bind_origin_basis_value_dependency_worklist_ready"] is True

    by_offset = {
        row["displacement"]: row
        for row in report["analysis"]["pose_store_values"]
    }
    origin = by_offset[0x00]
    assert origin["store_value_varnode"]["text"] == "EBX"
    assert origin["store_value_definition"] is not None
    assert [node["opcode"] for node in origin["dependency_slice"]] == ["COPY"]
    assert [root["root_kind"] for root in origin["terminal_roots"]] == ["general-register"]
    assert origin["terminal_roots"][0]["text"] == "EDX"

    floating = by_offset[0xD4]
    assert floating["store_value_varnode"]["text"] == "ST0"
    assert floating["store_value_definition"] is None
    assert floating["dependency_slice"] == []
    assert floating["terminal_roots"][0]["root_kind"] == "floating-register"
    assert floating["preceding_direct_calls"]
    assert floating["preceding_direct_calls"][-1]["direct_targets"] == ["0x00909990"]

    blocker_ids = {row["id"] for row in report["blockers"]}
    assert "general-register-source-root-semantics-unresolved" in blocker_ids
    assert "floating-register-call-return-provenance-unresolved" in blocker_ids
    assert "instruction-pcode-not-cfg-ssa" in blocker_ids
    assert "BODY0-target-parameter-callsite-value-join-unproven" in blocker_ids
    assert "bind-origin-basis-concrete-values-unproven" in blocker_ids

    assert report["handoff"]["BODY0_bind_origin_basis_values_ready"] is False
    assert report["handoff"]["BODY0_pointer_at_bind_callsite_ready"] is False
    assert report["handoff"]["BODY0_bind_frame_proof_ready"] is False
    assert report["scope"]["preceding_CALL_used_as_floating_return_proof"] is False
    assert report["scope"]["cfg_ssa_value_identity_proven"] is False
    assert report["scope"]["host_floating_math_substitution_allowed"] is False


def test_memory_load_source_is_exposed_as_finite_semantic_worklist(tmp_path: Path) -> None:
    _, report = _run(tmp_path, memory_source=True)

    by_offset = {row["displacement"]: row for row in report["analysis"]["pose_store_values"]}
    origin = by_offset[0x00]
    assert origin["contains_memory_load"] is True
    assert [node["opcode"] for node in origin["dependency_slice"]] == ["LOAD", "COPY"]
    kinds = {root["root_kind"] for root in origin["terminal_roots"]}
    assert "address-space-selector" in kinds
    assert "general-register" in kinds
    blocker_ids = {row["id"] for row in report["blockers"]}
    assert "pose-source-memory-load-address-semantics-unresolved" in blocker_ids


def test_multiple_store_pcode_ops_block_structural_frontier(tmp_path: Path) -> None:
    _, report = _run(tmp_path, duplicate_store_at=0xF4)

    assert report["analysis"]["all_target_role_pose_stores_analyzed"] is False
    assert report["handoff"]["pose_writer_pose_store_value_dependency_frontier_ready"] is False
    blocker = next(
        row for row in report["blockers"]
        if row["id"] == "pose-store-pcode-cardinality-not-one"
    )
    assert blocker["store_pcode_count"] == 2


def test_rejects_incomplete_target_role_witness_coverage(tmp_path: Path) -> None:
    m = _module()
    row, store_addresses = _fixture(m)
    target = _target_role(m, store_addresses)
    target["analysis"]["pose_write_witnesses"].pop()
    target_path = tmp_path / "target.json"
    target_path.write_text(json.dumps(target) + "\n", encoding="utf-8")
    instruction_path = tmp_path / "instructions.jsonl"
    instruction_path.write_text(json.dumps(row) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="target-role witness coverage mismatch"):
        m.analyze_bmw_body0_bind_pose_writer_value_provenance(target_path, instruction_path)


def test_rejects_target_role_semantic_preclaim(tmp_path: Path) -> None:
    m = _module()
    row, store_addresses = _fixture(m)
    target = _target_role(m, store_addresses)
    target["handoff"]["BODY0_bind_origin_basis_values_ready"] = True
    target_path = tmp_path / "target.json"
    target_path.write_text(json.dumps(target) + "\n", encoding="utf-8")
    instruction_path = tmp_path / "instructions.jsonl"
    instruction_path.write_text(json.dumps(row) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="unexpectedly preclaims BODY0_bind_origin_basis_values_ready"):
        m.analyze_bmw_body0_bind_pose_writer_value_provenance(target_path, instruction_path)
