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


def test_phase708_keeps_exact_deep_chain_external_provider_set() -> None:
    report = build_frontier()
    assert report["format"] == FORMAT
    assert report["phase"] == 699
    assert report["refresh_after_phase"] == 707
    assert report["refresh_label"] == "Process 2 Phase 708 coordination refresh"
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


def test_phase708_matches_current_native_provider_api() -> None:
    motion_header = (
        ROOT / "native_runtime/include/shift_fun_00770e80_motion_read_effect_provider_chain.hpp"
    ).read_text(encoding="utf-8")
    scalar_header = (
        ROOT / "native_runtime/include/shift_fun_00770e80_scalar_provider_anchor_chain.hpp"
    ).read_text(encoding="utf-8")
    schedule_header = (
        ROOT / "native_runtime/include/shift_fun_00770e80_two_half_step_schedule.hpp"
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


def test_phase708_closes_global_body_owner_identity_without_overpromoting_delta_target() -> None:
    report = build_frontier()
    closed = {row["boundary"]: row for row in report["closed_boundaries"]}
    composed = closed["global vehicle/BODY-owner identity composition contract"]
    assert "PR #1208" in composed["proof"]
    assert composed["retail_identity_ready"] is True
    assert composed["selected_BODY_index"] == 0
    assert composed["global_vehicle_address"] == "0x00c13700"
    assert composed["BODY_owner_pointer_field_offset"] == "0x339c"
    assert composed["BODY_array_owner_is_global_vehicle_base"] is False
    assert composed["update_child_pointer_equality_required"] is False

    phase707 = closed["native retail BODY-owner identity producer"]
    assert phase707["phase"] == 707
    assert phase707["retail_identity_ready"] is True
    assert phase707["selected_BODY_index"] == 0
    assert phase707["caller_injected_identity_required"] is False

    delta = {row["id"]: row for row in report["providers"]}[
        "fun_007682c0_delta_consumer"
    ]
    assert any("PR #1208" in evidence for evidence in delta["evidence"])
    assert any("Phase 707" in evidence for evidence in delta["evidence"])
    assert delta["blockers"] == [
        "the exact BODY pointer/record receiving the FUN_007682c0 +0x50 application is not yet proven to be the retail BMW chassis BODY 0 record",
    ]
    assert "destination pointer/record provenance" in delta["process1_requested_proof"][0]
    assert "instruction export/receiver proof" not in " ".join(delta["blockers"])

    joins = {row["id"]: row for row in report["cross_chain_joins"]}
    body_identity = joins["body_to_vehicle_identity"]
    assert body_identity["state"] == "retail_proven_and_consumed"
    assert body_identity["process2_action"] == "closed"
    assert body_identity["blockers"] == []
    assert any("PR #1208" in evidence for evidence in body_identity["evidence"])
    assert any("Phase 707" in evidence for evidence in body_identity["evidence"])
    assert "do not reintroduce update-child pointer equality" in body_identity["policy"]


def test_phase708_removes_closed_fun_00765470_receiver_proof_from_refresh_row() -> None:
    provider = {row["id"]: row for row in build_frontier()["providers"]}[
        "fun_00765470_half_step_refresh_bundle"
    ]
    assert any("PR #1208" in evidence for evidence in provider["evidence"])
    assert any("Phase 707" in evidence for evidence in provider["evidence"])
    assert len(provider["blockers"]) == 2
    assert all("instruction export" not in blocker for blocker in provider["blockers"])
    assert any("refresh schedule" in blocker for blocker in provider["blockers"])
    assert len(provider["process1_requested_proof"]) == 2
    assert all(
        "entry-ECX" not in request and "receiver provenance" not in request
        for request in provider["process1_requested_proof"]
    )


def test_phase708_tracks_pose_writer_physical_abi_without_semantic_promotion() -> None:
    closed = {row["boundary"]: row for row in build_frontier()["closed_boundaries"]}
    abi = closed["BODY0 bind pose-writer physical ABI"]
    assert "PR #1210" in abi["proof"]
    assert abi["BODY0_pointer_proven"] is False
    assert abi["BODY0_bind_origin_proven"] is False
    assert abi["BODY0_bind_basis_proven"] is False
    assert abi["BODY0_bind_frame_proof_ready"] is False

    joins = {row["id"]: row for row in build_frontier()["cross_chain_joins"]}
    transform = joins["body_pose_to_renderer_world_transform"]
    assert transform["state"] == "renderer_sink_ready_retail_bind_witness_pending"
    assert any("PR #1210" in evidence for evidence in transform["evidence"])
    assert any("Phase 707" in evidence for evidence in transform["evidence"])
    assert transform["blockers"] == [
        "positive SHIFT.BMWBody0BindFrameProof/1 with source-backed BODY0 pointer, bind origin and bind basis semantics is not committed",
    ]
    assert "none on renderer transport" in transform["additional_dependency"]
    assert "infer pose-writer parameter semantics" in transform["policy"]


def test_phase708_marks_renderer_transport_647_649_closed() -> None:
    closed = {row["boundary"]: row for row in build_frontier()["closed_boundaries"]}
    assert closed["dynamic vehicle world-transform transport core"]["phase"] == 646
    live = closed["live vehicle Vulkan vertex upload"]
    assert live["phase"] == 647
    assert live["proof"].startswith("SHIFT.LiveVehicleVertexBufferUpload/1")
    wiring = closed["shift_runtime vehicle Vulkan frame wiring"]
    assert wiring["phase"] == 648
    assert wiring["retail_transform_producer_claimed"] is False
    persistent = closed["persistent Phase706 transform -> live Vulkan upload"]
    assert persistent["phase"] == 649
    assert persistent["proof"] == "SHIFT.PersistentVehicleVulkanUpload/1"
    assert persistent["stale_transform_rejected_before_gpu_access"] is True


def test_phase708_keeps_transform_and_machine_promotions_fail_closed() -> None:
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
    assert guards["retail_body_owner_identity_ready"] is True
    assert guards["retail_identity_injected_by_caller"] is False
    assert guards["body_pose_to_vehicle_transform_promotion_allowed"] is False
    assert guards["phase645_static_bind_transform_is_dynamic_pose"] is False
    assert guards["phase646_transport_core_is_body_frame_proof"] is False
    assert guards["phase704_composition_contract_is_retail_bind_proof"] is False
    assert guards["phase706_persistent_transform_is_renderer_mutation"] is False
    assert guards["phase649_renderer_sink_ready"] is True
    assert guards["phase649_renderer_sink_is_retail_transform_producer"] is False
    assert guards["body0_pose_writer_physical_abi_implies_semantic_bind_roles"] is False
    assert guards["original_game_execution_required"] is False
    assert guards["new_runtime_capture_required"] is False

    joins = {row["id"]: row for row in report["cross_chain_joins"]}
    assert joins["outer_update_cadence_owner"]["process2_action"] == REQUEST_PROCESS1
    assert joins["body_to_vehicle_identity"]["process2_action"] == "closed"
    assert joins["body_pose_to_renderer_world_transform"]["process2_action"] == REQUEST_PROCESS1
    assert joins["retail_resource_to_initial_body_state"]["process2_action"] == REQUEST_PROCESS1


def test_phase708_builder_emits_stable_machine_readable_report(tmp_path: Path) -> None:
    output = tmp_path / "provider_frontier.json"
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/build_native_vehicle_external_provider_frontier.py"),
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
