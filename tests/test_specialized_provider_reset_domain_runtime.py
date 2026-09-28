import specialized_provider_reset_domain_runtime as runtime


def test_bulk_clear_slots_are_expanded_to_double_addresses():
    slots = runtime._slots_from_bulk_clears(
        [
            {
                "bulk_clears": [
                    {"base": "0x1000", "bytes": 0x18},
                ]
            }
        ],
        start=0x1000,
        end=0x1040,
    )

    assert slots == {
        0x1000,
        0x1008,
        0x1010,
    }


def test_build_reset_domain_separates_zero_and_unit_slots():
    result = runtime.build_reset_domain(
        {
            "provider_id": 0,
            "reset_function": "FUN_007d3150",
            "ready": True,
            "errors": [],
            "rows": [
                {
                    "zero_assignments": ["0x00c21740"],
                    "bulk_clears": [
                        {"base": "0x00c21750", "bytes": 0x10},
                    ],
                    "diagonal_address": "0x00c21738",
                },
                {
                    "zero_assignments": [],
                    "bulk_clears": [],
                    "diagonal_address": "0x00c21768",
                },
            ],
        },
        provider_id=0,
    )

    assert result["reset_zero_slot_count"] == 3
    assert result["unit_diagonal_slot_count"] == 2
    assert result["reset_touched_slot_count"] == 5
    assert result["zero_unit_overlap_count"] == 0
    assert result["zero_unit_disjoint"] is True
    assert "0x00c21738" in result["unit_diagonal_addresses"]


def test_validate_reset_domain_checks_unit_cardinality():
    result = runtime.validate_reset_domain(
        {
            "provider_id": 1,
            "scalar_count": 34,
            "zero_addresses": [],
            "unit_diagonal_addresses": ["0x00c1fe38"],
            "touched_addresses": ["0x00c1fe38"],
            "reset_touched_slot_count": 1,
            "reset_zero_slot_count": 0,
            "errors": [],
        }
    )

    assert result["ready"] is False
    assert "unit-diagonal-count:expected=34:actual=1" in result["errors"]


def test_validate_reset_domain_rejects_zero_unit_overlap():
    result = runtime.validate_reset_domain(
        {
            "provider_id": 0,
            "scalar_count": 2,
            "zero_addresses": ["0x00c21738"],
            "unit_diagonal_addresses": [
                "0x00c21738",
                "0x00c21748",
            ],
            "touched_addresses": [
                "0x00c21738",
                "0x00c21748",
            ],
            "reset_touched_slot_count": 2,
            "reset_zero_slot_count": 1,
            "errors": [],
        }
    )

    # validate_reset_domain derives overlap from the supplied address sets.
    assert result["ready"] is False
    assert "unit-diagonal-overlaps-zero" in result["errors"]


def test_validate_reset_domain_accepts_disjoint_fixture():
    result = runtime.validate_reset_domain(
        {
            "provider_id": 0,
            "scalar_count": 2,
            "zero_addresses": ["0x00c21740"],
            "unit_diagonal_addresses": [
                "0x00c21738",
                "0x00c21748",
            ],
            "touched_addresses": [
                "0x00c21738",
                "0x00c21740",
                "0x00c21748",
            ],
            "reset_touched_slot_count": 3,
            "reset_zero_slot_count": 1,
            "errors": [],
        }
    )

    assert result["ready"] is True


def test_summarize_reset_domain():
    result = runtime.summarize_reset_domain(
        {
            "provider_id": 0,
            "scalar_count": 40,
            "direct_zero_slot_count": 300,
            "bulk_zero_slot_count": 150,
            "reset_zero_slot_count": 370,
            "unit_diagonal_slot_count": 40,
            "reset_touched_slot_count": 410,
            "workspace_zero_slot_count": 370,
            "output_zero_slot_count": 0,
            "zero_unit_overlap_count": 0,
            "zero_unit_disjoint": True,
            "ready": True,
        }
    )

    assert result["reset_zero_slot_count"] == 370
    assert result["unit_diagonal_slot_count"] == 40
    assert result["reset_touched_slot_count"] == 410
    assert result["zero_unit_disjoint"] is True
