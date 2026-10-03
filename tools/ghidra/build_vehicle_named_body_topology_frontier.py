#!/usr/bin/env python3
"""Narrow the retail BMW vehicle -> chassis BODY identity frontier.

This composition layer joins the already-proven vehicle/BODY pointer-domain
boundary, the source/machine-backed named vehicle BODY fields, and the exact
BMW M3 retail SDF manifest.  It deliberately does not infer that nine named
vehicle BODY roles occupy nine distinct runtime BODY indices.  When an exact
SDF source is supplied, its SHA-256 is checked against the retail manifest and
the existing SDF parser is used to recover the exact BODY name/order before any
residual candidate set is emitted.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.VehicleNamedBodyTopologyFrontier/1"
IDENTITY_FORMAT = "SHIFT.VehicleBodyIdentityFrontier/1"
BODY_ABI_FORMAT = "SHIFT.BodyPersistentStateABI/1"
BMW_MANIFEST_FORMAT = "SHIFT.BMWM3VehiclePhysicsResourceManifest/1"
SDF_RUNTIME_FORMAT = "SHIFT.RigidBodySDFRuntime/1"

BMW_ARCHIVE = "BMW_M3_E36.bff"
BMW_SDF_PATH = "vehicles/physics/suspension/aarm_multilink.sdf"
BMW_SDF_SHA256 = "fe0b18e95e81f87d67076b70890965a0a1384a925bfd836aaf5aa705fc4781ed"
BMW_SDF_BODY_COUNT = 11
BODY_STRIDE = 0x170

VEHICLE_SOLVER_SETUP = "0x007615c0"
UPSTREAM_BATCH = "0x00713050"
FIRST_UPDATE_CALLER = "0x00794a30"

# Phase 633 / FUN_007615c0 source-backed names.  The offsets are independently
# frozen by BodyPersistentStateABI/1.  Distinct *roles* are proven; distinct
# runtime BODY indices are intentionally not inferred until exact SDF names are
# available.
NAMED_BODY_FIELDS = (
    {"name": "fl_wheel", "role": "wheel", "slot": 0, "vehicle_offset": 0x820},
    {"name": "fl_spindle", "role": "spindle", "slot": 0, "vehicle_offset": 0x824},
    {"name": "fr_wheel", "role": "wheel", "slot": 1, "vehicle_offset": 0x12A0},
    {"name": "fr_spindle", "role": "spindle", "slot": 1, "vehicle_offset": 0x12A4},
    {"name": "rl_wheel", "role": "wheel", "slot": 2, "vehicle_offset": 0x1D20},
    {"name": "rl_spindle", "role": "spindle", "slot": 2, "vehicle_offset": 0x1D24},
    {"name": "rr_wheel", "role": "wheel", "slot": 3, "vehicle_offset": 0x27A0},
    {"name": "rr_spindle", "role": "spindle", "slot": 3, "vehicle_offset": 0x27A4},
    {"name": "rear_axle", "role": "rear-axle", "slot": None, "vehicle_offset": 0x2E00},
)


def _load(path: Path, expected: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("format") != expected:
        raise ValueError(f"{path}: expected {expected}")
    return value


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _int(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError(f"invalid integer value: {value!r}")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        text = value.strip()
        if text.startswith("+"):
            text = text[1:]
        return int(text, 0)
    raise ValueError(f"invalid integer value: {value!r}")


def _component_topology(report: dict[str, Any]) -> dict[str, Any]:
    topology = report.get("vehicle_topology")
    if not isinstance(topology, dict):
        raise ValueError("BODY ABI vehicle_topology missing")

    # build_contract() uses a nested component_slots object.  The older committed
    # evidence snapshot is flat.  Both are the same SHIFT.BodyPersistentStateABI/1
    # topology contract, so accept either representation while checking every
    # identity-bearing value.
    slots = topology.get("component_slots")
    if isinstance(slots, dict):
        return {
            "count": _int(slots.get("count")),
            "base": _int(slots.get("base")),
            "stride": _int(slots.get("stride")),
            "component_offsets": tuple(_int(v) for v in slots.get("component_offsets") or ()),
            "wheel_relative": _int(slots.get("wheel_body_pointer_relative")),
            "spindle_relative": _int(slots.get("spindle_body_pointer_relative")),
            "wheel_absolute": tuple(_int(v) for v in slots.get("wheel_body_pointer_absolute") or ()),
            "spindle_absolute": tuple(_int(v) for v in slots.get("spindle_body_pointer_absolute") or ()),
            "rear_axle": _int(topology.get("rear_axle_body_pointer")),
        }

    return {
        "count": _int(topology.get("component_count")),
        "base": _int(topology.get("component_base")),
        "stride": _int(topology.get("component_stride")),
        "component_offsets": tuple(_int(v) for v in topology.get("component_offsets") or ()),
        "wheel_relative": _int(topology.get("wheel_body_pointer_relative")),
        "spindle_relative": _int(topology.get("spindle_body_pointer_relative")),
        "wheel_absolute": tuple(_int(v) for v in topology.get("wheel_body_pointer_absolute") or ()),
        "spindle_absolute": tuple(_int(v) for v in topology.get("spindle_body_pointer_absolute") or ()),
        "rear_axle": _int(topology.get("rear_axle_body_pointer")),
    }


def _validate_component_topology(report: dict[str, Any]) -> dict[str, Any]:
    topology = _component_topology(report)
    expected_components = (0x400, 0xE80, 0x1900, 0x2380)
    expected_wheels = (0x820, 0x12A0, 0x1D20, 0x27A0)
    expected_spindles = (0x824, 0x12A4, 0x1D24, 0x27A4)
    _require(topology["count"] == 4, "vehicle component count drift")
    _require(topology["base"] == 0x400, "vehicle component base drift")
    _require(topology["stride"] == 0xA80, "vehicle component stride drift")
    _require(topology["component_offsets"] == expected_components, "vehicle component offsets drift")
    _require(topology["wheel_relative"] == 0x420, "wheel BODY field offset drift")
    _require(topology["spindle_relative"] == 0x424, "spindle BODY field offset drift")
    _require(topology["wheel_absolute"] == expected_wheels, "wheel BODY absolute fields drift")
    _require(topology["spindle_absolute"] == expected_spindles, "spindle BODY absolute fields drift")
    _require(topology["rear_axle"] == 0x2E00, "rear-axle BODY field offset drift")
    return topology


def _manifest_sdf(
    manifest: dict[str, Any], *, expected_sdf_sha256: str
) -> dict[str, Any]:
    _require(manifest.get("source_archive") == BMW_ARCHIVE, "BMW source archive drift")
    rows = manifest.get("archive_entry_points")
    if not isinstance(rows, list):
        raise ValueError("BMW manifest archive_entry_points missing")
    matches = [row for row in rows if isinstance(row, dict) and row.get("path") == BMW_SDF_PATH]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one retail SDF entry; found {len(matches)}")
    archive_row = matches[0]
    sdf = manifest.get("sdf")
    if not isinstance(sdf, dict):
        raise ValueError("BMW manifest sdf section missing")
    manifest_hash = str(sdf.get("sha256") or "").lower()
    _require(manifest_hash == str(archive_row.get("sha256") or "").lower(), "BMW SDF hashes disagree")
    _require(manifest_hash == expected_sdf_sha256.lower(), "BMW retail SDF SHA-256 drift")
    _require(_int(sdf.get("body_count")) == BMW_SDF_BODY_COUNT, "BMW SDF BODY count drift")
    _require(_int(sdf.get("body_stride")) == BODY_STRIDE, "BMW SDF BODY stride drift")
    return {
        "path": BMW_SDF_PATH,
        "sha256": manifest_hash,
        "body_count": BMW_SDF_BODY_COUNT,
        "body_stride": BODY_STRIDE,
        "entry_index": archive_row.get("entry_index"),
        "uncompressed_size": archive_row.get("uncompressed_size"),
    }


def _load_sdf_module():
    path = Path(__file__).resolve().parents[2] / "src" / "physics" / "rigid_body_sdf_runtime.py"
    spec = importlib.util.spec_from_file_location("rigid_body_sdf_runtime_for_identity", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load SDF parser: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _exact_sdf_rows(path: Path, *, expected_sha256: str) -> list[dict[str, Any]]:
    data = path.read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected_sha256.lower():
        raise ValueError(
            f"exact SDF SHA-256 mismatch: expected {expected_sha256.lower()}, got {actual}"
        )
    module = _load_sdf_module()
    parsed = module.parse_sdf(data, strict=False)
    _require(parsed.get("format") == SDF_RUNTIME_FORMAT, "unexpected SDF parser format")
    _require((parsed.get("topology") or {}).get("body_count") == BMW_SDF_BODY_COUNT, "exact SDF BODY count drift")
    lowering = module.describe_sdf_body_runtime_lowering(parsed)
    _require(lowering.get("ready") is True, "exact SDF BODY names are duplicated")
    _require(lowering.get("body_count") == BMW_SDF_BODY_COUNT, "exact SDF lowering count drift")
    rows = lowering.get("rows")
    if not isinstance(rows, list) or len(rows) != BMW_SDF_BODY_COUNT:
        raise ValueError("exact SDF lowering rows missing")
    result: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("index"), int):
            raise ValueError("exact SDF lowering contains invalid row")
        name = str(row.get("name") or "").strip()
        if not name:
            raise ValueError(f"exact SDF BODY {row.get('index')} has no name")
        result.append({"index": row["index"], "name": name, "normalized_name": name.lower()})
    return result


def build_vehicle_named_body_topology_frontier(
    identity_frontier_path: Path,
    body_abi_path: Path,
    bmw_manifest_path: Path,
    *,
    sdf_source_path: Path | None = None,
    expected_sdf_sha256: str = BMW_SDF_SHA256,
) -> dict[str, Any]:
    identity = _load(identity_frontier_path, IDENTITY_FORMAT)
    body_abi = _load(body_abi_path, BODY_ABI_FORMAT)
    manifest = _load(bmw_manifest_path, BMW_MANIFEST_FORMAT)

    handoff = identity.get("handoff")
    scope = identity.get("scope")
    if not isinstance(handoff, dict) or not isinstance(scope, dict):
        raise ValueError("vehicle/BODY identity frontier handoff/scope missing")
    _require(handoff.get("persistent_BODY_pose_available") is True, "persistent BODY pose is no longer available")
    _require(handoff.get("vehicle_BODY_selection_ready") is False, "upstream frontier unexpectedly preselects a vehicle BODY")
    _require(handoff.get("selected_BODY_index") is None, "upstream frontier unexpectedly carries a BODY index")
    _require(scope.get("update_child_to_BODY_identity_proven") is False, "upstream frontier unexpectedly preclaims vehicle/BODY identity")

    topology = _validate_component_topology(body_abi)
    retail_sdf = _manifest_sdf(manifest, expected_sdf_sha256=expected_sdf_sha256)

    named_rows: list[dict[str, Any]] = []
    for spec in NAMED_BODY_FIELDS:
        row = dict(spec)
        row["vehicle_offset_hex"] = f"0x{spec['vehicle_offset']:x}"
        row["name_identity_state"] = "source-backed"
        row["runtime_BODY_index"] = None
        row["runtime_BODY_index_state"] = "unknown"
        named_rows.append(row)

    exact_rows: list[dict[str, Any]] | None = None
    matched: list[dict[str, Any]] = []
    residual: list[dict[str, Any]] = []
    if sdf_source_path is not None:
        exact_rows = _exact_sdf_rows(sdf_source_path, expected_sha256=retail_sdf["sha256"])
        by_name: dict[str, list[dict[str, Any]]] = {}
        for row in exact_rows:
            by_name.setdefault(row["normalized_name"], []).append(row)
        for field in named_rows:
            rows = by_name.get(field["name"], [])
            if len(rows) != 1:
                raise ValueError(
                    f"exact SDF must contain named vehicle BODY {field['name']!r} exactly once; found {len(rows)}"
                )
            body_row = rows[0]
            field["runtime_BODY_index"] = body_row["index"]
            field["runtime_BODY_index_state"] = "verified-exact-retail-sdf"
            matched.append({
                "name": field["name"],
                "runtime_BODY_index": body_row["index"],
                "vehicle_offset": field["vehicle_offset_hex"],
            })
        known_names = {row["name"] for row in named_rows}
        residual = [
            {"index": row["index"], "name": row["name"]}
            for row in exact_rows
            if row["normalized_name"] not in known_names
        ]
        _require(len(residual) == BMW_SDF_BODY_COUNT - len(NAMED_BODY_FIELDS), "exact SDF residual BODY cardinality changed")

    exact_names_ready = exact_rows is not None
    residual_count = len(residual) if exact_names_ready else None
    arithmetic_residual = BMW_SDF_BODY_COUNT - len(NAMED_BODY_FIELDS)

    blockers = []
    if not exact_names_ready:
        blockers.append({
            "id": "exact-retail-sdf-body-name-order-missing",
            "evidence_state": "unknown",
            "required_evidence": (
                f"extract {BMW_SDF_PATH} and match SHA-256 {retail_sdf['sha256']} before "
                "treating the 11-minus-9 cardinality difference as an exact candidate set"
            ),
        })
    blockers.extend([
        {
            "id": "main-chassis-BODY-semantic-selection",
            "evidence_state": "unknown",
            "candidate_rows": residual if exact_names_ready else [],
            "required_evidence": (
                "source/static evidence that identifies which exact SDF BODY is the persistent "
                "vehicle/chassis pose source; a plausible BODY name alone is not sufficient"
            ),
        },
        {
            "id": "update-child-to-vehicle-solver-base-continuity",
            "evidence_state": "unknown",
            "targets": [UPSTREAM_BATCH, FIRST_UPDATE_CALLER, VEHICLE_SOLVER_SETUP],
            "required_evidence": (
                "pointer-value or owner/registration continuity joining the *record+0x340 "
                "update child to the vehicle base whose named BODY fields are proven by FUN_007615c0"
            ),
        },
    ])

    return {
        "format": FORMAT,
        "inputs": {
            "vehicle_BODY_identity_frontier": str(identity_frontier_path),
            "BODY_persistent_state_ABI": str(body_abi_path),
            "BMW_vehicle_physics_manifest": str(bmw_manifest_path),
            "exact_sdf_source": None if sdf_source_path is None else str(sdf_source_path),
        },
        "retail_sdf": retail_sdf,
        "vehicle_solver_setup": {
            "function": VEHICLE_SOLVER_SETUP,
            "evidence_state": "source-plus-raw-disassembly-backed",
            "component_count": topology["count"],
            "component_base": f"0x{topology['base']:x}",
            "component_stride": f"0x{topology['stride']:x}",
            "named_BODY_field_role_count": len(named_rows),
            "named_BODY_fields": named_rows,
            "distinct_runtime_BODY_indices_proven_without_exact_sdf": False,
        },
        "cardinality_frontier": {
            "retail_sdf_BODY_record_count": BMW_SDF_BODY_COUNT,
            "named_vehicle_BODY_field_role_count": len(NAMED_BODY_FIELDS),
            "arithmetic_difference": arithmetic_residual,
            "arithmetic_difference_is_exact_residual_candidate_count": exact_names_ready,
            "exact_sdf_BODY_name_order_ready": exact_names_ready,
            "exact_named_BODY_matches": matched,
            "exact_residual_BODY_rows": residual,
            "exact_residual_BODY_count": residual_count,
        },
        "blockers": blockers,
        "next_instruction_targets": [UPSTREAM_BATCH, FIRST_UPDATE_CALLER, VEHICLE_SOLVER_SETUP],
        "handoff": {
            "persistent_BODY_pose_available": True,
            "named_vehicle_BODY_fields_ready": True,
            "exact_sdf_BODY_name_order_ready": exact_names_ready,
            "main_chassis_BODY_selected": False,
            "selected_BODY_index": None,
            "vehicle_BODY_selection_ready": False,
            "vehicle_world_transform_ready": False,
            "renderer_vehicle_transform_transport_ready": False,
            "critical_next_join": (
                "exact SDF BODY name/order -> main chassis BODY semantic identity -> "
                "update-child/vehicle-base continuity"
            ),
        },
        "scope": {
            "named_body_roles_are_distinct_runtime_indices": exact_names_ready,
            "nine_named_roles_plus_eleven_body_records_proves_two_candidates_without_exact_sdf": False,
            "body_name_alone_proves_chassis_semantics": False,
            "vehicle_field_offset_alone_proves_update_child_identity": False,
            "original_game_executed": False,
            "new_runtime_capture_required": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vehicle_body_identity_frontier", type=Path)
    parser.add_argument("body_persistent_state_abi", type=Path)
    parser.add_argument("bmw_vehicle_physics_manifest", type=Path)
    parser.add_argument("--sdf-source", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--targets-out", type=Path)
    args = parser.parse_args()

    report = build_vehicle_named_body_topology_frontier(
        args.vehicle_body_identity_frontier,
        args.body_persistent_state_abi,
        args.bmw_vehicle_physics_manifest,
        sdf_source_path=args.sdf_source,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    if args.targets_out:
        args.targets_out.parent.mkdir(parents=True, exist_ok=True)
        args.targets_out.write_text(
            "".join(address + "\n" for address in report["next_instruction_targets"]),
            encoding="utf-8",
        )
    print(f"format: {report['format']}")
    print(f"retail BMW SDF BODY records: {report['cardinality_frontier']['retail_sdf_BODY_record_count']}")
    print(f"named vehicle BODY roles: {report['cardinality_frontier']['named_vehicle_BODY_field_role_count']}")
    print(f"exact SDF name order ready: {report['cardinality_frontier']['exact_sdf_BODY_name_order_ready']}")
    print(f"vehicle BODY selection ready: {report['handoff']['vehicle_BODY_selection_ready']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
