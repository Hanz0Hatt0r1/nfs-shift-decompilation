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


def test_profile_zero_addresses_includes_bulk_clear_ranges():
    result = runtime._profile_zero_addresses(
        {
            "rows": [
                {
                    "zero_assignments": ["0x1000"],
                    "bulk_clears": [
                        {"base": "0x1010", "bytes": 0x10},
                    ],
                }
            ]
        },
        start=0x1000,
        end=0x1040,
    )

    assert result == {
        0x1000,
        0x1010,
        0x1018,
    }


def test_validate_reset_cleanup_accepts_exact_storage_equivalence():
    result = runtime.validate_reset_cleanup(
        {
            "provider_id": 0,
            "scalar_count": 2,
            "reset_zero_slot_count": 4,
            "cleanup_storage_slot_count": 4,
            "reset_unit_diagonal_count": 2,
            "reset_zero_cleanup_exact_match": True,
            "unit_diagonal_inside_cleanup": True,
            "unit_diagonal_in_reset_zero_domain": True,
            "output_zero_exact_match": True,
            "errors": [],
        }
    )

    assert result["ready"] is True
    assert result["errors"] == []


def test_validate_reset_cleanup_rejects_missing_zero_equivalence():
    result = runtime.validate_reset_cleanup(
        {
            "provider_id": 1,
            "scalar_count": 34,
            "reset_zero_slot_count": 280,
            "cleanup_storage_slot_count": 314,
            "reset_unit_diagonal_count": 34,
            "reset_zero_cleanup_exact_match": False,
            "unit_diagonal_inside_cleanup": True,
            "unit_diagonal_in_reset_zero_domain": False,
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
            "cleanup_storage_slot_count": 314,
            "reset_unit_diagonal_count": 33,
            "reset_zero_cleanup_exact_match": False,
            "unit_diagonal_inside_cleanup": True,
            "unit_diagonal_in_reset_zero_domain": False,
            "output_zero_exact_match": True,
            "errors": [],
        }
    )

    assert result["ready"] is False
    assert (
        "unit-diagonal-count:expected=34:actual=33"
        in result["errors"]
    )


def test_validate_reset_cleanup_allows_unit_seed_outside_reset_zero_domain():
    result = runtime.validate_reset_cleanup(
        {
            "provider_id": 1,
            "scalar_count": 34,
            "reset_zero_slot_count": 280,
            "cleanup_storage_slot_count": 314,
            "reset_unit_diagonal_count": 34,
            "reset_zero_cleanup_exact_match": False,
            "unit_diagonal_inside_cleanup": True,
            "unit_diagonal_in_reset_zero_domain": False,
            "output_zero_exact_match": True,
            "errors": [],
        }
    )

    assert "unit-diagonal-not-reset-zero" not in result["errors"]


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
            "unit_diagonal_in_reset_zero_domain": True,
            "output_zero_exact_match": True,
            "ready": True,
        }
    )

    assert result["provider_id"] == 0
    assert result["scalar_count"] == 40
    assert result["reset_zero_cleanup_exact_match"] is True
    assert result["unit_diagonal_in_reset_zero_domain"] is True
    assert result["output_zero_exact_match"] is True
