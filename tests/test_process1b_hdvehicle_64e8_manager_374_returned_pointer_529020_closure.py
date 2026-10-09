import json
from pathlib import Path

EVIDENCE = Path("evidence/hdvehicle_64e8_manager_374_returned_pointer_529020_closure.json")


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_producer_and_complete_consumer_surface_are_pinned():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8Manager374ReturnedPointer529020Closure/1"
    assert data["producer"]["function"] == "FUN_00529020"
    assert data["producer"]["materializer"] == "0x0052902b lea eax,[ecx+0x374]"
    surface = data["whole_image_consumer_surface"]
    assert surface["direct_control_transfer_count"] == 1
    assert surface["direct_jump_count"] == 0
    assert surface["absolute_function_pointer_occurrence_count"] == 0


def test_only_consumer_reads_pointee_without_pointer_escape():
    row = load_evidence()["only_consumer"]
    assert row["callsite"] == "0x0051f051"
    assert "0x0051f056 mov eax,[eax]" in row["post_call_machine"]
    assert row["returned_pointer_written_through"] is False
    assert row["returned_pointer_stored_or_forwarded"] is False
    assert row["only_pointee_value_is_read"] is True


def test_frontier_reduces_to_callee_forwarding_only():
    a = load_evidence()["adjudication"]
    assert a["returned_computed_pointer_consumer_surface_complete"] is True
    assert a["returned_pointer_path_can_write_manager_plus_0x374"] is False
    assert a["remaining_computed_runtime_path_count"] == 17
    assert a["callee_forwarding_surface_complete"] is False
    assert a["computed_address_manager_374_writer_surface_complete"] is False
    assert a["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert a["last_literal_0x004b86cf_rejected"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7
