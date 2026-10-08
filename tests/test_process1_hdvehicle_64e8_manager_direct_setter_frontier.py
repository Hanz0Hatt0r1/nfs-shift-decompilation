import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "hdvehicle_64e8_manager_direct_setter_frontier.json"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_and_target():
    p = _payload()
    assert p["format"] == "SHIFT.HDVehicle64e8ManagerDirectSetterFrontier/1"
    assert p["ready"] is True
    assert p["target"]["manager_getter"] == "FUN_00489ad0"
    assert p["target"]["slot"] == "manager+0x374"
    assert p["target"]["identity_join_needed"] == "manager+0x374 value == HDVehicle+0x4330"


def test_constructor_zero_is_pinned():
    c = _payload()["constructor"]
    assert c["function"] == "FUN_00488dc0"
    assert c["direct_slot_store"] == "0x00488e33 [manager+0x374] = 0"
    assert c["initial_slot_value"] == 0


def test_direct_manager_receiver_inventory_is_complete_and_has_no_setter():
    d = _payload()["direct_manager_receiver_calls"]
    assert d["total_calls"] == 44
    assert d["unique_targets"] == 12
    targets = d["targets"]
    assert len(targets) == 12
    assert sum(t["call_count"] for t in targets) == 44
    assert {t["function"] for t in targets} == {
        "FUN_004042e0",
        "FUN_00489430",
        "FUN_00489480",
        "FUN_00489310",
        "FUN_00402400",
        "FUN_004892c0",
        "FUN_00487240",
        "FUN_004894d0",
        "FUN_00488a60",
        "FUN_00488ad0",
        "FUN_0048c070",
        "FUN_004939e0",
    }
    assert all(t["direct_store_to_plus_0x374"] is False for t in targets)


def test_fail_closed_gate():
    a = _payload()["adjudication"]
    assert a["constructor_zero_proven"] is True
    assert a["direct_manager_receiver_method_setter_found"] is False
    assert a["direct_manager_receiver_method_setter_surface_exhausted"] is True
    assert a["indirect_virtual_alias_setter_still_possible"] is True
    assert a["singleton_slot_join_to_hdvehicle_4330_complete"] is False
    assert a["exact_hdvehicle_64e8_non_sentinel_writer_proven"] is False
    assert a["retail_input_control_provenance_proven"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7
