from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_bmw_offset33b_store_provenance.py"
SPEC = importlib.util.spec_from_file_location("bmw_offset33b_store_provenance", TOOL)
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
    return _varnode(
        name,
        space="register",
        offset=offset,
        size=size,
        register=True,
    )


def _const(value: int, size: int = 8) -> dict:
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


def _copy_instruction(address: str, dst: str, src: str, fallthrough: str) -> dict:
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


def _memory_copy_instruction(
    address: str,
    dst: str,
    base: str,
    displacement: int,
    fallthrough: str,
) -> dict:
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
                "inputs": [
                    _const(0, 4) | {"text": "RAM"},
                    _register(base),
                ],
            }
        ],
    }


def _store_instruction(
    address: str,
    base: str,
    displacement: int,
    value: int,
    *,
    width: int = 8,
    fallthrough: str,
    operand: str | None = None,
) -> dict:
    memory = operand or f"qword ptr [{base} + 0x{displacement:x}]"
    return {
        "address": address,
        "bytes": "dd00",
        "mnemonic": "FSTP",
        "text": f"FSTP {memory}",
        "operands": [memory],
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
                    _const(value, width),
                ],
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
                "signature": "undefined FUN_0076b280(void * this, int p1, void * p2)",
                "parameters": [],
                "mnemonic_sha256": fingerprint or MODULE.TARGET_MNEMONIC_SHA256,
            }
        ],
    )
    return root


def _relation(tmp_path: Path, *, numeric_ready: bool = False) -> Path:
    path = tmp_path / "relation.json"
    path.write_text(
        json.dumps(
            {
                "format": MODULE.RELATION_FORMAT,
                "ready": True,
                "retail": {
                    "functions": [
                        {
                            "address": MODULE.TARGET,
                            "mnemonic_sha256": MODULE.TARGET_MNEMONIC_SHA256,
                        }
                    ]
                },
                "symbolic_bind_relation": {
                    "translation": [
                        "-HDVehicle[0x33b0]",
                        "-HDVehicle[0x33b8]",
                        "-HDVehicle[0x33c0]",
                    ]
                },
                "gates": {
                    "BODY0_to_outer_vehicle_root_translation_symbolic_ready": True,
                    "BMW_numeric_offset33b_ready": numeric_ready,
                },
            }
        ),
        encoding="utf-8",
    )
    return path


def _instruction_export(tmp_path: Path, instructions: list[dict]) -> Path:
    path = tmp_path / "offset33b.jsonl"
    row = {
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
    _write_jsonl(path, [row])
    return path


def _positive_instructions() -> list[dict]:
    return [
        _copy_instruction("0x0076b280", "ESI", "ECX", "0x0076b282"),
        _store_instruction(
            "0x0076b282", "ESI", 0x33B0, 0x1111111111111111, fallthrough="0x0076b288"
        ),
        _store_instruction(
            "0x0076b288", "ESI", 0x33B8, 0x2222222222222222, fallthrough="0x0076b28e"
        ),
        _store_instruction(
            "0x0076b28e", "ESI", 0x33C0, 0x3333333333333333, fallthrough="0x0076b294"
        ),
        _ret("0x0076b294"),
    ]


def test_positive_frontier_proves_all_three_store_targets_but_not_numeric_values(tmp_path):
    report = MODULE.analyze_bmw_offset33b_store_provenance(
        _retail_root(tmp_path),
        _instruction_export(tmp_path, _positive_instructions()),
        _relation(tmp_path),
    )

    assert report["format"] == MODULE.FORMAT
    assert report["ready"] is True
    assert report["status"] == "store-frontier-ready"
    analysis = report["analysis"]
    assert analysis["candidate_store_count"] == 3
    assert analysis["entry_receiver_covered_byte_count"] == 24
    assert analysis["missing_entry_receiver_bytes"] == []
    assert analysis["terminal_root_kinds"] == ["constant"]
    for row in analysis["store_candidates"]:
        assert row["base_register_origins"] == ["entry:ECX"]
        assert row["target_is_FUN_0076b280_entry_ECX_on_all_reachable_paths"] is True
        assert row["HDVehicle_field_semantics_joined_from_symbolic_relation"] is True
        assert row["value_slice_constant_only"] is True
        assert row["numeric_value_proven"] is False
        assert row["BMW_numeric_offset_value_proven"] is False
    assert report["handoff"]["offset33b_store_provenance_ready"] is True
    assert report["handoff"]["BMW_numeric_offset33b_ready"] is False
    assert report["handoff"]["vehicle_world_transform_ready"] is False
    assert report["scope"]["constant_roots_auto_promoted_to_double_values"] is False


def test_memory_derived_base_blocks_positive_entry_receiver_coverage(tmp_path):
    instructions = _positive_instructions()
    instructions = [
        instructions[0],
        _memory_copy_instruction("0x0076b282", "EDI", "ESI", 0x20, "0x0076b284"),
        _store_instruction(
            "0x0076b284", "EDI", 0x33B0, 1, fallthrough="0x0076b288"
        ),
        instructions[2],
        instructions[3],
        instructions[4],
    ]
    report = MODULE.analyze_bmw_offset33b_store_provenance(
        _retail_root(tmp_path),
        _instruction_export(tmp_path, instructions),
        _relation(tmp_path),
    )

    assert report["ready"] is False
    first = report["analysis"]["store_candidates"][0]
    assert first["target_is_FUN_0076b280_entry_ECX_on_all_reachable_paths"] is False
    assert first["base_register_origin_flags"]["contains_memory_origin"] is True
    assert any(
        row["id"] == "offset33b-entry-receiver-store-coverage-incomplete"
        for row in report["blockers"]
    )


def test_complex_offset33b_memory_operand_is_a_structural_blocker(tmp_path):
    instructions = _positive_instructions()
    instructions[1] = _store_instruction(
        "0x0076b282",
        "ESI",
        0x33B0,
        1,
        fallthrough="0x0076b288",
        operand="qword ptr [ESI + EAX*4 + 0x33b0]",
    )
    report = MODULE.analyze_bmw_offset33b_store_provenance(
        _retail_root(tmp_path),
        _instruction_export(tmp_path, instructions),
        _relation(tmp_path),
    )

    assert report["ready"] is False
    assert report["analysis"]["structural_blockers"][0]["instruction"] == "0x0076b282"
    assert any(
        row["id"] == "offset33b-store-structural-ambiguity"
        for row in report["blockers"]
    )


def test_rejects_retail_function_fingerprint_drift(tmp_path):
    with pytest.raises(ValueError, match="mnemonic fingerprint drift"):
        MODULE.analyze_bmw_offset33b_store_provenance(
            _retail_root(tmp_path, fingerprint="0" * 64),
            _instruction_export(tmp_path, _positive_instructions()),
            _relation(tmp_path),
        )


def test_rejects_symbolic_relation_that_preclaims_numeric_offset(tmp_path):
    with pytest.raises(ValueError, match="preclaims BMW numeric offset33b"):
        MODULE.analyze_bmw_offset33b_store_provenance(
            _retail_root(tmp_path),
            _instruction_export(tmp_path, _positive_instructions()),
            _relation(tmp_path, numeric_ready=True),
        )


def test_rejects_extra_targeted_function_row(tmp_path):
    path = _instruction_export(tmp_path, _positive_instructions())
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"format": MODULE.INSTRUCTION_FORMAT}) + "\n")
    with pytest.raises(ValueError, match="expected one targeted instruction row"):
        MODULE.analyze_bmw_offset33b_store_provenance(
            _retail_root(tmp_path), path, _relation(tmp_path)
        )
