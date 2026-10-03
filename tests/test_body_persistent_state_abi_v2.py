from body_persistent_state_abi_runtime import (
    FORMAT as V1_FORMAT,
    native_pose_handoff as v1_native_pose_handoff,
)
from body_persistent_state_abi_v2 import (
    BODY_ARRAY_LOOP,
    BODY_INTEGRATOR,
    BODY_LANES,
    FORMAT,
    HALF_STEP_ORCHESTRATOR,
    PERSISTENT_GRAPH,
    build_contract,
    native_pose_handoff,
    unresolved_persistent_lanes,
    writers_for_offset,
)


def test_v2_closes_the_four_previously_unresolved_persistent_lanes():
    contract = build_contract()
    assert contract["format"] == FORMAT == "SHIFT.BodyPersistentStateABI/2"
    assert contract["status"] == "persistent-body-writer-bridge-closed"
    assert unresolved_persistent_lanes() == ()

    for lane in ("origin", "cross_vector", "motion_triplet", "basis"):
        assert BODY_LANES[lane]["writer_status"] == "proven-persistent-frame-integration"
        assert BODY_INTEGRATOR in BODY_LANES[lane]["writers"]


def test_integrator_writes_exact_persistent_targets_but_reads_accumulators():
    assert BODY_INTEGRATOR in writers_for_offset(0x00)
    assert BODY_INTEGRATOR in writers_for_offset(0x18)
    assert BODY_INTEGRATOR in writers_for_offset(0x30)
    assert BODY_INTEGRATOR in writers_for_offset(0x78)
    assert BODY_INTEGRATOR in writers_for_offset(0xD4)

    # The integrator consumes, but does not overwrite, the two solver accumulator lanes.
    assert BODY_INTEGRATOR not in writers_for_offset(0x48)
    assert BODY_INTEGRATOR not in writers_for_offset(0x60)
    assert BODY_INTEGRATOR in BODY_LANES["accumulator_a"]["readers"]
    assert BODY_INTEGRATOR in BODY_LANES["accumulator_b"]["readers"]


def test_persistent_graph_is_continuous_from_post_solve_to_pose():
    proven = {(edge["from"], edge["to"]): edge["status"] for edge in PERSISTENT_GRAPH}
    assert proven[(
        "FUN_007b4110 post-solve feedback",
        "FUN_007b2270 BODY-array loop -> FUN_007bab70",
    )] == "proven"
    assert proven[(
        "accumulator_b +0x60..+0x70",
        "motion_triplet +0x78..+0x88",
    )] == "proven"
    assert proven[(
        "motion_triplet +0x78..+0x88",
        "origin +0x00..+0x10",
    )] == "proven"
    assert proven[(
        "accumulator_a +0x48..+0x58",
        "prepared_vector +0x30..+0x40",
    )] == "proven"
    assert proven[(
        "prepared_vector +0x30..+0x40",
        "cross_vector +0x18..+0x28",
    )] == "proven"
    assert proven[(
        "cross_vector +0x18..+0x28",
        "basis +0xd4..+0xf4",
    )] == "proven"


def test_native_pose_handoff_is_now_ready_but_keeps_outer_unknowns_explicit():
    handoff = native_pose_handoff()
    assert handoff["ready"] is True
    assert handoff["body_array_loop"] == BODY_ARRAY_LOOP == "FUN_007b2270"
    assert handoff["body_integrator"] == BODY_INTEGRATOR == "FUN_007bab70"
    assert handoff["half_step_orchestrator"] == HALF_STEP_ORCHESTRATOR == "FUN_00765470"
    assert handoff["body_stride"] == 0x170
    assert handoff["half_step_scale"] == 0.5
    assert "rendered-frame cadence" in handoff["scope"]
    assert handoff["remaining_unknowns"]


def test_v1_remains_historical_fail_closed_contract():
    # Existing consumers of /1 retain the exact evidence boundary they were written for.
    assert V1_FORMAT == "SHIFT.BodyPersistentStateABI/1"
    assert v1_native_pose_handoff()["ready"] is False
