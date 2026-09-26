from spline_base_primitives_runtime import (
    advance_spline_cursor,
    describe_spline_object_destroy,
    interpolate_spline_position,
    sample_spline_slot,
)


def test_spline_destroy_preserves_exact_resource_release_order():
    result = describe_spline_object_destroy()
    assert [a["action"] for a in result["actions"]] == [
        "write vtable",
        "FUN_00688010",
        "FUN_006310c0",
        "FUN_006310c0",
        "FUN_006310c0",
        "FUN_006310c0",
        "FUN_004f0050",
        "FUN_006383f0",
    ]


def test_spline_slot_sampler_uses_only_slots_zero_and_one():
    words = list(range(25))
    result = sample_spline_slot(source_slot=1, resolved_words=words)
    assert result["source_slot"] == 1
    assert result["words"][0x64 // 4] == 0
    assert len(result["words"]) == 26


def test_spline_position_interpolation_corrects_y_wrap_before_blend():
    result = interpolate_spline_position(
        first_position=[1, 10, 3],
        second_position=[5, 20, 7],
        first_wrap=1,
        second_wrap=2,
        factor=0.25,
    )
    assert result["first_position"][1] == 2.0
    assert result["second_position"][1] == 4.0
    assert result["result"] == [2.0, 2.5, 4.0]


def test_forward_cursor_increments_plus_64_segment_index():
    result = advance_spline_cursor(
        cursor_words=list(range(26)),
        current_segment_index=3,
        next_segment_index=4,
        direction="forward",
        wrap_helper_changed=False,
    )
    assert result["segment_index"] == 4
    assert result["words"][25] == 4


def test_backward_cursor_decrements_plus_64_segment_index():
    result = advance_spline_cursor(
        cursor_words=list(range(26)),
        current_segment_index=3,
        next_segment_index=2,
        direction="backward",
        wrap_helper_changed=False,
    )
    assert result["segment_index"] == 2
    assert result["words"][24] == 2


def test_cursor_can_return_through_wrap_helper_at_zero():
    result = advance_spline_cursor(
        cursor_words=list(range(26)),
        current_segment_index=0,
        next_segment_index=7,
        direction="forward",
        wrap_helper_changed=True,
    )
    assert result["status"] == "helper-wrapped"
    assert result["helper"] == "FUN_007025a0"
