from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from native_vehicle_external_provider_frontier import (
    FORMAT,
    IMPLEMENT_NOW,
    REQUEST_PROCESS1,
    RUNTIME_ONLY_BLOCKED,
    build_frontier,
)

ROOT = Path(__file__).resolve().parents[1]


def test_phase699_freezes_exact_deep_chain_external_provider_set() -> None:
    report = build_frontier()
    assert report["format"] == FORMAT
    assert report["phase"] == 699
    assert report["external_provider_count"] == 9
    assert report["implement_now"] == []
    assert report["runtime_only_blocked"] == []
    assert report["action_counts"] == {
        IMPLEMENT_NOW: 0,
        REQUEST_PROCESS1: 9,
        RUNTIME_ONLY_BLOCKED: 0,
    }
    assert report["process1_handoff_requests"] == [
        "fun_00765c40_complete_anchor",
        "fun_00758b50_wheel_update",
        "fun_00766510_contact_response",
        "fun_007675f0_input_provider",
        "fun_007682c0_effect_provider",
        "fun_007682c0_delta_consumer",
        "fun_007afdd0_scalar_provider",
        "fun_007b8810_post_half_step",
        "fun_00765470_half_step_refresh_bundle",
    ]
    for row in report["providers"]:
        assert row["evidence_state"] == "static_frontier_available"
        assert row["process2_action"] == REQUEST_PROCESS1
        assert row["blockers"]
        assert row["process1_requested_proof"]


def test_phase699_matches_current_native_provider_api() -> None:
    motion_header = (
        ROOT / "native_runtime" / "include" /
        "shift_fun_00770e80_motion_read_effect_provider_chain.hpp"
    ).read_text(encoding="utf-8")
    scalar_header = (
        ROOT / "native_runtime" / "include" /
        "shift_fun_00770e80_scalar_provider_anchor_chain.hpp"
    ).read_text(encoding="utf-8")
    schedule_header = (
        ROOT / "native_runtime" / "include" /
        "shift_fun_00770e80_two_half_step_schedule.hpp"
    ).read_text(encoding="utf-8")

    assert "Fun0076d100AnchorCallback contact_factor" in motion_header
    assert "Fun0076d100AnchorCallback wheel_update" in motion_header
    assert "Fun0076d100AnchorCallback contact_response" in motion_header
    assert "Fun007675f0ContactOuterInputProvider contact_outer_input_provider" in motion_header
    assert "Fun007682c0EffectProvider motion_read_effect_provider" in motion_header
    assert "Fun007682c0AccumulatorDeltaConsumer motion_read_delta_consumer" in motion_header
    assert "Fun007afdd0ScalarProvider scalar_provider" in scalar_header
    assert "Fun00765470MachineScalarHalfStepProvider" in scalar_header
    assert "Fun007b8810PostHalfStepCallback" in scalar_header
    assert "FUN_007b8810" in schedule_header


def test_phase699_keeps_known_unsafe_promotions_forbidden() -> None:
    report = build_frontier()
    guards = report["guards"]
    assert guards["two_half_steps_preserved"] is True
    assert guards["persistent_body_state_preserved"] is True
    assert guards["participant_admission_preserved"] is True
    assert guards["missing_provider_fails_closed"] is True
    assert guards["fixed_step_auto_schedule_allowed"] is False
    assert guards["host_sqrt_substitution_allowed"] is False
    assert guards["host_sin_substitution_allowed"] is False
    assert guards["host_cos_substitution_allowed"] is False
    assert guards["body_pose_to_vehicle_transform_promotion_allowed"] is False
    assert guards["original_game_execution_required"] is False
    assert guards["new_runtime_capture_required"] is False

    joins = {row["id"]: row for row in report["cross_chain_joins"]}
    assert joins["outer_update_cadence_owner"]["process2_action"] == REQUEST_PROCESS1
    assert any(
        "machine-callsite mapping" in blocker
        for blocker in joins["outer_update_cadence_owner"]["blockers"]
    )
    assert joins["body_to_vehicle_identity"]["process2_action"] == REQUEST_PROCESS1
    assert any(
        "main_chassis_BODY_selected false" in blocker
        for blocker in joins["body_to_vehicle_identity"]["blockers"]
    )
    assert joins["body_pose_to_renderer_object_identity"]["process2_action"] == REQUEST_PROCESS1
    assert joins["retail_resource_to_initial_body_state"]["process2_action"] == REQUEST_PROCESS1

    closed = {row["boundary"]: row for row in report["closed_boundaries"]}
    assert closed["proven BODY-index -> persistent pose selection transport"]["phase"] == 698
    assert closed["proven BODY-index -> persistent pose selection transport"]["retail_identity_ready"] is False
    assert closed["BMW named BODY field topology"]["proof"] == "SHIFT.VehicleNamedBodyTopologyFrontier/1"
    assert closed["BMW named BODY field topology"]["selected_BODY_index"] is None
    assert "outer-update mapped machine callsite" not in closed


def test_phase699_builder_emits_stable_machine_readable_report(tmp_path: Path) -> None:
    output = tmp_path / "provider_frontier.json"
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "build_native_vehicle_external_provider_frontier.py"),
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload == build_frontier()
    assert f"format: {FORMAT}" in completed.stdout
    assert "external providers: 9" in completed.stdout
    assert "implement now: 0" in completed.stdout
    assert "Process 1 handoffs: 9" in completed.stdout
