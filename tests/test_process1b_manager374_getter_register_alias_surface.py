import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_manager_374_getter_register_alias_surface.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_authority_and_counts():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8Manager374GetterRegisterAliasSurface/1"
    assert data["ready"] is True
    assert data["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert data["scope"]["immediate_non_ecx_register_alias_count"] == 10
    assert data["scope"]["immediate_object_field_store_count"] == 0
    assert len(data["sites"]) == 10


def test_exact_register_alias_site_set_is_pinned():
    data = load_evidence()
    assert {(s["function"], s["callsite"], s["alias"]) for s in data["sites"]} == {
        ("FUN_0043a6c0", "0x0043a6e9", "EDI"),
        ("FUN_00492520", "0x00492591", "EDI"),
        ("FUN_00494422", "0x004944b0", "EBX"),
        ("FUN_00495690", "0x00495705", "EBX"),
        ("FUN_00496680", "0x004966c3", "ESI"),
        ("FUN_00498f20", "0x00498f36", "EBX"),
        ("FUN_00499de0", "0x0049a07d", "EDI"),
        ("FUN_004bad20", "0x004bad36", "ESI"),
        ("FUN_004bd000", "0x004bd017", "EDI"),
        ("FUN_0051df70", "0x0051df7a", "EDX"),
    }
    assert all(site["writes_manager_374"] is False for site in data["sites"])


def test_entry_and_helper_domain_disambiguation_is_explicit():
    data = load_evidence()
    by_name = {s["function"]: s for s in data["sites"]}
    assert by_name["FUN_004bad20"]["selected_entry_replaces_alias_before_offsets_0x2174_through_0x21ac"] is True
    assert by_name["FUN_0051df70"]["delayed_local_slot"] == "[ebp-0x4]"
    assert by_name["FUN_0051df70"]["callee_0x0051cb90_receives_output_slot_in_ecx_and_ignores_edx"] is True
    assert by_name["FUN_00494422"]["later_plus_0x374_read_uses_independent_getter"] == "0x0049450d"


def test_register_alias_class_closes_but_global_join_stays_open():
    adj = load_evidence()["adjudication"]
    assert adj["immediate_non_ecx_register_alias_surface_complete"] is True
    assert adj["immediate_object_field_store_surface_complete"] is True
    assert adj["register_alias_writer_count"] == 0
    assert adj["register_alias_surface_places_hdvehicle_plus_0x4330_into_manager_374"] is False
    assert adj["delayed_object_or_unrelated_reconstruction_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
