import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_manager_374_exact_receiver_vptr_rejection_batch.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_and_manager_identity():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8Manager374ExactReceiverVptrRejectionBatch/1"
    assert data["ready"] is True
    assert data["manager_identity"]["singleton"] == "0x00bc9fc0"
    assert data["manager_identity"]["root_vptr"] == "0x00ab9190"


def test_exact_rejection_site_set():
    data = load_evidence()
    assert [item["site"] for item in data["rejections"]] == [
        "0x0074874b",
        "0x008169c3",
        "0x00816c9c",
        "0x00833972",
        "0x00844343",
        "0x00844b67",
        "0x00d7f104",
    ]
    assert all(item["rejected_as_manager_374_writer"] is True for item in data["rejections"])


def test_direct_vptr_receivers_differ_from_manager():
    rows = {item["site"]: item for item in load_evidence()["rejections"]}
    assert rows["0x0074874b"]["receiver_vptr"] == "0x00b07938"
    assert rows["0x0074874b"]["vptr_equal"] is False
    assert rows["0x008169c3"]["final_receiver_vptr"] == "0x00b16158"
    assert rows["0x008169c3"]["vptr_equal"] is False
    assert rows["0x00833972"]["final_receiver_vptr"] == "0x00b190a8"
    assert rows["0x00833972"]["vptr_equal"] is False
    assert rows["0x00844343"]["receiver_vptr"] == "0x00b190a8"
    assert rows["0x00844343"]["vptr_equal"] is False
    assert rows["0x00844b67"]["receiver_vptr"] == "0x00b190a8"
    assert rows["0x00844b67"]["vptr_equal"] is False
    assert rows["0x00d7f104"]["receiver_vptr"] == "0x00ac1fc4"
    assert rows["0x00d7f104"]["vptr_equal"] is False


def test_fun_00816c70_receiver_is_exact_owner_child():
    row = {item["site"]: item for item in load_evidence()["rejections"]}["0x00816c9c"]
    prov = row["receiver_provenance"]
    assert "[ecx+0x56c]" in prov["child_getter_body"]
    assert any("push 0x390" in step for step in prov["owner_child_construction"])
    assert any("FUN_008167f0" in step for step in prov["owner_child_construction"])
    assert any("[esi+0x56c]" in step for step in prov["owner_child_construction"])
    assert row["receiver_constructor"] == "FUN_008167f0"
    assert row["receiver_vptr"] == "0x00b16158"
    assert row["vptr_equal"] is False


def test_worklist_reduces_twenty_to_thirteen_and_stays_fail_closed():
    data = load_evidence()
    work = data["worklist_transition"]
    assert work["incoming_site_count"] == 20
    assert work["rejected_site_count"] == 7
    assert work["remaining_site_count"] == 13
    assert work["incoming_function_count"] == 16
    assert work["rejected_function_count"] == 7
    assert work["remaining_function_count"] == 9
    assert len(work["remaining_sites"]) == 13
    assert len(work["remaining_functions"]) == 9

    adj = data["adjudication"]
    assert adj["seven_exact_receiver_sites_rejected"] is True
    assert adj["remaining_literal_store_receiver_provenance_complete"] is False
    assert adj["computed_address_manager_374_writer_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
