import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_manager_374_vptr_negative_batch1.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_seven_sites_have_non_manager_receiver_vptrs():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8Manager374VptrNegativeBatch1/1"
    assert data["ready"] is True
    assert data["upstream"]["participants_manager_vptr"] == "0x00ab916c"
    sites = data["rejected_sites"]
    assert len(sites) == 7
    assert [item["site"] for item in sites] == [
        "0x005ded7e", "0x0074874b", "0x008169c3", "0x00833972",
        "0x00844343", "0x00844b67", "0x00d7f104",
    ]
    assert all(item["same_receiver"] is True for item in sites)
    assert all(item["receiver_vptr"] != "0x00ab916c" for item in sites)


def test_worklist_reduces_23_to_16_without_identity_overclaim():
    data = load_evidence()
    adj = data["adjudication"]
    assert adj["rejected_site_count"] == 7
    assert adj["rejected_function_count"] == 7
    assert adj["all_rejected_receivers_have_explicit_incompatible_vptr_before_target_store"] is True
    assert adj["numeric_plus_0x374_equality_used_as_identity"] is False
    assert adj["remaining_literal_store_site_count"] == 16
    assert adj["remaining_literal_store_function_count"] == 12
    assert len(data["remaining_sites"]) == 16


def test_global_join_and_p1_3_remain_fail_closed():
    adj = load_evidence()["adjudication"]
    assert adj["remaining_literal_store_receiver_provenance_complete"] is False
    assert adj["computed_address_manager_374_writer_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
