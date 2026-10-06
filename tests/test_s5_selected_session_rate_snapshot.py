from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "native_capture/selected_session_rate_snapshot.cpp"
CMAKE = ROOT / "native_capture/CMakeLists.txt"


def test_snapshot_reads_only_source_backed_rate_anchors():
    source = SOURCE.read_text(encoding="utf-8")

    assert "kPreferredImageBase = 0x00400000u" in source
    assert "kExpectedPeTimestamp = 0x4af2ddcfu" in source
    assert "kExpectedImageSize = 0x00995000u" in source
    assert "kPhysicsManagerRva = 0x00c104e0u - kPreferredImageBase" in source
    assert "kPhysicsManagerVtableRva = 0x00b04524u - kPreferredImageBase" in source
    assert "kPhysicsTweakerRva = 0x00c12c40u - kPreferredImageBase" in source
    assert "kPhysicsTweakerTickRateRva = 0x00c130d2u - kPreferredImageBase" in source
    assert "kPhysicsTweakerLoadAnchorRva = 0x00710b06u - kPreferredImageBase" in source
    assert "kLoadedRateApplyAnchorRva = 0x00710c12u - kPreferredImageBase" in source
    assert "kPostPhysicsTweakerLoadFlagOffset = 0x2abu" in source
    assert "kManagerRateOffset = 0x388u" in source
    assert "kManagerReciprocalOffset = 0x38cu" in source
    assert "kManagerRateOver30Offset = 0x390u" in source
    assert "kManagerThirtyOverRateOffset = 0x394u" in source


def test_snapshot_requires_exact_retail_identity_and_loaded_rate_application():
    source = SOURCE.read_text(encoding="utf-8")

    assert "physics_tweaker_load_anchor_matches" in source
    assert "loaded_rate_apply_anchor_matches" in source
    assert "nt.FileHeader.TimeDateStamp == kExpectedPeTimestamp" in source
    assert "nt.OptionalHeader.SizeOfImage == kExpectedImageSize" in source
    assert "value.manager_vtable == expected_vtable" in source
    assert "value.post_load_flag == 1" in source
    assert "value.loaded_equals_manager_rate" in source
    assert "static_cast<std::int32_t>(value.loaded_rate_hz) == value.manager_rate_hz" in source
    assert "value.relationships_valid" in source
    assert "close_float(value.reciprocal, 1.0 / rate)" in source
    assert "close_float(value.rate_over_30, rate / 30.0)" in source
    assert "close_float(value.thirty_over_rate, 30.0 / rate)" in source


def test_snapshot_distinguishes_observed_180_from_constructor_default_guess():
    source = SOURCE.read_text(encoding="utf-8")

    assert '"constructor_default_180_used_as_admission_basis\\\": false' in source
    assert '"current_manager_rate_is_assumed_constant\\\": false' in source
    assert '"retail_inner_substep_execution_admitted\\\": false' in source
    assert "default_180.loaded_rate_hz = 180" in source
    assert "default_180.manager_rate_hz = 180" in source
    assert "post-load observed 180 Hz was incorrectly rejected" in source
    assert "global/manager rate mismatch was admitted" in source


def test_self_test_is_not_an_admission_artifact():
    source = SOURCE.read_text(encoding="utf-8")

    assert '"self-test-passed"' in source
    assert '"admission_eligible\\\": " << (admission_eligible ? "true" : "false")' in source
    assert "if (options.self_test) return run_self_test(options);" in source


def test_snapshot_is_a_separate_win32_target():
    cmake = CMAKE.read_text(encoding="utf-8")
    assert (
        "add_executable(shift_selected_session_rate_snapshot "
        "selected_session_rate_snapshot.cpp)"
    ) in cmake
    assert "shift_selected_session_rate_snapshot PROPERTY" in cmake
    assert "shift_d3d9_capture.cpp" not in SOURCE.read_text(encoding="utf-8")
