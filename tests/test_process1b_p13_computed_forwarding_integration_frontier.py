import json
from pathlib import Path

EVIDENCE = Path("evidence/p1b_p1_3_computed_forwarding_integration_frontier.json")


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_four_closed_sites_and_two_p1a_sites_remain():
    data = load_evidence()
    assert data["format"] == "SHIFT.P1B.P13ComputedForwardingIntegrationFrontier/1"
    assert data["queue"]["integration_owner"] == "Process 1B"
    assert data["closed_site_count"] == 4
    assert set(data["closed_sites"]) == {
        "0x005f6eda",
        "0x0070f62d",
        "0x0070fb45",
        "0x0070fdeb",
    }
    assert data["remaining_site_count"] == 2
    assert data["remaining_sites"] == ["0x005292db", "0x005f4ffa"]
    assert data["remaining_owner"] == "Process 1A / P1.3A"


def test_integrated_shard_contracts_are_pinned():
    data = load_evidence()
    contracts = {row["contract"] for row in data["consumed_handoffs"]}
    assert "SHIFT.HDVehicle64e8Manager374P13B0070f62dVptrRejection/1" in contracts
    assert "SHIFT.HDVehicle64e8Manager374P13B005f6edaReceiverRejection/1" in contracts
    assert "SHIFT.P1D.P13D.B04524ComputedReceiverRejections/1" in contracts


def test_aggregate_identity_gates_remain_fail_closed():
    a = load_evidence()["adjudication"]
    assert a["p1_3b_computed_forwarding_complete"] is True
    assert a["p1_3d_computed_forwarding_complete"] is True
    assert a["p1_3a_computed_forwarding_complete"] is False
    assert a["aggregate_computed_forwarding_complete"] is False
    assert a["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert a["last_literal_0x004b86cf_rejected"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7
