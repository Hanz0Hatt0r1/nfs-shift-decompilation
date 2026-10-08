import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_manager_374_literal_store_inventory.json"

EXPECTED_SITES = [
    "0x004826a6", "0x00488e33", "0x0051effd", "0x005ded7e", "0x0074874b",
    "0x007c0fa0", "0x007c1ace", "0x008169c3", "0x00816c9c", "0x00818157",
    "0x00833972", "0x00844343", "0x008446cb", "0x008446e3", "0x008446f8",
    "0x00844b67", "0x00865013", "0x0097da09", "0x0097daf8", "0x0097dc63",
    "0x0097ed06", "0x00a38974", "0x00a44ac5", "0x00d606f3", "0x00d7f104",
]


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_literal_write_inventory_is_exact_and_complete():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8Manager374LiteralStoreInventory/1"
    assert data["ready"] is True
    assert data["manager"]["singleton"] == "0x00bc9fc0"
    assert data["manager"]["target_offset"] == "+0x374"
    inv = data["inventory"]
    assert inv["literal_write_site_count"] == 25
    assert inv["containing_function_count"] == 21
    assert [item["site"] for item in inv["sites"]] == EXPECTED_SITES


def test_constructor_writer_is_exact_zero_init():
    data = load_evidence()
    writers = {item["site"]: item for item in data["proven_manager_domain_sites"]}
    ctor = writers["0x00488e33"]
    assert ctor["function"] == "FUN_00488dc0"
    assert "0x00bc9fc0" in ctor["receiver_proof"]
    assert "xor ebx,ebx" in ctor["value_proof"]
    assert ctor["write"] == "manager+0x374 = 0"
    assert ctor["can_place_hdvehicle_plus_0x4330"] is False


def test_selection_writer_is_allocator_owned_not_fixed_hdvehicle():
    data = load_evidence()
    writers = {item["site"]: item for item in data["proven_manager_domain_sites"]}
    selected = writers["0x00d606f3"]
    assert selected["function"] == "FUN_00d60660"
    assert "manager+0x2a0" in selected["value_proof"]
    assert "allocator-owned" in selected["write"]
    assert selected["can_place_fixed_hdvehicle_plus_0x4330"] is False
    assert selected["upstream_contract"] == "SHIFT.HDVehicle64e8Manager374ExactRootDirectCalleeSurface/1"


def test_remaining_literal_sites_are_worklist_not_rejections():
    data = load_evidence()
    work = data["remaining_receiver_provenance_worklist"]
    assert work["site_count"] == 23
    assert work["function_count"] == 19
    assert set(work["sites"]) == set(EXPECTED_SITES) - {"0x00488e33", "0x00d606f3"}
    assert len(work["functions"]) == 19


def test_broader_identity_and_p1_3_gates_remain_fail_closed():
    data = load_evidence()
    scope = data["scope"]
    assert scope["whole_text_scan"] is True
    assert scope["computed_address_writes_included"] is False
    assert scope["numeric_offset_implies_manager_identity"] is False
    adj = data["adjudication"]
    assert adj["literal_plus_0x374_write_inventory_complete"] is True
    assert adj["proven_manager_domain_literal_writer_count"] == 2
    assert adj["proven_manager_domain_literal_nonzero_writer_count"] == 1
    assert adj["remaining_literal_store_receiver_provenance_complete"] is False
    assert adj["computed_address_manager_374_writer_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
