import pytest

import sdf_solver_capture_runtime as runtime


def _capture():
    return {
        "scalar_count": 3,
        "rhs": [1.0, 2.0, 0.0],
        "matrix": [
            [1.0, 2.0, 0.0],
            [2.0, 3.0, 4.0],
            [0.0, 4.0, 5.0],
        ],
        "row_indices": [0, 3, 6],
        "runtime_identity_nodes": [2],
        "frame": 17,
        "metadata": {"source": "unit"},
    }


def test_normalize_solver_capture_preserves_40_scalar_shape_contract():
    capture = _capture()
    result = runtime.normalize_solver_capture(capture)
    assert result["ready"] is True
    assert result["scalar_count"] == 3
    assert result["rhs"] == [1.0, 2.0, 0.0]
    assert result["row_indices"] == [0, 3, 6]
    assert result["runtime_identity_nodes"] == [2]
    assert result["frame"] == 17


def test_normalize_solver_capture_rejects_bad_rhs_length():
    capture = _capture()
    capture["rhs"] = [1.0]
    with pytest.raises(ValueError, match="rhs length"):
        runtime.normalize_solver_capture(capture)


def test_solver_capture_fingerprint_is_stable():
    capture = _capture()
    first = runtime.solver_capture_fingerprint(capture)
    second = runtime.solver_capture_fingerprint(capture)
    assert first["sha256"] == second["sha256"]
    assert first["matrix_nonzero_count"] == 7
    assert first["rhs_nonzero_count"] == 2


def test_compare_solver_vectors_reports_exact_cell_errors():
    result = runtime.compare_solver_vectors(
        [1.0, 2.0, 3.0],
        [1.0, 2.01, 3.0],
        abs_tol=0.0,
        rel_tol=0.0,
    )
    assert result["ready"] is False
    assert result["mismatch_count"] == 1
    assert result["mismatches"][0]["index"] == 1
    assert result["mismatches"][0]["abs_error"] == pytest.approx(0.01)


def test_compare_solver_matrices_can_restrict_to_nonzero_support():
    result = runtime.compare_solver_matrices(
        [[1,0],[0,0]],
        [[1.1,0],[0,0]],
        sparse_only=True,
    )
    assert result["ready"] is False
    assert result["compared_cells"] == 1
    assert result["mismatch_count"] == 1
    assert result["mismatches"][0]["row"] == 0
    assert result["mismatches"][0]["column"] == 0


def test_compare_retail_storage_layout_validates_row_indices():
    result = runtime.compare_retail_storage_layout(_capture())
    assert result["ready"] is True
    assert result["matrix_bytes"] == 72
    assert result["row_pointer_bytes"] == 12
    assert result["row_pointers"] == [0, 24, 48]


def test_compare_retail_storage_layout_reports_bad_row_index():
    capture = _capture()
    capture["row_indices"] = [0, 4, 6]
    result = runtime.compare_retail_storage_layout(capture)
    assert result["ready"] is False
    assert result["row_index_mismatch_count"] == 1
    assert result["row_index_mismatches"][0]["row"] == 1


def test_compare_solver_captures_matches_identical_frames():
    capture = _capture()
    result = runtime.compare_solver_captures(capture, capture)
    assert result["ready"] is True
    assert result["status"] == "matched"
    assert result["rhs"]["mismatch_count"] == 0
    assert result["matrix"]["mismatch_count"] == 0
    assert result["storage"]["ready"] is True
    assert result["fingerprints"]["equal"] is True


def test_compare_solver_captures_returns_cell_level_divergence():
    expected = _capture()
    observed = _capture()
    observed["rhs"][1] = 2.25
    observed["matrix"][2][1] = 4.5
    observed["matrix"][1][2] = 4.5
    result = runtime.compare_solver_captures(expected, observed)
    assert result["ready"] is False
    assert result["status"] == "diverged"
    assert result["rhs"]["mismatches"][0]["index"] == 1
    assert result["matrix"]["mismatches"][0]["row"] == 1


def test_compare_solver_captures_blocks_scalar_count_mismatch():
    expected = _capture()
    observed = _capture()
    observed["scalar_count"] = 4
    observed["rhs"].append(3.0)
    observed["matrix"] = [
        [1.0, 2.0, 0.0, 0.0],
        [2.0, 3.0, 4.0, 0.0],
        [0.0, 4.0, 5.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]
    observed["row_indices"] = [0, 4, 8, 12]
    result = runtime.compare_solver_captures(expected, observed)
    assert result["ready"] is False
    assert result["status"] == "blocked"
    assert result["errors"][0]["kind"] == "scalar-count"


def test_capture_contract_is_explicit_about_runtime_dependency():
    report = runtime.describe_sdf_solver_capture_contract()
    assert report["ready"] is True
    assert report["required"]["scalar_count"] == "integer"
    assert report["retail_storage"]["row_index_formula"] == "scalar_count * row"
    assert "Identity-node selection remains capture-dependent." in report["limitations"]
