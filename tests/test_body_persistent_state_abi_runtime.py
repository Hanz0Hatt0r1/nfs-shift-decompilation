from body_persistent_state_abi_runtime import (
    BODY_LANES,
    FORMAT,
    PERSISTENT_GRAPH,
    VEHICLE_TOPOLOGY,
    build_contract,
    native_pose_handoff,
    unresolved_persistent_lanes,
    writers_for_offset,
)
from wheel_kinematics_runtime import WHEEL_RUNTIME_BASE, WHEEL_RUNTIME_STRIDE, WHEEL_STATE_BASE
from wheel_longitudinal_velocity_runtime import (
    PHYSICS_POSE_OFFSET,
    PHYSICS_VELOCITY_OFFSET,
    Vec3,
    apply_longitudinal_subtraction,
)


def test_contract_freezes_neutral_body_lane_offsets_without_inventing_pose_writer():
    contract = build_contract()
    assert contract["format"] == FORMAT == "SHIFT.BodyPersistentStateABI/1"
    assert BODY_LANES["origin"]["offsets"] == (0x00, 0x08, 0x10)
    assert BODY_LANES["cross_vector"]["offsets"] == (0x18, 0x20, 0x28)
    assert BODY_LANES["accumulator_a"]["offsets"] == (0x48, 0x50, 0x58)
    assert BODY_LANES["accumulator_b"]["offsets"] == (0x60, 0x68, 0x70)
    assert BODY_LANES["motion_triplet"]["offsets"] == (0x78, 0x80, 0x88)
    assert BODY_LANES["basis"]["offsets"][0] == 0xD4
    assert contract["status"] == "writer-frontier-proven-pose-bridge-unresolved"


def test_unresolved_lanes_are_exactly_the_persistent_pose_motion_frontier():
    assert unresolved_persistent_lanes() == (
        "origin",
        "cross_vector",
        "motion_triplet",
        "basis",
    )
    assert writers_for_offset(0x78) == ()
    assert writers_for_offset(0xD4) == ()
    assert writers_for_offset(0x00) == ()


def test_proven_accumulator_writers_do_not_alias_motion_triplet_writer():
    angular_writers = set(writers_for_offset(0x48))
    linear_writers = set(writers_for_offset(0x60))
    assert "FUN_00755f80" in angular_writers
    assert "FUN_007ba9e0" in angular_writers
    assert "FUN_007b4110" in angular_writers
    assert "FUN_007ba9e0" in linear_writers
    assert "FUN_007b4110" in linear_writers
    assert "FUN_00755f80" not in linear_writers
    assert writers_for_offset(0x78) == ()


def test_wheel_writer_contract_cross_checks_existing_python_oracle():
    assert PHYSICS_VELOCITY_OFFSET == 0x48
    assert PHYSICS_POSE_OFFSET == 0xD4
    assert apply_longitudinal_subtraction(
        shared_velocity=Vec3(8.0, -2.0, 5.0),
        reconstructed_world_velocity=Vec3(1.5, 3.0, -4.0),
    ) == Vec3(6.5, -5.0, 9.0)


def test_vehicle_component_and_body_pointer_topology_is_exact():
    slots = VEHICLE_TOPOLOGY["component_slots"]
    assert slots["count"] == 4
    assert slots["base"] == WHEEL_RUNTIME_BASE == 0x400
    assert slots["stride"] == WHEEL_RUNTIME_STRIDE == 0xA80
    assert slots["component_offsets"] == (0x400, 0xE80, 0x1900, 0x2380)
    assert slots["wheel_body_pointer_absolute"] == (0x820, 0x12A0, 0x1D20, 0x27A0)
    assert slots["spindle_body_pointer_absolute"] == (0x824, 0x12A4, 0x1D24, 0x27A4)
    assert VEHICLE_TOPOLOGY["rear_axle_body_pointer"] == 0x2E00
    assert VEHICLE_TOPOLOGY["wheel_state_slots"]["base"] == WHEEL_STATE_BASE == 0x848


def test_contact_record_arrays_remain_separate_from_body_pose_contract():
    aux = VEHICLE_TOPOLOGY["aux_contact_records"]
    factor = VEHICLE_TOPOLOGY["contact_factor_records"]
    assert aux == {
        "count": 2,
        "offsets": (0x37D8, 0x3858),
        "caller": "FUN_00766510",
        "callee": "FUN_00758fc0",
    }
    assert factor["count"] == 4
    assert factor["stride"] == 0x150
    assert factor["previous_base"] == 0xA70
    assert factor["factor_base"] == 0xA78


def test_persistent_graph_has_two_explicit_unresolved_bridges_after_post_solve():
    unresolved_edges = [
        edge for edge in PERSISTENT_GRAPH if edge["status"] == "unresolved"
    ]
    assert any(edge["from"] == "post-solve BODY accumulators" for edge in unresolved_edges)
    assert any(edge["from"] == "BODY +0x18/+0x78 motion-side lanes" for edge in unresolved_edges)
    assert any(
        edge["from"] == "solve" and edge["to"] == "FUN_007b4110 post-solve BODY accumulators"
        and edge["status"] == "proven"
        for edge in PERSISTENT_GRAPH
    )


def test_native_pose_handoff_is_fail_closed_and_prioritizes_outer_update_frontier():
    handoff = native_pose_handoff()
    assert handoff["ready"] is False
    assert handoff["required_writer_targets"] == (
        "origin",
        "cross_vector",
        "motion_triplet",
        "basis",
    )
    addresses = handoff["priority_function_addresses"]
    assert 0x00770E80 in addresses
    assert 0x0076D100 in addresses
    assert 0x007B4110 in addresses
    assert 0x007675F0 in addresses
