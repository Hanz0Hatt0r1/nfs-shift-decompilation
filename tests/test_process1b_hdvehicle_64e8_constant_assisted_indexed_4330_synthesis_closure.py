import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_constant_assisted_indexed_4330_synthesis_closure.json"


def data():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_symbolic_transition_inventory_and_known_outputs_only():
    p = data()
    assert p["format"] == "SHIFT.HDVehicle64e8ConstantAssistedIndexed4330SynthesisClosure/1"
    s = p["scan"]
    assert s["symbolic_transition_count"] == 181901
    assert s["register_or_index_assisted_transition_count"] == 152
    assert s["base_plus_0x4330_production_count"] == 5
    assert s["hidden_constant_assisted_indexed_production_count"] == 0
    assert all(x["steps"] == 1 for x in s["productions"])


def test_complex_frontier_stays_fail_closed():
    a = data()["adjudication"]
    assert a["straight_line_constant_assisted_indexed_4330_synthesis_complete"] is True
    assert a["hidden_constant_assisted_indexed_4330_materializer_count"] == 0
    assert a["two_unknown_origin_or_cross_control_flow_synthesis_complete"] is False
    assert a["opaque_or_external_4330_alias_surface_complete"] is False
    assert a["global_runtime_derived_4330_alias_surface_complete"] is False
    assert a["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert a["last_literal_0x004b86cf_rejected"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7
