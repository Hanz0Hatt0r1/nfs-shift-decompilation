#!/usr/bin/env python3
"""Build the selector-complete BMW first-bootstrap offset33b numeric family.

This pass consumes the exact retail Ghidra database, the already hash-locked BMW
CDF/SDF contract, the positive first-bootstrap additional-mass/reference-Y
proofs, and the derived hash-locked VDF/PhysicsTweaker geometry contract.

It deliberately does not select one race/profile configuration. Instead it
proves the complete numeric family for the retail selector domain:

    use_drift_cgheight_scale : bool
    player_difficulty       : {0, 1, 2}

A singular BODY0 -> outer-Vehicle matrix remains fail-closed until those session
selectors are bound. The independent outer-Vehicle -> VHF frame join is not
claimed here.
"""
from __future__ import annotations

import argparse
import json
from decimal import Decimal, getcontext
from pathlib import Path
from typing import Any, Mapping

getcontext().prec = 50

FORMAT = "SHIFT.BMWOffset33bSelectorCompleteNumeric/1"
GEOMETRY_FORMAT = "SHIFT.BMWOffset33bSelectorGeometryInputs/1"
RESOURCE_FORMAT = "SHIFT.BMWOffset33bResourceInputs/1"
ADDITIONAL_MASS_FORMAT = "SHIFT.BMWOffset33bActualAdditionalMassBootstrapZero/1"
REFERENCE_Y_FORMAT = "SHIFT.BMWOffset33bVehicleReferenceYBootstrapZero/1"
PROGRAM = "SHIFT.exe"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"

TARGETS = {
    "0x0041a730": ("FUN_0041a730", 130, "__fastcall", "cebe6331fa7e089c4f43934fe520319c51c238cd9acfe9ca0fa791e1fbd61a42"),
    "0x00421e00": ("FUN_00421e00", 14573, "__stdcall", "3f782b4666c407d89077d9e6f7791b037f9758ee5749f172626d60e5294d9120"),
    "0x0048dd90": ("FUN_0048dd90", 62, "__thiscall", "4a0aaf95eb0b63161f35042c7164fd3b6c62ffce2c793671eb52cd9c252ccffb"),
    "0x00492250": ("FUN_00492250", 705, "__thiscall", "2e8b1580fbdda1242168ea3fc35a67657771f54c26c7bddf890f9495f1c0fdee"),
    "0x00492520": ("FUN_00492520", 247, "__thiscall", "3e976a0cb7f19144082816f872e3897626e220a20f68d4ce5ce9e5261589880f"),
    "0x00498b80": ("FUN_00498b80", 413, "__fastcall", "2068489d7f9aa5a6cac13870ec42efe8f844315ba8d143688ae3c377d620016f"),
    "0x00703f10": ("FUN_00703f10", 2268, "__stdcall", "eaf605926a6da4b27c2c358286f33fe720f6d4e49a78026b376dafc9ac0cda75"),
    "0x0070e1c0": ("FUN_0070e1c0", 73, "__fastcall", "a67813ca15bfc96a3e79f353432bef5ed6436040915ddce5aaa01e2dcc900470"),
    "0x00711210": ("FUN_00711210", 1142, "__fastcall", "3b0e2145ff980d30214560071f02bc96b67f8ffc1671c25a7fa94e1d9009d31a"),
    "0x00714560": ("FUN_00714560", 348, "__thiscall", "0fdfd115ce435f07172048099c7c8ae063842de2dcad60bfb06ca40cbba49fd4"),
    "0x00714ed0": ("FUN_00714ed0", 468, "__fastcall", "47bbffc6f5d332609171baba59e0c8f5fc44a1bff680c2ba22247110bdd72ee8"),
    "0x00747b90": ("FUN_00747b90", 36, "__fastcall", "fda8fcb2b4d9c692033d047f34517b0b63f7f13bbcc9d63f59b57d3f6719b2cd"),
    "0x00749a60": ("FUN_00749a60", 9574, "__stdcall", "6430fcc5bf682b1ebf36f4806bd54c89e9838b2417c35081f32e60b6f55edcc7"),
    "0x00753590": ("FUN_00753590", 36, "__fastcall", "6ee202414e407b405a0710dacf80832588ad4b26b428be86d3e6587663b7ec5d"),
    "0x007535f0": ("FUN_007535f0", 34, "__fastcall", "d0f3c242b7cf073c0bbd41c0c10b5009ccde7712670f7a8a2b0467b84f51dd80"),
    "0x0076b280": ("FUN_0076b280", 7796, "__thiscall", "9563b40c06bcc7442aabd3308eefa62e1b9f7d0bb9afe752ddf0dc068e0cd7f6"),
    "0x007a6be0": ("FUN_007a6be0", 192, "__fastcall", "a3adb9a0fe8e67b3c0a4b7f091c32e5665304a8a4a695f5337d1bf2d7ab34712"),
    "0x007bef40": ("FUN_007bef40", 197, "__stdcall", "650cd59bb8b0ad5257a445cd9f03cffe3aeba8e07ed8c0cdbacb38f6ffb9c263"),
    "0x007bfbe0": ("FUN_007bfbe0", 1381, "__thiscall", "9b5b44a1685b5bf2c1a6b681a3864109a443cca18ce9c3445ebb1516a9a0c7b8"),
    "0x007c5a20": ("FUN_007c5a20", 154, "__fastcall", "9d90835cda9d35e4138e5b5b00d0625952e62d096e7c5eda08e3664f416d0f27"),
    "0x00d3b190": ("FUN_00d3b190", 45, "__thiscall", "14a5001e7a917fd8dfe0d8f6ecddd2b321468185b41b9c2b8fef4c2666d6aa0a"),
}

