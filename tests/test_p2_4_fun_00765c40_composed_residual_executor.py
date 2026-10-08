import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/p2_4_fun_00765c40_composed_residual_executor.json"
HEADER = ROOT / "native_runtime/include/shift_fun_00765c40_composed_residual_executor.hpp"
CMAKE = ROOT / "native_runtime/cmake/p2_4_fun_00765c40.cmake"
DOC = ROOT / "docs/P2_4_FUN_00765C40_COMPOSED_RESIDUAL_EXECUTOR.md"


def test_composed_residual_executor_keeps_exact_order_and_boundaries() -> None:
    payload = json.loads(EVIDENCE.read_text())
    assert payload["format"] == "SHIFT.Fun00765c40ComposedResidualExecutor/1"
    assert payload["ready"] is True
    assert payload["native_stage_order"] == ["WheelPlaneStateRefresh","SelectedWorldPositionTransform","SceneQuery","QueryCacheAndScalarCommit","WheelStateIndexSourceCommit","WheelJobQueueExecution","Fun007584f0PersistentMutation","PositiveLoadCountCommit","WheelPairStateRefresh","ContactArraySweep","OptionalBodyAccumulatorSweep"]
    boundaries = payload["explicit_boundaries"]
    assert boundaries["scene_query_provider_external"] is True
    assert boundaries["wheel_job_formula_external"] is True
    assert boundaries["fun_007584f0_computed_payloads_external"] is True
    assert boundaries["contact_body_predicates_and_vectors_external"] is True
    scope = payload["scope"]
    assert scope["end_to_end_native_orchestration_path_present"] is True
    assert scope["complete_FUN_00765c40_internalized"] is False
    assert scope["top_level_FUN_00765c40_provider_removed"] is False
    assert scope["external_provider_count_after"] == 7


def test_header_calls_existing_native_stages_in_one_path() -> None:
    text = HEADER.read_text()
    for needle in ["SHIFT.Fun00765c40ComposedResidualExecutor/1","materialize_fun_00765c40_wheel_plane_refresh_stage","execute_fun_00765c40_selected_bmw_world_position","execute_fun_00765c40_scene_query_stage","materialize_fun_00752fa0_wheel_state_assignment","execute_fun_00765c40_wheel_job_scheduling","materialize_fun_007584f0_persistent_write_stage","fun_00765c40_positive_load_term_count","materialize_fun_00765c40_wheel_pair_refresh_stage","materialize_fun_00765c40_contact_array_sweep_stage","execute_fun_00765c40_contact_body_accumulation","materialize_fun_00765c40_bounded_state_tail","execute_fun_00765c40_optional_body_accumulator_sweep","result.executed_stage_order = kFun00765c40ResidualStageOrder"]:
        assert needle in text


def test_cmake_and_docs_keep_provider_removal_fail_closed() -> None:
    cmake = CMAKE.read_text()
    assert "shift_runtime_fun_00765c40_composed_residual_executor_check" in cmake
    assert "native-physics-phase" not in cmake
    doc = DOC.read_text()
    assert "complete `FUN_00765c40` internalization remains false" in doc
    assert "top-level `FUN_00765c40` provider remains present" in doc
    assert "external provider count remains 7" in doc
