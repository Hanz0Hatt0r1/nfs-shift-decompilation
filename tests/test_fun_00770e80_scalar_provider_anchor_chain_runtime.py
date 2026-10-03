from __future__ import annotations

import pytest

import fun_00770e80_scalar_provider_anchor_chain_runtime as runtime


def test_phase691_calls_typed_scalar_provider_once_per_body_per_pass() -> None:
    scalar_calls: list[tuple[int, int]] = []

    def scalar_provider(pass_index: int, body_index: int, _basis, _rotation):
        scalar_calls.append((pass_index, body_index))
        return {
            "squared_magnitude_test": 0.0,
            "sqrt_magnitude": 0.0,
            "sine": 0.0,
            "cosine": 1.0,
        }

    def phase689_executor(adapted_provider):
        for pass_index in range(2):
            for body_index in range(3):
                adapted_provider(pass_index, body_index, "basis", "rotation")
        return {"phase689": "joined"}

    result = runtime.execute_fun_00770e80_scalar_provider_anchor_chain_runtime(
        phase689_executor,
        scalar_provider,
        body_count=3,
    )

    assert result.joined_result == {"phase689": "joined"}
    assert result.scalar_provider_call_counts == (3, 3)
    assert result.scalar_provider_call_count == 6
    assert scalar_calls == [
        (0, 0), (0, 1), (0, 2),
        (1, 0), (1, 1), (1, 2),
    ]


def test_phase691_rejects_missing_boundaries_and_bad_body_count() -> None:
    with pytest.raises(ValueError):
        runtime.execute_fun_00770e80_scalar_provider_anchor_chain_runtime(
            None,
            lambda *_: {},
            body_count=1,
        )
    with pytest.raises(ValueError):
        runtime.execute_fun_00770e80_scalar_provider_anchor_chain_runtime(
            lambda _: None,
            None,
            body_count=1,
        )
    with pytest.raises(ValueError):
        runtime.execute_fun_00770e80_scalar_provider_anchor_chain_runtime(
            lambda _: None,
            lambda *_: {},
            body_count=0,
        )


def test_phase691_rejects_incomplete_scalar_provider_cardinality() -> None:
    def phase689_executor(adapted_provider):
        adapted_provider(0, 0, "basis", "rotation")
        adapted_provider(1, 0, "basis", "rotation")
        return None

    with pytest.raises(ValueError):
        runtime.execute_fun_00770e80_scalar_provider_anchor_chain_runtime(
            phase689_executor,
            lambda *_: {},
            body_count=2,
        )


def test_phase691_rejects_body_index_outside_domain() -> None:
    def phase689_executor(adapted_provider):
        adapted_provider(0, 2, "basis", "rotation")
        return None

    with pytest.raises(ValueError):
        runtime.execute_fun_00770e80_scalar_provider_anchor_chain_runtime(
            phase689_executor,
            lambda *_: {},
            body_count=2,
        )


def test_phase691_contract_keeps_machine_scalar_gate_open() -> None:
    contract = runtime.contract()
    assert contract["format"] == "SHIFT.Fun00770e80ScalarProviderAnchorChainRuntime/1"
    assert contract["phase689_composed_anchor_chain_reused"] is True
    assert contract["fun_007afdd0_source_core_internal"] is True
    assert contract["arbitrary_basis_callback_external"] is False
    assert contract["scalar_boundary_fields"] == [
        "squared_magnitude_test",
        "sqrt_magnitude",
        "sine",
        "cosine",
    ]
    assert contract["machine_scalar_production_external"] is True
    assert contract["host_libm_substitution"] is False
    assert contract["persistent_body_bytes_preserved"] is True
    assert contract["fixed_step_auto_schedule"] is False
    assert contract["rendered_frame_cadence_proven"] is False
    assert contract["complete_fun_007afdd0_machine_semantics"] is False
    assert contract["complete_fun_00770e80_semantics"] is False
