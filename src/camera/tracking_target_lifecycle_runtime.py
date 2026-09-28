"""Evidence-backed TrackingCamera target attachment/lifecycle boundaries.

Recovered from FUN_0081f070 and FUN_0081f160.

The target acquisition loop is preserved literally: after FUN_0081ea70, the
manager's global service list is scanned, each candidate is checked for the
0xc25fb8 RTTI marker in its linked list, and FUN_00408210 compares the
candidate's +0x18 field with TrackingCamera +0x35. On success FUN_00812970
receives that candidate.
"""

from __future__ import annotations

from typing import Any, Iterable, Sequence

FORMAT = "SHIFT.TrackingTargetLifecycleRuntime/1"


def describe_tracking_target_acquisition(
    *,
    target_handle_present: bool,
    target_handle_count_nonzero: bool,
    service_available: bool,
    candidates: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Trace FUN_0081f070 without assigning semantics to service candidates."""
    actions: list[dict[str, Any]] = [
        {"action": "FUN_00812aa0"},
        {"action": "FUN_0081ea70"},
    ]

    if not target_handle_present or not target_handle_count_nonzero:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "tracking-target-acquisition",
            "status": "no-target-handle",
            "actions": actions,
        }

    if not service_available:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "tracking-target-acquisition",
            "status": "service-unavailable",
            "actions": actions + [
                {"action": "FUN_0080bfb0"},
                {"action": "FUN_0080b8e0"},
            ],
        }

    for ordinal, candidate in enumerate(candidates):
        has_rtti = bool(candidate.get("contains_rtti_0xc25fb8", False))
        compare_matches = bool(candidate.get("field_0x18_matches_target", False))
        row = {
            "ordinal": ordinal,
            "contains_rtti_0xc25fb8": has_rtti,
            "field_0x18_matches_target": compare_matches,
            "actions": [
                {
                    "action": "candidate linked-list scan",
                    "target": "DAT_00c25fb8",
                    "rtti_found": has_rtti,
                }
            ],
        }
        if has_rtti:
            row["actions"].append({
                "action": "FUN_00408210",
                "arguments": {
                    "candidate_field": "candidate + 0x18",
                    "target_handle": "TrackingCamera + 0x35",
                },
                "result": compare_matches,
            })
        if has_rtti and compare_matches:
            row["actions"].append({
                "action": "FUN_00812970",
                "argument": f"candidate[{ordinal}]",
            })
            actions.append(row)
            return {
                "format": FORMAT,
                "version": 1,
                "operation": "tracking-target-acquisition",
                "status": "attached",
                "selected_candidate": ordinal,
                "actions": actions,
                "candidate_trace": row,
                "evidence": {
                    "function": "FUN_0081f070",
                    "service_root": "FUN_0080bfb0",
                    "service_view": "FUN_0080b8e0",
                    "rtti_marker": "DAT_00c25fb8",
                    "compare": "FUN_00408210(candidate+0x18, this+0x35)",
                    "attach": "FUN_00812970",
                },
            }
        actions.append(row)

    return {
        "format": FORMAT,
        "version": 1,
        "operation": "tracking-target-acquisition",
        "status": "not-found",
        "actions": actions,
        "evidence": {
            "function": "FUN_0081f070",
            "rtti_marker": "DAT_00c25fb8",
        },
    }


def describe_tracking_camera_lifecycle_reset() -> dict[str, Any]:
    """Trace FUN_0081f160's lifecycle reset ordering."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "tracking-camera-lifecycle-reset",
        "actions": [
            {"action": "write vtable", "value": "PTR_FUN_00b16788"},
            {"action": "FUN_0081ea80"},
            {"action": "FUN_00675d70", "target": "+0x320"},
            {"action": "FUN_00813f70"},
        ],
        "evidence": {
            "function": "FUN_0081f160",
            "frame_stack": "+0x320",
        },
    }
