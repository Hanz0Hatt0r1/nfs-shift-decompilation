import pytest

from camera_activation_runtime import CameraActivationState, activate_camera


def test_param2_minus_one_uses_param1_as_effective_group():
    result = activate_camera(
        CameraActivationState(),
        param_1=3,
        param_2=-1,
        param_3=7,
        camera_found=True,
        is_tracking_camera=False,
    )
    assert result["effective_group"] == 3
    assert result["selected_camera_id"] == 7
    assert result["activation_mode"] == 3
    assert result["changed"] is True


def test_tracking_camera_uses_activation_mode_two():
    result = activate_camera(
        CameraActivationState(active_group=1, active_camera_id=2),
        param_1=4,
        param_2=5,
        param_3=9,
        camera_found=True,
        is_tracking_camera=True,
    )
    assert result["effective_group"] == 5
    assert result["activation_mode"] == 2
    assert result["deactivated_old_group"] == 1


def test_negative_camera_id_is_ignored():
    result = activate_camera(
        CameraActivationState(active_group=1, active_camera_id=2),
        param_1=4,
        param_2=5,
        param_3=-1,
        camera_found=True,
        is_tracking_camera=True,
    )
    assert result["status"] == "ignored-negative-camera-id"
    assert result["changed"] is False
    assert result["selected_camera_id"] == 2


def test_already_active_camera_is_noop():
    result = activate_camera(
        CameraActivationState(active_group=3, active_camera_id=9),
        param_1=4,
        param_2=5,
        param_3=9,
        camera_found=True,
        is_tracking_camera=False,
    )
    assert result["status"] == "no-op-already-active"
    assert result["changed"] is False


def test_missing_camera_is_noop_after_lookup_failure():
    result = activate_camera(
        CameraActivationState(active_group=2, active_camera_id=4),
        param_1=3,
        param_2=3,
        param_3=10,
        camera_found=False,
        is_tracking_camera=True,
    )
    assert result["status"] == "ignored-unresolved-camera"
    assert result["changed"] is False
