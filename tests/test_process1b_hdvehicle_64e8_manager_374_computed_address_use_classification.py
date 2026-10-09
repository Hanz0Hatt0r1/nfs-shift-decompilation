import json
from pathlib import Path

EVIDENCE = Path("evidence/hdvehicle_64e8_manager_374_computed_address_use_classification.json")


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_partition_counts_cover_inventory():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8Manager374ComputedAddressUseClassification/1"
    p = data["partition"]
    assert p["inventory_materializer_count"] == 22
    assert p["unwind_metadata_count"] == 2
    assert p["code_materializer_count"] == 20
    assert p["read_only_count"] == 1
    assert p["direct_write_through_count"] == 1
    assert p["return_escape_count"] == 1
    assert p["callee_forwarding_count"] == 17
    assert p["remaining_runtime_paths_where_write_is_still_possible"] == 19


def test_non_runtime_and_read_only_paths_are_pinned():
    data = load_evidence()
    assert [r["site"] for r in data["unwind_metadata"]] == ["0x00a6cfe7", "0x00a6d067"]
    row = data["read_only"][0]
    assert row["site"] == "0x009857b7"
    assert row["store_through_computed_pointer"] is False
    assert row["computed_pointer_forwarded_or_returned"] is False


def test_direct_write_and_escape_frontiers_are_explicit():
    data = load_evidence()
    assert data["direct_write_through"][0]["site"] == "0x00985bd3"
    assert data["direct_write_through"][0]["receiver_provenance_complete"] is False
    assert data["return_escape"][0]["site"] == "0x0052902b"
    assert data["return_escape"][0]["consumer_surface_complete"] is False
    assert len(data["callee_forwarding"]) == 17


def test_fail_closed_gates_remain_unchanged():
    a = load_evidence()["adjudication"]
    assert a["unwind_metadata_rejected_as_runtime_writers"] is True
    assert a["read_only_materializer_rejected_as_writer"] is True
    assert a["use_classification_complete_for_inventory"] is True
    assert a["remaining_runtime_path_count"] == 19
    assert a["remaining_receiver_provenance_complete"] is False
    assert a["computed_address_manager_374_writer_surface_complete"] is False
    assert a["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert a["last_literal_0x004b86cf_rejected"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7
