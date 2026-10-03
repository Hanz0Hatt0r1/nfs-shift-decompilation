"""Reference gate from proven BMW chassis topology to Phase 698 identity selection."""
from __future__ import annotations

from dataclasses import dataclass

FORMAT = "SHIFT.NativeBMWChassisBodySelectionGate/1"
BODY_COUNT = 11
MAIN_CHASSIS_BODY_INDEX = 0


@dataclass(frozen=True)
class BmwChassisTopology:
    body_count: int = BODY_COUNT
    wheel_spindle_body_indices_ready: bool = True
    main_chassis_body_selected: bool = True
    main_chassis_body_index: int = MAIN_CHASSIS_BODY_INDEX


@dataclass(frozen=True)
class UpdateChildVehicleSolverBaseContinuity:
    proven: bool


def build_selection(
    topology: BmwChassisTopology,
    continuity: UpdateChildVehicleSolverBaseContinuity,
) -> dict[str, object]:
    if topology != BmwChassisTopology():
        raise ValueError("BMW chassis selection gate requires the proven retail BODY topology")
    if not continuity.proven:
        raise ValueError(
            "BMW chassis selection gate requires proven update-child to vehicle solver-base continuity"
        )
    return {
        "selection_proven": True,
        "body_index": topology.main_chassis_body_index,
    }


def contract() -> dict[str, object]:
    return {
        "format": FORMAT,
        "main_chassis_body_selected": True,
        "main_chassis_body_index": MAIN_CHASSIS_BODY_INDEX,
        "current_update_child_to_vehicle_solver_base_continuity_proven": False,
        "current_vehicle_body_selection_ready": False,
        "phase698_selection_emitted_without_continuity": False,
        "synthetic_positive_continuity_is_retail_proof": False,
        "rear_axle_body_index_required_for_chassis_selection": False,
        "world_transform_mapping_proven": False,
        "fixed_step_auto_schedule": False,
        "original_game_executed": False,
        "new_runtime_capture_required": False,
    }


__all__ = [
    "FORMAT",
    "BODY_COUNT",
    "MAIN_CHASSIS_BODY_INDEX",
    "BmwChassisTopology",
    "UpdateChildVehicleSolverBaseContinuity",
    "build_selection",
    "contract",
]
