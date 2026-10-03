"""Reference state machine for Phase 697 persistent FUN_007682c0 integration.

This oracle owns only runtime admission, persistent BODY transport, pose-generation
telemetry and commit ordering around the already-proven Phase 696 executor. It
never reconstructs the unresolved FUN_007682c0 sqrt/x87 producer path.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

FORMAT = "SHIFT.Fun00770e80MotionReadRuntimeState/1"


@dataclass(frozen=True)
class MotionReadExecutionResult:
    final_body_bytes: bytes
    physics_pass_provider_call_count: int
    half_step_provider_call_count: int
    scalar_provider_call_count: int
    applied_rotation_count: int
    zero_noop_count: int
    contact_outer_input_provider_call_count: int
    contact_outer_native_call_count: int
    contact_outer_gate_open_count: int
    motion_read_effect_provider_call_count: int
    motion_read_delta_consumer_call_count: int
    motion_read_gate_open_count: int


@dataclass
class ExplicitMotionReadRuntimeState:
    body_count: int
    body_record_size: int
    initialized: bool = False
    explicit_update_count: int = 0
    body_pose_snapshot_generation: int = 0
    body_bytes: bytes = b""
    last_outer_timestep: float = 0.0
    last_physics_pass_provider_call_count: int = 0
    last_half_step_provider_call_count: int = 0
    last_scalar_provider_call_count: int = 0
    last_applied_rotation_count: int = 0
    last_zero_noop_count: int = 0
    last_contact_outer_input_provider_call_count: int = 0
    last_contact_outer_native_call_count: int = 0
    last_contact_outer_gate_open_count: int = 0
    last_motion_read_effect_provider_call_count: int = 0
    last_motion_read_delta_consumer_call_count: int = 0
    last_motion_read_gate_open_count: int = 0

    @property
    def expected_body_bytes(self) -> int:
        return self.body_count * self.body_record_size

    def initialize(self, initial_body_bytes: bytes, *, workspace_ready: bool) -> None:
        if not workspace_ready:
            raise ValueError("Phase 697 requires ready physics workspace")
        if self.body_count <= 0 or self.body_record_size <= 0:
            raise ValueError("Phase 697 requires non-zero BODY cardinality")
        if len(initial_body_bytes) != self.expected_body_bytes:
            raise ValueError("Phase 697 BODY byte cardinality mismatch")

        self.initialized = True
        self.explicit_update_count = 0
        self.body_pose_snapshot_generation = 0
        self.body_bytes = bytes(initial_body_bytes)
        self.last_outer_timestep = 0.0
        self.last_physics_pass_provider_call_count = 0
        self.last_half_step_provider_call_count = 0
        self.last_scalar_provider_call_count = 0
        self.last_applied_rotation_count = 0
        self.last_zero_noop_count = 0
        self.last_contact_outer_input_provider_call_count = 0
        self.last_contact_outer_native_call_count = 0
        self.last_contact_outer_gate_open_count = 0
        self.last_motion_read_effect_provider_call_count = 0
        self.last_motion_read_delta_consumer_call_count = 0
        self.last_motion_read_gate_open_count = 0

    def execute(
        self,
        outer_timestep: float,
        *,
        workspace_ready: bool,
        participant_ready: bool,
        participant_identity_join_proven: bool,
        executor: Callable[[bytes], MotionReadExecutionResult],
    ) -> MotionReadExecutionResult:
        if not self.initialized:
            raise ValueError("Phase 697 BODY state is not initialized")
        if not workspace_ready:
            raise ValueError("Phase 697 requires ready physics workspace")
        if not participant_ready or not participant_identity_join_proven:
            raise ValueError("Phase 697 requires ready participant identity")
        if len(self.body_bytes) != self.expected_body_bytes:
            raise ValueError("Phase 697 persistent BODY cardinality mismatch")
        if not callable(executor):
            raise ValueError("Phase 697 requires Phase 696 executor")

        previous_body_bytes = self.body_bytes
        result = executor(previous_body_bytes)
        if len(result.final_body_bytes) != self.expected_body_bytes:
            raise ValueError("Phase 697 executor returned malformed BODY state")

        # Runtime-owned state is committed only after the complete Phase 696
        # executor and returned-cardinality check succeed.
        self.body_bytes = bytes(result.final_body_bytes)
        self.last_outer_timestep = outer_timestep
        self.last_physics_pass_provider_call_count = (
            result.physics_pass_provider_call_count
        )
        self.last_half_step_provider_call_count = result.half_step_provider_call_count
        self.last_scalar_provider_call_count = result.scalar_provider_call_count
        self.last_applied_rotation_count = result.applied_rotation_count
        self.last_zero_noop_count = result.zero_noop_count
        self.last_contact_outer_input_provider_call_count = (
            result.contact_outer_input_provider_call_count
        )
        self.last_contact_outer_native_call_count = result.contact_outer_native_call_count
        self.last_contact_outer_gate_open_count = result.contact_outer_gate_open_count
        self.last_motion_read_effect_provider_call_count = (
            result.motion_read_effect_provider_call_count
        )
        self.last_motion_read_delta_consumer_call_count = (
            result.motion_read_delta_consumer_call_count
        )
        self.last_motion_read_gate_open_count = result.motion_read_gate_open_count
        self.explicit_update_count += 1
        self.body_pose_snapshot_generation = self.explicit_update_count
        return result


def contract() -> dict[str, object]:
    return {
        "format": FORMAT,
        "phase696_executor_reused": True,
        "persistent_body_bytes": True,
        "persistent_pose_generation": True,
        "participant_admission_before_executor": True,
        "runtime_owned_state_committed_after_success": True,
        "motion_read_effect_provider_telemetry": True,
        "motion_read_delta_consumer_telemetry": True,
        "motion_read_body_identity_application_external": True,
        "motion_read_machine_scalar_production_external": True,
        "host_sqrt_substitution_allowed": False,
        "fixed_step_auto_schedule": False,
    }


__all__ = [
    "FORMAT",
    "MotionReadExecutionResult",
    "ExplicitMotionReadRuntimeState",
    "contract",
]
