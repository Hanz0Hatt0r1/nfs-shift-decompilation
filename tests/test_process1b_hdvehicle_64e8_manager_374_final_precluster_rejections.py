import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "hdvehicle_64e8_manager_374_final_precluster_rejections.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_and_upstream_worklist():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8Manager374FinalPreclusterRejections/1"
    assert data["ready"] is True
    assert data["upstream"]["remaining_literal_site_count"] == 5
    assert data["upstream"]["remaining_sites"] == [
        "0x00865013",
        "0x0097da09",
        "0x0097daf8",
        "0x0097dc63",
        "0x0097ed06",
    ]


def test_00865013_stays_open_on_first_argument_provenance():
    row = load_evidence()["explicit_non_rejection"]
    assert row["site"] == "0x00865013"
    assert row["function"] == "FUN_00864c10"
    assert "first stack argument" in row["target_base_source"]
    assert row["caller_this_vptr"] == "0x00b1d508"
    assert row["caller_this_vptr_proves_target_base_identity"] is False
    assert row["status"] == "open pending exact first-argument provenance"


def test_0097ed06_is_nonzero_producer_negative_only():
    data = load_evidence()
    row = data["rejections"][0]
    assert row["site"] == "0x0097ed06"
    assert row["zero_source"] == "0x0097ecbe xor ebx,ebx"
    assert row["receiver_identity_required_for_nonzero_producer_rejection"] is False
    assert row["receiver_identity_complete"] is False
    assert row["can_place_hdvehicle_plus_0x4330_into_manager_plus_0x374"] is False


def test_four_literal_sites_remain_and_gates_stay_closed():
    data = load_evidence()
    adj = data["adjudication"]
    assert adj["closed_site_count_this_contract"] == 1
    assert adj["remaining_literal_site_count"] == 4
    assert adj["remaining_literal_sites"] == [
        "0x00865013",
        "0x0097da09",
        "0x0097daf8",
        "0x0097dc63",
    ]
    assert adj["literal_manager_374_receiver_provenance_complete"] is False
    assert adj["computed_address_manager_374_writer_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
