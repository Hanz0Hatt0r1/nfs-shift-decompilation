#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.BMWOuterVHFNumericRelation/1"
SEMANTIC_FORMAT = "SHIFT.OuterVehicleBMWVHFRootRelation/1"
DELTA_FORMAT = "SHIFT.BMWPrimaryPlayerFirstBootstrapRenderRootDelta/1"
ROOT_FORMAT = "SHIFT.BMWVHFHierarchyRootFrame/1"
VEHICLE = "BMW_M3_E36"
SESSION = "Silverstone+BMW_M3_E36"
CANONICAL_VHF = "vehicles/bmw_m3_e36/bmw_m3_e36.vhf"
DECODED_SHA256 = "e08887d17d9e34e703a385260f41017fc19acbebc3405614b375e81766b4bd51"
ROOT_PATH = "CAR[BMW_M3_E36]/NODE[HIERARCHY:Root]"
ROW_CONVENTION = "row-major D3D row-vector affine"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    _require(isinstance(value, Mapping), f"{label} missing")
    return value


def _vector(value: Any, count: int, label: str) -> tuple[float, ...]:
    _require(
        isinstance(value, Sequence) and not isinstance(value, (str, bytes)),
        f"{label} must be numeric sequence",
    )
    _require(len(value) == count, f"{label} must contain exactly {count} scalars")
    out: list[float] = []
    for item in value:
        _require(
            not isinstance(item, bool) and isinstance(item, (int, float)),
            f"{label} contains non-numeric scalar",
        )
        number = float(item)
        _require(math.isfinite(number), f"{label} contains non-finite scalar")
        out.append(number)
    return tuple(out)


def _matrix16(value: Any, label: str) -> tuple[float, ...]:
    return _vector(value, 16, label)


def _validate_row_affine(matrix: Sequence[float], label: str) -> None:
    _require(
        all(abs(float(matrix[index])) <= 1.0e-9 for index in (3, 7, 11)),
        f"{label} is not row-vector affine",
    )
    _require(
        abs(float(matrix[15]) - 1.0) <= 1.0e-9,
        f"{label} homogeneous component drift",
    )


def _matmul(a: Sequence[float], b: Sequence[float]) -> tuple[float, ...]:
    _require(len(a) == 16 and len(b) == 16, "matrix multiply requires 4x4 matrices")
    return tuple(
        sum(float(a[row * 4 + k]) * float(b[k * 4 + column]) for k in range(4))
        for row in range(4)
        for column in range(4)
    )


def _inverse4(matrix: Sequence[float]) -> tuple[float, ...]:
    _require(len(matrix) == 16, "matrix inverse requires 4x4 matrix")
    rows = [
        [float(matrix[row * 4 + column]) for column in range(4)]
        + [1.0 if row == column else 0.0 for column in range(4)]
        for row in range(4)
    ]
    for column in range(4):
        pivot = max(range(column, 4), key=lambda row: abs(rows[row][column]))
        _require(
            abs(rows[pivot][column]) > 1.0e-12,
            "VHF root->outer matrix is singular",
        )
        if pivot != column:
            rows[column], rows[pivot] = rows[pivot], rows[column]
        scale = rows[column][column]
        rows[column] = [value / scale for value in rows[column]]
        for row in range(4):
            if row == column:
                continue
            factor = rows[row][column]
            if factor:
                rows[row] = [
                    rows[row][index] - factor * rows[column][index]
                    for index in range(8)
                ]
    out = tuple(rows[row][4 + column] for row in range(4) for column in range(4))
    _require(all(math.isfinite(value) for value in out), "matrix inverse produced non-finite scalar")
    return out


def _translation(delta: Sequence[float]) -> tuple[float, ...]:
    x, y, z = _vector(delta, 3, "delta_local")
    return (
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        x, y, z, 1.0,
    )


