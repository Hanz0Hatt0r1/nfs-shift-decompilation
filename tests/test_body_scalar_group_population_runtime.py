import body_scalar_group_population_runtime as runtime


def _domain():
    return {
        "solver_scalar_count": 6,
        "records": [
            {
                "runtime_record_index": 0,
                "section": "JOINT",
                "solver_width": 3,
                "scalar_base": 0,
                "scalar_indices": [0, 1, 2],
                "posbody": "A",
                "negbody": "B",
            },
            {
                "runtime_record_index": 1,
                "section": "HINGE",
                "solver_width": 2,
                "scalar_base": 3,
                "scalar_indices": [3, 4],
                "posbody": "B",
                "negbody": "C",
            },
            {
                "runtime_record_index": 2,
                "section": "BAR",
                "solver_width": 1,
                "scalar_base": 5,
                "scalar_indices": [5],
                "posbody": "C",
                "negbody": "A",
            },
        ],
    }


def test_scalar_group_witness_creates_two_endpoint_insertions_per_record():
    result = runtime.build_scalar_group_witness(_domain())

    assert result["ready"] is True
    assert result["runtime_constraint_records"] == 3
    assert result["endpoint_insertion_count"] == 6
    assert sorted(result["groups_by_body"]) == ["A", "B", "C"]


def test_section_population_mapping_is_exact():
    assert runtime.SECTION_POPULATION["JOINT"] == {
        "helper": "FUN_007ba8b0",
        "body_group_width": 3,
        "body_group_storage": "+0x160",
        "record_stride": 0x40,
        "scalar_index_offset": "+0x30",
        "auxiliary_offset": None,
    }
    assert runtime.SECTION_POPULATION["HINGE"]["auxiliary_offset"] == "+0x90"
    assert runtime.SECTION_POPULATION["BAR"]["body_group_width"] == 1


def test_witness_keeps_scalar_blocks_exact():
    result = runtime.build_scalar_group_witness(_domain())

    by_position = {
        item["ordered_position"]: item
        for item in result["insertions"]
        if item["endpoint_field"] == "posbody"
    }

    assert by_position[0]["scalar_indices"] == [0, 1, 2]
    assert by_position[1]["scalar_indices"] == [3, 4]
    assert by_position[2]["scalar_indices"] == [5]


def test_validate_scalar_group_witness_accepts_complete_fixture():
    witness = runtime.build_scalar_group_witness(_domain())
    result = runtime.validate_scalar_group_witness(witness)

    assert result["ready"] is True
    assert result["endpoint_insertions"] == 6
    assert result["errors"] == []


def test_validate_scalar_group_witness_rejects_wrong_endpoint_count():
    result = runtime.validate_scalar_group_witness(
        {
            "scalar_count": 6,
            "runtime_constraint_records": 3,
            "insertions": [{}] * 5,
            "errors": [],
        }
    )

    assert result["ready"] is False
    assert (
        "endpoint-insertion-count:expected=6:actual=5"
        in result["errors"]
    )


def test_validate_scalar_group_witness_rejects_bad_scalar_range():
    witness = runtime.build_scalar_group_witness(_domain())
    witness["insertions"][0]["scalar_indices"] = [0, 2, 3]

    result = runtime.validate_scalar_group_witness(witness)

    assert result["ready"] is False
    assert "scalar-index-range-mismatch:JOINT:0" in result["errors"]


def test_validate_scalar_group_witness_rejects_bad_storage_mapping():
    witness = runtime.build_scalar_group_witness(_domain())
    witness["insertions"][0]["body_group_storage"] = "+0x168"

    result = runtime.validate_scalar_group_witness(witness)

    assert result["ready"] is False
    assert "body-group-storage-mismatch:JOINT" in result["errors"]


def test_summarize_scalar_group_witness_counts_widths():
    witness = runtime.build_scalar_group_witness(_domain())
    summary = runtime.summarize_scalar_group_witness(witness)

    assert summary["scalar_count"] == 6
    assert summary["runtime_constraint_records"] == 3
    assert summary["endpoint_insertions"] == 6
    assert summary["width3_group_count"] == 2
    assert summary["width2_group_count"] == 2
    assert summary["width1_group_count"] == 2


def test_contract_contains_source_to_body_population_formula():
    result = runtime.build_scalar_group_population_contract(_domain())

    assert result["function"] == "FUN_007b3820"
    assert result["downstream"] == "FUN_007b2010 -> FUN_007ba2b0"
    assert result["formula"]["endpoint_population"].startswith(
        "helper invoked once"
    )
    assert result["status"] == (
        "source-backed-body-scalar-group-population"
    )
