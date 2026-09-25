"""Evidence-backed camera-view profile selector/state loader.

Recovered from FUN_00812ed0, FUN_0081c020, FUN_0081c050, FUN_0081c090,
FUN_0081c920, FUN_0081caa0, and FUN_0081cb60.

The source exposes a concrete camera profile object used by the runtime camera
view. This module preserves exact offsets, selector predicates, and update
ordering while leaving generic UI/group/vtable helpers opaque.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

FORMAT = "SHIFT.CameraViewProfileRuntime/1"


@dataclass(frozen=True)
class CameraProfile:
    profile_id: int
    fov_bits_or_value: Any
    aspect_ratio_bits_or_value: Any
    near_z_bits_or_value: Any
    far_z_bits_or_value: Any
    service_value: Any
    impact_positional_extents: Any = None
    impact_orientational_extents: Any = None
    speed_positional_extents: Any = None
    speed_orientational_extents: Any = None
    hide_car: bool = False
    hide_car_rear_look: bool = False
    render_cockpit: bool = False
    allow_cycle: bool = False


@dataclass(frozen=True)
class CameraViewState:
    selector_profile_id: int = -1  # +0xc0
    selected_profile_id: int = -1  # +0xc4
    selected_profile_object: Any = None  # +0x80
    last_service_profile_id: int = 0  # +0xc8
    last_fallback_profile_id: int = -1  # +0xcc
    render_cockpit: bool = False  # +0xd2


def resolve_camera_data_object(camera_data: Mapping[str, Any]) -> dict[str, Any]:
    """Reproduce FUN_00812ed0's one-level e8 forwarding."""
    root = camera_data.get("plus_0x64")
    if root is None:
        return {
            "format": FORMAT,
            "version": 1,
            "resolved": None,
            "status": "null-root",
            "evidence": {
                "function": "FUN_00812ed0",
                "root": "+0x64",
            },
        }

    nested = root.get("plus_0xe8")
    resolved = nested if nested not in (None, 0) else root
    return {
        "format": FORMAT,
        "version": 1,
        "resolved": resolved,
        "status": "nested-forward" if nested not in (None, 0) else "root",
        "evidence": {
            "function": "FUN_00812ed0",
            "root": "+0x64",
            "forward": "+0xe8",
        },
    }


def service_profile_matches(
    *,
    service_current_id: int,
    selected_profile_id: int,
) -> bool:
    """Reproduce FUN_0081c020."""
    service_id = int(service_current_id)
    profile_id = int(selected_profile_id)
    return service_id >= 0 and service_id == profile_id


def service_profile_differs(
    *,
    service_current_id: int,
    selected_profile_id: int,
) -> bool:
    """Reproduce the return condition of FUN_0081c050."""
    service_id = int(service_current_id)
    profile_id = int(selected_profile_id)
    if service_id == -1 and profile_id == -1:
        return False
    return profile_id != service_id


def normalized_profile_time(
    *,
    sample_time: float,
    profile_start: float,
    profile_end: float,
) -> float:
    """Reproduce FUN_0081c090's clamp to [0,1] for finite ordered endpoints."""
    value = (float(sample_time) - float(profile_start)) / (
        float(profile_end) - float(profile_start)
    )
    if value < 0.0 or value == 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def camera_profile_catalog() -> dict[str, Any]:
    """Return exact profile fields consumed by FUN_0081c920 and its registration."""
    return {
        "format": FORMAT,
        "version": 1,
        "fields": [
            {"name": "OriRate", "offset": 0x10, "type": "vec3"},
            {"name": "VelocityOriRatio", "offset": 0x1C, "type": "f32"},
            {"name": "TargetPertubationScale", "offset": 0x20, "type": "f32"},
            {"name": "RearPos", "offset": 0x28, "type": "vec3"},
            {"name": "PosOffset", "offset": 0x2C, "type": "vec3"},
            {"name": "OriOffset", "offset": 0x38, "type": "vec3"},
            {"name": "HeadPhysicsScale", "offset": 0x44, "type": "vec3"},
            {"name": "Radius", "offset": 0x50, "type": "f32"},
            {"name": "FOV", "offset": 0x54, "type": "f32"},
            {"name": "FOVMax", "offset": 0x58, "type": "f32"},
            {"name": "FOVMaxSpeedMPH", "offset": 0x5C, "type": "f32"},
            {"name": "AspectRatio", "offset": 0x60, "type": "f32"},
            {"name": "NearZ", "offset": 0x64, "type": "f32"},
            {"name": "FarZ", "offset": 0x68, "type": "f32"},
            {"name": "ImpactShakePositionalExtents", "offset": 0x6C, "type": "vec3"},
            {"name": "ImpactShakeOrientationalExtents", "offset": 0x78, "type": "vec3"},
            {"name": "ImpactShakeFrequencyFactor", "offset": 0x84, "type": "f32"},
            {"name": "SpeedShakePositionalExtents", "offset": 0x88, "type": "vec3"},
            {"name": "SpeedShakeOrientationalExtents", "offset": 0x94, "type": "vec3"},
            {"name": "SpeedShakeFrequencyFactor", "offset": 0xA0, "type": "f32"},
            {"name": "SpeedShakeMinSpeed", "offset": 0xA4, "type": "f32"},
            {"name": "SpeedShakeMaxSpeed", "offset": 0xA8, "type": "f32"},
            {"name": "HideCar", "offset": 0xAC, "type": "bool"},
            {"name": "HideCarRearLook", "offset": 0xAD, "type": "bool"},
            {"name": "RenderCockpit", "offset": 0xAE, "type": "bool"},
            {"name": "AllowCycle", "offset": 0xAF, "type": "bool"},
        ],
        "evidence": {
            "registration": "FUN_008229e0",
            "loader": "FUN_0081c920",
        },
    }


