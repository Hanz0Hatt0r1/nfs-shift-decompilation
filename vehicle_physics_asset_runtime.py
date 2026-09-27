"""Evidence-backed reconstruction of the vehicle-physics asset root registry.

FUN_0074ec30 constructs seven runtime-relative roots from the Physics Manager
vehicle/physics path fields. FUN_0074d640 then consumes the Chassis root when
building the participant .cdf path.
"""
from __future__ import annotations

from typing import Any

FORMAT = "SHIFT.VehiclePhysicsAssetRuntime/1"

ROOTS = (
    ("chassis", "Chassis/"),
    ("collision", "Collision/"),
    ("engines", "Engines/"),
    ("gearbox", "GearBox/"),
    ("suspension", "Suspension/"),
    ("upgrades", "Upgrades/"),
    ("vehicles", "Vehicles/"),
)


def build_vehicle_physics_roots(base: str = "vehicles/Physics/") -> dict[str, str]:
    if not base:
        raise ValueError("base must be non-empty")
    return {name: f"{base}{suffix}" for name, suffix in ROOTS}


def build_vehicle_physics_contract() -> dict[str, Any]:
    roots = build_vehicle_physics_roots()
    return {
        "format": FORMAT,
        "version": 1,
        "source": ".\\Source\\System\\PhysicsParticipant.cpp",
        "root_builder": "FUN_0074ec30",
        "base_components": {
            "manager_field_0x378": "vehicles/",
            "manager_field_0x37c": "Physics/",
        },
        "roots": roots,
        "consumers": {
            "chassis": {
                "function": "FUN_0074d640",
                "use": "build participant CDF path",
                "suffix": ".cdf",
                "field_offset": 0x04,
            },
            "collision": {"status": "registered runtime root"},
            "engines": {"status": "registered runtime root"},
            "gearbox": {"status": "registered runtime root"},
            "suspension": {"status": "registered runtime root"},
            "upgrades": {"status": "registered runtime root"},
            "vehicles": {"status": "registered runtime root"},
        },
        "status": "path-registry-reconstructed",
        "unknowns": [
            "which concrete runtime loaders consume each non-Chassis root",
            "filename/key schema below each root",
            "whether root names differ for DLC/patch data",
        ],
    }
