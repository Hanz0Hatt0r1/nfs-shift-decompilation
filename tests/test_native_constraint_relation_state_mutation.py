from pathlib import Path


def test_phase633_ports_fun_00757d2c_relation_state_mutation_without_scheduler():
    header = Path(
        "native_runtime/include/shift_constraint_relation_state_mutation.hpp"
    ).read_text(encoding="utf-8")
    source = Path(
        "native_runtime/src/constraint_relation_state_mutation.cpp"
    ).read_text(encoding="utf-8")
    checker = Path(
        "native_runtime/tests/constraint_relation_state_mutation_check.cpp"
    ).read_text(encoding="utf-8")
    runtime = Path(
        "native_runtime/src/shift_runtime.cpp"
    ).read_text(encoding="utf-8")

    assert "apply_fun_00757d2c_pair_relation_state_mutation" in header
    assert "apply_fun_00757d2c_bar_endpoint_state_mutation" in header
    assert "ConstraintRelationStateMutationResult" in header

    assert "unordered_pair_matches" in source
    assert "relation.positive.body_index == body_index" in source
    assert "relation.negative.body_index == body_index" in source
    assert "if (bit == 0u)" in source
    assert "bit = 1u" in source
    assert "bit = 0u" not in source
    assert "cardinality mismatch" in source
    assert "endpoint BODY index is outside relation domain" in source

    assert "FUN_00757d2c" in checker
    assert '\\"pair_branch_joint_hinge\\": true' in checker
    assert '\\"pair_match_unordered\\": true' in checker
    assert '\\"bar_branch_endpoint_match\\": true' in checker
    assert '\\"mutation_set_only\\": true' in checker
    assert '\\"scheduler_integrated\\": false' in checker
    assert '\\"event_timing_assigned\\": false' in checker

    assert "shift_constraint_relation_state_mutation.hpp" not in runtime
    assert "apply_fun_00757d2c_pair_relation_state_mutation" not in runtime
    assert "apply_fun_00757d2c_bar_endpoint_state_mutation" not in runtime
