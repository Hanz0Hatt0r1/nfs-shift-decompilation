#!/usr/bin/env python3
"""Materialize the complete BMW M3 E36 first-bootstrap numeric offset33b family.

The retail producer does not have one mode-independent Y result: CGHeight is
scaled by PhysicsTweaker according to the four physics-difficulty slots and by a
normal/drift selector.  This analyzer therefore proves all eight valid numeric
branches instead of guessing the currently selected mode.

It consumes only hash/provenance/value evidence; no retail payload is committed.
The outer-Vehicle -> VHF-root relation remains an independent downstream proof.
"""
from __future__ import annotations

import argparse
import json
import math
import struct
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.BMWOffset33bNumericBootstrapFamily/1"
INPUT_FORMAT = "SHIFT.BMWOffset33bNumericBootstrapInputs/1"
RESOURCE_FORMAT = "SHIFT.BMWOffset33bResourceInputs/1"
PROGRAM = "SHIFT.exe"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"
DEFAULT_INPUTS = Path(__file__).resolve().parents[2] / "evidence" / "bmw_offset33b_numeric_bootstrap_inputs.json"
DEFAULT_RESOURCES = Path(__file__).resolve().parents[2] / "evidence" / "bmw_offset33b_resource_inputs.json"

FUNCTIONS = {
    "0x0076b280": "9563b40c06bcc7442aabd3308eefa62e1b9f7d0bb9afe752ddf0dc068e0cd7f6",
    "0x007bf0e0": "51d7f506d0fac2043e40379dfea8da9d214647941897182f1822e9eef4d7a76f",
    "0x007bfbe0": "9b5b44a1685b5bf2c1a6b681a3864109a443cca18ce9c3445ebb1516a9a0c7b8",
    "0x007c19c0": "6fdac41ffc3eafa1e12bb5ad6ca6abbaa5008103f1a5d6e1fd6d7afe12025be6",
    "0x00703f10": "eaf605926a6da4b27c2c358286f33fe720f6d4e49a78026b376dafc9ac0cda75",
    "0x00749a60": "6430fcc5bf682b1ebf36f4806bd54c89e9838b2417c35081f32e60b6f55edcc7",
}
WHEELS = ("FL", "FR", "RL", "RR")


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _f32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", float(value)))[0]


def _finite_vec(value: Any, count: int, field: str) -> list[float]:
    if not isinstance(value, list) or len(value) != count:
        raise ValueError(f"{field}: expected {count} numeric values")
    out = [float(item) for item in value]
    if not all(math.isfinite(item) for item in out):
        raise ValueError(f"{field}: non-finite value")
    return out


def _load_functions(root: Path) -> dict[str, dict[str, Any]]:
    binary = _read_json(root / "binary.json")
    if binary.get("program_name") != PROGRAM or binary.get("executable_md5") != PE_MD5:
        raise ValueError("unexpected retail executable identity")
    found: dict[str, dict[str, Any]] = {}
    with (root / "functions.jsonl").open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                continue
            address = str(row.get("address") or "").lower()
            if address in FUNCTIONS:
                found[address] = row
    for address, fingerprint in FUNCTIONS.items():
        row = found.get(address)
        if row is None:
            raise ValueError(f"missing retail function {address}")
        if row.get("mnemonic_sha256") != fingerprint:
            raise ValueError(f"{address}: mnemonic fingerprint drift")
        if row.get("external") is True or row.get("thunk") is True:
            raise ValueError(f"{address}: expected concrete retail function")
    return found


