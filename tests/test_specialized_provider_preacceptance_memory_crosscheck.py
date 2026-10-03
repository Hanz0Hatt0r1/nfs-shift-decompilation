import specialized_provider_preacceptance_matrix_runtime as runtime


def _summary(*, index=0, callers=None, consistent=True, role_marker=True):
    callers = ["FUN_007b3820"] if callers is None else callers
    return {
        "format": "SHIFT-MEMORY-SOURCE-SEMANTIC-SUMMARY/1",
        "allocation_size_role_proven": True,
        "released_pointer_role_proven": False,
        "semantic_profiles_consistent": consistent,
        "wrapper_profiles": [
            {
                "wrapper": "FUN_008868d0",
                "allocation_size": {
                    "proven_callsite_count": 4,
                    "source_argument_indices": [index],
                    "source_argument_index_consistent": True,
                    "source_argument_index": index,
                    "observed_source_expressions": [
                        "scalar_count * 4",
                        "other_count * 4",
                    ],
                    "caller_count": len(callers),
                    "callers": callers,
                },
                "released_pointer": None,
                "proven_source_roles": ["allocation-size"] if role_marker else [],
                "blockers": [],
            }
        ],
        "blockers": [],
        "scope": {
            "source_allocation_size_role_proven": True,
            "source_role_indices_consistent": consistent,
            "pool_selector_role_proven": False,
            "allocator_abi_proven": False,
        },
    }


def test_memory_summary_crosschecks_row_pointer_allocation_size_role():
    result = runtime.build_matrix_construction_contract(_summary())

    evidence = result["memory_wrapper_evidence"]
    assert result["status"] == (
        "source-and-diagnostic-backed-preacceptance-matrix-build"
    )
    assert evidence["allocator"] == "FUN_008868d0"
    assert evidence["allocation_size_role_proven"] is True
    assert evidence["expected_source_argument_index"] == 0
    assert evidence["source_argument_index"] == 0
    assert evidence["source_argument_index_matches_contract"] is True
    assert evidence["matrix_builder_caller_observed"] is True
    assert evidence["crosscheck_ready"] is True
    assert evidence["blockers"] == []
    assert "scalar_count * 4" in evidence["observed_source_expressions"]

    validation = runtime.validate_matrix_construction_contract(_summary())
    assert validation["ready"] is True
    assert validation["memory_crosscheck_requested"] is True
    assert validation["row_pointer_allocation_size_crosschecked"] is True
    assert validation["memory_crosscheck_blockers"] == []


def test_wrong_source_argument_index_fails_closed_without_invalidating_source_contract():
    result = runtime.build_matrix_construction_contract(_summary(index=1))

    evidence = result["memory_wrapper_evidence"]
    assert result["status"] == "source-backed-preacceptance-matrix-build"
    assert evidence["allocation_size_role_proven"] is True
    assert evidence["source_argument_index"] == 1
    assert evidence["source_argument_index_matches_contract"] is False
    assert evidence["crosscheck_ready"] is False
    assert "allocation_size_source_index_mismatch" in evidence["blockers"]

    validation = runtime.validate_matrix_construction_contract(_summary(index=1))
    assert validation["ready"] is True
    assert validation["row_pointer_allocation_size_crosschecked"] is False
    assert "allocation_size_source_index_mismatch" in validation[
        "memory_crosscheck_blockers"
    ]


def test_missing_matrix_builder_caller_fails_closed():
    result = runtime.build_matrix_construction_contract(
        _summary(callers=["FUN_00112233"])
    )

    evidence = result["memory_wrapper_evidence"]
    assert evidence["allocation_size_role_proven"] is True
    assert evidence["source_argument_index_matches_contract"] is True
    assert evidence["matrix_builder_caller_observed"] is False
    assert evidence["crosscheck_ready"] is False
    assert evidence["blockers"] == ["matrix_builder_caller_not_observed"]


def test_role_marker_is_required_for_crosscheck():
    result = runtime.build_matrix_construction_contract(_summary(role_marker=False))

    evidence = result["memory_wrapper_evidence"]
    assert evidence["allocation_size_role_proven"] is False
    assert evidence["crosscheck_ready"] is False
    assert "allocation_size_role_marker_missing" in evidence["blockers"]


def test_no_summary_preserves_legacy_status_and_explicit_blocker():
    result = runtime.build_matrix_construction_contract()

    assert result["status"] == "source-backed-preacceptance-matrix-build"
    evidence = result["memory_wrapper_evidence"]
    assert evidence["summary_present"] is False
    assert evidence["crosscheck_ready"] is False
    assert evidence["blockers"] == [
        "memory_source_semantic_summary_not_supplied"
    ]


def test_wrong_memory_summary_format_is_rejected():
    try:
        runtime.build_matrix_construction_contract({"format": "WRONG"})
    except ValueError as exc:
        assert "SHIFT-MEMORY-SOURCE-SEMANTIC-SUMMARY/1" in str(exc)
    else:
        raise AssertionError("wrong memory source summary format was accepted")
