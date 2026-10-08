import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "hdvehicle_64e8_bootstrap_sentinel.json"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_and_target_alias_arithmetic():
    p = _payload()
    assert p["format"] == "SHIFT.HDVehicle64e8BootstrapSentinel/1"
    assert p["ready"] is True
    t = p["target"]
    assert t["root_storage"] == "HDVehicle+0x64e8"
    assert t["record_base"] == "HDVehicle+0x4330"
    assert t["record_offset"] == "0x21b8"
    assert int("0x21a4", 16) + int("0x14", 16) == int("0x21b8", 16)
    assert int("0x4330", 16) + int("0x21b8", 16) == int("0x64e8", 16)


def test_constructor_callee_sets_target_to_minus_one():
    c = _payload()["constructor_chain"]
    assert c["record_constructor"] == "FUN_00772200"
    assert c["nested_constructor_call"] == "0x007722e0 call FUN_00458a80 with ECX=EDI"
    assert c["writer"] == "FUN_00458a80"
    assert c["contiguous_dword_range"] == "receiver+0x4 through receiver+0xf8 inclusive"
    assert c["target_inside_range"] is True
    assert c["bootstrap_value"] == -1


def test_mode4_consumer_treats_minus_one_as_skip_sentinel():
    c = _payload()["consumer_branch"]
    assert c["function"] == "FUN_007c3b00"
    assert c["load"] == "0x007c48ba EAX = [record+0x21b8]"
    assert c["sentinel_compare"] == "0x007c48c0 compare EAX with -1"
    assert c["sentinel_branch"] == "0x007c48c6 jump to 0x007c48d1 when equal"
    assert c["bootstrap_effect"] == "fresh -1 skips VehicleLoadData+0x4c8 overwrite"


def test_fail_closed_runtime_and_control_gates():
    p = _payload()
    assert p["manager_literal_candidates"]["joined_to_selected_hdvehicle_record"] is False
    a = p["adjudication"]
    assert a["alias_callee_bootstrap_writer_proven"] is True
    assert a["fresh_hdvehicle_64e8_value_proven"] is True
    assert a["fresh_hdvehicle_64e8_is_minus_one"] is True
    assert a["mode4_bootstrap_transfer_to_vld4c8_occurs"] is False
    assert a["later_runtime_writer_proven"] is False
    assert a["retail_input_control_provenance_proven"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7
