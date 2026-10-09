import json
from pathlib import Path

EVIDENCE = Path("evidence/hdvehicle_64e8_manager_374_source_only_forwarding_batch.json")


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_batch_count_and_groups():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8Manager374SourceOnlyForwardingBatch/1"
    assert data["closed_site_count"] == 11
    groups = data["groups"]
    assert groups["bitmask_source"]["sites"] == ["0x0052aac0"]
    assert groups["string_object_source"]["sites"] == ["0x0075070b", "0x0075096d"]
    assert len(groups["network_format_source"]["sites"]) == 6
    assert groups["network_state_source"]["sites"] == ["0x005f569b", "0x005f5a3e"]


def test_all_closed_groups_are_source_only():
    groups = load_evidence()["groups"]
    assert groups["bitmask_source"]["writes_source"] is False
    assert groups["string_object_source"]["writes_source"] is False
    assert groups["network_format_source"]["writes_source"] is False
    assert groups["network_state_source"]["writes_source"] is False
    assert groups["network_format_source"]["extra_0x005f6593_call"] == "0x008f3df0 is exact one-byte ret and cannot mutate the computed pointer"


def test_remaining_destination_receiver_paths_are_exact():
    data = load_evidence()
    assert data["remaining_forwarding_sites"] == [
        "0x005292db",
        "0x005f4ffa",
        "0x005f6eda",
        "0x0070f62d",
        "0x0070fb45",
        "0x0070fdeb",
    ]
    a = data["adjudication"]
    assert a["source_only_forwarding_site_count"] == 11
    assert a["remaining_callee_forwarding_path_count"] == 6
    assert a["remaining_forwarding_paths_require_receiver_or_destination_identity"] is True


def test_fail_closed_gates_remain_unchanged():
    a = load_evidence()["adjudication"]
    assert a["computed_address_manager_374_writer_surface_complete"] is False
    assert a["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert a["last_literal_0x004b86cf_rejected"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7
