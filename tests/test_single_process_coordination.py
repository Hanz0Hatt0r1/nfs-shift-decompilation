import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "docs/PLAYABLE_SLICE_SINGLE_PROCESS_INSTRUCTIONS_V5.md"
PROMPT = ROOT / "docs/PLAYABLE_SLICE_SINGLE_PROCESS_PROMPT_V5.md"
EXECUTION = ROOT / "evidence/playable_slice_single_process_execution.json"


def test_single_process_execution_contract_is_active_and_current() -> None:
    payload = json.loads(EXECUTION.read_text(encoding="utf-8"))
    frontier = payload["current_frontier"]

    assert payload["format"] == "SHIFT.PlayableSliceSingleProcessExecution/1"
    assert payload["status"] == "active"
    assert payload["execution_model"] == "single-process"
    assert payload["legacy_parallel_coordination_retired"] is True
    assert frontier["semantic_relation_contract"] == "SHIFT.OuterVehicleBMWVHFRootRelation/1"
    assert frontier["semantic_relation_ready"] is True
    assert frontier["outer_vhf_numeric_relation_contract"] == "SHIFT.BMWOuterVHFNumericRelation/1"
    assert frontier["outer_vhf_numeric_relation_ready"] is True
    assert frontier["body0_bind_frame_contract"] == "SHIFT.BMWBody0BindFrameProof/1"
    assert frontier["body0_bind_frame_ready"] is True
    assert frontier["persistent_world_transform_wiring_contract"] == "SHIFT.BMWPersistentWorldTransformRuntimeWiring/1"
    assert frontier["vehicle_world_transform_ready"] is True
    assert frontier["retail_outer_cadence_contract"] == "SHIFT.RetailOuterUpdateCadence/1"
    assert frontier["retail_outer_cadence_admitted"] is True
    assert frontier["selected_session_physics_tweaker_rate_contract"] == "SHIFT.SelectedSessionPhysicsTweakerRate/1"
    assert frontier["selected_session_physics_tweaker_rate_ready"] is True
    assert frontier["selected_session_physics_tweaker_rate_hz"] == 180
    assert frontier["selected_session_physics_tweaker_archive"] == "PHYSICSBOOTFLOW.bff"
    assert frontier["selected_session_retail_execution_contract"] == "SHIFT.SelectedSessionRetailVehicleExecution/1"
    assert frontier["selected_session_retail_execution_ready"] is True
    assert frontier["selected_session_normal_outer_substeps"] == 6
    assert frontier["fun_007682c0_delta_destination_contract"] == "SHIFT.Fun007682c0Body0DeltaDestination/1"
    assert frontier["fun_007682c0_delta_destination_ready"] is True
    assert frontier["fun_007682c0_delta_application_internal"] is True
    assert frontier["fun_007682c0_machine_effect_contract"] == "SHIFT.Fun007682c0MachineEffectProduction/1"
    assert frontier["fun_007682c0_effect_production_internal"] is True
    assert frontier["fun_007682c0_x87_fsqrt_internal"] is True
    assert frontier["active_external_provider_count"] == 8
    assert frontier["current_blocker_id"] == "fun-007682c0-raw-input-producer-refresh"
    assert "raw HDVehicle/DAT inputs" in frontier["current_blocker"]
    assert "effect arithmetic" in frontier["current_blocker"]
    assert frontier["pc_build_is_primary_authority"] is True
    assert frontier["xbox_360_recomp_may_corroborate_or_accelerate_search"] is True
    assert frontier["runtime_capture_required"] is False


