import math

import pytest

from contact_response_orchestration_runtime import (
    AUX_RECORD_OFFSETS,
    AuxRecordOracleInput,
    build_contract,
    execute_fun_00766510_partial_contact_chain,
)
from wheel_contact_response_runtime import CurveParameters, ResponseTable


def _table():
    return ResponseTable(
        negative_or_zero=(
            (1.0, 0.0, 0.0),
            (0.0, 2.0, 0.0),
            (0.0, 0.0, 3.0),
        ),
        positive=(
            (4.0, 0.0, 0.0),
            (0.0, 5.0, 0.0),
            (0.0, 0.0, 6.0),
        ),
        component_scales=(1.0, 1.0, 1.0),
    )


def _record(active=True):
    return AuxRecordOracleInput(
        active=active,
        transformed_record_point=(5.0, 4.0, 1.0),
        local_point=(5.0, 4.0, 1.0),
        directional_multiplier=1.0,
        gain=2.0,
        scale=2.0,
    )


def _run(post_primary):
    return execute_fun_00766510_partial_contact_chain(
        original_world_y=10.0,
        returned_contact_height=7.0,
        fallback_and_query_limit=4.0,
        depth_slope=2.0,
        base_offset=1.0,
        directional_curve=CurveParameters(0.0, 0.0, 0.0, 0.0),
        response_table=_table(),
        tangent_x=0.0,
        tangent_z=1.0,
        response_input=(-1.0, 2.0, 3.0),
        body_accumulator_after_primary_application=post_primary,
        aux_reference_point=(2.0, 3.0, 5.0),
        aux_records=(_record(), _record()),
    )


def test_contract_freezes_explicit_primary_application_barrier():
    contract = build_contract()
    assert contract["function"] == "FUN_00766510"
    assert AUX_RECORD_OFFSETS == (0x37D8, 0x3858)
    assert contract["auxiliary"]["count"] == 2
    assert contract["primary_application"]["missing_state"] == "reject"
    assert contract["runtime_scheduling"] == "unproven"
    assert contract["full_FUN_00766510_ported"] is False


def test_exact_response_then_barrier_then_two_auxiliary_records():
    result = _run({"angular": (1.0, 2.0, 3.0), "linear": (4.0, 5.0, 6.0)})

    assert result.query_scalar == 3.0
    assert result.response.clamped_query_scalar == 3.0
    assert result.response.directional_factor == 1.0
    assert result.response.response_gain == 7.0
    assert result.response.response_vector == (1.0, 20.0, 54.0)
    assert result.response.auxiliary_response == (1.0, -4.0, -9.0)

    assert result.body_accumulator_at_primary_barrier == {
        "angular": (1.0, 2.0, 3.0),
        "linear": (4.0, 5.0, 6.0),
    }
    assert result.auxiliary_order == (0, 1)
    assert result.auxiliary_applied_count == 2
    assert result.body_accumulator == {
        "angular": (193.0, -318.0, 323.0),
        "linear": (4.0, 69.0, 70.0),
    }


def test_missing_or_nonfinite_post_primary_state_fails_closed():
    with pytest.raises(ValueError, match="primary response application state"):
        _run(None)

    with pytest.raises(ValueError):
        _run({"angular": (math.inf, 0.0, 0.0), "linear": (0.0, 0.0, 0.0)})


def test_invalid_aux_record_count_fails_closed():
    with pytest.raises(ValueError, match="exactly two"):
        execute_fun_00766510_partial_contact_chain(
            original_world_y=10.0,
            returned_contact_height=7.0,
            fallback_and_query_limit=4.0,
            depth_slope=2.0,
            base_offset=1.0,
            directional_curve=CurveParameters(0.0, 0.0, 0.0, 0.0),
            response_table=_table(),
            tangent_x=0.0,
            tangent_z=1.0,
            response_input=(-1.0, 2.0, 3.0),
            body_accumulator_after_primary_application={
                "angular": (0.0, 0.0, 0.0),
                "linear": (0.0, 0.0, 0.0),
            },
            aux_reference_point=(2.0, 3.0, 5.0),
            aux_records=(_record(),),
        )
