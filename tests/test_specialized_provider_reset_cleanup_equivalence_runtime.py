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


def test_case_seed_clear_conflicts_stays_empty_for_valid_row():
    result = runtime._case_seed_clear_conflicts(
        {
            "rows": [
                {
                    "pivot_index": 0,
                    "diagonal_address": "0x1000",
                    "zero_assignments": ["0x1008"],
                    "bulk_clears": [
                        {"base": "0x1010", "bytes": 0x08},
                    ],
                }
            ]
        }
    )

    assert result == []


def test_case_seed_clear_conflicts_detects_same_case_overlap():
    result = runtime._case_seed_clear_conflicts(
        {
            "rows": [
                {
                    "pivot_index": 7,
                    "diagonal_address": "0x1050",
                    "zero_assignments": ["0x1050"],
                    "bulk_clears": [],
                }
            ]
        }
    )

    assert result == [7]


def test_validate_reset_cleanup_accepts_exact_reset_partition():
    result = runtime.validate_reset_cleanup(
        {
            "provider_id": 0,
            "scalar_count": 2,
            "reset_zero_slot_count": 2,
            "cleanup_storage_slot_count": 2,
            "reset_unit_diagonal_count": 2,
            "reset_zero_cleanup_exact_match": True,
            "reset_zero_subset_cleanup": True,
            "unit_diagonal_inside_cleanup": True,
            "unit_diagonal_overlaps_reset_zero": False,
            "case_seed_clear_conflicts": [],
            "cleanup_reconstructed_from_reset": True,
            "cleanup_reset_partition_disjoint": True,
            "output_zero_exact_match": True,
            "errors": [],
        }
    )

    assert result["ready"] is True
    assert result["errors"] == []


def test_validate_reset_cleanup_rejects_missing_reset_seed():
    result = runtime.validate_reset_cleanup(
        {
            "provider_id": 1,
            "scalar_count": 34,
            "reset_zero_slot_count": 280,
            "cleanup_storage_slot_count": 314,
            "reset_unit_diagonal_count": 34,
            "reset_zero_cleanup_exact_match": False,
            "reset_zero_subset_cleanup": True,
            "unit_diagonal_inside_cleanup": True,
            "unit_diagonal_overlaps_reset_zero": False,
            "case_seed_clear_conflicts": [],
            "cleanup_reconstructed_from_reset": False,
            "cleanup_reset_partition_disjoint": True,
            "output_zero_exact_match": True,
            "errors": [],
        }
    )

    assert result["ready"] is False
    assert "cleanup-not-reconstructed-from-reset" in result["errors"]


def test_validate_reset_cleanup_requires_one_diagonal_per_scalar():
    result = runtime.validate_reset_cleanup(
        {
            "provider_id": 1,
            "scalar_count": 34,
            "reset_zero_slot_count": 280,
            "cleanup_storage_slot_count": 314,
            "reset_unit_diagonal_count": 33,
            "reset_zero_cleanup_exact_match": True,
            "reset_zero_subset_cleanup": True,
            "unit_diagonal_inside_cleanup": True,
            "unit_diagonal_overlaps_reset_zero": False,
            "case_seed_clear_conflicts": [],
            "cleanup_reconstructed_from_reset": True,
            "cleanup_reset_partition_disjoint": True,
            "output_zero_exact_match": True,
            "errors": [],
        }
    )

    assert result["ready"] is False
    assert "unit-diagonal-count:expected=34:actual=33" in result["errors"]


def test_validate_reset_cleanup_rejects_overlapping_unit_seed():
    result = runtime.validate_reset_cleanup(
        {
            "provider_id": 1,
            "scalar_count": 34,
            "reset_zero_slot_count": 280,
            "cleanup_storage_slot_count": 314,
            "reset_unit_diagonal_count": 34,
            "reset_zero_cleanup_exact_match": False,
            "reset_zero_subset_cleanup": True,
            "unit_diagonal_inside_cleanup": True,
            "unit_diagonal_overlaps_reset_zero": True,
            "cleanup_reconstructed_from_reset": True,
            "cleanup_reset_partition_disjoint": False,
            "output_zero_exact_match": True,
            "errors": [],
        }
    )

    assert result["ready"] is False
    assert "unit-diagonal-overlaps-reset-zero" in result["errors"]


def test_summarize_reset_cleanup():
    result = runtime.summarize_reset_cleanup(
        {
            "provider_id": 0,
            "scalar_count": 40,
            "cleanup_storage_slot_count": 410,
            "reset_zero_slot_count": 370,
            "reset_unit_diagonal_count": 40,
            "reset_zero_cleanup_exact_match": True,
            "reset_zero_subset_cleanup": True,
            "unit_diagonal_inside_cleanup": True,
            "unit_diagonal_overlaps_reset_zero": False,
            "cleanup_reconstructed_from_reset": True,
            "cleanup_reset_partition_disjoint": True,
            "output_zero_exact_match": True,
            "ready": True,
        }
    )

    assert result["provider_id"] == 0
    assert result["scalar_count"] == 40
    assert result["reset_zero_cleanup_exact_match"] is True
    assert result["cleanup_reconstructed_from_reset"] is True
    assert result["cleanup_reset_partition_disjoint"] is True
    assert result["output_zero_exact_match"] is True
