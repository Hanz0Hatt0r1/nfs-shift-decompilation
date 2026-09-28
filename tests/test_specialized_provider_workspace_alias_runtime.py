import specialized_provider_workspace_alias_runtime as runtime


def test_enumerate_candidate_addresses_reports_aliases():
    mapping = runtime.enumerate_candidate_addresses(
        (0x1000, 0x1018),
        scalar_count=4,
        workspace_start=0x1000,
        workspace_end=0x1038,
    )

    assert mapping[0x1000] == ((0, 0),)
    assert mapping[0x1018] == ((0, 3), (1, 0))
    assert mapping[0x1020] == ((1, 1),)


def test_enumerate_candidate_addresses_excludes_out_of_range_cells():
    mapping = runtime.enumerate_candidate_addresses(
        (0x1000,),
        scalar_count=4,
        workspace_start=0x1000,
        workspace_end=0x1018,
    )

    assert sorted(mapping) == [0x1000, 0x1008, 0x1010]


def test_validate_alias_map_rejects_out_of_range_diagonal():
    result = runtime.validate_alias_map(
        {
            "provider_id": 0,
            "scalar_count": 2,
            "workspace": {"start": "0x1000", "end": "0x1020"},
            "diagonal_entries": [
                {"pivot_index": 0, "diagonal_address": "0x1000"},
                {"pivot_index": 1, "diagonal_address": "0x2000"},
            ],
            "collision_classes": [],
            "errors": [],
        }
    )

    assert result["ready"] is False
    assert "pivot-1-diagonal-outside-workspace" in result["errors"]


def test_summarize_alias_map_exposes_collision_metrics():
    report = {
        "provider_id": 1,
        "scalar_count": 34,
        "candidate_cell_count": 1156,
        "unique_storage_addresses": 746,
        "collision_address_count": 401,
        "alias_entry_count": 410,
        "diagonal_entries": [1] * 34,
        "ready": True,
    }

    summary = runtime.summarize_alias_map(report)

    assert summary["candidate_cell_count"] == 1156
    assert summary["unique_storage_addresses"] == 746
    assert summary["collision_address_count"] == 401
    assert summary["alias_entry_count"] == 410
    assert summary["diagonal_count"] == 34
