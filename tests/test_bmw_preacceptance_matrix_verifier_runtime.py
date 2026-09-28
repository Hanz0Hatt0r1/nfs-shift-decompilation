import hashlib
import json
from pathlib import Path

import bmw_preacceptance_matrix_verifier_runtime as runtime


def _make_expected_matrix() -> list[list[float]]:
    rows = [10] * 10 + [25] * 20 + [10] * 10
    n = 40
    matrix = [[0.0] * n for _ in range(n)]

    # Deterministic helper fixture: create the exact expected row cardinalities
    # without relying on a proprietary matrix payload.
    for row, count in enumerate(rows):
        selected = list(range(count))
        if row >= 10 and row < 30:
            start = max(0, row - 12)
            selected = list(range(start, min(n, start + count)))
        for column in selected:
            matrix[row][column] = 1.0

    # Force symmetry and a complete diagonal while preserving the test's role
    # as an aggregate-metric fixture.
    for row in range(n):
        matrix[row][row] = 1.0
        for column in range(row + 1, n):
            value = 1.0 if (
                matrix[row][column] != 0.0
                or matrix[column][row] != 0.0
            ) else 0.0
            matrix[row][column] = value
            matrix[column][row] = value
    return matrix


def test_generated_metrics_reports_square_support():
    matrix = (
        (1.0, 1.0),
        (1.0, 1.0),
    )

    result = runtime._generated_metrics(matrix)

    assert result["scalar_count"] == 2
    assert result["matrix_nonzero_cells"] == 4
    assert result["matrix_zero_cells"] == 0
    assert result["strict_upper_nonzero_cells"] == 1
    assert result["diagonal_one"] is True
    assert result["symmetric"] is True
    assert result["bit_hash_sha256"] == hashlib.sha256(
        bytes([1, 1, 1, 1])
    ).hexdigest()


def test_compare_generated_to_expected_seed_rejects_wrong_dimension():
    result = runtime.compare_generated_to_expected_seed(
        (
            (1.0, 0.0),
            (0.0, 1.0),
        )
    )

    assert result["ready"] is False
    assert result["mismatch_count"] >= 1
    assert any(
        item["field"] == "matrix_nonzero_cells"
        for item in result["mismatches"]
    )


def test_compare_generated_to_expected_seed_reports_full_observed_metrics():
    # Build a small structural matrix only to validate report shape. It is not
    # expected to match the 40-scalar BMW contract.
    matrix = [
        [1.0, 0.0, 1.0],
        [0.0, 1.0, 0.0],
        [1.0, 0.0, 1.0],
    ]
    result = runtime.compare_generated_to_expected_seed(matrix)

    assert result["observed"]["scalar_count"] == 3
    assert result["observed"]["diagonal_one"] is True
    assert result["mismatch_count"] >= 1


def test_summarize_verification():
    result = runtime.summarize_verification(
        {
            "status": "matched",
            "ready": True,
            "sdf": {"body_count": 11},
            "solver_domain_shape": {
                "actual_constraint_record_count": 28,
                "actual_solver_scalar_count": 40,
            },
            "seed_comparison": {
                "observed": {
                    "matrix_nonzero_cells": 700,
                    "strict_upper_nonzero_cells": 330,
                    "bit_hash_sha256": "6d066aabff0adbdbc5ad303c4d98db381498918023478e913a1883c8c79fc764",
                }
            },
            "acceptance_candidates": {
                "match_count": 0,
            },
            "errors": [],
        }
    )

    assert result["ready"] is True
    assert result["sdf_body_count"] == 11
    assert result["solver_constraint_records"] == 28
    assert result["solver_scalar_count"] == 40
    assert result["matrix_nonzero_cells"] == 700
    assert result["strict_upper_nonzero_cells"] == 330
    assert result["provider_candidate_count"] == 0


def test_extract_target_sdf_requires_exact_entry(tmp_path, monkeypatch):
    class Entry:
        index = 1
        path = runtime.TARGET_SDF
        type = 2
        compressed_size = 10
        uncompressed_size = 20

    class Archive:
        def __init__(self, path):
            self.entries = [Entry()]

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def extract_entry(self, entry, type2="lzx"):
            assert type2 == "lzx"
            return b"sdf"

    source = tmp_path / "BMW_M3_E36.bff"
    source.write_bytes(b"dummy")

    monkeypatch.setattr(runtime, "BFF", Archive)
    result = runtime.extract_target_sdf(source)

    assert result["entry"]["path"] == runtime.TARGET_SDF
    assert result["entry"]["decoded_size"] == 3


def test_expected_constants_are_stable():
    assert runtime.EXPECTED_BMW == {
        "body_count": 11,
        "runtime_constraint_records": 28,
        "solver_scalar_count": 40,
    }
    assert runtime.EXPECTED_SEED["matrix_nonzero_cells"] == 700
    assert runtime.EXPECTED_SEED["strict_upper_nonzero_cells"] == 330
    assert len(runtime.EXPECTED_SEED["row_nonzero_counts"]) == 40
