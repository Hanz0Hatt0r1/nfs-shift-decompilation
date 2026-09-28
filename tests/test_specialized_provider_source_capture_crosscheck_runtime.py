import specialized_provider_source_capture_crosscheck_runtime as runtime


def test_factor_edge_addresses_use_provider_row_pointer():
    result = runtime.factor_edge_addresses(
        0,
        [(0, 1), (1, 2)],
    )

    assert result[0]["address"] == "0x00c21740"
    assert result[1]["address"] == "0x00c21810"


def test_crosscheck_partitions_factor_and_capture_addresses():
    source_pattern = {
        "provider_id": 0,
        "ready": True,
        "edges": [
            {"pivot_index": 0, "column": 1},
            {"pivot_index": 0, "column": 2},
        ],
    }
    before = {
        "provider_id": 0,
        "stage": "pre-solve-provider",
        "workspace": [0.0] * 1190,
        "output_vector": [0.0] * 40,
    }
    after = {
        "provider_id": 0,
        "stage": "post-solve-provider",
        "workspace": [0.0] * 1190,
        "output_vector": [0.0] * 40,
    }
    # row 0 base 0xC21738: cols 1 and 2 are 0xC21740 / 0xC21748.
    after["workspace"][1] = 1.0
    after["workspace"][2] = 2.0
    after["workspace"][10] = 3.0

    result = runtime.crosscheck_source_factor_writes(
        source_pattern,
        before,
        after,
    )

    assert result["ready"] is True
    assert result["source_factor_edge_count"] == 2
    assert result["capture_changed_workspace_address_count"] == 3
    assert result["overlap_count"] == 2
    assert result["factor_address_not_observed_changed_count"] == 0
    assert result["capture_workspace_change_not_factor_count"] == 1


def test_crosscheck_allows_source_factor_noop_without_failure():
    source_pattern = {
        "provider_id": 1,
        "ready": True,
        "edges": [
            {"pivot_index": 0, "column": 1},
        ],
    }
    before = {
        "provider_id": 1,
        "stage": "pre-solve-provider",
        "workspace": [0.0] * 746,
        "output_vector": [0.0] * 34,
    }
    after = {
        "provider_id": 1,
        "stage": "post-solve-provider",
        "workspace": [0.0] * 746,
        "output_vector": [0.0] * 34,
    }

    result = runtime.crosscheck_source_factor_writes(
        source_pattern,
        before,
        after,
    )

    assert result["ready"] is True
    assert result["factor_address_not_observed_changed_count"] == 1


def test_summarize_crosscheck_reports_ratio():
    result = runtime.summarize_crosscheck(
        {
            "provider_id": 0,
            "source_factor_edge_count": 10,
            "capture_changed_workspace_address_count": 15,
            "overlap_count": 8,
            "factor_address_not_observed_changed_count": 2,
            "capture_workspace_change_not_factor_count": 7,
            "ready": True,
        }
    )

    assert result["source_factor_overlap_ratio"] == 0.8


def test_validate_crosscheck_detects_partition_error():
    result = runtime.validate_crosscheck(
        {
            "provider_id": 0,
            "source_factor_address_count": 4,
            "overlap_count": 1,
            "factor_address_not_observed_changed_count": 1,
            "capture_changed_workspace_address_count": 3,
            "capture_workspace_change_not_factor_count": 2,
            "errors": [],
        }
    )

    assert result["ready"] is False
    assert "factor-address-partition-mismatch" in result["errors"]
