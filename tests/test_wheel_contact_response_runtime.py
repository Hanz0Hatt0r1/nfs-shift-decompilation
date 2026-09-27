import math

import pytest

from wheel_contact_response_runtime import (
    CurveParameters,
    ResponseTable,
    build_contract,
    build_quadratic_response,
    clamp_query_scalar,
    directional_factor,
    evaluate_contact_response,
    pack_curve_parameters,
)


def test_query_scalar_clamp_matches_caller_boundary():
    assert clamp_query_scalar(-2.0, 4.0) == 0.0
    assert clamp_query_scalar(2.0, 4.0) == 2.0
    assert clamp_query_scalar(9.0, 4.0) == 4.0


def test_curve_packer_matches_fun_00752f10():
    packed = pack_curve_parameters(0.25, 2.0, 1.5)
    assert packed.amplitude == pytest.approx(0.25)
    assert packed.double_width == pytest.approx(4.0)
    assert packed.inverse_width_pi == pytest.approx(math.pi / 2.0)
    assert packed.half_offset == pytest.approx(0.25)


def test_directional_factor_matches_cosine_branch_and_fourth_power_ratio():
    curve = CurveParameters(0.25, 4.0, math.pi / 2.0, 0.25)
    value = directional_factor(curve, 1.0, 1.0)
    angle = math.atan2(1.0, -1.0)
    angular = 1.0 + (1.0 - math.cos(angle * math.pi / 2.0)) * 0.25
    ratio4 = 0.5 ** 4
    expected = angular * (1.0 - (1.0 - ratio4) * 0.25)
    assert value == pytest.approx(expected)


def test_directional_factor_zero_velocity_returns_angular_term():
    curve = CurveParameters(0.9, 4.0, math.pi / 2.0, 0.25)
    angle = math.atan2(0.0, -0.0)
    expected = 1.0 + (1.0 - math.cos(angle * math.pi / 2.0)) * 0.25
    assert directional_factor(curve, 0.0, 0.0) == pytest.approx(expected)


def test_quadratic_response_selects_sign_vectors_and_aux_sign():
    table = ResponseTable(
        negative_or_zero=((1, 2, 3), (4, 5, 6), (7, 8, 9)),
        positive=((10, 20, 30), (40, 50, 60), (70, 80, 90)),
        component_scales=(1, 2, 3),
    )
    vector, aux = build_quadratic_response(table, (-2.0, 3.0, 0.0))
    assert vector == pytest.approx((364.0, 458.0, 552.0))
    assert aux == pytest.approx((4.0, -18.0, 0.0))


def test_composed_response_preserves_gain_and_quadratic_outputs():
    curve = pack_curve_parameters(0.2, 2.0, 1.2)
    table = ResponseTable(
        negative_or_zero=((1, 0, 0), (0, 2, 0), (0, 0, 3)),
        positive=((4, 0, 0), (0, 5, 0), (0, 0, 6)),
        component_scales=(1, 1, 1),
    )
    result = evaluate_contact_response(
        query_scalar=9.0,
        query_limit=4.0,
        depth_slope=2.0,
        base_offset=1.0,
        directional_curve=curve,
        response_table=table,
        tangent_x=-1.0,
        tangent_z=3.0,
        response_input=(-1.0, 2.0, 3.0),
    )
    assert result.clamped_query_scalar == pytest.approx(4.0)
    assert result.response_gain == pytest.approx((2 * 4 + 1) * result.directional_factor)
    assert result.response_vector == pytest.approx((1.0, 20.0, 54.0))
    assert result.auxiliary_response == pytest.approx((1.0, -4.0, -9.0))


def test_contract_contains_only_observable_meanings():
    contract = build_contract()
    assert contract["consumer"] == "FUN_00766510"
    assert contract["directional_factor"]["angle"] == "atan2(tangent_x, -tangent_z)"
    assert contract["directional_factor"]["planar_ratio"] == "(tangent_z^2 / (tangent_x^2 + tangent_z^2))^4"
    assert contract["response_builder"]["negative_or_zero_vector_offsets_by_component"] == ["0x00", "0x48", "0x78"]
    assert contract["response_builder"]["positive_vector_offsets_by_component"] == ["0x18", "0x30", "0x60"]
    assert contract["state"]["query_scalar"] == "+0x38e0"
