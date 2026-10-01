from pathlib import Path


def test_phase634_fun_00757d2c_component_branch_matches_raw_disassembly():
    header = Path(
        "native_runtime/include/shift_constraint_relation_state_mutation.hpp"
    ).read_text(encoding="utf-8")
    source = Path(
        "native_runtime/src/constraint_relation_state_mutation.cpp"
    ).read_text(encoding="utf-8")
    checker = Path(
        "native_runtime/tests/constraint_relation_component_dispatch_check.cpp"
    ).read_text(encoding="utf-8")
    runtime = Path(
        "native_runtime/src/shift_runtime.cpp"
    ).read_text(encoding="utf-8")

    assert "ConstraintRelationComponentIdentity" in header
    assert "ConstraintRelationVehicleComponentMap" in header
    assert "apply_fun_00757d2c_component_relation_state_mutation" in header
    assert "apply_fun_00757d20_component_slot_relation_state_mutation" in header

    assert "if (secondary_body_index.has_value())" in source
    assert "ConstraintRelationStateMutationBranch::BarEndpoint" in source
    assert "ConstraintRelationStateMutationBranch::JointHingePair" in source
    assert "component_state_504_set = true" in source
    assert "component_state_540_set = true" in source
    assert "!rear_axle_body_index.has_value()" in source
    assert "component slot is outside 0..3" in source

    assert "FUN_00757d20" in checker
    assert "0x469736" in checker
    assert "FUN_00757d2c" in checker
    assert '\\"secondary_nonnull_selects_bar\\": true' in checker
    assert '\\"secondary_null_selects_joint_hinge\\": true' in checker
    assert (
        '\\"joint_hinge_pair_uses_primary_and_rear_axle\\": true'
        in checker
    )
    assert '\\"null_rear_axle_matches_nothing\\": true' in checker
    assert '\\"four_slot_wrapper_verified\\": true' in checker
    assert '\\"scheduler_integrated\\": false' in checker

    assert "apply_fun_00757d2c_component_relation_state_mutation" not in runtime
    assert (
        "apply_fun_00757d20_component_slot_relation_state_mutation"
        not in runtime
    )
