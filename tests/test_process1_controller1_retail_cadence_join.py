from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JOIN = ROOT / "evidence/process1_controller1_retail_cadence_join.json"
OWNER = ROOT / "evidence/process1_physics_manager_controller_owner.json"
PACING = ROOT / "evidence/process1_controller1_alertable_pacing.json"
CADENCE = ROOT / "evidence/s5_retail_outer_update_cadence.json"
POLICY = ROOT / "native_runtime/src/runtime_loop_policy.hpp"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_process1_join_uses_existing_authoritative_contracts() -> None:
    join = _load(JOIN)
    owner = _load(OWNER)
    pacing = _load(PACING)
    cadence = _load(CADENCE)

    assert join["format"] == "SHIFT.Process1Controller1RetailCadenceJoin/1"
    assert join["ready"] is True
    assert owner["format"] == "SHIFT.Process1PhysicsManagerControllerOwner/1"
    assert owner["ready"] is True
    assert pacing["format"] == "SHIFT.Process1Controller1AlertablePacing/1"
    assert pacing["ready"] is True
    assert cadence["format"] == "SHIFT.RetailOuterUpdateCadence/1"
    assert cadence["ready"] is True

    assert join["inputs"]["controller_owner"]["format"] == owner["format"]
    assert join["inputs"]["controller_pacing"]["format"] == pacing["format"]
    assert join["inputs"]["retail_outer_cadence"]["format"] == cadence["format"]
    assert join["promotion"]["existing_s5_cadence_reused_without_reproof"] is True
    assert join["limits"]["new_machine_code_claims_added"] is False


def test_controller_and_physics_manager_identities_join_exactly() -> None:
    join = _load(JOIN)
    owner = _load(OWNER)
    pacing = _load(PACING)
    cadence = _load(CADENCE)
    identity = join["identity_join"]

    assert identity["controller_name"] == owner["controller_registration"]["controller_name"]
    assert identity["controller_name"] == pacing["joins"]["controller_name"]
    assert identity["controller_worker"] == owner["controller_worker"]["worker_target"]
    assert identity["controller_worker"] == pacing["joins"]["controller_worker"]
    assert identity["controller_worker"] == cadence["bmanager_registration_dispatch"]["worker_loop"]

    assert identity["manager_scheduler"] == owner["manager_scheduler"]["function"]
    assert identity["manager_scheduler"] == cadence["bmanager_registration_dispatch"]["manager_timing_gate"]
    assert identity["physics_manager_vtable"] == owner["physics_manager"]["vtable"]
    assert identity["physics_manager_vtable"] == cadence["owner_handoff"]["vtable_address"]
    assert identity["physics_manager_default_update_slot_offset"] == owner["manager_scheduler"]["default_virtual_slot_offset"]
    assert identity["physics_manager_default_update_slot_offset"] == cadence["bmanager_registration_dispatch"]["default_dispatch_slot_offset"]
    assert identity["physics_manager_default_update_target"] == owner["physics_manager"]["update_target"]
    assert identity["physics_manager_default_update_target"] == cadence["bmanager_registration_dispatch"]["default_dispatch_target"]


def test_controller_polling_is_not_promoted_to_physics_or_render_cadence() -> None:
    join = _load(JOIN)
    pacing = _load(PACING)
    cadence = _load(CADENCE)

    controller = join["timing_domains"]["controller_worker"]
    physics = join["timing_domains"]["physics_manager"]

    assert controller["requested_timeout_ms"] == pacing["worker_pacing"]["requested_milliseconds"] == 10
    assert pacing["worker_pacing"]["alertable"] is True
    assert controller["exact_frequency_hz_proven"] is False
    assert controller["is_physics_cadence"] is False
    assert controller["is_render_cadence"] is False
    assert cadence["bmanager_registration_dispatch"]["poll_sleep_is_physics_cadence"] is False
    assert cadence["limits"]["worker_poll_10ms_promoted"] is False
    assert cadence["limits"]["rendered_frame_equivalence_claimed"] is False

    assert physics["nominal_frequency_hz"] == cadence["outer_manager_cadence"]["configured_frequency_hz"] == 30.0
    assert physics["quantized_gate_ms"] == cadence["outer_manager_cadence"]["period_ms"] == 33
    assert physics["normal_outer_increment_seconds"] == cadence["fixed_step_accumulator"]["normal_outer_increment_seconds"]
    assert physics["steady_scheduler_invocations_per_default_dispatch"] == cadence["scheduler_multiplicity"]["steady_state_scheduler_invocations_per_manager_dispatch"] == 1
    assert physics["scheduler_authority"] == cadence["runtime_handoff"]["scheduler_authority"] == "RetailEvidence"


def test_native_policy_consumes_s5_retail_authority_not_host_or_polling_clock() -> None:
    join = _load(JOIN)
    cadence = _load(CADENCE)
    policy = POLICY.read_text(encoding="utf-8")

    assert "kRetailOuterNominalFrequencyHz = 30.0" in policy
    assert "kRetailOuterGatePeriodMs = 33" in policy
    assert "kRetailNormalOuterIncrementSeconds" in policy
    assert "kNativeContinuousFixedDt = 1.0 / 60.0" in policy
    assert "RetailOuterSchedulerContract" in policy
    assert "RuntimeSchedulerAuthority::RetailEvidence" in policy
    assert "host 1/60 pacing cannot satisfy retail scheduler/cadence authority" in policy

    runtime_join = join["runtime_join"]
    assert runtime_join["nominal_frequency_hz"] == cadence["runtime_handoff"]["outer_schedule"]["nominal_frequency_hz"]
    assert runtime_join["gate_period_ms"] == cadence["runtime_handoff"]["outer_schedule"]["gate_period_ms"]
    assert runtime_join["normal_outer_increment_seconds"] == cadence["runtime_handoff"]["simulation_quantum"]["normal_outer_increment_seconds"]
    assert runtime_join["controller_sleep_used_as_runtime_frequency_source"] is False
    assert runtime_join["host_1_60_used_as_retail_frequency_source"] is False


def test_join_keeps_next_render_wake_question_fail_closed() -> None:
    join = _load(JOIN)
    promotion = join["promotion"]

    assert promotion["controller_thread_lifecycle_to_manager_owner_joined"] is True
    assert promotion["manager_owner_to_existing_retail_cadence_joined"] is True
    assert promotion["runtime_retail_scheduler_authority_matches_existing_s5_evidence"] is True
    assert promotion["controller_10ms_equals_100hz_proven"] is False
    assert promotion["controller_cadence_equals_physics_cadence_proven"] is False
    assert promotion["physics_cadence_equals_render_cadence_proven"] is False
    assert promotion["one_physics_update_per_rendered_frame_proven"] is False
    assert join["limits"]["render_frame_cadence_proven"] is False
    assert "alertable wake" in join["next_blocker"]["description"]
    assert join["next_blocker"]["process"] == 1
