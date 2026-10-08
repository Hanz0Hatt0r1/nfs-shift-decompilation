from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/ghidra/inventory_fun_00758b50_input_surface.py"
DOC = ROOT / "docs/PROCESS_1_FUN_00758B50_INPUT_SURFACE_INVENTORY.md"


def _module():
    spec = importlib.util.spec_from_file_location("fun00758b50_input_probe", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_probe_is_source_hash_locked() -> None:
    module = _module()
    assert module.FORMAT == "SHIFT.Fun00758b50InputSurfaceInventory/1"
    assert module.TARGET == "FUN_00758b50"
    assert module.PINNED_SOURCE_SHA256 == "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
    assert module.RETAIL_EXECUTABLE_SHA256 == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"


def test_inventory_distinguishes_lhs_offset_references() -> None:
    module = _module()
    body = [
        "void FUN_00758b50(void *this)",
        "{",
        "  local_8 = *(double *)((int)this + 0x538);",
        "  *(double *)((int)this + 0x528) = local_8;",
        "  FUN_00755950((void *)((int)this + 0x400));",
        "  if (*(char *)((int)this + 0x940) == 0) {",
        "    FUN_007baa70(this, local_20, local_40);",
        "  }",
        "}",
    ]
    inventory = module._inventory(100, body)
    assert inventory["assignment_count"] == 2
    by_offset = {}
    for row in inventory["offset_reference_sites"]:
        by_offset.setdefault(row["offset"], []).append(row)
    assert by_offset["0x538"][0]["appears_on_assignment_lhs"] is False
    assert by_offset["0x528"][0]["appears_on_assignment_lhs"] is True
    assert by_offset["0x400"][0]["appears_on_assignment_lhs"] is False
    assert by_offset["0x940"][0]["appears_on_assignment_lhs"] is False
    assert inventory["unique_direct_callees"] == ["FUN_00755950", "FUN_007baa70"]


def test_probe_extracts_only_target_definition() -> None:
    module = _module()
    source = [
        "void caller(void) { FUN_00758b50(1); }",
        "void FUN_00758b50(void *this)",
        "{",
        "  *(int *)((int)this + 4) = 1;",
        "}",
        "void later(void) { FUN_00758b50(2); }",
    ]
    start, end, body = module._extract_function(source)
    assert start == 2
    assert end == 5
    assert body[0] == "void FUN_00758b50(void *this)"
    assert body[-1] == "}"


def test_documentation_keeps_inventory_non_semantic() -> None:
    text = DOC.read_text(encoding="utf-8")
    for token in (
        "source-hash-locked",
        "not evidence that the field is throttle",
        "Local aliases",
        "FUN_00758b50",
        "retail_control_value_producer_identified = false",
        "provider count remains **7**",
        "NEXT_STEP",
    ):
        assert token in text
