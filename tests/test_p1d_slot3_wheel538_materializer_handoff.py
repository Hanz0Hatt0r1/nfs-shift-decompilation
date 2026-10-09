import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "build_p1d_slot3_wheel538_handoff.py"
P1A = ROOT / "evidence" / "p1a_p13a_slot01_wheel538_forwarding_frontier.json"
OVERLAP = ROOT / "evidence" / "p1a_p13a_slot01_overlap_store_closure.json"
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
    assert module.build(P1A, OVERLAP, CONSUMER) == json.loads(PINNED.read_text(encoding="utf-8"))


def test_slot3_literal_local_surfaces_close_without_promoting_writer():
    payload = json.loads(PINNED.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.P1D.P13DSlot3Wheel538MaterializerHandoff/1"
    slot3 = payload["slot3"]
    assert slot3["wheel_runtime_receiver_absolute"] == "HDVehicle+0x2380"
    assert slot3["absolute_target"] == "HDVehicle+0x28b8"
    assert slot3["absolute_byte_range"] == ["HDVehicle+0x28b8", "HDVehicle+0x28c0"]

    surface = payload["exact_local_surface"]
    assert surface["whole_image_exact_0x538_scalar_use_count"] == 43
    assert surface["positive_address_materializer_count"] == 4
    assert surface["all_positive_materializers_rejected_as_selected_slot3_f64_producers"] is True
    assert surface["direct_positive_qword_store_slot3_destination"] == "HDVehicle+0x2c00"
    assert surface["direct_positive_qword_store_matches_slot3_target"] is False

    overlap = payload["exact_literal_overlap_store_surface"]
    assert overlap["overlapping_store_count"] == 25
    assert overlap["partial_store_count"] == 24
    assert overlap["qword_or_wider_store_count"] == 1
    assert overlap["function_count"] == 13
    assert overlap["unowned_instruction_count"] == 0
    assert overlap["all_partial_store_receivers_rejected"] is True
    assert overlap["known_qword_store_receiver_rejected"] is True
    assert overlap["selected_slot3_exact_literal_overlap_writer_found"] is False

    adj = payload["adjudication"]
    assert adj["slot3_exact_local_0x538_materializer_callee_subset_complete"] is True
    assert adj["slot3_exact_literal_overlap_store_surface_complete"] is True
    assert adj["slot3_computed_address_store_surface_complete"] is False
    assert adj["slot3_escaped_alias_store_surface_complete"] is False
    assert adj["slot3_overlapping_bulk_copy_surface_complete"] is False
    assert adj["slot3_writer_provenance_proven"] is False
    assert adj["p1_3d_complete"] is False
    assert adj["external_provider_count"] == 7


def test_builder_rejects_consumer_slot_drift(tmp_path):
    module = load_module()
    p1a = json.loads(P1A.read_text(encoding="utf-8"))
    overlap = json.loads(OVERLAP.read_text(encoding="utf-8"))
    consumer = json.loads(CONSUMER.read_text(encoding="utf-8"))
    consumer["consumer"]["slot_offsets"][-1] = "0x28bc"
    p1a_path = tmp_path / "p1a.json"
    overlap_path = tmp_path / "overlap.json"
    consumer_path = tmp_path / "consumer.json"
    p1a_path.write_text(json.dumps(p1a), encoding="utf-8")
    overlap_path.write_text(json.dumps(overlap), encoding="utf-8")
    consumer_path.write_text(json.dumps(consumer), encoding="utf-8")
    try:
        module.build(p1a_path, overlap_path, consumer_path)
    except ValueError as exc:
        assert "slot map drift" in str(exc)
    else:
        raise AssertionError("slot-map drift must fail closed")


def test_builder_rejects_overlap_count_drift(tmp_path):
    module = load_module()
    overlap = json.loads(OVERLAP.read_text(encoding="utf-8"))
    overlap["inventory"]["overlapping_store_count"] = 24
    overlap_path = tmp_path / "overlap.json"
    overlap_path.write_text(json.dumps(overlap), encoding="utf-8")
    try:
        module.build(P1A, overlap_path, CONSUMER)
    except ValueError as exc:
        assert "overlapping_store_count drift" in str(exc)
    else:
        raise AssertionError("overlap inventory drift must fail closed")
