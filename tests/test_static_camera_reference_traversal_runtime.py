from static_camera_reference_traversal_runtime import (
    advance_reference_record,
    copy_reference_record,
    describe_backward_transition,
    describe_forward_transition,
    describe_static_camera_reference_layout,
    retreat_reference_record,
)


def test_reference_record_has_exact_25_dwords():
    source = list(range(25))
    assert copy_reference_record(source) == source


def test_forward_step_sets_index_from_owner_then_increments():
    result = advance_reference_record(
        list(range(25)),
        owner_index=2,
        boundary_hit=False,
    )
    assert result["record"][0x19] == 3
    assert result["status"] == "advanced"


def test_forward_step_stops_on_owner_zero_boundary_hit():
    result = advance_reference_record(
        list(range(25)),
        owner_index=0,
        boundary_hit=True,
    )
    assert result["record"][0x19] == 0
    assert result["status"] == "boundary-stop"
    assert result["actions"][1]["action"] == "FUN_007025a0"


def test_backward_step_sets_index_from_owner_then_decrements():
    result = retreat_reference_record(
        list(range(25)),
        owner_index=4,
        boundary_hit=False,
    )
    assert result["record"][0x19] == 3


def test_backward_step_stops_on_owner_zero_boundary_hit():
    result = retreat_reference_record(
        list(range(25)),
        owner_index=0,
        boundary_hit=True,
    )
    assert result["status"] == "boundary-stop"
    assert result["actions"][1]["action"] == "FUN_00702580"


def test_forward_transition_emits_three_words_and_unit_scalar():
    result = describe_forward_transition(
        next_record_exists=True,
        next_record_id="next",
        current_record_id="current",
    )
    assert result["output_words"] == ["next", "current", 0]
    assert result["output_scalar"] == 1.0


def test_backward_transition_emits_one_sentinel_word_and_unit_scalar():
    result = describe_backward_transition(
        previous_record_exists=True,
        previous_record_id="prev",
        current_record_id="current",
    )
    assert result["output_words"] == ["prev", "current", 0x3F800000]
    assert result["output_scalar"] == 1.0


def test_reference_layout_exposes_exact_byte_size_and_index_offset():
    result = describe_static_camera_reference_layout()
    assert result["record_bytes"] == 100
    assert result["index_offset"] == 0x64
