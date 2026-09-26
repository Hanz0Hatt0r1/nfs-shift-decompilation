from spline_storage_runtime import (
    SplineRecord,
    cubic_scalar_interpolation,
    interpolate_position,
    map_spline_index,
    normalize_spline_parameter,
    resize_spline_records,
    scalar_20_interpolation_contract,
    spline_property_registration,
    spline_record_defaults,
)


def test_record_defaults_match_exact_storage():
    result = spline_record_defaults()
    assert result["record_size"] == 0x24
    assert result["writes"]["+0x1c"] == 1.0
    assert result["writes"]["+0x20"] == 0.0


def test_registration_keeps_known_and_opaque_property_names():
    result = spline_property_registration()
    assert result["properties"][0]["name_symbol"] == "DAT_00afc8b8"
    assert result["properties"][1]["name"] == "MovementRate"
    assert result["properties"][2]["offset"] == 0x20


def test_index_mode_zero_clamps():
    assert map_spline_index(index=-1, count=4, mode=0)["mapped"] == 0
    assert map_spline_index(index=8, count=4, mode=0)["mapped"] == 3


def test_index_mode_one_wraps():
    assert map_spline_index(index=5, count=4, mode=1)["mapped"] == 1


def test_index_modes_two_and_three_use_mirror_remainder():
    assert map_spline_index(index=3, count=4, mode=2, mirror_decision=0)["mapped"] == 3
    assert map_spline_index(index=3, count=4, mode=3, mirror_decision=1)["mapped"] == 1


def test_scalar_interpolation_has_minimum_point_one():
    records = [SplineRecord(scalar_1c=0.0) for _ in range(4)]
    result = cubic_scalar_interpolation(records, index=1, t=0.5, mode=0)
    assert result["value"] == 0.1


def test_scalar_interpolation_applies_sixteen_power_edge_fade():
    records = [SplineRecord(scalar_1c=1.0) for _ in range(4)]
    result = cubic_scalar_interpolation(records, index=0, t=0.0, mode=0)
    assert result["edge_factor"] == 0.0
    assert result["value"] == 0.1


def test_scalar_20_nonpositive_values_use_fallback():
    records = [
        SplineRecord(scalar_20=-1),
        SplineRecord(scalar_20=0),
        SplineRecord(scalar_20=2),
        SplineRecord(scalar_20=3),
    ]
    result = scalar_20_interpolation_contract(
        records, index=1, t=0.5, mode=0, fallback=4
    )
    assert result["effective_values"] == [4.0, 4.0, 2.0, 3.0]


def test_position_interpolation_returns_three_components():
    records = [
        SplineRecord(position=(float(i), float(i + 1), float(i + 2)))
        for i in range(4)
    ]
    result = interpolate_position(records, index=1, t=0.0, mode=0)
    assert result["value"] == [1.0, 2.0, 3.0]


def test_parameter_normalization_carries_integer_segment():
    result = normalize_spline_parameter(
        segment_index=2,
        parameter=1.25,
        count=4,
        mode=0,
    )
    assert result["segment_index"] == 3.0
    assert result["parameter"] == 0.25


def test_resize_preserves_exact_byte_formula():
    result = resize_spline_records([], 3)
    assert result["actions"][2]["bytes"] == 4 + 3 * 0x24
