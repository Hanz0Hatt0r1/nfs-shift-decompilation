from __future__ import annotations

import pytest

import explicit_outer_update_runtime_state as runtime


def make_body_bytes(body_count: int, fill: int = 0x21) -> bytes:
    return bytes([fill]) * (body_count * runtime.BODY_RECORD_SIZE)


def test_phase690_carries_body_bytes_only_across_explicit_calls() -> None:
    state = runtime.initialize_explicit_outer_update_runtime_state(
        make_body_bytes(2),
        runtime_body_count=2,
        workspace_ready=True,
    )
    seen: list[tuple[float, bytes]] = []

    def executor(dt: float, body_bytes: bytes) -> bytes:
        seen.append((dt, body_bytes))
        return bytes((value + 1) & 0xFF for value in body_bytes)

    first = runtime.execute_explicit_outer_update_runtime_state(
        state,
        runtime_body_count=2,
        workspace_ready=True,
        participant_ready=True,
        participant_identity_join_proven=True,
        outer_timestep=0.5,
        phase689_executor=executor,
    )
    second = runtime.execute_explicit_outer_update_runtime_state(
        first,
        runtime_body_count=2,
        workspace_ready=True,
        participant_ready=True,
        participant_identity_join_proven=True,
        outer_timestep=0.25,
        phase689_executor=executor,
    )

    assert seen[0] == (0.5, state.body_bytes)
    assert seen[1] == (0.25, first.body_bytes)
    assert first.explicit_update_count == 1
    assert second.explicit_update_count == 2
    assert second.last_outer_timestep == 0.25


def test_phase690_rejects_admission_failures_before_executor() -> None:
    state = runtime.initialize_explicit_outer_update_runtime_state(
        make_body_bytes(2),
        runtime_body_count=2,
        workspace_ready=True,
    )
    calls = 0

    def executor(_: float, body_bytes: bytes) -> bytes:
        nonlocal calls
        calls += 1
        return body_bytes

    cases = [
        dict(workspace_ready=False, participant_ready=True, participant_identity_join_proven=True),
        dict(workspace_ready=True, participant_ready=False, participant_identity_join_proven=True),
        dict(workspace_ready=True, participant_ready=True, participant_identity_join_proven=False),
    ]
    for case in cases:
        with pytest.raises(ValueError):
            runtime.execute_explicit_outer_update_runtime_state(
                state,
                runtime_body_count=2,
                outer_timestep=0.5,
                phase689_executor=executor,
                **case,
            )
    assert calls == 0


def test_phase690_rejects_body_cardinality_and_missing_executor() -> None:
    with pytest.raises(ValueError):
        runtime.initialize_explicit_outer_update_runtime_state(
            make_body_bytes(2)[:-1],
            runtime_body_count=2,
            workspace_ready=True,
        )

    state = runtime.initialize_explicit_outer_update_runtime_state(
        make_body_bytes(2),
        runtime_body_count=2,
        workspace_ready=True,
    )
    with pytest.raises(ValueError):
        runtime.execute_explicit_outer_update_runtime_state(
            state,
            runtime_body_count=3,
            workspace_ready=True,
            participant_ready=True,
            participant_identity_join_proven=True,
            outer_timestep=0.5,
            phase689_executor=lambda _, body_bytes: body_bytes,
        )
    with pytest.raises(ValueError):
        runtime.execute_explicit_outer_update_runtime_state(
            state,
            runtime_body_count=2,
            workspace_ready=True,
            participant_ready=True,
            participant_identity_join_proven=True,
            outer_timestep=0.5,
            phase689_executor=None,
        )


def test_phase690_rejects_malformed_executor_output() -> None:
    state = runtime.initialize_explicit_outer_update_runtime_state(
        make_body_bytes(2),
        runtime_body_count=2,
        workspace_ready=True,
    )
    with pytest.raises(ValueError):
        runtime.execute_explicit_outer_update_runtime_state(
            state,
            runtime_body_count=2,
            workspace_ready=True,
            participant_ready=True,
            participant_identity_join_proven=True,
            outer_timestep=0.5,
            phase689_executor=lambda _dt, body_bytes: body_bytes[:-1],
        )


def test_phase690_contract_keeps_cadence_and_machine_gate_open() -> None:
    contract = runtime.contract()
    assert contract["format"] == "SHIFT.NativeExplicitOuterUpdateRuntimeState/1"
    assert contract["phase689_composed_outer_update_reused"] is True
    assert contract["persistent_body_bytes_carried_between_explicit_updates"] is True
    assert contract["workspace_admission_required"] is True
    assert contract["participant_identity_admission_required"] is True
    assert contract["fixed_step_auto_schedule"] is False
    assert contract["rendered_frame_cadence_proven"] is False
    assert contract["per_pass_refresh_synthesized"] is False
    assert contract["fun_007afdd0_machine_scalar_gate_closed"] is False
    assert contract["complete_fun_00770e80_semantics"] is False
