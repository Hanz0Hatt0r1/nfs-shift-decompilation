import specialized_provider_acceptance_predicate_runtime as runtime
from specialized_provider_runtime import get_provider


def test_index_cell_roundtrip_for_small_domain():
    n = 5
    for row in range(n):
        for column in range(row + 1, n):
            index = runtime._cell_to_index(row, column, n)
            assert runtime._index_to_cell(index, n) == (row, column)


def test_signature_matrices_match_both_provider_predicates():
    for provider_id in (0, 1):
        matrix = runtime.build_signature_matrix(provider_id)
        result = runtime.evaluate_acceptance_predicate(
            provider_id,
            matrix,
        )
        assert result["ready"] is True
        assert result["matched"] is True
        assert result["status"] == "matched"
        assert result["upper_triangle_cells"] == (
            get_provider(provider_id).scalar_count
            * (get_provider(provider_id).scalar_count - 1)
            // 2
        )


def test_provider0_predicate_rejects_first_cell_divergence():
    matrix = runtime.build_signature_matrix(0)
    matrix[0][1] = 1.0
    matrix[1][0] = 1.0

    result = runtime.evaluate_acceptance_predicate(0, matrix)

    assert result["ready"] is True
    assert result["matched"] is False
    assert result["status"] == "pattern-divergence"
    assert result["mismatch"]["row"] == 0
    assert result["mismatch"]["column"] == 1
    assert result["mismatch"]["linear_index"] == 0
    assert result["mismatch"]["expected_nonzero"] is False
    assert result["mismatch"]["observed_nonzero"] is True


def test_provider0_predicate_rejects_transition_cell_with_exact_location():
    matrix = runtime.build_signature_matrix(0)
    matrix[0][3] = 0.0
    matrix[3][0] = 0.0

    result = runtime.evaluate_acceptance_predicate(0, matrix)

    assert result["status"] == "pattern-divergence"
    assert result["mismatch"]["row"] == 0
    assert result["mismatch"]["column"] == 3


def test_provider1_predicate_rejects_dimension_mismatch():
    provider = get_provider(1)
    matrix = [
        [0.0] * (provider.scalar_count + 1)
        for _ in range(provider.scalar_count + 1)
    ]

    result = runtime.evaluate_acceptance_predicate(1, matrix)

    assert result["status"] == "dimension-mismatch"
    assert result["ready"] is False
    assert result["matched"] is False
    assert result["expected_scalar_count"] == 34
    assert result["actual_scalar_count"] == 35


def test_description_contains_retail_final_run_checks():
    result = runtime.describe_acceptance_predicate()

    assert result["source_behavior"]["provider0"] == {
        "dimension_constant": "0x28",
        "final_transition_count": 0x52,
        "final_run_length": 0xc2,
    }
    assert result["source_behavior"]["provider1"] == {
        "dimension_constant": "0x22",
        "final_transition_count": 0x6a,
        "final_run_length": 0x31,
    }


def test_contract_validation_accepts_both_signature_matrices():
    result = runtime.validate_acceptance_predicate_contract()

    assert result["ready"] is True
    assert result["errors"] == []


def test_rle_position_reports_run_and_offset():
    provider = get_provider(0)

    position = runtime._rle_position(
        2,
        provider.rle,
    )

    assert position["run_index"] == 1
    assert position["run_offset"] == 0
    assert position["state"] is True
