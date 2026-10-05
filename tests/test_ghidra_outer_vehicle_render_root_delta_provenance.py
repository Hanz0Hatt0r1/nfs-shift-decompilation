from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_outer_vehicle_render_root_delta_provenance.py"
SPEC = importlib.util.spec_from_file_location("outer_vehicle_render_root_delta_provenance", TOOL)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _varnode(
    text: str,
    *,
    space: str,
    offset: str,
    size: int,
    constant: bool = False,
    register: bool = False,
    unique: bool = False,
) -> dict:
    return {
        "text": text,
        "space": space,
        "offset": offset,
        "size": size,
        "constant": constant,
        "register": register,
        "unique": unique,
    }


def _register(name: str, offset: str = "0x0", size: int = 4) -> dict:
    return _varnode(name, space="register", offset=offset, size=size, register=True)


def _const(value: int, size: int = 4) -> dict:
    return _varnode(
        f"0x{value:x}",
        space="const",
        offset=f"0x{value:x}",
        size=size,
        constant=True,
    )


def _unique(offset: int, size: int = 4) -> dict:
    return _varnode(
        f"u_{offset:x}",
        space="unique",
        offset=f"0x{offset:x}",
        size=size,
        unique=True,
    )


def _copy(address: str, dst: str, src: str, fallthrough: str) -> dict:
    return {
        "address": address,
        "bytes": "8bf1",
        "mnemonic": "MOV",
        "text": f"MOV {dst},{src}",
        "operands": [dst, src],
        "flow_type": "FALL_THROUGH",
        "fallthrough": fallthrough,
        "flows": [],
        "references": [],
        "pcode": [
            {
                "opcode": "COPY",
                "text": f"{dst} = COPY {src}",
                "output": _register(dst),
                "inputs": [_register(src)],
            }
        ],
    }


def _store(
    address: str,
    base: str,
    displacement: int,
    value: int,
    *,
    fallthrough: str,
    operand: str | None = None,
) -> dict:
    memory = operand or f"dword ptr [{base} + 0x{displacement:x}]"
    return {
        "address": address,
        "bytes": "8900",
        "mnemonic": "MOV",
        "text": f"MOV {memory},0x{value:x}",
        "operands": [memory, f"0x{value:x}"],
        "flow_type": "FALL_THROUGH",
        "fallthrough": fallthrough,
        "flows": [],
        "references": [],
        "pcode": [
            {
                "opcode": "STORE",
                "text": f"STORE ram({memory}) = 0x{value:x}",
                "output": None,
                "inputs": [
                    _const(0, 4) | {"text": "RAM"},
                    _unique(int(address, 0), 4),
                    _const(value, 4),
                ],
            }
        ],
    }


def _memory_copy(address: str, dst: str, base: str, displacement: int, fallthrough: str) -> dict:
    return {
        "address": address,
        "bytes": "8b00",
        "mnemonic": "MOV",
        "text": f"MOV {dst},dword ptr [{base} + 0x{displacement:x}]",
        "operands": [dst, f"dword ptr [{base} + 0x{displacement:x}]"],
        "flow_type": "FALL_THROUGH",
        "fallthrough": fallthrough,
        "flows": [],
        "references": [],
        "pcode": [
            {
                "opcode": "LOAD",
                "text": f"{dst} = LOAD ram({base}+0x{displacement:x})",
                "output": _register(dst),
                "inputs": [_const(0, 4) | {"text": "RAM"}, _register(base)],
            }
        ],
    }


