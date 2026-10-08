import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_manager_374_vptr_receiver_rejections.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_exact_vptr_rejection_inventory():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8Manager374VptrReceiverRejections/1"
    assert data["ready"] is True
    assert data["upstream"]["remaining_site_count_before"] == 20
    assert data["upstream"]["participants_manager_vptr"] == "0x00ab916c"
    assert data["upstream"]["inherited_negative_site_excluded_here"] == "0x005ded7e"
    rows = data["rejections"]
    assert [r["site"] for r in rows] == [
        "0x0074874b",
        "0x008169c3",
        "0x00833972",
        "0x00844343",
        "0x00844b67",
        "0x00d7f104",
    ]
    assert all(r.get("vptr_is_participants_manager") is False or r.get("all_explicit_vptrs_are_not_participants_manager") is True for r in rows)


def test_worklist_reduces_without_promoting_identity_join():
    adj = load_evidence()["adjudication"]
    assert adj["rejected_site_count"] == 6
    assert adj["remaining_literal_store_site_count"] == 14
    assert adj["rejections_use_exact_same_receiver_vptr_identity"] is True
    assert adj["numeric_plus_0x374_equality_used_as_identity"] is False
    assert adj["remaining_literal_store_receiver_provenance_complete"] is False
    assert adj["computed_address_manager_374_writer_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
