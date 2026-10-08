from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/ghidra/inventory_fun_00765c40_write_surface.py"
DOC = ROOT / "docs/PROCESS_1_FUN_00765C40_WRITE_INVENTORY.md"


def _module():
    spec = importlib.util.spec_from_file_location("fun00765c40_write_probe", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_probe_is_source_hash_locked_and_fail_closed() -> None:
    module = _module()
    assert module.FORMAT == "SHIFT.Fun00765c40WriteSurfaceInventory/1"
    assert module.TARGET == "FUN_00765c40"
    assert module.PINNED_SOURCE_SHA256 == (
        "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
    )
    assert module.RETAIL_EXECUTABLE_SHA256 == (
        "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    )


def test_assignment_detector_ignores_comparisons() -> None:
    module = _module()
    assert module._assignment_site(1, "if (a == b) {") is None
    assert module._assignment_site(2, "if (a != b) {") is None
    site = module._assignment_site(3, "*(double *)(param_1 + 0x38e0) = local_20;")
    assert site == {
        "line": 3,
        "operator": "=",
        "lhs": "*(double *)(param_1 + 0x38e0)",
        "text": "*(double *)(param_1 + 0x38e0) = local_20;",
        "mentions_param_1": True,
        "mentions_this": False,
    }


def test_inventory_preserves_assignments_calls_globals_and_offsets() -> None:
    module = _module()
    body = [
        "void FUN_00765c40(int param_1)",
        "{",
        "  local_4 = DAT_00abcdef;",
        "  *(int *)(param_1 + 0x38dc) = iVar1;",
        "  *(double *)(param_1 + 0x38e0) = local_20;",
        "  local_8 += 1;",
        "  FUN_007b0710(&local_40);",
        "  if (local_8 == 1) {",
        "    FUN_00112233(param_1 + 0xb38);",
        "  }",
        "}",
    ]
    inventory = module._inventory(200, body)
    assert inventory["assignment_count"] == 4
    assert [row["line"] for row in inventory["param_1_assignment_sites"]] == [203, 204]
    assert inventory["unique_direct_callees"] == ["FUN_00112233", "FUN_007b0710"]
    assert inventory["unique_global_references"] == ["DAT_00abcdef"]
    assert inventory["hex_offset_frequency"] == {"0xb38": 1, "0x38dc": 1, "0x38e0": 1}


def test_probe_extracts_only_target_definition() -> None:
    module = _module()
    source = [
        "void caller(void) { FUN_00765c40(1); }",
        "void FUN_00765c40(int param_1)",
        "{",
        "  *(int *)(param_1 + 4) = 1;",
        "}",
        "void later(void) { FUN_00765c40(2); }",
    ]
    start, end, body = module._extract_function(source)
    assert start == 2
    assert end == 5
    assert body[0] == "void FUN_00765c40(int param_1)"
    assert body[-1] == "}"


def test_documentation_keeps_write_inventory_non_semantic() -> None:
    text = DOC.read_text(encoding="utf-8")
    for token in (
        "raw write/call inventory",
        "not a proof that all writes target HDVehicle",
        "local aliases",
        "FUN_00765c40",
        "SHIFT.exe.c",
        "P1.2b",
        "provider count remains 7",
        "NEXT_STEP",
    ):
        assert token in text
