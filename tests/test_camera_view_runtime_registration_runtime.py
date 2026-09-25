from camera_view_runtime_registration_runtime import (
    camera_view_property_registration,
    wrap_angle_from_runtime,
)


def test_positive_angle_uses_runtime_seed_minus_pi():
    result = wrap_angle_from_runtime(1.0, 4.0)
    assert result["result"] == 4.0 - 3.1415927
    assert result["branch"] == "positive"


def test_zero_and_negative_angles_use_negated_seed_minus_pi():
    assert wrap_angle_from_runtime(0.0, 4.0)["result"] == -(4.0 - 3.1415927)
    assert wrap_angle_from_runtime(-1.0, 4.0)["result"] == -(4.0 - 3.1415927)


def test_nan_takes_non_positive_branch_like_source():
    result = wrap_angle_from_runtime(float("nan"), 4.0)
    assert result["branch"] == "non-positive-or-nan"


def test_property_registration_matches_exact_offsets_and_type_ids():
    result = camera_view_property_registration()
    props = {row["name"]: row for row in result["properties"]}
    assert props["FreeLookOri"]["storage_offset"] == 0x84
    assert props["FreeLookOri"]["property_type_id"] == 0x10
    assert props["PosOri"]["storage_offset"] == 0x90
    assert props["AttachedVehicleIndex"]["storage_offset"] == 0xC0
    assert props["AttachedVehicleIndex"]["property_type_id"] == 3


def test_all_registrations_use_flags_two_and_shared_default():
    result = camera_view_property_registration()
    assert {row["registration_flags"] for row in result["properties"]} == {2}
    assert {row["default_value"] for row in result["properties"]} == {"DAT_00aa9b60"}