def _ret(address: str) -> dict:
    return {
        "address": address,
        "bytes": "c3",
        "mnemonic": "RET",
        "text": "RET",
        "operands": [],
        "flow_type": "TERMINATOR",
        "fallthrough": None,
        "flows": [],
        "references": [],
        "pcode": [],
    }


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _retail_root(tmp_path: Path, *, fingerprint: str | None = None) -> Path:
    root = tmp_path / "ghidra"
    root.mkdir()
    (root / "binary.json").write_text(
        json.dumps({"program_name": MODULE.PROGRAM, "executable_md5": MODULE.PE_MD5}),
        encoding="utf-8",
    )
    _write_jsonl(
        root / "functions.jsonl",
        [
            {
                "address": MODULE.TARGET,
                "name": MODULE.TARGET_NAME,
                "namespace": "Global",
                "size": MODULE.TARGET_SIZE,
                "thunk": False,
                "external": False,
                "calling_convention": MODULE.TARGET_CALLING_CONVENTION,
                "signature": "undefined FUN_00795d60(void * param_1, char p2, float * p3, void * p4, char p5)",
                "parameters": [],
                "mnemonic_sha256": fingerprint or MODULE.TARGET_MNEMONIC_SHA256,
            }
        ],
    )
    return root


def _bridge(tmp_path: Path, *, preclaim: bool = False) -> Path:
    path = tmp_path / "bridge.json"
    path.write_text(
        json.dumps(
            {
                "format": MODULE.BRIDGE_FORMAT,
                "status": "outer-render-snapshot-affine-bridge-proven-vhf-delta-join-pending",
                "ready": True,
                "handoff": {
                    "outer_vehicle_to_render_root_symbolic_affine_ready": True,
                    "render_root_translation_delta_producer_bounded": True,
                    "outer_vehicle_root_to_VHF_vehicle_root_ready": preclaim,
                    "outer_vehicle_root_to_VHF_fixed_affine_delta_ready": False,
                    "BODY0_bind_frame_proof_ready": False,
                },
                "outer_transform": {
                    "local_delta_has_concrete_setup_producer": True,
                    "render_root_local_delta_offsets": ["+0x19c", "+0x1a0", "+0x1a4"],
                },
                "snapshot_relation": {
                    "translation_formula": "P_snapshot = P_outer + R_outer * delta_local"
                },
            }
        ),
        encoding="utf-8",
    )
    return path


def _instruction_export(tmp_path: Path, instructions: list[dict]) -> Path:
    path = tmp_path / "delta.jsonl"
    _write_jsonl(
        path,
        [
            {
                "format": MODULE.INSTRUCTION_FORMAT,
                "program": MODULE.PROGRAM,
                "requested": MODULE.TARGET,
                "found": True,
                "function": {
                    "address": MODULE.TARGET,
                    "name": MODULE.TARGET_NAME,
                    "size": MODULE.TARGET_SIZE,
                    "calling_convention": MODULE.TARGET_CALLING_CONVENTION,
                },
                "instruction_count": len(instructions),
                "instructions": instructions,
            }
        ],
    )
    return path


def _positive_instructions() -> list[dict]:
    return [
        _copy("0x00795d60", "ESI", "ECX", "0x00795d62"),
        _store("0x00795d62", "ESI", 0x19C, 0x3F000000, fallthrough="0x00795d68"),
        _store("0x00795d68", "ESI", 0x1A0, 0xBF800000, fallthrough="0x00795d6e"),
        _store("0x00795d6e", "ESI", 0x1A4, 0x00000000, fallthrough="0x00795d74"),
        _ret("0x00795d74"),
    ]


