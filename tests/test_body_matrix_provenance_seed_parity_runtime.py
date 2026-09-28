import body_matrix_provenance_seed_parity_runtime as runtime


def _domain():
    return {
        "solver_scalar_count": 3,
        "records": [
            {
                "runtime_record_index": 0,
                "section": "JOINT",
                "solver_width": 3,
                "scalar_base": 0,
                "scalar_indices": [0, 1, 2],
                "posbody": "A",
                "negbody": "B",
            }
        ],
    }


def test_provenance_seed_parity_has_one_provenance_per_nonzero_cell():
    result = runtime.build_provenance_seed_parity(_domain())

    assert result["ready"] is True
    assert result["missing_provenance_cells"] == []
    assert result["unsupported_nonzero_cells"] == []
    assert result["provenance"]["nonzero_cell_count"] == 9
    assert result["seed_metrics"]["nonzero"] == 9


def test_validate_provenance_seed_parity_accepts_structural_consistency():
    result = runtime.build_provenance_seed_parity_contract(_domain())

    assert result["validation"]["ready"] is False
    assert "bmw-seed-shape-mismatch" in result["validation"]["errors"]


def test_validate_provenance_seed_parity_rejects_missing_provenance():
    result = runtime.build_provenance_seed_parity(_domain())
    result["missing_provenance_cells"] = ["0,0"]

    validation = runtime.validate_provenance_seed_parity(result)

    assert validation["ready"] is False
    assert "missing-provenance-present" in validation["errors"]


def test_validate_provenance_seed_parity_rejects_provenance_count_mismatch():
    result = runtime.build_provenance_seed_parity(_domain())
    result["provenance"]["nonzero_cell_count"] = 8

    validation = runtime.validate_provenance_seed_parity(result)

    assert validation["ready"] is False
    assert "matrix-provenance-cell-count-mismatch" in validation["errors"]


def test_validate_provenance_seed_parity_accepts_explicit_bmw_shape_fixture():
    report = {
        "scalar_count": 40,
        "seed_metrics": {
            "nonzero": 700,
            "zero": 900,
            "strict_upper_nonzero": 330,
            "row_nonzero_counts": [10] * 10 + [25] * 20 + [10] * 10,
        },
        "provenance": {
            "nonzero_cell_count": 700,
        },
        "seed_shape_match": True,
        "missing_provenance_cells": [],
        "unsupported_nonzero_cells": [],
        "errors": [],
    }

    validation = runtime.validate_provenance_seed_parity(report)

    assert validation["ready"] is True
    assert validation["errors"] == []


def test_summarize_provenance_seed_parity():
    result = runtime.summarize_provenance_seed_parity(
        {
            "scalar_count": 40,
            "seed_metrics": {
                "nonzero": 700,
                "strict_upper_nonzero": 330,
            },
            "provenance": {
                "nonzero_cell_count": 700,
            },
            "missing_provenance_cells": [],
            "unsupported_nonzero_cells": [],
            "seed_shape_match": True,
            "ready": True,
        }
    )

    assert result == {
        "scalar_count": 40,
        "nonzero_cells": 700,
        "strict_upper_nonzero": 330,
        "provenance_cells": 700,
        "missing_provenance_cells": 0,
        "unsupported_nonzero_cells": 0,
        "seed_shape_match": True,
        "ready": True,
    }


def test_contract_preserves_full_provenance_layer():
    result = runtime.build_provenance_seed_parity_contract(_domain())

    assert "generated_matrix" in result
    assert "provenance" in result
    assert "seed_metrics" in result
    assert "expected_seed_shape" in result
