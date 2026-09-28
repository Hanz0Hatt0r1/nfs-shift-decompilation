import sdf_endpoint_contribution_schedule_runtime as runtime


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


def test_endpoint_schedule_preserves_self_multiplicity():
    result = runtime.build_endpoint_contribution_schedule(_domain())

    assert result["ready"] is True
    assert result["endpoint_group_count"] == 6
    assert result["self_operation_count"] == 6
    assert result["pair_operation_count"] == 3
    assert result["operation_count"] == 9


def test_endpoint_schedule_has_expected_union_cells():
    result = runtime.build_endpoint_contribution_schedule(_domain())

    assert result["write_cell_count"] == 21
    assert result["lower_triangle_off_diagonal_cell_count"] == 11


def test_self_operations_are_endpoint_specific():
    result = runtime.build_endpoint_contribution_schedule(_domain())

    self_ops = [
        operation
        for operation in result["operations"]
        if operation["kind"] == "self"
    ]

    assert {
        operation["endpoint_field"]
        for operation in self_ops
    } == {"posbody", "negbody"}
    assert {
        operation["body"]
        for operation in self_ops
    } == {"A", "B", "C"}


def test_pair_operations_keep_shared_body_and_kernel():
    result = runtime.build_endpoint_contribution_schedule(_domain())

    pair_ops = [
        operation
        for operation in result["operations"]
        if operation["kind"] == "pair"
    ]

    assert {operation["body"] for operation in pair_ops} == {
        "A",
        "B",
        "C",
    }
    assert {
        operation["kernel"]
        for operation in pair_ops
    } == {
        "FUN_007bbb80",
        "FUN_007bb250",
    }


def test_pair_kernel_prefers_joint_over_hinge_and_bar():
    left = {
        "section": "HINGE",
    }
    right = {
        "section": "JOINT",
    }

    assert runtime._pair_kernel(left, right) == "FUN_007bbb80"


def test_validate_endpoint_schedule_accepts_fixture():
    result = runtime.build_endpoint_schedule_contract(_domain())

    assert result["validation"]["ready"] is True
    assert result["validation"]["errors"] == []


def test_validate_endpoint_schedule_rejects_upper_cell():
    result = runtime.build_endpoint_contribution_schedule(_domain())
    result["operations"][0]["cells"].append([0, 5])

    validation = runtime.validate_endpoint_schedule(result)

    assert validation["ready"] is False
    assert "operation-cell-out-of-lower-domain:0,5" in validation["errors"]


def test_validate_endpoint_schedule_rejects_self_count_mismatch():
    result = runtime.build_endpoint_contribution_schedule(_domain())
    result["self_operation_count"] -= 1

    validation = runtime.validate_endpoint_schedule(result)

    assert validation["ready"] is False
    assert "self-operation-count-mismatch" in validation["errors"]


def test_summarize_endpoint_schedule():
    result = runtime.summarize_endpoint_schedule(
        {
            "scalar_count": 40,
            "body_count": 11,
            "runtime_constraint_records": 28,
            "endpoint_group_count": 56,
            "self_operation_count": 56,
            "pair_operation_count": 42,
            "operation_count": 98,
            "write_cell_count": 700,
            "lower_triangle_off_diagonal_cell_count": 330,
            "ready": True,
        }
    )

    assert result["scalar_count"] == 40
    assert result["endpoint_group_count"] == 56
    assert result["pair_operation_count"] == 42
    assert result["write_cell_count"] == 700