def _validate_inputs(path: Path, resource_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    inputs = _read_json(path)
    resources = _read_json(resource_path)
    if inputs.get("format") != INPUT_FORMAT or inputs.get("ready") is not True:
        raise ValueError(f"{path}: expected positive {INPUT_FORMAT}")
    if resources.get("format") != RESOURCE_FORMAT or resources.get("ready") is not True:
        raise ValueError(f"{resource_path}: expected positive {RESOURCE_FORMAT}")

    retail = inputs.get("retail") or {}
    if retail.get("program_name") != PROGRAM or retail.get("executable_md5") != PE_MD5:
        raise ValueError("numeric inputs retail identity drift")
    listed = {
        str(row.get("address") or "").lower(): row.get("mnemonic_sha256")
        for row in retail.get("functions") or []
        if isinstance(row, Mapping)
    }
    if listed != FUNCTIONS:
        raise ValueError("numeric inputs function inventory/fingerprint drift")

    cdf = inputs.get("bmw_cdf") or {}
    resource_cdf = resources.get("cdf") or {}
    if cdf.get("decoded_sha256") != resource_cdf.get("decoded_sha256"):
        raise ValueError("BMW CDF hash does not join resource-input contract")
    if float((cdf.get("general") or {}).get("Mass", -1)) != float(
        (resource_cdf.get("values") or {}).get("Mass", -2)
    ):
        raise ValueError("BMW CDF mass drift")
    if _finite_vec((cdf.get("general") or {}).get("FuelTankPos"), 3, "FuelTankPos") != _finite_vec(
        (resource_cdf.get("values") or {}).get("FuelTankPos"), 3, "resource FuelTankPos"
    ):
        raise ValueError("BMW FuelTankPos drift")
    if _finite_vec((cdf.get("general") or {}).get("GraphicalOffset"), 3, "GraphicalOffset") != _finite_vec(
        (resource_cdf.get("values") or {}).get("GraphicalOffset"), 3, "resource GraphicalOffset"
    ):
        raise ValueError("BMW GraphicalOffset drift")

    bootstrap = inputs.get("bootstrap") or {}
    required_contracts = {
        "SHIFT.BMWOffset33bBootstrapMassRatio/1",
        "SHIFT.BMWOffset33bActualAdditionalMassBootstrapZero/1",
        "SHIFT.BMWOffset33bVehicleReferenceYBootstrapZero/1",
    }
    if set(bootstrap.get("source_contracts") or []) != required_contracts:
        raise ValueError("bootstrap source-contract inventory drift")
    if float(bootstrap.get("auxiliary_mass", -1)) != 173.0:
        raise ValueError("auxiliary mass drift")
    if float(bootstrap.get("BODY0_mass", -1)) != 1287.0:
        raise ValueError("BODY0 mass drift")
    if float(bootstrap.get("additional_mass", 1)) != 0.0:
        raise ValueError("additional-mass zero proof lost")
    if float(bootstrap.get("vehicle_reference_y", 1)) != 0.0:
        raise ValueError("vehicle reference-Y zero proof lost")
    if bootstrap.get("rear_axle_present") is not False:
        raise ValueError("BMW rear-axle absence drift")
    if bootstrap.get("driver_head_in_auxiliary_COM") is not False:
        raise ValueError("driver-head exclusion drift")

    semantics = inputs.get("semantics") or {}
    for field in (
        "vdf_offsets_are_float32",
        "vdf_dimensions_are_float32",
        "cg_height_is_tuneable_float32",
        "cg_rear_range_is_tuneable_float32",
        "physics_tweaker_scales_are_float32",
        "ride_height_range_is_float64",
        "fuel_tank_pos_is_float64",
        "wheel_radius_is_second_VDF_dimension_times_half",
        "ride_height_selected_index_is_zero",
        "track_wheelbase_overrides_apply_only_when_nonzero",
    ):
        if semantics.get(field) is not True:
            raise ValueError(f"semantic gate {field} is not ready")
    return inputs, resources


def _corner_vectors(inputs: Mapping[str, Any]) -> dict[str, list[float]]:
    vdf = ((inputs.get("vehicles_global") or {}).get("vdf") or {})
    offsets = vdf.get("wheel_offsets_vec3f") or {}
    dimensions = vdf.get("wheel_dimensions_vec2f") or {}
    cdf = inputs.get("bmw_cdf") or {}
    general = cdf.get("general") or {}
    ride = cdf.get("wheel_ride_height") or {}
    defaults = cdf.get("suspension_constructor_defaults") or {}
    absent = set(cdf.get("suspension_overrides_absent") or [])
    expected_absent = {"FrontWheelTrack", "RearWheelTrack", "LeftWheelBase", "RightWheelBase"}
    if absent != expected_absent or any(float(defaults.get(name, 1.0)) != 0.0 for name in expected_absent):
        raise ValueError("track/wheelbase zero-default proof drift")

    vectors = {name: [_f32(v) for v in _finite_vec(offsets.get(name), 3, f"VDF {name} offset")] for name in WHEELS}
    if int(general.get("Symmetric", 0)) != 1:
        raise ValueError("BMW Symmetric path drift")

    front_z = (vectors["FL"][2] + vectors["FR"][2]) * 0.5
    front_x = (vectors["FL"][0] - vectors["FR"][0]) * 0.5
    rear_z = (vectors["RL"][2] + vectors["RR"][2]) * 0.5
    rear_x = (vectors["RL"][0] - vectors["RR"][0]) * 0.5
    vectors["FL"][0], vectors["FR"][0] = front_x, -front_x
    vectors["FL"][2] = vectors["FR"][2] = front_z
    vectors["RL"][0], vectors["RR"][0] = rear_x, -rear_x
    vectors["RL"][2] = vectors["RR"][2] = rear_z

    reference_y = float((inputs.get("bootstrap") or {})["vehicle_reference_y"])
    graphical_y = _f32(_finite_vec(general.get("GraphicalOffset"), 3, "GraphicalOffset")[1])
    local48 = float(reference_y - graphical_y)
    for name in WHEELS:
        dims = [_f32(v) for v in _finite_vec(dimensions.get(name), 2, f"VDF {name} dimensions")]
        radius = float(dims[1]) * 0.5
        row = ride.get(name) or {}
        rng = _finite_vec(row.get("range"), 3, f"{name} RideHeightRange")
        setting = _f32(float(row.get("setting", 999)))
        selected = int(setting)
        count = int(rng[2])
        selected = 0 if count < 1 else min(max(selected, 0), count - 1)
        if selected != 0:
            raise ValueError(f"{name}: first-bootstrap ride-height selected index drift")
        ride_height = rng[0] + selected * rng[1]
        vectors[name][1] = local48 - ride_height + radius
    return vectors


def _auxiliary_com(inputs: Mapping[str, Any], corners: Mapping[str, list[float]]) -> tuple[list[float], list[float]]:
    bootstrap = inputs.get("bootstrap") or {}
    masses = bootstrap.get("corner_runtime_masses") or {}
    fuel_mass = float(bootstrap.get("fuel_tank_runtime_mass", -1))
    if fuel_mass != 1.0:
        raise ValueError("fuel-tank runtime mass drift")
    if any(float(masses.get(name, -1)) != 43.0 for name in WHEELS):
        raise ValueError("BMW corner runtime mass drift")
    fuel_offset = _finite_vec(((inputs.get("bmw_cdf") or {}).get("general") or {}).get("FuelTankPos"), 3, "FuelTankPos")
    rear_mid = [(corners["RL"][i] + corners["RR"][i]) * 0.5 for i in range(3)]
    fuel_point = [rear_mid[i] + fuel_offset[i] for i in range(3)]
    total = sum(float(masses[name]) for name in WHEELS) + fuel_mass
    expected_total = float(bootstrap.get("auxiliary_mass"))
    if total != expected_total:
        raise ValueError("auxiliary COM mass total drift")
    weighted = [sum(corners[name][i] * float(masses[name]) for name in WHEELS) + fuel_point[i] * fuel_mass for i in range(3)]
    return [value / total for value in weighted], fuel_point


def _target_xz(inputs: Mapping[str, Any], corners: Mapping[str, list[float]]) -> tuple[float, float, float]:
    general = (inputs.get("bmw_cdf") or {}).get("general") or {}
    right_range = _finite_vec(general.get("CGRightRange"), 3, "CGRightRange")
    right_setting = int(float(general.get("CGRightSetting", 999)))
    right_fraction = right_range[0] + right_setting * right_range[1]
    rear_range = [_f32(v) for v in _finite_vec(general.get("CGRearRange"), 3, "CGRearRange")]
    rear_setting = int(_f32(float(general.get("CGRearSetting", 999))))
    rear_fraction = float(rear_range[0] + rear_setting * rear_range[1])
    left_mid = (corners["RL"][0] + corners["FL"][0]) * 0.5
    right_mid = (corners["RR"][0] + corners["FR"][0]) * 0.5
    front_mid = (corners["FR"][2] + corners["FL"][2]) * 0.5
    rear_mid = (corners["RR"][2] + corners["RL"][2]) * 0.5
    x = (right_mid - left_mid) * right_fraction + left_mid
    z = front_mid + (rear_mid - front_mid) * rear_fraction
    return x, z, rear_fraction


def _matrix(translation: list[float]) -> list[list[float]]:
    return [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [translation[0], translation[1], translation[2], 1.0],
    ]


def analyze(ghidra_export: Path, input_path: Path = DEFAULT_INPUTS, resource_path: Path = DEFAULT_RESOURCES) -> dict[str, Any]:
    _load_functions(ghidra_export)
    inputs, resources = _validate_inputs(input_path, resource_path)
    corners = _corner_vectors(inputs)
    com, fuel_point = _auxiliary_com(inputs, corners)
    target_x, target_z, rear_fraction = _target_xz(inputs, corners)

    general = (inputs.get("bmw_cdf") or {}).get("general") or {}
    cg_height = _f32(float(general.get("CGHeight")))
    bootstrap = inputs.get("bootstrap") or {}
    ratio = float(bootstrap["auxiliary_mass"]) / float(bootstrap["BODY0_mass"])
    tweaker = ((inputs.get("vehicles_global") or {}).get("physics_tweaker") or {})
    difficulty_order = list(tweaker.get("difficulty_order") or [])
    if len(difficulty_order) != 4:
        raise ValueError("physics difficulty domain must contain four modes")
    mode_scales = {
        "normal": [_f32(v) for v in _finite_vec(tweaker.get("cg_height_scale_vec4f"), 4, "CGHeight Scale")],
        "drift": [_f32(v) for v in _finite_vec(tweaker.get("drift_cg_height_scale_vec4f"), 4, "Drift CGHeight Scale")],
    }

    variants: list[dict[str, Any]] = []
    for drift_name, scales in mode_scales.items():
        for index, scale in enumerate(scales):
            target_y = float(cg_height) * float(scale)
            target = [target_x, target_y, target_z]
            offset = [(com[i] - target[i]) * ratio for i in range(3)]
            translation = [-value for value in offset]
            variants.append(
                {
                    "drift_mode": drift_name == "drift",
                    "physics_difficulty_index": index,
                    "physics_difficulty_name": difficulty_order[index],
                    "cg_height_scale_float32": scale,
                    "target_CG": target,
                    "offset33b": offset,
                    "BODY0_to_outer_vehicle_translation": translation,
                    "BODY0_to_outer_vehicle_matrix_row_vector": _matrix(translation),
                }
            )

    keys = {(v["drift_mode"], v["physics_difficulty_index"]) for v in variants}
    if keys != {(drift, index) for drift in (False, True) for index in range(4)}:
        raise ValueError("numeric mode family is incomplete")
    if not all(math.isfinite(x) for row in variants for x in row["offset33b"]):
        raise ValueError("non-finite numeric offset33b variant")

    return {
        "format": FORMAT,
        "version": 1,
        "status": "complete-mode-parametric-numeric-bind-ready",
        "ready": True,
        "inputs": {
            "numeric_bootstrap_inputs": str(input_path),
            "resource_inputs": str(resource_path),
            "ghidra_export": str(ghidra_export),
        },
        "retail": {"program_name": PROGRAM, "executable_md5": PE_MD5, "validated_function_fingerprints": FUNCTIONS},
        "resource_identity": {
            "BMW_CDF_sha256": (resources.get("cdf") or {}).get("decoded_sha256"),
            "VehiclesGlobal_sha256": ((inputs.get("vehicles_global") or {}).get("archive_sha256")),
            "BMW_VDF_sha256": (((inputs.get("vehicles_global") or {}).get("vdf") or {}).get("decoded_sha256")),
            "PhysicsTweaker_sha256": (((inputs.get("vehicles_global") or {}).get("physics_tweaker") or {}).get("decoded_sha256")),
        },
        "bootstrap_geometry": {
            "corner_vectors_after_symmetry_and_ride_height": corners,
            "fuel_tank_point": fuel_point,
            "auxiliary_weighted_COM": com,
            "auxiliary_mass": float(bootstrap["auxiliary_mass"]),
            "BODY0_mass": float(bootstrap["BODY0_mass"]),
            "mass_ratio": ratio,
            "CGRight_fraction": 0.5,
            "CGRear_fraction_float32": rear_fraction,
            "target_CG_x": target_x,
            "target_CG_z": target_z,
            "CGHeight_float32": cg_height,
        },
        "numeric_mode_family": variants,
        "handoff": {
            "offset33b_auxiliary_weighted_COM_ready": True,
            "offset33b_target_CG_mode_family_ready": True,
            "offset33b_complete_mode_dispatch_ready": True,
            "BMW_numeric_offset33b_ready": True,
            "BODY0_to_outer_vehicle_root_numeric_matrix_ready": True,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            "BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "next_proof": {
            "target": "outer Vehicle-root -> canonical BMW VHF vehicle-root owner/frame relation",
            "numeric_BODY0_to_outer_vehicle_matrix_no_longer_blocked": True,
        },
        "scope": {
            "all_four_physics_difficulty_indices_covered": True,
            "normal_and_drift_CGHeight_tables_covered": True,
            "active_mode_value_guessed": False,
            "mode_parametric_numeric_result_is_complete": True,
            "VHF_frame_identity_assumed": False,
            "original_game_executed": False,
            "runtime_capture_required": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument("--inputs", type=Path, default=DEFAULT_INPUTS)
    parser.add_argument("--resources", type=Path, default=DEFAULT_RESOURCES)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)
    report = analyze(args.ghidra_export, args.inputs, args.resources)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
