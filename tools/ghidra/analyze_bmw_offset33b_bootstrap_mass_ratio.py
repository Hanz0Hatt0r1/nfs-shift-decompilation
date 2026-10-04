#!/usr/bin/env python3
"""Prove the BMW first-bootstrap mass ratio used by FUN_0076b280 offset33b.

This pass closes only the scalar mass factor in the retail expression:

    offset33b = (auxiliary_weighted_COM - target_CG) *
                (auxiliary_mass / BODY0_mass)

It combines exact retail function/call fingerprints, reviewed source-backed BODY
construction semantics, the exact BMW SDF/CDF resource contract, and the already
positive actual-participant additional-mass bootstrap-zero proof.  It does not
claim the COM or target-CG vectors are numeric yet.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.BMWOffset33bBootstrapMassRatio/1"
RESOURCE_FORMAT = "SHIFT.BMWOffset33bResourceInputs/1"
ADDITIONAL_MASS_FORMAT = "SHIFT.BMWOffset33bActualAdditionalMassBootstrapZero/1"
PROGRAM = "SHIFT.exe"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"

TARGETS = {
    "0x007615c0": ("FUN_007615c0", 792, "__thiscall", "0b2268dceb26dfaff8814b4091e50d48371b74083ac6d41e3d50da99cc036a22"),
    "0x0076b280": ("FUN_0076b280", 7796, "__thiscall", "9563b40c06bcc7442aabd3308eefa62e1b9f7d0bb9afe752ddf0dc068e0cd7f6"),
    "0x007b3670": ("FUN_007b3670", 430, "__thiscall", "bcf42f221ca37b7ee8f907b0783fc8da894ecc3528e86506f6d58e448a0953d3"),
    "0x007b3da0": ("FUN_007b3da0", 104, "__thiscall", "01332c7b9536deb41afbe4fe71c38e002fcac3b5936eda7d25ae8d373b5f7c12"),
    "0x007b6900": ("FUN_007b6900", 2379, "__thiscall", "154593816d7647c6cd8a0ee37b96e92c38cd78b318bd16cdbfcefb7bca3aba81"),
    "0x007bba90": ("FUN_007bba90", 125, "__thiscall", "ade565ab3fa59f77ca0ec62392629eaec5642920ea64d5b7e1760d849fb0e587"),
}

REQUIRED_DIRECT_EDGES = {
    ("0x007615c0", "0x007615ed", "0x007b6900"),
    ("0x007b6900", "0x007b6e8f", "0x007b3670"),
    ("0x007b3670", "0x007b3792", "0x007bba90"),
}

LOOKUP_CALLS = (
    "0x00761665",  # body
    "0x007616df",  # fl_wheel
    "0x007616f5",  # fl_spindle
    "0x0076170b",  # fr_wheel
    "0x00761721",  # fr_spindle
    "0x00761737",  # rl_wheel
    "0x0076174d",  # rl_spindle
    "0x00761763",  # rr_wheel
    "0x00761779",  # rr_spindle
    "0x0076178f",  # rear_axle
    "0x007617a5",  # fuel_tank
    "0x007617bb",  # driver_head
)

LOOKUP_BINDINGS = {
    "body": "HDVehicle+0x33a0",
    "fl_wheel": "HDVehicle+0x820",
    "fl_spindle": "HDVehicle+0x824",
    "fr_wheel": "HDVehicle+0x12a0",
    "fr_spindle": "HDVehicle+0x12a4",
    "rl_wheel": "HDVehicle+0x1d20",
    "rl_spindle": "HDVehicle+0x1d24",
    "rr_wheel": "HDVehicle+0x27a0",
    "rr_spindle": "HDVehicle+0x27a4",
    "rear_axle": "HDVehicle+0x2e00",
    "fuel_tank": "HDVehicle+0x280",
    "driver_head": "HDVehicle+0x298",
}

CORNER_BODIES = (
    "fl_wheel", "fl_spindle",
    "fr_wheel", "fr_spindle",
    "rl_wheel", "rl_spindle",
    "rr_wheel", "rr_spindle",
)
BODY0_NAME = "body"
DRIVER_HEAD_NAME = "driver_head"
FUEL_TANK_NAME = "fuel_tank"
OPTIONAL_REAR_AXLE_NAME = "rear_axle"


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_no}: expected JSON object")
            rows.append(value)
    return rows


def _validate_retail(ghidra_export: Path) -> dict[str, Any]:
    binary = _read_json(ghidra_export / "binary.json")
    if binary.get("program_name") != PROGRAM or binary.get("executable_md5") != PE_MD5:
        raise ValueError("retail binary identity mismatch")

    functions = {str(row.get("address") or "").lower(): row for row in _read_jsonl(ghidra_export / "functions.jsonl")}
    admitted: list[dict[str, Any]] = []
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

    edges = _read_jsonl(ghidra_export / "callgraph.jsonl")
    direct = {
        (
            str(row.get("from_function") or "").lower(),
            str(row.get("instruction") or "").lower(),
            str(row.get("to") or "").lower(),
        )
        for row in edges
        if row.get("indirect") is False
    }
    missing = sorted(REQUIRED_DIRECT_EDGES - direct)
    if missing:
        raise ValueError(f"missing required construction edge(s): {missing}")

    lookup_edges = {
        str(row.get("instruction") or "").lower()
        for row in edges
        if str(row.get("from_function") or "").lower() == "0x007615c0"
        and str(row.get("to") or "").lower() == "0x007b3da0"
        and row.get("indirect") is False
    }
    if lookup_edges != set(LOOKUP_CALLS):
        raise ValueError("FUN_007615c0 BODY lookup callsite set drift")

    return {
        "program": PROGRAM,
        "pe_md5": PE_MD5,
        "functions": admitted,
        "required_direct_edges": [
            {"from_function": a, "instruction": b, "to": c}
            for a, b, c in sorted(REQUIRED_DIRECT_EDGES)
        ],
        "body_lookup_calls": list(LOOKUP_CALLS),
    }


def _validate_additional_mass(path: Path) -> dict[str, Any]:
    report = _read_json(path)
    if report.get("format") != ADDITIONAL_MASS_FORMAT or report.get("ready") is not True:
        raise ValueError("actual additional-mass bootstrap-zero proof is not ready")
    handoff = report.get("handoff")
    proven = report.get("proven_value")
    object_graph = report.get("object_graph")
    if not isinstance(handoff, Mapping) or not isinstance(proven, Mapping) or not isinstance(object_graph, Mapping):
        raise ValueError("additional-mass proof structure missing")
    if handoff.get("offset33b_actual_additional_mass_bootstrap_zero_ready") is not True:
        raise ValueError("additional-mass zero handoff not ready")
    if handoff.get("offset33b_additional_mass_term_can_be_elided_for_first_bootstrap") is not True:
        raise ValueError("additional-mass term is not bootstrap-elidable")
    if proven.get("type") != "float32" or float(proven.get("value", 1.0)) != 0.0:
        raise ValueError("additional-mass value is not exact float32 zero")
    if int(object_graph.get("participant_additional_mass_offset", -1)) != 0xBA0:
        raise ValueError("participant additional-mass offset drift")
    if int(object_graph.get("vehicle_additional_mass_offset", -1)) != 0x860:
        raise ValueError("embedded Vehicle additional-mass offset drift")
    return report


def _validate_resources(path: Path) -> tuple[dict[str, Any], dict[str, float]]:
    report = _read_json(path)
    if report.get("format") != RESOURCE_FORMAT or report.get("ready") is not True:
        raise ValueError("BMW offset33b resource inputs are not ready")
    handoff = report.get("handoff")
    scope = report.get("scope")
    if not isinstance(handoff, Mapping) or not isinstance(scope, Mapping):
        raise ValueError("resource input handoff/scope missing")
    for field in (
        "offset33b_resource_inputs_ready",
        "offset33b_direct_CDF_load_data_mapping_ready",
        "offset33b_SDF_body_resource_values_ready",
    ):
        if handoff.get(field) is not True:
            raise ValueError(f"resource input gate {field} is not ready")
    if handoff.get("BMW_numeric_offset33b_ready") is not False:
        raise ValueError("resource input unexpectedly preclaims numeric offset33b")
    if scope.get("runtime_BODY_mass_equals_raw_SDF_mass_assumed") is not False:
        raise ValueError("upstream resource contract unexpectedly assumes runtime BODY mass identity")

    cdf = report.get("cdf")
    sdf = report.get("sdf")
    if not isinstance(cdf, Mapping) or not isinstance(sdf, Mapping):
        raise ValueError("CDF/SDF resource records missing")
    values = cdf.get("values")
    bodies = sdf.get("bodies")
    if not isinstance(values, Mapping) or not isinstance(bodies, list):
        raise ValueError("CDF values or SDF BODY list missing")
    mass = float(values.get("Mass", math.nan))
    if not math.isfinite(mass) or mass <= 0.0:
        raise ValueError("BMW CDF Mass invalid")

    body_masses: dict[str, float] = {}
    indexes: set[int] = set()
    for row in bodies:
        if not isinstance(row, Mapping):
            raise ValueError("invalid SDF BODY row")
        name = row.get("name")
        index = row.get("index")
        value = float(row.get("mass", math.nan))
        if not isinstance(name, str) or not name or not isinstance(index, int):
            raise ValueError("invalid SDF BODY identity")
        if name in body_masses or index in indexes:
            raise ValueError("duplicate SDF BODY identity")
        if not math.isfinite(value) or value < 0.0:
            raise ValueError(f"invalid SDF BODY mass for {name}")
        body_masses[name] = value
        indexes.add(index)
    if set(indexes) != set(range(len(bodies))):
        raise ValueError("SDF BODY indexes are not contiguous")
    required = {BODY0_NAME, DRIVER_HEAD_NAME, FUEL_TANK_NAME, *CORNER_BODIES}
    missing = sorted(required - set(body_masses))
    if missing:
        raise ValueError(f"required BMW BODY records missing: {missing}")
    if OPTIONAL_REAR_AXLE_NAME in body_masses:
        raise ValueError("BMW SDF unexpectedly contains rear_axle BODY")
    return report, body_masses


def analyze(
    ghidra_export: Path,
    resource_inputs_path: Path,
    additional_mass_proof_path: Path,
) -> dict[str, Any]:
    retail = _validate_retail(ghidra_export)
    resources, body_masses = _validate_resources(resource_inputs_path)
    additional = _validate_additional_mass(additional_mass_proof_path)

    cdf_mass = float(resources["cdf"]["values"]["Mass"])
    additional_mass = float(additional["proven_value"]["value"])

    corner_mass_rows = [{"name": name, "mass": body_masses[name]} for name in CORNER_BODIES]
    corner_mass = sum(row["mass"] for row in corner_mass_rows)
    # FUN_0076b280 explicitly sets fuel_tank runtime +0x120 to 1.0 before the
    # weighted-COM accumulation. The exact BMW SDF value is independently 1.0.
    sdf_fuel_mass = body_masses[FUEL_TANK_NAME]
    if sdf_fuel_mass != 1.0:
        raise ValueError("BMW fuel_tank SDF mass drifted from reviewed retail value 1.0")
    effective_fuel_mass = 1.0

    auxiliary_mass = corner_mass + effective_fuel_mass
    subtract_from_cdf_mass = auxiliary_mass
    body0_mass = cdf_mass + additional_mass - subtract_from_cdf_mass
    if body0_mass <= 0.0 or not math.isfinite(body0_mass):
        raise ValueError("computed BODY0 bootstrap mass is invalid")
    ratio = auxiliary_mass / body0_mass

    return {
        "format": FORMAT,
        "version": 1,
        "status": "bootstrap-mass-ratio-proven",
        "ready": True,
        "inputs": {
            "ghidra_export": str(ghidra_export),
            "resource_inputs": str(resource_inputs_path),
            "actual_additional_mass_proof": str(additional_mass_proof_path),
        },
        "retail": retail,
        "source_backed_semantics": {
            "BODY_construction_chain": (
                "FUN_007b6900 parses SDF BODY records -> FUN_007b3670 -> FUN_007bba90; "
                "FUN_007bba90 writes parsed mass directly to runtime BODY+0x120"
            ),
            "BODY_lookup": (
                "FUN_007b3da0 scans runtime BODY names and returns 0 when the requested name is absent"
            ),
            "HDVehicle_lookup_bindings": LOOKUP_BINDINGS,
            "driver_head_exclusion": (
                "FUN_007615c0 stores lookup('driver_head') at HDVehicle+0x298; "
                "FUN_0076b280 excludes HDVehicle+0x298 from the CDF-mass subtraction"
            ),
            "rear_axle_optional": (
                "FUN_007615c0 stores lookup('rear_axle') at HDVehicle+0x2e00; "
                "BMW SDF has no rear_axle BODY, so the lookup is null and the optional mass/COM term is absent"
            ),
            "corner_auxiliary_loop": (
                "FUN_0076b280 iterates wheel/spindle pointer pairs beginning at HDVehicle+0x820/+0x824 "
                "with 0xa80-byte corner stride and accumulates each runtime BODY+0x120 mass"
            ),
            "fuel_mass_override": "FUN_0076b280 writes runtime fuel_tank BODY+0x120 = 1.0 before accumulation",
        },
        "mass_terms": {
            "cdf_mass": cdf_mass,
            "additional_mass_first_bootstrap": additional_mass,
            "corner_bodies": corner_mass_rows,
            "corner_body_mass_sum": corner_mass,
            "fuel_tank_sdf_mass": sdf_fuel_mass,
            "fuel_tank_effective_mass": effective_fuel_mass,
            "rear_axle_present": False,
            "rear_axle_effective_mass": 0.0,
            "driver_head_mass": body_masses[DRIVER_HEAD_NAME],
            "driver_head_excluded_from_body0_mass_subtraction": True,
            "auxiliary_mass": auxiliary_mass,
            "BODY0_mass": body0_mass,
            "auxiliary_to_BODY0_mass_ratio": ratio,
        },
        "symbolic_reduction": {
            "offset33b_expression": (
                "(auxiliary_weighted_COM - target_CG) * auxiliary_to_BODY0_mass_ratio"
            ),
            "numeric_mass_factor": ratio,
            "remaining_vector_terms": ["auxiliary_weighted_COM", "target_CG"],
        },
        "handoff": {
            "offset33b_runtime_BODY_mass_construction_join_ready": True,
            "offset33b_driver_head_exclusion_ready": True,
            "offset33b_rear_axle_absence_ready": True,
            "offset33b_auxiliary_mass_ready": True,
            "offset33b_BODY0_bootstrap_mass_ready": True,
            "offset33b_mass_ratio_ready": True,
            "offset33b_auxiliary_weighted_COM_ready": False,
            "offset33b_target_CG_ready": False,
            "BMW_numeric_offset33b_ready": False,
            "BODY0_to_outer_vehicle_root_numeric_matrix_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "next_proof": {
            "target": "prove the two remaining vectors auxiliary_weighted_COM and target_CG",
            "do_not_reopen": [
                "BODY0 mass",
                "auxiliary mass",
                "driver_head identity at HDVehicle+0x298",
                "rear_axle presence",
            ],
        },
        "scope": {
            "raw_SDF_mass_promoted_globally_to_runtime_mass": False,
            "bootstrap_runtime_mass_join_is_construction_order_specific": True,
            "driver_head_included_in_auxiliary_mass": False,
            "rear_axle_mass_assumed_nonzero": False,
            "COM_or_target_CG_numeric_values_assumed": False,
            "numeric_offset33b_claimed": False,
            "original_game_executed": False,
            "runtime_capture_required": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument("resource_inputs", type=Path)
    parser.add_argument("actual_additional_mass_proof", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)
    report = analyze(args.ghidra_export, args.resource_inputs, args.actual_additional_mass_proof)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out is None:
        print(text, end="")
    else:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
