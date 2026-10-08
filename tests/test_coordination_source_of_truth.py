import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXECUTION = ROOT / "evidence/playable_slice_three_process_execution.json"
LANES = ROOT / "coordination/lane_ownership.json"
STATUS = ROOT / "coordination/PLAYABLE_SLICE_STATUS.md"
RENDER = ROOT / "tools/coordination/render_playable_slice_status.py"


def _queues(payload):
    rows = {}
    for process in payload["processes"].values():
        for row in process["queue"]:
            assert row["id"] not in rows
            rows[row["id"]] = row
    return rows


def test_execution_state_is_single_live_status_source():
    registry = json.loads(LANES.read_text(encoding="utf-8"))
    assert registry["source_of_truth"] == "evidence/playable_slice_three_process_execution.json"
    assert registry["rules"]["live_status_must_come_from_source_of_truth"] is True
    assert registry["rules"]["lane_registry_is_ownership_policy_not_status"] is True


def test_lane_registry_covers_every_queue_exactly_once():
    execution = json.loads(EXECUTION.read_text(encoding="utf-8"))
    registry = json.loads(LANES.read_text(encoding="utf-8"))
    queues = _queues(execution)
    assigned = [task_id for lane in registry["lanes"] for task_id in lane["queue_ids"]]
    assert len(assigned) == len(set(assigned))
    assert set(assigned) == set(queues)


def test_provider_count_is_canonical_and_consistent():
    execution = json.loads(EXECUTION.read_text(encoding="utf-8"))
    assert execution["main_frontier"]["active_external_provider_count"] == execution["provider_frontier"]["count"]


def test_completed_p11_releases_p23_without_decrementing_provider_count():
    execution = json.loads(EXECUTION.read_text(encoding="utf-8"))
    queues = _queues(execution)
    frontier = execution["main_frontier"]
    assert queues["P1.1"]["state"] == "complete"
    assert frontier["fun_00766510_p1_complete"] is True
    assert queues["P2.3"]["state"] == "ready-to-consume"
    assert queues["P2.4"]["state"] == "ready-to-consume"
    assert execution["provider_frontier"]["count"] == 7
    assert frontier["active_external_provider_count"] == 7
    assert execution["provider_frontier"]["target_after_first_reduction"] == 6


def test_final_smoke_cannot_bypass_control_or_camera():
    execution = json.loads(EXECUTION.read_text(encoding="utf-8"))
    frontier = execution["main_frontier"]
    if frontier["final_playable_smoke_currently_runnable"]:
        assert frontier["final_playable_smoke_entrypoint_ready"]
        assert frontier["retail_control_chain_complete"]
        assert frontier["retail_camera_follow_ready"]


def test_generated_status_is_current():
    result = subprocess.run(
        [sys.executable, str(RENDER), "--check"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert STATUS.exists()
