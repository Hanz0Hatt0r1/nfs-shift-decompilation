import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STAGED = ROOT / "evidence/process2_bmw_body0_bind_frame_staged_handoff.json"
SWARM = ROOT / "evidence/playable_slice_blocker_swarm.json"
PACKET = ROOT / "evidence/process2_bmw_body0_bind_frame_proof_packet.json"
PROCESS = ROOT / "PROCESS_INSTRUCTIONS.md"
CANONICAL = ROOT / "docs/PLAYABLE_SLICE_PROCESS_INSTRUCTIONS_V4.md"
SWARM_DOC = ROOT / "docs/PLAYABLE_SLICE_BLOCKER_SWARM.md"
PROMPTS = ROOT / "docs/PLAYABLE_SLICE_PARALLEL_PROCESS_PROMPTS_V4.md"


def test_staged_bind_handoff_keeps_final_runtime_gate_closed() -> None:
    payload = json.loads(STAGED.read_text(encoding="utf-8"))

    assert payload["format"] == "SHIFT.Process2BMWBody0BindFrameStagedHandoff/1"
    assert payload["status"] == "ready-gate"
    assert payload["policy"]["consume_positive_stages_immediately"] is True
    assert payload["policy"]["final_runtime_admission_stays_fail_closed"] is True
    assert payload["policy"]["missing_semantic_value_may_be_guessed"] is False
    assert payload["policy"]["host_1_60_may_satisfy_retail_cadence"] is False

    stages = {row["id"]: row for row in payload["stages"]}
    assert stages["retail_body0_identity"]["state"] == "positive-consumed"
    assert stages["body0_vhf_composition_formula"]["state"] == "positive-consumed"
    assert stages["exact_bmw_vhf_resource_identity"]["state"] == "positive-available"
    assert stages["exact_bmw_vhf_hierarchy_root_frame"]["state"] == "positive-available"
    assert stages["exact_bmw_vhf_hierarchy_root_frame"]["contract"] == "SHIFT.BMWVHFHierarchyRootFrame/1"
    assert "PR #1323" in stages["exact_bmw_vhf_hierarchy_root_frame"]["source"]
    assert stages["outer_vehicle_render_snapshot_affine_bridge"]["state"] == "positive-available"
    assert stages["outer_vehicle_to_exact_vhf_root_relation"]["state"] == "blocked"
    assert stages["final_body0_bind_frame_proof"]["state"] == "blocked"
    assert (
        stages["final_body0_bind_frame_proof"]["contract"]
        == "SHIFT.BMWBody0BindFrameProof/1"
    )


def test_process2_has_parallel_work_without_promoting_bind_semantics() -> None:
    payload = json.loads(STAGED.read_text(encoding="utf-8"))
    work = {row["id"]: row for row in payload["process2_parallel_work"]}

    assert work["consume_new_positive_stages"]["state"] == "runnable"
    assert work["consume_exact_vhf_root_frame_stage"]["state"] == "runnable"
    assert work["consume_exact_vhf_root_frame_stage"]["contract"] == "SHIFT.BMWVHFHierarchyRootFrame/1"
    assert work["external_provider_and_control_frontier"]["state"] == "runnable"
    assert work["scheduler_consumer_seam"]["state"] == "ready"
    assert work["persistent_transform_freshness"]["state"] == "ready-keep-green"
    assert work["retail_vehicle_world_transform_admission"]["state"] == "blocked"
    assert (
        work["scheduler_consumer_seam"]["contract"]
        == "SHIFT.Process2RuntimeSchedulerAuthority/1"
    )


