import native_physics_workspace_boundary as runtime


def test_phase603_native_workspace_boundary_is_source_backed():
    report = runtime.build_native_physics_workspace_boundary(40)

    assert report["format"] == "SHIFT.NativePhysicsWorkspaceBoundary/1"
    assert report["ready"] is True
    assert report["blocking_reasons"] == []
    assert report["scalar_count"] == 40

    storage = report["storage"]
    assert storage["matrix_double_count"] == 1600
    assert storage["matrix_bytes"] == 12800
    assert storage["retail_row_pointer_count"] == 40
    assert storage["retail_row_pointer_bytes"] == 160
    assert storage["rhs_scalar_count"] == 40
    assert storage["rhs_bytes"] == 320
    assert storage["native_row_indices"][0] == 0
    assert storage["native_row_indices"][1] == 40
    assert storage["native_row_indices"][-1] == 1560

    fixed = report["fixed_step"]
    assert fixed["provider_bound"] is False
    assert fixed["provider_absent_clear_ready"] is True
    assert fixed["body_contribution_execution"] is False
    assert fixed["constraint_coupling_execution"] is False
    assert fixed["solver_execution"] is False
    assert fixed["post_solve_execution"] is False


def test_phase603_rejects_non_positive_scalar_domain():
    for value in (0, -1):
        try:
            runtime.build_native_physics_workspace_boundary(value)
        except ValueError as exc:
            assert "scalar_count must be positive" in str(exc)
        else:
            raise AssertionError("non-positive scalar_count was accepted")
