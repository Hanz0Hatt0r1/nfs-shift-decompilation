"""End-to-end verification of the BMW pre-acceptance structural matrix.

Phase 487 drives the existing BFF/SDF/solver-domain pipeline and compares the
generated FUN_007ba2b0 0/1 seed against the Phase 406 BMW evidence. The check
includes the complete matrix bit hash, not only aggregate non-zero counts.

It intentionally keeps provider acceptance results as a separate diagnostic:
BMW/provider identity remains capture-gated.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from shift_importer import BFF
from rigid_body_sdf_runtime import parse_sdf
from bmw_m3_e36_solver_domain_runtime import (
    build_solver_domain,
    validate_expected_bmw_shape,
)
from body_solver_domain_matrix_builder_runtime import (
    build_bmw_matrix_structure,
    evaluate_generated_acceptance,
)

FORMAT = "SHIFT.BMWPreAcceptanceMatrixVerifierRuntime/1"

TARGET_SDF = "vehicles/physics/suspension/aarm_multilink.sdf"
EXPECTED_ARCHIVE_SHA256 = (
    "c31d34a0a7cab04bcff693fa0cbda3400f50d690a9c8bb2521b2882fc2a68d70"
)
EXPECTED_SDF_SHA256 = (
    "fe0b18e95e81f87d67076b70890965a0a1384a925bfd836aaf5aa705fc4781ed"
)
EXPECTED_BMW = {
    "body_count": 11,
    "runtime_constraint_records": 28,
    "solver_scalar_count": 40,
}
EXPECTED_SEED = {
    "matrix_nonzero_cells": 700,
    "matrix_zero_cells": 900,
    "strict_upper_nonzero_cells": 330,
    "row_nonzero_counts": (
        [10] * 10
        + [25] * 20
        + [10] * 10
    ),
    "bit_hash_sha256": (
        "6d066aabff0adbdbc5ad303c4d98db381498918023478e913a1883c8c79fc764"
    ),
    "diagonal_one": True,
    "symmetric": True,
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _find_unique_entry(archive: BFF, logical_path: str):
    wanted = logical_path.replace("\\", "/").lower()
    matches = [
        entry
        for entry in archive.entries
        if entry.path.replace("\\", "/").lower() == wanted
    ]
    if len(matches) != 1:
        raise ValueError(
            f"expected exactly one BFF entry for {logical_path!r}, found {len(matches)}"
        )
    return matches[0]


def extract_target_sdf(
    bff_path: str | Path,
) -> dict[str, Any]:
    source = Path(bff_path)
    archive_sha = _sha256(source.read_bytes())

    with BFF(source) as archive:
        entry = _find_unique_entry(archive, TARGET_SDF)
        payload = archive.extract_entry(entry, type2="lzx")

    return {
        "archive": {
            "path": str(source),
            "size_bytes": source.stat().st_size,
            "sha256": archive_sha,
            "sha256_matches": archive_sha == EXPECTED_ARCHIVE_SHA256,
        },
        "entry": {
            "index": int(entry.index),
            "path": entry.path,
            "type": int(entry.type),
            "compressed_size": int(entry.compressed_size),
            "uncompressed_size": int(entry.uncompressed_size),
            "decoded_size": len(payload),
            "decoded_sha256": _sha256(payload),
            "decoded_sha256_matches": (
                _sha256(payload) == EXPECTED_SDF_SHA256
            ),
        },
        "payload": payload,
    }


def _generated_metrics(matrix: Sequence[Sequence[float]]) -> dict[str, Any]:
    n = len(matrix)
    row_counts = [
        sum(
            1
            for value in row
            if float(value) != 0.0
        )
        for row in matrix
    ]
    flat = bytes(
        1 if float(value) != 0.0 else 0
        for row in matrix
        for value in row
    )
    nonzero = sum(row_counts)
    strict_upper = sum(
        1
        for row in range(n)
        for column in range(row + 1, n)
        if float(matrix[row][column]) != 0.0
    )
    return {
        "scalar_count": n,
        "matrix_nonzero_cells": nonzero,
        "matrix_zero_cells": n * n - nonzero,
        "strict_upper_nonzero_cells": strict_upper,
        "row_nonzero_counts": row_counts,
        "bit_hash_sha256": hashlib.sha256(flat).hexdigest(),
        "diagonal_one": all(
            float(matrix[index][index]) == 1.0
            for index in range(n)
        ),
        "symmetric": all(
            float(matrix[row][column])
            == float(matrix[column][row])
            for row in range(n)
            for column in range(n)
        ),
    }


def compare_generated_to_expected_seed(
    matrix: Sequence[Sequence[float]],
) -> dict[str, Any]:
    actual = _generated_metrics(matrix)
    mismatches: list[dict[str, Any]] = []

    for field in (
        "matrix_nonzero_cells",
        "matrix_zero_cells",
        "strict_upper_nonzero_cells",
        "bit_hash_sha256",
        "diagonal_one",
        "symmetric",
    ):
        if actual[field] != EXPECTED_SEED[field]:
            mismatches.append(
                {
                    "field": field,
                    "expected": EXPECTED_SEED[field],
                    "observed": actual[field],
                }
            )

    expected_rows = EXPECTED_SEED["row_nonzero_counts"]
    if actual["row_nonzero_counts"] != expected_rows:
        differing_rows = [
            index
            for index, (expected, observed) in enumerate(
                zip(expected_rows, actual["row_nonzero_counts"])
            )
            if expected != observed
        ]
        mismatches.append(
            {
                "field": "row_nonzero_counts",
                "expected": expected_rows,
                "observed": actual["row_nonzero_counts"],
                "differing_rows": differing_rows,
            }
        )

    return {
        "format": "SHIFT.BMWPreAcceptanceMatrixSeedComparison/1",
        "version": 1,
        "status": "matched" if not mismatches else "structural-divergence",
        "ready": not mismatches,
        "expected": dict(EXPECTED_SEED),
        "observed": actual,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
    }


def verify_bmw_preacceptance_matrix(
    bff_path: str | Path,
    *,
    strict_sdf: bool = False,
) -> dict[str, Any]:
    extracted = extract_target_sdf(bff_path)
    payload = extracted.pop("payload")

    sdf_report = parse_sdf(
        payload,
        strict=strict_sdf,
    )
    solver_domain = build_solver_domain(sdf_report)
    shape = validate_expected_bmw_shape(
        solver_domain,
        body_count=EXPECTED_BMW["body_count"],
        joint_hinge_count=4,
        bar_count=20,
    )

    generated = None
    seed_compare = None
    acceptance = None
    errors: list[str] = []

    if shape.get("ready") is not True:
        errors.extend(shape.get("errors") or [])
    if solver_domain.get("ready") is not True:
        errors.extend(solver_domain.get("unresolved") or [])
        errors.extend(solver_domain.get("errors") or [])

    if not errors:
        generated = build_bmw_matrix_structure(solver_domain)
        errors.extend(generated.get("errors") or [])

        if generated.get("ready") is True:
            seed_compare = compare_generated_to_expected_seed(
                generated["matrix"]
            )
            acceptance = evaluate_generated_acceptance(generated)
            if seed_compare.get("ready") is not True:
                errors.append("bmw-seed-structural-divergence")

    ready = (
        extracted["archive"]["sha256_matches"]
        and extracted["entry"]["decoded_sha256_matches"]
        and shape.get("ready") is True
        and solver_domain.get("ready") is True
        and generated is not None
        and generated.get("ready") is True
        and seed_compare is not None
        and seed_compare.get("ready") is True
        and not errors
    )

    return {
        "format": FORMAT,
        "version": 1,
        "status": "matched" if ready else "blocked-or-diverged",
        "ready": ready,
        "source": {
            "archive_sha256_expected": EXPECTED_ARCHIVE_SHA256,
            "sdf_sha256_expected": EXPECTED_SDF_SHA256,
            "target_sdf": TARGET_SDF,
        },
        "extraction": {
            "archive": extracted["archive"],
            "entry": extracted["entry"],
        },
        "sdf": {
            "ready": sdf_report.get("ready") is True,
            "status": sdf_report.get("status"),
            "body_count": sdf_report.get("topology", {}).get("body_count"),
            "joint_hinge_count": sdf_report.get(
                "topology", {}
            ).get("joint_hinge_count"),
            "bar_count": sdf_report.get(
                "topology", {}
            ).get("bar_count"),
        },
        "solver_domain_shape": shape,
        "solver_domain": solver_domain,
        "generated_matrix": generated,
        "seed_comparison": seed_compare,
        "acceptance_candidates": acceptance,
        "errors": list(dict.fromkeys(errors)),
        "interpretation": {
            "structural_match": (
                "full matrix 0/1 support matches the Phase 406 seed hash and row counts"
            ),
            "provider_identity": (
                "not inferred; acceptance candidates are diagnostic only"
            ),
        },
    }


def summarize_verification(
    report: Mapping[str, Any],
) -> dict[str, Any]:
    seed = report.get("seed_comparison") or {}
    observed = seed.get("observed") or {}
    acceptance = report.get("acceptance_candidates") or {}

    return {
        "status": report.get("status"),
        "ready": bool(report.get("ready")),
        "sdf_body_count": (
            report.get("sdf") or {}
        ).get("body_count"),
        "solver_constraint_records": (
            report.get("solver_domain_shape") or {}
        ).get("actual_constraint_record_count"),
        "solver_scalar_count": (
            report.get("solver_domain_shape") or {}
        ).get("actual_solver_scalar_count"),
        "matrix_nonzero_cells": observed.get(
            "matrix_nonzero_cells"
        ),
        "strict_upper_nonzero_cells": observed.get(
            "strict_upper_nonzero_cells"
        ),
        "bit_hash_sha256": observed.get(
            "bit_hash_sha256"
        ),
        "provider_candidate_count": acceptance.get(
            "match_count",
        ),
        "errors": list(report.get("errors") or []),
    }


__all__ = [
    "FORMAT",
    "TARGET_SDF",
    "EXPECTED_ARCHIVE_SHA256",
    "EXPECTED_SDF_SHA256",
    "EXPECTED_BMW",
    "EXPECTED_SEED",
    "extract_target_sdf",
    "compare_generated_to_expected_seed",
    "verify_bmw_preacceptance_matrix",
    "summarize_verification",
]
