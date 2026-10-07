"""Evidence-backed outer numeric kernel for FUN_007675f0."""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite, sqrt

FORMAT = "SHIFT.PhysicsHelper675F0Runtime/1"
FUNCTION = "FUN_007675f0"
SOURCE_FILE = "SHIFT.exe.c"
SOURCE_LINE = 759784

DISTANCE_LIMIT = 200.0
DISTANCE_GATE_MIN = 5.0
SPEED_GATE_MIN = 1.0
SPEED_FACTOR_OFFSET = 13.888889
SPEED_FACTOR_SCALE = 5.5555553
GAP_OFFSET = 1.5
GAP_SCALE = 2.5
FORCE_MULTIPLIER = 1.5
FORCE_NEGATIVE_SCALE = -0.05

@dataclass(frozen=True)
class Vec3:
    x: float
    y: float
    z: float
    def __post_init__(self):
        if not all(isfinite(float(v)) for v in (self.x,self.y,self.z)):
            raise ValueError("vector components must be finite")
    def as_tuple(self): return (float(self.x),float(self.y),float(self.z))

def planar_length_xz(vector: Vec3) -> float:
    return sqrt(vector.x*vector.x + vector.z*vector.z)

def normalize_planar(vector: Vec3) -> Vec3:
    length = planar_length_xz(vector)
    if length == 0.0:
        raise ValueError("cannot normalize a zero XZ vector")
    inv = 1.0/length
    return Vec3(vector.x*inv,0.0,vector.z*inv)

def lowpass_distance(previous: float, distance: float, cap: float, response: float = 0.5) -> float:
    for value,name in ((previous,"previous"),(distance,"distance"),(cap,"cap"),(response,"response")):
        if not isfinite(float(value)): raise ValueError(f"{name} must be finite")
    return (distance-previous) * (response/(cap+response)) + previous

def update_distance_state(previous: float, distance: float, cap: float) -> float:
    return lowpass_distance(previous,distance,cap,0.5) if distance <= DISTANCE_LIMIT else DISTANCE_LIMIT

def speed_factor(speed_x: float, speed_z: float) -> tuple[float,float]:
    speed = sqrt(speed_x*speed_x + speed_z*speed_z)
    raw = (speed-SPEED_FACTOR_OFFSET)/SPEED_FACTOR_SCALE
    return speed, min(1.0,max(0.0,raw))

def contact_gate(distance: float, speed: float) -> bool:
    return distance < DISTANCE_LIMIT and distance > DISTANCE_GATE_MIN and speed > SPEED_GATE_MIN

def gap_factor(filtered_distance_state: float, surface_scalar: float) -> float:
    """Machine-correct gap: use committed +0x4080 state, not raw distance."""
    gap = filtered_distance_state-(surface_scalar-GAP_OFFSET)
    if gap <= 0.0: return 0.0
    if gap >= GAP_SCALE: return 1.0
    return gap/GAP_SCALE

def contact_force_scalar(base_scalar: float, projected_scalar: float, gap_factor_value: float,
                         alignment_scalar: float, speed_factor_value: float) -> float:
    return ((base_scalar*FORCE_MULTIPLIER-projected_scalar)
            * (2.0-gap_factor_value) * gap_factor_value
            * alignment_scalar * speed_factor_value)

def submission_scales(force_scalar: float, param_3: float) -> tuple[float,float]:
    first = force_scalar*param_3
    return first, first*FORCE_NEGATIVE_SCALE

def build_contract():
    return {
        "format": FORMAT, "version": 1, "function": FUNCTION,
        "source": {"file": SOURCE_FILE, "line": SOURCE_LINE},
        "distance": {
            "construction": "sqrt(dx^2 + dz^2)", "limit": 200.0,
            "state_update": "FUN_00783a30(previous, distance, body_field+0xa0, 0.5) when distance <= 200; else 200",
        },
        "speed": {
            "components": ["body + 0x78","body + 0x88"],
            "magnitude": "sqrt(vx^2 + vz^2)",
            "factor": "clamp((speed - 13.888889) / 5.5555553, 0, 1)",
        },
        "gate": "distance < 200 && distance > 5 && speed > 1",
        "force_scalar": {
            "gap": "filtered_distance_state - (surface_scalar - 1.5)",
            "machine_correction": "PC 0x00767937 reloads the value stored at HDVehicle+0x4080 before gap formation",
            "shape": "gap >= 2.5 ? 1 : gap / 2.5",
            "formula": "(base_scalar*1.5 - projected_scalar) * (2-shape) * shape * alignment * speed_factor",
        },
        "submission": {"first_scale": "force_scalar * param_3", "second_scale": "force_scalar * param_3 * -0.05",
                      "consumer": "FUN_007ba9e0", "calls": 2},
        "unresolved": [
            "semantic names and physical units of body/node fields",
            "FUN_00759210 node refresh/provider implementation behind HDVehicle+0x120",
            "internal semantics of FUN_00759c90/FUN_007551e0/FUN_00755340 in this caller",
        ],
    }

__all__=["FORMAT","FUNCTION","SOURCE_FILE","SOURCE_LINE","DISTANCE_LIMIT","DISTANCE_GATE_MIN",
         "SPEED_GATE_MIN","SPEED_FACTOR_OFFSET","SPEED_FACTOR_SCALE","GAP_OFFSET","GAP_SCALE",
         "FORCE_MULTIPLIER","FORCE_NEGATIVE_SCALE","Vec3","planar_length_xz","normalize_planar",
         "lowpass_distance","update_distance_state","speed_factor","contact_gate","gap_factor",
         "contact_force_scalar","submission_scales","build_contract"]
