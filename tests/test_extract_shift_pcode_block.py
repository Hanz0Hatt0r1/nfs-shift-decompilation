import json
from pathlib import Path

import pytest

from tools.ghidra.extract_shift_pcode_block import FORMAT, extract_block


def _instruction(address: str, data: str, flow: str) -> dict:
    return {
        "address": address,
        "bytes": data,
        "mnemonic": "NOP" if data == "90" else "RET",
        "text": "NOP" if data == "90" else "RET",
        "operands": [],
        "flow_type": flow,
        "fallthrough": None,
        "flows": [],
        "references": [],
        "pcode": [{"opcode": "RETURN", "text": "return", "output": None,
                   "inputs": []}],
    }


def _source(path: Path, instructions: list[dict]) -> None:
    row = {
        "format": FORMAT,
        "program": "SHIFT.exe",
        "requested": "0x00401000",
        "found": True,
        "function": {"address": "0x00401000", "name": "FUN_00401000",
                     "size": 2, "calling_convention": "unknown"},
        "instruction_count": len(instructions),
        "instructions": instructions,
    }
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")


def test_extracts_a_contiguous_terminal_block(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    expected = _instruction("0x00401001", "c3", "TERMINATOR")
    _source(source, [
        _instruction("0x00401000", "90", "FALL_THROUGH"), expected,
    ])

    row = extract_block(source, "0x00401001", "0x00401001")

    assert row["function"]["address"] == "0x00401001"
    assert row["function"]["size"] == 1
    assert row["instructions"] == [expected]


def test_rejects_instruction_gaps(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    _source(source, [
        _instruction("0x00401000", "90", "FALL_THROUGH"),
        _instruction("0x00401002", "c3", "TERMINATOR"),
    ])

    with pytest.raises(ValueError, match="gap"):
        extract_block(source, "0x00401000", "0x00401002")


def test_rejects_nonterminal_block_end(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    _source(source, [_instruction("0x00401000", "90", "FALL_THROUGH")])

    with pytest.raises(ValueError, match="terminal control-flow"):
        extract_block(source, "0x00401000", "0x00401000")
