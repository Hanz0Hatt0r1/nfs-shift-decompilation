"""Scheduling oracle for the proven FUN_00765470 wheel-before-feedback join.

This module freezes only the static relative order:

    FUN_00763570 -> existing Phase 679 feedback/integration join

The callback payloads remain external and byte-identical.  It does not model
intervening FUN_00765470 local work or claim complete half-step semantics.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

FORMAT = "SHIFT.Fun00765470WheelFeedbackJoinRuntime/1"
HALF_STEP = "FUN_00765470"
WHEEL_SHARED_TRIPLET = "FUN_00763570"
POST_SOLVE_FEEDBACK = "FUN_007b4110"
BODY_ARRAY_INTEGRATION = "FUN_007b2270"


@dataclass(frozen=True)
class JoinResult:
    body_bytes: bytes
    events: tuple[str, ...]
    wheel_shared_triplet_anchor_count: int


def execute_wheel_feedback_join(
    body_bytes: bytes,
    wheel_shared_triplet: Callable[[], None] | None,
    feedback_integration: Callable[[bytes], bytes] | None,
) -> JoinResult:
    if wheel_shared_triplet is None:
        raise ValueError("FUN_00765470 proven join requires FUN_00763570 callback")
    if feedback_integration is None:
        raise ValueError("FUN_00765470 proven join requires Phase 679 feedback/integration callback")

    events: list[str] = []
    wheel_shared_triplet()
    events.append(WHEEL_SHARED_TRIPLET)

    output = feedback_integration(body_bytes)
    if not isinstance(output, bytes):
        raise ValueError("Phase 679 feedback/integration callback must return bytes")
    events.extend((POST_SOLVE_FEEDBACK, BODY_ARRAY_INTEGRATION))

    return JoinResult(output, tuple(events), 1)


def contract() -> dict[str, object]:
    return {
        "format": FORMAT,
        "half_step": HALF_STEP,
        "required_order": [
            WHEEL_SHARED_TRIPLET,
            POST_SOLVE_FEEDBACK,
            BODY_ARRAY_INTEGRATION,
        ],
        "phase679_join_reused": True,
        "intervening_local_work_modeled": False,
        "complete_fun_00765470_semantics": False,
        "wheel_shared_triplet_callback_external": True,
        "feedback_integration_bytes_reconstructed": False,
    }
