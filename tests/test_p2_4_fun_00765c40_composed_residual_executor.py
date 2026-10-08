import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/p2_4_fun_00765c40_composed_residual_executor.json"
HEADER = ROOT / "native_runtime/include/shift_fun_00765c40_composed_residual_executor.hpp"
CMAKE = ROOT / "native_runtime/cmake/p2_4_fun_00765c40.cmake"
DOC = ROOT / "docs/P2_4_FUN_00765C40_COMPOSED_RESIDUAL_EXECUTOR.md"


def test_composed_residual_executor_keeps_exact_order_and_boundaries() -> None:
    payload = json.loads(EVIDENCE.read_text())
    assert payload["format"] == "SHIFT.Fun00765c40ComposedResidualExecutor/2"
    assert payload["ready"] is True
    assert payload["native_stage_order"] == ["WheelPlaneStateRefresh","SelectedWorldPositionTransform","SceneQuery","QueryCacheAndScalarCommit","WheelStateIndexSourceCommit","WheelJobQueueExecution","Fun007584f0PersistentMutation","PositiveLoadCountCommit","WheelPairStateRefresh","ContactArraySweep","OptionalBodyAccumulatorSweep"]
    native_owned = payload["native_owned_inputs"]
    assert native_owned["selected_bmw_query_miss_fallback"] is True
    assert native_owned["query_miss_fallback_explicit_input_removed"] is True
    assert native_owned["retail_f32_to_f64_bits"] == "0x3fb99999a0000000"
    assert native_owned["fun_007584f0_interpolation_formula"] is True
    assert native_owned["fun_007584f0_interpolation_explicit_scalar_removed"] is True
    assert native_owned["fun_007584f0_interpolation_argument_count"] == 4
    boundaries = payload["explicit_boundaries"]
    assert boundaries["scene_query_provider_external"] is True
    assert boundaries["wheel_job_formula_external"] is True
    assert boundaries["fun_007584f0_positive_qword_payloads_external"] is True
    assert boundaries["fun_007584f0_interpolation_scalar_external"] is False
    assert boundaries["contact_body_predicates_and_vectors_external"] is True
    compatibility = payload["compatibility"]
    assert compatibility["legacy_persistent_write_interpolation_result_field_retained"] is True
    assert compatibility["legacy_persistent_write_interpolation_result_consumed_by_composed_executor"] is False
    assert compatibility["residual_producer_handoff_format_changed"] is False
    scope = payload["scope"]
    assert scope["end_to_end_native_orchestration_path_present"] is True
    assert scope["complete_FUN_00765c40_internalized"] is False
    assert scope["top_level_FUN_00765c40_provider_removed"] is False
    assert scope["external_provider_count_after"] == 7


def test_header_calls_existing_native_stages_in_one_path() -> None:
    text = HEADER.read_text()
    for needle in ["SHIFT.Fun00765c40ComposedResidualExecutor/2","materialize_fun_00765c40_wheel_plane_refresh_stage","execute_fun_00765c40_selected_bmw_world_position","execute_fun_00765c40_scene_query_stage","materialize_fun_00752fa0_wheel_state_assignment","execute_fun_00765c40_wheel_job_scheduling","execute_fun_007584f0_interpolation_native","materialize_fun_007584f0_persistent_write_stage","fun_00765c40_positive_load_term_count","materialize_fun_00765c40_wheel_pair_refresh_stage","materialize_fun_00765c40_contact_array_sweep_stage","execute_fun_00765c40_contact_body_accumulation","materialize_fun_00765c40_bounded_state_tail","execute_fun_00765c40_optional_body_accumulator_sweep","result.executed_stage_order = kFun00765c40ResidualStageOrder"]:
        assert needle in text
    assert "selected_bmw_m3_e36_fun_00765c40_query_fallback()" in text
    assert "double query_miss_fallback" not in text
    assert "inputs.query_miss_fallback" not in text
    assert "persistent_write_inputs.interpolation_result =" in text
    assert "result.persistent_write_interpolation.value" in text
    assert "inputs.persistent_write.interpolation_result" not in text


def test_cmake_and_docs_keep_provider_removal_fail_closed() -> None:
    cmake = CMAKE.read_text()
    assert "shift_runtime_fun_00765c40_composed_residual_executor_check" in cmake
    assert "native-physics-phase" not in cmake
    doc = DOC.read_text()
    assert "query miss fallback is no longer an explicit composed input" in doc
    assert "precomputed `FUN_007584f0` interpolation scalar is no longer consumed" in doc
    assert "complete `FUN_00765c40` internalization remains false" in doc
    assert "top-level `FUN_00765c40` provider remains present" in doc
    assert "external provider count remains 7" in doc
