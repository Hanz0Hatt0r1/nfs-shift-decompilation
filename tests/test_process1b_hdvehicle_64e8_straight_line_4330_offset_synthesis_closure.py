import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_straight_line_4330_offset_synthesis_closure.json"


def data():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_transition_inventory_and_only_known_productions():
    p = data()
    assert p["format"] == "SHIFT.HDVehicle64e8StraightLine4330OffsetSynthesisClosure/1"
    s = p["scan"]
    assert s["affine_transition_count"] == 181525
    assert s["base_plus_0x4330_production_count"] == 5
    assert s["multi_step_base_plus_0x4330_production_count"] == 0
    assert all(x["steps"] == 1 for x in s["productions"])
    assert {x["site"] for x in s["productions"]} == {
        "0x00768c16", "0x00769551", "0x0076b241", "0x0076e1c1", "0x00a70642"
    }


def test_fail_closed_complex_synthesis_frontier():
    a = data()["adjudication"]
    assert a["straight_line_simple_affine_4330_synthesis_surface_complete"] is True
    assert a["hidden_multi_step_simple_affine_4330_materializer_count"] == 0
    assert a["indexed_two_origin_or_cross_control_flow_synthesis_complete"] is False
    assert a["externally_supplied_or_opaque_4330_alias_surface_complete"] is False
    assert a["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert a["last_literal_0x004b86cf_rejected"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7
