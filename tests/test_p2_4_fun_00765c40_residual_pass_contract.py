from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/p2_4_fun_00765c40_residual_pass_contract.json"
OWNERSHIP = ROOT / "evidence/fun_00765c40_residual_ownership_frontier.json"
WRITE_SURFACE = ROOT / "evidence/fun_00765c40_direct_machine_write_surface.json"
COLLISION = ROOT / "evidence/fun_0074f560_collision_provider_machine_proof.json"
HEADER = ROOT / "native_runtime/include/shift_fun_00765c40_residual_pass_contract.hpp"
CMAKE = ROOT / "native_runtime/cmake/p2_4_fun_00765c40.cmake"
PHASE753 = ROOT / "native_runtime/cmake/phase753.cmake"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_p2_4_consumes_completed_p1_2_handoff_fail_closed() -> None:
    native = _json(EVIDENCE)
    owner = _json(OWNERSHIP)
    assert native["format"] == "SHIFT.Fun00765c40ResidualPassContract/1"
    assert native["ready"] is True
    assert native["authority"]["ownership_handoff"] == owner["format"]
    assert owner["ready"] is True
    assert owner["completion_gate"]["p1_2_complete"] is True
    assert owner["completion_gate"]["fun_00765c40_provider_removal_authorized"] is True
    assert native["scope"]["complete_FUN_00765c40_internalized"] is False
    assert native["scope"]["top_level_FUN_00765c40_provider_removed"] is False
    assert native["scope"]["external_provider_count_before"] == 7
    assert native["scope"]["external_provider_count_after"] == 7


def test_p2_4_pins_only_the_proven_lower_scene_query_boundary() -> None:
    native = _json(EVIDENCE)["scene_query_boundary"]
    collision = _json(COLLISION)["provider_dispatch"]
    assert native["provider_global_pointer"] == collision["provider_global_pointer"]
    assert native["vtable_slot"] == "+" + collision["virtual_slot_offset"]
    assert native["surface_record_stride"] == "0x58"
    assert native["typed_external_boundary_required"] is True
    assert native["physical_implementation_internalized"] is False
    assert native["guessed_track_query_allowed"] is False

    header = HEADER.read_text(encoding="utf-8")
    assert "0x00c133ac" in header
    assert "0x1c0u" in header
    assert "Fun00765c40SceneQueryBoundary" in header
    assert "guessed track/scene query" in header


def test_p2_4_native_state_geometry_matches_machine_surface() -> None:
    native = _json(EVIDENCE)["native_state_surfaces"]
    machine = _json(WRITE_SURFACE)
    groups = {group["kind"]: group for group in machine["direct_write_groups"]}

    assert native["wheel_loop_a_offsets"] == groups["wheel_qword_loop_a"]["offsets"]
    assert native["wheel_pair_loop_b_offsets"] == groups["wheel_qword_pair_loop_b"]["offsets"]
    assert native["contact_record_pointer_array"]["base"] == groups["contact_record_pointer_array"]["base_offset"]
    assert native["contact_record_pointer_array"]["count"] == groups["contact_record_pointer_array"]["count"]
    assert native["contact_scalar_array"]["base"] == groups["contact_scalar_qword_array"]["base_offset"]
    assert native["contact_scalar_array"]["count"] == groups["contact_scalar_qword_array"]["count"]
    assert native["positive_load_count"] == "+0x407c"


def test_p2_4_stage_order_keeps_queue_before_load_count_and_contact_sweeps() -> None:
    stages = _json(EVIDENCE)["retail_stage_order"]
    assert stages.index("scene_query") < stages.index("query_cache_and_scalar_commit")
    assert stages.index("wheel_state_index_source_commit") < stages.index("wheel_job_queue_execution")
    assert stages.index("wheel_job_queue_execution") < stages.index("FUN_007584f0_persistent_mutation")
    assert stages.index("FUN_007584f0_persistent_mutation") < stages.index("positive_load_count_commit")
    assert stages.index("positive_load_count_commit") < stages.index("contact_array_sweep")
    assert stages[-1] == "optional_BODY_accumulator_sweep"


def test_p2_4_native_helpers_are_executable_but_removal_gate_remains_closed() -> None:
    native = _json(EVIDENCE)
    helpers = native["native_helpers"]
    assert helpers["scene_query_and_0x38dc_0x38e0_commit_internalized"] is True
    assert helpers["FUN_00752fa0_wheel_assignment_internalized"] is True
    assert helpers["positive_load_count_internalized"] is True
    assert helpers["remaining_stage_arithmetic_internalized"] is False

    header = HEADER.read_text(encoding="utf-8")
    assert "Fun00765c40SceneQueryProvider" in header
    assert "execute_fun_00765c40_scene_query_stage" in header
    assert "project_fun_00765c40_query_input_scalar" in header
    assert "materialize_fun_00752fa0_wheel_state_assignment" in header
    assert "fun_00765c40_positive_load_term_count" in header
    assert "value > 0.0" in header


def test_p2_4_cmake_uses_stable_blocker_module_after_phase753() -> None:
    phase753 = PHASE753.read_text(encoding="utf-8")
    cmake = CMAKE.read_text(encoding="utf-8")
    assert "include(${CMAKE_CURRENT_LIST_DIR}/p2_4_fun_00765c40.cmake)" in phase753
    assert "shift_runtime_fun_00765c40_residual_pass_contract_check" in cmake
    assert "phase754" not in cmake.lower()
