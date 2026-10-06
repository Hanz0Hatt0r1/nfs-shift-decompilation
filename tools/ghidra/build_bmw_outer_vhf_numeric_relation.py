#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.BMWOuterVehicleVHFNumericRelation/1"
RELATION_FORMAT = "SHIFT.OuterVehicleBMWVHFRootRelation/1"
DELTA_FORMAT = "SHIFT.BMWPrimaryPlayerFirstBootstrapRenderRootDelta/1"
ROOT_FORMAT = "SHIFT.BMWVHFHierarchyRootFrame/1"
RESOURCE_JOIN_FORMAT = "SHIFT.BMWVehicleRenderModelResourceJoin/1"
CANONICAL_VHF = "vehicles/bmw_m3_e36/bmw_m3_e36.vhf"
DECODED_VHF_SHA256 = "e08887d17d9e34e703a385260f41017fc19acbebc3405614b375e81766b4bd51"
ROOT_NODE_PATH = "CAR[BMW_M3_E36]/NODE[HIERARCHY:Root]"
ROW_VECTOR_CONVENTION = "row-major D3D row-vector affine"

_ROOT_BUILDER_PATH = Path(__file__).with_name("build_bmw_vhf_hierarchy_root_frame.py")
_ROOT_SPEC = importlib.util.spec_from_file_location("bmw_vhf_root_builder_for_numeric_relation", _ROOT_BUILDER_PATH)
if _ROOT_SPEC is None or _ROOT_SPEC.loader is None:
    raise RuntimeError("cannot load BMW VHF root-frame builder")
_ROOT_BUILDER = importlib.util.module_from_spec(_ROOT_SPEC)
_ROOT_SPEC.loader.exec_module(_ROOT_BUILDER)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    _require(isinstance(value, Mapping), f"{label} missing")
    return value


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(value, dict), f"{path}: expected JSON object")
    return value


def _matrix16(value: Any, label: str) -> list[float]:
    _require(
        isinstance(value, Sequence) and not isinstance(value, (str, bytes)) and len(value) == 16,
        f"{label} must contain 16 scalars",
    )
    out: list[float] = []
    for item in value:
        _require(not isinstance(item, bool) and isinstance(item, (int, float)), f"{label} contains non-numeric scalar")
        number = float(item)
        _require(math.isfinite(number), f"{label} contains non-finite scalar")
        out.append(number)
    return out


def _mat_mul(a: Sequence[float], b: Sequence[float]) -> list[float]:
    _require(len(a) == 16 and len(b) == 16, "matrix multiply requires 4x4 matrices")
    return [
        sum(float(a[row * 4 + k]) * float(b[k * 4 + col]) for k in range(4))
        for row in range(4)
        for col in range(4)
    ]


def _inverse4(matrix: Sequence[float]) -> list[float]:
    source = _matrix16(matrix, "matrix inverse input")
    augmented = [
        [source[row * 4 + col] for col in range(4)]
        + [1.0 if row == col else 0.0 for col in range(4)]
        for row in range(4)
    ]
    for col in range(4):
        pivot = max(range(col, 4), key=lambda row: abs(augmented[row][col]))
        _require(abs(augmented[pivot][col]) > 1.0e-12, "outer/VHF affine matrix is singular")
        augmented[col], augmented[pivot] = augmented[pivot], augmented[col]
        divisor = augmented[col][col]
        augmented[col] = [value / divisor for value in augmented[col]]
        for row in range(4):
            if row == col:
                continue
            factor = augmented[row][col]
            if factor != 0.0:
                augmented[row] = [
                    value - factor * pivot_value
                    for value, pivot_value in zip(augmented[row], augmented[col])
                ]
    return [augmented[row][col] for row in range(4) for col in range(4, 8)]


def _translation_row(delta: Sequence[float]) -> list[float]:
    _require(len(delta) == 3, "delta_local must contain three scalars")
    xyz: list[float] = []
    for item in delta:
        _require(not isinstance(item, bool) and isinstance(item, (int, float)), "delta_local contains non-numeric scalar")
        number = float(item)
        _require(math.isfinite(number), "delta_local contains non-finite scalar")
        xyz.append(number)
    return [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        xyz[0], xyz[1], xyz[2], 1.0,
    ]


