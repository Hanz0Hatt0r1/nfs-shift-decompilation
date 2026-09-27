"""Evidence-backed SHIFT tyre/slip-curve runtime boundary."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.TireModelRuntime/1"
SOURCE = "./Source/Vehicle/tire_manager.cpp"
LOAD_FUNCTION = "FUN_007a32a0"
BUILD_CURVE_FUNCTION = "FUN_007a07c0"
EVAL_CURVE_FUNCTION = "FUN_007a0c00"
BUILD_RESPONSE_FUNCTION = "FUN_007a06a0"
TEMPERATURE_RESPONSE_FUNCTION = "FUN_007a0490"
RUNTIME_BIND_FUNCTION = "FUN_007572f0"

SLIP_CURVE_OBJECT = {
    "record_stride": 0x38,
    "compiled_segment_stride": 0x28,
    "storage_pointer_offset": 0x34,
    "count_offset": 0x30,
    "maximum_value_offset": 0x18,
    "maximum_position_offset": 0x20,
    "extrapolation_slope_offset": 0x10,
    "extrapolation_base_offset": 0x08,
}

COMPOUND_PROPERTIES = {
    "TyreLatDragReduction": 0x08,
    "TyreLongDragReduction": 0x10,
    "Style": 0x24,
    "LaunchControlFactor": 0x28,
}

SLIPCURVE_PROPERTIES = {
    "DrySlide": 0x28,
    "WetSlide": 0x30,
    "CorneringStiffness": 0x38,
    "BrakingStiffness": 0x40,
    "SelfAligningStiffness": 0x48,
    "CamberStiffnessRelative": 0x50,
    "DesignLoad": 0x58,
    "LatInitialLoadStiffnessScale": 0x5C,
    "LongInitialLoadStiffnessScale": 0x60,
    "SlipSpeedFadeMin": 0x68,
    "SlipSpeedFadeMax": 0x70,
    "RadiusRPM": 0x78,
    "Width": 0x80,
    "SpringBase": 0x88,
    "SpringkPa": 0x90,
    "Damper": 0x98,
    "SpeedEffectsMin": 0xA0,
    "SpeedEffectsMax": 0xA8,
    "LoadSensLatMin": 0xB0,
    "LoadSensLatMid": 0xB8,
    "LoadSensLatMax": 0xC0,
    "LoadSensLongMin": 0xC8,
    "LoadSensLongMid": 0xD0,
    "LoadSensLongMax": 0xD8,
    "LongTorqueSensMin": 0xE0,
    "LongTorqueSensMid": 0xE8,
    "LongTorqueSensMax": 0xF0,
    "LatPeakMin": 0xF8,
    "LatPeakMid": 0x100,
    "LatPeakMax": 0x108,
    "LongPeakMin": 0x110,
    "LongPeakMid": 0x118,
    "LongPeakMax": 0x120,
    "HeatBasePeakMin": 0x128,
    "HeatBasePeakMult": 0x130,
    "CamberLatLongMin": 0x148,
    "CamberLatLongMid": 0x150,
    "CamberLatLongMax": 0x158,
    "RollingResistance": 0x160,
    "HeatingMin": 0x168,
    "HeatingMax": 0x170,
    "TransferMin": 0x178,
    "TransferMid": 0x180,
    "TransferMax": 0x188,
    "HeatDistribMin": 0x190,
    "HeatDistribMax": 0x198,
    "AirTreadRate": 0x1A0,
    "WearRate": 0x1A8,
    "Softness": 0x1B0,
    "AISensMin": 0x1B8,
    "AISensMax": 0x1C0,
    "AIGripMult": 0x1C8,
    "AIPeakSlip": 0x1D0,
    "AIWear": 0x1D8,
    "OptimumTemp": 0x1E0,
    "TemperaturesMax": 0x1E8,
    "OptimumPressureBase": 0x1F0,
    "OptimumPressureMult": 0x1F8,
    "GripTempPressBase": 0x200,
    "GripTempPressMid": 0x208,
    "GripTempPressMax": 0x210,
    "FailureTemp": 0x218,
    "LatCurveName": 0x138,
    "BrakingCurveName": 0x13C,
    "TractiveCurveName": 0x140,
}

RUNTIME_CURVE_POINTERS = {
    "LatCurve": 0x6E0,
    "BrakingCurve": 0x6E4,
    "TractiveCurve": 0x6E8,
}

SOURCE_LINES = {
    "FUN_007a0490": 799028,
    "FUN_007a05c0": 799091,
    "FUN_007a06a0": 799143,
    "FUN_007a07c0": 799218,
    "FUN_007a0c00": 799419,
    "FUN_007a32a0": 799568,
    "FUN_007572f0": 751703,
    "FUN_00757318": 752195,
}

COMPOUND_SCOPE_TOKENS = (
    "NONE:", "FRONTLEFT:", "FRONTRIGHT:", "REARLEFT:", "REARRIGHT:",
    "FRONT:", "REAR:", "LEFT:", "RIGHT:", "ALL:",
)

@dataclass(frozen=True)
class CubicSegment:
    c3: float
    c2: float
    c1: float
    c0: float

    def evaluate(self, x: float) -> float:
        return ((self.c3 * x + self.c2) * x + self.c1) * x + self.c0


def evaluate_precompiled_curve(
    *,
    x: float,
    domain: float,
    maximum_value: float,
    extrapolation_slope: float,
    extrapolation_base: float,
    segments: list[CubicSegment],
) -> float:
    """Mirror FUN_007a0c00's observed arithmetic after the segment lookup."""
    if not segments:
        raise ValueError("curve has no compiled segments")
    scaled = (x * maximum_value) / domain if x <= domain else (
        (extrapolation_base + (extrapolation_slope / domain) * (x - domain) + 1.0)
        * maximum_value
    )
    # FUN_00715990 is ROUND(); the retail call path uses non-negative normalized inputs.
    index = int(scaled + 0.5)
    index = min(index, len(segments) - 1)
    return segments[index].evaluate(scaled)


