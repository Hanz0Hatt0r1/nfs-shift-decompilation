"""Source-backed parser and schema for SHIFT vehicle .cdf physics configuration.

The retail CDF loader is an INI-like text reader. This module preserves the raw
text/value representation while attaching only source-proven metadata:
section handler, parser helper and destination offsets recovered from SHIFT.exe.c.
No physical unit or gameplay meaning is inferred.
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

FORMAT = "SHIFT.VehicleCDFRuntime/1"
SOURCE_FILE = "SHIFT.exe.c"
SOURCE_LOADER = "FUN_007be420"

_SECTION_RE = re.compile(r"^\s*\[([^\]]+)\]\s*$")
_ASSIGN_RE = re.compile(r"^\s*([^=:#]+?)\s*=\s*(.*?)\s*$")
_NUMBER_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")
_INT_RE = re.compile(r"^[+-]?\d+$")


@dataclass(frozen=True)
class CDFPropertySpec:
    name: str
    helper: str
    offsets: tuple[int, ...] = ()
    value_shape: str = "unknown"
    source: str = SOURCE_FILE

    @property
    def offset_hex(self) -> list[str]:
        return [f"0x{offset:x}" for offset in self.offsets]


def _spec(name: str, helper: str, *offsets: int, shape: str = "unknown") -> CDFPropertySpec:
    return CDFPropertySpec(name, helper, tuple(offsets), shape)


def _map(*specs: CDFPropertySpec) -> dict[str, CDFPropertySpec]:
    return {item.name: item for item in specs}


GENERAL = _map(
    _spec("Rules", "FUN_007a65e0", 0x14, shape="scalar32"),
    _spec("GarageDisplayFlags", "FUN_007a65e0", 0x18, shape="scalar32"),
    _spec("Mass", "FUN_007a75a0", 0x1c, shape="scalar64"),
    _spec("Inertia", "FUN_007a75a0", 0x30, 0x44, 0x58, shape="tuple3"),
    _spec("DriftInertia", "FUN_007a75a0", 0x78, 0x8c, 0xa0, shape="tuple3"),
    _spec("CGHeight", "FUN_007a75a0", 0x180, shape="scalar64"),
    _spec("WedgePushrod", "FUN_007a6a90", 0xc0, shape="scalar64"),
    _spec("GraphicalOffset", "FUN_007a75a0", 0xc8, 0xdc, 0xf0, shape="tuple3"),
    _spec("CollisionOffset", "FUN_007a75a0", 0x110, 0x124, 0x138, shape="tuple3"),
    _spec("FLUndertray", "FUN_007a6a90", 0x1f0, 0x1f8, 0x200, shape="tuple3"),
    _spec("FRUndertray", "FUN_007a6a90", 0x208, 0x210, 0x218, shape="tuple3"),
    _spec("RLUndertray", "FUN_007a6a90", 0x220, 0x228, 0x230, shape="tuple3"),
    _spec("RRUndertray", "FUN_007a6a90", 0x238, 0x240, 0x248, shape="tuple3"),
    _spec("UndertrayParams", "FUN_007a6a90", 0x310, 0x318, 0x320, shape="tuple3"),
    _spec("FuelTankPos", "FUN_007a6a90", 0x158, 0x160, 0x168, shape="tuple3"),
    _spec("FuelTankMotion", "FUN_007a6a90", 0x170, 0x178, shape="tuple2"),
    _spec("AIMinPassesPerTick", "FUN_007a65e0", 0x194, shape="scalar32"),
    _spec("AIRotationThreshold", "FUN_007a6a90", 0x198, shape="scalar64"),
    _spec("AIEvenSuspension", "FUN_007a6a90", 0x1a0, shape="scalar64"),
    _spec("AISpringRate", "FUN_007a6a90", 0x1a8, shape="scalar64"),
    _spec("AIDamperSlow", "FUN_007a6a90", 0x1b0, shape="scalar64"),
    _spec("AIDamperFast", "FUN_007a6a90", 0x1b8, shape="scalar64"),
    _spec("AIDownforceZArm", "FUN_007a6a90", 0x1c0, shape="scalar64"),
    _spec("AIDownforceBias", "FUN_007a6a90", 0x1c8, shape="scalar64"),
    _spec("AITorqueStab", "FUN_007a6a90", 0x1d0, 0x1d8, 0x1e0, shape="tuple3"),
    _spec("Symmetric", "FUN_007a65e0", 0x10, shape="scalar32"),
    _spec("DamageFile", "FUN_007a63e0", shape="string"),
    _spec("CGRightRange", "FUN_007a6a90", 0x338, 0x340, 0x348, shape="tuple3"),
    _spec("CGRightSetting", "FUN_007a6a90", 0x4a0, shape="scalar64"),
    _spec("CGRearRange", "FUN_007a75a0", 0x350, 0x364, 0x378, shape="tuple3"),
    _spec("CGRearSetting", "FUN_007a75a0", 0x4a8, shape="scalar64"),
    _spec("WedgeRange", "FUN_007a6a90", 0x398, 0x3a0, 0x3a8, shape="tuple3"),
    _spec("WedgeSetting", "FUN_007a6a90", 0x4c0, shape="scalar64"),
    _spec("FrontTireCompoundSetting", "FUN_007a6a90", 0x4c8, shape="scalar64"),
    _spec("RearTireCompoundSetting", "FUN_007a6a90", 0x4d0, shape="scalar64"),
    _spec("FuelRange", "FUN_007a6a90", 0x3b0, 0x3b8, 0x3c0, shape="tuple3"),
    _spec("FuelSetting", "FUN_007a6a90", 0x4d8, shape="scalar64"),
    _spec("NumPitstopsRange", "FUN_007a6a90", 0x3c8, 0x3d0, 0x3d8, shape="tuple3"),
    _spec("NumPitstopsSetting", "FUN_007a6a90", 0x4e0, shape="scalar64"),
)
for _n, _base in ((f"Pitstop{i}", 0x3e0 + (i - 1) * 0x18) for i in range(1, 9)):
    GENERAL[f"{_n}Range"] = _spec(f"{_n}Range", "FUN_007a6a90", _base, _base + 8, _base + 0x10, shape="tuple3")
    GENERAL[f"{_n}Setting"] = _spec(f"{_n}Setting", "FUN_007a6a90", 0x4e0 + i * 8, shape="scalar64")
for i in range(5):
    GENERAL[f"AdjustableUpgradeLevel_{i}"] = _spec(
        f"AdjustableUpgradeLevel_{i}", "FUN_007a65e0", 0x2364 + i * 4, shape="scalar32"
    )
GENERAL["UpgradedTyre"] = _spec("UpgradedTyre", "FUN_007a63e0", shape="string")


for _i, _name in enumerate(("Undertray00", "Undertray01", "Undertray02", "Undertray03")):
    _base = 0x1f8 + _i * 0x18
    GENERAL[_name] = _spec(_name, "FUN_007a6a90", _base - 8, _base, _base + 8, shape="tuple3")


def _wheel_specs() -> dict[str, CDFPropertySpec]:
    names = [
        ("BumpTravel", 0x00, "scalar64"), ("ReboundTravel", 0x08, "scalar64"),
        ("BumpStopSpring", 0x10, "scalar64"), ("BumpStopRisingSpring", 0x18, "scalar64"),
        ("BumpStopDamper", 0x20, "scalar64"), ("BumpStopRisingDamper", 0x28, "scalar64"),
        ("BumpStage2", 0x30, "scalar64"), ("ReboundStage2", 0x38, "scalar64"),
        ("FrictionTorque", 0xb8, "scalar64"), ("BrakeTorque", 0xc0, "scalar64"),
        ("BrakeWearRate", 0x120, "scalar64"), ("BrakeFailure", 0x128, "tuple2"),
        ("BrakeOptimumTemp", 0xd8, "scalar64"), ("BrakeFadeRange", 0xe0, "scalar64"),
        ("BrakeDiscInertia", 0x118, "scalar64"), ("BrakeHeating", 0xe8, "scalar64"),
        ("BrakeCooling", 0x100, "tuple2"), ("BrakeDuctCooling", 0x110, "scalar64"),
        ("SpinInertia", 0xa0, "scalar64"), ("CGOffsetX", 0x68, "scalar64"),
        ("SpringMult", 0x40, "scalar64"), ("DamperMult", 0x54, "scalar64"),
        ("PushrodSpindle", 0x70, "tuple3"), ("PushrodBody", 0x88, "tuple3"),
        ("CamberRange", 0x138, "tuple3"), ("CamberSetting", 0x150, "scalar64"),
        ("PressureRange", 0x158, "tuple3"), ("PressureSetting", 0x170, "scalar64"),
        ("RideHeightRange", 0x178, "tuple3"), ("RideHeightSetting", 0x190, "scalar64"),
        ("PackerRange", 0x1a8, "tuple3"), ("PackerSetting", 0x1c0, "scalar64"),
        ("SpringRange", 0x1c8, "tuple3"), ("SpringSetting", 0x210, "scalar64"),
        ("SlowBumpRange", 0x228, "tuple3"), ("SlowBumpSetting", 0x240, "scalar64"),
        ("FastBumpRange", 0x248, "tuple3"), ("FastBumpSetting", 0x260, "scalar64"),
        ("SlowReboundRange", 0x268, "tuple3"), ("SlowReboundSetting", 0x280, "scalar64"),
        ("FastReboundRange", 0x288, "tuple3"), ("FastReboundSetting", 0x2a0, "scalar64"),
        ("BrakeDiscRange", 0x2a8, "tuple3"), ("BrakeDiscSetting", 0x2c0, "scalar64"),
        ("BrakePadRange", 0x2c8, "tuple3"), ("BrakePadSetting", 0x2e0, "scalar64"),
    ]
    out = {}
    for name, base, shape in names:
        arity = {"scalar64": 1, "tuple2": 2, "tuple3": 3}[shape]
        helper = "FUN_007a75a0" if name in {
            "BrakeTorque", "BrakeHeating", "SpringMult", "DamperMult",
            "RideHeightSetting", "SpringRange", "SpringSetting"
        } else "FUN_007a6a90"
        out[name] = _spec(name, helper, *tuple(base + i * 8 for i in range(arity)), shape=shape)
    return out


WHEEL = _wheel_specs()


def _suspension_specs() -> dict[str, CDFPropertySpec]:
    rows = [
        ("FixInnerSuspHeight", "FUN_007a6a90", 0x08, "scalar64"),
        ("CorrectedInnerSuspHeight", "FUN_007a6a90", 0x10, "scalar64"),
        ("ApplySlowToFastDampers", "FUN_007a6470", 0x18, "bool8"),
        ("AdjustSuspRates", "FUN_007a6470", 0x19, "bool8"),
        ("AlignWheels", "FUN_007a6470", 0x1a, "bool8"),
        ("FrontWheelTrack", "FUN_007a6a90", 0x20, "scalar64"),
        ("RearWheelTrack", "FUN_007a6a90", 0x28, "scalar64"),
        ("LeftWheelBase", "FUN_007a6a90", 0x30, "scalar64"),
        ("RightWheelBase", "FUN_007a6a90", 0x38, "scalar64"),
        ("SpringBasedAntiSway", "FUN_007a6470", 0x40, "bool8"),
        ("AllowNoAntiSway", "FUN_007a6470", 0x41, "bool8"),
        ("FrontAntiSwayBase", "FUN_007a6a90", 0x48, "scalar64"),
        ("FrontAntiSwayRate", "FUN_007a6a90", 0x50, 0x58, "tuple2"),
        ("RearAntiSwayBase", "FUN_007a6a90", 0x60, "scalar64"),
        ("RearAntiSwayRate", "FUN_007a6a90", 0x68, 0x70, "tuple2"),
        ("Front3rdBumpTravel", "FUN_007a6a90", 0x78, "scalar64"),
        ("Front3rdReboundTravel", "FUN_007a6a90", 0x80, "scalar64"),
        ("Front3rdBumpStopSpring", "FUN_007a6a90", 0x88, "scalar64"),
        ("Front3rdBumpStopRisingSpring", "FUN_007a6a90", 0x90, "scalar64"),
        ("Front3rdBumpStopDamper", "FUN_007a6a90", 0x98, "scalar64"),
        ("Front3rdBumpStopRisingDamper", "FUN_007a6a90", 0xa0, "scalar64"),
        ("Front3rdBumpStage2", "FUN_007a6a90", 0xa8, "scalar64"),
        ("Front3rdReboundStage2", "FUN_007a6a90", 0xb0, "scalar64"),
        ("Rear3rdBumpTravel", "FUN_007a6a90", 0xb8, "scalar64"),
        ("Rear3rdReboundTravel", "FUN_007a6a90", 0xc0, "scalar64"),
        ("Rear3rdBumpStopSpring", "FUN_007a6a90", 0xc8, "scalar64"),
        ("Rear3rdBumpStopRisingSpring", "FUN_007a6a90", 0xd0, "scalar64"),
        ("Rear3rdBumpStopDamper", "FUN_007a6a90", 0xd8, "scalar64"),
        ("Rear3rdBumpStopRisingDamper", "FUN_007a6a90", 0xe0, "scalar64"),
        ("Rear3rdBumpStage2", "FUN_007a6a90", 0xe8, "scalar64"),
        ("Rear3rdReboundStage2", "FUN_007a6a90", 0xf0, "scalar64"),
    ]
    out = {}
    for name, helper, *rest in rows:
        shape = rest[-1]
        offsets = tuple(rest[:-1])
        out[name] = _spec(name, helper, *offsets, shape=shape)
    range_rows = [
        ("FrontAntiSwayRange", 0xf8, 0x10c, 0x120, 0x368),
        ("RearAntiSwayRange", 0x140, 0x154, 0x168, 0x37c),
        ("FrontToeInRange", 0x188, 0x190, 0x198, 0x3b8),
        ("RearToeInRange", 0x1a0, 0x1a8, 0x1b0, 0x3c0),
        ("LeftFenderFlareRange", 0x1b8, 0x1c0, 0x1c8, 0x3c8),
        ("RightFenderFlareRange", 0x1d0, 0x1d8, 0x1e0, 0x3d0),
        ("LeftCasterRange", 0x1e8, 0x1f0, 0x1f8, 0x3d8),
        ("RightCasterRange", 0x200, 0x208, 0x210, 0x3e0),
        ("LeftTrackBarRange", 0x218, 0x220, 0x228, 0x3e8),
        ("RightTrackBarRange", 0x230, 0x238, 0x240, 0x3f0),
        ("Front3rdPackerRange", 0x248, 0x250, 0x258, 0x3f8),
        ("Front3rdSpringRange", 0x260, 0x268, 0x270, 0x400),
        ("Front3rdSlowBumpRange", 0x278, 0x280, 0x288, 0x408),
        ("Front3rdFastBumpRange", 0x290, 0x298, 0x2a0, 0x410),
        ("Front3rdSlowReboundRange", 0x2a8, 0x2b0, 0x2b8, 0x418),
        ("Front3rdFastReboundRange", 0x2c0, 0x2c8, 0x2d0, 0x420),
        ("Rear3rdPackerRange", 0x2d8, 0x2e0, 0x2e8, 0x428),
        ("Rear3rdSpringRange", 0x2f0, 0x2f8, 0x300, 0x430),
        ("Rear3rdSlowBumpRange", 0x308, 0x310, 0x318, 0x438),
        ("Rear3rdFastBumpRange", 0x320, 0x328, 0x330, 0x440),
        ("Rear3rdSlowReboundRange", 0x338, 0x340, 0x348, 0x448),
        ("Rear3rdFastReboundRange", 0x350, 0x358, 0x360, 0x450),
    ]
    for name, a, b, c, setting in range_rows:
        out[name] = _spec(name, "FUN_007a75a0" if "AntiSwayRange" in name else "FUN_007a6a90", a, b, c, shape="tuple3")
        out[name.replace("Range", "Setting")] = _spec(
            name.replace("Range", "Setting"),
            "FUN_007a75a0" if setting in {0x368, 0x390, 0x37c, 0x3a4} else "FUN_007a6a90",
            setting,
            shape="scalar64",
        )
    return out


SUSPENSION = _suspension_specs()


CONTROLS = _map(
    _spec("SteeringFFBMult", "FUN_007a6a90", 0x00, shape="scalar64"),
    _spec("UpshiftAlgorithm", "FUN_007a6a90", 0xa0, 0xa8, shape="tuple2"),
    _spec("DownshiftAlgorithm", "FUN_007a6a90", 0xb0, 0xb8, 0xc0, shape="tuple3"),
    _spec("AutoUpshiftSlipLimit", "FUN_007a6a90", 0x08, shape="scalar64"),
    _spec("AutoUpshiftSlipLimitDrift", "FUN_007a6a90", 0x10, shape="scalar64"),
    _spec("AutoUpshiftGripThresh", "FUN_007a6a90", 0x18, shape="scalar64"),
    _spec("AutoDownshiftGripThresh", "FUN_007a6a90", 0x20, shape="scalar64"),
    _spec("TractionControlGrip", "FUN_007a6a90", 0x28, 0x30, shape="tuple2"),
    _spec("TractionControlLevel", "FUN_007a6a90", 0x38, 0x40, shape="tuple2"),
    _spec("ABS4Wheel", "FUN_007a6470", 0x49, shape="bool8"),
    _spec("ABSGrip", "FUN_007a6a90", 0x50, 0x58, shape="tuple2"),
    _spec("ABSLevel", "FUN_007a6a90", 0x60, 0x68, shape="tuple2"),
    _spec("OnboardBrakeBias", "FUN_007a6470", 0x48, shape="bool8"),
    _spec("SteerLockRange", "FUN_007a6a90", 0xc8, 0xd0, 0xd8, shape="tuple3"),
    _spec("SteerLockSetting", "FUN_007a75a0", 0xe0, shape="scalar64"),
    _spec("DriftSteerLockSetting", "FUN_007a75a0", 0xf4, shape="scalar64"),
    _spec("RearBrakeRange", "FUN_007a6a90", 0x108, 0x110, 0x118, shape="tuple3"),
    _spec("RearBrakeSetting", "FUN_007a6a90", 0x120, shape="scalar64"),
    _spec("BrakePressureRange", "FUN_007a6a90", 0x128, 0x130, 0x138, shape="tuple3"),
    _spec("BrakePressureSetting", "FUN_007a75a0", 0x140, shape="scalar64"),
    _spec("HandbrakePressRange", "FUN_007a6a90", 0x158, 0x160, 0x168, shape="tuple3"),
    _spec("HandbrakePressSetting", "FUN_007a6a90", 0x170, shape="scalar64"),
    _spec("SpeedSensitiveSteeringScale", "FUN_007a67b0", 0x180, shape="scalar32"),
    _spec("JoypadDampeningScale", "FUN_007a67b0", 0x184, shape="scalar32"),
)
for _name, _base in (
    ("ThrottleControl", 0x188), ("DriftThrottleControl", 0x198),
    ("AntilockBrakes", 0x1a8), ("StabilityControl", 0x1b8),
    ("ShiftMode", 0x1c8), ("SteeringHelp", 0x1d8), ("BrakeHelp", 0x1e8),
    ("DriftSpeedHelp", 0x1f8), ("DriftYawHelp", 0x208), ("DriftIdealLineHelp", 0x218),
    ("OppositeLock", 0x228),
):
    CONTROLS[_name] = _spec(_name, "FUN_007a65e0", _base, _base + 4, _base + 8, _base + 12, shape="tuple4")
for _name, _base, _arity in (
    ("TractionControlSlip", 0x238, 2), ("ABSSlip1", 0x240, 2), ("ABSSlip2", 0x248, 2),
    ("ThrottleLinearity", 0x250, 1), ("MaxSteerVelocityScale", 0x254, 1),
    ("NominalRiseDampingScale", 0x258, 1), ("NominalFallDampingScale", 0x25c, 1),
    ("NominalYawAngleScale", 0x260, 1), ("YawAngleEffectScale", 0x264, 1),
    ("SteerFilterGripScale", 0x26c, 1), ("SteerFilterSlipScale", 0x270, 1),
    ("DriftSteerFilterSpeedOffset", 0x274, 1), ("SteerFilterAutoVelocityScale", 0x280, 1),
    ("SteerFilterAutoRiseVelocityScale", 0x284, 1), ("SteerFilterAutoFallVelocityScale", 0x288, 1),
    ("SteerFilterAutoStraightLockScale", 0x28c, 1), ("SteerFilterAutoYawAngleDampingScale", 0x290, 1),
    ("SteerFilterAutoAimSlipScale", 0x294, 1),
):
    helper = "FUN_007a65e0" if _name == "UseTireStiffness" else "FUN_007a67b0"
    CONTROLS[_name] = _spec(_name, helper, *tuple(_base + i*4 for i in range(_arity)), shape=f"tuple{_arity}" if _arity > 1 else "scalar32")
CONTROLS["UseTireStiffness"] = _spec("UseTireStiffness", "FUN_007a65e0", 0x268, shape="scalar32")
CONTROLS["DriftGrip"] = _spec("DriftGrip", "FUN_007a6a90", 0x70, 0x78, 0x80, shape="tuple3")
CONTROLS["DriftDriveTorqueMultiplier"] = _spec("DriftDriveTorqueMultiplier", "FUN_007a67b0", 0x90, 0x94, 0x98, 0x9c, shape="tuple4")
CONTROLS["SteeringMultiplier"] = _spec("SteeringMultiplier", "FUN_007a6a90", 0x278, shape="scalar64")


DRIVELINE = _map(
    _spec("ClutchEngageRate", "FUN_007a75a0", 0x08, shape="scalar64"),
    _spec("ClutchInertia", "FUN_007a75a0", 0x1c, shape="scalar64"),
    _spec("ClutchTorque", "FUN_007a75a0", 0x30, shape="scalar64"),
    _spec("ClutchWear", "FUN_007a6a90", 0x48, shape="scalar64"),
    _spec("ClutchFriction", "FUN_007a6a90", 0x50, shape="scalar64"),
    _spec("BaulkTorque", "FUN_007a75a0", 0x58, shape="scalar64"),
    _spec("AllowManualOverride", "FUN_007a6470", 0x6c, shape="bool8"),
    _spec("SemiAutomatic", "FUN_007a6470", 0x6d, shape="bool8"),
    _spec("UpshiftDelay", "FUN_007a75a0", 0x70, shape="scalar64"),
    _spec("UpshiftClutchTime", "FUN_007a75a0", 0x84, shape="scalar64"),
    _spec("UpshiftLiftThrottle", "FUN_007a6a90", 0x98, shape="scalar64"),
    _spec("DownshiftDelay", "FUN_007a75a0", 0xa0, shape="scalar64"),
    _spec("DownshiftClutchTime", "FUN_007a75a0", 0xb4, shape="scalar64"),
    _spec("DownshiftBlipThrottle", "FUN_007a6a90", 0xc8, shape="scalar64"),
    _spec("DiffPumpTorque", "FUN_007a75a0", 0xe8, shape="scalar64"),
    _spec("DriftDiffSpool", "FUN_007a6470", 0xfc, shape="bool8"),
    _spec("WheelDrive", "FUN_007a63e0", shape="string"),
    _spec("ForwardGears", "FUN_007a75a0", 0xd4, shape="scalar64"),
    _spec("DiffPumpRange", "FUN_007a75a0", 0x100, 0x114, 0x128, shape="tuple3"),
    _spec("DiffPowerRange", "FUN_007a6a90", 0x148, 0x150, 0x158, shape="tuple3"),
    _spec("DiffCoastRange", "FUN_007a6a90", 0x160, 0x168, 0x170, shape="tuple3"),
    _spec("DiffPreloadRange", "FUN_007a6a90", 0x178, 0x180, 0x188, shape="tuple3"),
    _spec("FinalDriveSetting", "FUN_007a75a0", 0x190, shape="scalar64"),
    _spec("ReverseSetting", "FUN_007a75a0", 0x1a4, shape="scalar64"),
    _spec("DiffPumpSetting", "FUN_007a75a0", 0x258, shape="scalar64"),
    _spec("DiffPowerSetting", "FUN_007a75a0", 0x26c, shape="scalar64"),
    _spec("DiffCoastSetting", "FUN_007a75a0", 0x280, shape="scalar64"),
    _spec("DiffPreloadSetting", "FUN_007a75a0", 0x294, shape="scalar64"),
    _spec("AdjustableGearsMinimumLevel", "FUN_007a65e0", 0x2a8, shape="scalar32"),
    _spec("AdjustableFinalGearsMinimumLevel", "FUN_007a65e0", 0x2ac, shape="scalar32"),
    _spec("AdjustableGearsRange", "FUN_007a65e0", 0x2b0, shape="scalar32"),
    _spec("AdjustableGearsFinalRange", "FUN_007a65e0", 0x2b4, shape="scalar32"),
)
for i, off in enumerate((0x1b8, 0x1cc, 0x1e0, 0x1f4, 0x208, 0x21c, 0x230, 0x244), start=1):
    DRIVELINE[f"Gear{i}Setting"] = _spec(f"Gear{i}Setting", "FUN_007a75a0", off, shape="scalar64")


FENDER = _map(
    _spec("FenderCenter", "FUN_007a6a90", 0x60, 0x68, 0x70, shape="tuple3"),
    _spec("FenderDragParams", "FUN_007a6a90", 0x08, 0x10, 0x18, shape="tuple3"),
    _spec("FenderLiftParams", "FUN_007a6a90", 0x20, 0x28, 0x30, shape="tuple3"),
    _spec("FenderSideways", "FUN_007a6a90", 0x38, shape="scalar64"),
    _spec("FenderPeakYaw", "FUN_007a6a90", 0x50, 0x58, shape="tuple2"),
)

FRONTWING = _map(
    _spec("FWDragParams", "FUN_007a75a0", 0x18, 0x2c, 0x40, shape="tuple3"),
    _spec("FWLiftParams", "FUN_007a75a0", 0x54, 0x68, 0x7c, shape="tuple3"),
    _spec("FWMaxHeight", "FUN_007a75a0", 0x04, shape="scalar64"),
    _spec("FWLiftHeight", "FUN_007a6a90", 0x90, shape="scalar64"),
    _spec("FWLiftSideways", "FUN_007a6a90", 0x98, shape="scalar64"),
    _spec("FWLiftPeakYaw", "FUN_007a6a90", 0x290, 0x298, shape="tuple2"),
    _spec("FWCenter", "FUN_007a6a90", 0x278, 0x280, 0x288, shape="tuple3"),
    _spec("FWRange", "FUN_007a75a0", 0x2a0, 0x2b4, 0x2c8, shape="tuple3"),
    _spec("FWSetting", "FUN_007a75a0", 0x2e8, shape="scalar64"),
)
for _name in ("FWLeft", "FWRight", "FWUp", "FWDown", "FWAft", "FWFore", "FWRot"):
    FRONTWING[_name] = _spec(_name, "FUN_007c0820/FUN_007c0860", shape="opaque-control")


REARWING = _map(
    _spec("RWRange", "FUN_007a75a0", 0x2a0, 0x2b4, 0x2c8, shape="tuple3"),
    _spec("RWSetting", "FUN_007a75a0", 0x2e8, shape="scalar64"),
    _spec("RWDragParams", "FUN_007a75a0", 0x18, 0x2c, 0x40, shape="tuple3"),
    _spec("RWLiftParams", "FUN_007a75a0", 0x54, 0x68, 0x7c, shape="tuple3"),
    _spec("RWLiftSideways", "FUN_007a6a90", 0x98, shape="scalar64"),
    _spec("RWPeakYaw", "FUN_007a6a90", 0x290, 0x298, shape="tuple2"),
    _spec("RWCenter", "FUN_007a6a90", 0x278, 0x280, 0x288, shape="tuple3"),
)
for _name in ("RWLeft", "RWRight", "RWUp", "RWDown", "RWAft", "RWFore", "RWRot"):
    REARWING[_name] = _spec(_name, "FUN_007c0820/FUN_007c0860", shape="opaque-control")



BODYAERO = _map(
    _spec("BodyDragBase", "FUN_007a75a0", 0x00, shape="scalar64"),
    _spec("BodyDragHeightAvg", "FUN_007a6a90", 0x18, shape="scalar64"),
    _spec("BodyDragHeightDiff", "FUN_007a6a90", 0x20, shape="scalar64"),
    _spec("BodyMaxHeight", "FUN_007a6a90", 0x28, shape="scalar64"),
    _spec("BodyCenter", "FUN_007a6a90", 0x30, 0x38, 0x40, shape="tuple3"),
    _spec("RadiatorDrag", "FUN_007a6a90", 0x48, shape="scalar64"),
    _spec("RadiatorLift", "FUN_007a6a90", 0x50, shape="scalar64"),
    _spec("BrakeDuctDrag", "FUN_007a6a90", 0x58, shape="scalar64"),
    _spec("BrakeDuctLift", "FUN_007a6a90", 0x60, shape="scalar64"),
    _spec("RadiatorRange", "FUN_007a6a90", 0x230, 0x238, 0x240, shape="tuple3"),
    _spec("RadiatorSetting", "FUN_007a6a90", 0x260, shape="scalar64"),
    _spec("BrakeDuctRange", "FUN_007a6a90", 0x248, 0x250, 0x258, shape="tuple3"),
    _spec("BrakeDuctSetting", "FUN_007a6a90", 0x268, shape="scalar64"),
)
for _name in ("BodyLeft", "BodyRight", "BodyUp", "BodyDown", "BodyAft", "BodyFore", "BodyRot"):
    BODYAERO[_name] = _spec(_name, "FUN_007c0820/FUN_007c0860", shape="opaque-control")


DIFFUSER = _map(
    _spec("DiffuserBase", "FUN_007a75a0", 0x04, 0x18, 0x2c, shape="tuple3"),
    _spec("DiffuserFrontHeight", "FUN_007a6a90", 0x80, shape="scalar64"),
    _spec("DiffuserRake", "FUN_007a6a90", 0x50, 0x58, 0x60, shape="tuple3"),
    _spec("DiffuserLimits", "FUN_007a6a90", 0x68, 0x70, 0x78, shape="tuple3"),
    _spec("DiffuserStall", "FUN_007a6a90", 0x88, 0x90, shape="tuple2"),
    _spec("DiffuserSideways", "FUN_007a6a90", 0x98, shape="scalar64"),
    _spec("DiffuserPeakYaw", "FUN_007a6a90", 0xc8, 0xd0, shape="tuple2"),
    _spec("DiffuserCenter", "FUN_007a6a90", 0xb0, 0xb8, 0xc0, shape="tuple3"),
)


SECTION_SPECS: dict[str, dict[str, CDFPropertySpec]] = {
    "GENERAL": GENERAL,
    "FRONTWING": FRONTWING,
    "LEFTFENDER": FENDER,
    "RIGHTFENDER": FENDER,
    "REARWING": REARWING,
    "BODYAERO": BODYAERO,
    "DIFFUSER": DIFFUSER,
    "SUSPENSION": SUSPENSION,
    "CONTROLS": CONTROLS,
    "ENGINE": {
        "SpeedLimiter": _spec("SpeedLimiter", "FUN_007a6470", 0x28f0, shape="bool8"),
    },
    "DRIVELINE": DRIVELINE,
    "FRONTLEFT": WHEEL,
    "FRONTRIGHT": WHEEL,
    "REARLEFT": WHEEL,
    "REARRIGHT": WHEEL,
    "BASIC": {
        "Downforce": _spec("Downforce", "FUN_007715f0", shape="opaque-dispatch"),
        "Balance": _spec("Balance", "FUN_007715f0", shape="opaque-dispatch"),
        "Gearing": _spec("Gearing", "FUN_007715f0", shape="opaque-dispatch"),
        "Custom": _spec("Custom", "FUN_007a65e0", shape="scalar32"),
    },
}

SECTION_HANDLERS = {
    "GENERAL": "FUN_007be420",
    "FRONTWING": "FUN_007c0a20",
    "LEFTFENDER": "FUN_007bccc0(type=10)",
    "RIGHTFENDER": "FUN_007bccc0(type=11)",
    "REARWING": "FUN_007c0c00",
    "BODYAERO": "FUN_007c27e0",
    "DIFFUSER": "FUN_007bda10",
    "SUSPENSION": "FUN_007bdb80",
    "CONTROLS": "FUN_007bd290",
    "ENGINE": "FUN_007be420(section-specific SpeedLimiter)",
    "DRIVELINE": "FUN_007bcdf0",
    "FRONTLEFT": "FUN_007bc770(index=0)",
    "FRONTRIGHT": "FUN_007bc770(index=1)",
    "REARLEFT": "FUN_007bc770(index=2)",
    "REARRIGHT": "FUN_007bc770(index=3)",
    "BASIC": "FUN_007715f0/FUN_007a65e0",
}

def _strip_inline_comment(line: str) -> str:
    for marker in ("//", "#", ";"):
        if marker in line:
            line = line.split(marker, 1)[0]
    return line.strip()


def _parse_atom(text: str) -> Any:
    value = text.strip()
    low = value.lower()
    if low in {"true", "false"}:
        return low == "true"
    if _INT_RE.fullmatch(value):
        try:
            return int(value, 10)
        except ValueError:
            pass
    if _NUMBER_RE.fullmatch(value):
        try:
            return float(value)
        except ValueError:
            pass
    return value.strip('"')


def parse_cdf(data: str | bytes, *, strict: bool = False) -> dict[str, Any]:
    text = data.decode("utf-8", "replace") if isinstance(data, bytes) else str(data)
    sections: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    warnings: list[str] = []

    for line_no, original in enumerate(text.splitlines(), 1):
        stripped = _strip_inline_comment(original)
        if not stripped:
            continue
        section_match = _SECTION_RE.match(stripped)
        if section_match:
            name = section_match.group(1).strip().upper()
            current = {
                "name": name,
                "original_name": section_match.group(1).strip(),
                "line": line_no,
                "entries": [],
            }
            sections.append(current)
            continue

        assignment = _ASSIGN_RE.match(stripped)
        if assignment is None:
            warnings.append(f"line:{line_no}:unparsed:{original.strip()}")
            if strict:
                raise ValueError(warnings[-1])
            continue

        if current is None:
            warnings.append(f"line:{line_no}:property-before-section")
            if strict:
                raise ValueError(warnings[-1])
            continue

        key = assignment.group(1).strip()
        raw = assignment.group(2).strip()
        parsed: Any
        shape = "atom"
        if raw.startswith("(") and raw.endswith(")"):
            inner = raw[1:-1].strip()
            parts = [part.strip() for part in inner.split(",")]
            parsed = [_parse_atom(part) for part in parts]
            shape = f"tuple{len(parsed)}"
        elif "," in raw:
            parts = [part.strip() for part in raw.split(",")]
            parsed = [_parse_atom(part) for part in parts]
            shape = f"tuple{len(parsed)}"
        else:
            parsed = _parse_atom(raw)

        spec = SECTION_SPECS.get(current["name"], {}).get(key)
        current["entries"].append({
            "name": key,
            "raw": raw,
            "value": parsed,
            "parsed_shape": shape,
            "line": line_no,
            "schema": None if spec is None else {
                "helper": spec.helper,
                "offsets": list(spec.offsets),
                "offset_hex": spec.offset_hex,
                "value_shape": spec.value_shape,
                "source": spec.source,
            },
            "recognized": spec is not None,
        })

    recognized = 0
    unknown = 0
    for section in sections:
        for entry in section["entries"]:
            if entry["recognized"]:
                recognized += 1
            else:
                unknown += 1

    return {
        "format": FORMAT,
        "version": 1,
        "source": {
            "file": SOURCE_FILE,
            "loader": SOURCE_LOADER,
        },
        "status": "parsed",
        "ready": not warnings,
        "sections": sections,
        "section_count": len(sections),
        "entry_count": sum(len(section["entries"]) for section in sections),
        "recognized_entry_count": recognized,
        "unknown_entry_count": unknown,
        "warnings": warnings,
        "handlers": {
            section["name"]: SECTION_HANDLERS.get(section["name"], "unknown")
            for section in sections
        },
        "limitations": [
            "Parser preserves numeric/string syntax but does not assign physical units.",
            "Unknown properties are retained verbatim and are not discarded.",
            "helper functions identify storage/loader boundaries only; they are not treated as unit/type declarations.",
        ],
    }


def section_entries(report: Mapping[str, Any], section: str) -> list[Mapping[str, Any]]:
    wanted = section.strip().upper()
    for row in report.get("sections") or []:
        if str(row.get("name", "")).upper() == wanted:
            return list(row.get("entries") or [])
    return []


def source_schema(section: str | None = None) -> dict[str, Any]:
    if section is not None:
        wanted = section.strip().upper()
        specs = SECTION_SPECS.get(wanted, {})
        return {
            "format": FORMAT,
            "version": 1,
            "section": wanted,
            "handler": SECTION_HANDLERS.get(wanted),
            "properties": {
                name: {
                    "helper": spec.helper,
                    "offsets": list(spec.offsets),
                    "offset_hex": spec.offset_hex,
                    "value_shape": spec.value_shape,
                    "source": spec.source,
                }
                for name, spec in sorted(specs.items())
            },
        }
    return {
        "format": FORMAT,
        "version": 1,
        "sections": {
            name: source_schema(name)["properties"]
            for name in sorted(SECTION_SPECS)
        },
        "handlers": dict(SECTION_HANDLERS),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Parse SHIFT vehicle CDF text against the recovered loader schema")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--schema-section", default=None)
    args = parser.parse_args(argv)

    if args.schema_section:
        report = source_schema(args.schema_section)
    else:
        report = parse_cdf(args.input.read_bytes(), strict=args.strict)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report.get("status", "schema"),
        "ready": report.get("ready", True),
        "sections": report.get("section_count"),
        "entries": report.get("entry_count"),
        "recognized": report.get("recognized_entry_count"),
        "unknown": report.get("unknown_entry_count"),
    }, ensure_ascii=False, indent=2))
    return 0 if report.get("ready", True) else 2


if __name__ == "__main__":
    raise SystemExit(main())
