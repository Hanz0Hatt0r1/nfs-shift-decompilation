import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "slot2_vld4c8_wedgesetting_base_writer.json"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_and_owned_destination():
    p = _payload()
    assert p["format"] == "SHIFT.Slot2VehicleLoadData4c8WedgeSettingBaseWriter/1"
    assert p["ready"] is True
    assert p["wedge_setting_load"]["retail_key"] == "WedgeSetting"
    assert p["wedge_setting_load"]["retail_key_address"] == "0x00b0ec14"
    assert p["wedge_setting_load"]["normalized_destination"] == "nested+0x4c0 = VehicleLoadData+0x4c8"


def test_single_double_parser_path_is_pinned():
    p = _payload()["parser_boundary"]
    assert p["function"] == "FUN_007a6a90"
    assert p["format_address"] == "0x00b0c570"
    assert p["format_literal"] == "(%lf)"
    assert p["successful_assignment_count_checked"] == 1
    assert p["selected_numeric_value_proven"] is False


def test_fresh_optional_override_is_skipped_but_runtime_remains_open():
    o = _payload()["override_relation"]
    assert o["override_source"] == "HDVehicle+0x64e8"
    assert o["fresh_override_source_value"] == -1
    assert o["fresh_override_skipped"] is True
    assert o["runtime_non_sentinel_override_proven"] is False
    a = _payload()["adjudication"]
    assert a["vld_4c8_base_resource_writer_proven"] is True
    assert a["wedge_setting_resource_load_proven"] is True
    assert a["fresh_mode4_override_skipped"] is True
    assert a["runtime_non_sentinel_override_proven"] is False
    assert a["selected_wedge_setting_numeric_value_proven"] is False
    assert a["retail_input_control_provenance_proven"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7
