import sdf_constraint_solver_frame_runtime as frame


def test_solver_frame_contract_exposes_exact_dispatch_and_projection_widths():
    report = frame.describe_sdf_solver_frame_contract(
        solver_scalar_count=6,
        body_count=2,
    )
    assert report["ready"] is True
    assert report["entry"] == "FUN_007b3f40"
    assert report["provider_branch"]["provider_absent"]["rhs_clear"] == (
        "zero 6 doubles at +0x40"
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
