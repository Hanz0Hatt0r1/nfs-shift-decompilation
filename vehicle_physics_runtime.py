"""Evidence-backed vehicle physics data/runtime boundary for Need for Speed: SHIFT."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.VehiclePhysicsDetailsRuntime/1"
SOURCE_FILE = "./Source/Vehicle/hdvehicle.cpp"
VEHICLE_LOAD_SOURCE = "./Source/Vehicle/vehload.cpp"
DOUBLE_SLASH = chr(92) * 2


@dataclass(frozen=True)
class PropertyEvidence:
    name: str
    offset: int
    registration: str
    width: str = "scalar"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "offset": self.offset,
            "offset_hex": f"0x{self.offset:x}",
            "registration": self.registration,
            "width": self.width,
        }


GENERAL_PROPERTIES = (
    PropertyEvidence("Mass", 0x1C, "FUN_007a75a0"),
    PropertyEvidence("Inertia", 0x30, "FUN_007a75a0", "vec3"),
    PropertyEvidence("DriftInertia", 0x78, "FUN_007a75a0", "vec3"),
    PropertyEvidence("CGHeight", 0x180, "FUN_007a75a0"),
    PropertyEvidence("WedgePushrod", 0xC0, "FUN_007a6a90"),
    PropertyEvidence("GraphicalOffset", 0xC8, "FUN_007a75a0", "vec3"),
    PropertyEvidence("CollisionOffset", 0x110, "FUN_007a75a0", "vec3"),
    PropertyEvidence("FuelTankPos", 0x158, "FUN_007a6a90", "vec3"),
    PropertyEvidence("FuelTankMotion", 0x170, "FUN_007a6a90", "vec2"),
    PropertyEvidence("AIMinPassesPerTick", 0x194, "FUN_007a65e0", "u32"),
    PropertyEvidence("AIRotationThreshold", 0x198, "FUN_007a6a90"),
    PropertyEvidence("AIEvenSuspension", 0x1A0, "FUN_007a6a90"),
    PropertyEvidence("AISpringRate", 0x1A8, "FUN_007a6a90"),
    PropertyEvidence("AIDamperSlow", 0x1B0, "FUN_007a6a90"),
    PropertyEvidence("AIDamperFast", 0x1B8, "FUN_007a6a90"),
    PropertyEvidence("AIDownforceZArm", 0x1C0, "FUN_007a6a90"),
    PropertyEvidence("AIDownforceBias", 0x1C8, "FUN_007a6a90"),
    PropertyEvidence("AITorqueStab", 0x1D0, "FUN_007a6a90", "vec3"),
    PropertyEvidence("Symmetric", 0x10, "FUN_007a65e0", "u32"),
)

ENGINE_PROPERTIES = (
    PropertyEvidence("FuelConsumption", 0x16D8, "FUN_007a75a0"),
    PropertyEvidence("FuelEstimate", 0x16F0, "FUN_007a6a90"),
    PropertyEvidence("EngineInertia", 0x16F8, "FUN_007a75a0"),
    PropertyEvidence("IdleThrottle", 0x1740, "FUN_007a6a90"),
    PropertyEvidence("IdleRPMLogic", 0x170C, "FUN_007a75a0", "vec2"),
    PropertyEvidence("LaunchEfficiency", 0x1748, "FUN_007a6a90"),
    PropertyEvidence("LaunchRPMLogic", 0x1750, "FUN_007a6a90", "vec2"),
    PropertyEvidence("RevLimitLogic", 0x1800, "FUN_007a6a90"),
    PropertyEvidence("RevLimitAvailable", 0x1808, "FUN_007a6470", "bool"),
    PropertyEvidence("RevLimitRange", 0x1760, "FUN_007a75a0", "vec3"),
    PropertyEvidence("RevLimitSetting", 0x17A8, "FUN_007a75a0"),
    PropertyEvidence("EngineMapRange", 0x17C0, "FUN_007a6a90", "vec3"),
    PropertyEvidence("EngineMapSetting", 0x17D8, "FUN_007a6a90"),
    PropertyEvidence("EngineBrakingMapRange", 0x17E0, "FUN_007a6a90", "vec3"),
    PropertyEvidence("EngineBrakingMapSetting", 0x17F8, "FUN_007a6a90"),
    PropertyEvidence("LifetimeEngineRPM", 0x2870, "FUN_007a75a0", "vec2"),
    PropertyEvidence("LifetimeOilTemp", 0x28A0, "FUN_007a6a90", "vec2"),
    PropertyEvidence("LifetimeAvg", 0x28B0, "FUN_007a6a90"),
    PropertyEvidence("LifetimeVar", 0x28B8, "FUN_007a6a90"),
    PropertyEvidence("EngineEmission", 0x28C0, "FUN_007a6a90", "vec3"),
    PropertyEvidence("EngineSound", 0x28D8, "FUN_007a6a90", "vec3"),
    PropertyEvidence("OnboardStarter", 0x28F1, "FUN_007a6470", "bool"),
    PropertyEvidence("StarterTiming", 0x28F8, "FUN_007a6a90", "vec3"),
    PropertyEvidence("OptimumOilTemp", 0x2810, "FUN_007a6a90"),
    PropertyEvidence("CombustionHeat", 0x2818, "FUN_007a75a0"),
    PropertyEvidence("EngineSpeedHeat", 0x282C, "FUN_007a75a0"),
    PropertyEvidence("OilMinimumCooling", 0x2840, "FUN_007a6a90"),
    PropertyEvidence("OilWaterHeatTransfer", 0x2848, "FUN_007a6a90", "vec2"),
    PropertyEvidence("WaterMinimumCooling", 0x2858, "FUN_007a6a90"),
    PropertyEvidence("RadiatorCooling", 0x2860, "FUN_007a6a90", "vec2"),
)

WHEEL_PROPERTIES = (
    PropertyEvidence("BumpTravel", 0x00, "FUN_007a6a90"),
    PropertyEvidence("ReboundTravel", 0x08, "FUN_007a6a90"),
    PropertyEvidence("BumpStopSpring", 0x10, "FUN_007a6a90"),
    PropertyEvidence("BumpStopRisingSpring", 0x18, "FUN_007a6a90"),
    PropertyEvidence("BumpStopDamper", 0x20, "FUN_007a6a90"),
    PropertyEvidence("BumpStopRisingDamper", 0x28, "FUN_007a6a90"),
    PropertyEvidence("BumpStage2", 0x30, "FUN_007a6a90"),
    PropertyEvidence("ReboundStage2", 0x38, "FUN_007a6a90"),
    PropertyEvidence("SpringMult", 0x40, "FUN_007a75a0"),
    PropertyEvidence("CGOffsetX", 0x68, "FUN_007a6a90"),
    PropertyEvidence("PushrodSpindle", 0x70, "FUN_007a6a90", "vec3"),
    PropertyEvidence("PushrodBody", 0x88, "FUN_007a6a90", "vec3"),
    PropertyEvidence("SpinInertia", 0xA0, "FUN_007a6a90"),
    PropertyEvidence("FrictionTorque", 0xB8, "FUN_007a6a90"),
    PropertyEvidence("BrakeTorque", 0xC0, "FUN_007a75a0"),
    PropertyEvidence("BrakeOptimumTemp", 0xD8, "FUN_007a6a90"),
    PropertyEvidence("BrakeFadeRange", 0xE0, "FUN_007a6a90"),
    PropertyEvidence("BrakeHeating", 0xE8, "FUN_007a75a0"),
    PropertyEvidence("BrakeCooling", 0x100, "FUN_007a6a90", "vec2"),
    PropertyEvidence("BrakeDuctCooling", 0x110, "FUN_007a6a90"),
    PropertyEvidence("BrakeDiscInertia", 0x118, "FUN_007a6a90"),
    PropertyEvidence("BrakeWearRate", 0x120, "FUN_007a6a90"),
    PropertyEvidence("BrakeFailure", 0x128, "FUN_007a6a90", "vec2"),
    PropertyEvidence("CamberRange", 0x138, "FUN_007a6a90", "vec3"),
    PropertyEvidence("CamberSetting", 0x150, "FUN_007a6a90"),
    PropertyEvidence("PressureRange", 0x158, "FUN_007a6a90", "vec3"),
    PropertyEvidence("PressureSetting", 0x170, "FUN_007a6a90"),
    PropertyEvidence("RideHeightRange", 0x178, "FUN_007a6a90", "vec3"),
    PropertyEvidence("RideHeightSetting", 0x190, "FUN_007a75a0"),
    PropertyEvidence("PackerRange", 0x1A8, "FUN_007a6a90", "vec3"),
    PropertyEvidence("PackerSetting", 0x1C0, "FUN_007a6a90"),
    PropertyEvidence("SpringRange", 0x1C8, "FUN_007a75a0", "vec3"),
    PropertyEvidence("SpringSetting", 0x210, "FUN_007a75a0"),
    PropertyEvidence("SlowBumpRange", 0x228, "FUN_007a6a90", "vec3"),
    PropertyEvidence("SlowBumpSetting", 0x240, "FUN_007a6a90"),
    PropertyEvidence("FastBumpRange", 0x248, "FUN_007a6a90", "vec3"),
    PropertyEvidence("FastBumpSetting", 0x260, "FUN_007a6a90"),
    PropertyEvidence("SlowReboundRange", 0x268, "FUN_007a6a90", "vec3"),
    PropertyEvidence("SlowReboundSetting", 0x280, "FUN_007a6a90"),
    PropertyEvidence("FastReboundRange", 0x288, "FUN_007a6a90", "vec3"),
    PropertyEvidence("FastReboundSetting", 0x2A0, "FUN_007a6a90"),
    PropertyEvidence("BrakeDiscRange", 0x2A8, "FUN_007a6a90", "vec3"),
    PropertyEvidence("BrakeDiscSetting", 0x2C0, "FUN_007a6a90"),
    PropertyEvidence("BrakePadRange", 0x2C8, "FUN_007a6a90", "vec3"),
    PropertyEvidence("BrakePadSetting", 0x2E0, "FUN_007a6a90"),
)

SUSPENSION_PROPERTIES = (
    PropertyEvidence("FixInnerSuspHeight", 0x08, "FUN_007a6a90"),
    PropertyEvidence("CorrectedInnerSuspHeight", 0x10, "FUN_007a6a90"),
    PropertyEvidence("ApplySlowToFastDampers", 0x18, "FUN_007a6470", "bool"),
    PropertyEvidence("AdjustSuspRates", 0x19, "FUN_007a6470", "bool"),
    PropertyEvidence("AlignWheels", 0x1A, "FUN_007a6470", "bool"),
    PropertyEvidence("FrontWheelTrack", 0x20, "FUN_007a6a90"),
    PropertyEvidence("RearWheelTrack", 0x28, "FUN_007a6a90"),
    PropertyEvidence("LeftWheelBase", 0x30, "FUN_007a6a90"),
    PropertyEvidence("RightWheelBase", 0x38, "FUN_007a6a90"),
    PropertyEvidence("SpringBasedAntiSway", 0x40, "FUN_007a6470", "bool"),
    PropertyEvidence("AllowNoAntiSway", 0x41, "FUN_007a6470", "bool"),
    PropertyEvidence("FrontAntiSwayBase", 0x48, "FUN_007a6a90"),
    PropertyEvidence("FrontAntiSwayRate", 0x50, "FUN_007a6a90", "vec2"),
    PropertyEvidence("RearAntiSwayBase", 0x60, "FUN_007a6a90"),
    PropertyEvidence("RearAntiSwayRate", 0x68, "FUN_007a6a90", "vec2"),
    PropertyEvidence("Front3rdBumpTravel", 0x78, "FUN_007a6a90"),
    PropertyEvidence("Front3rdReboundTravel", 0x80, "FUN_007a6a90"),
    PropertyEvidence("Front3rdBumpStopSpring", 0x88, "FUN_007a6a90"),
    PropertyEvidence("Front3rdBumpStopRisingSpring", 0x90, "FUN_007a6a90"),
    PropertyEvidence("Front3rdBumpStopDamper", 0x98, "FUN_007a6a90"),
    PropertyEvidence("Front3rdBumpStopRisingDamper", 0xA0, "FUN_007a6a90"),
    PropertyEvidence("Front3rdBumpStage2", 0xA8, "FUN_007a6a90"),
    PropertyEvidence("Front3rdReboundStage2", 0xB0, "FUN_007a6a90"),
    PropertyEvidence("Rear3rdBumpTravel", 0xB8, "FUN_007a6a90"),
    PropertyEvidence("Rear3rdReboundTravel", 0xC0, "FUN_007a6a90"),
    PropertyEvidence("Rear3rdBumpStopSpring", 0xC8, "FUN_007a6a90"),
    PropertyEvidence("Rear3rdBumpStopRisingSpring", 0xD0, "FUN_007a6a90"),
    PropertyEvidence("Rear3rdBumpStopDamper", 0xD8, "FUN_007a6a90"),
    PropertyEvidence("Rear3rdBumpStopRisingDamper", 0xE0, "FUN_007a6a90"),
    PropertyEvidence("Rear3rdBumpStage2", 0xE8, "FUN_007a6a90"),
    PropertyEvidence("Rear3rdReboundStage2", 0xF0, "FUN_007a6a90"),
    PropertyEvidence("FrontAntiSwayRange", 0xF8, "FUN_007a75a0", "vec3"),
    PropertyEvidence("FrontAntiSwaySetting", 0x368, "FUN_007a75a0"),
    PropertyEvidence("DriftFrontAntiSwaySetting", 0x390, "FUN_007a75a0"),
    PropertyEvidence("RearAntiSwayRange", 0x140, "FUN_007a75a0", "vec3"),
    PropertyEvidence("RearAntiSwaySetting", 0x37C, "FUN_007a75a0"),
    PropertyEvidence("DriftRearAntiSwaySetting", 0x3A4, "FUN_007a75a0"),
    PropertyEvidence("FrontToeInRange", 0x188, "FUN_007a6a90", "vec3"),
    PropertyEvidence("FrontToeInSetting", 0x3B8, "FUN_007a6a90"),
    PropertyEvidence("RearToeInRange", 0x1A0, "FUN_007a6a90", "vec3"),
    PropertyEvidence("RearToeInSetting", 0x3C0, "FUN_007a6a90"),
    PropertyEvidence("LeftFenderFlareRange", 0x1B8, "FUN_007a6a90", "vec3"),
    PropertyEvidence("LeftFenderFlareSetting", 0x3C8, "FUN_007a6a90"),
    PropertyEvidence("RightFenderFlareRange", 0x1D0, "FUN_007a6a90", "vec3"),
    PropertyEvidence("RightFenderFlareSetting", 0x3D0, "FUN_007a6a90"),
    PropertyEvidence("LeftCasterRange", 0x1E8, "FUN_007a6a90", "vec3"),
    PropertyEvidence("LeftCasterSetting", 0x3D8, "FUN_007a6a90"),
    PropertyEvidence("RightCasterRange", 0x200, "FUN_007a6a90", "vec3"),
    PropertyEvidence("RightCasterSetting", 0x3E0, "FUN_007a6a90"),
)

DRIVELINE_PROPERTIES = (
    PropertyEvidence("ClutchEngageRate", 0x08, "FUN_007a75a0"),
    PropertyEvidence("ClutchInertia", 0x1C, "FUN_007a75a0"),
    PropertyEvidence("ClutchTorque", 0x30, "FUN_007a75a0"),
    PropertyEvidence("ClutchWear", 0x48, "FUN_007a6a90"),
    PropertyEvidence("ClutchFriction", 0x50, "FUN_007a6a90"),
    PropertyEvidence("BaulkTorque", 0x58, "FUN_007a75a0"),
    PropertyEvidence("AllowManualOverride", 0x6C, "FUN_007a6470", "bool"),
    PropertyEvidence("SemiAutomatic", 0x6D, "FUN_007a6470", "bool"),
    PropertyEvidence("UpshiftDelay", 0x70, "FUN_007a75a0"),
    PropertyEvidence("UpshiftClutchTime", 0x84, "FUN_007a75a0"),
    PropertyEvidence("UpshiftLiftThrottle", 0x98, "FUN_007a6a90"),
    PropertyEvidence("DownshiftDelay", 0xA0, "FUN_007a75a0"),
    PropertyEvidence("DownshiftClutchTime", 0xB4, "FUN_007a75a0"),
    PropertyEvidence("DownshiftBlipThrottle", 0xC8, "FUN_007a6a90"),
    PropertyEvidence("ForwardGears", 0xD4, "FUN_007a75a0"),
    PropertyEvidence("DiffPumpTorque", 0xE8, "FUN_007a75a0"),
    PropertyEvidence("DriftDiffSpool", 0xFC, "FUN_007a6470", "bool"),
    PropertyEvidence("WheelDrive", 0x04, "FUN_007a63e0", "string"),
    PropertyEvidence("DiffPumpRange", 0x100, "FUN_007a75a0", "vec3"),
    PropertyEvidence("DiffPowerRange", 0x148, "FUN_007a6a90", "vec3"),
    PropertyEvidence("DiffCoastRange", 0x160, "FUN_007a6a90", "vec3"),
    PropertyEvidence("DiffPreloadRange", 0x178, "FUN_007a6a90", "vec3"),
    PropertyEvidence("FinalDriveSetting", 0x190, "FUN_007a75a0"),
    PropertyEvidence("ReverseSetting", 0x1A4, "FUN_007a75a0"),
    PropertyEvidence("Gear1Setting", 0x1B8, "FUN_007a75a0"),
    PropertyEvidence("Gear2Setting", 0x1CC, "FUN_007a75a0"),
    PropertyEvidence("Gear3Setting", 0x1E0, "FUN_007a75a0"),
    PropertyEvidence("Gear4Setting", 0x1F4, "FUN_007a75a0"),
    PropertyEvidence("Gear5Setting", 0x208, "FUN_007a75a0"),
    PropertyEvidence("Gear6Setting", 0x21C, "FUN_007a75a0"),
    PropertyEvidence("Gear7Setting", 0x230, "FUN_007a75a0"),
    PropertyEvidence("Gear8Setting", 0x244, "FUN_007a75a0"),
    PropertyEvidence("DiffPumpSetting", 0x258, "FUN_007a75a0"),
    PropertyEvidence("DiffPowerSetting", 0x26C, "FUN_007a75a0"),
    PropertyEvidence("DiffCoastSetting", 0x280, "FUN_007a75a0"),
    PropertyEvidence("DiffPreloadSetting", 0x294, "FUN_007a75a0"),
    PropertyEvidence("AdjustableGearsMinimumLevel", 0x2A8, "FUN_007a65e0", "u32"),
    PropertyEvidence("AdjustableFinalGearsMinimumLevel", 0x2AC, "FUN_007a65e0", "u32"),
    PropertyEvidence("AdjustableGearsRange", 0x2B0, "FUN_007a65e0", "u32"),
    PropertyEvidence("AdjustableGearsFinalRange", 0x2B4, "FUN_007a65e0", "u32"),
)

WHEEL_SECTION_TARGETS = {
    "FRONTLEFT": {"parser": "FUN_007bc770", "index": 0, "object_offset": 0x2C78},
    "FRONTRIGHT": {"parser": "FUN_007bc770", "index": 1, "object_offset": 0x2F68},
    "REARLEFT": {"parser": "FUN_007bc770", "index": 2, "object_offset": 0x3258},
    "REARRIGHT": {"parser": "FUN_007bc770", "index": 3, "object_offset": 0x3548},
}

SECTION_TARGETS = {
    "GENERAL": {"parser": "FUN_007be420", "object_offset": 0x08},
    "FRONTWING": {"parser": "FUN_007c0a20", "object_offset": 0x6A0},
    "LEFTFENDER": {"parser": "FUN_007bccc0", "index": 10, "object_offset": 0x570},
    "RIGHTFENDER": {"parser": "FUN_007bccc0", "index": 11, "object_offset": 0x608},
    "REARWING": {"parser": "FUN_007c0c00", "object_offset": 0x9A0},
    "BODYAERO": {"parser": "FUN_007c27e0", "object_offset": 0xCA0},
    "DIFFUSER": {"parser": "FUN_007bda10", "object_offset": 0xF10},
    "SUSPENSION": {"parser": "FUN_007bdb80", "object_offset": 0xFE8},
    "CONTROLS": {"parser": "FUN_007bd290", "object_offset": 0x1440},
    "ENGINE": {"special": "SpeedLimiter", "object_offset": 0x28F0},
    "DRIVELINE": {"parser": "FUN_007bcdf0", "object_offset": 0x29C0},
    **WHEEL_SECTION_TARGETS,
    "BASIC": {"special": "Downforce/Balance/Gearing", "object_offset": 0x2198},
}

POSTLOAD_CALLS = (
    "FUN_007c3920", "FUN_007bf0e0 x4", "FUN_007bf590", "FUN_007bfbe0",
    "FUN_007bdb60", "FUN_007bf790", "FUN_007bf6e0", "FUN_007c2110",
    "FUN_007bf430 x2", "FUN_007bf310 x2",
)

RPM_TORQUE_LIMIT = 127

@dataclass(frozen=True)
class RPMTorquePoint:
    """One EDF RPMTorque tuple in source-file order."""
    rpm: float
    brake: float
    throttle: float

    def as_tuple(self) -> tuple[float, float, float]:
        return (float(self.rpm), float(self.brake), float(self.throttle))


def _iter_rpm_points_with_lines(raw_text: str, points: Sequence[RPMTorquePoint]):
    index = 0
    for line_no, line in enumerate(raw_text.splitlines(), 1):
        line = line.split("//", 1)[0].strip()
        if not line or not line.startswith("RPMTorque") or "=" not in line:
            continue
        raw = line.split("=", 1)[1].strip().strip("()")
        try:
            values = [float(part.strip()) for part in raw.split(",")]
        except ValueError:
            continue
        if len(values) != 3 or index >= len(points):
            continue
        yield line_no, points[index]
        index += 1


def parse_rpm_torque_points(text: str | bytes, *, strict: bool = False) -> dict[str, Any]:
    """Parse EDF RPMTorque records using the exact source storage order.

    FUN_007c3280 calls FUN_007a6a90 with the destination pointers ordered as
    slot+2, slot, slot+1. Thus text order RPM, brake, throttle becomes
    storage order brake, throttle, RPM.
    """
    raw_text = text.decode("utf-8", "replace") if isinstance(text, bytes) else str(text)
    points: list[RPMTorquePoint] = []
    warnings: list[str] = []
    for line_no, line in enumerate(raw_text.splitlines(), 1):
        line = line.split("//", 1)[0].strip()
        if not line or not line.startswith("RPMTorque"):
            continue
        if "=" not in line:
            warnings.append(f"line:{line_no}:rpm-torque-missing-equals")
            continue
        raw = line.split("=", 1)[1].strip()
        if raw.startswith("(") and raw.endswith(")"):
            raw = raw[1:-1]
        try:
            values = [float(part.strip()) for part in raw.split(",")]
        except ValueError:
            warnings.append(f"line:{line_no}:rpm-torque-invalid-number:{raw}")
            continue
        if len(values) != 3:
            warnings.append(f"line:{line_no}:rpm-torque-arity:{len(values)}")
            continue
        point = RPMTorquePoint(values[0], values[1], values[2])
        if len(points) >= RPM_TORQUE_LIMIT:
            warnings.append("rpm-torque:too-many-points:127")
            continue
        if point.brake > point.throttle:
            warnings.append(f"line:{line_no}:rpm-torque-brake-greater-than-throttle")
        if points and point.rpm <= points[-1].rpm:
            warnings.append(f"line:{line_no}:rpm-torque-curve-out-of-order")
        points.append(point)

    if strict and warnings:
        raise ValueError(warnings[0])

    return {
        "format": "SHIFT.RPMTorqueRuntime/1",
        "version": 1,
        "status": "parsed" if not warnings else "parsed-with-warnings",
        "ready": not warnings,
        "point_count": len(points),
        "limit": RPM_TORQUE_LIMIT,
        "points": [
            {
                "line": line_no,
                "rpm": point.rpm,
                "brake": point.brake,
                "throttle": point.throttle,
                "source_tuple": [point.rpm, point.brake, point.throttle],
                "storage_order": [point.brake, point.throttle, point.rpm],
            }
            for line_no, point in _iter_rpm_points_with_lines(raw_text, points)
        ],
        "storage": {
            "base_offset": 0x1818,
            "record_stride": 0x20,
            "component_offsets": {"brake": 0x00, "throttle": 0x08, "rpm": 0x10},
        },
        "validation": {
            "source_brake_greater_than_throttle_check": "brake <= throttle required",
            "source_rpm_order_check": "strictly increasing RPM",
            "source_limit_check": "existing_count < 127 before appending",
        },
        "warnings": warnings,
        "evidence": {
            "loader": "FUN_007c3280",
            "tuple_reader": "FUN_007a6a90",
            "source_file": "./Source/Vehicle/vehload.cpp",
            "too_many_points_line": "0x6dd",
            "brake_throttle_line": "0x6df",
            "order_line": "0x6e1",
        },
    }
ENGINE_RPM_TORQUE = {
    "storage_base_offset": 0x1818,
    "entry_stride": 0x20,
    "point_components": 3,
    "diagnostic_when_existing_points_ge": 127,
    "diagnostic": "Too many RPM-torque points",
    "ordering_checks": [
        "component_1 >= component_0",
        "component_2 strictly increases relative to previous component_2",
    ],
    "status": "source component order and validation branches proven; interpolation/postload semantics remain unresolved",
    "text_tuple_order": ["rpm", "brake", "throttle"],
    "storage_order": ["brake", "throttle", "rpm"],
}

DRIVELINE_SOLVER = {
    "integrator_function": "FUN_00764266",
    "solver_function": "FUN_007af310",
    "dimension": 6,
    "failure_log": "Could not solve driveline",
    "source_file": SOURCE_FILE,
    "source_line_hex": "0x1d46",
    "source_line_decimal": 7494,
    "post_solver_wheel_sign_threshold_checks": [
        {"state_offset": 0xD0, "limit_source_offset": 0x770, "result_slot": "wheel_0"},
        {"state_offset": 0xCC, "limit_source_offset": 0x11F0, "result_slot": "wheel_1"},
        {"state_offset": 0xC8, "limit_source_offset": 0x1C70, "result_slot": "wheel_2"},
        {"state_offset": 0xC4, "limit_source_offset": 0x26F0, "result_slot": "wheel_3"},
        {"state_offset": 0x1C, "limit_source_offset": 0x30, "result_slot": "driveline_input"},
    ],
    "status": "linear-system-solve-is-proven; physical variable names are not",
}


def _find_function_line(source: str, function: str) -> int | None:
    pattern = re.compile(rf"\b{re.escape(function)}\(")
    lines = source.splitlines()
    for number, line in enumerate(lines, 1):
        if not pattern.search(line):
            continue
        context = " ".join(lines[max(0, number - 3):number])
        if "__thiscall" in context or "__fastcall" in context or "__cdecl" in context:
            return number
    return None


def _presence(source: str, needle: str) -> bool:
    return needle in source


def build_vehicle_physics_contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "status": "evidence-backed-runtime-boundary",
        "source": SOURCE_FILE,
        "vehicle_loader": {
            "function": "FUN_007c3b00",
            "source_file": VEHICLE_LOAD_SOURCE,
            "sections": SECTION_TARGETS,
            "open_error": "Could not open HDV file: %s",
        },
        "general": [p.to_dict() for p in GENERAL_PROPERTIES],
        "engine": {
            "properties": [p.to_dict() for p in ENGINE_PROPERTIES],
            "rpm_torque": ENGINE_RPM_TORQUE,
            "file_loader": "FUN_007c3280",
            "file_source": VEHICLE_LOAD_SOURCE,
            "file_source_line_hex": "0x6b8",
        },
        "suspension": [p.to_dict() for p in SUSPENSION_PROPERTIES],
        "wheel": [p.to_dict() for p in WHEEL_PROPERTIES],
        "driveline": [p.to_dict() for p in DRIVELINE_PROPERTIES],
        "postload": list(POSTLOAD_CALLS),
        "driveline_solver": DRIVELINE_SOLVER,
        "resource_links": {
            "engine_default_extension": ".edf",
            "driveline_wheeldrive_property": "WheelDrive",
            "basic_properties": ["Downforce", "Balance", "Gearing"],
        },
        "unknowns": [
            "physical units for individual HDV properties",
            "full internal variable naming of the 6-variable driveline system",
            "exact meaning of wheel sign state values -1/0/1 beyond observed branch behavior",
            "exact RPMTorque component semantics and final interpolation formula",
            "concrete cross-file ownership below .cgp/.cdf/.edf/.gdf/.sdf",
        ],
    }


def validate_contract_shape() -> dict[str, Any]:
    groups = {
        "general": GENERAL_PROPERTIES,
        "engine": ENGINE_PROPERTIES,
        "suspension": SUSPENSION_PROPERTIES,
        "wheel": WHEEL_PROPERTIES,
        "driveline": DRIVELINE_PROPERTIES,
    }
    duplicate_offsets = {
        name: sorted({p.offset for p in rows if [x.offset for x in rows].count(p.offset) > 1})
        for name, rows in groups.items()
    }
    return {
        "format": "SHIFT.VehiclePhysicsDetailsContractValidation/1",
        "ready": all(not values for values in duplicate_offsets.values()),
        "property_counts": {name: len(rows) for name, rows in groups.items()},
        "duplicate_offsets": duplicate_offsets,
    }


def analyze_source(source_path: str | Path) -> dict[str, Any]:
    path = Path(source_path)
    raw = path.read_bytes()
    source = raw.decode("utf-8", errors="ignore")
    hd_tag = "." + DOUBLE_SLASH + "Source" + DOUBLE_SLASH + "Vehicle" + DOUBLE_SLASH + "hdvehicle.cpp"
    load_tag = "." + DOUBLE_SLASH + "Source" + DOUBLE_SLASH + "Vehicle" + DOUBLE_SLASH + "vehload.cpp"
    checks = {
        "vehicle_loader_present": _presence(source, "FUN_007c3b00(void *this"),
        "general_parser_present": _presence(source, "FUN_007be420(void *this"),
        "wheel_parser_present": _presence(source, "FUN_007bc770(void *this"),
        "suspension_parser_present": _presence(source, "FUN_007bdb80(void *this"),
        "driveline_parser_present": _presence(source, "FUN_007bcdf0(void *this"),
        "engine_file_loader_present": _presence(source, "FUN_007c3280(void *this"),
        "rpm_torque_validation_present": _presence(source, "Too many RPM-torque points"),
        "edf_postload_present": _presence(source, "FUN_007c3920(this,this_00,&param_3,param_5);"),
        "driveline_solver_present": _presence(source, "FUN_007af310(unaff_EBP + -0x1b8,6)"),
        "solver_failure_message_present": _presence(source, "Could not solve driveline"),
        "hdvehicle_source_tag_present": _presence(source, hd_tag),
        "vehicle_loader_source_tag_present": _presence(source, load_tag),
    }
    function_lines = {
        name: _find_function_line(source, name)
        for name in (
            "FUN_007c3b00", "FUN_007be420", "FUN_007bc770", "FUN_007bdb80",
            "FUN_007bcdf0", "FUN_007c3280", "FUN_007c3920", "FUN_00764266", "FUN_007af310",
        )
    }
    return {
        "format": "SHIFT.VehiclePhysicsSourceEvidence/1",
        "version": 1,
        "source_path": str(source_path),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "checks": checks,
        "function_lines": function_lines,
        "ready": all(checks.values()),
        "contract": build_vehicle_physics_contract(),
        "contract_validation": validate_contract_shape(),
    }


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Extract SHIFT vehicle-physics source evidence")
    parser.add_argument("input", help="recovered SHIFT.exe.c")
    parser.add_argument("output", help="SHIFT.VehiclePhysicsSourceEvidence/1 JSON output")
    args = parser.parse_args(argv)
    report = analyze_source(args.input)
    Path(args.output).write_text(json.dumps(report, indent=2, ensure_ascii=False) + chr(10), encoding="utf-8")
    return 0 if report["ready"] else 2


__all__ = [
    "FORMAT", "GENERAL_PROPERTIES", "ENGINE_PROPERTIES", "WHEEL_PROPERTIES",
    "SUSPENSION_PROPERTIES", "DRIVELINE_PROPERTIES", "SECTION_TARGETS",
    "ENGINE_RPM_TORQUE", "RPMTorquePoint", "parse_rpm_torque_points", "DRIVELINE_SOLVER", "build_vehicle_physics_contract",
    "validate_contract_shape", "analyze_source",
]


if __name__ == "__main__":
    raise SystemExit(main())
