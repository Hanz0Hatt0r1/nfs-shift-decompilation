from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_register_relative_accesses.py"
SPEC = importlib.util.spec_from_file_location("register_relative_accesses", TOOL)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_float_ptr_register_relative_operand_is_admitted() -> None:
    assert MODULE._parse_memory_operand("float ptr [ECX + 0x24]") == ("ECX", 0x24)


def test_double_ptr_register_relative_operand_is_admitted() -> None:
    assert MODULE._parse_memory_operand("double ptr [ESI + 0x33b0]") == ("ESI", 0x33B0)


def test_indexed_x87_operand_remains_fail_closed() -> None:
    assert MODULE._parse_memory_operand("double ptr [ESI + EAX*4 + 0x33b0]") is None
