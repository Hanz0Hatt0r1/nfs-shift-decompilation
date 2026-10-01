from pathlib import Path


def test_phase635_closes_fun_0076ed60_initialization_callsite_without_fixed_step_wiring():
    header = Path(
        "native_runtime/include/shift_constraint_relation_state_mutation.hpp"
    ).read_text(encoding="utf-8")
    source = Path(
        "native_runtime/src/constraint_relation_state_mutation.cpp"
    ).read_text(encoding="utf-8")
    checker = Path(
        "native_runtime/tests/constraint_relation_state_initialization_check.cpp"
    ).read_text(encoding="utf-8")
    runtime = Path(
        "native_runtime/src/shift_runtime.cpp"
    ).read_text(encoding="utf-8")

    assert "kVehicleConstraintSetupConfigComponentBaseOffset = 0x88u" in header
    assert "kVehicleConstraintSetupConfigComponentStride = 0xA0u" in header
    assert "kVehicleConstraintSetupMutationFlagOffset = 0x98u" in header
    assert "vehicle_constraint_setup_mutation_flag_source_offset" in header
    assert "VehicleConstraintRelationInitializationState" in header
    assert "apply_fun_0076ed60_vehicle_relation_state_initialization" in header

    assert "if (!initialization.mutation_enabled[slot])" in source
    assert "result.dispatched_slot_order[result.dispatched_slot_count] = slot" in source
    assert "initialization.spindle_body_present[slot]" in source
    assert "dispatch_fun_00757d2c_vehicle_slot_relation_state_mutation" in source

    assert "0x120u" in checker
    assert "0x1C0u" in checker
    assert "0x260u" in checker
    assert "0x300u" in checker
    assert r'\"initialization_provenance_closed\": true' in checker
    assert r'\"fixed_step_scheduler_event\": false' in checker
    assert r'\"persistent_runtime_state_integrated\": false' in checker

    assert "apply_fun_0076ed60_vehicle_relation_state_initialization" not in runtime
