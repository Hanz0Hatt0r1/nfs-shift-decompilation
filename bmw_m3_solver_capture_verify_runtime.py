"""BMW M3 specific structural verification for captured SDF solver frames."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from sdf_solver_capture_runtime import (
    compare_retail_storage_layout,
    normalize_solver_capture,
)
from pathlib import Path

from rigid_body_sdf_runtime import parse_sdf
from bmw_m3_e36_solver_domain_runtime import build_solver_domain
from shift_importer_v3_reference import BFF

TARGET_ARCHIVE_SHA256 = "c31d34a0a7cab04bcff693fa0cbda3400f50d690a9c8bb2521b2882fc2a68d70"
TARGET_RESOURCE = "vehicles/physics/suspension/aarm_multilink.sdf"
TARGET_RESOURCE_SHA256 = "fe0b18e95e81f87d67076b70890965a0a1384a925bfd836aaf5aa705fc4781ed"


FORMAT = "SHIFT.BMWM3SolverCaptureVerify/1"

EXPECTED = {
    "body_count": 11,
    "source_constraint_records": 24,
    "runtime_constraint_records": 28,
    "solver_scalar_count": 40,
    "matrix_cells": 1600,
    "matrix_bytes": 12800,
    "row_pointer_count": 40,
    "row_pointer_bytes": 160,
    "seed_nonzero_cells": 700,
}


def verify_bmw_m3_capture_structure(
    capture: Mapping[str, Any],
    *,
    runtime_identity_nodes: Sequence[int] | None = None,
) -> dict[str, Any]:
    """Verify a normalized capture against the real BMW M3 SDF solver shape."""
    normalized = normalize_solver_capture(capture)
    n = normalized["scalar_count"]
    errors: list[str] = []
    warnings: list[str] = []

    if n != EXPECTED["solver_scalar_count"]:
        errors.append(
            f"solver-scalar-count:{n}!={EXPECTED['solver_scalar_count']}"
        )

    storage = compare_retail_storage_layout(normalized)
    if not storage["ready"]:
        errors.append("retail-row-index-layout")

    matrix_nonzero = sum(
        1
        for row in normalized["matrix"]
        for value in row
        if value != 0.0
    )
    if matrix_nonzero < EXPECTED["seed_nonzero_cells"]:
        warnings.append(
            f"matrix-nonzero-below-seed-support:{matrix_nonzero}<"
            f"{EXPECTED['seed_nonzero_cells']}"
        )

    captured_identity = normalized["runtime_identity_nodes"]
    if runtime_identity_nodes is not None:
        expected_identity = [int(value) for value in runtime_identity_nodes]
        if captured_identity and captured_identity != expected_identity:
            errors.append("runtime-identity-node-mismatch")
        elif not captured_identity:
            warnings.append("runtime-identity-nodes-not-present-in-capture")

    return {
        "format": FORMAT,
        "version": 1,
        "status": "verified" if not errors else "blocked",
        "ready": not errors,
        "scope": "BMW M3 E36 aarm_multilink.sdf",
        "expected": dict(EXPECTED),
        "observed": {
            "solver_scalar_count": n,
            "matrix_cells": n * n,
            "matrix_bytes": n * n * 8,
            "row_pointer_count": n,
            "row_pointer_bytes": n * 4,
            "matrix_nonzero_cells": matrix_nonzero,
            "runtime_identity_nodes": captured_identity,
        },
        "storage": storage,
        "errors": errors,
        "warnings": warnings,
        "evidence": {
            "physics_resource": "vehicles/physics/suspension/aarm_multilink.sdf",
            "source_domain": "Phase 405",
            "seed_support": "Phase 406",
            "capture_schema": "Phase 411",
            "binary_ingestion": "Phase 412",
        },
        "limitations": [
            "The verifier checks BMW M3 topology/storage shape; it does not claim numeric equivalence without a captured expected matrix/vector.",
            "Matrix non-zero support is reported diagnostically because later coefficient arithmetic or identity resets can change individual values.",
        ],
    }


def verify_bff_domain(bff_path: str | Path) -> dict[str, Any]:
    import hashlib

    source = Path(bff_path)
    archive_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    errors: list[str] = []
    if archive_sha != TARGET_ARCHIVE_SHA256:
        errors.append(f"unexpected-archive-sha256:{archive_sha}")

    if errors:
        return {
            "ready": False,
            "status": "blocked",
            "errors": errors,
        }

    try:
        with BFF(source) as archive:
            target = TARGET_RESOURCE.strip("/").lower()
            matches = [
                entry
                for entry in archive.entries
                if entry.path.replace("\\", "/").strip("/").lower() == target
            ]
            if len(matches) != 1:
                return {
                    "ready": False,
                    "status": "blocked",
                    "errors": [f"target-entry-count:{len(matches)}"],
                }
            entry = matches[0]
            data = archive.extract_entry(entry, type2="lzx")
    except Exception as exc:
        return {
            "ready": False,
            "status": "blocked",
            "errors": [f"bff-extract:{exc}"],
        }

    digest = hashlib.sha256(data).hexdigest()
    if digest != TARGET_RESOURCE_SHA256:
        return {
            "ready": False,
            "status": "blocked",
            "errors": [f"unexpected-sdf-sha256:{digest}"],
        }

    sdf = parse_sdf(data, strict=True)
    solver = build_solver_domain(sdf)
    ready = (
        solver.get("ready") is True
        and int(solver.get("solver_scalar_count", 0)) == EXPECTED["solver_scalar_count"]
    )
    return {
        "ready": ready,
        "status": "verified" if ready else "blocked",
        "errors": [] if ready else ["solver-domain-not-ready"],
        "source": {
            "archive_sha256": archive_sha,
            "resource": TARGET_RESOURCE,
            "resource_sha256": digest,
            "entry_index": entry.index,
            "compression_type": entry.type,
            "compressed_size": entry.compressed_size,
            "uncompressed_size": entry.uncompressed_size,
        },
        "sdf": {
            "record_count": sdf.get("record_count"),
            "topology": sdf.get("topology", {}),
        },
        "solver_domain": solver,
    }


def verify_bmw_m3_capture_pair(
    capture: Mapping[str, Any],
    expected: Mapping[str, Any],
    *,
    abs_tol: float = 0.0,
    rel_tol: float = 0.0,
) -> dict[str, Any]:
    """Combine BMW-specific structural checks with Phase 411 cell-level comparison."""
    from sdf_solver_capture_runtime import compare_solver_captures

    structure = verify_bmw_m3_capture_structure(capture)
    if not structure["ready"]:
        return {
            "format": "SHIFT.BMWM3SolverCapturePairVerification/1",
            "version": 1,
            "status": "blocked",
            "ready": False,
            "structure": structure,
            "comparison": None,
        }

    comparison = compare_solver_captures(
        expected,
        capture,
        abs_tol=abs_tol,
        rel_tol=rel_tol,
    )
    return {
        "format": "SHIFT.BMWM3SolverCapturePairVerification/1",
        "version": 1,
        "status": "matched" if comparison["ready"] else "diverged",
        "ready": comparison["ready"],
        "structure": structure,
        "comparison": comparison,
    }


def describe_bmw_m3_solver_capture_verifier() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "status": "source-backed-structural-verifier",
        "ready": True,
        "expected_shape": dict(EXPECTED),
        "real_resource": "aarm_multilink.sdf",
        "comparison_path": {
            "structure": "BMW M3 40-scalar / 40x40 / 160-byte row-pointer domain",
            "values": "Phase 411 exact cell-level comparison",
            "ingestion": "Phase 412 explicit-offset binary reader",
        },
        "limitations": [
            "No captured solver state is assumed or synthesized.",
            "Numeric matrix equality remains unavailable until a real runtime capture is supplied.",
        ],
    }


__all__ = [
    "EXPECTED",
    "verify_bmw_m3_capture_structure",
    "verify_bmw_m3_capture_pair",
    "verify_bff_domain",
    "describe_bmw_m3_solver_capture_verifier",
]
