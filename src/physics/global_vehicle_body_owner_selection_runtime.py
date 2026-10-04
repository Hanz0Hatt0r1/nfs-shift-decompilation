"""Reference adapter from Process 1 global BODY-owner identity to Phase 698/700."""
from __future__ import annotations
from dataclasses import dataclass

FORMAT = "SHIFT.NativeGlobalVehicleBodyOwnerSelection/1"
PROCESS1_FORMAT = "SHIFT.GlobalVehicleBodyOwnerIdentity/1"
RETAIL_GLOBAL_VEHICLE_ADDRESS = 0x00C13700
RETAIL_BODY_OWNER_POINTER_FIELD_OFFSET = 0x339C
RETAIL_BMW_CHASSIS_BODY_INDEX = 0


@dataclass(frozen=True)
class GlobalVehicleBodyOwnerIdentityHandoff:
    outer_receiver_to_body_owner_continuity_proven: bool = False
    vehicle_body_selection_ready: bool = False
    selected_body_index: int | None = None
    phase698_positive_selection_admissible: bool = False
    phase700_runtime_handoff_admissible: bool = False
    phase703_update_child_equality_gate_required: bool = False
    phase703_gate_rewrite_ready: bool = False


def blocked_identity_fixture() -> GlobalVehicleBodyOwnerIdentityHandoff:
    """Negative fixture only; this is no longer the current retail state."""
    return GlobalVehicleBodyOwnerIdentityHandoff()


def blocked_current_retail_handoff() -> GlobalVehicleBodyOwnerIdentityHandoff:
    """Compatibility alias retained for older negative regressions."""
    return blocked_identity_fixture()


def retail_positive_handoff() -> GlobalVehicleBodyOwnerIdentityHandoff:
    """Process 1 #1208 committed retail SHIFT.GlobalVehicleBodyOwnerIdentity/1."""
    return GlobalVehicleBodyOwnerIdentityHandoff(
        outer_receiver_to_body_owner_continuity_proven=True,
        vehicle_body_selection_ready=True,
        selected_body_index=RETAIL_BMW_CHASSIS_BODY_INDEX,
        phase698_positive_selection_admissible=True,
        phase700_runtime_handoff_admissible=True,
        phase703_update_child_equality_gate_required=False,
        phase703_gate_rewrite_ready=True,
    )


def build_selection(handoff: GlobalVehicleBodyOwnerIdentityHandoff) -> dict[str, object]:
    if handoff.phase703_update_child_equality_gate_required:
        raise ValueError("obsolete update-child equality gate was reintroduced")
    ready = handoff.outer_receiver_to_body_owner_continuity_proven
    if not (handoff.vehicle_body_selection_ready == ready
            and handoff.phase698_positive_selection_admissible == ready
            and handoff.phase700_runtime_handoff_admissible == ready
            and handoff.phase703_gate_rewrite_ready == ready):
        raise ValueError("global vehicle BODY-owner identity readiness flags disagree")
    if not ready:
        if handoff.selected_body_index is not None:
            raise ValueError("blocked global vehicle BODY-owner identity preclaims a BODY index")
        raise ValueError("global vehicle BODY-owner identity is not retail-ready")
    if handoff.selected_body_index != RETAIL_BMW_CHASSIS_BODY_INDEX:
        raise ValueError("positive global vehicle BODY-owner identity must select BODY 0")
    return {"selection_proven": True, "body_index": RETAIL_BMW_CHASSIS_BODY_INDEX}


def synthetic_positive_handoff() -> GlobalVehicleBodyOwnerIdentityHandoff:
    """Synthetic positive fixture retained only for malformed-input tests."""
    return GlobalVehicleBodyOwnerIdentityHandoff(
        outer_receiver_to_body_owner_continuity_proven=True,
        vehicle_body_selection_ready=True,
        selected_body_index=0,
        phase698_positive_selection_admissible=True,
        phase700_runtime_handoff_admissible=True,
        phase703_gate_rewrite_ready=True,
    )


def contract() -> dict[str, object]:
    return {
        "format": FORMAT,
        "process1_contract": PROCESS1_FORMAT,
        "current_retail_global_vehicle_BODY_owner_identity_ready": True,
        "current_retail_selected_BODY_index": RETAIL_BMW_CHASSIS_BODY_INDEX,
        "retail_global_vehicle_address": RETAIL_GLOBAL_VEHICLE_ADDRESS,
        "retail_BODY_owner_pointer_field_offset": RETAIL_BODY_OWNER_POINTER_FIELD_OFFSET,
        "BODY_array_owner_is_global_vehicle_base": False,
        "BODY_array_owner_pointer_loaded_from_global_vehicle_base": True,
        "retail_BMW_chassis_BODY_index": RETAIL_BMW_CHASSIS_BODY_INDEX,
        "obsolete_update_child_equality_gate_required": False,
        "synthetic_positive_identity_is_retail_proof": False,
        "phase698_selector_reused": True,
        "phase700_runtime_handoff_reused": True,
        "phase645_VHF_bind_transform_is_dynamic_physics_pose": False,
        "phase646_dynamic_transform_transport_available": True,
        "phase649_persistent_vulkan_upload_available": True,
        "BODY0_bind_frame_proof_ready": False,
        "fixed_step_auto_schedule": False,
        "original_game_executed": False,
        "new_runtime_capture_required": False,
    }
