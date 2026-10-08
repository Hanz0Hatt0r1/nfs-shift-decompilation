import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_render_manager_entry_alias_nonconsumption_surface.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_and_exact_target_set():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8RenderManagerEntryAliasNonConsumptionSurface/1"
    assert data["ready"] is True
    assert data["exact_outer_root"] == "0x00bc185c"
    assert [item["target"] for item in data["targets"]] == [
        "0x00449630",
        "0x00459140",
        "0x0045abe0",
        "0x00468ed0",
        "0x00489ad0",
        "0x00493fb0",
    ]


def test_each_path_destroys_or_replaces_exact_outer_alias():
    targets = {item["target"]: item for item in load_evidence()["targets"]}
    assert targets["0x00449630"]["entry_alias_register"] == "EDX"
    assert targets["0x00449630"]["alias_read_before_kill"] is False
    assert "0x00449639" in targets["0x00449630"]["first_alias_kill"]

    assert targets["0x00459140"]["entry_alias_register"] == "ECX"
    assert targets["0x00459140"]["alias_read_before_kill"] is False
    assert any("0x0045915b" in step for step in targets["0x00459140"]["route"])

    nested = targets["0x0045abe0"]["nested_helper"]
    assert nested["target"] == "0x00886980"
    assert nested["reads_entry_ecx"] is False
    assert "0x0045abe5" in targets["0x0045abe0"]["post_call_alias_kill"]

    assert targets["0x00468ed0"]["alias_read_before_kill"] is False
    assert len(targets["0x00468ed0"]["all_path_kills_before_read"]) == 2


def test_distinct_singleton_returns_are_not_outer_root():
    targets = {item["target"]: item for item in load_evidence()["targets"]}
    manager = targets["0x00489ad0"]
    assert manager["entry_alias_read"] is False
    assert manager["returned_pointer_is_exact_outer_root"] is False
    assert "0x00bc9fc0" in manager["return_value"]

    other = targets["0x00493fb0"]
    assert other["entry_alias_read"] is False
    assert other["returned_pointer_is_exact_outer_root"] is False
    assert "0x00bcae00" in other["return_value"]


def test_bounded_worklist_reduces_ten_to_four_without_opening_global_gates():
    data = load_evidence()
    work = data["worklist"]
    assert work["bounded_direct_target_count_before_this_contract"] == 10
    assert work["closed_target_count_this_contract"] == 6
    assert work["bounded_direct_target_count_after_this_contract"] == 4
    assert work["remaining_targets"] == [
        "0x0045bfc0",
        "0x0045cc50",
        "0x0045db50",
        "0x00462400",
    ]
    adj = data["adjudication"]
    assert adj["six_entry_alias_paths_closed_negative"] is True
    assert adj["bounded_direct_target_opaque_surface_complete"] is False
    assert adj["opaque_callee_created_or_returned_alias_surface_complete"] is False
    assert adj["external_or_unknown_origin_alias_surface_complete"] is False
    assert adj["two_unknown_origin_hdvehicle_4330_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
