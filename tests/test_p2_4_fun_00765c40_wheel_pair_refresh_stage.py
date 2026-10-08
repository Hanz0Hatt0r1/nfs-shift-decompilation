import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/p2_4_fun_00765c40_wheel_pair_refresh_stage.json"
HEADER = ROOT / "native_runtime/include/shift_fun_00765c40_wheel_pair_refresh_stage.hpp"
CMAKE = ROOT / "native_runtime/cmake/p2_4_fun_00765c40.cmake"
DOC = ROOT / "docs/P2_4_FUN_00765C40_WHEEL_PAIR_REFRESH_STAGE.md"


def test_p2_4_wheel_pair_refresh_contract_is_fail_closed() -> None:
    payload = json.loads(EVIDENCE.read_text())
    assert payload["format"] == "SHIFT.Fun00765c40WheelPairRefreshStage/1"
    assert payload["ready"] is True

    surface = payload["retail_write_surface"]
    assert surface["sites"] == ["0x0076606b", "0x00766073"]
    assert surface["wheel_count"] == 4
    assert surface["stride"] == "0x0a80"
    assert surface["qword_pairs"] == [
        ["+0x0ba0", "+0x0ba8"],
        ["+0x1620", "+0x1628"],
        ["+0x20a0", "+0x20a8"],
        ["+0x2b20", "+0x2b28"],
    ]
    assert surface["semantic_name_proven"] is False

    native = payload["native_consumption"]
    assert native["source_computed_qword_payloads_are_explicit_inputs"] is True
    assert native["qword_payloads_preserved_bit_for_bit"] is True
    assert native["all_eight_destinations_native_owned"] is True
    assert native["preceding_x87_arithmetic_internalized"] is False

    scope = payload["scope"]
    assert scope["p2_4_wheel_pair_write_stage_internalized"] is True
    assert scope["complete_FUN_00765c40_internalized"] is False
    assert scope["top_level_FUN_00765c40_provider_removed"] is False
    assert scope["external_provider_count_before"] == 7
    assert scope["external_provider_count_after"] == 7


def test_native_header_pins_exact_geometry_order_and_bit_preservation() -> None:
    text = HEADER.read_text()
    assert "SHIFT.Fun00765c40WheelPairRefreshStage/1" in text
    for value in (
        "0x0ba0u", "0x0ba8u", "0x1620u", "0x1628u",
        "0x20a0u", "0x20a8u", "0x2b20u", "0x2b28u",
    ):
        assert value in text
    assert "0x0a80u" in text
    assert "std::uint64_t" in text
    assert "state.qword_bits = computed.qword_bits" in text
    assert "PositiveLoadCountCommit" in text
    assert "WheelPairStateRefresh" in text


def test_stable_p2_4_cmake_and_docs_keep_provider_removal_closed() -> None:
    cmake = CMAKE.read_text()
    assert "shift_runtime_fun_00765c40_wheel_pair_refresh_stage_check" in cmake
    assert "native-physics-phase" not in cmake

    doc = DOC.read_text()
    assert "external provider count remains 7" in doc
    assert "Remove the top-level `FUN_00765c40` callback only after" in doc
