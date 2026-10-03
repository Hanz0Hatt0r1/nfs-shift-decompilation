from __future__ import annotations

import math

import pytest

from fun_00770e80_composed_anchor_chain_runtime import (
    HALF_EXECUTE,
    HALF_PROVIDER,
    PASS_EXECUTE,
    PASS_PROVIDER,
    POST_HALF,
    contract,
    execute_fun_00770e80_composed_anchor_chain_runtime,
)


def test_composed_chain_preserves_two_pass_order_and_body_handoff() -> None:
    seen: list[tuple[str, int, bytes | None]] = []

    def pass_provider(index: int) -> dict[str, int]:
        seen.append((PASS_PROVIDER, index, None))
        return {"pass": index}

    def pass_executor(index: int, payload: dict[str, int]) -> str:
        assert payload == {"pass": index}
        seen.append((PASS_EXECUTE, index, None))
        return f"pass-{index}"

    def half_provider(index: int, half_dt: float, body: bytes) -> dict[str, object]:
        assert half_dt == pytest.approx(0.25)
        seen.append((HALF_PROVIDER, index, body))
        return {"pass": index, "body": body}

    def half_executor(
        index: int,
        half_dt: float,
        payload: dict[str, object],
        body: bytes,
    ) -> tuple[str, bytes]:
        assert half_dt == pytest.approx(0.25)
        assert payload["pass"] == index
        assert payload["body"] == body
        seen.append((HALF_EXECUTE, index, body))
        return f"half-{index}", body + bytes([0xA0 + index])

    def post_half(index: int) -> None:
        seen.append((POST_HALF, index, None))

    result = execute_fun_00770e80_composed_anchor_chain_runtime(
        b"BODY",
        pass_provider,
        pass_executor,
        half_provider,
        half_executor,
        post_half,
        0.5,
    )

    assert result.pass_results == ("pass-0", "pass-1")
    assert result.half_step_results == ("half-0", "half-1")
    assert result.half_step_input_body_bytes == (b"BODY", b"BODY\xA0")
    assert result.final_body_bytes == b"BODY\xA0\xA1"
    assert result.events == (
        (PASS_PROVIDER, 0),
        (PASS_EXECUTE, 0),
        (HALF_PROVIDER, 0),
        (HALF_EXECUTE, 0),
        (POST_HALF, 0),
        (PASS_PROVIDER, 1),
        (PASS_EXECUTE, 1),
        (HALF_PROVIDER, 1),
        (HALF_EXECUTE, 1),
        (POST_HALF, 1),
    )
    assert seen[2] == (HALF_PROVIDER, 0, b"BODY")
    assert seen[7] == (HALF_PROVIDER, 1, b"BODY\xA0")


def test_composed_chain_requires_every_external_boundary() -> None:
    args = dict(
        initial_body_bytes=b"x",
        physics_pass_provider=lambda index: index,
        physics_pass_executor=lambda index, payload: payload,
        half_step_provider=lambda index, dt, body: None,
        half_step_executor=lambda index, dt, payload, body: (None, body),
        post_half_step=lambda index: None,
        outer_timestep=0.1,
    )
    for field in (
        "physics_pass_provider",
        "physics_pass_executor",
        "half_step_provider",
        "half_step_executor",
        "post_half_step",
    ):
        broken = dict(args)
        broken[field] = None
        with pytest.raises(ValueError):
            execute_fun_00770e80_composed_anchor_chain_runtime(**broken)


def test_composed_chain_rejects_non_finite_timestep() -> None:
    with pytest.raises(ValueError, match="finite"):
        execute_fun_00770e80_composed_anchor_chain_runtime(
            b"x",
            lambda index: None,
            lambda index, payload: None,
            lambda index, dt, body: None,
            lambda index, dt, payload, body: (None, body),
            lambda index: None,
            math.inf,
        )


def test_contract_keeps_refresh_and_frame_cadence_unproven() -> None:
    payload = contract()
    assert payload["format"] == "SHIFT.Fun00770e80ComposedAnchorChainRuntime/1"
    assert payload["pass_count"] == 2
    assert payload["phase684_required_anchor_sequence_reused"] is True
    assert payload["phase688_machine_half_step_reused"] is True
    assert payload["persistent_body_bytes_carried_between_half_steps"] is True
    assert payload["per_pass_physics_refresh_proven"] is False
    assert payload["per_half_step_solver_refresh_proven"] is False
    assert payload["rendered_frame_cadence_proven"] is False
    assert payload["complete_fun_00770e80_semantics"] is False