def test_single_process_queue_advances_inside_s6_provider_producers() -> None:
    payload = json.loads(EXECUTION.read_text(encoding="utf-8"))
    queue = payload["queue"]

    assert [row["id"] for row in queue] == ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9"]
    assert queue[0]["state"] == "positive"
    assert "delta_local" in queue[0]["task"]
    assert queue[1]["state"] == "positive"
    assert "M_outer_to_vhf_root" in queue[1]["task"]
    assert queue[2]["state"] == "positive"
    assert "SHIFT.BMWBody0BindFrameProof/1" in queue[2]["task"]
    assert queue[3]["state"] == "positive"
    assert "world-transform" in queue[3]["task"]
    assert queue[4]["state"] == "positive"
    assert "180 Hz" in queue[4]["task"]
    assert "1/180" in queue[4]["task"]
    assert queue[5]["state"] == "current"
    assert "destination and effect arithmetic are positive" in queue[5]["task"]
    assert "raw HDVehicle/DAT input producer refresh" in queue[5]["task"]
    assert "camera-follow" in queue[7]["task"]


def test_single_process_machine_effect_is_positive_but_raw_refresh_and_control_remain_closed() -> None:
    payload = json.loads(EXECUTION.read_text(encoding="utf-8"))
    positives = payload["positive_gates"]
    gates = payload["false_gates"]

    assert positives["outer_vehicle_root_to_VHF_relation_numeric_matrix_ready"] is True
    assert positives["BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready"] is True
    assert positives["BODY0_bind_frame_proof_ready"] is True
    assert positives["vehicle_world_transform_ready"] is True
    assert positives["retail_outer_cadence_admitted"] is True
    assert positives["loaded_inner_physics_rate_admitted"] is True
    assert positives["retail_inner_substep_execution_admitted"] is True
    assert positives["fun_007682c0_body0_delta_destination_ready"] is True
    assert positives["fun_007682c0_body0_delta_application_internal"] is True
    assert positives["fun_007682c0_effect_production_internal"] is True
    assert positives["fun_007682c0_x87_fsqrt_internal"] is True
    assert gates["fun_007682c0_raw_input_refresh_internal"] is False
    assert gates["retail_provider_control_producers_complete"] is False
    assert gates["retail_control_chain_complete"] is False
    assert gates["retail_camera_follow_ready"] is False
    assert "SHIFT.Fun007682c0MachineEffectProduction/1 exact PC machine effect arithmetic with x87 FSQRT and no host sqrt substitution" in payload["positive_checkpoints"]
    assert payload["internal_checkpoint_policy"]["cross_process_handoffs_exist"] is False
    assert payload["internal_checkpoint_policy"]["positive_contracts_consumed_immediately"] is True
    assert payload["internal_checkpoint_policy"]["unsupported_gate_promotion_allowed"] is False
    assert payload["internal_checkpoint_policy"]["host_1_60_may_satisfy_retail_cadence"] is False
    assert payload["internal_checkpoint_policy"]["host_std_sqrt_may_replace_retail_x87_fsqrt"] is False
    assert payload["internal_checkpoint_policy"]["missing_numeric_values_may_be_guessed"] is False
    assert payload["internal_checkpoint_policy"]["pc_build_primary_authority"] is True
    assert payload["internal_checkpoint_policy"]["xbox_360_recomp_may_replace_pc_proof"] is False


def test_v5_replaces_worker_ownership_with_one_critical_path() -> None:
    canonical = CANONICAL.read_text(encoding="utf-8")
    prompt = PROMPT.read_text(encoding="utf-8")

    assert "Status: **canonical coordination instructions**" in canonical
    assert "There are no active Process 1 / Process 2 / Process 3 workers." in canonical
    assert "S1  materialize exact selected-BMW FUN_00795d60 delta_local values" in canonical
    assert "NEXT_STEP" in canonical
    assert "slice/<blocker>" in canonical
    assert "blocker swarm" in canonical.lower()
    assert "Ты — единственный active development process" in prompt
    assert "Активных PROCESS 1 / PROCESS 2 / PROCESS 3 больше нет" in prompt
    assert "CURRENT SHORTEST BLOCKER" in prompt
    assert "Do NOT re-prove identity-vs-affine semantics" in prompt
