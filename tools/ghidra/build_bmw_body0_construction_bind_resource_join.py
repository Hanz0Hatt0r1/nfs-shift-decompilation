#!/usr/bin/env python3
"""Join exact retail BMW BODY0 resource values to the proven construction bind chain.

This is the byte-free CI consumer for the exact BODY[0] pos/ori values recovered
from the hash-admitted retail BMW_M3_E36.bff.  It reuses
SHIFT.BMWBody0ConstructionBindContinuity/1 for the static SDF descriptor ->
persistent BODY writer proof, validates the committed derived resource metadata,
and materializes only BODY0-local -> SDF-model construction-frame pose.

It deliberately does not equate the SDF model frame with the VHF vehicle-root
or assembly frame, so SHIFT.BMWBody0BindFrameProof/1 remains fail-closed.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_bmw_body0_construction_bind_continuity as _continuity

FORMAT = "SHIFT.BMWBody0ConstructionBindResourceJoin/1"
RESOURCE_VALUES_FORMAT = "SHIFT.BMWBody0BindResourceValues/1"
DEFAULT_RESOURCE_VALUES = ROOT / "evidence" / "bmw_m3_e36_body0_bind_resource_values.json"

ARCHIVE_FILENAME = "BMW_M3_E36.bff"
ARCHIVE_SIZE = 18934688
ARCHIVE_SHA256 = "c31d34a0a7cab04bcff693fa0cbda3400f50d690a9c8bb2521b2882fc2a68d70"
RESOURCE_PATH = "vehicles/physics/suspension/aarm_multilink.sdf"
RESOURCE_ENTRY_INDEX = 1091
RESOURCE_COMPRESSION_TYPE = 2
RESOURCE_COMPRESSED_SIZE = 1110
RESOURCE_UNCOMPRESSED_SIZE = 5056
RESOURCE_SHA256 = "fe0b18e95e81f87d67076b70890965a0a1384a925bfd836aaf5aa705fc4781ed"
EXPECTED_BODY0_POS = [0.0, 0.0, 0.0]
EXPECTED_BODY0_ORI = [0.0, 0.0, 0.0]


def _load_json(path: Path, expected_format: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    if value.get("format") != expected_format:
        raise ValueError(f"{path}: expected {expected_format}")
    return value


def _require_equal(observed: Any, expected: Any, label: str) -> None:
    if observed != expected:
        raise ValueError(f"{label} drift: {observed!r} != {expected!r}")


def _validate_resource_values(
    path: Path,
    intake: Mapping[str, Any],
) -> dict[str, Any]:
    value = _load_json(path, RESOURCE_VALUES_FORMAT)
    if value.get("version") != 1 or value.get("ready") is not True:
        raise ValueError("BMW BODY0 resource values are not ready")
    if value.get("status") != "exact-retail-derived-values":
        raise ValueError("BMW BODY0 resource-values status drift")

    source = value.get("source")
    body0 = value.get("body0")
    scope = value.get("scope")
    if not isinstance(source, Mapping) or not isinstance(body0, Mapping):
        raise ValueError("BMW BODY0 resource evidence missing source/body0")
    if not isinstance(scope, Mapping):
        raise ValueError("BMW BODY0 resource evidence scope missing")

    archive = intake.get("archive") or {}
    sdf = intake.get("sdf_entry") or {}
    structure = intake.get("structure") or {}

    expected_source = {
        "archive_filename": ARCHIVE_FILENAME,
        "archive_size_bytes": ARCHIVE_SIZE,
        "archive_sha256": ARCHIVE_SHA256,
        "resource_path": RESOURCE_PATH,
        "resource_entry_index": RESOURCE_ENTRY_INDEX,
        "resource_compression_type": RESOURCE_COMPRESSION_TYPE,
        "resource_compressed_size": RESOURCE_COMPRESSED_SIZE,
        "resource_uncompressed_size": RESOURCE_UNCOMPRESSED_SIZE,
        "resource_sha256": RESOURCE_SHA256,
        "extraction_contract": "SHIFT.BMWBody0BindResourceMaterialization/1",
    }
    for key, expected in expected_source.items():
        _require_equal(source.get(key), expected, f"resource source {key}")

    _require_equal(archive.get("filename"), ARCHIVE_FILENAME, "intake archive filename")
    _require_equal(int(archive.get("size_bytes", -1)), ARCHIVE_SIZE, "intake archive size")
    _require_equal(archive.get("sha256"), ARCHIVE_SHA256, "intake archive SHA-256")
    _require_equal(sdf.get("path"), RESOURCE_PATH, "intake SDF path")
    _require_equal(int(sdf.get("index", -1)), RESOURCE_ENTRY_INDEX, "intake SDF index")
    _require_equal(int(sdf.get("compression_type", -1)), RESOURCE_COMPRESSION_TYPE, "intake SDF compression type")
    _require_equal(int(sdf.get("compressed_size", -1)), RESOURCE_COMPRESSED_SIZE, "intake SDF compressed size")
    _require_equal(int(sdf.get("uncompressed_size", -1)), RESOURCE_UNCOMPRESSED_SIZE, "intake SDF uncompressed size")
    _require_equal(sdf.get("decoded_sha256"), RESOURCE_SHA256, "intake SDF SHA-256")

    _require_equal(int(body0.get("body_count", -1)), int(structure.get("body_count", -1)), "BODY count")
    _require_equal(int(body0.get("body_count", -1)), len(_continuity.EXPECTED_BMW_BODIES), "retail BODY count")
    _require_equal(int(body0.get("body_index", -1)), _continuity.BODY_INDEX, "BODY0 index")
    _require_equal(body0.get("body_name"), _continuity.BODY_NAME, "BODY0 name")

    pos = _continuity._finite3(body0.get("pos"), "BODY0 pos")
    ori = _continuity._finite3(body0.get("ori"), "BODY0 ori")
    _require_equal(pos, EXPECTED_BODY0_POS, "BODY0 pos derived value")
    _require_equal(ori, EXPECTED_BODY0_ORI, "BODY0 ori derived value")
    exact_zero = _continuity._zero3(ori)
    if not exact_zero:
        raise ValueError("BMW BODY0 exact-zero orientation proof lost")
    _require_equal(body0.get("ori_is_exact_zero"), True, "BODY0 exact-zero claim")
    _require_equal(
        body0.get("zero_orientation_identity_shortcut_eligible"),
        True,
        "BODY0 identity-shortcut claim",
    )

    for forbidden_true in (
        "raw_archive_committed",
        "raw_resource_committed",
        "original_game_executed",
        "new_runtime_capture_required",
        "identity_matrix_assumed",
        "SDF_model_frame_assumed_equal_VHF_vehicle_root",
        "vehicle_world_transform_claimed",
    ):
        if scope.get(forbidden_true) is not False:
            raise ValueError(f"resource evidence scope must keep {forbidden_true}=false")

    return {
        "path": str(path),
        "format": RESOURCE_VALUES_FORMAT,
        "source": dict(source),
        "body0": {
            "body_count": int(body0["body_count"]),
            "body_index": int(body0["body_index"]),
            "body_name": str(body0["body_name"]),
            "pos": pos,
            "ori": ori,
            "ori_is_exact_zero": True,
        },
    }


def build_bmw_body0_construction_bind_resource_join(
    ghidra_export: Path,
    intake_path: Path,
    resource_values_path: Path = DEFAULT_RESOURCE_VALUES,
) -> dict[str, Any]:
    static = _continuity.build_bmw_body0_construction_bind_continuity(
        ghidra_export,
        intake_path,
    )
    if static.get("ready") is not True:
        raise ValueError("construction bind continuity is not ready")
    handoff = static.get("handoff") or {}
    for key in (
        "BODY_descriptor_pos_ori_semantics_ready",
        "construction_origin_continuity_ready",
        "construction_basis_continuity_ready",
    ):
        if handoff.get(key) is not True:
            raise ValueError(f"construction continuity lost required proof: {key}")
    if handoff.get("BODY0_bind_frame_proof_ready") is not False:
        raise ValueError("upstream continuity unexpectedly claims final BODY0 bind frame")

    intake = _continuity._validate_intake(intake_path)
    resource = _validate_resource_values(resource_values_path, intake)
    pos = resource["body0"]["pos"]
    basis = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
    row_matrix = _continuity._identity_pose_row(pos)

    return {
        "format": FORMAT,
        "version": 1,
        "status": "body0-local-to-sdf-model-bind-proven",
        "ready": True,
        "static_continuity": {
            "format": static.get("format"),
            "status": static.get("status"),
            "source_static_proof": static.get("source_static_proof"),
        },
        "resource_values": resource,
        "BODY0_local_to_SDF_model": {
            "ready": True,
            "evidence_state": "proven-exact-retail-derived-values-plus-static-construction-continuity",
            "body_index": _continuity.BODY_INDEX,
            "body_name": _continuity.BODY_NAME,
            "origin": list(pos),
            "orientation": list(resource["body0"]["ori"]),
            "basis": basis,
            "row_matrix": row_matrix,
            "matrix_is_exact_identity": row_matrix == [
                1.0, 0.0, 0.0, 0.0,
                0.0, 1.0, 0.0, 0.0,
                0.0, 0.0, 1.0, 0.0,
                0.0, 0.0, 0.0, 1.0,
            ],
        },
        "handoff": {
            "BODY_descriptor_pos_ori_semantics_ready": True,
            "construction_origin_continuity_ready": True,
            "construction_basis_continuity_ready": True,
            "BODY0_resource_pos_ori_values_ready": True,
            "BODY0_local_to_SDF_model_bind_pose_ready": True,
            "SDF_model_to_VHF_vehicle_root_frame_relation_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "blockers": [
            {
                "id": "SDF-model-to-VHF-vehicle-root-frame-relation-unproven",
                "status": "unknown",
                "required_evidence": (
                    "prove the static frame relation between the SDF model construction frame "
                    "and the VHF vehicle-root/assembly frame; do not infer equality from the exact "
                    "identity BODY0 local pose"
                ),
            }
        ],
        "scope": {
            "raw_archive_required_in_CI": False,
            "raw_SDF_required_in_CI": False,
            "raw_game_bytes_committed": False,
            "identity_matrix_assumed": False,
            "identity_matrix_derived_from_exact_zero_pos_ori": True,
            "SDF_model_frame_assumed_equal_VHF_vehicle_root": False,
            "BODY0_bind_frame_proof_claimed": False,
            "vehicle_world_transform_claimed": False,
            "original_game_executed": False,
            "new_runtime_capture_required": False,
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument("bmw_intake", type=Path)
    parser.add_argument(
        "--resource-values",
        type=Path,
        default=DEFAULT_RESOURCE_VALUES,
        help="committed SHIFT.BMWBody0BindResourceValues/1 evidence",
    )
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)

    report = build_bmw_body0_construction_bind_resource_join(
        args.ghidra_export,
        args.bmw_intake,
        args.resource_values,
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