def test_positive_store_frontier_proves_delta_fields_but_not_vhf_relation(tmp_path):
    report = MODULE.analyze_outer_vehicle_render_root_delta_provenance(
        _retail_root(tmp_path),
        _instruction_export(tmp_path, _positive_instructions()),
        _bridge(tmp_path),
    )

    assert report["format"] == MODULE.FORMAT
    assert report["ready"] is True
    assert report["status"] == "delta-store-provenance-ready"
    analysis = report["analysis"]
    assert analysis["candidate_store_count"] == 3
    assert analysis["entry_receiver_covered_byte_count"] == 12
    assert analysis["missing_entry_receiver_bytes"] == []
    assert analysis["terminal_root_kinds"] == ["constant"]
    for row in analysis["store_candidates"]:
        assert row["base_register_origins"] == ["entry:ECX"]
        assert row["target_is_FUN_00795d60_entry_ECX_on_all_reachable_paths"] is True
        assert row["outer_Vehicle_delta_field_semantics_joined_from_bridge"] is True
        assert row["VHF_frame_semantics_proven"] is False
        assert row["outer_vehicle_root_to_VHF_relation_proven"] is False
    assert report["handoff"]["render_root_delta_store_provenance_ready"] is True
    assert report["handoff"]["outer_vehicle_root_to_VHF_vehicle_root_ready"] is False
    assert report["handoff"]["BODY0_bind_frame_proof_ready"] is False
    assert report["scope"]["equal_numeric_values_used_as_frame_identity_proof"] is False
    assert report["blockers"][-1]["id"] == "render-root-delta-value-roots-to-canonical-vhf-root"


def test_memory_derived_store_base_blocks_positive_coverage(tmp_path):
    instructions = _positive_instructions()
    instructions = [
        instructions[0],
        _memory_copy("0x00795d62", "EDI", "ESI", 0x20, "0x00795d64"),
        _store("0x00795d64", "EDI", 0x19C, 1, fallthrough="0x00795d68"),
        instructions[2],
        instructions[3],
        instructions[4],
    ]
    report = MODULE.analyze_outer_vehicle_render_root_delta_provenance(
        _retail_root(tmp_path),
        _instruction_export(tmp_path, instructions),
        _bridge(tmp_path),
    )

    assert report["ready"] is False
    first = report["analysis"]["store_candidates"][0]
    assert first["target_is_FUN_00795d60_entry_ECX_on_all_reachable_paths"] is False
    assert first["base_register_origin_flags"]["contains_memory_origin"] is True
    assert any(
        row["id"] == "render-root-delta-entry-receiver-store-coverage-incomplete"
        for row in report["blockers"]
    )


def test_complex_delta_memory_operand_is_structural_blocker(tmp_path):
    instructions = _positive_instructions()
    instructions[1] = _store(
        "0x00795d62",
        "ESI",
        0x19C,
        1,
        fallthrough="0x00795d68",
        operand="dword ptr [ESI + EAX*4 + 0x19c]",
    )
    report = MODULE.analyze_outer_vehicle_render_root_delta_provenance(
        _retail_root(tmp_path),
        _instruction_export(tmp_path, instructions),
        _bridge(tmp_path),
    )

    assert report["ready"] is False
    assert report["analysis"]["structural_blockers"][0]["instruction"] == "0x00795d62"
    assert any(
        row["id"] == "render-root-delta-store-structural-ambiguity"
        for row in report["blockers"]
    )


def test_rejects_retail_function_fingerprint_drift(tmp_path):
    with pytest.raises(ValueError, match="mnemonic fingerprint drift"):
        MODULE.analyze_outer_vehicle_render_root_delta_provenance(
            _retail_root(tmp_path, fingerprint="0" * 64),
            _instruction_export(tmp_path, _positive_instructions()),
            _bridge(tmp_path),
        )


def test_rejects_bridge_that_preclaims_vhf_identity(tmp_path):
    with pytest.raises(ValueError, match="preclaims outer/VHF frame identity"):
        MODULE.analyze_outer_vehicle_render_root_delta_provenance(
            _retail_root(tmp_path),
            _instruction_export(tmp_path, _positive_instructions()),
            _bridge(tmp_path, preclaim=True),
        )


def test_rejects_extra_targeted_instruction_row(tmp_path):
    path = _instruction_export(tmp_path, _positive_instructions())
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"format": MODULE.INSTRUCTION_FORMAT}) + "\n")
    with pytest.raises(ValueError, match="expected one targeted instruction row"):
        MODULE.analyze_outer_vehicle_render_root_delta_provenance(
            _retail_root(tmp_path), path, _bridge(tmp_path)
        )
