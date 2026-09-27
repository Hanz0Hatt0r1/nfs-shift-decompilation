import pytest

import sdf_constraint_matrix_assembly_runtime as runtime


def test_create_zero_matrix_builds_solver_domain():
    assert runtime.create_zero_matrix(3) == [
        [0.0,0.0,0.0],
        [0.0,0.0,0.0],
        [0.0,0.0,0.0],
    ]


def test_assemble_lower_triangle_preserves_source_write_direction():
    result = runtime.assemble_lower_triangle(
        5,
        [
            {"kind": "joint", "row_base": 2, "column_base": 0, "block": ((1,2),(3,4))},
            {"kind": "hinge", "row_base": 3, "column_base": 1, "block": ((5,), (6,))},
        ],
    )
    assert result["matrix"] == [
        [0.0,0.0,0.0,0.0,0.0],
        [0.0,0.0,0.0,0.0,0.0],
        [1.0,2.0,0.0,0.0,0.0],
        [3.0,9.0,0.0,0.0,0.0],
        [0.0,6.0,0.0,0.0,0.0],
    ]
    assert result["contribution_count"] == 2
    assert result["upper_nonzero_without_lower"] == []


def test_materialize_symmetric_view_is_explicit_derived_operation():
    lower = [
        [1.0,0.0,0.0],
        [2.0,3.0,0.0],
        [4.0,5.0,6.0],
    ]
    assert runtime.materialize_symmetric_view(lower) == [
        [1.0,2.0,4.0],
        [2.0,3.0,5.0],
        [4.0,5.0,6.0],
    ]


def test_assembler_contract_lists_all_recovered_block_types():
    report = runtime.describe_sdf_constraint_matrix_assembly_contract()
    assert report["ready"] is True
    assert report["kernels"] == {
        "SEED": "FUN_007ba2b0",
        "JOINT": "FUN_007bbb80",
        "HINGE": "FUN_007bb250",
        "BAR": "FUN_007bb6c0",
    }
    assert "JOINT/HINGE 3x2" in report["blocks"]
    assert "HINGE/BAR 2x1 or 1x2" in report["blocks"]
    assert "BAR/BAR 1x1" in report["blocks"]


def test_assembler_rejects_non_square_matrix():
    with pytest.raises(ValueError, match="square"):
        runtime.add_block([[0,0],[0]], row_base=0, column_base=0, block=((1,),))


def test_build_solver_ready_matrix_applies_identity_constraints_after_assembly():
    result = runtime.build_solver_ready_matrix(
        3,
        [
            {"kind": "joint", "row_base": 1, "column_base": 0, "block": ((2,), (3,))},
        ],
        [7.0, 8.0, 9.0],
        [1],
    )
    assert result["ready"] is True
    assert result["assembled"]["matrix"] == [
        [0.0,0.0,0.0],
        [2.0,0.0,0.0],
        [3.0,0.0,0.0],
    ]
    assert result["matrix"] == [
        [0.0,0.0,0.0],
        [0.0,1.0,0.0],
        [3.0,0.0,0.0],
    ]
    assert result["rhs"] == [7.0,0.0,9.0]


def test_retail_matrix_storage_uses_scalar_count_row_stride():
    layout = runtime.build_retail_matrix_storage(
        4,
        matrix_base_address=0x1000,
    )
    assert layout["row_indices"] == [0, 4, 8, 12]
    assert layout["row_pointers"] == [
        0x1000,
        0x1020,
        0x1040,
        0x1060,
    ]
    assert layout["matrix_double_count"] == 16
    assert layout["matrix_bytes"] == 128


def test_retail_matrix_materialization_matches_row_pointer_formula():
    result = runtime.materialize_retail_matrix(
        [
            [1, 2, 3],
            [4, 5, 6],
            [7, 8, 9],
        ],
        matrix_base_address=0x2000,
    )
    assert result["matrix_pool"] == [
        1.0, 2.0, 3.0,
        4.0, 5.0, 6.0,
        7.0, 8.0, 9.0,
    ]
    assert result["layout"]["row_indices"] == [0, 3, 6]
    assert result["layout"]["row_pointers"] == [0x2000, 0x2018, 0x2030]
    assert runtime.read_retail_matrix_cell(
        result["matrix_pool"],
        scalar_count=3,
        row_index_offset=result["layout"]["row_indices"][2],
        column=1,
    ) == 8.0


def test_retail_matrix_storage_validation_accepts_canonical_layout():
    matrix = [
        [1.0, 0.0, 0.0],
        [2.0, 3.0, 0.0],
        [4.0, 5.0, 6.0],
    ]
    layout = runtime.build_retail_matrix_storage(3, 0x3000)
    result = runtime.validate_retail_matrix_storage(matrix, layout)
    assert result["ready"] is True
    assert result["errors"] == []
    assert result["validated_rows"] == 3


def test_retail_matrix_storage_validation_rejects_wrong_row_offset():
    matrix = [[1.0, 0.0], [2.0, 3.0]]
    layout = runtime.build_retail_matrix_storage(2, 0x4000)
    layout["row_indices"][1] = 1
    result = runtime.validate_retail_matrix_storage(matrix, layout)
    assert result["ready"] is False
    assert "row-1-index-mismatch" in result["errors"]


def test_retail_matrix_storage_rejects_invalid_row_index_length():
    with pytest.raises(ValueError, match="row_indices length"):
        runtime.build_retail_matrix_storage(3, row_indices=[0, 3])


def test_retail_matrix_storage_rejects_non_square_matrix():
    with pytest.raises(ValueError, match="square"):
        runtime.flatten_retail_matrix([[1, 2], [3]])


def test_solver_ready_matrix_exposes_retail_storage_after_identity_reset():
    result = runtime.build_solver_ready_matrix(
        3,
        contributions=[
            {
                "kind": "seed",
                "row_base": 0,
                "column_base": 0,
                "block": (
                    (1, 1, 0),
                    (1, 1, 1),
                    (0, 1, 1),
                ),
            },
        ],
        rhs=[5, 6, 7],
        selected_identity_nodes=[1],
    )
    assert result["format"] == "SHIFT.SDFSolverReadyMatrix/2"
    assert result["matrix"][1] == [0.0, 1.0, 0.0]
    assert result["rhs"] == [5.0, 0.0, 7.0]
    retail = result["retail_storage"]
    assert retail["row_indices"] == [0, 3, 6]
    assert retail["row_pointers"] == [0, 24, 48]
    assert retail["matrix_pool"][4] == 1.0
    assert retail["matrix_pool"][1] == 0.0
    assert retail["matrix_pool"][3] == 0.0


def test_assembly_contract_exposes_identity_reset_as_late_stage():
    report = runtime.describe_sdf_constraint_matrix_assembly_contract()
    assert report["assembly_order"][-1] == "BAR kernel"
    assert report["limitations"][1].startswith("Coefficient values")
