"""Scheduling oracle for Phase 690 explicit persistent outer-update runtime state.

This module deliberately models only the runtime-state boundary around the already
implemented Phase 689 composed outer update. It does not infer a cadence from the
native fixed-step loop and it does not synthesize any per-pass physics inputs.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

FORMAT = "SHIFT.NativeExplicitOuterUpdateRuntimeState/1"
BODY_RECORD_SIZE = 0x170


@dataclass(frozen=True)
class ExplicitOuterUpdateRuntimeState:
    body_count: int
    body_bytes: bytes
    explicit_update_count: int = 0
    last_outer_timestep: float = 0.0


def initialize_explicit_outer_update_runtime_state(
    initial_body_bytes: bytes,
    *,
    runtime_body_count: int,
    workspace_ready: bool,
) -> ExplicitOuterUpdateRuntimeState:
    if not workspace_ready:
        raise ValueError("Phase 690 requires a ready physics workspace")
    if runtime_body_count <= 0:
        raise ValueError("Phase 690 requires a non-zero BODY count")
    expected = runtime_body_count * BODY_RECORD_SIZE
    if len(initial_body_bytes) != expected:
        raise ValueError("Phase 690 BODY byte cardinality mismatch")
    return ExplicitOuterUpdateRuntimeState(
        body_count=runtime_body_count,
        body_bytes=bytes(initial_body_bytes),
    )


def execute_explicit_outer_update_runtime_state(
    state: ExplicitOuterUpdateRuntimeState,
    *,
    runtime_body_count: int,
    workspace_ready: bool,
    participant_ready: bool,
    participant_identity_join_proven: bool,
    outer_timestep: float,
    phase689_executor: Callable[[float, bytes], bytes] | None,
) -> ExplicitOuterUpdateRuntimeState:
    if not workspace_ready:
        raise ValueError("Phase 690 requires a ready physics workspace")
    if not participant_ready or not participant_identity_join_proven:
        raise ValueError("Phase 690 requires ready participant identity")
    if runtime_body_count != state.body_count:
        raise ValueError("Phase 690 runtime BODY count mismatch")
    expected = runtime_body_count * BODY_RECORD_SIZE
    if len(state.body_bytes) != expected:
        raise ValueError("Phase 690 persistent BODY state cardinality mismatch")
    if phase689_executor is None:
        raise ValueError("Phase 690 requires the Phase 689 executor")

    final_body_bytes = bytes(phase689_executor(outer_timestep, state.body_bytes))
    if len(final_body_bytes) != expected:
        raise ValueError("Phase 690 executor returned malformed BODY state")

    return ExplicitOuterUpdateRuntimeState(
        body_count=state.body_count,
        body_bytes=final_body_bytes,
        explicit_update_count=state.explicit_update_count + 1,
        last_outer_timestep=outer_timestep,
    )


def contract() -> dict[str, object]:
    return {
        "format": FORMAT,
        "phase689_composed_outer_update_reused": True,
        "persistent_body_bytes_carried_between_explicit_updates": True,
        "workspace_admission_required": True,
        "participant_identity_admission_required": True,
        "fixed_step_auto_schedule": False,
        "rendered_frame_cadence_proven": False,
        "per_pass_refresh_synthesized": False,
        "fun_007afdd0_machine_scalar_gate_closed": False,
        "complete_fun_00770e80_semantics": False,
    }
