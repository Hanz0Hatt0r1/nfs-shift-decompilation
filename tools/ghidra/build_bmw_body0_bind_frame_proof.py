#!/usr/bin/env python3
"""Compose the selected BMW BODY0 -> VHF-root bind frame from positive proofs.

This is a fail-closed S3 composer.  It does not rediscover BODY0 semantics or the
outer Vehicle/VHF relation.  It consumes the already-positive symbolic
BODY0->outer relation, selected-session numeric BODY0->outer materialization, and
positive numeric outer->VHF relation, then applies the established D3D row-vector
composition order:

    M_BODY0_to_VHF = M_BODY0_to_outer * M_outer_to_VHF

The output is the frozen positive schema consumed by the existing BBFP packet
builder/runtime admission seam.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.BMWBody0BindFrameProof/1"
SYMBOLIC_FORMAT = "SHIFT.BMWBody0VehicleRootBindRelation/1"
SELECTOR_FORMAT = "SHIFT.BMWOffset33bNativeSessionSelection/1"
OUTER_VHF_FORMAT = "SHIFT.BMWOuterVHFNumericRelation/1"

BODY_INDEX = 0
BODY_NAME = "body"
VEHICLE = "BMW_M3_E36"
SESSION = "Silverstone+BMW_M3_E36"
FRAME_RELATION = "BODY0-local-to-VHF-vehicle-root"
ROW_CONVENTION = "row-major D3D row-vector affine"
COMPOSITION = "M_BODY0_to_vhf_root = M_BODY0_to_outer * M_outer_to_vhf_root"
CANONICAL_VHF = "vehicles/bmw_m3_e36/bmw_m3_e36.vhf"
DECODED_VHF_SHA256 = "e08887d17d9e34e703a385260f41017fc19acbebc3405614b375e81766b4bd51"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _load(path: Path, expected: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(value, dict), f"{path}: expected JSON object")
    _require(value.get("format") == expected, f"{path}: expected {expected}")
    return value


def _finite_vector(value: Any, count: int, label: str) -> list[float]:
    _require(
        isinstance(value, Sequence) and not isinstance(value, (str, bytes)) and len(value) == count,
        f"{label} must contain exactly {count} scalars",
    )
    result: list[float] = []
    for item in value:
        _require(not isinstance(item, bool) and isinstance(item, (int, float)), f"{label} contains non-numeric value")
        number = float(item)
        _require(math.isfinite(number), f"{label} contains non-finite value")
        result.append(number)
    return result


def _det3(matrix: Sequence[float]) -> float:
    a, b, c = matrix[0], matrix[1], matrix[2]
    d, e, f = matrix[4], matrix[5], matrix[6]
    g, h, i = matrix[8], matrix[9], matrix[10]
    return a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)


def _row_affine(value: Any, label: str) -> list[float]:
    matrix = _finite_vector(value, 16, label)
    _require(all(abs(matrix[index]) <= 1.0e-9 for index in (3, 7, 11)), f"{label} is not D3D row-vector affine")
    _require(abs(matrix[15] - 1.0) <= 1.0e-9, f"{label} homogeneous component is not one")
    det = _det3(matrix)
    _require(math.isfinite(det) and abs(det) > 1.0e-12, f"{label} linear block is singular")
    return matrix


def _nested_row_matrix(value: Any, label: str) -> list[float]:
    _require(
        isinstance(value, Sequence) and not isinstance(value, (str, bytes)) and len(value) == 4,
        f"{label} must contain four rows",
    )
    flat: list[float] = []
    for index, row in enumerate(value):
        flat.extend(_finite_vector(row, 4, f"{label} row {index}"))
    return _row_affine(flat, label)


def mul4(lhs: Sequence[float], rhs: Sequence[float]) -> list[float]:
    """Multiply two 4x4 row-major matrices without changing vector convention."""
    a = _row_affine(lhs, "left relation matrix")
    b = _row_affine(rhs, "right relation matrix")
    result = [
        sum(a[row * 4 + k] * b[k * 4 + column] for k in range(4))
        for row in range(4)
        for column in range(4)
    ]
    return _row_affine(result, "composed BODY0->VHF matrix")


def _same(lhs: Sequence[float], rhs: Sequence[float], tolerance: float = 1.0e-12) -> bool:
    return len(lhs) == len(rhs) and all(abs(float(a) - float(b)) <= tolerance for a, b in zip(lhs, rhs))


def _validate_symbolic(value: Mapping[str, Any]) -> list[str]:
    _require(value.get("ready") is True and value.get("status") == "symbolic-ready", "symbolic BODY0->outer relation is not ready")
    relation = value.get("symbolic_bind_relation")
    _require(isinstance(relation, Mapping), "symbolic BODY0->outer relation payload missing")
    _require(relation.get("from_frame") == "BODY0-local", "symbolic BODY0 source frame drift")
    _require(relation.get("to_frame") == "outer-Vehicle-root", "symbolic BODY0 target frame drift")
    _require(relation.get("rotation") == "identity", "symbolic BODY0 rotation drift")
    _require(
        relation.get("translation") == [
            "-HDVehicle[0x33b0]",
            "-HDVehicle[0x33b8]",
            "-HDVehicle[0x33c0]",
        ],
        "symbolic BODY0 translation equation drift",
    )
    gates = value.get("gates")
    _require(isinstance(gates, Mapping), "symbolic BODY0 gate table missing")
    _require(gates.get("BODY0_to_outer_vehicle_root_rotation_identity_ready") is True, "BODY0 rotation identity gate not ready")
    _require(gates.get("BODY0_to_outer_vehicle_root_translation_symbolic_ready") is True, "BODY0 translation symbolic gate not ready")
    _require(gates.get("BODY0_to_outer_vehicle_root_symbolic_matrix_ready") is True, "BODY0 symbolic matrix gate not ready")
    scope = value.get("scope")
    _require(isinstance(scope, Mapping), "symbolic BODY0 scope missing")
    _require(scope.get("numeric_offset_assumed") is False, "symbolic proof assumed numeric offset")
    _require(scope.get("identity_translation_assumed") is False, "symbolic proof assumed identity translation")
    _require(scope.get("new_runtime_capture_used") is False, "symbolic proof used runtime capture")
    _require(scope.get("original_game_executed") is False, "symbolic proof executed original game")

    retail = value.get("retail")
    _require(isinstance(retail, Mapping), "symbolic BODY0 retail provenance missing")
    functions = retail.get("functions")
    _require(isinstance(functions, list) and functions, "symbolic BODY0 source function list missing")
    targets: list[str] = []
    for row in functions:
        _require(isinstance(row, Mapping), "symbolic BODY0 source function row invalid")
        name = row.get("name")
        _require(isinstance(name, str) and name.startswith("FUN_"), "symbolic BODY0 source function name invalid")
        targets.append(name)
    return targets


def _validate_selector(value: Mapping[str, Any]) -> tuple[list[float], list[float], list[float]]:
    _require(value.get("ready") is True, "selected BMW native-session relation is not ready")
    _require(value.get("vehicle") == VEHICLE, "selected BMW vehicle drift")
    _require(value.get("session_target") == SESSION, "selected BMW session drift")
    handoff = value.get("handoff")
    _require(isinstance(handoff, Mapping), "selected BMW handoff missing")
    _require(handoff.get("BMW_numeric_offset33b_ready") is True, "selected BMW offset33b gate not ready")
    _require(handoff.get("BODY0_to_outer_vehicle_root_numeric_matrix_ready") is True, "selected BODY0->outer matrix gate not ready")
    _require(handoff.get("BODY0_bind_frame_proof_ready") is False, "selector illegally preclaims final BODY0 bind proof")

    selected = value.get("selected_numeric")
    _require(isinstance(selected, Mapping), "selected BMW numeric payload missing")
    body_to_outer = _nested_row_matrix(selected.get("BODY0_to_outer_vehicle_root_row_vector_matrix"), "selected BODY0->outer matrix")
    translation = _finite_vector(selected.get("BODY0_to_outer_vehicle_root_translation"), 3, "selected BODY0->outer translation")
    offset = _finite_vector(selected.get("offset33b"), 3, "selected offset33b")
    _require(_same(body_to_outer[12:15], translation), "selected BODY0->outer matrix translation disagrees with selected translation")
    _require(_same(translation, [-x for x in offset]), "selected BODY0->outer translation is not exact -offset33b relation")

    scope = value.get("scope")
    _require(isinstance(scope, Mapping), "selected BMW selector scope missing")
    _require(scope.get("BODY0_to_outer_vehicle_rotation_identity_reused_from_upstream_proof") is True, "BODY0 rotation identity provenance missing")
    _require(scope.get("outer_vehicle_to_VHF_identity_assumed") is False, "selector assumes outer/VHF identity")
    _require(scope.get("BODY0_bind_frame_proof_invented") is False, "selector invented BODY0 bind proof")
    _require(scope.get("vehicle_world_transform_claimed") is False, "selector preclaims world transform")
    _require(scope.get("original_game_executed") is False, "selector unexpectedly executed original game")
    _require(scope.get("runtime_capture_required") is False, "selector unexpectedly requires runtime capture")
    return body_to_outer, translation, offset


def _validate_outer_vhf(value: Mapping[str, Any]) -> list[float]:
    _require(value.get("ready") is True, "outer/VHF numeric relation is not ready")
    _require(value.get("status") == "selected-bmw-first-bootstrap-outer-vhf-numeric-relation-proven", "outer/VHF numeric relation status drift")
    _require(value.get("vehicle") == VEHICLE, "outer/VHF vehicle drift")
    _require(value.get("session_target") == SESSION, "outer/VHF session drift")
    subject = value.get("subject")
    _require(isinstance(subject, Mapping), "outer/VHF subject missing")
    _require(str(subject.get("canonical_vhf") or "").replace("\\", "/").lower() == CANONICAL_VHF, "outer/VHF canonical VHF drift")
    _require(subject.get("decoded_sha256") == DECODED_VHF_SHA256, "outer/VHF decoded VHF SHA drift")

    numeric = value.get("numeric")
    _require(isinstance(numeric, Mapping), "outer/VHF numeric payload missing")
    _require(numeric.get("matrix_convention") == ROW_CONVENTION, "outer/VHF matrix convention drift")
    _require(numeric.get("finite") is True and numeric.get("invertible") is True, "outer/VHF matrix is not finite/invertible")
    matrix = _row_affine(numeric.get("M_outer_to_vhf_root"), "outer->VHF matrix")

    handoff = value.get("handoff")
    _require(isinstance(handoff, Mapping), "outer/VHF handoff missing")
    _require(handoff.get("outer_vehicle_root_to_VHF_vehicle_root_ready") is True, "outer/VHF semantic relation gate not ready")
    _require(handoff.get("outer_vehicle_root_to_VHF_fixed_affine_delta_ready") is True, "outer/VHF fixed-affine gate not ready")
    _require(handoff.get("outer_vehicle_root_to_VHF_relation_numeric_matrix_ready") is True, "outer/VHF numeric matrix gate not ready")
    _require(handoff.get("BODY0_bind_frame_proof_ready") is False, "outer/VHF input illegally preclaims BODY0 bind proof")
    limits = value.get("limits")
    _require(isinstance(limits, Mapping), "outer/VHF limits missing")
    _require(limits.get("identity_semantics_inferred_from_numeric_identity") is False, "outer/VHF numeric identity was promoted to semantic identity")
    _require(limits.get("BODY0_bind_frame_claimed") is False, "outer/VHF input claims BODY0 bind frame")
    _require(limits.get("vehicle_world_transform_claimed") is False, "outer/VHF input claims world transform")
    return matrix


def build_proof(symbolic: Mapping[str, Any], selector: Mapping[str, Any], outer_vhf: Mapping[str, Any]) -> dict[str, Any]:
    targets = _validate_symbolic(symbolic)
    body_to_outer, translation, offset = _validate_selector(selector)
    outer_to_vhf = _validate_outer_vhf(outer_vhf)
    body_to_vhf = mul4(body_to_outer, outer_to_vhf)

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "status": "ready",
        "evidence_state": "proven-static",
        "body_index": BODY_INDEX,
        "body_name": BODY_NAME,
        "frame_relation": FRAME_RELATION,
        "matrix_convention": ROW_CONVENTION,
        "body0_local_to_vhf_vehicle_root_row_matrix": body_to_vhf,
        "numeric": {
            "BODY0_to_outer_vehicle_root_row_matrix": body_to_outer,
            "outer_vehicle_root_to_VHF_row_matrix": outer_to_vhf,
            "BODY0_to_VHF_vehicle_root_row_matrix": body_to_vhf,
            "BODY0_to_outer_translation": translation,
            "offset33b": offset,
            "composition_formula": COMPOSITION,
            "composition_order_proven": True,
        },
        "provenance": {
            "source_targets": targets,
            "symbolic_BODY0_outer_contract": SYMBOLIC_FORMAT,
            "selected_BODY0_outer_contract": SELECTOR_FORMAT,
            "outer_VHF_numeric_contract": OUTER_VHF_FORMAT,
            "canonical_vhf": CANONICAL_VHF,
            "decoded_vhf_sha256": DECODED_VHF_SHA256,
            "row_vector_relation_chain": [
                "q_outer = q_BODY0 * M_BODY0_to_outer",
                "q_vhf = q_outer * M_outer_to_vhf_root",
                COMPOSITION,
            ],
            "numeric_equality_to_BODY0_outer_is_consequence_of_independent_outer_VHF_identity_matrix": True,
        },
        "handoff": {
            "BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready": True,
            "BODY0_bind_frame_proof_ready": True,
            "vehicle_world_transform_ready": False,
            "consumer": "SHIFT.NativeBMWBody0BindFrameProofPacket/1 -> S4 persistent fresh BMW world transform",
        },
        "scope": {
            "identity_matrix_assumed": False,
            "outer_VHF_semantic_identity_inferred": False,
            "first_primary_player_bootstrap_relation_scope_preserved": True,
            "selected_native_policy_is_retail_live_session_observation": False,
            "original_game_executed": False,
            "new_runtime_capture_used": False,
            "vehicle_world_transform_claimed": False,
            "retail_scheduler_cadence_claimed": False,
        },
    }


def build_from_paths(symbolic_path: Path, selector_path: Path, outer_vhf_path: Path) -> dict[str, Any]:
    return build_proof(
        _load(symbolic_path, SYMBOLIC_FORMAT),
        _load(selector_path, SELECTOR_FORMAT),
        _load(outer_vhf_path, OUTER_VHF_FORMAT),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("symbolic", type=Path, help=SYMBOLIC_FORMAT)
    parser.add_argument("selector", type=Path, help=SELECTOR_FORMAT)
    parser.add_argument("outer_vhf", type=Path, help=OUTER_VHF_FORMAT)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    report = build_from_paths(args.symbolic, args.selector, args.outer_vhf)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
