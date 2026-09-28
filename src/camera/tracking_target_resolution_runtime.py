"""Evidence-backed TrackingCamera target-resolution boundaries.

Recovered from FUN_0081f2e0, FUN_0081f330 and FUN_0081f7c0.

These helpers choose between a specialized global service target and the
camera manager's configured target, query target transforms, and forward a
RTTI-resolved target pointer through the tracking camera vtable.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.TrackingTargetResolutionRuntime/1"


def resolve_tracking_target(
    *,
    manager_has_target: bool,
    manager_target: Any,
    global_service_flag_82e: bool,
    global_service_flag_82f: bool,
    nested_target: Any,
    nested_target_has_rtti: bool,
) -> dict[str, Any]:
    """Reproduce FUN_0081f2e0's exact target selection predicates."""
    if (
        manager_has_target
        and not global_service_flag_82e
        and not global_service_flag_82f
        and nested_target is not None
        and nested_target_has_rtti
    ):
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "tracking-target-resolve",
            "status": "specialized-global-target",
            "target": nested_target,
            "evidence": {
                "function": "FUN_0081f2e0",
                "global_service": "FUN_0080bfb0",
                "flags": ["+0x82e", "+0x82f"],
                "rtti_type": "0xc25fb8",
            },
        }

    return {
        "format": FORMAT,
        "version": 1,
        "operation": "tracking-target-resolve",
        "status": "manager-target" if manager_has_target else "none",
        "target": manager_target if manager_has_target else None,
        "evidence": {
            "function": "FUN_0081f2e0",
            "fallback": "manager +0x64",
        },
    }


def query_tracking_target_position(
    *,
    resolved_target: Any,
    target_state: int,
) -> dict[str, Any]:
    """Reproduce FUN_0081f330's conditional query boundary."""
    if resolved_target is None:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "tracking-target-position",
            "status": "no-target",
            "output": [0.0, 0.0, 0.0],
            "evidence": {"function": "FUN_0081f330"},
        }

    if int(target_state) < 0:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "tracking-target-position",
            "status": "state-negative",
            "output": [0.0, 0.0, 0.0],
            "evidence": {
                "function": "FUN_0081f330",
                "state_field": "target +0xfc",
                "query": "FUN_008155f0",
            },
        }

    return {
        "format": FORMAT,
        "version": 1,
        "operation": "tracking-target-position",
        "status": "query-helper",
        "output": [None, None, None],
        "actions": [
            {
                "action": "FUN_008155f0",
                "arguments": {
                    "tracking_camera": "this",
                    "output": "param_1",
                },
            }
        ],
        "evidence": {
            "function": "FUN_0081f330",
            "state_field": "target +0xfc",
            "fallback": "zero three-float output",
        },
        "limitations": [
            "FUN_008155f0 output values remain opaque",
        ],
    }


def describe_tracking_target_forward(
    *,
    source_object: Any | None,
    rtti_result: Any | None,
) -> dict[str, Any]:
    """Trace FUN_0081f7c0's RTTI-based vtable forwarding."""
    forwarded = (
        rtti_result
        if source_object is not None and rtti_result is not None
        else None
    )
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "tracking-target-forward",
        "status": "rtti-forwarded" if forwarded is not None else "null-forwarded",
        "rtti_type": "0xc25fb8",
        "forwarded": forwarded,
        "actions": [
            {
                "action": "FUN_004b71f0",
                "condition": source_object is not None,
                "type": "0xc25fb8",
            },
            {
                "action": "source.vtable +0x5c",
                "argument": forwarded,
            },
        ],
        "evidence": {
            "function": "FUN_0081f7c0",
            "null_branch": "source.vtable +0x5c(0)",
        },
    }
