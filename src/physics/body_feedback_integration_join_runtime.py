"""Scheduling oracle for the proven BODY feedback -> integration anchor order.

This does not model the arithmetic of either stage. It freezes the static order
inside the recovered FUN_00765470 boundary and requires byte-exact handoff from
the feedback stage into the BODY-array integration stage.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

FORMAT = "SHIFT.NativeBodyFeedbackIntegrationJoin/1"
HALF_STEP_ANCHOR = "FUN_00765470"
POST_SOLVE_FEEDBACK = "FUN_007b4110"
BODY_ARRAY_INTEGRATION = "FUN_007b2270"
BODY_INTEGRATOR = "FUN_007bab70"
BASIS_ROTATION = "FUN_007afdd0"


@dataclass(frozen=True)
class BodyFeedbackIntegrationJoinTrace:
    output: bytes
    events: tuple[str, ...]
    feedback_output: bytes


def execute_body_feedback_integration_join(
    body_bytes: bytes,
    feedback_stage: Callable[[bytes], bytes],
    integration_stage: Callable[[bytes], bytes],
) -> BodyFeedbackIntegrationJoinTrace:
    if not callable(feedback_stage) or not callable(integration_stage):
        raise ValueError("feedback and integration stages must be callable")
    if not isinstance(body_bytes, bytes):
        raise ValueError("BODY join input must be bytes")

    feedback_output = feedback_stage(body_bytes)
    if not isinstance(feedback_output, bytes):
        raise ValueError("feedback stage must return bytes")
    output = integration_stage(feedback_output)
    if not isinstance(output, bytes):
        raise ValueError("integration stage must return bytes")

    return BodyFeedbackIntegrationJoinTrace(
        output=output,
        events=(POST_SOLVE_FEEDBACK, BODY_ARRAY_INTEGRATION),
        feedback_output=feedback_output,
    )


def build_body_feedback_integration_join_contract() -> dict:
    return {
        "format": FORMAT,
        "half_step_anchor": HALF_STEP_ANCHOR,
        "ordered_anchors": (POST_SOLVE_FEEDBACK, BODY_ARRAY_INTEGRATION),
        "body_integrator": BODY_INTEGRATOR,
        "basis_rotation": BASIS_ROTATION,
        "feedback_before_integration_proven": True,
        "byte_exact_feedback_to_integration_handoff": True,
        "basis_rotation_arithmetic_external": True,
        "complete_half_step_implemented": False,
        "render_frame_scheduler_proven": False,
    }
