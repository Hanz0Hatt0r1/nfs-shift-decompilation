from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HEADER = ROOT / "native_runtime" / "include" / "shift_bmw_offset33b_native_selector.hpp"
SOURCE = ROOT / "native_runtime" / "src" / "bmw_offset33b_native_selector.cpp"
CPP_CHECK = ROOT / "native_runtime" / "tests" / "bmw_offset33b_native_selector_check.cpp"
PHASE = ROOT / "native_runtime" / "cmake" / "phase714.cmake"
PHASE707 = ROOT / "native_runtime" / "cmake" / "phase707.cmake"
DOC = ROOT / "docs" / "PHASE714_BMW_OFFSET33B_NATIVE_SELECTOR_BIND.md"


def test_phase714_keeps_outer_vehicle_root_separate_from_vhf_root():
    header = HEADER.read_text(encoding="utf-8")
    source = SOURCE.read_text(encoding="utf-8")

    assert '"SHIFT.NativeBMWOffset33bSelector/1"' in header
    assert "struct BmwBody0OuterVehicleRootBind" in header
    assert "body0_local_to_outer_vehicle_root" in header
    assert "ProvenBmwBody0BindFrame" not in header
    assert "body0_local_to_vhf_vehicle_root" not in header
    assert "outer Vehicle root -> VHF vehicle root remains an independent blocker" in source


def test_phase714_binds_deterministic_silverstone_selector():
    source = SOURCE.read_text(encoding="utf-8")

    assert "selector.ready = true;" in source
    assert "selector.use_drift_cgheight_scale = false;" in source
    assert "selector.player_difficulty = 1u;" in source
    assert "selector.player_difficulty > 2u" in source
    assert "BMW offset33b selector is not bound" in source
    assert "BMW offset33b selector requires Player Difficulty 0..2" in source


def test_phase714_preserves_all_selector_family_numeric_cases():
    source = SOURCE.read_text(encoding="utf-8")
    check = CPP_CHECK.read_text(encoding="utf-8")

    assert "0.004956085581085581085581085581085581" in source
    assert "-0.000689602064602064602064602064602065" in source
    assert "0.018129356754356754356754356754356754" in source
    assert "0.011470862470862470862470862470862471" in source
    assert "cgheight_scale = 0.25;" in source
    assert "cgheight_scale = 0.75;" in source
    assert "cgheight_scale = 0.6;" in source

    assert "for (std::uint32_t difficulty = 0u; difficulty <= 2u; ++difficulty)" in check
    assert "normal0" in check and "normal1" in check and "normal2" in check
    assert "rejected_unbound" in check
    assert "rejected_difficulty3" in check


def test_phase714_is_wired_into_native_cmake_chain():
    phase = PHASE.read_text(encoding="utf-8")
    phase707 = PHASE707.read_text(encoding="utf-8")

    assert "src/bmw_offset33b_native_selector.cpp" in phase
    assert "tests/bmw_offset33b_native_selector_check.cpp" in phase
    assert "shift_runtime_bmw_offset33b_native_selector" in phase
    assert "include(${CMAKE_CURRENT_LIST_DIR}/phase714.cmake)" in phase707


def test_phase714_documents_positive_and_fail_closed_handoff():
    doc = DOC.read_text(encoding="utf-8")

    assert "BMW_numeric_offset33b_ready                      = true" in doc
    assert "BODY0_to_outer_vehicle_root_numeric_matrix_ready = true" in doc
    assert "outer_vehicle_root_to_VHF_vehicle_root_ready = false" in doc
    assert "BODY0_bind_frame_proof_ready                 = false" in doc
    assert "vehicle_world_transform_ready                = false" in doc