REQUIRED_DIRECT_EDGES = {
    ("0x00498b80", "0x00498b9b", "0x0070e1c0"),
    ("0x00498b80", "0x00498c5e", "0x00492520"),
    ("0x00492520", "0x00492539", "0x00492250"),
    ("0x00492250", "0x004924d7", "0x0048dd90"),
    ("0x00711210", "0x007114b3", "0x00714560"),
    ("0x0076b280", "0x0076b9fb", "0x00747b90"),
    ("0x0076b280", "0x0076ba11", "0x007535f0"),
    ("0x0076b280", "0x0076ba29", "0x00753590"),
    ("0x0076b280", "0x0076ba41", "0x00747b90"),
    ("0x007bfbe0", "0x007bfcff", "0x007c5a20"),
    ("0x007bfbe0", "0x007bfd0a", "0x007a6be0"),
    ("0x007bfbe0", "0x007bfd32", "0x007bef40"),
}

EXPECTED_STRINGS = {
    "Player Difficulty (0-2)": ("0x00aae8f8", "0x00421e00", "0x00423e8a"),
    "MWL::PhysicsEvent_ChangeRaceMode::AddVehicleChange": ("0x00b041e8", "0x0070b880", "0x0070b8a6"),
    "MWL::Core::PhysicsParticipantManager::ChangeRaceMode": ("0x00b04708", "0x00714560", "0x007145b4"),
    "Wheel FL Offset": ("0x00b03cf4", "0x00703f10", "0x0070418e"),
    "Wheel FL Dimensions": ("0x00b03ce0", "0x00703f10", "0x007041dd"),
    "Wheel FR Offset": ("0x00b03cd0", "0x00703f10", "0x00704239"),
    "Wheel FR Dimensions": ("0x00b03cbc", "0x00703f10", "0x00704285"),
    "Wheel RL Offset": ("0x00b03cac", "0x00703f10", "0x007042de"),
    "Wheel RL Dimensions": ("0x00b03c98", "0x00703f10", "0x0070432d"),
    "Wheel RR Offset": ("0x00b03c88", "0x00703f10", "0x00704386"),
    "Wheel RR Dimensions": ("0x00b03c74", "0x00703f10", "0x007043d5"),
    "CGHeight Scale": ("0x00b07c9c", "0x00749a60", "0x0074b572"),
    "Drift CGHeight Scale": ("0x00b07c84", "0x00749a60", "0x0074b5d5"),
}

