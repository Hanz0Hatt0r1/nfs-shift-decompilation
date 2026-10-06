import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "docs/PLAYABLE_SLICE_SINGLE_PROCESS_INSTRUCTIONS_V5.md"
PROMPT = ROOT / "docs/PLAYABLE_SLICE_SINGLE_PROCESS_PROMPT_V5.md"
EXECUTION = ROOT / "evidence/playable_slice_single_process_execution.json"


def test_single_process_execution_contract_is_active_and_current() -> None:
    payload = json.loads(EXECUTION.read_text(encoding="utf-8"))

    assert payload["format"] == "SHIFT.PlayableSliceSingleProcessExecution/1"
    assert payload["status"] == "active"
    assert payload["execution_model"] == "single-process"
    assert payload["legacy_parallel_coordination_retired"] is True
    assert payload["current_frontier"]["semantic_relation_contract"] == "SHIFT.OuterVehicleBMWVHFRootRelation/1"
    assert payload["current_frontier"]["semantic_relation_ready"] is True
    assert payload["current_frontier"]["semantic_relation_kind"] == "setup-fixed-affine"
    assert payload["current_frontier"]["selected_bmw_delta_contract"] == "SHIFT.BMWPrimaryPlayerFirstBootstrapRenderRootDelta/1"
    assert payload["current_frontier"]["selected_bmw_delta_numeric_ready"] is True
    assert payload["current_frontier"]["outer_vhf_numeric_relation_contract"] == "SHIFT.BMWOuterVHFNumericRelation/1"
    assert payload["current_frontier"]["outer_vhf_numeric_relation_ready"] is True
    assert payload["current_frontier"]["body0_bind_frame_contract"] == "SHIFT.BMWBody0BindFrameProof/1"
    assert payload["current_frontier"]["body0_bind_frame_ready"] is True
    assert payload["current_frontier"]["persistent_world_transform_wiring_contract"] == "SHIFT.BMWPersistentWorldTransformRuntimeWiring/1"
    assert payload["current_frontier"]["vehicle_world_transform_ready"] is True
    assert payload["current_frontier"]["current_blocker_id"] == "retail-outer-update-scheduler-cadence-admission"
    assert "scheduler/cadence" in payload["current_frontier"]["current_blocker"]
    assert payload["current_frontier"]["runtime_capture_required"] is False


def test_single_process_queue_orders_world_transform_before_scheduler_control_camera() -> None:
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
    assert queue[4]["state"] == "current"
    assert "scheduler/cadence" in queue[4]["task"]
    assert "camera-follow" in queue[7]["task"]


def test_single_process_opens_only_retail_cadence_after_s4() -> None:
    payload = json.loads(EXECUTION.read_text(encoding="utf-8"))
    positives = payload["positive_gates"]
    gates = payload["false_gates"]

    assert positives["outer_vehicle_root_to_VHF_relation_numeric_matrix_ready"] is True
    assert positives["BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready"] is True
    assert positives["BODY0_bind_frame_proof_ready"] is True
    assert positives["vehicle_world_transform_ready"] is True
    assert "outer_vehicle_root_to_VHF_relation_numeric_matrix_ready" not in gates
    assert "BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready" not in gates
    assert "BODY0_bind_frame_proof_ready" not in gates
    assert "vehicle_world_transform_ready" not in gates
    assert gates["retail_cadence_admitted"] is False
    assert gates["retail_control_chain_complete"] is False
    assert gates["retail_camera_follow_ready"] is False
    assert payload["internal_checkpoint_policy"]["cross_process_handoffs_exist"] is False
    assert payload["internal_checkpoint_policy"]["positive_contracts_consumed_immediately"] is True
    assert payload["internal_checkpoint_policy"]["unsupported_gate_promotion_allowed"] is False
    assert payload["internal_checkpoint_policy"]["host_1_60_may_satisfy_retail_cadence"] is False
    assert payload["internal_checkpoint_policy"]["missing_numeric_values_may_be_guessed"] is False


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
