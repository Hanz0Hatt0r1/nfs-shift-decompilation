"""Direct-call anchor sequence proven inside FUN_0076d100.

This module intentionally models only the required ordered anchors selected by
SHIFT.GhidraBodyUpdateScheduleFrontier/2. Intervening local arithmetic and other
calls remain outside the contract.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

FORMAT = "SHIFT.Fun0076d100AnchorSequenceRuntime/1"
PHYSICS_PASS = "FUN_0076d100"
CONTACT_FACTOR = "FUN_00765c40"
WHEEL_UPDATE = "FUN_00758b50"
CONTACT_RESPONSE = "FUN_00766510"
TAIL = "FUN_00769ef0"
CONTACT_OUTER = "FUN_007675f0"
MOTION_READ_GATE = "FUN_007682c0"


@dataclass(frozen=True)
class AnchorSequenceResult:
    events: tuple[str, ...]
    tail_invocation_count: int


def execute_required_anchor_sequence(
    contact_factor: Callable[[], None] | None,
    wheel_update: Callable[[], None] | None,
    contact_response: Callable[[], None] | None,
    contact_outer: Callable[[], None] | None,
    motion_read_gate: Callable[[], None] | None,
) -> AnchorSequenceResult:
    callbacks = (
        contact_factor,
        wheel_update,
        contact_response,
        contact_outer,
        motion_read_gate,
    )
    if any(callback is None for callback in callbacks):
        raise ValueError("FUN_0076d100 required-anchor sequence needs all callback boundaries")

    events: list[str] = []
    contact_factor()
    events.append(CONTACT_FACTOR)
    wheel_update()
    events.append(WHEEL_UPDATE)
    contact_response()
    events.append(CONTACT_RESPONSE)

    # FUN_00769ef0 is the uniquely recovered direct tail callee. Its two required
    # direct anchors are represented here without claiming its other local work.
    contact_outer()
    events.append(CONTACT_OUTER)
    motion_read_gate()
    events.append(MOTION_READ_GATE)

    return AnchorSequenceResult(tuple(events), 1)


def contract() -> dict[str, object]:
    return {
        "format": FORMAT,
        "physics_pass": PHYSICS_PASS,
        "required_pass_order": [
            CONTACT_FACTOR,
            WHEEL_UPDATE,
            CONTACT_RESPONSE,
            TAIL,
        ],
        "required_tail_order": [CONTACT_OUTER, MOTION_READ_GATE],
        "tail_function": TAIL,
        "complete_fun_0076d100_semantics": False,
        "complete_fun_00769ef0_semantics": False,
        "intervening_local_work_modeled": False,
        "callback_bodies_external": True,
    }
