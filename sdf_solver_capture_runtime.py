"""Capture-schema and cell-level comparison for real SHIFT SDF solver frames."""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.SDFSolverCaptureRuntime/1"


def _to_float_list(values: Sequence[float | int], *, name: str) -> list[float]:
    try:
        out = [float(value) for value in values]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must contain numeric values") from exc
    if any(not math.isfinite(value) for value in out):
        raise ValueError(f"{name} must contain finite values")
    return out


def _matrix(values: Sequence[Sequence[float | int]], *, name: str) -> list[list[float]]:
    out = [_to_float_list(row, name=f"{name}[{index}]") for index, row in enumerate(values)]
    width = len(out)
    if any(len(row) != width for row in out):
        raise ValueError(f"{name} must be square")
    return out


def normalize_solver_capture(capture: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize a captured scalar solver frame."""
    scalar_count = int(capture.get("scalar_count", -1))
    if scalar_count < 0:
        raise ValueError("scalar_count must be non-negative")

    rhs = _to_float_list(capture.get("rhs") or [], name="rhs")
    matrix = _matrix(capture.get("matrix") or [], name="matrix")
    if len(rhs) != scalar_count:
        raise ValueError("rhs length must equal scalar_count")
    if len(matrix) != scalar_count:
        raise ValueError("matrix width must equal scalar_count")

    row_indices = [int(value) for value in capture.get("row_indices", [])]
    if row_indices and len(row_indices) != scalar_count:
        raise ValueError("row_indices length must equal scalar_count")

    return {
        "format": FORMAT,
        "version": 1,
        "status": "normalized",
        "ready": True,
        "scalar_count": scalar_count,
        "rhs": rhs,
        "matrix": matrix,
        "row_indices": row_indices,
        "runtime_identity_nodes": [
            int(value) for value in capture.get("runtime_identity_nodes", [])
        ],
        "frame": capture.get("frame"),
        "source": capture.get("source"),
        "metadata": dict(capture.get("metadata") or {}),
    }


def solver_capture_fingerprint(capture: Mapping[str, Any]) -> dict[str, Any]:
    normalized = normalize_solver_capture(capture)
    payload = {
        "scalar_count": normalized["scalar_count"],
        "row_indices": normalized["row_indices"],
        "rhs": normalized["rhs"],
        "matrix": normalized["matrix"],
        "runtime_identity_nodes": normalized["runtime_identity_nodes"],
    }
    digest = hashlib.sha256(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).hexdigest()
    return {
        "format": "SHIFT.SDFSolverCaptureFingerprint/1",
        "version": 1,
        "ready": True,
        "sha256": digest,
        "scalar_count": normalized["scalar_count"],
        "matrix_nonzero_count": sum(
            1 for row in normalized["matrix"] for value in row if value != 0.0
        ),
        "rhs_nonzero_count": sum(
            1 for value in normalized["rhs"] if value != 0.0
        ),
    }


def compare_solver_vectors(
    expected: Sequence[float | int],
    observed: Sequence[float | int],
    *,
    abs_tol: float = 0.0,
    rel_tol: float = 0.0,
) -> dict[str, Any]:
    exp = _to_float_list(expected, name="expected")
    obs = _to_float_list(observed, name="observed")
    if len(exp) != len(obs):
        raise ValueError("expected and observed vectors must have equal length")
    mismatches: list[dict[str, Any]] = []
    max_abs = 0.0
    max_rel = 0.0
    for index, (a, b) in enumerate(zip(exp, obs)):
        diff = abs(a - b)
        scale = max(abs(a), abs(b))
        rel = diff / scale if scale else 0.0
        max_abs = max(max_abs, diff)
        max_rel = max(max_rel, rel)
        if diff > float(abs_tol) + float(rel_tol) * scale:
            mismatches.append({
                "index": index,
                "expected": a,
                "observed": b,
                "abs_error": diff,
                "rel_error": rel,
            })
    return {
        "format": "SHIFT.SDFSolverVectorComparison/1",
        "version": 1,
        "ready": not mismatches,
        "length": len(exp),
        "mismatch_count": len(mismatches),
        "max_abs_error": max_abs,
        "max_rel_error": max_rel,
        "mismatches": mismatches,
    }


def compare_solver_matrices(
    expected: Sequence[Sequence[float | int]],
    observed: Sequence[Sequence[float | int]],
    *,
    abs_tol: float = 0.0,
    rel_tol: float = 0.0,
    sparse_only: bool = False,
) -> dict[str, Any]:
    exp = _matrix(expected, name="expected")
    obs = _matrix(observed, name="observed")
    if len(exp) != len(obs):
        raise ValueError("expected and observed matrices must have equal size")

    mismatches: list[dict[str, Any]] = []
    max_abs = 0.0
    max_rel = 0.0
    compared_cells = 0
    n = len(exp)
    for row in range(n):
        for column in range(n):
            a = exp[row][column]
            b = obs[row][column]
            if sparse_only and a == 0.0 and b == 0.0:
                continue
            compared_cells += 1
            diff = abs(a - b)
            scale = max(abs(a), abs(b))
            rel = diff / scale if scale else 0.0
            max_abs = max(max_abs, diff)
            max_rel = max(max_rel, rel)
            if diff > float(abs_tol) + float(rel_tol) * scale:
                mismatches.append({
                    "row": row,
                    "column": column,
                    "expected": a,
                    "observed": b,
                    "abs_error": diff,
                    "rel_error": rel,
                })

    return {
        "format": "SHIFT.SDFSolverMatrixComparison/1",
        "version": 1,
        "ready": not mismatches,
        "scalar_count": n,
        "compared_cells": compared_cells,
        "mismatch_count": len(mismatches),
        "max_abs_error": max_abs,
        "max_rel_error": max_rel,
        "mismatches": mismatches,
    }


def compare_retail_storage_layout(
    capture: Mapping[str, Any],
    *,
    matrix_base_address: int = 0,
) -> dict[str, Any]:
    normalized = normalize_solver_capture(capture)
    n = normalized["scalar_count"]
    row_indices = normalized["row_indices"]
    if not row_indices:
        row_indices = [n * row for row in range(n)]
    expected_indices = [n * row for row in range(n)]
    index_mismatches = [
        {"row": row, "expected": expected_indices[row], "observed": row_indices[row]}
        for row in range(n)
        if row_indices[row] != expected_indices[row]
    ]
    return {
        "format": "SHIFT.SDFSolverRetailStorageComparison/1",
        "version": 1,
        "ready": not index_mismatches,
        "scalar_count": n,
        "matrix_bytes": n * n * 8,
        "row_pointer_bytes": n * 4,
        "row_index_mismatch_count": len(index_mismatches),
        "row_index_mismatches": index_mismatches,
        "row_pointers": [
            int(matrix_base_address) + index * 8
            for index in row_indices
        ],
    }


def compare_solver_captures(
    expected: Mapping[str, Any],
    observed: Mapping[str, Any],
    *,
    abs_tol: float = 0.0,
    rel_tol: float = 0.0,
) -> dict[str, Any]:
    exp = normalize_solver_capture(expected)
    obs = normalize_solver_capture(observed)
    if exp["scalar_count"] != obs["scalar_count"]:
        return {
            "format": "SHIFT.SDFSolverCaptureComparison/1",
            "version": 1,
            "ready": False,
            "status": "blocked",
            "errors": [{
                "kind": "scalar-count",
                "expected": exp["scalar_count"],
                "observed": obs["scalar_count"],
            }],
        }

    vector = compare_solver_vectors(
        exp["rhs"], obs["rhs"], abs_tol=abs_tol, rel_tol=rel_tol
    )
    matrix = compare_solver_matrices(
        exp["matrix"], obs["matrix"], abs_tol=abs_tol, rel_tol=rel_tol
    )
    storage = compare_retail_storage_layout(observed)
    fingerprint_expected = solver_capture_fingerprint(exp)
    fingerprint_observed = solver_capture_fingerprint(obs)
    return {
        "format": "SHIFT.SDFSolverCaptureComparison/1",
        "version": 1,
        "status": "matched" if vector["ready"] and matrix["ready"] and storage["ready"] else "diverged",
        "ready": vector["ready"] and matrix["ready"] and storage["ready"],
        "scalar_count": exp["scalar_count"],
        "rhs": vector,
        "matrix": matrix,
        "storage": storage,
        "fingerprints": {
            "expected": fingerprint_expected["sha256"],
            "observed": fingerprint_observed["sha256"],
            "equal": fingerprint_expected["sha256"] == fingerprint_observed["sha256"],
        },
        "errors": [],
    }


def describe_sdf_solver_capture_contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "status": "source-backed-capture-schema",
        "ready": True,
        "required": {
            "scalar_count": "integer",
            "rhs": "scalar_count doubles",
            "matrix": "scalar_count x scalar_count doubles",
        },
        "optional": {
            "row_indices": "scalar_count integer matrix-pool row offsets",
            "runtime_identity_nodes": "scalar indices selected by runtime +0x70 flag",
            "frame": "capture frame/draw identifier",
            "source": "capture provenance",
            "metadata": "caller-defined metadata",
        },
        "retail_storage": {
            "matrix_pool": "scalar_count^2 doubles",
            "row_pointers": "scalar_count 32-bit offsets",
            "row_index_formula": "scalar_count * row",
        },
        "comparison": {
            "vector": "cell-level absolute/relative error",
            "matrix": "cell-level absolute/relative error",
            "storage": "row-index/pointer shape",
            "fingerprint": "SHA-256 of normalized vector/matrix/storage identity data",
        },
        "limitations": [
            "The capture schema does not derive missing runtime values from a trace.",
            "Identity-node selection remains capture-dependent.",
        ],
    }


__all__ = [
    "normalize_solver_capture",
    "solver_capture_fingerprint",
    "compare_solver_vectors",
    "compare_solver_matrices",
    "compare_retail_storage_layout",
    "compare_solver_captures",
    "describe_sdf_solver_capture_contract",
]