def _is_identity(matrix: Sequence[float], tolerance: float = 1.0e-9) -> bool:
    identity = [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0,
    ]
    return all(abs(float(a) - b) <= tolerance for a, b in zip(matrix, identity))


def _validate_relation(value: Mapping[str, Any]) -> None:
    _require(value.get("format") == RELATION_FORMAT and value.get("ready") is True, "outer/VHF semantic relation not positive")
    subject = _mapping(value.get("subject"), "outer/VHF relation subject")
    _require(subject.get("vehicle") == "BMW_M3_E36", "outer/VHF vehicle identity drift")
    _require(str(subject.get("canonical_vhf") or "").replace("\\", "/").lower() == CANONICAL_VHF, "outer/VHF canonical VHF drift")
    _require(str(subject.get("decoded_sha256") or "").lower() == DECODED_VHF_SHA256, "outer/VHF decoded VHF identity drift")
    _require(subject.get("root_node_path") == ROOT_NODE_PATH, "outer/VHF root node drift")
    _require(str(subject.get("matrix_number") or "") == "0", "outer/VHF root MatrixNumber drift")
    relation = _mapping(value.get("relation"), "outer/VHF relation")
    _require(relation.get("kind") == "fixed_affine", "outer/VHF relation must remain setup-fixed affine")
    _require(relation.get("matrix_convention") == ROW_VECTOR_CONVENTION, "outer/VHF matrix convention drift")
    _require(relation.get("delta_producer") == "FUN_00795d60", "outer/VHF delta producer drift")
    _require(relation.get("relation_matrix_numeric_ready") is False, "upstream relation already preclaims numeric matrix")
    handoff = _mapping(value.get("handoff"), "outer/VHF relation handoff")
    _require(handoff.get("outer_vehicle_root_to_VHF_vehicle_root_ready") is True, "outer/VHF semantic relation gate not ready")
    _require(handoff.get("outer_vehicle_root_to_VHF_fixed_affine_delta_ready") is True, "outer/VHF fixed-affine gate not ready")
    _require(handoff.get("outer_vehicle_root_to_VHF_relation_numeric_matrix_ready") is False, "outer/VHF numeric gate preclaimed")


def _validate_delta(value: Mapping[str, Any]) -> list[float]:
    _require(value.get("format") == DELTA_FORMAT and value.get("ready") is True, "selected BMW delta contract not positive")
    _require(value.get("vehicle") == "BMW_M3_E36", "selected BMW delta vehicle drift")
    _require(value.get("session_target") == "Silverstone+BMW_M3_E36", "selected BMW delta session drift")
    limits = _mapping(value.get("limits"), "selected BMW delta limits")
    _require(limits.get("first_primary_player_bootstrap_only") is True, "selected BMW delta scope widened")
    selected = _mapping(value.get("selected_numeric"), "selected BMW numeric delta")
    delta = selected.get("delta_local")
    _translation_row(delta)
    _require(selected.get("producer") == "FUN_00795d60", "selected BMW delta producer drift")
    handoff = _mapping(value.get("handoff"), "selected BMW delta handoff")
    _require(handoff.get("BMW_primary_player_first_bootstrap_render_root_delta_numeric_ready") is True, "selected BMW numeric delta gate not ready")
    _require(handoff.get("outer_vehicle_root_to_VHF_relation_numeric_matrix_ready") is False, "selected BMW delta preclaims numeric relation")
    return [float(item) for item in delta]


