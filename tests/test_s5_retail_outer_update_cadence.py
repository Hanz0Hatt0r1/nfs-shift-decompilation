import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/s5_retail_outer_update_cadence.json"
BUILDER = ROOT / "tools/ghidra/build_s5_retail_outer_update_cadence.py"


def _load():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_positive_retail_outer_cadence_handoff_is_pinned_and_admitted():
    report = _load()
    assert report["format"] == "SHIFT.RetailOuterUpdateCadence/1"
    assert report["status"] == "retail-outer-cadence-admitted"
    assert report["ready"] is True
    assert report["blocker"] == "retail-outer-update-scheduler-cadence-admission"
    provenance = report["provenance"]
    assert provenance["source_sha256"] == "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
    assert provenance["retail_pe_md5"] == "705af8b420e5eb1e3834ac43d5533c6b"
    assert provenance["retail_pe_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert len(provenance["machine_byte_anchors"]) >= 16


def test_registration_and_default_dispatch_join_to_source_backed_owner_slot():
    report = _load()
    owner = report["owner_handoff"]
    dispatch = report["bmanager_registration_dispatch"]
    assert owner["verified"] is True
    assert owner["vtable_address"] == "0x00b04524"
    assert owner["initializer_slot_offset"] == "0x04"
    assert owner["initializer_target"] == "FUN_00710a70"
    assert owner["slot_offset"] == 0x18
    assert owner["target"] == "FUN_00711b50"
    assert dispatch["accessor_alias_to_cPhysicsManager_proven"] is True
    assert dispatch["registration_and_default_dispatch_proven"] is True
    assert dispatch["controller_list_offset"] == "0x58"
    assert dispatch["default_mode_flag_offset"] == "0x529"
    assert dispatch["default_mode_flag_value"] == 0
    assert dispatch["dispatch_selector"] == "FUN_00647d80"
    assert dispatch["default_dispatch_slot_offset"] == "0x18"
    assert dispatch["alternate_mode_slot_offset"] == "0x1c"
    assert dispatch["worker_poll_sleep_ms"] == 10
    assert dispatch["poll_sleep_is_physics_cadence"] is False


def test_scheduler_multiplicity_is_one_on_default_zero_filled_path():
    report = _load()
    multiplicity = report["scheduler_multiplicity"]
    assert multiplicity["multi_call_flag"] == "DAT_00c104a4"
    assert multiplicity["multi_call_flag_initial_storage"] == "PE zero-fill"
    assert multiplicity["source_visible_writers"] == 0
    assert multiplicity["normal_calls_to_FUN_007155e0_per_FUN_0070f940"] == 1
    assert multiplicity["scheduler_object_initial_state"] == 1
    assert multiplicity["state_transition_surface"] == [
        "1 -> 2",
        "2 -> 3 under active-init condition",
    ]
    assert multiplicity["steady_active_state"] == 3
    assert multiplicity["steady_state_scheduler_invocations_per_manager_dispatch"] == 1
    assert report["adjudication"][
        "one_steady_scheduler_invocation_per_default_manager_dispatch_proven"
    ] is True


def test_outer_gate_and_simulation_quantum_remain_distinct():
    report = _load()
    outer = report["outer_manager_cadence"]
    fixed = report["fixed_step_accumulator"]
    assert outer["configured_frequency_hz"] == 30.0
    assert outer["period_expression"] == "ROUND(1000.0 / 30.0)"
    assert outer["period_ms"] == 33
    assert outer["nominal_hz_and_ms_gate_are_distinct"] is True
    assert abs(fixed["normal_outer_increment_seconds"] - (1.0 / 30.0)) < 5e-9
    assert fixed["normal_scale_increment_is_one_thirtieth"] is True
    assert fixed["substep_dt_expression"] == "1.0/rate"
    assert fixed["fixed_step_semantics_proven"] is True


def test_rate_writer_and_physics_tweaker_default_do_not_guess_loaded_session_rate():
    report = _load()
    rate = report["physics_rate_field"]
    assert rate["writer"] == "FUN_0070f170"
    assert rate["rate_offset"] == "0x388"
    assert rate["reciprocal_offset"] == "0x38c"
    assert rate["rate_over_30_offset"] == "0x390"
    assert rate["thirty_over_rate_offset"] == "0x394"
    assert rate["relationships"] == [
        "+0x388 = rate",
        "+0x38c = 1/rate",
        "+0x390 = rate/30",
        "+0x394 = 30/rate",
    ]
    assert rate["constructor_default_rate_hz"] == 180
    assert rate["tick_rate_tweaker_base"] == "DAT_00c12c40"
    assert rate["tick_rate_tweaker_offset"] == "0x492"
    assert rate["runtime_rate_global"] == "DAT_00c130d2"
    assert rate["runtime_rate_global_is_tweaker_field_alias"] is True
    assert rate["physics_tweaker_xml_load_observed"] is True
    assert rate["rate_domain_proven"] is True
    assert rate["final_numeric_rate_not_frozen"] is True
    assert report["limits"]["constructor_default_180_promoted_to_loaded_session_rate"] is False


def test_runtime_handoff_selects_outer_retail_authority_without_overclaiming_inner_rate():
    report = _load()
    handoff = report["runtime_handoff"]
    assert handoff["scheduler_authority"] == "RetailEvidence"
    assert handoff["retail_outer_cadence_admitted"] is True
    assert handoff["outer_schedule"] == {
        "default_mode_required": True,
        "gate_period_ms": 33,
        "nominal_frequency_hz": 30.0,
    }
    quantum = handoff["simulation_quantum"]
    assert quantum["inner_substep_seconds"] == "1/rate_source"
    assert quantum["constructor_default_rate_hz"] == 180
    assert quantum["constructor_default_substeps_per_normal_outer_increment"] == 6
    assert quantum["session_rate_requires_loaded_PhysicsTweaker_value"] is True
    assert handoff["must_not_substitute_host_1_60"] is True
    assert handoff["must_not_treat_worker_poll_10ms_as_physics_cadence"] is True
    assert report["adjudication"]["outer_scheduler_cadence_admitted"] is True
    assert report["adjudication"]["final_inner_rate_requires_loaded_PhysicsTweaker_value"] is True


def test_limits_reject_false_time_equivalences():
    limits = _load()["limits"]
    assert limits["host_1_60_promoted"] is False
    assert limits["worker_poll_10ms_promoted"] is False
    assert limits["rendered_frame_equivalence_claimed"] is False
    assert limits["alternate_BManager_mode_admitted"] is False
    assert limits["final_numeric_physics_rate_guessed"] is False
    assert limits["constructor_default_180_promoted_to_loaded_session_rate"] is False
    assert limits["runtime_capture_used"] is False
    assert limits["original_game_executed"] is False


def test_builder_is_fail_closed_and_contains_no_host_1_60_substitution():
    source = BUILDER.read_text(encoding="utf-8")
    assert "SOURCE_SHA256" in source
    assert "PE_MD5" in source
    assert "PE_SHA256" in source
    assert "is_zero_fill" in source
    assert "DAT_00c104a4" in source
    assert "0x00c12c40 + 0x492 != 0x00c130d2" in source
    assert "physics_tweaker_default_tick_rate_180" in source
    assert "ROUND(1000.0 / 30.0)" in source
    assert "1.0/rate" in source
    assert "1.0 / 60.0" not in source
    assert "host_1_60_promoted':False" in source
    assert "worker_poll_10ms_promoted':False" in source
