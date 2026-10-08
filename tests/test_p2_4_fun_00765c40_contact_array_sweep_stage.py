import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/p2_4_fun_00765c40_contact_array_sweep_stage.json"
HEADER = ROOT / "native_runtime/include/shift_fun_00765c40_contact_array_sweep_stage.hpp"
CMAKE = ROOT / "native_runtime/cmake/p2_4_fun_00765c40.cmake"
DOC = ROOT / "docs/P2_4_FUN_00765C40_CONTACT_ARRAY_SWEEP_STAGE.md"


def test_contact_array_sweep_contract_is_exact_and_fail_closed() -> None:
    payload = json.loads(EVIDENCE.read_text())
    assert payload["format"] == "SHIFT.Fun00765c40ContactArraySweepStage/1"
    assert payload["ready"] is True

    surface = payload["retail_write_surface"]
    assert surface["slot_count"] == 12
    assert surface["record_pointer_array"] == {
        "site": "0x00766120",
        "base": "+0x35c8",
        "last": "+0x35f4",
        "stride": 4,
        "width": "dword",
    }
    assert surface["scalar_qword_array"] == {
        "site": "0x0076618b",
        "base": "+0x35f8",
        "last": "+0x3650",
        "stride": 8,
        "width": "qword",
    }
    assert surface["semantic_names_proven"] is False

    native = payload["native_consumption"]
    assert native["record_pointer_payloads_are_explicit_inputs"] is True
    assert native["scalar_qword_payloads_are_explicit_inputs"] is True
    assert native["payloads_preserved_bit_for_bit"] is True
    assert native["all_24_array_destinations_native_owned"] is True
    assert native["per_slot_producer_arithmetic_internalized"] is False
    assert native["bounded_state_tail_offsets_0x3660_0x3678_internalized"] is False

    scope = payload["scope"]
    assert scope["complete_FUN_00765c40_internalized"] is False
    assert scope["top_level_FUN_00765c40_provider_removed"] is False
    assert scope["external_provider_count_after"] == 7


def test_native_header_pins_geometry_widths_and_order() -> None:
    text = HEADER.read_text()
    assert "SHIFT.Fun00765c40ContactArraySweepStage/1" in text
    for value in ("0x35c8u", "0x35f4u", "0x35f8u", "0x3650u"):
        assert value in text
    assert "std::uint32_t" in text
    assert "std::uint64_t" in text
    assert "WheelPairStateRefresh" in text
    assert "ContactArraySweep" in text
    assert "computed.record_pointer_tokens" in text
    assert "computed.scalar_qword_bits" in text


def test_stable_p2_4_cmake_and_docs_keep_tail_separate() -> None:
    cmake = CMAKE.read_text()
    assert "shift_runtime_fun_00765c40_contact_array_sweep_stage_check" in cmake
    assert "native-physics-phase" not in cmake

    doc = DOC.read_text()
    assert "+0x3660/+0x3668/+0x3670/+0x3678" in doc
    assert "external provider count remains 7" in doc
