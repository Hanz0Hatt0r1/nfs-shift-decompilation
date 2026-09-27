import sdf_body_accumulator_runtime as runtime


def test_body_accumulator_contract_matches_retail_layout():
    report = runtime.describe_sdf_body_accumulator_contract()
    assert report["ready"] is True
    assert report["storage"]["solver_vector_contribution"] == {"base": "+0x150", "count": "+0xa4", "element_size": 8}
    assert report["storage"]["solver_matrix_contribution"] == {"base": "+0x154", "count": "+0xa8", "element_size": 8}
    assert report["storage"]["row_pointers"] == {"base": "+0x158", "count": "+0xac", "element_size": 4}
    assert report["storage"]["row_indices"]["base"] == "+0x15c"
    assert report["hinge_refresh"]["sample_stride"] == 0xA0
    assert report["hinge_refresh"]["condition"] == "sample +0x98 != 0"
    assert report["hinge_refresh"]["transform_call"] == "FUN_007aefb0"


def test_body_accumulator_reset_rebuilds_row_pointer_table():
    report = runtime.build_sdf_body_accumulator_reset(
        primary_count=4,
        secondary_count=3,
        row_indices=[2, 0, 1],
    )
    assert report["ready"] is True
    assert report["solver_vector_after_reset"] == [0.0, 0.0, 0.0, 0.0]
    assert report["solver_matrix_after_reset"] == [0.0, 0.0, 0.0]
    assert report["row_pointers"] == ["+0x154+2*8", "+0x154+0*8", "+0x154+1*8"]


def test_body_accumulator_reset_validation_blocks_bad_pointer_table():
    result = runtime.validate_sdf_body_accumulator_reset({
        "solver_vector_count": 2,
        "solver_matrix_count": 1,
        "solver_vector_after_reset": [0.0],
        "solver_matrix_after_reset": [0.0],
        "row_indices": [0, 1],
        "row_pointers": ["+0x154+0*8"],
    })
    assert result["ready"] is False
    assert "primary-count-mismatch" in result["errors"]
    assert "pointer-table-count-mismatch" in result["errors"]
