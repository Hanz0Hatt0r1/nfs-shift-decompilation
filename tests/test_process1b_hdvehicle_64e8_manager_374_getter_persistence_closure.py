import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_manager_374_getter_persistence_closure.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_authority_and_getter_inventory():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8Manager374GetterPersistenceClosure/1"
    assert data["ready"] is True
    assert data["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert data["getter"] == "FUN_00489ad0"
    assert data["whole_image_direct_getter_callsite_count"] == 394


def test_persistence_partition_is_complete():
    part = load_evidence()["exact_root_persistence_partition"]
    assert part["stack_save_count"] == 9
    assert part["object_or_global_store_count"] == 0
    assert part["previously_closed"]["immediate_eax_stack_saves"] == 2
    assert part["previously_closed"]["delayed_gpr_to_stack_saves"] == 4
    assert len(part["remaining_delayed_eax_to_stack_saves"]) == 3


def test_three_residual_eax_stack_aliases_are_target_negative():
    entries = load_evidence()["exact_root_persistence_partition"]["remaining_delayed_eax_to_stack_saves"]
    assert {e["function"] for e in entries} == {"FUN_00460c80", "FUN_00498b80", "FUN_00499de0"}
    for entry in entries:
        assert entry["root_written_through"] is False
        assert entry["target_plus_0x374_write"] is False
    last = next(e for e in entries if e["function"] == "FUN_00499de0")
    assert last["forwarded_callee"] == "FUN_004939e0 -> FUN_0040f290"
    assert last["callee_target_plus_0x374_write"] is False


def test_frontier_stays_fail_closed_on_reconstruction():
    adj = load_evidence()["adjudication"]
    assert adj["exact_getter_stack_persistence_surface_complete"] is True
    assert adj["exact_getter_object_or_global_persistence_surface_complete"] is True
    assert adj["exact_getter_object_or_global_store_count"] == 0
    assert adj["exact_getter_persistence_can_create_manager_plus_0x374_value"] is False
    assert adj["non_immediate_manager_root_reconstruction_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
