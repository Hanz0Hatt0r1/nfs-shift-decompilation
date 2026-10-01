from pathlib import Path


def test_phase634_dispatches_named_vehicle_slots_without_assigning_timing():
    header = Path(
        "native_runtime/include/shift_constraint_relation_state_mutation.hpp"
    ).read_text(encoding="utf-8")
    source = Path(
        "native_runtime/src/constraint_relation_state_mutation.cpp"
    ).read_text(encoding="utf-8")
    checker = Path(
        "native_runtime/tests/constraint_relation_state_dispatch_check.cpp"
    ).read_text(encoding="utf-8")
    runtime = Path(
        "native_runtime/src/shift_runtime.cpp"
    ).read_text(encoding="utf-8")

    assert "kVehicleConstraintComponentCount = 4u" in header
    assert "kVehicleConstraintComponentBaseOffset = 0x400u" in header
    assert "kVehicleConstraintComponentStride = 0xA80u" in header
    assert "kVehicleConstraintWheelBodyFieldOffset = 0x420u" in header
    assert "kVehicleConstraintSpindleBodyFieldOffset = 0x424u" in header
    assert "kVehicleConstraintRearAxleBodyFieldOffset = 0x2E00u" in header
    assert "VehicleConstraintBodyIdentityMap" in header
    assert "dispatch_fun_00757d2c_vehicle_slot_relation_state_mutation" in header

    assert "body_map.wheel_body_indices[component_slot]" in source
    assert "body_map.spindle_body_indices[component_slot]" in source
    assert "body_map.rear_axle_body_index" in source
    assert "if (spindle_body_present)" in source
    assert "apply_fun_00757d2c_bar_endpoint_state_mutation" in source
    assert "apply_fun_00757d2c_pair_relation_state_mutation" in source
    assert "outside recovered 0..3 domain" in source

    assert "0x400u" in checker
    assert "0xE80u" in checker
    assert "0x1900u" in checker
    assert "0x2380u" in checker
    assert r'\"pair_branch_uses_wheel_rear_axle\": true' in checker
    assert r'\"bar_branch_uses_spindle\": true' in checker
    assert r'\"branch_from_spindle_presence\": true' in checker
    assert r'\"set_only_preserved_through_dispatch\": true' in checker
    assert r'\"scheduler_integrated\": false' in checker
    assert r'\"event_timing_assigned\": false' in checker
    assert "shift_constraint_relation_state_mutation.hpp" not in runtime
    assert (
        "dispatch_fun_00757d2c_vehicle_slot_relation_state_mutation"
        not in runtime
    )
