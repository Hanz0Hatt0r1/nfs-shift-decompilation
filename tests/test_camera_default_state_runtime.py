import pytest

from camera_default_state_runtime import camera_default_state


def test_static_camera_template_preserves_exact_float_defaults():
    state = camera_default_state("static")
    fields = state["fields"]
    assert fields["FOV"]["bits_hex"] == "0x3f490fdb"
    assert fields["NearZ"]["value"] == 1.0
    assert fields["FarZ"]["value"] == pytest.approx(750.0)
    assert fields["Type"] == 1
    assert fields["Target"] == 6
    assert fields["LookAt"] == 6


def test_static_camera_zero_vector_and_quaternion_defaults_are_not_normalized():
    fields = camera_default_state("static")["fields"]
    assert fields["Pos"] == [0.0, 0.0, 0.0]
    assert fields["QuatOri"] == [0.0, 0.0, 0.0, 0.0]


def test_static_camera_alias_fields_keep_the_same_storage_offsets_and_defaults():
    state = camera_default_state("static")
    assert state["offsets"]["ShakeFrequencyMin"] == state["offsets"]["ShakeScreenVelocityMin"]
    assert state["fields"]["ShakeFrequencyMin"]["bits_hex"] == state["fields"]["ShakeScreenVelocityMin"]["bits_hex"]
    assert state["fields"]["ShakeFrequency"]["value"] == state["fields"]["ShakeScreenVelocity"]["value"]


def test_tracking_template_inherits_static_defaults_and_adds_tracking_defaults():
    fields = camera_default_state("tracking")["fields"]
    assert fields["FOV"]["bits_hex"] == "0x3f490fdb"
    assert fields["MovementRate"]["value"] == 0.0
    assert fields["SplineID"] == -1
    assert fields["TargetSplineID"] == -1
    assert fields["bAutoZoom"] is False
    assert fields["TrackingLagSmoothening"]["value"] == pytest.approx(0.8)
    assert fields["TrackingErrorFrequency"]["value"] == pytest.approx(2.0)
    assert fields["TrackingErrorCorrectionSpeed"]["value"] == pytest.approx(1.0)
    assert fields["SplinesRatio"]["value"] == pytest.approx(1.0)


def test_invalid_camera_default_kind_is_rejected():
    with pytest.raises(ValueError):
        camera_default_state("area")
