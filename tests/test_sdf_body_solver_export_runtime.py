import pytest

import sdf_body_solver_export_runtime as runtime


def test_body_solver_export_contract_matches_retail_offsets_and_order():
    report = runtime.describe_sdf_body_solver_export_contract()
    assert report["ready"] is True
    assert report["function"] == "FUN_007ba570"
    assert report["sources"]["primary"] == "+0x150"
    assert report["sources"]["primary_count"] == "+0xa4"
    assert report["sources"]["secondary"] == "+0x154"
    assert report["sources"]["secondary_count"] == "+0xa8"
    assert report["order"] == [
        "copy primary accumulator",
        "copy secondary accumulator",
    ]
    assert report["operations"][0]["operation"] == "destination[i] += source[i]"
    assert report["operations"][1]["operation"] == "destination[i] += source[i]"


def test_body_solver_export_adds_runtime_channels_to_destinations():
    result = runtime.export_body_accumulators(
        [1.0, 2.5, -3.0],
        [4.0, -5.0],
        [10.0, 20.0, 30.0],
        [1.0, 2.0],
    )
    assert result["primary"] == [11.0, 22.5, 27.0]
    assert result["secondary"] == [5.0, -3.0]
    assert result["source_counts"] == {"primary": 3, "secondary": 2}


def test_body_solver_export_rejects_short_destination_buffers():
    with pytest.raises(ValueError, match="destination"):
        runtime.export_body_accumulators([1, 2], [3], [0], [0])
