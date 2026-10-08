import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_whole_text_4330_materialization_occurrence_closure.json"


def data():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_whole_text_occurrence_inventory():
    p = data()
    assert p["format"] == "SHIFT.HDVehicle64e8WholeText4330MaterializationOccurrenceClosure/1"
    s = p["scan"]
    assert s["whole_text_immediate_or_displacement_0x4330_occurrence_count"] == 6
    assert s["runtime_pointer_arithmetic_site_count"] == 5
    assert s["normal_runtime_materializer_count"] == 4
    assert s["unwind_only_materializer_count"] == 1
    assert s["unknown_generic_single_instruction_materializer_count"] == 0
    assert {x["site"] for x in s["occurrences"]} == {
        "0x00768c16", "0x00769551", "0x0076b241", "0x0076e1c1", "0x007a28ab", "0x00a70642"
    }


def test_rel32_occurrence_is_not_materializer():
    hit = next(x for x in data()["scan"]["occurrences"] if x["site"] == "0x007a28ab")
    assert "rel32" in hit["role"]
    assert "call" in hit["instruction"]


def test_fail_closed_remaining_frontier():
    a = data()["adjudication"]
    assert a["whole_text_single_instruction_4330_materialization_surface_complete"] is True
    assert a["unknown_generic_single_instruction_4330_materializer_exists"] is False
    assert a["known_normal_runtime_materializers_persistence_return_closed"] is True
    assert a["known_unwind_materializer_closed"] is True
    assert a["multi_instruction_runtime_4330_synthesis_complete"] is False
    assert a["externally_supplied_or_opaque_4330_alias_surface_complete"] is False
    assert a["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert a["last_literal_0x004b86cf_rejected"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7