EXPECTED_GEOMETRY = {
    "vdf_sha": "f4c925bc6799439a12906d0aed9b73e22052cb46f7fbd4ea6f48409b9776a082",
    "tweaker_sha": "6cdd05f0512d367c8ce240cb13dd22fe10fb3e21da95185ea8f79e1ca67ca62f",
    "tire_sha": "93277c754fb0f6ed76d683acd89c261d8d18b7bcf26ffbd76c5bf50846eb9df3",
    "cdf_sha": "bbee83f0d2fdcbfc2bbd62ddb2a10bf6fed71bb1b4fa78f303a4730d038b970d",
    "wheel_offsets": {
        "fl": ["0.711", "0.31", "-1.35"],
        "fr": ["-0.711", "0.31", "-1.35"],
        "rl": ["0.7225", "0.31", "1.35"],
        "rr": ["-0.7225", "0.31", "1.35"],
    },
    "wheel_dimensions": {
        "fl": ["0.225", "0.62"],
        "fr": ["0.225", "0.62"],
        "rl": ["0.225", "0.62"],
        "rr": ["0.225", "0.62"],
    },
    "cdf": {
        "CGHeight": "0.28",
        "CGRightRange": ["0.5", "0.0", "0"],
        "CGRightSetting": 0,
        "CGRearRange": ["0.47", "0.0", "0"],
        "CGRearSetting": 0,
        "front_RideHeightRange": ["0.1", "-0.005", "6"],
        "front_RideHeightSetting": 0,
        "rear_RideHeightRange": ["0.11", "-0.005", "6"],
        "rear_RideHeightSetting": 0,
    },
    "normal_scale": ["0.6", "0.6", "0.75", "0.825"],
    "drift_scale": ["0.25", "0.25", "0.25", "0.67"],
    "valid_difficulty": [0, 1, 2],
}

CORNER_BODY_PAIRS = {
    "fl": ("fl_wheel", "fl_spindle"),
    "fr": ("fr_wheel", "fr_spindle"),
    "rl": ("rl_wheel", "rl_spindle"),
    "rr": ("rr_wheel", "rr_spindle"),
}


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, 1):
            if not raw.strip():
                continue
            value = json.loads(raw)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_no}: expected object")
            rows.append(value)
    return rows


def _d(value: Any) -> Decimal:
    if isinstance(value, bool):
        raise ValueError("boolean is not numeric input")
    return Decimal(str(value))


def _vec(values: Any, size: int, field: str) -> list[Decimal]:
    if not isinstance(values, list) or len(values) != size:
        raise ValueError(f"{field}: expected {size}-component vector")
    return [_d(value) for value in values]


def _validate_retail(root: Path) -> dict[str, Any]:
    binary = _read_json(root / "binary.json")
    if binary.get("program_name") != PROGRAM or binary.get("executable_md5") != PE_MD5:
        raise ValueError("retail binary identity mismatch")

    functions = {
        str(row.get("address") or "").lower(): row
        for row in _read_jsonl(root / "functions.jsonl")
    }
    admitted = []
    for address, (name, size, convention, digest) in TARGETS.items():
        row = functions.get(address)
        if row is None:
            raise ValueError(f"missing retail function {address}")
        if row.get("name") != name or int(row.get("size", -1)) != size:
            raise ValueError(f"{address}: function identity drift")
        if row.get("calling_convention") != convention:
            raise ValueError(f"{address}: calling convention drift")
        if row.get("mnemonic_sha256") != digest:
            raise ValueError(f"{address}: mnemonic fingerprint drift")
        admitted.append({
            "address": address,
            "name": name,
            "size": size,
            "calling_convention": convention,
            "mnemonic_sha256": digest,
        })

    direct = {
        (
            str(row.get("from_function") or "").lower(),
            str(row.get("instruction") or "").lower(),
            str(row.get("to") or "").lower(),
        )
        for row in _read_jsonl(root / "callgraph.jsonl")
        if row.get("indirect") is False
    }
    missing = sorted(REQUIRED_DIRECT_EDGES - direct)
    if missing:
        raise ValueError(f"missing required direct edge(s): {missing}")

    strings = _read_jsonl(root / "strings_xrefs.jsonl")
    by_value = {str(row.get("value") or ""): row for row in strings}
    string_proof = []
    for value, (address, function, xref) in EXPECTED_STRINGS.items():
        row = by_value.get(value)
        if row is None or str(row.get("address") or "").lower() != address:
            raise ValueError(f"retail string anchor drift: {value}")
        functions_seen = {str(v).lower() for v in row.get("functions") or []}
        xrefs_seen = {str(v).lower() for v in row.get("xrefs") or []}
        if function not in functions_seen or xref not in xrefs_seen:
            raise ValueError(f"retail string xref drift: {value}")
        string_proof.append({
            "value": value,
            "address": address,
            "function": function,
            "xref": xref,
        })

    return {
        "program": PROGRAM,
        "pe_md5": PE_MD5,
        "functions": admitted,
        "required_direct_edges": [
            {"from_function": a, "instruction": b, "to": c}
            for a, b, c in sorted(REQUIRED_DIRECT_EDGES)
        ],
        "string_anchors": string_proof,
    }


