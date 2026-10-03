import importlib.util
import json
from pathlib import Path

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "analyze_register_relative_accesses.py"
    )
    spec = importlib.util.spec_from_file_location(
        "analyze_register_relative_accesses", path
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _instruction(address, text, operands, pcode):
    return {
        "address": address,
        "bytes": "90",
        "mnemonic": text.split()[0],
        "text": text,
        "operands": operands,
        "flow_type": "FALL_THROUGH",
        "fallthrough": None,
        "flows": [],
        "references": [],
        "pcode": pcode,
    }


def _row(instructions, *, version=2):
    return {
        "format": f"SHIFT.GhidraFunctionInstructions/{version}",
        "program": "SHIFT.exe",
        "requested": "0x00700000",
        "found": True,
        "function": {
            "address": "0x00700000",
            "name": "FUN_00700000",
            "size": 64,
            "calling_convention": "__thiscall",
        },
        "instruction_count": len(instructions),
        "instructions": instructions,
    }


def _write(path, rows):
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_classifies_simple_register_relative_reads_writes_and_groups(tmp_path):
    module = _load_module()
    export = tmp_path / "instructions.jsonl"
    _write(
        export,
        [
            _row(
                [
                    _instruction(
                        "0x00700000",
                        "MOV dword ptr [ECX + 0x18],EAX",
                        ["dword ptr [ECX + 0x18]", "EAX"],
                        [
                            "unique:100 = INT_ADD ECX, 0x18",
                            "STORE ram, unique:100, EAX",
                        ],
                    ),
                    _instruction(
                        "0x00700004",
                        "MOV EDX,dword ptr [ECX + 0xd4]",
                        ["EDX", "dword ptr [ECX + 0xd4]"],
                        [
                            "unique:200 = INT_ADD ECX, 0xd4",
                            "EDX = LOAD ram, unique:200",
                        ],
                    ),
                    _instruction(
                        "0x00700008",
                        "ADD dword ptr [ECX + 0x20],EAX",
                        ["dword ptr [ECX + 0x20]", "EAX"],
                        [
                            "unique:300 = INT_ADD ECX, 0x20",
                            "unique:304 = LOAD ram, unique:300",
                            "unique:308 = INT_ADD unique:304, EAX",
                            "STORE ram, unique:300, unique:308",
                        ],
                    ),
                    _instruction(
                        "0x0070000c",
                        "MOV dword ptr [ESI - 0x4],EAX",
                        ["dword ptr [ESI - 0x4]", "EAX"],
                        ["STORE ram, ESI, EAX"],
                    ),
                ]
            )
        ],
    )

    report = module.analyze_register_relative_accesses(export)
    assert report["format"] == "SHIFT.GhidraRegisterRelativeAccesses/1"
    assert report["access_count"] == 4
    assert report["write_access_count"] == 3
    assert report["read_access_count"] == 2
    assert report["pcode_classification_blocker_count"] == 0
    assert report["unparsed_memory_operand_count"] == 0

    by_displacement = {
        (row["base_register"], row["displacement_hex"]): row
        for row in report["accesses"]
    }
    assert by_displacement[("ECX", "0x18")]["access"] == "write"
    assert by_displacement[("ECX", "0xd4")]["access"] == "read"
    assert by_displacement[("ECX", "0x20")]["access"] == "read-write"
    assert by_displacement[("ESI", "-0x4")]["access"] == "write"

    group = next(
        row
        for row in report["access_groups"]
        if row["base_register"] == "ECX" and row["displacement_hex"] == "0x20"
    )
    assert group["read_count"] == 1
    assert group["write_count"] == 1
    assert group["promoted"] is False
    assert report["scope"]["body_or_vehicle_identity_proven"] is False
    assert report["scope"]["persistent_state_writer_proven"] is False


def test_base_register_filter_does_not_relabel_pointer_semantics(tmp_path):
    module = _load_module()
    export = tmp_path / "instructions.jsonl"
    _write(
        export,
        [
            _row(
                [
                    _instruction(
                        "0x00700000",
                        "MOV dword ptr [ECX + 0x18],EAX",
                        ["dword ptr [ECX + 0x18]", "EAX"],
                        ["STORE ram, ECX, EAX"],
                    ),
                    _instruction(
                        "0x00700004",
                        "MOV dword ptr [ESI + 0x18],EAX",
                        ["dword ptr [ESI + 0x18]", "EAX"],
                        ["STORE ram, ESI, EAX"],
                    ),
                ]
            )
        ],
    )
    report = module.analyze_register_relative_accesses(
        export, base_registers=["ECX"]
    )
    assert report["access_count"] == 1
    assert report["filtered_access_count"] == 1
    assert report["base_register_filter"] == ["ECX"]
    assert report["scope"]["base_register_is_this_pointer"] is False


def test_complex_operands_and_missing_load_store_are_blockers(tmp_path):
    module = _load_module()
    export = tmp_path / "instructions.jsonl"
    _write(
        export,
        [
            _row(
                [
                    _instruction(
                        "0x00700000",
                        "MOV EAX,dword ptr [ECX + EDX*4 + 0x10]",
                        ["EAX", "dword ptr [ECX + EDX*4 + 0x10]"],
                        ["EAX = LOAD ram, unique:100"],
                    ),
                    _instruction(
                        "0x00700004",
                        "LEA EAX,[ECX + 0x18]",
                        ["EAX", "[ECX + 0x18]"],
                        ["EAX = INT_ADD ECX, 0x18"],
                    ),
                ]
            )
        ],
    )
    report = module.analyze_register_relative_accesses(export)
    assert report["access_count"] == 0
    assert report["unparsed_memory_operand_count"] == 1
    assert report["pcode_classification_blocker_count"] == 1
    assert report["pcode_classification_blockers"][0]["displacement_hex"] == "0x18"


def test_v1_export_fails_closed_without_pcode(tmp_path):
    module = _load_module()
    export = tmp_path / "instructions.jsonl"
    _write(export, [_row([], version=1)])
    with pytest.raises(ValueError, match="requires SHIFT.GhidraFunctionInstructions/2"):
        module.analyze_register_relative_accesses(export)


def test_rejects_unknown_register_filter(tmp_path):
    module = _load_module()
    export = tmp_path / "instructions.jsonl"
    _write(
        export,
        [
            _row(
                [
                    _instruction(
                        "0x00700000",
                        "NOP",
                        [],
                        ["COPY EAX, EAX"],
                    )
                ]
            )
        ],
    )
    with pytest.raises(ValueError, match="unsupported x86 base register"):
        module.analyze_register_relative_accesses(export, base_registers=["RAX"])
