import json
from pathlib import Path

import pytest

from tools.ghidra.build_shift_pcode_supplement import (
    SHIFT_FORMAT,
    adapt_row,
    emit_source,
)


def _row(address: str) -> dict:
    return {
        "format": SHIFT_FORMAT,
        "program": "SHIFT.exe",
        "found": True,
        "function": {"address": address},
        "instruction_count": 1,
        "instructions": [{}],
    }


def test_shift_rows_adapt_to_the_shared_lowerer_schema() -> None:
    row = _row("0x00401000")
    adapted = adapt_row(row, "REVENGINSTR.GhidraFunctionInstructions/1")
    assert adapted["format"] == "REVENGINSTR.GhidraFunctionInstructions/1"
    assert adapted["resolved_address"] == "0x00401000"
    assert row["format"] == SHIFT_FORMAT


def test_instruction_slice_adapts_only_when_it_covers_the_exact_range() -> None:
    row = {
        "format": "SHIFT.GhidraInstructionSlice/1",
        "program": "SHIFT.exe",
        "start": "0x00401000",
        "length": 1,
        "exact_instruction_at_start": True,
        "instructions": [{"address": "0x00401000", "bytes": "c3", "pcode": []}],
    }
    adapted = adapt_row(row, "REVENGINSTR.GhidraFunctionInstructions/1")
    assert adapted["resolved_address"] == "0x00401000"
    assert adapted["function"]["name"] == "FUN_00401000"
    assert adapted["instructions"] == row["instructions"]

    row["length"] = 2
    with pytest.raises(ValueError, match="length does not match"):
        adapt_row(row, "REVENGINSTR.GhidraFunctionInstructions/1")


def test_emitter_writes_shared_runtime_once_and_rejects_duplicate_addresses(tmp_path: Path) -> None:
    rows = tmp_path / "functions.jsonl"
    rows.write_text(json.dumps(_row("0x00401000")) + "\n", encoding="utf-8")

    def compile_function(row: dict, _spaces: dict, *, include_runtime: bool = True) -> tuple[str, int]:
        assert row["format"] == "REVENGINSTR.GhidraFunctionInstructions/1"
        if include_runtime:
            return "/* runtime */\nstatic int helper(void) { return 1; }\nint rvi_00401000(RviPcodeContext *ctx) { return helper(); }\n", 1
        return "/* Generated from raw P-code. */\nint rvi_00401000(RviPcodeContext *ctx) { return 0; }\n", 1

    source = tmp_path / "supplement.c"
    report = emit_source(rows, {}, source, compile_function,
                         "REVENGINSTR.GhidraFunctionInstructions/1", RuntimeError)
    generated = source.read_text(encoding="utf-8")
    assert report["lowered_functions"] == 1
    assert generated.count("static int helper") == 1
    assert generated.count("int rvi_00401000(") == 1

    rows.write_text("\n".join(json.dumps(_row("0x00401000")) for _ in range(2)) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate function address"):
        emit_source(rows, {}, source, compile_function,
                    "REVENGINSTR.GhidraFunctionInstructions/1", RuntimeError)
