from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "native_capture/selected_session_rate_snapshot.cpp"
CMAKE = ROOT / "native_capture/CMakeLists.txt"


def test_snapshot_reads_only_source_backed_rate_anchors():
    source = SOURCE.read_text(encoding="utf-8")

    assert "kPreferredImageBase = 0x00400000u" in source
    assert "kPhysicsManagerRva = 0x00c104e0u - kPreferredImageBase" in source
    assert "kPhysicsManagerVtableRva = 0x00b04524u - kPreferredImageBase" in source
    assert "kPhysicsTweakerTickRateRva = 0x00c130d2u - kPreferredImageBase" in source
    assert "kPostPhysicsTweakerLoadFlagOffset = 0x2abu" in source
    assert "kManagerRateOffset = 0x388u" in source
    assert "kManagerReciprocalOffset = 0x38cu" in source
    assert "kManagerRateOver30Offset = 0x390u" in source
    assert "kManagerThirtyOverRateOffset = 0x394u" in source


def test_snapshot_requires_post_load_owner_and_rate_relationships():
    source = SOURCE.read_text(encoding="utf-8")

    assert "value.manager_vtable == expected_vtable" in source
    assert "value.post_load_flag == 1" in source
    assert "value.loaded_rate_hz > 0" in source
    assert "value.manager_rate_hz > 0" in source
    assert "value.relationships_valid" in source
    assert "close_float(value.reciprocal, 1.0 / rate)" in source
    assert "close_float(value.rate_over_30, rate / 30.0)" in source
    assert "close_float(value.thirty_over_rate, 30.0 / rate)" in source


def test_snapshot_never_promotes_constructor_default_or_constant_manager_rate():
    source = SOURCE.read_text(encoding="utf-8")

    assert '"constructor_default_180_used_as_admission_basis\\\": false' in source
    assert '"current_manager_rate_is_assumed_constant\\\": false' in source
    assert '"retail_inner_substep_execution_admitted\\\": false' in source
    assert "sample.loaded_rate_hz = 240" in source
    assert "sample.manager_rate_hz = 240" in source
    assert "sample.loaded_rate_hz = 180" not in source
    assert "sample.manager_rate_hz = 180" not in source


def test_snapshot_is_a_separate_win32_target():
    cmake = CMAKE.read_text(encoding="utf-8")
    assert (
        "add_executable(shift_selected_session_rate_snapshot "
        "selected_session_rate_snapshot.cpp)"
    ) in cmake
    assert "shift_selected_session_rate_snapshot PROPERTY" in cmake
    assert "shift_d3d9_capture.cpp" not in SOURCE.read_text(encoding="utf-8")
