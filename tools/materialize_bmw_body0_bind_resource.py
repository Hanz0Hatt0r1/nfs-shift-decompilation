#!/usr/bin/env python3
"""Materialize the exact retail BMW BODY0 SDF pose input for Process 1.

This tool solves the data-availability half of the remaining BMW BODY0 bind
blocker. It supports two fail-closed sources for the same already-proven retail
SDF identity:

* the exact retail ``BMW_M3_E36.bff`` through the existing source-backed BFF
  extractor; or
* ``SHIFT.OfflineRuntimeBootstrap/1`` after Process 3 has admitted the exact
  decoded SDF through ``SHIFT.TypedResourceClosure/1``.

Both paths report BODY[0] ``pos``/``ori`` without inventing the still-unproven
outer-Vehicle/VHF frame join or a numeric vehicle-world transform.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
PHYSICS = SRC / "physics"
LEGACY = SRC / "legacy"
for path in (ROOT, SRC, PHYSICS, LEGACY, Path(__file__).resolve().parent):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

from rigid_body_sdf_runtime import parse_sdf, records_by_type
from verify_bmw_m3_e36_solver_domain import (
    TARGET_ARCHIVE_SHA256,
    TARGET_RESOURCE,
    TARGET_RESOURCE_SHA256,
    extract_target_sdf,
)

FORMAT = "SHIFT.BMWBody0BindResourceMaterialization/1"
INTAKE_FORMAT = "SHIFT.BMWM3PhysicsIntakeEvidence/1"
RUNTIME_BOOTSTRAP_FORMAT = "SHIFT.OfflineRuntimeBootstrap/1"
PHYSICS_MANIFEST_FORMAT = "SHIFT.VehiclePhysicsResourceManifest/1"
TYPED_CLOSURE_FORMAT = "SHIFT.TypedResourceClosure/1"
DEFAULT_INTAKE = ROOT / "evidence" / "bmw_m3_e36_physics_intake_phase404.json"
TARGET_VEHICLE = "BMW_M3_E36"
BODY_INDEX = 0
BODY_NAME = "body"
EXPECTED_BODIES = (
    "body",
    "fl_spindle",
    "fr_spindle",
    "fl_wheel",
    "fr_wheel",
    "rl_spindle",
    "rr_spindle",
    "rl_wheel",
    "rr_wheel",
    "fuel_tank",
    "driver_head",
)


def _load_json_object(path: Path, *, expected_format: str | None = None) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    if expected_format is not None and value.get("format") != expected_format:
        raise ValueError(f"{path}: expected {expected_format}")
    return value


def _load_intake(path: Path) -> dict[str, Any]:
    value = _load_json_object(path, expected_format=INTAKE_FORMAT)

    archive = value.get("archive") or {}
    sdf = value.get("sdf_entry") or {}
    structure = value.get("structure") or {}
    if archive.get("filename") != "BMW_M3_E36.bff":
        raise ValueError("Phase 404 BMW archive filename drift")
    if archive.get("sha256") != TARGET_ARCHIVE_SHA256:
        raise ValueError("Phase 404 BMW archive SHA-256 drift")
    if sdf.get("path") != TARGET_RESOURCE:
        raise ValueError("Phase 404 BMW SDF path drift")
    if sdf.get("decoded_sha256") != TARGET_RESOURCE_SHA256:
        raise ValueError("Phase 404 BMW SDF SHA-256 drift")
    if int(sdf.get("index", -1)) != 1091:
        raise ValueError("Phase 404 BMW SDF entry index drift")
    if int(sdf.get("compression_type", -1)) != 2:
        raise ValueError("Phase 404 BMW SDF compression type drift")
    if int(sdf.get("compressed_size", -1)) != 1110:
        raise ValueError("Phase 404 BMW SDF compressed size drift")
    if int(sdf.get("uncompressed_size", -1)) != 5056:
        raise ValueError("Phase 404 BMW SDF uncompressed size drift")
    if int(structure.get("body_count", -1)) != len(EXPECTED_BODIES):
        raise ValueError("Phase 404 BMW BODY count drift")
    if tuple(value.get("bodies") or ()) != EXPECTED_BODIES:
        raise ValueError("Phase 404 BMW BODY order/name drift")
    return value


def _values(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        str(entry.get("name")): entry.get("value")
        for entry in record.get("entries") or []
        if isinstance(entry, Mapping)
    }


def _finite3(value: Any, label: str) -> list[float]:
    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes))
        or len(value) != 3
    ):
        raise ValueError(f"{label}: expected exactly three scalars")
    result: list[float] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise ValueError(f"{label}: non-numeric scalar")
        number = float(item)
        if not math.isfinite(number):
            raise ValueError(f"{label}: non-finite scalar")
        result.append(number)
    return result


def _expected_sdf_provenance(intake: Mapping[str, Any]) -> dict[str, Any]:
    sdf_entry = intake.get("sdf_entry") or {}
    return {
        "entry_index": int(sdf_entry.get("index", -1)),
        "path": str(sdf_entry.get("path") or ""),
        "compression_type": int(sdf_entry.get("compression_type", -1)),
        "compressed_size": int(sdf_entry.get("compressed_size", -1)),
        "uncompressed_size": int(sdf_entry.get("uncompressed_size", -1)),
        "decoded_sha256": str(sdf_entry.get("decoded_sha256") or ""),
    }


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _inspect_decoded_sdf(
    data: bytes,
    provenance: Mapping[str, Any],
    intake: Mapping[str, Any],
) -> dict[str, Any]:
    expected = _expected_sdf_provenance(intake)
    for key, wanted in expected.items():
        observed = provenance.get(key)
        if observed != wanted:
            raise ValueError(
                f"BMW SDF provenance drift for {key}: {observed!r} != {wanted!r}"
            )
    if len(data) != expected["uncompressed_size"]:
        raise ValueError(
            f"decoded BMW SDF length drift: {len(data)} != {expected['uncompressed_size']}"
        )

    parsed = parse_sdf(data, strict=True)
    if parsed.get("ready") is not True:
        raise ValueError("decoded BMW SDF did not parse cleanly")
    bodies = records_by_type(parsed, "BODY")
    names = [str(_values(record).get("name") or "") for record in bodies]
    if tuple(names) != EXPECTED_BODIES:
        raise ValueError("decoded BMW SDF BODY order/name drift")

    body0 = _values(bodies[BODY_INDEX])
    pos = _finite3(body0.get("pos"), "BODY0 pos")
    ori = _finite3(body0.get("ori"), "BODY0 ori")
    ori_is_exact_zero = all(value == 0.0 for value in ori)
    return {
        "body_count": len(bodies),
        "body_index": BODY_INDEX,
        "body_name": BODY_NAME,
        "pos": pos,
        "ori": ori,
        "ori_is_exact_zero": ori_is_exact_zero,
        "zero_orientation_identity_shortcut_eligible": ori_is_exact_zero,
    }


def _write_optional_sdf(data: bytes, sdf_out: str | Path | None) -> str | None:
    if sdf_out is None:
        return None
    output = Path(sdf_out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)
    return str(output)


def _result(
    *,
    body0: Mapping[str, Any],
    provenance: Mapping[str, Any],
    materialized_path: str | None,
    source_mode: str,
    archive_input_path: str | None,
    runtime_bootstrap_path: str | None = None,
    physics_manifest_path: str | None = None,
) -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "status": "materialized",
        "ready": True,
        "source_mode": source_mode,
        "retail_archive": {
            "canonical_filename": "BMW_M3_E36.bff",
            "sha256": TARGET_ARCHIVE_SHA256,
            "input_path": archive_input_path,
        },
        "resource": {
            "path": TARGET_RESOURCE,
            "entry_index": provenance.get("entry_index"),
            "compression_type": provenance.get("compression_type"),
            "compressed_size": provenance.get("compressed_size"),
            "uncompressed_size": provenance.get("uncompressed_size"),
            "decoded_sha256": provenance.get("decoded_sha256"),
            "materialized_path": materialized_path,
        },
        "runtime_bootstrap": (
            {
                "format": RUNTIME_BOOTSTRAP_FORMAT,
                "path": runtime_bootstrap_path,
                "vehicle_physics_manifest": physics_manifest_path,
                "vehicle_sdf_handoff_consumed": True,
            }
            if runtime_bootstrap_path is not None
            else None
        ),
        "body0": dict(body0),
        "handoff": {
            "BODY0_resource_pos_ori_values_ready": True,
            "construction_bind_continuity_input_ready": True,
            "BODY0_local_to_SDF_model_bind_pose_ready": False,
            "SDF_model_to_VHF_vehicle_root_frame_relation_ready": False,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "next_proof": {
            "consumer": "tools/ghidra/build_bmw_body0_construction_bind_continuity.py",
            "requires_materialized_sdf": materialized_path is None,
            "remaining_semantic_blocker": (
                "outer Vehicle root -> VHF vehicle-root frame relation"
            ),
            "remaining_semantic_blockers": [
                "BMW numeric HDVehicle offset33b values",
                "outer Vehicle root -> VHF vehicle-root frame relation",
            ],
        },
        "scope": {
            "original_game_executed": False,
            "new_runtime_capture_required": False,
            "new_BFF_parser_semantics_added": False,
            "retail_hash_semantics_rederived": False,
            "typed_resource_identity_rederived": False,
            "SDF_model_frame_assumed_equal_VHF_vehicle_root": False,
            "outer_vehicle_root_assumed_equal_VHF_vehicle_root": False,
            "vehicle_world_transform_claimed": False,
        },
    }


def materialize_bmw_body0_bind_resource(
    bff_path: str | Path,
    *,
    intake_path: str | Path = DEFAULT_INTAKE,
    sdf_out: str | Path | None = None,
) -> dict[str, Any]:
    """Extract the exact BMW SDF from the retail BFF and inspect BODY0."""
    archive_path = Path(bff_path)
    intake_file = Path(intake_path)
    intake = _load_intake(intake_file)

    data, provenance = extract_target_sdf(archive_path)
    body0 = _inspect_decoded_sdf(data, provenance, intake)
    written = _write_optional_sdf(data, sdf_out)

    return _result(
        body0=body0,
        provenance=provenance,
        materialized_path=written,
        source_mode="retail-bff-extraction",
        archive_input_path=str(archive_path),
    )


def _resolve_recorded_file(raw: Any, *, record_path: Path, label: str) -> Path:
    text = str(raw or "").strip()
    if not text:
        raise ValueError(f"{label}: path missing")
    value = Path(text).expanduser()
    if value.is_absolute():
        if not value.is_file():
            raise ValueError(f"{label}: file missing: {value}")
        return value.resolve()

    candidates = [
        (Path.cwd() / value).resolve(),
        (record_path.parent / value).resolve(),
    ]
    existing: list[Path] = []
    for candidate in candidates:
        if candidate.is_file() and candidate not in existing:
            existing.append(candidate)
    if not existing:
        raise ValueError(f"{label}: recorded relative file not found: {text}")
    if len(existing) != 1:
        raise ValueError(f"{label}: recorded relative path is ambiguous: {text}")
    return existing[0]


def _validate_runtime_bootstrap_sdf(
    bootstrap_path: Path,
    intake: Mapping[str, Any],
) -> tuple[bytes, dict[str, Any], Path, Path]:
    bootstrap = _load_json_object(
        bootstrap_path,
        expected_format=RUNTIME_BOOTSTRAP_FORMAT,
    )
    if bootstrap.get("offline_build_ready") is not True:
        raise ValueError("runtime bootstrap offline build is not ready")
    if str(bootstrap.get("vehicle") or "") != TARGET_VEHICLE:
        raise ValueError("runtime bootstrap vehicle is not BMW_M3_E36")

    readiness = bootstrap.get("readiness") or {}
    if not isinstance(readiness, Mapping):
        raise ValueError("runtime bootstrap readiness missing")
    if readiness.get("retail_archive_identity_ready") is not True:
        raise ValueError("runtime bootstrap retail archive identity is not ready")
    if readiness.get("vehicle_physics_materialized_resources_ready") is not True:
        raise ValueError("runtime bootstrap typed physics materializations are not ready")

    artifacts = bootstrap.get("artifacts") or {}
    if not isinstance(artifacts, Mapping):
        raise ValueError("runtime bootstrap artifacts missing")
    sdf_path = _resolve_recorded_file(
        artifacts.get("vehicle_sdf"),
        record_path=bootstrap_path,
        label="runtime bootstrap vehicle_sdf",
    )
    manifest_path = _resolve_recorded_file(
        artifacts.get("vehicle_physics_manifest"),
        record_path=bootstrap_path,
        label="runtime bootstrap vehicle_physics_manifest",
    )
    manifest = _load_json_object(
        manifest_path,
        expected_format=PHYSICS_MANIFEST_FORMAT,
    )
    if manifest.get("ready") is not True:
        raise ValueError("vehicle physics manifest is not ready")
    if manifest.get("materialized_resources_ready") is not True:
        raise ValueError("vehicle physics manifest materialized resources are not ready")
    if manifest.get("blocking_reasons") not in ([], None):
        raise ValueError("vehicle physics manifest has blocking reasons")

    entries = manifest.get("entries") or {}
    sdf = entries.get("sdf") if isinstance(entries, Mapping) else None
    if not isinstance(sdf, Mapping):
        raise ValueError("vehicle physics manifest has no SDF entry")
    normalized_path = str(sdf.get("path") or "").replace("\\", "/").strip("/").lower()
    if normalized_path != TARGET_RESOURCE.lower():
        raise ValueError("vehicle physics manifest SDF path drift")
    if str(sdf.get("decoded_sha256") or "").lower() != TARGET_RESOURCE_SHA256:
        raise ValueError("vehicle physics manifest SDF decoded SHA-256 drift")
    if str(sdf.get("materialized_sha256") or "").lower() != TARGET_RESOURCE_SHA256:
        raise ValueError("vehicle physics manifest SDF materialized SHA-256 drift")
    if sdf.get("materialization_source") != TYPED_CLOSURE_FORMAT:
        raise ValueError("vehicle physics manifest SDF materialization source drift")

    manifest_sdf_path = _resolve_recorded_file(
        sdf.get("materialized_path"),
        record_path=manifest_path,
        label="vehicle physics manifest SDF materialized_path",
    )
    if manifest_sdf_path != sdf_path:
        raise ValueError("runtime bootstrap vehicle_sdf disagrees with physics manifest")

    data = sdf_path.read_bytes()
    if _sha256_bytes(data) != TARGET_RESOURCE_SHA256:
        raise ValueError("runtime bootstrap vehicle_sdf current SHA-256 mismatch")

    provenance = _expected_sdf_provenance(intake)
    return data, provenance, sdf_path, manifest_path


def materialize_bmw_body0_bind_resource_from_runtime_bootstrap(
    runtime_bootstrap_path: str | Path,
    *,
    intake_path: str | Path = DEFAULT_INTAKE,
    sdf_out: str | Path | None = None,
) -> dict[str, Any]:
    """Consume Process 3's exact persistent decoded SDF without re-extraction."""
    bootstrap_path = Path(runtime_bootstrap_path)
    intake = _load_intake(Path(intake_path))
    data, provenance, input_sdf, manifest_path = _validate_runtime_bootstrap_sdf(
        bootstrap_path,
        intake,
    )
    body0 = _inspect_decoded_sdf(data, provenance, intake)
    written = _write_optional_sdf(data, sdf_out)
    materialized_path = written if written is not None else str(input_sdf)

    return _result(
        body0=body0,
        provenance=provenance,
        materialized_path=materialized_path,
        source_mode="offline-runtime-bootstrap-typed-sdf",
        archive_input_path=None,
        runtime_bootstrap_path=str(bootstrap_path),
        physics_manifest_path=str(manifest_path),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "bff",
        nargs="?",
        type=Path,
        help="exact retail BMW_M3_E36.bff bytes (legacy/source-backed path)",
    )
    parser.add_argument(
        "--runtime-bootstrap",
        type=Path,
        help=(
            "SHIFT.OfflineRuntimeBootstrap/1 with exact artifacts.vehicle_sdf; "
            "mutually exclusive with bff"
        ),
    )
    parser.add_argument(
        "--intake",
        type=Path,
        default=DEFAULT_INTAKE,
        help="Phase 404 BMW intake evidence",
    )
    parser.add_argument(
        "--sdf-out",
        type=Path,
        help="optional copy path for exact decoded aarm_multilink.sdf bytes",
    )
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)

    if (args.bff is None) == (args.runtime_bootstrap is None):
        parser.error("choose exactly one of bff or --runtime-bootstrap")

    if args.runtime_bootstrap is not None:
        report = materialize_bmw_body0_bind_resource_from_runtime_bootstrap(
            args.runtime_bootstrap,
            intake_path=args.intake,
            sdf_out=args.sdf_out,
        )
    else:
        assert args.bff is not None
        report = materialize_bmw_body0_bind_resource(
            args.bff,
            intake_path=args.intake,
            sdf_out=args.sdf_out,
        )

    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
