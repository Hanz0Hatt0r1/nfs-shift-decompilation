from spline_arc_length_runtime import (
    SplineCursor,
    advance_spline_cursor,
    clamp_and_dispatch_offset,
    describe_parameter_normalization,
    early_boundary_result,
    rebuild_spline_length,
)


def test_parameter_normalization_matches_while_loops():
    result = describe_parameter_normalization(segment_index=2, parameter=2.25)
    assert result["segment_index"] == 4.0
    assert result["parameter"] == 0.25
    assert result["steps"] == ["increment-index", "increment-index"]


def test_reverse_boundary_uses_11640_callback_boundary():
    result = early_boundary_result(
        spline_length=100,
        cursor_progress=0.25,
        proposed_distance=-50,
        normalized_progress=-0.25,
        reverse=True,
        endpoint_handler_result=12.5,
    )
    assert result["status"] == "reverse-boundary"
    assert result["action"] == "FUN_00811640"
    assert result["remaining"] == 12.5


def test_forward_boundary_uses_16120_callback_boundary():
    result = early_boundary_result(
        spline_length=100,
        cursor_progress=0.75,
        proposed_distance=50,
        normalized_progress=1.25,
        reverse=False,
        external_scalar=0.0,
        spline_loop_flag=False,
        endpoint_handler_result=17.5,
    )
    assert result["action"] == "FUN_00816120"
    assert result["remaining"] == 17.5


def test_cursor_advance_accepts_sampler_step_and_updates_position():
    cursor = SplineCursor(state_10=0, segment_t=0, x=0, y=0, z=0)

    def sampler(segment_index, t, param3, mode):
        return {
            "position": [1.0, 0.0, 0.0],
            "state_10_out": 0.5,
            "segment_t_out": t,
            "denominator": 1.0,
            "param3_out": param3,
        }

    state, result = advance_spline_cursor(
        cursor,
        spline_length=10,
        param3=1,
        distance_delta=1,
        boundary_callback_enabled=False,
        reverse_or_zero_flag=False,
        sampler=sampler,
        max_outer_steps=1,
    )
    assert state.x == 1.0
    assert result["accepted_steps"] == 1


def test_cursor_advance_refines_a_too_large_step():
    cursor = SplineCursor()

    def sampler(segment_index, t, param3, mode):
        return {
            "position": [2.0 * t, 0.0, 0.0],
            "state_10_out": 0.0,
            "segment_t_out": t,
            "denominator": 1.0,
            "param3_out": param3,
        }

    _, result = advance_spline_cursor(
        cursor,
        spline_length=10,
        param3=1,
        distance_delta=0.001,
        boundary_callback_enabled=False,
        reverse_or_zero_flag=False,
        sampler=sampler,
        max_outer_steps=1,
    )
    assert result["refinement_steps"] >= 1


def test_offset_dispatch_matches_22620_clamp_shape():
    result = clamp_and_dispatch_offset(
        cursor_progress=0.5,
        spline_length=10,
        param3=0.2,
        param4=1.0,
    )
    assert result["raw_offset"] == -3.0
    assert result["selected_delta"] == -1.0


def test_length_rebuild_sums_positive_sampler_returns():
    result = rebuild_spline_length(node_count=4, sample_returns=[2, 3, 0, 10])
    assert result["length"] == 5.0
    assert result["iterations"] == 2
