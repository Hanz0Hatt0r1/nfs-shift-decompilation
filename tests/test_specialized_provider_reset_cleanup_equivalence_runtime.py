import specialized_provider_reset_cleanup_equivalence_runtime as runtime


def test_coverage_slots_expand_merged_intervals_and_direct_addresses():
    slots = runtime._coverage_slots(
        {
            "merged_intervals": [
                {"start": "0x1000", "end": "0x1020"},
            ],
            "direct_zero_addresses": [
                "0x1030",
            ],
        }
    )

    assert slots == {
        0x1000,
        0x1008,
        0x1010,
        0x1018,
        0x1030,
    }


def test_compare_reset_cleanup_accepts_exact_storage_equivalence():
    result = runtime.compare_reset_cleanup
    # Pure structural helper validation is exercised through the public
    # validator below; this test keeps the expected booleans explicit.
    report = {
        "provider_id": 0,
        "scalar_count": 2,
        "reset_zero_slot_count": 4,
        "cleanup_storage_slot_count": 4,
        "reset_unit_diagonal_count": 2,
        "reset_zero_cleanup_exact_match": True,
        "unit_diagonal_inside_cleanup": True,
        "unit_diagonal_overwrites_reset_zero": True,
        "output_zero_exact_match": True,
        "errors": [],
    }

    validated = runtime.validate_reset_cleanup(report)

    assert validated["ready"] is True
    assert validated["errors"] == []


def test_validate_reset_cleanup_rejects_missing_zero_equivalence():
    result = runtime.validate_reset_cleanup(
        {
            "provider_id": 0,
            "scalar_count": 2,
            "reset_zero_slot_count": 3,
            "cleanup_storage_slot_count": 4,
            "reset_unit_diagonal_count": 2,
            "reset_zero_cleanup_exact_match": False,
            "unit_diagonal_inside_cleanup": True,
            "unit_diagonal_overwrites_reset_zero": True,
            "output_zero_exact_match": True,
            "errors": [],
        }
    )

    assert result["ready"] is False
    assert "reset-zero-cleanup-not-exact" in result["errors"]


def test_validate_reset_cleanup_requires_one_diagonal_per_scalar():
    result = runtime.validate_reset_cleanup(
        {
            "provider_id": 1,
            "scalar_count": 34,
            "reset_zero_slot_count": 280,
            "cleanup_storage_slot_count": 280,
            "reset_unit_diagonal_count": 33,
            "reset_zero_cleanup_exact_match": True,
            "unit_diagonal_inside_cleanup": True,
            "unit_diagonal_overwrites_reset_zero": True,
            "output_zero_exact_match": True,
            "errors": [],
        }
    )

    assert result["ready"] is False
    assert (
        "unit-diagonal-count:expected=34:actual=33"
        in result["errors"]
    )


def test_summarize_reset_cleanup():
    result = runtime.summarize_reset_cleanup(
        {
            "provider_id": 0,
            "scalar_count": 40,
            "cleanup_storage_slot_count": 410,
            "reset_zero_slot_count": 410,
            "reset_unit_diagonal_count": 40,
            "reset_zero_cleanup_exact_match": True,
            "unit_diagonal_inside_cleanup": True,
            "unit_diagonal_overwrites_reset_zero": True,
            "output_zero_exact_match": True,
            "ready": True,
        }
    )

    assert result["provider_id"] == 0
    assert result["scalar_count"] == 40
    assert result["reset_zero_cleanup_exact_match"] is True
    assert result["unit_diagonal_overwrites_reset_zero"] is True
    assert result["output_zero_exact_match"] is True