def test_final_packet_explicitly_consumes_staged_policy() -> None:
    packet = json.loads(PACKET.read_text(encoding="utf-8"))

    assert packet["format"] == "SHIFT.Process2BMWBody0BindFrameProofPacket/1"
    assert packet["input"]["required_contract"] == "SHIFT.BMWBody0BindFrameProof/1"
    assert (
        packet["input"]["staged_handoff_contract"]
        == "SHIFT.Process2BMWBody0BindFrameStagedHandoff/1"
    )
    assert packet["input"]["partial_handoff_consumption_required"] is True
    assert packet["input"]["current_positive_handoff_present"] is False
    assert packet["output"]["retail_world_transform_admitted"] is False
    assert "staged-handoff-active" in packet["ownership"]["process2_state"]


def test_blocker_swarm_retargets_after_positive_vhf_root_frame() -> None:
    swarm = json.loads(SWARM.read_text(encoding="utf-8"))

    assert swarm["format"] == "SHIFT.PlayableSliceBlockerSwarm/1"
    assert swarm["status"] == "active"
    assert swarm["primary_owner"] == "Process 1"
    assert swarm["final_semantic_authority"] == "Process 1"
    assert "SHIFT.BMWVHFHierarchyRootFrame/1" in swarm["current_frontier"]["input_contracts"]
    assert any("PR #1323" in row for row in swarm["current_frontier"]["newly_positive"])
    assert swarm["fallback_policy"]["downstream_process_may_idle"] is False
    assert swarm["fallback_policy"]["duplicate_semantic_question_allowed"] is False
    assert swarm["fallback_policy"]["unsupported_gate_promotion_allowed"] is False
    assert swarm["fallback_policy"]["superseded_shards_must_be_retargeted_after_upstream_merge"] is True

    shards = {row["process"]: row for row in swarm["shards"]}
    assert shards["Process 1"]["role"] == "proof-owner"
    assert shards["Process 1"]["may_publish_final_semantic_proof"] is True
    assert "BMWVHFHierarchyRootFrame/1" in shards["Process 1"]["task"]
    assert shards["Process 2"]["role"] == "runtime-consumer-assist"
    assert shards["Process 2"]["may_publish_final_semantic_proof"] is False
    assert "BMWVHFHierarchyRootFrame/1" in shards["Process 2"]["task"]
    assert shards["Process 3"]["role"] == "resource-runtime-frame-assist"
    assert shards["Process 3"]["may_publish_final_semantic_proof"] is False
    assert "SHIFT.BMWVHFRootFrameSceneConsumer/1" in shards["Process 3"]["output"]


def test_v4_is_canonical_and_prompts_retarget_superseded_shard() -> None:
    process = PROCESS.read_text(encoding="utf-8")
    canonical = CANONICAL.read_text(encoding="utf-8")
    swarm_doc = SWARM_DOC.read_text(encoding="utf-8")
    prompts = PROMPTS.read_text(encoding="utf-8")

    assert "PLAYABLE_SLICE_PROCESS_INSTRUCTIONS_V4.md" in process
    assert "PLAYABLE_SLICE_PARALLEL_PROCESS_PROMPTS_V4.md" in process
    assert "PLAYABLE_SLICE_BLOCKER_SWARM.md" in process
    assert "playable_slice_blocker_swarm.json" in process
    assert "process2_bmw_body0_bind_frame_staged_handoff.json" in process
    assert "staged cross-process handoffs" in canonical.lower()
    assert "missing final bind proof != Process 2 globally idle" in canonical
    assert "SHIFT.BMWVHFHierarchyRootFrame/1" in swarm_doc
    assert "resource-root extraction shard is already complete" in swarm_doc
    assert "SHIFT.BMWVHFRootFrameSceneConsumer/1" in swarm_doc
    assert "НЕ означает, что PROCESS 2 глобально простаивает" in prompts
    assert "SHIFT.BMWVHFHierarchyRootFrame/1 positive via merged PR #1323" in prompts
    assert "старый shard «извлечь exact HIERARCHY root frame» УЖЕ ЗАКРЫТ PR #1323" in prompts
    assert "resource-runtime-frame-assist shard" in prompts
    assert "Не угадывай missing matrix/affine relation" in prompts
