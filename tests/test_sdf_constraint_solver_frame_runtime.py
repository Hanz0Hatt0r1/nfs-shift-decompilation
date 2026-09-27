import sdf_constraint_solver_frame_runtime as frame


def test_solver_frame_contract_exposes_exact_dispatch_and_projection_widths():
    report = frame.describe_sdf_solver_frame_contract(
        solver_scalar_count=6,
        body_count=2,
    )
    assert report["ready"] is True
    assert report["entry"] == "FUN_007b3f40"
    assert report["provider_branch"]["provider_absent"]["rhs_clear"] == (
        "zero scalar_count doubles at +0x40"
    )
    assert report["body_projection"]["JOINT"]["width"] == 3
    assert report["body_projection"]["HINGE"]["width"] == 2
    assert report["body_projection"]["BAR"]["width"] == 1
    assert report["body_projection"]["JOINT"]["sample_scalar_base"] == "+0x30"
    assert report["body_projection"]["HINGE"]["sample_scalar_base"] == "+0x94"
    assert report["body_projection"]["BAR"]["sample_scalar_base"] == "+0x30"
    assert report["builtin_diagonal_reset"]["function"] == "FUN_007b2210"
    assert report["solve_dispatch"]["provider_present"] == "provider vtable +0x18"
    assert report["solve_dispatch"]["provider_absent"] == "FUN_007b0f20"


def test_solver_frame_profile_validation_accepts_ready_asset_profile():
    result = frame.validate_sdf_solver_frame_profile({
        "summary": {
            "sdf_solver_scalar_count": 5,
            "sdf_constraint_solver_graph_ready": True,
            "sdf_sparse_solver_contract_ready": True,
        }
    })
    assert result["ready"] is True
    assert result["errors"] == []


def test_solver_frame_profile_validation_blocks_missing_solver_graph():
    result = frame.validate_sdf_solver_frame_profile({
        "summary": {
            "sdf_solver_scalar_count": 5,
            "sdf_constraint_solver_graph_ready": False,
            "sdf_sparse_solver_contract_ready": True,
        }
    })
    assert result["ready"] is False
    assert "solver-graph-not-ready" in result["errors"]


def test_builtin_diagonal_reset_derives_odd_base_scalar_blocks():
    import sdf_constraint_solver_frame_runtime as frame

    scalar = {
        "order": [0, 1, 2],
        "block_widths": [3, 2, 1],
        "solver_base_index_by_record": {0: 0, 1: 3, 2: 5},
    }
    result = frame.derive_builtin_diagonal_reset_nodes(scalar)
    assert result["scalar_nodes"] == [3, 4, 5]
    assert result["selected_record_count"] == 2
    assert result["selected_records"][0]["record_index"] == 1
    assert result["selected_records"][1]["record_index"] == 2


def test_builtin_diagonal_reset_zeroes_rows_columns_and_rhs():
    import sdf_constraint_solver_frame_runtime as frame

    result = frame.apply_builtin_diagonal_reset(
        [
            [1, 2, 3],
            [4, 5, 6],
            [7, 8, 9],
        ],
        [10, 11, 12],
        [1],
    )
    assert result["matrix"] == [
        [1.0, 0.0, 3.0],
        [0.0, 1.0, 0.0],
        [7.0, 0.0, 9.0],
    ]
    assert result["rhs"] == [10.0, 0.0, 12.0]


def test_solver_frame_contract_v2_separates_pre_and_post_solve():
    report = frame.describe_sdf_solver_frame_contract(
        solver_scalar_count=5,
        body_count=3,
    )
    assert report["format"] == "SHIFT.SDFConstraintSolverFrameRuntime/2"
    assert report["pre_solve"]["order"] == [
        "FUN_007b3ed0",
        "FUN_007bb8d0 per body",
        "FUN_007bc680 per body",
        "FUN_007ba570 per body",
        "FUN_007b2210 selected scalar rows",
        "provider vtable +0x18 or FUN_007b0f20",
    ]
    assert report["post_solve"]["function"] == "FUN_007b4110"
    assert report["post_solve"]["source_line"] == 814168


def test_solver_frame_v2_post_solve_preserves_exact_constraint_widths():
    report = frame.describe_sdf_solver_frame_contract(solver_scalar_count=6)
    assert report["post_solve_projection"]["JOINT"]["width"] == 3
    assert report["post_solve_projection"]["HINGE"]["width"] == 2
    assert report["post_solve_projection"]["BAR"]["width"] == 1
    assert report["post_solve_projection"]["BAR"]["vector_source"] == (
        "+0x40/+0x48/+0x50"
    )
