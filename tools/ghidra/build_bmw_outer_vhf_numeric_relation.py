#!/usr/bin/env python3
"""Compose the exact selected BMW outer-Vehicle -> VHF-root numeric relation.

This tool is intentionally fail-closed. It consumes the already-positive semantic
relation and first-bootstrap delta, but it requires the *materialized retail*
SHIFT.BMWVHFHierarchyRootFrame/1 instance carrying the canonical Root
world_matrix_row_vector. MatrixNumber 0 is never treated as identity by itself.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.BMWOuterVHFNumericRelation/1"
RELATION_FORMAT = "SHIFT.OuterVehicleBMWVHFRootRelation/1"
DELTA_FORMAT = "SHIFT.BMWPrimaryPlayerFirstBootstrapRenderRootDelta/1"
ROOT_FORMAT = "SHIFT.BMWVHFHierarchyRootFrame/1"
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


def _load(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    return _mapping(value, str(path))


def _vector(value: Any, n: int, label: str) -> list[float]:
    _require(isinstance(value, Sequence) and not isinstance(value, (str, bytes)), f"{label} must be a sequence")
    _require(len(value) == n, f"{label} must contain {n} scalars")
    out: list[float] = []
    for item in value:
        _require(not isinstance(item, bool) and isinstance(item, (int, float)), f"{label} contains non-numeric scalar")
        number = float(item)
        _require(math.isfinite(number), f"{label} contains non-finite scalar")
        out.append(number)
    return out


def _matrix16(value: Any, label: str) -> list[float]:
    out = _vector(value, 16, label)
    _require(all(abs(out[i]) <= 1e-9 for i in (3, 7, 11)), f"{label} is not row-vector affine")
    _require(abs(out[15] - 1.0) <= 1e-9, f"{label} homogeneous component drift")
    return out


def _mul(a: Sequence[float], b: Sequence[float]) -> list[float]:
    return [sum(float(a[r * 4 + k]) * float(b[k * 4 + c]) for k in range(4)) for r in range(4) for c in range(4)]


def _translation(delta: Sequence[float]) -> list[float]:
    x, y, z = _vector(delta, 3, "delta_local")
    return [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        x, y, z, 1.0,
    ]


def _invert4(m: Sequence[float]) -> list[float]:
    matrix = _matrix16(m, "matrix to invert")
    rows = [[matrix[r * 4 + c] for c in range(4)] + [1.0 if r == c else 0.0 for c in range(4)] for r in range(4)]
    for col in range(4):
        pivot = max(range(col, 4), key=lambda r: abs(rows[r][col]))
        _require(abs(rows[pivot][col]) > 1e-12, "relation matrix is singular")
        rows[col], rows[pivot] = rows[pivot], rows[col]
        scale = rows[col][col]
        rows[col] = [v / scale for v in rows[col]]
        for r in range(4):
            if r == col:
                continue
            factor = rows[r][col]
            rows[r] = [x - factor * y for x, y in zip(rows[r], rows[col])]
    result = [rows[r][4 + c] for r in range(4) for c in range(4)]
    return _matrix16(result, "inverse relation matrix")


def _validate_relation(value: Mapping[str, Any]) -> Mapping[str, Any]:
    _require(value.get("format") == RELATION_FORMAT and value.get("ready") is True, "outer/VHF semantic relation not positive")
    subject = _mapping(value.get("subject"), "relation subject")
    _require(subject.get("vehicle") == "BMW_M3_E36", "relation vehicle drift")
    _require(str(subject.get("canonical_vhf") or "").replace("\\", "/").lower() == CANONICAL_VHF, "relation canonical VHF drift")
    _require(str(subject.get("decoded_sha256") or "").lower() == DECODED_SHA256, "relation decoded VHF SHA drift")
    _require(subject.get("root_node_path") == ROOT_PATH, "relation root path drift")
    relation = _mapping(value.get("relation"), "relation payload")
    _require(relation.get("kind") == "fixed_affine", "relation kind drift")
    _require(relation.get("matrix_convention") == ROW_CONVENTION, "relation matrix convention drift")
    _require(relation.get("outer_to_vhf_root_formula") == "inverse(M_vhf_root_to_model * T(delta_local))", "relation formula drift")
    _require(relation.get("relation_matrix_numeric_ready") is False, "upstream relation unexpectedly preclaims numeric matrix")
    handoff = _mapping(value.get("handoff"), "relation handoff")
    _require(handoff.get("outer_vehicle_root_to_VHF_vehicle_root_ready") is True, "outer/VHF semantic relation gate not ready")
    _require(handoff.get("outer_vehicle_root_to_VHF_fixed_affine_delta_ready") is True, "fixed-affine gate not ready")
    return relation


def _validate_delta(value: Mapping[str, Any]) -> list[float]:
    _require(value.get("format") == DELTA_FORMAT and value.get("ready") is True, "first-bootstrap BMW delta not positive")
    _require(value.get("session_target") == "Silverstone+BMW_M3_E36", "delta session target drift")
    policy = _mapping(value.get("native_bootstrap_policy"), "delta native policy")
    _require(policy.get("first_vehicle_bootstrap") is True and policy.get("physics_participant_spawn_config_plus_0x10") == 0, "delta bootstrap policy drift")
    selected = _mapping(value.get("selected_numeric"), "delta selected_numeric")
    _require(selected.get("scope") == "first explicit native primary-player vehicle bootstrap before any origin-update path", "delta scope drift")
    delta = _vector(selected.get("delta_local"), 3, "selected BMW delta_local")
    _require(delta == [0.0, 0.0, 0.0], "canonical first-bootstrap BMW delta drift")
    handoff = _mapping(value.get("handoff"), "delta handoff")
    _require(handoff.get("BMW_primary_player_first_bootstrap_render_root_delta_numeric_ready") is True, "delta numeric gate not ready")
    _require(handoff.get("outer_vehicle_root_to_VHF_relation_numeric_matrix_ready") is False, "delta stage preclaims numeric relation")
    return delta


def _validate_root(value: Mapping[str, Any]) -> tuple[list[float], str, list[str]]:
    _require(value.get("format") == ROOT_FORMAT and value.get("ready") is True, "BMW VHF root frame not positive")
    source = _mapping(value.get("source"), "BMW VHF root source")
    _require(str(source.get("resolved_path") or "").replace("\\", "/").strip("/").lower() == CANONICAL_VHF, "BMW VHF root source path drift")
    _require(str(source.get("decoded_sha256") or "").lower() == DECODED_SHA256, "BMW VHF root decoded SHA drift")
    frame = _mapping(value.get("vehicle_root_frame"), "BMW VHF vehicle_root_frame")
    _require(frame.get("node_type") == "HIERARCHY" and frame.get("node_name") == "Root", "BMW VHF root node drift")
    _require(frame.get("node_path") == ROOT_PATH, "BMW VHF root node path drift")
    matrix_number = str(frame.get("matrix_number") or "")
    _require(bool(matrix_number), "BMW VHF root MatrixNumber missing")
    chain_raw = frame.get("matrix_parent_chain_ids")
    _require(isinstance(chain_raw, list) and bool(chain_raw), "BMW VHF root parent chain missing")
    chain = [str(v) for v in chain_raw]
    _require(chain[-1] == matrix_number, "BMW VHF root parent chain terminal mismatch")
    provenance = _mapping(value.get("provenance"), "BMW VHF root provenance")
    _require(provenance.get("exact_root_affine_matrix_ready") is True, "BMW VHF exact root matrix gate not ready")
    matrix = _matrix16(frame.get("world_matrix_row_vector"), "BMW VHF root world_matrix_row_vector")
    return matrix, matrix_number, chain


def build_numeric_relation(relation: Mapping[str, Any], delta: Mapping[str, Any], root: Mapping[str, Any]) -> dict[str, Any]:
    _validate_relation(relation)
    delta_xyz = _validate_delta(delta)
    root_to_model, matrix_number, chain = _validate_root(root)
    root_to_outer = _mul(root_to_model, _translation(delta_xyz))
    outer_to_root = _invert4(root_to_outer)
    identity_numeric = all(abs(v - (1.0 if i in (0, 5, 10, 15) else 0.0)) <= 1e-9 for i, v in enumerate(outer_to_root))
    return {
        "format": FORMAT,
        "version": 1,
        "status": "bmw-outer-vhf-numeric-relation-proven",
        "ready": True,
        "semantic_authority": "single process",
        "session_target": "Silverstone+BMW_M3_E36",
        "inputs": {
            "semantic_relation": RELATION_FORMAT,
            "first_bootstrap_delta": DELTA_FORMAT,
            "vhf_root_frame": ROOT_FORMAT,
        },
        "subject": {
            "vehicle": "BMW_M3_E36",
            "canonical_vhf": CANONICAL_VHF,
            "decoded_sha256": DECODED_SHA256,
            "root_node_path": ROOT_PATH,
            "matrix_number": matrix_number,
            "matrix_parent_chain_ids": chain,
        },
        "numeric_relation": {
            "matrix_convention": ROW_CONVENTION,
            "delta_local": delta_xyz,
            "M_vhf_root_to_model": root_to_model,
            "M_vhf_root_to_outer": root_to_outer,
            "M_outer_to_vhf_root": outer_to_root,
            "numeric_matrix_is_identity": identity_numeric,
            "identity_semantics_proven": False,
        },
        "handoff": {
            "outer_vehicle_root_to_VHF_vehicle_root_ready": True,
            "outer_vehicle_root_to_VHF_fixed_affine_delta_ready": True,
            "outer_vehicle_root_to_VHF_relation_numeric_matrix_ready": True,
            "BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
            "consumer": "S3 exact BMW BODY0->outer * outer->VHF composition",
        },
        "limits": {
            "matrix_number_zero_used_as_identity_proof": False,
            "numeric_identity_promoted_to_semantic_identity": False,
            "root_matrix_invented": False,
            "runtime_capture_used": False,
            "original_game_executed": False,
        },
        "NEXT_STEP": "compose selected-session BODY0->outer numeric matrix with M_outer_to_vhf_root and publish SHIFT.BMWBody0BindFrameProof/1",
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("semantic_relation", type=Path)
    ap.add_argument("first_bootstrap_delta", type=Path)
    ap.add_argument("vhf_root_frame", type=Path)
    ap.add_argument("--json-out", type=Path)
    ns = ap.parse_args()
    report = build_numeric_relation(_load(ns.semantic_relation), _load(ns.first_bootstrap_delta), _load(ns.vhf_root_frame))
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if ns.json_out:
        ns.json_out.parent.mkdir(parents=True, exist_ok=True)
        ns.json_out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
