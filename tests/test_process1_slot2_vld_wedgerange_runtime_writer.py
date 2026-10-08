import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "slot2_vld_wedgerange_runtime_writer.json"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_and_owned_loader_receiver():
    p = _payload()
    assert p["format"] == "SHIFT.Slot2VehicleLoadDataWedgeRangeRuntimeWriter/1"
    assert p["ready"] is True
    o = p["owner_chain"]
    assert o["outer_function"] == "FUN_007c3b00"
    assert o["outer_receiver_copy"] == "0x007c3b21 ESI = ECX"
    assert o["loader_receiver_setup"] == "0x007c4009 ECX = ESI+0x8 = VehicleLoadData+0x8"
    assert o["loader_call"] == "0x007c400c call FUN_007be420"


def test_wedge_range_destinations_normalize_to_vld_fields():
    w = _payload()["wedge_range_load"]
    assert w["retail_key"] == "WedgeRange"
    assert w["retail_key_address"] == "0x00b0ec24"
    assert w["normalized_destinations"] == [
        "nested+0x398 = VehicleLoadData+0x3a0",
        "nested+0x3a0 = VehicleLoadData+0x3a8",
        "nested+0x3a8 = VehicleLoadData+0x3b0",
    ]


def test_parser_boundary_uses_three_double_format():
    p = _payload()["parser_boundary"]
    assert p["function"] == "FUN_007a6a90"
    assert p["format_address"] == "0x00b0c584"
    assert p["format_literal"] == "(%lf,%lf,%lf)"
    assert p["destination_order"][:2] == [
        "VehicleLoadData+0x3a0",
        "VehicleLoadData+0x3a8",
    ]
    assert p["resource_values_materialized_here"] is False


def test_runtime_writer_closes_owner_not_control_semantics():
    j = _payload()["slot2_join"]
    assert j["post_construction_writer_owner_proven"] is True
    assert j["exact_loaded_numeric_values_proven"] is False
    assert j["control_semantics_proven"] is False
    a = _payload()["adjudication"]
    assert a["vld_3a0_post_construction_writer_proven"] is True
    assert a["vld_3a8_post_construction_writer_proven"] is True
    assert a["wedge_range_resource_load_proven"] is True
    assert a["resource_value_source_fully_proven"] is False
    assert a["retail_input_control_provenance_proven"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7
