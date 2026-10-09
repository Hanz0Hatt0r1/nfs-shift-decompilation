import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "build_p1d_slot3_wheel538_handoff.py"
P1A = ROOT / "evidence" / "p1a_p13a_slot01_wheel538_forwarding_frontier.json"
CONSUMER = ROOT / "evidence" / "fun_00755950_absolute_consumed_field_machine_proof.json"
PINNED = ROOT / "evidence" / "p1d_slot3_wheel538_materializer_handoff.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1d_slot3_wheel538_handoff", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_builder_reproduces_pinned_handoff():
    module = load_module()
    assert module.build(P1A, CONSUMER) == json.loads(PINNED.read_text(encoding="utf-8"))


def test_slot3_exact_local_subset_closes_without_promoting_writer():
    payload = json.loads(PINNED.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.P1D.P13DSlot3Wheel538MaterializerHandoff/1"
    assert payload["slot3"] == {
        "slot": 3,
        "wheel_runtime_receiver": "HDVehicle+0x400+3*0xa80",
        "wheel_runtime_receiver_absolute": "HDVehicle+0x2380",
        "local_field": "+0x538",
        "absolute_target": "HDVehicle+0x28b8",
        "width": "f64/qword",
    }
    surface = payload["exact_local_surface"]
    assert surface["whole_image_exact_0x538_scalar_use_count"] == 43
    assert surface["positive_address_materializer_count"] == 4
    assert surface["all_positive_materializers_rejected_as_selected_slot3_f64_producers"] is True
    assert surface["direct_positive_qword_store"] == "0x00761b67 fstp qword [esi+0x538]"
    assert surface["direct_positive_qword_store_slot3_destination"] == "HDVehicle+0x2c00"
    assert surface["direct_positive_qword_store_matches_slot3_target"] is False

    adj = payload["adjudication"]
    assert adj["slot3_exact_local_0x538_materializer_callee_subset_complete"] is True
    assert adj["slot3_direct_positive_qword_0x538_store_rejected"] is True
    assert adj["slot3_base_plus_delta_alias_surface_complete"] is False
    assert adj["slot3_overlapping_bulk_copy_surface_complete"] is False
    assert adj["slot3_writer_provenance_proven"] is False
    assert adj["p1_3d_complete"] is False
    assert adj["external_provider_count"] == 7


def test_builder_rejects_consumer_slot_drift(tmp_path):
    module = load_module()
    p1a = json.loads(P1A.read_text(encoding="utf-8"))
    consumer = json.loads(CONSUMER.read_text(encoding="utf-8"))
    consumer["consumer"]["slot_offsets"][-1] = "0x28bc"
    p1a_path = tmp_path / "p1a.json"
    consumer_path = tmp_path / "consumer.json"
    p1a_path.write_text(json.dumps(p1a), encoding="utf-8")
    consumer_path.write_text(json.dumps(consumer), encoding="utf-8")
    try:
        module.build(p1a_path, consumer_path)
    except ValueError as exc:
        assert "slot map drift" in str(exc)
    else:
        raise AssertionError("slot-map drift must fail closed")
