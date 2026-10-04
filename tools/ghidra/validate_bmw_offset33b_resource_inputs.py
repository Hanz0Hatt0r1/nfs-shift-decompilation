#!/usr/bin/env python3
"""Validate hash-locked BMW resource inputs for the offset33b numeric proof.

The pass deliberately stops before assigning any resource value to a machine
LOAD.  It validates archive/resource identity and joins only the already
source-backed CDF parser offsets to FUN_0076b280's load-data layout (+0x8).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]
PHYSICS = ROOT / "src" / "physics"
if str(PHYSICS) not in sys.path:
    sys.path.insert(0, str(PHYSICS))

import vehicle_cdf_runtime as _cdf

FORMAT = "SHIFT.BMWOffset33bResourceInputsValidation/1"
INPUT_FORMAT = "SHIFT.BMWOffset33bResourceInputs/1"
MANIFEST_FORMAT = "SHIFT.BMWM3VehiclePhysicsResourceManifest/1"
BODY0_FORMAT = "SHIFT.BMWBody0BindResourceMaterialization/1"
ARCHIVE_SHA256 = "c31d34a0a7cab04bcff693fa0cbda3400f50d690a9c8bb2521b2882fc2a68d70"
CDF_PATH = "vehicles/physics/chassis/bmw_m3_e36.cdf"
CDF_SHA256 = "bbee83f0d2fdcbfc2bbd62ddb2a10bf6fed71bb1b4fa78f303a4730d038b970d"
SDF_PATH = "vehicles/physics/suspension/aarm_multilink.sdf"
SDF_SHA256 = "fe0b18e95e81f87d67076b70890965a0a1384a925bfd836aaf5aa705fc4781ed"
DIRECT_FIELDS = ("Mass", "GraphicalOffset", "FuelTankPos", "FuelTankMotion")
EXPECTED_BODY_NAMES = (
    "body", "fl_spindle", "fr_spindle", "fl_wheel", "fr_wheel",
    "rl_spindle", "rr_spindle", "rl_wheel", "rr_wheel",
    "fuel_tank", "driver_head",
)


def _load(path: Path, expected: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("format") != expected:
        raise ValueError(f"{path}: expected {expected}")
    return value


def _finite(value: Any, label: str) -> None:
    values: Sequence[Any]
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        values = [value]
    elif isinstance(value, list):
        values = value
    else:
        raise ValueError(f"{label}: expected numeric scalar/list")
    if not values:
        raise ValueError(f"{label}: empty numeric value")
    for item in values:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise ValueError(f"{label}: non-numeric value")
        if not math.isfinite(float(item)):
            raise ValueError(f"{label}: non-finite value")


def _manifest_entry(manifest: Mapping[str, Any], path: str) -> Mapping[str, Any]:
    rows = manifest.get("archive_entry_points")
    if not isinstance(rows, list):
        raise ValueError("physics manifest archive_entry_points missing")
    matches = [row for row in rows if isinstance(row, Mapping) and row.get("path") == path]
    if len(matches) != 1:
        raise ValueError(f"physics manifest expected exactly one {path}")
    return matches[0]


def validate(inputs_path: Path, manifest_path: Path, body0_path: Path) -> dict[str, Any]:
    inputs = _load(inputs_path, INPUT_FORMAT)
    manifest = _load(manifest_path, MANIFEST_FORMAT)
    body0 = _load(body0_path, BODY0_FORMAT)
    if inputs.get("ready") is not True:
        raise ValueError("offset33b resource inputs are not ready")

    archive = inputs.get("retail_archive") or {}
    if archive.get("filename") != "BMW_M3_E36.bff" or archive.get("sha256") != ARCHIVE_SHA256:
        raise ValueError("BMW archive identity drift")

    cdf = inputs.get("cdf") or {}
    sdf = inputs.get("sdf") or {}
    if cdf.get("path") != CDF_PATH or cdf.get("decoded_sha256") != CDF_SHA256:
        raise ValueError("BMW CDF identity drift")
    if sdf.get("path") != SDF_PATH or sdf.get("decoded_sha256") != SDF_SHA256:
        raise ValueError("BMW SDF identity drift")

    for observed, expected_index, expected_type, expected_z, expected_u in (
        (cdf, 1088, 2, 5358, 24817),
        (sdf, 1091, 2, 1110, 5056),
    ):
        if int(observed.get("entry_index", -1)) != expected_index:
            raise ValueError("BMW resource entry index drift")
        if int(observed.get("compression_type", -1)) != expected_type:
            raise ValueError("BMW resource compression type drift")
        if int(observed.get("compressed_size", -1)) != expected_z or int(observed.get("uncompressed_size", -1)) != expected_u:
            raise ValueError("BMW resource size drift")

    for path, observed in ((CDF_PATH, cdf), (SDF_PATH, sdf)):
        manifest_row = _manifest_entry(manifest, path)
        if manifest_row.get("sha256") != observed.get("decoded_sha256"):
            raise ValueError(f"{path}: manifest SHA drift")
        for field in ("entry_index", "compressed_size", "uncompressed_size", "type"):
            observed_field = "compression_type" if field == "type" else field
            if int(manifest_row.get(field, -1)) != int(observed.get(observed_field, -2)):
                raise ValueError(f"{path}: manifest {field} drift")

    values = cdf.get("values")
    if not isinstance(values, Mapping):
        raise ValueError("CDF values missing")
    for name in (*DIRECT_FIELDS, "CGHeight"):
        if name not in values:
            raise ValueError(f"CDF value missing: {name}")
        _finite(values[name], f"CDF.{name}")

    mapping = inputs.get("fun_0076b280_load_data_mapping") or {}
    rows = mapping.get("direct_fields")
    if not isinstance(rows, list) or len(rows) != len(DIRECT_FIELDS):
        raise ValueError("FUN_0076b280 direct CDF mapping incomplete")
    by_name = {str(row.get("semantic_field", "")).rsplit(".", 1)[-1]: row for row in rows if isinstance(row, Mapping)}
    if set(by_name) != set(DIRECT_FIELDS):
        raise ValueError("FUN_0076b280 direct CDF field set drift")
    for name in DIRECT_FIELDS:
        row = by_name[name]
        spec = _cdf.GENERAL.get(name)
        if spec is None:
            raise ValueError(f"source-backed CDF schema lost {name}")
        parser_offsets = row.get("cdf_parser_offsets")
        load_offsets = row.get("load_data_offsets")
        if parser_offsets != list(spec.offsets):
            raise ValueError(f"{name}: CDF parser offset drift")
        if load_offsets != [offset + 8 for offset in spec.offsets]:
            raise ValueError(f"{name}: FUN_0076b280 load-data offset drift")
        if row.get("value") != values[name]:
            raise ValueError(f"{name}: mapped value drift")

    derived = mapping.get("derived_load_data_offsets_not_promoted_from_resource_name")
    if derived != [0x338]:
        raise ValueError("derived load-data frontier must retain only +0x338")

    bodies = sdf.get("bodies")
    if not isinstance(bodies, list) or len(bodies) != len(EXPECTED_BODY_NAMES):
        raise ValueError("SDF BODY table size drift")
    for index, (row, expected_name) in enumerate(zip(bodies, EXPECTED_BODY_NAMES)):
        if not isinstance(row, Mapping):
            raise ValueError(f"SDF BODY[{index}] malformed")
        if int(row.get("index", -1)) != index or row.get("name") != expected_name:
            raise ValueError(f"SDF BODY[{index}] identity drift")
        _finite(row.get("mass"), f"SDF BODY[{index}].mass")
        pos = row.get("pos")
        if not isinstance(pos, list) or len(pos) != 3:
            raise ValueError(f"SDF BODY[{index}].pos shape drift")
        _finite(pos, f"SDF BODY[{index}].pos")

    body0_handoff = body0.get("handoff") or {}
    body0_resource = body0.get("body0") or {}
    if body0_handoff.get("BODY0_resource_pos_ori_values_ready") is not True:
        raise ValueError("BODY0 resource evidence is not ready")
    if body0_resource.get("body_index") != 0 or body0_resource.get("body_name") != "body":
        raise ValueError("BODY0 resource identity drift")
    if bodies[0].get("pos") != body0_resource.get("pos"):
        raise ValueError("SDF BODY0 position disagrees with BODY0 resource evidence")

    handoff = inputs.get("handoff") or {}
    required_true = (
        "offset33b_resource_inputs_ready",
        "offset33b_direct_CDF_load_data_mapping_ready",
        "offset33b_SDF_body_resource_values_ready",
    )
    required_false = (
        "offset33b_memory_LOAD_semantic_join_ready",
        "BMW_numeric_offset33b_ready",
        "BODY0_to_outer_vehicle_root_numeric_matrix_ready",
        "BODY0_bind_frame_proof_ready",
        "vehicle_world_transform_ready",
    )
    if any(handoff.get(field) is not True for field in required_true):
        raise ValueError("resource-input positive handoff drift")
    if any(handoff.get(field) is not False for field in required_false):
        raise ValueError("resource-input fail-closed handoff drift")

    return {
        "format": FORMAT,
        "version": 1,
        "status": "validated",
        "ready": True,
        "resource_inputs": str(inputs_path),
        "cdf_direct_field_count": len(DIRECT_FIELDS),
        "sdf_body_count": len(bodies),
        "derived_load_data_frontier": ["+0x338"],
        "handoff": dict(handoff),
        "next_proof": "join exact FUN_0076b280 machine LOAD base provenance to these source-backed load-data/resource fields",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("resource_inputs", type=Path)
    parser.add_argument("physics_manifest", type=Path)
    parser.add_argument("body0_resource", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    report = validate(args.resource_inputs, args.physics_manifest, args.body0_resource)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out is None:
        print(text, end="")
    else:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