def build_numeric_relation(
    semantic_relation: Mapping[str, Any],
    selected_delta: Mapping[str, Any],
    root_frame: Mapping[str, Any],
) -> dict[str, Any]:
    _validate_relation(semantic_relation)
    delta = _validate_delta(selected_delta)
    _require(root_frame.get("format") == ROOT_FORMAT and root_frame.get("ready") is True, "exact BMW VHF root frame not positive")
    source = _mapping(root_frame.get("source"), "BMW VHF root source")
    _require(str(source.get("resolved_path") or "").replace("\\", "/").lower() == CANONICAL_VHF, "root-frame canonical VHF drift")
    _require(str(source.get("decoded_sha256") or "").lower() == DECODED_VHF_SHA256, "root-frame decoded SHA-256 drift")
    frame = _mapping(root_frame.get("vehicle_root_frame"), "BMW VHF root frame")
    _require(frame.get("node_path") == ROOT_NODE_PATH and str(frame.get("matrix_number") or "") == "0", "BMW VHF exact root identity drift")
    _require(frame.get("matrix_parent_chain_ids") == ["0"], "BMW VHF Root parent chain drift")
    vhf_root_to_model = _matrix16(frame.get("world_matrix_row_vector"), "BMW VHF Root world row matrix")
    delta_translation = _translation_row(delta)
    vhf_root_to_outer = _mat_mul(vhf_root_to_model, delta_translation)
    outer_to_vhf_root = _inverse4(vhf_root_to_outer)
    _require(all(math.isfinite(item) for item in outer_to_vhf_root), "outer/VHF numeric relation is non-finite")

    numeric_identity = _is_identity(outer_to_vhf_root)
    return {
        "format": FORMAT,
        "version": 1,
        "status": "selected-bmw-first-bootstrap-outer-vhf-numeric-relation-proven",
        "ready": True,
        "vehicle": "BMW_M3_E36",
        "session_target": "Silverstone+BMW_M3_E36",
        "scope": "first explicit native primary-player vehicle bootstrap before any origin-update path",
        "inputs": {
            "semantic_relation": RELATION_FORMAT,
            "selected_delta": DELTA_FORMAT,
            "root_frame": ROOT_FORMAT,
            "resource_join": RESOURCE_JOIN_FORMAT,
        },
        "root_provenance": {
            "canonical_vhf": CANONICAL_VHF,
            "decoded_sha256": DECODED_VHF_SHA256,
            "root_node_path": ROOT_NODE_PATH,
            "matrix_number": "0",
            "matrix_parent_chain_ids": ["0"],
            "world_matrix_row_vector": vhf_root_to_model,
            "world_matrix_is_identity": bool(frame.get("world_matrix_is_identity")),
        },
        "delta_provenance": {
            "producer": "FUN_00795d60",
            "delta_local": delta,
            "lifetime": "selected first native primary-player Vehicle::InitVehicle bootstrap state",
        },
        "composition": {
            "matrix_convention": ROW_VECTOR_CONVENTION,
            "formula_vhf_root_to_outer": "M_vhf_root_to_model * T(delta_local)",
            "formula_outer_to_vhf_root": "inverse(M_vhf_root_to_model * T(delta_local))",
            "M_vhf_root_to_model": vhf_root_to_model,
            "T_delta_local": delta_translation,
            "M_vhf_root_to_outer": vhf_root_to_outer,
            "M_outer_to_vhf_root": outer_to_vhf_root,
        },
        "relation": {
            "kind": "fixed_affine",
            "matrix_convention": ROW_VECTOR_CONVENTION,
            "row_vector_matrix": outer_to_vhf_root,
            "relation_matrix_numeric_ready": True,
            "numeric_matrix_is_identity": numeric_identity,
            "identity_semantics_explicitly_proven": False,
            "identity_numeric_result_does_not_widen_setup_fixed_scope": True,
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
            "identity_inferred_from_root_matrix_alone": False,
            "numeric_identity_promoted_to_global_identity_semantics": False,
            "restart_or_mode_switch_relation_claimed": False,
            "BODY0_bind_frame_claimed": False,
            "vehicle_world_transform_claimed": False,
            "runtime_capture_used": False,
            "original_game_executed": False,
        },
        "next_blocker": {
            "id": "BMW-BODY0-bind-frame-composition",
            "required": "compose selected BMW BODY0->outer numeric matrix with this exact outer->VHF matrix and publish SHIFT.BMWBody0BindFrameProof/1",
        },
    }


def analyze_archive(
    semantic_relation: Mapping[str, Any],
    selected_delta: Mapping[str, Any],
    resource_join: Mapping[str, Any],
    primary_vehicle_archive: Path,
) -> dict[str, Any]:
    root_frame = _ROOT_BUILDER.analyze_archive(resource_join, primary_vehicle_archive)
    return build_numeric_relation(semantic_relation, selected_delta, root_frame)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("semantic_relation", type=Path)
    parser.add_argument("selected_delta", type=Path)
    parser.add_argument("resource_join", type=Path)
    parser.add_argument("primary_vehicle_archive", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)
    report = analyze_archive(
        _load_json(args.semantic_relation),
        _load_json(args.selected_delta),
        _load_json(args.resource_join),
        args.primary_vehicle_archive,
    )
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
