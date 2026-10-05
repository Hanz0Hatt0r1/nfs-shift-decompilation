import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STAGED = ROOT / "evidence/process2_bmw_body0_bind_frame_staged_handoff.json"
PACKET = ROOT / "evidence/process2_bmw_body0_bind_frame_proof_packet.json"
PROCESS = ROOT / "PROCESS_INSTRUCTIONS.md"
CANONICAL = ROOT / "docs/PLAYABLE_SLICE_PROCESS_INSTRUCTIONS_V4.md"
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


def test_v4_is_canonical_and_process2_prompt_forbids_global_idle() -> None:
    process = PROCESS.read_text(encoding="utf-8")
    canonical = CANONICAL.read_text(encoding="utf-8")
    prompts = PROMPTS.read_text(encoding="utf-8")

    assert "PLAYABLE_SLICE_PROCESS_INSTRUCTIONS_V4.md" in process
    assert "PLAYABLE_SLICE_PARALLEL_PROCESS_PROMPTS_V4.md" in process
    assert "process2_bmw_body0_bind_frame_staged_handoff.json" in process
    assert "staged cross-process handoffs" in canonical.lower()
    assert "missing final bind proof != Process 2 globally idle" in canonical
    assert "НЕ означает, что PROCESS 2 глобально простаивает" in prompts
    assert "Не угадывай missing matrix/affine relation" in prompts
