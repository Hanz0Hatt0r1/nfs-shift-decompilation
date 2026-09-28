import body_solver_domain_matrix_builder_runtime as runtime
from body_matrix_structure_runtime import BodyGroup


def _domain():
    return {
        "solver_scalar_count": 4,
        "records": [
            {
                "section": "JOINT",
                "solver_width": 3,
                "scalar_indices": [0, 1, 2],
                "posbody": "A",
                "negbody": "B",
            },
            {
                "section": "BAR",
                "solver_width": 1,
                "scalar_indices": [3],
                "posbody": "B",
                "negbody": "C",
            },
        ],
    }


def test_body_group_map_attaches_each_constraint_to_both_endpoints():
    groups = runtime.build_body_group_map(_domain())

    assert sorted(group.width for group in groups["A"]) == [3]
    assert sorted(group.width for group in groups["B"]) == [1, 3]
    assert sorted(group.width for group in groups["C"]) == [1]


def test_structural_matrix_is_symmetric_and_diagonal_seeded():
    result = runtime.build_structural_matrix(_domain())

    assert result["ready"] is True
    assert result["matrix_nonzero_cells"] == 16
    assert result["strict_upper_nonzero_cells"] == 6
    assert result["diagonal_missing"] == []
    assert result["symmetric"] is True


def test_structural_matrix_contains_body_union_cells():
    result = runtime.build_structural_matrix(_domain())
    matrix = result["matrix"]

    for row in range(4):
        for column in range(4):
            assert matrix[row][column] == 1.0


def test_bmw_wrapper_requires_40_scalars():
    result = runtime.build_bmw_matrix_structure(_domain())

    assert result["ready"] is False
    assert result["status"] == "dimension-mismatch"
    assert result["expected_scalar_count"] == 40


def test_compare_structure_to_seed_accepts_exact_support():
    generated = runtime.build_structural_matrix(_domain())
    seed = {
        "matrix": generated["matrix"],
    }

    result = runtime.compare_structure_to_seed(
        generated,
        seed,
    )

    assert result["ready"] is True
    assert result["mismatch_count"] == 0


def test_compare_structure_to_seed_reports_cell_mismatch():
    generated = runtime.build_structural_matrix(_domain())
    seed = {
        "matrix": [row[:] for row in generated["matrix"]],
    }
    seed["matrix"][0][3] = 0.0

    result = runtime.compare_structure_to_seed(
        generated,
        seed,
    )

    assert result["ready"] is False
    assert {"row": 0, "column": 3} <= result["mismatches"][0].items()


def test_acceptance_evaluation_reports_candidate_status():
    generated = runtime.build_structural_matrix(_domain())

    result = runtime.evaluate_generated_acceptance(
        generated,
        provider_ids=(0, 1),
    )

    assert result["scalar_count"] == 4
    assert result["status"] == "no-match"
    assert result["provider_identity_inferred"] is False


def test_contract_records_source_formula_and_scope():
    result = runtime.build_body_matrix_builder_contract(_domain())

    assert result["source"] == "FUN_007b2010 -> FUN_007ba2b0"
    assert result["formula"]["group_width"] == "JOINT=3, HINGE=2, BAR=1"
    assert result["status"] == (
        "source-backed-body-solver-domain-matrix-builder"
    )


def test_summarize_structural_matrix():
    result = runtime.summarize_structural_matrix(
        {
            "scalar_count": 4,
            "body_count": 3,
            "matrix_nonzero_cells": 16,
            "strict_upper_nonzero_cells": 6,
            "diagonal_missing": [],
            "symmetric": True,
            "ready": True,
        }
    )

    assert result == {
        "scalar_count": 4,
        "body_count": 3,
        "matrix_nonzero_cells": 16,
        "strict_upper_nonzero_cells": 6,
        "diagonal_missing_count": 0,
        "symmetric": True,
        "ready": True,
    }
