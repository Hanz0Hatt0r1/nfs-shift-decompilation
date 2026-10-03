from __future__ import annotations

import pytest

from fun_00770e80_motion_read_runtime_state import (
    ExplicitMotionReadRuntimeState,
    MotionReadExecutionResult,
    contract,
)


def _result(body_bytes: bytes, *, delta: int = 1) -> MotionReadExecutionResult:
    updated = bytes((value + delta) & 0xFF for value in body_bytes)
    return MotionReadExecutionResult(
        final_body_bytes=updated,
        physics_pass_provider_call_count=2,
        half_step_provider_call_count=2,
        scalar_provider_call_count=4,
        applied_rotation_count=0,
        zero_noop_count=4,
        contact_outer_input_provider_call_count=2,
        contact_outer_native_call_count=2,
        contact_outer_gate_open_count=2,
        motion_read_effect_provider_call_count=2,
        motion_read_delta_consumer_call_count=2,
        motion_read_gate_open_count=2,
    )


def test_phase697_carries_body_bytes_and_commits_motion_read_telemetry() -> None:
    state = ExplicitMotionReadRuntimeState(body_count=2, body_record_size=4)
    initial = bytes(range(8))
    state.initialize(initial, workspace_ready=True)
    seen: list[bytes] = []

    def executor(body_bytes: bytes) -> MotionReadExecutionResult:
        seen.append(bytes(body_bytes))
        return _result(body_bytes)

    first = state.execute(
        0.5,
        workspace_ready=True,
        participant_ready=True,
        participant_identity_join_proven=True,
        executor=executor,
    )
    second = state.execute(
        0.5,
        workspace_ready=True,
        participant_ready=True,
        participant_identity_join_proven=True,
        executor=executor,
    )

    assert seen == [initial, first.final_body_bytes]
    assert state.body_bytes == second.final_body_bytes
    assert state.explicit_update_count == 2
    assert state.body_pose_snapshot_generation == 2
    assert state.last_outer_timestep == 0.5
    assert state.last_physics_pass_provider_call_count == 2
    assert state.last_half_step_provider_call_count == 2
    assert state.last_scalar_provider_call_count == 4
    assert state.last_contact_outer_input_provider_call_count == 2
    assert state.last_contact_outer_native_call_count == 2
    assert state.last_motion_read_effect_provider_call_count == 2
    assert state.last_motion_read_delta_consumer_call_count == 2
    assert state.last_motion_read_gate_open_count == 2


def test_phase697_admission_rejects_before_executor() -> None:
    state = ExplicitMotionReadRuntimeState(body_count=1, body_record_size=4)
    state.initialize(b"abcd", workspace_ready=True)
    calls = 0

    def executor(body_bytes: bytes) -> MotionReadExecutionResult:
        nonlocal calls
        calls += 1
        return _result(body_bytes)

    with pytest.raises(ValueError, match="ready participant identity"):
        state.execute(
            0.5,
            workspace_ready=True,
            participant_ready=False,
            participant_identity_join_proven=True,
            executor=executor,
        )
    assert calls == 0
    assert state.explicit_update_count == 0
    assert state.body_bytes == b"abcd"


def test_phase697_failure_or_bad_cardinality_preserves_runtime_owned_state() -> None:
    state = ExplicitMotionReadRuntimeState(body_count=1, body_record_size=4)
    state.initialize(b"abcd", workspace_ready=True)

    def fail(_body_bytes: bytes) -> MotionReadExecutionResult:
        raise RuntimeError("provider failure")

    with pytest.raises(RuntimeError, match="provider failure"):
        state.execute(
            0.5,
            workspace_ready=True,
            participant_ready=True,
            participant_identity_join_proven=True,
            executor=fail,
        )
    assert state.body_bytes == b"abcd"
    assert state.explicit_update_count == 0
    assert state.last_motion_read_effect_provider_call_count == 0

    def malformed(body_bytes: bytes) -> MotionReadExecutionResult:
        result = _result(body_bytes)
        return MotionReadExecutionResult(
            **{**result.__dict__, "final_body_bytes": b"bad"}
        )

    with pytest.raises(ValueError, match="malformed BODY state"):
        state.execute(
            0.5,
            workspace_ready=True,
            participant_ready=True,
            participant_identity_join_proven=True,
            executor=malformed,
        )
    assert state.body_bytes == b"abcd"
    assert state.explicit_update_count == 0
    assert state.body_pose_snapshot_generation == 0


def test_phase697_contract_keeps_machine_identity_and_cadence_external() -> None:
    payload = contract()
    assert payload["format"] == "SHIFT.Fun00770e80MotionReadRuntimeState/1"
    assert payload["phase696_executor_reused"] is True
    assert payload["persistent_body_bytes"] is True
    assert payload["persistent_pose_generation"] is True
    assert payload["participant_admission_before_executor"] is True
    assert payload["runtime_owned_state_committed_after_success"] is True
    assert payload["motion_read_body_identity_application_external"] is True
    assert payload["motion_read_machine_scalar_production_external"] is True
    assert payload["host_sqrt_substitution_allowed"] is False
    assert payload["fixed_step_auto_schedule"] is False
