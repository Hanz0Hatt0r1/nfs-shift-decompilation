import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "hdvehicle_64e8_manager_domain_frontier.json"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_identity_and_target():
    p = _payload()
    assert p["format"] == "SHIFT.HDVehicle64e8ManagerDomainFrontier/1"
    assert p["ready"] is True
    assert p["target"]["root_storage"] == "HDVehicle+0x64e8"
    assert p["target"]["owned_subobject_base"] == "HDVehicle+0x4330"
    assert p["target"]["subobject_offset"] == "0x21b8"


def test_four_literal_sites_collapse_to_two_receiver_domains():
    d = _payload()["literal_store_domains"]
    assert d["singleton_slot"]["store_instruction"] == "0x004b86cf"
    assert d["singleton_slot"]["manager_constructor_zeroes_slot"] == "0x00488e33 [manager+0x374] = 0"
    stores = d["indexed_collection"]["stores"]
    assert [(x["instruction"], x["value"]) for x in stores] == [
        ("0x004bb205", 4),
        ("0x004bca6b", 3),
        ("0x00d775ee", 2),
    ]
    assert all(x["receiver"] == "FUN_0054ed00(manager+0x2a0,index)" for x in stores)


def test_hdvehicle_4330_direct_machine_surface_is_pinned():
    h = _payload()["hdvehicle_4330_machine_surface"]
    assert h["constructor"].startswith("0x0076b241")
    assert h["update"].startswith("0x00768c16")
    assert h["destructor"].startswith("0x00769551")
    assert h["load_forward"].startswith("0x0076e1c1")
    assert h["direct_fun_00489ad0_call_in_constructor_update_destructor"] is False
    assert h["direct_fun_0054ed00_call_in_constructor_update_destructor"] is False


def test_fail_closed_ownership_and_p1_3_gates():
    a = _payload()["adjudication"]
    assert a["four_literal_store_sites_reduced_to_two_receiver_domains"] is True
    assert a["singleton_slot_join_to_hdvehicle_4330_complete"] is False
    assert a["indexed_collection_join_to_hdvehicle_4330_complete"] is False
    assert a["exact_hdvehicle_64e8_writer_proven"] is False
    assert a["literal_candidates_rejected"] is False
    assert a["alias_or_indirect_registration_still_possible"] is True
    assert a["retail_input_control_provenance_proven"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7
