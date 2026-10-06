import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STAGED = ROOT / "evidence/process2_bmw_body0_bind_frame_staged_handoff.json"
SWARM = ROOT / "evidence/playable_slice_blocker_swarm.json"
PACKET = ROOT / "evidence/process2_bmw_body0_bind_frame_proof_packet.json"
PROCESS = ROOT / "PROCESS_INSTRUCTIONS.md"
V4 = ROOT / "docs/PLAYABLE_SLICE_PROCESS_INSTRUCTIONS_V4.md"
SWARM_DOC = ROOT / "docs/PLAYABLE_SLICE_BLOCKER_SWARM.md"
PARALLEL_PROMPTS = ROOT / "docs/PLAYABLE_SLICE_PARALLEL_PROCESS_PROMPTS_V4.md"


def test_legacy_staged_handoff_is_single_process_compatibility_checkpoint() -> None:
    payload = json.loads(STAGED.read_text(encoding="utf-8"))

    assert payload["format"] == "SHIFT.Process2BMWBody0BindFrameStagedHandoff/1"
    assert payload["status"] == "ready-gate"
    assert payload["coordination_status"] == "legacy-compatibility-checkpoint"
    assert payload["active_execution_model"] == "single-process"
    assert payload["active_execution_contract"] == "SHIFT.PlayableSliceSingleProcessExecution/1"
    assert payload["legacy_process_labels_define_active_ownership"] is False
    assert payload["policy"]["consume_positive_stages_immediately"] is True
    assert payload["policy"]["final_runtime_admission_stays_fail_closed"] is True
    assert payload["policy"]["missing_semantic_value_may_be_guessed"] is False
    assert payload["policy"]["host_1_60_may_satisfy_retail_cadence"] is False

    stages = {row["id"]: row for row in payload["stages"]}
    assert stages["retail_body0_identity"]["state"] == "positive-consumed"
    assert stages["body0_vhf_composition_formula"]["state"] == "positive-consumed"
    assert stages["exact_bmw_vhf_resource_identity"]["state"] == "positive-consumed"
    assert stages["exact_bmw_vhf_hierarchy_root_frame"]["state"] == "positive-consumed"
    assert stages["outer_vehicle_render_snapshot_affine_bridge"]["state"] == "positive-consumed"

    relation = stages["outer_vehicle_to_exact_vhf_root_relation"]
    assert relation["contract"] == "SHIFT.OuterVehicleBMWVHFRootRelation/1"
    assert relation["state"] == "positive-semantic-numeric-pending"
    assert relation["relation_kind"] == "setup-fixed-affine"
    assert "PR #1331" in relation["source"]
    assert any("+0x19c" in item for item in relation["requires"])

    final = stages["final_body0_bind_frame_proof"]
    assert final["contract"] == "SHIFT.BMWBody0BindFrameProof/1"
    assert final["state"] == "blocked"

    ownership = payload["ownership"]
    assert ownership["active_owner"] == "single playable-slice process"
    assert ownership["historical_roles_are_active_workers"] is False
    assert ownership["final_runtime_admission_remains_fail_closed"] is True


def test_legacy_runtime_packet_remains_fail_closed() -> None:
    packet = json.loads(PACKET.read_text(encoding="utf-8"))

    assert packet["format"] == "SHIFT.Process2BMWBody0BindFrameProofPacket/1"
    assert packet["input"]["required_contract"] == "SHIFT.BMWBody0BindFrameProof/1"
    assert packet["input"]["current_positive_handoff_present"] is False
    assert packet["output"]["retail_world_transform_admitted"] is False


def test_blocker_swarm_is_retired() -> None:
    swarm = json.loads(SWARM.read_text(encoding="utf-8"))

    assert swarm["format"] == "SHIFT.PlayableSliceBlockerSwarm/1"
    assert swarm["status"] == "retired"
    assert swarm["active"] is False
    assert swarm["superseded_by"] == "SHIFT.PlayableSliceSingleProcessExecution/1"
    assert swarm["active_worker_count"] == 1
    assert swarm["parallel_shards_active"] is False
    assert swarm["cross_process_handoffs_active"] is False
    assert swarm["limits"]["may_select_new_work"] is False
    assert swarm["limits"]["may_define_semantic_ownership"] is False


def test_old_parallel_coordination_files_are_retired() -> None:
    v4 = V4.read_text(encoding="utf-8")
    swarm_doc = SWARM_DOC.read_text(encoding="utf-8")
    prompts = PARALLEL_PROMPTS.read_text(encoding="utf-8")

    assert "Status: **RETIRED" in v4
    assert "PLAYABLE_SLICE_SINGLE_PROCESS_INSTRUCTIONS_V5.md" in v4
    assert "Status: **RETIRED**" in swarm_doc
    assert "PLAYABLE_SLICE_SINGLE_PROCESS_INSTRUCTIONS_V5.md" in swarm_doc
    assert "Status: **RETIRED**" in prompts
    assert "PLAYABLE_SLICE_SINGLE_PROCESS_PROMPT_V5.md" in prompts


def test_root_instructions_select_only_single_process_coordination() -> None:
    process = PROCESS.read_text(encoding="utf-8")

    assert "PLAYABLE_SLICE_SINGLE_PROCESS_INSTRUCTIONS_V5.md" in process
    assert "PLAYABLE_SLICE_SINGLE_PROCESS_PROMPT_V5.md" in process
    assert "playable_slice_single_process_execution.json" in process
    assert "There are no active Process 1 / Process 2 / Process 3 ownership lanes" in process
    assert "slice/<blocker>" in process
    assert "NEXT_STEP:" in process