def _validate_semantic(value: Mapping[str, Any]) -> None:
    _require(
        value.get("format") == SEMANTIC_FORMAT and value.get("ready") is True,
        "semantic outer/VHF relation not positive",
    )
    subject = _mapping(value.get("subject"), "semantic subject")
    _require(subject.get("vehicle") == VEHICLE, "semantic vehicle drift")
    _require(
        str(subject.get("canonical_vhf") or "").replace("\\", "/").lower()
        == CANONICAL_VHF,
        "semantic canonical VHF drift",
    )
    _require(
        str(subject.get("decoded_sha256") or "").lower() == DECODED_SHA256,
        "semantic decoded VHF identity drift",
    )
    _require(subject.get("root_node_path") == ROOT_PATH, "semantic root path drift")
    relation = _mapping(value.get("relation"), "semantic relation")
    _require(relation.get("kind") == "fixed_affine", "semantic relation kind drift")
    _require(
        relation.get("matrix_convention") == ROW_CONVENTION,
        "semantic matrix convention drift",
    )
    _require(
        relation.get("outer_to_vhf_root_formula")
        == "inverse(M_vhf_root_to_model * T(delta_local))",
        "semantic numeric formula drift",
    )
    _require(
        relation.get("relation_matrix_numeric_ready") is False,
        "semantic input unexpectedly already numeric",
    )
    handoff = _mapping(value.get("handoff"), "semantic handoff")
    _require(
        handoff.get("outer_vehicle_root_to_VHF_vehicle_root_ready") is True,
        "semantic outer/VHF relation gate not ready",
    )
    _require(
        handoff.get("outer_vehicle_root_to_VHF_fixed_affine_delta_ready") is True,
        "semantic fixed-affine gate not ready",
    )
    _require(
        handoff.get("outer_vehicle_root_to_VHF_relation_numeric_matrix_ready") is False,
        "semantic numeric gate unexpectedly preclaimed",
    )


def _validate_delta(value: Mapping[str, Any]) -> tuple[float, float, float]:
    _require(
        value.get("format") == DELTA_FORMAT and value.get("ready") is True,
        "first-bootstrap delta proof not positive",
    )
    _require(
        value.get("status") == "bmw-primary-player-first-bootstrap-render-root-delta-proven",
        "delta proof status drift",
    )
    _require(
        value.get("vehicle") == VEHICLE and value.get("session_target") == SESSION,
        "delta proof subject drift",
    )
    selected = _mapping(value.get("selected_numeric"), "selected delta")
    delta = _vector(selected.get("delta_local"), 3, "selected delta_local")
    _require(
        delta == (0.0, 0.0, 0.0),
        "S2 proof scope requires exact first-bootstrap delta_local=(0,0,0)",
    )
    _require(selected.get("producer") == "FUN_00795d60", "delta producer drift")
    handoff = _mapping(value.get("handoff"), "delta handoff")
    _require(
        handoff.get("BMW_primary_player_first_bootstrap_render_root_delta_numeric_ready")
        is True,
        "delta numeric gate not ready",
    )
    _require(
        handoff.get("outer_vehicle_root_to_VHF_relation_numeric_matrix_ready") is False,
        "delta input unexpectedly preclaims numeric relation",
    )
    return delta


def _validate_root(
    value: Mapping[str, Any], semantic: Mapping[str, Any]
) -> tuple[float, ...]:
    _require(
        value.get("format") == ROOT_FORMAT
        and value.get("version") == 1
        and value.get("ready") is True,
        "exact BMW VHF root-frame artifact not positive",
    )
    _require(
        value.get("status") == "canonical-bmw-vhf-hierarchy-root-frame-proven",
        "BMW VHF root-frame status drift",
    )
    source = _mapping(value.get("source"), "root-frame source")
    _require(
        str(source.get("resolved_path") or "").replace("\\", "/").lower()
        == CANONICAL_VHF,
        "root-frame VHF path drift",
    )
    _require(
        str(source.get("decoded_sha256") or "").lower() == DECODED_SHA256,
        "root-frame decoded SHA-256 drift",
    )
    frame = _mapping(value.get("vehicle_root_frame"), "vehicle_root_frame")
    _require(frame.get("car_name") == VEHICLE, "root-frame CAR identity drift")
    _require(frame.get("node_path") == ROOT_PATH, "root-frame node path drift")
    matrix_number = str(frame.get("matrix_number") or "")
    semantic_subject = _mapping(semantic.get("subject"), "semantic subject")
    _require(
        matrix_number == str(semantic_subject.get("matrix_number") or ""),
        "root-frame MatrixNumber disagrees with semantic relation",
    )
    chain = frame.get("matrix_parent_chain_ids")
    _require(
        isinstance(chain, list) and bool(chain) and str(chain[-1]) == matrix_number,
        "root-frame parent chain missing/drift",
    )
    root = _matrix16(
        frame.get("world_matrix_row_vector"),
        "BMW VHF root world row matrix",
    )
    _validate_row_affine(root, "BMW VHF root world row matrix")
    handoff = _mapping(value.get("handoff"), "root-frame handoff")
    _require(
        handoff.get("canonical_BMW_VHF_hierarchy_root_frame_ready") is True,
        "root-frame gate not ready",
    )
    _require(
        handoff.get("canonical_BMW_VHF_hierarchy_root_matrix_ready") is True,
        "root-matrix gate not ready",
    )
    return root


