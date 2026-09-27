import pytest

import sdf_body_solver_export_runtime as runtime


def test_body_solver_export_contract_matches_retail_offsets_and_order():
    report = runtime.describe_sdf_body_solver_export_contract()
    assert report["ready"] is True
    assert report["function"] == "FUN_007ba570"
    assert report["sources"]["solver_vector"] == "+0x150"
    assert report["sources"]["solver_vector_count"] == "+0xa4"
    assert report["sources"]["solver_matrix"] == "+0x154"
    assert report["sources"]["solver_matrix_count"] == "+0xa8"
    assert report["order"] == [
        "add per-body solver vector contribution",
        "add per-body solver matrix contribution",
    ]
    assert report["operations"][0]["operation"] == "solver_vector_destination[i] += source[i]"
    assert report["operations"][1]["operation"] == "solver_matrix_destination[i] += source[i]"


def test_body_solver_export_adds_runtime_channels_to_destinations():
    result = runtime.export_body_accumulators(
        [1.0, 2.5, -3.0],
        [4.0, -5.0],
        [10.0, 20.0, 30.0],
        [1.0, 2.0],
    )
    assert result["solver_vector"] == [11.0, 22.5, 27.0]
    assert result["solver_matrix"] == [5.0, -3.0]
    assert result["source_counts"] == {"solver_vector": 3, "solver_matrix": 2}


def test_body_solver_export_rejects_short_destination_buffers():
    with pytest.raises(ValueError, match="destination"):
        runtime.export_body_accumulators([1, 2], [3], [0], [0])
