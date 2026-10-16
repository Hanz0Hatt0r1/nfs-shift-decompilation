from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ADAPTER_PATH = ROOT / "tools/ghidra/adapt_revenginstr_function_instructions.py"
SPEC = importlib.util.spec_from_file_location("function_instruction_adapter", ADAPTER_PATH)
assert SPEC and SPEC.loader
adapter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adapter)


def test_adapts_generic_row_to_existing_shift_v2_shape(tmp_path: Path) -> None:
    instruction = {
        "address": "0x00101119",
        "bytes": "55",
        "mnemonic": "PUSH",
        "text": "PUSH RBP",
        "operands": ["RBP"],
        "flow_type": "FALL_THROUGH",
        "fallthrough": "0x0010111a",
        "flows": [],
        "references": [],
        "pcode": [{
            "opcode": "COPY",
            "text": "(unique, 0x1, 8) = COPY RBP",
            "output": {
                "text": "(unique, 0x1, 8)",
                "space": "unique",
                "offset": "0x1",
                "size": 8,
                "constant": False,
                "register": False,
                "unique": True,
            },
            "inputs": [],
        }],
    }
    generic = {
        "format": "REVENGINSTR.GhidraFunctionInstructions/1",
        "program": "sample",
        "requested": "00101119",
        "resolved_address": "0x00101119",
        "found": True,
        "function": {
            "address": "0x00101119",
            "name": "sample",
            "size": 1,
            "calling_convention": "__stdcall",
        },
        "instruction_count": 1,
        "instructions": [instruction],
    }
    source = tmp_path / "generic.jsonl"
    destination = tmp_path / "shift.jsonl"
    source.write_text(json.dumps(generic) + "\n", encoding="utf-8")

    adapter.adapt_file(source, destination)

    result = json.loads(destination.read_text(encoding="utf-8"))
    assert result == {
        "format": "SHIFT.GhidraFunctionInstructions/2",
        "program": "sample",
        "requested": "0x00101119",
        "found": True,
        "function": generic["function"],
        "instruction_count": 1,
        "instructions": [instruction],
    }


def test_rejects_unrecognized_generic_format() -> None:
    with pytest.raises(ValueError, match="REVENGINSTR.GhidraFunctionInstructions/1"):
        adapter.adapt_row({"format": "unknown"}, 1)


def test_shift_runner_prefers_shared_exporter_and_keeps_fallback() -> None:
    runner = (ROOT / "tools/ghidra/run_shift_function_instructions.sh").read_text(encoding="utf-8")
    assert "ExportGhidraFunctionInstructions.java" in runner
    assert "ShiftFunctionInstructionExporter.java" in runner
    assert "adapt_revenginstr_function_instructions.py" in runner
    assert "USE_SHARED_EXPORTER" in runner
