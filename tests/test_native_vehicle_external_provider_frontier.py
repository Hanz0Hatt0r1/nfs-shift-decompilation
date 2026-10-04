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
    assert report["refresh_after_phase"] == 703
    assert report["external_provider_count"] == 9
    assert report["implement_now"] == []
    assert report["runtime_only_blocked"] == []
    assert report["action_counts"] == {IMPLEMENT_NOW: 0, REQUEST_PROCESS1: 9, RUNTIME_ONLY_BLOCKED: 0}
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
    motion_header = (ROOT / "native_runtime/include/shift_fun_00770e80_motion_read_effect_provider_chain.hpp").read_text(encoding="utf-8")
    scalar_header = (ROOT / "native_runtime/include/shift_fun_00770e80_scalar_provider_anchor_chain.hpp").read_text(encoding="utf-8")
    schedule_header = (ROOT / "native_runtime/include/shift_fun_00770e80_two_half_step_schedule.hpp").read_text(encoding="utf-8")
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


def test_phase699_consumes_global_body_owner_contract_without_reintroducing_update_child_gate() -> None:
    report = build_frontier()
    providers = {row["id"]: row for row in report["providers"]}
    delta = providers["fun_007682c0_delta_consumer"]
    assert any("PR #1196" in evidence for evidence in delta["evidence"])
    assert any("Phase 703" in evidence for evidence in delta["evidence"])
    assert delta["blockers"] == [
        "SHIFT.GlobalVehicleBodyOwnerIdentity/1 is not retail-ready because the targeted FUN_00765470 instruction export/receiver proof is not committed",
    ]
    assert "update-child" not in " ".join(delta["process1_requested_proof"]).lower()

    joins = {row["id"]: row for row in report["cross_chain_joins"]}
    body_identity = joins["body_to_vehicle_identity"]
    assert body_identity["state"] == "composed_global_owner_contract_ready_retail_receiver_proof_pending"
    assert any("PR #1194" in evidence for evidence in body_identity["evidence"])
    assert any("PR #1195" in evidence for evidence in body_identity["evidence"])
    assert any("PR #1196" in evidence for evidence in body_identity["evidence"])
    assert any("Phase 703" in evidence for evidence in body_identity["evidence"])
    assert body_identity["blockers"] == [
        "targeted retail FUN_00765470 instruction export/receiver proof is not committed, so the composed identity is not retail-ready",
    ]
    assert "do not reintroduce update-child pointer equality" in body_identity["policy"]


def test_phase699_tracks_fun_00765470_receiver_proof_separately_from_refresh_producers() -> None:
    report = build_frontier()
    provider = {row["id"]: row for row in report["providers"]}["fun_00765470_half_step_refresh_bundle"]
    assert any("PR #1195" in evidence for evidence in provider["evidence"])
    assert any("PR #1196" in evidence for evidence in provider["evidence"])
    assert any("instruction export" in blocker for blocker in provider["blockers"])
    assert any("refresh schedule" in blocker for blocker in provider["blockers"])
    assert len(provider["process1_requested_proof"]) == 3


def test_phase699_consumes_phase645_646_renderer_side_without_claiming_body_frame_mapping() -> None:
    report = build_frontier()
    closed = {row["boundary"]: row for row in report["closed_boundaries"]}
    assert closed["canonical BMW VHF static bind transform"]["phase"] == 645
    assert closed["dynamic vehicle world-transform transport core"]["phase"] == 646
    assert "live_vulkan_wiring_pending" in closed["dynamic vehicle world-transform transport core"]["state"]

    joins = {row["id"]: row for row in report["cross_chain_joins"]}
    transform = joins["body_pose_to_renderer_world_transform"]
    assert transform["state"] == "bind_frame_composition_blocked_transport_core_ready"
    assert any("Phase 645" in evidence for evidence in transform["evidence"])
    assert any("Phase 646" in evidence for evidence in transform["evidence"])
    assert transform["blockers"] == [
        "persistent BODY0 pose frame -> Phase 645 VHF vehicle-root/body-MEB bind-frame composition is not proven",
    ]
    assert "live Vulkan buffer wiring" in transform["additional_dependency"]


def test_phase699_closed_boundaries_reflect_phase700_703_without_promoting_retail_identity() -> None:
    closed = {row["boundary"]: row for row in build_frontier()["closed_boundaries"]}
    assert closed["NativeRuntimeState -> selected BODY pose handoff"]["phase"] == 700
    composed = closed["global vehicle/BODY-owner identity composition contract"]
    assert composed["proof"].startswith("SHIFT.GlobalVehicleBodyOwnerIdentity/1")
    assert composed["selected_BODY_index_when_ready"] == 0
    assert composed["retail_identity_ready"] is False
    assert composed["update_child_pointer_equality_required"] is False
    phase703 = closed["native composed BODY-owner identity consumer"]
    assert phase703["phase"] == 703
    assert phase703["proof"] == "SHIFT.NativeGlobalVehicleBodyOwnerSelection/1"
    assert phase703["retail_identity_ready"] is False


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
    assert guards["update_child_pointer_equality_required"] is False
    assert guards["body_pose_to_vehicle_transform_promotion_allowed"] is False
    assert guards["phase645_static_bind_transform_is_dynamic_pose"] is False
    assert guards["phase646_transport_core_is_body_frame_proof"] is False
    assert guards["original_game_execution_required"] is False
    assert guards["new_runtime_capture_required"] is False

    joins = {row["id"]: row for row in report["cross_chain_joins"]}
    assert joins["outer_update_cadence_owner"]["process2_action"] == REQUEST_PROCESS1
    assert joins["body_to_vehicle_identity"]["process2_action"] == REQUEST_PROCESS1
    assert joins["body_pose_to_renderer_world_transform"]["process2_action"] == REQUEST_PROCESS1
    assert joins["retail_resource_to_initial_body_state"]["process2_action"] == REQUEST_PROCESS1


def test_phase699_builder_emits_stable_machine_readable_report(tmp_path: Path) -> None:
    output = tmp_path / "provider_frontier.json"
    completed = subprocess.run(
        [sys.executable, str(ROOT / "tools/build_native_vehicle_external_provider_frontier.py"), str(output)],
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
