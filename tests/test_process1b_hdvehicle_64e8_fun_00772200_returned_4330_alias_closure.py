import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_772200_returned_4330_alias_closure.json"


def data():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_returned_receiver_shape_and_caller_inventory():
    p = data()
    assert p["format"] == "SHIFT.HDVehicle64e8Fun00772200Returned4330AliasClosure/1"
    assert p["callee"]["returned_receiver"] == "0x0077233f mov eax,esi"
    assert p["callee"]["returns_input_receiver"] is True
    assert {c["callsite"] for c in p["direct_callers"]} == {"0x0076b247", "0x00798f5c"}


def test_exact_hdvehicle_caller_ignores_returned_alias():
    exact = next(c for c in data()["direct_callers"] if c["caller"] == "FUN_0076b130")
    assert "HDVehicle+0x4330" in exact["receiver"]
    assert exact["post_call_exact_eax_store"] is False
    assert exact["post_call_exact_eax_forward"] is False
    assert exact["returned_4330_alias_escapes"] is False


def test_other_caller_is_stack_local_and_fail_closed_frontier_remains():
    p = data()
    other = next(c for c in p["direct_callers"] if c["caller"] == "FUN_00798df0")
    assert "EBP-0x238c" in other["receiver"]
    assert other["receiver_is_exact_hdvehicle_4330"] is False
    a = p["adjudication"]
    assert a["fun_00772200_returned_4330_alias_surface_complete"] is True
    assert a["downstream_consumer_persistence_return_surface_complete"] is False
    assert a["global_runtime_derived_4330_alias_surface_complete"] is False
    assert a["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert a["last_literal_0x004b86cf_rejected"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7
