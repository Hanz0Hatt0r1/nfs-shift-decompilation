import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/p2_4_fun_00765c40_wheel_plane_refresh_stage.json"
HEADER = ROOT / "native_runtime/include/shift_fun_00765c40_wheel_plane_refresh_stage.hpp"
CMAKE = ROOT / "native_runtime/cmake/p2_4_fun_00765c40.cmake"
DOC = ROOT / "docs/P2_4_FUN_00765C40_WHEEL_PLANE_REFRESH_STAGE.md"


def test_wheel_plane_refresh_contract_is_exact_and_fail_closed() -> None:
    payload = json.loads(EVIDENCE.read_text())
    assert payload["format"] == "SHIFT.Fun00765c40WheelPlaneRefreshStage/1"
    assert payload["ready"] is True

    surface = payload["retail_write_surface"]
    assert surface["count"] == 4
    assert surface["base"] == "+0x0a70"
    assert surface["stride"] == "0x0a80"
    assert surface["offsets"] == ["+0x0a70", "+0x14f0", "+0x1f70", "+0x29f0"]
    assert surface["width"] == "qword"
    assert surface["semantic_name_proven"] is False
    assert surface["source_arithmetic_proven"] is False

    native = payload["native_consumption"]
    assert native["four_qword_inputs_are_explicit"] is True
    assert native["payloads_preserved_bit_for_bit"] is True
    assert native["destination_geometry_native_owned"] is True
    assert native["first_residual_stage_pinned"] is True
    assert native["source_arithmetic_internalized"] is False

    scope = payload["scope"]
    assert scope["complete_FUN_00765c40_internalized"] is False
    assert scope["top_level_FUN_00765c40_provider_removed"] is False
    assert scope["external_provider_count_after"] == 7


def test_native_header_pins_exact_geometry_and_order() -> None:
    text = HEADER.read_text()
    assert "SHIFT.Fun00765c40WheelPlaneRefreshStage/1" in text
    for value in ("0x0a70u", "0x14f0u", "0x1f70u", "0x29f0u"):
        assert value in text
    assert "std::uint64_t" in text
    assert "WheelPlaneStateRefresh" in text
    assert "return {computed};" in text


def test_stable_p2_4_cmake_and_docs_keep_provider_fail_closed() -> None:
    cmake = CMAKE.read_text()
    assert "shift_runtime_fun_00765c40_wheel_plane_refresh_stage_check" in cmake
    assert "native-physics-phase" not in cmake

    doc = DOC.read_text()
    assert "source arithmetic: remains external" in doc
    assert "external provider count: remains 7" in doc
