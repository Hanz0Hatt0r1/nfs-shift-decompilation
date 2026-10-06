import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/s5_retail_outer_update_cadence.json"
BUILDER = ROOT / "tools/ghidra/build_s5_retail_outer_update_cadence.py"


def _load():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_positive_retail_cadence_handoff_is_pinned_and_admitted():
    report = _load()
    assert report["format"] == "SHIFT.RetailOuterUpdateCadence/1"
    assert report["status"] == "retail-cadence-admitted"
    assert report["ready"] is True
    assert report["blocker"] == "retail-outer-update-scheduler-cadence-admission"
    provenance = report["provenance"]
    assert provenance["source_sha256"] == "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
    assert provenance["retail_pe_md5"] == "705af8b420e5eb1e3834ac43d5533c6b"
    assert provenance["retail_pe_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert len(provenance["machine_byte_anchors"]) >= 10


def test_registration_and_default_dispatch_join_to_source_backed_owner_slot():
    report = _load()
    owner = report["owner_handoff"]
    dispatch = report["bmanager_registration_dispatch"]
    assert owner["verified"] is True
    assert owner["slot_offset"] == 0x18
    assert owner["target"] == "FUN_00711b50"
    assert dispatch["accessor_alias_to_cPhysicsManager_proven"] is True
    assert dispatch["registration_and_default_dispatch_proven"] is True
    assert dispatch["controller_list_offset"] == "0x58"
    assert dispatch["default_mode_flag_offset"] == "0x529"
    assert dispatch["default_mode_flag_value"] == 0
    assert dispatch["default_dispatch_slot_offset"] == "0x18"
    assert dispatch["alternate_mode_slot_offset"] == "0x1c"
    assert dispatch["worker_poll_sleep_ms"] == 10
    assert dispatch["poll_sleep_is_physics_cadence"] is False


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


def test_rate_writer_closes_plus_0x388_domain_without_guessing_final_rate():
    rate = _load()["physics_rate_field"]
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
    assert rate["rate_domain_proven"] is True
    assert rate["final_numeric_rate_not_frozen"] is True


def test_runtime_handoff_selects_retail_authority_but_rejects_false_substitutions():
    report = _load()
    handoff = report["runtime_handoff"]
    assert handoff["scheduler_authority"] == "RetailEvidence"
    assert handoff["retail_cadence_admitted"] is True
    assert handoff["outer_schedule"] == {
        "default_mode_required": True,
        "gate_period_ms": 33,
        "nominal_frequency_hz": 30.0,
    }
    assert handoff["simulation_quantum"]["inner_substep_seconds"] == "1/rate_source"
    assert handoff["must_not_substitute_host_1_60"] is True
    assert handoff["must_not_treat_worker_poll_10ms_as_physics_cadence"] is True
    limits = report["limits"]
    assert limits["host_1_60_promoted"] is False
    assert limits["worker_poll_10ms_promoted"] is False
    assert limits["rendered_frame_equivalence_claimed"] is False
    assert limits["alternate_BManager_mode_admitted"] is False
    assert limits["final_numeric_physics_rate_guessed"] is False
    assert limits["runtime_capture_used"] is False
    assert limits["original_game_executed"] is False


def test_builder_is_fail_closed_and_contains_no_host_1_60_substitution():
    source = BUILDER.read_text(encoding="utf-8")
    assert "SOURCE_SHA256" in source
    assert "PE_MD5" in source
    assert "PE_SHA256" in source
    assert "machine_byte_anchors" in source
    assert "ROUND(1000.0 / 30.0)" in source
    assert "1.0/rate" in source
    assert "1.0 / 60.0" not in source
    assert "host_1_60_promoted\": False" in source
    assert "worker_poll_10ms_promoted\": False" in source