def evaluate(
    semantic: Mapping[str, Any],
    delta_proof: Mapping[str, Any],
    root_frame: Mapping[str, Any],
) -> dict[str, Any]:
    _validate_semantic(semantic)
    delta = _validate_delta(delta_proof)
    root_to_model = _validate_root(root_frame, semantic)
    root_to_outer = _matmul(root_to_model, _translation(delta))
    _validate_row_affine(root_to_outer, "VHF root->outer matrix")
    outer_to_root = _inverse4(root_to_outer)
    _validate_row_affine(outer_to_root, "outer->VHF root matrix")
    identity_check = _matmul(root_to_outer, outer_to_root)
    _require(
        all(
            abs(identity_check[index] - (1.0 if index // 4 == index % 4 else 0.0))
            <= 1.0e-8
            for index in range(16)
        ),
        "matrix inverse verification failed",
    )

    subject = _mapping(semantic.get("subject"), "semantic subject")
    frame = _mapping(root_frame.get("vehicle_root_frame"), "vehicle_root_frame")
    return {
        "format": FORMAT,
        "version": 1,
        "status": "selected-bmw-first-bootstrap-outer-vhf-numeric-relation-proven",
        "ready": True,
        "vehicle": VEHICLE,
        "session_target": SESSION,
        "inputs": {
            "semantic_relation": SEMANTIC_FORMAT,
            "delta_proof": DELTA_FORMAT,
            "vhf_root_frame": ROOT_FORMAT,
        },
        "subject": {
            "canonical_vhf": CANONICAL_VHF,
            "decoded_sha256": DECODED_SHA256,
            "root_node_path": ROOT_PATH,
            "matrix_number": str(subject.get("matrix_number")),
            "matrix_parent_chain_ids": [
                str(value) for value in frame.get("matrix_parent_chain_ids")
            ],
        },
        "numeric": {
            "matrix_convention": ROW_CONVENTION,
            "delta_local": list(delta),
            "M_vhf_root_to_model": list(root_to_model),
            "M_vhf_root_to_outer": list(root_to_outer),
            "M_outer_to_vhf_root": list(outer_to_root),
            "formula": "M_outer_to_vhf_root = inverse(M_vhf_root_to_model * T(delta_local))",
            "finite": True,
            "invertible": True,
        },
        "handoff": {
            "outer_vehicle_root_to_VHF_vehicle_root_ready": True,
            "outer_vehicle_root_to_VHF_fixed_affine_delta_ready": True,
            "outer_vehicle_root_to_VHF_relation_numeric_matrix_ready": True,
            "BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
            "consumer": "single-process S3 SHIFT.BMWBody0BindFrameProof/1 composition",
        },
        "limits": {
            "first_primary_player_bootstrap_only": True,
            "identity_semantics_inferred_from_numeric_identity": False,
            "synthetic_root_matrix_allowed": False,
            "BODY0_bind_frame_claimed": False,
            "vehicle_world_transform_claimed": False,
        },
    }


def _load(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(value, Mapping), f"{path}: expected JSON object")
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("semantic_relation", type=Path)
    parser.add_argument("delta_proof", type=Path)
    parser.add_argument("vhf_root_frame", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    report = evaluate(
        _load(args.semantic_relation),
        _load(args.delta_proof),
        _load(args.vhf_root_frame),
    )
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
