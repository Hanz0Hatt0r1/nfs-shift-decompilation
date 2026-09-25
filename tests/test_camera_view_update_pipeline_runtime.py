from camera_view_update_pipeline_runtime import (
    CameraViewUpdateInputs,
    describe_camera_view_update,
)


def _ready(**overrides):
    base = CameraViewUpdateInputs(
        param1_delta=10,
        param2_delta=20,
        param4_low_byte_nonzero=False,
        param5_low_byte_nonzero=False,
        param6_low_byte_nonzero=False,
        runtime_ready=True,
        profile_present=True,
        service_present=True,
    )
    data = base.__dict__.copy()
    data.update(overrides)
    return CameraViewUpdateInputs(**data)


def test_runtime_or_profile_guard_falls_back_before_profile_work():
    result = describe_camera_view_update(_ready(runtime_ready=False))
    assert result["status"] == "fallback"
    assert result["actions"][0]["action"] == "clear +0x60"
    assert any(x["action"] == "FUN_0081b400" for x in result["actions"])


def test_param4_low_byte_selects_param2_as_effective_delta():
    result = describe_camera_view_update(_ready(param4_low_byte_nonzero=True))
    assert result["effective_delta"] == 20


def test_dirty_profile_forces_1000_delta_and_bdb0_then_clears_marker():
    result = describe_camera_view_update(_ready(camera_data_dirty=True))
    assert result["first_pass"] is True
    assert any(x.get("value") == 1000.0 for x in result["actions"] if x["action"] == "force delta")
    assert any(x["action"] == "FUN_0081bdb0" for x in result["actions"])


def test_missing_service_falls_back_after_initial_work():
    result = describe_camera_view_update(_ready(service_present=False))
    assert result["status"] == "service-fallback"
    assert any(x["action"] == "FUN_0081b400" for x in result["actions"])


def test_param6_updates_base_velocity_only_when_param4_low_byte_is_zero():
    result = describe_camera_view_update(
        _ready(param6_low_byte_nonzero=True, param4_low_byte_nonzero=False)
    )
    assert any(x["action"] == "FUN_004368e0 -> FUN_004422e0" for x in result["actions"])


def test_param4_nonzero_skips_base_velocity_adjustment():
    result = describe_camera_view_update(
        _ready(param6_low_byte_nonzero=True, param4_low_byte_nonzero=True)
    )
    assert not any(x["action"] == "FUN_004368e0 -> FUN_004422e0" for x in result["actions"])


def test_first_pass_uses_bc70_second_pass_uses_motion_filter_when_param4_zero():
    first = describe_camera_view_update(_ready(camera_data_dirty=True))
    second = describe_camera_view_update(_ready(camera_data_dirty=False))
    assert any(x["action"] == "FUN_0081bc70" for x in first["actions"])
    assert any(x["action"] == "FUN_0081b980" for x in second["actions"])


def test_cockpit_flag_changes_attachment_branch_and_orientation_inversion():
    result = describe_camera_view_update(
        _ready(cockpit_flag=True, profile_property_5_present=True)
    )
    assert any(x["action"] == "resolve profile attachment" for x in result["actions"])
    assert any(x["action"] == "invert cockpit orientation components" for x in result["actions"])


def test_profile_b4_mode_emits_camera_space_contribution_boundary():
    result = describe_camera_view_update(_ready(profile_b4_mode=1))
    assert any(x["action"] == "apply profile +0xb4 camera-space contribution" for x in result["actions"])


def test_param4_profile_cockpit_path_exposes_raw_collision_grid_stage():
    result = describe_camera_view_update(
        _ready(param4_low_byte_nonzero=True, profile_has_b8_behavior=True)
    )
    assert any(x["action"] == "collision-sample grid" for x in result["actions"])


def test_normal_update_ends_with_velocity_copy_and_matrix_finalization():
    result = describe_camera_view_update(_ready())
    assert result["actions"][-3]["action"] == "copy +0x2ec/+0x2f0/+0x2f4 -> +0x28/+0x2c/+0x30"
    assert result["actions"][-1]["action"] == "clear +0x60"
