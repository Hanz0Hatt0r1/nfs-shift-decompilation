import json
from pathlib import Path

EVIDENCE = Path("evidence/p1b_p1_3_computed_forwarding_integration_frontier.json")
COMPUTED = Path("evidence/p1b_manager374_computed_runtime_closure.json")


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def load_computed():
    return json.loads(COMPUTED.read_text(encoding="utf-8"))


def test_all_six_computed_forwarding_sites_are_closed():
    data = load_evidence()
    assert data["format"] == "SHIFT.P1B.P13ComputedForwardingIntegrationFrontier/1"
    assert data["queue"]["integration_owner"] == "Process 1B"
    assert data["closed_site_count"] == 6
    assert data["closed_sites"] == [
        "0x005292db",
        "0x005f4ffa",
        "0x005f6eda",
        "0x0070f62d",
        "0x0070fb45",
        "0x0070fdeb",
    ]
    assert data["remaining_site_count"] == 0
    assert data["remaining_sites"] == []
    assert data["remaining_owner"] is None


def test_all_shard_handoff_contracts_are_consumed():
    data = load_evidence()
    contracts = {row["contract"] for row in data["consumed_handoffs"]}
    assert contracts == {
        "SHIFT.HDVehicle64e8Manager374P13A005292dbReceiverRejection/1",
        "SHIFT.HDVehicle64e8Manager374P13A005f4ffaReceiverRejection/1",
        "SHIFT.HDVehicle64e8Manager374P13B005f6edaReceiverRejection/1",
        "SHIFT.HDVehicle64e8Manager374P13B0070f62dVptrRejection/1",
        "SHIFT.P1D.P13D.B04524ComputedReceiverRejections/1",
    }


def test_aggregate_computed_forwarding_is_closed_but_identity_is_not():
    a = load_evidence()["adjudication"]
    assert a["p1_3a_computed_forwarding_complete"] is True
    assert a["p1_3b_computed_forwarding_complete"] is True
    assert a["p1_3d_computed_forwarding_complete"] is True
    assert a["aggregate_computed_forwarding_complete"] is True
    assert a["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert a["last_literal_0x004b86cf_rejected"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7


def test_computed_runtime_aggregate_cannot_drift_from_integration_frontier():
    frontier = load_evidence()
    computed = load_computed()
    assert computed["format"] == "SHIFT.P1B.Manager374ComputedRuntimeClosure/1"
    assert computed["surface"]["receiver_or_destination_forwarding_path_count"] == 6
    assert computed["surface"]["receiver_or_destination_forwarding_paths_closed"] == 6
    assert computed["surface"]["remaining_computed_runtime_path_count"] == 0
    assert computed["adjudication"]["computed_runtime_paths_complete"] is True
    assert frontier["closed_site_count"] == computed["surface"]["receiver_or_destination_forwarding_paths_closed"]
    assert frontier["remaining_site_count"] == computed["surface"]["remaining_computed_runtime_path_count"]
