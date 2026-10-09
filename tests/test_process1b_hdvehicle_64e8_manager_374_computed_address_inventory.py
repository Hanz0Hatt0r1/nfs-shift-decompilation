import json
from pathlib import Path

EVIDENCE = Path("evidence/hdvehicle_64e8_manager_374_computed_address_inventory.json")


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_inventory_shape_and_counts():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8Manager374ComputedAddressInventory/1"
    inv = data["inventory"]
    assert inv["materializer_count"] == 22
    assert inv["code_candidate_count"] == 20
    assert inv["unwind_metadata_candidate_count"] == 2
    assert len(inv["sites"]) == 22


def test_unwind_candidates_are_separated():
    rows = load_evidence()["inventory"]["sites"]
    unwind = [r for r in rows if r["kind"] == "unwind_metadata"]
    assert [r["site"] for r in unwind] == ["0x00a6cfe7", "0x00a6d067"]
    assert all(r["function"].startswith("Unwind@") for r in unwind)


def test_key_code_clusters_are_pinned():
    rows = load_evidence()["inventory"]["sites"]
    sites = {r["site"]: r for r in rows}
    assert sites["0x0052902b"]["function"] == "FUN_00529020"
    assert sites["0x005f6eda"]["function"] == "FUN_005f6850"
    assert sites["0x0070fdeb"]["function"] == "FUN_0070fae0"
    assert sites["0x0075096d"]["function"] == "FUN_007506b0"
    assert sites["0x00985bd3"]["instruction"] == "add esi,0x374"


def test_inventory_is_not_promoted_to_identity_closure():
    adjudication = load_evidence()["adjudication"]
    assert adjudication["explicit_computed_address_worklist_finite"] is True
    assert adjudication["explicit_computed_address_receiver_provenance_complete"] is False
    assert adjudication["computed_address_manager_374_writer_surface_complete"] is False
    assert adjudication["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adjudication["last_literal_0x004b86cf_rejected"] is False
    assert adjudication["p1_3_control_producer_complete"] is False
    assert adjudication["external_provider_count"] == 7
