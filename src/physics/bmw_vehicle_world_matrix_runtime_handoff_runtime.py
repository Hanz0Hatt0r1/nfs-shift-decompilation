"""Reference composition of Phase 703 identity admission and Phase 704 world matrix."""
from __future__ import annotations

from typing import Any

from bmw_body0_vhf_world_matrix_composition_runtime import (
    ProvenBody0BindFrame,
    ProvenVhfBindFrame,
    compose,
)
from global_vehicle_body_owner_selection_runtime import (
    GlobalVehicleBodyOwnerIdentityHandoff,
    build_selection,
)

FORMAT = "SHIFT.NativeBMWVehicleWorldMatrixRuntimeHandoff/1"


def build_handoff(
    *,
    identity: GlobalVehicleBodyOwnerIdentityHandoff,
    body_index: int,
    origin: tuple[float, float, float],
    basis: tuple[float, float, float, float, float, float, float, float, float],
    vhf_bind: ProvenVhfBindFrame,
    body0_bind: ProvenBody0BindFrame,
) -> dict[str, Any]:
    selection = build_selection(identity)
    if int(selection["body_index"]) != body_index:
        raise ValueError("selected BODY identity does not match supplied persistent pose")
    composition = compose(
        body_index=body_index,
        origin=origin,
        basis=basis,
        vhf_bind=vhf_bind,
        body0_bind=body0_bind,
    )
    return {
        "body_index": body_index,
        "body0_runtime_row": composition["body0_runtime_row"],
        "vehicle_world_matrix": composition["vehicle_world_matrix"],
    }


def contract() -> dict[str, object]:
    return {
        "format": FORMAT,
        "phase703_identity_admission_reused": True,
        "phase700_runtime_pose_handoff_reused_by_native": True,
        "phase704_composition_reused": True,
        "current_retail_identity_ready": False,
        "current_retail_BODY0_bind_ready": False,
        "current_retail_world_matrix_ready": False,
        "read_only_runtime_handoff": True,
        "phase646_matrix_output": True,
        "live_vulkan_buffer_mutation_enabled": False,
        "fixed_step_auto_schedule": False,
        "original_game_executed": False,
        "new_runtime_capture_required": False,
    }
