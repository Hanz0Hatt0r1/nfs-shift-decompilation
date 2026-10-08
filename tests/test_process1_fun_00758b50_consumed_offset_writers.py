from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/ghidra/trace_fun_00758b50_consumed_offset_writers.py"
DOC = ROOT / "docs/PROCESS_1_FUN_00758B50_CONSUMED_OFFSET_WRITERS.md"


def _module():
    spec = importlib.util.spec_from_file_location("fun00758b50_writer_trace", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _inventory() -> dict:
    return {
        "format": "SHIFT.Fun00758b50InputSurfaceInventory/1",
        "inventory": {
            "offset_reference_sites": [
                {"line": 10, "offset": "0x538", "appears_on_assignment_lhs": False},
                {"line": 11, "offset": "0x538", "appears_on_assignment_lhs": False},
                {"line": 12, "offset": "0x528", "appears_on_assignment_lhs": True},
                {"line": 13, "offset": "0x940", "appears_on_assignment_lhs": False},
            ]
        },
    }


def test_constants_are_pinned() -> None:
    module = _module()
    assert module.FORMAT == "SHIFT.Fun00758b50ConsumedOffsetWriterCandidates/1"
    assert module.TARGET == "FUN_00758b50"
    assert module.INPUT_FORMAT == "SHIFT.Fun00758b50InputSurfaceInventory/1"
    assert module.PINNED_SOURCE_SHA256 == "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
    assert module.RETAIL_EXECUTABLE_SHA256 == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"


def test_candidate_offsets_keep_only_read_only_target_offsets() -> None:
    module = _module()
    candidates = module._candidate_offsets(_inventory())
    assert [row["offset"] for row in candidates] == ["0x538", "0x940"]
    assert candidates[0]["target_reference_count"] == 2
    assert candidates[0]["target_assignment_lhs_count"] == 0


def test_extract_functions_and_rank_direct_writers() -> None:
    module = _module()
    lines = [
        "void FUN_00111111(void *this)",
        "{",
        "  *(double *)((int)this + 0x538) = 1.0;",
        "}",
        "void FUN_00222222(void *param_1)",
        "{",
        "  local_4 = *(int *)((int)param_1 + 0x940);",
        "}",
        "void FUN_00333333(void *this)",
        "{",
        "  *(int *)((int)this + 0x940) = 1;",
        "  *(int *)((int)this + 0x538) = 2;",
        "}",
        "void FUN_00758b50(void *this)",
        "{",
        "  local_8 = *(double *)((int)this + 0x538);",
        "  if (*(char *)((int)this + 0x940) == 0) {}",
        "}",
    ]
    functions = module._extract_functions(lines)
    assert [row["name"] for row in functions] == [
        "FUN_00111111",
        "FUN_00222222",
        "FUN_00333333",
        "FUN_00758b50",
    ]
    ranked = module._scan_direct_writers(functions, module._candidate_offsets(_inventory()))
    by_offset = {row["offset"]: row for row in ranked}
    assert by_offset["0x538"]["direct_assignment_writer_functions"] == [
        "FUN_00111111",
        "FUN_00333333",
    ]
    assert by_offset["0x940"]["direct_assignment_writer_functions"] == ["FUN_00333333"]
    assert ranked[0]["offset"] == "0x940"


def test_numeric_offset_match_does_not_promote_control_semantics() -> None:
    text = DOC.read_text(encoding="utf-8")
    for token in (
        "numeric offset",
        "receiver/base provenance",
        "alias-complete",
        "throttle/brake/steering",
        "P1.3",
        "provider count remains **7**",
        "NEXT_STEP",
    ):
        assert token in text
