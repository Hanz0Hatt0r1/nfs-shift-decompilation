import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "slot2_vld3a0_3a8_bootstrap_zero.json"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_and_receiver_normalization():
    p = _payload()
    assert p["format"] == "SHIFT.Slot2VehicleLoadData3a0_3a8BootstrapZero/1"
    assert p["ready"] is True
    c = p["constructor_chain"]
    assert c["vehicle_load_data_constructor"] == "FUN_007c3170"
    assert c["nested_receiver_setup"] == "0x007c31a3 ECX = VehicleLoadData+0x8"
    stores = c["normalized_stores"]
    assert [(s["instruction"], s["root_store"]) for s in stores] == [
        ("0x007c11fa", "VehicleLoadData+0x3a0"),
        ("0x007c1200", "VehicleLoadData+0x3a8"),
    ]


def test_x87_top_is_zero_for_both_qword_stores():
    z = _payload()["x87_zero_proof"]
    assert z["zero_seeds"] == ["0x007c1087 fldz", "0x007c108f fldz"]
    assert z["store_top_value"] == 0.0
    assert z["same_top_value_for_both_target_stores"] is True


def test_slot2_bootstrap_join_is_zero_but_runtime_is_open():
    j = _payload()["slot2_join"]
    assert j["fresh_hdvehicle_5238_value"] == 0.0
    assert j["fresh_hdvehicle_5240_value"] == 0.0
    assert j["runtime_overwrite_proven"] is False
    a = _payload()["adjudication"]
    assert a["vld_3a0_bootstrap_writer_proven"] is True
    assert a["vld_3a8_bootstrap_writer_proven"] is True
    assert a["vld_3a0_bootstrap_zero_proven"] is True
    assert a["vld_3a8_bootstrap_zero_proven"] is True
    assert a["runtime_value_producers_proven"] is False
    assert a["retail_input_control_provenance_proven"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7