def _validate_geometry(path: Path) -> dict[str, Any]:
    report = _read_json(path)
    if report.get("format") != GEOMETRY_FORMAT or report.get("ready") is not True:
        raise ValueError("selector geometry inputs are not ready")
    sources = report.get("sources")
    vdf = report.get("vdf")
    cdf = report.get("cdf_selector_inputs")
    tweaker = report.get("physics_tweaker")
    selector = report.get("selector_contract")
    scope = report.get("scope")
    if not all(isinstance(v, Mapping) for v in (sources, vdf, cdf, tweaker, selector, scope)):
        raise ValueError("selector geometry input structure missing")

    if sources["vehicle_vdf"]["entry"]["decoded_sha256"] != EXPECTED_GEOMETRY["vdf_sha"]:
        raise ValueError("BMW VDF decoded identity drift")
    if sources["physics_tweaker"]["entry"]["decoded_sha256"] != EXPECTED_GEOMETRY["tweaker_sha"]:
        raise ValueError("PhysicsTweaker decoded identity drift")
    if sources["street_1_tire"]["entry"]["decoded_sha256"] != EXPECTED_GEOMETRY["tire_sha"]:
        raise ValueError("Street_1 decoded identity drift")
    if sources["bmw_cdf"]["decoded_sha256"] != EXPECTED_GEOMETRY["cdf_sha"]:
        raise ValueError("BMW CDF decoded identity drift")

    if vdf.get("vehicle_tyres") != "Street_1":
        raise ValueError("BMW VDF tire selection drift")
    for field in ("wheel_offsets", "wheel_dimensions"):
        rows = vdf.get(field)
        if not isinstance(rows, Mapping) or set(rows) != set(EXPECTED_GEOMETRY[field]):
            raise ValueError(f"BMW VDF {field} corner set drift")
        for corner, expected in EXPECTED_GEOMETRY[field].items():
            if [_d(x) for x in rows[corner]] != [Decimal(x) for x in expected]:
                raise ValueError(f"BMW VDF {field}.{corner} drift")
    for field, expected in EXPECTED_GEOMETRY["cdf"].items():
        observed = cdf.get(field)
        if isinstance(expected, list):
            if [_d(x) for x in observed or []] != [Decimal(x) for x in expected]:
                raise ValueError(f"BMW CDF selector field {field} drift")
        elif isinstance(expected, int):
            if observed != expected:
                raise ValueError(f"BMW CDF selector field {field} drift")
        elif _d(observed) != Decimal(expected):
            raise ValueError(f"BMW CDF selector field {field} drift")
    if [_d(x) for x in tweaker.get("CGHeight Scale", [])] != [Decimal(x) for x in EXPECTED_GEOMETRY["normal_scale"]]:
        raise ValueError("normal CGHeight Scale drift")
    if [_d(x) for x in tweaker.get("Drift CGHeight Scale", [])] != [Decimal(x) for x in EXPECTED_GEOMETRY["drift_scale"]]:
        raise ValueError("drift CGHeight Scale drift")
    if selector.get("valid_player_difficulty") != EXPECTED_GEOMETRY["valid_difficulty"]:
        raise ValueError("Player Difficulty domain drift")
    if selector.get("array_index_3_is_valid_player_difficulty") is not False:
        raise ValueError("Player Difficulty index 3 must remain out of domain")
    if selector.get("player_difficulty_property") != "Player Difficulty (0-2)":
        raise ValueError("Player Difficulty semantic anchor drift")
    if scope.get("single_profile_default_assumed_for_numeric_family") is not False:
        raise ValueError("selector family must not assume one profile default")
    return report


