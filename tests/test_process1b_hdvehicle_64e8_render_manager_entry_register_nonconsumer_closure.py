import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_render_manager_entry_register_nonconsumer_closure.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_target_inventory_and_cumulative_closure():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8RenderManagerEntryRegisterNonconsumerClosure/1"
    assert data["ready"] is True
    assert [item["entry"] for item in data["targets"]] == [
        "0x00459140",
        "0x0045abe0",
        "0x00489ad0",
        "0x00493fb0",
    ]
    adj = data["adjudication"]
    assert adj["newly_closed_direct_target_count"] == 4
    assert adj["cumulative_explicitly_closed_direct_target_count"] == 11
    assert adj["remaining_bounded_direct_target_count"] == 6


def test_entry_receiver_is_not_observed_or_returned_as_outer_root():
    data = load_evidence()
    for item in data["targets"]:
        assert item["exact_outer_root_observed_from_entry_register"] is False
    singleton_returns = {item["entry"]: item.get("returned_value") for item in data["targets"]}
    assert singleton_returns["0x00489ad0"] == "0x00bc9fc0"
    assert singleton_returns["0x00493fb0"] == "0x00bcae00"
    assert next(item for item in data["targets"] if item["entry"] == "0x00489ad0")["returned_value_is_exact_outer_root"] is False
    assert next(item for item in data["targets"] if item["entry"] == "0x00493fb0")["returned_value_is_exact_outer_root"] is False


def test_fail_closed_frontier_is_preserved():
    adj = load_evidence()["adjudication"]
    assert adj["these_targets_can_create_persist_or_return_exact_outer_root_from_entry_receiver"] is False
    assert adj["bounded_17_target_opaque_callee_surface_complete"] is False
    assert adj["external_or_unknown_origin_alias_surface_complete"] is False
    assert adj["two_unknown_origin_hdvehicle_4330_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
