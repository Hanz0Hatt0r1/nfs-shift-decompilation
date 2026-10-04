from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_register_relative_accesses.py"
SPEC = importlib.util.spec_from_file_location("register_relative_accesses_float_qualifiers", TOOL)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_parses_ghidra_float_and_double_ptr_register_relative_operands():
    assert MODULE._parse_memory_operand("float ptr [ECX + 0x18]") == ("ECX", 0x18)
    assert MODULE._parse_memory_operand("double ptr [ESI + 0x33b0]") == ("ESI", 0x33B0)


def test_float_qualifier_does_not_relax_complex_addressing():
    assert MODULE._parse_memory_operand("double ptr [ESI + EAX*4 + 0x33b0]") is None
