from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_00713630_reference_source.json"
HEADER = ROOT / "native_runtime/include/shift_fun_00713630_reference_source.hpp"
TEST = ROOT / "native_runtime/tests/fun_00713630_reference_source_check.cpp"
PHASE747 = ROOT / "native_runtime/cmake/phase747.cmake"
PHASE748 = ROOT / "native_runtime/cmake/phase748.cmake"


def test_phase748_evidence_freezes_machine_backed_writer() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun00713630ReferenceSource/1"
    assert payload["ready"] is True
    assert payload["platform_authority"] == "PC retail primary"
    assert payload["source"]["retail_executable_sha256"] == (
        "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    )
    spans = payload["source"]["machine_spans"]
    assert spans["FUN_00712940"]["sha256"] == (
        "5f39e507f181793de613158848251f35b20e098349c4d3fe28383df3793f12d4"
    )
    assert spans["FUN_00713630"]["sha256"] == (
        "2ae2558440bf633e3bd6e926c2a060451b5c8d630df7a2dbb94ce51e5f030590"
    )
    assert spans["FUN_007144a0"]["sha256"] == (
        "11dcc27639936fc13379f4e91f6a3d35697715ccfdce10c7865baf2f431308db"
    )
    assert spans["CRT_FCOS_wrapper"]["sha256"] == (
        "0de3a2479ceb44dc4eeb1eba23ab27c53407c3fd7eb2052f7fc9a7df1790dbbd"
    )
    assert spans["CRT_FSIN_wrapper"]["sha256"] == (
        "cae7003b4b9682164685955c7aa4c877b523f3ed0a72844b3b0c1d71312fb81f"
    )


def test_phase748_geometry_and_phase747_handoff_are_explicit() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    manager = payload["manager_geometry"]
    assert manager["participant_array"] == "+0x140"
    assert manager["participant_count"] == "+0x144"
    assert manager["cadence_counter"] == "+0x158"
    assert manager["record_stride"] == "0x1fa0"
    assert manager["active_byte"] == "+0x4e"
    assert manager["refresh_condition"] == "manager_counter % 3 == 0"

    participant = payload["participant_input"]
    assert participant["sample_base"] == "+0x2b10"
    assert participant["sample_count"] == 3
    assert participant["sample_stride"] == "0x0c"
    assert participant["angle"] == "+0x4b0 f32"

    writer = payload["writer_output"]
    assert writer["participant_plus_0x16b8"] == "0.0f"
    assert writer["participant_plus_0x2128"] == "primary aggregate"
    assert writer["participant_plus_0x212c"] == "secondary aggregate"
    assert writer["consumer"] == "SHIFT.Fun00766510SharedReferenceVector/1"


def test_phase748_active_cpp_keeps_earlier_runtime_inputs_unfrozen() -> None:
    header = HEADER.read_text(encoding="utf-8")
    test = TEST.read_text(encoding="utf-8")

    assert "SHIFT.Fun00713630ReferenceSource/1" in header
    assert "SHIFT.Fun00712940ReferenceAggregate/1" in header
    assert "kFun00713630ParticipantSampleBaseOffset = 0x2b10u" in header
    assert "kFun00713630ParticipantSampleCount = 3u" in header
    assert "kFun00713630ParticipantSampleStride = 0x0cu" in header
    assert "kFun00713630ParticipantAngleOffset = 0x4b0u" in header
    assert "Fun00766510ParticipantReferenceSource3f participant_source" in header
    assert "DAT_00c12eec" in header
    assert "DAT_00c12f04" in header
    assert "fsin" in header
    assert "fcos" in header
    assert "manager_counter % 3 == 0" in header
    assert "contact_response_provider_removed" in test
    assert "false" in test

    scope = json.loads(EVIDENCE.read_text(encoding="utf-8"))["scope"]
    assert scope["external_provider_count_before"] == 7
    assert scope["external_provider_count_after"] == 7
    assert scope["provider_count_reduced"] is False
    assert scope["contact_response_provider_removed"] is False
    assert scope["dynamic_writer_arithmetic_internalized"] is True
    assert scope["selected_session_constants_invented"] is False


def test_phase748_cmake_is_chained_after_phase747() -> None:
    phase747 = PHASE747.read_text(encoding="utf-8")
    phase748 = PHASE748.read_text(encoding="utf-8")
    assert "include(${CMAKE_CURRENT_LIST_DIR}/phase748.cmake)" in phase747
    assert "shift_runtime_fun_00713630_reference_source_check" in phase748
