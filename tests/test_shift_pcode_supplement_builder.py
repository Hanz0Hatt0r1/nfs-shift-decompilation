import json
from pathlib import Path

import pytest

from tools.ghidra.build_shift_pcode_supplement import (
    SHIFT_FORMAT,
    adapt_row,
    emit_source,
    preserve_dynamic_branchind_targets,
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


def test_indirect_branch_keeps_runtime_target_when_static_flow_is_incomplete() -> None:
    generated = """switch (rvi_360_branch_target_value) {
    case UINT64_C(0xbe): if (rvi_call(ctx, UINT64_C(0xbe)) != 0) return -1; return 0;
    default: return -1;
    }
"""

    lowered = preserve_dynamic_branchind_targets(generated)

    assert "case UINT64_C(0xbe):" in lowered
    assert "default: if (rvi_call(ctx, rvi_360_branch_target_value) != 0) return -1; return 0;" in lowered
    assert "default: return -1;" not in lowered


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


@pytest.mark.parametrize("entry", ["0x00906240", "0x00906246", "0x00d6fecc"])
def test_lower_address_basic_block_starts_at_the_declared_entrypoint(
    tmp_path: Path, entry: str
) -> None:
    entry_offset = int(entry, 16)
    entry_suffix = f"{entry_offset:08x}"
    entry_label = f"rvi_label_{entry_offset:016x}"
    row = _row(entry)
    row["function"]["size"] = 195
    row["instruction_count"] = 2
    row["instructions"] = [
        {"address": "0x00906230", "bytes": "8d42ffc3"},
        {"address": entry, "bytes": "33c0", "branch_target": "0x00906230"},
    ]
    rows = tmp_path / "function.jsonl"
    rows.write_text(json.dumps(row) + "\n", encoding="utf-8")
    source = tmp_path / "supplement.c"

    def compile_function(function: dict, _spaces: dict, *, include_runtime: bool = True) -> tuple[str, int]:
        assert function["function"]["address"] == entry
        assert function["instructions"][0]["address"] == "0x00906230"
        assert function["instructions"][1]["branch_target"] == "0x00906230"
        prefix = "/* runtime */\n" if include_runtime else ""
        return (prefix + f"int rvi_{entry_suffix}(RviPcodeContext *ctx) {{\n"
                "uint8_t _unique[1] = {0};\nif (!ctx) return -1;\n"
                "rvi_label_0000000000906230: ;\n"
                f"{entry_label}: ;\nreturn 0;\n}}\n", 2)

    report = emit_source(rows, {}, source, compile_function,
                         "REVENGINSTR.GhidraFunctionInstructions/1", RuntimeError)
    generated = source.read_text(encoding="utf-8")
    assert report["lowered_functions"] == 1
    assert f"int rvi_{entry_suffix}(" in generated
    assert "int rvi_00906230(" not in generated
    assert generated.index("if (!ctx) return -1;") < generated.index(
        f"goto {entry_label};") < generated.index(
            "rvi_label_0000000000906230:")


def test_lower_address_tail_jump_stays_an_internal_branch(tmp_path: Path) -> None:
    entry = "0x0088a2c0"
    lower_block = "0x0088a0e0"
    entry_label = "rvi_label_000000000088a2c0"
    lower_label = "rvi_label_000000000088a0e0"
    row = _row(entry)
    row["function"]["size"] = 488
    row["instruction_count"] = 133
    row["instructions"] = [
        {"address": lower_block},
        {"address": entry},
        {"address": "0x0088a2c7", "branch_target": lower_block},
    ]
    rows = tmp_path / "function.jsonl"
    rows.write_text(json.dumps(row) + "\n", encoding="utf-8")
    source = tmp_path / "supplement.c"

    def compile_function(_function: dict, _spaces: dict, *, include_runtime: bool = True) -> tuple[str, int]:
        prefix = "/* runtime */\n" if include_runtime else ""
        return (prefix + "int rvi_0088a2c0(RviPcodeContext *ctx) {\n"
                "uint8_t _unique[1] = {0};\n"
                f"{lower_label}: ;\n"
                f"{entry_label}: ;\n"
                "rvi_label_000000000088a2c7: ;\n"
                f"goto {lower_label};\nreturn 0;\n}}\n", 599)

    emit_source(rows, {}, source, compile_function,
                "REVENGINSTR.GhidraFunctionInstructions/1", RuntimeError)
    generated = source.read_text(encoding="utf-8")
    assert generated.index(f"goto {entry_label};") < generated.index(f"{lower_label}:")
    assert f"goto {lower_label};" in generated
    assert "rvi_call(ctx, UINT64_C(0x88a0e0))" not in generated