def load_camera_profile(
    state: CameraViewState,
    *,
    requested_profile_id: int,
    resolved_profile: CameraProfile | None,
    suppress_history_update: bool = False,
    manager_group: Any = None,
    group_id: int = -1,
    service_current_id: int = -1,
) -> tuple[CameraViewState, dict[str, Any]]:
    """Trace FUN_0081c920's field copies and conditional history updates."""
    profile_id = (
        int(requested_profile_id)
        if int(requested_profile_id) != -2
        else int(state.selected_profile_id)
    )
    if resolved_profile is None:
        return CameraViewState(
            selector_profile_id=state.selector_profile_id,
            selected_profile_id=profile_id,
            selected_profile_object=None,
            last_service_profile_id=state.last_service_profile_id,
            last_fallback_profile_id=state.last_fallback_profile_id,
            render_cockpit=state.render_cockpit,
        ), {
            "format": FORMAT,
            "version": 1,
            "status": "profile-not-found",
            "selected_profile_id": profile_id,
            "actions": [
                {"action": "+0xc4 = requested profile id" if int(requested_profile_id) != -2 else "keep +0xc4"},
                {"action": "FUN_0080b8d0(manager, +0xc4)"},
                {"action": "return"},
            ],
            "evidence": {
                "function": "FUN_0081c920",
                "lookup": "FUN_0080b8d0",
            },
        }

    actions: list[dict[str, Any]] = [
        {"action": "write +0xc4", "value": profile_id},
        {"action": "write +0x80", "value": resolved_profile.profile_id},
        {"action": "copy +0x54 -> +0x34", "field": "FOV", "value": resolved_profile.fov_bits_or_value},
        {"action": "copy +0x60 -> +0x38", "field": "AspectRatio", "value": resolved_profile.aspect_ratio_bits_or_value},
        {"action": "copy +0x64 -> +0x3c", "field": "NearZ", "value": resolved_profile.near_z_bits_or_value},
        {"action": "copy +0x68 -> +0x40", "field": "FarZ", "value": resolved_profile.far_z_bits_or_value},
        {"action": "copy +0x50 -> +0xd4", "field": "Radius", "value": resolved_profile.service_value},
        {"action": "copy +0x6c -> +0x12c", "field": "ImpactShakePositionalExtents"},
        {"action": "copy +0x78 -> +0x138", "field": "ImpactShakeOrientationalExtents"},
        {"action": "copy +0x88 -> +0xd8", "field": "SpeedShakePositionalExtents"},
        {"action": "copy +0x94 -> +0xe4", "field": "SpeedShakeOrientationalExtents"},
        {
            "action": "FUN_0080ce10",
            "arguments": {"group": group_id, "value": int(resolved_profile.render_cockpit)},
        },
        {
            "action": "FUN_0080cdf0",
            "arguments": {"group": group_id, "value": not resolved_profile.hide_car},
        },
        {"action": "write +0xd1", "value": 1},
    ]

    service_history = state.last_service_profile_id
    fallback_history = state.last_fallback_profile_id
    if not suppress_history_update:
        if (
            service_profile_matches(
                service_current_id=int(service_current_id),
                selected_profile_id=profile_id,
            )
            and resolved_profile.hide_car_rear_look
        ):
            service_history = profile_id
            actions.append({"action": "write +0xc8", "value": profile_id})
        elif service_profile_differs(
            service_current_id=int(service_current_id),
            selected_profile_id=profile_id,
        ):
            fallback_history = profile_id
            actions.append({"action": "write +0xcc", "value": profile_id})
        actions.append({"action": "zero +0x84/+0x88/+0x8c"})

    if resolved_profile.render_cockpit:
        actions.append({
            "action": "FUN_0080cdf0",
            "arguments": {
                "group": group_id,
                "value": not bool(resolved_profile.hide_car_rear_look),
            },
        })

    new_state = CameraViewState(
        selected_profile_id=profile_id,
        selected_profile_object=resolved_profile,
        last_service_profile_id=service_history,
        last_fallback_profile_id=fallback_history,
        render_cockpit=resolved_profile.render_cockpit,
    )
    return new_state, {
        "format": FORMAT,
        "version": 1,
        "status": "loaded",
        "selected_profile_id": profile_id,
        "actions": actions,
        "evidence": {
            "function": "FUN_0081c920",
            "profile_lookup": "FUN_0080b8d0",
            "profile_fov": "+0x54",
            "profile_aspect": "+0x60",
            "profile_nearz": "+0x64",
            "profile_farz": "+0x68",
            "profile_service_value": "+0x50",
            "impact_vectors": ["+0x6c", "+0x78"],
            "speed_vectors": ["+0x88", "+0x94"],
            "flags": ["+0xac", "+0xad", "+0xae", "+0xaf"],
            "selected_id": "+0xc4",
            "selected_object": "+0x80",
            "history_a": "+0xc8",
            "history_b": "+0xcc",
            "loaded_marker": "+0xd1",
        },
        "limitations": [
            "FUN_0080b8d0 profile lookup is retained as an opaque manager lookup",
            "FUN_0080ce10/FUN_0080cdf0 semantics are retained as group helpers",
        ],
    }


