import pytest

import bmw_m3_solver_capture_verify_runtime as runtime


def _capture40():
    n = 40
    return {
        "scalar_count": n,
        "rhs": [float(index) for index in range(n)],
        "matrix": [
            [1.0 if row == column else 0.0 for column in range(n)]
            for row in range(n)
        ],
        "row_indices": [n * row for row in range(n)],
        "runtime_identity_nodes": [3, 9],
    }


def test_bmw_m3_structure_accepts_40_scalar_retail_shape():
    result = runtime.verify_bmw_m3_capture_structure(_capture40())
    assert result["ready"] is True
    assert result["observed"]["solver_scalar_count"] == 40
    assert result["observed"]["matrix_cells"] == 1600
    assert result["observed"]["matrix_bytes"] == 12800
    assert result["observed"]["row_pointer_bytes"] == 160


def test_bmw_m3_structure_blocks_wrong_scalar_count():
    capture = _capture40()
    capture["scalar_count"] = 39
    capture["rhs"] = capture["rhs"][:39]
    capture["matrix"] = [row[:39] for row in capture["matrix"][:39]]
    capture["row_indices"] = [39 * row for row in range(39)]
    result = runtime.verify_bmw_m3_capture_structure(capture)
    assert result["ready"] is False
    assert any(error.startswith("solver-scalar-count:") for error in result["errors"])


def test_bmw_m3_structure_blocks_bad_row_index_shape():
    capture = _capture40()
    capture["row_indices"][7] = 999
    result = runtime.verify_bmw_m3_capture_structure(capture)
    assert result["ready"] is False
    assert "retail-row-index-layout" in result["errors"]


def test_bmw_m3_structure_reports_seed_support_as_warning_only():
    capture = _capture40()
    capture["matrix"] = [
        [0.0 for _ in range(40)]
        for _ in range(40)
    ]
    result = runtime.verify_bmw_m3_capture_structure(capture)
    assert result["ready"] is True
    assert any(
        warning.startswith("matrix-nonzero-below-seed-support:")
        for warning in result["warnings"]
    )


def test_bmw_m3_structure_can_check_capture_identity_nodes():
    result = runtime.verify_bmw_m3_capture_structure(
        _capture40(),
        runtime_identity_nodes=[3, 9],
    )
    assert result["ready"] is True
    assert result["observed"]["runtime_identity_nodes"] == [3, 9]
    assert any(
        warning.startswith("matrix-nonzero-below-seed-support:")
        for warning in result["warnings"]
    )


def test_bmw_m3_structure_reports_missing_identity_nodes_without_blocking():
    capture = _capture40()
    capture["runtime_identity_nodes"] = []
    result = runtime.verify_bmw_m3_capture_structure(
        capture,
        runtime_identity_nodes=[3, 9],
    )
    assert result["ready"] is True
    assert "runtime-identity-nodes-not-present-in-capture" in result["warnings"]


def test_bmw_m3_pair_verification_uses_exact_cell_comparison():
    expected = _capture40()
    observed = _capture40()
    observed["rhs"][12] = 12.5
    result = runtime.verify_bmw_m3_capture_pair(
        observed,
        expected,
        abs_tol=0.0,
        rel_tol=0.0,
    )
    assert result["ready"] is False
    assert result["comparison"]["rhs"]["mismatch_count"] == 1
    assert result["comparison"]["rhs"]["mismatches"][0]["index"] == 12


def test_bmw_m3_verifier_contract_is_capture_dependent():
    result = runtime.describe_bmw_m3_solver_capture_verifier()
    assert result["ready"] is True
    assert result["expected_shape"]["solver_scalar_count"] == 40
    assert result["expected_shape"]["matrix_cells"] == 1600
    assert "No captured solver state is assumed or synthesized." in result["limitations"]
