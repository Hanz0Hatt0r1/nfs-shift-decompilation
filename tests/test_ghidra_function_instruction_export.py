import importlib.util
import json
from pathlib import Path

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "validate_function_instruction_export.py"
    )
    spec = importlib.util.spec_from_file_location("validate_function_instruction_export", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _instruction(address, payload="55", mnemonic="PUSH", text="PUSH EBP"):
    return {
        "address": address,
        "bytes": payload,
        "mnemonic": mnemonic,
        "text": text,
        "operands": ["EBP"],
        "flow_type": "FALL_THROUGH",
        "fallthrough": "0x00886901",
        "flows": [],
        "references": [],
    }


def _row(address, name, instructions):
    return {
        "format": "SHIFT.GhidraFunctionInstructions/1",
        "program": "SHIFT.exe",
        "requested": address,
        "found": True,
        "function": {
            "address": address,
            "name": name,
            "size": 8,
            "calling_convention": "__cdecl",
        },
        "instruction_count": len(instructions),
        "instructions": instructions,
    }


def _write(path, rows):
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def test_normalizes_supported_target_spellings():
    module = _load_module()
    assert module.normalize_target("0x00886900") == "0x00886900"
    assert module.normalize_target("00886900") == "0x00886900"
    assert module.normalize_target("FUN_00886900") == "0x00886900"


def test_validates_exact_target_set_and_instruction_count(tmp_path):
    module = _load_module()
    export = tmp_path / "functions.jsonl"
    _write(
        export,
        [
            _row(
                "0x00886900",
                "FUN_00886900",
                [
                    _instruction("0x00886900"),
                    _instruction("0x00886901", "8b442404", "MOV", "MOV EAX,dword ptr [ESP + 0x4]"),
                ],
            ),
            _row(
                "0x00886930",
                "FUN_00886930",
                [_instruction("0x00886930", "51", "PUSH", "PUSH ECX")],
            ),
        ],
    )
    report = module.validate_export(export, ["FUN_00886900", "0x00886930"])
    assert report["function_count"] == 2
    assert report["instruction_count"] == 3
    assert report["functions"] == ["0x00886900", "0x00886930"]


def test_rejects_unresolved_target(tmp_path):
    module = _load_module()
    export = tmp_path / "functions.jsonl"
    _write(
        export,
        [
            {
                "format": "SHIFT.GhidraFunctionInstructions/1",
                "program": "SHIFT.exe",
                "requested": "FUN_00886900",
                "found": False,
                "function": None,
                "instruction_count": 0,
                "instructions": [],
            }
        ],
    )
    with pytest.raises(ValueError, match="unresolved target"):
        module.validate_export(export, ["FUN_00886900"])


def test_rejects_non_increasing_instruction_addresses(tmp_path):
    module = _load_module()
    export = tmp_path / "functions.jsonl"
    _write(
        export,
        [
            _row(
                "0x00886900",
                "FUN_00886900",
                [
                    _instruction("0x00886900"),
                    _instruction("0x00886900", "90", "NOP", "NOP"),
                ],
            )
        ],
    )
    with pytest.raises(ValueError, match="not increasing"):
        module.validate_export(export, ["FUN_00886900"])


def test_rejects_bad_instruction_bytes(tmp_path):
    module = _load_module()
    export = tmp_path / "functions.jsonl"
    row = _row(
        "0x00886900",
        "FUN_00886900",
        [_instruction("0x00886900", "zz")],
    )
    _write(export, [row])
    with pytest.raises(ValueError, match="invalid instruction bytes"):
        module.validate_export(export, ["FUN_00886900"])


def test_rejects_duplicate_requested_targets(tmp_path):
    module = _load_module()
    export = tmp_path / "functions.jsonl"
    _write(export, [])
    with pytest.raises(ValueError, match="duplicate requested"):
        module.validate_export(export, ["FUN_00886900", "0x00886900"])
