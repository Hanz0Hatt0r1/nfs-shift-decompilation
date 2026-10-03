"""Scheduling oracle for Phase 689 composed FUN_00770e80 anchor chain.

The oracle models only proven anchor ordering and raw persistent BODY byte handoff.
Per-pass physics inputs and per-half-step solver/machine inputs remain mandatory
providers so this layer does not invent refresh semantics between the two retail
half-steps.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

FORMAT = "SHIFT.Fun00770e80ComposedAnchorChainRuntime/1"
PASS_PROVIDER = "phase684-pass-provider"
PASS_EXECUTE = "phase684-pass"
HALF_PROVIDER = "phase688-half-step-provider"
HALF_EXECUTE = "phase688-half-step"
POST_HALF = "FUN_007b8810"
PASS_COUNT = 2


@dataclass(frozen=True)
class ComposedAnchorChainRuntimeResult:
    pass_results: tuple[Any, ...]
    half_step_results: tuple[Any, ...]
    final_body_bytes: bytes
    events: tuple[tuple[str, int], ...]
    half_step_input_body_bytes: tuple[bytes, ...]


def execute_fun_00770e80_composed_anchor_chain_runtime(
    initial_body_bytes: bytes,
    physics_pass_provider: Callable[[int], Any] | None,
    physics_pass_executor: Callable[[int, Any], Any] | None,
    half_step_provider: Callable[[int, float, bytes], Any] | None,
    half_step_executor: Callable[[int, float, Any, bytes], tuple[Any, bytes]] | None,
    post_half_step: Callable[[int], None] | None,
    outer_timestep: float,
) -> ComposedAnchorChainRuntimeResult:
    if physics_pass_provider is None:
        raise ValueError("Phase 689 requires physics-pass provider")
    if physics_pass_executor is None:
        raise ValueError("Phase 689 requires Phase 684 executor")
    if half_step_provider is None:
        raise ValueError("Phase 689 requires half-step provider")
    if half_step_executor is None:
        raise ValueError("Phase 689 requires Phase 688 executor")
    if post_half_step is None:
        raise ValueError("Phase 689 requires FUN_007b8810 callback")

    outer_timestep = float(outer_timestep)
    if not __import__("math").isfinite(outer_timestep):
        raise ValueError("outer timestep must be finite")
    half_timestep = outer_timestep * 0.5
    if not __import__("math").isfinite(half_timestep):
        raise ValueError("half timestep must be finite")

    current_body_bytes = bytes(initial_body_bytes)
    pass_results: list[Any] = []
    half_results: list[Any] = []
    events: list[tuple[str, int]] = []
    half_inputs: list[bytes] = []

    for pass_index in range(PASS_COUNT):
        pass_payload = physics_pass_provider(pass_index)
        events.append((PASS_PROVIDER, pass_index))
        pass_results.append(physics_pass_executor(pass_index, pass_payload))
        events.append((PASS_EXECUTE, pass_index))

        half_inputs.append(current_body_bytes)
        half_payload = half_step_provider(pass_index, half_timestep, current_body_bytes)
        events.append((HALF_PROVIDER, pass_index))
        half_result, next_body_bytes = half_step_executor(
            pass_index,
            half_timestep,
            half_payload,
            current_body_bytes,
        )
        current_body_bytes = bytes(next_body_bytes)
        half_results.append(half_result)
        events.append((HALF_EXECUTE, pass_index))

        post_half_step(pass_index)
        events.append((POST_HALF, pass_index))

    return ComposedAnchorChainRuntimeResult(
        pass_results=tuple(pass_results),
        half_step_results=tuple(half_results),
        final_body_bytes=current_body_bytes,
        events=tuple(events),
        half_step_input_body_bytes=tuple(half_inputs),
    )


def contract() -> dict[str, object]:
    return {
        "format": FORMAT,
        "source_function": "FUN_00770e80",
        "pass_count": PASS_COUNT,
        "per_pass_order": [
            PASS_PROVIDER,
            PASS_EXECUTE,
            HALF_PROVIDER,
            HALF_EXECUTE,
            POST_HALF,
        ],
        "phase684_required_anchor_sequence_reused": True,
        "phase688_machine_half_step_reused": True,
        "persistent_body_bytes_carried_between_half_steps": True,
        "per_pass_physics_refresh_proven": False,
        "per_half_step_solver_refresh_proven": False,
        "intervening_local_work_modeled": False,
        "rendered_frame_cadence_proven": False,
        "complete_fun_00770e80_semantics": False,
    }