def _validate_resource_inputs(path: Path) -> tuple[dict[str, Any], dict[str, Decimal]]:
    report = _read_json(path)
    if report.get("format") != RESOURCE_FORMAT or report.get("ready") is not True:
        raise ValueError("BMW resource inputs are not ready")
    cdf = report.get("cdf")
    sdf = report.get("sdf")
    if not isinstance(cdf, Mapping) or not isinstance(sdf, Mapping):
        raise ValueError("BMW CDF/SDF inputs missing")
    if cdf.get("decoded_sha256") != EXPECTED_GEOMETRY["cdf_sha"]:
        raise ValueError("resource-input CDF identity disagrees with geometry contract")
    mapping = report.get("fun_0076b280_load_data_mapping")
    if not isinstance(mapping, Mapping):
        raise ValueError("FUN_0076b280 load-data mapping missing")
    if mapping.get("derived_load_data_offsets_not_promoted_from_resource_name") != [824]:
        raise ValueError("derived VehicleLoadData+0x338 frontier drift")
    values = cdf.get("values")
    bodies = sdf.get("bodies")
    if not isinstance(values, Mapping) or not isinstance(bodies, list):
        raise ValueError("BMW resource values missing")

    if _vec(values.get("GraphicalOffset"), 3, "GraphicalOffset") != [Decimal(0)] * 3:
        raise ValueError("BMW GraphicalOffset must be exact zero for this bootstrap proof")
    body_masses: dict[str, Decimal] = {}
    for row in bodies:
        if not isinstance(row, Mapping) or not isinstance(row.get("name"), str):
            raise ValueError("invalid SDF BODY row")
        body_masses[row["name"]] = _d(row.get("mass"))
    required = {"body", "fuel_tank", "driver_head"}
    for pair in CORNER_BODY_PAIRS.values():
        required.update(pair)
    missing = sorted(required - set(body_masses))
    if missing:
        raise ValueError(f"required BODY masses missing: {missing}")
    if "rear_axle" in body_masses:
        raise ValueError("BMW SDF unexpectedly has rear_axle")
    return report, body_masses


def _validate_additional_mass(path: Path) -> dict[str, Any]:
    report = _read_json(path)
    if report.get("format") != ADDITIONAL_MASS_FORMAT or report.get("ready") is not True:
        raise ValueError("additional-mass bootstrap proof not ready")
    handoff = report.get("handoff")
    proven = report.get("proven_value")
    if not isinstance(handoff, Mapping) or not isinstance(proven, Mapping):
        raise ValueError("additional-mass proof structure missing")
    if handoff.get("offset33b_actual_additional_mass_bootstrap_zero_ready") is not True:
        raise ValueError("additional-mass zero handoff not ready")
    if proven.get("bits") != "0x00000000" or _d(proven.get("value")) != 0:
        raise ValueError("additional-mass proof is not exact zero")
    return report


def _validate_reference_y(path: Path) -> dict[str, Any]:
    report = _read_json(path)
    if report.get("format") != REFERENCE_Y_FORMAT or report.get("ready") is not True:
        raise ValueError("vehicle-reference-Y bootstrap proof not ready")
    handoff = report.get("handoff")
    join = report.get("offset33b_join")
    if not isinstance(handoff, Mapping) or not isinstance(join, Mapping):
        raise ValueError("vehicle-reference-Y proof structure missing")
    if handoff.get("offset33b_vehicle_reference_y_bootstrap_zero_ready") is not True:
        raise ValueError("vehicle-reference-Y zero handoff not ready")
    if join.get("reduced_expression") != "-effective_graphical_offset_y":
        raise ValueError("vehicle-reference-Y reduced expression drift")
    return report


def _selected_range(spec: list[Decimal], setting: int, label: str) -> Decimal:
    if len(spec) != 3:
        raise ValueError(f"{label}: expected base/step/count")
    base, step, count = spec
    if count != count.to_integral_value() or int(count) < 0:
        raise ValueError(f"{label}: invalid count")
    if int(count) == 0:
        if setting != 0:
            raise ValueError(f"{label}: fixed range requires setting 0")
        return base
    if setting < 0 or setting >= int(count):
        raise ValueError(f"{label}: setting outside range")
    return base + step * Decimal(setting)


def _as_float(values: list[Decimal]) -> list[float]:
    return [float(v) for v in values]


def _decimal_text(value: Decimal) -> str:
    return "0" if value == 0 else str(value)


