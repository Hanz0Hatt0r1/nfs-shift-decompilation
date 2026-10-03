from __future__ import annotations

import pytest

from fun_00770e80_contact_outer_runtime_state import (
    ContactOuterExecutionResult,
    ExplicitContactOuterRuntimeState,
    contract,
)


def _result(body_bytes: bytes, marker: int) -> ContactOuterExecutionResult:
    return ContactOuterExecutionResult(
        final_body_bytes=bytes([marker]) * len(body_bytes),
        physics_pass_provider_call_count=2,
        half_step_provider_call_count=2,
        scalar_provider_call_count=4,
        applied_rotation_count=0,
        zero_noop_count=4,
        contact_outer_input_provider_call_count=2,
        contact_outer_native_call_count=2,
        contact_outer_gate_open_count=1,
    )


def test_phase694_commits_persistent_body_and_telemetry_after_success() -> None:
    state = ExplicitContactOuterRuntimeState(body_count=2, body_record_size=4)
    initial = bytes(range(8))
    state.initialize(initial, workspace_ready=True)

    seen: list[bytes] = []

    def first_executor(body_bytes: bytes) -> ContactOuterExecutionResult:
        seen.append(body_bytes)
        return _result(body_bytes, 0x31)

    first = state.execute(
        0.5,
        workspace_ready=True,
        participant_ready=True,
        participant_identity_join_proven=True,
        executor=first_executor,
    )
    assert seen == [initial]
    assert state.body_bytes == first.final_body_bytes
    assert state.explicit_update_count == 1
    assert state.last_physics_pass_provider_call_count == 2
    assert state.last_half_step_provider_call_count == 2
    assert state.last_scalar_provider_call_count == 4
    assert state.last_contact_outer_input_provider_call_count == 2
    assert state.last_contact_outer_native_call_count == 2
    assert state.last_contact_outer_gate_open_count == 1

    first_persistent = state.body_bytes

    def second_executor(body_bytes: bytes) -> ContactOuterExecutionResult:
        seen.append(body_bytes)
        return _result(body_bytes, 0x52)

    second = state.execute(
        0.5,
        workspace_ready=True,
        participant_ready=True,
        participant_identity_join_proven=True,
        executor=second_executor,
    )
    assert seen[1] == first_persistent
    assert state.body_bytes == second.final_body_bytes
    assert state.body_bytes != first_persistent
    assert state.explicit_update_count == 2


def test_phase694_admission_fails_before_executor_and_preserves_commit() -> None:
    state = ExplicitContactOuterRuntimeState(body_count=1, body_record_size=4)
    state.initialize(b"abcd", workspace_ready=True)
    calls = 0

    def executor(body_bytes: bytes) -> ContactOuterExecutionResult:
        nonlocal calls
        calls += 1
        return _result(body_bytes, 0x11)

    with pytest.raises(ValueError, match="participant identity"):
        state.execute(
            0.5,
            workspace_ready=True,
            participant_ready=False,
            participant_identity_join_proven=True,
            executor=executor,
        )
    assert calls == 0
    assert state.body_bytes == b"abcd"
    assert state.explicit_update_count == 0


def test_phase694_failed_executor_does_not_commit_partial_state() -> None:
    state = ExplicitContactOuterRuntimeState(body_count=1, body_record_size=4)
    state.initialize(b"abcd", workspace_ready=True)

    def executor(_body_bytes: bytes) -> ContactOuterExecutionResult:
        raise RuntimeError("provider failure")

    with pytest.raises(RuntimeError, match="provider failure"):
        state.execute(
            0.5,
            workspace_ready=True,
            participant_ready=True,
            participant_identity_join_proven=True,
            executor=executor,
        )
    assert state.body_bytes == b"abcd"
    assert state.explicit_update_count == 0
    assert state.last_contact_outer_native_call_count == 0


def test_phase694_rejects_malformed_body_result_before_commit() -> None:
    state = ExplicitContactOuterRuntimeState(body_count=1, body_record_size=4)
    state.initialize(b"abcd", workspace_ready=True)

    with pytest.raises(ValueError, match="malformed BODY state"):
        state.execute(
            0.5,
            workspace_ready=True,
            participant_ready=True,
            participant_identity_join_proven=True,
            executor=lambda body_bytes: ContactOuterExecutionResult(
                final_body_bytes=b"bad",
                physics_pass_provider_call_count=2,
                half_step_provider_call_count=2,
                scalar_provider_call_count=4,
                applied_rotation_count=0,
                zero_noop_count=4,
                contact_outer_input_provider_call_count=2,
                contact_outer_native_call_count=2,
                contact_outer_gate_open_count=1,
            ),
        )
    assert state.body_bytes == b"abcd"
    assert state.explicit_update_count == 0


def test_phase694_contract_keeps_unproven_scheduling_and_producers_external() -> None:
    payload = contract()
    assert payload["format"] == "SHIFT.Fun00770e80ContactOuterRuntimeState/1"
    assert payload["phase693_executor_reused"] is True
    assert payload["persistent_body_bytes"] is True
    assert payload["participant_admission_before_executor"] is True
    assert payload["fixed_step_auto_schedule"] is False
    assert payload["machine_scalar_production_external"] is True
    assert payload["contact_outer_input_production_external"] is True
