#!/usr/bin/env python3
"""Join exact BMW SDF name/order evidence to the vehicle BODY topology frontier.

Version 2 corrects the v1 assumption that the semantic `rear_axle` vehicle field
role is also an SDF `name=` value.  The archive-derived Phase 404 evidence proves
the exact retail SDF BODY order and contains no `rear_axle` record.  Therefore
wheel/spindle names are joined directly, while the `rear_axle` field remains a
separate semantic BODY-pointer role whose exact SDF index is unresolved.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.VehicleNamedBodyTopologyFrontier/2"
IDENTITY_FORMAT = "SHIFT.VehicleBodyIdentityFrontier/1"
BODY_ABI_FORMAT = "SHIFT.BodyPersistentStateABI/1"
BMW_MANIFEST_FORMAT = "SHIFT.BMWM3VehiclePhysicsResourceManifest/1"
PHASE404_FORMAT = "SHIFT.BMWM3PhysicsIntakeEvidence/1"
SDF_RUNTIME_FORMAT = "SHIFT.RigidBodySDFRuntime/1"
BMW_ARCHIVE = "BMW_M3_E36.bff"
BMW_SDF_PATH = "vehicles/physics/suspension/aarm_multilink.sdf"
BMW_SDF_SHA256 = "fe0b18e95e81f87d67076b70890965a0a1384a925bfd836aaf5aa705fc4781ed"
BMW_SDF_BODY_COUNT = 11
BODY_STRIDE = 0x170
VEHICLE_SOLVER_SETUP = "0x007615c0"
UPSTREAM_BATCH = "0x00713050"
FIRST_UPDATE_CALLER = "0x00794a30"
DEFAULT_PHASE404 = "evidence/bmw_m3_e36_physics_intake_phase404.json"

# Only these eight Phase 633 source names are also proven exact retail SDF names
# by Phase 404. `rear_axle` is intentionally absent from this table.
SDF_NAMED_FIELDS = (
    ("fl_wheel", "wheel", 0, 0x820),
    ("fl_spindle", "spindle", 0, 0x824),
    ("fr_wheel", "wheel", 1, 0x12A0),
    ("fr_spindle", "spindle", 1, 0x12A4),
    ("rl_wheel", "wheel", 2, 0x1D20),
    ("rl_spindle", "spindle", 2, 0x1D24),
    ("rr_wheel", "wheel", 3, 0x27A0),
    ("rr_spindle", "spindle", 3, 0x27A4),
)
REAR_AXLE_FIELD = ("rear_axle", "rear-axle", None, 0x2E00)


def _load(path: Path, expected: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("format") != expected:
        raise ValueError(f"{path}: expected {expected}")
    return value


def _require(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def _int(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError(f"invalid integer: {value!r}")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value.strip().lstrip("+"), 0)
    raise ValueError(f"invalid integer: {value!r}")


def _topology(report: dict[str, Any]) -> dict[str, Any]:
    value = report.get("vehicle_topology")
    if not isinstance(value, dict):
        raise ValueError("BODY ABI vehicle_topology missing")
    slots = value.get("component_slots")
    if isinstance(slots, dict):
        row = {
            "count": slots.get("count"), "base": slots.get("base"), "stride": slots.get("stride"),
            "components": slots.get("component_offsets"),
            "wheel_rel": slots.get("wheel_body_pointer_relative"),
            "spindle_rel": slots.get("spindle_body_pointer_relative"),
            "wheels": slots.get("wheel_body_pointer_absolute"),
            "spindles": slots.get("spindle_body_pointer_absolute"),
            "rear_axle": value.get("rear_axle_body_pointer"),
        }
    else:
        row = {
            "count": value.get("component_count"), "base": value.get("component_base"),
            "stride": value.get("component_stride"), "components": value.get("component_offsets"),
            "wheel_rel": value.get("wheel_body_pointer_relative"),
            "spindle_rel": value.get("spindle_body_pointer_relative"),
            "wheels": value.get("wheel_body_pointer_absolute"),
            "spindles": value.get("spindle_body_pointer_absolute"),
            "rear_axle": value.get("rear_axle_body_pointer"),
        }
    for key in ("count", "base", "stride", "wheel_rel", "spindle_rel", "rear_axle"):
        row[key] = _int(row[key])
    for key in ("components", "wheels", "spindles"):
        row[key] = tuple(_int(v) for v in (row[key] or ()))
    expected = {
        "count": 4, "base": 0x400, "stride": 0xA80,
        "components": (0x400, 0xE80, 0x1900, 0x2380),
        "wheel_rel": 0x420, "spindle_rel": 0x424,
        "wheels": (0x820, 0x12A0, 0x1D20, 0x27A0),
        "spindles": (0x824, 0x12A4, 0x1D24, 0x27A4),
        "rear_axle": 0x2E00,
    }
    _require(row == expected, f"vehicle BODY topology drift: {row}")
    return row


def _manifest_sdf(manifest: dict[str, Any], expected_hash: str) -> dict[str, Any]:
    _require(manifest.get("source_archive") == BMW_ARCHIVE, "BMW source archive drift")
    entries = manifest.get("archive_entry_points")
    if not isinstance(entries, list):
        raise ValueError("BMW archive_entry_points missing")
    matches = [r for r in entries if isinstance(r, dict) and r.get("path") == BMW_SDF_PATH]
    if len(matches) != 1:
        raise ValueError(f"expected one BMW SDF entry; found {len(matches)}")
    entry = matches[0]
    sdf = manifest.get("sdf")
    if not isinstance(sdf, dict):
        raise ValueError("BMW sdf section missing")
    digest = str(sdf.get("sha256") or "").lower()
    _require(digest == str(entry.get("sha256") or "").lower(), "BMW SDF hashes disagree")
    _require(digest == expected_hash.lower(), "BMW retail SDF SHA-256 drift")
    _require(_int(sdf.get("body_count")) == BMW_SDF_BODY_COUNT, "BMW SDF BODY count drift")
    _require(_int(sdf.get("body_stride")) == BODY_STRIDE, "BMW SDF BODY stride drift")
    return {
        "path": BMW_SDF_PATH, "sha256": digest, "body_count": BMW_SDF_BODY_COUNT,
        "body_stride": BODY_STRIDE, "entry_index": _int(entry.get("entry_index")),
        "uncompressed_size": _int(entry.get("uncompressed_size")),
    }


def _phase404_rows(report: dict[str, Any], retail_sdf: dict[str, Any]) -> list[dict[str, Any]]:
    _require(report.get("status") == "decoded-from-user-supplied-bff", "Phase 404 archive provenance drift")
    archive = report.get("archive")
    sdf_entry = report.get("sdf_entry")
    structure = report.get("structure")
    bodies = report.get("bodies")
    if not all(isinstance(v, dict) for v in (archive, sdf_entry, structure)) or not isinstance(bodies, list):
        raise ValueError("Phase 404 evidence structure missing")
    _require(archive.get("filename") == BMW_ARCHIVE, "Phase 404 archive filename drift")
    _require(sdf_entry.get("path") == retail_sdf["path"], "Phase 404 SDF path drift")
    _require(_int(sdf_entry.get("index")) == retail_sdf["entry_index"], "Phase 404 SDF entry index drift")
    _require(str(sdf_entry.get("decoded_sha256") or "").lower() == retail_sdf["sha256"], "Phase 404 SDF SHA-256 drift")
    _require(_int(sdf_entry.get("uncompressed_size")) == retail_sdf["uncompressed_size"], "Phase 404 SDF size drift")
    _require(_int(structure.get("body_count")) == retail_sdf["body_count"], "Phase 404 BODY count drift")
    _require(len(bodies) == retail_sdf["body_count"], "Phase 404 BODY name count drift")
    rows = []
    seen: set[str] = set()
    for index, raw in enumerate(bodies):
        name = str(raw).strip()
        normalized = name.lower()
        _require(bool(name), f"Phase 404 BODY {index} has empty name")
        _require(normalized not in seen, f"Phase 404 duplicate BODY name: {name}")
        seen.add(normalized)
        rows.append({"index": index, "name": name, "normalized_name": normalized})
    return rows


def _sdf_module():
    path = Path(__file__).resolve().parents[2] / "src" / "physics" / "rigid_body_sdf_runtime.py"
    spec = importlib.util.spec_from_file_location("rigid_body_sdf_for_identity_v2", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load SDF parser: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _crosscheck_raw_sdf(path: Path, *, digest: str, expected_rows: list[dict[str, Any]]) -> None:
    data = path.read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    _require(actual == digest, f"exact SDF SHA-256 mismatch: expected {digest}, got {actual}")
    module = _sdf_module()
    parsed = module.parse_sdf(data, strict=False)
    _require(parsed.get("format") == SDF_RUNTIME_FORMAT, "unexpected SDF parser format")
    lowering = module.describe_sdf_body_runtime_lowering(parsed)
    _require(lowering.get("ready") is True, "exact SDF lowering is not ready")
    raw_rows = lowering.get("rows")
    if not isinstance(raw_rows, list):
        raise ValueError("exact SDF lowering rows missing")
    actual_names = [str(row.get("name") or "").strip().lower() for row in raw_rows]
    expected_names = [row["normalized_name"] for row in expected_rows]
    _require(actual_names == expected_names, "raw SDF BODY order disagrees with Phase 404 evidence")


def build_vehicle_named_body_topology_frontier(
    identity_path: Path,
    body_abi_path: Path,
    manifest_path: Path,
    *,
    phase404_evidence_path: Path | None = None,
    sdf_source_path: Path | None = None,
    expected_sdf_sha256: str = BMW_SDF_SHA256,
) -> dict[str, Any]:
    identity = _load(identity_path, IDENTITY_FORMAT)
    body_abi = _load(body_abi_path, BODY_ABI_FORMAT)
    manifest = _load(manifest_path, BMW_MANIFEST_FORMAT)
    if phase404_evidence_path is None:
        phase404_evidence_path = Path(__file__).resolve().parents[2] / DEFAULT_PHASE404
    phase404 = _load(phase404_evidence_path, PHASE404_FORMAT)

    handoff = identity.get("handoff") or {}
    scope = identity.get("scope") or {}
    _require(handoff.get("persistent_BODY_pose_available") is True, "persistent BODY pose unavailable")
    _require(handoff.get("vehicle_BODY_selection_ready") is False, "upstream frontier unexpectedly preselects a vehicle BODY")
    _require(handoff.get("selected_BODY_index") is None, "upstream frontier unexpectedly carries BODY index")
    _require(scope.get("update_child_to_BODY_identity_proven") is False, "upstream frontier preclaims vehicle/BODY identity")

    topology = _topology(body_abi)
    retail_sdf = _manifest_sdf(manifest, expected_sdf_sha256)
    sdf_rows = _phase404_rows(phase404, retail_sdf)
    if sdf_source_path is not None:
        _crosscheck_raw_sdf(sdf_source_path, digest=retail_sdf["sha256"], expected_rows=sdf_rows)

    by_name = {row["normalized_name"]: row for row in sdf_rows}
    mapped = []
    fields = []
    for name, role, slot, offset in SDF_NAMED_FIELDS:
        _require(name in by_name, f"Phase 404 exact SDF lacks proven vehicle BODY name {name!r}")
        sdf_row = by_name[name]
        field = {
            "name": name, "role": role, "slot": slot, "vehicle_offset": f"0x{offset:x}",
            "sdf_name_state": "verified-phase404-retail-sdf",
            "runtime_BODY_index": sdf_row["index"],
            "runtime_BODY_index_state": "verified-phase404-retail-sdf",
        }
        fields.append(field)
        mapped.append({"name": name, "runtime_BODY_index": sdf_row["index"], "vehicle_offset": field["vehicle_offset"]})

    rear_name, rear_role, rear_slot, rear_offset = REAR_AXLE_FIELD
    fields.append({
        "name": rear_name, "role": rear_role, "slot": rear_slot,
        "vehicle_offset": f"0x{rear_offset:x}",
        "sdf_name_state": "not-an-exact-retail-sdf-name",
        "runtime_BODY_index": None,
        "runtime_BODY_index_state": "unknown-semantic-role-to-SDF-index",
    })
    exact_sdf_names = {row["normalized_name"] for row in sdf_rows}
    _require(rear_name not in exact_sdf_names, "retail SDF unexpectedly acquired rear_axle name; re-audit Phase 633 role")

    mapped_names = {name for name, *_ in SDF_NAMED_FIELDS}
    residual = [
        {"index": row["index"], "name": row["name"]}
        for row in sdf_rows if row["normalized_name"] not in mapped_names
    ]
    _require(len(residual) == 3, "exact non-wheel/spindle residual cardinality drift")

    blockers = [
        {
            "id": "rear-axle-field-role-to-SDF-index", "evidence_state": "unknown",
            "vehicle_offset": "0x2e00",
            "required_evidence": "trace FUN_007615c0 value production for vehicle+0x2e00 to one exact SDF BODY pointer/index",
        },
        {
            "id": "main-chassis-BODY-semantic-selection", "evidence_state": "unknown",
            "exact_non_wheel_spindle_rows": residual,
            "required_evidence": "prove which exact retail SDF BODY supplies the vehicle/chassis world pose; BODY name plausibility alone is insufficient",
        },
        {
            "id": "update-child-to-vehicle-solver-base-continuity", "evidence_state": "unknown",
            "targets": [UPSTREAM_BATCH, FIRST_UPDATE_CALLER, VEHICLE_SOLVER_SETUP],
            "required_evidence": "join *record+0x340 update child to the vehicle base whose BODY fields are populated by FUN_007615c0",
        },
    ]

    return {
        "format": FORMAT,
        "supersedes": "SHIFT.VehicleNamedBodyTopologyFrontier/1",
        "inputs": {
            "vehicle_BODY_identity_frontier": str(identity_path),
            "BODY_persistent_state_ABI": str(body_abi_path),
            "BMW_vehicle_physics_manifest": str(manifest_path),
            "phase404_archive_derived_evidence": str(phase404_evidence_path),
            "raw_sdf_crosscheck": None if sdf_source_path is None else str(sdf_source_path),
        },
        "retail_sdf": {
            **retail_sdf,
            "body_name_order_state": "verified-archive-derived-phase404",
            "body_rows": [{"index": row["index"], "name": row["name"]} for row in sdf_rows],
        },
        "vehicle_solver_setup": {
            "function": VEHICLE_SOLVER_SETUP,
            "evidence_state": "source-plus-raw-disassembly-backed",
            "component_count": topology["count"], "component_base": f"0x{topology['base']:x}",
            "component_stride": f"0x{topology['stride']:x}",
            "vehicle_BODY_field_role_count": len(fields),
            "exact_sdf_name_mapped_field_count": len(mapped),
            "semantic_only_field_count": 1,
            "BODY_fields": fields,
        },
        "exact_name_join": {
            "exact_sdf_BODY_name_order_ready": True,
            "exact_named_BODY_matches": mapped,
            "exact_non_wheel_spindle_BODY_rows": residual,
            "rear_axle_is_exact_sdf_name": False,
            "rear_axle_runtime_BODY_index": None,
            "main_chassis_BODY_selected": False,
            "selected_BODY_index": None,
        },
        "blockers": blockers,
        "next_instruction_targets": [UPSTREAM_BATCH, FIRST_UPDATE_CALLER, VEHICLE_SOLVER_SETUP],
        "handoff": {
            "persistent_BODY_pose_available": True,
            "exact_sdf_BODY_name_order_ready": True,
            "wheel_spindle_BODY_indices_ready": True,
            "rear_axle_BODY_index_ready": False,
            "main_chassis_BODY_selected": False,
            "selected_BODY_index": None,
            "vehicle_BODY_selection_ready": False,
            "vehicle_world_transform_ready": False,
            "renderer_vehicle_transform_transport_ready": False,
            "phase698_positive_selection_admissible": False,
            "critical_next_join": "FUN_007615c0 rear_axle/chassis pointer production + update-child/vehicle-base continuity",
        },
        "scope": {
            "phase404_body_order_is_archive_derived": True,
            "rear_axle_semantic_role_is_sdf_name": False,
            "non_wheel_spindle_name_is_chassis_proof": False,
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
    parser.add_argument("--phase404-evidence", type=Path)
    parser.add_argument("--sdf-source", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--targets-out", type=Path)
    args = parser.parse_args()
    report = build_vehicle_named_body_topology_frontier(
        args.vehicle_body_identity_frontier, args.body_persistent_state_abi,
        args.bmw_vehicle_physics_manifest, phase404_evidence_path=args.phase404_evidence,
        sdf_source_path=args.sdf_source,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    if args.targets_out:
        args.targets_out.parent.mkdir(parents=True, exist_ok=True)
        args.targets_out.write_text("".join(x + "\n" for x in report["next_instruction_targets"]), encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"exact SDF BODY order ready: {report['handoff']['exact_sdf_BODY_name_order_ready']}")
    print(f"wheel/spindle BODY indices ready: {report['handoff']['wheel_spindle_BODY_indices_ready']}")
    print(f"vehicle BODY selection ready: {report['handoff']['vehicle_BODY_selection_ready']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
