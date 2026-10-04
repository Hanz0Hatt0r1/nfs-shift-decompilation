#!/usr/bin/env python3
"""Materialize the exact retail BMW BODY0 SDF pose input for Process 1.

This tool solves the data-availability half of the remaining BMW BODY0 bind
blocker.  It reuses the already source-backed BMW BFF extractor and Phase 404
intake evidence, writes the exact decoded ``aarm_multilink.sdf`` when requested,
and reports BODY[0] ``pos``/``ori`` without inventing the still-unproven
SDF-model -> VHF vehicle-root frame relation.
"""
from __future__ import annotations

import argparse
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
DEFAULT_INTAKE = ROOT / "evidence" / "bmw_m3_e36_physics_intake_phase404.json"
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


def _load_intake(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("format") != INTAKE_FORMAT:
        raise ValueError(f"{path}: expected {INTAKE_FORMAT}")

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


def _inspect_decoded_sdf(
    data: bytes,
    provenance: Mapping[str, Any],
    intake: Mapping[str, Any],
) -> dict[str, Any]:
    sdf_entry = intake.get("sdf_entry") or {}
    expected = {
        "entry_index": int(sdf_entry.get("index", -1)),
        "path": str(sdf_entry.get("path") or ""),
        "compression_type": int(sdf_entry.get("compression_type", -1)),
        "compressed_size": int(sdf_entry.get("compressed_size", -1)),
        "uncompressed_size": int(sdf_entry.get("uncompressed_size", -1)),
        "decoded_sha256": str(sdf_entry.get("decoded_sha256") or ""),
    }
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


def materialize_bmw_body0_bind_resource(
    bff_path: str | Path,
    *,
    intake_path: str | Path = DEFAULT_INTAKE,
    sdf_out: str | Path | None = None,
) -> dict[str, Any]:
    archive_path = Path(bff_path)
    intake_file = Path(intake_path)
    intake = _load_intake(intake_file)

    data, provenance = extract_target_sdf(archive_path)
    body0 = _inspect_decoded_sdf(data, provenance, intake)

    written: str | None = None
    if sdf_out is not None:
        output = Path(sdf_out)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(data)
        written = str(output)

    return {
        "format": FORMAT,
        "version": 1,
        "status": "materialized",
        "ready": True,
        "retail_archive": {
            "canonical_filename": "BMW_M3_E36.bff",
            "sha256": TARGET_ARCHIVE_SHA256,
            "input_path": str(archive_path),
        },
        "resource": {
            "path": TARGET_RESOURCE,
            "entry_index": provenance.get("entry_index"),
            "compression_type": provenance.get("compression_type"),
            "compressed_size": provenance.get("compressed_size"),
            "uncompressed_size": provenance.get("uncompressed_size"),
            "decoded_sha256": provenance.get("decoded_sha256"),
            "materialized_path": written,
        },
        "body0": body0,
        "handoff": {
            "BODY0_resource_pos_ori_values_ready": True,
            "construction_bind_continuity_input_ready": True,
            "BODY0_local_to_SDF_model_bind_pose_ready": False,
            "SDF_model_to_VHF_vehicle_root_frame_relation_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "next_proof": {
            "consumer": "tools/ghidra/build_bmw_body0_construction_bind_continuity.py",
            "requires_materialized_sdf": written is None,
            "remaining_semantic_blocker": (
                "SDF model construction frame -> VHF vehicle-root/assembly frame relation"
            ),
        },
        "scope": {
            "original_game_executed": False,
            "new_runtime_capture_required": False,
            "new_BFF_parser_semantics_added": False,
            "retail_hash_semantics_rederived": False,
            "SDF_model_frame_assumed_equal_VHF_vehicle_root": False,
            "vehicle_world_transform_claimed": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bff", type=Path, help="exact retail BMW_M3_E36.bff bytes")
    parser.add_argument(
        "--intake",
        type=Path,
        default=DEFAULT_INTAKE,
        help="Phase 404 BMW intake evidence",
    )
    parser.add_argument(
        "--sdf-out",
        type=Path,
        help="optional output path for exact decoded aarm_multilink.sdf bytes",
    )
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)

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
