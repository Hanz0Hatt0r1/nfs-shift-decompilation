from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAMERA = ROOT / "src" / "camera"
if str(CAMERA) not in sys.path:
    sys.path.insert(0, str(CAMERA))

from camera_follow_current_transform_handoff import (  # noqa: E402
    FORMAT,
    WORLD_WIRING_FORMAT,
    build_handoff,
)
from camera_follow_source_frontier import build_camera_follow_source_frontier  # noqa: E402

WORLD_WIRING = ROOT / "evidence" / "bmw_persistent_world_transform_runtime_wiring.json"
COMMITTED = ROOT / "evidence" / "camera_follow_p14_current_vehicle_transform_handoff.json"


def _world_wiring() -> dict:
    return json.loads(WORLD_WIRING.read_text(encoding="utf-8"))


def test_current_production_world_transform_closes_p14_handoff() -> None:
    camera = build_camera_follow_source_frontier()
    report = build_handoff(camera, _world_wiring())

    assert report["format"] == FORMAT
    assert report["ready"] is True
    assert report["status"] == "ready-for-process2-camera-feed"
    assert report["process2_action"] == "implement_camera_feed"
    assert report["blocking_reasons"] == []

    camera_state = report["camera"]
    assert camera_state["selected_player_target_identity_ready"] is True
    assert camera_state["vehicle_pose_dependency_ready"] is True
    assert camera_state["retail_physics_before_camera_order_ready"] is True
    assert camera_state["mode2_per_frame_target"] == "FUN_008216a0"

    transform = report["vehicle_transform"]
    assert transform["wiring_format"] == WORLD_WIRING_FORMAT
    assert transform["production_wiring_ready"] is True
    assert transform["body_index"] == 0
    assert transform["BODY0_bind_proof_ready"] is True
    assert transform["BODY0_bind_runtime_admission_ready"] is True
    assert transform["persistent_world_transform_ready"] is True
    assert transform["same_fixed_step_commit_publish_ready"] is True

    adjudication = report["adjudication"]
    assert adjudication["p1_4_retail_camera_follow_proof_complete"] is True
    assert adjudication["process2_camera_feed_handoff_ready"] is True
    assert adjudication["process3_p3_5_camera_semantics_handoff_ready"] is True
    assert adjudication["camera_runtime_feed_implemented"] is False
    assert adjudication["external_provider_count"] == 7


def test_world_wiring_gate_fails_closed() -> None:
    camera = build_camera_follow_source_frontier()
    wiring = _world_wiring()
    wiring["ready"] = False
    report = build_handoff(camera, wiring)
    assert report["ready"] is False
    assert report["process2_action"] == "hold"
    assert "camera-follow-handoff:world-wiring-not-ready" in report["blocking_reasons"]


def test_camera_semantics_gate_fails_closed() -> None:
    camera = build_camera_follow_source_frontier()
    camera["proof_state"]["mode2_selected_player_target_identity_ready"] = False
    report = build_handoff(camera, _world_wiring())
    assert report["ready"] is False
    assert "camera-follow-handoff:selected-player-target-identity-not-ready" in report["blocking_reasons"]


def test_committed_handoff_matches_live_contract_shape() -> None:
    committed = json.loads(COMMITTED.read_text(encoding="utf-8"))
    assert committed["format"] == FORMAT
    assert committed["ready"] is True
    assert committed["status"] == "ready-for-process2-camera-feed"
    assert committed["vehicle_transform"]["body_index"] == 0
    assert committed["handoff"]["process2_action"] == "implement_camera_feed"
    assert committed["adjudication"]["p1_4_retail_camera_follow_proof_complete"] is True
    assert committed["adjudication"]["external_provider_count"] == 7
