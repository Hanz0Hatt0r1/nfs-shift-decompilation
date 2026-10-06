from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "native_capture/selected_session_rate_snapshot.cpp"
CMAKE = ROOT / "native_capture/CMakeLists.txt"


def test_snapshot_reads_only_source_backed_rate_anchors():
    source = SOURCE.read_text(encoding="utf-8")

    assert "kPreferredImageBase = 0x00400000u" in source
    assert "kExpectedPeTimestamp = 0x4af2ddcfu" in source
    assert "kExpectedImageSize = 0x00995000u" in source
    assert "kPhysicsManagerRva" in source and "0x00c104e0u" in source
    assert "kPhysicsManagerVtableRva" in source and "0x00b04524u" in source
    assert "kPhysicsTweakerRva" in source and "0x00c12c40u" in source
    assert "kPhysicsTweakerTickRateRva" in source and "0x00c130d2u" in source
    assert "kPhysicsTweakerLoadAnchorRva" in source and "0x00710b06u" in source
    assert "kLoadedRateApplyAnchorRva" in source and "0x00710c12u" in source
    assert "kPostPhysicsTweakerLoadFlagOffset = 0x2abu" in source
    assert "kManagerRateOffset = 0x388u" in source
    assert "kManagerReciprocalOffset = 0x38cu" in source
    assert "kManagerRateOver30Offset = 0x390u" in source
    assert "kManagerThirtyOverRateOffset = 0x394u" in source


def test_snapshot_requires_exact_retail_identity_before_loaded_rate_observation():
    source = SOURCE.read_text(encoding="utf-8")

    assert "physics_tweaker_load_anchor_matches" in source
    assert "loaded_rate_apply_anchor_matches" in source
    assert "nt.FileHeader.TimeDateStamp == kExpectedPeTimestamp" in source
    assert "nt.OptionalHeader.SizeOfImage == kExpectedImageSize" in source
    assert "value.manager_vtable == expected_vtable" in source
    assert "value.post_load_flag == 1" in source
    assert "value.loaded_rate_hz > 0" in source
    assert "value.loaded_rate_ready" in source


def test_current_manager_domain_is_observed_but_not_loaded_rate_prerequisite():
    source = SOURCE.read_text(encoding="utf-8")

    assert "value.loaded_equals_manager_rate" in source
    assert "value.relationships_valid" in source
    assert "close_float(value.reciprocal, 1.0 / rate)" in source
    assert "close_float(value.rate_over_30, rate / 30.0)" in source
    assert "close_float(value.thirty_over_rate, 30.0 / rate)" in source
    assert "equality is an observation that chooses the next blocker" in source
    assert "sample.loaded_rate_hz = 240" in source
    assert "sample.manager_rate_hz = 210" in source
    assert "!sample.loaded_equals_manager_rate" in source


def test_snapshot_never_promotes_constructor_default_or_inner_execution():
    source = SOURCE.read_text(encoding="utf-8")

    assert "constructor_default_180_used_as_admission_basis" in source
    assert "current_manager_rate_is_assumed_constant" in source
    assert "retail_inner_substep_execution_admitted" in source
    assert "sample.loaded_rate_hz = 180" not in source


def test_self_test_proves_separation_but_is_never_admission_eligible():
    source = SOURCE.read_text(encoding="utf-8")

    assert "self-test-passed" in source
    assert "if (options.self_test) return run_self_test(options);" in source
    assert "sample.loaded_rate_ready" in source
    assert "!sample.loaded_equals_manager_rate" in source
    assert "effective_admission_eligible" in source
    assert "admission_eligible && !self_test" in source
    assert "Synthetic validation must never produce an artifact" in source


def test_snapshot_is_a_separate_win32_target():
    cmake = CMAKE.read_text(encoding="utf-8")
    assert (
        "add_executable(shift_selected_session_rate_snapshot "
        "selected_session_rate_snapshot.cpp)"
    ) in cmake
    assert "shift_selected_session_rate_snapshot PROPERTY" in cmake
    assert "shift_d3d9_capture.cpp" not in SOURCE.read_text(encoding="utf-8")
