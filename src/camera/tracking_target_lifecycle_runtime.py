"""Evidence-backed TrackingCamera override/lifecycle boundaries.

Retail machine code corrects an earlier naming mistake in this model.  The
FUN_00812aa0/FUN_0081f070 scan does *not* resolve the CTrackingCamData
``Target`` field.  It compares the runtime camera field at byte ``+0xd4`` with
a candidate name at byte ``+0x60``.  CTrackingCamData reflection registers
``Target`` at ``+0x78`` and ``OverridedBy`` at ``+0xd4``.  RTTI 0xc25fb8 is
constructed through FUN_0081f990 as the TrackingCamera-sized object.  The scan
therefore belongs to camera-to-camera override linkage and must not be used as
player-vehicle target proof.
"""

from __future__ import annotations

from typing import Any, Iterable

FORMAT = "SHIFT.TrackingTargetLifecycleRuntime/2"


def describe_tracking_override_resolution(
    *,
    override_name_present: bool,
    override_name_count_nonzero: bool,
    service_available: bool,
    candidates: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Trace the FUN_0081f070 override-name scan with exact byte offsets."""
    actions: list[dict[str, Any]] = [
        {"action": "FUN_00812aa0"},
        {"action": "FUN_0081ea70"},
    ]

    if not override_name_present or not override_name_count_nonzero:
        return {
            "format": FORMAT,
            "version": 2,
            "operation": "tracking-camera-override-resolution",
            "status": "no-override-name",
            "actions": actions,
        }

    if not service_available:
        return {
            "format": FORMAT,
            "version": 2,
            "operation": "tracking-camera-override-resolution",
            "status": "service-unavailable",
            "actions": actions + [
                {"action": "FUN_0080bfb0"},
                {"action": "FUN_0080b8e0"},
            ],
        }

    for ordinal, candidate in enumerate(candidates):
        has_rtti = bool(candidate.get("contains_rtti_0xc25fb8", False))
        compare_matches = bool(candidate.get("name_0x60_matches_override_0xd4", False))
        row = {
            "ordinal": ordinal,
            "contains_rtti_0xc25fb8": has_rtti,
            "name_0x60_matches_override_0xd4": compare_matches,
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
                    "candidate_name": "candidate byte +0x60",
                    "override_name": "TrackingCamera byte +0xd4 (OverridedBy)",
                },
                "result": compare_matches,
            })
        if has_rtti and compare_matches:
            row["actions"].append({
                "action": "FUN_00812970",
                "argument": f"candidate[{ordinal}]",
                "destination": "TrackingCamera byte +0xe8",
            })
            actions.append(row)
            return {
                "format": FORMAT,
                "version": 2,
                "operation": "tracking-camera-override-resolution",
                "status": "attached",
                "selected_candidate": ordinal,
                "actions": actions,
                "candidate_trace": row,
                "semantic_classification": "camera-to-camera override linkage",
                "not_vehicle_target_proof": True,
                "evidence": {
                    "function": "FUN_0081f070",
                    "service_root": "FUN_0080bfb0",
                    "service_view": "FUN_0080b8e0",
                    "rtti_marker": "DAT_00c25fb8",
                    "compare": "FUN_00408210(candidate byte +0x60, this byte +0xd4)",
                    "attach": "FUN_00812970 -> this byte +0xe8",
                    "reflection_target_field": "CTrackingCamData byte +0x78",
                    "reflection_override_field": "CTrackingCamData byte +0xd4 (OverridedBy)",
                },
            }
        actions.append(row)

    return {
        "format": FORMAT,
        "version": 2,
        "operation": "tracking-camera-override-resolution",
        "status": "not-found",
        "actions": actions,
        "semantic_classification": "camera-to-camera override linkage",
        "not_vehicle_target_proof": True,
        "evidence": {
            "function": "FUN_0081f070",
            "rtti_marker": "DAT_00c25fb8",
            "reflection_target_field": "CTrackingCamData byte +0x78",
            "reflection_override_field": "CTrackingCamData byte +0xd4 (OverridedBy)",
        },
    }


def describe_tracking_target_acquisition(
    *,
    target_handle_present: bool,
    target_handle_count_nonzero: bool,
    service_available: bool,
    candidates: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Compatibility wrapper for the formerly misnamed override scan."""
    normalized = []
    for candidate in candidates:
        row = dict(candidate)
        if "name_0x60_matches_override_0xd4" not in row:
            row["name_0x60_matches_override_0xd4"] = bool(
                row.get("field_0x18_matches_target", False)
            )
        normalized.append(row)
    result = describe_tracking_override_resolution(
        override_name_present=target_handle_present,
        override_name_count_nonzero=target_handle_count_nonzero,
        service_available=service_available,
        candidates=normalized,
    )
    result["compatibility_wrapper"] = "describe_tracking_target_acquisition"
    return result


def describe_tracking_camera_lifecycle_reset() -> dict[str, Any]:
    """Trace FUN_0081f160's lifecycle reset ordering."""
    return {
        "format": FORMAT,
        "version": 2,
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
