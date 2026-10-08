import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STAGED = ROOT / "evidence/process2_bmw_body0_bind_frame_staged_handoff.json"
SWARM = ROOT / "evidence/playable_slice_blocker_swarm.json"
PACKET = ROOT / "evidence/process2_bmw_body0_bind_frame_proof_packet.json"
PROCESS = ROOT / "PROCESS_INSTRUCTIONS.md"
V5 = ROOT / "docs/PLAYABLE_SLICE_SINGLE_PROCESS_INSTRUCTIONS_V5.md"
V6 = ROOT / "docs/PLAYABLE_SLICE_THREE_PROCESS_INSTRUCTIONS_V6.md"
PROMPTS = ROOT / "docs/PLAYABLE_SLICE_THREE_PROCESS_PROMPTS_V6.md"


def test_legacy_staged_handoff_remains_historical_checkpoint() -> None:
    payload = json.loads(STAGED.read_text(encoding="utf-8"))

    assert payload["format"] == "SHIFT.Process2BMWBody0BindFrameStagedHandoff/1"
    assert payload["status"] == "ready-gate"
    assert payload["coordination_status"] == "legacy-compatibility-checkpoint"
    assert payload["policy"]["final_runtime_admission_stays_fail_closed"] is True
    assert payload["policy"]["missing_semantic_value_may_be_guessed"] is False
    assert payload["policy"]["host_1_60_may_satisfy_retail_cadence"] is False


def test_legacy_runtime_packet_remains_fail_closed_snapshot() -> None:
    packet = json.loads(PACKET.read_text(encoding="utf-8"))

    assert packet["format"] == "SHIFT.Process2BMWBody0BindFrameProofPacket/1"
    assert packet["input"]["required_contract"] == "SHIFT.BMWBody0BindFrameProof/1"


def test_blocker_swarm_stays_retired_under_explicit_three_process_ownership() -> None:
    swarm = json.loads(SWARM.read_text(encoding="utf-8"))

    assert swarm["format"] == "SHIFT.PlayableSliceBlockerSwarm/1"
    assert swarm["status"] == "retired"
    assert swarm["active"] is False
    assert swarm["superseded_by"] == "SHIFT.PlayableSliceThreeProcessExecution/1"
    assert swarm["active_worker_count"] == 3
    assert swarm["parallel_shards_active"] is False
    assert swarm["cross_process_handoffs_active"] is True
    assert swarm["limits"]["may_select_new_work"] is False
    assert swarm["limits"]["may_define_semantic_ownership"] is False


def test_v5_is_retired_and_v6_is_canonical() -> None:
    v5 = V5.read_text(encoding="utf-8")
    v6 = V6.read_text(encoding="utf-8")
    prompts = PROMPTS.read_text(encoding="utf-8")

    assert "Status: **RETIRED**" in v5
    assert "Status: **canonical coordination instructions**" in v6
    assert "Status: **canonical parallel prompts**" in prompts


def test_root_instructions_route_to_canonical_execution_and_explicit_lanes() -> None:
    process = PROCESS.read_text(encoding="utf-8")

    assert "PLAYABLE_SLICE_THREE_PROCESS_INSTRUCTIONS_V6.md" in process
    assert "PLAYABLE_SLICE_THREE_PROCESS_PROMPTS_V6.md" in process
    assert "playable_slice_three_process_execution.json" in process
    assert "coordination/PLAYABLE_SLICE_STATUS.md" in process
    assert "coordination/lane_ownership.json" in process
    assert "P1A-contact" in process
    assert "P1B-control" in process
    assert "P1D-camera" in process
    assert "P2-runtime" in process
    assert "P3-integration" in process
    assert "NEXT_OWNER:" in process
