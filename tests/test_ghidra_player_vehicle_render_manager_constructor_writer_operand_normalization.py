from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_player_vehicle_render_manager_constructor_writer.py"
SPEC = importlib.util.spec_from_file_location(
    "analyze_player_vehicle_render_manager_constructor_writer_operand_normalization",
    TOOL,
)
assert SPEC and SPEC.loader
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def _instruction(address: str, mnemonic: str, operands: list[str]):
    return {
        "address": address,
        "mnemonic": mnemonic,
        "operands": operands,
    }


def test_accepts_retail_ghidra_trimmed_hex_immediate_for_constructor_label():
    instruction = _instruction(m.CTOR_LABEL_PUSH, "PUSH", ["0xab55a4"])
    result = m._require_instruction(
        {m.CTOR_LABEL_PUSH: instruction},
        m.CTOR_LABEL_PUSH,
        "PUSH",
        [m.CTOR_LABEL_ADDRESS],
    )
    assert result is instruction
    assert m.CTOR_LABEL_ADDRESS == "0x00ab55a4"


def test_plain_hex_immediate_normalization_is_numeric_only():
    assert m._operand_equivalent("0xab55a4", "0x00ab55a4") is True
    assert m._operand_equivalent("0x00000400", "0x400") is True
    assert m._operand_equivalent("EAX", "eax") is True


def test_memory_operands_remain_structurally_fail_closed():
    assert m._operand_equivalent("[0xbc185c]", "[0x00bc185c]") is False
    instruction = _instruction("0x00400000", "MOV", ["[0xbc185c]", "EAX"])
    with pytest.raises(ValueError, match="operand drift"):
        m._require_instruction(
            {"0x00400000": instruction},
            "0x00400000",
            "MOV",
            ["[0x00bc185c]", "EAX"],
        )
