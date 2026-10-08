from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/p2_4_fun_00765c40_wheel_pair_refresh.json"
WRITE_SURFACE = ROOT / "evidence/fun_00765c40_direct_machine_write_surface.json"
HEADER = ROOT / "native_runtime/include/shift_fun_00765c40_wheel_pair_refresh.hpp"
TEST = ROOT / "native_runtime/tests/fun_00765c40_wheel_pair_refresh_check.cpp"
CMAKE = ROOT / "native_runtime/cmake/p2_4_fun_00765c40.cmake"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_p2_4_wheel_pair_refresh_pins_machine_write_geometry() -> None:
    native = _json(EVIDENCE)
    machine = _json(WRITE_SURFACE)
    groups = {group["kind"]: group for group in machine["direct_write_groups"]}
    assert native["format"] == "SHIFT.Fun00765c40WheelPairRefresh/1"
    assert native["ready"] is True
    assert native["destination_pairs"] == [
        ["+0x0ba0", "+0x0ba8"],
        ["+0x1620", "+0x1628"],
        ["+0x20a0", "+0x20a8"],
        ["+0x2b20", "+0x2b28"],
    ]
    flattened = [item for pair in native["destination_pairs"] for item in pair]
    assert flattened == groups["wheel_qword_pair_loop_b"]["offsets"]
    assert native["pair_stride"] == "0x0a80"


def test_p2_4_wheel_pair_first_lane_uses_exact_float_clamp_max_path() -> None:
    lane = _json(EVIDENCE)["first_lane"]
    assert lane["source_a"] == "float(HDVehicle+0x8)"
    assert lane["source_b"] == "float(HDVehicle+0x28)"
    assert lane["same_value_written_to_all_four_pairs"] is True
    assert lane["arithmetic_internalized"] is True

    header = HEADER.read_text(encoding="utf-8")
    native_test = TEST.read_text(encoding="utf-8")
    assert "static_cast<float>(value)" in header
    assert "narrowed <= 0.0f" in header
    assert "narrowed >= 1.0f" in header
    assert "std::max(source_a, source_b)" in header
    assert "selected * 100.0f" in header
    assert "75.0" in native_test
    assert "100.0" in native_test


def test_p2_4_wheel_pair_sqrt_lane_remains_explicit() -> None:
    lane = _json(EVIDENCE)["second_lane"]
    assert lane["same_value_written_to_all_four_pairs"] is True
    assert lane["sqrt_operand_proven"] is False
    assert lane["arithmetic_internalized"] is False
    assert lane["source_computed_result_is_explicit_input"] is True
    header = HEADER.read_text(encoding="utf-8")
    assert "double sqrt_lane" in header
    assert "pair[1] = inputs.sqrt_lane" in header


def test_p2_4_wheel_pair_refresh_remains_fail_closed_for_provider_removal() -> None:
    scope = _json(EVIDENCE)["scope"]
    assert scope["wheel_pair_refresh_internalized"] is True
    assert scope["complete_FUN_00765c40_internalized"] is False
    assert scope["top_level_FUN_00765c40_provider_removed"] is False
    assert scope["external_provider_count_before"] == 7
    assert scope["external_provider_count_after"] == 7


def test_p2_4_wheel_pair_refresh_is_chained_into_stable_cmake() -> None:
    cmake = CMAKE.read_text(encoding="utf-8")
    assert "shift_runtime_fun_00765c40_wheel_pair_refresh_check" in cmake
    assert "phase754" not in cmake.lower()
