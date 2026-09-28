import body_matrix_cell_provenance_runtime as runtime


def _domain():
    return {
        "solver_scalar_count": 3,
        "records": [
            {
                "runtime_record_index": 0,
                "section": "JOINT",
                "solver_width": 3,
                "scalar_base": 0,
                "scalar_indices": [0, 1, 2],
                "posbody": "A",
                "negbody": "B",
            }
        ],
    }


def _overlapping_domain():
    return {
        "solver_scalar_count": 2,
        "records": [
            {
                "runtime_record_index": 0,
                "section": "BAR",
                "solver_width": 1,
                "scalar_base": 0,
                "scalar_indices": [0],
                "posbody": "A",
                "negbody": "B",
            },
            {
                "runtime_record_index": 1,
                "section": "BAR",
                "solver_width": 1,
                "scalar_base": 1,
                "scalar_indices": [1],
                "posbody": "A",
                "negbody": "C",
            },
        ],
    }


def test_cell_provenance_is_ready_for_valid_domain():
    result = runtime.build_cell_provenance(_domain())

    assert result["ready"] is True
    assert result["nonzero_cell_count"] == 9
    assert result["diagonal_cell_count"] == 3
    assert result["symmetric_support"] is True


def test_provenance_for_cell_contains_endpoint_and_record_identity():
    result = runtime.build_cell_provenance(_domain())

    entries = runtime.provenance_for_cell(result, 0, 2)

    assert entries
    assert entries[0]["body"] in {"A", "B"}
    assert entries[0]["source_scalar_index"] == 0
    assert entries[0]["target_scalar_index"] == 2
    assert entries[0]["source_runtime_record_index"] == 0
    assert entries[0]["target_runtime_record_index"] == 0


def test_overlapping_groups_create_multiple_producers_for_shared_cell():
    result = runtime.build_cell_provenance(_overlapping_domain())

    # A receives both BAR groups and therefore its 0,1 cross-cell has a
    # provenance witness in both ordered group directions.
    entries = runtime.provenance_for_cell(result, 0, 1)

    assert len(entries) >= 2
    assert result["max_producers_per_cell"] >= 2
    assert result["summary"] if "summary" in result else True


def test_validate_cell_provenance_accepts_valid_report():
    result = runtime.build_cell_provenance_contract(_domain())

    assert result["validation"]["ready"] is True
    assert result["validation"]["errors"] == []


def test_validate_cell_provenance_rejects_wrong_source_index():
    result = runtime.build_cell_provenance_contract(_domain())
    entry = result["provenance"]["0,1"][0]
    entry["source_scalar_index"] = 2

    validation = runtime.validate_cell_provenance(result)

    assert validation["ready"] is False
    assert "source-index-mismatch:0,1" in validation["errors"]


def test_validate_cell_provenance_rejects_non_unit_value():
    result = runtime.build_cell_provenance_contract(_domain())
    result["provenance"]["0,0"][0]["value"] = 2.0

    validation = runtime.validate_cell_provenance(result)

    assert validation["ready"] is False
    assert "non-unit-provenance-value:0,0" in validation["errors"]


def test_summarize_cell_provenance():
    result = runtime.summarize_cell_provenance(
        {
            "scalar_count": 40,
            "body_count": 11,
            "nonzero_cell_count": 700,
            "diagonal_cell_count": 40,
            "max_producers_per_cell": 6,
            "provenance": {
                "0,0": [{}, {}],
                "0,1": [{}],
            },
            "symmetric_support": True,
            "ready": True,
        }
    )

    assert result["scalar_count"] == 40
    assert result["nonzero_cell_count"] == 700
    assert result["diagonal_cell_count"] == 40
    assert result["max_producers_per_cell"] == 6
    assert result["cells_with_multiple_producers"] == 1
    assert result["symmetric_support"] is True


def test_validate_cell_provenance_detects_cell_count_mismatch():
    validation = runtime.validate_cell_provenance(
        {
            "scalar_count": 2,
            "provenance": {"0,0": []},
            "nonzero_cell_count": 2,
            "errors": [],
        }
    )

    assert validation["ready"] is False
    assert "nonzero-cell-count-mismatch" in validation["errors"]
