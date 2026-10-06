import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/s5_retail_outer_update_cadence_completion.json"
BUILDER = ROOT / "tools/ghidra/build_s5_retail_outer_update_cadence_completion.py"


def _load():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_completion_requires_positive_base_and_same_owner_vtable():
    report = _load()
    assert report["format"] == "SHIFT.RetailOuterUpdateCadenceCompletion/1"
    assert report["status"] == "retail-cadence-proof-complete"
    assert report["ready"] is True
    assert report["base"] == {
        "format": "SHIFT.RetailOuterUpdateCadence/1",
        "ready": True,
        "retail_pe_md5": "705af8b420e5eb1e3834ac43d5533c6b",
        "source_sha256": "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9",
    }
    owner = report["same_owner_vtable"]
    assert owner["verified"] is True
    assert owner["vtable_address"] == "0x00b04524"
    assert owner["initializer_slot_offset"] == "0x04"
    assert owner["initializer_target"] == "FUN_00710a70"
    assert owner["scheduler_slot_offset"] == "0x18"
    assert owner["scheduler_target"] == "FUN_00711b50"
    assert owner["alternate_slot_offset"] == "0x1c"


def test_steady_scheduler_multiplicity_is_one_not_debug_four():
    multiplicity = _load()["scheduler_multiplicity"]
    assert multiplicity["verified"] is True
    assert multiplicity["multi_call_flag"] == "DAT_00c104a4"
    assert multiplicity["multi_call_flag_initial_storage"] == "PE zero-fill"
    assert multiplicity["source_visible_writers"] == 0
    assert multiplicity["calls_present_in_function"] == 4
    assert multiplicity["normal_calls_per_FUN_0070f940"] == 1
    assert multiplicity["scheduler_object_initial_state"] == 1
    assert multiplicity["steady_active_state"] == 3
    assert multiplicity["steady_state_scheduler_invocations_per_default_manager_dispatch"] == 1


def test_rate_source_is_loaded_tweaker_value_not_constructor_default_guess():
    report = _load()
    rate = report["physics_rate_source"]
    assert rate["verified"] is True
    assert rate["tweaker"] == "Physics Tweaker"
    assert rate["xml"] == "PhysicsTweaker.xml"
    assert rate["field"] == "tick rate"
    assert rate["tweaker_base"] == "DAT_00c12c40"
    assert rate["field_offset"] == "0x492"
    assert rate["runtime_alias"] == "DAT_00c130d2"
    assert rate["constructor_default_rate_hz"] == 180
    assert rate["loaded_value_applied_by"] == "FUN_0070f170"
    assert rate["cPhysicsManager_rate_offset"] == "0x388"
    assert rate["final_loaded_session_rate_frozen"] is False
    assert report["limits"]["constructor_default_180_promoted_to_loaded_session_rate"] is False
    assert report["limits"]["final_numeric_physics_rate_guessed"] is False


def test_completion_handoff_is_retail_authority_without_false_host_substitution():
    report = _load()
    handoff = report["handoff"]
    assert handoff["retail_outer_scheduler_cadence_proof_complete"] is True
    assert handoff["scheduler_authority"] == "RetailEvidence"
    assert handoff["retail_cadence_admitted"] is True
    assert handoff["host_1_60_is_retail_evidence"] is False
    assert handoff["worker_poll_10ms_is_physics_cadence"] is False
    assert report["limits"]["host_1_60_promoted"] is False
    assert report["limits"]["worker_poll_10ms_promoted"] is False
    assert report["limits"]["rendered_frame_equivalence_claimed"] is False


def test_builder_pins_missing_static_closure_fail_closed():
    source = BUILDER.read_text(encoding="utf-8")
    for token in (
        "SOURCE_SHA256",
        "PE_MD5",
        "PE_SHA256",
        "0x00B04528",
        "0x00B0453C",
        "DAT_00c104a4",
        "is_zero_fill",
        "PhysicsTweaker.xml",
        '"tick rate"',
        "0x00C12C40 + 0x492",
        "steady_state_scheduler_invocations_per_default_manager_dispatch",
    ):
        assert token in source
    assert "1.0 / 60.0" not in source
    assert '"host_1_60_promoted": False' in source
    assert '"worker_poll_10ms_promoted": False' in source
