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
        [0.0,0.0,6.0,0.0,0.0],
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
