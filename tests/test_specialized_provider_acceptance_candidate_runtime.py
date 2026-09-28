import specialized_provider_acceptance_candidate_runtime as runtime


def test_analyze_acceptance_candidates_unique_match():
    matrix = __import__(
        "specialized_provider_acceptance_predicate_runtime",
        fromlist=["build_signature_matrix"],
    ).build_signature_matrix(0)

    result = runtime.analyze_acceptance_candidates(
        matrix,
        provider_ids=(0, 1),
    )

    assert result["matching_provider_ids"] == [0]
    assert result["match_count"] == 1
    assert result["status"] == "unique-match"
    assert result["provider_identity_inferred"] is False


def test_analyze_acceptance_candidates_no_match():
    matrix = [
        [0.0] * 40
        for _ in range(40)
    ]

    result = runtime.analyze_acceptance_candidates(
        matrix,
        provider_ids=(0,),
    )

    assert result["matching_provider_ids"] == []
    assert result["match_count"] == 0
    assert result["status"] == "no-match"


def test_analyze_acceptance_candidates_dimension_mismatch_is_not_match():
    matrix = [
        [0.0] * 40
        for _ in range(40)
    ]

    result = runtime.analyze_acceptance_candidates(
        matrix,
        provider_ids=(1,),
    )

    assert result["status"] == "no-match"
    assert result["matching_provider_ids"] == []
    assert result["providers"][0]["status"] == "dimension-mismatch"
    assert result["ready"] is False


def test_analyze_capture_candidates_consumes_existing_logical_schema():
    predicate = __import__(
        "specialized_provider_acceptance_predicate_runtime",
        fromlist=["build_signature_matrix"],
    )
    matrix = predicate.build_signature_matrix(0)

    result = runtime.analyze_capture_candidates(
        {
            "scalar_count": 40,
            "matrix": matrix,
            "rhs": [0.0] * 40,
        },
        provider_ids=(0,),
    )

    assert result["matching_provider_ids"] == [0]


def test_summarize_acceptance_candidates():
    result = runtime.summarize_acceptance_candidates(
        {
            "matrix_dimension": 40,
            "matching_provider_ids": [0],
            "match_count": 1,
            "status": "unique-match",
            "ready": True,
            "provider_identity_inferred": False,
        }
    )

    assert result == {
        "matrix_dimension": 40,
        "matching_provider_ids": [0],
        "match_count": 1,
        "status": "unique-match",
        "ready": True,
        "provider_identity_inferred": False,
    }


def test_contract_preserves_bmw_seed_boundary():
    contract = runtime.build_acceptance_candidate_contract()

    assert contract["known_bmw_seed_boundary"]["scalar_count"] == 40
    assert contract["known_bmw_seed_boundary"]["strict_upper_nonzero_cells"] == 330
    assert contract["known_bmw_seed_boundary"]["provider0_expected_strict_upper_nonzero"] == 450
    assert contract["known_bmw_seed_boundary"]["provider1_expected_dimension"] == 34
