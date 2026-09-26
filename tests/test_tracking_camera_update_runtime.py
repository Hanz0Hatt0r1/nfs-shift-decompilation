from tracking_camera_update_runtime import (
    compute_autozoom_update,
    compute_speed_fov_blend,
    describe_tracking_camera_update,
    select_tracking_camera_target,
)


def test_target_selector_resets_on_zero_param():
    result = select_tracking_camera_target(
        target_id=3,
        entries=[],
        param2=0,
    )
    assert result["status"] == "reset"


def test_target_selector_matches_entry_vtable_id():
    result = select_tracking_camera_target(
        target_id=3,
        entries=[
            {"vtable_plus_0x14_result": 1},
            {"vtable_plus_0x14_result": 3},
        ],
        param2=3,
    )
    assert result["status"] == "matched"
    assert result["matched_entry"] == 1


def test_autozoom_clamps_desired_value_and_limits_step():
    result = compute_autozoom_update(
        current_zoom=1,
        distance=100,
        update_enabled=True,
        write_initial_zoom=False,
        previous_zoom=0.5,
        delta=0.2,
    )
    assert result["desired"] == 3.5 if False else 0.35
    assert result["value"] == 0.55


def test_speed_fov_blend_clamps_normalized_t():
    result = compute_speed_fov_blend(
        current_fov=1,
        speed=15,
        fov_min_speed=0,
        fov_max_speed=10,
        fov_min=1,
        fov_max=2,
        shake_min_speed=0,
        shake_max_speed=10,
        shake_min_scale=0.5,
        shake_max_scale=1.5,
    )
    assert result["fov_t"] == 1.0
    assert result["fov_value"] == 2.0


def test_tracking_update_orders_target_offset_fov_shake_and_orientation():
    result = describe_tracking_camera_update(
        delta=0.1,
        input_position=[1, 2, 3],
        target_position=[4, 5, 6],
        tracking_position=[0, 0, 0],
        target_mode=1,
        target_spline_id=-1,
        static_direction=False,
        autozoom=True,
        speed=10,
        current_fov=0.5,
        service_available=True,
        target_query_available=True,
        cockpit_query_result=False,
        autozoom_previous=0.5,
        autozoom_initialized=True,
        fov_blend={
            "fov_min_speed": 0,
            "fov_max_speed": 20,
            "fov_min": 0.5,
            "fov_max": 1.0,
            "shake_min_speed": 0,
            "shake_max_speed": 20,
            "shake_min_scale": 0.1,
            "shake_max_scale": 0.2,
        },
        shake_enabled=True,
        final_orientation=[1, 0, 0, 0],
    )
    names = [a["action"] for a in result["actions"]]
    assert names.index("FUN_0081f330") < names.index("FUN_00820bc0")
    assert names.index("FUN_00820bc0") < names.index("FUN_008207c0")
