import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_4330_large_consumer_persistence_closure.json"


def data():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_large_consumer_reread_and_forward_inventory():
    p = data()
    assert p["format"] == "SHIFT.HDVehicle64e8Large4330ConsumerPersistenceClosure/1"
    by_name = {x["function"]: x for x in p["large_consumers"]}
    assert by_name["FUN_0076b280"]["exact_param_reread_count"] == 14
    assert by_name["FUN_007618f0"]["exact_param_reread_count"] == 11
    assert len(by_name["FUN_0076b280"]["exact_pointer_forward_sites"]) == 2
    assert len(by_name["FUN_007618f0"]["exact_pointer_forward_sites"]) == 3
    assert all(x["exact_pointer_memory_store"] is False for x in p["large_consumers"])
    assert all(x["exact_pointer_return"] is False for x in p["large_consumers"])


def test_forwarded_consumers_do_not_persist_or_return_pointer():
    p = data()
    assert {x["function"] for x in p["forwarded_consumers"]} == {
        "FUN_00769640", "FUN_007567a0", "FUN_00756bb0", "FUN_00771db0", "FUN_00771e10"
    }
    assert all(x["exact_pointer_store"] is False for x in p["forwarded_consumers"])
    assert all(x["exact_pointer_return"] is False for x in p["forwarded_consumers"])
    assert all(x["exact_pointer_forward"] is False for x in p["forwarded_consumers"])


def test_fail_closed_global_frontier_remains():
    a = data()["adjudication"]
    assert a["large_consumer_exact_param_reread_count"] == 25
    assert a["large_consumer_exact_pointer_forward_count"] == 5
    assert a["bounded_large_consumer_persistence_return_surface_complete"] is True
    assert a["downstream_consumer_persistence_return_surface_complete"] is True
    assert a["global_runtime_derived_4330_alias_surface_complete"] is False
    assert a["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert a["last_literal_0x004b86cf_rejected"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7
