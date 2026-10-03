import math

import pytest

from fun_007afdd0_scalar_provider_join_runtime import (
    FORMAT,
    ProviderJoinBodyInput,
    contract,
    execute_scalar_provider_join,
)
from fun_007afdd0_source_core import Fun007afdd0ScalarBoundary


IDENTITY = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)


def test_contract_keeps_machine_scalar_boundary_external():
    payload = contract()
    assert payload["format"] == FORMAT
    assert payload["source_core_used"] is True
    assert payload["host_math_used"] is False
    assert payload["machine_scalar_production_ready"] is False
    assert payload["production_basis_callback_replacement_ready"] is False


def test_provider_runs_once_per_body_in_array_order_and_zero_path_is_noop():
    calls = []
    bodies = [
        ProviderJoinBodyInput(IDENTITY, (0.0, 0.0, 0.0)),
        ProviderJoinBodyInput(IDENTITY, (0.0, 0.0, 2.0)),
    ]

    def provider(index, basis, increment):
        calls.append((index, basis, increment))
        if index == 0:
            return Fun007afdd0ScalarBoundary(
                squared_magnitude_test=0.0,
                sqrt_magnitude=math.nan,
                sine=math.nan,
                cosine=math.nan,
            )
        return Fun007afdd0ScalarBoundary(
            squared_magnitude_test=4.0,
            sqrt_magnitude=2.0,
            sine=1.0,
            cosine=0.0,
        )

    result = execute_scalar_provider_join(bodies, provider)
    assert result.provider_call_order == (0, 1)
    assert [row[0] for row in calls] == [0, 1]
    assert result.applied_rotation_count == 1
    assert result.zero_noop_count == 1
    assert result.bodies[0].basis == IDENTITY
    assert result.bodies[1].basis == (
        0.0, -1.0, 0.0,
        1.0, 0.0, 0.0,
        0.0, 0.0, 1.0,
    )


def test_nonzero_body_rejects_nonfinite_external_scalar_boundary():
    body = ProviderJoinBodyInput(IDENTITY, (1.0, 0.0, 0.0))

    def provider(index, basis, increment):
        return Fun007afdd0ScalarBoundary(
            squared_magnitude_test=1.0,
            sqrt_magnitude=1.0,
            sine=float("inf"),
            cosine=1.0,
        )

    with pytest.raises(ValueError, match="non-finite"):
        execute_scalar_provider_join([body], provider)


def test_missing_provider_and_invalid_cardinality_fail_closed():
    with pytest.raises(ValueError, match="requires a scalar provider"):
        execute_scalar_provider_join([], None)

    bad = ProviderJoinBodyInput((1.0,) * 8, (0.0, 0.0, 0.0))
    with pytest.raises(ValueError, match="exactly 9"):
        execute_scalar_provider_join([bad], lambda *_: Fun007afdd0ScalarBoundary(0.0))