def build_curve_contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "functions": {
            "load_tbc": LOAD_FUNCTION,
            "build_curve": BUILD_CURVE_FUNCTION,
            "evaluate_curve": EVAL_CURVE_FUNCTION,
            "build_response": BUILD_RESPONSE_FUNCTION,
            "temperature_response": TEMPERATURE_RESPONSE_FUNCTION,
            "runtime_bind": RUNTIME_BIND_FUNCTION,
        },
        "source_lines": SOURCE_LINES,
        "curve_object": SLIP_CURVE_OBJECT,
        "compound_properties": COMPOUND_PROPERTIES,
        "slipcurve_properties": SLIPCURVE_PROPERTIES,
        "runtime_curve_pointers": RUNTIME_CURVE_POINTERS,
        "compound_scope_tokens": COMPOUND_SCOPE_TOKENS,
        "runtime_derivations": {
            "inverse_origin_slope_destination": 0x6F0,
            "inverse_origin_slope_source_curve": 0x6E0,
            "inverse_origin_slope_sample": 0.0001,
            "inverse_origin_slope_denominator_scale": 0.0004,
            "heat_base_peak_product_destination": 0x6F8,
            "heat_base_peak_complement_destination": 0x700,
            "camber_sin_scale_destination": 0x718,
            "camber_lower_angle_guard_destination": 0x720,
            "camber_upper_angle_guard_destination": 0x728,
            "ambient_temperature_bias": 273.16,
            "source_file": SOURCE,
        },
        "status": "evidence-backed; physical-unit/semantic labels remain conservative",
    }


def analyze_source(source_path: str | Path) -> dict[str, Any]:
    path = Path(source_path)
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="ignore")
    needles = {
        "tbc_loader": 'FUN_007a32a0',
        "slipcurve_marker": '"[SLIPCURVE]"',
        "compound_marker": '"[COMPOUND]"',
        "lat_curve": '"LatCurve"',
        "braking_curve": '"BrakingCurve"',
        "tractive_curve": '"TractiveCurve"',
        "origin_eval": 'FUN_007a0c00(*(int *)(iVar9 + 0x6e0),0,0x3ff00000,0.0001)',
        "tire_source_tag": '"./Source/Vehicle/tire_manager.cpp"',
    }
    # The decompiler spells source paths with doubled backslashes.
    source_tag_ok = (
        "./Source/Vehicle/tire_manager.cpp" in text
        or (".\Source\Vehicle\tire_manager.cpp" in text)
    )
    checks = {
        "tbc_loader": "FUN_007a32a0" in text,
        "slipcurve_marker": '"[SLIPCURVE]"' in text,
        "compound_marker": '"[COMPOUND]"' in text,
        "lat_curve": '"LatCurve"' in text,
        "braking_curve": '"BrakingCurve"' in text,
        "tractive_curve": '"TractiveCurve"' in text,
        "origin_eval": "FUN_007a0c00(*(int *)(iVar9 + 0x6e0),0,0x3ff00000,0.0001)" in text,
        "tire_source_tag": source_tag_ok,
        "round_helper": "int FUN_00715990(float param_1)" in text,
    }
    return {
        "format": "SHIFT.TireModelSourceEvidence/1",
        "source_path": str(path),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "checks": checks,
        "ready": all(checks.values()),
        "curve_contract": build_curve_contract(),
        "needle_catalog": needles,
    }


__all__ = [
    "COMPOUND_PROPERTIES",
    "COMPOUND_SCOPE_TOKENS",
    "CubicSegment",
    "RUNTIME_CURVE_POINTERS",
    "SLIP_CURVE_OBJECT",
    "SLIPCURVE_PROPERTIES",
    "analyze_source",
    "build_curve_contract",
    "evaluate_precompiled_curve",
]
