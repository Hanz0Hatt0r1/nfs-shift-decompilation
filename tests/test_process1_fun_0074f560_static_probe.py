from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/ghidra/inventory_fun_0074f560_provider_surface.py"
DOC = ROOT / "docs/PROCESS_1_FUN_0074F560_STATIC_PROBE.md"


def _module():
    spec = importlib.util.spec_from_file_location("fun0074f560_probe", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_probe_is_hash_locked_and_fail_closed() -> None:
    module = _module()
    assert module.FORMAT == "SHIFT.Fun0074f560ProviderSurfaceInventory/1"
    assert module.TARGET == "FUN_0074f560"
    assert module.PINNED_SOURCE_SHA256 == (
        "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
    )
    assert module.RETAIL_EXECUTABLE_SHA256 == (
        "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    )


def test_probe_extracts_only_the_target_definition() -> None:
    module = _module()
    source = [
        "void caller(void)",
        "{",
        "  FUN_0074f560(param_1);",
        "}",
        "",
        "undefined8 FUN_0074f560(int param_1)",
        "{",
        "  FUN_00112233(param_1);",
        "  return 0;",
        "}",
        "",
        "void later(void)",
        "{",
        "  FUN_0074f560(1);",
        "}",
    ]
    start, end, body = module._extract_function(source)
    assert start == 6
    assert end == 10
    assert body[0] == "undefined8 FUN_0074f560(int param_1)"
    assert body[-1] == "}"


def test_probe_inventories_direct_calls_globals_offsets_and_indirect_candidates() -> None:
    module = _module()
    body = [
        "undefined8 FUN_0074f560(int param_1)",
        "{",
        "  FUN_00112233(param_1 + 0x20);",
        "  local_4 = DAT_00abcdef;",
        "  (**(code **)(param_1 + 0x18))(param_1);",
        "  FUN_00445566(param_1 + 0x20);",
        "}",
    ]
    inventory = module._inventory_body(100, body)
    assert inventory["unique_direct_callees"] == ["FUN_00112233", "FUN_00445566"]
    assert inventory["unique_global_references"] == ["DAT_00abcdef"]
    assert inventory["hex_offset_frequency"] == {"0x18": 1, "0x20": 2}
    assert inventory["potential_indirect_call_sites"] == [
        {"line": 104, "text": "(**(code **)(param_1 + 0x18))(param_1);"}
    ]


def test_documentation_does_not_promote_probe_output_to_provider_proof() -> None:
    text = DOC.read_text(encoding="utf-8")
    for token in (
        "raw navigation inventory",
        "not a positive provider-ownership contract",
        "FUN_0074f560",
        "SHIFT.exe.c",
        "pointer provenance",
        "PhysX",
        "NEXT_STEP",
    ):
        assert token in text
