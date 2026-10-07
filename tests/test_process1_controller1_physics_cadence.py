from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/process1_controller1_physics_cadence.json"
PRIOR = ROOT / "evidence/process1_physics_manager_controller_owner.json"
DOC = ROOT / "docs/PROCESS_1_CONTROLLER1_PHYSICS_CADENCE.md"


def test_controller1_physics_cadence_contract_is_exact() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    assert payload["format"] == "SHIFT.Process1Controller1PhysicsCadence/1"
    assert payload["ready"] is True
    assert payload["source"]["authority"] == "PC retail 1.02"
    assert payload["source"]["retail_executable_md5"] == "705af8b420e5eb1e3834ac43d5533c6b"
    assert payload["source"]["retail_executable_sha256"] == (
        "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    )
    assert payload["source"]["retail_source_sha256"] == (
        "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
    )
    assert payload["source"]["xbox_recomp_required"] is False

    controller = payload["controller_1_polling"]
    assert controller["controller_name"] == "Controller #1"
    assert controller["worker"] == "FUN_00662880"
    assert controller["sleep_wrapper"] == "FUN_00649780"
    assert controller["sleep_api"] == "SleepEx"
    assert controller["sleep_timeout_ms"] == 10
    assert controller["sleep_alertable"] is True
    assert controller["sleep_occurs_after_manager_dispatch_in_loop"] is True
    assert controller["fixed_wakeup_frequency_proven"] is False
    assert controller["nominal_100hz_claim_forbidden"] is True
    assert controller["render_frame_wakeup_relation_proven"] is False

    assert controller["machine_spans"]["controller_loop_dispatch_sleep_backedge"]["sha256"] == (
        "7162bf4986b40ba0fed17689144c996ff3787896c6e357fff93802ba957f8812"
    )
    sleep_span = controller["machine_spans"]["sleep_ex_wrapper"]
    assert sleep_span["sha256"] == (
        "260451a7ed8644869aebf1085cde645cf66e9be0397021c69457405e77d760a5"
    )
    assert sleep_span["iat_cell"] == "0x00aa6274"
    assert sleep_span["iat_symbol"] == "SleepEx"


def test_physics_manager_30hz_is_distinct_internal_scheduler_contract() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    manager = payload["physics_manager_internal_cadence"]

    assert manager["physics_manager_vtable"] == "0x00b04524"
    assert manager["initialization_slot_offset"] == "0x4"
    assert manager["initialization_target"] == "FUN_00710a70"
    assert manager["frequency_setter"] == "FUN_00647860"
    assert manager["desired_frequency_hz"] == 30.0
    assert manager["desired_frequency_f32_bits"] == "0x41f00000"
    assert manager["fixed_frequency_mode_offset"] == "0xdc"
    assert manager["fixed_frequency_mode_value"] == 1
    assert manager["integer_period_ms_offset"] == "0xe8"
    assert manager["integer_period_ms"] == 33
    assert manager["integer_period_derivation"] == "truncate(1000.0 / 30.0)"
    assert manager["mode_byte_offset"] == "0xf8"
    assert manager["mode_byte_value"] == 0
    assert "Desired Freq" in manager["diagnostic_label"]
    assert manager["selected_mode_max_dispatches_per_scheduler_invocation"] == 1
    assert manager["selected_mode_uses_elapsed_accumulator"] is True
    assert manager["selected_mode_retains_residual_after_dispatch"] is True
    assert manager["selected_mode_exact_wall_clock_30hz_proven"] is False

    spans = manager["machine_spans"]
    assert spans["physics_manager_init_slot_pointer"]["sha256"] == (
        "af5a703bed6ab7af99e1cc148b10e9bcff1c0bd9546366b80fc8158bcf9a9547"
    )
    assert spans["physics_manager_30hz_setter_call"]["sha256"] == (
        "42287985821d4791ba878c05c057a41dac685024c263aeb37d8664ad806068da"
    )
    assert spans["manager_frequency_setter"]["sha256"] == (
        "22c1656bac743db9d3ca84ff703ea79036fee14e63f93e3095a87b2dd5422081"
    )
    assert spans["manager_selected_single_dispatch_branch_gate"]["sha256"] == (
        "58438134add52369441bb9ded374dd3e5d66b59b57b7c5b651a69b091ba3943e"
    )
    assert spans["manager_selected_single_dispatch_branch"]["sha256"] == (
        "38ff27af839ae9ea9a8745aa6e12efcfa1b0c3e4240791fa639a517f6aeaedb9"
    )


def test_cadence_domains_remain_fail_closed_from_render() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    separation = payload["cadence_separation"]
    promotion = payload["promotion"]

    assert separation["controller_poll_timeout_ms"] == 10
    assert separation["physics_manager_desired_frequency_hz"] == 30.0
    assert separation["physics_manager_integer_period_ms"] == 33
    assert separation["controller_poll_timeout_equals_physics_manager_period"] is False
    assert separation["controller_polling_frequency_equals_physics_frequency_proven"] is False
    assert separation["physics_manager_frequency_equals_render_frequency_proven"] is False
    assert separation["controller_polling_equals_render_frequency_proven"] is False
    assert separation["render_frame_cadence_proven"] is False

    assert promotion["controller1_alertable_10ms_polling_proven"] is True
    assert promotion["physics_manager_desired_30hz_configuration_proven"] is True
    assert promotion["physics_manager_33ms_integer_period_proven"] is True
    assert promotion["physics_manager_selected_single_dispatch_mode_proven"] is True
    assert promotion["exact_controller_wakeup_frequency_proven"] is False
    assert promotion["exact_physics_wall_clock_frequency_proven"] is False
    assert promotion["render_frame_cadence_proven"] is False
    assert promotion["one_physics_manager_update_per_render_frame_proven"] is False

    document = DOC.read_text(encoding="utf-8")
    assert "This is **not** a proven 100 Hz controller frequency." in document
    assert "No equality among those domains is inferred." in document
    assert "10 ms Controller #1 polling timeout" in document
    assert "!= 30 Hz Physics Manager desired cadence" in document
    assert "!= render/presentation cadence" in document


def test_contract_closes_prior_wake_question_without_rewriting_prior_evidence() -> None:
    prior = json.loads(PRIOR.read_text(encoding="utf-8"))
    current = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    assert prior["format"] == "SHIFT.Process1PhysicsManagerControllerOwner/1"
    assert prior["promotion"]["exact_controller_wakeup_frequency_proven"] is False
    assert "wake/synchronization cadence" in prior["next_blocker"]["description"]

    assert current["controller_1_polling"]["sleep_timeout_ms"] == 10
    assert current["controller_1_polling"]["fixed_wakeup_frequency_proven"] is False
    assert "alertable-wake/APC" in current["next_blocker"]["description"]
    assert current["next_blocker"]["process"] == 1