def _decimals(values: list[Decimal]) -> list[str]:
    return [_decimal_text(v) for v in values]


def _translation_matrix(translation: list[Decimal]) -> list[list[float]]:
    return [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [float(translation[0]), float(translation[1]), float(translation[2]), 1.0],
    ]


def analyze(
    ghidra_export: Path,
    resource_inputs_path: Path,
    additional_mass_path: Path,
    reference_y_path: Path,
    geometry_inputs_path: Path,
) -> dict[str, Any]:
    retail = _validate_retail(ghidra_export)
    geometry = _validate_geometry(geometry_inputs_path)
    resources, body_masses = _validate_resource_inputs(resource_inputs_path)
    additional = _validate_additional_mass(additional_mass_path)
    _validate_reference_y(reference_y_path)

    cdf_values = resources["cdf"]["values"]
    vdf = geometry["vdf"]
    cdf = geometry["cdf_selector_inputs"]
    tweaker = geometry["physics_tweaker"]
    selector = geometry["selector_contract"]

    vehicle_reference_y = Decimal(0)
    graphical_offset_y = _d(cdf_values["GraphicalOffset"][1])
    if vehicle_reference_y != 0 or graphical_offset_y != 0:
        raise ValueError("reviewed BMW bootstrap requires zero reference-Y and GraphicalOffset.y")

    front_ride = _selected_range(
        _vec(cdf["front_RideHeightRange"], 3, "front_RideHeightRange"),
        int(cdf["front_RideHeightSetting"]),
        "front RideHeight",
    )
    rear_ride = _selected_range(
        _vec(cdf["rear_RideHeightRange"], 3, "rear_RideHeightRange"),
        int(cdf["rear_RideHeightSetting"]),
        "rear RideHeight",
    )

    wheel_offsets = {
        corner: _vec(values, 3, f"wheel_offsets.{corner}")
        for corner, values in vdf["wheel_offsets"].items()
    }
    wheel_dimensions = {
        corner: _vec(values, 2, f"wheel_dimensions.{corner}")
        for corner, values in vdf["wheel_dimensions"].items()
    }
    if set(wheel_offsets) != set(CORNER_BODY_PAIRS) or set(wheel_dimensions) != set(CORNER_BODY_PAIRS):
        raise ValueError("BMW VDF corner set drift")

    corrected: dict[str, list[Decimal]] = {}
    for corner in ("fl", "fr", "rl", "rr"):
        point = list(wheel_offsets[corner])
        ride = front_ride if corner in {"fl", "fr"} else rear_ride
        half_second_wheel_dimension = wheel_dimensions[corner][1] / Decimal(2)
        point[1] = vehicle_reference_y - graphical_offset_y - ride + half_second_wheel_dimension
        corrected[corner] = point

    pair_masses: dict[str, Decimal] = {}
    weighted = [Decimal(0), Decimal(0), Decimal(0)]
    auxiliary_mass = Decimal(0)
    for corner, names in CORNER_BODY_PAIRS.items():
        mass = body_masses[names[0]] + body_masses[names[1]]
        pair_masses[corner] = mass
        auxiliary_mass += mass
        for axis in range(3):
            weighted[axis] += corrected[corner][axis] * mass

    if body_masses["fuel_tank"] != 1:
        raise ValueError("BMW fuel_tank SDF mass drift")
    effective_fuel_mass = Decimal(1)
    rear_midpoint = [
        (corrected["rl"][axis] + corrected["rr"][axis]) / Decimal(2)
        for axis in range(3)
    ]
    fuel_pos = _vec(cdf_values["FuelTankPos"], 3, "FuelTankPos")
    fuel_motion = _vec(cdf_values["FuelTankMotion"], 2, "FuelTankMotion")
    if fuel_motion[0] == 0:
        raise ValueError("FuelTankMotion spring term is zero")
    fuel_anchor = list(rear_midpoint)
    fuel_anchor[1] = vehicle_reference_y - graphical_offset_y
    fuel_point = [fuel_anchor[axis] + fuel_pos[axis] for axis in range(3)]
    fuel_point[1] -= Decimal("9.81") / fuel_motion[0]
    auxiliary_mass += effective_fuel_mass
    for axis in range(3):
        weighted[axis] += fuel_point[axis] * effective_fuel_mass

    auxiliary_com = [value / auxiliary_mass for value in weighted]

    cdf_mass = _d(cdf_values["Mass"])
    additional_mass = _d(additional["proven_value"]["value"])
    body0_mass = cdf_mass + additional_mass - auxiliary_mass
    if body0_mass <= 0:
        raise ValueError("computed BODY0 bootstrap mass is not positive")
    mass_ratio = auxiliary_mass / body0_mass

    left_x = (corrected["fl"][0] + corrected["rl"][0]) / Decimal(2)
    right_x = (corrected["fr"][0] + corrected["rr"][0]) / Decimal(2)
    front_z = (corrected["fl"][2] + corrected["fr"][2]) / Decimal(2)
    rear_z = (corrected["rl"][2] + corrected["rr"][2]) / Decimal(2)

    cg_right = _selected_range(
        _vec(cdf["CGRightRange"], 3, "CGRightRange"),
        int(cdf["CGRightSetting"]),
        "CGRight",
    )
    cg_rear = _selected_range(
        _vec(cdf["CGRearRange"], 3, "CGRearRange"),
        int(cdf["CGRearSetting"]),
        "CGRear",
    )
    target_x = left_x + (right_x - left_x) * cg_right
    target_z = front_z + (rear_z - front_z) * cg_rear
    cg_height = _d(cdf["CGHeight"])

    normal_scales = [_d(v) for v in tweaker["CGHeight Scale"]]
    drift_scales = [_d(v) for v in tweaker["Drift CGHeight Scale"]]
    valid_difficulties = list(selector["valid_player_difficulty"])

    family = []
    unique: dict[tuple[str, ...], dict[str, Any]] = {}
    for use_drift in (False, True):
        scales = drift_scales if use_drift else normal_scales
        for difficulty in valid_difficulties:
            scale = scales[difficulty]
            target = [target_x, cg_height * scale, target_z]
            offset = [
                (auxiliary_com[axis] - target[axis]) * mass_ratio
                for axis in range(3)
            ]
            translation = [-value for value in offset]
            row = {
                "use_drift_cgheight_scale": use_drift,
                "player_difficulty": difficulty,
                "cgheight_scale": float(scale),
                "target_CG": _as_float(target),
                "target_CG_decimal": _decimals(target),
                "offset33b": _as_float(offset),
                "offset33b_decimal": _decimals(offset),
                "BODY0_to_outer_vehicle_root_translation": _as_float(translation),
                "BODY0_to_outer_vehicle_root_translation_decimal": _decimals(translation),
                "BODY0_to_outer_vehicle_root_row_vector_matrix": _translation_matrix(translation),
            }
            family.append(row)
            key = tuple(_decimals(translation))
            unique.setdefault(key, {
                "translation_decimal": list(key),
                "selectors": [],
            })["selectors"].append({
                "use_drift_cgheight_scale": use_drift,
                "player_difficulty": difficulty,
            })

    return {
        "format": FORMAT,
        "version": 1,
        "status": "selector-complete-numeric-family-ready",
        "ready": True,
        "inputs": {
            "ghidra_export": str(ghidra_export),
            "resource_inputs": str(resource_inputs_path),
            "additional_mass_proof": str(additional_mass_path),
            "vehicle_reference_y_proof": str(reference_y_path),
            "selector_geometry_inputs": str(geometry_inputs_path),
        },
        "retail": retail,
        "source_backed_selector_semantics": {
            "change_race_mode_packet": (
                "FUN_0070e1c0 creates event type 0x20; FUN_00498b80 fills packet+0xc via "
                "FUN_00492520 -> FUN_00492250; FUN_00711210 case 0x20 calls FUN_00714560"
            ),
            "difficulty": (
                "FUN_00492250 reads profile/options +0x10f4 and passes it as FUN_0048dd90 param_3; "
                "FUN_0048dd90 writes RaceModeInfo+0x6c; reflected field is 'Player Difficulty (0-2)'"
            ),
            "default_difficulty": (
                "FUN_0041a730 writes profile/options +0x10f4 = 1; FUN_00d3b190 is the setter"
            ),
            "selector_staging": (
                "FUN_00714560 copies packet RaceModeInfo+0x00..0x7b into manager staging +0x3b4; "
                "FUN_00714ed0 copies the same 0x7c-byte staging block into DAT_00c12860. "
                "Therefore RaceModeInfo+0x0e -> DAT_00c1286e and +0x6c -> DAT_00c128cc."
            ),
            "drift_scale_selector": (
                "FUN_00492250 writes RaceModeInfo+0x0e for its reviewed race-mode branch; "
                "FUN_007bfbe0 chooses CGHeight Scale vs Drift CGHeight Scale from "
                "DAT_00c1286e and indexes the selected Vec4f with DAT_00c128cc"
            ),
            "difficulty_domain": valid_difficulties,
            "profile_default_is_required_for_family": False,
        },
        "bootstrap_geometry": {
            "wheel_dimension_component_used": 1,
            "wheel_dimension_component_operation": "second VDF Wheel * Dimensions component / 2",
            "fuel_anchor_y_overwritten_with_vehicle_reference_y_before_FuelTankPos": True,
            "corrected_wheel_points": {
                corner: _as_float(corrected[corner]) for corner in ("fl", "fr", "rl", "rr")
            },
            "corrected_wheel_points_decimal": {
                corner: _decimals(corrected[corner]) for corner in ("fl", "fr", "rl", "rr")
            },
            "corner_pair_masses": {corner: float(value) for corner, value in pair_masses.items()},
            "fuel_point": _as_float(fuel_point),
            "fuel_point_decimal": _decimals(fuel_point),
            "auxiliary_mass": float(auxiliary_mass),
            "BODY0_mass": float(body0_mass),
            "mass_ratio": float(mass_ratio),
            "mass_ratio_decimal": str(mass_ratio),
            "auxiliary_weighted_COM": _as_float(auxiliary_com),
            "auxiliary_weighted_COM_decimal": _decimals(auxiliary_com),
            "target_CG_x": float(target_x),
            "target_CG_z": float(target_z),
        },
        "selector_family": family,
        "unique_BODY0_to_outer_vehicle_root_translations": list(unique.values()),
        "handoff": {
            "offset33b_auxiliary_weighted_COM_ready": True,
            "offset33b_target_CG_selector_family_ready": True,
            "BMW_numeric_offset33b_selector_family_ready": True,
            "BODY0_to_outer_vehicle_root_selector_family_ready": True,
            "BMW_numeric_offset33b_ready_when_race_mode_selector_bound": True,
            "BODY0_to_outer_vehicle_root_numeric_matrix_ready_when_selector_bound": True,
            "BMW_numeric_offset33b_ready": False,
            "BODY0_to_outer_vehicle_root_numeric_matrix_ready": False,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "blockers": [
            {
                "id": "race-mode-selector-not-bound-to-native-bootstrap",
                "required_evidence": (
                    "supply the source-backed ChangeRaceMode selector pair "
                    "(use_drift_cgheight_scale, Player Difficulty 0..2) to the native bootstrap"
                ),
            },
            {
                "id": "outer-vehicle-root-to-VHF-vehicle-root-frame-join-unproven",
                "required_evidence": (
                    "prove the static/dynamic affine relation from the concrete outer Vehicle root "
                    "to the VHF vehicle-root/assembly frame before promoting BODY0 bind/world transform"
                ),
            },
        ],
        "scope": {
            "single_profile_default_assumed": False,
            "player_difficulty_index_3_admitted": False,
            "VDF_dimensions_component_0_used_for_corner_y": False,
            "rear_midpoint_y_retained_for_fuel_anchor": False,
            "raw_retail_resource_bytes_committed": False,
            "BODY0_to_outer_vehicle_rotation_identity_reused_from_existing_symbolic_proof": True,
            "outer_vehicle_to_VHF_identity_assumed": False,
            "BODY0_bind_frame_proof_invented": False,
            "vehicle_world_transform_ready": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument("resource_inputs", type=Path)
    parser.add_argument("additional_mass_proof", type=Path)
    parser.add_argument("vehicle_reference_y_proof", type=Path)
    parser.add_argument(
        "--geometry",
        type=Path,
        default=Path(__file__).resolve().parents[2]
        / "evidence"
        / "bmw_offset33b_selector_geometry_inputs.json",
    )
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)

    report = analyze(
        args.ghidra_export,
        args.resource_inputs,
        args.additional_mass_proof,
        args.vehicle_reference_y_proof,
        args.geometry,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
