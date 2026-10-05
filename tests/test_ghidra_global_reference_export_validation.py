from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "validate_global_reference_export.py"
SPEC = importlib.util.spec_from_file_location("validate_global_reference_export", TOOL)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _row() -> dict:
    return {
        "format": "SHIFT.GhidraGlobalReferences/1",
        "program": "SHIFT.exe",
        "executable_md5": "705af8b420e5eb1e3834ac43d5533c6b",
        "requested": "DAT_00bc185c",
        "resolved_address": "0x00bc185c",
        "found": True,
        "primary_symbol": "DAT_00bc185c",
        "data_type": "undefined4",
        "data_length": 4,
        "reference_count": 2,
        "function_addresses": ["0x00412340"],
        "references": [
            {
                "from": "0x00412350",
                "type": "DATA",
                "operand_index": 1,
                "primary": True,
                "function_address": "0x00412340",
                "function_name": "FUN_00412340",
                "instruction": "MOV EAX,dword ptr [0xbc185c]",
            },
            {
                "from": "0x00bc2000",
                "type": "DATA",
                "operand_index": -1,
                "primary": False,
                "function_address": None,
                "function_name": None,
                "instruction": None,
            },
        ],
    }


def _write(tmp_path: Path, row: dict) -> Path:
    path = tmp_path / "refs.jsonl"
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    return path


def test_accepts_consistent_export(tmp_path: Path):
    MODULE.validate(_write(tmp_path, _row()), ["DAT_00bc185c"])
    MODULE.validate(_write(tmp_path, _row()), ["0x00bc185c"])


def test_rejects_reference_count_drift(tmp_path: Path):
    row = _row()
    row["reference_count"] = 1
    with pytest.raises(ValueError, match="reference_count"):
        MODULE.validate(_write(tmp_path, row), ["0x00bc185c"])


def test_rejects_function_summary_drift(tmp_path: Path):
    row = _row()
    row["function_addresses"] = ["0x00499999"]
    with pytest.raises(ValueError, match="function_addresses"):
        MODULE.validate(_write(tmp_path, row), ["0x00bc185c"])


def test_rejects_missing_global(tmp_path: Path):
    row = _row()
    row["found"] = False
    with pytest.raises(ValueError, match="not found"):
        MODULE.validate(_write(tmp_path, row), ["0x00bc185c"])


def test_normalize_accepts_supported_forms():
    assert MODULE.normalize_address("0x00BC185C") == "0x00bc185c"
    assert MODULE.normalize_address("DAT_00bc185c") == "0x00bc185c"
    assert MODULE.normalize_address("00bc185c") == "0x00bc185c"
