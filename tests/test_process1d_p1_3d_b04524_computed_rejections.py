import json
from pathlib import Path


EVIDENCE = Path("evidence/p1d_p1_3d_b04524_computed_rejections.json")


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_p1d_shard_and_receiver_identity_are_pinned():
    data = load_evidence()
    assert data["format"] == "SHIFT.P1D.P13D.B04524ComputedReceiverRejections/1"
    assert data["shard"]["id"] == "P1.3D"
    assert data["shard"]["owner"] == "Process 1D"
    assert data["shard"]["integration_owner"] == "Process 1B"
    assert data["receiver_class"]["vptr"] == "0x00b04524"
    assert data["receiver_class"]["entry_receiver_capture"] == "0x0070fafd ESI = entry ECX"
    assert data["receiver_class"]["constructor_vptr_store"] == "0x0070fb13 mov [esi],0x00b04524"


def test_only_p1d_assigned_computed_sites_are_closed():
    data = load_evidence()
    assert [row["site"] for row in data["sites"]] == ["0x0070fb45", "0x0070fdeb"]
    assert all(row["can_target_participants_manager_plus_0x374"] is False for row in data["sites"])
    assert "0x0070f62d" not in [row["site"] for row in data["sites"]]


def test_handoff_reduces_aggregate_frontier_but_keeps_p13_fail_closed():
    adjudication = load_evidence()["adjudication"]
    assert adjudication["assigned_site_count"] == 2
    assert adjudication["rejected_site_count"] == 2
    assert adjudication["assigned_sites_complete"] is True
    assert adjudication["p1_3d_computed_forwarding_handoff_ready"] is True
    assert adjudication["aggregate_remaining_forwarding_path_count_after_handoff"] == 4
    assert adjudication["aggregate_remaining_sites_after_handoff"] == [
        "0x005292db",
        "0x005f4ffa",
        "0x005f6eda",
        "0x0070f62d",
    ]
    assert adjudication["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adjudication["last_literal_0x004b86cf_rejected"] is False
    assert adjudication["p1_3_control_producer_complete"] is False
    assert adjudication["external_provider_count"] == 7