def select_camera_profile(
    state: CameraViewState,
    *,
    profile_id: int,
    profile: CameraProfile | None,
) -> tuple[CameraViewState, dict[str, Any]]:
    """Trace FUN_0081caa0's history-aware profile selection."""
    if service_profile_matches(
        service_current_id=state.selected_profile_id,
        selected_profile_id=int(profile_id),
    ):
        history = state.last_service_profile_id
        reason = "service-current-profile"
    elif service_profile_differs(
        service_current_id=state.selected_profile_id,
        selected_profile_id=int(profile_id),
    ):
        history = state.last_fallback_profile_id
        reason = "fallback-profile"
    else:
        history = state.last_service_profile_id
        reason = "no-service-id-difference"

    loaded, result = load_camera_profile(
        state,
        requested_profile_id=int(history),
        resolved_profile=profile,
        suppress_history_update=True,
        group_id=int(profile_id),
    )
    return loaded, {
        "format": FORMAT,
        "version": 1,
        "status": "selected",
        "selector_profile_id": int(profile_id),
        "selector_reason": reason,
        "history_value_used": int(history),
        "actions": [
            {
                "action": "write +0xc0",
                "value": int(profile_id),
            },
            {
                "action": "FUN_0081c920",
                "profile_id": int(history),
            },
            *result["actions"],
        ],
        "evidence": {
            "function": "FUN_0081caa0",
            "selector_field": "+0xc0",
            "service-match": "FUN_0081c020",
            "service-diff": "FUN_0081c050",
        },
    }


def update_cockpit_flag(
    *,
    current_flag: int,
    new_flag: int,
    manager_swap_in_progress: bool,
) -> dict[str, Any]:
    """Trace FUN_0081cb60."""
    old = int(current_flag) & 0xFF
    new = int(new_flag) & 0xFF
    if old == new:
        return {
            "format": FORMAT,
            "version": 1,
            "status": "unchanged",
            "actions": [],
            "evidence": {"function": "FUN_0081cb60", "flag": "+0xd2"},
        }
    if manager_swap_in_progress:
        return {
            "format": FORMAT,
            "version": 1,
            "status": "blocked-by-swap",
            "actions": [],
            "evidence": {"function": "FUN_0081cb60", "guard": "manager +0x269c"},
        }
    return {
        "format": FORMAT,
        "version": 1,
        "status": "updated",
        "value": new,
        "actions": [
            {"action": "write +0xd2", "value": new},
            {"action": "FUN_0081c920(-2,0)"},
            {"action": "write +0xd1", "value": 1},
            {"action": "FUN_0080cd40(manager)", "meaning": "camera buffer update boundary"},
        ],
        "evidence": {
            "function": "FUN_0081cb60",
            "guard": "manager +0x269c == 0",
            "flag": "+0xd2",
            "reload": "FUN_0081c920(-2,0)",
        },
    }
