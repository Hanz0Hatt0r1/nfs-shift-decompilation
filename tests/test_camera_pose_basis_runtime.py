from camera_pose_basis_runtime import (
    build_pose_basis,
    describe_external_source_state,
    resolve_profile_scale_or_default,
)


def test_pose_basis_has_three_normalized_stages():
    result = build_pose_basis([1, 0, 0], [0, 1, 0])
    assert result["stages"]["first"]["vector"] == (1.0, 0.0, 0.0)
    assert result["stages"]["second"]["vector"] == (0.0, 0.0, 1.0)
    assert result["stages"]["third"]["vector"] == (0.0, -1.0, 0.0)


def test_pose_basis_preserves_source_order_nine_float_output():
    result = build_pose_basis([1, 0, 0], [0, 1, 0])
    assert len(result["basis_3x3_source_order"]) == 9
    assert result["actions"][-1]["action"] == "FUN_00449930"


def test_external_source_disabled_id_keeps_state_setup_but_marks_disabled():
    result = describe_external_source_state(
        external_id=0,
        opaque_position_output=[1, 2, 3],
        opaque_orientation_scalar=7,
        helper_9024d0_result=3,
        global_angle_offset=1,
        source_vtable_fov_result=2,
    )
    assert result["status"] == "disabled"
    assert result["writes"]["+0x4c"] == 0
    assert result["writes"]["+0x50"] == 0


def test_external_source_active_preserves_opaque_helper_results():
    result = describe_external_source_state(
        external_id=4,
        opaque_position_output=[1, 2, 3],
        opaque_orientation_scalar=7.0,
        helper_9024d0_result=4.0,
        global_angle_offset=1.5,
        source_vtable_fov_result=2.5,
    )
    assert result["status"] == "active"
    assert result["writes"]["+0x1c"] == 2.5
    assert result["writes"]["+0x20"] == 7.0
    assert result["writes"]["+0x34"] == 2.5


def test_profile_scale_returns_profile_value_or_one():
    assert resolve_profile_scale_or_default(True, 3.0)["value"] == 3.0
    assert resolve_profile_scale_or_default(False, 3.0)["value"] == 1.0
