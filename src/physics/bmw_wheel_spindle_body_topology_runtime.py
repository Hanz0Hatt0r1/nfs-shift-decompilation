"""Reference contract for the Process 1 v2 BMW wheel/spindle BODY handoff."""
from __future__ import annotations

from dataclasses import dataclass

FORMAT = "SHIFT.NativeBMWWheelSpindleBodyTopology/1"
BODY_COUNT = 11
WHEEL_BODY_INDICES = (3, 4, 7, 8)
SPINDLE_BODY_INDICES = (1, 2, 5, 6)
WHEEL_NAMES = ("fl_wheel", "fr_wheel", "rl_wheel", "rr_wheel")
SPINDLE_NAMES = ("fl_spindle", "fr_spindle", "rl_spindle", "rr_spindle")


@dataclass(frozen=True)
class BmwWheelSpindleBodyTopology:
    body_count: int = BODY_COUNT
    wheel_body_indices: tuple[int, int, int, int] = WHEEL_BODY_INDICES
    spindle_body_indices: tuple[int, int, int, int] = SPINDLE_BODY_INDICES
    wheel_spindle_body_indices_ready: bool = True
    rear_axle_body_index_ready: bool = False
    main_chassis_body_selected: bool = False


@dataclass(frozen=True)
class ProvenRearAxleBodyIndex:
    proven: bool
    body_index: int


def retail_topology() -> BmwWheelSpindleBodyTopology:
    return BmwWheelSpindleBodyTopology()


def complete_constraint_body_map(
    topology: BmwWheelSpindleBodyTopology,
    rear_axle: ProvenRearAxleBodyIndex,
) -> dict[str, object]:
    if topology != retail_topology():
        raise ValueError("BMW wheel/spindle topology drifted from the proven retail frontier")
    if not rear_axle.proven:
        raise ValueError("BMW vehicle constraint map requires proven rear-axle BODY identity")
    if rear_axle.body_index < 0 or rear_axle.body_index >= topology.body_count:
        raise ValueError("rear-axle BODY index is outside the exact retail SDF domain")
    return {
        "wheel_body_indices": topology.wheel_body_indices,
        "spindle_body_indices": topology.spindle_body_indices,
        "rear_axle_body_index": rear_axle.body_index,
    }


def contract() -> dict[str, object]:
    topology = retail_topology()
    return {
        "format": FORMAT,
        "retail_sdf_body_count": topology.body_count,
        "slot_order": ["FL", "FR", "RL", "RR"],
        "wheel_names": list(WHEEL_NAMES),
        "wheel_body_indices": list(topology.wheel_body_indices),
        "spindle_names": list(SPINDLE_NAMES),
        "spindle_body_indices": list(topology.spindle_body_indices),
        "wheel_spindle_body_indices_ready": True,
        "rear_axle_body_index_ready": False,
        "main_chassis_body_selected": False,
        "full_vehicle_constraint_body_map_ready": False,
        "phase698_positive_selection_admissible": False,
        "distinct_body_indices_assumed": False,
        "sdf_name_implies_chassis_identity": False,
        "original_game_executed": False,
        "new_runtime_capture_required": False,
    }


__all__ = [
    "FORMAT",
    "BODY_COUNT",
    "WHEEL_BODY_INDICES",
    "SPINDLE_BODY_INDICES",
    "BmwWheelSpindleBodyTopology",
    "ProvenRearAxleBodyIndex",
    "retail_topology",
    "complete_constraint_body_map",
    "contract",
]
