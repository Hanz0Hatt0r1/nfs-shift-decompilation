import math

import pytest

from body_array_basis_callback_runtime import (
    BODY_STRIDE,
    FORMAT,
    BodyBasisCallbackInput,
    build_body_array_basis_callback_contract,
    execute_body_array_basis_callback_schedule,
)


IDENTITY = (
    1.0, 0.0, 0.0,
    0.0, 1.0, 0.0,
    0.0, 0.0, 1.0,
)


def test_contract_freezes_source_backed_boundary():
    contract = build_body_array_basis_callback_contract()
    assert contract["format"] == FORMAT
    assert contract["body_stride"] == BODY_STRIDE == 0x170
    assert contract["retail_iteration_order_proven"] is True
    assert contract["basis_provider_inside_each_body_proven"] is True
    assert contract["basis_rotation_arithmetic_external"] is True
    assert contract["render_frame_scheduler_proven"] is False


def test_provider_runs_once_per_body_in_retail_array_order():
    bodies = (
        BodyBasisCallbackInput(IDENTITY, (0.25, 0.0, 0.0)),
        BodyBasisCallbackInput(IDENTITY, (0.0, -0.5, 0.0)),
        BodyBasisCallbackInput(IDENTITY, (0.0, 0.0, 0.75)),
    )
    calls = []

    def provider(basis, increment):
        calls.append((basis, increment))
        updated = list(basis)
        updated[0] += float(len(calls))
        return updated

    result = execute_body_array_basis_callback_schedule(bodies, provider)
    assert [call[1] for call in calls] == [body.rotation_increment for body in bodies]
    assert [basis[0] for basis in result] == [2.0, 3.0, 4.0]


def test_empty_body_array_does_not_call_provider():
    called = False

    def provider(basis, increment):
        nonlocal called
        called = True
        return basis

    assert execute_body_array_basis_callback_schedule((), provider) == ()
    assert called is False


def test_rejects_non_finite_input_before_provider():
    calls = 0

    def provider(basis, increment):
        nonlocal calls
        calls += 1
        return basis

    bodies = (
        BodyBasisCallbackInput(IDENTITY, (math.inf, 0.0, 0.0)),
    )
    with pytest.raises(ValueError, match="non-finite"):
        execute_body_array_basis_callback_schedule(bodies, provider)
    assert calls == 0


def test_rejects_non_finite_provider_output():
    bodies = (BodyBasisCallbackInput(IDENTITY, (0.0, 0.0, 0.0)),)

    def provider(basis, increment):
        updated = list(basis)
        updated[4] = math.nan
        return updated

    with pytest.raises(ValueError, match="non-finite"):
        execute_body_array_basis_callback_schedule(bodies, provider)


def test_rejects_provider_output_with_wrong_size():
    bodies = (BodyBasisCallbackInput(IDENTITY, (0.0, 0.0, 0.0)),)
    with pytest.raises(ValueError, match="exactly 9"):
        execute_body_array_basis_callback_schedule(
            bodies,
            lambda basis, increment: basis[:8],
        )


def test_rejects_missing_provider():
    with pytest.raises(ValueError, match="requires a basis-rotation provider"):
        execute_body_array_basis_callback_schedule((), None)  # type: ignore[arg-type]
