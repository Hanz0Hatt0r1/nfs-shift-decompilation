import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_manager_374_exact_root_direct_callee_surface.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_authority_and_scope():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8Manager374ExactRootDirectCalleeSurface/1"
    assert data["ready"] is True
    assert data["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert data["manager"]["getter"] == "FUN_00489ad0"
    assert data["manager"]["target_offset"] == "+0x374"
    assert data["scope"]["direct_callee_count"] == 9


def test_exact_root_direct_callee_set_and_single_positive_writer():
    data = load_evidence()
    callees = data["direct_callees"]
    assert len(callees) == 9
    assert {entry["target"] for entry in callees} == {
        "FUN_00471ed0", "FUN_0045b760", "FUN_00d60660", "FUN_005083b0",
        "FUN_004892c0", "FUN_00d610c0", "FUN_00d61310", "FUN_00d61e00",
        "FUN_0040f290",
    }
    positives = [entry for entry in callees if entry["direct_target_write"]]
    assert len(positives) == 1
    assert positives[0]["target"] == "FUN_00d60660"
    assert positives[0]["target_write_instruction"] == "0x00d606f3"
    assert positives[0]["write"] == "manager+0x374 = selected manager+0x2a0 entry"


def test_other_direct_receivers_leave_root_domain_before_descendant_work():
    data = load_evidence()
    negatives = [entry for entry in data["direct_callees"] if not entry["direct_target_write"]]
    assert len(negatives) == 8
    assert all("manager+0x2a0" in entry["receiver_transition"] or "manager+0x2d8" in entry["receiver_transition"] for entry in negatives)


def test_selection_writer_is_disjoint_from_fixed_hdvehicle_and_frontier_stays_fail_closed():
    adj = load_evidence()["adjudication"]
    assert adj["exact_root_direct_callee_surface_complete"] is True
    assert adj["direct_callees_writing_manager_374_count"] == 1
    assert adj["only_direct_nonzero_writer"] == "FUN_00d60660"
    assert adj["only_direct_nonzero_writer_value_domain"] == "allocator-owned manager+0x2a0 selected entry"
    assert adj["only_direct_nonzero_writer_can_equal_fixed_hdvehicle_plus_0x4330"] is False
    assert adj["direct_exact_root_surface_places_hdvehicle_plus_0x4330_into_manager_374"] is False
    assert adj["escaped_storage_paths_complete"] is False
    assert adj["stack_argument_alias_paths_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
